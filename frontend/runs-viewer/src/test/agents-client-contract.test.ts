/**
 * ARLS M3 — client<->server contract test for @/api/agentJobsClient.
 *
 * WHY THIS FILE EXISTS: all 9 pre-existing `agents-*.test.tsx` files mock
 * `@/hooks/useAgentJobs` wholesale (`vi.mock("@/hooks/useAgentJobs", ...)`),
 * so none of them ever calls the real `agentJobsClient.ts` functions or the
 * real M1 SSE reader (`useAgentJobEvents` in `@/hooks/useAgentJobs.ts`).
 * `agents-sse-auth.test.ts` is the one exception — it exercises the real SSE
 * reader against the real hook module — but nothing exercised the five
 * REST call functions (`launchAgentJob`, `getAgentJob`,
 * `listAgentJobArtifacts`, `cancelAgentJob`, `acceptAgentJobArtifacts`)
 * against the real client<->transport boundary. That gap is why an SSE 401
 * shipped unnoticed: every consumer-level test saw a mocked hook return
 * canned data and never touched `fetch`.
 *
 * This file imports the REAL functions from `@/api/agentJobsClient` (never
 * `@/hooks/useAgentJobs` mocked) and intercepts `globalThis.fetch` — the one
 * seam both the client's `loopbackRequest()` helper and the SSE hook's
 * `fetch` + `ReadableStream` path go through. Six distinct HTTP calls are
 * covered, matching the six routes registered under `/api` by
 * `src/research_foundry/api/routers/agent_jobs.py`:
 *
 *   1. POST   /api/agent-jobs                       launchAgentJob
 *   2. GET    /api/agent-jobs/{job_id}               getAgentJob
 *   3. GET    /api/agent-jobs/{job_id}/artifacts     listAgentJobArtifacts
 *   4. POST   /api/agent-jobs/{job_id}/cancel        cancelAgentJob
 *   5. POST   /api/agent-jobs/{job_id}/accept        acceptAgentJobArtifacts
 *   6. GET    /api/agent-jobs/{job_id}/events        useAgentJobEvents (SSE)
 *
 * Each assertion pins method + URL pathname + the resolved Authorization
 * header, so changing any route string in agentJobsClient.ts or
 * useAgentJobs.ts breaks this file.
 *
 * client.ts reads LOOPBACK_ENABLED / LOOPBACK_BASE as module-level constants
 * evaluated at import time (same constraint documented in
 * p5-auth-header.test.ts and agents-sse-auth.test.ts), so every test does
 * `vi.resetModules()` + a dynamic import to force a fresh evaluation against
 * the env values set just before.
 *
 * NOTE: credential fixtures below are deliberately short, obviously-fake
 * strings and are always interpolated (never written as a literal
 * "Bearer <...>" string) so this file cannot trip the repo's secret-scanning
 * guard.
 */

import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

