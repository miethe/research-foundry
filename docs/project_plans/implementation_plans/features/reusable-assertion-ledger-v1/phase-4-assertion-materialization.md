---
schema_version: 2
doc_type: phase_plan
title: "Phase 4 (P3): Assertion Materialization"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 4
phase_id: P3
phase_title: Assertion Materialization
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P2 registry passed review.
  - Citation/segmentation contracts needed by extraction are versioned.
exit_criteria:
  - Passage-bound assertions and evaluations persist with exact dedupe and extraction provenance.
  - Historical runs can reference durable IDs additively without changing local IDs.
related_documents:
  - docs/project_plans/exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md
  - docs/project_plans/exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
integration_owner: python-backend-engineer
ui_touched: false
target_surfaces: []
seam_tasks: [P3-003]
owner: python-backend-engineer
contributors: [backend-architect]
priority: high
risk_level: high
files_affected:
  - src/research_foundry/services/assertion_materialization.py
  - src/research_foundry/services/claim_mapping.py
  - src/research_foundry/services/export_service.py
  - schemas/claim_ledger.schema.yaml
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - tests/test_pipeline_ingest_extract_claims.py
  - tests/integration/test_export_round_trip.py
---

# Phase 4 (P3): Assertion Materialization

**Effort:** 8 points
**Dependencies:** P2 approved.

## Outcome

Create durable source assertions as observations of an exact passage, record extraction/evaluation provenance, and add optional persistent lineage to run artifacts. Exact fingerprint dedupe never implies semantic equivalence.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P3-001 | Assertion/evaluation materializer | Persist atomic assertion text, qualifiers, extraction contract, reviewer/evaluation state, and audit event against exact passage versions. | 3 pts | python-backend-engineer, backend-architect | sonnet | adaptive | P2 |
| P3-002 | Exact dedupe and bounded backfill | Implement deterministic exact matching, abstention on ambiguity, and idempotent replay/backfill over the P0 corpus. | 3 pts | python-backend-engineer | sonnet | adaptive | P3-001 |
| P3-003 | Run/export lineage seam [H6] | Add optional edition/assertion references to claim ledgers and exports; preserve run-local IDs, anchors, sources, and inference semantics. | 2 pts | python-backend-engineer, backend-architect | sonnet | adaptive | P3-001, P3-002 |

## Structured acceptance

#### AC P3-LINEAGE: Persistent references remain additive
- target_surfaces:
  - `src/research_foundry/services/claim_mapping.py`
  - `schemas/claim_ledger.schema.yaml`
  - `src/research_foundry/services/export_service.py`
  - `frontend/runs-viewer/src/types/rf/run-export.ts`
- propagation_contract: Materialization emits optional persistent edition/assertion references; claim mapping stores them without replacing local IDs; export preserves both identity domains.
- resilience: When ledger records or new fields are absent, claim mapping and export retain legacy output semantics; ambiguous identity records a typed abstention rather than a guessed link.
- visual_evidence_required: false
- verified_by: [P3-003, P7-001]

## File ownership

- `python-backend-engineer` owns the materializer, claim-mapping seam, and backfill.
- `backend-architect` reviews inference separation, audit event shape, and export compatibility.
- `P3-003` is the serialization barrier before catalog/API work.

## Quality and review gates

- [ ] Assertion packets retain exact passage, qualifiers, extraction contract, and evaluation provenance.
- [ ] Exact duplicates reuse identity; semantic similarity alone does not.
- [ ] Backfill is bounded, resumable, and does not edit historical run evidence.
- [ ] Legacy and enriched export fixtures both pass.
- [ ] Assertion-only mode requires no canonical-claim records.
- [ ] `task-completion-validator` passes P3.

## Validation

- Run ingest/extract/claim pipeline and export round-trip tests.
- Replay the bounded corpus twice and compare persistent IDs and audit events.
- Diff legacy fixture output except for explicitly optional versioned fields.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
