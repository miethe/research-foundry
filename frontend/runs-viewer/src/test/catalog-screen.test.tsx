/**
 * Catalog screen tests — replaces g4-library.test.tsx (public-multiuser-p0p1,
 * Phase 1 frontend / Wave C).
 *
 * Covers:
 *   - Nav + /library→/catalog redirect equivalents (kept from g4-library).
 *   - CatalogScreen renders its loading state, then the tab strip with live
 *     counts sourced from useCatalogStats.
 *   - Tab switching shows the right item type's rows.
 *   - Free-text search (debounced) filters rows.
 *   - Selecting a row populates the inspector.
 *   - Disabled "Add to Report" / "Run Follow-up Research" actions carry the
 *     Phase 3/4 tooltip text.
 *   - Reports / Report-ready tabs show the absorbed old-Library content
 *     (published report entries; reusable outputs + writeback artifacts).
 *
 * Static-mode data control: overrides globalThis.fetch locally (this file
 * only — restored in afterEach) to serve custom index.json / run.json
 * fixtures, and resets client.ts's memoized catalog index cache before each
 * test via __resetCatalogIndexCacheForTests so each test rebuilds from its
 * own fetch mock instead of reusing a prior test's cached index.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { CatalogScreen } from "@/screens/CatalogScreen";
import { AppShell } from "@/app/AppShell";
import { __resetCatalogIndexCacheForTests } from "@/api/client";
import type { RFRunExport, RFRunSummary } from "@/types/rf";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const RUN_ID = "rf_run_catalog_test";

const RUN_FIXTURE: RFRunExport = {
  schema_version: "1.3",
  run_id: RUN_ID,
  status_derived: "verified",
  sensitivity: "public",
  created_at: "2026-01-01T00:00:00Z",
  linked_projects: ["TestProj"],
  claims: [
    {
      claim_id: "c1",
      text: "Hybrid retrieval reduces latency across CPU-only deployments significantly.",
      status: "supported",
      claim_type: "factual",
      confidence: "high",
      report_locations: [{ heading: "Findings" }],
      sources: [
        {
          source_card_id: "src_a",
          evidence_id: "ev_a",
          relation: "supports",
          resolved: true,
          dangling: false,
          title: "Benchmark Paper",
          source_type: "paper",
          url: "https://example.com/paper",
          trust: { source_rank: "primary" },
          usage: { allowed_for_public_output: true, citation_required: true },
          sensitivity: "public",
          evidence_locator: "p.12",
          summary: "Benchmark summary text.",
          quote: "Verbatim quote text.",
        },
      ],
    },
    {
      claim_id: "c2",
      text: "Therefore hybrid retrieval should be the default configuration.",
      status: "inference",
      claim_type: "inference",
      confidence: "medium",
      inference_basis: { from_claims: ["c1"], reasoning_summary: "Because c1 shows the latency reduction." },
      sources: [],
    },
  ],
  claim_counts: null,
  verification: null,
  governance: null,
  timeline: null,
  report_draft: "# Catalog Test Report\n\nIntro paragraph body text for the report.\n\nMore detail follows.",
  reusable_output_candidates: [{ description: "Reusable retrieval eval harness", is_skillbom_candidate: true }],
  writebacks: {
    targets: [{ name: "MeatyWiki", destination: "meatywiki://kb", status: "Published" }],
    approved_for_writeback: true,
  },
};

const INDEX_FIXTURE: RFRunSummary[] = [
  {
    run_id: RUN_ID,
    status_derived: "verified",
    created_at: "2026-01-01T00:00:00Z",
    sensitivity: "public",
    claim_counts: null,
    title: null,
  },
];

function makeJsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function make404Response(url: string): Response {
  return new Response(`Not found: ${url}`, { status: 404 });
}

let previousFetch: typeof fetch;

beforeEach(() => {
  __resetCatalogIndexCacheForTests();
  previousFetch = globalThis.fetch;
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;

    if (url.endsWith("/data/index.json") || url === "data/index.json") {
      return makeJsonResponse(INDEX_FIXTURE);
    }
    const match = url.match(/\/data\/([^/]+)\/run\.json$/);
    if (match) {
      const runId = decodeURIComponent(match[1]!);
      if (runId === RUN_ID) return makeJsonResponse(RUN_FIXTURE);
      return make404Response(url);
    }
    return make404Response(url);
  }) as unknown as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = previousFetch;
});

// ── Render helper ─────────────────────────────────────────────────────────────

function renderCatalog() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <MemoryRouter initialEntries={["/catalog"]}>
      <QueryClientProvider client={qc}>
        <CatalogScreen />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

// ── Nav + redirect equivalents (kept from g4-library.test.tsx) ───────────────

describe("isActiveNav — Catalog nav item (kept from g4-library)", () => {
  it("Catalog nav button is enabled and current at /catalog", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/catalog"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const catBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Catalog",
    ) as HTMLButtonElement | undefined;
    expect(catBtn).not.toBeUndefined();
    expect(catBtn!.disabled).toBe(false);
    expect(catBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Catalog nav button stays current at the /library redirect alias", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/library"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const catBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Catalog",
    );
    expect(catBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("/library redirects to /catalog", () => {
    function LocationDisplay() {
      const location = useLocation();
      return <div data-testid="location">{location.pathname}</div>;
    }
    const { container } = render(
      <MemoryRouter initialEntries={["/library"]}>
        <Routes>
          <Route path="/library" element={<Navigate to="/catalog" replace />} />
          <Route path="/catalog" element={<LocationDisplay />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(container.querySelector("[data-testid='location']")?.textContent).toBe("/catalog");
  });
});

// ── CatalogScreen — loading + tab counts ─────────────────────────────────────

describe("CatalogScreen — loading state and tab counts", () => {
  it("shows a loading state before the static-mode index resolves", () => {
    renderCatalog();
    expect(screen.getByTestId("catalog-screen")).toBeInTheDocument();
    expect(screen.getByTestId("catalog-loading")).toBeInTheDocument();
  });

  it("renders the tab strip with live counts once the index resolves", async () => {
    renderCatalog();
    const claimsTab = await screen.findByTestId("catalog-tab-claim");
    expect(claimsTab.textContent).toContain("Claims");
    expect(claimsTab.textContent).toContain("1"); // one claim (c1)

    const inferenceTab = screen.getByTestId("catalog-tab-inference");
    expect(inferenceTab.textContent).toContain("1"); // one inference (c2)

    const sourceTab = screen.getByTestId("catalog-tab-source");
    expect(sourceTab.textContent).toContain("1"); // one deduped source

    const reportTab = screen.getByTestId("catalog-tab-report");
    expect(reportTab.textContent).toContain("1");

    const reportReadyTab = screen.getByTestId("catalog-tab-report-ready");
    expect(reportReadyTab.textContent).toContain("2"); // reusable_output + writeback
  });
});

// ── Tab switching ─────────────────────────────────────────────────────────────

describe("CatalogScreen — tab switching", () => {
  it("shows the claim row on the default Claims tab", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    const row = await screen.findByTestId(/^catalog-row-ci_/);
    expect(row.textContent).toContain("Hybrid retrieval reduces latency");
  });

  it("switching to Sources shows the deduped source row", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    fireEvent.click(screen.getByTestId("catalog-tab-source"));
    await waitFor(() => {
      expect(screen.getByTestId("catalog-results-table").textContent).toContain("Benchmark Paper");
    });
  });

  it("switching to Reports shows the published-report entry (absorbed Library semantics)", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    fireEvent.click(screen.getByTestId("catalog-tab-report"));
    await waitFor(() => {
      expect(screen.getByTestId("catalog-results-table").textContent).toContain("Catalog Test Report");
    });
  });

  it("switching to Report-ready shows reusable outputs + writeback artifacts (absorbed Library semantics)", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    fireEvent.click(screen.getByTestId("catalog-tab-report-ready"));
    const reusableGroup = await screen.findByTestId("catalog-group-reusable");
    expect(reusableGroup.textContent).toContain("Reusable retrieval eval harness");
    const writebackGroup = await screen.findByTestId("catalog-group-writeback");
    expect(writebackGroup.textContent).toContain("MeatyWiki");
  });
});

// ── Free-text search ──────────────────────────────────────────────────────────

describe("CatalogScreen — free-text search", () => {
  it("filters rows by a debounced search query", async () => {
    const { container } = renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    await screen.findByTestId(/^catalog-row-ci_/);

    fireEvent.change(screen.getByTestId("catalog-search-input"), { target: { value: "hybrid retrieval" } });

    await waitFor(
      () => {
        expect(screen.getByTestId("catalog-results-table").textContent).toContain("Hybrid retrieval");
      },
      { timeout: 2000 },
    );

    fireEvent.change(screen.getByTestId("catalog-search-input"), { target: { value: "no-match-xyz" } });

    await waitFor(
      () => {
        expect(screen.queryByTestId("catalog-results-table")).toBeNull();
      },
      { timeout: 2000 },
    );
    // Scope to the main results column — the inspector rail also renders its
    // own (unrelated) empty-state, so assert on the main column's content.
    const mainColumn = container.querySelector(".rv-catalog-main");
    expect(mainColumn?.textContent).toContain("No items match the current filters.");
  });
});

// ── Selection → inspector ─────────────────────────────────────────────────────

describe("CatalogScreen — selecting a row populates the inspector", () => {
  it("shows the empty inspector state before any selection", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    expect(screen.getByTestId("catalog-inspector-empty")).toBeInTheDocument();
  });

  it("populates the inspector with the selected claim's provenance and source cards", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    const row = await screen.findByTestId(/^catalog-row-ci_/);
    fireEvent.click(row);

    const inspector = await screen.findByTestId("catalog-inspector");
    expect(inspector.textContent).toContain("c1");
    expect(screen.getByTestId("catalog-provenance")).toBeInTheDocument();
    expect(screen.getByTestId("catalog-inspector-sources").textContent).toContain("Benchmark Paper");
  });

  it("shows disabled action buttons with the Phase 3/4 planned tooltips", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    const row = await screen.findByTestId(/^catalog-row-ci_/);
    fireEvent.click(row);
    await screen.findByTestId("catalog-inspector");

    const addToReport = screen.getByTestId("catalog-action-add-to-report") as HTMLButtonElement;
    expect(addToReport.disabled).toBe(true);
    expect(addToReport.getAttribute("title")).toBe("Planned — Report Builder (Phase 3)");

    const followUp = screen.getByTestId("catalog-action-followup-research") as HTMLButtonElement;
    expect(followUp.disabled).toBe(true);
    expect(followUp.getAttribute("title")).toBe("Planned — Agent Research (Phase 4)");
  });

  it("shows an 'Open run' action that opens the run detail modal", async () => {
    renderCatalog();
    await screen.findByTestId("catalog-tab-claim");
    const row = await screen.findByTestId(/^catalog-row-ci_/);
    fireEvent.click(row);
    await screen.findByTestId("catalog-inspector");

    fireEvent.click(screen.getByTestId("catalog-action-open-run"));
    const modal = await screen.findByTestId("run-detail-modal");
    expect(modal.getAttribute("data-run-id")).toBe(RUN_ID);
  });
});
