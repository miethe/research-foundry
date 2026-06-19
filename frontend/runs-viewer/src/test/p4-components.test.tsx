/**
 * P4-VITEST — Phase 4 component tests.
 *
 * Tests cover (per P4 success criteria and task assignments):
 *   (1)  ClaimLedgerTable: renders all clm_NNN rows; row click fires onClaimSelect;
 *        each row has id=clm_NNN anchor
 *   (2)  LedgerFacets: multi-facet AND logic; empty selection shows all
 *   (3)  SourceCard sensitivity (P4-SENS-001 / R9 gate): work_sensitive → redaction
 *        placeholder, NOT verbatim quote/summary; public → real quote renders
 *   (4)  ProvenanceModal — open/close; ≤2 clicks to verbatim quote
 *   (5)  ProvenanceModal inference chain (P4-VITEST-INFERENCE / RIB-018 class):
 *        non-empty from_claims → linked chain; empty from_claims → RIB-018 warning
 *   (6)  ReportRenderer: every [claim:clm_NNN] renders as a clickable ClaimChip
 *   (7)  CompositionSidebar: clicking category dims non-matching chips
 *   (8)  LineageGraph: populated run renders graph; empty claims → empty-state
 */

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, act }   from "@testing-library/react";
import { MemoryRouter }             from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRef }                   from "react";
import type { ReactNode }           from "react";

// Components under test
import { ClaimLedgerTable }   from "@/components/ClaimLedger/ClaimLedgerTable";
import { LedgerFacets }       from "@/components/ClaimLedger/LedgerFacets";
import { SourceCard }         from "@/components/SourceCard/SourceCard";
import { ProvenanceModal }    from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";
import { ReportRenderer }     from "@/components/ReportOverlay/ReportRenderer";
import { ClaimChip }          from "@/components/ReportOverlay/ClaimChip";
import { CompositionSidebar } from "@/components/ReportOverlay/CompositionSidebar";
import { ArtifactLineageGraph } from "@/components/LineageGraph/LineageGraph";

// Types
import type { RFClaim, RFRunExport } from "@/types/rf";

// Fixtures
import fixtureRunRaw from "@/test/fixtures/run.json";
import { WORK_SENSITIVE_SOURCE, PUBLIC_SOURCE } from "@/test/fixtures/sensitive-sources";
import {
  INFERENCE_CLAIMS_WITH_BASIS,
  INFERENCE_CLAIMS_EMPTY_BASIS,
} from "@/test/fixtures/inference-claims";

const fixtureRun = fixtureRunRaw as unknown as RFRunExport;

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

/** Minimal RFClaim builder for ledger tests. */
function makeClaim(overrides: Partial<RFClaim> & { claim_id: string; text: string }): RFClaim {
  return {
    materiality:    "core",
    claim_type:     "factual",
    status:         "supported",
    confidence:     "high",
    inference_basis: { from_claims: [], reasoning_summary: null },
    sources:        [],
    ...overrides,
  };
}

// ── (1) ClaimLedgerTable ──────────────────────────────────────────────────────

