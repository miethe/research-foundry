/**
 * fr14-context-pane.test.tsx — FR-14 Context Pane unit/integration tests.
 *
 * Covers FE-001 through FE-006 per the phase-3 plan:
 *   FE-001: null/absent context → empty-state per section + schema guard
 *   FE-002: Routing Decision — populated render + null empty-state
 *   FE-003: Research Brief   — populated render + YAML frontmatter strip + null empty-state
 *   FE-004: Swarm Plan       — tree render + raw-YAML toggle + null empty-state
 *   FE-005: Upstream Entities — all 3 IDs rendered + null empty-state
 *   FE-006: RunDetailWorkspace/ContextPane integration with full context fixture
 *
 * Uses static fixture mode (no API mock needed). The run.json fixture has been
 * extended to schema 1.3 with a full context block for these tests.
 * scaffold-run.json remains at schema 1.0 / no context for empty-state tests.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ContextPane } from "@/components/RunDetail/ContextPane";
import { RunDetailWorkspace } from "@/components/RunDetail/RunDetailWorkspace";
import type { RFRunExport } from "@/types/rf";
import type { RFRunContextSummary } from "@/types/rf/run-export";

// Fixtures
import fixtureRunRaw from "@/test/fixtures/run.json";
import scaffoldRunRaw from "@/test/fixtures/scaffold-run.json";

const fixtureRun = fixtureRunRaw as unknown as RFRunExport;
const scaffoldRun = scaffoldRunRaw as unknown as RFRunExport;

// ── Test helpers ──────────────────────────────────────────────────────────────

// Clear sessionStorage before each test so useCollapseState always starts
// with the default collapsed=true state and doesn't inherit state from prior tests.
beforeEach(() => {
  try { sessionStorage.clear(); } catch { /* ignore — unavailable in some envs */ }
});

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

/**
 * Build a minimal schema-1.3 RFRunExport with an optional context override.
 * runIdSuffix is used to create unique run_ids so sessionStorage keys don't
 * collide across tests (useCollapseState keys include run_id).
 */
let _runIdCounter = 0;
function makeRun13(context?: RFRunContextSummary | null, runIdSuffix?: string): RFRunExport {
  const id = runIdSuffix ?? String(++_runIdCounter);
  return {
    schema_version: "1.3",
    run_id: `rf_run_fr14_${id}`,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: false, passed: null, exit_code: null, checks: [] },
    governance: null,
    timeline: null,
    context: context ?? null,
  };
}

/** Full populated context used across multiple tests. */
const FULL_CONTEXT: RFRunContextSummary = {
  routing_decision: {
    decision: "rf_domain_researcher",
    rationale: "Domain-specific discovery required.",
    est_cost_usd: 0.42,
    budget_usd: 2.0,
    sensitivity_tier: "personal",
  },
  research_brief_md:
    "---\ntype: research_brief\ntitle: Test Brief\n---\n\n# Test Research Brief\n\nThis brief tests frontmatter stripping.",
  swarm_plan: {
    swarm: "discovery_swarm",
    agents: ["rf_source_scout", "rf_domain_researcher"],
    adapters: ["web_search", "web_fetch"],
    budget: {
      max_cost_usd: 2.0,
      max_runtime_minutes: 30,
    },
  },
  upstream_entities: {
    intent_id: "intent_test_001",
    ibom_id: "ibom_test_001",
    intenttree_node_id: "it_node_test_001",
  },
};

// ── FE-001: Schema guard + null/absent context ────────────────────────────────

