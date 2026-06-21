/**
 * G1-swarm tests — SwarmScreen component tests + isActiveNav coverage for Swarm.
 *
 * Covers:
 *   TEST-G1-01: routing_decision card renders agent + rationale when present
 *   TEST-G1-02: swarm_plan section renders when data present (structured + array)
 *   TEST-G1-03: full empty state when context is null (pre-F5 exports)
 *   TEST-G1-04: isActiveNav returns true for Swarm at /runs/:runId/swarm
 *   SMOKE-G1-01: Swarm nav item enabled and not disabled
 *   SMOKE-G1-02: SwarmScreen renders without crash with data present
 *   SMOKE-G1-03: SwarmScreen renders without crash with context absent
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SwarmScreen } from "@/screens/SwarmScreen";
import { AppShell } from "@/app/AppShell";
import type { RFRunExport } from "@/types/rf";

// ── Fixtures ──────────────────────────────────────────────────────────────────

/** Minimal run with no context block (pre-F5 export). */
function makeRunNoContext(runId: string): RFRunExport {
  return {
    schema_version: "1.1",
    run_id: runId,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: true, passed: true, exit_code: 0, checks: [] },
    governance: null,
    timeline: null,
    // context deliberately absent
  };
}

/** Run with null context (explicit null — pre-F5). */
function makeRunNullContext(runId: string): RFRunExport {
  return {
    ...makeRunNoContext(runId),
    context: null,
  };
}

/** Run with a populated context block (post-F5 export). */
function makeRunWithSwarmData(runId: string): RFRunExport {
  return {
    ...makeRunNoContext(runId),
    title: "My Test Research Run",
    context: {
      routing_decision: {
        decision: "rf_domain_researcher",
        rationale: "Chosen because the query requires domain-specific source discovery.",
      },
      swarm_plan: {
        swarm: "discovery_swarm",
        agents: ["rf_source_scout", "rf_deep_reader"],
        adapters: ["web_fetch", "pubmed"],
      },
    },
  };
}

/** Run with routing_decision only (swarm_plan absent). */
function makeRunWithRoutingOnly(runId: string): RFRunExport {
  return {
    ...makeRunNoContext(runId),
    context: {
      routing_decision: {
        decision: "rf_synthesizer",
        rationale: "Synthesis-only run; no discovery needed.",
      },
      swarm_plan: null,
    },
  };
}

// ── Test helpers ───────────────────────────────────────────────────────────────

