---
schema_version: 2
doc_type: spike
title: "Source Metadata Capture & Propagation — Technical Feasibility Findings (tech leg)"
status: completed
created: 2026-08-02
updated: 2026-08-02
feature_slug: source-metadata-propagation
leg_id: tech
exploration_charter_ref: docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md
verdict: feasible-with-constraints
confidence: 0.82
audience: [ai-agents, developers]
related_documents:
  - schemas/source_card.schema.yaml
  - schemas/claim_ledger.schema.yaml
  - schemas/source_assertion.schema.yaml
  - docs/dev/architecture/adr-rights-entity-model.md
  - docs/project_plans/design-specs/claim-term-indexing.md
---

# Technical Feasibility & Owning Entity — tech leg

## 1. Verdict

**`feasible-with-constraints`** — confidence **0.82**.

**The deal-killer is refuted.** Attribute propagation to claims can be made fully deterministic and
recomputable from files alone, with no model call on the read path and no authoritative DB — because
**the propagation mechanism already exists and already does exactly this for a thinner attribute
set**. `export_service._resolve_source()` (`src/research_foundry/services/export_service.py:601-661`)
is already the point where a claim's bare `{source_card_id, evidence_id, relation, locator}` citation
is joined against the loaded source card to attach `title`, `source_type`, `url`, `trust`, `usage`,
`sensitivity`, `quote`, `summary`. The charter's premise that "every attribute of the source is
dropped" is true of the **claim ledger file**, but not of the **export/render path** — the join is
there, it just carries a thin set and nothing downstream queries it as a first-class attribute.

This reframes the work substantially: this is **not** a new propagation mechanism. It is
(a) a capture wiring fix, (b) one new governance entity, and (c) widening an existing deterministic
join. The four named constraints are in §6.

## 2. Owning Entity Recommendation

**Three entities, split by who authored the statement** — this is the load-bearing distinction, and
conflating the three is the main design hazard.

| What | Owner | Change class |
|---|---|---|
| First-party descriptive metadata (DOI, PMID, authors, publisher, version, published_at) | `schemas/source_card.schema.yaml` — **already modeled** | **wiring fix, no schema change** |
| First-party bibliographic facts extracted *from the source's own text* | Reusable Assertion Ledger (`source_assertion.schema.yaml`) — `evidence_item_type: bibliographic_metadata` already exists (`:106-155`) | no change |
| **Third-party judgments about a source** (citation counts, ratings, ranks, backlinks, index membership, retraction notices) | **NEW entity: `schemas/source_attribution.schema.yaml`** + a non-authoritative mirror on the card | new entity, additive |

### 2a. First-party metadata is not a schema problem — it is a threading problem

`source.authors`, `source.publisher`, `source.version`, `source.published_at`, and
`source.locator.doi` **all already exist in the schema**. `services/source_cards.py:322-338` hardcodes
them to `[]` / `None` / `"unknown"`. The `ingest_source()` signature (`:178-192`) accepts `content:
str` — bare extracted text — and has **no parameter for structured provider metadata**, even though
`services/search_router/` providers hold it. So the metadata is discarded at a Python call boundary,
not rejected by a schema. This is the cheapest, lowest-risk, highest-value slice in the whole
exploration and it carries **zero migration blast radius**.

### 2b. Why NOT the Reusable Assertion Ledger for third-party judgments

The ledger is tantalisingly close — its subject *is* a source (`source_edition_id` + `passage_id`,
`:27-32`), not a claim, and `bibliographic_metadata` is already an `evidence_item_type`. It fails on
four structural points, in descending severity:

1. **No asserted-by field.** `extraction_provenance` (`:61-80`) records extractor/provider/model/
   prompt_version/observed_at — provenance of *the extraction act*, not of *the assertion's author*.
   A third-party rating's entire governance value is "OpenAlex says this, retrieved then, under those
   terms". The ledger cannot express the asserter. Adding one means amending a schema that is
   `additionalProperties: false` at top level with 12 required fields — a change to the strictest
   schema family in the repo, to serve a subject it wasn't shaped for.
