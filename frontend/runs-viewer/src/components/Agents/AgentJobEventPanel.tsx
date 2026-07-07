/**
 * AgentJobEventPanel — P4.5 UI-5.5 (updated UI-5.7).
 *
 * Renders the live SSE event stream for an agent job (AC-2.3).
 *
 * Behaviour:
 *  - Enabled when jobStatus is in the known running set (queued / running /
 *    streaming) OR is an unrecognized future status not in any known set.
 *    Known non-active pre-run states (pending) and known terminal states
 *    (completed / failed / cancelled) do NOT enable the stream.
 *  - Shows "Waiting for events…" placeholder when disabled or no events have
 *    arrived yet; the ARIA live region is always mounted so screen readers pick
 *    up the first arriving event.
 *  - Shows "Stream interrupted — reconnecting…" when the hook reports an error
 *    state; actual reconnect logic lives in useAgentJobEvents.
 *  - Accumulated events are kept visible after a job reaches a terminal state
 *    (completed / failed / cancelled) so operators can review the log. A
 *    "Stream closed — job {status}" indicator is shown in the panel header.
 *  - Unknown (unrecognized) statuses enable the stream as "potentially running"
 *    and show a small "(unknown status)" indicator in the panel header (UI-5.7).
 *  - Auto-scrolls to the latest event row.
 *
 * SECURITY (AC-2.3):
 *  - Event payloads are already-redacted by the server (P4.4 redact_payload gate).
 *  - This component MUST NOT call console.log with payload values.
 *  - formatPayloadSummary strips credential-shaped keys as a defence-in-depth
 *    measure, replacing values with "[REDACTED]".
 *
 * Usage hint: mount with key={jobId} when the job selection changes so React
 * unmounts/remounts the hook and events reset cleanly for the new job.
 */

import { useEffect, useRef } from "react";
import { useAgentJobEvents } from "@/hooks/useAgentJobs";
import type { AgentJobEvent } from "@/api/agentJobsClient";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface AgentJobEventPanelProps {
  /** The job to stream events for.  null = pre-launch; panel shows placeholder. */
  jobId: string | null;
  /** Raw status string from job detail — panel decides enabled based on this. */
  jobStatus: string;
}

// ── Running-status helpers ────────────────────────────────────────────────────

const RUNNING_STATUSES = new Set(["queued", "running", "streaming"]);

/**
 * Known terminal states — stream is closed; accumulated events remain visible.
 * UI-5.7: panel shows a "Stream closed — job {status}" indicator for these.
 */
const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

/**
 * Known non-active pre-run states — the job has not started yet.
 * These are neither "running" nor "terminal" but are explicitly known, so they
 * do NOT fall through to the unknown-status forward-compat path.
 */
const PRE_RUN_STATUSES = new Set(["pending"]);

/**
 * Returns true when the job should have an active SSE connection.
 *
 * Decision table:
 *   RUNNING_STATUSES   (queued, running, streaming) → true  (known active)
 *   TERMINAL_STATUSES  (completed, failed, cancelled) → false (known done)
 *   PRE_RUN_STATUSES   (pending) → false (known not-yet-started)
 *   Anything else      → true   (unknown future status; treat as potentially
 *                                running so the stream is not silently broken)
 *
 * UI-5.7: This forward-compat rule prevents a future "paused" or "interrupted"
 * status from silently stopping event delivery.
 */
function isRunningStatus(status: string): boolean {
  if (RUNNING_STATUSES.has(status)) return true;
  if (TERMINAL_STATUSES.has(status)) return false;
  if (PRE_RUN_STATUSES.has(status)) return false;
  // Unknown status: treat as potentially running.
  return true;
}

/** Returns true when the job has reached a known terminal state. */
function isTerminalStatus(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}

/**
 * Returns true when the status is not in any known set (running, terminal, or
 * pre-run). These are future/unrecognized statuses that get the "(unknown
 * status)" indicator in the panel header (UI-5.7).
 */
function isUnknownStatus(status: string): boolean {
  return (
    !RUNNING_STATUSES.has(status) &&
    !TERMINAL_STATUSES.has(status) &&
    !PRE_RUN_STATUSES.has(status)
  );
}

// ── Payload sanitiser (security defence-in-depth) ────────────────────────────

/**
 * Pattern matching credential-shaped keys that must never appear in the UI.
 * Server already redacts; this is a defence-in-depth layer.
 */
const CREDENTIAL_KEY_RE =
  /token|secret|password|credential|auth(?:ori[sz]ation)?|bearer|api[_-]?key|apikey/i;

const PAYLOAD_SUMMARY_MAX = 120;

/**
 * Produces a short, sanitised summary string of an event payload.
 *
 * - Credential-shaped key values are replaced with "[REDACTED]".
 * - Output is capped at PAYLOAD_SUMMARY_MAX characters.
 * - SECURITY: never log the raw payload — only the sanitised result is
 *   included in rendered output.
 */
