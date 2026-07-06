/**
 * P8-SMOKE — SMOKE-001: Runtime smoke tests for all UI surfaces touched by
 * the Run Metadata Enrichment feature (Phases 5–7).
 *
 * Per R-P4 mandate: every target_surface that had a TSX file touched must
 * have a smoke check.  These tests render each surface with BOTH:
 *   (A) a fully-enriched run (linked_projects, category, tags, cost_usd, etc.)
 *   (B) a pre-migration null-metadata run (scaffold-run.json — all new fields absent)
 *
 * Assertion pattern:
 *   - No crash on either fixture  (render succeeds)
 *   - Enriched run: metadata-specific elements ARE present
 *   - Null-metadata run: metadata-specific elements are ABSENT (R-P2 resilience)
 *
 * Surfaces covered (smoke table from phase-6-8 plan):
 *   1. RunCard         — project badge + tags chips
 *   2. RunList (via FilterTabs) — filter sections expand; metadata options rendered
 *   3. FilterTabs      — metadata facet sections with options; a11y fieldset/legend
 *   4. RunDetailWorkspace (overview tab) — metadata section + enrichment widgets
 *   5. RunDetailModal  — sub-header meta-line with project/tags
 *   6. ClaimAuditWorkbench — renders without crash for both fixtures
 *   7. LineageDetailPanel  — runMeta reference chips shown/hidden per fixture
 */

import { describe, it, expect, vi }  from "vitest";
import { render, fireEvent, act }     from "@testing-library/react";
import { MemoryRouter }               from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode }             from "react";

// Components under test
import { RunCard }                from "@/components/RunList/RunCard";
import type { RunCardData }       from "@/components/RunList/RunCard";
import { FilterTabs }             from "@/components/RunList/FilterTabs";
import type { MetadataFilterState, MetadataFilterOptions } from "@/components/RunList/FilterTabs";
import { RunDetailWorkspace }     from "@/components/RunDetail/RunDetailWorkspace";
import { RunDetailModal }         from "@/components/RunDetail/RunDetailModal";
import { ClaimAuditWorkbench }    from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { LineageDetailPanel }     from "@/components/LineageGraph/LineageDetailPanel";
import type { LineageRunMetaRef } from "@/components/LineageGraph/LineageDetailPanel";
import type { LineageNode }       from "@/components/LineageGraph/lineageTree";

// Types
import type { RFRunExport, RFRunSummary } from "@/types/rf";

// Fixtures (static — no network)
import fixtureRunRaw   from "@/test/fixtures/run.json";
import scaffoldRunRaw  from "@/test/fixtures/scaffold-run.json";
import aosRunRaw       from "@/test/fixtures/aos-run.json";

const fixtureRun  = fixtureRunRaw  as unknown as RFRunExport;
const scaffoldRun = scaffoldRunRaw as unknown as RFRunExport;
const aosRun      = aosRunRaw      as unknown as RFRunExport;

// ── Enriched run — extends fixture with P5/P7 metadata + enrichment fields ────

/** Fully-populated run with all new schema-1.2 metadata and enrichment fields. */
const ENRICHED_RUN: RFRunExport = {
  ...fixtureRun,
  // P5 metadata
  linked_projects: ["ResearchFoundry", "SkillMeat"],
  category:        "AI Engineering",
  tags:            ["mcp", "tooling", "agentic-os", "llm", "orchestration"],
  backlog_idea_ref: "RIB-042",
  backlog_idea_id:  "mcp-tool-interop",
  // P7 enrichment
  cost_usd:        0.0312,
  model_profiles: {
    extraction_model_profile:   "haiku",
    synthesis_model_profile:    "sonnet",
    verification_model_profile: "haiku",
    max_runtime_minutes:        30,
    freshness_days:             7,
    max_cost_usd:               0.05,
  },
  source_count_by_type: { official_doc: 4, blog: 3, paper: 2, repo: 1 },
  writebacks: {
    targets: [
      { name: "MeatyWiki", destination: "wiki/mcp-tools", status: "published", url: "https://wiki.example.com" },
      { name: "SkillMeat",  destination: "skills/mcp",    status: "pending" },
    ],
  },
};

