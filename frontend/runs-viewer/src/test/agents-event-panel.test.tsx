/**
 * AGENTS-EVENT-PANEL — P4.5 Vitest tests for UI-5.5 (AgentJobEventPanel).
 *
 * Tests cover (per AC-2.3 requirements):
 *   (1) Renders "Waiting for events" when jobId is null
 *   (2) Renders "Waiting for events" when job is not in a running status
 *   (3) Renders events list when events are available (mock useAgentJobEvents)
 *   (4) ARIA live region present in both waiting and live states
 *   (5) Does not render raw credential-shaped values in payload summary
 *
 * Additional coverage:
 *   (6) Shows "Stream interrupted — reconnecting…" when hook status = "error"
 *   (7) Forward-compat: unknown status starting with "run" enables the stream
 *   (8) Terminal status (completed/failed/cancelled) does not enable stream
 *   (9) Event rows expose data-event-type for testability
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

// ── Module mock (hoisted before component imports) ────────────────────────────
// Mock @/hooks/useAgentJobs to control useAgentJobEvents without live SSE.
vi.mock("@/hooks/useAgentJobs", () => ({
  useAgentJobEvents: vi.fn(),
  isAgentsLoopbackEnabled: vi.fn(() => true),
}));

// ── Component import (after vi.mock so it receives the mocked module) ─────────
import { AgentJobEventPanel } from "@/components/Agents/AgentJobEventPanel";

// ── Typed mock references ─────────────────────────────────────────────────────
import { useAgentJobEvents } from "@/hooks/useAgentJobs";
import type { AgentJobEvent } from "@/api/agentJobsClient";
import type { AgentJobEventsStatus } from "@/hooks/useAgentJobs";

const mockUseAgentJobEvents = vi.mocked(useAgentJobEvents);

// ── Fixture helpers ───────────────────────────────────────────────────────────

function makeEvent(
  overrides: Partial<AgentJobEvent> & { event_type: string },
): AgentJobEvent {
  return {
    payload: {},
    sequence: null,
    ...overrides,
  };
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

// ── (1) Waiting state: jobId null ─────────────────────────────────────────────

describe("AgentJobEventPanel — waiting state (jobId null)", () => {
  it("renders 'Waiting for events' when jobId is null", () => {
    const { container } = render(
      <AgentJobEventPanel jobId={null} jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-waiting']")).not.toBeNull();
    expect(container.textContent).toContain("Waiting for events");
  });

  it("does NOT render the events list when jobId is null", () => {
    const { container } = render(
      <AgentJobEventPanel jobId={null} jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-list']")).toBeNull();
  });

  it("passes enabled=false to the hook when jobId is null", () => {
    render(<AgentJobEventPanel jobId={null} jobStatus="running" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith(null, false);
  });
});

// ── (2) Waiting state: non-running status ─────────────────────────────────────

describe("AgentJobEventPanel — waiting state (non-running status)", () => {
  it("renders 'Waiting for events' when jobStatus is 'completed'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-abc" jobStatus="completed" />,
    );
    expect(container.querySelector("[data-testid='agent-event-waiting']")).not.toBeNull();
  });

  it("renders 'Waiting for events' when jobStatus is 'failed'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-abc" jobStatus="failed" />,
    );
    expect(container.querySelector("[data-testid='agent-event-waiting']")).not.toBeNull();
  });

  it("renders 'Waiting for events' when jobStatus is 'cancelled'", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-abc" jobStatus="cancelled" />,
    );
    expect(container.querySelector("[data-testid='agent-event-waiting']")).not.toBeNull();
  });

  it("passes enabled=false to the hook for terminal statuses", () => {
    render(<AgentJobEventPanel jobId="job-abc" jobStatus="cancelled" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-abc", false);
  });
});

// ── (3) Events list renders correctly ─────────────────────────────────────────

describe("AgentJobEventPanel — events list", () => {
  it("renders events list when events are available", () => {
    mockHook(
      [
        makeEvent({ event_type: "agent_started", sequence: 1 }),
        makeEvent({ event_type: "tool_call", sequence: 2 }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-list']")).not.toBeNull();
  });

  it("renders an item for each event", () => {
    mockHook(
      [
        makeEvent({ event_type: "agent_started", sequence: 1 }),
        makeEvent({ event_type: "tool_call", sequence: 2 }),
        makeEvent({ event_type: "agent_stopped", sequence: 3 }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const items = container.querySelectorAll("[data-testid^='agent-event-item-']");
    expect(items.length).toBe(3);
  });

  it("renders event_type prominently on each item", () => {
    mockHook(
      [makeEvent({ event_type: "tool_call_result", sequence: 5 })],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const typeEl = container.querySelector("[data-testid='agent-event-type-5']");
    expect(typeEl?.textContent).toBe("tool_call_result");
  });

  it("renders sequence number when present", () => {
    mockHook(
      [makeEvent({ event_type: "agent_started", sequence: 7 })],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-seq-7']")).not.toBeNull();
  });

  it("does NOT render the 'Waiting' message when events are present", () => {
    mockHook([makeEvent({ event_type: "agent_started", sequence: 1 })], "live");
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-waiting']")).toBeNull();
  });

  it("items have data-event-type attribute for testability", () => {
    mockHook(
      [makeEvent({ event_type: "claim_extracted", sequence: 4 })],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const item = container.querySelector("[data-testid='agent-event-item-4']");
    expect(item?.getAttribute("data-event-type")).toBe("claim_extracted");
  });

  it("passes enabled=true to the hook when running and jobId is set", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="running" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", true);
  });
});

// ── (4) ARIA live region ──────────────────────────────────────────────────────

describe("AgentJobEventPanel — ARIA live region", () => {
  it("ARIA live region is present when in waiting state (jobId null)", () => {
    const { container } = render(
      <AgentJobEventPanel jobId={null} jobStatus="idle" />,
    );
    const liveRegion = container.querySelector("[aria-live='polite']");
    expect(liveRegion).not.toBeNull();
  });

  it("ARIA live region is present when displaying events", () => {
    mockHook(
      [makeEvent({ event_type: "agent_started", sequence: 1 })],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const liveRegion = container.querySelector("[aria-live='polite']");
    expect(liveRegion).not.toBeNull();
  });

  it("ARIA live region is present when waiting with non-running status", () => {
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="completed" />,
    );
    const liveRegion = container.querySelector("[aria-live='polite']");
    expect(liveRegion).not.toBeNull();
  });

  it("the events list is nested inside the ARIA live region", () => {
    mockHook(
      [makeEvent({ event_type: "agent_started", sequence: 1 })],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const liveRegion = container.querySelector("[aria-live='polite']");
    const list = liveRegion?.querySelector("[data-testid='agent-event-list']");
    expect(list).not.toBeNull();
  });
});

// ── (5) Security: no credential-shaped values in rendered output ──────────────

describe("AgentJobEventPanel — security: credential redaction in payload summary", () => {
  it("does not render a raw bearer token value in the payload summary", () => {
    mockHook(
      [
        makeEvent({
          event_type: "auth_event",
          sequence: 1,
          payload: { token: "bearer_secret_xyz_abc123", action: "authenticated" },
        }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    // The raw token value must be absent
    expect(container.textContent).not.toContain("bearer_secret_xyz_abc123");
    // It should be replaced with the redaction sentinel
    expect(container.textContent).toContain("[REDACTED]");
  });

  it("does not render a raw password value in the payload summary", () => {
    mockHook(
      [
        makeEvent({
          event_type: "credential_event",
          sequence: 2,
          payload: { password: "s3cr3t_hunter2", step: "validate" },
        }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-2" jobStatus="running" />,
    );
    expect(container.textContent).not.toContain("s3cr3t_hunter2");
    expect(container.textContent).toContain("[REDACTED]");
  });

  it("does not render a raw api_key value in the payload summary", () => {
    mockHook(
      [
        makeEvent({
          event_type: "tool_call",
          sequence: 3,
          payload: { api_key: "sk-openai-abc999", model: "gpt-5" },
        }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-3" jobStatus="running" />,
    );
    expect(container.textContent).not.toContain("sk-openai-abc999");
    expect(container.textContent).toContain("[REDACTED]");
  });

  it("renders non-credential payload fields without modification", () => {
    mockHook(
      [
        makeEvent({
          event_type: "claim_extracted",
          sequence: 4,
          payload: { claim_id: "clm_042", status: "pending" },
        }),
      ],
      "live",
    );
    const { container } = render(
      <AgentJobEventPanel jobId="job-4" jobStatus="running" />,
    );
    // Non-credential fields pass through
    expect(container.textContent).toContain("clm_042");
  });
});

// ── (6) Stream-interrupted state ─────────────────────────────────────────────

describe("AgentJobEventPanel — stream interrupted state", () => {
  it("shows 'Stream interrupted — reconnecting…' when hook status is 'error'", () => {
    mockHook([], "error");
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const interrupted = container.querySelector("[data-testid='agent-event-interrupted']");
    expect(interrupted).not.toBeNull();
    expect(interrupted?.textContent).toContain("Stream interrupted");
    expect(interrupted?.textContent).toContain("reconnecting");
  });

  it("interrupted notice has role=status", () => {
    mockHook([], "error");
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    const interrupted = container.querySelector("[data-testid='agent-event-interrupted']");
    expect(interrupted?.getAttribute("role")).toBe("status");
  });

  it("does NOT show interrupted notice when hook status is 'live'", () => {
    mockHook([makeEvent({ event_type: "agent_started", sequence: 1 })], "live");
    const { container } = render(
      <AgentJobEventPanel jobId="job-1" jobStatus="running" />,
    );
    expect(container.querySelector("[data-testid='agent-event-interrupted']")).toBeNull();
  });
});

// ── (7) Forward-compat: unknown "run*" statuses ────────────────────────────────

describe("AgentJobEventPanel — forward-compat status detection", () => {
  it("enables stream for known status 'queued'", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="queued" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", true);
  });

  it("enables stream for known status 'streaming'", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="streaming" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", true);
  });

  it("enables stream for unknown 'running_paused' status (starts with 'run')", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="running_paused" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", true);
  });

  it("does NOT enable stream for 'pending' (not in set, does not start with 'run')", () => {
    render(<AgentJobEventPanel jobId="job-1" jobStatus="pending" />);
    expect(mockUseAgentJobEvents).toHaveBeenCalledWith("job-1", false);
  });
});
