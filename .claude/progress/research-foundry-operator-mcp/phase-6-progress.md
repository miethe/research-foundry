---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 6
status: in_progress
created: '2026-07-28'
updated: '2026-07-31'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- validation-implementer
contributors:
- senior-code-reviewer
- documentation-writer
- changelog-generator
- task-completion-validator
- karen
tasks:
- id: OPM-6.1
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - P5
  estimate: 0.5 pt
- id: OPM-6.2
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - OPM-6.1
  estimate: 0.5 pt
- id: OPM-6.3
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - OPM-6.1
  estimate: 0.5 pt
- id: OPM-6.4
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - OPM-6.1
  estimate: 0.5 pt
- id: OPM-6.5
  status: in_progress
  assigned_to:
  - validation-implementer
  - senior-code-reviewer
  dependencies:
  - OPM-6.1
  estimate: 0.5 pt
- id: OPM-6.6
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - OPM-6.1
  estimate: 0.25 pt
- id: OPM-6.7
  status: in_progress
  assigned_to:
  - validation-implementer
  - senior-code-reviewer
  dependencies:
  - OPM-6.1
  estimate: 0.25 pt
- id: OPM-6.8
  status: in_progress
  assigned_to:
  - validation-implementer
  dependencies:
  - OPM-6.1
  estimate: 0.25 pt
- id: OPM-6.9
  status: in_progress
  assigned_to:
  - documentation-writer
  - changelog-generator
  dependencies:
  - OPM-6.2
  - OPM-6.3
  - OPM-6.4
  - OPM-6.5
  - OPM-6.6
  - OPM-6.7
  - OPM-6.8
  estimate: 0.5 pt
- id: OPM-6.10
  status: pending
  assigned_to:
  - task-completion-validator
  - karen
  dependencies:
  - OPM-6.9
  estimate: 0.25 pt
parallelization:
  batch_1:
  - OPM-6.1
  batch_2:
  - OPM-6.2
  - OPM-6.3
  - OPM-6.4
  - OPM-6.5
  - OPM-6.6
  - OPM-6.7
  - OPM-6.8
  batch_3:
  - OPM-6.9
  batch_4:
  - OPM-6.10
total_tasks: 10
completed_tasks: 0
in_progress_tasks: 9
blocked_tasks: 0
progress: 0
---

# Phase 6 Progress — Hardening, Documentation, and Exact-Tree Review

**Dependencies**: P5.
**Integration owner**: validation implementer.
**Exit state**: one exact integrated candidate satisfies AC OPM-1..7 with truthful repository/live boundaries.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-6.1 | Integrated fixture matrix | Fixtures contain no owner/private data and enumerate expected receipts/effects | 0.5 pt |
| OPM-6.2 | Confirmation adversarial gate | AC OPM-1 evidenced; zero-effect assertions explicit | 0.5 pt |
| OPM-6.3 | Workspace/sensitivity gate | AC OPM-2 evidenced with no existence leak | 0.5 pt |
| OPM-6.4 | Lifecycle recovery gate | AC OPM-3 evidenced; interrupted/uninterrupted converge | 0.5 pt |
| OPM-6.5 | Closed-adapter gate | AC OPM-4 evidenced | 0.5 pt |
| OPM-6.6 | Import/stage seam gate | AC OPM-5 evidenced | 0.25 pt |
| OPM-6.7 | Preview-only gate | AC OPM-6 evidenced; zero external/mirror effects | 0.25 pt |
| OPM-6.8 | Transport/error gate | AC OPM-7 evidenced | 0.25 pt |
| OPM-6.9 | Docs, CHANGELOG, deferred specs | Docs match exact tool inventory and do not claim live qualification | 0.5 pt |
| OPM-6.10 | Final exact-tree review | Tier 3 approval recorded on exact current tree | 0.25 pt |

Quality gate (per plan): AC OPM-1..7 all evidenced against the exact P6 tree; docs label remote transport and live writeback `deferred` and owner/private qualification `not_executed_owner_data_absent` unless real authorized evidence exists; `task-completion-validator` then `karen` approve.

Note: the plan's Subagent column lists `documentation-writer`/`changelog-generator` at `model: haiku` for OPM-6.9 — per prior-session finding (haiku subagents inaccessible in this environment), dispatch OPM-6.9 with `model="sonnet"` override at execution time.