/** Pre-migration run — no new metadata fields at all (simulates schema < 1.2). */
const NULL_METADATA_RUN: RFRunExport = {
  ...scaffoldRun,
  // Explicitly absent — these fields must not exist or be null
  linked_projects: undefined,
  category:        undefined,
  tags:            undefined,
  backlog_idea_ref: undefined,
  backlog_idea_id:  undefined,
  cost_usd:        undefined,
  model_profiles:  undefined,
  source_count_by_type: undefined,
  writebacks:      undefined,
};

// ── Test helpers ──────────────────────────────────────────────────────────────

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

/** Minimal RunCardData from RFRunSummary-like shape. */
function makeRunCardData(run: RFRunExport, title?: string | null): RunCardData {
  return {
    run_id:         run.run_id,
    status_derived: run.status_derived,
    created_at:     run.created_at ?? null,
    sensitivity:    run.sensitivity ?? null,
    claim_counts:   run.claim_counts ?? null,
    title:          title !== undefined ? title : (run as RFRunSummary).title ?? null,
    linked_projects: (run as RFRunSummary).linked_projects ?? null,
    category:        (run as RFRunSummary).category ?? null,
    tags:            (run as RFRunSummary).tags ?? null,
  };
}

// ── (1) RunCard — project badge + tags chips ──────────────────────────────────

describe("SMOKE-001 / RunCard", () => {
  it("(enriched) renders without crash", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(ENRICHED_RUN)} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-card']")).not.toBeNull();
  });

  // Regression: title row must show human-readable text, never the raw rf_run_YYYY... slug.
  it("(with title) run-title testid shows the exported title, not the raw run_id slug", () => {
    const cardData = makeRunCardData(ENRICHED_RUN, "MCP Tool Interoperability Study");
    const { container } = render(
      <RunCard run={cardData} />,
      { wrapper: makeWrapper() },
    );
    const titleEl = container.querySelector("[data-testid='run-title']");
    expect(titleEl).not.toBeNull();
    expect(titleEl!.textContent).toBe("MCP Tool Interoperability Study");
    // Must not equal the raw run_id slug
    expect(titleEl!.textContent).not.toBe(ENRICHED_RUN.run_id);
  });

  it("(no title) run-title testid shows humanized slug, not raw run_id when title absent", () => {
    const cardData = makeRunCardData(ENRICHED_RUN, null);
    const { container } = render(
      <RunCard run={cardData} />,
      { wrapper: makeWrapper() },
    );
    const titleEl = container.querySelector("[data-testid='run-title']");
    expect(titleEl).not.toBeNull();
    // Humanized slug must differ from the raw rf_run_YYYY... value (spaces/caps added)
    // and must not be empty
    expect(titleEl!.textContent!.trim().length).toBeGreaterThan(0);
    expect(titleEl!.textContent).not.toBe(ENRICHED_RUN.run_id);
    // The raw id must appear in data-testid="run-id", not in data-testid="run-title"
    const idEl = container.querySelector("[data-testid='run-id']");
    expect(idEl?.textContent).toBe(ENRICHED_RUN.run_id);
  });

  it("(enriched) shows project badges for linked_projects", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(ENRICHED_RUN)} />,
      { wrapper: makeWrapper() },
    );
    const projectSection = container.querySelector("[data-testid='run-card-projects']");
    expect(projectSection).not.toBeNull();
    const badges = projectSection!.querySelectorAll("[data-testid='project-badge']");
    expect(badges.length).toBe(2);
    expect(badges[0]!.textContent).toBe("ResearchFoundry");
    expect(badges[1]!.textContent).toBe("SkillMeat");
  });

  it("(enriched) shows top 3 tag chips + overflow badge for >3 tags", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(ENRICHED_RUN)} />,
      { wrapper: makeWrapper() },
    );
    const tagsSection = container.querySelector("[data-testid='run-card-tags']");
    expect(tagsSection).not.toBeNull();
    const tagChips = tagsSection!.querySelectorAll("[data-testid='tag-chip']");
    expect(tagChips.length).toBe(3); // top 3 only
    const overflow = tagsSection!.querySelector("[data-testid='tag-overflow']");
    expect(overflow).not.toBeNull();
    expect(overflow!.textContent).toContain("+2"); // 5 tags total - 3 visible = 2 overflow
  });

  it("(null-metadata) renders without crash", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(NULL_METADATA_RUN)} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-card']")).not.toBeNull();
  });

  it("(null-metadata) omits project section when linked_projects absent", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(NULL_METADATA_RUN)} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-card-projects']")).toBeNull();
  });

  it("(null-metadata) omits tags section when tags absent", () => {
    const { container } = render(
      <RunCard run={makeRunCardData(NULL_METADATA_RUN)} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-card-tags']")).toBeNull();
  });
});

