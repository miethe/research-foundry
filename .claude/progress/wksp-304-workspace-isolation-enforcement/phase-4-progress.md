---
type: progress
schema_version: 2
doc_type: progress
prd: wksp-304-workspace-isolation-enforcement
feature_slug: wksp-304-workspace-isolation-enforcement
phase: 4
title: "Enforcing flip + deny paths — the atomic arming step (Mode D core)"
status: pending
created: 2026-07-08
updated: 2026-07-08
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
commit_refs: []
pr_refs: []

owners: ["backend-architect"]
contributors: ["python-backend-engineer"]

tasks:
  # NOTE: every task below includes TASK-3.6 in `dependencies` by design — this is
  # the non-negotiable P3->P4 ordering invariant (decisions block D4 / Risk 1).
  # P4 must not start until Phase 3's 100%-coverage checklist (TASK-3.6) has
  # signed off and been task-completion-validator-reviewed.
  - id: "TASK-4.1"
    description: "Flip require_workspace_scope to enforcing + D3 ordering proof"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TASK-3.6"]
  - id: "TASK-4.2"
    description: "Wire 404-on-read + list-omit deny consumption (OQ-1)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TASK-4.1", "TASK-3.6"]
  - id: "TASK-4.3"
    description: "Wire mutation-deny paths (AC-5)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.2", "TASK-3.6"]
  - id: "TASK-4.4"
    description: "(Optional, non-blocking) Deny-event telemetry (OQ-2)"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TASK-4.2", "TASK-3.6"]

parallelization:
  batch_1: ["TASK-4.1"]
  batch_2: ["TASK-4.2"]
  batch_3: ["TASK-4.3", "TASK-4.4"]
---

# wksp-304-workspace-isolation-enforcement - Phase 4

**HARD GATE**: no task in this phase may begin until Phase 3's `TASK-3.6` (100%-coverage checklist) has signed off and been `task-completion-validator`-reviewed. Every task row below carries `TASK-3.6` in its `dependencies` for exactly this reason.

| Task | Description | Status | Assigned | Dependencies |
|------|--------------|--------|----------|--------------|
| TASK-4.1 | Flip require_workspace_scope to enforcing + D3 ordering proof | pending | backend-architect | TASK-3.6 |
| TASK-4.2 | Wire 404-on-read + list-omit deny consumption | pending | backend-architect | TASK-4.1, TASK-3.6 |
| TASK-4.3 | Wire mutation-deny paths (AC-5) | pending | python-backend-engineer | TASK-4.2, TASK-3.6 |
| TASK-4.4 | (Optional) Deny-event telemetry (OQ-2) | pending | backend-architect | TASK-4.2, TASK-3.6 |

Full task detail: [phase-4-enforcing-flip.md](../../../docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1/phase-4-enforcing-flip.md)
