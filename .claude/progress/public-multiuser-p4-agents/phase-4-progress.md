---
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 4
phase_title: 'P4.4: Agent-job APIs + event streaming + acceptance'
status: completed
created: 2026-07-07
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-3-4-backend-integration.md
commit_refs: 72033a8,3d01ee0
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: API-4.1
  title: POST /api/agent-jobs launch endpoint (governance gate)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  - src/research_foundry/services/agent_job_service.py
  dependencies:
  - ADP-3.3
- id: API-4.2
  title: GET /api/agent-jobs/{id} detail + GET .../artifacts list
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  dependencies:
  - API-4.1
- id: API-4.3
  title: GET /api/agent-jobs/{id}/events SSE stream (OQ-A resolution)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  dependencies:
  - API-4.1
- id: API-4.4
  title: POST /api/agent-jobs/{id}/cancel (crash-safe cleanup)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  dependencies:
  - API-4.1
- id: API-4.5
  title: POST /api/agent-jobs/{id}/accept (sole write path, gated)
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  - src/research_foundry/services/agent_job_service.py
  dependencies:
  - API-4.2
- id: API-4.6
  title: 'Seam task (R-P3): freeze API contract fixture for FE consumption + integration
    tests'
  status: completed
  assigned_to:
  - python-backend-engineer
  files_affected:
  - src/research_foundry/api/routers/agent_jobs.py
  - src/research_foundry/api/openapi.json
  - tests/integration/test_agent_jobs_api.py
  dependencies:
  - API-4.2
  - API-4.3
  - API-4.5
parallelization:
  batch_1:
  - API-4.1
  - API-4.2
  - API-4.3
  - API-4.4
  - API-4.5
  batch_2:
  - API-4.6
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
completion_ref: .claude/progress/public-multiuser-p4-agents/phase-4-completion.md
---

# Phase P4.4: Agent-job APIs + event streaming + acceptance

**Status**: in_progress
**Phase ref**: [phase-3-4-backend-integration.md](../../../docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-3-4-backend-integration.md)

## Notes

P4.3 completed (commit d8b4400). Building on: AgentJobService (agent_job_service.py),
ClaudeAgentSDKProvider (services/agent_providers/claude_agent_sdk_provider.py),
redact_payload (governance.py), guard_check (governance.py).

Batch 1 implements all 5 REST endpoints in agent_jobs.py.
Batch 2 seals the seam task (fixture + integration tests) and regenerates openapi.json.

Security invariant (carry-forward from P4.2): every SSE event payload MUST pass
redact_payload() server-side before it reaches the wire.