2. **Passage anchoring is mandatory and wrong here.** `source_edition_id`/`passage_id` are non-null
   except for `evidence_item_type: derived_synthesis` (`allOf` at `:490-546`). A citation count is
   not *in* a passage of the source. Recording one would require minting a synthetic passage — a
   provenance lie in the one entity whose job is provenance truth.
3. **`derived_synthesis` is the only passage-free escape hatch, and it is barred.**
   `synthesis.input_refs` is `minItems: 2` (`:404-421`) — a single-provider citation count has one
   input. And `synthesis.attestation.status` is write-capped at `candidate` forever by
   `AssertionMaterializer._enforce_synthesis_attestation_ceiling` (`assertion_materialization.py:704`),
   so a third-party fact would be permanently indistinguishable from an unvalidated RF draft.
4. **Immutability mismatch.** Ledger assertions carry `assertion_text_sha256` and an
   `assertion_version` — the model of a statement that is fixed once extracted. A citation count is a
   *time-varying observation of a mutable external world*. Versioning it in the ledger conflates
   "we re-extracted" with "the world changed".

**Charter conditional CO-2 resolves against the ledger**: the owning-entity choice does *not* hang on
the attestation lifecycle question, because the ledger is disqualified on subject-anchoring
(point 2) before attestation is reached. That conditional can be closed.

### 2c. The new entity: copy the rights-entity-model shape verbatim

The landed rights-entity-model is the validated in-repo precedent for exactly this problem shape — a
separate governance entity layered over the evidence chain, with a denormalized non-authoritative
mirror on the source card. Reuse it structurally rather than inventing:

| Rights precedent | Attribution analogue |
|---|---|
| `rights_record.schema.yaml` (authoritative, `additionalProperties: false`) | `source_attribution.schema.yaml` (authoritative, `additionalProperties: false`) |
| `source_card.rights_summary` mirror, `mirror_is_authoritative: const false` (`source_card.schema.yaml:169-171`) | `source_card.attribution_summary` mirror, **`is_rf_authored: const false`** |
| `rights_summary.rights_record_ids` link-before-assert `allOf` (`:310-372`) | `attribution_summary.attribution_ids` — mirror may not assert a non-null value without a linked record |
| `rights_triage.compute_capture_rights_summary()` (`rights_triage.py:90-113`) | `attribution_triage.compute_attribution_summary()` |
| `rights_validation.check_rights_divergence(as_of=…)` (`rights_validation.py:128`, **never reads the wall clock**) | `check_attribution_divergence(as_of=…)` — same discipline; this is precisely the staleness primitive a citation count needs |
| `rights_triage_failure` typed structural failure (`source_card.schema.yaml:292-309`) | `attribution_triage_failure`, same shape |
| guard rule `no_agent_cleared_rights_value` | guard rule `no_agent_authored_attribution_value` (§6d) |

Minimum authoritative record shape:

```yaml
type: source_attribution
attribution_id: attr_…
subject:
  source_card_id: sc_…          # required — the subject is a SOURCE, not a claim
  source_edition_id: sed_…      # optional; present when the judgment is edition-specific
asserted_by:                    # required — the field the Assertion Ledger cannot express
  asserter_id: openalex | crossref | semantic_scholar | jif | manual_operator
  asserter_type: third_party_service | third_party_publication | operator
  retrieved_at: 2026-08-02T…
  retrieval_method: api | file_import | manual_entry
  retrieval_evidence_ref: <path|null>   # required when asserter_type == third_party_*
  terms_ref: <rights_record_id|null>    # licensing lineage for the CACHED value
  valid_as_of: 2026-08-02T…
assertion_kind: citation_count | inbound_link_count | rating | rank |
                index_membership | retraction_notice | other
value: {numeric: 412}           # or {label: "Q1"} / {boolean: true}
value_scale: <string|null>      # e.g. "unbounded_count", "quartile", "0-100"
is_rf_authored: false           # const false — hard governance invariant
notes: <string>
```