describe("ClaimLedgerTable", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_001", text: "First claim text about feature A." }),
    makeClaim({ claim_id: "clm_002", text: "Second claim text about feature B.", status: "inference" }),
    makeClaim({ claim_id: "clm_003", text: "Third claim text about feature C.", status: "speculation", confidence: "low" }),
  ];

  it("renders a row for every claim in the array", () => {
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelectorAll("[data-testid^='ledger-row-']")).toHaveLength(3);
    expect(container.querySelector("[data-testid='ledger-row-clm_001']")).not.toBeNull();
    expect(container.querySelector("[data-testid='ledger-row-clm_002']")).not.toBeNull();
    expect(container.querySelector("[data-testid='ledger-row-clm_003']")).not.toBeNull();
  });

  it("each row has id=clm_NNN for deep-link anchoring", () => {
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    CLAIMS.forEach((c) => {
      const row = container.querySelector(`#${c.claim_id}`);
      expect(row).not.toBeNull();
    });
  });

  it("row click fires onClaimSelect with the correct claimId", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='ledger-row-clm_002']") as HTMLElement;
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith("clm_002");
  });

  it("row click fires correct claimId for the last row", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='ledger-row-clm_003']") as HTMLElement;
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith("clm_003");
  });

  it("Enter key on row fires onClaimSelect", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='ledger-row-clm_001']") as HTMLElement;
    fireEvent.keyDown(row, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("clm_001");
  });

  it("renders status badge for each row", () => {
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='ledger-status-clm_001']")?.textContent).toMatch(/supported/i);
    expect(container.querySelector("[data-testid='ledger-status-clm_002']")?.textContent).toMatch(/inference/i);
    expect(container.querySelector("[data-testid='ledger-status-clm_003']")?.textContent).toMatch(/speculation/i);
  });

  it("renders empty-state when claims array is empty", () => {
    const { container } = render(
      <ClaimLedgerTable claims={[]} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='ledger-empty']")).not.toBeNull();
    expect(container.querySelector("[data-testid='ledger-table']")).toBeNull();
  });

  it("renders all clm_NNN rows from the real fixture (91 claims)", () => {
    const { container } = render(
      <ClaimLedgerTable claims={fixtureRun.claims} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    const rows = container.querySelectorAll("[data-testid^='ledger-row-']");
    expect(rows.length).toBe(fixtureRun.claims.length);
    // Spot-check the first claim ID
    expect(container.querySelector("#clm_001")).not.toBeNull();
  });

  it("marks selected row with aria-selected=true", () => {
    const { container } = render(
      <ClaimLedgerTable claims={CLAIMS} onClaimSelect={() => {}} selectedClaimId="clm_002" />,
      { wrapper: makeWrapper() },
    );
    const selectedRow = container.querySelector("[data-testid='ledger-row-clm_002']");
    expect(selectedRow?.getAttribute("aria-selected")).toBe("true");
    const otherRow = container.querySelector("[data-testid='ledger-row-clm_001']");
    expect(otherRow?.getAttribute("aria-selected")).toBe("false");
  });
});

// ── (2) LedgerFacets — multi-facet AND logic ──────────────────────────────────

