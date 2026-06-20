/**
 * lineageLayout.test.ts — Unit tests for layoutLineage().
 *
 * Covers: source-first ordering, only-expanded children included,
 * parent vertical centering on children, edge kinds, bounds computation,
 * and collapse hiding descendants.
 */

import { describe, it, expect } from "vitest";
import { layoutLineage } from "./lineageLayout";
import type { LineageNode } from "./lineageTree";

// ── Fixtures ───────────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  kind: LineageNode["kind"],
  children: LineageNode[] = [],
): LineageNode {
  return {
    id,
    kind,
    title: id,
    chips: [],
    details: [],
    children,
  };
}

/** Minimal source-first tree: run → source → extraction → claim */
function makeSimpleTree(): LineageNode[] {
  const claim      = makeNode("claim:clm_001",                "claim");
  const extraction = makeNode("extraction:src_001:ev_001",    "extraction", [claim]);
  const source     = makeNode("source:src_001",               "source",     [extraction]);
  const run        = makeNode("run:run_001",                  "run",        [source]);
  return [run];
}

/** Two-source tree to test sibling spacing */
function makeTwoSourceTree(): LineageNode[] {
  const claim1     = makeNode("claim:clm_001", "claim");
  const claim2     = makeNode("claim:clm_002", "claim");
  const ext1       = makeNode("extraction:src_001:ev_001", "extraction", [claim1]);
  const ext2       = makeNode("extraction:src_002:ev_002", "extraction", [claim2]);
  const source1    = makeNode("source:src_001", "source", [ext1]);
  const source2    = makeNode("source:src_002", "source", [ext2]);
  const run        = makeNode("run:run_001",    "run",    [source1, source2]);
  return [run];
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("layoutLineage — empty input", () => {
  it("returns empty result for empty roots", () => {
    const result = layoutLineage([], new Set());
    expect(result.nodes).toHaveLength(0);
    expect(result.edges).toHaveLength(0);
    expect(result.bounds.width).toBe(0);
    expect(result.bounds.height).toBe(0);
  });
});

describe("layoutLineage — only root visible (nothing expanded)", () => {
  it("renders only the run root when nothing is expanded", () => {
    const roots = makeSimpleTree();
    const expanded = new Set<string>(); // nothing expanded

    const result = layoutLineage(roots, expanded);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0]?.id).toBe("run:run_001");
  });

  it("produces no edges when only root is visible", () => {
    const roots = makeSimpleTree();
    const result = layoutLineage(roots, new Set());
    expect(result.edges).toHaveLength(0);
  });
});

describe("layoutLineage — expanding root shows children", () => {
  it("expanding run reveals source child", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);

    const result = layoutLineage(roots, expanded);
    const ids = result.nodes.map((n) => n.id);
    expect(ids).toContain("run:run_001");
    expect(ids).toContain("source:src_001");
    expect(ids).not.toContain("extraction:src_001:ev_001");
  });

  it("expanding run + source reveals extraction", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001"]);

    const result = layoutLineage(roots, expanded);
    const ids = result.nodes.map((n) => n.id);
    expect(ids).toContain("extraction:src_001:ev_001");
    expect(ids).not.toContain("claim:clm_001");
  });

  it("full expansion shows all four nodes", () => {
    const roots = makeSimpleTree();
    const expanded = new Set([
      "run:run_001",
      "source:src_001",
      "extraction:src_001:ev_001",
    ]);

    const result = layoutLineage(roots, expanded);
    expect(result.nodes).toHaveLength(4);
  });
});

describe("layoutLineage — source-first ordering", () => {
  it("source node appears before extraction in nodes array", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001"]);

    const result = layoutLineage(roots, expanded);
    const sourceIdx = result.nodes.findIndex((n) => n.id === "source:src_001");
    const extractIdx = result.nodes.findIndex((n) => n.id === "extraction:src_001:ev_001");
    expect(sourceIdx).toBeLessThan(extractIdx);
  });

  it("run node is first in nodes array", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001", "extraction:src_001:ev_001"]);
    const result = layoutLineage(roots, expanded);
    expect(result.nodes[0]?.id).toBe("run:run_001");
  });
});

describe("layoutLineage — horizontal tree layout (x positions)", () => {
  it("run node is in column 0 (leftmost x)", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001"]);
    const result = layoutLineage(roots, expanded);

    const runNode    = result.nodes.find((n) => n.id === "run:run_001")!;
    const sourceNode = result.nodes.find((n) => n.id === "source:src_001")!;

    expect(runNode.x).toBeLessThan(sourceNode.x);
    expect(runNode.depth).toBe(0);
  });

  it("each depth level has a greater x than its parent", () => {
    const roots = makeSimpleTree();
    const expanded = new Set([
      "run:run_001",
      "source:src_001",
      "extraction:src_001:ev_001",
    ]);
    const result = layoutLineage(roots, expanded);

    const sorted = [...result.nodes].sort((a, b) => a.depth - b.depth);
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i]!.x).toBeGreaterThan(sorted[i - 1]!.x);
    }
  });
});

