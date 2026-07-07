/**
 * AGENTS-LAUNCH — P4.5 Vitest tests for UI-5.3 components.
 *
 * Covers (per task spec):
 *   (1)  PolicyGateSummary: renders "not recorded" for every null policy_snapshot sub-field
 *   (2)  PolicyGateSummary: renders field values when policy_snapshot is fully set
 *   (3)  AgentJobLaunchForm: Launch button disabled when acknowledgment unchecked
 *   (4)  AgentJobLaunchForm: Launch button enabled only when all required fields + checkbox filled
 *   (5)  AgentJobLaunchForm: Governance rejection (mock 422) shows violations list, form not cleared
 *   (6)  AgentsScreen: renders static-info when isAgentsLoopbackEnabled returns false
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mock (hoisted before component imports) ────────────────────────────
// Mock @/hooks/useAgentJobs so test controls isAgentsLoopbackEnabled +
// useLaunchAgentJob without live API access.
vi.mock("@/hooks/useAgentJobs", () => ({
  isAgentsLoopbackEnabled: vi.fn(() => false),
  useLaunchAgentJob: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  })),
}));

// ── Component imports (after vi.mock so they receive mocked module) ────────────
import { PolicyGateSummary } from "@/components/Agents/PolicyGateSummary";
import { AgentJobLaunchForm } from "@/components/Agents/AgentJobLaunchForm";
import { AgentsScreen } from "@/screens/AgentsScreen";

// ── Types and typed mock references ──────────────────────────────────────────
import type { AgentJobDetail } from "@/api/agentJobsClient";
import { AgentJobsApiError } from "@/api/agentJobsClient";
import { isAgentsLoopbackEnabled, useLaunchAgentJob } from "@/hooks/useAgentJobs";

const mockIsLoopback = vi.mocked(isAgentsLoopbackEnabled);
const mockUseLaunchAgentJob = vi.mocked(useLaunchAgentJob);

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

function defaultLaunchMock() {
  mockUseLaunchAgentJob.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

beforeEach(() => {
  defaultLaunchMock();
  mockIsLoopback.mockReturnValue(false);
});

// ── Test fixtures ─────────────────────────────────────────────────────────────

/** Job with null policy_snapshot — every gate field should render "not recorded". */
const JOB_NULL_SNAPSHOT: AgentJobDetail = {
  agent_job_id: "job_test_001",
  status: "RUNNING",
  created_at: "2026-07-07T10:00:00Z",
  updated_at: "2026-07-07T10:01:00Z",
  workspace_id: null,
  created_by: null,
  policy_snapshot: null,
};

/** Job with policy_snapshot fully populated — all gate fields should show real values. */
const JOB_SET_SNAPSHOT: AgentJobDetail = {
  agent_job_id: "job_test_002",
  status: "COMPLETED",
  created_at: "2026-07-07T10:00:00Z",
  updated_at: "2026-07-07T10:05:00Z",
  workspace_id: null,
  created_by: null,
  policy_snapshot: {
    provider: "claude",
    model: "claude-sonnet-4-6",
    tools: ["search_web", "extract_claims"],
    budget_usd: 10.0,
    sensitivity: "public",
  },
};

/** Job with policy_snapshot set but all sub-fields null (AC-4.5 edge case). */
const JOB_SNAPSHOT_ALL_NULL: AgentJobDetail = {
  agent_job_id: "job_test_003",
  status: "PENDING",
  created_at: "2026-07-07T10:00:00Z",
  updated_at: "2026-07-07T10:00:00Z",
  workspace_id: null,
  created_by: null,
  policy_snapshot: {
    provider: null,
    model: null,
    tools: null,
    budget_usd: null,
    sensitivity: null,
  },
};

/** Governance rejection error fixture (AC-4.4). */
const GOVERNANCE_ERROR = new AgentJobsApiError(
  "POST",
  "/api/agent-jobs",
  422,
  "Unprocessable Entity",
  {
    error: "governance_rejected",
    exit_code: 3,
    violations: [
      {
        rule_id: "RL_BUDGET_001",
        severity: "error",
        message: "Budget exceeds allowed limit for this workspace",
      },
    ],
  },
);

// ── (1) PolicyGateSummary — null policy_snapshot ──────────────────────────────

describe("PolicyGateSummary — null policy_snapshot (AC-4.5)", () => {
  it("renders 'not recorded' for provider when policy_snapshot is null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-provider']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for model when policy_snapshot is null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-model']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for tools when policy_snapshot is null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-tools']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for budget when policy_snapshot is null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-budget']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for sensitivity when policy_snapshot is null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-sensitivity']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for workspace (D12: always null)", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_NULL_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-workspace']")?.textContent?.trim(),
    ).toBe("not recorded");
  });

  it("renders 'not recorded' for all snapshot sub-fields when each is explicitly null", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SNAPSHOT_ALL_NULL} />,
      { wrapper: makeWrapper() },
    );
    const snapFields = ["provider", "model", "tools", "budget", "sensitivity"] as const;
    snapFields.forEach((field) => {
      expect(
        container
          .querySelector(`[data-testid='policy-gate-value-${field}']`)
          ?.textContent?.trim(),
      ).toBe("not recorded");
    });
  });

  it("shows placeholder message when job is null", () => {
    const { container } = render(
      <PolicyGateSummary job={null} />,
      { wrapper: makeWrapper() },
    );
    expect(container.textContent).toContain("Launch a job to see policy gates");
  });
});

// ── (2) PolicyGateSummary — populated policy_snapshot ────────────────────────

