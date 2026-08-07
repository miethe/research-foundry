/**
 * AGENTS-SCREEN-JOB-TRANSITION — M2 review fix-cycle tests (CONFIRM-LEAK-01 +
 * AC-M2-3).
 *
 * These tests render the REAL `AgentsScreen` end-to-end (not CancelJobControl
 * or AgentJobEventPanel in isolation) because both findings are about state
 * that crosses component boundaries at the AgentsScreen call site — the
 * exact boundary a per-component unit test cannot see:
 *
 *   (1) CONFIRM-LEAK-01 — CancelJobControl's `confirming` state must not
 *       survive a relaunch (job A -> job B) in the same render slot. Proven
 *       by a REAL click sequence (arm confirm for job A, relaunch to job B,
 *       assert the confirm step did not survive and no cancel was
 *       dispatched) — not by asserting a `key` prop exists on an element.
 *
 *   (2) AC-M2-3 — a terminal status delivered through the shared
 *       useAgentJob(jobId) query (the same query useCancelAgentJob's
 *       onSuccess invalidates) must reach AgentJobEventPanel, not just
 *       CancelJobControl. Proven by changing the MOCKED QUERY's return value
 *       and forcing a re-render — never by passing a terminal jobStatus prop
 *       directly to the panel.
 *
 * Full-module mock (every hook AgentsScreen's render tree can reach is
 * stubbed here) — NOT the "partial real-module mock" repair the M2 review's
 * finding 4 flagged as still-needed; that repair targets the 7 pre-existing
 * protected `agents-*.test.tsx` files' narrow mocks and is explicitly M3's
 * job. This file is new and self-contained, so a full mock here does not
 * touch that repair's scope.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mock (hoisted before component imports) ────────────────────────────
vi.mock("@/hooks/useAgentJobs", () => ({
  isAgentsLoopbackEnabled: vi.fn(() => true),
  useLaunchAgentJob: vi.fn(),
  useAgentJob: vi.fn(),
  useCancelAgentJob: vi.fn(),
  useAgentJobEvents: vi.fn(() => ({ events: [], status: "idle" })),
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

// ── Component import (after vi.mock so it receives the mocked module) ─────────
import { AgentsScreen } from "@/screens/AgentsScreen";
import { useLaunchAgentJob, useAgentJob, useCancelAgentJob } from "@/hooks/useAgentJobs";
import type { AgentJobDetail, LaunchAgentJobRequest } from "@/api/agentJobsClient";

const mockUseLaunchAgentJob = vi.mocked(useLaunchAgentJob);
const mockUseAgentJob = vi.mocked(useAgentJob);
const mockUseCancelAgentJob = vi.mocked(useCancelAgentJob);

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

function makeJob(overrides: Partial<AgentJobDetail> & { agent_job_id: string }): AgentJobDetail {
  return {
    status: "running",
    created_at: "2026-08-07T10:00:00Z",
    updated_at: "2026-08-07T10:00:00Z",
    workspace_id: null,
    created_by: null,
    policy_snapshot: null,
    ...overrides,
  };
}

/** Fills the launch form's required fields and checks the acknowledgment box. */
function fillLaunchForm(container: HTMLElement) {
  fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
    target: { value: "claude-sonnet-4-6" },
  });
  fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
    target: { value: "search_web" },
  });
  const ack = container.querySelector("input[name='acknowledged']") as HTMLInputElement;
  if (!ack.checked) fireEvent.click(ack);
}

function clickLaunch(container: HTMLElement) {
  fireEvent.click(container.querySelector("[data-testid='launch-submit']") as HTMLElement);
}

/**
 * Queues launch responses: each call to the mocked mutate() pops the next
 * job off the queue and fires the caller's onSuccess with it — mirroring
 * AgentJobLaunchForm's real `mutation.mutate(req, { onSuccess: onLaunchSuccess })`
 * call so a real click drives a real activeJob transition inside AgentsScreen.
 */
