---
schema_version: 2
doc_type: phase_plan
title: "WKSP-304 Phase 5: Regression + Enforcement Test Matrix"
status: draft
created: 2026-07-08
phase: "P5"
phase_title: "Runtime-verification phase — every AC and every target_surfaces entry gets a test"
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
feature_slug: wksp-304-workspace-isolation-enforcement
entry_criteria: ["Phase 4 complete and task-completion-validator-passed (fail-closed invariants confirmed)"]
exit_criteria:
  - "Full ~40-50 test matrix green"
  - "Leak tests fail when a predicate is deliberately removed (mutation-tested)"
  - "MANDATORY task-completion-validator gate before Phase 6 — explicit per decisions block §1"
---

# Phase 5: Regression + Enforcement Test Matrix

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 4](./phase-4-enforcing-flip.md)

**Duration**: ~2 days
**Dependencies**: Phase 4 complete and validator-passed
**Assigned Subagent(s)**: `python-backend-engineer` (solo)

This is the plan's R-P4-equivalent runtime-verification phase (this feature is backend-only, so there is no `*.tsx` "runtime smoke" per se — this test matrix plays that role for every AC's `target_surfaces`). Every `target_surfaces` entry from AC-1 through AC-7 must have at least one test in this phase's matrix that exercises it directly.

**Critical credibility requirement**: leak-coverage tests (TASK-5.3) must be **mutation-tested** — i.e., authored so that deliberately removing a predicate from the implementation causes the test to fail. A leak test that would pass even with the leak present is not a real test.

---

## Task Table

| Task ID | Task Name | Description | Verifies AC | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|--------------|----------|-------------|-------|--------|---------------|
| TASK-5.1 | Core 2-workspace x {read, list, mutate} x {allowed, denied} matrix (~12 tests) | For each of the ~20-25 methods enumerated in AC-2's target_surfaces, exercise both a same-workspace (allowed) and cross-workspace (denied) call for each of read/list/mutate where applicable, against 2 distinct workspaces. Confirms both AC-2 (scoping) and AC-3 (deny path) end-to-end. | AC-2, AC-3 | 0.6 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.2 | Router-level identity-propagation regression tests (~AC-1 target_surfaces, 6 routers) | For each of the 6 routers in AC-1's target_surfaces, a test confirming the router forwards `request.state.identity` through to the service call correctly under a live (or lightly mocked) request — the runtime counterpart to Phase 2's TASK-2.4 seam-verification code inspection. | AC-1 | 0.3 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.3 | Join / tombstone leak edge cases, mutation-tested (~15 tests) | For every JOIN/tombstone path closed in Phase 3 (TASK-3.4), author a test that fails if the joined-side or delete-state predicate is removed. Deliberately verify this by temporarily reverting one predicate locally and confirming the corresponding test fails, then restoring it — document this mutation-test pass in the task's completion note. | AC-4 | 0.5 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.4 | Mutation-deny tests (AC-5) | Zero-UPDATE/DELETE-issued spy tests for cross-workspace mutation targets across `catalog.py`, `agent_jobs.py`, `reports.py` mutation endpoints. | AC-5 | 0.2 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.5 | Single-operator fallback — full unmodified suite pass (~10 new tests + full existing suite) | Run the complete pre-existing `test_workspace_migration_service.py` and `test_p5_regression_suite.py` unmodified with `workspace_isolation_enforcement=enabled` set globally in the test environment — the "break it if you dare" gate. Add ~10 new targeted `identity=None` tests covering CLI/direct-service call patterns across the 3 services. | AC-6 | 0.3 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.6 | Config validation matrix (~5 tests) | Full integration-level matrix: `auto\|enabled\|disabled` x loopback/non-loopback x `provider=none`/other, asserting the `ValueError`/resolution behavior at app-create time (extends TASK-1.2's unit-level coverage to the app-integration level). | AC-7 | 0.1 pt | python-backend-engineer | sonnet | adaptive | Phase 4 |
| TASK-5.7 | SQL-injection-safety assertions | For each of the ~60-80 query points touched in Phase 3, assert the constructed query string contains a placeholder token (`?` or the Postgres-native equivalent per TASK-3.0's determination), never an interpolated literal. May be implemented as a single parametrized test iterating over captured query strings rather than 60-80 discrete tests. | NFR-Security (PRD §6.2) | tests count toward the ~40-50 total | included above | python-backend-engineer | sonnet | adaptive | Phase 4 |

**Phase 5 total**: 2 pts (matches decisions block §4 estimation anchor).

---

## Quality Gates

- [ ] ~40-50 tests land and pass (TASK-5.1 through TASK-5.7 combined).
- [ ] Every `target_surfaces` entry across AC-1 through AC-7 has at least one directly-exercising test.
- [ ] TASK-5.3 leak tests are confirmed mutation-tested (documented pass/fail-on-revert evidence).
- [ ] TASK-5.5's full pre-existing suite passes unmodified with enforcement globally enabled — zero test edits permitted to make this pass.
- [ ] No string-interpolated SQL found across the touched query points (TASK-5.7).
- [ ] **MANDATORY `task-completion-validator` gate before Phase 6 begins** — this is an explicitly named gate per decisions block §1, not a generic phase-end pass.

## Key Files and Integration Points

- `tests/test_workspace_isolation_enforcement.py` (new — core matrix, leak tests, mutation tests, mutation-deny tests)
- `tests/test_config_workspace_enforcement.py` (new — config validation matrix)
- `tests/**/test_workspace_migration_service.py`, `test_p5_regression_suite.py` (existing — must pass unmodified per TASK-5.5)

---

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 4](./phase-4-enforcing-flip.md) | [Next: Phase 6](./phase-6-docs-changelog.md)
