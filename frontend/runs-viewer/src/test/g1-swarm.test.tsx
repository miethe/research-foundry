/**
 * g1-swarm.test.tsx — v2.3 Stage-1 nav + swarm + row-click tests.
 *
 * D2: run-scoped sidebar items (Runs, Reports, Ledger, Swarm) are ABSENT from NAV_ITEMS.
 *     Global tabs present: Portfolio, Library, Policies, Alerts, Settings, Help.
 * D1: Clicking a RunTable <tr> opens the run modal (setModalRunId).
 * D6: Swarm tab present in RunDetailWorkspace on both page and modal.
 * D4 (integration): onNavigate is threaded from RunDetailModal → DetailModal.
 */

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { AppShell } from "@/app/AppShell";
import { RunDetailWorkspace } from "@/components/RunDetail/RunDetailWorkspace";
import { RunDetailModal } from "@/components/RunDetail/RunDetailModal";
import { RunTable } from "@/screens/RunList";
import type { RFRunExport, RFClaim } from "@/types/rf";
import type { RunCardData } from "@/components/RunList/RunCard";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeRun(runId: string): RFRunExport {
  return {
    schema_version: "1.1",
    run_id: runId,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: true, passed: true, exit_code: 0, checks: [] },
    governance: null,
    timeline: null,
  };
}

function makeRunWithSwarm(runId: string): RFRunExport {
  return {
    ...makeRun(runId),
    title: "Swarm Test Run",
    context: {
      routing_decision: {
        decision: "rf_domain_researcher",
        rationale: "Domain-specific discovery required.",
      },
      swarm_plan: {
        swarm: "discovery_swarm",
        agents: ["rf_source_scout"],
        adapters: ["web_fetch"],
      },
    },
  };
}

function makeRunCardData(run: RFRunExport): RunCardData {
  return {
    run_id: run.run_id,
    status_derived: run.status_derived,
    created_at: null,
    sensitivity: null,
    claim_counts: null,
    title: (run as { title?: string }).title ?? null,
    linked_projects: null,
    category: null,
    tags: null,
  };
}

function makeWrapper(initialPath = "/runs") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialPath]}>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

// ── D2: Run-scoped items absent from sidebar nav ──────────────────────────────

describe("D2 — sidebar cleanup: run-scoped items absent from NAV_ITEMS", () => {
  it("Runs nav item is ABSENT from the sidebar", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const runsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Runs",
    );
    expect(runsBtn).toBeUndefined();
  });

  it("Reports nav item is ABSENT from the sidebar", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const reportsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Reports",
    );
    expect(reportsBtn).toBeUndefined();
  });

  it("Ledger nav item is ABSENT from the sidebar", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const ledgerBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Ledger",
    );
    expect(ledgerBtn).toBeUndefined();
  });

  it("Swarm nav item is ABSENT from the sidebar", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn).toBeUndefined();
  });

  it("Portfolio nav item is present and active at /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const pfBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Portfolio",
    );
    expect(pfBtn).not.toBeUndefined();
    expect(pfBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Catalog nav item is present (was Library, renamed Phase 0)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/catalog"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const catBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Catalog",
    );
    expect(catBtn).not.toBeUndefined();
    expect(catBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Policies nav item is present and active at /policies", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/policies"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const plBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    );
    expect(plBtn).not.toBeUndefined();
    expect(plBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Alerts nav item is present and active at /alerts", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/alerts"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alBtn).not.toBeUndefined();
    expect(alBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Settings nav item is present and active at /settings", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const stBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Settings",
    );
    expect(stBtn).not.toBeUndefined();
    expect(stBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Help nav item is present and active at /help", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/help"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const hpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    );
    expect(hpBtn).not.toBeUndefined();
    expect(hpBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("exactly 8 nav items are present (Portfolio, Catalog, Builder, Agents, Policies, Alerts, Settings, Help)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    expect(navButtons.length).toBe(8);
  });
});

// ── D1: RunTable row click opens modal ───────────────────────────────────────

