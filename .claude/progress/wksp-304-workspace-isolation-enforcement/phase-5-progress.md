---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 5
title: "Regression + enforcement test matrix \u2014 runtime-verification phase"
status: completed
created: '2026-07-08'
updated: '2026-07-09'
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs:
- caec975
- '5418568'
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-5.1
  description: Core 2-workspace x {read, list, mutate} x {allowed, denied} matrix
    (~12 tests)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T01:00Z
  evidence:
  - commit: caec975
  - test: tests/test_workspace_isolation_enforcement.py (2-workspace x read/list/mutate
      x allowed/denied matrix, 24 tests)
  verified_by:
  - phase5-validator-batch1
- id: TASK-5.2
  description: Router-level identity-propagation regression tests (6 routers)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T01:00Z
  evidence:
  - commit: caec975
  - test: tests/test_workspace_isolation_enforcement.py (6-router identity-propagation
      regression, 7 tests)
  verified_by:
  - phase5-validator-batch1
- id: TASK-5.3
  description: Join / tombstone leak edge cases, mutation-tested (~15 tests)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T02:00Z
  evidence:
  - test: tests/test_workspace_isolation_enforcement.py::TestJoinAndTombstoneLeaksClosed
      (mutation-test evidence block, ~line 606-665)
  verified_by:
  - TASK-5.3-mutation-remediation
- id: TASK-5.4
  description: Mutation-deny tests (AC-5)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T01:00Z
  evidence:
  - commit: caec975
  - test: tests/test_workspace_isolation_enforcement.py (mutation-deny spies, AC-5,
      4 tests)
  verified_by:
  - phase5-validator-batch1
- id: TASK-5.5
  description: "Single-operator fallback \u2014 full unmodified suite pass (AC-6)"
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T04:00Z
  evidence:
  - test: tests/test_workspace_isolation_enforcement.py::TestIdentityNoneSingleOperatorFallback
  - finding: builder_service.create_draft has no identity param; workspace_id=None
      on created drafts; under forced enforcement, self-read of own draft denied by
      null-mismatch rule; 3 test_p5_regression_suite.py TestAuditExposureGate failures
      reproduce this
  - test: tests/integration/test_p5_regression_suite.py::TestAuditExposureGate (3->0
      failures under forced enforcement)
  - test: tests/test_workspace_isolation_enforcement.py+test_config_workspace_enforcement.py+test_p5_regression_suite.py+unit/test_builder_service.py
      (167 passed unforced, unchanged before/after fix)
  verified_by:
  - TASK-5.5-selfcheck
  - TASK-5.5-unblock-validator
  note: 'P5.5b unblock: threaded identity into builder_service.create_draft (workspace_id
    stamped from identity.workspace_id when present; byte-identical when identity=None).
    Validator PASS.'
- id: TASK-5.6
  description: Config validation matrix (~5 tests, AC-7)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T00:30Z
  evidence:
  - test: tests/test_config_workspace_enforcement.py
  verified_by:
  - TASK-5.6-selfcheck
- id: TASK-5.7
  description: SQL-injection-safety assertions
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  started: 2026-07-09T00:00Z
  completed: 2026-07-09T01:00Z
  evidence:
  - commit: caec975
  - test: tests/test_workspace_isolation_enforcement.py (SQL-injection-safety / parameterized-bind
      assertions, 6 tests)
  verified_by:
  - phase5-validator-batch1
parallelization:
  batch_1:
  - TASK-5.1
  - TASK-5.2
  - TASK-5.3
  - TASK-5.4
  - TASK-5.5
  - TASK-5.6
  - TASK-5.7
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
completion_ref: .claude/progress/wksp-304-workspace-isolation-enforcement/phase-5-completion.md
---

# wksp-304-workspace-isolation-enforcement - Phase 5

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-5.1 | Core 2-workspace x {read,list,mutate} x {allowed,denied} matrix | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.2 | Router-level identity-propagation regression tests | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.3 | Join / tombstone leak edge cases (mutation-tested) | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.4 | Mutation-deny tests (AC-5) | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.5 | Single-operator fallback full-suite pass (AC-6) | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.6 | Config validation matrix (AC-7) | pending | python-backend-engineer | TASK-4.3 |
| TASK-5.7 | SQL-injection-safety assertions | pending | python-backend-engineer | TASK-4.3 |

**Mandatory gate**: `task-completion-validator` must pass this phase before Phase 6 begins (decisions block §1).

Full task detail: [phase-5-regression-matrix.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-5-regression-matrix.md)
