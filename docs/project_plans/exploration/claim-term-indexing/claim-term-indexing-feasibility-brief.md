---
schema_version: 2
doc_type: report
report_category: feasibility
title: "Claim Term Indexing — Feasibility Brief"
status: finalized
created: 2026-07-23
updated: '2026-07-23'
feature_slug: claim-term-indexing
verdict: go
verdict_confidence: 0.77
exploration_charter_ref: 
  docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md
proposed_adr_ref:
recommended_next_action: "/plan:plan-feature --tier=2 --charter=docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md"
related_documents:
- docs/project_plans/design-specs/claim-term-indexing.md
---

# Claim Term Indexing — Feasibility Brief

---

## 1. Synopsis

Claim term indexing proposes attaching a deterministic, write-time-computed vocabulary index — matched terms plus an optional usage-role annotation (finding, threshold, measurement, background) — to RF claims (and later inferences/reports/source cards), so operators, CARP's planner, and runs-viewer analysts can find and browse entities by controlled term rather than free-text substring alone. It surfaced from an operator idea (2026-07-23) motivated by the pediatric-anemia-site evidence-foundry use case (WBC/CBC/ferritin term-centric views) and is directly corroborated by CARP's same-day, in-repo `required_terms` mechanism, which independently hand-rolled a weaker version of this exact capability.

---

## 2. Investigation Summary

| Leg | Agent | Confidence | Findings | Conclusion |
|-----|-------|-----------|----------|------------|
| tech | ica-executor (claude-sonnet-5[1m]) | 0.82 | [tech-findings.md](spikes/tech-findings.md) | Feasible-with-constraints: a pure deterministic function at `claim_mapping.build_claim_ledger` write time (no model, no network) can populate `terms`/`usage_roles`, propagating additively through `claim_ledger.yaml` (open schema) → `export_service.export_run` → `catalog_service` derived tables; strict `additionalProperties: false` families (`canonical_claim`, `inference_record`, `source_assertion`) need an explicit schema-version bump, deferred to v2. |
| priorart | ica-executor (claude-sonnet-5[1m]) | 0.75 | [priorart-findings.md](spikes/priorart-findings.md) | Adapt, don't build: CARP's case-folded `required_terms` substring match (`catalog_retrieval.py:385-419`) is the extraction primitive to reuse; the catalog's derived/rebuildable sqlite3+FTS5 read-model doctrine (`catalog_service.py`) is the storage pattern to replicate; no term/tag field exists anywhere today in claim, ledger, or writeback schemas (confirmed gap, exhaustive grep). |
| risk | ica-executor (claude-sonnet-5[1m]) | 0.78 | [risk-findings.md](spikes/risk-findings.md) | Deal-killer not triggered on code inspection, **and empirically confirmed**: a live before/after `rf verify` run against a real 87-claim pediatric-CDS ledger (`rf_run_20260717_rf_cbc_001_pediatric_cds_establish`) with an injected `_term_index` field produced byte-identical verification output (same exit code, same 17 checks, 0 claims flipped status) — only the non-semantic `generated_at` timestamp differed. Primary residual risks are namespace collision with `pediatric_cds` structured blocks (mitigated by a `_term_index.*` namespace convention, never bare `usage_role`) and the flat-`search_text` sensitivity-redaction leak precedent, which a per-sensitivity-tier term derivation must avoid repeating. |
| value | ica-executor (claude-sonnet-5[1m]) | 0.72 | [value-findings.md](spikes/value-findings.md) | Real, evidenced value: CARP (merged same day, commit `d824290`) independently reinvented per-term matching to work around the absence of a stored term field, and its own PRD names the resulting risk (`catalog-assisted-research-planning-v1.md:349`, missed synonym matches become residual discovery). Value is a precision/consistency play for a small number of high-stakes clinical lookups plus a concrete CARP quality lever, not a broad search-volume win — existing FTS5/BM25 already serves cheap literal-token search. |

---

## 3. Cost Estimate

**Rough estimate**: 8–13 story points (Tier 2 equivalent)

**Comparable past feature**: CARP P1 (Contract and Policy Freeze) + P2 (Governed Catalog Adapter) — 9 pts, landed commit `d824290` (`docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md:246-247`)