describe("LedgerFacets", () => {
  /** Four claims spanning all three status and materiality types */
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_a", text: "A", status: "supported",   materiality: "core",       claim_type: "factual",     confidence: "high"   }),
    makeClaim({ claim_id: "clm_b", text: "B", status: "inference",   materiality: "background", claim_type: "inference",   confidence: "medium" }),
    makeClaim({ claim_id: "clm_c", text: "C", status: "speculation", materiality: "core",       claim_type: "speculation", confidence: "low"    }),
    makeClaim({ claim_id: "clm_d", text: "D", status: "supported",   materiality: "background", claim_type: "factual",     confidence: "medium" }),
  ];

  it("emits all claims when no facets are active (empty selection shows all)", () => {
    const onFiltered = vi.fn();
    render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    // First call is the initial useEffect emission
    expect(onFiltered).toHaveBeenCalled();
    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(4);
  });

  it("single status facet narrows to matching claims only", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    // Click the "supported" status facet
    const pill = container.querySelector("[data-testid='facet-pill-status-supported']") as HTMLElement;
    act(() => { fireEvent.click(pill); });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall.map((c) => c.claim_id)).toEqual(expect.arrayContaining(["clm_a", "clm_d"]));
    expect(lastCall).toHaveLength(2);
  });

  it("multi-facet AND logic: status=supported AND materiality=core yields only clm_a", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    // Click status=supported AND materiality=core
    const statusPill = container.querySelector("[data-testid='facet-pill-status-supported']") as HTMLElement;
    const matPill    = container.querySelector("[data-testid='facet-pill-materiality-core']") as HTMLElement;
    act(() => { fireEvent.click(statusPill); });
    act(() => { fireEvent.click(matPill); });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(1);
    expect(lastCall[0]?.claim_id).toBe("clm_a");
  });

  it("multi-facet AND logic: status=inference AND claim_type=inference yields only clm_b", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    const statusPill   = container.querySelector("[data-testid='facet-pill-status-inference']") as HTMLElement;
    const typePill     = container.querySelector("[data-testid='facet-pill-claim_type-inference']") as HTMLElement;
    act(() => { fireEvent.click(statusPill); });
    act(() => { fireEvent.click(typePill); });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(1);
    expect(lastCall[0]?.claim_id).toBe("clm_b");
  });

  it("three-facet AND logic: status=supported AND confidence=high AND claim_type=factual yields only clm_a", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='facet-pill-status-supported']") as HTMLElement);
      fireEvent.click(container.querySelector("[data-testid='facet-pill-confidence-high']") as HTMLElement);
      fireEvent.click(container.querySelector("[data-testid='facet-pill-claim_type-factual']") as HTMLElement);
    });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(1);
    expect(lastCall[0]?.claim_id).toBe("clm_a");
  });

  it("AND logic with contradicting facets produces empty result", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    // status=inference AND confidence=high — no claim satisfies both
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='facet-pill-status-inference']") as HTMLElement);
      fireEvent.click(container.querySelector("[data-testid='facet-pill-confidence-high']") as HTMLElement);
    });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(0);
  });

  it("clear-all button resets to showing all claims", () => {
    const onFiltered = vi.fn();
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={onFiltered} />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='facet-pill-status-supported']") as HTMLElement);
    });
    // Clear button should be visible now
    const clearBtn = container.querySelector("[data-testid='facet-clear']") as HTMLElement;
    expect(clearBtn).not.toBeNull();
    act(() => { fireEvent.click(clearBtn); });

    const lastCall = onFiltered.mock.calls[onFiltered.mock.calls.length - 1]![0] as RFClaim[];
    expect(lastCall).toHaveLength(4);
  });

  it("renders the facets panel with correct testId", () => {
    const { container } = render(
      <LedgerFacets claims={CLAIMS} onFiltered={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='ledger-facets']")).not.toBeNull();
  });
});

// ── (3) SourceCard sensitivity (P4-SENS-001 / R9 gate) ───────────────────────

