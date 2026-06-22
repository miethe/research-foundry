---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 3
title: Config & Flag Wiring
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
- id: P3-001
  description: "Extend FoundryConfig.viewer in config.py with: bind_host (default 127.0.0.1), serve_port (default 7432), auth_mode (default none, enum none|token), auth_token_env (default RF_SERVE_TOKEN), allowlist (default []), cors_origins (default [*] in loopback). Validate auth_mode and allowlist."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-002
  estimated_effort: "0.75 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "foundry.yaml viewer:{serve_port:9000} applies override; invalid auth_mode raises ConfigValidationError; all defaults apply when keys absent"

- id: P3-002
  description: "Update rf serve --help to show --port default 7432 and note MeatyWiki conflict. Add comment in config.py near serve_port. Verify 7432 not in agentic_meta_dev/infra/agentic-node/SERVICES.md."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-001
  estimated_effort: "0.25 pts"
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "CLI help shows --port 7432 as default; config comment cites MeatyWiki conflict; SERVICES.md check confirms 7432 is free"

- id: P3-003
  description: "Update frontend/runs-viewer/src/api/client.ts loopback base URL default from http://127.0.0.1:8765/api to http://127.0.0.1:7432/api. Document VITE_RUNS_FRONTEND_LOOPBACK_API, VITE_RUNS_LOOPBACK_API_BASE, VITE_RUNS_LOOPBACK_API_TOKEN in frontend/runs-viewer/README.md."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-001
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "client.ts loopback base URL default is 7432; env vars documented with examples; loopbackGet signature unchanged"

parallelization:
  batch_1:
  - P3-001
  batch_2:
  - P3-002
  - P3-003
  critical_path:
  - P3-001
  - P3-003
  estimated_total_time: "0.5 days"

blockers: []

success_criteria:
- id: SC-P3-1
  description: "All five viewer.* config keys parse correctly with defaults"
  status: pending
- id: SC-P3-2
  description: "Invalid auth_mode value raises a clear validation error"
  status: pending
- id: SC-P3-3
  description: "rf serve CLI help shows --port 7432 default"
  status: pending
- id: SC-P3-4
  description: "client.ts loopback base URL default updated to 7432"
  status: pending
- id: SC-P3-5
  description: "FE env vars documented in frontend/runs-viewer/README.md"
  status: pending

files_modified:
- src/research_foundry/config.py
- frontend/runs-viewer/src/api/client.ts
---

# runs-loopback-api - Phase 3: Config & Flag Wiring

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Extend `FoundryConfig.viewer` with all `viewer.*` config keys, deconflict port 7432 from MeatyWiki, and update `client.ts` loopback base URL. This phase runs in Wave 2 parallel with P2. Requires P1 complete.

## Implementation Notes

- OQ-2 resolved: Default port is `7432` (deconflicts from MeatyWiki's `8765`).
- OQ-4 resolved: Token lives in env var named by `viewer.auth_token_env` (default: `RF_SERVE_TOKEN`). Token MUST NOT be inline in `foundry.yaml`.
- OQ-5 resolved: `GET /data/governance.json` reads from `FoundryConfig.governance` block (P2-006).
- Do NOT change the dict-access style in `config.py` — extend using existing pattern.
- P3-002 and P3-003 can run in parallel after P3-001 completes.
- P3-003 also touches `client.ts` but only to update the default URL string — scope is minimal.
