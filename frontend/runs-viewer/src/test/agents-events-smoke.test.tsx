/**
 * AGENTS-EVENTS-SMOKE — P4.5 UI-5.9 runtime smoke tests.
 *
 * Covers 4 AGENT-VERIFY IDs:
 *   AGENT-VERIFY-event-stream-smoke       — live streaming render (AC-2.3)
 *   AGENT-VERIFY-acceptance-flow-smoke    — accept/reject integration (AC-3.5)
 *   AGENT-VERIFY-no-direct-write-audit    — no catalog write path bypass
 *   AGENT-VERIFY-policy-snapshot-resilience — null fields + unknown status
 *
 * Scope: smoke-level integration tests. Do NOT duplicate the fine-grained
 * assertions already covered in agents-event-panel.test.tsx,
 * agents-intake.test.tsx, or agents-resilience.test.tsx.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ── Module mock (hoisted before all component imports) ────────────────────────
// All three hooks live in @/hooks/useAgentJobs — one mock covers everything.
vi.mock("@/hooks/useAgentJobs", () => ({
  useAgentJobEvents: vi.fn(),
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
  isAgentsLoopbackEnabled: vi.fn(() => true),
}));

// ── Component imports (after vi.mock so they receive the mocked module) ───────
import { AgentJobEventPanel } from "@/components/Agents/AgentJobEventPanel";
import { EvidenceIntakePanel } from "@/components/Agents/EvidenceIntakePanel";
import { PolicyGateSummary } from "@/components/Agents/PolicyGateSummary";

// ── Types and typed mock references ──────────────────────────────────────────
import type { AgentJobArtifact, AgentJobDetail, AgentJobEvent } from "@/api/agentJobsClient";
import {
  useAgentJobEvents,
  useAgentJobArtifacts,
  useAcceptAgentJobArtifacts,
} from "@/hooks/useAgentJobs";
import type { AgentJobEventsStatus } from "@/hooks/useAgentJobs";

const mockUseEvents    = vi.mocked(useAgentJobEvents);
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

function makeEvent(
  overrides: Partial<AgentJobEvent> & { event_type: string },
): AgentJobEvent {
  return { payload: {}, sequence: null, ...overrides };
}

function mockEvents(
  events: AgentJobEvent[] = [],
  status: AgentJobEventsStatus = "idle",
) {
  mockUseEvents.mockReturnValue({ events, status });
}

function mockArtifacts(data: AgentJobArtifact[] | undefined = undefined) {
  mockUseArtifacts.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

function mockAccept(mutateFn = vi.fn()) {
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

function makeJob(overrides?: Partial<AgentJobDetail>): AgentJobDetail {
  return {
    agent_job_id: "job_smoke_001",
    status: "completed",
    created_at: "2026-07-07T12:00:00Z",
    updated_at: "2026-07-07T12:05:00Z",
    workspace_id: null,
    created_by: null,
    policy_snapshot: {
      provider: "anthropic",
      model: "claude-sonnet",
      tools: ["web_search"],
      budget_usd: 5.0,
      sensitivity: "low",
    },
    ...overrides,
  };
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  mockEvents([], "idle");
  mockArtifacts(undefined);
  mockAccept();
});

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT-VERIFY-event-stream-smoke
// ═══════════════════════════════════════════════════════════════════════════════

describe("AGENT-VERIFY-event-stream-smoke — live streaming render", () => {
  it("renders the event in the list with event_type visible when hook returns live events", () => {
    mockEvents(
      [makeEvent({ event_type: "tool_call", payload: { tool: "search_web" }, sequence: 1 })],
      "live",
    );

    const { container } = render(
      <AgentJobEventPanel jobId="job_001" jobStatus="running" />,
    );

    // Event list must be present
    expect(container.querySelector("[data-testid='agent-event-list']")).not.toBeNull();
    // event_type must be visible using the sequence-keyed testid
    const typeEl = container.querySelector("[data-testid='agent-event-type-1']");
    expect(typeEl).not.toBeNull();
    expect(typeEl?.textContent).toBe("tool_call");
  });

  it("ARIA live region is present and marked aria-live='polite' during a live stream", () => {
    mockEvents(
      [makeEvent({ event_type: "tool_call", payload: { tool: "search_web" }, sequence: 1 })],
      "live",
    );

    const { container } = render(
      <AgentJobEventPanel jobId="job_001" jobStatus="running" />,
    );

    const liveRegion = container.querySelector("[data-testid='agent-event-live-region']");
    expect(liveRegion).not.toBeNull();
    expect(liveRegion?.getAttribute("aria-live")).toBe("polite");
  });

  it("'Waiting for events' placeholder is NOT shown when events exist", () => {
    mockEvents(
      [makeEvent({ event_type: "tool_call", payload: { tool: "search_web" }, sequence: 1 })],
      "live",
    );

    const { container } = render(
      <AgentJobEventPanel jobId="job_001" jobStatus="running" />,
    );

    expect(container.querySelector("[data-testid='agent-event-waiting']")).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT-VERIFY-acceptance-flow-smoke
// ═══════════════════════════════════════════════════════════════════════════════

describe("AGENT-VERIFY-acceptance-flow-smoke — accept/reject integration", () => {
  // Fixtures — one source_card (candidates present) + one claim_proposal (null candidates).
  const SOURCE_CARD: AgentJobArtifact = {
    artifact_id: "smoke_sc_001",
    artifact_kind: "source_card",
    accepted: false,
    source_candidates: [{ src_id: "src_01" }],
  };

  const CLAIM_NULL: AgentJobArtifact = {
    artifact_id: "smoke_cp_001",
    artifact_kind: "claim_proposal",
    accepted: false,
    source_candidates: null,
  };

  it("claim_proposal with null source_candidates shows the 'incomplete proposal' badge", () => {
    mockArtifacts([SOURCE_CARD, CLAIM_NULL]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    const badge = container.querySelector(
      `[data-testid='intake-incomplete-badge-${CLAIM_NULL.artifact_id}']`,
    );
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toMatch(/incomplete proposal/i);
  });

  it("source_card with candidates present does NOT show the incomplete badge", () => {
    mockArtifacts([SOURCE_CARD, CLAIM_NULL]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    expect(
      container.querySelector(
        `[data-testid='intake-incomplete-badge-${SOURCE_CARD.artifact_id}']`,
      ),
    ).toBeNull();
  });

  it("Accept all staged calls mutate with jobId and no artifact_ids — backend accepts all staged", () => {
    const mutateFn = vi.fn();
    mockAccept(mutateFn);
    mockArtifacts([SOURCE_CARD, CLAIM_NULL]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    // Check the source_card checkbox (cosmetic review gate — enables the Accept button)
    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${SOURCE_CARD.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement,
      );
    });

    expect(mutateFn).toHaveBeenCalledOnce();
    // Backend accepts all staged — req must NOT contain artifact_ids (P5 scope)
    const arg = mutateFn.mock.calls[0]![0] as { jobId: string; req: Record<string, unknown> };
    expect(arg.jobId).toBe("job_001");
    expect(arg.req).not.toHaveProperty("artifact_ids");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT-VERIFY-no-direct-write-audit
// ═══════════════════════════════════════════════════════════════════════════════

describe("AGENT-VERIFY-no-direct-write-audit — no path bypasses the accept endpoint", () => {
  const ARTIFACT: AgentJobArtifact = {
    artifact_id: "audit_sc_001",
    artifact_kind: "source_card",
    accepted: false,
    source_candidates: null,
  };

  it("clicking 'Accept selected' triggers the mutate function — the sole catalog-write path", () => {
    const mutateFn = vi.fn();
    mockAccept(mutateFn);
    mockArtifacts([ARTIFACT]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    act(() => {
      fireEvent.click(
        container.querySelector("[data-testid='intake-accept-btn']") as HTMLButtonElement,
      );
    });

    expect(mutateFn).toHaveBeenCalledOnce();
  });

  it("clicking 'Reject all' does NOT trigger the mutate function", () => {
    const mutateFn = vi.fn();
    mockAccept(mutateFn);
    mockArtifacts([ARTIFACT]);

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

  it("accepted-summary state is absent unless isSuccess=true — no state-only bypass", () => {
    // Even after checking a checkbox, the accepted summary must remain absent
    // until acceptMutation.isSuccess resolves — confirming there is no direct
    // state path that would imply a catalog write without the API call.
    const mutateFn = vi.fn();
    mockAccept(mutateFn);
    mockArtifacts([ARTIFACT]);

    const { container } = render(
      <EvidenceIntakePanel jobId="job_001" />,
      { wrapper: makeWrapper() },
    );

    act(() => {
      fireEvent.click(
        container.querySelector(
          `[data-testid='intake-checkbox-${ARTIFACT.artifact_id}']`,
        ) as HTMLInputElement,
      );
    });

    // Accepted summary absent — mutate has not yet resolved isSuccess=true
    expect(container.querySelector("[data-testid='intake-accepted-summary']")).toBeNull();
    expect(container.querySelector("[data-testid='intake-acceptance-id']")).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT-VERIFY-policy-snapshot-resilience
// ═══════════════════════════════════════════════════════════════════════════════

describe("AGENT-VERIFY-policy-snapshot-resilience — null fields + unknown status", () => {
  it("renders 'not recorded' for every policy_snapshot cell when all sub-fields are null", () => {
    const job = makeJob({
      policy_snapshot: {
        provider: null,
        model: null,
        tools: null,
        budget_usd: null,
        sensitivity: null,
      },
    });

    const { container } = render(<PolicyGateSummary job={job} />);

    const cells: Array<[testId: string, fieldName: string]> = [
      ["policy-gate-value-provider",    "provider"],
      ["policy-gate-value-model",       "model"],
      ["policy-gate-value-tools",       "tools"],
      ["policy-gate-value-budget",      "budget_usd"],
      ["policy-gate-value-sensitivity", "sensitivity"],
    ];

    for (const [testId, fieldName] of cells) {
      const cell = container.querySelector(`[data-testid='${testId}']`);
      expect(cell, `cell for ${fieldName} must exist in the DOM`).not.toBeNull();
      expect(
        cell?.textContent?.trim(),
        `${fieldName} must read "not recorded" when null`,
      ).toBe("not recorded");
    }
  });

  it("renders the unrecognized status badge for the unknown status string 'suspended'", () => {
    const job = makeJob({ status: "suspended" });

    const { container } = render(<PolicyGateSummary job={job} />);

    const badge = container.querySelector("[data-testid='policy-gate-status-unrecognized']");
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toContain("unrecognized");
  });

  it("does NOT render the unrecognized badge for known status 'running'", () => {
    const job = makeJob({ status: "running" });

    const { container } = render(<PolicyGateSummary job={job} />);

    expect(
      container.querySelector("[data-testid='policy-gate-status-unrecognized']"),
    ).toBeNull();
  });

  it("does NOT render the unrecognized badge for known status 'completed'", () => {
    const job = makeJob({ status: "completed" });

    const { container } = render(<PolicyGateSummary job={job} />);

    expect(
      container.querySelector("[data-testid='policy-gate-status-unrecognized']"),
    ).toBeNull();
  });
});
