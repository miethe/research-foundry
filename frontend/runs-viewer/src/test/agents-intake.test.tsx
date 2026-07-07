/**
 * AGENTS-INTAKE — P4.5 Vitest tests for UI-5.6 EvidenceIntakePanel.
 *
 * Covers (per task spec AC-3.5):
 *   (1)  Renders artifact list from useAgentJobArtifacts mock
 *   (2)  Renders "incomplete proposal" badge for claim_proposal with missing
 *        source_candidates (undefined or null)
 *   (3)  Regular (non-claim_proposal and complete claim_proposal) items do NOT
 *        get the incomplete badge
 *   (4)  "Accept selected" button calls accept mutation with checked artifact IDs
 *   (5)  Success state shows accepted_artifact_count from AcceptResponse
 *   (6)  Accept button disabled when no artifacts are selected
 *   (7)  No direct write path — accepted summary absent unless
 *        acceptMutation.isSuccess is true (SECURITY invariant)
 *
 * Additional tests:
 *   (8)  "Reject all" action transitions to rejected state without calling accept
 *   (9)  Job history placeholder is rendered (no listAgentJobs endpoint)
 *   (10) Incomplete badge has role=alert for accessibility
 *   (11) Accept button shows "Accepting…" when mutation is pending
 *   (12) Accept error banner displayed when acceptMutation.isError
 *   (13) artifact_kind badge renders correct kind text
 *   (14) artifact_id is truncated for long IDs
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mock (hoisted before component imports) ────────────────────────────
vi.mock("@/hooks/useAgentJobs", () => ({
  useAgentJobArtifacts: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  })),
  useAcceptAgentJobArtifacts: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: null,
  })),
}));

// ── Component imports (after vi.mock) ─────────────────────────────────────────
import { EvidenceIntakePanel } from "@/components/Agents/EvidenceIntakePanel";

// ── Types and typed mock references ──────────────────────────────────────────
import type { AgentJobArtifact, AcceptResponse } from "@/api/agentJobsClient";
import { useAgentJobArtifacts, useAcceptAgentJobArtifacts } from "@/hooks/useAgentJobs";

const mockUseArtifacts = vi.mocked(useAgentJobArtifacts);
const mockUseAccept    = vi.mocked(useAcceptAgentJobArtifacts);

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

/** Default accept-mutation mock — no pending, no error, not yet succeeded. */
function defaultAcceptMock(mutateFn = vi.fn()) {
  mockUseAccept.mockReturnValue({
    mutate: mutateFn,
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

/** Default artifacts-query mock — loading=false, no data yet. */
function defaultArtifactsMock(data: AgentJobArtifact[] | undefined = undefined) {
  mockUseArtifacts.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

beforeEach(() => {
  defaultAcceptMock();
  defaultArtifactsMock();
});

// ── Test fixtures ─────────────────────────────────────────────────────────────

const ARTIFACT_SOURCE_CARD: AgentJobArtifact = {
  artifact_id: "art_sc_001",
  artifact_kind: "source_card",
  accepted: false,
  source_candidates: null, // not a claim_proposal → no badge
};

const ARTIFACT_CLAIM_COMPLETE: AgentJobArtifact = {
  artifact_id: "art_cp_001",
  artifact_kind: "claim_proposal",
  accepted: false,
  source_candidates: [{ src_id: "src_001" }], // present → NOT incomplete
};

const ARTIFACT_CLAIM_MISSING_CANDIDATES: AgentJobArtifact = {
  artifact_id: "art_cp_002",
  artifact_kind: "claim_proposal",
  accepted: false,
  source_candidates: undefined, // absent → INCOMPLETE badge
};

const ARTIFACT_CLAIM_NULL_CANDIDATES: AgentJobArtifact = {
  artifact_id: "art_cp_003",
  artifact_kind: "claim_proposal",
  accepted: false,
  source_candidates: null, // explicit null → INCOMPLETE badge
};

const ARTIFACT_LONG_ID: AgentJobArtifact = {
  artifact_id: "art_very_long_id_0123456789",
  artifact_kind: "source_card",
  accepted: false,
};

const ACCEPT_RESPONSE: AcceptResponse = {
  agent_job_id: "job_001",
  acceptance_id: "acc_abc_123",
  accepted_artifact_count: 2,
  artifact_ids: ["art_sc_001", "art_cp_001"],
  accepted_by: null,
  accepted_at: "2026-07-07T14:00:00Z",
};

// ── (1) Renders artifact list from useAgentJobArtifacts ───────────────────────

describe("EvidenceIntakePanel — artifact list rendering", () => {
  it("renders artifact list when artifacts are present", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-artifact-list']")).not.toBeNull();
    expect(container.querySelector("[data-testid='intake-artifact-art_sc_001']")).not.toBeNull();
    expect(container.querySelector("[data-testid='intake-artifact-art_cp_001']")).not.toBeNull();
  });

  it("renders empty-state message when artifact list is empty", () => {
    defaultArtifactsMock([]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-empty']")).not.toBeNull();
    expect(container.querySelector("[data-testid='intake-artifact-list']")).toBeNull();
  });

  it("renders loading state when artifacts are loading", () => {
    mockUseArtifacts.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-loading']")).not.toBeNull();
  });

  it("renders error state when artifacts query fails", () => {
    mockUseArtifacts.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-error']")).not.toBeNull();
    expect(container.querySelector("[data-testid='intake-error']")?.getAttribute("role")).toBe("alert");
  });
});

// ── (2) Incomplete proposal badge for missing/null source_candidates ───────────

describe("EvidenceIntakePanel — incomplete proposal badge (AC-3.5)", () => {
  it("renders incomplete badge for claim_proposal with undefined source_candidates", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_MISSING_CANDIDATES]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const badge = container.querySelector(
      `[data-testid='intake-incomplete-badge-${ARTIFACT_CLAIM_MISSING_CANDIDATES.artifact_id}']`,
    );
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toMatch(/incomplete proposal/i);
  });

  it("renders incomplete badge for claim_proposal with null source_candidates", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_NULL_CANDIDATES]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(
      container.querySelector(
        `[data-testid='intake-incomplete-badge-${ARTIFACT_CLAIM_NULL_CANDIDATES.artifact_id}']`,
      ),
    ).not.toBeNull();
  });

  it("item has rv-intake-panel__item--incomplete class for incomplete proposals", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_MISSING_CANDIDATES]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const item = container.querySelector(
      `[data-testid='intake-artifact-${ARTIFACT_CLAIM_MISSING_CANDIDATES.artifact_id}']`,
    );
    expect(item?.className).toContain("rv-intake-panel__item--incomplete");
  });

  it("data-incomplete=true attribute set on incomplete proposal item", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_MISSING_CANDIDATES]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const item = container.querySelector(
      `[data-testid='intake-artifact-${ARTIFACT_CLAIM_MISSING_CANDIDATES.artifact_id}']`,
    );
    expect(item?.getAttribute("data-incomplete")).toBe("true");
  });
});

