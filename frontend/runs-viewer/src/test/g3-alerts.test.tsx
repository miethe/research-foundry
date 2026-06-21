/**
 * G3-alerts tests — AlertsFeed component tests + isActiveNav coverage for Alerts.
 *
 * Covers:
 *   UNIT-G3-screen:        renders the screen container
 *   UNIT-G3-loading:       shows loading indicator on mount
 *   UNIT-G3-aggregation:   renders alert cards for runs that have signals
 *   UNIT-G3-empty:         renders empty-state panel when all runs are clean
 *   UNIT-G3-title-fallback: resolves run title with fallback chain
 *   UNIT-G3-view-link:     each card has a /runs/:runId link
 *   UNIT-G3-error:         renders placeholder when a per-run fetch fails
 *   UNIT-G3-nav:           isActiveNav returns true for Alerts at /alerts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AlertsFeed } from "@/screens/AlertsFeed";
import { AppShell } from "@/app/AppShell";
import type { RFRunExport, RFRunSummary } from "@/types/rf";
import * as clientModule from "@/api/client";

// ── Shared fixture helpers ────────────────────────────────────────────────────

/** Minimal clean run (no alert signals, schema 1.2). */
function makeCleanRun(runId: string): RFRunExport {
  return {
    schema_version: "1.2",
    run_id: runId,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: true, passed: true, exit_code: 0, checks: [] },
    governance: null,
    timeline: null,
  };
}

/** Run with one failed verification check (triggers failedChecks signal). */
function makeRunWithFailedCheck(runId: string): RFRunExport {
  return {
    ...makeCleanRun(runId),
    verification: {
      present: true,
      passed: false,
      exit_code: 1,
      checks: [
        { id: "check_1", severity: "error", status: "fail", detail: "failed check", locations: [] },
      ],
    },
  };
}

/** Run with unsupported claims (triggers unsupportedClaims signal). */
function makeRunWithUnsupportedClaims(runId: string): RFRunExport {
  return {
    ...makeCleanRun(runId),
    claims: [
      {
        claim_id: "clm_001",
        text: "An unsupported claim",
        status: "unsupported",
        claim_type: "factual",
        sources: [],
      },
    ],
  };
}

/** Run with schema mismatch (future schema version). */
function makeRunWithSchemaMismatch(runId: string): RFRunExport {
  return {
    ...makeCleanRun(runId),
    schema_version: "99.0",
  };
}

/** Minimal run summary for the index. */
function makeRunSummary(runId: string): RFRunSummary {
  return {
    run_id: runId,
    status_derived: "verified",
    created_at: null,
    sensitivity: null,
    claim_counts: null,
  };
}

// ── fetch mock helpers ────────────────────────────────────────────────────────

type FetchMockMap = {
  index: RFRunSummary[];
  runs: Record<string, RFRunExport | "error">;
};

function installFetchMock(config: FetchMockMap) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
        ? input.href
        : (input as Request).url;

    if (url.endsWith("/data/index.json") || url === "data/index.json") {
      return new Response(JSON.stringify(config.index), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    const runDetailMatch = url.match(/\/data\/([^/]+)\/run\.json$/);
    if (runDetailMatch) {
      const runId = decodeURIComponent(runDetailMatch[1]!);
      const runData = config.runs[runId];
      if (runData === "error") {
        return new Response("Server error", { status: 500 });
      }
      if (runData) {
        return new Response(JSON.stringify(runData), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("Not found", { status: 404 });
    }

    return new Response("Not found", { status: 404 });
  });
}

// ── UNIT-G3-screen: basic render ──────────────────────────────────────────────

describe("AlertsFeed — basic render", () => {
  beforeEach(() => {
    installFetchMock({ index: [], runs: {} });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the alerts screen container", async () => {
    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );
    // The container should be immediately present
    expect(document.querySelector("[data-testid='alerts-feed']")).not.toBeNull();
  });

  it("renders the page heading 'Alerts'", async () => {
    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );
    const h1 = document.querySelector("h1");
    expect(h1).not.toBeNull();
    expect(h1!.textContent).toBe("Alerts");
  });
});

// ── UNIT-G3-loading: shows loading indicator ──────────────────────────────────