The `const false` on `is_rf_authored` is the direct answer to the charter's governance hazard: it makes
"a rating mistaken for an RF-authored fact" a **schema violation**, not a review-diligence question.

## 3. Propagation Mechanism — where, and why it is deterministic

**Propagate at export/hydration time, in `export_service._resolve_source()`
(`export_service.py:601-661`), fed by `_load_source_cards()` (`:580-598`), invoked from `export_run()`
(`:1333`).** Widen the existing per-citation hydration to carry an `attribution` block and the
first-party metadata fields alongside the `trust`/`usage` it already attaches.

**Why this point is deterministic and file-recomputable:**

- It is a **pure join** — a dict lookup of a loaded source card's front-matter against a claim's
  `sources[]` entry. No model, no network, no clock.
- It **persists no derived state**. Every `export_run` recomputes it from the files. There is nothing
  to drift, nothing to backfill, and the "no-backfill regime" question does not arise for the
  propagated attributes (it still arises for the *records*, which is the risk leg's territory).
- **The DB is derived by construction, for free.** `catalog_service._build_catalog_rows()` consumes
  `export_data` — it does not read source cards independently — and `import_run`/`rebuild`
  (`:1326, :1388`) are **delete-then-insert per run in one transaction** (`:1341-1349`). So every
  attribute added to `_resolve_source` reaches sqlite as a rebuild-from-files projection. No
  incremental-update path exists to make the DB authoritative even accidentally.
- **The read path is already model-free.** `catalog_service.search`/`get_item`/`stats`
  (`:1461, :1772, :1923`) and the Knowledge MCP entry points (`knowledge_access.py:1598, :1626`) are
  plain SQL/FTS over pre-built rows. Widening the row schema does not introduce a model call.

**Why NOT claim-map write time**, despite the `_term_index` precedent:

`_term_index` is a valid precedent for write-time derivation but the **wrong** precedent here, and the
distinction is sharp: `_term_index` is a function of the claim's own **immutable text** (computed at
`claim_mapping.py:276-284` via `term_index.build_term_index()`), so freezing it into the ledger is
sound. A third-party attribution is a function of a **mutable external world**. Freezing a citation
count into `claim_ledger.md` would (a) make the claim ledger a stale mirror requiring its own
divergence validator, (b) silently misrepresent a 2026-09 reader's view of a 2026-08 count, and
(c) require reading source cards inside `build_claim_ledger` (`:213-347`), which today sees **only
extraction cards** (`:244`) and holds **ids and locator only** (`:248-271`) — the pediatric-CDS
threshold scan (`:241`) is the sole existing carve-out. Adding a general source-card dependency there
buys nothing the export join doesn't already give.

**Snapshotting resolves itself.** The authoritative attribution record is a *file inside the run*,
carrying `retrieved_at` + `valid_as_of`. So a committed bundle freezes the observation naturally by
virtue of the record being committed; the export join is pure recomputation over that frozen record.
No separate snapshot mechanism is needed. Note `writeback.build_bundle()` (`writeback.py:183-263`)
carries only counts/pointers and loads no card content — it needs no change (see OQ-3).

## 4. Aggregation Semantics

**Decision: carry-the-set as canonical, plus two named monotone rollups. No averaging, ever.**

**The set is the native shape and requires no choice.** `_resolve_source` resolves *per citation*, so
a claim citing N cards already yields N independently-hydrated entries. Conflicting attributes are
carried side by side with their asserters — the same way `trust.conflicts_with`
(`source_card.schema.yaml:94-103`) already models source-level disagreement rather than resolving it.
Two asserters disagreeing about the same source are **both carried, both attributed, neither
adjudicated**.

On top of the set, exactly two claim-level rollups, both pure functions of it (so no information is
lost and both are recomputable):

1. **`best_source_rank` = max over `trust.source_rank`.** The enum
   `primary|secondary|tertiary|unknown` has a declared total order, so max is well-defined. `max` is
   the right choice because the operative triage question is *"what is the strongest evidence behind
   this claim"*, and max is the only monotone aggregate under which adding a weak corroborating card
   cannot **dilute** a claim already backed by a primary source. (`mean` would punish thorough
   sourcing; `min` alone would render most multi-source claims `unknown` given every card born
   `source_rank: "unknown"` at `source_cards.py:332`.)