// File-level safety net: every `it()` restores env + spies in its own
// afterEach, but this catches the case where a beforeEach/afterEach itself
// throws before reaching its own vi.unstubAllEnvs()/vi.restoreAllMocks()
// call, so a leak can never survive past this file into the files that run
// after it in the same worker.
afterAll(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

const API_BASE = "http://127.0.0.1:7432/api";
const JOB_ID = "aj_contract_0001";

// Fake credential fixtures — one per test to keep spies isolated.
const LAUNCH_CRED = "launch-cred-1";
const GET_CRED = "get-cred-1";
const ARTIFACTS_CRED = "artifacts-cred-1";
const CANCEL_CRED = "cancel-cred-1";
const ACCEPT_CRED = "accept-cred-1";
const SSE_CRED = "sse-cred-1";

const LOOPBACK_ON = {
  VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
  VITE_RUNS_LOOPBACK_API_BASE: API_BASE,
} as const;

/**
 * Set import.meta.env for a test via vi.stubEnv, which — unlike hand-mutating
 * `import.meta.env` directly — records each key's PRIOR value (including
 * "was absent") the first time it is touched, so `vi.unstubAllEnvs()` in
 * afterEach restores every key to its exact prior state (present or absent),
 * not just the ones this helper's caller happened to remember to clear.
 *
 * ROOT-CAUSE NOTE (fixed 2026-08-10): the prior version of this helper wrote
 * straight onto `import.meta.env` — a single object that Vitest shares live
 * across the whole worker process, NOT a fresh per-test-file snapshot. Every
 * `it()` here called `setEnv({ ...LOOPBACK_ON, ... })`, which sets
 * VITE_RUNS_FRONTEND_LOOPBACK_API and VITE_RUNS_LOOPBACK_API_BASE, but the
 * old `afterEach` only ever cleared VITE_RUNS_LOOPBACK_API_TOKEN. Those two
 * LOOPBACK_ON keys were never restored, so they stayed "true" / the fake API
 * base on `import.meta.env` for the rest of the worker's lifetime — leaking
 * into every later test file's fresh `client.ts` import (each file's own
 * `vi.resetModules()` gives a fresh MODULE registry, but not a fresh
 * `import.meta.env` object) and flipping unrelated components like
 * BuilderScreen into loopback mode they never expect. Confirmed via a
 * standalone probe: `vi.stubEnv("X", "y"); expect(import.meta.env.X).toBe("y")`
 * followed by `vi.unstubAllEnvs()` correctly deletes the key again — i.e.
 * `import.meta.env` genuinely is the same live object `vi.stubEnv` targets,
 * and only `vi.stubEnv`'s own bookkeeping (not hand-rolled key tracking)
 * reliably reverses it.
 */
function setEnv(overrides: Record<string, string | boolean | undefined>) {
  for (const [k, v] of Object.entries(overrides)) {
    vi.stubEnv(k, v === undefined ? undefined : String(v));
  }
}

function urlOf(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
}

function headerOf(init: RequestInit | undefined, name: string): string | null {
  if (!init?.headers) return null;
  const h = init.headers as Record<string, string>;
  return h[name] ?? null;
}

interface CapturedRequest {
  method: string;
  pathname: string;
  authorization: string | null;
  body: unknown;
}

/**
 * Install a fetch spy that captures every request as a CapturedRequest
 * (method + URL pathname + resolved Authorization header + parsed JSON
 * body) and always answers with a single canned JSON response. One call
 * per test keeps each REST assertion isolated to the one request it made.
 */
function installRestServer(status: number, responseBody: unknown): { requests: CapturedRequest[] } {
  const requests: CapturedRequest[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = urlOf(input as RequestInfo | URL);
    let body: unknown = undefined;
    if (typeof init?.body === "string") {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    requests.push({
      method: (init?.method ?? "GET").toUpperCase(),
      pathname: new URL(url).pathname,
      authorization: headerOf(init, "Authorization"),
      body,
    });
    return new Response(JSON.stringify(responseBody), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  return { requests };
}

/** Load the real client module fresh, alongside client.ts's resolver setter. */
async function loadClientModule() {
  const clientMod = await import("@/api/client");
  const agentJobsMod = await import("@/api/agentJobsClient");
  return { ...agentJobsMod, setAuthTokenResolver: clientMod.setAuthTokenResolver };
}

/** Load the real hook module fresh, alongside client.ts's resolver setter. */
async function loadHookModule() {
  const clientMod = await import("@/api/client");
  const hooksMod = await import("@/hooks/useAgentJobs");
  return { ...hooksMod, setAuthTokenResolver: clientMod.setAuthTokenResolver };
}

// ═════════════════════════════════════════════════════════════════════════════
// REST calls (1-5) — real loopbackRequest() through a real fetch spy
// ═════════════════════════════════════════════════════════════════════════════

describe("agentJobsClient — real HTTP contract (REST calls 1-5 of 6)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Restores every key vi.stubEnv touched in this test — including the two
    // LOOPBACK_ON keys, not just the per-test credential — to its exact
    // prior value (present or absent). See setEnv()'s ROOT-CAUSE NOTE above.
    vi.unstubAllEnvs();
  });

  it("1. launchAgentJob() → POST /api/agent-jobs with Authorization + JSON body", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: LAUNCH_CRED });
    const { requests } = installRestServer(201, {
      agent_job_id: JOB_ID,
      status: "queued",
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
      workspace_id: null,
      created_by: null,
      policy_snapshot: null,
    });

    const { launchAgentJob } = await loadClientModule();
    const result = await launchAgentJob({
      provider: "anthropic",
      model_profile: "sonnet",
      request_kind: "research",
      policy_snapshot: { allowed_tools: ["web_search"], data_scopes: ["public"] },
    });

    expect(result.agent_job_id).toBe(JOB_ID);
    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("POST");
    expect(requests[0]!.pathname).toBe("/api/agent-jobs");
    expect(requests[0]!.authorization).toBe(`Bearer ${LAUNCH_CRED}`);
    expect(requests[0]!.body).toMatchObject({
      provider: "anthropic",
      model_profile: "sonnet",
      request_kind: "research",
    });
  });

  it("2. getAgentJob() → GET /api/agent-jobs/{job_id} with Authorization", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: GET_CRED });
    const { requests } = installRestServer(200, {
      agent_job_id: JOB_ID,
      status: "running",
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:01:00Z",
      workspace_id: null,
      created_by: null,
      policy_snapshot: null,
    });

    const { getAgentJob } = await loadClientModule();
    const result = await getAgentJob(JOB_ID);

    expect(result.status).toBe("running");
    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("GET");
    expect(requests[0]!.pathname).toBe(`/api/agent-jobs/${JOB_ID}`);
    expect(requests[0]!.authorization).toBe(`Bearer ${GET_CRED}`);
  });

  it("3. listAgentJobArtifacts() → GET /api/agent-jobs/{job_id}/artifacts with Authorization", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: ARTIFACTS_CRED });
    const { requests } = installRestServer(200, [
      { artifact_id: "art_1", artifact_kind: "source_card", accepted: false },
    ]);

    const { listAgentJobArtifacts } = await loadClientModule();
    const result = await listAgentJobArtifacts(JOB_ID);

    expect(result).toHaveLength(1);
    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("GET");
    expect(requests[0]!.pathname).toBe(`/api/agent-jobs/${JOB_ID}/artifacts`);
    expect(requests[0]!.authorization).toBe(`Bearer ${ARTIFACTS_CRED}`);
  });

  it("4. cancelAgentJob() → POST /api/agent-jobs/{job_id}/cancel with Authorization", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CANCEL_CRED });
    const { requests } = installRestServer(200, null);

    const { cancelAgentJob } = await loadClientModule();
    await cancelAgentJob(JOB_ID);

    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("POST");
    expect(requests[0]!.pathname).toBe(`/api/agent-jobs/${JOB_ID}/cancel`);
    expect(requests[0]!.authorization).toBe(`Bearer ${CANCEL_CRED}`);
  });

  it("5. acceptAgentJobArtifacts() → POST /api/agent-jobs/{job_id}/accept with Authorization + JSON body", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: ACCEPT_CRED });
    const { requests } = installRestServer(200, {
      agent_job_id: JOB_ID,
      acceptance_id: "acc_1",
      accepted_artifact_count: 1,
      artifact_ids: ["art_1"],
      accepted_by: "tester",
      accepted_at: "2026-08-10T00:02:00Z",
    });

    const { acceptAgentJobArtifacts } = await loadClientModule();
    const result = await acceptAgentJobArtifacts(JOB_ID, { accepted_by: "tester", notes: null });

    expect(result.accepted_artifact_count).toBe(1);
    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("POST");
    expect(requests[0]!.pathname).toBe(`/api/agent-jobs/${JOB_ID}/accept`);
    expect(requests[0]!.authorization).toBe(`Bearer ${ACCEPT_CRED}`);
    expect(requests[0]!.body).toMatchObject({ accepted_by: "tester" });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// SSE call (6 of 6) — the real M1 reader (useAgentJobEvents) through a real
