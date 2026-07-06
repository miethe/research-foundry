/**
 * BuilderScreen tests — public-multiuser-p2p3, Phase 3 / Wave F
 * (+ visual-fidelity polish pass: F1-F8, demo-data fallback).
 *
 * Static mode only (no VITE_RUNS_FRONTEND_LOOPBACK_API in the test env), so
 * this renders the read-only demo draft path end to end:
 *   - AppShell's Builder nav item is enabled and routes to /builder.
 *   - BuilderScreen renders the static-mode banner + the demo draft
 *     (lib/builderMocks.ts) hydrated into the Draft Report card (outline +
 *     editor folded into ONE card, F2) / inspector / basket.
 *   - BuilderCatalogPane's left pane uses the SAME static catalog index as
 *     CatalogScreen (useCatalog hooks unchanged by this wave) — a small run
 *     fixture is faked via globalThis.fetch exactly like catalog-screen.test.tsx.
 *   - Checking a catalog row stages it in the Claim Basket.
 *   - Selecting a different outline section swaps the visible block group.
 *   - A second describe block covers the demo-catalog fallback (F5/"demo
 *     data") when the real catalog is empty in static mode.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BuilderScreen } from "@/screens/BuilderScreen";
import { AppShell } from "@/app/AppShell";
import { __resetCatalogIndexCacheForTests } from "@/api/client";
import type { RFRunExport, RFRunSummary } from "@/types/rf";

// ── Catalog fixture (feeds BuilderCatalogPane's left pane) ───────────────────

const RUN_ID = "rf_run_builder_test";

const RUN_FIXTURE: RFRunExport = {
  schema_version: "1.3",
  run_id: RUN_ID,
  status_derived: "verified",
  sensitivity: "public",
  created_at: "2026-01-01T00:00:00Z",
  claims: [
    {
      claim_id: "c1",
      text: "Hybrid retrieval reduces latency across CPU-only deployments significantly.",
      status: "supported",
      claim_type: "factual",
      confidence: "high",
      sources: [
        {
          source_card_id: "src_a",
          evidence_id: "ev_a",
          relation: "supports",
          resolved: true,
          dangling: false,
          title: "Benchmark Paper",
          source_type: "paper",
          sensitivity: "public",
        },
      ],
    },
  ],
  claim_counts: null,
  verification: null,
  governance: null,
  timeline: null,
  report_draft: null,
};

const INDEX_FIXTURE: RFRunSummary[] = [
  { run_id: RUN_ID, status_derived: "verified", created_at: "2026-01-01T00:00:00Z", sensitivity: "public", claim_counts: null, title: null },
];

function makeJsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function make404Response(url: string): Response {
  return new Response(`Not found: ${url}`, { status: 404 });
}

function installFetchMock(index: RFRunSummary[], runsById: Record<string, RFRunExport>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;
    if (url.endsWith("/data/index.json") || url === "data/index.json") return makeJsonResponse(index);
    const match = url.match(/\/data\/([^/]+)\/run\.json$/);
    if (match) {
      const runId = decodeURIComponent(match[1]!);
      if (runsById[runId]) return makeJsonResponse(runsById[runId]);
      return make404Response(url);
    }
    return make404Response(url);
  }) as unknown as typeof fetch;
}

let previousFetch: typeof fetch;

beforeEach(() => {
  __resetCatalogIndexCacheForTests();
  previousFetch = globalThis.fetch;
  installFetchMock(INDEX_FIXTURE, { [RUN_ID]: RUN_FIXTURE });
});

afterEach(() => {
  globalThis.fetch = previousFetch;
});

function renderBuilder() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <MemoryRouter initialEntries={["/builder"]}>
      <QueryClientProvider client={qc}>
        <BuilderScreen />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

// ── Nav ───────────────────────────────────────────────────────────────────────

describe("AppShell — Builder nav item", () => {
  it("is enabled and current at /builder", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/builder"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const builderBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Builder",
    ) as HTMLButtonElement | undefined;
    expect(builderBtn).not.toBeUndefined();
    expect(builderBtn!.disabled).toBe(false);
    expect(builderBtn!.getAttribute("aria-current")).toBe("page");
  });
});

// ── BuilderScreen (static/demo-draft mode) ────────────────────────────────────

describe("BuilderScreen — static mode with mock draft", () => {
  it("renders the workspace regions hydrated from the bundled demo draft", async () => {
    renderBuilder();

    expect(await screen.findByTestId("builder-screen")).toBeInTheDocument();

    // Static-mode read-only banner (loopback-only v1 choice).
    expect(screen.getByTestId("builder-static-banner")).toBeInTheDocument();

    // F4: compact topbar — project control + relative "Saved" indicator (not
    // a verbose absolute timestamp) + a reserved run-context slot.
    expect(screen.getByText("Report Builder")).toBeInTheDocument();
    expect(screen.getByTestId("builder-project-select")).toHaveTextContent("Retrieval Architecture Comparison");
    expect(screen.getByTestId("builder-saved-indicator")).toHaveTextContent(/Saved/);
    expect(screen.getByTestId("builder-saved-indicator").textContent).not.toMatch(/\d{4}-\d{2}-\d{2}/);
    expect(screen.getByTestId("builder-run-context")).toHaveTextContent("rf_run_20260614_hybrid_bm25_vector_and_ft5s_ranking");

    // F2: outline + editor are ONE "Draft Report" card, with the title above both.
    const draftCard = screen.getByTestId("builder-draftcard");
    expect(within(draftCard).getByTestId("builder-outline")).toBeInTheDocument();
    expect(within(draftCard).getByTestId("builder-block-editor")).toBeInTheDocument();
    expect(screen.getByTestId("builder-title-input")).toHaveDisplayValue(/Hybrid Retrieval: BM25, Vector, FTS5/);

    // Outline renders numbered sections from the demo draft, unabbreviated.
    const outline = screen.getByTestId("builder-outline");
    expect(within(outline).getByText("Executive summary")).toBeInTheDocument();
    expect(within(outline).getByText("Architecture overview")).toBeInTheDocument();

    // Block editor shows the active (first) section's blocks with claim chips.
    expect(screen.getByTestId("builder-claim-chip-clm_043")).toBeInTheDocument();

    // F3: Audit inspector renders carded sections with badges + correct action buttons.
    expect(screen.getByTestId("builder-audit-inspector")).toBeInTheDocument();
    expect(screen.getByTestId("builder-inspector-pct-pill")).toBeInTheDocument();
    const verifyBtn = screen.getByTestId("builder-verify-draft");
    expect(verifyBtn.className).toContain("rv-builder-btn-verify");
    const publishBtn = screen.getByTestId("builder-publish-preview");
    expect(publishBtn.className).toContain("rv-builder-split-btn__main");
    expect(screen.getByTestId("builder-publish-preview-caret")).toBeInTheDocument();

    // Claim basket bottom bar present (empty until a catalog row is checked).
    expect(screen.getByTestId("claim-basket")).toBeInTheDocument();
    expect(screen.getByTestId("claim-basket-count")).toHaveTextContent("0 items selected");
  });

  it("disables mutation controls (verify/publish/toolbar) in static mode", async () => {
    renderBuilder();
    await screen.findByTestId("builder-screen");
    expect(screen.getByTestId("builder-verify-draft")).toBeDisabled();
    expect(screen.getByTestId("builder-publish-preview")).toBeDisabled();
    expect(screen.getByTestId("builder-outline-add-section")).toBeDisabled();
  });

  it("switches the visible section when an outline item is clicked", async () => {
    renderBuilder();
    await screen.findByTestId("builder-screen");

    fireEvent.click(screen.getByTestId("builder-outline-item-b_h2"));

    const editor = screen.getByTestId("builder-block-editor");
    expect(within(editor).getByText(/Architecture overview/)).toBeInTheDocument();
  });

  it("stages a catalog claim into the Claim Basket when its row is checked", async () => {
    renderBuilder();
    await screen.findByTestId("builder-screen");

    const row = await screen.findByTestId("builder-catalog-row-c1");
    fireEvent.click(row);

    expect(screen.getByTestId("claim-basket-count")).toHaveTextContent("1 item selected");
    expect(screen.getByTestId("claim-basket-chip-c1")).toBeInTheDocument();
  });

  it("F6: claim chips fold status into a colored dot, not a separate full-width pill", async () => {
    renderBuilder();
    await screen.findByTestId("builder-screen");

    const chip = screen.getByTestId("builder-claim-chip-clm_043");
    expect(chip.querySelector(".rv-builder-claim-chip__dot")).not.toBeNull();
    // The old separate coverage-status pill row is gone.
    expect(document.querySelector(".rv-builder-block__coverage-chip")).toBeNull();
  });
});

// ── Demo catalog fallback (F5 / "demo data") ──────────────────────────────────

describe("BuilderCatalogPane — demo fallback when the real catalog is empty", () => {
  it("shows the bundled 6-claim demo set, including the cited clm_042/043/044", async () => {
    installFetchMock([], {}); // genuinely empty static catalog
    renderBuilder();
    await screen.findByTestId("builder-screen");

    // Falls back to the demo set for the default "Claims" tab.
    expect(await screen.findByTestId("builder-catalog-row-clm_043")).toBeInTheDocument();
    expect(screen.getByTestId("builder-catalog-row-clm_042")).toBeInTheDocument();
    expect(screen.getByTestId("builder-catalog-row-clm_044")).toBeInTheDocument();

    // F5 scaffolding: pill filter row + sort/count strip render even with no live data.
    expect(screen.getByTestId("builder-catalog-status-pill")).toBeInTheDocument();
    expect(screen.getByTestId("builder-catalog-count")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("builder-catalog-more-filters"));
    expect(screen.getByText("Materiality ▾")).toBeInTheDocument();

    // Inferences tab also resolves from the demo set (clm_038).
    fireEvent.click(screen.getByTestId("builder-catalog-tab-inference"));
    expect(await screen.findByTestId("builder-catalog-row-clm_038")).toBeInTheDocument();
  });
});
