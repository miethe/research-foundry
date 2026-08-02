---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-source-metadata-propagation
title: "Source Metadata Capture & Provenance-Preserving Propagation — Human Brief"
status: draft
category: human-briefs

feature_slug: source-metadata-propagation
feature_family: source-metadata-propagation
feature_version: v1

prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md
  - docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-feasibility-brief.md
  - docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - docs/project_plans/human-briefs/rights-entity-model.md
  - docs/dev/architecture/rf-run-export-schema.json

owner: nick
contributors: [Opus orchestrator]

audience: [humans]

priority: P2
confidence: 0.78

created: 2026-08-02
updated: 2026-08-02
target_release: ""

tags: [human-brief, source-metadata, provenance, governance]
---

# Source Metadata Capture & Provenance-Preserving Propagation — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-08-02

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md` — **not found on
  disk as of this brief's authoring (2026-08-02)**. The plan's frontmatter already points to it; confirm
  it has landed before execution starts, or treat the plan as the interim source of truth.
- **Plan**: `docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md`
- **Design Specs**: `source-metadata-propagation-proposed-adr.md` (status: proposed — acceptance happens
  at the exploration verdict gate, not in the ADR itself)
- **SPIKEs**: `source-metadata-propagation-charter.md` (3-leg investigation: tech / risk / prior-art) +
  `spikes/tech-findings.md`, `spikes/risk-findings.md`, `spikes/prior-art-findings.md`
- **Feasibility Brief**: `source-metadata-propagation-feasibility-brief.md` — verdict: conditional,
  confidence 0.78, scoped to Phases A+B; Phase C (third-party live ingestion) deferred behind a licensing
  precondition
- **Related Briefs**: `rights-entity-model.md` (H5 anchor feature — see §2)

---

## 2. Estimation Sanity Check

**Itemized floor (H4 bundle-vs-sum)**: Phases A+B itemize to **40 pts** (A items: 5+3+5+3 = 16 for
metadata/rank/hydration/rollups, plus 5 catalog + 5 regression; B items: 3+5+3+3). 6 capability areas
(schema, ingest, export, catalog, governance, tests) ≥ 3, so the per-area sum is the **floor**, not the
estimate.

**H1 noun-counting**: one new authoritative entity (`source_attribution`) + one mirror block + new
catalog columns → ≥2 pts each, already inside the itemization.

**H2 dual-implementation**: N/A — no local+enterprise split on this surface. ×1.0.

**H3 algorithmic service flag**: `check_attribution_divergence` (divergence) and `attribution_triage.py`
(triage/resolution) both trip the keyword flag → each already ≥3 pts. Satisfied.

**H5 anchor**: `rights-entity-model-v1` — ADR `docs/dev/architecture/adr-rights-entity-model.md`, merged
`17a2cb0`, 6 phases P0–P5. All three exploration legs converged on it independently. Same shape:
non-authoritative mirror on `source_card`, additive no-backfill schema change, fail-closed governance
boundary proven by negative tests. **Delta justification**: this feature *adds* export-time propagation
and catalog columns the anchor did not have, and *drops* third-party fetch (deferred to Phase C) — net
roughly comparable to slightly larger, which is why 4 milestones rather than the anchor's 6 phases.

**H6 hidden plumbing (+15%)**: +6 pts for schema-registry wiring, catalog row builders, DTOs, CHANGELOG,
the `.claude/rules/` guard-rule doc, and docs.

**H7 huge-file multiplier**: `catalog_service.py` is **2242 lines** (>2K) → the catalog task's 5 pts ×2
= +5.

**Bottom-up total: ~48 pts** (40 floor + 6 + 5, rounded). **This exceeds the feasibility brief's own
A+B subtotal of 38** — the delta is entirely H6 and H7, which the brief's itemization carried no line
for. Per the skill, trust bottom-up. Note this discrepancy explicitly for the human reader; it is the
single most likely source of schedule surprise.

**Large-file override check**: `catalog_service.py` >2K lines, but the change is *localized* (add
columns + row-builder fields), which the override explicitly exempts. Already Tier 3 regardless.

**Top-down anchor**: `rights-entity-model-v1` (~41–45 pts, 6 phases). This feature lands at ~48 pts
across 4 milestones — comparable scope, more compressed structure (see H5 above).

**Reconciliation**: Bottom-up (48) beats the feasibility brief's earlier itemization (38) by ~26%. Both
H6 and H7 are legitimate, previously-uncounted line items rather than padding — trust the 48-pt number
for scheduling, not the brief's 38.

---

## 3. Wave & Orchestration Notes

**Critical path**: The plan sequences all 4 milestones (`waves: [["M1"], ["M2"], ["M3"], ["M4"]]`), but only
part of that is load-bearing. **`M1 → M2` is merge-conflict hygiene, not a dependency** — both changes are
additive under existing open seams in `schemas/source_card.schema.yaml`, and M2 could land first if
convenient; it is sequenced only to keep two agents off that shared file. **`M2 → M3 → M4` IS a genuine
semantic dependency**: M3 enforces a shape M2 defines, and M4's rollups and columns consume both M1's
hydration and M2's records. Do not let an executor treat M1→M2 as immovable.

**Parallel opportunities**: None across milestones — the shared-file barrier rules out overlap. Within a
milestone, task-level parallelism is an implementation-planner call, not an orchestration lens.

**Merge order**: M1 → M2 → M3 → M4, one milestone per merge. Do not attempt to land M2 and M3 in the same
window even if M3 looks trivial — M3 is the authorization-boundary milestone and needs to stand on its
own commit for auditability.

**Gate shape** (do not over-gate M1–M3, do not under-gate M4):
- **M1**: two lenses (`security` + `validator`), reason `untrusted-input` — it threads externally-controlled
  provider strings (authors/DOI/publisher, currently hardcoded empty at `source_cards.py:322-329`) into
  cards that reach exported claim JSON.
- **M2**: one lens (`validator`).
- **M3**: two lenses (`security` + `validator`), reason `authz-boundary`.
- **M4**: two lenses (`security` + `validator`), reason `irreversible-outward` (it performs a literal
  catalog schema migration) — **plus a per-milestone `karen`**, because M4 is the C3 milestone.
- **Correct final shape**: M1 security+validator/untrusted-input · M2 validator · M3
  security+validator/authz-boundary · M4 security+validator/irreversible-outward + per-milestone karen (C3).
- M1–M3 are C2 and get **only the single final-tree karen** — do not schedule per-milestone karen passes
  on them; that would be over-gating relative to the plan's own risk classification.

**Mode-D halts**: both M3 (authorization boundary — the guard rule that stops an agent from minting a
third-party attribution value) and M4 (catalog schema migration) require an explicit human
approval stop before landing, per the plan's Mode-D note.

**Cross-feature coupling**: None currently in flight that touches `source_card.schema.yaml` or
`catalog_service.py` concurrently — confirm this is still true immediately before M1 starts, since both
are hot files.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | Plan frontmatter | Which search-router providers actually return DOI / citation counts / structured authors today? M1 sizing rests on it. | open — resolve at M1 entry | implementation-planner / M1 executor |
| OQ-4 | Plan frontmatter | Is `trust.source_rank` derivation deterministic from source_type + rights/access basis, or does it need a capture-time model call? | open — resolve at M1 entry | M1 executor |
| OQ-3 | Plan frontmatter | Does `attribution_summary` carry values, or only attribution_ids + counts? | **closed — resolved at plan authoring** | Plan decision: ids/counts/monotone rollups ONLY, never a raw value; recompute-only from authoritative records |
| OQ-2 | Plan frontmatter | Is the catalog sqlite migration path established, or rebuild-only? M4 sizing rests on it. | open — resolve at M4 entry | M4 executor |
| CO-2 | Charter conditional | Should the Reusable Assertion Ledger (`source_assertion.schema.yaml`) own third-party attributions instead of a new entity? | **closed** — disqualified | Feasibility brief: Ledger disqualified on subject-anchoring before attestation lifecycle is even reached |

**Note on OQ-3**: resolved, not carried forward — leaving it open was an unresolved interface fork that
also changed M4's query contract. Making the mirror value-free is what structurally closes the
sibling-field bypass named in §6 below: there is no value-bearing property left on the card to write into.

**Note on OQ-4**: its answer does **not** threaten the deal-killer. A *write-path* (capture-time) model
call is permitted under the charter; only the *read path* (export/query) must stay fully deterministic
and model-free. Do not let an executor over-read this OQ as reopening the deal-killer.

**Note on CO-2**: this is closed, not deferred. The brief disqualifies the Reusable Assertion Ledger on
subject-anchoring grounds before the question of attestation lifecycle (candidate → cleared) is even
reached — do not let a future contributor re-propose the Ledger as the owning entity without re-litigating
this specific disqualification.

---

## 5. Deferred Items Rationale

- **DEF-1 — Phase C third-party live ingestion** (`services/attribution_fetch/`, `rf attribution` CLI,
  ~8 pts): Deferred because it is licensing-gated. Promote when per-provider license terms for bundle
  redistribution are verified.
- **DEF-2 — Scopus / Web of Science**: Deferred — proprietary, no license currently held. Promote only
  if a license is procured; do not build speculative integration code against these providers first.
- **DEF-3 — Semantic Scholar / PubMed ingestion**: Deferred because it depends on the attribution
  mechanism this plan builds. Promote once Phase B (M2/M3) lands and the entity + governance boundary
  are stable.
- **DEF-4 — `writeback.build_bundle()` attribution summary in the manifest**: Deferred; no committed
  scope in this plan. Promote when a consumer needs attribution surfaced in the writeback manifest
  itself, not just the catalog.
- **DEF-5 — downstream-consumer allowlist audit** (catalog/run-export hand-listed keys): Deferred.
  Promote when a new consumer surface is added that hand-lists source-card keys — audit at that point
  rather than pre-emptively.
- **DEF-6 — live ToS re-verification for Semantic Scholar / NCBI**: Deferred; the risk leg's findings are
  code-trace/desk-research only. Promote before DEF-3 is unblocked — do not let DEF-3 start on stale ToS
  assumptions.

---

## 6. Risk Narrative

- **Authorization-boundary leak (HIGH)**: `_RIGHTS_GOVERNED_FIELDS` in `governance.py:35-40` is a
  structurally blind 4-field name list, and a second name-based rule would reproduce the same blindness
  one level up — an agent simply writes `trust.third_party_citation_rank` instead of the guarded name.
  M3's **PRIMARY control is now schema shape** (`additionalProperties: false` + `if asserter_type
  startsWith third_party_ then retrieval_evidence_ref required`); the name-based guard is defence-in-depth
  only. At the orchestration level: do not let M3 pass on "the guard exists" alone. The negative test
  MUST include a **sibling-field bypass** case, then the schema `if/then` must be removed and the same
  suite must go RED (mutation-verified non-vacuity), exactly as called out in the plan's AC table.
- **No-backfill result-set bias (CERTAIN by construction)**: pre-existing cards will read "no data"
  indistinguishably from "verified zero" unless M4 ships tri-state coverage *with* the query surface,
  not after it. This is a hard M4 gate, not a nice-to-have — watch that an executor doesn't ship the
  filter first and the coverage line "later."
- **Staleness reads as currency (MED)**: a third-party rating that is 18 months old must not render
  identically to one captured yesterday. Refresh creates a new record; in-place overwrite is forbidden.
  Watch for any M2/M4 code path that mutates an existing attribution record rather than superseding it.
- **`pediatric_cds` contamination (MED-HIGH)**: both `oneOf` branches in `pediatric_cds.schema.json` are
  `additionalProperties: false` — a stray key from the new attribution fields is a hard schema-validation
  failure (`ExitCode.SCHEMA(2)`), not a soft warning. This is exactly the kind of thing that passes a
  narrow unit test and then fails the first live `pediatric_cds` bundle. M3's AC table already has a
  dedicated pediatric-namespace test for this — do not let it get treated as redundant with the general
  governance suite.
- **The 7-bundle non-regression is unproven going into execution (MED)**: the exploration code-traced
  this, it never ran `rf verify` against the live bundles. M4's AC requires it live. If M4 shows all 7
  passing, that is new information relative to everything written before this brief — treat it as a
  genuine result, not a formality.

---

## 7. What to Watch For

- **MeatyWiki prior-decision search FAILED** during exploration — hybrid mode aborted with `embedding
  provider unreachable: Ollama 404 at http://10.42.10.76:11434/api/embed`. FTS matched candidates but
  nothing rendered. This is a **failed lookup, not a confirmed absence** of prior decisions on this
  surface. Re-run when the node's embedding provider is back before assuming no prior art exists beyond
  what the charter's prior-art leg found.
