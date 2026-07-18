/**
 * useRunContext — hybrid embed + lazy-load hook for the run Context tab
 * (DFR-001, design-spec: runs-context-panels-lazy-load-v2.md).
 *
 * Strategy:
 *   1. Small embedded context (< 200 KB serialized): use `run.context`
 *      directly, no network call — this is the ONLY path exercised by the
 *      static export build (isLoopbackEnabled() is false there), preserving
 *      the offline invariant (NFR-CP-1: panels render identically without
 *      `rf serve` running).
 *   2. Large embedded context (or none), with the loopback API available:
 *      fetch GET /api/runs/:runId/context with a 2s client-side timeout.
 *      Any failure (network error, non-2xx, or timeout) falls back silently
 *      to the embedded context — panel render is never blocked.
 *   3. Large embedded context (or none), API unavailable: use whatever was
 *      embedded (possibly null — panels show their existing empty-state).
 *
 * Deviation from the design-spec's full hybrid table: the spec's "size >= 200KB
 * OR API reachable regardless of size" trigger would fetch even when a small
 * embedded context is already available (to prefer freshness). This hook
 * intentionally skips the network call whenever the embedded context is
 * small, since the v1 embed is deterministic-at-export and the freshness
 * gain does not justify a request on every panel view for the common case.
 * Revisit if operator feedback specifically wants live-refresh for small runs.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchRunContext, isLoopbackEnabled } from "@/api/client";
import { isSchemaAtLeast13 } from "@/lib/runs";
import type { RFRunExport } from "@/types/rf";
import type { RFRunContextSummary } from "@/types/rf/run-export";

// ── Tuning constants (per design-spec §"Trigger: Size Threshold" / §"2-second timeout") ──

/** Embedded context at or above this serialized size prefers the live API fetch. */
export const CONTEXT_SIZE_THRESHOLD_BYTES = 200_000; // 200 KB

/** Client-side timeout for the live context fetch — matches existing loopback heuristics. */
export const CONTEXT_FETCH_TIMEOUT_MS = 2_000;

export type RunContextSource = "embedded" | "api" | "none";

export interface UseRunContextResult {
  /** The best-currently-known context value — embedded, live-fetched, or null. */
  context: RFRunContextSummary | null;
  /** Where `context` came from, for diagnostics/telemetry — not required for rendering. */
  source: RunContextSource;
  /** True while a live fetch is in flight (embedded value, if any, is already returned). */
  isFetching: boolean;
}

export const runContextQueryKey = (runId: string) =>
  ["rf", "runs", "context", runId] as const;

/** JSON.stringify length as a cheap proxy for the spec's "estimated size" heuristic. */
function estimateSize(context: RFRunContextSummary | null | undefined): number {
  if (!context) return 0;
  try {
    return JSON.stringify(context).length;
  } catch {
    return 0;
  }
}

/**
 * Races fetchRunContext against a hard timeout, aborting the in-flight
 * request when the timeout fires. Rejection (abort, network error, non-2xx)
 * propagates to the caller as a query error.
 */
function fetchRunContextWithTimeout(
  runId: string,
  timeoutMs: number,
): Promise<RFRunContextSummary | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetchRunContext(runId, { signal: controller.signal }).finally(() => {
    clearTimeout(timer);
  });
}

/**
 * Resolves the context block to render for a run's Context tab, per the
 * DFR-001 hybrid embed + lazy-load strategy.
 *
 * @param run - The current RFRunExport (or null/undefined while loading).
 */
export function useRunContext(run: RFRunExport | null | undefined): UseRunContextResult {
  const runId = run?.run_id ?? "";
  const embedded = run?.context ?? null;
  const embeddedIsSmall = embedded != null && estimateSize(embedded) < CONTEXT_SIZE_THRESHOLD_BYTES;

  // Only ever attempt the network path when the API is available, the run's
  // schema is new enough for ContextPane to actually render the result (its
  // schema guard discards context for pre-1.3 runs — fetching for one would
  // burn the full CONTEXT_FETCH_TIMEOUT_MS on every mount for a result that
  // is always thrown away), AND the embedded context isn't already small
  // enough to use as-is. In static export builds isLoopbackEnabled() is
  // always false, so shouldFetch is always false there — the offline
  // invariant holds structurally.
  const shouldFetch =
    Boolean(runId) &&
    isLoopbackEnabled() &&
    isSchemaAtLeast13(run?.schema_version) &&
    !embeddedIsSmall;

  const query = useQuery<RFRunContextSummary | null, Error>({
    queryKey: runContextQueryKey(runId),
    queryFn: () => fetchRunContextWithTimeout(runId, CONTEXT_FETCH_TIMEOUT_MS),
    enabled: shouldFetch,
    retry: false,
    staleTime: 30_000,
  });

  if (embeddedIsSmall) {
    return { context: embedded, source: "embedded", isFetching: false };
  }

  if (!shouldFetch) {
    // Offline / API disabled — embedded (possibly null) is the only source.
    return { context: embedded, source: embedded ? "embedded" : "none", isFetching: false };
  }

  if (query.isSuccess) {
    // The endpoint is authoritative once it responds successfully — including
    // an explicit `null` (run has no context artifacts), per the DFR-001
    // response contract (`GET /api/runs/{run_id}/context`).
    return { context: query.data, source: query.data ? "api" : "none", isFetching: false };
  }

  if (query.isError) {
    // Any failure — network error, non-2xx, or the 2s timeout abort — falls
    // back to the embedded snapshot silently. Panel render is never blocked.
    return { context: embedded, source: embedded ? "embedded" : "none", isFetching: false };
  }

  // Still resolving: show the embedded value immediately (if any) and
  // upgrade to the live value once the query settles.
  return { context: embedded, source: embedded ? "embedded" : "none", isFetching: true };
}

export default useRunContext;
