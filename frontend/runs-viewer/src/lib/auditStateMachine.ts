/**
 * auditStateMachine — pure derivation function for the Audit tab highlight/filter state machine.
 *
 * Four states (per Feature Contract §5.1):
 *   none              — no facets active, no claim selected
 *   composition       — facets active, no claim selected → composition highlight in report
 *   selected-claim    — a claim row is selected (facets may or may not be active)
 *   (deselect-to-composition is a transition, not a stable state)
 *
 * This function is intentionally pure so that it can be unit-tested without React.
 */

import type { RFClaim } from "@/types/rf";
import type { LedgerFacetState } from "@/components/ClaimLedger/LedgerFacets";

// Re-export for consumers (avoids importing from ReportRenderer internals)
export type HighlightMode = "none" | "composition" | "selected-claim";

export interface AuditHighlightState {
  highlightMode:  HighlightMode;
  activeClaimIds: Set<string>;
  highlightText:  boolean;
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
 * Derives the highlight state for ReportRenderer from the two independent state variables.
 *
 * @param activeFacets     Current LedgerFacetState (all empty Sets when no facets active)
 * @param selectedClaimId  Currently selected claim row ID, or null
 * @param claims           Full unfiltered claims array from the run export
 * @returns AuditHighlightState — { highlightMode, activeClaimIds, highlightText }
 */
export function deriveAuditHighlight(
  activeFacets:    LedgerFacetState,
  selectedClaimId: string | null,
  claims:          RFClaim[],
): AuditHighlightState {
  // State: selected-claim — takes precedence over facets
  if (selectedClaimId !== null) {
    return {
      highlightMode:  "selected-claim",
      activeClaimIds: new Set([selectedClaimId]),
      highlightText:  true,
    };
  }

  const facetsActive = !isFacetEmpty(activeFacets);

  // State: composition — facets active, no claim selected
  if (facetsActive) {
    return {
      highlightMode:  "composition",
      activeClaimIds: deriveMatchedClaimIds(claims, activeFacets),
      highlightText:  false,
    };
  }

  // State: none — no facets, no selection
  return {
    highlightMode:  "none",
    activeClaimIds: new Set(),
    highlightText:  false,
  };
}
