---
type: progress
schema_version: 2
doc_type: progress
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
milestone: M3
phase: 3
title: Contract test exercises the real client with no hooks mocks
status: pending
created: '2026-08-03'
updated: '2026-08-03'
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ4A3H0R7KZT8WF6A7DG1VTG
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
- id: ARLS-3.1
  description: Add a test file exercising the real agentJobsClient and useAgentJobEvents
    (no @/hooks/useAgentJobs module mock), asserting all 6 routes' method + path
    + auth header against agent_jobs.py (FR-8).
  status: pending
  dependencies: []
- id: ARLS-3.2
  description: Add the positive auth-failure mutation control — breaking one client
    path must make the contract test FAIL; revert and confirm `git status --porcelain`
    is empty (FR-9).
  status: pending
  dependencies:
  - ARLS-3.1
- id: ARLS-3.3
  description: Add runtime-resolver vs. build-time-env auth-token precedence test
    cases, mirroring the FR-1 precedence contract (FR-10).
  status: pending
  dependencies:
  - ARLS-3.1
- id: ARLS-3.G
  description: 'Milestone gate (validator lens): all 6 routes'' method + path +
    auth header asserted against agent_jobs.py; mutation check fails as designed;
    the 7 pre-existing tests unchanged and passing; no new suite failures vs the
    baseline set; tree left clean.'
  status: pending
  dependencies:
  - ARLS-3.2
  - ARLS-3.3
parallelization:
  batch_1:
  - ARLS-3.1
  batch_2:
  - ARLS-3.2
  - ARLS-3.3
  batch_3:
  - ARLS-3.G
  critical_path:
  - ARLS-3.1
  - ARLS-3.2
  - ARLS-3.G
blockers: []
success_criteria:
- id: AC-M3-1
  description: '>=1 test file exercises agentJobsClient.ts without mocking @/hooks/useAgentJobs.'
  status: pending
- id: AC-M3-2
  description: All 6 routes' method + path + auth header are asserted against
    agent_jobs.py.
  status: pending
- id: AC-M3-3
  description: Breaking one client path makes the contract test FAIL; reverting
    leaves `git status --porcelain` empty.
  status: pending
- id: AC-M3-4
  description: The 7 pre-existing agents-*.test.tsx tests remain unchanged and
    passing.
  status: pending
- id: AC-M3-5
  description: No new suite failures vs. the baseline failing-file set (~4 known-failing).
  status: pending
files_modified: []
progress: 0
---

# agent-research-loopback-slice - Phase 3 (M3): Contract test exercises the real client with no hooks mocks

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/agent-research-loopback-slice/phase-3-progress.md -t ARLS-3.1 -s completed
```

---

## Objective

A test drives the real `agentJobsClient` (and the M1 reader) against an intercepted transport, so
client/server drift fails a test rather than only showing up in `openapi.json` diffs. Roughly ARLS-03
(4 pts) in the PRD backlog.

## Entry criteria

`depends_on: ["M2"]` in the plan's `wave_plan`. M3 asserts against both M1's SSE reader and M2's
cancel call, so it can only cover them once both exist — do not start until M2's `ARLS-2.G` gate has
passed.

## Exit criteria (verbatim from plan)

- "All 6 routes' method + path + auth header asserted against agent_jobs.py; mutation check fails as
  designed"

## Gate lens

`validator` only — no `gate_lens_reason` (single-lens milestone). Per plan `routing_constraints`: "M3
harness scaffolding is offload-eligible; the positive-control and mutation-check assertion design MUST
stay claude-primary — a vacuous control is worse than none." Capability bar: workhorse.

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| M3 non-vacuous contract test | break one client path, re-run the contract test | test **FAILS**; revert; `git status --porcelain` empty |
| Typecheck (all) | `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit` | no output (bare `npx tsc --noEmit` is a NO-OP here — must pass `-p`) |
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 (~4 known-failing) |

## Sequencing note (load-bearing, from plan)

M1 → M2 → M3, in this order, deliberately: M3 asserts against both the M1 reader and the M2 cancel
call, so it can only cover them once they exist — this is the terminal milestone.

## Named risks relevant to this milestone (from plan)

- **A green test that proves nothing** is the exact defect class this milestone exists to close — the
  trap is a test asserting the header against a mock that would pass either way. The mutation check
  (ARLS-3.2) and header-removal check (M1's `ARLS-1.4`) exist because assertion-shaped tests are what
  let the original SSE-auth defect through.
- **Vacuous control risk on the positive-control design.** Per `routing_constraints`, the
  positive-control and mutation-check assertion design must stay claude-primary even though harness
  scaffolding is offload-eligible — a vacuous control is worse than none.
- **Silent scope drift into Mode-D.** Mode-D is non-negotiable — auth · payments · migrations ·
  deletion · secrets · infra. Not expected to be adjacent for this milestone's test-only scope, but
  the rule applies uniformly across the plan.

## Implementation Notes

Deviations and rationale go in
`.claude/worknotes/agent-research-loopback-slice/implementation-notes.md` (execution ledger), not here.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges, and
whether OQ-2 (fetch-spy vs. MSW) was resolved as the default fetch-spy pattern or required adopting MSW.
