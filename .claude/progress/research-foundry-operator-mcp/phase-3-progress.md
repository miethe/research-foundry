---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 3
status: in_progress
created: '2026-07-28'
updated: '2026-07-30'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs:
- 70c8a6f
- c88e77e
- 9ddb087
- 8fe3a2c
- 415fb5e
- 22a75cc
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: OPM-3.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2
  - CARP-4.G
  estimate: 1 pt
  started: 2026-07-30T20:05Z
  completed: 2026-07-30T21:00Z
  evidence:
  - commit: 70c8a6f
  - test: tests/unit/test_operator_mcp_adapter_base.py
  - test: tests/unit/test_operator_mcp_adapter_run_plan.py
- id: OPM-3.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-3.1
  estimate: 1.5 pts
  started: 2026-07-30T20:05Z
  completed: 2026-07-30T20:50Z
  evidence:
  - commit: 70c8a6f
  - test: tests/unit/test_swarm_service.py
- id: OPM-3.3
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-3.2
  estimate: 1.5 pts
  started: 2026-07-30T21:10Z
  completed: 2026-07-30T21:55Z
  evidence:
  - commit: c88e77e
  - test: tests/unit/test_operator_mcp_adapter_swarm_start.py
- id: OPM-3.4
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.4
  estimate: 1 pt
  started: 2026-07-30T21:10Z
  completed: 2026-07-30T22:30Z
  evidence:
  - commit: 9ddb087
  - test: tests/unit/test_operator_mcp_adapter_job_lifecycle.py
parallelization:
  batch_1:
  - OPM-3.1
  - OPM-3.4
  batch_2:
  - OPM-3.2
  batch_3:
  - OPM-3.3
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 3 Progress — Run Planning and Swarm Adapters

**Dependencies**: P2 and `CARP-4.G`.
**Integration owner**: python-backend-engineer.
**Exit state**: plan/swarm operations and lifecycle tools execute through canonical services and common receipts.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-3.1 | Plan adapter | Direct-service/MCP-adapter fixture outputs equivalent canonical refs | 1 pt |
| OPM-3.2 | Canonical swarm service | CLI parity passes; unknown/disallowed adapters deny; dry-run has zero effects | 1.5 pts |
| OPM-3.3 | Swarm start adapter | Degraded adapters remain typed; cancel/resume does not duplicate candidate artifact | 1.5 pts |
| OPM-3.4 | Job lifecycle adapters | No raw event file reads, unbounded pages, or wrong-workspace detail | 1 pt |

Quality gate (per plan): tool adapters invoke no CLI/Typer/subprocess path; plan/swarm/cancel/resume parity and negative policy fixtures pass; `task-completion-validator` approves exact service extraction and adapters.
