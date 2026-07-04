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
import type { CatalogItemDetail, CatalogSearchParams, CatalogSearchResult, CatalogStats } from "@/types/rf/catalog";
import { getViewerSettings } from "@/lib/viewerSettings";
import { buildCatalogIndex, catalogStats as computeCatalogStats, getCatalogItem, searchCatalog } from "@/lib/catalog";
import type { CatalogIndex } from "@/lib/catalog";

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

// ── Evidence Catalog (public-multiuser-p0p1, Phase 1) ────────────────────────

/**
 * Static-mode index build is expensive (fetchRunList + N×fetchRunDetail), so
 * it is memoized as a module-level promise (D4: "cache the built index in
 * module/queryClient"). The memoization is intentionally NOT tied to any
 * TanStack QueryClient instance so it behaves identically whichever
 * QueryClientProvider wraps the app (real app vs. test harness).
 */
let catalogIndexPromise: Promise<CatalogIndex> | null = null;

async function getCatalogIndex(): Promise<CatalogIndex> {
  if (!catalogIndexPromise) {
    catalogIndexPromise = (async () => {
      const summaries = await fetchRunList();
      const runs = await Promise.all(summaries.map((s) => fetchRunDetail(s.run_id)));
      return buildCatalogIndex(runs);
    })();
  }
  return catalogIndexPromise;
}

/**
 * Test-only escape hatch: forces the next getCatalogIndex() call to rebuild
 * from the CURRENT fetchRunList/fetchRunDetail responses instead of reusing
 * the memoized static-mode index. Not used by app code.
 */
export function __resetCatalogIndexCacheForTests(): void {
  catalogIndexPromise = null;
}

function catalogSearchQueryString(params: CatalogSearchParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.item_type) query.set("item_type", params.item_type);
  if (params.project) query.set("project", params.project);
  if (params.status) query.set("status", params.status);
  if (params.sensitivity) query.set("sensitivity", params.sensitivity);
  if (params.run_id) query.set("run_id", params.run_id);
  if (params.sort) query.set("sort", params.sort);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

/**
 * GET /api/catalog/stats → per-item-type counts + runs_indexed + last_import_at.
 *
 * Static mode: derived from the client-built catalog index (see getCatalogIndex).
 * Loopback mode: calls the RF catalog API.
 */
export async function fetchCatalogStats(): Promise<CatalogStats> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet<CatalogStats>("/catalog/stats");
  }
  const index = await getCatalogIndex();
  return computeCatalogStats(index);
}

/**
 * GET /api/catalog/search?... → paginated, filtered, sorted catalog items + facets.
 *
 * Static mode: filters/sorts/paginates the client-built index via searchCatalog().
 * Loopback mode: calls the RF catalog API with the same query param contract.
 */
export async function fetchCatalogSearch(params: CatalogSearchParams = {}): Promise<CatalogSearchResult> {
  if (LOOPBACK_ENABLED) {
    return loopbackGet<CatalogSearchResult>(`/catalog/search${catalogSearchQueryString(params)}`);
  }
  const index = await getCatalogIndex();
  return searchCatalog(index, params);
}

/**
 * GET /api/catalog/items/:catalogItemId → full item detail (summary + payload + links).
 *
 * Returns null when the item is not found (404 in loopback mode; absent from
 * the index in static mode) — never throws for a plain not-found.
 */
export async function fetchCatalogItem(catalogItemId: string): Promise<CatalogItemDetail | null> {
  if (LOOPBACK_ENABLED) {
    try {
      return await loopbackGet<CatalogItemDetail>(`/catalog/items/${encodeURIComponent(catalogItemId)}`);
    } catch (err) {
      if (err instanceof ClientError && err.status === 404) return null;
      throw err;
    }
  }
  const index = await getCatalogIndex();
  return getCatalogItem(index, catalogItemId);
}
