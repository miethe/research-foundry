/**
 * ARLS M1 — SSE auth + frame-parser contract for useAgentJobEvents.
 *
 * WHY THIS FILE EXISTS: all 7 pre-existing `agents-*` tests mock
 * `@/hooks/useAgentJobs`, so every one of them passed while the live event
 * stream 401'd in production (the credential rode a `?token=` query param that no
 * server auth surface reads). Those tests validly cover component behaviour;
 * NOTHING covered the client<->server transport contract. This file covers it, at
 * the layer beneath them: the real hook, the real header builder, a spied
 * `globalThis.fetch` (OQ-2 -> fetch spy, not MSW — the spy expresses SSE
 * streaming fine via a real ReadableStream body).
 *
 * The load-bearing test is "positive control": the fake server is AUTH-GATED
 * (401 unless an `Authorization` bearer header is present), so deleting the
 * header from the hook makes the hook deliver ZERO events — the test fails on the
 * observable outcome, not merely on a header assertion that a permissive mock
 * would pass either way. Its companion ("control bites") proves the gate is not
 * vacuous by showing the same server yields zero events when nothing resolves.
 *
 * client.ts reads LOOPBACK_ENABLED / LOOPBACK_BASE as module-level constants, so
 * (as in p5-auth-header.test.ts) each test does vi.resetModules() + a dynamic
 * import to re-evaluate with patched import.meta.env values. Both dynamic
 * imports in a test share one module registry, so the `setAuthTokenResolver` we
 * call is the same client instance the hook reads.
 *
 * NOTE: credential fixtures below are deliberately short, obviously-fake strings
 * and are always interpolated (never written as a literal "Bearer <...>" string),
 * so this file cannot trip the repo's secret-scanning guard.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, render, act, waitFor } from "@testing-library/react";
import React from "react";
// Pure parser — safe to import statically (no env-dependent behaviour).
import { SseFrameParser } from "@/hooks/useAgentJobs";

const JOB_ID = "aj_test_0001";
const API_BASE = "http://127.0.0.1:7432/api";

// Fake credential fixtures (short by design — see NOTE above).
const ENV_CRED = "env-cred-1";
const SESSION_CRED = "sess-cred-1";
const GATED_CRED = "gate-cred-1";
const RETRY_CRED = "retry-cred";
const CHUNK_CRED = "chunk-cred";
const URL_CANARY = "url-leak-canary";

// ── helpers ───────────────────────────────────────────────────────────────────

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

/** Read one header from fetch's RequestInit (the hook passes a plain Record). */
function headerOf(init: RequestInit | undefined, name: string): string | null {
  if (!init?.headers) return null;
  const h = init.headers as Record<string, string>;
  return h[name] ?? null;
}

function urlOf(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
}

/**
 * A real web ReadableStream of UTF-8 bytes — chunk boundaries exactly as given.
 * When `keepOpen` is true the stream never closes, modelling a live job whose
 * server-side generator is still polling (so `status` settles on "live").
 */
function byteStream(chunks: string[], keepOpen: boolean): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      if (!keepOpen) controller.close();
    },
  });
}

