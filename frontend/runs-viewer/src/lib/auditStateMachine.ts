/**
 * auditStateMachine — pure derivation function for the Audit tab highlight/filter state machine.
 *
 * Six states (per Feature Contract §5.1, extended by P2 Wave C for report_anchors):
 *   none               — no facets active, no claim/paragraph selected, no anchor filters
 *   composition        — facets active, no claim selected → composition highlight in report
 *   selected-claim      — a claim row is selected (facets may or may not be active)
 *   selected-paragraph — a report paragraph (anchor block_id) is selected (P2 Wave C)
 *   anchor-filter      — one or more anchor coverage filters active, no selection (P2 Wave C)
 *   (deselect-to-composition is a transition, not a stable state)
 *
 * P2 Wave C EXTENDS this state machine (does not replace it): the new
 * anchor-derived states are additive and only reachable via the optional
 * 4th `anchorState` argument. Every existing call site with 3 positional
 * arguments (facets, selectedClaimId, claims) is unaffected — anchorState
 * defaults to undefined, which never triggers the new branches.
 *
 * This function is intentionally pure so that it can be unit-tested without React.
 */

import type { RFClaim, RFReportAnchorBlock } from "@/types/rf";
import type { LedgerFacetState } from "@/components/ClaimLedger/LedgerFacets";
import { computeAnchorFilterMatches, computeBlockCoverage } from "./reportAnchors";
import type { AnchorFilterKey } from "./reportAnchors";

export type { AnchorFilterKey } from "./reportAnchors";

// Re-export for consumers (avoids importing from ReportRenderer internals)
export type HighlightMode = "none" | "composition" | "selected-claim" | "selected-paragraph" | "anchor-filter";

export interface AuditHighlightState {
  highlightMode:  HighlightMode;
  activeClaimIds: Set<string>;
  highlightText:  boolean;
  /**
   * P2 Wave C — the block_id highlighted directly in "selected-paragraph"
   * mode, independent of whether the paragraph has any resolved claim links
   * (an unsupported paragraph with zero claim_links must still highlight).
   * Undefined in all pre-existing modes.
   */
  selectedBlockId?: string | null;
  /**
   * P2 Wave C — block_ids matching the active anchor filter set in
   * "anchor-filter" mode. Undefined in all pre-existing modes; a defined
   * (possibly empty) Set signals ReportRenderer to prefer block-based
   * highlighting over claim-id text matching.
   */
  activeBlockIds?: Set<string>;
}

/**
 * P2 Wave C — optional paragraph/anchor-filter input, additive to the
 * existing (facets, selectedClaimId, claims) signature. `anchors` mirrors
 * `run.report_anchors`: absent/null means legacy mode (D9) — none of the
 * new states are derivable and deriveAuditHighlight behaves exactly as
 * before.
 */
export interface AuditAnchorState {
  /** Currently selected paragraph's block_id, or null. Precedence: below selectedClaimId, above facets/anchorFilters. */
  selectedBlockId: string | null;
  /** Active anchor coverage filters — independent of LedgerFacets' claim-level status facet. */
  anchorFilters:   Set<AnchorFilterKey>;
  anchors:         RFReportAnchorBlock[] | null | undefined;
}

/**
 * Returns true when all dimensions in a LedgerFacetState are empty (no facets active).
 */
export function isFacetEmpty(facets: LedgerFacetState): boolean {
  return (
    facets.status.size      === 0 &&
    facets.materiality.size === 0 &&
    facets.claim_type.size  === 0 &&
    facets.confidence.size  === 0
  );
}

/**
 * Derives the matched claim-ID union from the full claims list + current facet state.
 * Mirrors the AND-filter logic in LedgerFacets.applyFacets so the union is consistent
 * with the left-table filtering, without requiring a second call through LedgerFacets.
 */
