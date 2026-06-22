/**
 * LineageGraph.tsx — Tab container that owns shared state for the Lineage tab.
 *
 * Sprint 1: list view + detail panel + view-mode toggle scaffold.
 * Sprint 2: replace the graph slot with a React Flow canvas.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { RFRunExport } from "@/types/rf";
import { buildLineageTree, type LineageNode } from "./lineageTree";
import { LineageList } from "./LineageList";
import { LineageDetailPanel } from "./LineageDetailPanel";
import { LineageFlow } from "./LineageFlow";

export interface ArtifactLineageGraphProps {
  run: RFRunExport;
  selectedClaimId?: string | null;
  onSelectClaim?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
  /** Called when the user double-clicks a lineage row or clicks the ⤢ button in LineageDetailPanel. */
  onExpandNode?: (node: LineageNode) => void;
}

type ViewMode = "list" | "graph";

export function ArtifactLineageGraph({
  run,
  selectedClaimId,
  onSelectClaim,
  onOpenProvenance,
  onExpandNode,
}: ArtifactLineageGraphProps) {
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
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  // Sync: when selectedClaimId prop changes, select the matching claim node
  useEffect(() => {
    if (!selectedClaimId) return;
    const matchId = `claim:${selectedClaimId}`;
    const exists = allIds.includes(matchId);
    if (exists) setSelectedNodeId(matchId);
  }, [selectedClaimId, allIds]);

  // Memoized so the graph view (which stores these in node.data) gets stable refs
  // and doesn't rebuild every React Flow node on each parent render.
  const handleToggle = useCallback((nodeId: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  const handleSelectNode = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      // If it's a claim node, forward the claimId to the parent
      const node = findNode(tree, nodeId);
      if (node?.kind === "claim" && node.claimId && onSelectClaim) {
        onSelectClaim(node.claimId);
      }
    },
    [tree, onSelectClaim],
  );

  function handleExpandAll() {
    setExpanded(new Set(allIds));
  }

  function handleCollapseAll() {
    setExpanded(new Set(tree[0] ? [tree[0].id] : []));
  }

  const selectedNode: LineageNode | null = selectedNodeId
    ? (findNode(tree, selectedNodeId) ?? null)
    : null;

  return (
    <div className="rv-lineage rv-lineage-explorer" data-testid="lineage-graph">
      {/* Toolbar */}
      <div className="rv-lineage-explorer__toolbar">
        <div>
          <span className="rv-kicker">Source-first lineage</span>
          <h2>Evidence to claims to report</h2>
        </div>

        <div className="rv-lineage-explorer__toolbar-right">
          {/* View toggle */}
          <div className="rv-lineage-view-toggle it-seg" role="group" aria-label="View mode">
            <button
              type="button"
              className={viewMode === "list" ? "active" : ""}
              aria-pressed={viewMode === "list"}
              data-testid="lineage-view-list"
              onClick={() => setViewMode("list")}
            >
              List
            </button>
            <button
              type="button"
              className={viewMode === "graph" ? "active" : ""}
              aria-pressed={viewMode === "graph"}
              data-testid="lineage-view-graph"
              onClick={() => setViewMode("graph")}
            >
              Graph
            </button>
          </div>

          {/* Expand / collapse */}
          <div className="rv-lineage-explorer__actions">
            <button
              type="button"
              className="it-btn ghost xs"
              onClick={handleExpandAll}
              data-testid="lineage-expand-all"
            >
              Expand all
            </button>
            <button
              type="button"
              className="it-btn ghost xs"
              onClick={handleCollapseAll}
              data-testid="lineage-collapse-all"
            >
              Collapse all
            </button>
          </div>
        </div>
      </div>

      {/* Two-pane body */}
      <div className="rv-lineage-workspace">
        {/* Main view region */}
        <div className="rv-lineage-main">
          {viewMode === "list" ? (
            <LineageList
              roots={tree}
              expanded={expanded}
              onToggle={handleToggle}
              selectedNodeId={selectedNodeId}
              onSelectNode={handleSelectNode}
              onExpandNode={onExpandNode}
            />
          ) : (
            <div
              id="lineage-graph-canvas-slot"
              data-testid="lineage-graph-canvas-slot"
              className="rv-lineage-graph-slot"
            >
              <LineageFlow
                roots={tree}
                expanded={expanded}
                onToggle={handleToggle}
                selectedNodeId={selectedNodeId}
                onSelectNode={handleSelectNode}
                onExpandNode={onExpandNode}
              />
            </div>
          )}
        </div>

        {/* Detail panel — P5 DISP-005: pass run meta for reference chips */}
        <LineageDetailPanel
          node={selectedNode}
          runMeta={{ tags: run.tags, category: run.category }}
          onSelectClaim={onSelectClaim}
          onOpenProvenance={onOpenProvenance}
          onExpandNode={onExpandNode}
        />
      </div>

      {/* Hidden compat summary (preserve existing testid for other tests) */}
      <div
        className="rv-lineage__compat-summary"
        data-testid="lineage-svg"
        aria-hidden="true"
      >
        {tree[0]?.children.length ?? 0} sources
      </div>
    </div>
  );
}

// ── Utilities ──────────────────────────────────────────────────────────────────

function flattenNodeIds(nodes: LineageNode[]): string[] {
  return nodes.flatMap((node) => [node.id, ...flattenNodeIds(node.children)]);
}

function findNode(nodes: LineageNode[], id: string): LineageNode | undefined {
  for (const node of nodes) {
    if (node.id === id) return node;
    const found = findNode(node.children, id);
    if (found) return found;
  }
  return undefined;
}

export default ArtifactLineageGraph;
