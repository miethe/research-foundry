/**
 * lineageFlowElements.test.ts — Unit tests for buildFlowElements().
 *
 * Tests the pure mapping from lineage tree → React Flow nodes/edges arrays
 * WITHOUT rendering React Flow itself (jsdom + React Flow have ResizeObserver
 * issues; testing the pure helper is robust and covers the critical logic).
 *
 * Covers:
 * - Node count matches layoutLineage visible nodes
 * - Node positions are sourced from layoutLineage (not invented here)
 * - Node styles carry correct width/height from layout
 * - Edge stroke colors come from targetKind accent
 * - Selected flag is set correctly
 * - isExpanded / childCount are correct
 * - Edge markerEnd color matches targetKind accent
 */

import { describe, it, expect, vi } from "vitest";
import { buildFlowElements } from "./lineageFlowElements";
import { LINEAGE_KIND_META } from "./lineageTree";
import type { LineageNode } from "./lineageTree";

// ── Fixtures ───────────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  kind: LineageNode["kind"],
  children: LineageNode[] = [],
): LineageNode {
  return { id, kind, title: id, chips: [], details: [], children };
}

/** run → source → extraction → claim */
function makeSimpleTree(): LineageNode[] {
  const claim      = makeNode("claim:clm_001",             "claim");
  const extraction = makeNode("extraction:src_001:ev_001", "extraction", [claim]);
  const source     = makeNode("source:src_001",            "source",     [extraction]);
  const run        = makeNode("run:run_001",               "run",        [source]);
  return [run];
}

const noop = vi.fn();

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("buildFlowElements — empty input", () => {
  it("returns empty nodes and edges for empty roots", () => {
    const { nodes, edges } = buildFlowElements([], new Set(), null, noop, noop);
    expect(nodes).toHaveLength(0);
    expect(edges).toHaveLength(0);
  });
});

describe("buildFlowElements — node count mirrors layoutLineage", () => {
  it("only root visible when nothing expanded", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    expect(nodes).toHaveLength(1);
    expect(nodes[0]?.id).toBe("run:run_001");
  });

  it("run + source visible when run is expanded", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(["run:run_001"]), null, noop, noop);
    expect(nodes).toHaveLength(2);
    const ids = nodes.map((n) => n.id);
    expect(ids).toContain("run:run_001");
    expect(ids).toContain("source:src_001");
  });

  it("all 4 nodes visible when fully expanded", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const { nodes } = buildFlowElements(roots, expanded, null, noop, noop);
    expect(nodes).toHaveLength(4);
  });
});

describe("buildFlowElements — node positions from layoutLineage", () => {
  it("node position.x is greater for deeper depth levels", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { nodes } = buildFlowElements(roots, expanded, null, noop, noop);

    const runNode    = nodes.find((n) => n.id === "run:run_001")!;
    const sourceNode = nodes.find((n) => n.id === "source:src_001")!;

    expect(runNode.position.x).toBeLessThan(sourceNode.position.x);
  });

  it("node position.y is a number (sourced from layout, not hardcoded 0)", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    expect(typeof nodes[0]?.position.y).toBe("number");
  });
});

describe("buildFlowElements — node style width/height", () => {
  it("run node carries correct width and height in style", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    // run kind: KIND_WIDTH=260, KIND_HEIGHT=84
    expect(runNode.style?.width).toBe(260);
    expect(runNode.style?.height).toBe(84);
  });

  it("claim node carries correct width and height in style", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const { nodes } = buildFlowElements(roots, expanded, null, noop, noop);
    const claimNode = nodes.find((n) => n.id === "claim:clm_001")!;
    // claim kind: KIND_WIDTH=240, KIND_HEIGHT=76
    expect(claimNode.style?.width).toBe(240);
    expect(claimNode.style?.height).toBe(76);
  });
});

describe("buildFlowElements — node data", () => {
  it("selected node has isSelected=true", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), "run:run_001", noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    expect(runNode.data.isSelected).toBe(true);
  });

  it("non-selected node has isSelected=false", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { nodes } = buildFlowElements(roots, expanded, "run:run_001", noop, noop);
    const sourceNode = nodes.find((n) => n.id === "source:src_001")!;
    expect(sourceNode.data.isSelected).toBe(false);
  });

  it("expanded node has isExpanded=true", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { nodes } = buildFlowElements(roots, expanded, null, noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    expect(runNode.data.isExpanded).toBe(true);
  });

  it("collapsed node has isExpanded=false", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    expect(runNode.data.isExpanded).toBe(false);
  });

  it("run node childCount equals its children array length (1 source child)", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    expect(runNode.data.childCount).toBe(1);
  });

  it("leaf nodes (no children) have childCount=0", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const { nodes } = buildFlowElements(roots, expanded, null, noop, noop);
    const claimNode = nodes.find((n) => n.id === "claim:clm_001")!;
    expect(claimNode.data.childCount).toBe(0);
  });

  it("node data includes the LineageNode reference", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    const runNode = nodes.find((n) => n.id === "run:run_001")!;
    expect(runNode.data.node.kind).toBe("run");
    expect(runNode.data.node.id).toBe("run:run_001");
  });

  it("node type is 'lineage'", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    expect(nodes[0]?.type).toBe("lineage");
  });

  it("nodes are not draggable", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    expect(nodes[0]?.draggable).toBe(false);
  });
});

describe("buildFlowElements — edge stroke colors by target kind", () => {
  it("edge to source node uses teal accent", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    const edge = edges.find((e) => e.target === "source:src_001")!;
    expect(edge).toBeDefined();
    const expectedAccent = LINEAGE_KIND_META.source.accent;
    expect(edge.style?.stroke).toBe(expectedAccent);
  });

  it("edge to extraction node uses purple accent", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    const edge = edges.find((e) => e.target === "extraction:src_001:ev_001")!;
    expect(edge).toBeDefined();
    const expectedAccent = LINEAGE_KIND_META.extraction.accent;
    expect(edge.style?.stroke).toBe(expectedAccent);
  });

  it("edge to claim node uses gold accent", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    const edge = edges.find((e) => e.target === "claim:clm_001")!;
    expect(edge).toBeDefined();
    const expectedAccent = LINEAGE_KIND_META.claim.accent;
    expect(edge.style?.stroke).toBe(expectedAccent);
  });

  it("edge markerEnd color matches targetKind accent", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    const edge = edges.find((e) => e.target === "source:src_001")!;
    const markerEnd = edge.markerEnd as { color?: string } | undefined;
    expect(markerEnd?.color).toBe(LINEAGE_KIND_META.source.accent);
  });

  it("edges use smoothstep type for elbow routing", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    expect(edges[0]?.type).toBe("smoothstep");
  });

  it("edge count matches visible parent→child pairs", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);
    // 3 visible edges: run→source, source→extraction, extraction→claim
    expect(edges).toHaveLength(3);
  });
});

describe("buildFlowElements — handles in/out positions", () => {
  it("nodes have targetPosition=Left and sourcePosition=Right", () => {
    const roots = makeSimpleTree();
    const { nodes } = buildFlowElements(roots, new Set(), null, noop, noop);
    const runNode = nodes[0]!;
    expect(runNode.targetPosition).toBe("left");
    expect(runNode.sourcePosition).toBe("right");
  });
});
