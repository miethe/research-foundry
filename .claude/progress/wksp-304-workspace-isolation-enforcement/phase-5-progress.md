---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 5
title: "Regression + enforcement test matrix — runtime-verification phase"
status: pending
created: 2026-07-08
updated: 2026-07-08
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs: []
pr_refs: []

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "TASK-5.1"
    description: "Core 2-workspace x {read, list, mutate} x {allowed, denied} matrix (~12 tests)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.2"
    description: "Router-level identity-propagation regression tests (6 routers)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.3"
    description: "Join / tombstone leak edge cases, mutation-tested (~15 tests)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.4"
    description: "Mutation-deny tests (AC-5)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.5"
    description: "Single-operator fallback — full unmodified suite pass (AC-6)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.6"
    description: "Config validation matrix (~5 tests, AC-7)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]
  - id: "TASK-5.7"
    description: "SQL-injection-safety assertions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.3"]

parallelization:
  batch_1: ["TASK-5.1", "TASK-5.2", "TASK-5.3", "TASK-5.4", "TASK-5.5", "TASK-5.6", "TASK-5.7"]
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