function queueLaunches(jobs: AgentJobDetail[]) {
  const queue = [...jobs];
  mockUseLaunchAgentJob.mockReturnValue({
    mutate: vi.fn(
      (_req: LaunchAgentJobRequest, opts?: { onSuccess?: (job: AgentJobDetail) => void }) => {
        const job = queue.shift();
        if (job) opts?.onSuccess?.(job);
      },
    ),
    isPending: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

beforeEach(() => {
  mockUseAgentJob.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
  mockUseCancelAgentJob.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    isSuccess: false,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
});

// ═══════════════════════════════════════════════════════════════════════════════
// (1) CONFIRM-LEAK-01 — confirm state must not survive a jobId transition
// ═══════════════════════════════════════════════════════════════════════════════

describe("AgentsScreen — job-scoped subtree keying (CONFIRM-LEAK-01)", () => {
  it(
    "arming Cancel confirm for job A does not survive a relaunch to job B, " +
      "and job B's own confirm cycle dispatches only job B",
    () => {
      const JOB_A = makeJob({ agent_job_id: "job-a" });
      const JOB_B = makeJob({ agent_job_id: "job-b" });
      queueLaunches([JOB_A, JOB_B]);
      const mutateCancel = vi.fn();
      mockUseCancelAgentJob.mockReturnValue({
        mutate: mutateCancel,
        isPending: false,
        isError: false,
        error: null,
        isSuccess: false,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any);

      const { container } = render(<AgentsScreen />, { wrapper: makeWrapper() });

      // Launch job A via a real submit.
      act(() => fillLaunchForm(container));
      act(() => clickLaunch(container));
      expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();

      // Arm the confirm step for job A via a real click.
      act(() => {
        fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
      });
      expect(container.querySelector("[data-testid='cancel-job-confirm-btn']")).not.toBeNull();

      // Relaunch WITHOUT navigating away — the ordinary path that reproduces
      // the defect (form fields + acknowledgment persist from the first
      // launch, so a second click on the same button is a real relaunch).
      act(() => clickLaunch(container));

      // The confirm step must NOT survive the jobId transition: only the
      // plain "Cancel Job" button is visible for job B, and nothing was
      // dispatched just from the relaunch itself.
      expect(container.querySelector("[data-testid='cancel-job-confirm-btn']")).toBeNull();
      expect(container.querySelector("[data-testid='cancel-job-btn']")).not.toBeNull();
      expect(mutateCancel).not.toHaveBeenCalled();

      // A fresh confirm cycle against the NEW instance dispatches job B's own
      // id — proving the remounted control is correctly wired to job B, not
      // silently inert or still pointed at job A.
      act(() => {
        fireEvent.click(container.querySelector("[data-testid='cancel-job-btn']") as HTMLElement);
      });
      act(() => {
        fireEvent.click(
          container.querySelector("[data-testid='cancel-job-confirm-btn']") as HTMLElement,
        );
      });
      expect(mutateCancel).toHaveBeenCalledOnce();
      expect(mutateCancel.mock.calls[0]![0]).toBe("job-b");
    },
  );
});

// ═══════════════════════════════════════════════════════════════════════════════
// (2) AC-M2-3 — terminal status reaches AgentJobEventPanel via the shared query
// ═══════════════════════════════════════════════════════════════════════════════

describe("AgentsScreen — shared live job query reaches AgentJobEventPanel (AC-M2-3)", () => {
  it(
    "a terminal status delivered through useAgentJob(jobId) flips the panel " +
      "to the closed/terminal state, without any component receiving a new jobStatus prop directly",
    () => {
      const JOB = makeJob({ agent_job_id: "job-terminal-001", status: "running" });
      queueLaunches([JOB]);

      const { container, rerender } = render(<AgentsScreen />, { wrapper: makeWrapper() });

      act(() => fillLaunchForm(container));
      act(() => clickLaunch(container));

      // Not terminal yet — the panel shows no "Stream closed" indicator.
      expect(container.querySelector("[data-testid='agent-event-terminal-status']")).toBeNull();

      // Simulate the query-invalidation-driven refetch (useCancelAgentJob's
      // real onSuccess invalidates this exact query key) landing a terminal
      // status. This changes the QUERY's data, not any component's props.
      mockUseAgentJob.mockReturnValue({
        data: { ...JOB, status: "cancelled" },
        isLoading: false,
        isError: false,
        error: null,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any);
      act(() => {
        rerender(<AgentsScreen />);
      });

      const badge = container.querySelector("[data-testid='agent-event-terminal-status']");
      expect(badge).not.toBeNull();
      expect(badge?.textContent).toContain("cancelled");

      // Same shared query — the cancel control agrees and hides itself,
      // proving both surfaces read one source of truth rather than diverging
      // (CancelJobControl already covered this in agents-cancel.test.tsx;
      // asserted here too as a same-render cross-check).
      expect(container.querySelector("[data-testid='cancel-job-control']")).toBeNull();
    },
  );
});
