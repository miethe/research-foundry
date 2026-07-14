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

import { useState, useCallback, forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import type { RFClaim, RFSensitivity } from "@/types/rf";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import { ReusableAssertionFieldsColumn } from "@/components/AssertionCatalog/ReusableAssertionFieldsColumn";
import "@/styles/assertions.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProvenanceModalHandle {
  open:  (claimId: string) => void;
  close: () => void;
}

export interface ProvenanceModalProps {
  claims:        RFClaim[];
  /** Called when a from_claims chain link is clicked — opens the referenced claim. */
  onChainClick?: (claimId: string) => void;
  /** Adds a higher stacking layer when opened from inside another modal. */
  stacked?: boolean;
  /** Allows parent modals to suppress their own Escape/overlay close while this is open. */
  onOpenChange?: (open: boolean) => void;
  /** Active sensitivity threshold from the run export. Passed to SourceCard to avoid re-masking
   *  content already emitted at a higher threshold. When absent, SourceCard defaults to client_sensitive. */
  sensitivityThreshold?: RFSensitivity | null;
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
  function ProvenanceModal({ claims, onChainClick, stacked = false, onOpenChange, sensitivityThreshold }, ref) {
    const [openClaimId, setOpenClaimId] = useState<string | null>(null);
    const openerRef = useRef<HTMLElement | null>(null);
    const dialogRef = useRef<HTMLDivElement | null>(null);
    const closeButtonRef = useRef<HTMLButtonElement | null>(null);

    const open  = useCallback((claimId: string) => {
      const activeElement = document.activeElement;
      setOpenClaimId((currentClaimId) => {
        if (currentClaimId === null && activeElement instanceof HTMLElement) {
          openerRef.current = activeElement;
        }
        return claimId;
      });
      onOpenChange?.(true);
    }, [onOpenChange]);
    const close = useCallback(() => {
      setOpenClaimId(null);
      onOpenChange?.(false);
      const opener = openerRef.current;
      openerRef.current = null;
      if (opener?.isConnected) opener.focus();
    }, [onOpenChange]);

    useImperativeHandle(ref, () => ({ open, close }), [open, close]);

    useEffect(() => {
      if (!openClaimId) return undefined;
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
          close();
          return;
        }
        if (event.key !== "Tab") return;
        const dialog = dialogRef.current;
        if (!dialog) return;
        const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        )).filter((element) => !element.hasAttribute("disabled") && element.getAttribute("aria-hidden") !== "true");
        if (focusable.length === 0) {
          event.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const activeElement = document.activeElement;
        if (event.shiftKey && (activeElement === first || !dialog.contains(activeElement))) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (activeElement === last || !dialog.contains(activeElement))) {
          event.preventDefault();
          first.focus();
        }
      };
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }, [close, openClaimId]);

    useEffect(() => {
      if (openClaimId) closeButtonRef.current?.focus();
    }, [openClaimId]);

    if (!openClaimId) return null;

    const claim = claims.find((c) => c.claim_id === openClaimId);

    return (
      /* ── Overlay ── */
      <div
        className={`rv-modal-overlay${stacked ? " rv-modal-overlay--stacked" : ""}`}
        data-testid="provenance-modal-overlay"
        onClick={(e) => { if (e.target === e.currentTarget) close(); }}
        role="presentation"
      >
        <div
          ref={dialogRef}
          className={`rv-modal${claim ? " rv-modal--assertion-columns" : ""}`}
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
              ref={closeButtonRef}
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
            <div className="rv-modal__provenance-columns" data-testid="modal-provenance-columns">
            <div className="rv-modal__provenance-left" data-testid="modal-provenance-left">

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
                      <SourceCard key={`${src.source_card_id}-${src.evidence_id}`} source={src} sensitivityThreshold={sensitivityThreshold} />
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

            {/* ── Reusable assertion fields (P6-002) ── */}
            <ReusableAssertionFieldsColumn claim={claim} />

            </div>
            </div>
          )}
        </div>
      </div>
    );
  }
);

export default ProvenanceModal;
