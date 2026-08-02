---
schema_version: 2
doc_type: report
report_category: feasibility
title: "Source Metadata Capture & Propagation — Feasibility Brief"
status: draft
created: 2026-08-02
updated: 2026-08-02
feature_slug: source-metadata-propagation
verdict: conditional
verdict_confidence: 0.78
exploration_charter_ref: docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md
proposed_adr_ref: docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md
recommended_next_action: "/plan:plan-feature --tier=3 scoped to Phases A+B; defer-until: per-provider license terms verified for bundle redistribution"
related_documents:
  - docs/project_plans/exploration/source-metadata-propagation/spikes/tech-findings.md
  - docs/project_plans/exploration/source-metadata-propagation/spikes/risk-findings.md
  - docs/project_plans/exploration/source-metadata-propagation/spikes/prior-art-findings.md
  - docs/dev/architecture/adr-rights-entity-model.md
---

# Source Metadata Capture & Propagation — Feasibility Brief

---

## 1. Synopsis

RF captures source metadata write-only today: `trust.source_rank` is hardcoded to `unknown`
(`source_cards.py:331-338`), `ingest_source()` has no parameter for structured provider metadata,
and third-party judgments about a source (citation counts, rankings, backlinks) have no owning
entity at all. The operator asks to capture rich first-party metadata at ingest and carry
third-party assertions-about-sources — with their own provenance — up to claims and reports as
queryable attributes, without a model call on the read path or an authoritative derived DB. The
three-leg investigation refutes the charter's stated deal-killer and, more importantly, corrects
its premise: propagation is not new territory, it is an existing deterministic join
(`export_service._resolve_source()`) that already carries a thin attribute set and needs widening,
not replacing.

---

## 2. Investigation Summary

| Leg | Agent | Confidence | Findings | Conclusion |
|-----|-------|-----------|----------|------------|
| tech | spike-writer | 0.82 | [tech-findings.md](spikes/tech-findings.md) | Feasible-with-constraints. Deal-killer refuted: `_resolve_source()` is already the deterministic export-time join; widen it. New `source_attribution` entity needed for third-party judgments; first-party metadata is a wiring fix, not a schema change. |
| risk | data-layer-expert | 0.72 | [risk-findings.md](spikes/risk-findings.md) | New fields are safely additive under `source.*`/`trust.*`; `rf verify` never re-validates the general `source_card` schema (only the closed `pediatric_cds` block); no-backfill creates a result-set bias hazard requiring tri-state coverage; governance guard is a 4-field allowlist blind to new rating fields; Scopus/Web of Science are licensing-excluded. |
| prior-art | search-specialist | 0.75 | [prior-art-findings.md](spikes/prior-art-findings.md) | Build on RF's own vocabulary — adopt shape (PROV-O qualified-relation, Web Annotation non-authoritative mirror, SPDX declared/concluded split) not external ontologies. H5 anchor: rights-entity-model-v1 (`17a2cb0`). Counter-proposed extending `source_assertion.schema.yaml`; overruled per orchestrator adjudication below. |

---

## 3. Cost Estimate

**Rough estimate**: 34–48 story points (Tier 3 equivalent)

**Comparable past feature**: `rights-entity-model-v1` (ADR `docs/dev/architecture/adr-rights-entity-model.md`, merged `17a2cb0`) — closest prior feature by shape: added a denormalized non-authoritative mirror to `source_card`/`source_assertion`, solved the identical files-canonical/no-read-path-model-call constraint via mirror-not-runtime-API, required an additive no-backfill-required schema change, and closed with a fail-closed governance boundary proven by negative tests across 6 phases (P0–P5). All three legs converge on this anchor independently.

**Major cost drivers** (tech leg §7, Phase A+B scope only): thread structured provider metadata
into `ingest_source()` (5 pts, `source_cards.py:178-192,:308-363`); derive a real `trust.source_rank`
instead of the hardcode (3 pts, `source_cards.py:332` — OQ-4: may not be fully deterministic); new
`source_attribution.schema.yaml` + mirror block (3 pts); `attribution_triage.py` (5 pts, patterned on
`rights_triage.py:90-113`); `check_attribution_divergence(as_of=…)` (3 pts, patterned on
`rights_validation.py:128`); widen `_resolve_source()` join (5 pts, `export_service.py:601-661`);
claim-level rollups (3 pts); catalog columns + sqlite schema (5 pts,
`catalog_service.py:557-572,:850-889`); guard rule + governance tests (3 pts); tests/regression over
the 7 pediatric bundles (5 pts).

**Explicitly out of the range above**: Phase C third-party fetch path (item 10, ~8 pts) — licensing-gated, see §5 and §7.

---

## 4. Value Statement

**Primary beneficiaries**: RF operators and report authors who currently cannot filter, sort, or
triage evidence by anything but claim text — `authority_score()` exists but has no call site
(`ranking.py:19-43`), and `rf_deep_reader`'s `credibility_score` output is read by no code.

