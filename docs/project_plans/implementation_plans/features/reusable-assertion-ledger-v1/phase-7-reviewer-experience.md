---
schema_version: 2
doc_type: phase_plan
title: "Phase 7 (P6): Reviewer Experience"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 7
phase_id: P6
phase_title: Reviewer Experience
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P4 OpenAPI and generated frontend types are frozen.
exit_criteria:
  - Reviewer can discover an assertion, inspect exact provenance, and understand stale/denied/impact states.
  - Missing optional backend fields produce explicit resilient UI states.
related_documents:
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
integration_owner: ui-engineer-enhanced
ui_touched: true
target_surfaces:
  - frontend/runs-viewer/src/screens/CatalogScreen.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
seam_tasks: [P6-001, P6-004]
owner: ui-engineer-enhanced
contributors: [frontend-developer, ui-designer]
priority: high
risk_level: high
files_affected:
  - frontend/runs-viewer/src/types/rf/generated.ts
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/hooks/useCatalog.ts
  - frontend/runs-viewer/src/screens/CatalogScreen.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
  - frontend/runs-viewer/src/test/assertion-ledger-review.test.tsx
---

# Phase 7 (P6): Reviewer Experience

**Effort:** 7 points
**Dependencies:** P4 approved; may proceed beside P5.

## Outcome

Extend existing catalog, claim-audit, provenance, lineage, and run-detail patterns. No separate reviewer application or image-generation work is introduced.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P6-001 | Client/type seam [H6] | Consume generated packet/search/impact types, add query hooks, and model explicit loading, denied, legacy-missing, stale, invalid, and error states. | 1 pt | frontend-developer, ui-engineer-enhanced | sonnet | adaptive | P4-003 |
| P6-002 | Assertion discovery/detail | Extend CatalogScreen and ProvenanceModal with assertion filters, exact passage/edition, qualifiers, evaluation, rights, freshness, and prior use. | 2 pts | ui-engineer-enhanced | sonnet | adaptive | P6-001 |
| P6-003 | Audit, impact, and optional merge review | Extend claim audit, lineage detail, and run detail with impact summaries and reversible candidate review only when merge flag is enabled. | 2 pts | ui-engineer-enhanced, frontend-developer | sonnet | adaptive | P6-001 |
| P6-004 | Component/resilience seam | Add accessible component tests for full, missing-field, denied, assertion-only, stale, and impact states; hand target surfaces to P7 runtime smoke. | 2 pts | frontend-developer, ui-engineer-enhanced | sonnet | adaptive | P6-002, P6-003 |

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

## File ownership

- `frontend-developer` owns generated types, client, hooks, and test harness.
- `ui-engineer-enhanced` owns the five named TSX surfaces and accessibility behavior.
- `P6-001` and `P6-004` serialize shared client/component contract changes.

## Quality and review gates

- [ ] Component tests cover full, denied, missing-field, stale, and assertion-only responses.
- [ ] Merge controls are absent when `RF_CANONICAL_CLAIMS_ENABLED` is false.
- [ ] Inference labels cannot be mistaken for source assertions.
- [ ] Keyboard navigation, focus return, accessible names, and contrast pass.
- [ ] P7-004 runtime smoke is scheduled for every `target_surfaces` path.
- [ ] `task-completion-validator` passes P6.

## Validation

- Run runs-viewer typecheck and focused component/accessibility tests.
- Generate screenshots only in P7 runtime smoke after P5 impact data is integrated.
- Confirm no UI path sends a query before workspace/auth context resolves.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