2. **`weakest_source_rank` = min over the same enum.** Retained as a *separate* field, not a
   replacement, because it answers the complementary and equally real reviewer query: *"which claims
   lean on tertiary evidence?"* Keeping both makes the pair lossless w.r.t. the ordering.

**Explicitly refused: any numeric aggregation across `assertion_kind`s.** Averaging a citation count
with a quartile rating is meaningless, and — decisively — it would be **RF minting its own
bibliometric judgment**, which the charter puts out of scope. Cross-source numeric attributions
(citation counts, backlink counts) propagate as a **set-union keyed by `(asserter_id,
assertion_kind)`** only. `sum` is likewise refused: summing citation counts across the distinct
sources backing one claim produces a number that describes nothing.

## 5. Constraint Check (AOS invariants)

| Constraint | Verdict | Evidence |
|---|---|---|
| Files canonical | **PASS** | Authoritative `source_attribution` records are run files; the card-level `attribution_summary` is a mirror with `is_rf_authored: const false` + link-before-assert, mirroring `rights_summary` (`source_card.schema.yaml:139-152, :310-372`) |
| DB derived-only | **PASS, structurally** | Catalog is delete-then-insert per run from `export_data` (`catalog_service.py:1341-1349`); no incremental path exists |
| No model on read path | **PASS** | `_resolve_source` is a dict join; catalog/MCP reads are SQL/FTS (`catalog_service.py:1461`, `knowledge_access.py:1598`). Model/network involvement is confined to *acquisition* — and even there a provider API fetch is deterministic |
| Existing bundles keep verifying | **PASS (tech view; risk leg owns the empirical proof)** | `verification.py:1347-1364` maps SCHEMA(2)/GOVERNANCE(3)/UNSUPPORTED(4) off specific existing fields only; no check inspects unrecognized keys, and `source_card.schema.yaml` is `additionalProperties: true` (`:411`). An optional additive block cannot reach any exit code |

## 6. Named Constraints (the "with-constraints" in the verdict)

- **C-1 — Propagate at export, not at claim-map.** §3. Violating this makes the claim ledger a stale
  mirror and re-opens the deal-killer via the back door.
- **C-2 — Third-party *ingestion* is licensing-gated and must be a separate, deferrable phase.** The
  design holds without it (first-party capture + propagation ship standalone). This maps directly onto
  the charter's `conditional` criterion — but note it is a **phasing** constraint, not a verdict
  downgrade, because the propagation architecture is proven independent of what feeds it. The risk
  leg owns the terms assessment.
- **C-3 — The mirror must be fail-closed.** `attribution_summary` sets `additionalProperties: false`
  on its own subtree even though the parent card is permissive — exactly the reasoning already
  recorded at `source_card.schema.yaml:139-152`.
- **C-4 — A new guard rule is mandatory, not optional.** `no_agent_authored_attribution_value`: an
  agent-writable path may not mint a record with `asserter_type: third_party_*` and a null
  `retrieval_evidence_ref`, and may never write `is_rf_authored: true` (schema-enforced as `const
  false`). Direct analogue of `no_agent_cleared_rights_value`.

## 7. Integration Points & Effort

