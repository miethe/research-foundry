---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-p5-auth-rbac
feature_slug: public-multiuser-p5-auth-rbac
phase: 3
phase_title: Workspace Isolation Migration + Enforcement
status: completed
created: '2026-07-07'
updated: '2026-07-08'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
phase_doc_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md
commit_refs: []
pr_refs: []
completion_ref: .claude/progress/public-multiuser-p5-auth-rbac/phase-3-completion.md
owners:
- data-layer-expert
- backend-architect
contributors: []
tasks:
- id: WKSP-301
  title: Dry-run workspace-scoping evaluation (no writes)
  status: completed
  assigned_to:
  - data-layer-expert
  model: sonnet
  effort: extended
  dependencies: []
  started: null
  completed: null
  verified_by:
  - GATE-1
  evidence: []
  files_affected:
  - src/research_foundry/api/auth/scope.py
  - src/research_foundry/services/workspace_migration_service.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/paths.py
- id: WKSP-302
  title: "Rollback runbook \u2014 tested reverse-migration path"
  status: completed
  assigned_to:
  - data-layer-expert
  model: sonnet
  effort: extended
  dependencies:
  - WKSP-301
  started: null
  completed: null
  verified_by:
  - GATE-1
  evidence: []
  files_affected:
  - src/research_foundry/services/workspace_migration_service.py
  - src/research_foundry/cli_commands.py
  - tests/unit/test_workspace_migration_service.py
  - docs/dev/architecture/runbooks/workspace-migration-rollback.md
- id: WKSP-303
  title: Legacy-record default-workspace backfill (OQ-B)
  status: completed
  assigned_to:
  - data-layer-expert
  model: sonnet
  effort: extended
  dependencies:
  - WKSP-301
  - WKSP-302
  started: null
  completed: null
  verified_by:
  - GATE-1
  evidence:
  - report: .claude/evidence/phase-3/migration-backfill-report.md
  - manifest: .rf_state/migrations/20260708T145911.176668Z-workspace-backfill.json
  files_affected:
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/workspace_migration_service.py
  - src/research_foundry/cli_commands.py
  - tests/unit/test_workspace_migration_service.py
- id: GATE-1
  title: "Human Gate #1 \u2014 dry-run + backfill review (BLOCKS enforcement)"
  status: completed
  assigned_to:
  - human-operator
  model: n/a
  effort: n/a
  dependencies:
  - WKSP-301
  - WKSP-302
  - WKSP-303
  started: '2026-07-08T14:58:00Z'
  completed: '2026-07-08T14:59:11Z'
  verified_by: []
  evidence:
  - gate: mig_20260708T145811-gate1-approval.json
  - report: .claude/evidence/phase-3/migration-backfill-report.md
  files_affected: []
  notes: Human must create .rf_state/migrations/<id>-gate1-approval.json before WKSP-304
    can run
- id: WKSP-304
  title: "Enforcement flip \u2014 workspace isolation advisory \u2192 blocking"
  status: blocked
  assigned_to:
  - backend-architect
  model: sonnet
  effort: extended
  dependencies:
  - GATE-1
  started: null
  completed: null
  verified_by:
  - WKSP-305
  - WKSP-900
  evidence: []
  files_affected:
  - src/research_foundry/api/auth/scope.py
  - src/research_foundry/config.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/cli_commands.py
  notes: "BLOCKED on Human Gate #1 approval \u2014 do NOT start until gate fires"
- id: WKSP-305
  title: Cross-workspace isolation regression suite (0 leaks)
  status: blocked
  assigned_to:
  - data-layer-expert
  - backend-architect
  model: sonnet
  effort: extended
  dependencies:
  - WKSP-304
  started: null
  completed: null
  verified_by: []
  evidence: []
  files_affected:
  - tests/integration/test_workspace_isolation.py
  notes: BLOCKED on WKSP-304
- id: WKSP-900
  title: 'AC: FE handles enforced workspace scoping (cross-workspace record -> 404,
    not 403)'
  status: blocked
  assigned_to:
  - backend-architect
  model: sonnet
  effort: extended
  dependencies:
  - WKSP-304
  started: null
  completed: null
  verified_by: []
  evidence: []
  files_affected:
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - tests/integration/test_workspace_isolation.py
  notes: "BLOCKED on WKSP-304. Phase 8 consumes this contract \u2014 do NOT renumber\
    \ task ID."
parallelization:
  batch_1:
  - WKSP-301
  batch_2:
  - WKSP-302
  batch_3:
  - WKSP-303
dry_run_report_ref: .claude/evidence/phase-3/migration-dry-run-report.md
gate_1_status: pending
gate_1_approval_artifact: .rf_state/migrations/<migration_run_id>-gate1-approval.json
total_tasks: 7
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 3
progress: 57
---

# Phase 3: Workspace Isolation Migration + Enforcement — Progress

> **Mode D — MUST-STAY — NO ICA/CODEX OFFLOAD**
> This session covers BUILD + DRY-RUN only. Hard stop at Human Gate #1.
> WKSP-304/305/900 are pending Gate #1 human approval and will NOT be executed here.

**Phase Doc**: `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md`
**Worktree**: `worktree-agent-a9dc7f074bc768ff5`

## Batch Execution Log

### Batch 1: WKSP-301 — Dry-run + advisory scoping predicate
- Status: pending
- Agent: data-layer-expert

### Batch 2: WKSP-302 — Rollback runbook + tested reverse-migration
- Status: pending (depends on WKSP-301)
- Agent: data-layer-expert

### Batch 3: WKSP-303 — Real backfill code + idempotency tests (fixtures only)
- Status: pending (depends on WKSP-301, WKSP-302)
- Agent: data-layer-expert

### Dry-run execution against real workspace (READ-ONLY)
- Status: pending
- Output: `.claude/evidence/phase-3/migration-dry-run-report.md`

### HARD STOP — Human Gate #1
- All code + dry-run report committed to worktree
- Enforcement inert until Gate #1 fires