describe("FE-001 — schema guard and null context empty-states", () => {
  it("shows unavailable state for schema < 1.3 (schema 1.2)", () => {
    const run: RFRunExport = {
      ...makeRun13(),
      schema_version: "1.2",
      context: FULL_CONTEXT,
    };
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
    expect(unavailable!.textContent).toContain("Context not available for this run");
  });

  it("shows unavailable state for schema < 1.3 (schema 1.0 scaffold run)", () => {
    const { container } = render(<ContextPane run={scaffoldRun} />, {
      wrapper: makeWrapper(),
    });
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
  });

  it("shows unavailable state when schema is 1.3 but context is null", () => {
    const run = makeRun13(null);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
  });

  it("shows unavailable state when context is absent (undefined)", () => {
    const run: RFRunExport = {
      schema_version: "1.3",
      run_id: "rf_run_no_context",
      status_derived: "verified",
      claims: [],
      claim_counts: null,
      verification: null,
      governance: null,
      timeline: null,
      // context intentionally omitted (undefined)
    };
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
  });

  it("shows 4 collapsible section headers when schema 1.3 and context present", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    expect(container.querySelector("[data-testid='context-pane-unavailable']")).toBeNull();
    expect(container.querySelector("[data-testid='context-section-routing']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-brief']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-swarm']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-upstream']")).not.toBeNull();
  });

  it("all sections are collapsed by default", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    // Collapsed sections don't render their body
    expect(container.querySelector("[data-testid='context-section-routing-body']")).toBeNull();
    expect(container.querySelector("[data-testid='context-section-brief-body']")).toBeNull();
    expect(container.querySelector("[data-testid='context-section-swarm-body']")).toBeNull();
    expect(container.querySelector("[data-testid='context-section-upstream-body']")).toBeNull();
  });

  it("no console errors on pre-1.3 run (scaffold fixture)", () => {
    // If this render throws/errors, vitest will catch it
    expect(() =>
      render(<ContextPane run={scaffoldRun} />, { wrapper: makeWrapper() })
    ).not.toThrow();
  });
});

// ── FE-002: Routing Decision ──────────────────────────────────────────────────

describe("FE-002 — Routing Decision section", () => {
  it("renders routing decision with decision name after expand", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    const toggle = container.querySelector("[data-testid='context-section-routing-toggle']") as HTMLButtonElement;
    act(() => { fireEvent.click(toggle); });
    const body = container.querySelector("[data-testid='context-section-routing-body']");
    expect(body).not.toBeNull();
    expect(body!.textContent).toContain("rf_domain_researcher");
  });

  it("renders routing decision rationale after expand", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-routing-toggle']")!);
    });
    const body = container.querySelector("[data-testid='context-section-routing-body']");
    expect(body!.textContent).toContain("Domain-specific discovery required");
  });

  it("renders est_cost_usd and budget_usd metadata", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-routing-toggle']")!);
    });
    const costEl = container.querySelector("[data-testid='context-routing-cost']");
    expect(costEl).not.toBeNull();
    expect(costEl!.textContent).toContain("0.4200");
    const budgetEl = container.querySelector("[data-testid='context-routing-budget']");
    expect(budgetEl).not.toBeNull();
    expect(budgetEl!.textContent).toContain("2.00");
  });

  it("renders sensitivity_tier chip", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-routing-toggle']")!);
    });
    const sensEl = container.querySelector("[data-testid='context-routing-sensitivity']");
    expect(sensEl).not.toBeNull();
    expect(sensEl!.textContent).toContain("personal");
  });

  it("shows empty-state when routing_decision is null", () => {
    const run = makeRun13({ ...FULL_CONTEXT, routing_decision: null });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-routing-toggle']")!);
    });
    const empty = container.querySelector("[data-testid='context-section-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Routing decision not available");
  });

  it("does not render metadata block when extra fields absent", () => {
    const run = makeRun13({
      ...FULL_CONTEXT,
      routing_decision: { decision: "rf_domain_researcher", rationale: "test" },
    });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-routing-toggle']")!);
    });
    expect(container.querySelector("[data-testid='context-routing-meta']")).toBeNull();
  });
});

// ── FE-003: Research Brief (frontmatter strip) ────────────────────────────────

