/**
 * lineageFlowElements.ts — Pure helper that converts layoutLineage output into
 * React Flow nodes and edges arrays.
 *
 * Kept as a pure module-level function so it can be unit-tested without any
 * React Flow DOM / canvas rendering in jsdom.
 */

import { MarkerType, type Node, type Edge, Position } from "@xyflow/react";
import { layoutLineage } from "./lineageLayout";
import { LINEAGE_KIND_META } from "./lineageTree";
import type { LineageNode } from "./lineageTree";
import type { LineageFlowNodeData } from "./LineageFlow";

// React Flow v12: Node<Data> is the correct node type for typed nodes
type LineageRFNode = Node<LineageFlowNodeData>;

export interface FlowElements {
  nodes: LineageRFNode[];
  edges: Edge[];
}

/**
 * Build React Flow node + edge arrays from the lineage tree.
 *
 * This is a pure function — no React hooks, no side-effects.
 * All position / sizing data comes from `layoutLineage`; we never recompute
 * positions here.
 *
 * D4: onExpandNode is stored in node.data so LineageFlowNode can call it on
 * single-click, opening DetailModal with the node payload.
 */
export function buildFlowElements(
  roots: LineageNode[],
  expanded: Set<string>,
  selectedNodeId: string | null,
  onToggle: (id: string) => void,
  onSelectNode: (id: string) => void,
  onExpandNode?: (node: LineageNode) => void,
): FlowElements {
  // NOTE: callbacks passed here are stored in node.data; React Flow re-renders
  // nodes when data changes, so callers should provide stable references (useCallback).
  const layout = layoutLineage(roots, expanded);

  const nodes: LineageRFNode[] = layout.nodes.map((rect) => {
    const meta = LINEAGE_KIND_META[rect.node.kind];
    const isSelected = rect.id === selectedNodeId;
    const isExpanded = expanded.has(rect.id);
    const childCount = rect.node.children.length;

    const data: LineageFlowNodeData = {
      node: rect.node,
      meta,
      isSelected,
      isExpanded,
      childCount,
      onToggle,
      onSelectNode,
      onExpandNode,
    };

    return {
      id: rect.id,
      type: "lineage",
      position: { x: rect.x, y: rect.y },
      data,
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      draggable: false,
      selectable: true,
      style: { width: rect.w, height: rect.h },
    };
  });

  // Deduplicate edges by ID — layoutLineage can emit duplicate edges when a
  // non-leaf node pushes parent→child in its children loop AND the recursive
  // leaf-branch also pushes the same edge.
  const seenEdgeIds = new Set<string>();
  const edges: Edge[] = layout.edges
    .filter((e) => {
      if (seenEdgeIds.has(e.id)) return false;
      seenEdgeIds.add(e.id);
      return true;
    })
    .map((e) => {
      const targetMeta = LINEAGE_KIND_META[e.targetKind];
      const accent = targetMeta.accent;
      return {
        id: e.id,
        source: e.sourceId,
        target: e.targetId,
        type: "smoothstep",
        className: "rv-lineage-edge",
        style: {
          stroke: accent,
          strokeWidth: 2,
          opacity: 0.85,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: accent,
          width: 14,
          height: 14,
        },
      };
    });

  return { nodes, edges };
}