- **SkillMeat returned genuinely empty** for "source metadata" and "provenance" queries during
  exploration (note for anyone re-running it: this CLI wants `--format json`, not `--json`).
- **`docs/project_plans/deferred-items-backlog.md` does not exist in this repo** — the deferred-backlog
  look-first step during exploration was a true no-op, so no `DI-` rows were pulled into this feature's
  deferred set. Don't assume DEF-1..DEF-6 above were cross-checked against a backlog; they weren't,
  because there is nothing to cross-check against yet.
- **IntentTree had no genuine related nodes** — one substring false positive on "EventSource" surfaced
  and was discarded. Do not treat IntentTree as having confirmed no related in-flight work; it simply
  found nothing real to report.
- **The 7-bundle `rf verify` non-regression was never executed during exploration** — the whole
  exploration is code-trace only (see §6 above). Do not report M4's live 7-bundle pass as merely
  "confirming what we already knew" — it is the first real execution of that check.
- **The PRD file referenced by this brief and by the plan's own frontmatter does not exist on disk yet**
  (checked 2026-08-02) — confirm it has been authored before treating `prd_ref` as a live pointer.
- **Shared hot files**: `schemas/source_card.schema.yaml` and `catalog_service.py` (2242 lines) are both
  touched by this feature and are exactly the kind of file that silently drifts if another feature lands
  a change to either mid-execution. Re-check for concurrent edits before each milestone, not just before
  M1.