describe("FE-003 — Research Brief section", () => {
  it("renders research brief markdown content after expand", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-brief-toggle']")!);
    });
    const body = container.querySelector("[data-testid='context-section-brief-body']");
    expect(body).not.toBeNull();
    const renderer = body!.querySelector("[data-testid='report-renderer']");
    expect(renderer).not.toBeNull();
  });

  it("YAML frontmatter is stripped — rendered body does not contain frontmatter keys", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-brief-toggle']")!);
    });
    const renderer = container.querySelector("[data-testid='report-renderer']");
    expect(renderer).not.toBeNull();
    // The frontmatter lines "type: research_brief" and "title: Test Brief" must be stripped
    // (they should not appear as rendered paragraph text in the body)
    expect(renderer!.textContent).not.toContain("type: research_brief");
    expect(renderer!.textContent).not.toContain("title: Test Brief");
  });

  it("brief body content is rendered after frontmatter strip", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-brief-toggle']")!);
    });
    const renderer = container.querySelector("[data-testid='report-renderer']");
    expect(renderer!.textContent).toContain("Test Research Brief");
    expect(renderer!.textContent).toContain("frontmatter stripping");
  });

  it("shows empty-state when research_brief_md is null", () => {
    const run = makeRun13({ ...FULL_CONTEXT, research_brief_md: null });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-brief-toggle']")!);
    });
    const empty = container.querySelector("[data-testid='context-section-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Research brief not available");
  });

  it("renders brief from the real fixture run (schema 1.3)", () => {
    const { container } = render(<ContextPane run={fixtureRun} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-brief-toggle']")!);
    });
    const body = container.querySelector("[data-testid='context-section-brief-body']");
    expect(body).not.toBeNull();
    // Fixture has research_brief_md with YAML frontmatter — renderer should not show raw frontmatter
    const renderer = body!.querySelector("[data-testid='report-renderer']");
    expect(renderer).not.toBeNull();
    // The frontmatter ---/schema_version/type lines should not appear in rendered text
    expect(renderer!.textContent).not.toContain("schema_version: \"0.1\"");
  });
});

// ── FE-004: Swarm Plan (OQ-3: tree + raw toggle) ─────────────────────────────

describe("FE-004 — Swarm Plan section (OQ-3 two-level tree + raw escape hatch)", () => {
  it("renders swarm plan tree after expand", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const tree = container.querySelector("[data-testid='context-swarm-tree']");
    expect(tree).not.toBeNull();
  });

  it("renders swarm name, agents, and adapters in flat rows", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const swarmName = container.querySelector("[data-testid='swarm-tree-swarm-name']");
    expect(swarmName).not.toBeNull();
    expect(swarmName!.textContent).toContain("discovery_swarm");

    const agents = container.querySelector("[data-testid='swarm-tree-agents']");
    expect(agents).not.toBeNull();
    expect(agents!.textContent).toContain("rf_source_scout");

    const adapters = container.querySelector("[data-testid='swarm-tree-adapters']");
    expect(adapters).not.toBeNull();
    expect(adapters!.textContent).toContain("web_search");
  });

  it("renders a level-2 sub-tree toggle for nested 'budget' object", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const budgetSubtree = container.querySelector("[data-testid='swarm-tree-subtree-budget']");
    expect(budgetSubtree).not.toBeNull();
  });

  it("expanding the budget sub-tree reveals nested fields", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const budgetToggle = container.querySelector(
      "[data-testid='swarm-tree-subtree-budget-toggle']"
    ) as HTMLButtonElement | null;
    expect(budgetToggle).not.toBeNull();
    act(() => { fireEvent.click(budgetToggle!); });
    const budgetBody = container.querySelector("[data-testid='swarm-tree-subtree-budget-body']");
    expect(budgetBody).not.toBeNull();
    expect(budgetBody!.textContent).toContain("max_cost_usd");
  });

  it("'Show raw' button is present and toggles raw JSON block", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const rawBtn = container.querySelector("[data-testid='swarm-tree-raw-btn']") as HTMLButtonElement;
    expect(rawBtn).not.toBeNull();
    // Raw block should be hidden initially
    expect(container.querySelector("[data-testid='swarm-tree-raw-block']")).toBeNull();

    // Click "Show raw"
    act(() => { fireEvent.click(rawBtn); });
    const rawBlock = container.querySelector("[data-testid='swarm-tree-raw-block']");
    expect(rawBlock).not.toBeNull();
    // Raw block should contain JSON
    expect(rawBlock!.textContent).toContain("discovery_swarm");
    expect(rawBlock!.textContent).toContain("web_search");

    // Click again to hide
    act(() => { fireEvent.click(rawBtn); });
    expect(container.querySelector("[data-testid='swarm-tree-raw-block']")).toBeNull();
  });

  it("raw JSON block contains full plan JSON including nested budget", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const rawBtn = container.querySelector("[data-testid='swarm-tree-raw-btn']") as HTMLButtonElement;
    act(() => { fireEvent.click(rawBtn); });
    const rawBlock = container.querySelector("[data-testid='swarm-tree-raw-block']");
    // The raw JSON should include the full plan — including nested budget object
    expect(rawBlock!.textContent).toContain("max_runtime_minutes");
  });

  it("shows empty-state when swarm_plan is null", () => {
    const run = makeRun13({ ...FULL_CONTEXT, swarm_plan: null });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-swarm-toggle']")!);
    });
    const empty = container.querySelector("[data-testid='context-section-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Swarm plan not available");
  });
});

