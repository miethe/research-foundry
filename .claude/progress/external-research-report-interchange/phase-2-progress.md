---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 2
title: Staging and Immutable Receipts
status: completed
created: '2026-07-26'
updated: '2026-07-26'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-terra
tasks:
- id: ERI-2.1
  description: 'Safe packet inspection: validate containment, regular files, declared
    members, byte/count limits, schema versions, and streaming member hashes before
    any effect'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-1.4
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-26T00:00:00Z'
  evidence:
  - test: tests/unit/test_external_research_interchange.py
  verified_by:
  - self
- id: ERI-2.2
  description: 'Stable staging manifest: persist immutable packet/action manifest
    and workspace/target-scoped receipt identity using atomic publication; synthesis
    bytes remain governed artifacts'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-2.1
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-26T00:00:00Z'
  evidence:
  - test: tests/unit/test_external_research_interchange.py
  verified_by:
  - self
- id: ERI-2.3
  description: 'Effects and terminal receipt: immutable per-action effects, separate
    atomic checkpoints, immutable terminal receipt whose counts reconcile to exact
    actions'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-2.2
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-26T00:00:00Z'
  evidence:
  - test: tests/unit/test_external_research_interchange.py
  verified_by:
  - self
- id: ERI-2.4
  description: 'Replay, conflict, and dry-run: exact replay returns the same terminal
    receipt; changed/conflicting manifests deny; dry-run reports safe planned actions
    with zero canonical effects'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-2.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-26T00:00:00Z'
  completed: '2026-07-26T00:00:00Z'
  evidence:
  - test: tests/unit/test_external_research_interchange.py
  verified_by:
  - self
parallelization:
  batch_1:
  - ERI-2.1
  batch_2:
  - ERI-2.2
  batch_3:
  - ERI-2.3
  - ERI-2.4
progress: 100
---

# Phase 2 — Staging and Immutable Receipts

Hostile-input-safe packet inspection, atomic staging manifest, immutable effects +
terminal receipt, and replay/conflict/dry-run semantics.

Owning surface: `src/research_foundry/services/external_research_interchange.py`,
`tests/unit/test_external_research_interchange.py`.
