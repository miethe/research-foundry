/**
 * ClaimLedgerTable — tabular view of all clm_NNN ledger entries.
 *
 * Each row:
 *   - id="clm_NNN" anchor for deep-link from VerificationChecklist
 *   - claim text (truncated with full text on title)
 *   - status badge (supported/inference/speculation/…)
 *   - confidence badge (low/medium/high)
 *   - materiality badge (core/background/style/material)
 *   - row click → onClaimSelect(claimId)
 *
 * Accepts a filtered claim array from LedgerFacets.
 * No external deps beyond design tokens + .rv-* CSS.
 */

import type { RFClaim, RFClaimStatus, RFClaimConfidence, RFMateriality } from "@/types/rf";

// ── Badge maps ────────────────────────────────────────────────────────────────

const STATUS_CHIP: Record<RFClaimStatus, string> = {
  supported:    "green",
  mixed:        "gold",
  contradicted: "red",
  inference:    "blue",
  speculation:  "orange",
  unsupported:  "red",
};

const STATUS_LABEL: Record<RFClaimStatus, string> = {
  supported:    "Supported",
  mixed:        "Mixed",
  contradicted: "Contradicted",
  inference:    "Inference",
  speculation:  "Speculation",
  unsupported:  "Unsupported",
};

const CONFIDENCE_CHIP: Record<RFClaimConfidence, string> = {
  low:    "orange",
  medium: "gold",
  high:   "green",
};

const MATERIALITY_CHIP: Record<RFMateriality, string> = {
  core:       "blue",
  material:   "blue",
  background: "",
  style:      "",
};

const MATERIALITY_LABEL: Record<RFMateriality, string> = {
  core:       "Core",
  material:   "Material",
  background: "Background",
  style:      "Style",
};

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ClaimLedgerTableProps {
  claims:         RFClaim[];
  onClaimSelect:  (claimId: string) => void;
  selectedClaimId?: string | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ClaimLedgerTable({ claims, onClaimSelect, selectedClaimId }: ClaimLedgerTableProps) {
  if (claims.length === 0) {
    return (
      <div className="rv-ledger-empty" data-testid="ledger-empty">
        <p className="rv-ledger-empty__msg">No claims match the current filters.</p>
      </div>
    );
  }

  return (
    <div className="rv-ledger-table-wrapper" data-testid="ledger-table">
      <table className="rv-ledger-table" role="grid" aria-label="Claim ledger">
        <thead>
          <tr>
            <th className="rv-ledger-th rv-ledger-th--id">Claim ID</th>
            <th className="rv-ledger-th rv-ledger-th--text">Claim Text</th>
            <th className="rv-ledger-th rv-ledger-th--status">Status</th>
            <th className="rv-ledger-th rv-ledger-th--conf">Confidence</th>
            <th className="rv-ledger-th rv-ledger-th--mat">Materiality</th>
            <th className="rv-ledger-th rv-ledger-th--sources">Sources</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => {
            const statusChip  = claim.status ? STATUS_CHIP[claim.status]  ?? "" : "";
            const statusLabel = claim.status ? STATUS_LABEL[claim.status] ?? claim.status : "—";
            const confChip    = claim.confidence ? CONFIDENCE_CHIP[claim.confidence] ?? "" : "";
            const matChip     = claim.materiality ? MATERIALITY_CHIP[claim.materiality] ?? "" : "";
            const matLabel    = claim.materiality ? MATERIALITY_LABEL[claim.materiality] ?? claim.materiality : "—";
            const isSelected  = selectedClaimId === claim.claim_id;

            return (
              <tr
                key={claim.claim_id}
                id={claim.claim_id}
                className={`rv-ledger-row${isSelected ? " rv-ledger-row--selected" : ""}`}
                data-testid={`ledger-row-${claim.claim_id}`}
                data-claim-id={claim.claim_id}
                data-status={claim.status}
                onClick={() => onClaimSelect(claim.claim_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onClaimSelect(claim.claim_id);
                  }
                }}
                tabIndex={0}
                role="row"
                aria-selected={isSelected}
              >
                {/* Claim ID */}
                <td className="rv-ledger-td rv-ledger-td--id">
                  <code className="rv-ledger-claim-id">{claim.claim_id}</code>
                </td>

                {/* Claim text (truncated) */}
                <td className="rv-ledger-td rv-ledger-td--text">
                  <span
                    className="rv-ledger-text"
                    title={claim.text}
                  >
                    {claim.text.length > 120
                      ? `${claim.text.slice(0, 120)}…`
                      : claim.text}
                  </span>
                </td>

                {/* Status badge */}
                <td className="rv-ledger-td rv-ledger-td--status">
                  <span
                    className={`it-chip ${statusChip} rv-ledger-badge`}
                    data-testid={`ledger-status-${claim.claim_id}`}
                  >
                    {statusLabel}
                  </span>
                </td>

                {/* Confidence badge */}
                <td className="rv-ledger-td rv-ledger-td--conf">
                  {claim.confidence ? (
                    <span
                      className={`it-chip ${confChip} rv-ledger-badge`}
                      data-testid={`ledger-confidence-${claim.claim_id}`}
                    >
                      {claim.confidence}
                    </span>
                  ) : (
                    <span className="rv-ledger-dash">—</span>
                  )}
                </td>

                {/* Materiality badge */}
                <td className="rv-ledger-td rv-ledger-td--mat">
                  {claim.materiality ? (
                    <span
                      className={`it-chip ${matChip} rv-ledger-badge`}
                      data-testid={`ledger-materiality-${claim.claim_id}`}
                    >
                      {matLabel}
                    </span>
                  ) : (
                    <span className="rv-ledger-dash">—</span>
                  )}
                </td>

                {/* Source count */}
                <td className="rv-ledger-td rv-ledger-td--sources">
                  <span className="rv-ledger-source-count" data-testid={`ledger-sources-${claim.claim_id}`}>
                    {claim.sources.length}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default ClaimLedgerTable;
