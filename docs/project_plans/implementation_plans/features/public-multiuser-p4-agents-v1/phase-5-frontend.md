---
schema_version: 2
doc_type: phase_plan
title: "Phase 5: Frontend — /agents Route"
status: draft
created: 2026-07-06
phase: "P4.5"
phase_title: "Frontend /agents route"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
entry_criteria:
  - "P4.3 e2e proven (contracts mockable); API-4.6 seam fixture available (may build against mock before P4.4 fully lands, per parallel-wave note)"
exit_criteria:
  - "Runtime smoke over all target_surfaces green; npm run build + Playwright job-flow spec green"
---

# Phase 5: Frontend

[← Back to plan summary](../public-multiuser-p4-agents-v1.md)

**Column conventions**: `Estimate` = story points. `Model`: `opus|sonnet|haiku|gpt-5.5-codex`. `Effort` (claude): `adaptive|extended`. `Provider` (only where offload applies): `claude|ica`. See `.claude/skills/planning/references/multi-model-guidance.md`.

---

## Phase P4.5: Frontend `/agents` route

**Estimate**: 4 pts
**Dependencies**: P4.3 (contracts mockable); runs in parallel with P4.4 per the plan's wave 4 (backend `api/` vs frontend `runs-viewer/`, no file overlap)
**Isolation**: shared
**Assigned Subagent(s)**: ui-engineer-enhanced (primary); **ICA Sonnet 4.6** (secondary, job-list/event-log subcomponents only)
**Agent Routing**: Job-list and event-log subcomponents (UI-5.5, UI-5.6) are offloadable to ICA Sonnet 4.6 **behind a `task-completion-validator` gate** — give the delegate the mockup + the existing AppShell nav pattern. The launch form + `PolicyGateSummary` (UI-5.3) stay on the primary sonnet session: this is governance-visible UI (the gates a researcher must see before launch) and warrants the closer review a primary-authored task gets.
**Integration Owner (R-P3, receiving side)**: ui-engineer-enhanced consumes the API-4.6 contract fixture from `phase-3-4-backend-integration.md`; UI-5.1 below is this phase's half of the seam-verification pair.

### Overview

