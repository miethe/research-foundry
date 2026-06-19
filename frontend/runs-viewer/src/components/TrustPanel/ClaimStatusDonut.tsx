/**
 * ClaimStatusDonut — SVG donut chart showing claim status distribution.
 *
 * Renders three arcs from evidence_bundle.counts:
 *   - supported (green)
 *   - inference (blue)
 *   - speculation (orange)
 *
 * Empty-state: when evidence_bundle / counts is absent, renders a "No claims
 * data" placeholder (never crashes).
 *
 * This is a pure CSS+SVG donut — no charting library dependency.
 */

import type { RFClaimCounts } from "@/types/rf";

// ── SVG donut helpers ─────────────────────────────────────────────────────────

const R = 40;           // circle radius
const CX = 50;          // center x
const CY = 50;          // center y
// Circumference not used directly; arc drawing handled by describeArc path function
const STROKE_WIDTH = 14;

interface ArcSpec {
  label: string;
  value: number;
  colorClass: string;
  stroke: string;
}

function polarToXY(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
): string {
  // Clamp to avoid full-circle SVG path edge case
  const clampedEnd = Math.min(endAngle, startAngle + 359.999);
  const start = polarToXY(cx, cy, r, startAngle);
  const end = polarToXY(cx, cy, r, clampedEnd);
  const largeArc = clampedEnd - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface ClaimStatusDonutProps {
  /** claim_counts from the run export. May be null when evidence_bundle absent. */
  claimCounts: RFClaimCounts | null | undefined;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ClaimStatusDonut({ claimCounts }: ClaimStatusDonutProps) {
  // Empty-state
  if (!claimCounts) {
    return (
      <div className="rv-donut rv-donut--empty" data-testid="claim-donut-empty">
        <p className="rv-donut__empty-msg">No claims data.</p>
      </div>
    );
  }

  const supported   = claimCounts.supported   ?? claimCounts.claims_supported   ?? 0;
  const inference   = claimCounts.inference   ?? claimCounts.claims_inference   ?? 0;
  const speculation = claimCounts.speculation ?? claimCounts.claims_speculation ?? 0;
  const total       = claimCounts.total       ?? claimCounts.claims_total       ??
                      (supported + inference + speculation);

  // Empty-state when all zeros
  if (total === 0) {
    return (
      <div className="rv-donut rv-donut--empty" data-testid="claim-donut-empty">
        <p className="rv-donut__empty-msg">No claims data.</p>
      </div>
    );
  }

  const arcs: ArcSpec[] = [
    {
      label:      "Supported",
      value:      supported,
      colorClass: "rv-donut-arc--supported",
      stroke:     "var(--it-green-500)",
    },
    {
      label:      "Inference",
      value:      inference,
      colorClass: "rv-donut-arc--inference",
      stroke:     "var(--it-blue-500)",
    },
    {
      label:      "Speculation",
      value:      speculation,
      colorClass: "rv-donut-arc--speculation",
      stroke:     "var(--it-orange-500)",
    },
  ];

  // Build arc segments
  let currentAngle = 0;
  const segments = arcs.map((arc) => {
    const fraction = arc.value / total;
    const sweepAngle = fraction * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + sweepAngle;
    currentAngle = endAngle;
    return { ...arc, startAngle, endAngle, fraction, sweepAngle };
  });

  return (
    <div className="rv-donut" data-testid="claim-donut">
      {/* SVG donut */}
      <div className="rv-donut__chart">
        <svg
          viewBox="0 0 100 100"
          width="96"
          height="96"
          aria-hidden="true"
        >
          {/* Track */}
          <circle
            cx={CX}
            cy={CY}
            r={R}
            fill="none"
            stroke="var(--it-neutral-100)"
            strokeWidth={STROKE_WIDTH}
          />
          {/* Arcs */}
          {segments.map((seg) => {
            if (seg.value === 0) return null;
            const d = describeArc(CX, CY, R, seg.startAngle, seg.endAngle);
            return (
              <path
                key={seg.label}
                d={d}
                fill="none"
                stroke={seg.stroke}
                strokeWidth={STROKE_WIDTH}
                strokeLinecap="butt"
                className={seg.colorClass}
                data-testid={`donut-arc-${seg.label.toLowerCase()}`}
              />
            );
          })}
          {/* Center label */}
          <text
            x={CX}
            y={CY - 4}
            textAnchor="middle"
            dominantBaseline="middle"
            className="rv-donut__center-value"
            fontSize="16"
            fontWeight="600"
            fill="var(--it-text-primary)"
          >
            {total}
          </text>
          <text
            x={CX}
            y={CY + 10}
            textAnchor="middle"
            dominantBaseline="middle"
            className="rv-donut__center-label"
            fontSize="9"
            fill="var(--it-text-tertiary)"
          >
            claims
          </text>
        </svg>
      </div>

      {/* Legend */}
      <ul className="rv-donut__legend" aria-label="Claim status breakdown">
        {arcs.map((arc) => (
          <li key={arc.label} className="rv-donut__legend-item">
            <span
              className={`rv-donut__legend-dot ${arc.colorClass}`}
              aria-hidden="true"
            />
            <span className="rv-donut__legend-label">{arc.label}</span>
            <span className="rv-donut__legend-count" data-testid={`donut-count-${arc.label.toLowerCase()}`}>
              {arc.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ClaimStatusDonut;