function sseResponse(chunks: string[], keepOpen: boolean): Response {
  return new Response(byteStream(chunks, keepOpen), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function unauthorizedResponse(): Response {
  return new Response(JSON.stringify({ detail: "Missing credential" }), {
    status: 401,
    statusText: "Unauthorized",
    headers: { "Content-Type": "application/json" },
  });
}

interface CapturedRequest {
  url: string;
  authorization: string | null;
  accept: string | null;
}

/**
 * Install a fetch spy that serves the agent-job SSE endpoint. When
 * `requireAuth` is true it behaves like the real server under
 * token-store / local_static auth: 401 unless a bearer header is present.
 */
function installSseServer(options: {
  chunks: string[];
  requireAuth: boolean;
  /** Leave the stream open after the chunks (default: close it). */
  keepOpen?: boolean;
}): { requests: CapturedRequest[] } {
  const requests: CapturedRequest[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = urlOf(input as RequestInfo | URL);
    if (!url.includes("/agent-jobs/")) {
      // Not our endpoint — mimic setup.ts's 404 fallback.
      return new Response(`Not found: ${url}`, { status: 404 });
    }
    const authorization = headerOf(init, "Authorization");
    requests.push({ url, authorization, accept: headerOf(init, "Accept") });
    if (options.requireAuth && !authorization?.startsWith("Bearer ")) {
      return unauthorizedResponse();
    }
    return sseResponse(options.chunks, options.keepOpen ?? false);
  });
  return { requests };
}

/** Load the hook + client from one fresh module registry. */
async function loadHookModule() {
  const clientMod = await import("@/api/client");
  const hooksMod = await import("@/hooks/useAgentJobs");
  return { ...hooksMod, setAuthTokenResolver: clientMod.setAuthTokenResolver };
}

/** Render useAgentJobEvents, recording every status it passed through. */
function renderEvents(
  useAgentJobEvents: (
    jobId: string | null,
    enabled: boolean,
  ) => { events: { sequence?: number | null }[]; status: string },
) {
  const statuses: string[] = [];
  const view = renderHook(() => {
    const result = useAgentJobEvents(JOB_ID, true);
    statuses.push(result.status);
    return result;
  });
  return { ...view, statuses };
}

const LOOPBACK_ON = {
  VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
  VITE_RUNS_LOOPBACK_API_BASE: API_BASE,
} as const;

function frame(sequence: number, eventType: string): string {
  return `data: ${JSON.stringify({
    event_type: eventType,
    payload: { detail: "redacted-by-server" },
    sequence,
  })}\n\n`;
}

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-1 — the stream authenticates by header, with buildAuthHeaders precedence
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — Authorization header on the stream request (AC-M1-1)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("sends an Authorization bearer header built from the build-time env value", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: ENV_CRED });
    const { requests } = installSseServer({ chunks: [frame(1, "stage_start")], requireAuth: false });

    const { useAgentJobEvents } = await loadHookModule();
    const { unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    expect(requests[0]!.authorization).toBe(`Bearer ${ENV_CRED}`);
    expect(requests[0]!.accept).toBe("text/event-stream");
    unmount();
  });

  it("prefers the runtime resolver over the build-time env value (buildAuthHeaders precedence)", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: ENV_CRED });
    const { requests } = installSseServer({ chunks: [frame(1, "stage_start")], requireAuth: false });

    const { useAgentJobEvents, setAuthTokenResolver } = await loadHookModule();
    setAuthTokenResolver(() => SESSION_CRED);
    try {
      const { unmount } = renderEvents(useAgentJobEvents);
      await waitFor(() => expect(requests.length).toBeGreaterThan(0));
      expect(requests[0]!.authorization).toBe(`Bearer ${SESSION_CRED}`);
      expect(requests[0]!.authorization).not.toContain(ENV_CRED);
      unmount();
    } finally {
      setAuthTokenResolver(null);
    }
  });

  it("omits the Authorization header entirely when nothing resolves", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
    const { requests } = installSseServer({ chunks: [frame(1, "stage_start")], requireAuth: false });

    const { useAgentJobEvents, setAuthTokenResolver } = await loadHookModule();
    setAuthTokenResolver(() => null);
    try {
      const { unmount } = renderEvents(useAgentJobEvents);
      await waitFor(() => expect(requests.length).toBeGreaterThan(0));
      // Must be absent — never a bearer prefix with an empty credential.
      expect(requests[0]!.authorization).toBeNull();
      unmount();
    } finally {
      setAuthTokenResolver(null);
    }
  });

  it("never puts a credential in the URL (NFR-1)", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: URL_CANARY });
    const { requests } = installSseServer({ chunks: [frame(7, "stage_start")], requireAuth: false });

    const { useAgentJobEvents } = await loadHookModule();
    const { unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    for (const request of requests) {
      expect(request.url).not.toContain(URL_CANARY);
      expect(request.url).not.toContain("token");
    }
    expect(requests[0]!.url).toBe(`${API_BASE}/agent-jobs/${JOB_ID}/events`);
    unmount();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-5 — POSITIVE CONTROL: events only arrive when the header is sent
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — positive control against an auth-gated server (AC-M1-5)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("POSITIVE CONTROL: delivers events through a 401-gated server — FAILS if the Authorization header is dropped", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: GATED_CRED });
    // requireAuth: true — exactly the server behaviour that made the shipped
    // ?token= transport return 401 and render an empty event panel.
    // keepOpen: true models a still-running job, so `status` settles on "live".
    installSseServer({
      chunks: [frame(1, "stage_start"), frame(2, "stage_complete")],
      requireAuth: true,
      keepOpen: true,
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(2));
    expect(result.current.status).toBe("live");
    expect(result.current.events).toEqual([
      { event_type: "stage_start", payload: { detail: "redacted-by-server" }, sequence: 1 },
      { event_type: "stage_complete", payload: { detail: "redacted-by-server" }, sequence: 2 },
    ]);
    unmount();
  });

  it("CONTROL BITES: the same gated server yields zero events and an error status when nothing resolves", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
    const { requests } = installSseServer({
      chunks: [frame(1, "stage_start"), frame(2, "stage_complete")],
      requireAuth: true,
      keepOpen: true,
    });

    const { useAgentJobEvents, setAuthTokenResolver } = await loadHookModule();
    setAuthTokenResolver(() => null);
    try {
      const { result, statuses, unmount } = renderEvents(useAgentJobEvents);
      await waitFor(() => expect(result.current.status).toBe("error"));
      expect(result.current.events).toHaveLength(0);
      expect(statuses).not.toContain("live");
      // The gate really bit: the request reached the server WITHOUT a bearer.
      expect(requests[0]!.authorization).toBeNull();
      unmount();
    } finally {
      setAuthTokenResolver(null);
    }
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-4 — partial-chunk-safe frame parsing, end to end through the hook
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — frames split across read() chunks (AC-M1-4)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("emits exactly one event per complete frame when the wire splits mid-frame", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    const whole = frame(1, "stage_start") + frame(2, "stage_complete") + frame(3, "job_done");
    // Deliberately brutal chunking: mid-JSON, mid-field-name, and a boundary
    // that splits the "\n\n" frame delimiter itself.
    const cut1 = whole.indexOf("stage_complete") - 12;
    const cut2 = whole.indexOf("job_done") + 4;
    installSseServer({
      chunks: [whole.slice(0, 9), whole.slice(9, cut1), whole.slice(cut1, cut2), whole.slice(cut2)],
      requireAuth: true,
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(3));
    expect(result.current.events.map((e) => e.sequence)).toEqual([1, 2, 3]);
    unmount();
  });

  it("skips a malformed frame without dropping the valid frames around it", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    installSseServer({
      chunks: [frame(1, "stage_start"), "data: {not json\n\n", frame(2, "stage_complete")],
      requireAuth: true,
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(2));
    expect(result.current.events.map((e) => e.sequence)).toEqual([1, 2]);
    unmount();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-3 — reconnect delay + last_event_id replay parity
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — reconnect + replay parity (AC-M1-3)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("schedules the retry at SSE_RECONNECT_DELAY_MS (3000ms) and resumes with last_event_id + the auth header", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: RETRY_CRED });
    const { requests } = installSseServer({ chunks: [frame(41, "stage_start")], requireAuth: true });
    // Spy without replacing the implementation, so we can read the scheduled
    // delay AND fire the callback deterministically (no fake-timer interplay
    // with the stream's microtask chain).
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    // First connection reads one event, then the server closes the stream —
    // EventSource-parity: status "error" and a retry scheduled.
    await waitFor(() => expect(result.current.events).toHaveLength(1));
    await waitFor(() => expect(result.current.status).toBe("error"));

    const scheduled = setTimeoutSpy.mock.calls.filter(([, delay]) => delay === 3_000);
    expect(scheduled.length).toBeGreaterThan(0);

    // Fire the retry callback: the reconnect must carry last_event_id=41 and
    // still authenticate by header.
    await act(async () => {
      (scheduled[0]![0] as () => void)();
      await Promise.resolve();
    });
    await waitFor(() => expect(requests.length).toBeGreaterThan(1));

    const retry = requests[1]!;
    expect(retry.url).toBe(`${API_BASE}/agent-jobs/${JOB_ID}/events?last_event_id=41`);
    expect(retry.authorization).toBe(`Bearer ${RETRY_CRED}`);
    expect(retry.url).not.toContain("token");
    unmount();
  });

  it("DUP-01: a clean reconnect does not duplicate already-seen events (server replay-from-zero)", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: RETRY_CRED });
    // installSseServer ignores last_event_id / query params entirely — this
    // mirrors the real server's `_sse_event_generator`, which always replays
    // events.jsonl from offset 0 regardless of what the client asks to resume
    // from (DUP-01, findings.yaml). Without a client-side dedup guard, the
    // retry below would re-append these same two frames and double the
    // accumulated event history.
    const { requests } = installSseServer({
      chunks: [frame(1, "stage_start"), frame(2, "stage_complete")],
      requireAuth: true,
    });
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");

    const { useAgentJobEvents } = await loadHookModule();
    const { result, statuses, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(2));
    await waitFor(() => expect(result.current.status).toBe("error"));

    const scheduled = setTimeoutSpy.mock.calls.filter(([, delay]) => delay === 3_000);
    expect(scheduled.length).toBeGreaterThan(0);

    // Fire the retry: the same fake server replays the SAME two frames again
    // (offset-0 replay), exactly like the real server does on every reconnect.
    await act(async () => {
      (scheduled[0]![0] as () => void)();
      await Promise.resolve();
    });
    await waitFor(() => expect(requests.length).toBeGreaterThan(1));
    // Wait for the SECOND connection's read loop to fully finish (its own
    // "error" status) before asserting — otherwise the assertion below would
    // pass trivially without the retry's re-delivered frames ever having been
    // processed by handleFrame.
    await waitFor(() =>
      expect(statuses.filter((s) => s === "error").length).toBeGreaterThanOrEqual(2),
    );

    expect(result.current.events).toHaveLength(2);
    expect(result.current.events).toEqual([
      { event_type: "stage_start", payload: { detail: "redacted-by-server" }, sequence: 1 },
      { event_type: "stage_complete", payload: { detail: "redacted-by-server" }, sequence: 2 },
    ]);
    unmount();
  });

  it("first connection carries no last_event_id (parity with the retired EventSource URL)", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: RETRY_CRED });
    const { requests } = installSseServer({ chunks: [], requireAuth: true });

    const { useAgentJobEvents } = await loadHookModule();
    const { unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    expect(requests[0]!.url).not.toContain("last_event_id");
    unmount();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// JOBID-LEAK-01 — per-job state must reset on a same-instance jobId change
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — JOBID-LEAK-01: jobId change on the same hook instance (regression)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("clears job A's stale high-sequence events and accepts job B's low-sequence events on a jobId rerender", async () => {
    // Production path: AgentsScreen renders AgentJobEventPanel without a
    // `key`, so relaunching swaps `jobId` on the SAME component/hook
    // instance (setActiveJob(job) after a successful relaunch). Before the
    // DUP-01 dedup guard, a jobId change was a visible-but-safe bug (A's and
    // B's events concatenated). The guard turned it into SILENT DATA LOSS:
    // lastSequenceRef survives the jobId change, so B's own low sequence
    // numbers read as an already-seen replay of A and get dropped. An
    // unmount/remount would never exercise this — it must be a rerender on
    // one instance.
    const JOB_A = "aj_test_000A";
    const JOB_B = "aj_test_000B";
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: RETRY_CRED });

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = urlOf(input as RequestInfo | URL);
      const authorization = headerOf(init, "Authorization");
      if (!authorization?.startsWith("Bearer ")) return unauthorizedResponse();
      if (url.includes(JOB_A)) {
        // Job A climbs to sequence 12 — lastSequenceRef.current reaches 12
        // while the stream stays open ("live"), exactly as in the repro.
        return sseResponse(
          [frame(10, "stage_start"), frame(11, "stage_progress"), frame(12, "stage_progress")],
          true,
        );
      }
      if (url.includes(JOB_B)) {
        // Job B's OWN events use LOW sequence numbers that overlap A's
        // range — these must NOT be treated as a stale replay of A.
        return sseResponse([frame(1, "stage_start"), frame(2, "stage_progress")], true);
      }
      return new Response(`Not found: ${url}`, { status: 404 });
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, rerender, unmount } = renderHook(
      ({ jobId }: { jobId: string }) => useAgentJobEvents(jobId, true),
      { initialProps: { jobId: JOB_A } },
    );

    await waitFor(() => expect(result.current.events).toHaveLength(3));
    expect(result.current.events.map((e) => e.sequence)).toEqual([10, 11, 12]);
    expect(result.current.status).toBe("live");

    // Relaunch: same hook instance, new jobId — no unmount involved.
    rerender({ jobId: JOB_B });

    // Job B's events must actually arrive...
    await waitFor(() => expect(result.current.events.map((e) => e.sequence)).toEqual([1, 2]));
    expect(result.current.events.map((e) => e.event_type)).toEqual(["stage_start", "stage_progress"]);
    // ...and none of job A's stale events may remain mixed in.
    expect(result.current.events.some((e) => e.sequence != null && e.sequence >= 10)).toBe(false);

    unmount();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-6 — static (non-loopback) mode is untouched