| # | Integration point | Files | Pts |
|---|---|---|---|
| 1 | Thread structured provider metadata into ingest (authors/DOI/publisher/version) | `services/source_cards.py:178-192, :308-363`; `services/search_router/providers/*`, `router.py` | 5 |
| 2 | Derive a real `trust.source_rank` instead of the `"unknown"` hardcode | `services/source_cards.py:332` | 3 |
| 3 | New `schemas/source_attribution.schema.yaml` + `attribution_summary` mirror block on card | `schemas/source_attribution.schema.yaml`, `schemas/source_card.schema.yaml` | 3 |
| 4 | `services/attribution_triage.py` — mirror computation + typed failure | new, patterned on `services/rights_triage.py:90-113` | 5 |
| 5 | `check_attribution_divergence(as_of=…)` + staleness reporting | new, patterned on `services/rights_validation.py:128` | 3 |
| 6 | **Propagation**: widen the hydration join | `services/export_service.py:580-598, :601-661` | 5 |
| 7 | Claim-level rollups (`best_source_rank` / `weakest_source_rank`, attributed-by set-union) | `services/export_service.py` (post-resolve) | 3 |
| 8 | Catalog columns + sqlite schema migration | `services/catalog_service.py:557-572, :850-889`, schema/migration | 5 |
| 9 | Guard rule `no_agent_authored_attribution_value` + governance tests | `.claude/rules/`, rights-guard test suite | 3 |
| 10 | Third-party fetch path (OpenAlex/Crossref/Semantic Scholar) — **licensing-gated, deferrable** | new `services/attribution_fetch/`, `rf attribution` CLI | 8 |
| 11 | Tests + regression over the 7 committed pediatric bundles | `tests/` | 5 |

**Range: 34–48 pts → Tier 3.** Suggested phasing, which matches the charter's `conditional` split:

- **Phase A — capture + propagation (additive, no new entity): items 1, 2, 6, 7, 8, 11 → ~24 pts.**
  Ships standalone value (queryable/filterable evidence) with the smallest blast radius.
- **Phase B — attribution entity + governance: items 3, 4, 5, 9 → ~14 pts.**
- **Phase C — third-party ingestion: item 10 → ~8 pts.** Gated on the risk leg's licensing finding.

## 8. Open Questions

- **OQ-1** — Which search-router providers actually return DOI / citation counts / structured author
  lists today? Item 1's 5 pts assumes the metadata is in hand at the provider boundary; if providers
  must each be extended, item 1 grows. *Not verified in this leg.*
- **OQ-2** — Does the catalog sqlite schema have an established migration path, or is it
  rebuild-only? Item 8's estimate assumes rebuild-from-files makes migration trivial; if there are
  persisted user-facing catalog views, it grows.
- **OQ-3** — Should `writeback.build_bundle()` (`writeback.py:183-263`) emit an attribution count /
  staleness summary in the bundle manifest? §3 argues no snapshot mechanism is *needed*; a manifest
  summary may still be wanted for reviewer legibility.
- **OQ-4** — Item 2 (deriving a real `source_rank`) is the one place a **judgment** is minted. Is
  rank derivable deterministically from `source_type` + rights/access basis, or does it require a
  model call at *capture* time? If the latter, it is still off the read path (acceptable) but must be
  recorded with extraction provenance. Consider splitting item 2 out of Phase A.
- **OQ-5** — Charter conditional CO-2 (owning entity depends on the ledger's attestation lifecycle) is
  **closable**: §2b disqualifies the ledger on subject-anchoring before attestation matters. Confirm
  at the verdict phase.
- **OQ-6** — Should `attribution_summary`'s mirror carry values at all, or only `attribution_ids` +
  counts? A values-carrying mirror needs the divergence validator (item 5); an ids-only mirror is
  cheaper but forces every read through the authoritative records.

## 9. Confidence Rationale — 0.82

**Raises it:** the propagation mechanism substantially already exists and already hydrates `trust`
(`export_service.py:601-661`); the DB is already rebuild-from-files by construction
(`catalog_service.py:1341-1349`); read paths are already SQL/FTS with no model
(`catalog_service.py:1461`); the verify gates provably cannot be tripped by an additive optional block
(`verification.py:1347-1364`); and the rights-entity-model supplies a *landed, validated* shape for
the new entity rather than a novel design — including the wall-clock-free `as_of` staleness
discipline that a cached third-party value specifically needs.

**Discounts it:** OQ-1 (provider metadata availability unverified — the cheapest slice's estimate
rests on it), OQ-2 (catalog migration path unverified), OQ-4 (`source_rank` derivation may not be
deterministic), and third-party licensing entirely unassessed by this leg. None of these threaten the
deal-killer; all of them can move the effort estimate.