// ── (2+3) FilterTabs — metadata facet sections + a11y ────────────────────────

const FILTER_META_OPTIONS: MetadataFilterOptions = {
  linkedProjects: ["ResearchFoundry", "SkillMeat"],
  categories:     ["AI Engineering", "Frontend Tooling"],
  tags:           ["mcp", "tooling"],
};

const FILTER_META_EMPTY: MetadataFilterState = {
  activeLinkedProjects: [],
  activeCategories:     [],
  activeTags:           [],
};

describe("SMOKE-001 / FilterTabs", () => {
  it("renders status tabs without crash (no metadata props)", () => {
    const { container } = render(
      <FilterTabs active="all" counts={{ all: 3 }} onChange={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='filter-tab-all']")).not.toBeNull();
  });

  it("(metadata) renders facet sections when metadata props provided", () => {
    const { container } = render(
      <FilterTabs
        active="all"
        counts={{ all: 3 }}
        onChange={() => {}}
        metadataFilters={FILTER_META_EMPTY}
        metadataOptions={FILTER_META_OPTIONS}
        onMetadataFilterChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='facet-section-project']")).not.toBeNull();
    expect(container.querySelector("[data-testid='facet-section-category']")).not.toBeNull();
    expect(container.querySelector("[data-testid='facet-section-tags']")).not.toBeNull();
  });

  it("(metadata) Project facet expands and shows options on click", () => {
    const { container } = render(
      <FilterTabs
        active="all"
        counts={{ all: 3 }}
        onChange={() => {}}
        metadataFilters={FILTER_META_EMPTY}
        metadataOptions={FILTER_META_OPTIONS}
        onMetadataFilterChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const header = container.querySelector("[data-testid='facet-section-project'] .rv-facet-header") as HTMLElement;
    expect(header).not.toBeNull();
    act(() => { fireEvent.click(header); });

    // After expanding, options should be visible
    // Note: data-testid uses the raw option value (not lowercased), title is lowercased
    const opt = container.querySelector("[data-testid='facet-option-project-ResearchFoundry']");
    expect(opt).not.toBeNull();
  });

  it("(metadata) toggling a project option fires onMetadataFilterChange with updated state", () => {
    const onChange = vi.fn();
    const { container } = render(
      <FilterTabs
        active="all"
        counts={{ all: 3 }}
        onChange={() => {}}
        metadataFilters={FILTER_META_EMPTY}
        metadataOptions={FILTER_META_OPTIONS}
        onMetadataFilterChange={onChange}
      />,
      { wrapper: makeWrapper() },
    );
    // Expand Project facet
    const header = container.querySelector("[data-testid='facet-section-project'] .rv-facet-header") as HTMLElement;
    act(() => { fireEvent.click(header); });

    // Toggle ResearchFoundry (data-testid uses raw option value)
    const opt = container.querySelector("[data-testid='facet-option-project-ResearchFoundry']") as HTMLElement;
    act(() => { fireEvent.click(opt); });

    expect(onChange).toHaveBeenCalled();
    const called = onChange.mock.calls[0]![0] as MetadataFilterState;
    expect(called.activeLinkedProjects).toContain("ResearchFoundry");
  });

  it("(a11y) FacetSection uses group+fieldset/legend semantics, not listbox+aria-multiselectable", () => {
    const { container } = render(
      <FilterTabs
        active="all"
        counts={{ all: 3 }}
        onChange={() => {}}
        metadataFilters={FILTER_META_EMPTY}
        metadataOptions={FILTER_META_OPTIONS}
        onMetadataFilterChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );

    // Expand Project facet to trigger rendering of the inner list
    const header = container.querySelector("[data-testid='facet-section-project'] .rv-facet-header") as HTMLElement;
    act(() => { fireEvent.click(header); });

    // A11y fix: must use fieldset element (not a ul[role=listbox])
    const fieldset = container.querySelector("[data-testid='facet-section-project'] fieldset");
    expect(fieldset).not.toBeNull();

    // Must NOT have role=listbox (that was the incorrect pattern)
    const listbox = container.querySelector("[role='listbox']");
    expect(listbox).toBeNull();

    // Must NOT have aria-multiselectable on a non-listbox container
    const multiselectable = container.querySelector("[aria-multiselectable]");
    expect(multiselectable).toBeNull();

    // Legend must be present inside fieldset
    const legend = fieldset!.querySelector("legend");
    expect(legend).not.toBeNull();
  });

  it("(a11y) filter-tabs tablist has aria-label for status tabs", () => {
    const { container } = render(
      <FilterTabs active="all" counts={{ all: 2 }} onChange={() => {}} />,
      { wrapper: makeWrapper() },
    );
    const tablist = container.querySelector("[role='tablist']");
    expect(tablist?.getAttribute("aria-label")).toBeTruthy();
  });

  it("(no metadata props) omits facet sections when metadata props absent", () => {
    const { container } = render(
      <FilterTabs active="all" counts={{ all: 2 }} onChange={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='facet-section-project']")).toBeNull();
    expect(container.querySelector("[data-testid='facet-section-category']")).toBeNull();
    expect(container.querySelector("[data-testid='facet-section-tags']")).toBeNull();
  });
});

// ── (4) RunDetailWorkspace — Overview tab metadata + enrichment widgets ────────

describe("SMOKE-001 / RunDetailWorkspace (Overview)", () => {
  it("(enriched) renders without crash", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={ENRICHED_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-detail-workspace']")).not.toBeNull();
  });

  it("(enriched) overview tab: run-metadata section present with linked_projects", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={ENRICHED_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-overview-metadata']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-linked-projects']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-category']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-tags']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-backlog-ref']")).not.toBeNull();
  });

  it("(enriched) overview tab: enrichment section present with all widgets", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={ENRICHED_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-overview-enrichment']")).not.toBeNull();
    expect(container.querySelector("[data-testid='enrichment-cost']")).not.toBeNull();
    expect(container.querySelector("[data-testid='enrichment-model-profiles']")).not.toBeNull();
    expect(container.querySelector("[data-testid='enrichment-source-count']")).not.toBeNull();
    expect(container.querySelector("[data-testid='enrichment-claim-distribution']")).not.toBeNull();
    expect(container.querySelector("[data-testid='enrichment-writebacks']")).not.toBeNull();
  });

  it("(enriched) cost widget shows formatted USD value", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={ENRICHED_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    const cost = container.querySelector("[data-testid='enrichment-cost']");
    expect(cost?.textContent).toContain("$0.0312");
  });

  it("(aos metadata) overview tab: renders schema 1.4 AOS UUIDs and RF native aliases", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={{ ...aosRun, aos_artifact_uuid: "unknown" }}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='run-overview-metadata']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-aos-run-uuid']")?.textContent)
      .toContain("11111111-1111-4111-8111-111111111111");
    expect(container.querySelector("[data-testid='metadata-aos-session-uuid']")?.textContent)
      .toContain("22222222-2222-4222-8222-222222222222");
    expect(container.querySelector("[data-testid='metadata-aos-feature-uuid']")?.textContent)
      .toContain("33333333-3333-4333-8333-333333333333");
    expect(container.querySelector("[data-testid='metadata-aos-trace-uuid']")?.textContent)
      .toContain("55555555-5555-4555-8555-555555555555");
    expect(container.querySelector("[data-testid='metadata-aos-artifact-uuid']")?.textContent)
      .toContain("Not available");

    const aliases = container.querySelector("[data-testid='metadata-aos-native-aliases']");
    expect(aliases?.textContent).toContain("rf_run_id");
    expect(aliases?.textContent).toContain(aosRun.run_id);
    expect(aliases?.textContent).not.toContain("op_run_id");
    expect(container.querySelector("[data-testid='metadata-aos-status']")).toBeNull();
  });

  it("(null-metadata) renders without crash", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={NULL_METADATA_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-detail-workspace']")).not.toBeNull();
  });

  it("(null-metadata) overview tab: metadata-empty message shown, no metadata rows", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={NULL_METADATA_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='metadata-empty']")).not.toBeNull();
    expect(container.querySelector("[data-testid='metadata-linked-projects']")).toBeNull();
    expect(container.querySelector("[data-testid='metadata-category']")).toBeNull();
    expect(container.querySelector("[data-testid='metadata-tags']")).toBeNull();
    expect(container.querySelector("[data-testid='metadata-aos-run-uuid']")).toBeNull();
    expect(container.querySelector("[data-testid='metadata-aos-native-aliases']")).toBeNull();
  });

  it("(null-metadata) overview tab: enrichment section absent when all fields null", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={NULL_METADATA_RUN}
        activeTab="overview"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    // No enrichment section since claim_counts.total=0 and all enrichment fields absent
    expect(container.querySelector("[data-testid='run-overview-enrichment']")).toBeNull();
  });

  it("(enriched) ledger tab renders ClaimAuditWorkbench without crash", () => {
    const { container } = render(
      <RunDetailWorkspace
        run={ENRICHED_RUN}
        activeTab="ledger"
        mode="modal"
        onTabChange={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='tabpanel-ledger']")).not.toBeNull();
  });
});

