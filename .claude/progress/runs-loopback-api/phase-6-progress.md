---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 6
title: Tests
status: completed
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
total_tasks: 10
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
execution_model: batch-parallel
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TEST-001
  description: TestClient test with fixture run corpus. Verify GET /api/runs response
    is list, each item has required RFRunSummary fields, empty corpus returns [].
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-002
  estimated_effort: 0.2 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Test green; covers empty and non-empty corpus. Risk R3 (endpoint-shape drift)
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-002
  description: 'TestClient test for GET /api/runs/{run_id}: known run_id -> 200 +
    RFRunExport shape; unknown run_id -> 404 + {detail:...} structured JSON body.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-002
  estimated_effort: 0.2 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Test green; 404 body is structured JSON. Risk R3
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-003
  description: TestClient tests for GET /api/runs/{run_id}/claims (non-empty + empty
    array) and GET /api/runs/{run_id}/sources/{id} (found + 404). Verify redacted
    fields in claims response.
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-002
  estimated_effort: 0.2 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Tests green; redacted fields verified in claims response. Risk R3
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-004
  description: 'TestClient test for GET /data/governance.json: response matches GovernanceConfig
    shape; no 500 on minimal config.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-002
  estimated_effort: 0.1 pts
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Test green. Risk R3
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-005
  description: 'TestClient test for GET /health: always returns 200 regardless of
    auth_mode (loopback + token).'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-002
  estimated_effort: 0.1 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Test green for both auth modes.
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-006
  description: Fixture run with sensitivity:work_sensitive claim. Threshold public.
    Verify GET /api/runs/{run_id} has quote and summary as [redacted:sensitivity].
    Verify parity with direct export_service.export_run() call on same fixture.
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-002
  estimated_effort: 0.4 pts
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Parity assertion passes; redacted fields match exactly between API and direct
    export_service call. Risk R1 (sensitivity bypass)
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-007
  description: 'TestClient with auth_mode=token: valid Bearer -> 200; missing header
    -> 401; invalid token -> 401; GET /health -> 200. Verify hmac.compare_digest path
    exercised.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-005
  estimated_effort: 0.4 pts
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: All branches green; GET /health bypasses auth. Risk R2 (network exposure)
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-008
  description: 'CliRunner test: rf serve --bind-host 0.0.0.0 --auth-mode none -> exits
    non-zero; --auth-mode token with token env unset -> exits non-zero; --auth-mode
    token with token set -> would start (stub uvicorn call).'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-007
  estimated_effort: 0.2 pts
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Both failure cases exit non-zero; success case stubs uvicorn.run. Risk R2
    (network exposure)
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-009
  description: 'TestClient with non-empty allowlist: request from unlisted IP -> 403;
    request from listed IP -> 200.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-008
  estimated_effort: 0.1 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Test green.
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
- id: TEST-010
  description: 'Core footprint isolation test: pip install research-foundry (no extra);
    python -c ''import research_foundry; print(ok)'' succeeds; python -c ''import
    fastapi'' fails.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-001
  estimated_effort: 0.1 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Both assertions pass. Risk R5 (dep footprint)
  started: '2026-06-22T16:14:00Z'
  completed: '2026-06-22T16:21:00Z'
  evidence:
  - test: tests/test_serve_api.py
parallelization:
  batch_1:
  - TEST-001
  - TEST-002
  - TEST-003
  - TEST-004
  - TEST-005
  batch_2:
  - TEST-006
  - TEST-007
  - TEST-010
  batch_3:
  - TEST-008
  batch_4:
  - TEST-009
  critical_path:
  - TEST-005
  - TEST-007
  - TEST-008
  - TEST-009
  estimated_total_time: 1 day
blockers: []
success_criteria:
- id: SC-P6-1
  description: All TEST-001 through TEST-010 green under .venv/bin/python -m pytest
  status: pending
- id: SC-P6-2
  description: "Sensitivity-gate parity test (TEST-006) passes \u2014 most critical\
    \ correctness gate"
  status: pending
- id: SC-P6-3
  description: Auth fail-closed bind test (TEST-008) passes
  status: pending
- id: SC-P6-4
  description: Core footprint isolation test (TEST-010) passes
  status: pending
- id: SC-P6-5
  description: hmac.compare_digest usage confirmed (TEST-007)
  status: pending
files_modified:
- tests/test_serve_api.py
- tests/test_serve_auth.py
- tests/test_serve_cli.py
progress: 100
---

# runs-loopback-api - Phase 6: Tests

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Implement all TEST-001 through TEST-010 covering endpoint contracts, sensitivity-gate parity, auth middleware, fail-closed bind, IP allowlist, and core footprint isolation. Wave 5; requires P5 complete.

## Implementation Notes

- Reference test pattern: `tests/test_cli_governance.py` (CliRunner + TestClient).
- Run tests under venv: `./.venv/bin/python -m pytest tests/test_serve_*.py` (per project memory).

**Risk-to-test mapping**:
- R1 (sensitivity bypass) -> TEST-006 (parity test — CRITICAL hard gate)
- R2 (network exposure) -> TEST-008 (fail-closed bind) + TEST-007 (token auth)
- R3 (endpoint-shape drift) -> TEST-001 through TEST-005
- R4 (port collision) -> Validated in P3-002 SERVICES.md check
- R5 (dep footprint) -> TEST-010 (extra isolation)

**Parallelization note**: TEST-001 through TEST-005 can run in a first parallel batch. TEST-006, TEST-007, and TEST-010 in a second batch. TEST-008 requires TEST-007. TEST-009 requires TEST-008.
