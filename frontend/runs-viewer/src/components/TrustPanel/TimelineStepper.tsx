/**
 * TimelineStepper — renders stage events from telemetry/run_trace.jsonl.
 *
 * Shows a vertical step list from the timeline array. Each event has a
 * timestamp, event type, and optional detail. Empty-state when timeline absent.
 */

import type { RFTimelineEvent } from "@/types/rf";

function formatTs(ts: string | undefined): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function humanizeEvent(event: string | undefined): string {
  if (!event) return "Event";
  return event
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface TimelineStepperProps {
  timeline: RFTimelineEvent[] | null | undefined;
}

export function TimelineStepper({ timeline }: TimelineStepperProps) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="rv-timeline rv-timeline--empty" data-testid="timeline-empty">
        <p className="rv-timeline__empty-msg">No timeline data available.</p>
      </div>
    );
  }

  return (
    <div className="rv-timeline" data-testid="timeline-stepper">
      <ol className="rv-timeline__list" role="list">
        {timeline.map((evt, idx) => (
          <li key={`${evt.ts ?? ""}-${idx}`} className="rv-timeline__step" data-testid="timeline-step">
            <span className="rv-timeline__dot" aria-hidden="true" />
            <div className="rv-timeline__body">
              <span className="rv-timeline__event-name">
                {humanizeEvent(evt.event)}
              </span>
              {evt.ts && (
                <span className="rv-timeline__ts">{formatTs(evt.ts)}</span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default TimelineStepper;
