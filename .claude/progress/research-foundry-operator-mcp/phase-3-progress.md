---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 3
status: pending
created: '2026-07-28'
updated: '2026-07-28'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: OPM-3.1
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2
  - CARP-4.G
  estimate: "1 pt"
- id: OPM-3.2
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-3.1
  estimate: "1.5 pts"
- id: OPM-3.3
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-3.2
  estimate: "1.5 pts"
- id: OPM-3.4
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-2.4
  estimate: "1 pt"
parallelization:
  batch_1:
  - OPM-3.1
  - OPM-3.4
  batch_2:
  - OPM-3.2
  batch_3:
  - OPM-3.3
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
progress: 0
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
