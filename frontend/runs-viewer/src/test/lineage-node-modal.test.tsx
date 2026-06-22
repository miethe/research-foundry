/**
 * lineage-node-modal.test.tsx — D4 tests (v2.3 Stage 2).
 *
 * Verifies:
 *  (D4-a) Single-click on a LineageList row fires onExpandNode (list mode now uses
 *         single-click, consistent with graph mode)
 *  (D4-b) DetailModal renders navigate action button when onNavigate provided + kind has a target
 *  (D4-c) Clicking navigate action fires onNavigate with correct tab/claimId
 *  (D4-d) No navigate button when onNavigate not provided (graceful)
 *  (D4-e) No navigate button for 'run' kind (omitted — already on run surface)
 *  (D4-f) Navigate button labels are correct per kind
 *  (D4-g) Clicking navigate fires onClose too (modal closes on navigate)
 *  (D4-h) Focus lands in modal when it opens (a11y: dialog has tabIndex=-1)
 *  (D4-i) Escape closes DetailModal (pre-existing, regression guard)
 *  (D4-j) Backdrop click closes DetailModal (pre-existing, regression guard)
 */

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { DetailModal } from "../components/RunDetail/DetailModal";
import type { DetailModalPayload } from "../components/RunDetail/DetailModal";
import type { LineageNode } from "../components/LineageGraph/lineageTree";
import { LineageList } from "../components/LineageGraph/LineageList";

// ── Wrapper ───────────────────────────────────────────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeNode(overrides: Partial<LineageNode> & { kind: LineageNode["kind"] }): LineageNode {
  return {
    id: `${overrides.kind}:test_001`,
    title: `Test ${overrides.kind} node`,
    chips: [],
    details: [],
    children: [],
    ...overrides,
  };
}

const CLAIM_NODE  = makeNode({ kind: "claim",      claimId: "clm_001", subtitle: "clm_001" });
const SOURCE_NODE = makeNode({ kind: "source",      subtitle: "src_001" });
const EXTRACT_NODE = makeNode({ kind: "extraction", subtitle: "ext_001" });
const REPORT_NODE  = makeNode({ kind: "report",     claimId: "clm_001" });
const WRITEBACK_NODE = makeNode({ kind: "writeback" });
const RUN_NODE    = makeNode({ kind: "run" });

// ── D4-a: LineageList row single-click fires onExpandNode ─────────────────────

describe("D4-a — LineageList row single-click fires onExpandNode", () => {
  const listNode: LineageNode = makeNode({ kind: "source", subtitle: "src_a" });

  it("single-click on a list row fires onExpandNode with the node", () => {
    const onSelectNode = vi.fn();
    const onExpandNode = vi.fn();
    const { container } = render(
      <LineageList
        roots={[listNode]}
        expanded={new Set()}
        onToggle={vi.fn()}
        selectedNodeId={null}
        onSelectNode={onSelectNode}
        onExpandNode={onExpandNode}
      />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='lineage-node-source:test_001']") as HTMLElement;
    act(() => { fireEvent.click(row); });
    expect(onExpandNode).toHaveBeenCalledOnce();
    expect(onExpandNode).toHaveBeenCalledWith(listNode);
  });

  it("single-click on a list row also fires onSelectNode", () => {
    const onSelectNode = vi.fn();
    const { container } = render(
      <LineageList
        roots={[listNode]}
        expanded={new Set()}
        onToggle={vi.fn()}
        selectedNodeId={null}
        onSelectNode={onSelectNode}
      />,
      { wrapper: makeWrapper() },
    );
    const row = container.querySelector("[data-testid='lineage-node-source:test_001']") as HTMLElement;
    act(() => { fireEvent.click(row); });
    expect(onSelectNode).toHaveBeenCalledOnce();
    expect(onSelectNode).toHaveBeenCalledWith(listNode.id);
  });
});

// ── D4-b: navigate button renders for applicable kinds ───────────────────────

describe("D4 — DetailModal navigate button renders for actionable node kinds", () => {
  const actionableNodes: [string, LineageNode][] = [
    ["claim",      CLAIM_NODE],
    ["source",     SOURCE_NODE],
    ["extraction", EXTRACT_NODE],
    ["report",     REPORT_NODE],
    ["writeback",  WRITEBACK_NODE],
  ];

  for (const [label, node] of actionableNodes) {
    it(`renders navigate button for '${label}' node when onNavigate provided`, () => {
      const payload: DetailModalPayload = { kind: "node", node };
      const { container } = render(
        <DetailModal payload={payload} onClose={vi.fn()} onNavigate={vi.fn()} />,
        { wrapper: makeWrapper() },
      );
      expect(container.querySelector("[data-testid='detail-modal-navigate']")).not.toBeNull();
    });
  }

  it("does NOT render navigate button for 'run' node (already on run surface)", () => {
    const payload: DetailModalPayload = { kind: "node", node: RUN_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='detail-modal-navigate']")).toBeNull();
  });
});

// ── D4-d: no navigate button when onNavigate not provided ────────────────────