function renderSwarmInRoute(run: RFRunExport) {
  const runId = run.run_id;
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  // Pre-seed cache so useRunDetail returns synchronously
  qc.setQueryData(["rf", "runs", "detail", runId], run);

  return render(
    <MemoryRouter initialEntries={[`/runs/${encodeURIComponent(runId)}/swarm`]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route path="/runs/:runId/swarm" element={<SwarmScreen />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

// ── SMOKE-G1-01: Swarm nav item enabled ───────────────────────────────────────

describe("isActiveNav — Swarm nav item (AC G1-05, SMOKE-G1-01)", () => {
  it("Swarm nav button is NOT disabled when a runId is in the URL", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs/run_abc/swarm"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    ) as HTMLButtonElement | undefined;
    expect(swarmBtn).not.toBeUndefined();
    expect(swarmBtn!.disabled).toBe(false);
  });

  it("Swarm nav button does NOT have data-state='disabled'", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs/run_abc/swarm"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn!.getAttribute("data-state")).toBe("contextual");
  });

  it("Swarm nav button has aria-current='page' when pathname ends with /swarm", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs/run_abc/swarm"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn).not.toBeUndefined();
    expect(swarmBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Swarm nav button does NOT have aria-current='page' on /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("Swarm nav button is disabled when no runId is active (on /runs)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    ) as HTMLButtonElement | undefined;
    expect(swarmBtn).not.toBeUndefined();
    expect(swarmBtn!.disabled).toBe(true);
  });

  it("enabling Swarm nav does not break Alerts active state at /alerts", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/alerts"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alertsBtn!.getAttribute("aria-current")).toBe("page");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn!.getAttribute("aria-current")).toBeNull();
  });
});

// ── SMOKE-G1-03 / TEST-G1-03: Full empty state when context absent ────────────

describe("SwarmScreen — full empty state when context absent (AC G1-04, SMOKE-G1-03, TEST-G1-03)", () => {
  it("renders the swarm screen container when context is absent", () => {
    const run = makeRunNoContext("run_no_ctx");
    const { container } = renderSwarmInRoute(run);
    expect(container.querySelector("[data-testid='swarm-screen']")).not.toBeNull();
  });

  it("shows 'Swarm data not available' message when context is undefined", () => {
    const run = makeRunNoContext("run_no_ctx_2");
    const { container } = renderSwarmInRoute(run);
    const empty = container.querySelector("[data-testid='swarm-context-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Swarm data not available");
  });

  it("shows 'Re-export this run' guidance when context is undefined", () => {
    const run = makeRunNoContext("run_no_ctx_3");
    const { container } = renderSwarmInRoute(run);
    const empty = container.querySelector("[data-testid='swarm-context-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent!.toLowerCase()).toContain("re-export");
  });

  it("shows full empty state when context is explicitly null", () => {
    const run = makeRunNullContext("run_null_ctx");
    const { container } = renderSwarmInRoute(run);
    const empty = container.querySelector("[data-testid='swarm-context-empty']");
    expect(empty).not.toBeNull();
  });

  it("does NOT throw a JS error when context is absent", () => {
    const run = makeRunNoContext("run_no_ctx_safe");
    expect(() => renderSwarmInRoute(run)).not.toThrow();
  });
});

// ── SMOKE-G1-02 / TEST-G1-01: Routing Decision card with data ─────────────────

describe("SwarmScreen — routing decision card (AC G1-02, SMOKE-G1-02, TEST-G1-01)", () => {
  it("renders swarm screen without crash when routing_decision is present", () => {
    const run = makeRunWithSwarmData("run_full");
    expect(() => renderSwarmInRoute(run)).not.toThrow();
  });

  it("renders the routing decision section", () => {
    const run = makeRunWithSwarmData("run_routing");
    const { container } = renderSwarmInRoute(run);
    expect(container.querySelector("[data-testid='swarm-routing-section']")).not.toBeNull();
  });

  it("renders the routing decision card with agent name", () => {
    const run = makeRunWithSwarmData("run_agent");
    const { container } = renderSwarmInRoute(run);
    const card = container.querySelector("[data-testid='swarm-routing-card']");
    expect(card).not.toBeNull();
    expect(card!.textContent).toContain("rf_domain_researcher");
  });

  it("renders the routing decision rationale text", () => {
    const run = makeRunWithSwarmData("run_rationale");
    const { container } = renderSwarmInRoute(run);
    const rationale = container.querySelector("[data-testid='swarm-routing-rationale']");
    expect(rationale).not.toBeNull();
    expect(rationale!.textContent).toContain("Chosen because");
  });

  it("renders 'No routing decision' placeholder when routing_decision is absent", () => {
    const run = makeRunNoContext("run_no_routing");
    // Give it a context but no routing_decision
    const runWithEmptyContext: RFRunExport = {
      ...run,
      context: { routing_decision: null, swarm_plan: null },
    };
    const { container } = renderSwarmInRoute(runWithEmptyContext);
    const empty = container.querySelector("[data-testid='swarm-routing-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("No routing decision recorded");
  });
});

// ── SMOKE-G1-02 / TEST-G1-02: Swarm plan section with data ───────────────────

describe("SwarmScreen — swarm plan section (AC G1-03, SMOKE-G1-02, TEST-G1-02)", () => {
  it("renders the swarm plan section", () => {
    const run = makeRunWithSwarmData("run_plan");
    const { container } = renderSwarmInRoute(run);
    expect(container.querySelector("[data-testid='swarm-plan-section']")).not.toBeNull();
  });

  it("renders structured swarm plan with swarm/agents/adapters", () => {
    const run = makeRunWithSwarmData("run_structured");
    const { container } = renderSwarmInRoute(run);
    const structured = container.querySelector("[data-testid='swarm-plan-structured']");
    expect(structured).not.toBeNull();
    expect(structured!.textContent).toContain("discovery_swarm");
  });

  it("renders agents from swarm_plan.agents", () => {
    const run = makeRunWithSwarmData("run_agents");
    const { container } = renderSwarmInRoute(run);
    const structured = container.querySelector("[data-testid='swarm-plan-structured']");
    expect(structured).not.toBeNull();
    expect(structured!.textContent).toContain("rf_source_scout");
  });

  it("renders 'No swarm plan' placeholder when swarm_plan is absent", () => {
    const run = makeRunWithRoutingOnly("run_no_plan");
    const { container } = renderSwarmInRoute(run);
    const empty = container.querySelector("[data-testid='swarm-plan-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("No swarm plan recorded");
  });

  it("renders the agents section chip list when agents can be derived", () => {
    const run = makeRunWithSwarmData("run_chips");
    const { container } = renderSwarmInRoute(run);
    expect(container.querySelector("[data-testid='swarm-agents-section']")).not.toBeNull();
    const chips = container.querySelectorAll("[data-testid='swarm-agent-chip']");
    expect(chips.length).toBeGreaterThan(0);
  });
});

// ── Regression guard: existing nav items not broken ───────────────────────────

describe("Swarm nav — no regression on existing nav items", () => {
  it("Portfolio is still active at /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const pfBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Portfolio",
    );
    expect(pfBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Settings is still active at /settings", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const settingsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Settings",
    );
    expect(settingsBtn!.getAttribute("aria-current")).toBe("page");
  });
});
