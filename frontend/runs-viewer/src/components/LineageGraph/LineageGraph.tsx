import { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { RFRunExport } from "@/types/rf";
import { buildLineageTree, type LineageNode } from "./lineageTree";

export interface ArtifactLineageGraphProps {
  run: RFRunExport;
  selectedClaimId?: string | null;
  onSelectClaim?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
}

export function ArtifactLineageGraph({ run, selectedClaimId, onSelectClaim, onOpenProvenance }: ArtifactLineageGraphProps) {
  const tree = useMemo(() => buildLineageTree(run), [run]);
  const allIds = useMemo(() => flattenNodeIds(tree), [tree]);
  const defaultExpanded = useMemo(() => {
    const ids = new Set<string>();
    const root = tree[0];
    if (root) {
      ids.add(root.id);
      if (root.children[0]) ids.add(root.children[0].id);
    }
    return ids;
  }, [tree]);
  const [expanded, setExpanded] = useState<Set<string>>(defaultExpanded);

  function toggle(nodeId: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }

  return (
    <div className="rv-lineage rv-lineage-explorer" data-testid="lineage-graph">
      <div className="rv-lineage-explorer__toolbar">
        <div>
          <span className="rv-kicker">Source-first lineage</span>
          <h2>Evidence to claims to report</h2>
        </div>
        <div className="rv-lineage-explorer__actions">
          <button type="button" className="it-btn ghost xs" onClick={() => setExpanded(new Set(allIds))} data-testid="lineage-expand-all">
            Expand all
          </button>
          <button type="button" className="it-btn ghost xs" onClick={() => setExpanded(new Set(tree[0] ? [tree[0].id] : []))} data-testid="lineage-collapse-all">
            Collapse all
          </button>
        </div>
      </div>

      <div className="rv-lineage-tree" role="tree" aria-label="Run lineage explorer">
        {tree.map((node) => (
          <LineageRow
            key={node.id}
            node={node}
            depth={0}
            expanded={expanded}
            selectedClaimId={selectedClaimId}
            onToggle={toggle}
            onSelectClaim={onSelectClaim}
            onOpenProvenance={onOpenProvenance}
          />
        ))}
      </div>

      <div className="rv-lineage__compat-summary" data-testid="lineage-svg" aria-hidden="true">
        {tree[0]?.children.length ?? 0} sources
      </div>
    </div>
  );
}

function LineageRow({
  node,
  depth,
  expanded,
  selectedClaimId,
  onToggle,
  onSelectClaim,
  onOpenProvenance,
}: {
  node: LineageNode;
  depth: number;
  expanded: Set<string>;
  selectedClaimId?: string | null;
  onToggle: (nodeId: string) => void;
  onSelectClaim?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.id);
  const isSelectedClaim = node.kind === "claim" && node.claimId === selectedClaimId;
  const testId = node.kind === "claim" && node.claimId ? `lineage-node-${node.claimId}` : `lineage-node-${node.id}`;

  return (
    <>
      <div
        className={`rv-lineage-row rv-lineage-row--${node.kind}${isSelectedClaim ? " rv-lineage-row--selected" : ""}`}
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelectedClaim || undefined}
        data-testid={testId}
        data-kind={node.kind}
        style={{ "--lineage-depth": depth } as CSSProperties & Record<"--lineage-depth", number>}
        title={node.subtitle ?? node.title}
      >
        <button
          type="button"
          className="rv-lineage-row__toggle"
          aria-label={hasChildren ? `${isExpanded ? "Collapse" : "Expand"} ${node.title}` : node.title}
          aria-expanded={hasChildren ? isExpanded : undefined}
          disabled={!hasChildren}
          onClick={() => hasChildren && onToggle(node.id)}
        >
          {hasChildren ? (isExpanded ? "v" : ">") : ""}
        </button>

        <div className="rv-lineage-row__body">
          <div className="rv-lineage-row__title">
            <strong>{node.title}</strong>
            {node.subtitle && <code>{node.subtitle}</code>}
          </div>
          {node.chips && node.chips.length > 0 && (
            <div className="rv-lineage-row__chips">
              {node.chips.map((chip) => (
                <span key={chip} className="it-chip">{chip}</span>
              ))}
            </div>
          )}
        </div>

        {node.details && node.details.length > 0 && (
          <dl className="rv-lineage-row__details">
            {node.details.map((item) => (
              <div key={`${item.label}-${item.value}`}>
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

        {node.claimId && (onSelectClaim || onOpenProvenance) && (
          <div className="rv-lineage-row__actions">
            {onSelectClaim && (
              <button type="button" className="it-btn ghost xs" onClick={() => onSelectClaim(node.claimId!)}>
                Select
              </button>
            )}
            {onOpenProvenance && (
              <button type="button" className="it-btn ghost xs" onClick={() => onOpenProvenance(node.claimId!)}>
                Open
              </button>
            )}
          </div>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div role="group">
          {node.children.map((child) => (
            <LineageRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              selectedClaimId={selectedClaimId}
              onToggle={onToggle}
              onSelectClaim={onSelectClaim}
              onOpenProvenance={onOpenProvenance}
            />
          ))}
        </div>
      )}
    </>
  );
}

function flattenNodeIds(nodes: LineageNode[]): string[] {
  return nodes.flatMap((node) => [node.id, ...flattenNodeIds(node.children)]);
}

export default ArtifactLineageGraph;