describe("SourceCard — sensitivity gate (R9 defense-in-depth)", () => {
  it("work_sensitive source renders the redaction placeholder", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const redacted = container.querySelector(
      "[data-testid='source-card-redacted-src_sensitive_001']",
    );
    expect(redacted).not.toBeNull();
  });

  it("work_sensitive source does NOT render the verbatim quote toggle", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const toggle = container.querySelector(
      "[data-testid='source-card-quote-toggle-src_sensitive_001']",
    );
    expect(toggle).toBeNull();
  });

  it("work_sensitive source: redaction placeholder contains sensitivity label", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const redacted = container.querySelector(
      "[data-testid='source-card-redacted-src_sensitive_001']",
    );
    expect(redacted?.textContent).toContain("work_sensitive");
  });

  it("work_sensitive source: data-redacted=true attribute is set", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const card = container.querySelector(
      "[data-testid='source-card-src_sensitive_001']",
    );
    expect(card?.getAttribute("data-redacted")).toBe("true");
  });

  it("public source renders the quote toggle (NOT redacted)", () => {
    const { container } = render(
      <SourceCard source={PUBLIC_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const toggle = container.querySelector(
      "[data-testid='source-card-quote-toggle-src_public_001']",
    );
    expect(toggle).not.toBeNull();
  });

  it("public source: data-redacted=false attribute is set", () => {
    const { container } = render(
      <SourceCard source={PUBLIC_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const card = container.querySelector(
      "[data-testid='source-card-src_public_001']",
    );
    expect(card?.getAttribute("data-redacted")).toBe("false");
  });

  it("public source: expanding the toggle reveals the real quote", () => {
    const { container } = render(
      <SourceCard source={PUBLIC_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    const toggle = container.querySelector(
      "[data-testid='source-card-quote-toggle-src_public_001']",
    ) as HTMLElement;
    act(() => { fireEvent.click(toggle); });

    const quoteBody = container.querySelector(
      "[data-testid='source-card-quote-src_public_001']",
    );
    expect(quoteBody).not.toBeNull();
    expect(quoteBody?.textContent).toContain("actual public verbatim quote");
  });

  it("public source: redaction placeholder is absent", () => {
    const { container } = render(
      <SourceCard source={PUBLIC_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='source-card-redacted-src_public_001']"),
    ).toBeNull();
  });

  it("work_sensitive source: the verbatim confidential quote is ABSENT from the rendered DOM (R9 defense-in-depth)", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    // The secret quote text must never appear — not in any node, attribute, or comment.
    expect(container.textContent).not.toContain("Verbatim confidential content — must be redacted in the UI.");
  });

  it("work_sensitive source: the confidential summary is ABSENT from the rendered DOM (R9 defense-in-depth)", () => {
    const { container } = render(
      <SourceCard source={WORK_SENSITIVE_SOURCE} />,
      { wrapper: makeWrapper() },
    );
    expect(container.textContent).not.toContain("This is a confidential summary that must not appear in the UI.");
  });
});

// ── (4) ProvenanceModal — open / close ───────────────────────────────────────

describe("ProvenanceModal — open/close and basic content", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({
      claim_id: "clm_001",
      text:     "First claim text used in modal test.",
      status:   "supported",
      sources:  [PUBLIC_SOURCE],
    }),
  ];

  /** Helper: renders ProvenanceModal via a controlling wrapper that exposes
   *  the imperative handle through a test-visible button. */
  function ModalHarness({ claims, claimId }: { claims: RFClaim[]; claimId: string }) {
    const modalRef = useRef<ProvenanceModalHandle>(null);
    return (
      <>
        <button
          data-testid="test-open-btn"
          onClick={() => modalRef.current?.open(claimId)}
        >
          Open
        </button>
        <button
          data-testid="test-close-btn"
          onClick={() => modalRef.current?.close()}
        >
          Close
        </button>
        <ProvenanceModal ref={modalRef} claims={claims} />
      </>
    );
  }

  it("modal is absent before open() is called", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='provenance-modal']")).toBeNull();
  });

  it("open(claimId) renders the modal with correct claim-id", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    const modal = container.querySelector("[data-testid='provenance-modal']");
    expect(modal).not.toBeNull();
    expect(modal?.getAttribute("data-claim-id")).toBe("clm_001");
  });

  it("close button dismisses the modal", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='provenance-modal']")).not.toBeNull();

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='modal-close']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='provenance-modal']")).toBeNull();
  });

  it("Escape key closes the modal", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    act(() => {
      fireEvent.keyDown(
        container.querySelector("[data-testid='provenance-modal-overlay']") as HTMLElement,
        { key: "Escape" },
      );
    });
    expect(container.querySelector("[data-testid='provenance-modal']")).toBeNull();
  });

  it("renders claim text in the modal body", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    const body = container.querySelector("[data-testid='modal-claim-text']");
    expect(body?.textContent).toContain("First claim text used in modal test.");
  });

  it("≤2 clicks from modal open to verbatim quote: click 1=open, click 2=expand quote", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_001" />,
      { wrapper: makeWrapper() },
    );
    // Click 1: open modal (chip click in report, simulated here by the test open btn)
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    // Click 2: expand the quote toggle
    const toggle = container.querySelector(
      "[data-testid='source-card-quote-toggle-src_public_001']",
    ) as HTMLElement;
    expect(toggle).not.toBeNull(); // Quote toggle present after modal opens = 1 more click
    act(() => { fireEvent.click(toggle); });

    const quoteBody = container.querySelector(
      "[data-testid='source-card-quote-src_public_001']",
    );
    expect(quoteBody?.textContent).toContain("actual public verbatim quote");
  });

  it("not-found claim renders 'not found' message", () => {
    const { container } = render(
      <ModalHarness claims={CLAIMS} claimId="clm_999" />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='modal-claim-not-found']")).not.toBeNull();
  });
});

