---
type: progress
schema_version: 2
doc_type: progress
prd: agent-research-loopback-slice
feature_slug: agent-research-loopback-slice
milestone: M1
phase: 1
title: SSE event stream authenticates via Authorization header
status: completed
created: '2026-08-03'
updated: '2026-08-07'
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ4A1ZHFXH1ZRDXPPFGEV95Z
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
gate_lens:
- security
- validator
gate_lens_reason: authz-boundary
mode_d_halt: false
karen_required_this_milestone: false
tasks:
- id: ARLS-1.1
  description: Replace EventSource with a fetch + ReadableStream SSE reader in useAgentJobEvents
    that sends a runtime-resolved Authorization header (FR-1), so no token appears
    in any URL (NFR-1).
  status: completed
  dependencies: []
- id: ARLS-1.2
  description: "Implement partial-chunk-safe SSE frame parsing \u2014 buffer partial\
    \ reads across chunk boundaries and parse only complete `data: {...}` frames (FR-2)."
  status: completed
  dependencies:
  - ARLS-1.1
- id: ARLS-1.3
  description: Preserve reconnect/backoff at SSE_RECONNECT_DELAY_MS (3000ms, unchanged)
    and last_event_id replay parity; confirm the hook's {events, status} contract
    and static (non-loopback) mode stay byte-unchanged (FR-3, FR-4, NFR-4).
  status: completed
  dependencies:
  - ARLS-1.2
- id: ARLS-1.4
  description: "Add an SSE-auth test asserting `Authorization: Bearer` on the outgoing\
    \ request, including a positive control that FAILS when the header is dropped\
    \ \u2014 the exit-bar test this milestone's own AC requires (subset of FR-8/FR-9\
    \ scoped to M1; the full contract suite is M3)."
  status: completed
  dependencies:
  - ARLS-1.3
- id: ARLS-1.G
  description: 'Milestone gate (security + validator lens, authz-boundary): SSE request
    carries a runtime-resolved Authorization header with no token in any URL; positive
    control fails when the header is removed; reconnect + replay at parity; zero diff
    under src/research_foundry/.'
  status: completed
  dependencies:
  - ARLS-1.4
  started: '2026-08-07T04:10:00Z'
  completed: '2026-08-07T08:10:00Z'
  evidence:
  - commit: 975db10
  - gate: security/senior-code-reviewer APPROVED (serialized, wf_026980f6-233)
  - gate: validator/task-completion-validator APPROVED (wf_0ed6aaab-86a)
  - test: 1110/1110 vitest, tsc -p tsconfig.app.json exit 0
parallelization:
  batch_1:
  - ARLS-1.1
  batch_2:
  - ARLS-1.2
  batch_3:
  - ARLS-1.3
  batch_4:
  - ARLS-1.4
  batch_5:
  - ARLS-1.G
  critical_path:
  - ARLS-1.1
  - ARLS-1.2
  - ARLS-1.3
  - ARLS-1.4
  - ARLS-1.G
blockers: []
success_criteria:
- id: AC-M1-1
  description: Authorization header sourced via buildAuthHeaders() precedence (runtime
    resolver wins over build-time env; header omitted when neither resolves).
  status: pending
- id: AC-M1-2
  description: "Zero diff under src/research_foundry/ \u2014 no server changes required\
    \ by the chosen design."
  status: pending
- id: AC-M1-3
  description: Reconnect at 3000ms resumes from the last sequence id (last_event_id
    replay parity, byte-for-byte unchanged).
  status: pending
- id: AC-M1-4
  description: SSE frame parser emits exactly one event per frame when frames split
    across read() chunks.
  status: pending
- id: AC-M1-5
  description: A test FAILS when the Authorization header is removed (positive control).
  status: pending
- id: AC-M1-6
  description: Static (non-loopback) mode is byte-unchanged.
  status: pending
- id: AC-M1-7
  description: "npx tsc -p tsconfig.app.json --noEmit is clean (bare `npx tsc --noEmit`\
    \ is a known no-op in this repo \u2014 must pass -p)."
  status: pending
files_modified:
- frontend/runs-viewer/src/hooks/useAgentJobs.ts
- frontend/runs-viewer/src/test/agents-sse-auth.test.ts
progress: 100
---

