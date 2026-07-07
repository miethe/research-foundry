/**
 * AGENTS-RESILIENCE — P4.5 Vitest tests for UI-5.7.
 *
 * Covers two resilience requirements:
 *
 * 1. PolicyGateSummary — null sub-fields (AC-4.5):
 *    (1a) All null policy_snapshot sub-fields render "not recorded"
 *         (parameterized over provider, model, tools, budget_usd, sensitivity)
 *    (1b) Null job-level fields (workspace_id, created_by) render "not recorded"
 *    (1c) Empty tools array renders "not recorded" (not a blank cell)
 *    (1d) Known status renders without an "(unrecognized)" label
 *    (1e) Unknown/future status renders WITH the "(unrecognized)" label  ← R-P2
 *
 * 2. AgentJobEventPanel — unknown job-status values (R-P2 extension):
 *    (2a) Unknown status (not in any known set) enables the SSE stream
 *    (2b) Terminal status shows accumulated events but the panel shows the
 *         "Stream closed" completion indicator
 *    (2c) Unknown status shows the "(unknown status)" indicator in the panel
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

// ── PolicyGateSummary ─────────────────────────────────────────────────────────

import { PolicyGateSummary } from "@/components/Agents/PolicyGateSummary";
import type { AgentJobDetail } from "@/api/agentJobsClient";

// ── AgentJobEventPanel — module mock (hoisted before import) ──────────────────

vi.mock("@/hooks/useAgentJobs", () => ({
  useAgentJobEvents: vi.fn(),
  isAgentsLoopbackEnabled: vi.fn(() => true),
}));

import { AgentJobEventPanel } from "@/components/Agents/AgentJobEventPanel";
import { useAgentJobEvents } from "@/hooks/useAgentJobs";
import type { AgentJobEvent } from "@/api/agentJobsClient";
import type { AgentJobEventsStatus } from "@/hooks/useAgentJobs";

const mockUseAgentJobEvents = vi.mocked(useAgentJobEvents);

// ── Fixture helpers ───────────────────────────────────────────────────────────

function makeJob(overrides?: Partial<AgentJobDetail>): AgentJobDetail {
  return {
    agent_job_id: "job-resilience-001",
    status: "completed",
    created_at: "2026-07-07T10:00:00Z",
    updated_at: "2026-07-07T10:05:00Z",
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

function makeEvent(
  overrides: Partial<AgentJobEvent> & { event_type: string },
): AgentJobEvent {
  return { payload: {}, sequence: null, ...overrides };
}

function mockHook(
  events: AgentJobEvent[] = [],
  status: AgentJobEventsStatus = "idle",
) {
  mockUseAgentJobEvents.mockReturnValue({ events, status });
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  mockHook([], "idle");
});

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 1 — PolicyGateSummary resilience
// ═══════════════════════════════════════════════════════════════════════════════

describe("PolicyGateSummary — null sub-fields render 'not recorded'", () => {
  // (1a) policy_snapshot sub-fields — parameterized
  it.each([
    ["provider", "policy-gate-value-provider"],
    ["model", "policy-gate-value-model"],
    ["sensitivity", "policy-gate-value-sensitivity"],
  ])("null policy_snapshot.%s renders 'not recorded'", (_field, testId) => {
    const job = makeJob({
      policy_snapshot: {
        provider: null,
        model: null,
        tools: null,
        budget_usd: null,
        sensitivity: null,
        // Override the specific field under test (already null above)
      },
    });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector(`[data-testid='${testId}']`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });

  it("null policy_snapshot.budget_usd renders 'not recorded'", () => {
    const job = makeJob({
      policy_snapshot: { budget_usd: null },
    });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector("[data-testid='policy-gate-value-budget']");
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });

  it("null policy_snapshot.tools renders 'not recorded'", () => {
    const job = makeJob({
      policy_snapshot: { tools: null },
    });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector("[data-testid='policy-gate-value-tools']");
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });

  it("empty policy_snapshot.tools array renders 'not recorded' (not blank)", () => {
    const job = makeJob({
      policy_snapshot: { tools: [] },
    });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector("[data-testid='policy-gate-value-tools']");
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });

  it("entirely null policy_snapshot renders 'not recorded' for all sub-fields", () => {
    const job = makeJob({ policy_snapshot: null });
    const { container } = render(<PolicyGateSummary job={job} />);

    const testIds = [
      "policy-gate-value-provider",
      "policy-gate-value-model",
      "policy-gate-value-tools",
      "policy-gate-value-budget",
      "policy-gate-value-sensitivity",
    ];
    for (const id of testIds) {
      const cell = container.querySelector(`[data-testid='${id}']`);
      expect(cell, `expected data-testid="${id}" to be present`).not.toBeNull();
      expect(cell?.textContent?.trim(), `field ${id} should read "not recorded"`).toBe(
        "not recorded",
      );
    }
  });

  // (1b) Job-level nullable fields
  it("null workspace_id renders 'not recorded'", () => {
    const job = makeJob({ workspace_id: null });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector("[data-testid='policy-gate-value-workspace']");
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });

  it("null created_by renders 'not recorded'", () => {
    const job = makeJob({ created_by: null });
    const { container } = render(<PolicyGateSummary job={job} />);
    const cell = container.querySelector("[data-testid='policy-gate-value-created-by']");
    expect(cell).not.toBeNull();
    expect(cell?.textContent?.trim()).toBe("not recorded");
  });
});

// ── (1d) + (1e) Status badge ──────────────────────────────────────────────────

describe("PolicyGateSummary — status rendering", () => {
  it.each(["queued", "running", "streaming", "completed", "failed", "cancelled"])(
    "known status '%s' renders WITHOUT '(unrecognized)' label",
    (knownStatus) => {
      const job = makeJob({ status: knownStatus });
      const { container } = render(<PolicyGateSummary job={job} />);
      expect(
        container.querySelector("[data-testid='policy-gate-status-unrecognized']"),
      ).toBeNull();
    },
  );

  // R-P2 required unit test: unknown status badge
  it("unknown status string renders WITH '(unrecognized)' label (R-P2)", () => {
    const job = makeJob({ status: "custom_running_v2" });
    const { container } = render(<PolicyGateSummary job={job} />);
    const badge = container.querySelector("[data-testid='policy-gate-status-unrecognized']");
    expect(badge, "unrecognized badge must be present for unknown status").not.toBeNull();
    expect(badge?.textContent).toContain("unrecognized");
  });

  it("unknown status still renders the raw status string alongside the badge", () => {
    const job = makeJob({ status: "paused_for_review" });
    const { container } = render(<PolicyGateSummary job={job} />);
    const statusCell = container.querySelector("[data-testid='policy-gate-value-status']");
    expect(statusCell?.textContent).toContain("paused_for_review");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 2 — AgentJobEventPanel resilience (R-P2 extension)
// ═══════════════════════════════════════════════════════════════════════════════

describe("AgentJobEventPanel — unknown status enables stream", () => {
  // (2a) Unknown status → treat as potentially running → enabled=true
  it.each(["paused", "interrupted", "superpowered", "custom_v3"])(
    "enables stream for unknown status '%s' (not in any known set)",
    (unknownStatus) => {
      render(<AgentJobEventPanel jobId="job-1" jobStatus={unknownStatus} />);
      expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", true);
    },
  );

  it("does NOT enable stream for known terminal status 'completed'", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="completed" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", false);
  });

  it("does NOT enable stream for known terminal status 'failed'", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="failed" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", false);
  });

  it("does NOT enable stream for known terminal status 'cancelled'", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="cancelled" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", false);
  });
});

describe("AgentJobEventPanel — terminal status shows completion indicator", () => {
  // (2b) Terminal status shows "Stream closed" indicator and keeps events visible.
  it.each(["completed", "failed", "cancelled"])(
    "shows 'Stream closed' indicator for terminal status '%s'",
    (terminalStatus) => {
      const { container } = render(
        <AgentJobEventPanel jobId="job-1" jobStatus={terminalStatus} />,
      );
      const indicator = container.querySelector("[data-testid='agent-event-terminal-status']");
      expect(indicator, "terminal indicator must be present").not.toBeNull();
      expect(indicator?.textContent).toContain("Stream closed");
      expect(indicator?.textContent).toContain(terminalStatus);
    },
  );

  it("terminal indicator has role='status' for accessibility", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="completed" />,
    );
    const indicator = container.querySelector("[data-testid='agent-event-terminal-status']");
    expect(indicator?.getAttribute("role")).toBe("status");
  });

  it("accumulated events remain visible when status transitions to terminal", () => {
    mockHook(
      [
        makeEvent({ event_type: "claim_extracted", sequence: 1 }),
        makeEvent({ event_type: "agent_stopped", sequence: 2 }),
      ],
      "idle",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="completed" />,
    );
    // Events list must still be rendered (state not cleared on terminal)
    const list = container.querySelector("[data-testid='agent-event-list']");
    expect(list, "events list must remain visible after terminal status").not.toBeNull();
    const items = list?.querySelectorAll("[data-testid^='agent-event-item-']");
    expect(items?.length).toBe(2);
  });

  it("running status does NOT show the terminal indicator", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(
      container.querySelector("[data-testid='agent-event-terminal-status']"),
    ).toBeNull();
  });
});

describe("AgentJobEventPanel — unknown status shows indicator", () => {
  // (2c) Unknown status shows "(unknown status)" indicator in panel header.
  it("shows '(unknown status)' indicator for unknown status 'paused'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="paused" />,
    );
    const indicator = container.querySelector("[data-testid='agent-event-unknown-status']");
    expect(indicator, "'unknown status' indicator must be present").not.toBeNull();
    expect(indicator?.textContent).toContain("unknown status");
  });

  it("'(unknown status)' indicator has role='status' for accessibility", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="interrupted" />,
    );
    const indicator = container.querySelector("[data-testid='agent-event-unknown-status']");
    expect(indicator?.getAttribute("role")).toBe("status");
  });

  it("does NOT show '(unknown status)' indicator for known running status 'running'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(
      container.querySelector("[data-testid='agent-event-unknown-status']"),
    ).toBeNull();
  });

  it("does NOT show '(unknown status)' indicator for known terminal status 'failed'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="failed" />,
    );
    expect(
      container.querySelector("[data-testid='agent-event-unknown-status']"),
    ).toBeNull();
  });

  it("does NOT show '(unknown status)' indicator when jobId is null (no active job)", () => {
    const { container } = render(
      <AgentJobEventPanel jobId={null} jobStatus="paused" />,
    );
    expect(
      container.querySelector("[data-testid='agent-event-unknown-status']"),
    ).toBeNull();
  });

  it("ARIA live region is always present even when unknown status indicator is shown", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="paused" />,
    );
    const liveRegion = container.querySelector("[aria-live='polite']");
    expect(liveRegion).not.toBeNull();
  });
});