describe("D4 — navigate button absent when onNavigate not provided", () => {
  it("no navigate button for claim node without onNavigate", () => {
    const payload: DetailModalPayload = { kind: "node", node: CLAIM_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='detail-modal-navigate']")).toBeNull();
  });

  it("no footer rendered without onNavigate", () => {
    const payload: DetailModalPayload = { kind: "node", node: SOURCE_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    expect(container.querySelector("[data-testid='detail-modal-footer']")).toBeNull();
  });
});

// ── D4-c: clicking navigate fires onNavigate with correct args ────────────────

describe("D4 — navigate action fires onNavigate with correct tab + claimId", () => {
  it("claim node → navigates to 'ledger' tab with claimId", () => {
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: CLAIM_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(onNavigate).toHaveBeenCalledOnce();
    const [tab, claimId] = onNavigate.mock.calls[0] as [string, string | undefined];
    expect(tab).toBe("ledger");
    // CLAIM_NODE has claimId='clm_001'
    expect(claimId).toBe("clm_001");
  });

  it("report node → navigates to 'report' tab with claimId", () => {
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: REPORT_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(onNavigate).toHaveBeenCalledOnce();
    const [tab] = onNavigate.mock.calls[0] as [string, string | undefined];
    expect(tab).toBe("report");
  });

  it("source node → navigates to 'lineage' tab", () => {
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: SOURCE_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(onNavigate).toHaveBeenCalledOnce();
    const [tab] = onNavigate.mock.calls[0] as [string, string | undefined];
    expect(tab).toBe("lineage");
  });

  it("extraction node → navigates to 'lineage' tab", () => {
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: EXTRACT_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    const [tab] = onNavigate.mock.calls[0] as [string, string | undefined];
    expect(tab).toBe("lineage");
  });

  it("writeback node → navigates to 'writeback' tab", () => {
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: WRITEBACK_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    const [tab] = onNavigate.mock.calls[0] as [string, string | undefined];
    expect(tab).toBe("writeback");
  });
});

// ── D4-g: clicking navigate fires onClose (modal closes) ─────────────────────

describe("D4 — clicking navigate action also closes the modal", () => {
  it("clicking navigate fires onClose", () => {
    const onClose = vi.fn();
    const onNavigate = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: CLAIM_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={onClose} onNavigate={onNavigate} />,
      { wrapper: makeWrapper() },
    );
    const btn = container.querySelector("[data-testid='detail-modal-navigate']") as HTMLElement;
    act(() => { fireEvent.click(btn); });
    expect(onClose).toHaveBeenCalledOnce();
  });
});

// ── D4-f: navigate button labels ─────────────────────────────────────────────

describe("D4 — navigate button labels match node kind", () => {
  const cases: [LineageNode["kind"], LineageNode, string][] = [
    ["claim",      CLAIM_NODE,      "Claim Ledger"],
    ["source",     SOURCE_NODE,     "Lineage"],
    ["extraction", EXTRACT_NODE,    "Lineage"],
    ["report",     REPORT_NODE,     "Report"],
    ["writeback",  WRITEBACK_NODE,  "Writeback"],
  ];

  for (const [kind, node, expectedFragment] of cases) {
    it(`'${kind}' node button label contains '${expectedFragment}'`, () => {
      const payload: DetailModalPayload = { kind: "node", node };
      const { container } = render(
        <DetailModal payload={payload} onClose={vi.fn()} onNavigate={vi.fn()} />,
        { wrapper: makeWrapper() },
      );
      const btn = container.querySelector("[data-testid='detail-modal-navigate']");
      expect(btn?.textContent).toContain(expectedFragment);
    });
  }
});

// ── D4-h: focus management (a11y) ─────────────────────────────────────────────

describe("D4 — focus management (a11y)", () => {
  it("dialog element has tabIndex=-1 (programmatic focus target)", () => {
    const payload: DetailModalPayload = { kind: "node", node: SOURCE_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    const dialog = container.querySelector("[data-testid='detail-modal']");
    expect(dialog?.getAttribute("tabindex")).toBe("-1");
  });

  it("dialog has role=dialog and aria-modal=true", () => {
    const payload: DetailModalPayload = { kind: "node", node: SOURCE_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={vi.fn()} />,
      { wrapper: makeWrapper() },
    );
    const dialog = container.querySelector("[data-testid='detail-modal']");
    expect(dialog?.getAttribute("role")).toBe("dialog");
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
  });
});

// ── D4-i: Escape closes DetailModal (regression guard) ───────────────────────

describe("D4 — Escape closes DetailModal (regression guard)", () => {
  it("Escape key fires onClose", () => {
    const onClose = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: CLAIM_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={onClose} />,
      { wrapper: makeWrapper() },
    );
    act(() => {
      fireEvent.keyDown(
        container.querySelector("[data-testid='detail-modal-overlay']") as HTMLElement,
        { key: "Escape" },
      );
    });
    expect(onClose).toHaveBeenCalledOnce();
  });
});

// ── D4-j: backdrop click closes DetailModal (regression guard) ────────────────

describe("D4 — backdrop click closes DetailModal (regression guard)", () => {
  it("clicking overlay backdrop fires onClose", () => {
    const onClose = vi.fn();
    const payload: DetailModalPayload = { kind: "node", node: SOURCE_NODE };
    const { container } = render(
      <DetailModal payload={payload} onClose={onClose} />,
      { wrapper: makeWrapper() },
    );
    const overlay = container.querySelector("[data-testid='detail-modal-overlay']") as HTMLElement;
    act(() => { fireEvent.click(overlay); });
    expect(onClose).toHaveBeenCalledOnce();
  });
});
