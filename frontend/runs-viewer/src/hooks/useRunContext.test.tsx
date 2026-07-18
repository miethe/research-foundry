/**
 * useRunContext.test.tsx — DFR-001 hybrid embed + lazy-load hook tests.
 *
 * Covers:
 *   - small embedded context → used directly, no network call (offline fast path)
 *   - large embedded context + API available → live fetch wins, source "api"
 *   - live fetch failure → silent fallback to the embedded context
 *   - live fetch timeout (2s) → silent fallback to the embedded context
 *   - API unavailable (static export) → offline invariant: embedded only, ever
 *
 * Mocks @/api/client's isLoopbackEnabled/fetchRunContext (mirrors the
 * src/hooks/useAssertions.test.tsx mocking pattern for API-boundary hooks).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import type { RFRunExport } from "@/types/rf";
import type { RFRunContextSummary } from "@/types/rf/run-export";

const mocks = vi.hoisted(() => ({
  fetchRunContext: vi.fn(),
  isLoopbackEnabled: vi.fn(),
}));

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    fetchRunContext: mocks.fetchRunContext,
    isLoopbackEnabled: mocks.isLoopbackEnabled,
  };
});

import { CONTEXT_FETCH_TIMEOUT_MS, useRunContext } from "./useRunContext";

// ── Test helpers ──────────────────────────────────────────────────────────────

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

let _runIdCounter = 0;
function makeRun(
  context: RFRunContextSummary | null,
  schemaVersion = "1.3",
): RFRunExport {
  const id = ++_runIdCounter;
  return {
    schema_version: schemaVersion,
    run_id: `rf_run_ctx_${id}`,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: null,
    governance: null,
    timeline: null,
    context,
  };
}

const SMALL_CONTEXT: RFRunContextSummary = {
  routing_decision: { decision: "rf_domain_researcher", rationale: "Small routing block." },
  research_brief_md: "# Small Brief\n\nJust a few lines.",
  swarm_plan: { swarm: "discovery_swarm", agents: ["rf_source_scout"] },
  upstream_entities: { intent_id: "intent_small_001" },
};

/** Serializes well past the 200 KB threshold via a padded research_brief_md. */
const LARGE_CONTEXT: RFRunContextSummary = {
  routing_decision: { decision: "rf_domain_researcher", rationale: "Large routing block." },
  research_brief_md: "# Large Brief\n\n" + "x".repeat(210_000),
  swarm_plan: { swarm: "discovery_swarm", agents: ["rf_source_scout"] },
  upstream_entities: { intent_id: "intent_large_001" },
};

const API_CONTEXT: RFRunContextSummary = {
  routing_decision: { decision: "rf_domain_researcher", rationale: "Freshly fetched from the API." },
  research_brief_md: "# Live Brief",
  swarm_plan: { swarm: "discovery_swarm", agents: ["rf_source_scout", "rf_domain_researcher"] },
  upstream_entities: { intent_id: "intent_live_001" },
};

describe("useRunContext (DFR-001)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses the embedded context directly with no network call when it is small", async () => {
    mocks.isLoopbackEnabled.mockReturnValue(true); // API available — must still skip the fetch
    const run = makeRun(SMALL_CONTEXT);

    const { result } = renderHook(() => useRunContext(run), { wrapper });

    expect(result.current).toEqual({
      context: SMALL_CONTEXT,
      source: "embedded",
      isFetching: false,
    });
    expect(mocks.fetchRunContext).not.toHaveBeenCalled();
  });

  it("prefers a successful live fetch over a large embedded context", async () => {
    mocks.isLoopbackEnabled.mockReturnValue(true);
    mocks.fetchRunContext.mockResolvedValue(API_CONTEXT);
    const run = makeRun(LARGE_CONTEXT);

    const { result } = renderHook(() => useRunContext(run), { wrapper });

    await waitFor(() => expect(result.current.source).toBe("api"));
    expect(result.current.context).toEqual(API_CONTEXT);
    expect(result.current.isFetching).toBe(false);
    expect(mocks.fetchRunContext).toHaveBeenCalledWith(
      run.run_id,
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("falls back to the embedded context when the live fetch fails", async () => {
    mocks.isLoopbackEnabled.mockReturnValue(true);
    mocks.fetchRunContext.mockRejectedValue(new Error("network error"));
    const run = makeRun(LARGE_CONTEXT);

    const { result } = renderHook(() => useRunContext(run), { wrapper });

    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(result.current.context).toEqual(LARGE_CONTEXT);
    expect(result.current.source).toBe("embedded");
  });

  it(
    "falls back to the embedded context when the live fetch exceeds the 2s timeout",
    async () => {
      mocks.isLoopbackEnabled.mockReturnValue(true);
      // Mimics real fetch()'s AbortController contract: never settles until aborted
      // by the hook's own timeout wrapper. Real timers are used here (rather than
      // vi.useFakeTimers) because React Query's internal scheduling depends on
      // microtask/MessageChannel timing that fake timers don't reliably drive.
      mocks.fetchRunContext.mockImplementation(
        (_runId: string, options?: { signal?: AbortSignal }) =>
          new Promise((_resolve, reject) => {
            options?.signal?.addEventListener("abort", () => {
              reject(Object.assign(new Error("The operation was aborted."), { name: "AbortError" }));
            });
          }),
      );
      const run = makeRun(LARGE_CONTEXT);

      const { result } = renderHook(() => useRunContext(run), { wrapper });
      expect(result.current.isFetching).toBe(true);

      await waitFor(() => expect(result.current.isFetching).toBe(false), {
        timeout: CONTEXT_FETCH_TIMEOUT_MS + 2_000,
      });
      expect(result.current.context).toEqual(LARGE_CONTEXT);
      expect(result.current.source).toBe("embedded");
    },
    CONTEXT_FETCH_TIMEOUT_MS + 5_000,
  );

  it("offline invariant: never calls the API and always uses the embedded context when the loopback API is unavailable", async () => {
    mocks.isLoopbackEnabled.mockReturnValue(false); // static export mode
    const run = makeRun(LARGE_CONTEXT);

    const { result } = renderHook(() => useRunContext(run), { wrapper });

    expect(result.current).toEqual({
      context: LARGE_CONTEXT,
      source: "embedded",
      isFetching: false,
    });
    expect(mocks.fetchRunContext).not.toHaveBeenCalled();

    // Null embedded context in static mode → graceful "none", never throws/blocks.
    const emptyRun = makeRun(null);
    const { result: emptyResult } = renderHook(() => useRunContext(emptyRun), { wrapper });
    expect(emptyResult.current).toEqual({ context: null, source: "none", isFetching: false });
  });

  it("never fetches for a pre-1.3-schema run even with a null embedded context and the loopback API enabled", async () => {
    // ContextPane's schema guard discards context for schema_version < "1.3"
    // regardless of what the hook resolves, so a fetch here would always be
    // wasted work (up to the full 2s timeout) on every ContextPane mount.
    mocks.isLoopbackEnabled.mockReturnValue(true);
    const run = makeRun(null, "1.2");

    const { result } = renderHook(() => useRunContext(run), { wrapper });

    expect(result.current).toEqual({ context: null, source: "none", isFetching: false });
    expect(mocks.fetchRunContext).not.toHaveBeenCalled();
  });
});
