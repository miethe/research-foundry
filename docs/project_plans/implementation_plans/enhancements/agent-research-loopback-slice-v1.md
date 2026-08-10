---
it_schema: 1
feature_slug: agent-research-loopback-slice
title: "Agent-research loopback slice — hardening — implementation plan"
doc_type: implementation_plan
status: completed
# M1 LANDED on main as 755e7d3 (squash of efb3919/f641c3c/957cc93/975db10/6fa2401),
# both gate lenses APPROVED. M2 LANDED on main as e3b7588, findings 1+2 of the parked-branch
# CHANGES_REQUESTED review closed and re-gated APPROVED by codex/gpt-5.6-terra (the mandated
# single validator lens). M3 LANDED on main as 47f374b (contract test) + 87fde4a (env-leak
# fix); the validator lens and the Tier-2 karen final-tree pass both APPROVED. Findings 3+4 and
# M1's open coverage gap were NOT silently folded into M3's close — each is recorded as its own
# annotated deferral in M3's exit_criteria below, naming its ITT node and gate.
commit_refs:
  - 755e7d3   # M1 squash to main (patch-identical to the superseded pre-squash ref 3276bfa)
  - 116295c   # M1 landing pointer + M2/M3 parked (patch-identical to superseded ref c2b86fe)
  - e3b7588   # M2 squash to main (patch-identical to the superseded pre-squash ref 161cf2f)
  - af642da   # M2 tracker close (patch-identical to superseded ref 238a7f9)
  - 47f374b   # M3 contract test
  - 87fde4a   # M3 env-leak fix
tier: 2
priority: P1
points: 13
risk_level: medium
context_class: C2          # M1/M3 cross-module in one repo; M2 single-module (C1)
feature_end_gate: karen    # Tier 2 mandate: ONE karen final-tree pass after M3, before close.
                           # NOT per-milestone — context_class C2/C1 does not earn that (see
                           # gate-risk-classes.md § Karen placement), which is why every
                           # phase progress file carries karen_required_this_milestone: false.
created: 2026-08-03
updated: 2026-08-10
changelog_required: true
prd_ref: docs/project_plans/PRDs/enhancements/agent-research-loopback-slice-v1.md
plan_ref: null
findings_doc_ref: null
deferred_items_spec_refs: []
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
itt_node_id: node_01KZ49ZWATPNKDNGF3APTBEFQP
related_documents:
  - docs/project_plans/feature_contracts/enhancements/runs-viewer-builder-live-claim-previews.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
acceptance_criteria:   # terse by design — the AC -> command -> evidence matrix below is the detail
  # "at parity" SUPERSEDED for M1 (landed 755e7d3): byte-parity with the retired EventSource meant
  # preserving a duplication bug (gate finding DUP-01). Read as: reconnect delay and last_event_id
  # preserved, replayed history de-duplicated. Rationale in the branch execution ledger.
  - "SSE authenticates by header from the runtime resolver, zero diff under src/research_foundry/, reconnect+replay at parity"
  - "Positive control fails when the Authorization header is dropped; contract test covers the real client with no hooks mocks"
  - "A job is cancellable from the UI; static (non-loopback) mode byte-unchanged"
open_questions:
  - id: OQ-1
    question: "Does stream_events() accept the resume id as a Last-Event-ID header, or only as the existing query param?"
    decision_rule: "Executor resolves from code truth at src/research_foundry/api/routers/agent_jobs.py:396-428 and sends whichever the server already reads. Implementation detail — do NOT halt on it. Only the *token* must move to a header; the resume id is not a credential and may stay a query param."
  - id: OQ-2
    question: "Is a globalThis.fetch spy sufficient for M3, or does MSW earn a new dependency?"
    decision_rule: "Default to the fetch-spy pattern already proven in src/test/p5-auth-header.test.ts (passes 14/14). Adopt MSW only if the spy cannot express SSE streaming; record the choice in the worknote either way."
