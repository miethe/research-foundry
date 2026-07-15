---
schema_version: 2
doc_type: phase_plan
title: "Phase 8 (P7): Evaluation and Hardening"
status: completed
created: 2026-07-12
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 8
phase_id: P7
phase_title: Evaluation and Hardening
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P5 and P6 passed task-completion-validator review.
exit_criteria:
  - Gold-set, compatibility, performance, prompt-injection, lifecycle, and isolation gates pass.
  - Runtime smoke covers each P6 target surface.
  - Karen approves the Tier 3 milestone.
related_documents:
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
spike_ref: null
integration_owner: python-backend-engineer
ui_touched: true
target_surfaces:
  - frontend/runs-viewer/src/screens/CatalogScreen.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
seam_tasks: [P7-001, P7-002, P7-004]
owner: python-backend-engineer
contributors: [data-layer-expert, frontend-developer, ui-engineer-enhanced]
priority: high
risk_level: critical
files_affected:
  - tests/fixtures/assertion_ledger/
  - tests/integration/test_assertion_reuse.py
  - tests/integration/test_assertion_impact.py
  - tests/unit/test_rbac_catalog.py
  - tests/unit/test_rbac_route_sweep.py
  - frontend/runs-viewer/e2e/assertion-ledger-review.spec.ts
  - frontend/runs-viewer/src/test/assertion-ledger-review.test.tsx
---

# Phase 8 (P7): Evaluation and Hardening

**Effort:** 8 points
**Dependencies:** P5 and P6 approved.

## Outcome

Integrate implementation paths and enforce release-blocking quality, safety, compatibility, performance, lifecycle, and visual-runtime gates.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P7-001 | Fidelity/compatibility gold set | Implement fixtures and assertions for grounding, atomicity, qualifier preservation, inference separation, exact identity, legacy exports, packet completeness, and propagation receipts. | 3 pts | python-backend-engineer, frontend-developer | sonnet | extended | P5, P6 |
| P7-002 | Adversarial isolation/security | Implement the lexical search, relationships, counts, facets, autocomplete/dedupe, caches, exports, logs, metrics, deletion, parser injection, and route-authorization suite. | 2 pts | python-backend-engineer, data-layer-expert | sonnet | extended | P7-001 fixtures |
| P7-003 | Performance/migration/rollback | Establish corpus-based p95 budgets; test projection rebuild, bounded backfill, interruption, downgrade/disable, and reuse-off recovery. | 2 pts | python-backend-engineer, data-layer-expert | sonnet | adaptive | P7-001 |
| P7-004 | UI runtime smoke evidence | Exercise every P6 target surface at runtime, capture required states, and run the accessibility check for independent review. | 1 pt | frontend-developer, ui-engineer-enhanced | sonnet | extended | P7-001, P7-002, P7-003 |

## Structured acceptance

#### AC P7-SMOKE: Runtime verifies the reviewer contract
- target_surfaces:
  - `frontend/runs-viewer/src/screens/CatalogScreen.tsx`
  - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
  - `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
  - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
  - `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx`
- propagation_contract: The running API serves authorized full, legacy-missing, denied, stale/invalidated, and assertion-only fixtures; the browser navigates each surface and verifies exact labels and actions.
- resilience: Missing optional fields and denied content never crash, leak metadata, display invented values, or hide existing run-local provenance.
- visual_evidence_required: "Desktop >=1440px screenshots for each scenario; keyboard/focus evidence for dialogs and review actions."
- verified_by: [P7-004]

## File ownership and independent review

- `python-backend-engineer` owns P7 integration plus backend gold-set, isolation, performance, migration, and rollback fixtures.
- `data-layer-expert` owns isolation topology and projection/rebuild assertions in P7-002 and P7-003.
- `frontend-developer` owns frontend compatibility fixtures and the P7-004 runtime-smoke harness.
- `ui-engineer-enhanced` owns runtime interaction, accessibility, and screenshot evidence for the named TSX surfaces.
- `task-completion-validator`, `senior-code-reviewer`, and Karen do not write P7 implementation artifacts; they independently review the completed evidence at the gates below.

## Quality and review gates

- [ ] Replay success metrics are reproduced on implementation code, not only the P0 harness.
- [ ] Retraction drill reaches 100% expected dependencies.
- [ ] Unauthorized disclosure is zero for content and derived signals.
- [ ] Source content cannot alter tool authority or system prompts.
- [ ] Legacy and enriched backend/frontend fixtures pass.
- [ ] Migration and rollback rehearsals produce receipts and no evidence loss.
- [ ] `senior-code-reviewer` audits P7-002 and P7-003 evidence and reports findings without modifying implementation artifacts.
- [ ] `task-completion-validator` passes P7.
- [ ] Karen passes the Tier 3 milestone; unresolved critical/high findings block P8 rollout.

## Validation

- Run backend unit/integration/schema/RBAC/export suites.
- Run runs-viewer typecheck, unit, E2E, accessibility, and runtime screenshot smoke.
- Run corpus benchmark, leakage matrix, retraction drill, migration rehearsal, and rollback rehearsal.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