Flip `AppShell.tsx`'s Agents nav entry from `disabled` to `enabled` (FR-18), reusing the P3 `isBuilderLoopbackEnabled()` pattern for an `isAgentsLoopbackEnabled()` analog (static-export mode renders a clear informational state, not a broken route). Build the launch flow, live event stream, and Evidence Intake accept/reject UI (FR-19). This is the plan's one UI-touching phase — Plan Generator Rule R-P4 requires a runtime-smoke task referencing every `target_surfaces` entry from this phase's ACs, added at the end of this table (UI-5.8/UI-5.9).

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Provider | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|----------|--------------|
| UI-5.1 | **Seam task (R-P3, receiving side)**: verify FE types against API-4.6 contract | Build `useAgentJobs.ts` hook + `agentJobsClient.ts` against the API-4.6 fixture (job detail incl. `policy_snapshot`, artifacts list, SSE event schema). Confirm OQ-B (staging store location) has no FE-visible impact beyond the artifacts-list shape already fixed. | FE types compile against the fixture with no `any`-typed escape hatches for the fields named in AC-2.3/AC-3.5/AC-4.4/AC-4.5. | 0.25 pt | ui-engineer-enhanced | sonnet | adaptive | claude | API-4.6 |
| UI-5.2 | AppShell nav flip + loopback gating | Flip `NAV_ITEMS` Agents entry `disabled`→`enabled` (FR-18); add `isAgentsLoopbackEnabled()` analog of `isBuilderLoopbackEnabled()` (`hooks/useBuilder.ts`/`api/reportsClient.ts` pattern) gating static-export mode to a clear informational state. | Static-export mode shows an informational (not broken) `/agents` state; loopback mode reaches the real route. | 0.5 pt | ui-engineer-enhanced | sonnet | adaptive | claude | UI-5.1 |
| UI-5.3 | `AgentJobLaunchForm.tsx` + `PolicyGateSummary.tsx` | Claim/report-gap context pre-population (AC-1.1); provider/model/tools/budget/sensitivity gates visible + explicit acknowledgment required before Launch enables (AC-1.2, AC-4.1, AC-4.4); surfaces the violated `rule_id`/message on a `guard_check` rejection (AC-4.4 resilience clause). | See AC-4.4 target_surfaces (`AgentsScreen.tsx`, `AgentJobLaunchForm.tsx`, `PolicyGateSummary.tsx`) — before/after screenshots at desktop ≥1440px per PRD `visual_evidence_required`. | 1 pt | ui-engineer-enhanced | sonnet | extended | claude | UI-5.2 |
| UI-5.4 | "Research this" entry points | Add entry points in `ClaimAuditWorkbench.tsx` and `ReportOverlay.tsx` passing `input_claim_ids`/`input_report_id` via route state into `AgentsScreen`'s launch form (AC-1.4). Direct navigation to `/agents` (no context) renders an empty/manual context picker, not an error (AC-1.4 resilience). | See AC-1.4 target_surfaces — before/after screenshots per `visual_evidence_required`. | 0.5 pt | ui-engineer-enhanced | sonnet | adaptive | claude | UI-5.3 |
| UI-5.5 | `AgentJobEventPanel.tsx` + `useAgentJobEvents` hook | EventSource consumption of `GET .../events`; append to an ARIA live region; "waiting for events" state on drop/empty, resumes from last known event without duplicating rows on reconnect (AC-2.3). | See AC-2.3 target_surfaces — before/after screenshots (mid-stream + post-completion). | 0.5 pt | ui-engineer-enhanced (delegate) | sonnet | adaptive | **ica** (behind `task-completion-validator` gate; give delegate the mockup + AppShell nav pattern) | UI-5.2 |
| UI-5.6 | `EvidenceIntakePanel.tsx` + job history list | Accept/reject controls calling `POST .../accept` with the selected subset (AC-3.5); items missing an expected field (e.g., no `source_candidates` on a `claim_proposal`) render an "incomplete proposal — review before accepting" badge rather than being silently omitted (AC-3.5 resilience). | See AC-3.5 target_surfaces — before/after screenshots with ≥1 accepted and ≥1 rejected item. | 0.5 pt | ui-engineer-enhanced (delegate) | sonnet | adaptive | **ica** (behind `task-completion-validator` gate) | UI-5.3 |
| UI-5.7 | FE resilience: missing `policy_snapshot` fields + unknown job-status values (R-P2) | `PolicyGateSummary` renders "not recorded" per-field (not omission/crash) when a job record predates a `policy_snapshot` field or a field is null (AC-4.5). **Additionally** (R-P2 extension beyond the PRD's explicit AC): job-history/detail views render an "unknown status" fallback badge for any `status` enum value not in the FE's known mapping, so a future backend status addition degrades gracefully rather than breaking the list. | AC-4.5 passes; unit test asserts an unrecognized status string renders the fallback badge, not a crash. | 0.25 pt | ui-engineer-enhanced | sonnet | adaptive | claude | UI-5.3 |
| UI-5.8 | **Runtime smoke (R-P4)** — launch & gates | `AGENT-VERIFY-launch-context-smoke` + `AGENT-VERIFY-launch-gates-smoke`: smoke over target_surfaces `ClaimAuditWorkbench.tsx`, `ReportOverlay.tsx`, `AgentsScreen.tsx`, `AgentJobLaunchForm.tsx`, `PolicyGateSummary.tsx` — verifies the "Research this" entry point pre-populates the launch form and gates block Launch until acknowledged. | Playwright smoke passes for both verify IDs; screenshots captured per PRD `visual_evidence_required`. | 0.25 pt | ui-engineer-enhanced | sonnet | adaptive | claude | UI-5.4 |
| UI-5.9 | **Runtime smoke (R-P4)** — streaming, acceptance, resilience, no-direct-write | `AGENT-VERIFY-event-stream-smoke`, `AGENT-VERIFY-acceptance-flow-smoke`, `AGENT-VERIFY-no-direct-write-audit`, `AGENT-VERIFY-policy-snapshot-resilience`: smoke over `AgentsScreen.tsx`, `AgentJobEventPanel.tsx`, `EvidenceIntakePanel.tsx`, `PolicyGateSummary.tsx` — verifies live streaming render, accept/reject flow, and (cross-referencing API-4.5's audit) that no code path bypasses the accept endpoint. | All 4 verify IDs pass; `AGENT-VERIFY-no-direct-write-audit` cross-checks API-4.5's backend audit test from the FE-triggered path. | 0.25 pt | ui-engineer-enhanced, python-backend-engineer (no-direct-write audit is cross-cutting) | sonnet | adaptive | claude | UI-5.5, UI-5.6, UI-5.7, API-4.5 |

**Phase P4.5 Quality Gates (phase exit gate, per decisions block):**
- [ ] Runtime smoke green over every `target_surfaces` entry named in PRD AC-1.4, AC-2.3, AC-3.5, AC-4.4, AC-4.5 (UI-5.8/UI-5.9).
- [ ] `npm run build` clean.
- [ ] Playwright job-flow spec green (launch-from-claim-context → live stream → accept/reject → nav flip).
- [ ] Static-export mode verified to show the informational `/agents` state (not a broken route).
- [ ] `task-completion-validator` **and** `karen` (integration milestone) both passed — one of the plan's 3 mandatory `karen` gates.

---

[← Back to plan summary](../public-multiuser-p4-agents-v1.md) | [← Phase 3–4](./phase-3-4-backend-integration.md) | [Next: Phase 6–7 →](./phase-6-7-second-adapter-validation.md)
