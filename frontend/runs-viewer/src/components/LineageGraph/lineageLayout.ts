/**
 * lineageLayout.ts — Pure, browser-free layout adapter for the lineage graph view.
 *
 * Computes a left-to-right horizontal tree layout over the currently EXPANDED
 * subtree. Sprint 2 will wire this into React Flow; this module has zero React
 * or DOM dependencies.
 */

import type { LineageNode, LineageNodeKind } from "./lineageTree";

// ── Per-kind node sizes ────────────────────────────────────────────────────────

const KIND_WIDTH: Record<LineageNodeKind, number> = {
  run:        260,
  source:     260,
  extraction: 240,
  claim:      240,
  report:     220,
  writeback:  220,
};

const KIND_HEIGHT: Record<LineageNodeKind, number> = {
  run:        84,
  source:     84,
  extraction: 76,
  claim:      76,
  report:     64,
  writeback:  64,
};

const COL_GAP = 72;   // horizontal gap between depth columns
const ROW_GAP = 18;   // vertical gap between siblings

// ── Public types ───────────────────────────────────────────────────────────────

export interface LineageRect {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  depth: number;
  node: LineageNode;
  parentId: string | null;
}

export interface LineageLayoutEdge {
  id: string;
  sourceId: string;
  targetId: string;
  sourceKind: LineageNodeKind;
  targetKind: LineageNodeKind;
}

export interface LineageLayoutResult {
  nodes: LineageRect[];
  edges: LineageLayoutEdge[];
  bounds: {
    width: number;
    height: number;
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  };
}

// ── Main layout function ───────────────────────────────────────────────────────

/**
 * Lay out the visible (expanded) lineage subtree as a left-to-right tree.
 *
 * Algorithm:
 * 1. Walk tree recursively, collecting visible nodes
 * 2. For each node, x = cumulative column offset for its depth
 * 3. Assign y by stacking children vertically, then center parent on its children
 * 4. Emit edges for every visible parent → child pair
 * 5. Compute bounds
 */
export function layoutLineage(
  roots: LineageNode[],
  expanded: Set<string>,
): LineageLayoutResult {
  const rects: LineageRect[] = [];
  const edges: LineageLayoutEdge[] = [];

  // Pass 1: collect column x-offsets by walking the tree
  const colX: number[] = [];
  buildColX(roots, expanded, colX, 0, 0);

  // Pass 2: assign y positions (bottom-up: place children, then center parent).
  // placeNode returns the vertical span its whole subtree occupies, so we advance
  // globalY by exactly this root's subtree — correct even with multiple roots.
  let globalY = 0;
  for (const root of roots) {
    const span = placeNode(root, null, 0, colX, expanded, rects, edges, { y: globalY });
    globalY = span.bottom + ROW_GAP;
  }

  // Compute bounds
  if (rects.length === 0) {
    return { nodes: [], edges: [], bounds: { width: 0, height: 0, minX: 0, minY: 0, maxX: 0, maxY: 0 } };
  }

  const minX = Math.min(...rects.map((r) => r.x));
  const minY = Math.min(...rects.map((r) => r.y));
  const maxX = Math.max(...rects.map((r) => r.x + r.w));
  const maxY = Math.max(...rects.map((r) => r.y + r.h));

  return {
    nodes: rects,
    edges,
    bounds: { width: maxX - minX, height: maxY - minY, minX, minY, maxX, maxY },
  };
}

/** Recursively build cumulative x-offset per depth column. */
function buildColX(
  nodes: LineageNode[],
  expanded: Set<string>,
  colX: number[],
  depth: number,
  prevRight: number,
): void {
  if (nodes.length === 0) return;

  // Width for this column is the widest kind among nodes at this depth
  const colWidth = Math.max(...nodes.map((n) => KIND_WIDTH[n.kind]));

  if (colX[depth] === undefined) {
    colX[depth] = prevRight;
  } else {
    colX[depth] = Math.max(colX[depth], prevRight);
  }

  const nextPrevRight = colX[depth]! + colWidth + COL_GAP;

  for (const node of nodes) {
    if (expanded.has(node.id) && node.children.length > 0) {
      buildColX(node.children, expanded, colX, depth + 1, nextPrevRight);
    }
  }
}

interface YCursor { y: number }

/**
 * Place a node and all its visible children.
 * Returns the vertical span [topY, bottomY] occupied by this node's subtree.
 */
function placeNode(
  node: LineageNode,
  parentId: string | null,
  depth: number,
  colX: number[],
  expanded: Set<string>,
  rects: LineageRect[],
  edges: LineageLayoutEdge[],
  cursor: YCursor,
): { top: number; bottom: number } {
  const x = colX[depth] ?? (depth * (260 + COL_GAP));
  const w = KIND_WIDTH[node.kind];
  const h = KIND_HEIGHT[node.kind];
  const visibleChildren = expanded.has(node.id) ? node.children : [];

  if (visibleChildren.length === 0) {
    // Leaf: place at cursor.y. The inbound edge is emitted by the parent's
    // children loop (below), so leaves never emit their own edge — this is what
    // keeps the edge set free of duplicates.
    const y = cursor.y;
    rects.push({ id: node.id, x, y, w, h, depth, node, parentId });
    cursor.y += h + ROW_GAP;
    return { top: y, bottom: y + h };
  }

  // Non-leaf: place children first, then center parent on them
  const childStartY = cursor.y;
  const childSpans: Array<{ top: number; bottom: number }> = [];

  // Reserve placeholder index for this node (we'll update y after children)
  const nodeIdx = rects.length;
  rects.push({ id: node.id, x, y: childStartY /* temp */, w, h, depth, node, parentId });

  for (const child of visibleChildren) {
    const span = placeNode(child, node.id, depth + 1, colX, expanded, rects, edges, cursor);
    childSpans.push(span);
    edges.push({
      id: `edge:${node.id}->${child.id}`,
      sourceId: node.id,
      targetId: child.id,
      sourceKind: node.kind,
      targetKind: child.kind,
    });
  }

  // Center parent on midpoint of first and last child centers
  const firstChild = childSpans[0];
  const lastChild = childSpans[childSpans.length - 1];
  let centeredY = childStartY;
  if (firstChild && lastChild) {
    const firstCenter = firstChild.top + (firstChild.bottom - firstChild.top) / 2;
    const lastCenter = lastChild.top + (lastChild.bottom - lastChild.top) / 2;
    centeredY = (firstCenter + lastCenter) / 2 - h / 2;
  }

  // Update the placeholder
  rects[nodeIdx] = { ...rects[nodeIdx]!, y: centeredY };

  const subtreeTop = Math.min(centeredY, childSpans[0]?.top ?? centeredY);
  const subtreeBottom = Math.max(centeredY + h, lastChild ? lastChild.bottom : centeredY + h);

  return { top: subtreeTop, bottom: subtreeBottom };
}

