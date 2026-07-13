---
schema_version: 2
doc_type: phase_plan
title: "Phase 6 (P5): Reuse, Refresh, and Impact"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 6
phase_id: P5
phase_title: Reuse Refresh and Impact
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P4 API and projection passed review.
  - Retraction SPIKE verdict permits the named private scope.
exit_criteria:
  - Retrieve-first decisions fail closed and emit typed reasons.
  - Correction/retraction drill enumerates expected dependencies and blocks reuse synchronously.
related_documents:
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
  - docs/project_plans/exploration/contradiction-log-v1/contradiction-log-v1-charter.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-charter.md
integration_owner: backend-architect
ui_touched: false
target_surfaces: []
seam_tasks: [P5-003]
owner: backend-architect
contributors: [python-backend-engineer, data-layer-expert]
priority: high
risk_level: high
files_affected:
  - src/research_foundry/services/assertion_reuse.py
  - src/research_foundry/services/assertion_impact.py
  - src/research_foundry/services/run_launch.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/catalog_service.py
  - tests/integration/test_assertion_reuse.py
  - tests/integration/test_assertion_impact.py
---

# Phase 6 (P5): Reuse, Refresh, and Impact

**Effort:** 8 points
**Dependencies:** P4 approved and propagation SPIKE continuation gate satisfied.

## Outcome

Implement safe reuse eligibility, refresh decisions, monotonic invalidation, and resumable dependency reconciliation. Contradiction remains an evidence relationship; correction/retraction is a lifecycle event.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P5-001 | Reuse and refresh policy | Evaluate edition, extraction contract, rights, sensitivity, freshness, evaluation, invalidation, and workspace state; return allow/deny/refresh plus reason. | 3 pts | backend-architect, python-backend-engineer | sonnet | extended | P4 |
| P5-002 | Impact graph and reconciliation | Traverse assertion dependencies; create operation receipts; block, stale, purge, regenerate, or queue idempotent actions with resume support. | 3 pts | backend-architect, data-layer-expert | sonnet | extended | P5-001 |
| P5-003 | Run/export/catalog seam | Integrate retrieve-first run launch, authoritative reuse blocking, derived projection cleanup, safe telemetry, and mocked writeback receipts. | 2 pts | python-backend-engineer, backend-architect | sonnet | adaptive | P5-001, P5-002 |

## Structured acceptance

#### AC P5-IMPACT: Lifecycle propagation is complete and monotonic
- target_surfaces:
  - `src/research_foundry/services/assertion_reuse.py`
  - `src/research_foundry/services/assertion_impact.py`
  - `src/research_foundry/services/run_launch.py`
  - `src/research_foundry/services/export_service.py`
  - `src/research_foundry/services/catalog_service.py`
- propagation_contract: The lifecycle event changes authoritative eligibility before traversal; one idempotent receipt enumerates actions for assertions, relationships, reports, runs, exports, projections/caches, and mocked downstream writebacks.
- resilience: Unknown state, adapter failure, interruption, or out-of-order event stays denied and resumes from the receipt without duplicate action or historical-provenance loss.
- visual_evidence_required: false
- verified_by: [P5-003, P7-001, P7-003]

## File ownership

- `backend-architect` owns eligibility, state machine, traversal, and receipt semantics.
- `python-backend-engineer` owns run/export/catalog integration and telemetry.
- `data-layer-expert` reviews graph completeness and derived-data cleanup.
- `P5-003` closes the cross-layer seam.

## Quality and review gates

- [ ] Unknown eligibility input fails closed with a typed reason.
- [ ] Invalid assertions stop appearing in eligible-reuse/current-read results before cleanup completes.
- [ ] Fixture manifests show 100% expected-object enumeration.
- [ ] Duplicate, interrupted, resumed, and out-of-order processing converges.
- [ ] Real external writebacks are default-denied; tests use mock receipts.
- [ ] `task-completion-validator` passes P5.

## Validation

- Run reuse-policy matrix and impact integration tests.
- Execute correction, invalid-extraction, retraction, deletion, and passage-drift drills.
- Compare normalized receipts after duplicate and interrupted replay.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