// ── (5) ProvenanceModal — inference chain (P4-VITEST-INFERENCE / RIB-018) ────

describe("ProvenanceModal — inference chain and RIB-018 warning (P4-VITEST-INFERENCE)", () => {
  function InferenceModalHarness({ claims, claimId }: { claims: RFClaim[]; claimId: string }) {
    const modalRef = useRef<ProvenanceModalHandle>(null);
    return (
      <>
        <button
          data-testid="test-open-btn"
          onClick={() => modalRef.current?.open(claimId)}
        >
          Open
        </button>
        <ProvenanceModal ref={modalRef} claims={claims} />
      </>
    );
  }

  it("inference claim with from_claims=[clm_010, clm_022] renders modal-from-claims section", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_WITH_BASIS}
        claimId="clm_050"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='modal-from-claims']")).not.toBeNull();
  });

  it("inference chain renders a link for clm_010", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_WITH_BASIS}
        claimId="clm_050"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='modal-chain-link-clm_010']")).not.toBeNull();
  });

  it("inference chain renders a link for clm_022", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_WITH_BASIS}
        claimId="clm_050"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='modal-chain-link-clm_022']")).not.toBeNull();
  });

  it("inference chain link click navigates to the basis claim", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_WITH_BASIS}
        claimId="clm_050"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    // Clicking the chain link should switch the modal to clm_010
    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='modal-chain-link-clm_010']") as HTMLElement,
      );
    });
    const modal = container.querySelector("[data-testid='provenance-modal']");
    expect(modal?.getAttribute("data-claim-id")).toBe("clm_010");
  });

  it("inference claim with empty from_claims=[] renders the RIB-018 warning (NOT the chain)", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_EMPTY_BASIS}
        claimId="clm_051"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    expect(container.querySelector("[data-testid='modal-rib018-warning']")).not.toBeNull();
    expect(container.querySelector("[data-testid='modal-from-claims']")).toBeNull();
  });

  it("RIB-018 warning contains expected text about inference basis", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_EMPTY_BASIS}
        claimId="clm_051"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    const warning = container.querySelector("[data-testid='modal-rib018-warning']");
    expect(warning?.textContent).toMatch(/inference unsupported/i);
    expect(warning?.textContent).toMatch(/RIB-018/i);
  });

  it("RIB-018 warning has role=alert for accessibility", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_EMPTY_BASIS}
        claimId="clm_051"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    const warning = container.querySelector("[data-testid='modal-rib018-warning']");
    expect(warning?.getAttribute("role")).toBe("alert");
  });

  it("inference claim inference section is absent for a supported (non-inference) claim", () => {
    const claims = [makeClaim({ claim_id: "clm_X", text: "Supported factual claim." })];
    function Harness() {
      const ref = useRef<ProvenanceModalHandle>(null);
      return (
        <>
          <button data-testid="open" onClick={() => ref.current?.open("clm_X")}>Open</button>
          <ProvenanceModal ref={ref} claims={claims} />
        </>
      );
    }
    const { container } = render(<Harness />, { wrapper: makeWrapper() });
    act(() => { fireEvent.click(container.querySelector("[data-testid='open']") as HTMLElement); });
    expect(container.querySelector("[data-testid='modal-inference-section']")).toBeNull();
  });

  it("reasoning_summary renders when present", () => {
    const { container } = render(
      <InferenceModalHarness
        claims={INFERENCE_CLAIMS_WITH_BASIS}
        claimId="clm_050"
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='test-open-btn']") as HTMLElement);
    });
    const reasoning = container.querySelector("[data-testid='modal-reasoning']");
    expect(reasoning?.textContent).toContain("Combining tool-lifecycle");
  });
});

// ── (6) ReportRenderer — [claim:clm_NNN] chips ───────────────────────────────

