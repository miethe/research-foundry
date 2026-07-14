/**
 * LineageDetailPanel — Right-hand detail panel for the selected lineage node.
 * Replaces the always-on inline <dl> that used to live inside every row.
 *
 * P5 DISP-005: accepts optional runMeta for reference tag/category chips in the panel header.
 * Chips are non-interactive context only; omitted when tags/category null/absent (R-P2).
 *
 * P6-003: this panel models the claim-lineage object graph only (LineageNode /
 * LINEAGE_KIND_META below). The typed assertion-relationship lineage (source
 * edition → passage → source assertion → report/run uses, plus inference)
 * has a materially different, packet/DTO-shaped inspector — see the sibling
 * AssertionOnlyInspector in ./AssertionOnlyLineage.tsx, which reuses this
 * file's `.rv-lineage-detail` CSS scaffold rather than this component's
 * LineageNode-typed props.
 */

import type { LineageNode } from "./lineageTree";
import { LINEAGE_KIND_META } from "./lineageTree";
import { KindIcon } from "./kindIcons";

/** Minimal run-level metadata for reference display (P5 DISP-005). */
export interface LineageRunMetaRef {
  tags?: string[] | null;
  category?: string | null;
}

export interface LineageDetailPanelProps {
  node: LineageNode | null;
  runMeta?: LineageRunMetaRef;
  onSelectClaim?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
  /** Called when the user clicks the ⤢ expand button; opens DetailModal with the node payload. */
  onExpandNode?: (node: LineageNode) => void;
}

export function LineageDetailPanel({ node, runMeta, onSelectClaim, onOpenProvenance, onExpandNode }: LineageDetailPanelProps) {
  // P5 DISP-005: reference chips — shown only when tags/category present (R-P2)
  const hasRunMeta = (runMeta?.tags?.length ?? 0) > 0 || runMeta?.category != null;

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
          {onExpandNode && (
            <button
              type="button"
              className="it-btn ghost xs rv-lineage-detail__expand"
              data-testid="lineage-detail-expand"
              aria-label="Expand lineage node in modal"
              onClick={() => onExpandNode(node)}
            >
              ⤢
            </button>
          )}
        </div>
        <strong className="rv-lineage-detail__title">{node.title}</strong>
        {node.subtitle && (
          <code className="rv-lineage-detail__subtitle">{node.subtitle}</code>
        )}
        {/* P5 DISP-005: run-level reference chips — context only, non-interactive */}
        {hasRunMeta && (
          <div className="rv-lineage-detail__run-meta" data-testid="lineage-run-meta" aria-label="Run context">
            {runMeta?.category ? (
              <span className="rv-run-modal__category" data-testid="lineage-run-category">
                {runMeta.category}
              </span>
            ) : null}
            {runMeta?.tags?.map((tag) => (
              <span key={tag} className="it-chip rv-tag-chip rv-tag-chip--sm" data-testid="lineage-run-tag">
                {tag}
              </span>
            ))}
          </div>
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
