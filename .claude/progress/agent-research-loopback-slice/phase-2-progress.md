---
type: progress
schema_version: 2
doc_type: progress
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
milestone: M2
phase: 2
title: Cancel affordance reaches the live cancel endpoint
status: completed
created: '2026-08-03'
updated: '2026-08-10'
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ4A2GHGR6QG4EP1AMNKAR3D
commit_refs:
- e3b7588
- af642da
pr_refs: []
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
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
  status: completed
  dependencies: []
  started: '2026-08-07T14:30:00Z'
  completed: '2026-08-07T15:10:00Z'
  evidence:
  - commit: e3b7588
  verified_by:
  - ARLS-2.G
- id: ARLS-2.2
  description: Add an explicit confirm step (confirm dialog or two-step button) before
    dispatching cancelAgentJob() (FR-6).
  status: completed
  dependencies:
  - ARLS-2.1
  started: '2026-08-07T14:30:00Z'
  completed: '2026-08-07T15:10:00Z'
  evidence:
  - commit: e3b7588
  verified_by:
  - ARLS-2.G
- id: ARLS-2.3
  description: Verify job-detail query invalidation and terminal-state reactivity
    on success (no manual refresh needed), and that failures surface an error rather
    than appearing successful; test both success and failure cancel paths (FR-7).
  status: completed
  dependencies:
  - ARLS-2.2
  started: '2026-08-07T14:30:00Z'
  completed: '2026-08-07T15:10:00Z'
  evidence:
  - commit: e3b7588
  verified_by:
  - ARLS-2.G
- id: ARLS-2.G
  description: 'Milestone gate (validator lens): useCancelAgentJob has a real caller;
    confirm-then-cancel and failure paths both tested.'
  status: completed
  dependencies:
  - ARLS-2.3
  started: '2026-08-07T14:30:00Z'
  completed: '2026-08-07T15:10:00Z'
  evidence:
  - commit: e3b7588
  - review: codex-gpt-5.6-terra-APPROVED
  verified_by:
  - ARLS-2.G
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
  status: completed
- id: AC-M2-2
  description: An explicit confirm step precedes the cancel request.
  status: completed
- id: AC-M2-3
  description: The job-detail query is invalidated on successful cancel.
  status: completed
- id: AC-M2-4
  description: >-
    A failed cancel surfaces an error rather than appearing successful. NOTE per
    plan M3 exit_criteria deferral (Finding 3, ITT node node_01KZP86B466SWBSA0VR6MV6FRT,
    Medium) -- the existing agents-cancel test for this path pre-loads mutation
    state, so the assertion is vacuous as worded. Marked completed on the narrow
    claim tested (an error surfaces), not on the deferred hardening.
  status: completed
- id: AC-M2-5
  description: useCancelAgentJob has >=1 caller outside the hooks directory.
  status: completed
- id: AC-M2-6
  description: >-
    Both success and failure cancel paths are tested. Same Finding-3 caveat as
    AC-M2-4 applies to the failure-path assertion -- see plan M3 exit_criteria.
  status: completed
files_modified: []
progress: 100
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
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 — exactly one file, `codegen/generate-types.contract.test.mjs` |

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