describe("ReportRenderer — claim chips", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_001", text: "First claim.", status: "supported" }),
    makeClaim({ claim_id: "clm_002", text: "Second claim.", status: "inference" }),
  ];

  it("renders empty-state when markdown is empty", () => {
    const { container } = render(
      <ReportRenderer markdown="" claims={[]} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='report-empty']")).not.toBeNull();
  });

  it("renders report-renderer wrapper for non-empty markdown", () => {
    const { container } = render(
      <ReportRenderer
        markdown="# Report\n\nSome text."
        claims={CLAIMS}
        onClaimSelect={() => {}}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='report-renderer']")).not.toBeNull();
  });

  it("every [claim:clm_NNN] pattern renders as a ClaimChip", () => {
    const md = "Evidence shows X [claim:clm_001] and also Y [claim:clm_002].";
    const { container } = render(
      <ReportRenderer markdown={md} claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='claim-chip-clm_001']")).not.toBeNull();
    expect(container.querySelector("[data-testid='claim-chip-clm_002']")).not.toBeNull();
  });

  it("ClaimChip fires onClaimSelect when clicked", () => {
    const onSelect = vi.fn();
    const md = "Statement [claim:clm_001] is important.";
    const { container } = render(
      <ReportRenderer markdown={md} claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    const chip = container.querySelector("[data-testid='claim-chip-clm_001']") as HTMLElement;
    act(() => { fireEvent.click(chip); });
    expect(onSelect).toHaveBeenCalledWith("clm_001");
  });

  it("multiple chips in same paragraph each fire correct claimId", () => {
    const onSelect = vi.fn();
    const md = "X [claim:clm_001] then Y [claim:clm_002] together.";
    const { container } = render(
      <ReportRenderer markdown={md} claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='claim-chip-clm_001']") as HTMLElement);
    });
    expect(onSelect).toHaveBeenLastCalledWith("clm_001");

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='claim-chip-clm_002']") as HTMLElement);
    });
    expect(onSelect).toHaveBeenLastCalledWith("clm_002");
  });

  it("chip for unknown claimId renders as disabled missing chip (not a button)", () => {
    const md = "Unknown ref [claim:clm_999] here.";
    const { container } = render(
      <ReportRenderer markdown={md} claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    const chip = container.querySelector("[data-testid='claim-chip-clm_999']");
    expect(chip).not.toBeNull();
    // Missing chip is a span (aria-disabled), not a button
    expect(chip?.tagName.toLowerCase()).toBe("span");
    expect(chip?.getAttribute("aria-disabled")).toBe("true");
  });
});

// ── ClaimChip direct tests ────────────────────────────────────────────────────

describe("ClaimChip", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_001", text: "Test claim.", status: "supported" }),
  ];

  it("renders a button for known claim", () => {
    const { container } = render(
      <ClaimChip claimId="clm_001" claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    const chip = container.querySelector("[data-testid='claim-chip-clm_001']");
    expect(chip?.tagName.toLowerCase()).toBe("button");
  });

  it("fires onClaimSelect when the chip is clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <ClaimChip claimId="clm_001" claims={CLAIMS} onClaimSelect={onSelect} />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='claim-chip-clm_001']") as HTMLElement);
    });
    expect(onSelect).toHaveBeenCalledWith("clm_001");
  });

  it("dimmed=true sets data-dimmed=true", () => {
    const { container } = render(
      <ClaimChip claimId="clm_001" claims={CLAIMS} onClaimSelect={() => {}} dimmed />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='claim-chip-clm_001']")?.getAttribute("data-dimmed"),
    ).toBe("true");
  });

  it("dimmed=false sets data-dimmed=false", () => {
    const { container } = render(
      <ClaimChip claimId="clm_001" claims={CLAIMS} onClaimSelect={() => {}} dimmed={false} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='claim-chip-clm_001']")?.getAttribute("data-dimmed"),
    ).toBe("false");
  });

  it("unknown claimId renders disabled span with aria-disabled", () => {
    const { container } = render(
      <ClaimChip claimId="clm_999" claims={CLAIMS} onClaimSelect={() => {}} />,
      { wrapper: makeWrapper() },
    );
    const chip = container.querySelector("[data-testid='claim-chip-clm_999']");
    expect(chip?.getAttribute("aria-disabled")).toBe("true");
    expect(chip?.tagName.toLowerCase()).toBe("span");
  });
});