describe("AlertsFeed — loading state", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading indicator while index.json is pending", async () => {
    // Delay the index fetch so we can observe the loading state
    let resolveIndex!: () => void;
    const indexPromise = new Promise<void>((res) => { resolveIndex = res; });

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
          ? input.href
          : (input as Request).url;

      if (url.endsWith("/data/index.json") || url === "data/index.json") {
        await indexPromise;
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("Not found", { status: 404 });
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    // Loading indicator should be present before fetch resolves
    expect(document.querySelector("[data-testid='alerts-loading']")).not.toBeNull();

    // Resolve and clean up
    act(() => { resolveIndex(); });
    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-loading']")).toBeNull();
    });
  });

  it("loading indicator disappears after all fetches complete", async () => {
    installFetchMock({
      index: [makeRunSummary("run_a")],
      runs: { run_a: makeCleanRun("run_a") },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-loading']")).toBeNull();
    });
  });
});

// ── UNIT-G3-aggregation: alert cards for runs with signals ────────────────────

describe("AlertsFeed — aggregation and card rendering (AC G3-3)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a card for a run with a failed verification check", async () => {
    const runId = "run_with_failed";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithFailedCheck(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card']")).not.toBeNull();
    });

    const card = document.querySelector(`[data-run-id='${runId}']`);
    expect(card).not.toBeNull();

    // failedChecks signal should be visible
    expect(
      document.querySelector("[data-testid='alert-signal-failedChecks']"),
    ).not.toBeNull();
  });

  it("renders a card for a run with unsupported claims", async () => {
    const runId = "run_unsupported";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithUnsupportedClaims(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        document.querySelector("[data-testid='alert-signal-unsupportedClaims']"),
      ).not.toBeNull();
    });
  });

  it("renders a card for a run with schema mismatch", async () => {
    const runId = "run_schema";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithSchemaMismatch(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        document.querySelector("[data-testid='alert-signal-schemaMismatch']"),
      ).not.toBeNull();
    });
  });

  it("does NOT render a card for a fully clean run", async () => {
    const runId = "run_clean";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeCleanRun(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    // Wait for loading to finish
    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-loading']")).toBeNull();
    });

    expect(document.querySelector("[data-testid='alert-card']")).toBeNull();
    // Empty state should be shown
    expect(document.querySelector("[data-testid='alerts-empty']")).not.toBeNull();
  });

  it("renders cards for multiple alerted runs", async () => {
    const runA = "run_a_alerts";
    const runB = "run_b_alerts";
    installFetchMock({
      index: [makeRunSummary(runA), makeRunSummary(runB)],
      runs: {
        [runA]: makeRunWithFailedCheck(runA),
        [runB]: makeRunWithUnsupportedClaims(runB),
      },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      const cards = document.querySelectorAll("[data-testid='alert-card']");
      expect(cards.length).toBe(2);
    });
  });

  it("shows only alerted run when mixed with a clean run", async () => {
    const alertedId = "run_alerted";
    const cleanId = "run_clean2";
    installFetchMock({
      index: [makeRunSummary(alertedId), makeRunSummary(cleanId)],
      runs: {
        [alertedId]: makeRunWithFailedCheck(alertedId),
        [cleanId]: makeCleanRun(cleanId),
      },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-loading']")).toBeNull();
    });

    const cards = document.querySelectorAll("[data-testid='alert-card']");
    expect(cards.length).toBe(1);
    expect(cards[0]!.getAttribute("data-run-id")).toBe(alertedId);
  });
});

// ── UNIT-G3-empty: empty state when all runs are clean (AC G3-4) ──────────────