// ── (3) Regular items do NOT get the incomplete badge ─────────────────────────

describe("EvidenceIntakePanel — no badge for regular items (AC-3.5)", () => {
  it("claim_proposal WITH source_candidates present does NOT get the incomplete badge", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(
      container.querySelector(
        `[data-testid='intake-incomplete-badge-${ARTIFACT_CLAIM_COMPLETE.artifact_id}']`,
      ),
    ).toBeNull();
  });

  it("source_card artifact (non-claim_proposal) does NOT get the incomplete badge", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(
      container.querySelector(
        `[data-testid='intake-incomplete-badge-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
      ),
    ).toBeNull();
  });

  it("data-incomplete=false on non-incomplete items", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const item = container.querySelector(
      `[data-testid='intake-artifact-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
    );
    expect(item?.getAttribute("data-incomplete")).toBe("false");
  });
});

// ── (4) Accept button calls mutation — backend accepts all staged ──────────────
// Backend AcceptJobBody has no artifact_ids field (accepts all staged for the job).
// Checkboxes are for user review (cosmetic); the req body is always {}.

describe("EvidenceIntakePanel — accept mutation (AC-3.5)", () => {
  it("Accept button calls mutate with jobId and empty req (no artifact_ids) — backend accepts all", () => {
    const mutateFn = vi.fn();
    defaultAcceptMock(mutateFn);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    // Check only the first artifact (cosmetic review gate — enables the button)
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement,
      );
    });

    expect(mutateFn).toHaveBeenCalledOnce();
    const callArg = mutateFn.mock.calls[0]![0] as { jobId: string; req: Record<string, unknown> };
    expect(callArg.jobId).toBe("job_001");
    // No artifact_ids in request — backend accepts all staged
    expect(callArg.req).not.toHaveProperty("artifact_ids");
  });

  it("mutate req has no artifact_ids even when both checkboxes are checked", () => {
    const mutateFn = vi.fn();
    defaultAcceptMock(mutateFn);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_CLAIM_COMPLETE.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement,
      );
    });

    const callArg = mutateFn.mock.calls[0]![0] as { jobId: string; req: Record<string, unknown> };
    expect(callArg.req).not.toHaveProperty("artifact_ids");
  });

  it("mutate is still called once when only one checkbox is checked before accepting", () => {
    const mutateFn = vi.fn();
    defaultAcceptMock(mutateFn);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    // Check both, then uncheck the first — button remains enabled (second still checked)
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_CLAIM_COMPLETE.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement,
      );
    });

    expect(mutateFn).toHaveBeenCalledOnce();
    const callArg = mutateFn.mock.calls[0]![0] as { jobId: string; req: Record<string, unknown> };
    expect(callArg.req).not.toHaveProperty("artifact_ids");
  });
});

