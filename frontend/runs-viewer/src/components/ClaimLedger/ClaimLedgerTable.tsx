/**
 * ClaimLedgerTable — tabular view of all clm_NNN ledger entries.
 *
 * Each row:
 *   - id="clm_NNN" anchor for deep-link from VerificationChecklist
 *   - claim text (truncated with full text on title)
 *   - status badge (supported/inference/speculation/…)
 *   - confidence badge (low/medium/high)
 *   - materiality badge (core/background/style/material)
 *   - clinical-attestation badge (clearance-gates-v1 M4; "unattested" only,
 *     present when the claim is clinically eligible per the backend's
 *     claim_clinical_eligibility() heuristic)
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
  /** Called when the user double-clicks a claim row; opens DetailModal with the claim payload. */
  onExpandClaim?: (claimId: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ClaimLedgerTable({ claims, onClaimSelect, selectedClaimId, onExpandClaim }: ClaimLedgerTableProps) {
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
            <th className="rv-ledger-th rv-ledger-th--terms">Terms</th>
            <th className="rv-ledger-th rv-ledger-th--clinical">Clinical</th>
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
            // Schema 1.7 (TASK-2.1): _term_index is OMITTED ENTIRELY (not
            // null/empty) for legacy claims and claims with zero vocabulary
            // hits — terms stays [] and the cell below renders nothing, per
            // AC "a claim with no _term_index renders no badge".
            const termIndex = claim._term_index;
            const terms = termIndex?.terms ?? [];

            return (
              <tr
                key={claim.claim_id}
                id={claim.claim_id}
                className={`rv-ledger-row${isSelected ? " rv-ledger-row--selected" : ""}`}
                data-testid={`ledger-row-${claim.claim_id}`}
                data-claim-id={claim.claim_id}
                data-status={claim.status}
                onClick={() => onClaimSelect(claim.claim_id)}
                onDoubleClick={() => onExpandClaim?.(claim.claim_id)}
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

                {/*
                  Term/usage-role badge (D2/FR-15 namespace-boundary
                  requirement): deliberately NOT `.it-chip` (the solid-fill
                  pill used by every status/confidence/materiality badge
                  above, and the pattern any future real `pediatric_cds`
                  structured-threshold display would use) — a dashed
                  outline, transparent fill, monospace "#term" glyph in its
                  own dedicated column so it can never visually merge with
                  or be mistaken for an attested clinical value.
                */}
                <td className="rv-ledger-td rv-ledger-td--terms" data-testid={`ledger-terms-${claim.claim_id}`}>
                  {terms.length > 0 && (
                    <div className="rv-ledger-term-badges">
                      {terms.map((term) => {
                        const role = termIndex?.usage_roles[term];
                        return (
                          <span
                            key={term}
                            className="rv-ledger-term-badge"
                            data-testid={`ledger-term-${claim.claim_id}-${term}`}
                            title={`Derived vocabulary term — non-authoritative, not an attested clinical threshold${role ? ` (usage role: ${role})` : ""}`}
                          >
                            <span className="rv-ledger-term-badge__mark" aria-hidden="true">#</span>
                            {term}
                            {role && <span className="rv-ledger-term-badge__role">{role}</span>}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </td>

                {/*
                  Clinical-attestation badge (clearance-gates-v1 M4).
                  Present only when the backend's clinical_attestation_status
                  is "unattested" -- the ONLY value it can ever hold today
                  (RF has no counsel/attestation workflow). Deliberately
                  reuses the dashed/monospace, non-`.it-chip` convention the
                  term badge above establishes -- with its own amber/caution
                  styling -- so it can never be mistaken for an attested
                  clinical value while still clearly signalling "pay
                  attention here", unlike the neutral term badge.
                */}
                <td className="rv-ledger-td rv-ledger-td--clinical" data-testid={`ledger-clinical-${claim.claim_id}`}>
                  {claim.clinical_attestation_status === "unattested" && (
                    <span
                      className="rv-ledger-clinical-badge"
                      data-testid={`ledger-clinical-badge-${claim.claim_id}`}
                      title="Clinical content — viewable and rule-buildable locally, but not attested for clinical reliance"
                    >
                      <span className="rv-ledger-clinical-badge__mark" aria-hidden="true">⚕</span>
                      unattested
                    </span>
                  )}
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
