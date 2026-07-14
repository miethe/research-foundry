/**
 * assertion-ledger-review.test.tsx — P6-004 component/resilience seam tests
 * for the reusable assertion ledger reviewer experience (P7 physical / P6
 * logical scope).
 *
 * Fixtures are built from the FROZEN generated DTOs
 * (`@/types/rf/assertions_api.generated.ts`, `@/types/rf/run-export.ts`) —
 * every packet/summary/impact literal below is typed against those
 * interfaces so a fixture can never silently drift from the real contract.
 * The one precedented exception is the legacy-missing-field pattern
 * (`undefined as unknown as Record<string, unknown>`), copied verbatim from
 * `src/hooks/useAssertions.test.tsx`, which encodes a real production shape:
 * legacy exports omit these keys entirely even though the generated
 * `EvidencePacket` interface marks them non-optional (see defect notes in
 * the P6-004 completion report).
 *
 * Coverage groups (see task P6-004 / design spec
 * docs/project_plans/design-specs/reusable-assertion-ledger-reviewer-experience-v1.md
 * §6, §7, §10, §11 AC UX-1..UX-6):
 *   A. FULL PACKET            — AssertionPacketInspector + AssertionPacketFields
 *   B. LEGACY-MISSING          — ReusableAssertionFieldsColumn + AssertionPacketFields
 *   C. DENIED                  — AssertionDeniedPanel + AssertionCatalogPane
 *   D. STALE + IMPACT          — AssertionStatusBand + AssertionInspector
 *   E. ASSERTION-ONLY          — AssertionOnlyLineage
 *   F. INTERACTION / A11Y      — AssertionResultsTable, ProvenanceModal, CopyIdButton
 */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, fireEvent, act, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRef } from "react";
import type { ReactNode } from "react";
import { AuthContext, type AuthContextValue } from "@/auth/AuthContext";

import type {
  AssertionImpactAction,
  AssertionImpactSummary,
  AssertionSummary,
  EvidencePacket,
  RightsDecision,
} from "@/types/rf/assertions_api.generated";
import type { AssertionViewState } from "@/hooks/useAssertions";
import type { RFClaim, RFRunExport } from "@/types/rf";

// ── Components under test ────────────────────────────────────────────────────
import { AssertionPacketInspector } from "@/components/AssertionCatalog/AssertionPacketInspector";
import { AssertionResultsTable } from "@/components/AssertionCatalog/AssertionResultsTable";
import { AssertionDeniedPanel } from "@/components/AssertionCatalog/AssertionDeniedPanel";
import { CopyIdButton } from "@/components/AssertionCatalog/CopyIdButton";
import { AssertionCatalogPane } from "@/components/AssertionCatalog/AssertionCatalogPane";
import { ReusableAssertionFieldsColumn } from "@/components/AssertionCatalog/ReusableAssertionFieldsColumn";
import { ProvenanceModal } from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";
import { AssertionInspector, AssertionStatusBand } from "@/components/ClaimLedger/AssertionAuditPanel";
import { ClaimAuditWorkbench } from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { AssertionOnlyLineage } from "@/components/LineageGraph/AssertionOnlyLineage";
import { RunDetailWorkspace } from "@/components/RunDetail/RunDetailWorkspace";

// ── Hook module mock (used only by AssertionCatalogPane / ReusableAssertionFieldsColumn /
//    AssertionOnlyLineage — every other component under test takes typed state as a prop). ──
const mocks = vi.hoisted(() => ({
  useAssertionSearch: vi.fn(),
  useEvidencePacket: vi.fn(),
  useAssertionImpact: vi.fn(),
  useAssertionLineage: vi.fn(),
}));

vi.mock("@/hooks/useAssertions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/hooks/useAssertions")>();
  return {
    ...actual,
    useAssertionSearch: mocks.useAssertionSearch,
    useEvidencePacket: mocks.useEvidencePacket,
    useAssertionImpact: mocks.useAssertionImpact,
    useAssertionLineage: mocks.useAssertionLineage,
  };
});

// ── Shared render wrapper ────────────────────────────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

beforeAll(() => {
  // jsdom has no Clipboard API by default; stub it so CopyIdButton's
  // navigator.clipboard.writeText() call resolves instead of throwing.
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    configurable: true,
  });
});

