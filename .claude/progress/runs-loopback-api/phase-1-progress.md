---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 1
title: API Foundation
status: pending
created: '2026-06-22'
updated: '2026-06-22'
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P1-001
  description: "Add fastapi>=0.111, uvicorn[standard]>=0.29 as optional [serve] extra in pyproject.toml. Add import guard in api/__init__.py that raises a clear install error if missing."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "P1 quality gate: pip install research-foundry (no extra) does not import fastapi or uvicorn"

- id: P1-002
  description: "Create src/research_foundry/api/app.py with create_app(config: FoundryConfig) -> FastAPI factory. Wire CORS middleware (default origins: localhost:*, 127.0.0.1:*; configurable). Include GET /health probe returning {status: ok}. Register runs router stub."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-001
  estimated_effort: "0.75 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "P1 quality gate: rf serve boots; GET /health returns 200; CORS preflight returns Access-Control-Allow-Origin"

- id: P1-003
  description: "Add serve command to cli_commands.py (or cli_serve.py). Accepts --port (default 7432), --bind-host (default 127.0.0.1), --auth-mode (none|token, default none), --sensitivity-threshold. Calls uvicorn.run(create_app(config), ...). Wire fail-closed bind check stub."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-002
  estimated_effort: "0.75 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "P1 quality gate: rf serve --help lists all flags; rf serve starts uvicorn on 127.0.0.1:7432; --port overrides port"

parallelization:
  batch_1:
  - P1-001
  batch_2:
  - P1-002
  batch_3:
  - P1-003
  critical_path:
  - P1-001
  - P1-002
  - P1-003
  estimated_total_time: "1 day"

blockers: []

success_criteria:
- id: SC-P1-1
  description: "pip install research-foundry (no extra) does not import fastapi or uvicorn"
  status: pending
- id: SC-P1-2
  description: "rf serve starts and GET /health returns 200"
  status: pending
- id: SC-P1-3
  description: "CORS allows SPA origin in loopback mode"
  status: pending
- id: SC-P1-4
  description: "rf serve --help shows all flags with correct defaults"
  status: pending

files_modified:
- src/research_foundry/api/__init__.py
- src/research_foundry/api/app.py
- src/research_foundry/cli_commands.py
- pyproject.toml
---

# runs-loopback-api - Phase 1: API Foundation

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Create the FastAPI app factory, CORS middleware, `GET /health` probe, `rf serve` Typer CLI command, and `[serve]` optional pyproject.toml extra. This is Wave 1 — the foundation all subsequent phases depend on.

## Implementation Notes

- Mirror `cli_commands.py` `run_export` Typer command structure for `serve`.
- CORS middleware: allow `http://localhost:*` and `http://127.0.0.1:*` by default (configurable).
- Optional import guard: `try: import fastapi; import uvicorn; except ImportError: raise ImportError(...)`.
- P4 implements the real fail-closed bind validation; P1-003 wires only the stub.
- Reference pattern: `docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md` §Phase P1.
