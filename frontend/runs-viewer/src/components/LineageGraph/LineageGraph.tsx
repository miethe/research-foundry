/**
 * ArtifactLineageGraph — SVG DAG showing the provenance chain for a run.
 *
 * Pipeline: source_card → extraction_card → claim_ledger_entry → evidence_bundle → report
 *
 * Built from the run.json export data (claims[], claim_counts, verification).
 * No @xyflow/react required — rendered as plain SVG for simplicity and zero
 * additional bundle cost beyond what is needed.
 *
 * Node types with verdict badge decorations:
 *   - source_card       (per unique source_card_id in claims[])
 *   - extraction_card   (inferred: one per source_card)
 *   - claim_ledger      (counts summary node)
 *   - evidence_bundle   (verdict: verified/unverified from run.verification)
 *   - report            (verdict: published/synthesized from status_derived)
 *
 * Graceful empty-state when claims[] is empty.
 */

import type { RFRunExport } from "@/types/rf";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DAGNode {
  id:      string;
  label:   string;
  kind:    "source_card" | "extraction_card" | "claim_ledger" | "evidence_bundle" | "report";
  verdict?: "pass" | "fail" | "pending" | null;
  count?:  number;
}

interface DAGEdge {
  from: string;
  to:   string;
}

// ── Layout constants ──────────────────────────────────────────────────────────

const NODE_W   = 140;
const NODE_H   = 48;
const H_GAP    = 60;   // horizontal gap between columns
const V_GAP    = 16;   // vertical gap between nodes in same column
const PAD      = 24;   // SVG padding

// ── Color map ─────────────────────────────────────────────────────────────────

const KIND_COLORS: Record<DAGNode["kind"], { fill: string; stroke: string; text: string }> = {
  source_card:     { fill: "#eff6ff", stroke: "#3b6fbd", text: "#1e3a6a" },
  extraction_card: { fill: "#f0fdf4", stroke: "#2f8f4a", text: "#14532d" },
  claim_ledger:    { fill: "#fefce8", stroke: "#b88a2b", text: "#78350f" },
  evidence_bundle: { fill: "#faf5ff", stroke: "#6f56c2", text: "#3b0764" },
  report:          { fill: "#fff7ed", stroke: "#c2641a", text: "#7c2d12" },
};

const VERDICT_COLORS = {
  pass:    { bg: "#dcfce7", text: "#15803d" },
  fail:    { bg: "#fee2e2", text: "#b91c1c" },
  pending: { bg: "#f1f5f9", text: "#475569" },
};

// ── Build DAG from run export ─────────────────────────────────────────────────

function buildDAG(run: RFRunExport): { columns: DAGNode[][]; edges: DAGEdge[] } {
  const sourceIds = Array.from(
    new Set(
      run.claims.flatMap((c) => c.sources.map((s) => s.source_card_id))
    )
  );

  // Column 0: source cards (up to 6; summarize if more)
  const MAX_SOURCES = 6;
  const sourceNodes: DAGNode[] = sourceIds.slice(0, MAX_SOURCES).map((id) => ({
    id:    `src_${id}`,
    label: id.length > 18 ? id.slice(0, 15) + "…" : id,
    kind:  "source_card",
  }));
  if (sourceIds.length > MAX_SOURCES) {
    sourceNodes.push({
      id:    "src_more",
      label: `+${sourceIds.length - MAX_SOURCES} more`,
      kind:  "source_card",
    });
  }

  // Column 1: extraction cards (one per source)
  const extractionNodes: DAGNode[] = sourceNodes.map((s) => ({
    id:    `ext_${s.id}`,
    label: "Extraction",
    kind:  "extraction_card",
  }));

  // Column 2: claim ledger (single summary node)
  const claimLedgerNode: DAGNode = {
    id:     "claim_ledger",
    label:  "Claim Ledger",
    kind:   "claim_ledger",
    count:  run.claim_counts?.total ?? run.claims.length,
  };

  // Column 3: evidence bundle
  const bundleVerdict =
    run.verification?.passed === true ? "pass" :
    run.verification?.passed === false ? "fail" :
    "pending";

  const bundleNode: DAGNode = {
    id:      "evidence_bundle",
    label:   "Evidence Bundle",
    kind:    "evidence_bundle",
    verdict: bundleVerdict,
  };

  // Column 4: report
  const reportVerdict =
    run.status_derived === "published" || run.status_derived === "verified" ? "pass" :
    run.status_derived === "synthesized" ? "pending" :
    "pending";

  const reportNode: DAGNode = {
    id:      "report",
    label:   "Report",
    kind:    "report",
    verdict: reportVerdict,
  };

  // Edges
  const edges: DAGEdge[] = [];

  sourceNodes.forEach((sn, i) => {
    edges.push({ from: sn.id, to: extractionNodes[i]!.id });
    edges.push({ from: extractionNodes[i]!.id, to: "claim_ledger" });
  });
  edges.push({ from: "claim_ledger", to: "evidence_bundle" });
  edges.push({ from: "evidence_bundle", to: "report" });

  return {
    columns: [sourceNodes, extractionNodes, [claimLedgerNode], [bundleNode], [reportNode]],
    edges,
  };
}