beforeEach(() => {
  vi.clearAllMocks();
  mocks.useAssertionSearch.mockReturnValue({
    data: undefined,
    isFetching: false,
    state: { kind: "loading" },
  });
  mocks.useEvidencePacket.mockReturnValue({ data: undefined, state: { kind: "loading" } });
  mocks.useAssertionImpact.mockReturnValue({ data: undefined, state: { kind: "loading" } });
  mocks.useAssertionLineage.mockReturnValue({ data: undefined, state: { kind: "loading" } });
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Fixture builders (typed against the generated DTOs) ──────────────────────

function makeRights(overrides: Partial<RightsDecision> = {}): RightsDecision {
  return { allowed: true, reason_code: "ok", ...overrides };
}

/** §6.A "Full packet catalog" — every populated field from the design spec's literal copy. */
function makeFullPacket(overrides: Partial<EvidencePacket> = {}): EvidencePacket {
  return {
    packet_version: "1",
    assertion_id: "ast_01JX7QF8M2",
    assertion_version: 3,
    assertion: {
      kind: "source_assertion",
      lifecycle_state: "eligible",
      assertion_text: "Hybrid retrieval improves recall for long-tail research questions.",
    },
    passage: {
      passage_id: "psg_01JX7Q00A1",
      normalized_text:
        "Hybrid retrieval increased Recall@50 by 22.3% compared with the best single retriever.",
      selectors: [{ value: "Section 5.3" }, { value: "Paragraph 2" }],
    },
    source_edition: {
      source_edition_id: "sed_01JX7Q00B2",
      captured_at: "2026-01-15T00:00:00Z",
    },
    qualifiers: {
      population: "Long-tail research queries",
      timeframe: "2025-2026",
    },
    qualifier_extensions: {},
    evaluations: [
      {
        evaluation_kind: "grounding",
        verdict: "pass",
        evaluator: { id: "reviewer_1" },
        evaluated_at: "2026-01-16T00:00:00Z",
      },
      {
        evaluation_kind: "human_review",
        verdict: "pass",
        evaluator: { id: "reviewer_2" },
        evaluated_at: "2026-01-17T00:00:00Z",
      },
    ],
    freshness: { lifecycle_state: "eligible" },
    access_scope: "personal",
    rights_decision: makeRights({ allowed: true, reason_code: "ok" }),
    relationships: [],
    run_uses: ["run_1", "run_2", "run_3", "run_4"],
    report_uses: ["rev_1", "rev_2", "rev_3"],
    ...overrides,
  };
}

/** §6.D "Stale impact workbench" packet. */
function makeStalePacket(overrides: Partial<EvidencePacket> = {}): EvidencePacket {
  return {
    packet_version: "1",
    assertion_id: "ast_01JX7QF8M2",
    assertion_version: 3,
    assertion: {
      kind: "source_assertion",
      lifecycle_state: "stale",
      text: "Hybrid retrieval improves recall for long-tail research questions.",
    },
    passage: {
      text: "Hybrid retrieval increased Recall@50 by 22.3% compared with the best single retriever.",
    },
    source_edition: { edition_id: "sed_old_014", captured_at: "2026-01-15" },
    qualifiers: {},
    qualifier_extensions: {},
    evaluations: [],
    freshness: {
      reason_code: "dependency_manifest_missing",
      previous_edition_id: "sed_old_014",
      current_edition_id: "sed_new_015",
      detected_at: "2026-02-01T00:00:00Z",
    },
    access_scope: "personal",
    rights_decision: makeRights({ allowed: false, reason_code: "dependency_manifest_missing" }),
    relationships: [],
    run_uses: [],
    report_uses: [],
    ...overrides,
  };
}

// Backend receipt coherence (AssertionImpactReconciler._load_receipt):
//
// | operation status | reason code | actions | action status / writeback disposition |
// | pending          | null        | manifest-sorted | completed prefix; pending suffix; completed writebacks have a disposition; pending writebacks omit it |
// | completed        | null        | manifest-sorted | every action completed; writebacks have a disposition |
// | blocked          | approved missing/invalid-manifest reason | zero | n/a |
//
// These summary fixtures mirror only combinations that the writer can persist.
const FULL_ACTIONS: AssertionImpactAction[] = [
  { object_id: "av_1", object_class: "assertion_version", action: "block_reuse", status: "completed" },
  { object_id: "av_2", object_class: "assertion_version", action: "block_reuse", status: "completed" },
  { object_id: "edge_1", object_class: "canonical_claim_edge", action: "mark_stale", status: "completed" },
  { object_id: "idx_1", object_class: "derived_cache_or_index", action: "purge_current_read", status: "completed" },
  { object_id: "exp_1", object_class: "export", action: "mark_stale", status: "completed" },
  { object_id: "wb_1", object_class: "mock_writeback_receipt", action: "queue_default_denied_reconciliation", status: "completed", writeback_status: "default_denied" },
  { object_id: "wb_2", object_class: "mock_writeback_receipt", action: "queue_default_denied_reconciliation", status: "pending" },
  { object_id: "rev_1", object_class: "report_revision", action: "mark_stale", status: "pending" },
  { object_id: "run_1", object_class: "run", action: "mark_stale", status: "pending" },
];

function makeImpactSummary(overrides: Partial<AssertionImpactSummary> = {}): AssertionImpactSummary {
  return {
    event_id: "evt_supersede_017",
    assertion_id: "ast_01JX7QF8M2",
    lifecycle_state: "blocked",
    access_scope: "personal",
    authoritative_reuse_blocked: true,
    operation_status: "pending",
    reason_code: null,
    replacement_edition_id: null,
    resumable: true,
    actions: FULL_ACTIONS,
    ...overrides,
  };
}

function makeBlockedImpactSummary(overrides: Partial<AssertionImpactSummary> = {}): AssertionImpactSummary {
  return makeImpactSummary({
    operation_status: "blocked",
    reason_code: "dependency_manifest_missing",
    resumable: false,
    actions: [],
    ...overrides,
  });
}

function makeClaim(overrides: Partial<RFClaim> & { claim_id: string; text: string }): RFClaim {
  return { sources: [], ...overrides };
}

// ═════════════════════════════════════════════════════════════════════════════
// A. FULL PACKET — AssertionPacketInspector / AssertionPacketFields
// ═════════════════════════════════════════════════════════════════════════════

describe("A. Full packet — AssertionPacketInspector", () => {
  function readyState(packet: EvidencePacket): AssertionViewState<EvidencePacket> {
    return { kind: "ready", data: packet };
  }

  it("renders the assertion text as the heading and the mono signature ast_id · vN", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const heading = container.querySelector(".rv-assertion-packet__text");
    expect(heading?.textContent).toBe(
      "Hybrid retrieval improves recall for long-tail research questions.",
    );
    const signature = container.querySelector(".rv-assertion-signature");
    expect(signature?.textContent).toBe("ast_01JX7QF8M2 · v3");
  });

  it("chips carry visible label text, not color-only state", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const header = container.querySelector(".rv-assertion-packet__signature-row") as HTMLElement;
    expect(within(header).getByText("Current")).toBeInTheDocument();
    expect(within(header).getByText("Eligible for reuse")).toBeInTheDocument();
  });

  it("labels an inference packet visibly and accessibly as Inference", () => {
    const inferencePacket = makeFullPacket({
      assertion: {
        kind: "inference",
        assertion_text: "The supported evidence implies the retrieval finding generalizes.",
        lifecycle_state: "eligible",
      },
    });
    const { container } = render(
      <AssertionPacketInspector state={readyState(inferencePacket)} />,
      { wrapper: makeWrapper() },
    );
    const inspector = container.querySelector("[data-testid='assertion-packet-inspector']") as HTMLElement;
    expect(inspector).toHaveAttribute("aria-label", "Inference");
    expect(within(inspector).getAllByText("Inference").length).toBeGreaterThan(0);
    expect(within(inspector).queryByText("Source assertion")).toBeNull();
  });

  it("renders the complete evidence-first packet sections in spec order", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const sectionTestIds = Array.from(
      container.querySelectorAll("[data-testid^='assertion-section-']"),
    ).map((el) => el.getAttribute("data-testid"));
    expect(sectionTestIds).toEqual([
      "assertion-section-edition",
      "assertion-section-passage",
      "assertion-section-qualifiers",
      "assertion-section-evaluation",
      "assertion-section-freshness",
      "assertion-section-rights",
      "assertion-section-relationships",
      "assertion-section-uses",
    ]);
  });

  it("Edition section shows the mono edition id without a false provenance affordance", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const edition = container.querySelector("[data-testid='assertion-section-edition']") as HTMLElement;
    expect(within(edition).getByText("sed_01JX7Q00B2")).toBeInTheDocument();
    expect(within(edition).getByRole("button", { name: "Copy source edition ID" })).toBeInTheDocument();
    expect(container.querySelector("[data-testid='assertion-open-provenance']")).toBeNull();
  });

  it("Passage section renders a semantic blockquote and a copyable locator box", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const passage = container.querySelector("[data-testid='assertion-section-passage']") as HTMLElement;
    const blockquote = passage.querySelector("blockquote");
    expect(blockquote?.tagName).toBe("BLOCKQUOTE");
    expect(blockquote?.textContent).toBe(
      "Hybrid retrieval increased Recall@50 by 22.3% compared with the best single retriever.",
    );
    expect(within(passage).getByText("Section 5.3 · Paragraph 2")).toBeInTheDocument();
    expect(within(passage).getByRole("button", { name: "Copy locator" })).toBeInTheDocument();
    expect(within(passage).getByRole("button", { name: "Copy passage ID" })).toBeInTheDocument();
  });

  it("Qualifiers render as a definition list of known fields", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const qualifiers = container.querySelector("[data-testid='assertion-section-qualifiers']") as HTMLElement;
    expect(within(qualifiers).getByText("Population")).toBeInTheDocument();
    expect(within(qualifiers).getByText("Long-tail research queries")).toBeInTheDocument();
    expect(within(qualifiers).getByText("Timeframe")).toBeInTheDocument();
    expect(within(qualifiers).getByText("2025-2026")).toBeInTheDocument();
  });

  it("Evaluation lists each verdict as a labeled row, not a bare boolean", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const evaluation = container.querySelector("[data-testid='assertion-section-evaluation']") as HTMLElement;
    expect(within(evaluation).getByText("Grounding")).toBeInTheDocument();
    expect(within(evaluation).getByText("Human review")).toBeInTheDocument();
    expect(within(evaluation).getAllByText("Pass")).toHaveLength(2);
  });

  it("Uses summarizes prior-use totals without a false lineage affordance", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} />,
      { wrapper: makeWrapper() },
    );
    const uses = container.querySelector("[data-testid='assertion-section-uses']") as HTMLElement;
    expect(uses.textContent).toContain("Used in 4 runs · 3 report revisions");
    expect(container.querySelector("[data-testid='assertion-view-lineage']")).toBeNull();
  });

  it("footer shows non-action access/reuse chips (no mutation action introduced)", () => {
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} onClose={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    const footer = container.querySelector(".rv-assertion-packet__footer") as HTMLElement;
    expect(within(footer).getByText("Personal")).toBeInTheDocument();
    expect(within(footer).getByText("Eligible for reuse")).toBeInTheDocument();
    expect(footer.querySelector("button")).toBeNull();
  });

  it("close control fires onClose and carries an accessible name", () => {
    const onClose = vi.fn();
    const { container } = render(
      <AssertionPacketInspector state={readyState(makeFullPacket())} onClose={onClose} />,
      { wrapper: makeWrapper() },
    );
    const closeBtn = container.querySelector("[data-testid='assertion-packet-close']") as HTMLElement;
    expect(closeBtn.getAttribute("aria-label")).toBe("Close source assertion inspector");
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("uses the inference discriminant in the close control's accessible name", () => {
    const { container } = render(
      <AssertionPacketInspector
        state={readyState(makeFullPacket({ assertion: { kind: "inference", lifecycle_state: "eligible" } }))}
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    expect(within(container).getByRole("button", { name: "Close inference inspector" })).toBeInTheDocument();
  });

  it("loading state is announced via role=status", () => {
    const { container } = render(
      <AssertionPacketInspector state={{ kind: "loading" }} />,
      { wrapper: makeWrapper() },
    );
    const loading = container.querySelector("[data-testid='assertion-packet-loading']");
    expect(loading).toHaveAttribute("role", "status");
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// B. LEGACY-MISSING — ReusableAssertionFieldsColumn / AssertionPacketFields
// ═════════════════════════════════════════════════════════════════════════════

describe("B. Legacy-missing provenance", () => {
  it("a claim without persistent_references renders the seven-row unavailable explainer, no inferred ids/versions", () => {
    const claim = makeClaim({ claim_id: "clm_043", text: "Legacy claim with no durable link." });
    const { container } = render(<ReusableAssertionFieldsColumn claim={claim} />, { wrapper: makeWrapper() });

    const column = container.querySelector("[data-testid='reusable-assertion-fields-legacy']") as HTMLElement;
    expect(column).not.toBeNull();
    expect(within(column).getByText(
      "This run predates persistent assertion fields. Run-local provenance remains available.",
    )).toBeInTheDocument();

    const rows = column.querySelectorAll(".rv-assertion-legacy-dl__row");
    expect(rows).toHaveLength(7);
    const labels = [
      "Persistent assertion ID",
      "Immutable source edition",
      "Exact passage selector",
      "Structured qualifiers",
      "Rights decision",
      "Freshness",
      "Impact data",
    ];
    rows.forEach((row, idx) => {
      expect(row.querySelector("dt")?.textContent).toContain(labels[idx]);
      expect(row.querySelector("dd")?.textContent).toBe("Unavailable in this export");
    });

    // No durable id/version is fabricated anywhere in this column.
    expect(column.querySelector("code")).toBeNull();
    expect(column.textContent).not.toMatch(/\bv\d+\b/);
  });

  it("mocked hook confirms the same legacy explainer even if useEvidencePacket were reached (defensive early return)", () => {
    mocks.useEvidencePacket.mockReturnValue({ state: { kind: "loading" } });
    const claim = makeClaim({ claim_id: "clm_044", text: "Second legacy claim." });
    const { container } = render(<ReusableAssertionFieldsColumn claim={claim} />, { wrapper: makeWrapper() });
    expect(container.querySelector("[data-testid='reusable-assertion-fields-legacy']")).not.toBeNull();
    expect(mocks.useEvidencePacket).toHaveBeenCalled();
  });

  it("field granularity: one absent packet field renders its own unavailable note without blanking populated sections", () => {
    const partialPacket = makeFullPacket({
      // Mirrors a real legacy artifact shape: the key is entirely absent, not null/empty.
      source_edition: undefined as unknown as Record<string, unknown>,
    });
    mocks.useEvidencePacket.mockReturnValue({
      state: { kind: "legacy-missing", data: partialPacket, missingFields: ["source_edition"] },
    });
    const claim = makeClaim({
      claim_id: "clm_045",
      text: "Claim with a durable link but a legacy-missing edition field.",
      persistent_references: { source_assertion_id: "ast_01JX7QF8M2" },
    });
    const { container } = render(<ReusableAssertionFieldsColumn claim={claim} />, { wrapper: makeWrapper() });

    const column = container.querySelector("[data-testid='reusable-assertion-fields']") as HTMLElement;
    expect(column).not.toBeNull();

    const edition = within(column).getByTestId("assertion-section-edition");
    expect(edition.textContent).toContain("Not recorded in this legacy artifact.");
    expect(edition.querySelector("code")).toBeNull();

    // Populated sections remain fully rendered — one missing field never collapses the rest.
    const passage = within(column).getByTestId("assertion-section-passage");
    expect(passage.querySelector("blockquote")?.textContent).toBe(
      "Hybrid retrieval increased Recall@50 by 22.3% compared with the best single retriever.",
    );
    const qualifiers = within(column).getByTestId("assertion-section-qualifiers");
    expect(within(qualifiers).getByText("Population")).toBeInTheDocument();
    const uses = within(column).getByTestId("assertion-section-uses");
    expect(uses.textContent).toContain("Used in 4 runs · 3 report revisions");
  });

  it("denied packet state surfaces the safe reason without rendering the legacy explainer", () => {
    mocks.useEvidencePacket.mockReturnValue({
      state: { kind: "denied", reasonCode: "rights_denied", reasonCopy: "Your current rights do not allow this assertion." },
    });
    const claim = makeClaim({
      claim_id: "clm_046",
      text: "Claim linked to a denied assertion.",
      persistent_references: { source_assertion_id: "ast_denied" },
    });
    const { container } = render(<ReusableAssertionFieldsColumn claim={claim} />, { wrapper: makeWrapper() });
    const column = container.querySelector("[data-testid='reusable-assertion-fields-denied']") as HTMLElement;
    expect(within(column).getByText("Reason:")).toBeInTheDocument();
    expect(within(column).getByText("rights_denied")).toBeInTheDocument();
    expect(container.querySelector("[data-testid='reusable-assertion-fields-legacy']")).toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// C. DENIED — AssertionDeniedPanel / AssertionCatalogPane
// ═════════════════════════════════════════════════════════════════════════════

describe("C. Denied catalog state", () => {
  it("renders the exact bounded-panel copy, a visible reason code, and role=status", () => {
    const { container } = render(
      <AssertionDeniedPanel reasonCode="assertion_ledger_access_denied" />,
      { wrapper: makeWrapper() },
    );
    const panel = container.querySelector("[data-testid='assertion-denied-panel']") as HTMLElement;
    expect(panel).toHaveAttribute("role", "status");
    expect(within(panel).getByText("Assertion ledger unavailable")).toBeInTheDocument();
    expect(within(panel).getByText("This workspace cannot access reusable assertion records.")).toBeInTheDocument();
    expect(within(panel).getByText("assertion_ledger_access_denied")).toBeInTheDocument();
    expect(within(panel).getByText(
      "No assertion content, counts, facets, suggestions, or prior-use metadata was loaded.",
    )).toBeInTheDocument();
    const recovery = within(panel).getByText(/Run-local research remains available from/);
    expect(recovery.querySelector("strong")?.textContent).toBe("Portfolio");
  });

  it("Return to Portfolio recovers to the run list route", () => {
    const { container } = render(
      <Routes>
        <Route path="/catalog" element={<AssertionDeniedPanel reasonCode="rights_denied" />} />
        <Route path="/runs" element={<div data-testid="runs-page">Portfolio</div>} />
      </Routes>,
      {
        wrapper: ({ children }: { children: ReactNode }) => {
          const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
          return (
            <MemoryRouter initialEntries={["/catalog"]}>
              <QueryClientProvider client={qc}>{children}</QueryClientProvider>
            </MemoryRouter>
          );
        },
      },
    );
    fireEvent.click(container.querySelector("[data-testid='assertion-denied-return']") as HTMLElement);
    expect(container.querySelector("[data-testid='runs-page']")).not.toBeNull();
  });

  it("AssertionCatalogPane denied search replaces filters, table, pagination, AND inspector together", () => {
    mocks.useAssertionSearch.mockReturnValue({
      data: undefined,
      isFetching: false,
      state: { kind: "denied", reasonCode: "assertion_ledger_access_denied", reasonCopy: "This workspace cannot access reusable assertion records." },
    });
    mocks.useEvidencePacket.mockReturnValue({ data: undefined, state: { kind: "loading" } });

    const { container } = render(<AssertionCatalogPane />, { wrapper: makeWrapper() });

    expect(container.querySelector("[data-testid='assertion-denied-panel']")).not.toBeNull();

    // Nothing candidate-derived survives alongside the denied panel.
    expect(container.querySelector("[data-testid='assertion-search-input']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-filter-lifecycle']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-filter-access']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-results-table']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-pagination']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-packet-inspector']")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-inspector-empty']")).toBeNull();
    expect(container.querySelectorAll("[data-testid^='assertion-row-']")).toHaveLength(0);
  });

  it("a denied search clears a prior selection and disables the packet query", async () => {
    const selected = { assertion_id: "ast_selected", assertion_version: 1, lifecycle_state: "eligible", access_scope: "personal", rights_decision: makeRights() };
    mocks.useAssertionSearch.mockReturnValue({
      data: { items: [selected], next_cursor: null, facets: { lifecycle_states: [], access_scopes: [] }, denial_reason: null },
      isFetching: false,
      state: { kind: "ready", data: { items: [selected], next_cursor: null, facets: { lifecycle_states: [], access_scopes: [] }, denial_reason: null } },
    });
    mocks.useEvidencePacket.mockReturnValue({ data: undefined, state: { kind: "loading" } });
    const { container, rerender } = render(<AssertionCatalogPane />, { wrapper: makeWrapper() });
    fireEvent.click(container.querySelector("[data-testid='assertion-row-ast_selected']") as HTMLElement);
    await waitFor(() => expect(mocks.useEvidencePacket).toHaveBeenLastCalledWith("ast_selected", expect.any(Function)));

    mocks.useAssertionSearch.mockReturnValue({
      data: undefined,
      isFetching: false,
      state: { kind: "denied", reasonCode: "assertion_ledger_access_denied", reasonCopy: "This workspace cannot access reusable assertion records." },
    });
    rerender(<AssertionCatalogPane />);

    await waitFor(() => expect(mocks.useEvidencePacket).toHaveBeenLastCalledWith(null, expect.any(Function)));
    expect(container.querySelector("[data-testid='assertion-packet-inspector']")).toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// D. STALE + IMPACT — AssertionStatusBand / AssertionInspector
// ═════════════════════════════════════════════════════════════════════════════

describe("D. Stale impact — AssertionStatusBand", () => {
  it("renders the exact blocking copy and role=status when not a live transition", () => {
    const { container } = render(
      <AssertionStatusBand visible reasonCode="dependency_manifest_missing" onViewImpactReceipt={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    const band = container.querySelector("[data-testid='assertion-status-band']") as HTMLElement;
    expect(band).toHaveAttribute("role", "status");
    expect(within(band).getByText("Reuse blocked — dependency manifest missing")).toBeInTheDocument();
    expect(within(band).getByText(
      "The dependency manifest required to verify downstream impact is missing, so reuse remains blocked.",
    )).toBeInTheDocument();
  });

  it("uses role=alert only when the block became active during this interaction", () => {
    const { container } = render(
      <AssertionStatusBand visible reasonCode="dependency_manifest_missing" onViewImpactReceipt={vi.fn()} justBecameBlocked />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='assertion-status-band']")).toHaveAttribute("role", "alert");
  });

  it("renders nothing when not visible, and wires View impact receipt when shown", () => {
    const onView = vi.fn();
    const { container, rerender } = render(
      <AssertionStatusBand visible={false} reasonCode="dependency_manifest_missing" onViewImpactReceipt={onView} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='assertion-status-band']")).toBeNull();

    rerender(<AssertionStatusBand visible reasonCode="dependency_manifest_missing" onViewImpactReceipt={onView} />);
    fireEvent.click(container.querySelector("[data-testid='view-impact-receipt-btn']") as HTMLElement);
    expect(onView).toHaveBeenCalledTimes(1);
  });
});

describe("D. Stale impact — ClaimAuditWorkbench authority", () => {
  it("uses a blocked authoritative impact DTO when the immutable packet remains current", () => {
    const currentPacket = makeFullPacket({
      assertion: {
        kind: "source_assertion",
        lifecycle_state: "eligible",
        assertion_text: "The packet remains current provenance.",
      },
    });
    mocks.useEvidencePacket.mockReturnValue({
      data: currentPacket,
      state: { kind: "ready", data: currentPacket },
    });
    const impact = makeBlockedImpactSummary({
      lifecycle_state: "blocked",
      reason_code: "dependency_manifest_invalid",
    });
    mocks.useAssertionImpact.mockReturnValue({
      data: impact,
      state: { kind: "ready", data: impact },
    });
    const run = {
      schema_version: "1.5",
      run_id: "run_impact_authority",
      status_derived: "complete",
      claims: [makeClaim({ claim_id: "clm_impact", text: "Impact authority test." })],
    } as RFRunExport;

    const { container } = render(
      <ClaimAuditWorkbench run={run} assertionId={currentPacket.assertion_id} />,
      { wrapper: makeWrapper() },
    );

    const band = container.querySelector("[data-testid='assertion-status-band']") as HTMLElement;
    expect(band).not.toBeNull();
    expect(within(band).getByText("Reuse blocked — dependency manifest invalid")).toBeInTheDocument();
    expect(within(band).queryByText("Reuse blocked — dependency manifest missing")).toBeNull();
    expect(container.querySelector("[data-testid='assertion-inspector']")).not.toBeNull();
    expect(container.querySelector("[data-testid='impact-operation']")).not.toBeNull();
    expect(within(container.querySelector("[data-testid='impact-operation']") as HTMLElement).getByTestId("impact-lifecycle-chip")).toHaveTextContent("Blocked");
  });
});

describe("D. Stale impact — AssertionInspector", () => {
  it("separates Stale (lifecycle) and Reuse blocked (state) as two distinct labeled facts", () => {
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    const lifecycle = container.querySelector(".rv-assertion-lifecycle-facts") as HTMLElement;
    expect(within(lifecycle).getByText("stale")).toBeInTheDocument();
    expect(within(lifecycle).getByText("Reuse blocked")).toBeInTheDocument();
  });

  it("shows the freshness receipt reason, edition transition, and detected timestamp", () => {
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    expect(container.textContent).toContain("dependency_manifest_missing");
    expect(container.textContent).toContain("sed_old_014");
    expect(container.textContent).toContain("sed_new_015");
    expect(container.textContent).toContain("2026-02-01T00:00:00Z");
  });

  it("labels the historical passage as non-reusable when the assertion is stale", () => {
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    const passageChip = container.querySelector(".rv-assertion-passage__chip");
    expect(passageChip?.textContent).toBe("Historical · non-reusable");
  });

  it("affected-use groups come only from the typed action list, in first-seen order, with writeback as a status breakdown", () => {
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    const rows = Array.from(container.querySelectorAll("[data-testid^='affected-use-']"));
    const labels = rows.map((r) => r.querySelector(".rv-assertion-affected-uses__label")?.textContent);
    expect(labels).toEqual([
      "Assertion versions",
      "Relationships / inferences",
      "Indexes / caches",
      "Exports / projections",
      "Writebacks",
      "Report revisions",
      "Runs",
    ]);
    const writebackRow = container.querySelector("[data-testid='affected-use-mock_writeback_receipt']") as HTMLElement;
    expect(writebackRow.querySelector(".rv-assertion-affected-uses__badge")?.textContent).toBe("1 denied · 1 Unavailable");
    const writebackActions = Array.from(container.querySelectorAll("[data-testid^='impact-action-']"))
      .filter((action) => action.textContent?.includes("wb_"));
    expect(writebackActions[0]).toHaveTextContent(/Action status\s*completed/);
    expect(writebackActions[0]).toHaveTextContent(/Writeback disposition\s*default_denied/);
    expect(writebackActions[1]).toHaveTextContent(/Action status\s*pending/);
    expect(writebackActions[1]).toHaveTextContent(/Writeback disposition\s*Unavailable/);
    const versionsRow = container.querySelector("[data-testid='affected-use-assertion_version']") as HTMLElement;
    expect(versionsRow.querySelector(".rv-assertion-affected-uses__badge")?.textContent).toBe("2");
  });

  it("preserves receipt action order and announces completion progress", () => {
    const interleavedActions: AssertionImpactAction[] = [
      { object_id: "av_first", object_class: "assertion_version", action: "block_reuse", status: "completed" },
      { object_id: "av_last", object_class: "assertion_version", action: "block_reuse", status: "completed" },
      { object_id: "edge_middle", object_class: "canonical_claim_edge", action: "mark_stale", status: "pending" },
    ];
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary({ actions: interleavedActions }) }} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='impact-actions']")?.textContent).toContain("2 of 3 actions completed");
    const renderedActions = Array.from(container.querySelectorAll("[data-testid^='impact-action-']"));
    expect(renderedActions.map((action) => action.textContent)).toEqual([
      expect.stringContaining("av_first"),
      expect.stringContaining("av_last"),
      expect.stringContaining("edge_middle"),
    ]);
  });

  it("shows the impact operation signature and a pending reconciliation line", () => {
    const { container } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    const op = container.querySelector("[data-testid='impact-operation']") as HTMLElement;
    expect(within(op).getByText("evt_supersede_017")).toBeInTheDocument();
    expect(within(op).getByText("pending")).toBeInTheDocument();
    const reconciliation = container.querySelector("[data-testid='reconciliation']") as HTMLElement;
    expect(reconciliation.textContent).toContain("Deterministic reconciliation pending");
  });

  it("never renders a blocked operation as completed or safe", () => {
    const { container } = render(
      <AssertionInspector
        packet={makeStalePacket()}
        impactState={{ kind: "ready", data: makeBlockedImpactSummary() }}
      />,
      { wrapper: makeWrapper() },
    );
    const op = container.querySelector("[data-testid='impact-operation']") as HTMLElement;
    const chip = within(op).getByText("blocked");
    expect(chip.className).toContain("red");
    expect(op.textContent).not.toContain("completed");
    const reconciliation = container.querySelector("[data-testid='reconciliation']") as HTMLElement;
    expect(reconciliation.textContent).toContain("Deterministic reconciliation blocked");
  });

  it("Open replacement edition renders only when the typed receipt supplies a target", () => {
    const { container, rerender } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "ready", data: makeImpactSummary() }} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='open-replacement-edition-btn']")).toBeNull();

    const onOpen = vi.fn();
    rerender(
      <AssertionInspector
        packet={makeStalePacket()}
        impactState={{ kind: "ready", data: makeImpactSummary({ replacement_edition_id: "sed_new_015" }) }}
        onOpenReplacementEdition={onOpen}
      />,
    );
    const btn = container.querySelector("[data-testid='open-replacement-edition-btn']") as HTMLElement;
    expect(btn).not.toBeNull();
    fireEvent.click(btn);
    expect(onOpen).toHaveBeenCalledWith("sed_new_015");
  });

  it("impact-unavailable state (including unknown enum values) shows zero counts and no replacement control", () => {
    const { container } = render(
      <AssertionInspector
        packet={makeStalePacket()}
        impactState={{ kind: "unavailable", rawValue: "some_future_status", data: makeImpactSummary(), zeroCounts: true }}
      />,
      { wrapper: makeWrapper() },
    );
    const unavailable = container.querySelector("[data-testid='impact-unavailable']") as HTMLElement;
    expect(within(unavailable).getByText("Impact data unavailable")).toBeInTheDocument();
    expect(container.querySelector("[data-testid='affected-uses']")).toBeNull();
    expect(container.querySelector("[data-testid='impact-operation']")).toBeNull();
    expect(container.querySelector("[data-testid='open-replacement-edition-btn']")).toBeNull();
  });

  it("impact loading and denied states never fabricate counts either", () => {
    const { container, rerender } = render(
      <AssertionInspector packet={makeStalePacket()} impactState={{ kind: "loading" }} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='impact-loading']")).not.toBeNull();
    expect(container.querySelector("[data-testid='affected-uses']")).toBeNull();

    rerender(
      <AssertionInspector
        packet={makeStalePacket()}
        impactState={{ kind: "denied", reasonCode: "rights_denied", reasonCopy: "Your current rights do not allow this assertion." }}
      />,
    );
    const denied = container.querySelector("[data-testid='impact-denied']") as HTMLElement;
    expect(within(denied).getByText("Impact data unavailable")).toBeInTheDocument();
    expect(container.querySelector("[data-testid='affected-uses']")).toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// E. ASSERTION-ONLY — AssertionOnlyLineage
// ═════════════════════════════════════════════════════════════════════════════

describe("E. Assertion-only lineage (canonical claims disabled by default)", () => {
  function stubReadyLineageAndPacket() {
    mocks.useEvidencePacket.mockReturnValue({
      state: {
        kind: "ready",
        data: makeFullPacket({
          access_scope: "personal",
          qualifiers: { population: "Long-tail research queries" },
        }),
      },
    });
    mocks.useAssertionLineage.mockReturnValue({
      state: {
        kind: "ready",
        data: {
          assertion_id: "ast_01JX7QF8M2",
          assertion_version: 3,
          relationships: [
            { kind: "inference", text: "The finding generalizes across retrieval backends.", inputs: ["ast_a", "ast_b"] },
          ],
          run_uses: ["run_1", "run_2", "run_3", "run_4"],
          report_uses: ["rev_1", "rev_2", "rev_3"],
          denial_reason: null,
        },
      },
    });
  }

  it("shows the exact assertion-only notice title and copy, with no merge control or canonical node", () => {
    stubReadyLineageAndPacket();
    const { container } = render(
      <AssertionOnlyLineage assertionId="ast_01JX7QF8M2" />,
      { wrapper: makeWrapper() },
    );
    const notice = container.querySelector("[data-testid='assertion-only-notice']") as HTMLElement;
    expect(within(notice).getByText("Assertion-only mode")).toBeInTheDocument();
    expect(within(notice).getByText(
      "Canonical claim grouping is disabled pending an independently labeled merge audit.",
    )).toBeInTheDocument();

    expect(container.querySelector("[data-testid='canonical-relationship-absent-notice']")).toBeNull();
    Array.from(container.querySelectorAll("button")).forEach((btn) => {
      expect(btn.textContent?.toLowerCase() ?? "").not.toContain("merge canonical");
    });
  });

  it("labels an inference derivation distinctly from a source assertion", () => {
    stubReadyLineageAndPacket();
    const { container } = render(
      <AssertionOnlyLineage assertionId="ast_01JX7QF8M2" />,
      { wrapper: makeWrapper() },
    );
    expect(container.textContent).toContain("INFERENCE · DERIVED");
    expect(container.textContent).toContain("Inputs: ast_a, ast_b");
  });

  it("provides the established selectable tree alternative for keyboard review", () => {
    stubReadyLineageAndPacket();
    const { container } = render(
      <AssertionOnlyLineage assertionId="ast_01JX7QF8M2" />,
      { wrapper: makeWrapper() },
    );
    fireEvent.click(within(container).getByTestId("assertion-lineage-view-list"));
    const tree = within(container).getByRole("tree", { name: "Assertion lineage explorer" });
    const assertion = within(tree).getByTestId("lineage-node-assertion");
    assertion.focus();
    fireEvent.keyDown(assertion, { key: "Enter" });
    expect(assertion).toHaveAttribute("aria-selected", "true");
    expect(tree.textContent).toContain("Source edition");
    expect(tree.textContent).toContain("Passage");
    expect(tree.textContent).toContain("Inference · derived");
    expect(tree.textContent).toContain("Report / run uses");
  });

  it("selected-assertion inspector separately shows durable identity, lifecycle, qualifiers, access, reuse, rights, and prior uses", () => {
    stubReadyLineageAndPacket();
    const { container } = render(
      <AssertionOnlyLineage assertionId="ast_01JX7QF8M2" onOpenProvenance={vi.fn()} onViewPriorUses={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    const inspector = container.querySelector("[data-testid='assertion-only-inspector']") as HTMLElement;
    expect(inspector).not.toBeNull();
    expect(within(inspector).getByText("Durable identity")).toBeInTheDocument();
    expect(within(inspector).getByText("ast_01JX7QF8M2")).toBeInTheDocument();
    expect(within(inspector).getByText("Lifecycle")).toBeInTheDocument();
    expect(within(inspector).getByText("Current")).toBeInTheDocument();
    expect(within(inspector).getByText("Qualifiers")).toBeInTheDocument();
    expect(within(inspector).getByText("Access")).toBeInTheDocument();
    expect(within(inspector).getByText("Personal")).toBeInTheDocument();
    expect(within(inspector).getByText("Reuse decision")).toBeInTheDocument();
    expect(within(inspector).getByText("Eligible for reuse")).toBeInTheDocument();
    expect(within(inspector).getByText("Rights")).toBeInTheDocument();
    expect(within(inspector).getByText("Reuse allowed")).toBeInTheDocument();
    expect(within(inspector).getByText("Prior uses")).toBeInTheDocument();
    expect(within(inspector).getByRole("button", { name: "7 total" })).toBeInTheDocument();
    expect(within(inspector).getByText("Open provenance")).toBeInTheDocument();
    expect(within(inspector).getByText("View prior uses")).toBeInTheDocument();
  });

  it("shows an in-flow empty state (never a crash) when no assertion is selected yet", () => {
    mocks.useEvidencePacket.mockReturnValue({ state: { kind: "loading" } });
    mocks.useAssertionLineage.mockReturnValue({ state: { kind: "loading" } });
    const { container } = render(<AssertionOnlyLineage assertionId={null} />, { wrapper: makeWrapper() });
    expect(container.querySelector("[data-testid='assertion-only-inspector-empty']")).not.toBeNull();
    // Still assertion-only mode even before a selection is made.
    expect(container.querySelector("[data-testid='assertion-only-notice']")).not.toBeNull();
  });

  it("renders unknown lifecycle/access and absent rights as field-level unavailable states", () => {
    mocks.useEvidencePacket.mockReturnValue({
      state: {
        kind: "ready",
        data: makeFullPacket({
          assertion: { kind: "source_assertion", lifecycle_state: "future_lifecycle" },
          access_scope: "future_scope",
          rights_decision: undefined as unknown as RightsDecision,
        }),
      },
    });
    mocks.useAssertionLineage.mockReturnValue({
      state: { kind: "denied", reasonCode: "rights_denied", reasonCopy: "Your current rights do not allow this assertion." },
    });
    const { container } = render(<AssertionOnlyLineage assertionId="ast_01JX7QF8M2" />, { wrapper: makeWrapper() });
    const inspector = container.querySelector("[data-testid='assertion-only-inspector']") as HTMLElement;
    expect(within(inspector).getByText("Unavailable (future_lifecycle)")).toBeInTheDocument();
    expect(within(inspector).getByText("Unavailable (future_scope)")).toBeInTheDocument();
    expect(within(inspector).getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(container.querySelector("[data-testid='assertion-lineage-unavailable']")?.textContent).toContain("Lineage unavailable");
  });

  it("derives assertion-only lineage from the selected claim in the production RunDetailWorkspace path", () => {
    stubReadyLineageAndPacket();
    const run = {
      schema_version: "1.5",
      run_id: "run_assertion_lineage",
      status_derived: "complete",
      claims: [makeClaim({
        claim_id: "clm_with_assertion",
        text: "A claim with a durable assertion link.",
        persistent_references: { source_assertion_id: "ast_01JX7QF8M2" },
      })],
    } as RFRunExport;
    const { container } = render(
      <RunDetailWorkspace
        run={run}
        activeTab="lineage"
        selectedClaimId="clm_with_assertion"
        mode="page"
        onTabChange={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='assertion-only-lineage']")).not.toBeNull();
    expect(container.querySelector("[data-testid='assertion-only-inspector']")?.textContent).toContain("ast_01JX7QF8M2");
  });

  it("re-derives lineage from post-change run data on a workspace/auth-scope transition", async () => {
    stubReadyLineageAndPacket();
    const preChangeRun = {
      schema_version: "1.5",
      run_id: "run_scope_transition",
      status_derived: "complete",
      claims: [makeClaim({
        claim_id: "clm_prior_scope",
        text: "A claim selected before the scope transition.",
        persistent_references: { source_assertion_id: "ast_same_id_across_scopes" },
      })],
    } as RFRunExport;
    const postChangeRun = {
      ...preChangeRun,
      claims: [makeClaim({
        claim_id: "clm_prior_scope",
        text: "The same claim was resolved from post-change workspace data.",
        persistent_references: { source_assertion_id: "ast_same_id_across_scopes" },
      })],
    } as RFRunExport;
    const scopeA: AuthContextValue = {
      identity: { user_id: "reviewer", workspace_id: "ws-a", roles: ["reviewer"] },
      isLoading: false,
      provider: "local_static",
      authMode: "local_static",
    };
    const scopeB: AuthContextValue = {
      ...scopeA,
      identity: { ...scopeA.identity!, workspace_id: "ws-b" },
    };

    const { rerender } = render(
      <AuthContext.Provider value={scopeA}>
        <RunDetailWorkspace
          run={preChangeRun}
          activeTab="lineage"
          selectedClaimId="clm_prior_scope"
          mode="page"
          onTabChange={vi.fn()}
        />
      </AuthContext.Provider>,
      { wrapper: makeWrapper() },
    );
    expect(mocks.useEvidencePacket).toHaveBeenLastCalledWith("ast_same_id_across_scopes");
    expect(mocks.useAssertionLineage).toHaveBeenLastCalledWith("ast_same_id_across_scopes");

    rerender(
      <AuthContext.Provider value={scopeB}>
        <RunDetailWorkspace
          run={postChangeRun}
          activeTab="lineage"
          selectedClaimId="clm_prior_scope"
          mode="page"
          onTabChange={vi.fn()}
        />
      </AuthContext.Provider>,
    );

    await waitFor(() => {
      expect(mocks.useEvidencePacket).toHaveBeenLastCalledWith("ast_same_id_across_scopes");
      expect(mocks.useAssertionLineage).toHaveBeenLastCalledWith("ast_same_id_across_scopes");
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// F. INTERACTION / A11Y — AssertionResultsTable, ProvenanceModal, CopyIdButton
// ═════════════════════════════════════════════════════════════════════════════

describe("F. Results table selection — aria-selected and keyboard select-without-modal", () => {
  const ITEMS: AssertionSummary[] = [
    { assertion_id: "ast_1", assertion_version: 2, lifecycle_state: "eligible", access_scope: "personal", rights_decision: makeRights() },
    { assertion_id: "ast_2", assertion_version: 1, lifecycle_state: "stale", access_scope: "work_sensitive", rights_decision: makeRights({ allowed: false, reason_code: "dependency_manifest_invalid" }) },
  ];

  it("exposes aria-selected on the active row only", () => {
    const { container } = render(
      <AssertionResultsTable items={ITEMS} selectedId="ast_1" onSelect={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='assertion-row-ast_1']")).toHaveAttribute("aria-selected", "true");
    expect(container.querySelector("[data-testid='assertion-row-ast_2']")).toHaveAttribute("aria-selected", "false");
  });

  it("Enter selects a row without opening a modal", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <AssertionResultsTable items={ITEMS} selectedId={null} onSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    fireEvent.keyDown(container.querySelector("[data-testid='assertion-row-ast_2']") as HTMLElement, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("ast_2");
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });

  it("Space selects a row without opening a modal", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <AssertionResultsTable items={ITEMS} selectedId={null} onSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    fireEvent.keyDown(container.querySelector("[data-testid='assertion-row-ast_1']") as HTMLElement, { key: " " });
    expect(onSelect).toHaveBeenCalledWith("ast_1");
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });

  it("row click also selects without opening a modal", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <AssertionResultsTable items={ITEMS} selectedId={null} onSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    fireEvent.click(container.querySelector("[data-testid='assertion-row-ast_1']") as HTMLElement);
    expect(onSelect).toHaveBeenCalledWith("ast_1");
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });
});

describe("F. ProvenanceModal — status banners, close, and focus-return contract", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_050", text: "Claim used for focus-return interaction tests.", sources: [] }),
  ];

  function ModalHarness({ claims, claimId }: { claims: RFClaim[]; claimId: string }) {
    const modalRef = useRef<ProvenanceModalHandle>(null);
    return (
      <>
        <button data-testid="open-provenance-btn" onClick={() => modalRef.current?.open(claimId)}>
          Open provenance
        </button>
        <ProvenanceModal ref={modalRef} claims={claims} />
      </>
    );
  }

  it("modal close button has an accessible name and dismisses the dialog", () => {
    const { container } = render(<ModalHarness claims={CLAIMS} claimId="clm_050" />, { wrapper: makeWrapper() });
    fireEvent.click(container.querySelector("[data-testid='open-provenance-btn']") as HTMLElement);
    const closeBtn = container.querySelector("[data-testid='modal-close']") as HTMLElement;
    expect(closeBtn.getAttribute("aria-label")).toBe("Close provenance modal");
    act(() => { fireEvent.click(closeBtn); });
    expect(container.querySelector("[data-testid='provenance-modal']")).toBeNull();
  });

  it("close returns focus to the invoking Open provenance control", () => {
    const { container } = render(<ModalHarness claims={CLAIMS} claimId="clm_050" />, { wrapper: makeWrapper() });
    const openBtn = container.querySelector("[data-testid='open-provenance-btn']") as HTMLElement;
    openBtn.focus();
    act(() => { fireEvent.click(openBtn); });
    const closeBtn = container.querySelector("[data-testid='modal-close']") as HTMLElement;
    act(() => { fireEvent.click(closeBtn); });
    expect(document.activeElement).toBe(openBtn);
  });

  it("modal dialog role and aria-modal are present for assistive tech", () => {
    const { container } = render(<ModalHarness claims={CLAIMS} claimId="clm_050" />, { wrapper: makeWrapper() });
    fireEvent.click(container.querySelector("[data-testid='open-provenance-btn']") as HTMLElement);
    const dialog = container.querySelector("[data-testid='provenance-modal']") as HTMLElement;
    expect(dialog).toHaveAttribute("role", "dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("Escape closes only the modal (regression guard, not a new behavior)", () => {
    const { container } = render(<ModalHarness claims={CLAIMS} claimId="clm_050" />, { wrapper: makeWrapper() });
    fireEvent.click(container.querySelector("[data-testid='open-provenance-btn']") as HTMLElement);
    fireEvent.keyDown(container.querySelector("[data-testid='provenance-modal-overlay']") as HTMLElement, { key: "Escape" });
    expect(container.querySelector("[data-testid='provenance-modal']")).toBeNull();
  });

  it("moves initial focus into the modal and traps Tab/Shift+Tab between its controls", () => {
    const focusClaims: RFClaim[] = [
      makeClaim({
        claim_id: "clm_inference",
        text: "Inference with an available chain target.",
        status: "inference",
        claim_type: "inference",
        inference_basis: { from_claims: ["clm_source"] },
        sources: [],
      }),
      makeClaim({ claim_id: "clm_source", text: "Source claim.", sources: [] }),
    ];
    const { container } = render(<ModalHarness claims={focusClaims} claimId="clm_inference" />, { wrapper: makeWrapper() });
    fireEvent.click(container.querySelector("[data-testid='open-provenance-btn']") as HTMLElement);
    const close = container.querySelector("[data-testid='modal-close']") as HTMLElement;
    const last = container.querySelector("[data-testid='modal-chain-link-clm_source']") as HTMLElement;
    expect(document.activeElement).toBe(close);
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(close);
  });
});

describe("F. CopyIdButton — object-specific accessible names", () => {
  it("uses the exact caller-supplied accessible name and copies the given value", async () => {
    const { container } = render(
      <CopyIdButton value="ast_01JX7QF8M2" label="Copy source assertion ID" />,
      { wrapper: makeWrapper() },
    );
    const button = within(container).getByRole("button", { name: "Copy source assertion ID" });
    await act(async () => {
      fireEvent.click(button);
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("ast_01JX7QF8M2");
  });

  it("renders distinct accessible names for distinct object copy controls in the same packet", () => {
    const { container } = render(
      <AssertionPacketInspector
        state={{ kind: "ready", data: makeFullPacket() }}
      />,
      { wrapper: makeWrapper() },
    );
    expect(within(container).getByRole("button", { name: "Copy source edition ID" })).toBeInTheDocument();
    expect(within(container).getByRole("button", { name: "Copy passage ID" })).toBeInTheDocument();
    expect(within(container).getByRole("button", { name: "Copy locator" })).toBeInTheDocument();
  });
});