decisions:
  - decision: "Carry the SSE token in an Authorization header via fetch + ReadableStream; retire EventSource for this stream."
    rationale: "Query-param token auth is not a supported server path anywhere — auth.py:200-226/:239-275, local_static.py:125, clerk.py:294-307 all read the Authorization header only (Clerk adds a __session cookie fallback, never a query param). The header design needs ZERO server changes and keeps a bearer credential out of URLs/logs/history. Rejected: runtime-resolve the token but keep the query param — needs new query-param bearer auth in the middleware for no benefit."
    status: accepted
  - decision: "Keep the 7 existing hooks-mocking agents-* tests; add a layer beneath them."
    rationale: "They validly cover component behavior. The gap is that NOTHING covered the client-server contract, which is why the 401 shipped. Add the missing layer; don't trade one blind spot for another."
    status: accepted
  - decision: "Static (non-loopback) mode is untouched."
    rationale: "A supported product surface, not dead code — bootstrap-agentic-node.sh:1836-1844 deliberately falls back to a tokenless static build when RF_TOKEN_AGENT is absent."
    status: accepted
routing_constraints:
  - "SSE auth transport and token-precedence correctness (M1) MUST stay claude-primary — authorization boundary, never offload"
  - "Any change under src/research_foundry/ MUST halt for explicit human approval (Mode-D auth surface); the chosen design requires none"
  - "SSE frame-parser implementation and its unit tests (M1) are offload-eligible once the header contract is settled"
  - "Cancel affordance UI (M2) is offload-eligible"
  - "M3 harness scaffolding is offload-eligible; the positive-control and mutation-check assertion design MUST stay claude-primary — a vacuous control is worse than none"
  - "Capability bar: M1 frontier-or-workhorse with a security lens; M2/M3 workhorse"
wave_plan:
  waves: [["M1"], ["M2"], ["M3"]]
  phases:
    - id: M1
      title: "SSE event stream authenticates via Authorization header"
      depends_on: []
      itt_node_id: node_01KZ4A1ZHFXH1ZRDXPPFGEV95Z
      gate_lens: [security, validator]
      gate_lens_reason: authz-boundary
      exit_criteria:   # MET — landed on main as 755e7d3; both gate lenses APPROVED
        - "SSE request carries a runtime-resolved Authorization header; no token in any URL"
        # "replay at parity" was deliberately SUPERSEDED — see gate finding DUP-01. Parity with the
        # retired EventSource meant re-appending the whole event history on every reconnect. The
        # client now de-duplicates by sequence; reconnect delay (3000ms) and last_event_id are
        # unchanged. Two further gate findings closed in the same milestone: CAST-01 (payload-less
        # frame crashed the panel) and JOBID-LEAK-01 (the DUP-01 guard leaked across a jobId change).
        - "Positive control fails when the header is removed; reconnect + replay at parity"
    - id: M2
      title: "Cancel affordance reaches the live cancel endpoint"
      depends_on: ["M1"]
      itt_node_id: node_01KZ4A2GHGR6QG4EP1AMNKAR3D
      gate_lens: [validator]
      exit_criteria:   # MET — landed on main as e3b7588; validator lens (codex) APPROVED
        # Findings 1+2 of the parked-branch review closed by a call-site design change (key the
        # job-scoped subtree by jobId; share the live job query to the event panel). Findings 3+4
        # (assertion-shaped pre-existing cancel tests + partial-real-module mock repair) explicitly
        # deferred to M3. The confirm-row double-click fragility remains OPEN — the review's claim
        # that keying closes it was verified WRONG (keying resets state across jobs, not cursor
        # geometry within one job); tracked separately.
        - "useCancelAgentJob has a real caller; confirm-then-cancel and failure paths both tested"
    - id: M3
      title: "Contract test exercises the real client with no hooks mocks"
      depends_on: ["M2"]
      itt_node_id: node_01KZ4A3H0R7KZT8WF6A7DG1VTG
      gate_lens: [validator]
      exit_criteria:   # MET — landed on main as 47f374b (contract test) + 87fde4a (env-leak fix);
                        # validator lens and the Tier-2 karen final-tree pass both APPROVED.
        - "All 6 routes' method + path + auth header asserted against agent_jobs.py; mutation check fails as designed"
        - "FEATURE-END GATE: the single Tier-2 karen final-tree pass runs after this milestone and APPROVES before the feature closes"
        - "DEFERRED, Medium — Finding 3: agents-cancel pre-loads mutation state, so AC-M2-4/AC-M2-6 are vacuous as worded. Gate = resolution of ITT node node_01KZP86B466SWBSA0VR6MV6FRT; this milestone's completion does not close it."
        - "DEFERRED, Low — Finding 4: no partial-real-module mocks; two missing exports (useCancelAgentJob, useAgentJob). Cannot be closed by a test-only diff. Gate = resolution of ITT node node_01KZP87QAJ7AKGYDP79F69VJ3X."
        - "DEFERRED, Low — M1 coverage gap: `enabled` false->true with an unchanged `jobId` is untested; the guard exists and works at useAgentJobs.ts:347-352. Gate = resolution of ITT node node_01KZP87QHPBBWYPTTB1MK80QH6."
        - "DEFERRED, not_started — confirm-row double-click geometry fragility, filed at ITT node node_01KZET6WBDPMZTT4Z5S3X88AYA. Gate = resolution of that node."
