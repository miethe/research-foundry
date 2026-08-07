/**
 * AGENTS-CANCEL — P4.5 ARLS-2.1 / 2.2 / 2.3 tests for CancelJobControl.
 *
 * Covers:
 *   (1) ARLS-2.1 — visibility gated on cancellable status (RUNNING_STATUSES),
 *       preferring the live useAgentJob() status over the fallback prop.
 *   (2) ARLS-2.2 — confirm gating: cancelAgentJob() (via useCancelAgentJob's
 *       mutate) never fires from a single click; only the explicit confirm
 *       button dispatches it. "Never mind" aborts without dispatching.
 *   (3) ARLS-2.3 — success path resets the confirm step (and, once the live
 *       query reflects the resulting terminal status, the control
 *       disappears with no manual refresh); failure path surfaces an error
 *       and leaves the control actionable — a failed cancel never looks
 *       successful.
 *
 * Follows the vi.mock("@/hooks/useAgentJobs") convention used by every other
 * agents-*.test.tsx file in this suite (agents-event-panel.test.tsx,
 * agents-resilience.test.tsx, agents-events-smoke.test.tsx).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";

// ── Module mock (hoisted before component imports) ────────────────────────────
vi.mock("@/hooks/useAgentJobs", () => ({
  isAgentsLoopbackEnabled: vi.fn(() => true),
  useAgentJob: vi.fn(),
  useCancelAgentJob: vi.fn(),
}));

// ── Component import (after vi.mock so it receives the mocked module) ─────────
import { CancelJobControl } from "@/components/Agents/CancelJobControl";
import { useAgentJob, useCancelAgentJob } from "@/hooks/useAgentJobs";
import type { AgentJobDetail } from "@/api/agentJobsClient";

const mockUseAgentJob = vi.mocked(useAgentJob);
const mockUseCancelAgentJob = vi.mocked(useCancelAgentJob);

// ── Test helpers ──────────────────────────────────────────────────────────────

function mockJobQuery(data: Partial<AgentJobDetail> | undefined) {
  mockUseAgentJob.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

function mockCancel(overrides?: {
  mutate?: ReturnType<typeof vi.fn>;
  isPending?: boolean;
  isError?: boolean;
  error?: Error | null;
}) {
  mockUseCancelAgentJob.mockReturnValue({
    mutate: overrides?.mutate ?? vi.fn(),
    isPending: overrides?.isPending ?? false,
    isError: overrides?.isError ?? false,
    error: overrides?.error ?? null,
    isSuccess: false,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

beforeEach(() => {
  mockJobQuery(undefined);
  mockCancel();
});

// ═══════════════════════════════════════════════════════════════════════════════
// (1) ARLS-2.1 — visibility gated on cancellable status
// ═══════════════════════════════════════════════════════════════════════════════

describe("CancelJobControl — visibility (ARLS-2.1)", () => {
  it("renders the Cancel Job button for a cancellable status ('running')", () => {
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);
    expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();
  });

  it.each(["queued", "streaming"])(
    "renders the Cancel Job button for cancellable status '%s'",
    (status) => {
      const { container } = render(<CancelJobControl jobId="job-1" jobStatus={status} />);
      expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();
    },
  );

  it.each(["pending", "completed", "failed", "cancelled"])(
    "renders nothing for non-cancellable status '%s'",
    (status) => {
      const { container } = render(<CancelJobControl jobId="job-1" jobStatus={status} />);
      expect(container.querySelector("[data-testid='cancel-job-control']")).toBeNull();
    },
  );

  it("prefers the live useAgentJob() status over the fallback jobStatus prop", () => {
    // Fallback prop says "running" (cancellable) but the live query already
    // resolved to a terminal state — the live status must win.
    mockJobQuery({ status: "completed" });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);
    expect(container.querySelector("[data-testid='cancel-job-control']")).toBeNull();
  });

  it("uses the fallback jobStatus prop when the live query has not resolved yet", () => {
    mockJobQuery(undefined);
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="queued" />);
    expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// (2) ARLS-2.2 — confirm gating
// ═══════════════════════════════════════════════════════════════════════════════

describe("CancelJobControl — confirm gating (ARLS-2.2)", () => {
  it("a single click on Cancel Job does NOT dispatch the cancel mutation", () => {
    const mutateFn = vi.fn();
    mockCancel({ mutate: mutateFn });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });

    expect(mutateFn).not.toHaveBeenCalled();
  });

  it("clicking Cancel Job arms the confirm step (Confirm/Never Mind visible)", () => {
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });

    expect(container.querySelector("[data-testid='cancel-job-confirm-btn']")).not.toBeNull();
    expect(container.querySelector("[data-testid='cancel-job-abort-btn']")).not.toBeNull();
  });

  it("clicking Confirm Cancel dispatches the mutation with the jobId", () => {
    const mutateFn = vi.fn();
    mockCancel({ mutate: mutateFn });
    const { container } = render(<CancelJobControl jobId="job-42" jobStatus="running" />);

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });
    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='cancel-job-confirm-btn']") as HTMLElement,
      );
    });

    expect(mutateFn).toHaveBeenCalledOnce();
    expect(mutateFn.mock.calls[0]![0]).toBe("job-42");
  });

  it("clicking Never Mind aborts without dispatching the mutation", () => {
    const mutateFn = vi.fn();
    mockCancel({ mutate: mutateFn });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-abort-btn']") as HTMLElement);
    });

    expect(mutateFn).not.toHaveBeenCalled();
    // Confirm step is torn down; the plain Cancel Job button is back.
    expect(container.querySelector("[data-testid='cancel-job-confirm-btn']")).toBeNull();
    expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();
  });

  it("Confirm and Never Mind are plain <button> elements (keyboard-reachable)", () => {
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);
    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });
    expect(
      container.querySelector("[data-testid='cancel-job-confirm-btn']")?.tagName,
    ).toBe("BUTTON");
    expect(
      container.querySelector("[data-testid='cancel-job-abort-btn']")?.tagName,
    ).toBe("BUTTON");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// (3) ARLS-2.3 — success and failure paths
// ═══════════════════════════════════════════════════════════════════════════════

describe("CancelJobControl — success path (ARLS-2.3)", () => {
  it("on success, the confirm step resets (component-level onSuccess fires)", () => {
    const mutateFn = vi.fn((_jobId: string, opts?: { onSuccess?: () => void }) => {
      opts?.onSuccess?.();
    });
    mockCancel({ mutate: mutateFn });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    act(() => {
      fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
    });
    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='cancel-job-confirm-btn']") as HTMLElement,
      );
    });

    // Confirm UI is torn down after a successful dispatch.
    expect(container.querySelector("[data-testid='cancel-job-confirm-btn']")).toBeNull();
  });

  it("once the invalidated job-detail query resolves to a terminal status, the control disappears with no manual refresh", () => {
    // Simulates useCancelAgentJob's onSuccess (useAgentJobs.ts:94) invalidating
    // agentJobQueryKey(jobId) and the resulting refetch resolving to "cancelled" —
    // this component's useAgentJob(jobId) call is the subscriber that picks it up.
    mockJobQuery({ status: "cancelled" });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);
    expect(container.querySelector("[data-testid='cancel-job-control']")).toBeNull();
  });
});

describe("CancelJobControl — failure path (ARLS-2.3)", () => {
  it("a failed cancel surfaces an inline error and does NOT hide the control", () => {
    mockCancel({ isError: true, error: new Error("network timeout") });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    const errorEl = container.querySelector("[data-testid='cancel-job-error']");
    expect(errorEl).not.toBeNull();
    expect(errorEl?.getAttribute("role")).toBe("alert");
    expect(errorEl?.textContent).toContain("network timeout");
    // The job is still running (the live query never advanced) — control stays visible.
    expect(container.querySelector("[data-testid='cancel-job-control']")).not.toBeNull();
  });

  it("a failed cancel does NOT invalidate/advance status — job remains cancellable and actionable", () => {
    mockCancel({ isError: true, error: new Error("server error") });
    mockJobQuery({ status: "running" });
    const { container } = render(<CancelJobControl jobId="job-1" jobStatus="running" />);

    // Cancel Job button (or confirm step) must still be present — never looks successful.
    const hasCancelBtn = container.querySelector("[data-testid='cancel-job-btn']") !== null;
    const hasConfirmBtn = container.querySelector("[data-testid='cancel-job-confirm-btn']") !== null;
    expect(hasCancelBtn || hasConfirmBtn).toBe(true);
  });
});