describe("D1 — RunTable row click opens run modal", () => {
  it("clicking a table row calls onOpen with the run_id", () => {
    const onOpen = vi.fn();
    const onSelect = vi.fn();
    const run = makeRun("test_run_001");
    const runs: RunCardData[] = [makeRunCardData(run)];

    const { container } = render(
      <RunTable
        runs={runs}
        selectedRunId={null}
        onSelect={onSelect}
        onOpen={onOpen}
      />,
      { wrapper: makeWrapper() },
    );

    const row = container.querySelector("[data-testid='run-table-row']");
    expect(row).not.toBeNull();
    act(() => { fireEvent.click(row!); });
    expect(onOpen).toHaveBeenCalledWith("test_run_001");
  });

  it("pressing Enter on a focused table row calls onOpen", () => {
    const onOpen = vi.fn();
    const run = makeRun("test_run_002");
    const runs: RunCardData[] = [makeRunCardData(run)];

    const { container } = render(
      <RunTable
        runs={runs}
        selectedRunId={null}
        onSelect={() => {}}
        onOpen={onOpen}
      />,
      { wrapper: makeWrapper() },
    );

    const row = container.querySelector("[data-testid='run-table-row']");
    expect(row).not.toBeNull();
    act(() => { fireEvent.keyDown(row!, { key: "Enter" }); });
    expect(onOpen).toHaveBeenCalledWith("test_run_002");
  });

  it("pressing Space on a focused table row calls onOpen", () => {
    const onOpen = vi.fn();
    const run = makeRun("test_run_003");
    const runs: RunCardData[] = [makeRunCardData(run)];

    const { container } = render(
      <RunTable
        runs={runs}
        selectedRunId={null}
        onSelect={() => {}}
        onOpen={onOpen}
      />,
      { wrapper: makeWrapper() },
    );

    const row = container.querySelector("[data-testid='run-table-row']");
    expect(row).not.toBeNull();
    act(() => { fireEvent.keyDown(row!, { key: " " }); });
    expect(onOpen).toHaveBeenCalledWith("test_run_003");
  });

  it("table row has tabIndex=0 and role=row for keyboard operability", () => {
    const run = makeRun("test_run_004");
    const { container } = render(
      <RunTable
        runs={[makeRunCardData(run)]}
        selectedRunId={null}
        onSelect={() => {}}
        onOpen={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='run-table-row']");
    expect(row?.getAttribute("tabindex")).toBe("0");
    expect(row?.getAttribute("role")).toBe("row");
  });

  it("clicking the inner Open button calls onOpen without double-firing via row", () => {
    const onOpen = vi.fn();
    const run = makeRun("test_run_005");

    const { container } = render(
      <RunTable
        runs={[makeRunCardData(run)]}
        selectedRunId={null}
        onSelect={() => {}}
        onOpen={onOpen}
      />,
      { wrapper: makeWrapper() },
    );

    const openBtn = container.querySelector(".rv-table-open");
    expect(openBtn).not.toBeNull();
    act(() => { fireEvent.click(openBtn!); });
    // onOpen called exactly once (stopPropagation prevents double-fire)
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith("test_run_005");
  });

  it("clicking inner title button calls onSelect, not onOpen", () => {
    const onOpen = vi.fn();
    const onSelect = vi.fn();
    const run = makeRun("test_run_006");

    const { container } = render(
      <RunTable
        runs={[makeRunCardData(run)]}
        selectedRunId={null}
        onSelect={onSelect}
        onOpen={onOpen}
      />,
      { wrapper: makeWrapper() },
    );

    const titleBtn = container.querySelector(".rv-table-link");
    expect(titleBtn).not.toBeNull();
    act(() => { fireEvent.click(titleBtn!); });
    expect(onSelect).toHaveBeenCalledWith("test_run_006");
    expect(onOpen).not.toHaveBeenCalled();
  });
});

// ── D6: Context tab present in RunDetailWorkspace (FR-14: renamed from Swarm) ─

describe("D6 — Context tab in RunDetailWorkspace (page + modal)", () => {
  it("Context tab button is present in the workspace tab bar", () => {
    const run = makeRun("test_run_context_page");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="overview"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const contextTab = container.querySelector("[data-testid='detail-tab-context']");
    expect(contextTab).not.toBeNull();
    expect(contextTab!.textContent).toBe("Context");
  });

  it("Context tab button is present in modal mode", () => {
    const run = makeRun("test_run_context_modal");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const contextTab = container.querySelector("[data-testid='detail-tab-context']");
    expect(contextTab).not.toBeNull();
  });

  it("clicking Context tab fires onTabChange with 'context'", () => {
    const onTabChange = vi.fn();
    const run = makeRun("test_run_context_click");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="overview"
        mode="page"
        onTabChange={onTabChange}
      />,
      { wrapper: makeWrapper() },
    );
    const contextTab = container.querySelector("[data-testid='detail-tab-context']") as HTMLButtonElement;
    expect(contextTab).not.toBeNull();
    act(() => { fireEvent.click(contextTab); });
    expect(onTabChange).toHaveBeenCalledWith("context");
  });

  it("Context tabpanel renders ContextPane with unavailable state when schema < 1.3", () => {
    // makeRun() sets schema_version "1.1" — context pane should show unavailable state
    const run = makeRun("test_run_context_unavailable");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const tabpanel = container.querySelector("[data-testid='tabpanel-context']");
    expect(tabpanel).not.toBeNull();
    const contextPane = container.querySelector("[data-testid='context-pane']");
    expect(contextPane).not.toBeNull();
    // Unavailable state shown when schema < 1.3
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
    expect(unavailable!.textContent).toContain("Context not available for this run");
  });

  it("Context tabpanel renders ContextPane with panels when schema >= 1.3 and context present", () => {
    const run: RFRunExport = {
      ...makeRunWithSwarm("test_run_context_content"),
      schema_version: "1.3",
    };
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const tabpanel = container.querySelector("[data-testid='tabpanel-context']");
    expect(tabpanel).not.toBeNull();
    // Should show collapsible sections (collapsed by default — headers visible)
    const routingSection = container.querySelector("[data-testid='context-section-routing']");
    expect(routingSection).not.toBeNull();
    const swarmSection = container.querySelector("[data-testid='context-section-swarm']");
    expect(swarmSection).not.toBeNull();
  });

  it("RunDetailModal has Context tab in the workspace (via pre-seeded cache)", async () => {
    const run = makeRunWithSwarm("test_run_modal_context");
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
    });
    qc.setQueryData(["rf", "runs", "detail", run.run_id], run);

    const { container } = render(
      <MemoryRouter>
        <QueryClientProvider client={qc}>
          <RunDetailModal runId={run.run_id} onClose={() => {}} />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    // Wait for run data to load from cache
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    const contextTab = container.querySelector("[data-testid='detail-tab-context']");
    expect(contextTab).not.toBeNull();
    expect(contextTab!.textContent).toBe("Context");
  });

  it("Ledger tab is still present in RunDetailWorkspace", () => {
    const run = makeRun("test_run_ledger_present");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="overview"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='detail-tab-ledger']")).not.toBeNull();
  });

  it("Report tab is still present in RunDetailWorkspace", () => {
    const run = makeRun("test_run_report_present");
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="overview"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='detail-tab-report']")).not.toBeNull();
  });
});

