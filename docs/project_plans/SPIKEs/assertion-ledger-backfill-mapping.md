---
schema_version: 2
doc_type: spike
title: "Assertion-Ledger Backfill Mapping — Root Cause, Recovery Feasibility, and Forward-Path Dependency (P2-01)"
status: draft
created: 2026-07-15
feature_slug: assertion-ledger-activation
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
related_documents:
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1/phase-2-backfill.md
  - docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md
research_questions:
  - "RQ1: Is the paraphrase-vs-verbatim mismatch a property of the extraction pipeline (systemic) or historical data only?"
  - "RQ2: For the 93.1% mismatch facts, can the verbatim quote be recovered by matching fact.text to the source card's quote(s)?"
  - "RQ3: Would relaxing the materializer's byte-identity gate preserve the fail-closed provenance guarantee?"
  - "RQ4: What is the recommended Phase-2 strategy, and does C1/forward-write need a paired fix?"
owner: nick
orchestrator: opus-4-8
---

# SPIKE — Assertion-Ledger Backfill Mapping (task P2-01)

This SPIKE is the blocking prerequisite named by `assertion-ledger-activation-v1.md` (task
**P2-01**, 2 pts) and extends OQ-1's corpus check (42 runs / 2,984 facts / 97.0% abstain-eligible)
from "is it 1:1?" to "why, and what — if anything — can be done about it, and does the answer
change what C1/P3 (the forward write driver) needs before it ships."

**Headline finding, ahead of the detail below:** the 97.0% abstain rate is **not historical
debris** — it is a property of the current extraction/ingest pipeline that any forward run will
reproduce almost exactly, **plus a second, independent, and more severe defect** (passage
segmentation is never wired into the assertion registry) that caps forward yield even closer to
0% than the ~3% floor the historical corpus shows today. Both are proven by direct code inspection
and a live experiment against `AssertionRegistry`, not inferred. Phase 2's own decision text
(task P2-01 in `phase-2-backfill.md`) also contains one factual assumption this SPIKE corrects:
option (b)'s "cached source text" does not exist anywhere in this workspace — see RQ2/RQ4.

---

## Investigation Summary

| RQ | Method | Finding | Confidence |
|----|--------|---------|-----------|
| **RQ1** (systemic vs. historical) | Read `extraction.py::_fact_from_point`, `claim_mapping.py::build_claim_ledger`, `source_cards.py::ingest_source`; corpus-wide per-run mismatch-rate distribution across all 42 runs; live experiment against `AssertionRegistry.ingest()`/`find_exact_passages()` using the exact call signature `source_cards.py` uses today | **Systemic — two independent, compounding defects.** (1) `extracted_facts[].text` is always copied from the source card's `extracted_points[].summary` (an LLM-authored paraphrase) — `quote` (the verbatim field) is never read for anything but a boolean `quote_available` flag. `claim_ledger.claims[].text` is then a verbatim copy of `fact.text`, so the claim the materializer must byte-match against a passage is *always* the paraphrase, never the quote. (2) Even on the rare fact where an agent's paraphrase happens to equal its own quote, `ingest_source()`'s call to `registry.ingest()` never passes `passages=`, so the registry stores exactly **one** passage per edition — the entire raw document — and a short quote can never bind via `find_exact_passages()` (proven empirically: 0 matches before the fix, 1 match after). OQ-2 already resolved that C1/P3 reuses this exact `ingest_source()` call, so both defects transfer unchanged to the forward path. | **HIGH** — grounded in source, reproduced live in 40/42 runs (93.2% mean, 97.5% median mismatch rate), and confirmed by direct code execution. |
| **RQ2** (quote-recovery feasibility) | Empirical string-similarity sweep over all 2,786 reproduced mismatch facts: light-normalized exact match, strict word-token substring, `difflib` fuzzy ratio at 6 thresholds, cross-point search (does *any other* quote on the same source card match?), manual inspection of the 0.90–0.999 similarity band | **Low and hard-capped if kept safe.** Light-normalized exact: 0.86%. Strict substring: 3.19%. Fuzzy ≥0.9 (the highest defensible tier): 4.06% — and manual inspection of that band still turns up a tense-changed sentence ("reduced" vs. "reduces"), showing ratio alone cannot cleanly separate cosmetic noise from meaning drift. Cross-point search recovers essentially nothing extra (+0.11%/+0.00%), confirming this is a genuine paraphrase problem, not a mis-linked evidence_id/locator problem. Best safe aggregate: 203 / 2,991 supported facts = **6.79%** (vs. 3.01% doing nothing). Higher thresholds (0.7–0.8) reach 27–41% but visibly admit real semantic drift on manual review — not safe to accept automatically. | **HIGH** — full-corpus measurement, not a sample; manually inspected the risk boundary, not just the aggregate. |
| **RQ3** (gate-relaxation safety) | Direct read of `assertion_materialization.py::_prepare_one` (the `quote != mapping.text` gate and the `assertion_text: mapping.text` persisted field); manual inspection of what a relaxed gate would certify | **No generic threshold relaxation is safe.** The persisted `source_assertion.assertion_text` field is set to `mapping.text` — the claim/paraphrase — and is certified as hash-bound (`find_exact_passages`) to one specific registry passage. Loosening the equality check would let a paraphrase be *labeled* verbatim-passage-bound, exactly the guarantee the module's own docstring disclaims providing ("neither segments passages nor attempts citation resolution"). The only relaxation that does *not* break this contract is symmetric markdown/formatting canonicalization before comparison (backtick/quote/whitespace normalization) — and that is already inside RQ2's numbers, not a separate lever. | **HIGH** — grounded directly in the persisted-field semantics, not just the abstention code names. |
| **RQ4** (recommendation) | Synthesis of RQ1–3, cross-checked against Phase 2's own pre-enumerated options (`phase-2-backfill.md` task P2-01) and OQ-2's resolution that C1/P3 = `ingest_source()` | **Primary: fix-forward-extraction-contract (mandatory, blocking).** C1/P3 is not "capped at ~3%" as historical data implies — it is capped near **0%** today because of the passage-segmentation gap alone, independent of the paraphrase gap. **Secondary (Phase 2 only): a narrowly-scoped quote-recovery step** (fuzzy ≥0.9 + spot-check) layered onto accept-low-yield, **not** the open-ended "re-derive against cached source text" Phase 2's own task text describes (that cache does not exist — see below). Reject open-ended gate-relaxation. Reject defer — the evidence is decisive now. | **HIGH** |

