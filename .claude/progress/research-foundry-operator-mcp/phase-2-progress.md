---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 2
status: in_progress
created: '2026-07-28'
updated: '2026-07-29'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors:
- data-layer-expert
tasks:
- id: OPM-2.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-1.G
  estimate: 1.5 pts
  started: 2026-07-30T00:20Z
  completed: 2026-07-30T01:15Z
  evidence:
  - test: tests/unit/test_operator_operation_service.py
  - validation: 257 passed exit 0 (orchestrator-independent re-run)
- id: OPM-2.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.1
  estimate: 1.5 pts
  started: 2026-07-30T01:35Z
  completed: 2026-07-30T02:05Z
  evidence:
  - test: tests/unit/test_operator_attempt_adapter.py
  - validation: 319 passed 0 failures exit 0 (orchestrator-independent re-run)
- id: OPM-2.3
  status: completed
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies:
  - OPM-2.2
  estimate: 1 pt
  started: 2026-07-30T02:30Z
  completed: 2026-07-30T03:10Z
  evidence:
  - test: tests/unit/test_operator_receipt_service.py
  - validation: 585 dots 0F 0E 0skip exit 0 (orchestrator-independent)
- id: OPM-2.4
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.3
  estimate: 1 pt
  started: 2026-07-30T03:15Z
  completed: 2026-07-30T03:55Z
  evidence:
  - test: tests/unit/test_operator_cancel_resume_service.py
  - validation: 600 dots 0F 0E 0skip exit 0 (orchestrator-independent)
parallelization:
  batch_1:
  - OPM-2.1
  batch_2:
  - OPM-2.2
  batch_3:
  - OPM-2.3
  batch_4:
  - OPM-2.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 2 Progress — Durable Operation Coordinator

**Dependencies**: `OPM-1.G` approved on the exact current tree.
**Integration owner**: python-backend-engineer.
**Exit state**: stable operation manifests coordinate AgentJob attempts and converge through retry/cancel/resume.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-2.1 | Immutable operation store | Exact manifest replay resolves same operation; changed manifest conflicts | 1.5 pts |
| OPM-2.2 | AgentJob attempt adapter | Legacy AgentJob reads pass; wrong-workspace attempts are indistinguishable from missing | 1.5 pts |
| OPM-2.3 | Effect/checkpoint/terminal receipts | Truncated/extra/duplicate/reordered/mismatched receipt fixtures deny | 1 pt |
| OPM-2.4 | Cancel and resume state machine | H3 ten-scenario matrix converges with uninterrupted effects | 1 pt |

Quality gate (per plan): process-loss, exact-retry, conflict, cancel, resume, policy-change, and reconciliation fixtures pass; operation receipt is primary (audit-service failure is explicit and cannot erase effect truth); `task-completion-validator` and `karen` approve the exact lifecycle candidate.