function formatPayloadSummary(payload: Record<string, unknown>): string {
  const sanitised: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(payload)) {
    sanitised[k] = CREDENTIAL_KEY_RE.test(k) ? "[REDACTED]" : v;
  }
  const raw = JSON.stringify(sanitised);
  return raw.length > PAYLOAD_SUMMARY_MAX
    ? raw.slice(0, PAYLOAD_SUMMARY_MAX - 3) + "..."
    : raw;
}

// ── Sub-component: single event row ──────────────────────────────────────────

interface EventRowProps {
  event: AgentJobEvent;
  index: number;
}

function EventRow({ event, index }: EventRowProps) {
  // SECURITY: sanitise before rendering; never interpolate raw payload.
  const payloadSummary = formatPayloadSummary(event.payload);
  const rowKey = event.sequence ?? index;

  return (
    <li
      className="rv-event-panel__item"
      data-testid={`agent-event-item-${rowKey}`}
      data-event-type={event.event_type}
    >
      <span
        className="rv-event-panel__item--type"
        data-testid={`agent-event-type-${rowKey}`}
      >
        {event.event_type}
      </span>

      {event.sequence != null && (
        <span
          className="rv-event-panel__item--seq"
          data-testid={`agent-event-seq-${event.sequence}`}
          aria-label={`Sequence ${event.sequence}`}
        >
          #{event.sequence}
        </span>
      )}

      <span
        className="rv-event-panel__item--payload"
        aria-label="Event payload summary"
      >
        {payloadSummary}
      </span>
    </li>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function AgentJobEventPanel({ jobId, jobStatus }: AgentJobEventPanelProps) {
  // Only open an SSE connection when the job is in an active state.
  const enabled = jobId !== null && isRunningStatus(jobStatus);

  const { events, status } = useAgentJobEvents(jobId, enabled);

  // Auto-scroll sentinel — scrolled into view whenever events grow.
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Guard: scrollIntoView may be absent in jsdom/test environments.
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === "function") {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length]);

  // Show the "interrupted" notice when the hook is in error state.
  // The hook handles reconnect internally; we just surface the status.
  const showInterrupted = status === "error";

  // UI-5.7: status-awareness indicators for the panel header.
  const showUnknownStatus = jobId !== null && isUnknownStatus(jobStatus);
  const showTerminal = isTerminalStatus(jobStatus);

  return (
    <div
      className="rv-event-panel"
      data-testid="agent-event-panel"
      data-job-status={jobStatus}
    >
      {/* Panel header: surfaces status indicators for unknown and terminal states */}
      {(showUnknownStatus || showTerminal) && (
        <div className="rv-event-panel__status-bar" data-testid="agent-event-status-bar">
          {showUnknownStatus && (
            <span
              className="rv-event-panel__badge rv-event-panel__badge--unknown"
              data-testid="agent-event-unknown-status"
              role="status"
              aria-label="Job status is not recognized by this viewer version"
            >
              (unknown status)
            </span>
          )}
          {showTerminal && (
            <span
              className="rv-event-panel__badge rv-event-panel__badge--terminal"
              data-testid="agent-event-terminal-status"
              role="status"
              aria-label={`Stream closed — job reached terminal state: ${jobStatus}`}
            >
              Stream closed — job {jobStatus}
            </span>
          )}
        </div>
      )}

      {/*
        ARIA live region is ALWAYS mounted so screen readers pick up events the
        moment they arrive, including the very first one (AC-2.3).
      */}
      <div
        className="rv-event-panel__live"
        aria-live="polite"
        aria-label="Agent job event stream"
        aria-atomic="false"
        data-testid="agent-event-live-region"
      >
        {events.length === 0 ? (
          <p
            className="rv-event-panel__status rv-event-panel__status--waiting"
            data-testid="agent-event-waiting"
          >
            Waiting for events…
          </p>
        ) : (
          <ol
            className="rv-event-panel__list"
            data-testid="agent-event-list"
            aria-label="Agent job event log"
          >
            {events.map((event, index) => (
              <EventRow
                key={`${event.event_type}-${event.sequence ?? index}`}
                event={event}
                index={index}
              />
            ))}
          </ol>
        )}

        {/* Stream-interrupted notice — shown when SSE errors and hook is reconnecting */}
        {showInterrupted && (
          <p
            className="rv-event-panel__status rv-event-panel__status--interrupted"
            role="status"
            data-testid="agent-event-interrupted"
          >
            Stream interrupted — reconnecting…
          </p>
        )}
      </div>

      {/* Scroll anchor — always after the live region */}
      <div ref={bottomRef} aria-hidden="true" className="rv-event-panel__scroll-anchor" />
    </div>
  );
}