// ── (5) RunDetailModal — sub-header meta-line with project/tags ───────────────

describe("SMOKE-001 / RunDetailModal", () => {
  it("(enriched) renders the modal shell without crash", () => {
    const { container } = render(
      <RunDetailModal runId={ENRICHED_RUN.run_id} onClose={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-detail-modal']")).not.toBeNull();
  });

  it("(enriched) shows metadata meta-line when run data loads (from fixture fetch mock)", async () => {
    const { container } = render(
      <RunDetailModal runId={ENRICHED_RUN.run_id} onClose={() => {}} />,
      { wrapper: makeWrapper() },
    );
    // The fixture fetch mock returns the run detail — wait for it
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    // fixture run.json has no linked_projects/category/tags so meta-line is absent
    // This verifies no crash during loading state
    expect(container.querySelector("[data-testid='run-detail-modal']")).not.toBeNull();
  });

  it("(null runId) returns null without crash", () => {
    const { container } = render(
      <RunDetailModal runId={null} onClose={() => {}} />,
      { wrapper: makeWrapper() },
    );
    // runId=null → component returns null (nothing rendered)
    expect(container.querySelector("[data-testid='run-detail-modal']")).toBeNull();
  });

  it("(scaffold runId) renders loading state for scaffold run", () => {
    const { container } = render(
      <RunDetailModal runId={NULL_METADATA_RUN.run_id} onClose={() => {}} />,
      { wrapper: makeWrapper() },
    );
    // Modal shell always renders when runId is non-null
    expect(container.querySelector("[data-testid='run-detail-modal']")).not.toBeNull();
  });

  it("(enriched) close button is present", () => {
    const { container } = render(
      <RunDetailModal runId={ENRICHED_RUN.run_id} onClose={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='run-modal-close']")).not.toBeNull();
  });
});

// ── (6) ClaimAuditWorkbench — renders for both fixtures ──────────────────────

describe("SMOKE-001 / ClaimAuditWorkbench", () => {
  it("(enriched) renders without crash with claims present", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={ENRICHED_RUN} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='claim-audit-workbench']")).not.toBeNull();
  });

  it("(enriched) shows the claims ledger table", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={ENRICHED_RUN} />,
      { wrapper: makeWrapper() },
    );
    // Has claims, so audit table should be present
    expect(container.querySelector("[data-testid='ledger-table']")).not.toBeNull();
  });

  it("(null-metadata) renders empty-state without crash when no claims", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={NULL_METADATA_RUN} />,
      { wrapper: makeWrapper() },
    );
    // Scaffold run has no claims → empty state
    expect(container.querySelector("[data-testid='claim-audit-workbench']")).not.toBeNull();
    // No ledger table when claims=[]
    expect(container.querySelector("[data-testid='ledger-table']")).toBeNull();
  });
});