// ── Regression: Portfolio active state ───────────────────────────────────────

describe("Regression — Portfolio active state unaffected by D2", () => {
  it("Portfolio is active at /runs (run list)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const pfBtn = Array.from(
      container.querySelectorAll(".rv-shell-nav__item"),
    ).find((btn) => btn.querySelector("strong")?.textContent === "Portfolio");
    expect(pfBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Portfolio is active on a run detail page /runs/:runId", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs/test_run_abc"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const pfBtn = Array.from(
      container.querySelectorAll(".rv-shell-nav__item"),
    ).find((btn) => btn.querySelector("strong")?.textContent === "Portfolio");
    expect(pfBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Settings is active at /settings", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const stBtn = Array.from(
      container.querySelectorAll(".rv-shell-nav__item"),
    ).find((btn) => btn.querySelector("strong")?.textContent === "Settings");
    expect(stBtn!.getAttribute("aria-current")).toBe("page");
  });
});

// ── D4 integration: onNavigate threaded from RunDetailModal → DetailModal ─────
//
// Verifies that the `onNavigate` prop is actually wired through RunDetailModal
// to DetailModal so the navigate action button appears when a lineage node is
// expanded from modal context (regression guard for the missing prop bug).

describe("D4 (integration) — RunDetailModal threads onNavigate into DetailModal", () => {
  function makeRunWithClaim(runId: string): RFRunExport {
    const claim: RFClaim = {
      claim_id: "clm_integration_001",
      text: "Integration test claim",
      status: "supported",
      sources: [
        {
          source_card_id: "src_int_001",
          evidence_id: "ev_int_001",
          relation: "supports",
          resolved: true,
          dangling: false,
          title: "Integration Source",
        },
      ],
    };
    return {
      schema_version: "1.1",
      run_id: runId,
      status_derived: "verified",
      claims: [claim],
      claim_counts: null,
      verification: { present: true, passed: true, exit_code: 0, checks: [] },
      governance: null,
      timeline: null,
    };
  }

  it("detail-modal-navigate button is present after expanding a lineage node from RunDetailModal", async () => {
    const runId = "test_run_d4_integration";
    const run = makeRunWithClaim(runId);

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
    });
    qc.setQueryData(["rf", "runs", "detail", runId], run);

    const { container } = render(
      <MemoryRouter>
        <QueryClientProvider client={qc}>
          <RunDetailModal runId={runId} onClose={vi.fn()} />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    // Wait for run data to hydrate from cache
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    // Switch to Lineage tab
    const lineageTab = container.querySelector("[data-testid='detail-tab-lineage']") as HTMLButtonElement | null;
    expect(lineageTab).not.toBeNull();
    act(() => { fireEvent.click(lineageTab!); });

    // The lineage tree root is a "run" kind node (no navigate action).
    // Its first child is a "source" kind node (navigate action → lineage tab).
    // Both are expanded by default (defaultExpanded in ArtifactLineageGraph).
    const sourceNode = container.querySelector("[data-kind='source']") as HTMLElement | null;
    expect(sourceNode).not.toBeNull();
    act(() => { fireEvent.click(sourceNode!); });

    // The navigate button should now be visible — confirming onNavigate was passed
    // from RunDetailModal → DetailModal (the D4 wiring fix).
    const navigateBtn = container.querySelector("[data-testid='detail-modal-navigate']");
    expect(navigateBtn).not.toBeNull();
  });
});