**Evidence of demand**:
- Direct operator ask captured in the charter hypothesis; the `value` leg was deliberately skipped
  per charter Notes (2026-08-02) — single-operator internal control plane, desirability is not open.
- Internal precedent exists for the target shape (`source_assertion.schema.yaml`'s
  `bibliographic_metadata` evidence type, `_term_index` write-time derivation) but nothing consumes
  it as a queryable/filterable attribute today.

**Counterfactual**: If not built, source quality signals remain permanently write-only and inert;
reports cannot distinguish a primary peer-reviewed source from an unranked one except by reading
prose, and the `trust.source_rank` field — already in the schema — continues silently defaulting
every card to `unknown` forever.

---

## 5. Risks & Blast Radius

| Risk | Category | Severity | Mitigation |
|------|----------|---------|------------|
| New fields land inside `pediatric_cds` (`additionalProperties: false`, hard-gated `SCHEMA(2)`) | technical | H | Hard namespace rule: new fields under `source.*`/`trust.*` only; unit test asserting the writer never emits `pediatric_cds.<new_key>` |
| No-backfill leaves existing cards silently reading "no data" indistinguishable from "verified zero" | technical/design | M-H | Tri-state coverage (`present`/`absent`/`not-yet-assessed`); surface "N of M sources have this attribute" from day one — hard precondition of go |
| Agent-writable path mints a third-party rating that reads as RF-attested fact | governance | H | `no_agent_authored_attribution_value` guard rule (new) + `is_rf_authored: const false` + co-located `source`/`observed_at` on every value |
| Third-party ToS/licensing violation via cached+redistributed data | operational | M | Crossref/OpenAlex/DataCite = CC0 unconditional; Semantic Scholar = with attribution; PubMed/NCBI = per-record only; Scopus/Web of Science = proprietary, excluded v1 |
| Staleness: a cached citation count silently drifts from truth | operational | M | Mandatory `observed_at`/`valid_as_of`; refresh creates a new record, never overwrites; rendered "as of `observed_at`," never a bare number |
| Downstream consumers (catalog, run-export) hand-list keys and silently drop new fields | operational | L-M | Flagged not chased to ground; propagation design must confirm no allowlist bump needed |

---

## 6. Architectural Implications

**Proposed ADR**: `docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md` — new `source_attribution` entity, shaped on rights-entity-model, hydrated at export time.

This fits the existing architecture without structural change — it widens two things already
present (`_resolve_source()`'s join, `source_card.schema.yaml`'s open `additionalProperties: true`
blocks) and adds one new entity following an already-landed pattern. The catalog remains
derived-by-construction (`catalog_service.py:1341-1349` delete-then-insert per run) with no
incremental path, so no read-path model call enters the chain source card → export join → catalog
row → Knowledge MCP read.

### Orchestrator adjudications (resolving leg conflicts)

