/**
 * CompositionSidebar — claim composition panel for ReportOverlay.
 *
 * Shows % supported / % inference / % speculation from evidence_bundle.counts
 * (claim_counts in the run export).
 *
 * Clicking a category:
 *   - activates a single-category filter
 *   - the active set of dimmedClaimIds is computed from that category
 *   - ReportRenderer dims non-matching chips via the dimmedClaimIds prop
 *
 * Clicking the same category again resets the filter.
 */

import { useState } from "react";
import type { RFClaimCounts, RFClaim } from "@/types/rf";

// ── Types ─────────────────────────────────────────────────────────────────────

export type CompositionFilter = "supported" | "inference" | "speculation" | null;

export interface CompositionSidebarProps {
  claimCounts:   RFClaimCounts | null | undefined;
  claims:        RFClaim[];
  /** Called when filter changes; parent passes dimmedClaimIds to ReportRenderer. */
  onFilterChange?: (activeClaimIds: Set<string> | null) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CompositionSidebar({ claimCounts, claims, onFilterChange }: CompositionSidebarProps) {
  const [activeFilter, setActiveFilter] = useState<CompositionFilter>(null);

  const total      = claimCounts?.total ?? claimCounts?.claims_total ?? 0;
  const supported  = claimCounts?.supported  ?? claimCounts?.claims_supported  ?? 0;
  const inference  = claimCounts?.inference  ?? claimCounts?.claims_inference  ?? 0;
  const speculation = claimCounts?.speculation ?? claimCounts?.claims_speculation ?? 0;

  const pct = (n: number) =>
    total > 0 ? `${Math.round((n / total) * 100)}%` : "0%";

  function handleFilterClick(filter: CompositionFilter) {
    const next = activeFilter === filter ? null : filter;
    setActiveFilter(next);

    if (!next) {
      onFilterChange?.(null);
      return;
    }

    // Compute the set of claim IDs that match the filter status
    const matchingIds = new Set<string>(
      claims
        .filter((c) => c.status === next)
        .map((c) => c.claim_id)
    );
    onFilterChange?.(matchingIds);
  }

  return (
    <div className="rv-comp-sidebar" data-testid="composition-sidebar">
      <h3 className="rv-comp-sidebar__title">Composition</h3>

      {total === 0 ? (
        <p className="rv-comp-sidebar__empty">No claim data available.</p>
      ) : (
        <div className="rv-comp-sidebar__items">
          {/* Supported */}
          <button
            type="button"
            className={`rv-comp-item rv-comp-item--supported${activeFilter === "supported" ? " rv-comp-item--active" : ""}`}
            data-testid="comp-item-supported"
            data-filter="supported"
            data-active={activeFilter === "supported" ? "true" : "false"}
            onClick={() => handleFilterClick("supported")}
            aria-pressed={activeFilter === "supported"}
          >
            <div className="rv-comp-item__bar-bg">
              <div
                className="rv-comp-item__bar-fill rv-comp-item__bar-fill--supported"
                style={{ width: pct(supported) }}
              />
            </div>
            <div className="rv-comp-item__labels">
              <span className="rv-comp-item__label">Supported</span>
              <span className="rv-comp-item__pct" data-testid="comp-pct-supported">
                {pct(supported)}
              </span>
              <span className="rv-comp-item__count" data-testid="comp-count-supported">
                {supported}/{total}
              </span>
            </div>
          </button>

          {/* Inference */}
          <button
            type="button"
            className={`rv-comp-item rv-comp-item--inference${activeFilter === "inference" ? " rv-comp-item--active" : ""}`}
            data-testid="comp-item-inference"
            data-filter="inference"
            data-active={activeFilter === "inference" ? "true" : "false"}
            onClick={() => handleFilterClick("inference")}
            aria-pressed={activeFilter === "inference"}
          >
            <div className="rv-comp-item__bar-bg">
              <div
                className="rv-comp-item__bar-fill rv-comp-item__bar-fill--inference"
                style={{ width: pct(inference) }}
              />
            </div>
            <div className="rv-comp-item__labels">
              <span className="rv-comp-item__label">Inference</span>
              <span className="rv-comp-item__pct" data-testid="comp-pct-inference">
                {pct(inference)}
              </span>
              <span className="rv-comp-item__count" data-testid="comp-count-inference">
                {inference}/{total}
              </span>
            </div>
          </button>

          {/* Speculation */}
          <button
            type="button"
            className={`rv-comp-item rv-comp-item--speculation${activeFilter === "speculation" ? " rv-comp-item--active" : ""}`}
            data-testid="comp-item-speculation"
            data-filter="speculation"
            data-active={activeFilter === "speculation" ? "true" : "false"}
            onClick={() => handleFilterClick("speculation")}
            aria-pressed={activeFilter === "speculation"}
          >
            <div className="rv-comp-item__bar-bg">
              <div
                className="rv-comp-item__bar-fill rv-comp-item__bar-fill--speculation"
                style={{ width: pct(speculation) }}
              />
            </div>
            <div className="rv-comp-item__labels">
              <span className="rv-comp-item__label">Speculation</span>
              <span className="rv-comp-item__pct" data-testid="comp-pct-speculation">
                {pct(speculation)}
              </span>
              <span className="rv-comp-item__count" data-testid="comp-count-speculation">
                {speculation}/{total}
              </span>
            </div>
          </button>
        </div>
      )}

      {/* Reset hint */}
      {activeFilter && (
        <button
          type="button"
          className="it-btn ghost xs rv-comp-sidebar__reset"
          data-testid="comp-filter-reset"
          onClick={() => handleFilterClick(null)}
        >
          Reset filter
        </button>
      )}

      {/* Total */}
      {total > 0 && (
        <p className="rv-comp-sidebar__total" data-testid="comp-total">
          {total} total claims
        </p>
      )}
    </div>
  );
}

export default CompositionSidebar;
