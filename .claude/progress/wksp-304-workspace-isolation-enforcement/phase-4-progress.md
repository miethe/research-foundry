---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 4
title: "Enforcing flip + deny paths \u2014 the atomic arming step (Mode D core)"
status: completed
created: '2026-07-08'
updated: '2026-07-09'
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs:
- 3449b1c
pr_refs: []
owners:
- backend-architect
contributors:
- python-backend-engineer
tasks:
- id: TASK-4.1
  description: Flip require_workspace_scope to enforcing + D3 ordering proof
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - TASK-3.6
  started: '2026-07-09T00:00:00Z'
  completed: '2026-07-09T00:10:00Z'
  evidence:
  - test: tests/unit/test_workspace_migration_service.py
  - file: src/research_foundry/api/auth/scope.py
- id: TASK-4.2
  description: Wire 404-on-read + list-omit deny consumption (OQ-1)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - TASK-4.1
  - TASK-3.6
  started: '2026-07-09T20:35:02Z'
  completed: '2026-07-09T20:35:02Z'
  evidence:
  - file: src/research_foundry/services/catalog_service.py
  - file: src/research_foundry/api/auth/scope.py
- id: TASK-4.3
  description: Wire mutation-deny paths (AC-5)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.2
  - TASK-3.6
  started: '2026-07-09T20:56:15Z'
  completed: '2026-07-09T20:56:15Z'
  evidence:
  - file: src/research_foundry/api/routers/reports.py
  - test: tests/unit/test_reports_api.py
  - test: tests/unit/test_share_token_auth_exemption.py
- id: TASK-4.4
  description: (Optional, non-blocking) Deny-event telemetry (OQ-2)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - TASK-4.2
  - TASK-3.6
  started: '2026-07-09T20:35:02Z'
  completed: '2026-07-09T20:35:02Z'
  evidence:
  - note: "Deferred \u2014 building a real deny-event counter/metric would require\
      \ either a new OTel metrics instrument (audit_service.py today only soft-imports\
      \ the OTel *trace* API for mutation spans, no Counter/meter primitive exists)\
      \ or extending audit_service's mutation-oriented ledger schema to a new read-denial\
      \ event type; both are nontrivial new infrastructure beyond a quick fit-in,\
      \ so the existing ERROR-level workspace_scope_enforced_denial structured JSON\
      \ log (already distinct from the advisory WARNING) remains the interim signal\
      \ a log-aggregation/security-monitoring pipeline can alert or count on."
parallelization:
  batch_1:
  - TASK-4.1
  batch_2:
  - TASK-4.2
  batch_3:
  - TASK-4.3
  - TASK-4.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
completion_ref: .claude/progress/wksp-304-workspace-isolation-enforcement/phase-4-completion.md
---

# wksp-304-workspace-isolation-enforcement - Phase 4

**HARD GATE**: no task in this phase may begin until Phase 3's `TASK-3.6` (100%-coverage checklist) has signed off and been `task-completion-validator`-reviewed. Every task row below carries `TASK-3.6` in its `dependencies` for exactly this reason.

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-4.1 | Flip require_workspace_scope to enforcing + D3 ordering proof | pending | backend-architect | TASK-3.6 |
| TASK-4.2 | Wire 404-on-read + list-omit deny consumption | pending | backend-architect | TASK-4.1, TASK-3.6 |
| TASK-4.3 | Wire mutation-deny paths (AC-5) | pending | python-backend-engineer | TASK-4.2, TASK-3.6 |
| TASK-4.4 | (Optional) Deny-event telemetry (OQ-2) | pending | backend-architect | TASK-4.2, TASK-3.6 |

Full task detail: [phase-4-enforcing-flip.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-4-enforcing-flip.md)
