/**
 * ProvenanceModal — two-click claim audit modal (W1 flagship).
 *
 * Click 1: row/chip click → onClaimSelect(claimId) → modal opens with claim data
 * Click 2: expand source card → verbatim quote visible
 *
 * The modal resolves claim data from the parent's claims[] array (passed in as prop).
 * No additional fetch — all data is pre-joined in the run.json export.
 *
 * AC P4-MODAL-1: ≤2 UI interactions from ledger row to verbatim quote.
 * AC P4-MODAL-2: inference claim with empty from_claims=[] → RIB-018 warning.
 *
 * Exposed API (ref pattern):
 *   const modalRef = useRef<ProvenanceModalHandle>(null);
 *   modalRef.current?.open(claimId);
 *   modalRef.current?.close();
 */

import { useState, useCallback, forwardRef, useImperativeHandle } from "react";
import type { RFClaim } from "@/types/rf";
import { SourceCard } from "@/components/SourceCard/SourceCard";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProvenanceModalHandle {
  open:  (claimId: string) => void;
  close: () => void;
}

export interface ProvenanceModalProps {
  claims:        RFClaim[];
  /** Called when a from_claims chain link is clicked — opens the referenced claim. */
  onChainClick?: (claimId: string) => void;
}

// ── Status chip map (mirrors ClaimLedgerTable) ────────────────────────────────

const STATUS_CHIP: Record<string, string> = {
  supported:    "green",
  mixed:        "gold",
  contradicted: "red",
  inference:    "blue",
  speculation:  "orange",
  unsupported:  "red",
};

// ── Component ─────────────────────────────────────────────────────────────────

export const ProvenanceModal = forwardRef<ProvenanceModalHandle, ProvenanceModalProps>(
  function ProvenanceModal({ claims, onChainClick }, ref) {
    const [openClaimId, setOpenClaimId] = useState<string | null>(null);

    const open  = useCallback((claimId: string) => setOpenClaimId(claimId), []);
    const close = useCallback(() => setOpenClaimId(null), []);

    useImperativeHandle(ref, () => ({ open, close }), [open, close]);

    // Close on Escape key or overlay click
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
      if (e.key === "Escape") close();
    }, [close]);

    if (!openClaimId) return null;

    const claim = claims.find((c) => c.claim_id === openClaimId);

    return (
      /* ── Overlay ── */
      <div
        className="rv-modal-overlay"
        data-testid="provenance-modal-overlay"
        onClick={(e) => { if (e.target === e.currentTarget) close(); }}
        onKeyDown={handleKeyDown}
        role="presentation"
      >
        <div
          className="rv-modal"
          role="dialog"
          aria-modal="true"
          aria-label={`Provenance for ${openClaimId}`}
          data-testid="provenance-modal"
          data-claim-id={openClaimId}
        >
          {/* ── Modal header ── */}
          <div className="rv-modal__header">
            <div className="rv-modal__title-row">
              <code className="rv-modal__claim-id">{openClaimId}</code>
              {claim?.status && (
                <span
                  className={`it-chip ${STATUS_CHIP[claim.status] ?? ""} rv-modal__status`}
                  data-testid="modal-status-badge"
                >
                  {claim.status}
                </span>
              )}
              {claim?.confidence && (
                <span className="it-chip rv-modal__confidence" data-testid="modal-confidence-badge">
                  {claim.confidence} confidence
                </span>
              )}
            </div>
            <button
              type="button"
              className="it-btn ghost sm rv-modal__close"
              data-testid="modal-close"
              onClick={close}
              aria-label="Close provenance modal"
            >
              ✕
            </button>
          </div>

          {/* ── Claim not found in claims array ── */}
          {!claim ? (
            <div className="rv-modal__body">
              <p className="rv-modal__not-found" data-testid="modal-claim-not-found">
                Claim <code>{openClaimId}</code> not found in the ledger.
              </p>
            </div>
          ) : (
            <div className="rv-modal__body" data-testid="modal-body">

              {/* ── Claim text ── */}
              <div className="rv-modal__claim-text" data-testid="modal-claim-text">
                <p>{claim.text}</p>
              </div>

              {/* ── Materiality / claim type metadata ── */}
              {(claim.materiality || claim.claim_type) && (
                <div className="rv-modal__meta">
                  {claim.materiality && (
                    <span className="it-chip rv-modal__meta-chip">
                      {claim.materiality}
                    </span>
                  )}
                  {claim.claim_type && (
                    <span className="it-chip rv-modal__meta-chip">
                      {claim.claim_type}
                    </span>
                  )}
                </div>
              )}

              {/* ── Inference: from_claims chain ── */}
              {claim.status === "inference" || claim.claim_type === "inference" ? (
                <div className="rv-modal__inference-section" data-testid="modal-inference-section">
                  <h3 className="rv-modal__section-title">Inference Basis</h3>

                  {/* RIB-018 guard: empty from_claims on an inference claim */}
                  {(claim.inference_basis?.from_claims ?? []).length === 0 ? (
                    <div
                      className="rv-modal__rib018-warning"
                      data-testid="modal-rib018-warning"
                      role="alert"
                    >
                      <span className="rv-modal__rib018-icon" aria-hidden="true">⚠</span>
                      <div>
                        <strong>Inference unsupported</strong>
                        <p className="rv-modal__rib018-detail">
                          This claim is labeled as inference but declares no basis claims (from_claims is empty).
                          This is a RIB-018 class false-pass: the claim cannot be audited for its reasoning chain.
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* Linked inference chain */
                    <div className="rv-modal__from-claims" data-testid="modal-from-claims">
                      <p className="rv-modal__from-claims-label">
                        This inference derives from:
                      </p>
                      <div className="rv-modal__from-claims-chain">
                        {(claim.inference_basis?.from_claims ?? []).map((fromId, idx) => (
                          <span key={fromId} className="rv-modal__chain-item">
                            <button
                              type="button"
                              className="rv-modal__chain-link it-btn ghost xs"
                              data-testid={`modal-chain-link-${fromId}`}
                              onClick={() => {
                                onChainClick?.(fromId);
                                open(fromId);
                              }}
                            >
                              {fromId}
                            </button>
                            {idx < (claim.inference_basis?.from_claims ?? []).length - 1 && (
                              <span className="rv-modal__chain-arrow" aria-hidden="true">→</span>
                            )}
                          </span>
                        ))}
                      </div>
                      {claim.inference_basis?.reasoning_summary && (
                        <p className="rv-modal__reasoning" data-testid="modal-reasoning">
                          {claim.inference_basis.reasoning_summary}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ) : null}

              {/* ── Sources section ── */}
              {claim.sources.length > 0 ? (
                <div className="rv-modal__sources-section" data-testid="modal-sources">
                  <h3 className="rv-modal__section-title">
                    Sources ({claim.sources.length})
                  </h3>
                  <div className="rv-modal__source-list">
                    {claim.sources.map((src) => (
                      <SourceCard key={`${src.source_card_id}-${src.evidence_id}`} source={src} />
                    ))}
                  </div>
                </div>
              ) : claim.status !== "inference" && claim.claim_type !== "inference" ? (
                /* Supported claim with zero sources — unexpected but handled */
                <div className="rv-modal__no-sources" data-testid="modal-no-sources">
                  <p>Source data unavailable for this claim.</p>
                </div>
              ) : null}

            </div>
          )}
        </div>
      </div>
    );
  }
);

export default ProvenanceModal;