// ── SVG rendering ─────────────────────────────────────────────────────────────

function computeLayout(columns: DAGNode[][]): {
  nodePositions: Map<string, { x: number; y: number }>;
  totalW: number;
  totalH: number;
} {
  const positions = new Map<string, { x: number; y: number }>();
  let totalH = 0;

  columns.forEach((col) => {
    const colH = col.length * NODE_H + (col.length - 1) * V_GAP;
    if (colH > totalH) totalH = colH;
  });

  columns.forEach((col, colIdx) => {
    const colH   = col.length * NODE_H + (col.length - 1) * V_GAP;
    const startY = PAD + (totalH - colH) / 2; // vertically center each column
    const x      = PAD + colIdx * (NODE_W + H_GAP);

    col.forEach((node, rowIdx) => {
      positions.set(node.id, {
        x,
        y: startY + rowIdx * (NODE_H + V_GAP),
      });
    });
  });

  const totalW = PAD + columns.length * (NODE_W + H_GAP) - H_GAP + PAD;
  return { nodePositions: positions, totalW, totalH: totalH + 2 * PAD };
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ArtifactLineageGraphProps {
  run: RFRunExport;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ArtifactLineageGraph({ run }: ArtifactLineageGraphProps) {
  if (run.claims.length === 0) {
    return (
      <div className="rv-lineage rv-lineage--empty" data-testid="lineage-empty">
        <p className="rv-lineage__empty-msg">No lineage data available for this run.</p>
      </div>
    );
  }

  const { columns, edges } = buildDAG(run);
  const allNodes = columns.flat();
  const { nodePositions, totalW, totalH } = computeLayout(columns);

  return (
    <div className="rv-lineage" data-testid="lineage-graph">
      <svg
        className="rv-lineage__svg"
        width={totalW}
        height={totalH}
        viewBox={`0 0 ${totalW} ${totalH}`}
        aria-label="Artifact lineage graph"
        role="img"
        data-testid="lineage-svg"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="7"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
          </marker>
        </defs>

        {/* ── Edges ── */}
        {edges.map((edge) => {
          const from = nodePositions.get(edge.from);
          const to   = nodePositions.get(edge.to);
          if (!from || !to) return null;

          const x1 = from.x + NODE_W;
          const y1 = from.y + NODE_H / 2;
          const x2 = to.x;
          const y2 = to.y + NODE_H / 2;
          const mx = (x1 + x2) / 2;

          return (
            <path
              key={`${edge.from}-${edge.to}`}
              d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="1.5"
              markerEnd="url(#arrowhead)"
              data-testid={`lineage-edge-${edge.from}-${edge.to}`}
            />
          );
        })}

        {/* ── Nodes ── */}
        {allNodes.map((node) => {
          const pos    = nodePositions.get(node.id);
          if (!pos) return null;

          const colors = KIND_COLORS[node.kind];
          const hasVerdict = node.verdict != null;
          const verdictColors = node.verdict ? VERDICT_COLORS[node.verdict] : null;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x},${pos.y})`}
              data-testid={`lineage-node-${node.id}`}
              data-kind={node.kind}
              data-verdict={node.verdict ?? undefined}
            >
              {/* Node rect */}
              <rect
                width={NODE_W}
                height={NODE_H}
                rx="8"
                ry="8"
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth="1.5"
              />

              {/* Kind label */}
              <text
                x={NODE_W / 2}
                y={hasVerdict ? NODE_H / 2 - 6 : NODE_H / 2 + 5}
                textAnchor="middle"
                fontSize="11"
                fontWeight="600"
                fill={colors.text}
                fontFamily="var(--it-font-sans, system-ui, sans-serif)"
              >
                {node.label}
              </text>

              {/* Count badge */}
              {node.count != null && (
                <text
                  x={NODE_W / 2}
                  y={NODE_H / 2 + 12}
                  textAnchor="middle"
                  fontSize="10"
                  fill={colors.text}
                  opacity="0.7"
                  fontFamily="var(--it-font-mono, monospace)"
                >
                  {node.count} claims
                </text>
              )}

              {/* Verdict badge */}
              {hasVerdict && verdictColors && (
                <g transform={`translate(${NODE_W / 2 - 22},${NODE_H / 2 + 4})`}>
                  <rect
                    width="44"
                    height="16"
                    rx="8"
                    fill={verdictColors.bg}
                  />
                  <text
                    x="22"
                    y="11"
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="700"
                    fill={verdictColors.text}
                    fontFamily="var(--it-font-sans, system-ui, sans-serif)"
                    data-testid={`lineage-verdict-${node.id}`}
                  >
                    {node.verdict === "pass" ? "PASS" : node.verdict === "fail" ? "FAIL" : "PENDING"}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="rv-lineage__legend">
        {(Object.entries(KIND_COLORS) as [DAGNode["kind"], typeof KIND_COLORS[DAGNode["kind"]]][]).map(([kind, c]) => (
          <span key={kind} className="rv-lineage__legend-item">
            <span
              className="rv-lineage__legend-dot"
              style={{ background: c.fill, border: `1.5px solid ${c.stroke}` }}
            />
            <span className="rv-lineage__legend-label">{kind.replace(/_/g, " ")}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export default ArtifactLineageGraph;
