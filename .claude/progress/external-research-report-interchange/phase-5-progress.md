---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 5
title: Resumable Importer and CLI
status: pending
created: '2026-07-26'
updated: '2026-07-27'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- api-designer
- task-completion-validator
- karen
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-terra
tasks:
- id: ERI-5.1
  description: 'Deterministic action orchestration: build sorted bounded actions from
    the canonical manifest, validate exact action/effect equality, resume at the first
    incomplete action'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-4.4
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-27T00:00:00Z'
  completed: '2026-07-27T14:00:00Z'
  evidence:
  - commit: pending
  - test: tests/integration/test_external_research_import.py
- id: ERI-5.2
  description: 'Chunking and cancellation: stream/hash packet members, process configurable
    source/candidate batches, preserve pending checkpoint on cancellation, enforce
    resource limits'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-5.1
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-27T00:00:00Z'
  completed: '2026-07-27T14:00:00Z'
  evidence:
  - test: tests/integration/test_external_research_import.py::TestBatchingAndResume
  - test: tests/integration/test_external_research_import.py::TestCancellation
- id: ERI-5.3
  description: 'CLI and machine output: add `rf intake external-report` with workspace,
    optional run, dry-run, resume, limit, and JSON/YAML-safe output; no-run is staging-only'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-5.2
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-27T00:00:00Z'
  completed: '2026-07-27T14:00:00Z'
  evidence:
  - test: tests/unit/test_external_research_cli.py
- id: ERI-5.4
  description: 'Provenance/export seam: record the RPC import context and safe receipt
    reference in explicit target-run/export activity; preserve legacy output and expose
    a service seam for future Operator MCP'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-5.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-27T00:00:00Z'
  completed: '2026-07-27T14:00:00Z'
  evidence:
  - test: tests/integration/test_external_research_import.py::TestProvenanceExportSeam
- id: ERI-5.G
  description: 'Exact-tree importer gate: task-completion-validator then Karen APPROVE
    the same exact complete P5 importer, receipt/checkpoint, CLI, provenance/export
    and Operator-MCP seam tree; material changes invalidate both verdicts'
  status: pending
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - ERI-5.4
  estimated_effort: 0 pts
  assigned_model: opus
  model_effort: extended
parallelization:
  batch_1:
  - ERI-5.1
  batch_2:
  - ERI-5.2
  batch_3:
  - ERI-5.3
  - ERI-5.4
  batch_4:
  - ERI-5.G
progress: 80
---

# Phase 5 — Resumable Importer and CLI

Deterministic action orchestration, resumable chunked import, `rf intake external-report`
CLI, and the provenance/export seam. Closes with the `ERI-5.G` exact-tree gate
(task-completion-validator then Karen on the same tree).
