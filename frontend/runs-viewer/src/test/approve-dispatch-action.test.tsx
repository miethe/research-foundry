/**
 * approve-dispatch-action.test.tsx — TEST-005 coverage for the Phase 3
 * "Approve & Dispatch" action added to the Writeback tab
 * (RunDetailWorkspace.tsx: ApproveDispatchAction / ApproveDispatchOutcomePanel).
 *
 * Covers (per Phase 4 TEST-005 of
 * docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md):
 *   1. Action visibility — button renders only when
 *      run.report_draft != null && writebackAvailable (UI-002 gate).
 *   2. Confirmation dialog — clicking the button opens the confirm dialog
 *      before any dispatch fires; canceling never calls the API.
 *   3. Outcome rendering — success/partial/blocked overall_status + per-target
 *      chips, including the `?? "unknown"` / `?? null` defensive fallbacks
 *      Phase 3 built in for missing/partial API fields.
 *   4. Governance-rejection vs generic-error — distinct glyph/wording (UI-004),
 *      driven by response shape (WritebackApiError + isWritebackApprovalRejection),
 *      not string-matching.
 *
 * approveAndDispatchWriteback() is mocked at the module boundary; everything
 * else exported from @/api/client (WritebackApiError, isWritebackApprovalRejection,
 * types) is the real implementation, so the component's own discrimination logic
 * is what's under test — not a re-implementation of it in the mock.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import type {
  ApproveDispatchResult,
  WritebackApprovalRejection,
} from "@/api/client";
import type { RFRunExport } from "@/types/rf";
import type { RFRunWritebacksSummary } from "@/types/rf/run-export";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    approveAndDispatchWriteback: vi.fn(),
  };
});

import { approveAndDispatchWriteback, WritebackApiError } from "@/api/client";
import { RunDetailWorkspace } from "@/components/RunDetail/RunDetailWorkspace";

const mockApprove = vi.mocked(approveAndDispatchWriteback);

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

const WRITEBACKS_WITH_CANDIDATES: RFRunWritebacksSummary = {
  targets: [{ name: "meatywiki", status: "present" }],
  approved_for_writeback: false,
  reviewer_notes: null,
  required_fix: null,
  previews: [
    {
      target: "meatywiki",
      filename: "meatywiki_writeback.md",
      content_type: "markdown",
      content: "# Candidate",
    },
  ],
};

let _runIdCounter = 0;
function makeRun(overrides: Partial<RFRunExport> = {}): RFRunExport {
  const id = String(++_runIdCounter);
  return {
    schema_version: "1.6",
    run_id: `rf_run_approve_dispatch_${id}`,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: false, passed: null, exit_code: null, checks: [] },
    governance: {},
    timeline: null,
    report_draft: "# Draft Report\n\nBody text.",
    writebacks: WRITEBACKS_WITH_CANDIDATES,
    ...overrides,
  } as RFRunExport;
}

function renderWorkspace(run: RFRunExport) {
  return render(
    <RunDetailWorkspace run={run} activeTab="writeback" mode="page" onTabChange={() => {}} />,
    { wrapper: makeWrapper() },
  );
}

function successResult(overrides: Partial<ApproveDispatchResult> = {}): ApproveDispatchResult {
  return {
    bundle_id: "bundle_1",
    verified: true,
    council_decision: "approve",
    reviewer_notes: "",
    required_fix: null,
    guard_result: { passed: true, exit_code: 0, violations: [] },
    target_status: { meatywiki: "success", skillmeat: "success", ccdash: "success" },
    overall_status: "success",
    ...overrides,
  };
}

beforeEach(() => {
  mockApprove.mockReset();
});

// ── 1. Action visibility (UI-002 gate) ───────────────────────────────────────

describe("TEST-005 — Approve & Dispatch action visibility", () => {
  it("renders the button when report_draft is present and writeback is available", () => {
    const run = makeRun();
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-approve-dispatch']")).not.toBeNull();
    expect(container.querySelector("[data-testid='writeback-approve-dispatch-button']")).not.toBeNull();
  });

  it("hides the button when report_draft is null (even with writeback candidates present)", () => {
    const run = makeRun({ report_draft: null });
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-approve-dispatch']")).toBeNull();
  });

  it("hides the button when writeback is unavailable (even with a report_draft present)", () => {
    const run = makeRun({ writebacks: null });
    const { container } = renderWorkspace(run);
    // Falls back to the FR-13 empty state — no governance panel, no action.
    expect(container.querySelector("[data-testid='writeback-empty-state']")).not.toBeNull();
    expect(container.querySelector("[data-testid='writeback-approve-dispatch']")).toBeNull();
  });

  it("hides the button when neither report_draft nor writeback candidates are present", () => {
    const run = makeRun({ report_draft: null, writebacks: null });
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-approve-dispatch']")).toBeNull();
  });
});

// ── 2. Confirmation dialog ───────────────────────────────────────────────────

describe("TEST-005 — confirmation dialog", () => {
  it("does not call the API until the button is clicked", () => {
    renderWorkspace(makeRun());
    expect(mockApprove).not.toHaveBeenCalled();
  });

  it("opens the confirm dialog on click, without dispatching yet", () => {
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    expect(container.querySelector("[data-testid='writeback-approve-confirm-dialog']")).not.toBeNull();
    expect(mockApprove).not.toHaveBeenCalled();
  });

  it("canceling the dialog closes it and never calls the API", async () => {
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    expect(container.querySelector("[data-testid='writeback-approve-confirm-dialog']")).not.toBeNull();

    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-cancel']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-confirm-dialog']")).toBeNull();
    });
    expect(mockApprove).not.toHaveBeenCalled();
  });

  it("confirming the dialog calls the API exactly once with the run_id", async () => {
    mockApprove.mockResolvedValueOnce(successResult());
    const run = makeRun();
    const { container } = renderWorkspace(run);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(mockApprove).toHaveBeenCalledTimes(1);
    });
    expect(mockApprove).toHaveBeenCalledWith(run.run_id);
  });
});

// ── 3. Outcome rendering (success / partial / blocked + defensive fallbacks) ─

describe("TEST-005 — outcome rendering", () => {
  it("renders a success outcome with all three target chips", async () => {
    mockApprove.mockResolvedValueOnce(successResult());
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")).not.toBeNull();
    });
    const outcome = container.querySelector("[data-testid='writeback-approve-outcome-success']")!;
    expect(outcome.textContent).toContain("success");
    expect(outcome.textContent).toContain("passed");
    expect(container.querySelector("[data-testid='writeback-approve-target-meatywiki']")!.textContent).toContain("success");
    expect(container.querySelector("[data-testid='writeback-approve-target-skillmeat']")!.textContent).toContain("success");
    expect(container.querySelector("[data-testid='writeback-approve-target-ccdash']")!.textContent).toContain("success");
    // The confirm dialog closes once an outcome is available.
    expect(container.querySelector("[data-testid='writeback-approve-confirm-dialog']")).toBeNull();
  });

  it("renders a partial outcome with mixed per-target statuses", async () => {
    mockApprove.mockResolvedValueOnce(
      successResult({
        overall_status: "partial",
        target_status: { meatywiki: "success", skillmeat: "failed", ccdash: "skipped" },
      }),
    );
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")!.textContent).toContain("partial");
    expect(container.querySelector("[data-testid='writeback-approve-target-meatywiki']")!.textContent).toContain("success");
    expect(container.querySelector("[data-testid='writeback-approve-target-skillmeat']")!.textContent).toContain("failed");
    expect(container.querySelector("[data-testid='writeback-approve-target-ccdash']")!.textContent).toContain("skipped");
  });

  it("renders a blocked overall_status without throwing", async () => {
    mockApprove.mockResolvedValueOnce(
      successResult({
        overall_status: "blocked",
        target_status: { meatywiki: "failed", skillmeat: "failed", ccdash: "failed" },
      }),
    );
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")!.textContent).toContain("blocked");
  });

  it("defaults to 'unknown' for missing per-target entries (partial target_status) without crashing", async () => {
    mockApprove.mockResolvedValueOnce(
      successResult({
        // Only meatywiki reported — skillmeat/ccdash entirely absent from the map.
        target_status: { meatywiki: "success" },
      }),
    );
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='writeback-approve-target-skillmeat']")!.textContent).toContain("unknown");
    expect(container.querySelector("[data-testid='writeback-approve-target-ccdash']")!.textContent).toContain("unknown");
  });

  it("renders 'unknown' overall_status and guard state when both are missing entirely, without crashing", async () => {
    // Cast through unknown: simulates a genuinely malformed/older API payload
    // missing overall_status and guard_result — exactly what the `?? "unknown"`
    // / `?? null` fallbacks in ApproveDispatchOutcomePanel exist to defend against.
    const malformed = {
      bundle_id: "bundle_2",
      verified: true,
      council_decision: "approve",
      reviewer_notes: "",
      required_fix: null,
      target_status: {},
    } as unknown as ApproveDispatchResult;
    mockApprove.mockResolvedValueOnce(malformed);

    const { container } = renderWorkspace(makeRun());
    expect(() => {
      fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
      fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);
    }).not.toThrow();

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-success']")).not.toBeNull();
    });
    const outcome = container.querySelector("[data-testid='writeback-approve-outcome-success']")!;
    expect(outcome.textContent).toContain("unknown");
    expect(container.querySelector("[data-testid='writeback-approve-target-meatywiki']")!.textContent).toContain("unknown");
  });
});

// ── 4. Governance-rejection vs generic-error (UI-004) ────────────────────────

describe("TEST-005 — governance-rejection vs generic-error distinction", () => {
  it("renders the governance-rejection panel (⛔, distinct wording, violations) for a discriminated rejection body", async () => {
    const rejection: WritebackApprovalRejection = {
      error: "governance_rejected",
      exit_code: 3,
      violations: [
        { rule_id: "no_secrets", severity: "block", message: "Detected a secret in evidence bundle." },
      ],
    };
    mockApprove.mockRejectedValueOnce(new WritebackApiError(422, "Unprocessable Entity", rejection));

    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-rejected']")).not.toBeNull();
    });
    const rejected = container.querySelector("[data-testid='writeback-approve-outcome-rejected']")!;
    expect(rejected.textContent).toContain("⛔");
    expect(rejected.textContent).toContain("Blocked by governance policy");
    expect(rejected.textContent).toContain("no_secrets");
    expect(rejected.textContent).toContain("Detected a secret in evidence bundle.");
    // Must not be misclassified as the generic-error panel.
    expect(container.querySelector("[data-testid='writeback-approve-outcome-error']")).toBeNull();
  });

  it("renders the generic-error panel (⚠, distinct wording) for a non-governance WritebackApiError body", async () => {
    mockApprove.mockRejectedValueOnce(
      new WritebackApiError(500, "Internal Server Error", { detail: "database unavailable" }),
    );

    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-error']")).not.toBeNull();
    });
    const errored = container.querySelector("[data-testid='writeback-approve-outcome-error']")!;
    expect(errored.textContent).toContain("⚠");
    expect(errored.textContent).toContain("Unexpected error");
    // Must not be misclassified as the governance-rejection panel.
    expect(container.querySelector("[data-testid='writeback-approve-outcome-rejected']")).toBeNull();
  });

  it("renders the generic-error panel for a plain thrown Error (e.g. network failure, no response body at all)", async () => {
    mockApprove.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-error']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='writeback-approve-outcome-error']")!.textContent).toContain(
      "Failed to fetch",
    );
  });

  it("closes the confirm dialog once a rejection outcome is available", async () => {
    mockApprove.mockRejectedValueOnce(
      new WritebackApiError(422, "Unprocessable Entity", {
        error: "governance_rejected",
        exit_code: 3,
        violations: [],
      } satisfies WritebackApprovalRejection),
    );
    const { container } = renderWorkspace(makeRun());
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-dispatch-button']")!);
    fireEvent.click(container.querySelector("[data-testid='writeback-approve-confirm-submit']")!);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='writeback-approve-outcome-rejected']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='writeback-approve-confirm-dialog']")).toBeNull();
  });
});
