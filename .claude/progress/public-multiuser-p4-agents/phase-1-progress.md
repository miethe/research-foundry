---
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 1
phase_title: 'P4.1: Job model + ResearchAgentProvider port'
status: completed
created: 2026-07-06
updated: '2026-07-06'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-1-2-foundations.md
commit_refs: []
pr_refs: []
owners:
- backend-architect
- python-backend-engineer
contributors: []
tasks:
- id: JOB-1.1
  title: ResearchAgentProvider Protocol + registry
  status: completed
  assigned_to:
  - backend-architect
  files_affected:
  - src/research_foundry/services/agent_providers/base.py
  dependencies: []
  started: null
  completed: null
  evidence:
  - note: src/research_foundry/services/agent_providers/base.py created; flake8 E9/F63/F7/F82
      clean; isinstance + registry round-trip assertions passed
- id: JOB-1.2
  title: agent_job schema + durable store (OQ-B)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/agent_job_schemas.py
  - src/research_foundry/paths.py
  dependencies:
  - JOB-1.1
  started: 2026-07-06T00:00Z
  completed: 2026-07-06T00:30Z
  evidence:
  - file: src/research_foundry/services/agent_job_schemas.py
  - file: src/research_foundry/paths.py
- id: JOB-1.3
  title: agent_job_event/artifact/tool_call/approval/acceptance schemas
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/services/agent_job_schemas.py
  - tests/unit/test_agent_job_schemas.py
  dependencies:
  - JOB-1.2
  started: '2026-07-06T00:00:00Z'
  completed: '2026-07-06T00:30:00Z'
  evidence:
  - test: tests/unit/test_agent_job_schemas.py
- id: JOB-1.4
  title: Job state machine
  status: completed
  assigned_to:
  - backend-architect
  files_affected:
  - src/research_foundry/services/agent_job_schemas.py
  - tests/unit/test_agent_job_schemas.py
  dependencies:
  - JOB-1.2
  started: null
  completed: null
  evidence:
  - note: 28 tests pass (ba53bf8); LEGAL_TRANSITIONS + validate_transition added to
      agent_job_schemas.py
parallelization:
  batch_1:
  - JOB-1.1
  batch_2:
  - JOB-1.2
  batch_3:
  - JOB-1.3
  batch_4:
  - JOB-1.4
serialization_note: 'JOB-1.3 and JOB-1.4 both touch agent_job_schemas.py and tests/unit/test_agent_job_schemas.py.
  File-ownership-first rule requires serialization — JOB-1.3 runs in batch_3, JOB-1.4
  in batch_4.

  '
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase P4.1 Progress: Job Model + ResearchAgentProvider Port

**Branch**: feat/public-multiuser-p4-agents
**Isolation**: shared
**Phase model**: sonnet
**Phase effort**: extended

## Batch Execution Plan

| Batch | Tasks | Assigned | Status |
|-------|-------|----------|--------|
| 1 | JOB-1.1 | backend-architect | pending |
| 2 | JOB-1.2 | python-backend-engineer | pending |
| 3 | JOB-1.3 | python-backend-engineer | pending |
| 4 | JOB-1.4 | backend-architect | pending |

## Files Affected (P4.1 boundary)

- `src/research_foundry/services/agent_providers/base.py` — new file (JOB-1.1)
- `src/research_foundry/services/agent_job_schemas.py` — new file (JOB-1.2, extended by JOB-1.3, JOB-1.4)
- `src/research_foundry/paths.py` — add `agent_job_dir` accessor (JOB-1.2)
- `tests/unit/test_agent_job_schemas.py` — new file (JOB-1.3, extended by JOB-1.4)

## Serialization Barriers (DO NOT TOUCH in P4.1)

- `src/research_foundry/api/openapi.json`
- `CHANGELOG.md`
- `frontend/runs-viewer/src/app/AppShell.tsx`

## Phase Exit Criteria

- [ ] Schema fixtures for all 6 record types committed and validated
- [ ] Registry round-trip (register→get→list) unit-tested
- [ ] State machine transition matrix unit-tested (legal + illegal)
- [ ] No provider implementation exists — confirmed by grep
- [ ] `task-completion-validator` review passed
