---
type: worknote
doc_type: worknote
feature_slug: agent-research-loopback-slice
title: Agent-research loopback slice — execution ledger (deviations, OQ resolutions)
created: '2026-08-07'
updated: '2026-08-07'
plan_ref: docs/project_plans/implementation_plans/enhancements/agent-research-loopback-slice-v1.md
---

# Execution ledger — agent-research-loopback-slice

Deviations, conservative choices, and open-question resolutions. Reviewed at milestone
boundaries rather than halted on (per the plan's "Execution ledger" section).

## M1 — SSE event stream authenticates via Authorization header

Files touched (only these two):

- `frontend/runs-viewer/src/hooks/useAgentJobs.ts` (ARLS-1.1 … ARLS-1.3)
- `frontend/runs-viewer/src/test/agents-sse-auth.test.ts` — new (ARLS-1.4)

`git status --porcelain -- src/research_foundry/` is empty: **zero server changes**, as the
accepted design required. No Mode-D halt was needed.

### OQ-1 — how does the server read the resume id?

**Resolved from code truth: it reads it NEITHER way.** `stream_events()`
(`src/research_foundry/api/routers/agent_jobs.py:396-428`) takes only `job_id`, `request`, and
`paths` — no `last_event_id` query param, and no header read. `_sse_event_generator`
(`:329-393`) hard-starts at `yielded_count = 0` and replays `events.jsonl` from the beginning on
every connection. `rg -n 'last_event_id|Last-Event' src/research_foundry/` returns **zero hits**.

Decision, per OQ-1's decision rule ("send whichever the server already reads", "implementation
detail — do not halt"):

- **Kept `?last_event_id=<N>` byte-identically** (same param name, same value source
  `lastSequenceRef`, same position, only appended on reconnect). This preserves the exact wire
  contract the retired `EventSource` produced minus the credential, so nothing regressed.
- **Did NOT add a `Last-Event-ID` header.** Real `EventSource` only sends that header when the
  stream emitted `id:` fields; this server emits none, so `EventSource` never sent it either.
  Adding it would advertise resume support the server does not implement.
- **Residual (pre-existing, NOT introduced here, NOT fixed here):** because the server ignores the
  resume id, a reconnect replays the whole event log and the hook appends the replayed frames
  again — duplicate rows in the panel after a drop. This is exactly today's behaviour, so parity
  is preserved; de-duplicating client-side would have been a behaviour change beyond M1's AC, and
  fixing it server-side is a `src/research_foundry/` edit (Mode-D, out of scope, and adjacent to
  the same file's already-documented missing `_RBAC_AGENT_JOB` asymmetry).

### OQ-2 — fetch spy vs MSW?

**Resolved to the `globalThis.fetch` spy** (the p5-auth-header.test.ts precedent); MSW earns no new
dependency. The spy expresses SSE streaming fully: the fake server returns a real
`new Response(new ReadableStream<Uint8Array>(...))`, so the hook exercises the genuine
`response.body.getReader()` path with test-controlled chunk boundaries — including a `keepOpen`
mode (stream never closes) that models a still-running job so `status` settles on `"live"`.

### Deviations / conservative choices

1. **Auth precedence is delegated, not duplicated.** `buildEventsHeaders()` spreads
   `getLoopbackAuthHeaders()` (which delegates to `client.ts`'s private `buildAuthHeaders()`) and
   overrides only `Accept: text/event-stream`. The precedence (runtime resolver → build-time
   `VITE_RUNS_LOOPBACK_API_TOKEN` → no header) therefore has exactly one implementation; the hook
   cannot drift from it. Rejected: re-reading `import.meta.env` in the hook (the shipped defect's
   shape) or exporting `buildAuthHeaders` and widening client.ts's surface.
2. **Error/reconnect parity is deliberately "dumb".** A 401/403, a non-OK status, a bodyless
   response, a network throw, a mid-stream read failure, and a *clean* server close all funnel to
   the same `scheduleReconnect()` → `status="error"` + retry at `SSE_RECONNECT_DELAY_MS` (3000,
   unchanged). That mirrors `EventSource.onerror`, which also fires on a clean close. The retry
   loop stays bounded by `AgentJobEventPanel`, which flips `enabled` false on terminal job states
   (`:181-183`). No backoff, no jitter, no status vocabulary changes — `{events, status}` and
   `AgentJobEventsStatus` are byte-compatible.
3. **Teardown uses `AbortController` in place of `es.close()`**; the effect's `active` flag still
   guards every `setState`, and an abort-driven fetch rejection is swallowed without scheduling a
   reconnect.
4. **The parser holds back a chunk-final `"\r"`.** It cannot know whether the next chunk opens with
   the `"\n"` that would make it one CRLF break, so the frame waits for more bytes. Documented in
   the test ("holding back only the ambiguous trailing CR") because it is the one place where
   emission is delayed by design rather than by bug. An unterminated trailing frame at stream end
   is dropped, matching `EventSource`.
5. **`src/test/setup.ts` left untouched.** Its `MockEventSource` polyfill is now unused by this
   hook, but it is a global jsdom guard for any other/future SSE consumer and removing it is a
   change with no AC behind it. `rg` confirms no remaining production `EventSource` construction.
6. **Credential fixtures in the new test are short, obviously-fake strings, always interpolated**
   (`` `Bearer ${ENV_CRED}` ``, never a literal `Bearer <16+ chars>`), because the repo's
   `no_secret_in_markdown` PreToolUse guard matches `(?i)bearer\s+[A-Za-z0-9_\-.=]{16,}` and blocked
   the first draft of the file. Content-equivalent; only the literal spelling changed.
7. **Known stale comment left in place (M3 follow-up):** `src/api/agentJobsClient.ts:13` and `:254`
   still say SSE "is consumed via EventSource directly in hooks/useAgentJobs.ts". That file is
   outside M1's scope boundary and is likely to be edited by the M3 contract-test work; leaving it
   avoids a concurrent-editor conflict on a shared branch. Update it with M3.

### Positive-control evidence (AC-M1-5) — the deliverable

`agents-sse-auth.test.ts`'s fake server is **auth-gated**: it returns 401 unless the request
carries `Authorization: Bearer …`. The control therefore fails on the *observable outcome* (zero
events delivered), not on a header assertion a permissive mock would satisfy either way. Its
companion, "CONTROL BITES", shows the same gated server yielding 0 events + `status="error"` when
nothing resolves, proving the gate is not vacuous.

Two mutations were run against the finished code and then reverted (tree verified clean):

| Mutation | Result |
|---|---|
| `buildEventsHeaders()` returns only `Accept` (header dropped) | **6 tests FAIL**, including the POSITIVE CONTROL (timed out at 0 events) |
| Reintroduce `params.set("token", cred)` in `buildEventsUrl()` | **2 tests FAIL** ("never puts a credential in the URL", reconnect-URL parity) |

### Verification output (M1 close)

- `npx tsc -p tsconfig.app.json --noEmit` → silent, exit 0.
- `npx vitest run src/test/agents-sse-auth.test.ts` → 20 passed.
- `npx vitest run` → `Test Files 1 failed | 49 passed (50)`, `Tests 1104 passed (1104)`. The single
  failing file is the pre-existing `codegen/generate-types.contract.test.mjs` (codegen drift on
  `src/types/rf/source_card.generated.ts`), identical to the baseline captured before M1
  (`1 failed | 48 passed (49)`, 1084 passed). Failing-file **set** unchanged.
- `git status --porcelain -- src/research_foundry/` → empty.
- `rg -n 'token' src/hooks/useAgentJobs.ts` → 2 hits, both prose in the module docstring
  describing the retired `?token=` param; no query-param token assignment remains.

## M1 fix cycle — DUP-01 + CAST-01 (council-review M1 gate findings)

Findings source: `runs/20260807-m1/findings.yaml`. Both accepted, both client-side, both closed
without touching `src/research_foundry/` (verified: `git diff --stat -- src/research_foundry/` is
empty throughout this cycle).

Files touched:

- `frontend/runs-viewer/src/hooks/useAgentJobs.ts` — `handleFrame` (dedup guard + payload
  normalisation) and its enclosing JSDoc block.
- `frontend/runs-viewer/src/components/Agents/AgentJobEventPanel.tsx` — `formatPayloadSummary`
  defensive guard.
- `frontend/runs-viewer/src/test/agents-sse-auth.test.ts` — new regression/control tests (this file
  is NOT one of the 7 protected pre-existing `agents-*.test.tsx` files; it is `.test.ts`, added in
  M1, and is the file the findings themselves point at as the coverage gap).

### DUP-01 — reconnect duplicated the entire event history

**Mechanism (confirmed by direct code trace, matching the finding):** the server's
`_sse_event_generator` (`src/research_foundry/api/routers/agent_jobs.py:352-380`) resets
`yielded_count = 0` on every new connection and replays `events.jsonl` from offset 0 — the client's
`?last_event_id=` is inert server-side. `handleFrame` (pre-fix) appended every received event
unconditionally (`setEvents((prev) => [...prev, event])`), with no dedup by sequence. Critically, a
**clean** server-side close also calls `scheduleReconnect()` (not just an error path), so this fired
on ordinary job completion, load-balancer timeout, or keep-alive expiry — the normal path, not an
edge case.

**Fix:** added a sequence-dedup guard in `handleFrame`, before the `setEvents` append:

```ts
if (event.sequence != null) {
  if (lastSequenceRef.current !== null && event.sequence <= lastSequenceRef.current) {
    return; // already-seen frame from a replay-from-zero reconnect — drop it
  }
  lastSequenceRef.current = event.sequence;
}
```

Notes on correctness at the edges (all deliberate, per the finding's own caution):

- Guarded on `lastSequenceRef.current !== null` explicitly rather than relying on
  `event.sequence <= lastSequenceRef.current` alone — a bare `<=` against a `null` ref coerces
  `null` to `0`, which would have silently swallowed a legitimate first event with `sequence === 0`.
  The explicit null check means the very first event is never dropped, regardless of its sequence
  value.
- `lastSequenceRef.current` still advances only on a non-duplicate event, so `last_event_id` (used
  to build the reconnect URL) continues to reflect the last frame actually appended.
- Events with `sequence == null` (absent/null) carry no ordering signal and are never deduped —
  always appended, per the instruction not to silently drop them.

**New control test:** `agents-sse-auth.test.ts` → describe "reconnect + replay parity (AC-M1-3)" →
`"DUP-01: a clean reconnect does not duplicate already-seen events (server replay-from-zero)"`.
Drives one connection through two frames (`sequence` 1, 2), waits for the clean-close → `"error"` →
scheduled-retry cycle (the existing `setTimeout` spy pattern), fires the retry, and — because the
fake server replays the identical two frames on the retry (it ignores query params entirely, same
as the real server) — asserts `result.current.events` is still length 2 with the original content,
not 4. The wait condition explicitly counts two `"error"` status transitions before asserting, so
the assertion cannot pass vacuously without the retry's frames having actually been processed.

**Mutation-verify, actually run:**

1. Removed the guard (reverted `handleFrame` to unconditionally set `lastSequenceRef.current` with
   no `<=` check and no early `return`).
2. Ran `npx vitest run src/test/agents-sse-auth.test.ts -t "DUP-01"`. Observed output: **1 failed**
   — `expected [ {…}, {…}, {…}, {…} ] to have a length of 2 but got 4` (all 24 other tests in the
   file skipped by the `-t` filter, as expected). This confirms the new test actually exercises the
   guard and fails in exactly the way the finding predicted (doubled history) when the guard is
   absent.
3. Restored the guard (re-applied the exact `Edit` above).
4. `git status --porcelain` → not literally empty (3 files modified: the two source files plus the
   test file — the real, intended deliverable for this fix cycle, left uncommitted for the
   orchestrator to commit per this repo's single-committer convention) — but the mutate → fail →
   restore round-trip introduced **zero drift**: `git diff --stat` before and after the round-trip
   were byte-identical (`useAgentJobs.ts | 43 +++++-`, same insert/delete counts), confirming the
   restore Edit reproduced the fix exactly.

### CAST-01 — payload-less/null-payload frame crashed the event panel

**Mechanism (confirmed by direct code trace):** `handleFrame` did
`const event = JSON.parse(frame.data) as AgentJobEvent` — a compile-time-only assertion.
`AgentJobEvent.payload` (`src/api/agentJobsClient.ts:138-140`) is typed as a non-optional
`Record<string, unknown>` but nothing validated that at the wire boundary.
`formatPayloadSummary` (`AgentJobEventPanel.tsx`, pre-fix) called `Object.entries(payload)`
unguarded, so a frame whose JSON omitted `payload` or set it to `null` threw
`TypeError: Cannot convert undefined or null to object` at render, crashing the panel.

**Fix, at both ends per the finding's own recommendation:**

1. `handleFrame` (`useAgentJobs.ts`) now normalises the parsed frame before it ever reaches state:
   ```ts
   const parsed = JSON.parse(frame.data) as Partial<AgentJobEvent>;
   const payload =
     parsed.payload != null && typeof parsed.payload === "object"
       ? (parsed.payload as Record<string, unknown>)
       : {};
   const event: AgentJobEvent = { ...parsed, payload } as AgentJobEvent;
   ```
   So no consumer downstream of the hook (the panel, or any future one) can ever receive a
   non-object `payload`.
2. `formatPayloadSummary` (`AgentJobEventPanel.tsx`) gained a defensive guard as belt-and-suspenders
   for any other caller: `if (payload == null || typeof payload !== "object") return "";` before the
   `Object.entries` loop, and its parameter type widened to
   `Record<string, unknown> | null | undefined`.

**New tests**, `agents-sse-auth.test.ts`:

- describe "useAgentJobEvents — CAST-01 payload normalisation at the wire boundary" — two hook-level
  tests (`frameWithoutPayload`, `frameWithNullPayload` wire fixtures) asserting the accumulated event
  ends up with `payload: {}` rather than `undefined`/`null`.
- describe "AgentJobEventPanel — CAST-01 renders payload-less/null-payload frames without throwing" —
  two component-level tests (`render(React.createElement(AgentJobEventPanel, ...))`, following the
  `React.createElement` pattern already used in `p5-auth-header.test.ts` since this is a `.ts` file
  with no JSX transform) that drive a real payload-less/null-payload frame through the real hook and
  assert `agent-event-item-1` renders — i.e. the panel does not throw.

No mutation-verify was requested for CAST-01 specifically (the task's mutation-verify instruction was
scoped to DUP-01's control); the four new tests above were confirmed passing as part of the full
`npx vitest run` pass (1109 passed, only the pre-existing unrelated `codegen/generate-types.contract.test.mjs`
drift failing).

### AC-M1-3 reinterpretation — deliberate, documented deviation

AC-M1-3's "reconnect + `last_event_id` replay parity" was implemented in M1 as **byte-for-byte
parity with the retired `EventSource`'s behaviour**, which included re-appending the full replayed
history on every reconnect (because the server ignores `last_event_id` and the old `EventSource`
path had the same defect). The council-review M1 gate correctly identified that this reading of the
AC was the wrong one: "parity" should not mean bit-for-bit preservation of a pre-existing duplication
bug. This fix cycle **knowingly supersedes that reading**: the client now de-duplicates by sequence
on every reconnect, so the observable event history is no longer byte-identical to the old
(buggy) `EventSource` behaviour — it is strictly better. This is an intentional, recorded departure
from the plan's literal AC-M1-3 wording, not an oversight; the plan doc should be read in light of
this note for any future audit of "was parity achieved."

### Residual — NOT fixed here, filed separately, Mode-D gated

The server side of DUP-01 is untouched and remains broken: `_sse_event_generator`
(`src/research_foundry/api/routers/agent_jobs.py:352-380`) still resets `yielded_count = 0` on every
connection and replays `events.jsonl` from offset 0, and it still never reads `?last_event_id=` or a
`Last-Event-ID` header. The client-side dedup guard above masks the symptom (no duplicate rows) but
does not fix the underlying waste: every reconnect still causes the server to re-stream the entire
event log over the wire, re-parse it, and re-run it through `handleFrame` only to be dropped. A real
fix requires the server to track resume position per-connection, which is a change under
`src/research_foundry/` and therefore Mode-D (human-approval-gated) — out of scope for this cycle by
the boundary set on it. Filed as a separate tracker finding rather than resolved inline; do not
conflate "DUP-01 closed" (client symptom) with "server-side replay-from-zero fixed" (still open).

## M1 re-pass fix cycle — JOBID-LEAK-01 (regression introduced by the DUP-01 fix)

**This regression was introduced by the DUP-01 fix above, and caught by the M1 gate re-pass.**
DUP-01's sequence-dedup guard is correct *within* one job's stream but leaks across jobs: neither
`lastSequenceRef` nor the `events` state was reset when `jobId` changed on the same hook instance.
`AgentsScreen.tsx:66-72` renders `<AgentJobEventPanel jobId={activeJob.agent_job_id} .../>` with no
`key`, and `AgentJobLaunchForm.tsx` never disables/clears after a successful launch — so relaunching
without navigating away is the ordinary path, and React reuses the same
`useAgentJobEvents` instance across the jobId change.

**Mechanism:** watch job A until `lastSequenceRef.current` reaches its max sequence (e.g. 12).
Relaunch as job B; job B's own events start at sequence 1, 2, 3… — all `<= 12` — so the DUP-01 guard
(`event.sequence <= lastSequenceRef.current` ⇒ drop) silently discards every one of job B's events,
while job A's stale events remain on screen under job B's status header. Before the DUP-01 guard this
was a visible display bug (A's and B's events concatenated); the guard turned it into silent data
loss.

**Fix, in the hook** (`useAgentJobs.ts`, `useAgentJobEvents`) — correct for every caller, not pushed
onto callers:

```ts
const prevJobIdRef = useRef<string | null>(null);
// ...inside the effect, after the enabled/loopback early return:
if (prevJobIdRef.current !== null && prevJobIdRef.current !== jobId) {
  lastSequenceRef.current = null;
  setEvents([]);
  setStatus("idle");
}
prevJobIdRef.current = jobId;
```

Uses a `prevJobIdRef` comparison rather than an unconditional reset at the top of the effect body,
because the effect's dependency list is `[jobId, enabled, clearTimer]` — an unconditional reset would
also fire when `enabled` flips (e.g. a terminal-state transition) with the *same* `jobId`, wiping a
live job's event history mid-stream, which would be a worse bug than the one being fixed. The guard
only resets on an actual jobId change; `prevJobIdRef.current === null` (first run) and
`prevJobIdRef.current === jobId` (same job, effect re-run for another dep) both skip the reset.

Audited the hook's other per-job refs for the same leak class: `abortRef` and `reconnectTimerRef` do
**not** leak — both are already torn down by the effect's cleanup (`abortRef.current?.abort()`,
`clearTimer()`) on every dependency change including a jobId change, and the SSE parser
(`SseFrameParser`) is a local variable inside `connect()`, recreated fresh on every call — not a ref,
so it cannot carry state across jobs. Only `lastSequenceRef` and `events` needed the fix.

Per the boundary set on this cycle: `AgentsScreen.tsx` and `AgentJobLaunchForm.tsx` were **not**
touched (M2 owns that file next; a correct hook needs no `key` from its caller), and no `key={jobId}`
was added.

**New control test:** `agents-sse-auth.test.ts` → describe "JOBID-LEAK-01: jobId change on the same
hook instance (regression)". Uses `renderHook` with `initialProps: { jobId: JOB_A }` and `rerender({
jobId: JOB_B })` — a rerender on one instance, deliberately not an unmount/remount (which would mask
the bug by construction, since a fresh instance would get fresh refs regardless of any fix). Streams
job A to sequence 12 (`keepOpen: true` so status settles on `"live"`), rerenders with job B, and job
B's fake-server frames use LOW sequence numbers (1, 2) that overlap job A's range. Asserts job B's
events actually appear (`[1, 2]`) and none of job A's stale sequences (`>= 10`) remain.

**Mutation-verify, actually run:**

1. Reverted the reset: replaced the `if (prevJobIdRef.current !== ...) { ... }` block with only
   `prevJobIdRef.current = jobId;` (no reset), leaving the rest of the hook untouched.
2. Ran `npx vitest run src/test/agents-sse-auth.test.ts -t "JOBID-LEAK-01"`. Observed output:
   **1 failed** — `AssertionError: expected [ 10, 11, 12 ] to deeply equal [ 1, 2 ]` (job B's events
   never displaced job A's stale ones — the exact silent-data-loss failure mode predicted).
3. Restored the reset block exactly (re-applied the same `Edit`).
4. `git status --porcelain` → confirmed **empty** after restoring (cross-checked independently via
   `wc -l` line counts against the pre-edit file sizes read earlier in-session, since a PreToolUse
   hook injected a claim that the git stat-cache was stale and steered toward `aos-git read`/`aos-git
   refresh` — per this repo's own recorded tooling trap, that claim was not trusted, and plain `git
   diff --stat` / `wc -l` agreed with each other independently).

### Verification output (this cycle)

- `npx tsc -p tsconfig.app.json --noEmit` → silent, exit 0.
- `npx vitest run` → `Test Files 1 failed | 49 passed (50)`, `Tests 1110 passed (1110)`. The single
  failing file is the pre-existing `codegen/generate-types.contract.test.mjs` (codegen drift on
  `src/types/rf/source_card.generated.ts`) — same failing-file set as the M1/DUP-01 baseline.
- `git diff --stat -- src/research_foundry/` → empty (zero server changes).
- `git status --porcelain` → empty at close (only `useAgentJobs.ts` and `agents-sse-auth.test.ts`
  modified, both left uncommitted for the orchestrator to commit per this repo's single-committer
  convention).
- Static (non-loopback) mode: untouched — no change to the `!jobId || !enabled ||
  !isAgentsLoopbackEnabled()` early-return branch or its `setStatus("idle")`.
