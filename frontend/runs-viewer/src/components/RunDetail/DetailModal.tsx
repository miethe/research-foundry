/**
 * DetailModal — generic item-expand overlay (F2 feature, v2.2).
 *
 * Accepts a discriminated union payload:
 *   - { kind: 'claim'; claimId: string; claims: RFClaim[] }
 *   - { kind: 'node'; node: LineageNode }
 *
 * Overlay conventions mirror ProvenanceModal:
 *   - .rv-modal-overlay / .rv-modal-overlay--stacked
 *   - .rv-modal / .rv-modal__header / .rv-modal__body
 *   - role="dialog", aria-modal="true"
 *   - Escape-to-close (via useEffect keydown listener)
 *   - backdrop click closes; dialog content click does not
 *   - stacked prop for z-index layering
 *   - onOpenChange callback for parent Escape suppression
 *
 * Entry points:
 *   - Double-click on RunCard (dispatches onExpandRun → opens RunDetailModal, not this)
 *   - ⤢ button in LineageDetailPanel header (onExpandNode → DetailModal with node payload)
 *   - Double-click on LineageList rows (onExpandNode → DetailModal with node payload)
 *   - Double-click on ClaimLedgerTable row (onExpandClaim → DetailModal with claim payload)
 *   - ⤢ button in ClaimInspector (onExpandClaim → DetailModal with claim payload)
 *
 * Resilience:
 *   - node.claimId === undefined → renders node metadata only + "No provenance available" note
 *   - claimId not found in claims array → renders "Claim not found" (mirrors ProvenanceModal:127-132)
 */

import { useCallback, useEffect } from "react";
import type { RFClaim } from "@/types/rf";
import type { LineageNode } from "@/components/LineageGraph/lineageTree";
import { LINEAGE_KIND_META } from "@/components/LineageGraph/lineageTree";
import { KindIcon } from "@/components/LineageGraph/kindIcons";
import { SourceCard } from "@/components/SourceCard/SourceCard";

// ── Payload types ─────────────────────────────────────────────────────────────

export type DetailModalPayload =
  | { kind: "claim"; claimId: string; claims: RFClaim[] }
  | { kind: "node"; node: LineageNode };

// ── Props ─────────────────────────────────────────────────────────────────────

export interface DetailModalProps {
  payload: DetailModalPayload | null;
  /** Adds a higher stacking layer when opened from inside another modal. */
  stacked?: boolean;
  /** Allows parent modals to suppress their own Escape/overlay close while this is open. */
  onOpenChange?: (open: boolean) => void;
  /** Called when the modal requests close. Parent sets payload to null. */
  onClose: () => void;
}

// ── Status chip map (mirrors ProvenanceModal) ─────────────────────────────────