describe("layoutLineage — parent vertical centering", () => {
  it("run node y is centered between its two source children", () => {
    const roots = makeTwoSourceTree();
    const expanded = new Set(["run:run_001"]);
    const result = layoutLineage(roots, expanded);

    const runNode     = result.nodes.find((n) => n.id === "run:run_001")!;
    const source1     = result.nodes.find((n) => n.id === "source:src_001")!;
    const source2     = result.nodes.find((n) => n.id === "source:src_002")!;

    const source1Center = source1.y + source1.h / 2;
    const source2Center = source2.y + source2.h / 2;
    const expectedRunCenter = (source1Center + source2Center) / 2;
    const actualRunCenter   = runNode.y + runNode.h / 2;

    // Allow 2px floating-point tolerance
    expect(Math.abs(actualRunCenter - expectedRunCenter)).toBeLessThan(2);
  });
});

describe("layoutLineage — edges carry sourceKind and targetKind", () => {
  it("edge run→source has correct kinds", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001"]);
    const result = layoutLineage(roots, expanded);

    const edge = result.edges.find(
      (e) => e.sourceId === "run:run_001" && e.targetId === "source:src_001",
    );
    expect(edge).toBeDefined();
    expect(edge?.sourceKind).toBe("run");
    expect(edge?.targetKind).toBe("source");
  });

  it("edge source→extraction has correct kinds", () => {
    const roots = makeSimpleTree();
    const expanded = new Set(["run:run_001", "source:src_001"]);
    const result = layoutLineage(roots, expanded);

    const edge = result.edges.find(
      (e) => e.sourceId === "source:src_001" && e.targetId === "extraction:src_001:ev_001",
    );
    expect(edge).toBeDefined();
    expect(edge?.sourceKind).toBe("source");
    expect(edge?.targetKind).toBe("extraction");
  });

  it("edge extraction→claim has correct kinds", () => {
    const roots = makeSimpleTree();
    const expanded = new Set([
      "run:run_001",
      "source:src_001",
      "extraction:src_001:ev_001",
    ]);
    const result = layoutLineage(roots, expanded);

    const edge = result.edges.find(
      (e) => e.targetId === "claim:clm_001",
    );
    expect(edge).toBeDefined();
    expect(edge?.sourceKind).toBe("extraction");
    expect(edge?.targetKind).toBe("claim");
  });
});

describe("layoutLineage — bounds computation", () => {
  it("bounds.minX is 0 for the leftmost node", () => {
    const roots = makeSimpleTree();
    const result = layoutLineage(roots, new Set());
    expect(result.bounds.minX).toBe(0);
  });

  it("bounds.width >= node width of root", () => {
    const roots = makeSimpleTree();
    const result = layoutLineage(roots, new Set());
    expect(result.bounds.width).toBeGreaterThanOrEqual(result.nodes[0]!.w);
  });

  it("bounds encompass all node rectangles", () => {
    const roots = makeSimpleTree();
    const expanded = new Set([
      "run:run_001",
      "source:src_001",
      "extraction:src_001:ev_001",
    ]);
    const result = layoutLineage(roots, expanded);

    for (const node of result.nodes) {
      expect(node.x).toBeGreaterThanOrEqual(result.bounds.minX);
      expect(node.y).toBeGreaterThanOrEqual(result.bounds.minY);
      expect(node.x + node.w).toBeLessThanOrEqual(result.bounds.maxX + 0.01);
      expect(node.y + node.h).toBeLessThanOrEqual(result.bounds.maxY + 0.01);
    }
  });
});

describe("layoutLineage — collapse hides descendants", () => {
  it("collapsing run hides source and all deeper nodes", () => {
    const roots = makeSimpleTree();
    // All were expanded; now collapse run
    const expanded = new Set<string>(); // run not in expanded
    const result = layoutLineage(roots, expanded);

    expect(result.nodes.map((n) => n.id)).not.toContain("source:src_001");
    expect(result.nodes.map((n) => n.id)).not.toContain("extraction:src_001:ev_001");
    expect(result.nodes.map((n) => n.id)).not.toContain("claim:clm_001");
  });

  it("collapsing source hides extraction but keeps source visible", () => {
    const roots = makeSimpleTree();
    // run is expanded, source is NOT expanded
    const expanded = new Set(["run:run_001"]);
    const result = layoutLineage(roots, expanded);

    const ids = result.nodes.map((n) => n.id);
    expect(ids).toContain("source:src_001");
    expect(ids).not.toContain("extraction:src_001:ev_001");
  });
});
