---
schema_version: 2
doc_type: progress
prd: public-multiuser-p4-agents
feature_slug: public-multiuser-p4-agents
phase: 5
status: completed
created: 2026-07-07
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1/phase-5-frontend.md
commit_refs: []
pr_refs: []
completion_ref: null
owners:
- ui-engineer-enhanced
contributors:
- python-backend-engineer
tasks:
- id: UI-5.1
  title: 'Seam task: FE types against API-4.6 contract'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/hooks/useAgentJobs.ts
  - frontend/runs-viewer/src/api/agentJobsClient.ts
  dependencies: []
  evidence: []
  verified_by: []
- id: UI-5.2
  title: AppShell nav flip + loopback gating + /agents route registration
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/screens/AgentsScreen.tsx
  - frontend/runs-viewer/src/app/routes.tsx
  - frontend/runs-viewer/src/app/App.tsx
  dependencies:
  - UI-5.1
  evidence: []
  verified_by: []
- id: UI-5.3
  title: AgentJobLaunchForm + PolicyGateSummary
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/components/Agents/AgentJobLaunchForm.tsx
  - frontend/runs-viewer/src/components/Agents/PolicyGateSummary.tsx
  - frontend/runs-viewer/src/screens/AgentsScreen.tsx
  dependencies:
  - UI-5.2
  evidence:
  - typecheck: 0 errors
  - test: 717/717 passed
  verified_by:
  - agents-launch.test.tsx
  started: '2026-07-07T12:00:00Z'
  completed: '2026-07-07T12:47:00Z'
- id: UI-5.4
  title: Research this entry points
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx
  dependencies:
  - UI-5.3
  evidence:
  - typecheck: 0 errors
  - test: 730/730 passed
  verified_by:
  - agents-entry-points.test.tsx
  started: '2026-07-07T12:50:00Z'
  completed: '2026-07-07T12:55:00Z'
- id: UI-5.5
  title: AgentJobEventPanel + useAgentJobEvents hook (SSE streaming)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/components/Agents/AgentJobEventPanel.tsx
  - frontend/runs-viewer/src/hooks/useAgentJobs.ts
  dependencies:
  - UI-5.2
  evidence:
  - typecheck: 0 errors
  - test: 759/759 passed
  verified_by:
  - agents-event-panel.test.tsx
  started: '2026-07-07T12:58:00Z'
  completed: '2026-07-07T13:00:00Z'
- id: UI-5.6
  title: EvidenceIntakePanel + job history list
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/components/Agents/EvidenceIntakePanel.tsx
  dependencies:
  - UI-5.3
  evidence:
  - typecheck: 0 errors
  - test: 795/795 passed
  verified_by:
  - agents-intake.test.tsx
  started: '2026-07-07T13:00:00Z'
  completed: '2026-07-07T13:05:00Z'
- id: UI-5.7
  title: 'FE resilience: missing policy_snapshot fields + unknown status values'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/components/Agents/PolicyGateSummary.tsx
  - frontend/runs-viewer/src/components/Agents/AgentJobEventPanel.tsx
  dependencies:
  - UI-5.3
  - UI-5.5
  evidence:
  - typecheck: 0 errors
  - test: 831/831 passed (36 new)
  verified_by:
  - agents-resilience.test.tsx
  started: '2026-07-07T13:06:00Z'
  completed: '2026-07-07T13:15:00Z'
- id: UI-5.8
  title: Runtime smoke — launch & gates (Playwright)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/test/agents-launch-smoke.test.tsx
  dependencies:
  - UI-5.4
  evidence:
  - test: frontend/runs-viewer/src/test/agents-launch-smoke.test.tsx
  verified_by:
  - UI-5.8
  started: 2026-07-07T13:10Z
  completed: 2026-07-07T13:16Z
- id: UI-5.9
  title: Runtime smoke — streaming, acceptance, resilience, no-direct-write
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  files_affected:
  - frontend/runs-viewer/src/test/agents-events-smoke.test.tsx
  dependencies:
  - UI-5.5
  - UI-5.6
  - UI-5.7
  evidence:
  - file: frontend/runs-viewer/src/test/agents-events-smoke.test.tsx
  - test: 14/14 pass, 0 TS errors
  verified_by:
  - UI-5.9
  started: 2026-07-07T13:15Z
  completed: 2026-07-07T13:25Z
parallelization:
  batch_1:
  - UI-5.1
  - UI-5.2
  batch_2:
  - UI-5.3
  batch_3:
  - UI-5.4
  - UI-5.5
  - UI-5.6
  batch_4:
  - UI-5.7
  batch_5:
  - UI-5.8
  - UI-5.9
total_tasks: 9
completed_tasks: 9
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 5 Progress: Frontend `/agents` Route

**Phase**: P4.5 | **Status**: in_progress | **Branch**: feat/public-multiuser-p4-agents

## Task Status

| Task | Title | Status | Agent |
|------|-------|--------|-------|
| UI-5.1 | Seam: FE types vs API-4.6 contract | pending | ui-engineer-enhanced |
| UI-5.2 | AppShell nav flip + loopback gating | pending | ui-engineer-enhanced |
| UI-5.3 | AgentJobLaunchForm + PolicyGateSummary | pending | ui-engineer-enhanced |
| UI-5.4 | "Research this" entry points | pending | ui-engineer-enhanced |
| UI-5.5 | AgentJobEventPanel + SSE hook | pending | ui-engineer-enhanced |
| UI-5.6 | EvidenceIntakePanel + job history | pending | ui-engineer-enhanced |
| UI-5.7 | FE resilience (nulls + unknown status) | pending | ui-engineer-enhanced |
| UI-5.8 | Smoke: launch & gates | pending | ui-engineer-enhanced |
| UI-5.9 | Smoke: streaming, acceptance, resilience | pending | ui-engineer-enhanced |

## Batch Plan

- **Batch 1** (serial — UI-5.1 then UI-5.2): API client + hooks foundation, then nav flip + route registration
- **Batch 2**: LaunchForm + PolicyGateSummary (governance-visible UI, extended effort)
- **Batch 3** (parallel — UI-5.4 + UI-5.5 + UI-5.6): Entry points, event panel, intake panel
- **Batch 4**: Resilience pass (nulls, unknown status)
- **Batch 5** (parallel — UI-5.8 + UI-5.9): Vitest smoke tests

## Notes

- API contract fixture: `tests/integration/test_agent_jobs_api.py` lines 13–66
- Auth contract: `workspace_id` and `created_by` are always nullable (D12 — auth deferred P5)
- Loopback gating: `/agents` only mounts in loopback/single-operator mode (default: disabled)
- ICA offload intended for UI-5.5 and UI-5.6 but handled by ui-engineer-enhanced here
- `AppShell.tsx` is the owned serialization barrier for this phase