// ── (7) CompositionSidebar — category filter dims non-matching chips ──────────

describe("CompositionSidebar", () => {
  const CLAIMS: RFClaim[] = [
    makeClaim({ claim_id: "clm_001", text: "Supported A.", status: "supported"   }),
    makeClaim({ claim_id: "clm_002", text: "Inference B.", status: "inference"   }),
    makeClaim({ claim_id: "clm_003", text: "Speculation C.", status: "speculation" }),
    makeClaim({ claim_id: "clm_004", text: "Supported D.", status: "supported"   }),
  ];

  const COUNTS = { total: 4, supported: 2, inference: 1, speculation: 1 };

  it("renders the sidebar with composition data", () => {
    const { container } = render(
      <CompositionSidebar claimCounts={COUNTS} claims={CLAIMS} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='composition-sidebar']")).not.toBeNull();
    expect(container.querySelector("[data-testid='comp-item-supported']")).not.toBeNull();
    expect(container.querySelector("[data-testid='comp-item-inference']")).not.toBeNull();
    expect(container.querySelector("[data-testid='comp-item-speculation']")).not.toBeNull();
  });

  it("shows percentages from claim counts", () => {
    const { container } = render(
      <CompositionSidebar claimCounts={COUNTS} claims={CLAIMS} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='comp-pct-supported']")?.textContent).toBe("50%");
    expect(container.querySelector("[data-testid='comp-pct-inference']")?.textContent).toBe("25%");
    expect(container.querySelector("[data-testid='comp-pct-speculation']")?.textContent).toBe("25%");
  });

  it("shows total claim count", () => {
    const { container } = render(
      <CompositionSidebar claimCounts={COUNTS} claims={CLAIMS} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='comp-total']")?.textContent).toContain("4");
  });

  it("clicking 'supported' category fires onFilterChange with matching IDs", () => {
    const onFilterChange = vi.fn();
    const { container } = render(
      <CompositionSidebar
        claimCounts={COUNTS}
        claims={CLAIMS}
        onFilterChange={onFilterChange}
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='comp-item-supported']") as HTMLElement);
    });
    expect(onFilterChange).toHaveBeenCalled();
    const activeSet = onFilterChange.mock.calls[0]![0] as Set<string>;
    expect(activeSet).toBeInstanceOf(Set);
    expect(activeSet.has("clm_001")).toBe(true);
    expect(activeSet.has("clm_004")).toBe(true);
    // inference claim should NOT be in the active set
    expect(activeSet.has("clm_002")).toBe(false);
  });

  it("clicking 'inference' category provides only inference claim IDs", () => {
    const onFilterChange = vi.fn();
    const { container } = render(
      <CompositionSidebar
        claimCounts={COUNTS}
        claims={CLAIMS}
        onFilterChange={onFilterChange}
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='comp-item-inference']") as HTMLElement);
    });
    const activeSet = onFilterChange.mock.calls[0]![0] as Set<string>;
    expect(activeSet.has("clm_002")).toBe(true);
    expect(activeSet.has("clm_001")).toBe(false);
  });

  it("clicking same category again resets filter (onFilterChange called with null)", () => {
    const onFilterChange = vi.fn();
    const { container } = render(
      <CompositionSidebar
        claimCounts={COUNTS}
        claims={CLAIMS}
        onFilterChange={onFilterChange}
      />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='comp-item-supported']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    act(() => { fireEvent.click(btn); }); // toggle off
    const lastCall = onFilterChange.mock.calls[onFilterChange.mock.calls.length - 1]![0];
    expect(lastCall).toBeNull();
  });

  it("active category button has data-active=true", () => {
    const { container } = render(
      <CompositionSidebar claimCounts={COUNTS} claims={CLAIMS} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='comp-item-supported']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(btn.getAttribute("data-active")).toBe("true");
  });

  it("reset filter button appears when filter is active and clears on click", () => {
    const onFilterChange = vi.fn();
    const { container } = render(
      <CompositionSidebar
        claimCounts={COUNTS}
        claims={CLAIMS}
        onFilterChange={onFilterChange}
      />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='comp-item-speculation']") as HTMLElement);
    });
    const resetBtn = container.querySelector("[data-testid='comp-filter-reset']") as HTMLElement;
    expect(resetBtn).not.toBeNull();
    act(() => { fireEvent.click(resetBtn); });
    const lastCall = onFilterChange.mock.calls[onFilterChange.mock.calls.length - 1]![0];
    expect(lastCall).toBeNull();
  });

  it("renders empty state when claimCounts is null", () => {
    const { container } = render(
      <CompositionSidebar claimCounts={null} claims={[]} />,
      { wrapper: makeWrapper() },
    );
    // No buttons when total=0
    expect(container.querySelector("[data-testid='comp-item-supported']")).toBeNull();
  });

  it("renders correctly with real fixture claim counts", () => {
    const { container } = render(
      <CompositionSidebar
        claimCounts={fixtureRun.claim_counts}
        claims={fixtureRun.claims}
      />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='comp-total']")?.textContent).toContain("91");
  });
});

