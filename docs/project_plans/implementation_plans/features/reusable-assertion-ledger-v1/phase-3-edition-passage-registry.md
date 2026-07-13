---
schema_version: 2
doc_type: phase_plan
title: "Phase 3 (P2): Edition and Passage Registry"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 3
phase_id: P2
phase_title: Edition and Passage Registry
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P1 schemas and identity contract passed review.
exit_criteria:
  - File-canonical workspace registry persists immutable editions and passages atomically.
  - PDF, OCR, HTML, and text fixtures prove deterministic identity and drift handling.
related_documents:
  - docs/dev/architecture/assertion-ledger-contract.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
integration_owner: python-backend-engineer
ui_touched: false
target_surfaces: []
seam_tasks: [P2-003]
owner: python-backend-engineer
contributors: [data-layer-expert]
priority: high
risk_level: high
files_affected:
  - src/research_foundry/services/assertion_registry.py
  - src/research_foundry/services/source_cards.py
  - tests/fixtures/assertion_ledger/
  - tests/unit/test_assertion_registry.py
---

# Phase 3 (P2): Edition and Passage Registry

**Effort:** 8 points
**Dependencies:** P1 approved.

## Outcome

Implement the private durable source boundary. Atomic writes and workspace-qualified paths preserve file-first portability; derived indexes are not introduced here.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P2-001 | Atomic edition registry | Create idempotent source/edition persistence, raw and normalized hashes, revision lineage, allowed-use/sensitivity metadata, and workspace path isolation. | 3 pts | python-backend-engineer, data-layer-expert | sonnet | adaptive | P1 |
| P2-002 | Passage selectors and drift | Persist exact quote/context plus position, structural, and hash selectors; classify unresolved or changed passages as non-reusable drift. | 3 pts | python-backend-engineer | sonnet | adaptive | P2-001 |
| P2-003 | Import and fixture seam | Integrate source-card/import entry points and multi-format fixtures without changing legacy source-card identity or canonical run files. | 2 pts | python-backend-engineer, data-layer-expert | sonnet | adaptive | P2-001, P2-002 |

## Structured acceptance

#### AC P2-REGISTRY: Registry resolves immutable editions and passages deterministically
- target_surfaces:
  - `src/research_foundry/services/assertion_registry.py`
  - `src/research_foundry/services/source_cards.py`
  - `tests/fixtures/assertion_ledger/`
- propagation_contract: Import computes workspace-qualified source identity, raw edition hash, normalized passage selectors, and revision lineage before an edition or passage is returned.
- resilience: Unsupported format, ambiguous selector, missing rights metadata, or hash mismatch produces a typed non-reusable result and leaves existing immutable records unchanged.
- visual_evidence_required: false
- verified_by: [P2-003]

## File ownership

- `python-backend-engineer` owns the registry service and import seam.
- `data-layer-expert` owns path topology, atomicity, and isolation fixture review.
- `P2-003` is the seam task for overlapping `source_cards.py` behavior.

## Quality and review gates

- [ ] Repeated ingest is idempotent and creates no duplicate edition/passage records.
- [ ] Materially changed source bytes create a new edition with predecessor lineage.
- [ ] Selector fixtures diagnose HTML, PDF, OCR, and text drift without silent reuse.
- [ ] Workspace A paths and identifiers never resolve Workspace B content.
- [ ] Atomic-write interruption leaves either old or complete new state.
- [ ] `task-completion-validator` passes P2.

## Validation

- Run focused registry unit tests and schema checks.
- Run multi-format fixture identity three times in different input orders.
- Inspect the produced file tree for workspace confinement and deterministic names.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