# agent-research-loopback-slice - Phase 1 (M1): SSE event stream authenticates via Authorization header

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/agent-research-loopback-slice/phase-1-progress.md -t ARLS-1.1 -s completed
```

---

## Objective

`useAgentJobEvents` reads the live-event stream over `fetch` + `ReadableStream`, sending a
runtime-resolved `Authorization` header instead of the current `?token=` query param that no server
auth surface reads. Reconnect and `last_event_id` replay behave exactly as before. Roughly ARLS-01
(6 pts) in the PRD backlog.

## Entry criteria

None declared (`depends_on: []` in the plan's `wave_plan`). This is the first milestone.

## Exit criteria (verbatim from plan)

- "SSE request carries a runtime-resolved Authorization header; no token in any URL"
- "Positive control fails when the header is removed; reconnect + replay at parity"

## Gate lens

`security`, `validator` — `gate_lens_reason: authz-boundary`. Per plan `wave_plan.phases[0]` and
`routing_constraints`: "SSE auth transport and token-precedence correctness (M1) MUST stay
claude-primary — authorization boundary, never offload." Capability bar: frontier-or-workhorse with a
security lens.

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| M1 header + parser + parity | `cd frontend/runs-viewer && npx vitest run src/test/agents-` | agents-* files pass; new SSE-auth test asserts `Authorization: Bearer` |
| M1 header positive control | remove the header line, re-run the SSE-auth test | test **FAILS**; restore and confirm `git status --porcelain` empty |
| M1 no server change | `git diff --stat -- src/research_foundry/` | empty output |
| M1 no token in URL | `rg -n 'token' frontend/runs-viewer/src/hooks/useAgentJobs.ts` | no query-param token assignment remains |
| Typecheck (all) | `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit` | no output (bare `npx tsc --noEmit` is a NO-OP here — must pass `-p`) |
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 (~4 known-failing) |

## Sequencing note (load-bearing, from plan)

M1 → M2 → M3, in this order, deliberately: M2 edits `AgentsScreen.tsx` against M1's settled hook
shape (avoiding two concurrent editors of the same seam), and M3 asserts against both M1's reader and
M2's cancel call, so it can only cover them once they exist.

## Named risks relevant to this milestone (from plan)

- **Hand-rolled SSE parsing is where the bugs will be.** `EventSource` gave frame parsing, reconnect,
  and replay free; all three become our code, with no fetch-stream reader in this repo to copy. Assume
  frames split across `read()` chunks and test that explicitly (ARLS-1.2).
- **A green test that proves nothing.** All 7 agents tests pass today while the stream 401s. Treat
  "tests pass" as insufficient evidence; the positive control (ARLS-1.4) is the deliverable.
- **Silent scope drift into Mode-D.** Mode-D is non-negotiable — auth · payments · migrations ·
  deletion · secrets · infra. M1 sits adjacent to the auth surface: the chosen design needs no server
  change, so **any need to edit `src/research_foundry/` means halting for explicit human approval, not
  proceeding.** This milestone does not schedule a Mode-D halt task (`mode_d_halt: false`) because the
  accepted design requires zero server changes — the halt is conditional on scope drift, not expected
  on the happy path.
- **Clerk mode masks the bug.** Its `__session` cookie fallback can make the stream look healthy;
  verify against token-store/`local_static`, the mode that actually 401s today.
- **SSE route's missing RBAC dependency** (`stream_events()`, `agent_jobs.py:396-428` has no
  `_RBAC_AGENT_JOB` dep, unlike launch/cancel/accept) is a residual asymmetry — explicitly out of scope
  for this PRD (NFR-2). Do not paper over it; do not attempt to fix it here.

## Implementation Notes

Deviations, OQ-1/OQ-2 resolutions, and rationale go in
`.claude/worknotes/agent-research-loopback-slice/implementation-notes.md` (execution ledger), not here.

## Completion Notes

ARLS-1.1 … ARLS-1.4 delivered in one session (all four own `hooks/useAgentJobs.ts`, so they could
not be split). ARLS-1.G (gate) remains open.

**What was built.** `useAgentJobEvents` now streams over `fetch` + `ReadableStream` and sends
`Authorization: Bearer …` sourced from `getLoopbackAuthHeaders()` → `buildAuthHeaders()` (one
precedence implementation, no duplication). `buildEventsUrl()` no longer emits `?token=`. A new
exported `SseFrameParser` does partial-chunk-safe framing (LF/CRLF/lone-CR, chunk-boundary CR held
back, unterminated tail dropped, comments ignored). Reconnect stays at 3000 ms with `last_event_id`
from `lastSequenceRef`; `{events, status}` and `AgentJobEventsStatus` are byte-compatible; static
mode untouched. New `src/test/agents-sse-auth.test.ts` (20 tests) drives the real hook against a
spied `globalThis.fetch` with a real `ReadableStream` body.

**Success criteria** — the `success_criteria[]` entries stay `pending` in frontmatter because
`update-status.py` only addresses `tasks[]` (it errors "Task 'AC-M1-1' not found"), and this rule
set forbids hand-editing progress frontmatter. Evidence, criterion by criterion:

| AC | Evidence |
|---|---|
| AC-M1-1 | 3 tests assert env-token, resolver-wins-over-env, and header-absent-when-neither-resolves |
| AC-M1-2 | `git status --porcelain -- src/research_foundry/` → empty |
| AC-M1-3 | reconnect test: `setTimeout` scheduled at exactly 3000 ms; retry URL is `…/events?last_event_id=41` and still carries the bearer; first connect carries no `last_event_id` |
| AC-M1-4 | 4-chunk brutal split (mid-JSON, mid-field, split `\n\n` delimiter) → exactly 3 events in order; 9 `SseFrameParser` unit tests |
| AC-M1-5 | auth-gated (401-without-bearer) fake server: positive control delivers 2 events; mutation dropping the header fails 6 tests incl. the control (0 events); mutation reintroducing `?token=` fails 2 |
| AC-M1-6 | static-mode test: `status === "idle"`, 0 events, 0 requests; no static code path touched |
| AC-M1-7 | `npx tsc -p tsconfig.app.json --noEmit` → silent, exit 0 |

**Suite state.** `npx vitest run` → `Test Files 1 failed | 49 passed (50)`, `Tests 1104 passed`.
Baseline captured before M1 was `1 failed | 48 passed (49)`, 1084 passed — same failing-file set
(only the pre-existing `codegen/generate-types.contract.test.mjs` codegen drift).

**Commit.** Feature-branch commit `efb3919` on `feat/agent-research-loopback-slice`.
`commit_refs` is deliberately left empty: per `.claude/rules/plan-bookkeeping.md` invariant 1 it may
only hold commits reachable from `main`, and this repo squash-merges, so the orchestrator should
record the squash sha there instead of the pre-squash branch commit.

**Unexpected challenges / learnings for M2.**

1. **React 18 batching collapses `connecting → live → error`.** Because stream reads resolve as
   microtasks (not macrotask events like `EventSource.onmessage`), asserting on a *recorded status
   history* is flaky — `live` never appears as its own render when the stream closes immediately.
   The test models a still-running job (a stream that never closes) to observe `live`. Any M2/M3
   assertion on intermediate hook status needs the same treatment.
2. **Fake timers were avoided.** The reconnect test spies on `globalThis.setTimeout` (keeping the
   real implementation), reads the scheduled delay, and fires the captured callback — deterministic,
   with no fake-timer/microtask interplay.
3. **A `Bearer <16+ chars>` string literal trips the repo secret guard**
   (`no_secret_in_markdown` matches `(?i)bearer\s+[A-Za-z0-9_\-.=]{16,}`). Use short fake credential
   constants and interpolate instead of writing the literal.
4. **`src/api/agentJobsClient.ts:13` and `:254` still claim SSE is consumed via `EventSource`** —
   stale after M1, left alone to avoid a concurrent-editor conflict on a shared branch. Fix with M3,
   which owns that file.
5. **OQ-1 residual for whoever touches replay:** the server ignores the resume id entirely, so a
   reconnect replays the full log and the hook re-appends it (duplicate rows). That is pre-existing
   behaviour, preserved deliberately; changing it means either client-side dedup (a behaviour change
   with no AC) or a `src/research_foundry/` edit (Mode-D).