describe("PolicyGateSummary — populated policy_snapshot", () => {
  it("renders provider value", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-provider']")?.textContent,
    ).toContain("claude");
  });

  it("renders model value", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-model']")?.textContent,
    ).toContain("claude-sonnet-4-6");
  });

  it("renders tools as comma-separated list", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    const toolsText =
      container.querySelector("[data-testid='policy-gate-value-tools']")?.textContent ?? "";
    expect(toolsText).toContain("search_web");
    expect(toolsText).toContain("extract_claims");
  });

  it("renders budget formatted as $X.XX USD", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-budget']")?.textContent,
    ).toContain("10.00");
  });

  it("renders sensitivity value", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    expect(
      container.querySelector("[data-testid='policy-gate-value-sensitivity']")?.textContent,
    ).toContain("public");
  });

  it("renders status as raw string inside code element", () => {
    const { container } = render(
      <PolicyGateSummary job={JOB_SET_SNAPSHOT} />,
      { wrapper: makeWrapper() },
    );
    const statusCell = container.querySelector("[data-testid='policy-gate-value-status']");
    expect(statusCell?.querySelector("code")?.textContent).toBe("COMPLETED");
  });
});

// ── (3) AgentJobLaunchForm — button disabled when acknowledgment unchecked ────

describe("AgentJobLaunchForm — Launch button enablement (AC-4.1)", () => {
  it("Launch button is disabled when acknowledgment is unchecked", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    // Fill required fields but leave acknowledgment unchecked
    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("Launch button is disabled when model is empty (even with checkbox checked)", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("Launch button is disabled when tools is empty (even with checkbox checked)", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });
});

// ── (4) AgentJobLaunchForm — button enabled when all fields + checkbox filled ──

describe("AgentJobLaunchForm — Launch button enabled (AC-4.1)", () => {
  it("Launch button is enabled when all required fields filled AND acknowledgment checked", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web,extract_claims" },
      });
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("Launch button returns to disabled after unchecking acknowledgment", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    // Enable then disable
    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });
    expect(
      (container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement).disabled,
    ).toBe(false);

    act(() => {
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });
    expect(
      (container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});

// ── (5) AgentJobLaunchForm — governance rejection (AC-4.4) ───────────────────

describe("AgentJobLaunchForm — governance rejection (AC-4.4)", () => {
  it("shows governance rejection banner when mutation returns a 422 governance error", () => {
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: GOVERNANCE_ERROR,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    const banner = container.querySelector("[data-testid='launch-governance-rejection']");
    expect(banner).not.toBeNull();
    expect(banner?.getAttribute("role")).toBe("alert");
  });

  it("shows each violation's rule_id in the rejection list", () => {
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: GOVERNANCE_ERROR,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    expect(container.textContent).toContain("RL_BUDGET_001");
  });

  it("shows each violation's message in the rejection list", () => {
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: GOVERNANCE_ERROR,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    expect(container.textContent).toContain("Budget exceeds allowed limit");
  });

  it("form fields are NOT cleared when a governance rejection is present", () => {
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: GOVERNANCE_ERROR,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    // Type into form fields
    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
    });

    // Violations banner is still shown
    expect(container.querySelector("[data-testid='launch-governance-rejection']")).not.toBeNull();

    // Form fields retain their values (NOT cleared)
    const modelInput = container.querySelector("input[name='model']") as HTMLInputElement;
    const toolsInput = container.querySelector("input[name='tools']") as HTMLInputElement;
    expect(modelInput.value).toBe("claude-sonnet-4-6");
    expect(toolsInput.value).toBe("search_web");
  });

  it("renders generic error banner (not governance) for non-governance API errors", () => {
    const genericError = new AgentJobsApiError(
      "POST",
      "/api/agent-jobs",
      500,
      "Internal Server Error",
      null,
    );
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: genericError,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    expect(container.querySelector("[data-testid='launch-generic-error']")).not.toBeNull();
    expect(container.querySelector("[data-testid='launch-governance-rejection']")).toBeNull();
  });
});

// ── (6) AgentsScreen — static-info gate ──────────────────────────────────────

describe("AgentsScreen — loopback gate", () => {
  it("renders static-info element when isAgentsLoopbackEnabled returns false", () => {
    mockIsLoopback.mockReturnValue(false);

    const { container } = render(<AgentsScreen />, { wrapper: makeWrapper() });

    expect(container.querySelector(".rv-agents-static-info")).not.toBeNull();
  });

  it("static-info has role=status for screen-reader announcement", () => {
    mockIsLoopback.mockReturnValue(false);

    const { container } = render(<AgentsScreen />, { wrapper: makeWrapper() });

    const info = container.querySelector(".rv-agents-static-info");
    expect(info?.getAttribute("role")).toBe("status");
  });

  it("static-info text mentions rf serve and loopback env var", () => {
    mockIsLoopback.mockReturnValue(false);

    const { container } = render(<AgentsScreen />, { wrapper: makeWrapper() });

    const text = container.textContent ?? "";
    expect(text).toContain("rf serve");
    expect(text).toContain("VITE_RUNS_FRONTEND_LOOPBACK_API");
  });

  it("does NOT render .rv-agents-static-info when loopback is enabled", () => {
    mockIsLoopback.mockReturnValue(true);

    const { container } = render(<AgentsScreen />, { wrapper: makeWrapper() });

    expect(container.querySelector(".rv-agents-static-info")).toBeNull();
    expect(container.querySelector(".rv-agents")).not.toBeNull();
  });
});