describe("AlertsFeed — empty state (AC G3-4)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the empty-state panel when no runs have alerts", async () => {
    installFetchMock({
      index: [makeRunSummary("clean_run")],
      runs: { clean_run: makeCleanRun("clean_run") },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-empty']")).not.toBeNull();
    });
  });

  it("empty state contains 'No attention signals' message", async () => {
    installFetchMock({ index: [], runs: {} });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-empty']")).not.toBeNull();
    });

    const emptyEl = document.querySelector("[data-testid='alerts-empty']");
    expect(emptyEl!.textContent).toContain("No attention signals");
  });

  it("empty state message includes 'all runs look clean' text", async () => {
    installFetchMock({ index: [], runs: {} });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      const emptyEl = document.querySelector("[data-testid='alerts-empty']");
      expect(emptyEl).not.toBeNull();
      expect(emptyEl!.textContent!.toLowerCase()).toContain("all runs look clean");
    });
  });

  it("empty state shown when index returns zero runs", async () => {
    installFetchMock({ index: [], runs: {} });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-empty']")).not.toBeNull();
      expect(document.querySelector("[data-testid='alert-card']")).toBeNull();
    });
  });
});

// ── UNIT-G3-title-fallback: run title resolution (AC G3-5) ────────────────────

describe("AlertsFeed — title fallback chain (AC G3-5)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("displays slug-derived title when no report_draft is present", async () => {
    const runId = "rf_run_20260101_my_test_research";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithFailedCheck(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card-title']")).not.toBeNull();
    });

    const titleEl = document.querySelector("[data-testid='alert-card-title']");
    expect(titleEl!.textContent!.length).toBeGreaterThan(0);
    // Should NOT be the raw run_id (slug conversion should humanize it)
    expect(titleEl!.textContent).not.toBe(runId);
  });

  it("displays run_id as secondary monospace chip", async () => {
    const runId = "run_has_chip";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithFailedCheck(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card-run-id']")).not.toBeNull();
    });

    const chipEl = document.querySelector("[data-testid='alert-card-run-id']");
    expect(chipEl!.textContent).toBe(runId);
  });

  it("prefers report_draft H1 heading when available", async () => {
    const runId = "run_with_report";
    const runWithReport: RFRunExport = {
      ...makeRunWithFailedCheck(runId),
      report_draft: "# My Research Report\n\nSome content.",
    };
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: runWithReport },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      const titleEl = document.querySelector("[data-testid='alert-card-title']");
      expect(titleEl!.textContent).toBe("My Research Report");
    });
  });
});

// ── UNIT-G3-view-link: "View run" link (AC G3-6) ─────────────────────────────

describe("AlertsFeed — view run link (AC G3-6)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("each alert card has a 'View run' link", async () => {
    const runId = "run_link_test";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithFailedCheck(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card-view-link']")).not.toBeNull();
    });

    const link = document.querySelector("[data-testid='alert-card-view-link']") as HTMLAnchorElement;
    expect(link.textContent).toBe("View run");
    expect(link.href).toContain(`/runs/${encodeURIComponent(runId)}`);
  });

  it("view link uses encodeURIComponent for run ID with special chars", async () => {
    const runId = "run/special?id=1";
    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: makeRunWithFailedCheck(runId) },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card-view-link']")).not.toBeNull();
    });

    const link = document.querySelector("[data-testid='alert-card-view-link']") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe(`/runs/${encodeURIComponent(runId)}`);
  });
});

// ── UNIT-G3-error: per-run fetch failure (AC G3-3 resilience) ─────────────────
//
// NOTE: fetchRunDetail in client.ts has a built-in graceful fallback — on 404/network
// error it returns a minimal empty RFRunExport rather than throwing. So the "error"
// path in AlertsFeed is tested by mocking the client module directly to simulate a
// throw (e.g., from a loopback mode network failure or other unexpected error).

describe("AlertsFeed — per-run fetch error handling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows 'data unavailable' placeholder for a run when fetchRunDetail throws", async () => {
    const failedId = "run_fetch_error";

    vi.spyOn(clientModule, "fetchRunList").mockResolvedValue([makeRunSummary(failedId)]);
    vi.spyOn(clientModule, "fetchRunDetail").mockRejectedValue(new Error("Network error"));

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card-error']")).not.toBeNull();
    });

    const errCard = document.querySelector("[data-testid='alert-card-error']");
    expect(errCard!.textContent).toContain("unavailable");
  });

  it("error card does not block rendering of other successful cards", async () => {
    const failedId = "run_fail";
    const goodId = "run_good";

    vi.spyOn(clientModule, "fetchRunList").mockResolvedValue([
      makeRunSummary(failedId),
      makeRunSummary(goodId),
    ]);
    vi.spyOn(clientModule, "fetchRunDetail").mockImplementation(async (runId) => {
      if (runId === failedId) throw new Error("Network error");
      return makeRunWithFailedCheck(runId);
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alerts-loading']")).toBeNull();
    });

    expect(document.querySelector("[data-testid='alert-card-error']")).not.toBeNull();
    expect(document.querySelector("[data-testid='alert-card']")).not.toBeNull();
  });
});