// ── FE-005: Upstream Entities ─────────────────────────────────────────────────

describe("FE-005 — Upstream Entities section", () => {
  it("renders all 3 entity badges after expand", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    const intentBadge = container.querySelector("[data-testid='context-entity-intent-id']");
    expect(intentBadge).not.toBeNull();
    expect(intentBadge!.textContent).toContain("intent_test_001");

    const ibomBadge = container.querySelector("[data-testid='context-entity-ibom-id']");
    expect(ibomBadge).not.toBeNull();
    expect(ibomBadge!.textContent).toContain("ibom_test_001");

    const itNodeBadge = container.querySelector("[data-testid='context-entity-intenttree-node-id']");
    expect(itNodeBadge).not.toBeNull();
    expect(itNodeBadge!.textContent).toContain("it_node_test_001");
  });

  it("each entity badge has an accessible title/aria-label", () => {
    const run = makeRun13(FULL_CONTEXT);
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    const intentBadge = container.querySelector("[data-testid='context-entity-intent-id']");
    expect(intentBadge!.getAttribute("aria-label")).toContain("Intent ID");
    const ibomBadge = container.querySelector("[data-testid='context-entity-ibom-id']");
    expect(ibomBadge!.getAttribute("aria-label")).toContain("iBOM ID");
    const itBadge = container.querySelector("[data-testid='context-entity-intenttree-node-id']");
    expect(itBadge!.getAttribute("aria-label")).toContain("IntentTree node ID");
  });

  it("renders only present IDs — omits badge for absent field", () => {
    const run = makeRun13({
      ...FULL_CONTEXT,
      upstream_entities: { intent_id: "intent_test_partial", ibom_id: null },
    });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    // intent_id present
    expect(container.querySelector("[data-testid='context-entity-intent-id']")).not.toBeNull();
    // ibom_id is null — badge omitted
    expect(container.querySelector("[data-testid='context-entity-ibom-id']")).toBeNull();
    // intenttree_node_id absent — badge omitted
    expect(container.querySelector("[data-testid='context-entity-intenttree-node-id']")).toBeNull();
  });

  it("shows empty-state when upstream_entities is null", () => {
    const run = makeRun13({ ...FULL_CONTEXT, upstream_entities: null });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    const empty = container.querySelector("[data-testid='context-section-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Upstream entities not available");
  });

  it("shows empty-state when upstream_entities has all null values", () => {
    const run = makeRun13({
      ...FULL_CONTEXT,
      upstream_entities: { intent_id: null, ibom_id: null, intenttree_node_id: null },
    });
    const { container } = render(<ContextPane run={run} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    const empty = container.querySelector("[data-testid='context-section-empty']");
    expect(empty).not.toBeNull();
  });

  it("renders upstream entities from the real fixture run", () => {
    const { container } = render(<ContextPane run={fixtureRun} />, {
      wrapper: makeWrapper(),
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='context-section-upstream-toggle']")!);
    });
    // fixtureRun has all 3 upstream entity IDs set
    expect(container.querySelector("[data-testid='context-entity-intent-id']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-entity-ibom-id']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-entity-intenttree-node-id']")).not.toBeNull();
  });
});

