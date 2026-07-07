---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 6
status: completed
created: '2026-07-07'
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-6-7-second-adapter-validation.md
commit_refs:
- 79b2175
- 130dc22
pr_refs: []
owners:
- python-backend-engineer
contributors:
- backend-architect
tasks:
- id: ADP-6.1
  title: openai_agents.py adapter (net-new, FR-2)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/adapters/openai_agents.py
  - src/research_foundry/services/agent_providers/openai_agents_provider.py
  - src/research_foundry/services/agent_job_service.py
  dependencies: []
- id: ADP-6.2
  title: SDK-native guardrails/HITL/tracing wiring
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/adapters/openai_agents.py
  - src/research_foundry/services/agent_providers/openai_agents_provider.py
  dependencies:
  - ADP-6.1
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:00:00Z'
  evidence:
  - commit: pending
- id: ADP-6.3
  title: Provider-parametrized integration test suite
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - tests/integration/test_agent_job_e2e_openai.py
  dependencies:
  - ADP-6.2
  started: '2026-07-07T00:00:00Z'
  completed: '2026-07-07T00:30:00Z'
  evidence:
  - file: tests/integration/test_agent_job_e2e_openai.py
parallelization:
  batch_1:
  - ADP-6.1
  batch_2:
  - ADP-6.2
  batch_3:
  - ADP-6.3
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
completion_ref: .claude/progress/public-multiuser-p4-agents/phase-6-completion.md
---

# Phase P4.6 Progress: openai_agents Second Adapter

**Plan ref**: `docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-6-7-second-adapter-validation.md`
**Branch**: `feat/public-multiuser-p4-agents`

## Quality Gates

- [ ] ADP-6.1: Registry lists `openai_agents`; stub job round-trips through spawn/temp-file/firewall path.
- [ ] ADP-6.2: Blocked-action test asserts block + recorded event.
- [ ] ADP-6.3: Both providers pass identical lifecycle test matrix.
- [ ] No isolation-layer (P4.2) files modified.
- [ ] `agents.enabled` / provider enable stays loopback/single-operator only.
- [ ] `task-completion-validator` review passed.
