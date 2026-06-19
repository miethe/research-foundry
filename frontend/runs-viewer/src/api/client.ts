/**
 * RF Runs Viewer API Client — P2-API-CLIENT
 *
 * Dual-mode, GET-only client:
 *
 *   Mode A (default): Static fixture mode
 *     Imports the static run.json fixture bundled with the app.
 *     Works without any running server.
 *     Used for development and the default viewer deployment.
 *
 *   Mode B: Loopback API mode
 *     Fetches from a local RF API server (e.g. MeatyWiki at :8765).
 *     Gated behind import.meta.env.VITE_RUNS_FRONTEND_LOOPBACK_API="true".
 *
 * NO POST/PUT/DELETE methods are exported. This is a read-only viewer.
 * The R9 sensitivity gate lives in the Python export service; this client
 * never has access to governed content.
 */

import type { RFRunExport, RFRunSummary } from "@/types/rf";

// ── Env flag ─────────────────────────────────────────────────────────────────

const LOOPBACK_ENABLED =
  typeof import.meta !== "undefined" &&
  (import.meta.env?.VITE_RUNS_FRONTEND_LOOPBACK_API === "true" ||
   import.meta.env?.VITE_RUNS_FRONTEND_LOOPBACK_API === true);

const LOOPBACK_BASE =
  import.meta.env?.VITE_RUNS_LOOPBACK_API_BASE ?? "http://127.0.0.1:8765/api";

// ── Base URL (for static asset fetches) ──────────────────────────────────────

const BASE_URL =
  typeof import.meta !== "undefined" && import.meta.env?.BASE_URL
    ? (import.meta.env.BASE_URL as string)
    : "/";

// ── Error type ────────────────────────────────────────────────────────────────

export class ClientError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ClientError";
    this.status = status;
  }
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function loopbackGet<T>(path: string): Promise<T> {
  const url = `${LOOPBACK_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new ClientError(res.status, `Loopback GET ${url} failed: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Fetch a static JSON asset served from the public/data directory.
 * The path is relative to the Vite BASE_URL (e.g. "data/index.json").
 */
async function staticGet<T>(assetPath: string): Promise<T> {
  const base = BASE_URL.endsWith("/") ? BASE_URL : `${BASE_URL}/`;
  const url  = `${base}${assetPath}`;
  const res  = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new ClientError(res.status, `Static GET ${url} failed: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Run List ──────────────────────────────────────────────────────────────────

/**
 * GET /runs → array of run summaries.
 *
 * Static mode: fetches public/data/index.json (all 38+ run summaries).
 * Loopback mode: calls the RF API (rf run list --json → GET /api/runs).
 */
export async function fetchRunList(): Promise<RFRunSummary[]> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet<RFRunSummary[]>("/runs");
  }

  // Static mode: fetch the pre-generated run index
  return staticGet<RFRunSummary[]>("data/index.json");
}

// ── Run Detail ────────────────────────────────────────────────────────────────

/**
 * GET /runs/:runId → full denormalized run.json document.
 *
 * Static mode: fetches public/data/<runId>/run.json.
 * Loopback mode: calls GET /api/runs/:runId.
 */
export async function fetchRunDetail(runId: string): Promise<RFRunExport> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet<RFRunExport>(`/runs/${encodeURIComponent(runId)}`);
  }

  // Static mode: fetch the per-run export
  try {
    return await staticGet<RFRunExport>(`data/${encodeURIComponent(runId)}/run.json`);
  } catch {
    // Run not found in static corpus — return graceful empty shape
    return {
      schema_version: "1.0",
      run_id:         runId,
      status_derived: "planned",
      claims:         [],
      claim_counts:   null,
      verification:   null,
      governance:     null,
      timeline:       null,
    };
  }
}

// ── Claim Ledger ──────────────────────────────────────────────────────────────

/**
 * GET /runs/:runId/claims → array of claims from the run's denormalized graph.
 *
 * Static mode: filters claims from the bundled fixture.
 * Loopback mode: calls GET /api/runs/:runId/claims.
 */
export async function fetchClaimLedger(
  runId: string,
): Promise<RFRunExport["claims"]> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet<RFRunExport["claims"]>(`/runs/${encodeURIComponent(runId)}/claims`);
  }

  const run = await fetchRunDetail(runId);
  return run.claims ?? [];
}

// ── Source Card ───────────────────────────────────────────────────────────────

/**
 * GET /runs/:runId/sources/:sourceCardId → resolved source data.
 *
 * Returns the first matching resolved source from the claim graph, or null
 * if not found. Static mode scans the bundled fixture; loopback fetches the
 * dedicated endpoint.
 *
 * Returns null (not throws) when the source card is not found.
 */
export async function fetchSourceCard(
  runId: string,
  sourceCardId: string,
): Promise<import("@/types/rf").RFResolvedSource | null> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet(
      `/runs/${encodeURIComponent(runId)}/sources/${encodeURIComponent(sourceCardId)}`,
    );
  }

  const run = await fetchRunDetail(runId);
  for (const claim of run.claims) {
    const src = claim.sources.find((s) => s.source_card_id === sourceCardId);
    if (src) return src;
  }
  return null;
}
