---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: "1-2"
title: "Config flag + fail-closed validation; identity threading router -> service"
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
  - id: "TASK-1.1"
    description: "Flag enum + parser for workspace_isolation_enforcement"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-1.2"
    description: "Resolver + fail-closed validation (resolve_workspace_isolation_enforced)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
  - id: "TASK-2.1"
    description: "Thread identity: catalog.py, agent_jobs.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-2.2"
    description: "Thread identity: reports.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-2.3"
    description: "Thread identity-adjacent surfaces: admin.py, audit.py, auth_identity.py (no-op verification)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-2.4"
    description: "Seam task: P2->P3 propagation verification"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1", "TASK-2.2", "TASK-3.1", "TASK-3.2", "TASK-3.3"]

parallelization:
  batch_1: ["TASK-1.1", "TASK-2.1", "TASK-2.2", "TASK-2.3"]
  batch_2: ["TASK-1.2"]
  batch_3: ["TASK-2.4"]
---

# wksp-304-workspace-isolation-enforcement - Phase 1-2

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-1.1 | Flag enum + parser | pending | python-backend-engineer | — |
| TASK-1.2 | Resolver + fail-closed validation | pending | python-backend-engineer | TASK-1.1 |
| TASK-2.1 | Thread identity: catalog.py, agent_jobs.py | pending | python-backend-engineer | — |
| TASK-2.2 | Thread identity: reports.py | pending | python-backend-engineer | — |
| TASK-2.3 | Thread identity-adjacent surfaces (no-op verification) | pending | python-backend-engineer | — |
| TASK-2.4 | Seam task: P2->P3 propagation verification | pending | python-backend-engineer | TASK-2.1, TASK-2.2, TASK-3.1, TASK-3.2, TASK-3.3 |

Full task detail: [phase-1-2-config-identity.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-1-2-config-identity.md)
