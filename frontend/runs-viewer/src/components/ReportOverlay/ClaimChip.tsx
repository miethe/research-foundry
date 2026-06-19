/**
 * ClaimChip — inline interactive chip for [claim:clm_NNN] report citations.
 *
 * Clicking the chip fires onClaimSelect(claimId) which opens ProvenanceModal.
 * If claimId is not found in the known ledger, renders a disabled chip with
 * a "Claim not found" title tooltip.
 *
 * `dimmed` prop: set by CompositionSidebar filter to dim non-matching chips.
 */

import type { RFClaim } from "@/types/rf";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ClaimChipProps {
  claimId:       string;
  claims:        RFClaim[];
  onClaimSelect: (claimId: string) => void;
  dimmed?:       boolean;
  selected?:     boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ClaimChip({ claimId, claims, onClaimSelect, dimmed = false, selected = false }: ClaimChipProps) {
  const claim = claims.find((c) => c.claim_id === claimId);

  // Determine chip color by status
  const statusColor: Record<string, string> = {
    supported:    "green",
    inference:    "blue",
    speculation:  "orange",
    mixed:        "gold",
    contradicted: "red",
    unsupported:  "red",
  };
  const chipColor = claim?.status ? statusColor[claim.status] ?? "" : "";

  if (!claim) {
    return (
      <span
        className="rv-claim-chip rv-claim-chip--missing"
        data-testid={`claim-chip-${claimId}`}
        data-claim-id={claimId}
        title="Claim not found in ledger"
        aria-disabled="true"
      >
        {claimId}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`rv-claim-chip it-chip ${chipColor}${dimmed ? " rv-claim-chip--dimmed" : ""}${selected ? " rv-claim-chip--selected" : ""}`}
      data-testid={`claim-chip-${claimId}`}
      data-claim-id={claimId}
      data-status={claim.status}
      data-dimmed={dimmed ? "true" : "false"}
      data-selected={selected ? "true" : "false"}
      aria-pressed={selected}
      title={`Claim ${claimId}: ${claim.text.slice(0, 80)}…`}
      onClick={() => onClaimSelect(claimId)}
    >
      {claimId}
    </button>
  );
}

export default ClaimChip;