const STATUS_CHIP: Record<string, string> = {
  supported:    "green",
  mixed:        "gold",
  contradicted: "red",
  inference:    "blue",
  speculation:  "orange",
  unsupported:  "red",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function DetailModal({ payload, stacked = false, onOpenChange, onClose }: DetailModalProps) {
  const close = useCallback(() => {
    onClose();
    onOpenChange?.(false);
  }, [onClose, onOpenChange]);

  // Notify parent when open state changes
  useEffect(() => {
    if (payload) {
      onOpenChange?.(true);
    }
  }, [payload, onOpenChange]);

  // Escape key handler — active only while payload is set
  useEffect(() => {
    if (!payload) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [close, payload]);

  if (!payload) return null;

  return (
    <div
      className={`rv-modal-overlay${stacked ? " rv-modal-overlay--stacked" : ""}`}
      data-testid="detail-modal-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
      role="presentation"
    >
      <div
        className="rv-modal rv-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-label={
          payload.kind === "claim"
            ? `Detail for ${payload.claimId}`
            : `Detail for ${payload.node.title}`
        }
        data-testid="detail-modal"
      >
        {/* ── Header ── */}
        <div className="rv-modal__header">
          <div className="rv-modal__title-row">
            {payload.kind === "claim" ? (
              <>
                <span className="it-chip rv-modal__kind-label">Claim</span>
                <code className="rv-modal__claim-id" data-testid="detail-modal-id">
                  {payload.claimId}
                </code>
              </>
            ) : (
              <>
                <span
                  className="rv-detail-modal__kind-icon"
                  style={{ color: LINEAGE_KIND_META[payload.node.kind].accent }}
                  aria-hidden="true"
                >
                  <KindIcon kind={payload.node.kind} size={16} />
                </span>
                <span className="it-chip rv-modal__kind-label">
                  {LINEAGE_KIND_META[payload.node.kind].label}
                </span>
                <strong className="rv-modal__node-title" data-testid="detail-modal-id">
                  {payload.node.title}
                </strong>
              </>
            )}
          </div>
          <button
            type="button"
            className="it-btn ghost sm rv-modal__close"
            data-testid="detail-modal-close"
            onClick={close}
            aria-label="Close detail modal"
          >
            ✕
          </button>
        </div>

        {/* ── Body ── */}
        <div className="rv-modal__body" data-testid="detail-modal-body">
          {payload.kind === "claim" ? (
            <ClaimModalBody claimId={payload.claimId} claims={payload.claims} />
          ) : (
            <NodeModalBody node={payload.node} />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Claim body ────────────────────────────────────────────────────────────────

function ClaimModalBody({ claimId, claims }: { claimId: string; claims: RFClaim[] }) {
  const claim = claims.find((c) => c.claim_id === claimId);

  if (!claim) {
    return (
      <p className="rv-modal__not-found" data-testid="detail-modal-claim-not-found">
        Claim <code>{claimId}</code> not found in the ledger.
      </p>
    );
  }

  return (
    <>
      {/* Status + confidence chips */}
      <div className="rv-modal__meta">
        {claim.status && (
          <span
            className={`it-chip ${STATUS_CHIP[claim.status] ?? ""} rv-modal__status`}
            data-testid="detail-modal-status"
          >
            {claim.status}
          </span>
        )}
        {claim.confidence && (
          <span className="it-chip rv-modal__confidence" data-testid="detail-modal-confidence">
            {claim.confidence} confidence
          </span>
        )}
        {claim.materiality && (
          <span className="it-chip rv-modal__meta-chip">{claim.materiality}</span>
        )}
        {claim.claim_type && (
          <span className="it-chip rv-modal__meta-chip">{claim.claim_type}</span>
        )}
      </div>

      {/* Claim text */}
      <div className="rv-modal__claim-text" data-testid="detail-modal-claim-text">
        <p>{claim.text}</p>
      </div>

      {/* Sources */}
      {claim.sources.length > 0 ? (
        <div className="rv-modal__sources-section" data-testid="detail-modal-sources">
          <h3 className="rv-modal__section-title">Sources ({claim.sources.length})</h3>
          <div className="rv-modal__source-list">
            {claim.sources.map((src) => (
              <SourceCard key={`${src.source_card_id}-${src.evidence_id}`} source={src} />
            ))}
          </div>
        </div>
      ) : (
        <p className="rv-muted" data-testid="detail-modal-no-sources">
          No source cards linked to this claim.
        </p>
      )}
    </>
  );
}

// ── Node body ─────────────────────────────────────────────────────────────────

function NodeModalBody({ node }: { node: LineageNode }) {
  const meta = LINEAGE_KIND_META[node.kind];

  return (
    <>
      {/* Subtitle */}
      {node.subtitle && (
        <code className="rv-detail-modal__subtitle" data-testid="detail-modal-subtitle">
          {node.subtitle}
        </code>
      )}

      {/* Chips */}
      {node.chips && node.chips.length > 0 && (
        <div className="rv-detail-modal__chips" data-testid="detail-modal-chips">
          {node.chips.map((chip) => (
            <span key={chip} className="it-chip">{chip}</span>
          ))}
        </div>
      )}

      {/* Details table */}
      {node.details && node.details.length > 0 && (
        <dl className="rv-lineage-detail__dl rv-detail-modal__dl" data-testid="detail-modal-details">
          {node.details.map((item) => (
            <div key={`${item.label}-${item.value}`} className="rv-lineage-detail__dl-row">
              <dt>{item.label}</dt>
              <dd>
                {item.href ? (
                  <a href={item.href} target="_blank" rel="noreferrer">{item.value}</a>
                ) : (
                  item.value
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {/* Claim link — or graceful absence note */}
      {node.claimId ? (
        <div className="rv-detail-modal__claim-ref" data-testid="detail-modal-claim-ref">
          <span className="rv-muted">Associated claim:</span>{" "}
          <code>{node.claimId}</code>
        </div>
      ) : (
        <p className="rv-muted" data-testid="detail-modal-no-provenance">
          No provenance available for this node type.
        </p>
      )}

      {/* Kind accent indicator */}
      <div className="rv-detail-modal__kind-footer" aria-hidden="true">
        <span style={{ color: meta.accent }}>
          <KindIcon kind={node.kind} size={12} />
        </span>
        <span className="rv-muted">{meta.label} node</span>
      </div>
    </>
  );
}

export default DetailModal;
