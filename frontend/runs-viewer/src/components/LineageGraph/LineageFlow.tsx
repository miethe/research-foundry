/**
 * LineageFlow.tsx — React Flow horizontal tree view for the Lineage tab.
 *
 * Sprint 2: replaces the placeholder in LineageGraph.tsx's graph slot.
 * All layout positions come from layoutLineage(); we never recompute them here.
 *
 * Architecture notes:
 * - nodeTypes and edgeTypes are defined at MODULE scope to avoid React Flow
 *   warnings about unstable references on every render.
 * - Framing uses React Flow's built-in `fitView` prop (+ fitViewOptions), which
 *   waits for node measurement internally. The component remounts on every
 *   list↔graph toggle, so the graph re-frames each time it is shown; it does NOT
 *   refit on expand/collapse, so the viewport stays stable while navigating.
 * - proOptions.hideAttribution is true — this is an internal homelab tool.
 */

import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Handle,
  Position,
  SmoothStepEdge,
  type Node,
  type NodeProps,
  type NodeTypes,
  type EdgeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useMemo, type CSSProperties } from "react";

import { buildFlowElements } from "./lineageFlowElements";
import { KindIcon, ChevronRight, ChevronDown } from "./kindIcons";
import { LINEAGE_KIND_META } from "./lineageTree";
import type { LineageNode, LineageKindMeta, LineageNodeKind } from "./lineageTree";
import type { LineageViewProps } from "./LineageList";

// ── Node data type ─────────────────────────────────────────────────────────────

export interface LineageFlowNodeData {
  node: LineageNode;
  meta: LineageKindMeta;
  isSelected: boolean;
  isExpanded: boolean;
  childCount: number;
  onToggle: (id: string) => void;
  onSelectNode: (id: string) => void;
  /** D4: single-click on graph node opens DetailModal with the node payload. */
  onExpandNode?: (node: LineageNode) => void;
  [key: string]: unknown; // satisfy React Flow's Record<string, unknown> constraint
}

// ── Node type alias (React Flow v12 pattern: NodeProps<Node<Data>>) ───────────

type LineageFlowNodeType = Node<LineageFlowNodeData>;

// ── Custom node component (defined at module scope to avoid re-registration) ───

function LineageFlowNode({ data, id }: NodeProps<LineageFlowNodeType>) {
  const { node, meta, isSelected, isExpanded, childCount, onToggle, onSelectNode, onExpandNode } = data;
  const chips = node.chips ?? [];
  const visibleChips = chips.slice(0, 3);

  function handleBodyClick() {
    onSelectNode(id);
    // D4: single-click on a graph node also opens DetailModal (graph mode has no
    // separate select vs. expand distinction, so one click does both).
    onExpandNode?.(node);
  }

  function handleBadgeClick(e: React.MouseEvent) {
    e.stopPropagation();
    onToggle(id);
  }

  return (
    <div
      className={[
        "rv-lnode",
        `rv-lnode--${node.kind}`,
        isSelected ? "rv-lnode--selected" : "",
      ].filter(Boolean).join(" ")}
      data-testid={`lineage-flow-node-${id}`}
      data-kind={node.kind}
      onClick={handleBodyClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelectNode(id);
          onExpandNode?.(node);
        }
      }}
    >
      {/* Left accent rail */}
      <span
        className="rv-lnode__rail"
        style={{ background: meta.accent } as CSSProperties}
        aria-hidden="true"
      />

      {/* Target handle (left edge) — visually hidden, needed for edge routing */}
      <Handle
        type="target"
        position={Position.Left}
        className="rv-lnode__handle rv-lnode__handle--target"
        isConnectable={false}
      />

      {/* Body */}
      <div className="rv-lnode__body">
        {/* Icon + title row */}
        <div className="rv-lnode__header">
          <span
            className="rv-lnode__icon"
            style={{ color: meta.accent } as CSSProperties}
            aria-hidden="true"
          >
            <KindIcon kind={node.kind} size={13} />
          </span>
          <strong className="rv-lnode__title">{node.title}</strong>
        </div>

        {/* Monospace id sublabel */}
        {node.subtitle && (
          <code className="rv-lnode__subtitle">{node.subtitle}</code>
        )}

        {/* Chips */}
        {visibleChips.length > 0 && (
          <div className="rv-lnode__chips" aria-hidden="true">
            {visibleChips.map((chip: string) => (
              <span key={chip} className="rv-lnode__chip">{chip}</span>
            ))}
          </div>
        )}
      </div>

      {/* Source handle (right edge) — visually hidden */}
      <Handle
        type="source"
        position={Position.Right}
        className="rv-lnode__handle rv-lnode__handle--source"
        isConnectable={false}
      />

      {/* Expand badge — only if the node has children */}
      {childCount > 0 && (
        <button
          type="button"
          className={[
            "rv-lnode__badge",
            isExpanded ? "rv-lnode__badge--expanded" : "",
          ].filter(Boolean).join(" ")}
          aria-label={`${isExpanded ? "Collapse" : "Expand"} ${node.title} (${childCount} child${childCount !== 1 ? "ren" : ""})`}
          onClick={handleBadgeClick}
          style={{ color: meta.accent, borderColor: meta.accent } as CSSProperties}
        >
          <span className="rv-lnode__badge-count">{childCount}</span>
          {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </button>
      )}
    </div>
  );
}

