/**
 * agents-launch-smoke.test.tsx — P4.5 UI-5.8
 *
 * Runtime smoke tests exercising the FULL launch flow end-to-end.
 * These tests render at the AgentsScreen level (or direct form level) and walk
 * through complete user journeys, complementing the isolated unit tests in
 * agents-launch.test.tsx (which cover individual component invariants).
 *
 * AGENT-VERIFY-launch-context-smoke:
 *   "Research this" route state pre-populates the launch form context section.
 *
 * AGENT-VERIFY-launch-gates-smoke:
 *   Governance gates block Launch until acknowledged; rejection flow renders
 *   violations and leaves form intact; PolicyGateSummary coexists on-screen.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mock (hoisted before component imports) ────────────────────────────
// Matches the pattern in agents-launch.test.tsx exactly.
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
import { AgentsScreen } from "@/screens/AgentsScreen";
import { AgentJobLaunchForm } from "@/components/Agents/AgentJobLaunchForm";
import { AgentJobsApiError } from "@/api/agentJobsClient";
import { isAgentsLoopbackEnabled, useLaunchAgentJob } from "@/hooks/useAgentJobs";

const mockIsLoopback = vi.mocked(isAgentsLoopbackEnabled);
const mockUseLaunchAgentJob = vi.mocked(useLaunchAgentJob);

// ── Fixtures ──────────────────────────────────────────────────────────────────

/** Governance rejection from a mock 422 response (AC-4.4). */
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
        rule_id: "RL_SMOKE_001",
        severity: "error",
        message: "Tool 'adversarial_tool' is not permitted by governance policy",
      },
    ],
  },
);

// ── Test helpers ──────────────────────────────────────────────────────────────

function defaultLaunchMock() {
  mockUseLaunchAgentJob.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

/**
 * Builds a Wrapper component.
 * Pass `routeState` to simulate arriving at /agents via navigate() with state
 * (e.g. from ClaimAuditWorkbench setting { input_claim_ids: [...] }).
 */
function makeWrapper(routeState?: unknown) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    const initialEntry = routeState
      ? { pathname: "/agents", state: routeState }
      : "/agents";
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

beforeEach(() => {
  defaultLaunchMock();
  mockIsLoopback.mockReturnValue(false);
});

// ── AGENT-VERIFY-launch-context-smoke ─────────────────────────────────────────
//
// Simulates arriving at /agents from ClaimAuditWorkbench via navigate("/agents",
// { state: { input_claim_ids: ["clm_001", "clm_002"] } }).
// The full AgentsScreen is rendered so the route state → form context path is
// exercised end-to-end.

describe("AGENT-VERIFY-launch-context-smoke: route state pre-populates form context", () => {
  it("claim IDs from route state appear in the read-only context section", () => {
    mockIsLoopback.mockReturnValue(true);

    const { container } = render(<AgentsScreen />, {
      wrapper: makeWrapper({ input_claim_ids: ["clm_001", "clm_002"] }),
    });

    const contextReadonly = container.querySelector(
      "[data-testid='launch-context-readonly']",
    );
    expect(contextReadonly).not.toBeNull();
    expect(contextReadonly?.textContent).toContain("clm_001");
    expect(contextReadonly?.textContent).toContain("clm_002");
  });

  it("manual context inputs are hidden when claim IDs arrive via route state", () => {
    mockIsLoopback.mockReturnValue(true);

    const { container } = render(<AgentsScreen />, {
      wrapper: makeWrapper({ input_claim_ids: ["clm_001", "clm_002"] }),
    });

    // Manual inputs for claim IDs / report ID should not be present when
    // context is pre-populated from route state (AC-1.1).
    expect(container.querySelector("input[name='manual_claim_ids']")).toBeNull();
    expect(container.querySelector("input[name='manual_report_id']")).toBeNull();
  });

  it("form is not in error state when arriving with pre-populated context", () => {
    mockIsLoopback.mockReturnValue(true);

    const { container } = render(<AgentsScreen />, {
      wrapper: makeWrapper({ input_claim_ids: ["clm_001", "clm_002"] }),
    });

    // Neither error banner should be present on initial render.
    expect(container.querySelector("[data-testid='launch-governance-rejection']")).toBeNull();
    expect(container.querySelector("[data-testid='launch-generic-error']")).toBeNull();
  });
});

// ── AGENT-VERIFY-launch-gates-smoke ──────────────────────────────────────────
//
// Walks the full gates flow:
//   1. Form with fields filled but acknowledgment unchecked → button disabled.
//   2. Checking acknowledgment → button enabled.
//   3. Governance rejection (mock 422) → violations shown.
//   4. Form fields NOT cleared after rejection.
//   5. PolicyGateSummary coexists on-screen when rejection is active (screen level).

describe("AGENT-VERIFY-launch-gates-smoke: governance gates block launch until acknowledged", () => {
  it("Launch button is disabled when acknowledgment checkbox is unchecked", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      // provider defaults to "claude", sensitivity to "public" — only model + tools needed.
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
      // Deliberately leave acknowledgment unchecked.
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("checking the acknowledgment checkbox enables the Launch button", () => {
    const { container } = render(
      <AgentJobLaunchForm onLaunchSuccess={vi.fn()} />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
      fireEvent.click(container.querySelector("input[name='acknowledged']") as HTMLInputElement);
    });

    const btn = container.querySelector("[data-testid='launch-submit']") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("governance violation rule_id is displayed after rejection", () => {
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

    const rejection = container.querySelector("[data-testid='launch-governance-rejection']");
    expect(rejection).not.toBeNull();
    expect(rejection?.getAttribute("role")).toBe("alert");
    expect(container.textContent).toContain("RL_SMOKE_001");
  });

  it("governance violation message is displayed after rejection", () => {
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

    expect(container.textContent).toContain("adversarial_tool");
    expect(container.textContent).toContain("not permitted by governance policy");
  });

  it("form fields are NOT cleared after governance rejection", () => {
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

    act(() => {
      fireEvent.change(container.querySelector("input[name='model']") as HTMLInputElement, {
        target: { value: "claude-sonnet-4-6" },
      });
      fireEvent.change(container.querySelector("input[name='tools']") as HTMLInputElement, {
        target: { value: "search_web" },
      });
    });

    // Violations banner still present.
    expect(container.querySelector("[data-testid='launch-governance-rejection']")).not.toBeNull();

    // Field values must be retained (not reset to defaults).
    expect(
      (container.querySelector("input[name='model']") as HTMLInputElement).value,
    ).toBe("claude-sonnet-4-6");
    expect(
      (container.querySelector("input[name='tools']") as HTMLInputElement).value,
    ).toBe("search_web");
  });

  it("PolicyGateSummary is still rendered in AgentsScreen when a rejection is active", () => {
    mockIsLoopback.mockReturnValue(true);
    mockUseLaunchAgentJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: GOVERNANCE_ERROR,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(<AgentsScreen />, {
      wrapper: makeWrapper(),
    });

    // PolicyGateSummary renders inside .rv-agents__policy (AgentsScreenLoopback).
    // With no job launched yet (activeJob = null) it shows the placeholder text.
    expect(container.querySelector("[data-testid='policy-gate-summary']")).not.toBeNull();
    expect(container.textContent).toContain("Launch a job to see policy gates");

    // Governance rejection banner co-exists on the same screen.
    expect(container.querySelector("[data-testid='launch-governance-rejection']")).not.toBeNull();
  });
});