// ── (8) LineageGraph ──────────────────────────────────────────────────────────

describe("ArtifactLineageGraph", () => {
  it("renders lineage-graph for populated run with claims", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-graph']")).not.toBeNull();
    expect(container.querySelector("[data-testid='lineage-svg']")).not.toBeNull();
  });

  it("renders empty-state when run.claims is empty", () => {
    const emptyRun: RFRunExport = {
      ...fixtureRun,
      claims: [],
    };
    const { container } = render(
      <ArtifactLineageGraph run={emptyRun} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-empty']")).not.toBeNull();
    expect(container.querySelector("[data-testid='lineage-graph']")).toBeNull();
  });

  it("renders node for claim_ledger", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-node-claim_ledger']")).not.toBeNull();
  });

  it("renders node for evidence_bundle", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-node-evidence_bundle']")).not.toBeNull();
  });

  it("renders node for report", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='lineage-node-report']")).not.toBeNull();
  });

  it("renders at least one source_card node from fixture claims", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    const sourceNodes = container.querySelectorAll("[data-kind='source_card']");
    expect(sourceNodes.length).toBeGreaterThan(0);
  });

  it("renders edges from source nodes to extraction nodes", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    // Any edge with from=src_* to ext_* should exist
    const edges = container.querySelectorAll("[data-testid^='lineage-edge-src_']");
    expect(edges.length).toBeGreaterThan(0);
  });

  it("evidence_bundle node has PASS verdict badge from passing verification", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    const verdictEl = container.querySelector("[data-testid='lineage-verdict-evidence_bundle']");
    expect(verdictEl?.textContent).toBe("PASS");
  });

  it("published run's report node has PASS verdict badge", () => {
    const { container } = render(
      <ArtifactLineageGraph run={fixtureRun} />,
      { wrapper: makeWrapper() },
    );
    const verdictEl = container.querySelector("[data-testid='lineage-verdict-report']");
    expect(verdictEl?.textContent).toBe("PASS");
  });

  it("graceful empty-state message text contains 'lineage data'", () => {
    const emptyRun: RFRunExport = { ...fixtureRun, claims: [] };
    const { container } = render(
      <ArtifactLineageGraph run={emptyRun} />,
      { wrapper: makeWrapper() },
    );
    const empty = container.querySelector("[data-testid='lineage-empty']");
    expect(empty?.textContent).toContain("lineage data");
  });
});
