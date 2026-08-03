---
type: context
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
title: "Agent Research Loopback Slice (Hardening) - Development Context"
status: "active"
created: "2026-08-03"
updated: "2026-08-03"

critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []
agents: []
---

# agent-research-loopback-slice - Development Context

**Status**: Active Development (not yet started — tracking artifacts only)
**Created**: 2026-08-03
**Last Updated**: 2026-08-03

> **Purpose**: Shared worknotes for all agents working this plan. Add brief observations, decisions,
> gotchas, and implementation notes that future agents should know. This file is the sticky-note pad;
> the execution ledger (OQ resolutions, Mode-D approval records, deviation rationale) lives in
> `implementation-notes.md` in this same directory — do not duplicate that content here.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: none yet

**Plan doctrine**: this is a Claude-5 plan — `routing_constraints` in the plan resolve model/agent
selection at dispatch time. Progress files in `.claude/progress/agent-research-loopback-slice/`
deliberately carry no `owners`/`assigned_to`/model pins; do not add them here either.

---

## Milestone map (M1->phase-1 .. M3->phase-3)

| Milestone | Progress file | ITT node | Gate lens | Mode-D halt |
|---|---|---|---|---|
| M1 — SSE event stream authenticates via Authorization header | `.claude/progress/agent-research-loopback-slice/phase-1-progress.md` | node_01KZ4A1ZHFXH1ZRDXPPFGEV95Z | security, validator (authz-boundary) | conditional — none scheduled; halts only on scope drift into `src/research_foundry/` |
| M2 — Cancel affordance reaches the live cancel endpoint | `.claude/progress/agent-research-loopback-slice/phase-2-progress.md` | node_01KZ4A2GHGR6QG4EP1AMNKAR3D | validator | no |
| M3 — Contract test exercises the real client with no hooks mocks | `.claude/progress/agent-research-loopback-slice/phase-3-progress.md` | node_01KZ4A3H0R7KZT8WF6A7DG1VTG | validator | no |

Plan-level ITT node: `node_01KZ49ZWATPNKDNGF3APTBEFQP` — tree `tree_01KVTH95G09FX26HCRPBV77DAE`.

Waves execute strictly in order (`wave_plan.waves: [["M1"],["M2"],["M3"]]`) and **the order is
load-bearing, not merge-conflict hygiene**: M2 edits `AgentsScreen.tsx` against M1's settled hook
shape (avoiding two concurrent editors of the same seam), and M3 asserts against both M1's reader and
M2's cancel call, so it can only cover them once they exist.

---

## Implementation Decisions

> Key architectural and technical decisions made during development

_None yet — see the plan's own `decisions:` frontmatter block for the three decisions already accepted
at plan-authoring time: carry the SSE token in an `Authorization` header via `fetch` + `ReadableStream`,
retiring `EventSource` for this stream (rejected: runtime-resolve the token but keep the query param);
keep the 7 existing hooks-mocking `agents-*` tests and add a layer beneath them (don't trade one blind
spot for another); static (non-loopback) mode is untouched (a supported product surface, not dead code)._

---

## Open questions carried into execution

- **OQ-1**: Does `stream_events()` accept the resume id as a `Last-Event-ID` header, or only as the
  existing query param? Decision rule: resolve from code truth at
  `src/research_foundry/api/routers/agent_jobs.py:396-428` and send whichever the server already reads
  — implementation detail, do NOT halt on it. Only the *token* must move to a header; the resume id is
  not a credential and may stay a query param.
- **OQ-2**: Is a `globalThis.fetch` spy sufficient for M3, or does MSW earn a new dependency? Decision
  rule: default to the fetch-spy pattern already proven in `src/test/p5-auth-header.test.ts` (14/14
  passing); adopt MSW only if the spy cannot express SSE streaming — record the choice here either way.

---

## Gotchas & Observations

> Things that tripped us up or patterns discovered during implementation

_None yet._

---

## Integration Notes

> How components interact and connect

_None yet._

---

## Performance Notes

> Performance considerations discovered during implementation

_None yet._

---

## Agent Handoff Notes

> Quick context for agents picking up work

_None yet — this is the initial tracking-artifact creation. Next agent picks up at M1 entry:
`ARLS-1.1` in `phase-1-progress.md` (replace `EventSource` with a fetch + `ReadableStream` reader)._

---

## References

**Related Files**:
- Source plan: `docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md`
- PRD: `docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md`
- Sibling shared-seam precedent (completed, not a dependency):
  `docs/project_plans/feature_contracts/enhancements/runs-viewer-builder-live-claim-previews.md`
- Plan that shipped the slice this PRD hardens:
  `docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md`
- Execution ledger (OQ resolutions, Mode-D approvals, deviations):
  `.claude/worknotes/agent-research-loopback-slice/implementation-notes.md`
- Progress files: `.claude/progress/agent-research-loopback-slice/phase-{1,2,3}-progress.md`
