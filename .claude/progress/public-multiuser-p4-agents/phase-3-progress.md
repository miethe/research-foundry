---
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 3
phase_title: 'P4.3: First provider adapter (claude_agent_sdk) e2e'
status: completed
created: 2026-07-07
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-3-4-backend-integration.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: ADP-3.1
  title: Promote claude_agent_sdk.py to real mode + wire claude_agent_sdk_provider.py
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/adapters/claude_agent_sdk.py
  - src/research_foundry/services/agent_providers/claude_agent_sdk_provider.py
  dependencies:
  - SEC-2.2
  - SEC-2.3
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:30:00Z'
  verified_by: []
  evidence:
  - import_check: imports OK
  - smoke_tests: 6/6 passed
  - unit_suite: 956 passed 0 failed
- id: ADP-3.2
  title: Wire Search Router + source-card/claim extraction as job tools/stages
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/agent_job_service.py
  - src/research_foundry/services/search_router/router.py
  - src/research_foundry/services/source_cards.py
  dependencies:
  - ADP-3.1
  started: '2026-07-07T01:00:00Z'
  completed: '2026-07-07T01:30:00Z'
  verified_by: []
  evidence:
  - unit_suite: 311 passed
  - smoke_test: build_job_brief+run_job_tool guards OK
- id: ADP-3.3
  title: E2E integration test — full job lifecycle (mock credentials)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - tests/integration/test_agent_job_e2e_claude.py
  dependencies:
  - ADP-3.2
  started: '2026-07-07T02:00:00Z'
  completed: '2026-07-07T02:30:00Z'
  verified_by: []
  evidence:
  - pytest: 8/8 passed
  - unit_suite: 311 passed no regressions
parallelization:
  batch_1:
  - ADP-3.1
  batch_2:
  - ADP-3.2
  batch_3:
  - ADP-3.3
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase P4.3 Progress: First Provider Adapter (`claude_agent_sdk`) e2e

**Constraint**: Mode-D Gate #2 NOT approved. All tests MUST use mock/stub credentials — no real API keys, no live provider network calls.

## Task Status

| Task | Title | Status | Batch |
|------|-------|--------|-------|
| ADP-3.1 | Promote adapter + provider to real mode | pending | 1 |
| ADP-3.2 | Wire Search Router + source-cards as job tools | pending | 2 |
| ADP-3.3 | E2E integration test (mock credentials) | pending | 3 |
