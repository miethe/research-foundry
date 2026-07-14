---
schema_version: 2
doc_type: phase_plan
title: "Phase 7 (P6): Reviewer Experience"
status: completed
created: 2026-07-12
updated: 2026-07-14
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 7
phase_id: P6
phase_title: Reviewer Experience
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P4 OpenAPI and generated frontend types are frozen.
  - P5 persisted impact receipts and workspace-scoped reconciliation reads are approved for API exposure.
exit_criteria:
  - Reviewer can discover an assertion, inspect exact provenance, and understand stale/denied/impact states.
  - Missing optional backend fields produce explicit resilient UI states.
related_documents:
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-reviewer-experience-v1.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
integration_owner: ui-engineer-enhanced
ui_touched: true
target_surfaces:
  - frontend/runs-viewer/src/screens/CatalogScreen.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
seam_tasks: [P6-000, P6-001, P6-004]
owner: ui-engineer-enhanced
contributors: [python-backend-engineer, frontend-developer, ui-designer]
priority: high
risk_level: high
files_affected:
  - src/research_foundry/services/assertion_impact.py
  - src/research_foundry/api/routers/assertions.py
  - src/research_foundry/api/openapi.json
  - frontend/runs-viewer/src/types/rf/assertions_api.generated.ts
  - frontend/runs-viewer/src/types/rf/generated.ts
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/hooks/useCatalog.ts
  - frontend/runs-viewer/src/screens/CatalogScreen.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
  - frontend/runs-viewer/src/test/assertion-ledger-review.test.tsx
  - tests/api/test_assertions_api.py
planning_maturity: shipped
---

# Phase 7 (P6): Reviewer Experience

**Effort:** 8 points
**Dependencies:** P4 approved; P6-000 begins only after the P5 impact receipt contract is approved, and its frozen generated output gates P6-001/P6-003.

## Outcome

Extend existing catalog, claim-audit, provenance, lineage, and run-detail patterns using the [reviewer-experience design spec](../../../design-specs/reusable-assertion-ledger-reviewer-experience-v1.md). No separate reviewer application is introduced. Conceptual mockups guide hierarchy and state design, but do not satisfy runtime visual evidence.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P6-000 | Impact read seam [H6] | Add a workspace-authorized assertion-impact summary read route/DTO over persisted P5 receipts, refresh OpenAPI and generated TypeScript, and prove denial returns zero action/count/object hints. No mutation route is introduced. | 1 pt | python-backend-engineer, frontend-developer | sonnet | adaptive | P5-002, P5-003 |
| P6-001 | Client/type seam [H6] | Consume generated packet/search/impact types, add query hooks, and model explicit loading, denied, legacy-missing, stale, invalid, and error states. | 1 pt | frontend-developer, ui-engineer-enhanced | sonnet | adaptive | P4-003, P6-000 |
| P6-002 | Assertion discovery/detail | Extend CatalogScreen and ProvenanceModal with assertion filters, exact passage/edition, qualifiers, evaluation, rights, freshness, and prior use. | 2 pts | ui-engineer-enhanced | sonnet | adaptive | P6-001 |
| P6-003 | Audit, impact, and optional merge review | Extend claim audit, lineage detail, and run detail with impact summaries and reversible candidate review only when merge flag is enabled. | 2 pts | ui-engineer-enhanced, frontend-developer | sonnet | adaptive | P6-000, P6-001 |
| P6-004 | Component/resilience seam | Add accessible component tests for full, missing-field, denied, assertion-only, stale, and impact states; hand target surfaces to logical P7 task P7-004 in physical Phase 8 runtime smoke. | 2 pts | frontend-developer, ui-engineer-enhanced | sonnet | adaptive | P6-002, P6-003 |

## Structured acceptance

#### AC P6-REVIEW: Reviewer sees provenance and impact without semantic laundering
- target_surfaces:
  - `frontend/runs-viewer/src/screens/CatalogScreen.tsx`
  - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
  - `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
  - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
  - `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx`
- propagation_contract: Generated API fields flow through the assertion hooks into discovery, exact provenance, report-use, lifecycle-impact, and optional merge-review views; inference and source assertion labels remain distinct.
- resilience: If persistent IDs, qualifiers, rights, freshness, impact, or canonical-claim fields are absent/null, each surface renders a labeled unavailable/legacy/assertion-only state and preserves existing run-local provenance.
- visual_evidence_required: "Desktop >=1440px screenshots for full packet, legacy-missing fields, denied packet, stale impact, and assertion-only mode."
- verified_by: [P6-004, P7-004]

#### AC P6-IMPACT-READ: Impact UI consumes one governed generated contract
- target_surfaces:
  - `src/research_foundry/services/assertion_impact.py`
  - `src/research_foundry/api/routers/assertions.py`
  - `src/research_foundry/api/openapi.json`
  - `frontend/runs-viewer/src/types/rf/assertions_api.generated.ts`
- propagation_contract: P5 persisted receipt state is read through a workspace-authorized service/route; the generated DTO preserves lifecycle, authoritative reuse block, safe reason, operation status, affected actions/counts, and authorized replacement-edition target without exposing file paths or adding mutation.
- resilience: Missing, denied, interrupted, malformed, or cross-workspace receipt state returns a typed unavailable/denied result with zero action, count, object, or membership hints; the frontend never reads ledger files or reconstructs impact from packet relationships.
- visual_evidence_required: "Logical P7 task P7-004 in physical Phase 8 captures stale-impact runtime evidence only after the P6-000 OpenAPI/codegen output is frozen."
- verified_by: [P6-000, P6-004, P7-004]

## File ownership

- `python-backend-engineer` owns the P6-000 service read, API route, OpenAPI contract, and API denial tests.
- `frontend-developer` owns generated types, client, hooks, and test harness; generation follows the P6-000 OpenAPI freeze.
- `ui-engineer-enhanced` owns the five named TSX surfaces and accessibility behavior.
- `P6-000`, `P6-001`, and `P6-004` serialize the impact contract, client plumbing, and shared component evidence.

## Quality and review gates

- [ ] Component tests cover full, denied, missing-field, stale, and assertion-only responses.
- [ ] P6-000 impact read denial exposes zero actions, counts, object IDs, replacement targets, or membership hints.
- [ ] Stale-impact UI and evidence use only the frozen P6-000 generated DTO; no frontend file read or inferred dependency traversal exists.
- [ ] Merge controls are absent when `RF_CANONICAL_CLAIMS_ENABLED` is false.
- [ ] Inference labels cannot be mistaken for source assertions.
- [ ] Keyboard navigation, focus return, accessible names, and contrast pass.
- [ ] Logical P7 task P7-004 in physical Phase 8 schedules runtime smoke for every `target_surfaces` path.
- [ ] `task-completion-validator` passes P6.

## Validation

- Run runs-viewer typecheck and focused component/accessibility tests.
- Capture runtime screenshots only in logical P7 task P7-004 (physical Phase 8) after the P6-000 impact read contract is frozen; conceptual mockups in the design spec are planning inputs and cannot satisfy P6-004 or P7-004.
- Confirm no UI path sends a query before workspace/auth context resolves.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