- **The plan's first draft shipped three verified vacuous acceptance criteria — a standing hazard for this
  feature, not a one-off.** (a) `rf verify` was proposed to "prove" export determinism, but
  `verification.py` never calls `export_run()` — and every `rf verify` invocation appends a timestamped
  event to `telemetry/run_trace.jsonl` that `_timeline()` (`export_service.py:1162`) folds into the
  export, so naive byte-comparison could never pass regardless of correctness. (b) A `for` loop over
  glob/grep output exits 0 when nothing matches — the 7-bundle sweep now asserts a **count**, not a
  status. (c) `pytest` on a not-yet-existing test file ERRORS (exit 4), which reads as "ran clean" rather
  than an honest failure. Note also: a reviewer's own proposed fix (`rf export --run-id`) was itself
  wrong — `rf export` is not a command; `export_run()` is reachable only via `export_service` or the API,
  which is why the determinism AC is now an in-process pytest, not a CLI invocation.

---

## 8. Expected Success Behaviors

- [ ] A freshly ingested source card visibly shows populated authors/DOI/publisher where it previously
  showed empty strings (check a real card, not a fixture).
- [ ] A catalog filter on a new attribution attribute states "N of M sources assessed" rather than
  silently returning a biased subset that looks like "0 sources have this rating."
- [ ] Any rendered third-party citation count or rating always displays "as of DATE" alongside the
  number — never a bare number with no observation timestamp.
- [ ] Deleting the `no_agent_authored_attribution_value` guard rule and re-running the governance suite
  turns it RED (non-vacuity check) — if it stays green with the rule removed, the test was never
  exercising the boundary.
- [ ] Running `rf verify` twice against the same run produces byte-identical export output both times
  (no wall-clock or non-deterministic ordering leaking into the propagated attributes).
- [ ] All 7 committed `pediatric_cds` bundles still exit 0 under `rf verify` after the schema change,
  confirmed live — not inferred from the schema diff.

---

## 9. Running Log

- [2026-08-02] Brief created from the implementation plan's frontmatter and the exploration artifacts
  (charter, feasibility brief, proposed ADR, 3 spike findings). Bottom-up estimate (48 pts) exceeds the
  feasibility brief's earlier A+B itemization (38 pts) by ~26%, entirely on H6/H7 — flagged in §2 as the
  likely schedule-surprise source. PRD file confirmed not yet on disk despite being named in both this
  brief's and the plan's frontmatter — flagged in §1 and §7.
