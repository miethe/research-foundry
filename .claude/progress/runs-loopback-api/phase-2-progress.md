---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 2
title: Read Endpoints
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
total_tasks: 6
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
- id: P2-001
  description: "Create src/research_foundry/api/routers/runs.py. Define FastAPI APIRouter with prefix /api. Inject FoundryPaths via dependency. Wire router into create_app()."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-003
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Router registered; GET /api/runs returns 200 with empty list when no runs exist; router visible in /openapi.json"

- id: P2-002
  description: "Implement GET /api/runs calling export_service.list_runs(paths). Returns RFRunSummary[] matching client.ts fetchRunList shape. Sensitivity threshold from config/CLI flag."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-001
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Response is JSON array; items match RFRunSummary fields; sensitivity filter applied; empty array (not 404) when no runs"

- id: P2-003
  description: "Implement GET /api/runs/{run_id} calling export_service.export_run(paths, run_id). Returns RFRunExport. 404 with structured {detail: run not found} if absent. Missing optional fields return null not 500."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-002
  estimated_effort: "0.75 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Response matches RFRunExport shape; missing run -> HTTP 404; sensitivity gate applied; tags/summary missing fields return null"

- id: P2-004
  description: "Implement GET /api/runs/{run_id}/claims returning export_run(paths, run_id)[claims]. Apply sensitivity filter. 404 propagated. Empty array (not null) when run has no claims. missing evidence_strength handled as null."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-003
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Returns claims array; quote/summary redacted per threshold; 404 on unknown run; empty array not null when no claims"

- id: P2-005
  description: "Implement GET /api/runs/{run_id}/sources/{source_card_id}. Scan export_run claims for matching source_card_id. Return RFResolvedSource. 404 if not found or run absent. Missing url/access_date returned as null."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-004
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Returns RFResolvedSource when source exists; HTTP 404 when absent; HTTP 404 propagated when run absent; url/access_date null-safe"

- id: P2-006
  description: "Implement GET /data/governance.json. Inspect prebuild-static-data.mjs output shape and fetchGovernanceConfig() in client.ts. Return FoundryConfig.governance snapshot matching GovernanceConfig TS type exactly."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-001
  estimated_effort: "0.25 pts"
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Response matches GovernanceConfig TS type; fields match prebuild-static-data.mjs output; no 500 on missing optional governance fields"

parallelization:
  batch_1:
  - P2-001
  batch_2:
  - P2-002
  - P2-006
  batch_3:
  - P2-003
  batch_4:
  - P2-004
  batch_5:
  - P2-005
  critical_path:
  - P2-001
  - P2-002
  - P2-003
  - P2-004
  - P2-005
  estimated_total_time: "1.5 days"

blockers: []

success_criteria:
- id: SC-P2-1
  description: "All 5 endpoints return correct JSON shape matching client.ts TypeScript types"
  status: pending
- id: SC-P2-2
  description: "Missing/unknown run_id returns HTTP 404 with structured body on all applicable endpoints"
  status: pending
- id: SC-P2-3
  description: "Sensitivity gate applied (verified by inspection; dedicated test in P6)"
  status: pending
- id: SC-P2-4
  description: "GET /api/runs returns empty array, not 404, when run corpus is empty"
  status: pending
- id: SC-P2-5
  description: "FE missing-field resilience ACs verified for P2-003, P2-004, P2-005"
  status: pending

files_modified:
- src/research_foundry/api/routers/runs.py
---

# runs-loopback-api - Phase 2: Read Endpoints

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Implement all 5 read endpoints in `api/routers/runs.py`, routing all data through `export_service`. This phase runs in Wave 2 parallel with P3. Requires P1 complete.

## Implementation Notes

**Critical invariant (Risk R1)**: ALL data responses MUST route through `export_service.export_run(paths, run_id)` or `export_service.list_runs(paths)`. The API layer must never read raw run artifact files directly.

**Endpoint-to-client.ts mapping**:
| Endpoint | client.ts function | client.ts approx. line |
|----------|--------------------|------------------------|
| `GET /api/runs` | `fetchRunList()` | ~109 |
| `GET /api/runs/{run_id}` | `fetchRunDetail()` | ~126 |
| `GET /api/runs/{run_id}/claims` | `fetchClaimLedger()` | ~175 |
| `GET /api/runs/{run_id}/sources/{source_card_id}` | `fetchSourceCard()` | ~197 |
| `GET /data/governance.json` | `fetchGovernanceConfig()` | ~158 |

P2-006 can be implemented in parallel with P2-002 (both depend only on P2-001 router scaffold).
