---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 5
title: Frontend Integration
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
total_tasks: 2
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer
contributors:
- python-backend-engineer
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P5-001
  description: "In client.ts, update loopbackGet() to inject Authorization: Bearer ${VITE_RUNS_LOOPBACK_API_TOKEN} header when env var is set and non-empty. When env var absent/empty, omit header entirely (no empty Authorization header). Follow P4-SEAM contract exactly. Surface 401 errors (do not swallow)."
  status: pending
  assigned_to:
  - ui-engineer
  dependencies:
  - P4-SEAM
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "loopbackGet sends auth header when VITE_RUNS_LOOPBACK_API_TOKEN is set; header omitted when not set; no other client.ts functions changed; 401 surfaces as error"

- id: P5-002
  description: "Manually (or via Playwright smoke script) verify SPA built with VITE_RUNS_FRONTEND_LOOPBACK_API=true and VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:7432/api loads runs from live API. Confirm all 5 endpoint call paths exercised. Update frontend/runs-viewer/README.md with env-var config instructions."
  status: pending
  assigned_to:
  - ui-engineer
  dependencies:
  - P5-001
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "SPA loads run list from live API in loopback mode; all 5 client.ts call paths triggered; env vars documented with loopback and LAN examples"

parallelization:
  batch_1:
  - P5-001
  batch_2:
  - P5-002
  critical_path:
  - P5-001
  - P5-002
  estimated_total_time: "0.5 days"

blockers: []

success_criteria:
- id: SC-P5-1
  description: "SPA loads run list from live API (VITE_RUNS_FRONTEND_LOOPBACK_API=true)"
  status: pending
- id: SC-P5-2
  description: "All 5 client.ts endpoint call paths exercise successfully against live server (runtime smoke — R-P4)"
  status: pending
- id: SC-P5-3
  description: "Auth header present in loopbackGet when VITE_RUNS_LOOPBACK_API_TOKEN set"
  status: pending
- id: SC-P5-4
  description: "Auth header absent when token env var not set"
  status: pending
- id: SC-P5-5
  description: "401 from server surfaces as error (not silently swallowed)"
  status: pending
- id: SC-P5-6
  description: "Env-config docs updated in frontend/runs-viewer/README.md"
  status: pending

files_modified:
- frontend/runs-viewer/src/api/client.ts
- frontend/runs-viewer/README.md
---

# runs-loopback-api - Phase 5: Frontend Integration

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Wire `loopbackGet()` auth-header injection in `client.ts` following the P4-SEAM contract, then run runtime smoke verification against the live API. Scope is `client.ts` only — no component changes. Wave 4; requires P4 complete (auth contract defined in P4-SEAM).

## Implementation Notes

- **Scope**: `frontend/runs-viewer/src/api/client.ts` only. No new SPA routes. No component changes.
- The dual-mode seam (`VITE_RUNS_FRONTEND_LOOPBACK_API`) was built in `runs-frontend-v1` and is already functional for static-data mode.
- Read the P4-SEAM contract comment in `api/middleware/auth.py` before touching `client.ts`.
- integration_owner: python-backend-engineer (defined in P4-SEAM).
- Target surfaces for runtime smoke (R-P3/R-P4, AC-7): all 5 `client.ts` function call paths.