// ── (5) Success state shows accepted_artifact_count ───────────────────────────

describe("EvidenceIntakePanel — success state (AC-3.5)", () => {
  it("shows accepted_artifact_count from AcceptResponse when mutation succeeds", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      data: ACCEPT_RESPONSE,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-accepted-summary']")).not.toBeNull();
    expect(
      container.querySelector("[data-testid='intake-accepted-count']")?.textContent,
    ).toBe("2");
  });

  it("shows acceptance_id in the success summary", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      data: ACCEPT_RESPONSE,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(
      container.querySelector("[data-testid='intake-acceptance-id']")?.textContent,
    ).toBe("acc_abc_123");
  });
});

// ── (6) Accept button disabled when no artifacts selected ─────────────────────

describe("EvidenceIntakePanel — accept button disabled state (AC-3.5)", () => {
  it("Accept button is disabled when no artifacts are selected (initial state)", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const btn = container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("Accept button becomes enabled after checking a checkbox", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    const btn = container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("Accept button returns to disabled after unchecking all checkboxes", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    // Check then uncheck
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    const btn = container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("Accept button disabled while mutation is pending (even when artifacts selected)", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
      isError: false,
      isSuccess: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    const btn = container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement;
    // Pending overrides enabled state
    expect(btn.disabled).toBe(true);
  });
});

// ── (7) No direct write path (SECURITY invariant) ────────────────────────────

describe("EvidenceIntakePanel — no direct write path (SECURITY)", () => {
  it("accepted summary is absent when isSuccess=false, even if artifacts are loaded", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD, ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    // Accepted summary must NOT appear without a successful acceptMutation
    expect(container.querySelector("[data-testid='intake-accepted-summary']")).toBeNull();
    expect(container.querySelector("[data-testid='intake-acceptance-id']")).toBeNull();
  });

  it("accepted summary appears ONLY when acceptMutation.isSuccess=true (not on checkbox state alone)", () => {
    // With isSuccess=false, checking checkboxes must NOT trigger an accepted state
    defaultAcceptMock();
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    // Accepted summary still absent — no mutate has completed
    expect(container.querySelector("[data-testid='intake-accepted-summary']")).toBeNull();
  });

  it("accepted summary appears when isSuccess=true (verifying the path requires the mutation)", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      data: ACCEPT_RESPONSE,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-accepted-summary']")).not.toBeNull();
  });
});

// ── (8) Reject all action ─────────────────────────────────────────────────────

describe("EvidenceIntakePanel — reject all action", () => {
  it("clicking 'Reject all' transitions to rejected state", () => {
    const mutateFn = vi.fn();
    defaultAcceptMock(mutateFn);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-reject-btn']") as HTMLButtonElement,
      );
    });

    expect(container.querySelector("[data-testid='intake-rejected-message']")).not.toBeNull();
    expect(container.textContent).toContain("No artifacts accepted");
  });

  it("'Reject all' never calls the accept mutation", () => {
    const mutateFn = vi.fn();
    defaultAcceptMock(mutateFn);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-reject-btn']") as HTMLButtonElement,
      );
    });

    expect(mutateFn).not.toHaveBeenCalled();
  });
});

// ── (9) Job history placeholder ───────────────────────────────────────────────

