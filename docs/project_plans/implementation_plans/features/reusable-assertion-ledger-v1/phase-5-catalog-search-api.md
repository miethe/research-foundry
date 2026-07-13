---
schema_version: 2
doc_type: phase_plan
title: "Phase 5 (P4): Catalog, Search, and API"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 5
phase_id: P4
phase_title: Catalog Search and API
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P3 enriched and legacy export fixtures passed review.
exit_criteria:
  - Workspace-scoped lexical discovery and evidence packets pass API/catalog tests.
  - OpenAPI and generated frontend types are synchronized.
related_documents:
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
spike_ref: null
integration_owner: python-backend-engineer
ui_touched: false
target_surfaces: []
seam_tasks: [P4-003]
owner: python-backend-engineer
contributors: [data-layer-expert, api-designer, frontend-developer]
priority: high
risk_level: high
files_affected:
  - src/research_foundry/services/assertion_catalog.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/api/routers/assertions.py
  - src/research_foundry/api/app.py
  - src/research_foundry/api/openapi.json
  - frontend/runs-viewer/src/types/rf/generated.ts
  - tests/unit/test_assertion_catalog.py
  - tests/integration/test_assertions_api.py
---

# Phase 5 (P4): Catalog, Search, and API

**Effort:** 8 points
**Dependencies:** P3 approved.

## Outcome

Build a rebuildable assertion projection, policy-first lexical discovery, bounded pagination, and a versioned evidence-packet API. Vector and graph retrieval are absent from the deployed v1 path.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P4-001 | Scoped projection/search | Build workspace-qualified assertion rows, exact/lexical filters, facets, bounded cursors, rebuild parity, and safe aggregate semantics. | 3 pts | data-layer-expert, python-backend-engineer | sonnet | adaptive | P3 |
| P4-002 | Evidence-packet endpoints | Add detail/search/lineage endpoints returning passage, qualifiers, evaluation/freshness, rights decision, relationships, reuse state, and run/report uses. | 3 pts | python-backend-engineer, api-designer | sonnet | adaptive | P4-001 |
| P4-003 | DTO/OpenAPI/codegen seam [H6] | Serialize policy reason codes and optional fields, refresh OpenAPI, generate TypeScript, and verify legacy/missing-field compatibility. | 2 pts | python-backend-engineer, frontend-developer | sonnet | adaptive | P4-001, P4-002 |

## Structured acceptance

#### AC P4-PACKET: API returns governed packets without derived-signal leakage
- target_surfaces:
  - `src/research_foundry/services/assertion_catalog.py`
  - `src/research_foundry/services/catalog_service.py`
  - `src/research_foundry/api/routers/assertions.py`
  - `src/research_foundry/api/openapi.json`
  - `frontend/runs-viewer/src/types/rf/generated.ts`
- propagation_contract: Authorized workspace and policy context are applied before query execution; packet DTOs and OpenAPI preserve the resulting content, denial reason, pagination, and optional lineage fields.
- resilience: Missing persistent fields preserve legacy catalog behavior; missing policy, rights, or workspace context yields typed denial with zero content, counts, candidates, or membership hints.
- visual_evidence_required: false
- verified_by: [P4-003, P7-001, P7-002]

## File ownership

- `data-layer-expert` owns projection topology and query/isolation behavior.
- `python-backend-engineer` owns router, DTOs, OpenAPI, and app registration.
- `frontend-developer` consumes generated types only after OpenAPI is frozen.
- `P4-003` is the backend/frontend seam and serialization barrier.

## Quality and review gates

- [ ] Projection rebuild yields equivalent records from durable ledger/run inputs.
- [ ] Search and facets apply authorization before ranking or aggregation.
- [ ] Packets never return assertion text without exact passage/edition context and policy decision.
- [ ] Pagination is bounded and deterministic.
- [ ] OpenAPI and generated types have no unexplained drift.
- [ ] `task-completion-validator` passes P4.
- [ ] Karen approves the API/isolation milestone.

## Validation

- Run catalog/API unit and integration suites plus RBAC route sweep.
- Delete and rebuild a test projection, then compare normalized results.
- Generate OpenAPI/types twice in check mode and compare hashes.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