// fetch + ReadableStream spy. This is the transport the shipped 401 rode.
// ═════════════════════════════════════════════════════════════════════════════

function sseFrame(sequence: number, eventType: string): string {
  return `data: ${JSON.stringify({ event_type: eventType, payload: {}, sequence })}\n\n`;
}

/**
 * Builds an SSE byte stream and hands the caller its controller so the test
 * can close it explicitly once assertions are done. Left open through
 * `start()` (no `controller.close()` there) so `status` settles on "live"
 * rather than immediately cycling to "error"/reconnect — but an
 * ever-open stream leaves the hook's `await reader.read()` pending forever
 * if nothing ever closes it, which is a dangling-microtask leak of its own
 * (independent of the import.meta.env leak fixed above). `onController`
 * captures the controller so the test can close it before `unmount()`,
 * letting that pending read() resolve with `done: true` and the hook's
 * internal loop exit cleanly instead of leaking past the test.
 */
function sseByteStream(
  chunks: string[],
  onController: (controller: ReadableStreamDefaultController<Uint8Array>) => void,
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      onController(controller);
    },
  });
}

describe("useAgentJobEvents — real SSE reader contract (call 6 of 6)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Restores every key vi.stubEnv touched in this test — including the two
    // LOOPBACK_ON keys, not just the per-test credential — to its exact
    // prior value (present or absent). See setEnv()'s ROOT-CAUSE NOTE above.
    vi.unstubAllEnvs();
  });

  it("6. opens GET /api/agent-jobs/{job_id}/events with an Authorization bearer header and delivers frames", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: SSE_CRED });

    const requests: CapturedRequest[] = [];
    let streamController: ReadableStreamDefaultController<Uint8Array> | null = null;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = urlOf(input as RequestInfo | URL);
      requests.push({
        method: (init?.method ?? "GET").toUpperCase(),
        pathname: new URL(url).pathname,
        authorization: headerOf(init, "Authorization"),
        body: undefined,
      });
      return new Response(
        sseByteStream([sseFrame(1, "stage_start")], (controller) => {
          streamController = controller;
        }),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderHook(() => useAgentJobEvents(JOB_ID, true));

    await waitFor(() => expect(result.current.events).toHaveLength(1));
    expect(result.current.status).toBe("live");
    expect(result.current.events[0]).toEqual({
      event_type: "stage_start",
      payload: {},
      sequence: 1,
    });

    // This is the exact assertion class the shipped regression violated: the
    // SSE request must carry the same real Authorization header the five
    // REST calls above carry, against the real route path.
    expect(requests).toHaveLength(1);
    expect(requests[0]!.method).toBe("GET");
    expect(requests[0]!.pathname).toBe(`/api/agent-jobs/${JOB_ID}/events`);
    expect(requests[0]!.authorization).toBe(`Bearer ${SSE_CRED}`);

    // Close the stream before unmounting: the hook's read loop is currently
    // parked on a second `await reader.read()` that will never resolve on
    // its own (the stream was left open on purpose so `status` could settle
    // on "live" above). Closing it here lets that read() resolve with
    // `done: true` and the loop exit cleanly, instead of leaving a
    // permanently-pending promise referencing this test's closures behind
    // once the test finishes.
    streamController?.close();
    unmount();
  });
});