---

## RQ1 — Systemic vs. historical: full trace of the defect

### 1a. The paraphrase-vs-quote defect (extraction/claim-mapping)

`src/research_foundry/services/extraction.py:66-78` (`_fact_from_point`):

```python
def _fact_from_point(point: dict) -> dict:
    text = str(point.get("summary") or "").strip()
    quote = point.get("quote")
    return {
        "evidence_id": str(point.get("evidence_id") or "ev_001"),
        "text": text or "(no summary)",
        ...
        "quote_available": bool(quote),   # <- quote is used ONLY as a boolean flag
        ...
    }
```

`quote` is read exactly once, to set a boolean. The actual verbatim string is never copied
anywhere in the extraction card. `src/research_foundry/services/claim_mapping.py:208`
(`build_claim_ledger`) then does `text = str(fact.get("text") or "").strip()` and writes it
straight into `claim["text"]` — so the claim ledger's `text` field, the value the materializer
must byte-match, is *always* the paraphrase, by construction, for every run that goes through
this contract.

Live corroboration from a real source card
(`runs/rf_run_20260613_as_of_mid_2026_what_are/sources/src_20260613_rib009_04.md`):

```yaml
extracted_points:
- evidence_id: ev_002
  summary: "An average GPT Researcher run takes roughly 3 minutes and costs about $0.10."
  quote:   "The average research task takes around 3 minutes to complete, and costs ~$0.1."
```

`extraction_card.extracted_facts[1].text` == the `summary` string verbatim (confirmed by reading
`ext_20260613_5d01acb5_001.yaml`). The `quote` string is never persisted past the source card.

**This is not one carder's style.** Sampled diverse runs/agents confirm the same pattern under
three different carder personas (`rf-swarm-carder`, `knitwit-swarm-carder`, `rf_source_carder`)
across unrelated domains (GPT Researcher docs, Etsy API docs, LangChain internals, LangSmith
docs, an SEC-filing benchmark paper) — summary and quote consistently diverge in wording, and
the divergence is the *point* of writing a summary at all.

### 1b. The passage-segmentation defect (registry ingestion) — new finding beyond OQ-1

`src/research_foundry/services/source_cards.py:311` is the **only** call site of
`AssertionRegistry.ingest()` in the codebase:

```python
registry.ingest(
    src_id, content, media_type=..., access_scope=sensitivity,
    allowed_use=registry_usage, retrieval_locator={...},
    source_card_snapshot=registry.source_card_snapshot(src_id, front_matter),
)   # <- no passages= argument
```

`AssertionRegistry.ingest()` (`assertion_registry.py:398`): `selected = list(passages) if passages
is not None else [raw_text]` — with no `passages=`, the **entire raw document becomes exactly one
passage**. `_prepare_one` in `assertion_materialization.py:307` then calls
`self.registry.find_exact_passages(mapping.source_card_id, quote)`, which matches by exact
SHA-256 of the candidate text against stored passages. A short quote can only ever match the
one whole-document passage if the quote *is* the entire document.