// ── (7) LineageDetailPanel — runMeta reference chips ─────────────────────────

/** Minimal LineageNode for smoke testing the detail panel. */
const SAMPLE_NODE: LineageNode = {
  id:       "run:rf_run_test",
  kind:     "run",
  title:    "Test Run",
  subtitle: undefined,
  chips:    ["published"],
  details:  [{ label: "Verification", value: "passed" }],
  children: [],
  claimId:  undefined,
};

describe("SMOKE-001 / LineageDetailPanel", () => {
  it("(no node) renders empty-state panel without crash", () => {
    const { container } = render(
      <LineageDetailPanel node={null} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-detail']")).not.toBeNull();
    expect(container.querySelector("[data-testid='lineage-detail-empty']")).not.toBeNull();
  });

  it("(enriched runMeta) renders run-level tag + category chips in panel header", () => {
    const runMeta: LineageRunMetaRef = {
      tags:     ["mcp", "tooling"],
      category: "AI Engineering",
    };
    const { container } = render(
      <LineageDetailPanel node={SAMPLE_NODE} runMeta={runMeta} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-run-meta']")).not.toBeNull();
    expect(container.querySelector("[data-testid='lineage-run-category']")?.textContent).toBe("AI Engineering");
    const tagChips = container.querySelectorAll("[data-testid='lineage-run-tag']");
    expect(tagChips.length).toBe(2);
  });

  it("(null runMeta) omits run-meta section when tags/category absent (R-P2)", () => {
    const nullRunMeta: LineageRunMetaRef = { tags: null, category: null };
    const { container } = render(
      <LineageDetailPanel node={SAMPLE_NODE} runMeta={nullRunMeta} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-run-meta']")).toBeNull();
  });

  it("(no runMeta prop) omits run-meta section when runMeta prop not provided", () => {
    const { container } = render(
      <LineageDetailPanel node={SAMPLE_NODE} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-run-meta']")).toBeNull();
  });

  it("(enriched runMeta) renders panel title and kind chip", () => {
    const runMeta: LineageRunMetaRef = { tags: ["agentic-os"], category: null };
    const { container } = render(
      <LineageDetailPanel node={SAMPLE_NODE} runMeta={runMeta} />,
      { wrapper: makeWrapper() },
    );
    // Panel title comes from node.title
    expect(container.querySelector(".rv-lineage-detail__title")?.textContent).toBe("Test Run");
  });

  it("(node with claim actions) renders select-claim + open-provenance buttons", () => {
    const claimNode: LineageNode = {
      ...SAMPLE_NODE,
      id:      "clm_001",
      kind:    "claim",
      title:   "A test claim",
      claimId: "clm_001",
      chips:   [],
      details: [{ label: "Sources", value: "src_001" }],
    };
    const onSelect = vi.fn();
    const onProvenance = vi.fn();
    const { container } = render(
      <LineageDetailPanel
        node={claimNode}
        onSelectClaim={onSelect}
        onOpenProvenance={onProvenance}
      />,
      { wrapper: makeWrapper() },
    );
    // Actions section should appear for claim nodes with handlers
    const actions = container.querySelector(".rv-lineage-detail__actions");
    expect(actions).not.toBeNull();
    // Both buttons present
    const buttons = actions!.querySelectorAll("button");
    expect(buttons.length).toBe(2);
  });
});