---

# Implementation Plan — Agent-research loopback slice (hardening)

The `isAgentsLoopbackEnabled` slice is feature-complete — all 6 `agentJobsClient.ts` calls have
exact backend counterparts — but its live-event stream does not authenticate: the token rides a
`?token=` query param that no server auth surface reads, so under token-store/`local_static` auth
the `EventSource` 401s and the event panel silently shows nothing. When this is done the stream
authenticates by header, a job can be cancelled from the UI, and a contract test covers the real
client so this class of defect fails a test instead of shipping.

## Scope boundary

**In:** `frontend/runs-viewer/src/hooks/useAgentJobs.ts`, `screens/AgentsScreen.tsx`,
`test/setup.ts`, the `agents-*` test files, and one new contract-test file.

**Out (stated, not silently dropped):**
- **Agent-job workspace/RBAC scoping** (`agentJobsClient.ts:93-94`) — blocked behind the formal DI-1
  re-audit + Mode-D sign-off gate on ITT node `node_01KXRSGNM4E5YYTP13TY7E4KEA`. A real gate, not a
  deferral of convenience.
- **Adding query-param bearer auth** — rejected decision above, not an oversight.
- **The static-mode fallback** — supported surface; deleting it breaks the node's tokenless build.
- **`stream_events()`'s missing `_RBAC_AGENT_JOB` dep** (`agent_jobs.py:396-428`, unlike
  launch/cancel/accept). Found while scoping; a server-side authz change is Mode-D and belongs with
  the DI-1 work, not smuggled into a frontend transport fix.

## Rubric — what "good" looks like

The SSE reader is judged on **parity and provability**, not elegance. Parity: an operator cannot tell
the transport changed — same reconnect delay, same replay-after-drop, same ordering. Provability:
every claim has a control that fails when the claim is false. The trap is a test asserting the header
against a mock that would pass either way; the mutation and header-removal checks exist because
assertion-shaped tests are exactly what let this defect through. Prefer the smallest change that
makes the failure mode impossible to reintroduce silently over refactoring the agents surface.

## Named risks

- **Hand-rolled SSE parsing is where the bugs will be.** `EventSource` gave frame parsing, reconnect,
  and replay free; all three become our code, with no fetch-stream reader in this repo to copy.
  Assume frames split across `read()` chunks and test that explicitly.
- **A green test that proves nothing.** All 7 agents tests pass today while the stream 401s. Treat
  "tests pass" as insufficient evidence; the positive control is the deliverable.
- **Silent scope drift into Mode-D.** Any edit under `src/research_foundry/` means the chosen design
  was abandoned — stop and escalate rather than proceed.
- **Clerk mode masks the bug.** Its `__session` cookie fallback can make the stream look healthy;
  verify against token-store/`local_static`, the mode that actually 401s.

## References

- `hooks/useAgentJobs.ts:115-127` (`buildEventsUrl`), `:142-219` (`useAgentJobEvents`), `:129`
  (reconnect delay), `:81` (`useCancelAgentJob`) — all under `frontend/runs-viewer/src/`
- `api/client.ts:114-123` (`buildAuthHeaders` precedence), `:98-100` (`setAuthTokenResolver`)
- `src/research_foundry/api/routers/agent_jobs.py:396-428` (SSE), `:436` (cancel);
  `api/middleware/auth.py:200-226`, `:239-275` (header-only auth)
- `src/test/p5-auth-header.test.ts` — non-hooks-mocking precedent to imitate;
  `src/test/setup.ts:115` — `MockEventSource` polyfill M1 replaces

## Milestones

### M1 — The live-event stream authenticates

`useAgentJobEvents` reads the stream over `fetch` + `ReadableStream`, sending a runtime-resolved
`Authorization` header; no token appears in any URL. Reconnect and replay behave as before.

**AC:** header sourced per `buildAuthHeaders()` precedence (runtime resolver → build-time env → none);
zero diff under `src/research_foundry/`; reconnect at 3000ms resuming from the last sequence id;
parser emits one event per frame when frames split across chunks; **a test fails when the header is
removed**; static mode byte-unchanged; `tsc -p tsconfig.app.json --noEmit` clean.

