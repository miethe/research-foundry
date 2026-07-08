---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-p5-auth-rbac
feature_slug: public-multiuser-p5-auth-rbac
phase: 6
status: completed
created: '2026-07-08'
updated: '2026-07-08'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
phase_doc_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-6-rate-limits-admin-sharing.md
commit_refs: []
pr_refs: []
completion_ref: .claude/progress/public-multiuser-p5-auth-rbac/phase-6-completion.md
owners:
- python-backend-engineer
- ui-engineer
contributors: []
tasks:
- id: P5.6-T1
  title: Rate-limit middleware
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  files_affected:
  - src/research_foundry/api/middleware/rate_limit.py
  - src/research_foundry/config.py
  - src/research_foundry/api/app.py
  - foundry.yaml
  started: '2026-07-08T01:00:00Z'
  completed: '2026-07-08T02:30:00Z'
  verified_by: []
  evidence:
  - test: tests/unit/test_rate_limit.py
- id: P5.6-T4
  title: Sharing/publish-preview gate extension
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  files_affected:
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/export_service.py
  started: '2026-07-08T01:00:00Z'
  completed: '2026-07-08T03:30:00Z'
  verified_by: []
  evidence:
  - test: tests/unit/test_publish_preview_role_independence.py
  - test: tests/integration/test_sharing_flow.py
- id: P5.6-CLI
  title: CLI package conflict fix (cli.py vs cli/ package)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  files_affected:
  - src/research_foundry/cli/__init__.py
  - src/research_foundry/cli.py
  started: '2026-07-08T00:00:00Z'
  completed: '2026-07-08T01:00:00Z'
  verified_by: []
  evidence:
  - test: tests/unit/test_cli_workspace_help.py
  notes: Merge cli.py content into cli/__init__.py so rf console-script entrypoint
    resolves; add smoke test for rf workspace migrate-dry-run --help
- id: P5.6-T2
  title: Admin settings backend API
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5.6-T1
  files_affected:
  - src/research_foundry/api/routers/admin.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/config.py
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: P5.6-T5
  title: RBAC enforcement toggle (explicit knob)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5.6-T1
  files_affected:
  - src/research_foundry/config.py
  - src/research_foundry/api/app.py
  - src/research_foundry/api/middleware/auth.py
  started: null
  completed: null
  verified_by: []
  evidence: []
  notes: 'NEW delta task. Config auth.rbac_enforcement: auto|disabled|enabled. Fail-closed
    on non-loopback. 5 mandatory test scenarios (a-e). Surface rbac_enforcement +
    effective in T2 admin API.'
- id: P5.6-T3
  title: Admin settings UI reconciliation + T5 surface
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - P5.6-T2
  - P5.6-T5
  files_affected:
  - frontend/runs-viewer/src/screens/SettingsScreen.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/components/AdminSettings/WorkspaceMembersPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/RateLimitConfigPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/AuthProviderStatusPanel.tsx
  started: null
  completed: null
  verified_by: []
  evidence: []
  notes: P5.8 already built admin panels to-contract. Reconcile actual T2 API shapes
    against 6 assumptions in phase-8-completion.md. Add rbac_enforcement read-only
    display. Wire AppShell rateLimitState reactive path.
- id: GATE-900
  title: 'AC: FE handles missing rate-limit-state field'
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - P5.6-T1
  - P5.6-T3
  files_affected:
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/test/p5-auth-header.test.ts
  started: null
  completed: null
  verified_by: []
  evidence: []
  notes: "ID LOCKED \u2014 Phase 8 references verbatim. P5.8 partially satisfied;\
    \ this task verifies against live T1 API shapes and adds missing-field unit test."
- id: GATE-901
  title: 'AC: FE handles missing admin-settings fields'
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - P5.6-T2
  - P5.6-T3
  files_affected:
  - frontend/runs-viewer/src/screens/SettingsScreen.tsx
  - frontend/runs-viewer/src/api/client.ts
  started: null
  completed: null
  verified_by: []
  evidence: []
  notes: "ID LOCKED \u2014 Phase 8 references verbatim. P5.8 partially satisfied;\
    \ verify against live T2 shapes, ensure per-subsection degradation tests pass."
parallelization:
  batch_1:
  - P5.6-T1
  - P5.6-T4
  - P5.6-CLI
  batch_2:
  - P5.6-T2
  - P5.6-T5
  batch_3:
  - P5.6-T3
  - GATE-900
  - GATE-901
seam_tasks:
- GATE-900
- GATE-901
reviewer_gates:
- gate: task-completion-validator
  timing: end-of-phase-before-karen
- gate: karen
  timing: end-of-phase-public-exposure-milestone
total_tasks: 8
completed_tasks: 8
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 6 Progress: Rate Limits + Admin Settings + Sharing/Publish-Preview Gates

**Status**: in_progress
**Phase doc**: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-6-rate-limits-admin-sharing.md

## Batch Execution Log

### Batch 1 (parallel): P5.6-T1 + P5.6-T4 + P5.6-CLI
- dispatched to python-backend-engineer (3 parallel Task() invocations)
- no file conflicts between tasks

### Batch 2 (sequential after batch 1): P5.6-T2 + P5.6-T5
- combined into single python-backend-engineer dispatch (both touch config.py / app.py)
- T5 fail-closed security: startup REFUSED if rbac_enforcement=disabled on non-loopback bind

### Batch 3 (sequential after batch 2): P5.6-T3 + GATE-900 + GATE-901
- single ui-engineer dispatch (all frontend files, no conflicts)
- reconciles P5.8's to-contract assumptions against live T2/T1 API shapes
- must check phase-8-completion.md "To-Contract Assumptions" section (6 items)

## Delta Tasks (not in original phase doc)

### P5.6-T5: RBAC enforcement toggle
Explicit `auth.rbac_enforcement: auto|disabled|enabled` config knob.
- `auto` = enforced when provider != none (current implicit behavior made explicit)
- `disabled` = fail-closed: REFUSED if bind_host is non-loopback
- `enabled` = enforced even when provider=none
- 5 mandatory test scenarios (a-e) in task prompt

### P5.6-CLI: CLI package conflict fix
`cli.py` and `cli/` package conflict causes `rf workspace ...` to be un-invokable via installed binary.
Fix: merge `cli.py` content into `cli/__init__.py`, pyproject.toml entry point `research_foundry.cli:app` resolves to package.
Add smoke test: `rf workspace migrate-dry-run --help` exits 0.
