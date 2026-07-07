/**
 * agents-entry-points.test.tsx — P4.5 UI-5.4
 *
 * Tests for the "Research this" entry point buttons added to:
 *   (1) ClaimAuditWorkbench — navigates to /agents with input_claim_ids
 *   (2) ReportOverlay       — navigates to /agents with input_report_id
 *
 * Both surfaces gate on isAgentsLoopbackEnabled(): disabled + tooltip when false.
 *
 * Follows the makeWrapper() + describe/it/expect/vi pattern from p4-components.test.tsx.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mocks ──────────────────────────────────────────────────────────────

// vi.hoisted ensures these refs are created before vi.mock factories run.
const { mockNavigate, mockIsLoopbackEnabled } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockIsLoopbackEnabled: vi.fn(() => true),
}));

vi.mock("react-router-dom", async () => {
  const actual = await import("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@/hooks/useAgentJobs", () => ({
  isAgentsLoopbackEnabled: mockIsLoopbackEnabled,
}));

// ── Components under test ─────────────────────────────────────────────────────

import { ClaimAuditWorkbench } from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { ReportOverlay } from "@/components/ReportOverlay/ReportOverlay";
import type { RFClaim, RFRunExport } from "@/types/rf";

// ── Helpers ───────────────────────────────────────────────────────────────────

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

/** Minimal RFClaim builder. */
function makeClaim(overrides: Partial<RFClaim> & { claim_id: string; text: string }): RFClaim {
  return {
    materiality: "core",
    claim_type: "factual",
    status: "supported",
    confidence: "high",
    inference_basis: { from_claims: [], reasoning_summary: null },
    sources: [],
    ...overrides,
  };
}

/** Minimal RFRunExport with two claims. */
const MINIMAL_CLAIMS: RFClaim[] = [
  makeClaim({ claim_id: "clm_001", text: "First claim for agent research." }),
  makeClaim({ claim_id: "clm_002", text: "Second claim for agent research." }),
];

const MINIMAL_RUN: RFRunExport = {
  schema_version: "1.4",
  run_id: "test-run-001",
  status_derived: "published",
  claims: MINIMAL_CLAIMS,
  title: "Test Research Run",
  sensitivity_threshold: null,
  claim_counts: { total: 2, supported: 2, inference: 0, speculation: 0 },
};

// ── (1) ClaimAuditWorkbench — "Research this" button ─────────────────────────

describe("ClaimAuditWorkbench — Research this entry point (UI-5.4)", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockIsLoopbackEnabled.mockReturnValue(true);
  });

  it("renders the Research this button in the toolbar", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='research-this-btn']")).not.toBeNull();
  });

  it("clicking Research this navigates to /agents with filtered claim IDs", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='research-this-btn']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(mockNavigate).toHaveBeenCalledOnce();
    expect(mockNavigate).toHaveBeenCalledWith("/agents", {
      state: { input_claim_ids: ["clm_001", "clm_002"] },
    });
  });

  it("button is disabled when isAgentsLoopbackEnabled returns false", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='research-this-btn']") as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.disabled).toBe(true);
  });

  it("disabled button shows loopback tooltip when loopback is off", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='research-this-btn']") as HTMLButtonElement;
    expect(btn.title).toContain("loopback mode");
    expect(btn.title).toContain("VITE_RUNS_FRONTEND_LOOPBACK_API=true");
  });

  it("button is enabled when isAgentsLoopbackEnabled returns true", () => {
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='research-this-btn']") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("disabled button does not fire navigate when clicked", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ClaimAuditWorkbench run={MINIMAL_RUN} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='research-this-btn']") as HTMLButtonElement;
    act(() => { fireEvent.click(btn); });
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

// ── (2) ReportOverlay — "Research this" button ────────────────────────────────

describe("ReportOverlay — Research this entry point (UI-5.4)", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockIsLoopbackEnabled.mockReturnValue(true);
  });

  it("renders the Research this button in the sidebar", () => {
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='report-research-this-btn']")).not.toBeNull();
  });

  it("clicking Research this navigates to /agents with the run's report ID", () => {
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(mockNavigate).toHaveBeenCalledOnce();
    expect(mockNavigate).toHaveBeenCalledWith("/agents", {
      state: { input_report_id: "test-run-001" },
    });
  });

  it("button is disabled when isAgentsLoopbackEnabled returns false", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.disabled).toBe(true);
  });

  it("disabled button shows loopback tooltip when loopback is off", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLButtonElement;
    expect(btn.title).toContain("loopback mode");
    expect(btn.title).toContain("VITE_RUNS_FRONTEND_LOOPBACK_API=true");
  });

  it("button is enabled when isAgentsLoopbackEnabled returns true", () => {
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("disabled button does not fire navigate when clicked", () => {
    mockIsLoopbackEnabled.mockReturnValue(false);
    const { container } = render(
      <ReportOverlay run={MINIMAL_RUN} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLButtonElement;
    act(() => { fireEvent.click(btn); });
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("uses the correct run_id as input_report_id when run has a different ID", () => {
    const altRun: RFRunExport = { ...MINIMAL_RUN, run_id: "rf_run_20260707_special" };
    const { container } = render(
      <ReportOverlay run={altRun} reportDraft={null} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='report-research-this-btn']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(mockNavigate).toHaveBeenCalledWith("/agents", {
      state: { input_report_id: "rf_run_20260707_special" },
    });
  });
});