**Major cost drivers**:
- Vocabulary loader + deterministic matcher (pure function, unit-testable) — reuses CARP's case-folded substring-match philosophy without CARP's auth/reuse-decision/pagination complexity (~3.5 of CARP's 5 P2 points were auth/reuse-specific, not needed here)
- Schema surface: additive fields on `claim_ledger.yaml` (open schema, cheap) vs. an explicit property + version bump on the strict `canonical_claim`/`inference_record`/`source_assertion` families (deferred to v2 per tech leg OQ-3)
- `catalog_service.py` (1985 lines) touch for a new `catalog_terms` table + `_build_claim_and_inference_rows` wiring — H7 huge-file-touch multiplier applies if edited in place
- Backfill script for existing verified bundles, modeled on `services/rights_backfill.py` (idempotent, additive, dry-run) — mechanical, given the `reindex_all_drafts`-style precedent

---

## 4. Value Statement

**Primary beneficiaries**: RF operators authoring pediatric-CDS runs (precision/consistency of high-stakes clinical lookups), CARP's automated retrieval planner (`catalog_retrieval.py`, quality lever on the covered/residual partition), runs-viewer analysts reviewing bundles, and future topic-driven report authors.

**Evidence of demand**:
- CARP's `_collect_candidates()` (`catalog_retrieval.py:385-449`) hand-rolls an N-substring-scan emulation of "does this assertion carry these terms" at *query time*, per research question, precisely because no stored per-entity term field exists — merged into production the same day this exploration ran (commit `d824290`).
- CARP's own PRD documents the accepted risk of the current approach: "Lexical catalog matching plus explicit constraints is sufficient for a conservative v1 selection surface; missed matches become residual discovery, not false coverage" (`catalog-assisted-research-planning-v1.md:349`) — a dated admission that synonym gaps silently over-trigger external discovery today.
- The `pediatric_cds` evidence-card schema already structures each finding with `population`/`assay_method`/`threshold{value,units_ucum}` fields (`schemas/pediatric_cds.schema.json`) — raw material a deterministic usage-role pass can key off without any new extraction step.

**Counterfactual**: If this is not built, term/topic lookups continue to rely on exact-token FTS5/BM25 substring search (no alias/synonym canonicalization, no usage-role distinction) or manual grep/re-reading of claim-ledger markdown, and CARP's `required_terms` mechanism stays hand-authored per question rather than validated against the vocabulary a claim actually carries — perpetuating the residual-discovery false-positive risk CARP's own PRD already names.

---

## 5. Risks & Blast Radius

| Risk | Category | Severity | Mitigation |
|------|----------|---------|------------|
| Content-addressed `source_assertion` identity drift if term/usage fields leak into the fixed 5-tuple hashing set | technical | H | Keep `terms`/`usage_role` fields strictly outside `SOURCE_ASSERTION_MATERIAL_FIELDS` (`assertion_identity.py:16-21`); add a regression test asserting `source_assertion_fingerprint()` is unchanged by an injected `_term_index` key. |
| Catalog-layer sensitivity granularity mismatch — a flat pre-computed term index bypassing per-`evidence_point` redaction, repeating the existing `search_text` leak precedent (`catalog_service.py:541-563`, `_redact_evidence_points` at `catalog_service.py:1215-1234`) | technical | M-H | Derive the term index per-sensitivity-tier (or from the post-redaction point set at read time), never folded into one flat blob computed once at max-permissive sensitivity. |
| Namespace/semantic collision between a derived `usage_role: threshold` label and real `pediatric_cds` schema-validated threshold blocks (hard-gated, strict exact-passage mode per CLAUDE.md) | operational | M | Namespace all derived fields under `_term_index.*` (never bare `usage_role`) — unambiguous non-authoritative posture, matching the rights-summary "denormalized, non-authoritative" precedent (`adr-rights-entity-model.md`). |
| `canonical_claim`/`inference_record`/`source_assertion` are schema-locked (`additionalProperties: false`); adding term fields there requires an explicit version bump and architect review | technical | M | Scope v1 to `claim_ledger.yaml` + `report_frontmatter.schema.yaml` (both already permissive); defer strict-family extension to a v2 decision with explicit `backend-architect` sign-off. |
| `rf verify` gate flipping `verification_status` on backfill/reindex of existing bundles | operational | L (empirically confirmed not triggered) | Empirical addendum on the risk leg: live before/after `rf verify` against 87 real pediatric-CDS claims with an injected `_term_index` field produced byte-identical output — 0 status flips, identical 17-check table. Recommend a fixture-based CI regression test to lock this in going forward. |
| Vocabulary and usage-role-mechanism reproducibility drift (a vocabulary edit silently changes historical index output; a model/embedding-derived usage role is not reproducible across model updates) | organizational | M | Stamp `vocabulary_version` on every computed index (mirrors CARP's own versioning discipline); use a lexicon/rule-based (not model/embedding-based) usage-role classifier for v1, keeping the entire pipeline off the read path per the charter's deal-killer. |

---

## 6. Architectural Implications

This fits cleanly into RF's existing layered, dual-stack architecture with no new subsystem required. It replicates two patterns already proven in this codebase: (1) CARP's deterministic, case-folded substring-match extraction (`catalog_retrieval.py:385-419`) as the term-matching primitive, applied at write time instead of query time; and (2) the catalog's derived/rebuildable sqlite3+FTS5 read-model doctrine (`catalog_service.py`, `builder_service.py`'s `reindex_all_drafts`) as the storage contract — file-canonical Markdown/YAML remains authoritative, `catalog.db` rows are disposable and always rebuildable from source. The primary architectural decision this exploration surfaces but does not resolve is whether/when to extend term indexing onto the strict, `additionalProperties: false` entity families (`canonical_claim`, `inference_record`, `source_assertion`) — deferred as an open question for the design spec and a candidate future ADR, not resolved here. No proposed ADR is drafted at this stage since the v1 scope (open-schema `claim_ledger` + `report_frontmatter` only) requires no decision that forces an architectural commitment beyond additive-field discipline already established by six prior `run.json` schema bumps (1.0→1.6).

---

## 7. Verdict

**Verdict**: go
**Confidence**: 0.77

**Rationale**:
The charter's go criteria require (a) tech and risk legs report confidence ≥ 0.7, and (b) the deal-killer is not triggered with a deterministic write-time indexing design identified. Both are met: tech landed at 0.82 and risk at 0.78 (the risk leg's confidence was explicitly raised from an initial 0.68 to 0.78 after an empirical addendum — a live before/after `rf verify` run against a real 87-claim pediatric-CDS ledger showed zero status flips from an injected `_term_index` field, closing the leg's one open empirical gap). The tech and priorart legs jointly identify a concrete deterministic write-time design (CARP-style case-folded substring matching at `claim_mapping.build_claim_ledger` time, stored additively in the already-permissive `claim_ledger.yaml` schema, propagated read-only through export → catalog). No code path was found — on inspection or empirically — where term/usage-role data participates in `verify_report`'s checks or the `no_agent_cleared_rights_value` guard's rights-clearance fields, satisfying the charter's deal-killer condition. Value leg confidence (0.72) is tempered but real: same-day, in-repo evidence (CARP's `required_terms` workaround, merged commit `d824290`) demonstrates the need is already manifesting in production code, not speculative. Aggregate confidence (0.77, weighted toward the two charter-gating legs) supports go, with scope deliberately bounded to the open-schema entity layer for v1 and strict-family extension deferred as a named follow-up decision.

**Recommended next action**: `/plan:plan-feature --tier=2 --charter=docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md`

---

## 8. Citations

- Exploration charter: `docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md`
- Tech leg SPIKE: `docs/project_plans/exploration/claim-term-indexing/spikes/tech-findings.md`
- Prior-art leg SPIKE: `docs/project_plans/exploration/claim-term-indexing/spikes/priorart-findings.md`
- Risk leg SPIKE: `docs/project_plans/exploration/claim-term-indexing/spikes/risk-findings.md`
- Value leg SPIKE: `docs/project_plans/exploration/claim-term-indexing/spikes/value-findings.md`
- Design spec (synthesized proposed design): `docs/project_plans/design-specs/claim-term-indexing.md`
- CARP contract freeze: `docs/dev/architecture/carp-contract-freeze.md`
- CARP implementation plan (H5 anchor): `docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md`
- CARP PRD (residual-discovery risk statement): `docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md`
- Rights entity model ADR: `docs/dev/architecture/adr-rights-entity-model.md`
- Run-export schema history: `docs/dev/architecture/rf-run-export-schema.json`