export function deriveMatchedClaimIds(claims: RFClaim[], facets: LedgerFacetState): Set<string> {
  if (!claims || claims.length === 0) return new Set();
  if (isFacetEmpty(facets)) return new Set();

  const ids = new Set<string>();
  for (const c of claims) {
    let pass = true;
    if (facets.status.size      > 0 && !facets.status.has(c.status ?? ""))           pass = false;
    if (facets.materiality.size > 0 && !facets.materiality.has(c.materiality ?? "")) pass = false;
    if (facets.claim_type.size  > 0 && !facets.claim_type.has(c.claim_type ?? ""))   pass = false;
    if (facets.confidence.size  > 0 && !facets.confidence.has(c.confidence ?? ""))   pass = false;
    if (pass) ids.add(c.claim_id);
  }
  return ids;
}

/**
 * Derives the highlight state for ReportRenderer from the independent state variables.
 *
 * Precedence (highest to lowest): selected-claim > selected-paragraph >
 * composition (facets) > anchor-filter > none. In practice the UI keeps
 * claim selection and paragraph selection mutually exclusive (selecting one
 * clears the other), so this ordering rarely matters in practice — it exists
 * so the function never produces an ambiguous/undefined result.
 *
 * @param activeFacets     Current LedgerFacetState (all empty Sets when no facets active)
 * @param selectedClaimId  Currently selected claim row ID, or null
 * @param claims           Full unfiltered claims array from the run export
 * @param anchorState      P2 Wave C (optional) — paragraph selection + anchor filters.
 *                         Omit entirely for legacy/pre-1.4-export callers.
 * @returns AuditHighlightState — { highlightMode, activeClaimIds, highlightText, ... }
 */
export function deriveAuditHighlight(
  activeFacets:    LedgerFacetState,
  selectedClaimId: string | null,
  claims:          RFClaim[],
  anchorState?:    AuditAnchorState,
): AuditHighlightState {
  // State: selected-claim — takes precedence over everything else
  if (selectedClaimId !== null) {
    return {
      highlightMode:  "selected-claim",
      activeClaimIds: new Set([selectedClaimId]),
      highlightText:  true,
    };
  }

  // State: selected-paragraph (P2 Wave C) — a report paragraph is selected.
  // Highlights by block_id directly (not by claim membership) so an
  // anchored paragraph with ZERO claim_links (e.g. "citation needed") still
  // highlights correctly; activeClaimIds is populated too so the paragraph's
  // OWN claim chips also render as active (not dimmed) via the existing
  // claim-id text-matching path in ReportRenderer.
  if (anchorState?.anchors != null && anchorState.selectedBlockId !== null) {
    const block = anchorState.anchors.find((b) => b.block_id === anchorState.selectedBlockId);
    const claimIds = new Set<string>(
      (block?.claim_links ?? [])
        .filter((link) => link.link_status !== "missing_claim")
        .map((link) => link.claim_id),
    );
    return {
      highlightMode:    "selected-paragraph",
      activeClaimIds:   claimIds,
      highlightText:    true,
      selectedBlockId:  anchorState.selectedBlockId,
      activeBlockIds:   new Set([anchorState.selectedBlockId]),
    };
  }

  const facetsActive = !isFacetEmpty(activeFacets);

  // State: composition — facets active, no claim/paragraph selected
  if (facetsActive) {
    return {
      highlightMode:  "composition",
      activeClaimIds: deriveMatchedClaimIds(claims, activeFacets),
      highlightText:  false,
    };
  }

  // State: anchor-filter (P2 Wave C) — coverage filters active, no selection.
  if (anchorState?.anchors != null && anchorState.anchorFilters.size > 0) {
    const coverage = computeBlockCoverage(anchorState.anchors, claims);
    const { blockIds, claimIds } = computeAnchorFilterMatches(coverage, anchorState.anchorFilters);
    return {
      highlightMode:  "anchor-filter",
      activeClaimIds: claimIds,
      highlightText:  true,
      activeBlockIds: blockIds,
    };
  }

  // State: none — no facets, no selection, no anchor filters
  return {
    highlightMode:  "none",
    activeClaimIds: new Set(),
    highlightText:  false,
  };
}
