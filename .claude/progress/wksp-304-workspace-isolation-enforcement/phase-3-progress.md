---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 3
title: "Query-layer scoping (3 services) — largest, single-owner phase"
status: pending
created: 2026-07-08
updated: 2026-07-08
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs: []
pr_refs: []

owners: ["data-layer-expert"]
contributors: ["backend-architect"]

tasks:
  - id: "TASK-3.0"
    description: "Pre-work exploration: caller-set + backend-parameter-style confirmation"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-1.1", "TASK-1.2", "TASK-2.1", "TASK-2.2", "TASK-2.3"]
  - id: "TASK-3.1"
    description: "Scope catalog_service.py (~10 query points)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-3.0"]
  - id: "TASK-3.2"
    description: "Scope builder_service.py (~4 query points)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-3.0"]
  - id: "TASK-3.3"
    description: "Scope agent_job_service.py (~2 query points)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-3.0"]
  - id: "TASK-3.4"
    description: "Close JOIN + tombstone leaks (AC-4)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-3.1", "TASK-3.2"]
  - id: "TASK-3.5"
    description: "Gate-helper contract review"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TASK-3.1", "TASK-3.2", "TASK-3.3"]
  - id: "TASK-3.6"
    description: "P3 exit-gate: 100%-coverage checklist (hard gate for Phase 4 entry)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-3.1", "TASK-3.2", "TASK-3.3", "TASK-3.4", "TASK-3.5"]

parallelization:
  batch_1: ["TASK-3.0"]
  batch_2: ["TASK-3.1", "TASK-3.2", "TASK-3.3"]
  batch_3: ["TASK-3.4", "TASK-3.5"]
  batch_4: ["TASK-3.6"]
---

# wksp-304-workspace-isolation-enforcement - Phase 3

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-3.0 | Pre-work exploration: caller-set + param-style confirmation | pending | data-layer-expert | P1+P2 tasks |
| TASK-3.1 | Scope catalog_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.2 | Scope builder_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.3 | Scope agent_job_service.py | pending | data-layer-expert | TASK-3.0 |
| TASK-3.4 | Close JOIN + tombstone leaks (AC-4) | pending | data-layer-expert | TASK-3.1, TASK-3.2 |
| TASK-3.5 | Gate-helper contract review | pending | backend-architect | TASK-3.1, TASK-3.2, TASK-3.3 |
| TASK-3.6 | **P3 exit-gate — hard gate for Phase 4 entry** | pending | data-layer-expert | TASK-3.1..3.5 |

**Non-negotiable ordering invariant**: TASK-3.6's sign-off (task-completion-validator reviewed) is the hard entry-gate for every Phase 4 task — see phase-4-progress.md.

Full task detail: [phase-3-query-layer-scoping.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-3-query-layer-scoping.md)
