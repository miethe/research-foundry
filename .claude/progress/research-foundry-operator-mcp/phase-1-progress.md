---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 1
status: in_progress
created: '2026-07-28'
updated: '2026-07-28'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- backend-architect
contributors:
- api-designer
- python-backend-engineer
- task-completion-validator
- karen
tasks:
- id: OPM-1.1
  status: completed
  assigned_to:
  - api-designer
  dependencies:
  - RPC-1.G
  - KMCP-1.G
  estimate: 1 pt
- id: OPM-1.2
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - OPM-1.1
  estimate: 1 pt
- id: OPM-1.3
  status: completed
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies:
  - OPM-1.2
  estimate: 1 pt
- id: OPM-1.4
  status: completed
  assigned_to:
  - api-designer
  dependencies:
  - OPM-1.1
  estimate: 1 pt
- id: OPM-1.G
  status: pending
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - OPM-1.2
  - OPM-1.3
  - OPM-1.4
  estimate: gate
parallelization:
  batch_1:
  - OPM-1.1
  batch_2:
  - OPM-1.2
  - OPM-1.4
  batch_3:
  - OPM-1.3
  batch_4:
  - OPM-1.G
total_tasks: 5
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 80
---

# Phase 1 Progress — Contract, Identity, and Confirmation

**Dependencies**: Research Provenance Continuity `RPC-1.G` and Knowledge MCP `KMCP-1.G` approved exact-tree contracts.
**Integration owner**: backend-architect.
**Exit state**: effect writers have stable schemas, trusted identity inputs, policy order, confirmation semantics, limits, and safe errors.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-1.1 | Operation and tool contract | Positive/negative fixtures validate; unknown/wildcard operations reject | 1 pt |
| OPM-1.2 | Identity and sensitivity contract | Missing/wrong identity and two-workspace fixtures return one safe denial | 1 pt |
| OPM-1.3 | Guard/preflight and confirmation | Expired/replayed/mismatched token matrix produces zero manifest/effects | 1 pt |
| OPM-1.4 | Receipt and bounded-error schemas | Golden/negative schemas reject unbounded/raw exception and unauthorized fields | 1 pt |
| OPM-1.G | Tier-3 contract gate | task-completion-validator then Karen APPROVE the same exact tree; material changes invalidate both verdicts | gate |

Quality gate (per plan): OPM-OQ-1..4 resolved or defaults explicitly approved; security reviewer verifies authorization-before-lookup and token binding; `task-completion-validator` then Karen approve the same exact schemas/examples/threat-matrix tree; no effect adapter or MCP server exists yet.
