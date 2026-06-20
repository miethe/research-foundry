/**
 * LineageDetailPanel — Right-hand detail panel for the selected lineage node.
 * Replaces the always-on inline <dl> that used to live inside every row.
 */

import type { LineageNode } from "./lineageTree";
import { LINEAGE_KIND_META } from "./lineageTree";
import { KindIcon } from "./kindIcons";

export interface LineageDetailPanelProps {
  node: LineageNode | null;
  onSelectClaim?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
}

export function LineageDetailPanel({ node, onSelectClaim, onOpenProvenance }: LineageDetailPanelProps) {
  if (!node) {
    return (
      <div className="rv-lineage-detail rv-lineage-detail--empty" data-testid="lineage-detail">
        <p className="rv-lineage-detail__empty" data-testid="lineage-detail-empty">
          Select a node to inspect its provenance.
        </p>
      </div>
    );
  }

  const meta = LINEAGE_KIND_META[node.kind];

  return (
    <div className="rv-lineage-detail" data-testid="lineage-detail">
      {/* Header */}
      <div className="rv-lineage-detail__header">
        <div className="rv-lineage-detail__kind-row">
          <span
            className="rv-lineage-detail__kind-icon"
            style={{ color: meta.accent }}
            aria-hidden="true"
          >
            <KindIcon kind={node.kind} size={16} />
          </span>
          <span className="it-chip rv-lineage-detail__kind-chip">{meta.label}</span>
        </div>
        <strong className="rv-lineage-detail__title">{node.title}</strong>
        {node.subtitle && (
          <code className="rv-lineage-detail__subtitle">{node.subtitle}</code>
        )}
      </div>

      {/* Chips */}
      {node.chips && node.chips.length > 0 && (
        <div className="rv-lineage-detail__chips">
          {node.chips.map((chip) => (
            <span key={chip} className="it-chip">{chip}</span>
          ))}
        </div>
      )}

      {/* Details */}
      {node.details && node.details.length > 0 && (
        <dl className="rv-lineage-detail__dl">
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

      {/* Claim actions */}
      {node.claimId && (onSelectClaim || onOpenProvenance) && (
        <div className="rv-lineage-detail__actions">
          {onSelectClaim && (
            <button
              type="button"
              className="it-btn ghost xs"
              onClick={() => onSelectClaim(node.claimId!)}
            >
              Select claim
            </button>
          )}
          {onOpenProvenance && (
            <button
              type="button"
              className="it-btn ghost xs"
              onClick={() => onOpenProvenance(node.claimId!)}
            >
              Open provenance
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default LineageDetailPanel;
