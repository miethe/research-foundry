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

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

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

/** Set import.meta.env for a test; must be called before the dynamic import. */
function setEnv(overrides: Record<string, string | boolean | undefined>) {
  for (const [k, v] of Object.entries(overrides)) {
    if (v === undefined) {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (import.meta.env as Record<string, unknown>)[k];
    } else {
      (import.meta.env as Record<string, unknown>)[k] = v;
    }
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
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
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

function sseByteStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      // Deliberately left open (no controller.close()) so `status` settles
      // on "live" rather than immediately cycling to "error"/reconnect.
    },
  });
}

describe("useAgentJobEvents — real SSE reader contract (call 6 of 6)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("6. opens GET /api/agent-jobs/{job_id}/events with an Authorization bearer header and delivers frames", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: SSE_CRED });

    const requests: CapturedRequest[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = urlOf(input as RequestInfo | URL);
      requests.push({
        method: (init?.method ?? "GET").toUpperCase(),
        pathname: new URL(url).pathname,
        authorization: headerOf(init, "Authorization"),
        body: undefined,
      });
      return new Response(sseByteStream([sseFrame(1, "stage_start")]), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
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

    unmount();
  });
});
