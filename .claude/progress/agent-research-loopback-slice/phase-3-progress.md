---
type: progress
schema_version: 2
doc_type: progress
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
milestone: M3
phase: 3
title: Contract test exercises the real client with no hooks mocks
status: completed
created: '2026-08-03'
updated: '2026-08-10'
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ4A3H0R7KZT8WF6A7DG1VTG
commit_refs:
- 47f374b
- 87fde4a
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
- id: ARLS-3.1
  description: Add a test file exercising the real agentJobsClient and useAgentJobEvents
    (no @/hooks/useAgentJobs module mock), asserting all 6 routes' method + path
    + auth header against agent_jobs.py (FR-8).
  status: completed
  dependencies: []
  evidence:
  - commit: 47f374b
  note: Adds src/test/agents-client-contract.test.ts (329 lines); drives the real
    agentJobsClient functions and the real M1 SSE reader against an intercepted
    fetch, asserting method + pathname + Authorization for all six agent_jobs.py
    routes. No existing test or production file modified.
- id: ARLS-3.2
  description: Add the positive auth-failure mutation control — breaking one client
    path must make the contract test FAIL; revert and confirm `git status --porcelain`
    is empty (FR-9).
  status: completed
  dependencies:
  - ARLS-3.1
  evidence:
  - commit: 47f374b
  - commit: 87fde4a
  note: Two mutations proven non-vacuous and independently reverted -- breaking
    the artifacts pathname, and stripping buildEventsHeaders() from the SSE call
    (the shipped-401 defect itself). Re-proven against 87fde4a's final version.
- id: ARLS-3.3
  description: Add runtime-resolver vs. build-time-env auth-token precedence test
    cases, mirroring the FR-1 precedence contract (FR-10).
  status: completed
  dependencies:
  - ARLS-3.1
  note: 'NOT delivered by this milestone''s new file -- agents-client-contract.test.ts
    (47f374b) does not add precedence cases. Marked completed as redundant rather
    than missing: this precedence contract is already transitively covered by
    src/test/agents-sse-auth.test.ts:200-230 (M1''s SSE path -- "prefers the runtime
    resolver over the build-time env value" and "omits the Authorization header
    entirely when nothing resolves") and by src/test/p5-auth-header.test.ts (the
    shared client.ts buildAuthHeaders() precedence, covering both the local_static
    and Clerk resolver paths). No new test written for FR-10 under M3; the AC is
    satisfied by pre-existing coverage.'
- id: ARLS-3.G
  description: 'Milestone gate (validator lens): all 6 routes'' method + path +
    auth header asserted against agent_jobs.py; mutation check fails as designed;
    the 10 pre-existing agents-* files unchanged and passing; no new suite failures
    vs the baseline set; tree left clean.'
  status: completed
  dependencies:
  - ARLS-3.2
  - ARLS-3.3
  evidence:
  - commit: 47f374b
  - commit: 87fde4a
  - gate: validator APPROVED
  - gate: karen Tier-2 final-tree pass APPROVED (feature_end_gate)
  - test: 1136 passed; failing-file set unchanged from baseline ({codegen/generate-types.contract.test.mjs})
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
  status: completed
- id: AC-M3-2
  description: All 6 routes' method + path + auth header are asserted against
    agent_jobs.py.
  status: completed
- id: AC-M3-3
  description: Breaking one client path makes the contract test FAIL; reverting
    leaves `git status --porcelain` empty.
  status: completed
- id: AC-M3-4
  description: The 10 pre-existing agents-* files (9 hooks-mocking .tsx files plus
    the M1 non-mocking agents-sse-auth.test.ts) remain unchanged and passing.
  status: completed
- id: AC-M3-5
  description: No new suite failures vs. the baseline failing-file set -- exactly
    one file, codegen/generate-types.contract.test.mjs.
  status: completed
- id: AC-M3-6
  description: 'AC6 caveat (do not misdiagnose as a regression): the failing-file
    set on main is unchanged and stable across repeat runs (1136 passed). During
    development a worktree run showed one additional failure, provenance-correctness.test.ts
    -- a worktree data-plane phantom, because ancillary .claude/worktrees/* checkouts
    lack the private data-plane mount that supplies that test''s fixture report_draft.md.'
  status: completed
files_modified:
- frontend/runs-viewer/src/test/agents-client-contract.test.ts
progress: 100
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
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 — exactly one file, `codegen/generate-types.contract.test.mjs` |

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

**What was built.** `src/test/agents-client-contract.test.ts` (landed `47f374b`) drives the real
`agentJobsClient` functions and the real M1 SSE reader against an intercepted `fetch`, asserting
method + pathname + `Authorization` for all six `agent_jobs.py` routes (launch, get, artifacts,
cancel, accept, events/SSE). OQ-2 resolved as the default fetch-spy pattern (no MSW dependency
added) — the same pattern already proven in `p5-auth-header.test.ts` and M1's `agents-sse-auth.test.ts`
was sufficient. Non-vacuity proven by two independently-caught-and-reverted mutations: a broken
artifacts pathname, and stripping `buildEventsHeaders()` from the SSE call — the shipped-401 defect
itself. No existing test or production file modified.

**Fix (`87fde4a`).** The contract test's `setEnv()` helper stubbed three `import.meta.env` keys per
test but its `afterEach` restored only one, so `VITE_RUNS_FRONTEND_LOOPBACK_API="true"` leaked
forward across the shared vitest worker into later files, flipping `builder-screen.test.tsx` out of
its expected static mode. Fixed by switching to `vi.stubEnv`/`vi.unstubAllEnvs` plus a file-level
`afterAll` safety net. Failing-file set on `main` after this fix is unchanged and stable across
repeat runs: `{codegen/generate-types.contract.test.mjs}`, 1136 passed.

**ARLS-3.3 (runtime-resolver vs. build-time-env precedence, FR-10) was not written as new coverage
in this file.** It is marked completed as redundant rather than missing: the precedence contract is
already exercised by `agents-sse-auth.test.ts:200-230` (SSE path) and `p5-auth-header.test.ts` (the
shared `client.ts` `buildAuthHeaders()` path).

**Deferrals.** Findings 3 and 4 from the M2 review, plus M1's open `enabled` false→true coverage
gap, are explicitly NOT closed by this milestone — each is recorded as its own annotated deferral in
the plan's M3 `exit_criteria`, naming its ITT node (`node_01KZP86B466SWBSA0VR6MV6FRT`,
`node_01KZP87QAJ7AKGYDP79F69VJ3X`, `node_01KZP87QHPBBWYPTTB1MK80QH6`). The confirm-row double-click
geometry fragility remains open at `node_01KZET6WBDPMZTT4Z5S3X88AYA`.

**Gate.** Validator lens APPROVED; the single Tier-2 `karen` final-tree pass (this plan's
`feature_end_gate`) also APPROVED, closing the feature.