// ── UNIT-G3-nav: isActiveNav for Alerts nav item ──────────────────────────────
// Tested via rendered AppShell with MemoryRouter: the Alerts nav button should
// have aria-current="page" when pathname is /alerts.

describe("isActiveNav — Alerts nav item active state", () => {
  it("Alerts nav button has aria-current='page' when pathname is /alerts", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/alerts"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alertsBtn).not.toBeUndefined();
    expect(alertsBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Alerts nav button does NOT have aria-current='page' on /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alertsBtn).not.toBeUndefined();
    expect(alertsBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("Alerts nav button is NOT disabled", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    ) as HTMLButtonElement | undefined;
    expect(alertsBtn).not.toBeUndefined();
    expect(alertsBtn!.disabled).toBe(false);
  });

  it("Alerts nav button does NOT have data-state='disabled'", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alertsBtn!.getAttribute("data-state")).toBe("enabled");
  });
});

// ── screen — test that AlertsFeed uses all 8 signal categories ───────────────

describe("AlertsFeed — all 8 signal categories rendered when present", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows all 8 signal types on a run with every signal triggered", async () => {
    const runId = "run_all_signals";
    // Build a run that triggers all 8 signals:
    // failedChecks: failed verification check
    // warningChecks: warning severity check (not failed, but warning)
    // unsupportedClaims: claim with status=unsupported
    // mixedClaims: claim with status=mixed
    // danglingSources: source with dangling=true
    // redactedSources: source with sensitivity > threshold
    // emptyInferenceBasis: inference claim with empty basis
    // schemaMismatch: unknown schema version
    const run: RFRunExport = {
      schema_version: "99.0",
      run_id: runId,
      status_derived: "verified",
      sensitivity_threshold: "public",
      claims: [
        {
          claim_id: "clm_unsupported",
          text: "Unsupported claim",
          status: "unsupported",
          claim_type: "factual",
          sources: [
            {
              source_card_id: "src_dangling",
              evidence_id: "ev_dangling",
              relation: "supports",
              dangling: true,
              resolved: false,
              sensitivity: "public",
            },
          ],
        },
        {
          claim_id: "clm_mixed",
          text: "Mixed claim",
          status: "mixed",
          claim_type: "factual",
          sources: [
            {
              source_card_id: "src_sensitive",
              evidence_id: "ev_sensitive",
              relation: "supports",
              dangling: false,
              resolved: true,
              sensitivity: "client_sensitive",
              quote: "text",
              summary: "summary",
            },
          ],
        },
        {
          claim_id: "clm_inference",
          text: "Inference with empty basis",
          status: "supported",
          claim_type: "inference",
          sources: [],
          inference_basis: { from_claims: [] },
        },
      ],
      claim_counts: null,
      verification: {
        present: true,
        passed: false,
        exit_code: 1,
        checks: [
          { id: "check_fail", severity: "error", status: "fail", detail: "failed", locations: [] },
          { id: "check_warn", severity: "warning", status: "pass", detail: "warning check", locations: [] },
        ],
      },
      governance: null,
      timeline: null,
    };

    installFetchMock({
      index: [makeRunSummary(runId)],
      runs: { [runId]: run },
    });

    render(
      <MemoryRouter>
        <AlertsFeed />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-testid='alert-card']")).not.toBeNull();
    });

    const expectedSignals = [
      "failedChecks",
      "warningChecks",
      "unsupportedClaims",
      "mixedClaims",
      "danglingSources",
      "redactedSources",
      "emptyInferenceBasis",
      "schemaMismatch",
    ];

    for (const signal of expectedSignals) {
      expect(
        document.querySelector(`[data-testid='alert-signal-${signal}']`),
        `Expected signal '${signal}' to be rendered`,
      ).not.toBeNull();
    }
  });
});