// ═════════════════════════════════════════════════════════════════════════════

describe("useAgentJobEvents — static mode opens no connection (AC-M1-6)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_FRONTEND_LOOPBACK_API: undefined, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("stays idle and issues no request when loopback mode is off", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: undefined,
      VITE_RUNS_LOOPBACK_API_BASE: API_BASE,
      VITE_RUNS_LOOPBACK_API_TOKEN: undefined,
    });
    const { requests } = installSseServer({ chunks: [frame(1, "stage_start")], requireAuth: false });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    expect(result.current.status).toBe("idle");
    expect(result.current.events).toHaveLength(0);
    expect(requests).toHaveLength(0);
    unmount();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-M1-4 — SseFrameParser unit contract (the hand-rolled parsing risk)
// ═════════════════════════════════════════════════════════════════════════════

describe("SseFrameParser — partial-chunk safety (AC-M1-4)", () => {
  it("buffers a frame split across pushes and emits it exactly once", () => {
    const parser = new SseFrameParser();
    expect(parser.push('data: {"sequence"')).toEqual([]);
    expect(parser.push(": 1}")).toEqual([]);
    expect(parser.push("\n")).toEqual([]);
    const frames = parser.push("\n");
    expect(frames).toHaveLength(1);
    expect(frames[0]!.data).toBe('{"sequence": 1}');
    // No duplicate on the next push.
    expect(parser.push("")).toEqual([]);
  });

  it("emits multiple frames delivered in a single chunk, in order", () => {
    const parser = new SseFrameParser();
    const frames = parser.push("data: one\n\ndata: two\n\ndata: three\n\n");
    expect(frames.map((f) => f.data)).toEqual(["one", "two", "three"]);
  });

  it("splits the frame delimiter itself across chunks without emitting early", () => {
    const parser = new SseFrameParser();
    expect(parser.push("data: alpha\n").map((f) => f.data)).toEqual([]);
    expect(parser.push("\ndata: beta\n\n").map((f) => f.data)).toEqual(["alpha", "beta"]);
  });

  it("handles CRLF endings, including a CRLF pair split across chunks", () => {
    const parser = new SseFrameParser();
    expect(parser.push("data: alpha\r\n\r").map((f) => f.data)).toEqual([]);
    expect(parser.push("\n").map((f) => f.data)).toEqual(["alpha"]);
  });

  it("handles lone-CR line endings, holding back only the ambiguous trailing CR", () => {
    const parser = new SseFrameParser();
    // Both CR-terminated frames dispatch because more bytes follow them.
    expect(
      parser.push("data: alpha\r\rdata: beta\r\rdata: partial").map((f) => f.data),
    ).toEqual(["alpha", "beta"]);
    // A CR that lands on the chunk boundary is deliberately held back — the next
    // chunk may open with the "\n" that makes it one CRLF break, not a boundary.
    expect(parser.push("\r").map((f) => f.data)).toEqual([]);
    expect(parser.push("\rdata: next").map((f) => f.data)).toEqual(["partial"]);
  });

  it("joins multi-line data fields with a newline and strips one leading space only", () => {
    const parser = new SseFrameParser();
    const frames = parser.push("data: line1\ndata:  line2\n\n");
    expect(frames).toHaveLength(1);
    expect(frames[0]!.data).toBe("line1\n line2");
  });

  it("ignores comment/heartbeat lines and never dispatches a dataless frame", () => {
    const parser = new SseFrameParser();
    expect(parser.push(": keep-alive\n\n")).toEqual([]);
    expect(parser.push("event: ping\n\n")).toEqual([]);
    expect(parser.push("data: real\n\n").map((f) => f.data)).toEqual(["real"]);
  });

  it("captures event and id fields when present", () => {
    const parser = new SseFrameParser();
    const frames = parser.push("event: stage\nid: 42\ndata: payload\n\n");
    expect(frames).toHaveLength(1);
    expect(frames[0]).toEqual({ data: "payload", event: "stage", id: "42" });
  });

  it("never emits an unterminated trailing frame (EventSource parity)", () => {
    const parser = new SseFrameParser();
    expect(parser.push("data: incomplete-no-blank-line\n")).toEqual([]);
    expect(parser.hasPendingFrame()).toBe(true);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// CAST-01 — a payload-less/null-payload frame must not crash the event panel
// ═════════════════════════════════════════════════════════════════════════════

/** A wire frame whose JSON omits the `payload` key entirely. */
function frameWithoutPayload(sequence: number, eventType: string): string {
  return `data: ${JSON.stringify({ event_type: eventType, sequence })}\n\n`;
}

/** A wire frame whose JSON sets `payload` to `null`. */
function frameWithNullPayload(sequence: number, eventType: string): string {
  return `data: ${JSON.stringify({ event_type: eventType, payload: null, sequence })}\n\n`;
}

describe("useAgentJobEvents — CAST-01 payload normalisation at the wire boundary", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("normalises an absent payload to {} instead of leaking undefined into events", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    installSseServer({
      chunks: [frameWithoutPayload(1, "stage_start")],
      requireAuth: true,
      keepOpen: true,
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(1));
    expect(result.current.events[0]).toEqual({
      event_type: "stage_start",
      payload: {},
      sequence: 1,
    });
    unmount();
  });

  it("normalises a null payload to {} instead of leaking null into events", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    installSseServer({
      chunks: [frameWithNullPayload(1, "stage_start")],
      requireAuth: true,
      keepOpen: true,
    });

    const { useAgentJobEvents } = await loadHookModule();
    const { result, unmount } = renderEvents(useAgentJobEvents);

    await waitFor(() => expect(result.current.events).toHaveLength(1));
    expect(result.current.events[0]).toEqual({
      event_type: "stage_start",
      payload: {},
      sequence: 1,
    });
    unmount();
  });
});

describe("AgentJobEventPanel — CAST-01 renders payload-less/null-payload frames without throwing", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({ VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("renders a frame whose payload is absent without throwing", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    installSseServer({
      chunks: [frameWithoutPayload(1, "stage_start")],
      requireAuth: true,
      keepOpen: true,
    });

    const { AgentJobEventPanel } = await import("@/components/Agents/AgentJobEventPanel");
    const { findByTestId, unmount } = render(
      React.createElement(AgentJobEventPanel, { jobId: JOB_ID, jobStatus: "running" }),
    );

    expect(await findByTestId("agent-event-item-1")).toBeTruthy();
    unmount();
  });

  it("renders a frame whose payload is null without throwing", async () => {
    setEnv({ ...LOOPBACK_ON, VITE_RUNS_LOOPBACK_API_TOKEN: CHUNK_CRED });
    installSseServer({
      chunks: [frameWithNullPayload(1, "stage_start")],
      requireAuth: true,
      keepOpen: true,
    });

    const { AgentJobEventPanel } = await import("@/components/Agents/AgentJobEventPanel");
    const { findByTestId, unmount } = render(
      React.createElement(AgentJobEventPanel, { jobId: JOB_ID, jobStatus: "running" }),
    );

    expect(await findByTestId("agent-event-item-1")).toBeTruthy();
    unmount();
  });
});