### M2 — A running job can be stopped

`AgentsScreen` shows a cancel affordance for cancellable jobs that calls the existing
`useCancelAgentJob`, confirms first, and refetches on success.

**AC:** affordance present only for cancellable states; explicit confirmation before the request;
job query invalidated on success; failures surface an error rather than looking successful;
`useCancelAgentJob` has ≥1 caller; both success and failure paths tested.

### M3 — The contract is covered without hooks mocks

A test drives the real `agentJobsClient` (and the M1 reader) against an intercepted transport, so
client/server drift fails a test rather than only showing up in `openapi.json` diffs.

**AC:** ≥1 file exercises `agentJobsClient.ts` without mocking `@/hooks/useAgentJobs`; all 6 routes'
method + path + auth header asserted against `agent_jobs.py`; **breaking one path makes it fail**,
then tree left clean; the 10 pre-existing `agents-*` files (9 hooks-mocking `.tsx` files plus the
M1 non-mocking `agents-sse-auth.test.ts`) unchanged and passing; no new suite failures vs the
baseline **set** — exactly one file, `codegen/generate-types.contract.test.mjs`.

**Landed as** `47f374b` (adds `src/test/agents-client-contract.test.ts`, the contract test) +
`87fde4a` (fix: the contract test's `import.meta.env` stubs leaked forward into later files sharing
the same vitest worker — switched to `vi.stubEnv`/`vi.unstubAllEnvs`). Verified: neither commit
touches any existing test or production file; both mutations (broken artifacts pathname, stripped
SSE auth header) independently caught by the test and reverted; `git status --porcelain` empty
after revert. **AC6 caveat:** the failing-file set on `main` is unchanged and stable across repeat
runs ({`codegen/generate-types.contract.test.mjs`}, 1136 passed). During development a worktree run
showed one additional failure, `provenance-correctness.test.ts` — this was never a regression: it
is a worktree data-plane phantom, because ancillary `.claude/worktrees/*` checkouts lack the private
data-plane mount that supplies that test's fixture `report_draft.md`. Do not misdiagnose a future
recurrence of this pattern as a shipped regression.

## AC -> command -> evidence

| AC | Command | Evidence of pass |
|---|---|---|
| M1 header + parser + parity | `cd frontend/runs-viewer && npx vitest run src/test/agents-` | agents-* files pass; new SSE-auth test asserts `Authorization: Bearer` |
| M1 header positive control | remove the header line, re-run the SSE-auth test | test **FAILS**; restore and confirm `git status --porcelain` empty |
| M1 no server change | `git diff --stat -- src/research_foundry/` | empty output |
| M1 no token in URL | `rg -n 'token' frontend/runs-viewer/src/hooks/useAgentJobs.ts` | no query-param token assignment remains |
| M2 cancel paths | `cd frontend/runs-viewer && npx vitest run src/test/agents-` | success and failure cancel tests pass |
| M2 hook has a caller | `rg -n 'useCancelAgentJob' frontend/runs-viewer/src --glob '!hooks/**'` | ≥1 hit outside the hooks dir |
| M3 non-vacuous contract test | break one client path, re-run the contract test | test **FAILS**; revert; `git status --porcelain` empty |
| Typecheck (all) | `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit` | no output (bare `npx tsc --noEmit` is a NO-OP here — must pass `-p`) |
| No new suite failures | `cd frontend/runs-viewer && npx vitest run` | failing-file **set** equals the baseline set captured before M1 — exactly one file, `codegen/generate-types.contract.test.mjs` |

## Sequencing (load-bearing)

M1 → M2 → M3, and the order matters: M2 edits `AgentsScreen.tsx` against M1's settled hook shape
(avoiding two concurrent editors of the same seam), and M3 asserts against both the M1 reader and
the M2 cancel call, so it can only cover them once they exist.

## Execution ledger

Deviations and conservative choices are logged with rationale to
`.claude/worknotes/agent-research-loopback-slice/implementation-notes.md`, reviewed at each milestone
boundary rather than halted on. **Blockers still stop**; beyond those, mid-milestone halts are only
for destructive action, real scope change, or operator-only input.

**Mode-D is non-negotiable** — **auth** · payments · migrations · deletion · secrets · infra. **M1
sits adjacent to the auth surface**: the chosen design needs no server change, so any need to edit
`src/research_foundry/` means halting for explicit human approval, not proceeding.
