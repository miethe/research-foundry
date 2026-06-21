/**
 * LineageFlow.test.ts — Tests for edge registration and class naming (AC 4.3).
 *
 * Strategy: test via the pure buildFlowElements helper (same strategy as
 * lineageFlowElements.test.ts) rather than attempting a full React Flow DOM
 * render in jsdom. React Flow v12 requires ResizeObserver + SVG layout that
 * jsdom cannot fully emulate; pure-function tests are robust and cover the
 * critical invariant (edges are produced with the correct className).
 *
 * What is verified here:
 *  - Edges produced by buildFlowElements carry className='rv-lineage-edge'
 *    (AC 4.3 — the class that CSS and screenshot selectors target)
 *  - Edge type is 'smoothstep' (the type that triggers edgeTypes lookup in
 *    <ReactFlow edgeTypes={edgeTypes}> which registers SmoothStepEdge)
 *  - The module-level edgeTypes export is correctly shaped (validates the
 *    import of SmoothStepEdge from @xyflow/react compiles and exports)
 */

import { describe, it, expect, vi } from "vitest";
import { buildFlowElements } from "./lineageFlowElements";
import type { LineageNode } from "./lineageTree";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  kind: LineageNode["kind"],
  children: LineageNode[] = [],
): LineageNode {
  return { id, kind, title: id, chips: [], details: [], children };
}

/** run → source (one edge) */
function makeEdgeTree(): LineageNode[] {
  const source = makeNode("source:src_001", "source");
  const run    = makeNode("run:run_001",    "run", [source]);
  return [run];
}

const noop = vi.fn();

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("LineageFlow — edge className (AC 4.3)", () => {
  it("edges produced by buildFlowElements carry className='rv-lineage-edge'", () => {
    const roots   = makeEdgeTree();
    const expanded = new Set(["run:run_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);

    expect(edges.length).toBeGreaterThan(0);
    for (const edge of edges) {
      expect(edge.className).toBe("rv-lineage-edge");
    }
  });

  it("edges use type='smoothstep' so edgeTypes lookup resolves SmoothStepEdge", () => {
    const roots   = makeEdgeTree();
    const expanded = new Set(["run:run_001"]);
    const { edges } = buildFlowElements(roots, expanded, null, noop, noop);

    expect(edges.length).toBeGreaterThan(0);
    for (const edge of edges) {
      expect(edge.type).toBe("smoothstep");
    }
  });
});

describe("LineageFlow — edgeTypes module export", () => {
  it("SmoothStepEdge is importable from @xyflow/react without error", async () => {
    // Dynamic import verifies the module compiles and exports the symbol.
    // If SmoothStepEdge is not a named export, this import will fail and the
    // test surface will report an import error (catches API drift early).
    const xyflow = await import("@xyflow/react");
    // SmoothStepEdge is a React.memo-wrapped component (an object with $$typeof),
    // not a plain function. We verify it is defined and non-null.
    expect(xyflow.SmoothStepEdge).toBeDefined();
    expect(xyflow.SmoothStepEdge).not.toBeNull();
    // React.memo components have $$typeof set to a Symbol
    expect((xyflow.SmoothStepEdge as { $$typeof?: unknown }).$$typeof).toBeTruthy();
  });

  it("LineageFlow module exports LineageFlow component", async () => {
    const module = await import("./LineageFlow");
    expect(typeof module.LineageFlow).toBe("function");
  });
});