1. **Owning entity: new `source_attribution.schema.yaml`**, not an extension of
   `source_assertion.schema.yaml` (Reusable Assertion Ledger). The ledger is disqualified on
   subject-anchoring: no asserted-by field (`extraction_provenance` records the extraction act, not
   the assertion's author), its passage anchor cannot honestly host a citation count, its one
   passage-free escape hatch (`derived_synthesis`) requires `input_refs minItems: 2` a
   single-provider count can't satisfy, and its attestation is write-capped at `candidate` forever
   (`assertion_materialization.py:704`). The new entity is shaped on `rights_record.schema.yaml`
   verbatim: authoritative record + non-authoritative `attribution_summary` mirror +
   `is_rf_authored: const false` + `check_attribution_divergence(as_of=…)`.
   *Preserved dissent*: prior-art recommended extending `source_assertion.schema.yaml` with a
   sibling `third_party_assertions[]` block instead of a new top-level entity. Overruled because
   prior-art's own H5 anchor (rights-entity-model, `17a2cb0`) is itself evidence for a *separate*
   entity — both legs agree on shape (qualified-relation/non-authoritative mirror), differing only
   on host schema; the tech leg's four-point structural disqualification (§2b) is dispositive.
2. **Propagation: export-time hydration**, extending `export_service._resolve_source()`
   (`:601-661`), not claim-map write time. `_term_index` is the wrong precedent: it is a pure
   function of immutable claim text; an attribution observes a mutable external world, and freezing
   a citation count into `claim_ledger.md` would make the canonical ledger stale without the claim
   changing. The export join is already deterministic, file-recomputable, per-run, zero persisted
   derived state.
3. **Aggregation: carry-the-set canonical**, plus `max`/`min` rollups on `source_rank`
   (`best_source_rank`/`weakest_source_rank`) — both pure functions of the set, lossless. Numeric
   averaging across `assertion_kind`s is refused (RF minting its own bibliometric judgment, out of
   scope). Cross-source numeric attributions propagate as set-union keyed by
   `(asserter_id, assertion_kind)` only.

### Premise correction, hard constraint, governance gap, licensing, no-backfill risk

The charter's claim that "every attribute is dropped" at the claim boundary is true of the **claim
ledger file**, false of the **export path**, which already joins
`title`/`source_type`/`url`/`trust`/`usage`/`sensitivity`/`quote`/`summary` (`export_service.py:601-661`).
Real gaps: (1) `ingest_source()` has no structured-metadata parameter — first-party fields hardcoded
empty (`source_cards.py:322-338`); (2) no third-party assertion entity exists; (3) nothing queries
the hydrated set as a filterable attribute.

New fields go under `source.*`/`trust.*` (both `additionalProperties: true`) or a new top-level
block — **never inside `pediatric_cds`**, whose both `oneOf` branches are
`additionalProperties: false` and hard-gated `SCHEMA(2)` (`verification.py:66`); any key placed
there breaks all 7 committed pediatric bundles.

`no_agent_cleared_rights_value` is a 4-field name allowlist (`governance.py:35-40`) — structurally
blind to a new rating field. The new guard rule `no_agent_authored_attribution_value` (tech leg C-4)
is a required deliverable of this build, not a follow-up.

Crossref/OpenAlex/DataCite = CC0, cacheable/redistributable unconditionally. Semantic Scholar =
usable with attribution carried through. Scopus/Web of Science/journal-ranking vendors =
proprietary, no license held — excluded from v1, gated behind a named procurement precondition.

No-backfill is a design risk, not a migration chore: a filterable attribute existing only on new
cards yields a corpus that silently appears smaller/lower-quality than reality. Requires tri-state
coverage semantics (`present`/`absent`/`not-yet-assessed`) shipped with the first query surface.

### Why conditional, not go

All three go-gates were met and the deal-killer was refuted, not confirmed — not a stop signal.
Phases A (capture + propagation, ~24 pts) and B (attribution entity + governance, ~14 pts) proceed
immediately as additive, existing-bundle-safe work. Only Phase C (live third-party ingestion, ~8
pts) is gated, on per-provider license terms verified sufficient for bundle redistribution
(Scopus/Web of Science already excluded; Semantic Scholar/PubMed need an attribution mechanism
before ingestion ships).

---

## 7. Verdict

**Verdict**: conditional
**Confidence**: 0.78

**Rationale**: The charter's deal-killer — that propagation cannot avoid a read-path model call or
an authoritative derived DB — is refuted with high confidence (tech leg 0.82): the mechanism already
exists (`_resolve_source()`), the catalog is rebuild-from-files by construction, and the read path is
already model-free SQL/FTS. The risk leg (0.72) confirms the schema change is additive-safe for the
7 committed bundles and surfaces two must-fix items (no-backfill bias, governance-guard gap) as
design requirements, not blockers. The verdict criteria's `conditional` path applies precisely as
the charter anticipated: propagation design is sound but third-party sourcing is blocked on
licensing for the Scopus/Web-of-Science class of provider. 0.78 (below either individual leg)
aggregates across three legs of varying certainty; OQ-1 (provider metadata availability) and OQ-2
(catalog migration path) remain unverified and could move the Phase A estimate.

**Recommended next action**: `/plan:plan-feature --tier=3 scoped to Phases A+B; defer-until:
per-provider license terms verified for bundle redistribution` (Phase C only).

---

## 8. Citations

- Exploration charter: `docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md`
- Tech leg SPIKE: `docs/project_plans/exploration/source-metadata-propagation/spikes/tech-findings.md`
- Risk leg SPIKE: `docs/project_plans/exploration/source-metadata-propagation/spikes/risk-findings.md`
- Prior-art leg SPIKE: `docs/project_plans/exploration/source-metadata-propagation/spikes/prior-art-findings.md`
- `src/research_foundry/services/export_service.py:601-661` — `_resolve_source()`, the existing deterministic hydration join
- `src/research_foundry/services/export_service.py:580-598` — `_load_source_cards()`
- `src/research_foundry/services/source_cards.py:322-338` — hardcoded empty first-party fields
- `src/research_foundry/services/source_cards.py:178-192` — `ingest_source()` signature, no structured-metadata parameter
- `src/research_foundry/schemas/pediatric_cds.schema.json:18-24` — closed `additionalProperties: false` branches
- `src/research_foundry/services/verification.py:66, :557-580` — `pediatric_cds_schema_invalid`, `ExitCode.SCHEMA(2)`
- `schemas/source_card.schema.yaml:407-411` — top-level `additionalProperties: true`
- `src/research_foundry/services/governance.py:35-40, :500-520` — `_RIGHTS_GOVERNED_FIELDS`, `no_agent_cleared_rights_value`
- `src/research_foundry/services/catalog_service.py:1341-1349` — delete-then-insert per run, DB derived by construction
- `docs/dev/architecture/adr-rights-entity-model.md` — H5 anchor, separate-governance-entity precedent (merged `17a2cb0`)
- `schemas/source_assertion.schema.yaml:61-80, :106-155, :404-422` — Reusable Assertion Ledger disqualification points