**Live experiment** (`/tmp/rf_spike/passage_binding_test.py`, run via the project's `.venv`):

```
Step 1: ingest exactly as source_cards.ingest_source() does today (no passages=)
  created=True, passages=1
Step 2: find_exact_passages(source_id, <a real verbatim quote substring>)
  matches found: 0   <- confirms a genuine verbatim quote CANNOT bind today
Step 3: find_exact_passages(source_id, <the full raw document text>)
  matches found: 1   <- sanity check, only the whole document matches
Step 4: re-ingest same content WITH passages=[quote, ...] wired explicitly (the fix)
  created=False, reusable=True, passages=3 (additive to the existing edition)
  find_exact_passages(source_id, quote) -> matches found: 1   <- now works
```

This proves the fix is small (wire `passages=[p["quote"] for p in points if p.get("quote")]`
into the existing `ingest_source()` call) and additive/non-breaking (re-ingesting the same
content with new passages just extends the edition), but it is **not optional** — without it,
`find_exact_passages` returns zero matches for essentially any real quote, regardless of whether
1a is ever fixed.

**Why this matters for C1/P3 specifically:** the parent plan's OQ-2 already resolved *"the
forward write driver (P3) wires the existing `rf ingest` CLI command"* — i.e., the exact
`ingest_source()` function tested above. There is no separate, richer forward path; C1 inherits
both 1a and 1b unchanged.

### 1c. Corpus-wide per-run distribution (systemic, not a few outlier runs)

Recomputed the mismatch rate independently per run across all 42 runs with a `claim_ledger.yaml`
(3,667 total claims; 676 are `inference`/`speculation` claims with no `sources` entry — correctly
excluded, matching the materializer's `non_source_claim_candidate` gate — leaving **2,991**
supported, single-sourced facts, within 0.23% of OQ-1's reported 2,984):

- Mean per-run mismatch rate: **93.2%**, median **97.5%**, stdev 18.6%.
- **40 of 42 runs** sit at 90–100% mismatch.
- The only two exceptions are dead ends, not counter-evidence: `rf_run_reusable_assertion_ledger_p0_fixture_v1` (0%) is a *deliberately crafted* P0 test fixture where summary was hand-set equal to quote — it exists specifically to prove the gate works when the contract is honored, which is exactly what this SPIKE independently confirms. `rf_run_20260626_agentic_sdlc_governance_prior_art_landscape` (23.1%) turns out to be a data-quality artifact, not a recovery success: several of its "points" are scraped page-navigation boilerplate ("Skip to content", raw page titles) where there was nothing to paraphrase, so summary trivially equals quote.

### RQ1 verdict

**Definitively systemic.** Forward runs through `rf ingest → rf extract → rf claim-map` will
reproduce the ~97% abstain rate (defect 1a) and, independently, will fail passage binding for
nearly all facts regardless of textual match (defect 1b, newly discovered here, not in OQ-1's
scope). C1/P3 is not merely "capped at the historical ~3% floor" — without both fixes it is
capped closer to 0%.

---

## RQ2 — Empirical quote-recovery results

Ran the recovery sweep against all 2,786 reproduced mismatch facts (matches OQ-1's 2,779 within
0.25%).

| Strategy | Recovered / 2,786 | % of mismatches | Cumulative materializable / 2,991 | Safety verdict |
|---|---|---|---|---|
| Baseline (current byte-identical gate) | 0 | 0% | 90 (3.01%) | current behavior |
| Light-normalized exact (case/whitespace-insensitive) | 24 | 0.86% | 114 (3.81%) | Safe — cosmetic only |
| Strict word-token substring | 89 | 3.19% | 179 (5.98%) | Safe — markup/punctuation only |
| Fuzzy ratio ≥ 0.9 (`difflib`, strict-normalized) | 113 | 4.06% | **203 (6.79%)** | Mostly safe; manual spot-check surfaced 1 tense-drift case in this band — recommend agent/human review, not fully automatic |
| Fuzzy ratio ≥ 0.8 | 343 | 12.31% | 433 (14.5%) | **Unsafe automatic** — real paraphrase divergence appears |
| Fuzzy ratio ≥ 0.7 | 744 | 26.70% | 834 (27.9%) | **Unsafe** — median-similarity examples show genuine meaning reorganization |
| Fuzzy ratio ≥ 0.6 | 1,159 | 41.60% | 1,249 (41.8%) | **Unsafe** |
| Fuzzy ratio ≥ 0.5 | 1,544 | 55.42% | 1,634 (54.6%) | **Unsafe** |
| Cross-point search (any *other* quote, same source card): substring | +3 | +0.11% | negligible | Confirms linkage is not the defect |
| Cross-point search: fuzzy ≥ 0.9 | +0 | +0.00% | negligible | Confirms linkage is not the defect |

Mean fuzzy ratio across all 2,786 mismatches: **0.517**. Mean Jaccard word-overlap: **0.432** —
i.e., the *typical* mismatch shares under half its words with the verbatim quote it's paired
with; this is genuine paraphrasing, not formatting noise.

**Manual inspection of the 0.90–0.999 band (85 facts)** — the band right below "already
matches" — found mostly safe cosmetic differences (markdown backticks, smart quotes, added/
removed parenthetical asides, third-person/passive-voice smoothing) but also at least one
genuine, if minor, meaning shift: *"Simple environmental hardening **reduced** exploit rates..."*
(claim, past tense, describing a specific result) vs. *"...**reduces** exploit rates..."*
(quote, present tense, describing a general property) — ratio 0.992. This confirms fuzzy ratio is
a blunt instrument: it cannot reliably distinguish "same passage, different rendering" from
"same passage, subtly reframed," even at its top percentile.

### RQ2 verdict

Recovery is real but small: **~4% incremental** at the only defensible safety tier (≥0.9,
still spot-check recommended), **~6.8% total** materializable yield combining exact-match +
safe recovery. This is a genuine improvement over the 3.0% naive floor (more than double), but
nowhere near the 25–40%+ that looser thresholds would suggest — and those looser thresholds are
demonstrably unsafe on manual review.

---

## RQ3 — Gate-relaxation safety

`assertion_materialization.py::_prepare_one` (line 341): `"assertion_text": mapping.text` — the
persisted `source_assertion.assertion_text` **is** the claim text (the paraphrase), not the
quote. The quote only exists to *authorize* that persisted string by proving it is byte-identical
to a real, hash-addressed passage (`find_exact_passages`, line 307). This is exactly what the
module's docstring states as its scope boundary: *"[the materializer] neither segments passages
nor attempts citation resolution... A candidate is materialized only when the extraction fact,
claim locator, source-card evidence point, private registry edition, and exact passage all bind
to one another."*

Relaxing `quote != mapping.text` to any similarity/substring threshold would not "recover a
quote" — it would **change what `assertion_text` means**: a downstream consumer of a
`source_assertion` record reasonably assumes that field is the actual quoted text from the bound
passage (the schema literally hash-binds it to one). A relaxed gate would let a paraphrase —
possibly reframing tense, scope, or emphasis, per the RQ2 manual inspection — be certified with
that same guarantee. That is a real correctness/trust regression, not a tuning knob: it would
make the assertion ledger no more trustworthy than the extraction card it's supposed to
strengthen.

**The one relaxation that does not break the contract:** symmetric, deterministic markdown/
formatting canonicalization (strip backticks/smart-quotes, normalize whitespace/case) applied to
*both* `quote` and `fact.text` before the identity check. This is not really "relaxing" the
guarantee — it is fixing a canonicalization gap the current byte-for-byte comparison doesn't
handle — and its yield is already inside RQ2's "light/strict normalized" rows (0.86%–3.19%), not
a new, larger lever.

### RQ3 verdict

**No generic threshold relaxation preserves the fail-closed guarantee.** Any move beyond
formatting canonicalization trades verifiable provenance for yield, which contradicts this
module's explicit design intent.

---

## RQ4 — Recommendation

### Correction to Phase 2's own framing (important before choosing)

`phase-2-backfill.md` describes option (b) as re-deriving "the verbatim span via `locator`
**against the cached source text**." That cache does not exist for this corpus: `find
assertion_ledger -maxdepth 3` from the workspace root returns nothing — **no
`assertion_ledger/` directory exists anywhere in this workspace.** `AssertionRegistry.root`
resolves under it, so this confirms the registry has never been populated for any of the 42
historical runs (consistent with `ledger_write_allowed` defaulting to `False`, and only being
turned on for the first time in the most recent commit, `ba9e551`, per this repo's own git log).
The only verbatim text that has ever existed for this corpus is the short per-point `quote`
field already measured in RQ2. **Option (b), if chosen, should be re-scoped to exactly what RQ2
measured** (fuzzy ≥0.9 over existing per-point quotes + spot-check), not an open-ended
"re-derive from a richer cache" — because there is no richer cache to re-derive from.

### Decision

| Option (from `phase-2-backfill.md`) | Recommended disposition |
|---|---|
| (a) Accept ~3.0% exact-match yield, report coverage transparently | **Adopt as the floor.** Cheapest, no new algorithmic surface, matches the plan's Tier-3 framing. |
| (b) Bounded quote-recovery step | **Adopt, but re-scoped and re-estimated down.** Fuzzy ≥0.9 over existing per-point quotes + a spot-check step (not a "cached source text" re-derivation, which doesn't exist). Raises yield from 3.0% to **6.8%**. Given the algorithm is a single `difflib`-style comparison (no new service, no new store), this is closer to **+1–2 pts**, not the plan's flagged **+3–5 pts**. |
| (c) Defer via retroactive re-extraction | **Reject for this SPIKE's scope** — out of scope per the plan's own framing, and moot given (a)+(b) already gives a decisive, cheap answer. |
| *(new, not in the original three)* Fix the forward extraction/ingest contract (defects 1a + 1b) | **Adopt as a separate, mandatory, blocking track — this is the primary recommendation of this SPIKE.** |

**Primary verdict: fix-forward-extraction-contract.** This is not one of Phase 2's three
pre-enumerated options because Phase 2 was scoped around the *backfill*, not the *forward driver*
— but OQ-2 already ties C1/P3 to the exact code path this SPIKE tested and found broken twice
over (1a: paraphrase copied instead of quote; 1b: no passage segmentation wired into
`AssertionRegistry.ingest()`). Per the parent plan's own risk note ("if a fourth, larger option
is needed, stop and re-plan Phase 2 rather than silently absorbing overrun"), this SPIKE is
explicitly surfacing that fourth option and recommending the plan be updated before P2's build
tasks (P2-02+) or P3 proceed.

**Secondary verdict (Phase 2, backfill only): accept-low-yield + scoped quote-recovery.**
Combine option (a) with a narrow, ratio ≥0.9, spot-checked recovery add-on. Do not build an
open-ended fuzzy-matching service — the data shows diminishing safety past 0.9 within a handful
of percentage points.

**Rejected: open-ended gate-relaxation.** RQ3 shows no generic threshold is safe; folding this
into option (b)'s narrow scope (canonicalization only) already captures the safe portion.

**Rejected: defer.** The evidence obtained here is decisive and inexpensive to act on; deferring
only lets more historical debt accumulate under the same broken forward contract.

---

## Implications for the implementation plan

**Phase 2 (P2) point estimate.** The plan currently anchors P2 at 7 pts (2 pt SPIKE decision +
5 pt build), flagging +3–5 pts if option (b) is chosen. This SPIKE's re-scoped option (b) is a
single bounded comparison utility over data that already exists in-run — recommend **+1–2 pts**,
not +3–5, i.e. a revised P2 estimate of **~8–9 pts** (2 pt SPIKE [delivered by this doc] + ~5 pt
base build + ~1–2 pt scoped recovery add-on), materially cheaper than the plan's own worst-case
flag. Success criteria for P2-02 onward should be restated as: *"backfill materializes ~6.8% of
historical supported facts (exact-match + fuzzy≥0.9-with-spot-check), reports the abstention-code
breakdown transparently in the receipt, and does not silently imply full-corpus coverage"* — this
is a downward revision from whatever baseline expectation existed before OQ-1/this SPIKE, and
should be communicated to stakeholders now rather than discovered at P2-05's dry-run-parity check.

**C1/P3 dependency — hard blocking, not optional.** OQ-2 already resolved that C1/P3 reuses
`source_cards.ingest_source()` verbatim. This SPIKE shows that function, unmodified, will
materialize close to **0%** of forward facts (defect 1b alone is sufficient to guarantee this,
independent of 1a). Recommend a new, explicit blocking task — sequenced before or alongside P2,
not discovered after P3 ships — with two concrete changes:
1. `extraction.py::_fact_from_point` (or a new extraction path) must carry the verbatim `quote`
   through to a materializable field, not only the paraphrased `summary`.
2. `source_cards.py::ingest_source()` must pass `passages=[p["quote"] for p in points if
   isinstance(p.get("quote"), str) and p["quote"]]` into its `registry.ingest()` call.

Without both, shipping P3/C1 on the current contract reproduces this feature's own stated
anti-goal — "the three enabled `foundry.yaml` flags produce observable ledger population instead
of a silent no-op" — for the *forward* path as well as the historical one. Recommend escalating
this to the human orchestrator alongside the P2-01 decision (both are Mode-D/Tier-3 territory
per the plan's own labeling), and updating `phase-2-backfill.md`'s option (b) language to drop
the "cached source text" phrasing, which this SPIKE found to be factually incorrect for this
corpus.

---

## Methodology & Evidence

All experiments were run against the live data-plane corpus (`runs/rf_run_*/claims/
claim_ledger.yaml` and co-located `sources/*.md`), 42 runs, using the project's `.venv` Python for
any code that imports `research_foundry` (per this repo's own "pytest must run under venv"
convention). Scripts are throwaway (`/tmp/rf_spike/*.py`), not committed; key ones:

- `/tmp/rf_spike/experiment.py` — corpus-wide gate replication (per-claim: locate source card →
  match `extracted_points` by `evidence_id`+`locator` → classify missing/mismatch/exact).
- `/tmp/rf_spike/diag2.py` — confirmed the 676-claim denominator gap is `inference`/`speculation`
  claims (588+88), not a methodology error.
- `/tmp/rf_spike/recovery.py` — RQ2's normalization/substring/fuzzy/cross-point sweep over all
  2,786 mismatch records, plus the highest/median/lowest-similarity example dump.
- `/tmp/rf_spike/band_inspect.py` — manual-inspection sample of the 0.90–0.999 fuzzy band.
- `/tmp/rf_spike/passage_binding_test.py` — live `AssertionRegistry.ingest()`/
  `find_exact_passages()` experiment proving the passage-segmentation gap and its fix, using the
  actual project code (`research_foundry.services.assertion_registry`) via `.venv/bin/python`.
- `/tmp/rf_spike/per_run_dist.py` — per-run mismatch-rate distribution across all 42 runs.

Source files read in full or in the cited ranges: `src/research_foundry/services/
assertion_materialization.py`, `extraction.py`, `source_cards.py`, `claim_mapping.py`,
`assertion_registry.py`, `config.py` (ledger-write-allowed default), `paths.py`.

## Dead ends (for future reference)

- Cross-point search (matching a mismatch fact against *other* points' quotes on the same source
  card) was hypothesized to catch mis-linked `evidence_id`/`locator` pairs; it recovered
  essentially nothing (+0.11%/+0.00%), ruling out mis-linking as a contributing cause.
- The 23.1%-mismatch outlier run initially looked like a partial recovery success; inspection
  showed it is a degraded-scrape artifact (nav boilerplate as both summary and quote), not a
  counter-example to the systemic finding.
- Considered whether the raw source content might be cached elsewhere (writebacks, telemetry) to
  give RQ2 a richer substrate than the per-point `quote`; confirmed no `assertion_ledger/`
  directory exists anywhere in the workspace, so no such cache exists for this corpus.

## Post-fix re-measurement (2026-07-16)

Commit `6af82ce` (branch `fix/assertion-extraction-contract`) landed exactly the two defects this
SPIKE's RQ1 identified as blocking (1a: bind `assertion_text`/the exact-passage check to the source
card's verbatim `extracted_points[].quote` instead of the paraphrase, dropping the
`quote != mapping.text` gate; 1b: `source_cards.ingest_source()` now passes `passages=` — deduped
verbatim quotes — into `AssertionRegistry.ingest()` so a short quote binds instead of only the
whole-document passage). This section re-measures the *actual* historical backfill yield against
that fixed code, across all 42 runs, using a throwaway `/tmp` registry + workspace (no writes to
`.rf_state/`, `assertion_ledger/`, `.rf_cache/`, or any real run artifact — every read is of the
real corpus; every write lands under a `tempfile.mkdtemp()` root, discarded after measurement).

**Headline finding, ahead of the detail below: the fix itself is a resounding, order-of-magnitude
success — isolated fact-level yield rises from the pre-fix ~3.0%/6.8% to 94.78% (2,835/2,991
supported facts) — but a third, independent, pre-existing, NOT-yet-fixed defect (newly discovered
here, call it 1c) currently blocks 39 of 42 runs from ever reaching that gate, and the
materializer's all-or-nothing-per-run design means even the fix's ~95% fact-level success rate
collapses to near-zero real output. If you literally ran a backfill today, it would produce 21
assertions out of 2,991 eligible facts (0.70%) — worse than this SPIKE's own pre-fix 3.0% floor —
entirely because of defect 1c, not because the landed fix underperforms.**

### Two measurements, not one: fix-isolated yield vs. real end-to-end yield

| Metric | What it measures | Result |
|---|---|---|
| **B — fix-isolated fact yield** | For every supported fact across all 42 runs (2,991, same denominator as RQ2), call the *real*, unmodified `AssertionMaterializer._prepare_one()` directly against a registry pre-populated via the *real*, unmodified `ingest_source()` registry-write logic — bypassing only the unrelated claim-ledger bijection check (see defect 1c below) so the fix under test can be measured in isolation | **94.78% would materialize** (2,835/2,991). Abstains: `missing_exact_passage_quote` 3.84% (115), `unresolved_passage_binding` 1.37% (41). |
| **A — real, end-to-end, today** | Call the actual public `AssertionMaterializer.materialize_run()` for all 42 runs, unmodified, no bypasses | **21 assertions materialize** across the whole corpus (0.70% of 2,991). 39/42 runs (92.9%) abstain immediately with `non_bijective_fact_claim_mapping` before ever reaching the passage-binding gate. Of the remaining 3 runs, 2 fully materialize (5/5 and 16/16 — the latter is the deliberately-crafted P0 fixture) and 1 (143 claims) aborts entirely (`missing_exact_passage_quote`) despite 82/143 of its own facts individually being materializable. |

Both numbers are real, reproducible measurements against the landed code — they answer different
questions. **B is "did the fix work?" (yes, decisively). A is "would backfilling today produce
value?" (no, because of a separate blocker).**

### RQ1-extended — Defect 1c: the claim-ledger bijection gate (new, independent, NOT fixed by 6af82ce)

`AssertionMaterializer._prepare()` (`assertion_materialization.py:235-249`) calls
`claim_mapping.py::validate_extraction_fact_claim_mappings()` before processing *any* claim in a
run. That function re-derives the claim set from scratch by re-scanning `extractions/*.yaml`
(`extraction_fact_claim_mappings()`) and requires `len(claims) == len(mappings)` plus
per-claim byte-identical `claim_id`/`text`/`sources[0]` fields — i.e., the *entire* persisted
`claim_ledger.yaml` must be exactly reproducible from a fresh scan of extraction cards, with zero
tolerance for anything appended afterward. If it isn't, `validate_extraction_fact_claim_mappings`
raises `ValueError("non_bijective_fact_claim_mapping")`, which `_prepare()` converts to
`_Abstain("non_bijective_fact_claim_mapping")` for the **whole run** — no fact in that run is ever
evaluated against the (now-fixed) passage-binding gate at all.

A corpus-wide diagnostic (re-deriving `extraction_fact_claim_mappings()` and diffing against
`claims[]` for all 42 runs) found the cause precisely: **39/42 runs have extra claims appended
*after* the fact-derived prefix** — and the fact-derived prefix (`claims[:len(mappings)]`) is
**byte-identical to a fresh re-scan in every single one of the 39 runs, with zero exceptions**.
The appended claims are exactly the run's `inference`/`speculation` claims — 588 `inference` + 88
`speculation` = **676**, matching this SPIKE's own RQ1c corpus tally to the claim. This is the
normal, expected downstream behavior of report synthesis (agents append inference/speculation
claims onto the same `claims[]` list after `build_claim_ledger()` first writes it) — not data
corruption. **The validator, as coded, treats normal report-synthesis output as ledger corruption
and refuses to process the run at all**, regardless of whether the fact-derived claims it would
otherwise process are perfectly sound.

This defect is confirmed pre-existing and untouched by the fix under test: `git log` shows
`claim_mapping.py` was last modified in `adeddcb` ("feat(services): full evidence-first pipeline"),
long before `6af82ce`; `git show 6af82ce` touches only `assertion_materialization.py` (the
quote-binding lines) and `source_cards.py` (the `passages=` wiring) — `_prepare()`'s bijection
call and `validate_extraction_fact_claim_mappings()` itself are byte-identical before and after.
This is **not a regression from the landed fix** — it is a separate, previously-undiscovered
blocker this re-measurement surfaces for the first time.

**Compounding factor — the all-or-nothing-per-run design.** Even *if* defect 1c is fixed (e.g., by
validating only the fact-derived prefix, or relaxing the check to ignore trailing
inference/speculation claims), `materialize_run()`'s `_prepare()` loop still aborts the **entire
run** on the *first* fact that fails any gate (`_Abstain` propagates out of the `for` loop with no
partial/skip-and-continue mode). Re-running Metric B's per-run tallies shows that even with 1c
hypothetically fixed, only **8/42 runs (19%)** would have zero abstaining facts and therefore
actually publish anything under `materialize_run()`'s current semantics; the other **34/42 (81%)**
have at least one abstaining fact each (median well under 10% of that run's facts) and would
therefore still yield **zero** assertions for the *entire* run, not a partial 90%+. This is a
second, independent lever — orthogonal to both defect 1c and the (now-fixed) 1a/1b — that
determines whether the fix's 94.78% *fact-level* yield ever becomes *run-level* output.

### Correcting a premise in this task's own framing: there is no quote-length cap

The task briefing that prompted this re-measurement hypothesized a "quotes TOO LONG" cap that
would trigger `ingest_source()`'s `passages=None` whole-document fallback. Direct inspection of
the landed code (`source_cards.py:319-327`) shows no length filter of any kind in that path — every
non-empty `point.get("quote")` is included in `quote_passages` regardless of length; the `_SHORT_QUOTE
= 280` constant exists only inside `_build_points()` (brand-new deterministic point construction for
*new* source cards), which is never invoked when backfilling an *existing* historical source card.
The only way `passages=None` (whole-document fallback) is reached is when **zero** of a card's
points carry any usable quote at all — moot, since every fact on such a card would already abstain
on `missing_exact_passage_quote` before ever reaching passage binding. The *real* granular cap this
measurement found instead is **nested/overlapping quotes**: 6/465 source cards (1.3%) have one
point's quote as a literal substring of another point's quote on the same card (e.g. a markdown
checklist quoted whole by one point and quoted as a shorter tail-fragment by another) — this trips
`AssertionRegistry._passage()`'s own passage-uniqueness invariant (`_PassageSelectionError
("ambiguous_selector")`), which aborts registration of **every** passage on that card, not just
the overlapping one. This affects all 41 `unresolved_passage_binding` facts in Metric B — a small,
real, structural cap distinct from the (non-existent) length-based one hypothesized going in.

### Verdict: does this change the Phase 2 (B2) re-scoping?

**Yes, but not simply "upward."** The passage-binding fix (this SPIKE's own primary recommendation,
now landed) is validated as an unambiguous, order-of-magnitude success at the fact level — 94.78%
vs. the pre-fix 3.0%/6.8% — fully vindicating the "fix-forward-extraction-contract" verdict this
SPIKE gave on 2026-07-15. **But Phase 2/B2 cannot simply move to "accept the now-high yield and
ship a backfill script"** — a new, decisive, blocking prerequisite has been found: **defect 1c
(the claim-ledger bijection gate in `claim_mapping.py::validate_extraction_fact_claim_mappings`)
must be relaxed to tolerate trailing inference/speculation claims before any backfill can process
more than 3/42 runs**, and **the all-or-nothing per-run design in
`AssertionMaterializer._prepare()`/`materialize_run()` should be reworked to a skip-and-continue
per-fact mode** before the fix's ~95% fact-level yield can become real run-level output (otherwise
81% of runs still publish zero assertions apiece). Recommend: (1) escalate defect 1c as a new,
explicit, blocking task sequenced before B2's build tasks — same severity class as 1a/1b, found by
the same method (direct code inspection + full-corpus empirical reproduction); (2) re-scope B2's
success criteria from "accept-low-yield (~6.8%)" to **"94.78% fact-level yield is achievable once
1c is fixed; run-level output additionally requires the all-or-nothing design to become
skip-and-continue, or ~81% of runs will still publish nothing despite eligible facts"** — a
meaningfully higher-value target than the original ~6.8%, but gated on two new prerequisite fixes,
not a plain "ship it" green light.

### Methodology & Evidence (post-fix re-measurement)

Ran against commit `6af82ce` on `fix/assertion-extraction-contract`, using the project's `.venv`
(`./.venv/bin/python`) per this repo's own "pytest must run under venv" convention. All registry
writes and claim-ledger reads/writes were isolated under a fresh `tempfile.mkdtemp(prefix=
"rf_backfill_measure_")` root; the real `runs/`, `.rf_state/`, `assertion_ledger/`, and `.rf_cache/`
directories were never written to (verified: only `shutil.copytree` reads from the real `runs/`
tree; all `AssertionRegistry`/`AssertionMaterializer` instances are constructed with
`paths=FoundryPaths(root=<temp>)`). `schemas/` was copied into the temp root because
`AssertionMaterializer.__init__` hardcodes `SchemaRegistry(schemas_dir=self.paths.schemas)` with no
distribution-root fallback (unlike `source_cards.py`'s own schema helper).

Since no raw fetched document is cached anywhere in this workspace for any historical run
(confirmed again here, consistent with RQ4's finding), each source card's registry "edition
content" was reconstructed as the join of that card's own deduped verbatim quotes — the only
verbatim text that has ever existed for this corpus. This is sufficient to faithfully exercise both
real blocking gates the fix touches (quote presence, and passage-registration uniqueness/binding)
without fabricating anything: nested-quote ambiguity (the one place content construction could in
principle be an artifact) was independently confirmed to be a property of the quotes themselves,
not the join order (see the `ambiguous_selector` example above, where one quote is a literal
substring of another *in the extracted quote text itself*, independent of how they're concatenated).

Key throwaway scripts (not committed): `/tmp/rf_spike_postfix/harness.py` (the consolidated,
final measurement — registry ingestion stats, Metric A via the real `materialize_run()`, Metric B
via direct `_prepare_one()` calls bypassing only the bijection gate, and the "even-if-1c-fixed"
run-level projection) plus three throwaway ad hoc diagnostics used to isolate defect 1c and the
`ambiguous_selector` root cause (bijection-mismatch classifier; failed-card/`unresolved_passage_binding`
cross-reference; bijective-run identification). Source files re-read in full for this
re-measurement: `assertion_materialization.py`, `assertion_registry.py`, `source_cards.py`,
`claim_mapping.py`, `paths.py`, `schemas.py`, `frontmatter.py`, `assertion_identity.py` — plus
`git show 6af82ce` and `git log -- claim_mapping.py` to confirm defect 1c's independence from the
fix under test.

### Dead ends (post-fix re-measurement)

- Considered literally calling `source_cards.ingest_source()` (the public function named in the
  task briefing) rather than reproducing its registry-write block directly. Ruled out: that
  function computes its own new `source_card_id` and regenerates brand-new deterministic
  `extracted_points` via `_build_points()`, which would silently overwrite the historical,
  LLM-authored points a run's claim mappings actually reference by `evidence_id`/`locator` —
  breaking `_evidence_point()`'s lookup for every claim on that card. Reproducing the fixed
  registry-write block (`source_cards.py:306-337`) directly, against the *existing* historical
  source card's own front matter, is the faithful backfill simulation; calling the full function
  is not.
- Considered batching all 42 runs' source-card ingestion strictly in run-chronological order to
  simulate an incremental backfill rather than ingest-all-then-materialize-all. Did not change the
  measured numbers in a way that mattered here (no cross-run source-card-id collisions were found
  in this corpus), so the simpler batch order was kept and is noted as an assumption, not hidden.

## Status History

- 2026-07-15 — draft — investigation complete; RQ1–RQ4 answered with corpus-wide empirical
  evidence and a live code experiment; decisive recommendation given. Awaiting promotion to
  `docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md` (the design-spec
  P2-01 is scoped to produce) and update to the parent plan's `deferred_items_spec_refs`.
- 2026-07-16 — post-fix re-measurement — commit `6af82ce` landed defects 1a/1b; re-measured against
  the fixed code across all 42 runs in an isolated `/tmp` workspace. Fix validated: fact-level yield
  94.78% (was 3.0%/6.8%). But real end-to-end yield today is only 0.70% (21/2,991) because of a
  newly-discovered, independent, pre-existing defect (1c: `claim_mapping.py`'s bijection validator
  rejects any ledger with appended inference/speculation claims — 39/42 runs affected) compounded by
  the materializer's all-or-nothing-per-run design. Recommend escalating defect 1c as a new blocking
  task ahead of B2's build tasks, and re-scoping B2's success criteria accordingly (see verdict
  above) rather than treating this fix alone as backfill-ready.
