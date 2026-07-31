---
type: progress
schema_version: 2
doc_type: progress
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
phase: 4
status: pending
created: '2026-07-28'
updated: '2026-07-31'
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors:
- api-designer
- task-completion-validator
tasks:
- id: OPM-4.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-5.G
  - OPM-2.4
  estimate: 1 pt
  started: 2026-07-31T00:30Z
  completed: 2026-07-31T01:20Z
  evidence:
  - commit: fcfcd89
  - test: tests/unit/test_operator_mcp_adapter_external_import.py
- id: OPM-4.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-4.1
  estimate: 1 pt
  started: 2026-07-31T00:30Z
  completed: 2026-07-31T01:20Z
  evidence:
  - commit: fcfcd89
  - test: tests/unit/test_operator_mcp_adapter_source_ingest.py
- id: OPM-4.3
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-4.2
  estimate: 1.5 pts
  started: 2026-07-31T00:30Z
  completed: 2026-07-31T01:20Z
  evidence:
  - commit: fcfcd89
  - test: tests/unit/test_operator_mcp_adapter_research_stages.py
- id: OPM-4.4
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPM-4.3
  estimate: 1 pt
  started: 2026-07-31T00:30Z
  completed: 2026-07-31T01:20Z
  evidence:
  - commit: fcfcd89
  - test: tests/unit/test_operator_mcp_adapter_verify_bundle.py
- id: OPM-4.5
  status: pending
  assigned_to:
  - api-designer
  - task-completion-validator
  dependencies:
  - OPM-4.1
  - OPM-4.2
  - OPM-4.3
  - OPM-4.4
  estimate: 0.5 pt
parallelization:
  batch_1:
  - OPM-4.1
  batch_2:
  - OPM-4.2
  batch_3:
  - OPM-4.3
  batch_4:
  - OPM-4.4
  batch_5:
  - OPM-4.5
total_tasks: 5
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 80
---

# Phase 4 Progress — Import and Research-Stage Adapters

**Dependencies**: P3 and `ERI-5.G`.
**Integration owner**: python-backend-engineer.
**Exit state**: import and canonical research stages share the operation lifecycle, preserve prerequisites/receipts, and block unsafe chaining.

| Task ID | Task | Acceptance criteria | Estimate |
|---|---|---|---:|
| OPM-4.1 | External import adapter | MCP adapter parses no packet member; direct ERI/MCP receipts match refs | 1 pt |
| OPM-4.2 | Source ingest adapter | No hard-coded default workspace; denied/degraded ingest remains explicit | 1 pt |
| OPM-4.3 | Extract and claim-map adapters | Missing/changed inputs deny; exact retry creates no duplicate cards/claims | 1.5 pts |
| OPM-4.4 | Synthesize, verify, and bundle adapters | Unsupported verification blocks dependent bundle action; no false success | 1 pt |
| OPM-4.5 | Cross-stage seam gate | Service parity, interrupted chain, and provenance-reference fixtures pass | 0.5 pt |

Quality gate (per plan): External Interchange exact-tree dependency is recorded; verification-denial, stage-missing, wrong-workspace, sensitivity, timeout, cancel, and resume cases pass; `task-completion-validator` and `karen` approve the integrated mutation milestone.