// ── nodeTypes and edgeTypes defined at module scope ────────────────────────────
// Both must be stable references (defined outside any component) to prevent
// React Flow from re-registering on every render, which causes flickering.

const nodeTypes: NodeTypes = {
  lineage: LineageFlowNode,
};

const edgeTypes: EdgeTypes = {
  smoothstep: SmoothStepEdge,
};

// ── Legend overlay ─────────────────────────────────────────────────────────────

function FlowLegend() {
  const kinds = Object.entries(LINEAGE_KIND_META) as [LineageNodeKind, LineageKindMeta][];
  return (
    <div className="rv-flow-legend" aria-label="Node kind legend">
      {kinds.map(([kind, meta]) => (
        <div key={kind} className="rv-flow-legend__item">
          <span
            className="rv-flow-legend__swatch"
            style={{ background: meta.accent } as CSSProperties}
            aria-hidden="true"
          />
          <span className="rv-flow-legend__label">{meta.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Inner component (has access to useReactFlow hook) ─────────────────────────

function LineageFlowInner({
  roots,
  expanded,
  onToggle,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
}: LineageViewProps) {
  // onToggle / onSelectNode / onExpandNode are memoized by the parent (LineageGraph),
  // so they are stable refs — safe to depend on directly without re-running each render.
  const { nodes, edges } = useMemo(
    () => buildFlowElements(roots, expanded, selectedNodeId, onToggle, onSelectNode, onExpandNode),
    [roots, expanded, selectedNodeId, onToggle, onSelectNode, onExpandNode],
  );

  function handleNodeColorForMinimap(node: { data?: unknown }): string {
    const nodeData = node.data as LineageFlowNodeData | undefined;
    if (!nodeData?.node?.kind) return "#94a3b8";
    return LINEAGE_KIND_META[nodeData.node.kind]?.accent ?? "#94a3b8";
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable
      panOnDrag
      zoomOnScroll
      minZoom={0.2}
      maxZoom={2.5}
      fitView
      fitViewOptions={{ padding: 0.16, maxZoom: 1.1 }}
      proOptions={{ hideAttribution: true }}
      data-testid="lineage-flow"
      className="rv-lineage-flow"
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={20}
        size={1.2}
        color="var(--it-border-soft, #d0dce7)"
      />
      <Controls showInteractive={false} className="rv-flow-controls" />
      <MiniMap
        nodeColor={handleNodeColorForMinimap}
        pannable
        zoomable
        className="rv-flow-minimap"
        maskColor="rgba(238,243,247,0.72)"
      />
      <FlowLegend />
    </ReactFlow>
  );
}

// ── Public export: ReactFlowProvider wrapper ───────────────────────────────────

export function LineageFlow(props: LineageViewProps) {
  return (
    <ReactFlowProvider>
      <LineageFlowInner {...props} />
    </ReactFlowProvider>
  );
}

export default LineageFlow;
