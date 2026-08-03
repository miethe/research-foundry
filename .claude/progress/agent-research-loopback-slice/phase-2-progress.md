---
type: progress
schema_version: 2
doc_type: progress
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
milestone: M2
phase: 2
title: Cancel affordance reaches the live cancel endpoint
status: pending
created: '2026-08-03'
updated: '2026-08-03'
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ4A2GHGR6QG4EP1AMNKAR3D
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
gate_lens:
- validator
mode_d_halt: false
karen_required_this_milestone: false
tasks:
- id: ARLS-2.1
  description: Add a cancel affordance to AgentsScreen.tsx (or AgentJobEventPanel.tsx)
    wired to useCancelAgentJob(), visible only for jobs in a cancellable (running)
    state per RUNNING_STATUSES (FR-5).
  status: pending
  dependencies: []
- id: ARLS-2.2
  description: Add an explicit confirm step (confirm dialog or two-step button)
    before dispatching cancelAgentJob() (FR-6).
  status: pending
  dependencies:
  - ARLS-2.1
- id: ARLS-2.3
  description: Verify job-detail query invalidation and terminal-state reactivity
    on success (no manual refresh needed), and that failures surface an error
    rather than appearing successful; test both success and failure cancel paths
    (FR-7).
  status: pending
  dependencies:
  - ARLS-2.2
- id: ARLS-2.G
  description: 'Milestone gate (validator lens): useCancelAgentJob has a real caller;
    confirm-then-cancel and failure paths both tested.'
  status: pending
  dependencies:
  - ARLS-2.3
parallelization:
  batch_1:
  - ARLS-2.1
  batch_2:
  - ARLS-2.2
  batch_3:
  - ARLS-2.3
  batch_4:
  - ARLS-2.G
  critical_path:
  - ARLS-2.1
  - ARLS-2.2
  - ARLS-2.3
  - ARLS-2.G
blockers: []
success_criteria:
- id: AC-M2-1
  description: Cancel affordance is present only for jobs in a cancellable (running)
    state.
  status: pending
- id: AC-M2-2
  description: An explicit confirm step precedes the cancel request.
  status: pending
- id: AC-M2-3
  description: The job-detail query is invalidated on successful cancel.
  status: pending
- id: AC-M2-4
  description: A failed cancel surfaces an error rather than appearing successful.
  status: pending
- id: AC-M2-5
  description: useCancelAgentJob has >=1 caller outside the hooks directory.
  status: pending
- id: AC-M2-6
  description: Both success and failure cancel paths are tested.
  status: pending
files_modified: []
progress: 0
---

# agent-research-loopback-slice - Phase 2 (M2): Cancel affordance reaches the live cancel endpoint

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/agent-research-loopback-slice/phase-2-progress.md -t ARLS-2.1 -s completed
```

---

## Objective

`AgentsScreen` shows a cancel affordance for cancellable jobs that calls the existing
`useCancelAgentJob`, confirms first, and refetches on success. Roughly ARLS-02 (3 pts) in the PRD
backlog.

## Entry criteria

`depends_on: ["M1"]` in the plan's `wave_plan`. M2 edits `AgentsScreen.tsx` against M1's settled hook
shape — do not start until M1's `ARLS-1.G` gate has passed, to avoid two concurrent editors of the
same seam.

## Exit criteria (verbatim from plan)

- "useCancelAgentJob has a real caller; confirm-then-cancel and failure paths both tested"

## Gate lens

`validator` only — no `gate_lens_reason` (single-lens milestone). Per plan `wave_plan.phases[1]` and
`routing_constraints`: "Cancel affordance UI (M2) is offload-eligible." Capability bar: workhorse.

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| M2 cancel paths | `cd frontend/runs-viewer && npx vitest run src/test/agents-` | success and failure cancel tests pass |
| M2 hook has a caller | `rg -n 'useCancelAgentJob' frontend/runs-viewer/src --glob '!hooks/**'` | ≥1 hit outside the hooks dir |
| Typecheck (all) | `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit` | no output (bare `npx tsc --noEmit` is a NO-OP here — must pass `-p`) |
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 (~4 known-failing) |

## Sequencing note (load-bearing, from plan)

M1 → M2 → M3, in this order, deliberately: M2 edits `AgentsScreen.tsx` against M1's settled hook
shape (avoiding two concurrent editors of the same seam), and M3 asserts against both M1's reader and
M2's cancel call, so it can only cover them once they exist.

## Named risks relevant to this milestone (from plan)

- **Cancel confirm step is skipped or fails to prevent accidental cancellation** (Low impact, Low
  likelihood per PRD risk table) — FR-6 makes the confirm step a Must; validate with an RTL test
  asserting no `cancelAgentJob()` call fires without confirm interaction (ARLS-2.2).
- **Static-mode behavior regresses as a side effect of touching shared `client.ts` code** (High
  impact, Low likelihood) — NFR-4 requires `git diff` verification scoped to loopback-guarded
  branches, plus a full static-mode suite run with zero new failures.
- **Silent scope drift into Mode-D.** Mode-D is non-negotiable — auth · payments · migrations ·
  deletion · secrets · infra. Not expected to be adjacent for this milestone's UI-only scope, but the
  rule applies uniformly across the plan.

## Implementation Notes

Deviations and rationale go in
`.claude/worknotes/agent-research-loopback-slice/implementation-notes.md` (execution ledger), not here.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges,
recommendations for M3.
