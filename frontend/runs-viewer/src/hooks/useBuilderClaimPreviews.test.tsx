/**
 * useBuilderClaimPreviews.test.tsx — AC-5 live-mode coverage for
 * runs-viewer-builder-live-claim-previews.
 *
 * client.ts reads LOOPBACK_ENABLED as a module-level constant, so — matching
 * the established pattern in src/test/p5-auth-header.test.ts — we use
 * vi.resetModules() + a dynamic import in each test to force a fresh module
 * evaluation with VITE_RUNS_FRONTEND_LOOPBACK_API="true".
 *
 * The mocked fetch response bodies below are captured verbatim (shape, not
 * content) from a live `rf serve` smoke against the LAN node's
 * GET /api/catalog/items/{id} — see the Completion Report's AC-7 section for
 * the exact recorded payload. This closes the never-verified assumption at
 * reportsClient.ts:23-28 for THIS payload (report_draft/claim_link fields
 * were separately verified via GET /api/reports/{id} in the same smoke).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReportClaimLink } from "@/types/rf/report_draft";

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

function link(overrides: Partial<ReportClaimLink> & { claim_link_id: string; block_id: string; claim_id: string }): ReportClaimLink {
  return {
    source_run_id: null,
    catalog_item_id: null,
    relation: "supports",
    span_start: 0,
    span_end: 10,
    quote_text_hash: null,
    link_status: "linked",
    ...overrides,
  };
}

// Verbatim shape observed from the live `rf serve` smoke (GET /api/catalog/items/ci_02665bb4cfd2).
const LIVE_CLAIM_ITEM = {
  catalog_item_id: "ci_02665bb4cfd2",
  item_type: "claim",
  title: "In the absence of a copyright statement on a PMC article…",
  summary: "In the absence of a copyright statement…",
  run_id: "rf_run_20260719_content_rights_and_licensing_review_what",
  local_ref: "clm_025",
  project: "pediatric-cds-platform",
  status: "supported",
  sensitivity: "personal",
  trust_label: "supported",
  confidence: "medium",
  source_count: 1,
  created_at: "2026-07-19T14:28:13-04:00",
  updated_at: "2026-07-19T14:28:13-04:00",
  payload: {
    text: "In the absence of a copyright statement on a PMC article, users should assume that standard copyright protection applies unless the article explicitly states otherwise.",
    materiality: "background",
    claim_type: "attribution",
    inference_basis: { from_claims: [], reasoning_summary: null },
    report_locations: [],
    cited_sources: [
      { source_card_id: "src_20260719_reg002_13", evidence_id: "ev_001", relation: "supports", locator: "PMC Copyright Notice" },
    ],
  },
  links: { outgoing: [], incoming: [], citing_drafts: [] },
  rf_schema_version: "1.0.0",
};

function makeJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useBuilderClaimPreviewResolver — loopback mode (AC-1/AC-3/AC-5)", () => {
  let previousFetch: typeof fetch;

  beforeEach(() => {
    vi.resetModules();
    previousFetch = globalThis.fetch;
    setEnv({ VITE_RUNS_FRONTEND_LOOPBACK_API: "true", VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api" });
  });

  afterEach(() => {
    globalThis.fetch = previousFetch;
    setEnv({ VITE_RUNS_FRONTEND_LOOPBACK_API: undefined, VITE_RUNS_LOOPBACK_API_BASE: undefined });
  });

  it("resolves a real claim link to a BuilderClaimPreview built from the live catalog-item payload shape", async () => {
    globalThis.fetch = vi.fn(async () => makeJsonResponse(LIVE_CLAIM_ITEM)) as unknown as typeof fetch;

    const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
    const links = [link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_025", catalog_item_id: "ci_02665bb4cfd2" })];

    const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });

    await waitFor(() => {
      const preview = result.current.resolve("clm_025");
      expect(preview).not.toBe("unknown");
    });

    const preview = result.current.resolve("clm_025");
    if (preview === "unknown") throw new Error("expected a resolved preview");
    expect(preview.text).toBe(LIVE_CLAIM_ITEM.payload.text);
    expect(preview.confidence).toBe("medium");
    expect(preview.materiality).toBe("background");
    expect(preview.status).toBe("supported");
    // normalizeCatalogItemDetail (api/client.ts) maps cited_sources -> sources
    // for claim/inference items — this is the exact seam AC-7 verifies.
    expect(preview.sources).toHaveLength(1);
    expect(preview.sources[0]?.source_card_id).toBe("src_20260719_reg002_13");
  });

  it("resolves to the explicit 'unknown' state — never a fabricated low-confidence preview — on 404 (AC-3)", async () => {
    globalThis.fetch = vi.fn(async () => makeJsonResponse({ detail: "catalog item not found" }, 404)) as unknown as typeof fetch;

    const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
    const links = [link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_missing", catalog_item_id: "ci_deleted" })];

    const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });

    await waitFor(() => {
      expect(result.current.resolve("clm_missing")).toBe("unknown");
    });
  });

  it("resolves to 'unknown' immediately when a claim link has no catalog_item_id — never blocks on a fetch that can't happen", () => {
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
    return (async () => {
      const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
      const links = [link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_orphan", catalog_item_id: null })];

      const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });
      expect(result.current.resolve("clm_orphan")).toBe("unknown");
      expect(globalThis.fetch).not.toHaveBeenCalled();
    })();
  });

  it("pins the fix-pass defect: a live item with `confidence: null` (the real production shape — GET /api/catalog/search on 10.42.10.76:7432 returns distinct confidence values of exactly [null, 'medium']) resolves to a fully-populated preview with confidence 'unknown', NOT a fabricated 'medium'", async () => {
    const NULL_CONFIDENCE_ITEM = { ...LIVE_CLAIM_ITEM, confidence: null };
    globalThis.fetch = vi.fn(async () => makeJsonResponse(NULL_CONFIDENCE_ITEM)) as unknown as typeof fetch;

    const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
    const links = [link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_025", catalog_item_id: "ci_02665bb4cfd2" })];

    const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });

    await waitFor(() => {
      const preview = result.current.resolve("clm_025");
      expect(preview).not.toBe("unknown");
    });

    const preview = result.current.resolve("clm_025");
    if (preview === "unknown") throw new Error("expected a resolved preview");
    // The claim itself is real and fully resolved — text/status/sources still
    // come through — only confidence is honestly reported as unknown.
    expect(preview.confidence).toBe("unknown");
    expect(preview.confidence).not.toBe("medium");
    expect(preview.text).toBe(NULL_CONFIDENCE_ITEM.payload.text);
    expect(preview.status).toBe("supported");
  });
});

// ── builder-claim-previews-loading-affordance: isLoading / isPending ────────

describe("useBuilderClaimPreviewResolver — pending affordance (AC-1/AC-4)", () => {
  let previousFetch: typeof fetch;

  beforeEach(() => {
    vi.resetModules();
    previousFetch = globalThis.fetch;
    setEnv({ VITE_RUNS_FRONTEND_LOOPBACK_API: "true", VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api" });
  });

  afterEach(() => {
    globalThis.fetch = previousFetch;
    setEnv({ VITE_RUNS_FRONTEND_LOOPBACK_API: undefined, VITE_RUNS_LOOPBACK_API_BASE: undefined });
  });

  it("isLoading is true while the catalog-item fetch is in flight, false once it settles", async () => {
    let resolveFetch!: (res: Response) => void;
    globalThis.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    ) as unknown as typeof fetch;

    const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
    const links = [link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_025", catalog_item_id: "ci_02665bb4cfd2" })];

    const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });

    // In flight — isLoading true, and resolve() has not yet fabricated an answer.
    expect(result.current.isLoading).toBe(true);

    resolveFetch(makeJsonResponse(LIVE_CLAIM_ITEM));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.resolve("clm_025")).not.toBe("unknown");
  });

  it("AC-4: isPending is false for a claim link with no catalog_item_id even while a sibling claim is still loading", async () => {
    let resolveFetch!: (res: Response) => void;
    globalThis.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    ) as unknown as typeof fetch;

    const { useBuilderClaimPreviewResolver } = await import("./useBuilderClaimPreviews");
    const links = [
      link({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_pending", catalog_item_id: "ci_02665bb4cfd2" }),
      link({ claim_link_id: "l2", block_id: "b2", claim_id: "clm_orphan", catalog_item_id: null }),
    ];

    const { result } = renderHook(() => useBuilderClaimPreviewResolver(links), { wrapper });

    // The sibling with a catalog_item_id is still in flight...
    expect(result.current.isLoading).toBe(true);
    expect(result.current.isPending("clm_pending")).toBe(true);
    // ...but the orphan (no catalog_item_id) never had a fetch to wait on.
    expect(result.current.isPending("clm_orphan")).toBe(false);
    expect(result.current.resolve("clm_orphan")).toBe("unknown");

    resolveFetch(makeJsonResponse(LIVE_CLAIM_ITEM));

    await waitFor(() => {
      expect(result.current.isPending("clm_pending")).toBe(false);
    });
    expect(result.current.isPending("clm_orphan")).toBe(false);
  });
});
