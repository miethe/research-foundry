/**
 * Vitest global test setup for the RF Runs Viewer.
 *
 * - Loads @testing-library/jest-dom matchers
 * - Stubs EventSource for jsdom (prevents "EventSource is not defined")
 * - Mocks global fetch so the rewired static-mode API client works in jsdom
 *   (jsdom has no HTTP server; we intercept fetch and return fixture data)
 */
import "@testing-library/jest-dom/vitest";
import { vi, beforeAll, afterAll } from "vitest";

// Inline fixture imports (build-time, no network needed in tests)
import fixtureRunRaw    from "@/test/fixtures/run.json";
import scaffoldRunRaw   from "@/test/fixtures/scaffold-run.json";

// ── fetch mock ────────────────────────────────────────────────────────────────
// The rewired client calls:
//   fetch(`${BASE_URL}data/index.json`)         → RFRunSummary[]
//   fetch(`${BASE_URL}data/<runId>/run.json`)   → RFRunExport
//
// In jsdom BASE_URL resolves to "/" so URLs look like:
//   /data/index.json
//   /data/rf_run_xxx/run.json
//
// We synthesise a minimal 2-entry index from the two bundled fixtures and
// serve the right full fixture when the run ID matches.

const FIXTURE_RUN_ID     = (fixtureRunRaw as { run_id?: string }).run_id   ?? "rf_run_test_fixture";
const SCAFFOLD_RUN_ID    = (scaffoldRunRaw as { run_id?: string }).run_id  ?? "rf_run_scaffold";

const SYNTHETIC_INDEX = [
  {
    run_id:         FIXTURE_RUN_ID,
    status_derived: (fixtureRunRaw as { status_derived?: string }).status_derived ?? "published",
    created_at:     (fixtureRunRaw as { created_at?: string }).created_at         ?? null,
    sensitivity:    (fixtureRunRaw as { sensitivity?: string }).sensitivity       ?? null,
    claim_counts:   (fixtureRunRaw as { claim_counts?: unknown }).claim_counts    ?? null,
  },
  {
    run_id:         SCAFFOLD_RUN_ID,
    status_derived: (scaffoldRunRaw as { status_derived?: string }).status_derived ?? "planned",
    created_at:     (scaffoldRunRaw as { created_at?: string }).created_at         ?? null,
    sensitivity:    null,
    claim_counts:   null,
  },
];

function makeJsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status:  200,
    headers: { "Content-Type": "application/json" },
  });
}

function make404Response(url: string): Response {
  return new Response(`Not found: ${url}`, { status: 404 });
}

const originalFetch = globalThis.fetch;

beforeAll(() => {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;

    // index.json → synthetic 2-entry summary list
    if (url.endsWith("/data/index.json") || url === "data/index.json") {
      return makeJsonResponse(SYNTHETIC_INDEX);
    }

    // per-run exports — strip leading slash and "data/" prefix, extract run_id
    const runDetailMatch = url.match(/\/data\/([^/]+)\/run\.json$/);
    if (runDetailMatch) {
      const runId = decodeURIComponent(runDetailMatch[1]!);
      if (runId === FIXTURE_RUN_ID)  return makeJsonResponse(fixtureRunRaw);
      if (runId === SCAFFOLD_RUN_ID) return makeJsonResponse(scaffoldRunRaw);
      return make404Response(url);
    }

    // Passthrough for anything else (loopback calls won't happen in tests)
    if (originalFetch) return originalFetch(input as Parameters<typeof fetch>[0]);
    return make404Response(url);
  });
});

afterAll(() => {
  if (originalFetch) {
    globalThis.fetch = originalFetch;
  }
});

/**
 * Minimal EventSource stub for JSDOM test environments.
 * Prevents "EventSource is not defined" for any component that might use SSE.
 */
class StubEventSource {
  static CONNECTING = 0 as const;
  static OPEN = 1 as const;
  static CLOSED = 2 as const;
  readyState = StubEventSource.CLOSED;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  constructor(_url: string) {}
  addEventListener(_type: string, _listener: EventListenerOrEventListenerObject) {}
  removeEventListener(_type: string, _listener: EventListenerOrEventListenerObject) {}
  close() {}
}

if (typeof global.EventSource === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).EventSource = StubEventSource;
}
