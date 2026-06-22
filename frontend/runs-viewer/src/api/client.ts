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
 *     Fetches from a local RF API server (rf serve, default port 7432).
 *     Gated behind import.meta.env.VITE_RUNS_FRONTEND_LOOPBACK_API="true".
 *
 * Env vars (Mode B):
 *   VITE_RUNS_FRONTEND_LOOPBACK_API  Set to "true" to activate loopback mode.
 *   VITE_RUNS_LOOPBACK_API_BASE      Override API base URL (default: http://127.0.0.1:7432/api).
 *   VITE_RUNS_LOOPBACK_API_TOKEN     Shared-secret token for auth_mode=token (injected at build
 *                                    time; omit header when not set). See frontend/runs-viewer/README.md.
 *
 * NO POST/PUT/DELETE methods are exported. This is a read-only viewer.
 * The R9 sensitivity gate lives in the Python export service; this client
 * never has access to governed content.
 */

import type { RFRunExport, RFRunSummary } from "@/types/rf";
import type { GovernanceConfig } from "@/types/governance";
import { getViewerSettings } from "@/lib/viewerSettings";

// ── Env flag ─────────────────────────────────────────────────────────────────

const LOOPBACK_ENABLED =
  typeof import.meta !== "undefined" &&
  (import.meta.env?.VITE_RUNS_FRONTEND_LOOPBACK_API === "true" ||
   import.meta.env?.VITE_RUNS_FRONTEND_LOOPBACK_API === true);

const LOOPBACK_BASE =
  import.meta.env?.VITE_RUNS_LOOPBACK_API_BASE ?? "http://127.0.0.1:7432/api";

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

// ── Data path helper ──────────────────────────────────────────────────────────

/**
 * Returns the normalized static data base path from viewer settings.
 *
 * The stored dataPath (e.g. '/data') has leading and trailing slashes stripped
 * so it can be safely concatenated: `${getStaticDataBase()}/index.json`.
 *
 * Default: '/data' → 'data' (same URLs as before this feature was added).
 *
 * Called at request time (not at module init) so that changes saved via
 * SettingsScreen take effect after the next page reload.
 */
function getStaticDataBase(): string {
  const raw = getViewerSettings().dataPath; // e.g. '/data', 'data', '/my/custom/path'
  return raw.replace(/^\/+|\/+$/g, ""); // strip leading/trailing slashes → 'data'
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

/**
 * AUTH-HEADER CONTRACT (P4-SEAM — implemented in Phase P5)
 *
 * When VITE_RUNS_LOOPBACK_API_TOKEN is set and non-empty:
 *   - MUST send `Authorization: Bearer ${VITE_RUNS_LOOPBACK_API_TOKEN}`
 *   - Token value is injected at Vite build time (not from runtime JS)
 *
 * When VITE_RUNS_LOOPBACK_API_TOKEN is absent or empty:
 *   - The Authorization header MUST be omitted entirely
 *   - MUST NOT send `Authorization: Bearer ` (empty string after "Bearer ")
 *
 * On HTTP 401 from the server:
 *   - Surface via ClientError — do NOT silently swallow it
 *
 * Full server-side contract lives in:
 *   src/research_foundry/api/middleware/auth.py (AUTH-HEADER CONTRACT block)
 */
async function loopbackGet<T>(path: string): Promise<T> {
  const url = `${LOOPBACK_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  // Build headers per the auth-header contract: inject Authorization only when
  // the token env var is set AND non-empty (Vite bakes it in at build time).
  const token: string = import.meta.env?.VITE_RUNS_LOOPBACK_API_TOKEN ?? "";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { method: "GET", headers });
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
  return staticGet<RFRunSummary[]>(`${getStaticDataBase()}/index.json`);
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
    return await staticGet<RFRunExport>(`${getStaticDataBase()}/${encodeURIComponent(runId)}/run.json`);
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

// ── Governance Config ─────────────────────────────────────────────────────────

/**
 * GET /data/governance.json → static governance config snapshot.
 *
 * Fetches the governance config baked into the build by prebuild-static-data.mjs.
 * Returns an empty GovernanceConfig object if the file is absent (404) or invalid.
 * Never throws — callers can always safely access the returned object.
 */
export async function fetchGovernanceConfig(): Promise<GovernanceConfig> {
  try {
    return await staticGet<GovernanceConfig>(`${getStaticDataBase()}/governance.json`);
  } catch {
    // File absent or unparseable — return empty config gracefully
    return {};
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