// ── FE-006: RunDetailWorkspace / ContextPane integration ─────────────────────

describe("FE-006 — RunDetailWorkspace + ContextPane integration", () => {
  it("renders Context tabpanel with 4 sections for schema-1.3 + populated context", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={fixtureRun}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const tabpanel = container.querySelector("[data-testid='tabpanel-context']");
    expect(tabpanel).not.toBeNull();
    // All 4 collapsible section headers present
    expect(container.querySelector("[data-testid='context-section-routing']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-brief']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-swarm']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-section-upstream']")).not.toBeNull();
  });

  it("Context tab shows unavailable state for pre-1.3 scaffold run", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={scaffoldRun}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const unavailable = container.querySelector("[data-testid='context-pane-unavailable']");
    expect(unavailable).not.toBeNull();
    expect(unavailable!.textContent).toContain("Context not available for this run");
  });

  it("no console errors on Context tab with pre-1.3 run (no hard destructuring)", () => {
    expect(() =>
      render(
        <RunDetailWorkspace
          run={scaffoldRun}
          activeTab="context"
          mode="page"
          onTabChange={() => {}}
        />,
        { wrapper: makeWrapper() },
      )
    ).not.toThrow();
  });

  it("expanding the Routing Decision section from workspace renders the card", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={fixtureRun}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const toggle = container.querySelector(
      "[data-testid='context-section-routing-toggle']"
    ) as HTMLButtonElement;
    expect(toggle).not.toBeNull();
    act(() => { fireEvent.click(toggle); });
    const body = container.querySelector("[data-testid='context-section-routing-body']");
    expect(body).not.toBeNull();
    // The routing decision from the fixture should be visible
    expect(body!.textContent).toContain("rf_domain_researcher");
  });

  it("expanding the Swarm Plan section shows the tree and raw toggle", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={fixtureRun}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='context-section-swarm-toggle']")!
      );
    });
    expect(container.querySelector("[data-testid='context-swarm-tree']")).not.toBeNull();
    expect(container.querySelector("[data-testid='swarm-tree-raw-btn']")).not.toBeNull();
  });

  it("expanding the Upstream Entities section shows all 3 entity badges from fixture", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={fixtureRun}
        activeTab="context"
        mode="page"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='context-section-upstream-toggle']")!
      );
    });
    expect(container.querySelector("[data-testid='context-entity-intent-id']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-entity-ibom-id']")).not.toBeNull();
    expect(container.querySelector("[data-testid='context-entity-intenttree-node-id']")).not.toBeNull();
  });

  it("uses optional chaining — run without context field does not throw", () => {
    const run: RFRunExport = {
      schema_version: "1.3",
      run_id: "rf_run_no_context_wired",
      status_derived: "verified",
      claims: [],
      claim_counts: null,
      verification: null,
      governance: null,
      timeline: null,
    };
    expect(() =>
      render(
        <RunDetailWorkspace
          run={run}
          activeTab="context"
          mode="page"
          onTabChange={() => {}}
        />,
        { wrapper: makeWrapper() },
      )
    ).not.toThrow();
  });
});