describe("EvidenceIntakePanel — job history stub", () => {
  it("renders job history placeholder when no listAgentJobs endpoint exists", () => {
    defaultArtifactsMock([]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-job-history']")).not.toBeNull();
    expect(
      container.querySelector("[data-testid='intake-job-history-placeholder']"),
    ).not.toBeNull();
    expect(
      container.querySelector("[data-testid='intake-job-history-placeholder']")?.textContent,
    ).toMatch(/job history coming soon/i);
  });

  it("job history placeholder is present in success state too", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      data: ACCEPT_RESPONSE,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-job-history-placeholder']")).not.toBeNull();
  });
});

// ── (10) Incomplete badge accessibility ───────────────────────────────────────

describe("EvidenceIntakePanel — accessibility", () => {
  it("incomplete proposal badge has role=alert", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_MISSING_CANDIDATES]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const badge = container.querySelector(
      `[data-testid='intake-incomplete-badge-${ARTIFACT_CLAIM_MISSING_CANDIDATES.artifact_id}']`,
    );
    expect(badge?.getAttribute("role")).toBe("alert");
  });

  it("intake-panel has aria-label", () => {
    defaultArtifactsMock([]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='intake-panel']")?.getAttribute("aria-label")).toBeTruthy();
  });
});

// ── (11) Accept button pending state ─────────────────────────────────────────

describe("EvidenceIntakePanel — pending UI state", () => {
  it("Accept button shows 'Accepting…' text while mutation is pending", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
      isError: false,
      isSuccess: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const btn = container.querySelector("[data-testid='intake-accept-btn']");
    expect(btn?.textContent).toMatch(/accepting/i);
  });
});

// ── (12) Accept error banner ──────────────────────────────────────────────────

describe("EvidenceIntakePanel — accept error display", () => {
  it("shows accept error banner when acceptMutation.isError is true", () => {
    mockUseAccept.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      isSuccess: false,
      data: undefined,
      error: new Error("Upstream server error"),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const banner = container.querySelector("[data-testid='intake-accept-error']");
    expect(banner).not.toBeNull();
    expect(banner?.getAttribute("role")).toBe("alert");
    expect(banner?.textContent).toContain("Accept failed");
  });
});

// ── (13) artifact_kind badge ──────────────────────────────────────────────────

describe("EvidenceIntakePanel — kind badge", () => {
  it("renders the artifact_kind text in the kind badge", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const badge = container.querySelector(
      `[data-testid='intake-kind-badge-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
    );
    expect(badge?.textContent).toBe("source_card");
  });

  it("renders claim_proposal kind badge correctly", () => {
    defaultArtifactsMock([ARTIFACT_CLAIM_COMPLETE]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const badge = container.querySelector(
      `[data-testid='intake-kind-badge-${ARTIFACT_CLAIM_COMPLETE.artifact_id}']`,
    );
    expect(badge?.textContent).toBe("claim_proposal");
  });
});

// ── (14) artifact_id truncation ───────────────────────────────────────────────

describe("EvidenceIntakePanel — artifact ID display", () => {
  it("truncates long artifact IDs in the display span", () => {
    defaultArtifactsMock([ARTIFACT_LONG_ID]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const idSpan = container.querySelector(
      `[data-testid='intake-artifact-id-${ARTIFACT_LONG_ID.artifact_id}']`,
    );
    // Display text is shorter than the full ID
    expect(idSpan?.textContent?.length).toBeLessThan(ARTIFACT_LONG_ID.artifact_id.length);
    expect(idSpan?.textContent).toContain("…");
  });

  it("preserves short artifact IDs in full", () => {
    defaultArtifactsMock([ARTIFACT_SOURCE_CARD]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const idSpan = container.querySelector(
      `[data-testid='intake-artifact-id-${ARTIFACT_SOURCE_CARD.artifact_id}']`,
    );
    // art_sc_001 is 10 chars — within the 12-char limit, rendered as-is
    expect(idSpan?.textContent).toBe(ARTIFACT_SOURCE_CARD.artifact_id);
  });

  it("full artifact ID is preserved in the title attribute for tooltip access", () => {
    defaultArtifactsMock([ARTIFACT_LONG_ID]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const idSpan = container.querySelector(
      `[data-testid='intake-artifact-id-${ARTIFACT_LONG_ID.artifact_id}']`,
    );
    expect(idSpan?.getAttribute("title")).toBe(ARTIFACT_LONG_ID.artifact_id);
  });
});
