---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 3
title: "Query-layer scoping (3 services) \u2014 largest, single-owner phase"
status: completed
created: '2026-07-08'
updated: '2026-07-09'
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs:
- d179fd4
pr_refs: []
owners:
- data-layer-expert
contributors:
- backend-architect
tasks:
- id: TASK-3.0
  description: 'Pre-work exploration: caller-set + backend-parameter-style confirmation'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-1.1
  - TASK-1.2
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  started: 2026-07-09T02:00Z
  completed: 2026-07-09T02:15Z
  evidence:
  - note: caller-set-reconfirmed-3-callers;param-style=sqlite-? -only-no-postgres
  verified_by:
  - phase-owner-batch1
- id: TASK-3.1
  description: Scope catalog_service.py (~10 query points)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-3.0
  started: 2026-07-09T02:20Z
  completed: 2026-07-09T03:30Z
  evidence:
  - test: tests/unit/test_catalog_service.py
  - note: real methods scoped=search,get_item,get_draft_index,list_draft_index (plan
      names list_items/count_items/get_related_items do not exist as separate methods)
  verified_by:
  - phase-owner-batch2
- id: TASK-3.2
  description: Scope builder_service.py (~4 query points)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-3.0
  started: 2026-07-09T02:20Z
  completed: 2026-07-09T03:30Z
  evidence:
  - test: tests/unit/test_builder_service.py
  - note: real methods scoped=load_draft,list_drafts,export_markdown; find_drafts
      does not exist, skipped
  verified_by:
  - phase-owner-batch2
- id: TASK-3.3
  description: Scope agent_job_service.py (~2 query points)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-3.0
  started: 2026-07-09T02:20Z
  completed: 2026-07-09T03:30Z
  evidence:
  - test: tests/unit/test_agent_job_service.py
  - note: real method scoped=load_job; list_jobs does not exist, skipped
  verified_by:
  - phase-owner-batch2
- id: TASK-3.4
  description: Close JOIN + tombstone leaks (AC-4)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-3.1
  - TASK-3.2
  started: 2026-07-09T04:00Z
  completed: 2026-07-09T04:45Z
  evidence:
  - test: tests/unit/test_catalog_service.py::test_get_draft_index_closes_catalog_links_join_leak
  - note: audit=catalog_service(get_item outgoing/incoming/citing_drafts already closed,
      get_draft_index links leak found+fixed);builder_service+agent_job_service=file-backed,no-SQL,no-JOIN-surface
  verified_by:
  - phase-owner-batch3
- id: TASK-3.5
  description: Gate-helper contract review
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  started: 2026-07-09T03:30Z
  completed: 2026-07-09T03:45Z
  evidence:
  - review: CONCERNS-noted;helper-shape-stable-for-P4-no-rewrite-needed
  - note: audit-coverage-gap-found-require_workspace_scope-wired-2-of-6-deny-paths;flag-for-P4-entry-checklist
  verified_by:
  - phase-owner-batch3
- id: TASK-3.6
  description: 'P3 exit-gate: 100%-coverage checklist (hard gate for Phase 4 entry)'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  - TASK-3.5
  started: 2026-07-09T05:20Z
  completed: 2026-07-09T06:00Z
  evidence:
  - doc: .claude/worknotes/wksp-304-workspace-isolation-enforcement/phase-3-exit-checklist.md
  - test: pytest tests/ -q -> 1673 passed, 5 pre-existing-unrelated failures in test_serve_api.py
      (confirmed via git stash against pre-change HEAD), 1 skipped, 1 xfailed
  - note: 8/8 real in-scope methods checked off 100%; 5 plan-assumed method names
      (list_items/count_items/get_related_items/find_drafts/list_jobs) documented
      as intentional exclusions (do not exist in codebase)
  verified_by:
  - phase-owner-batch4
parallelization:
  batch_1:
  - TASK-3.0
  batch_2:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  batch_3:
  - TASK-3.4
  - TASK-3.5
  batch_4:
  - TASK-3.6
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
completion_ref: .claude/progress/wksp-304-workspace-isolation-enforcement/phase-3-completion.md
---

# wksp-304-workspace-isolation-enforcement - Phase 3

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-3.0 | Pre-work exploration: caller-set + param-style confirmation | pending | data-layer-expert | P1+P2 tasks |
| TASK-3.1 | Scope catalog_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.2 | Scope builder_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.3 | Scope agent_job_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.4 | Close JOIN + tombstone leaks (AC-4) | pending | data-layer-expert | TASK-3.1, TASK-3.2 |
| TASK-3.5 | Gate-helper contract review | pending | backend-architect | TASK-3.1, TASK-3.2, TASK-3.3 |
| TASK-3.6 | **P3 exit-gate — hard gate for Phase 4 entry** | pending | data-layer-expert | TASK-3.1..3.5 |

**Non-negotiable ordering invariant**: TASK-3.6's sign-off (task-completion-validator reviewed) is the hard entry-gate for every Phase 4 task — see phase-4-progress.md.

Full task detail: [phase-3-query-layer-scoping.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-3-query-layer-scoping.md)
