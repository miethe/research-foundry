/**
 * AssertionOnlyLineage.tsx — P6-003 typed assertion-relationship lineage
 * (reusable assertion ledger reviewer experience v1, §5.4, §6.E).
 *
 * Self-contained: has its own ReactFlow instance with its own nodeTypes/
 * edgeTypes registered at module scope (React Flow silently renders nothing
 * if a custom node/edge type used in `nodes`/`edges` isn't present in these
 * maps — see LineageFlow.tsx for the existing claim-lineage precedent this
 * mirrors). This avoids touching the tested claim-lineage tree/flow modules
 * (lineageTree.ts, lineageFlowElements.ts, LineageFlow.tsx), which model a
 * fundamentally different object graph (run → source → extraction → claim →
 * report → writeback) than the assertion chain here (source edition →
 * passage → source assertion → report/run uses, with inference hanging
 * below).
 *
 * Data sources: useEvidencePacket() for the rich inspector fields (qualifiers,
 * access, rights, freshness) and useAssertionLineage() for the typed
 * relationship/use chain — the frozen AssertionLineage DTO does not carry
 * qualifiers/access/rights itself (see report "seam gaps").
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  useAssertionLineage,
  useClearAssertionStateOnWorkspaceChange,
  useEvidencePacket,
  selectPacketLifecycle,
  selectPacketObject,
  selectPacketSubject,
} from "@/hooks/useAssertions";
import { readString, readStringArray, assertionSignature } from "@/components/ClaimLedger/AssertionAuditPanel";
import { accessScopeDisplay, lifecycleDisplay, reuseDecisionDisplay } from "@/components/AssertionCatalog/assertionDisplay";
import { useAuth } from "@/auth/AuthContext";
import { isCanonicalClaimsEnabled } from "@/lib/canonicalClaimsFlag";
import type { AssertionLineage, EvidencePacket } from "@/types/rf/assertions_api.generated";
import { LineageList } from "./LineageList";
import type { LineageNode, LineageNodeKind } from "./lineageTree";

export interface AssertionOnlyLineageProps {
  assertionId: string | null;
  onOpenProvenance?: (assertionId: string) => void;
  onViewPriorUses?: (assertionId: string) => void;
}

// ── Chain node ───────────────────────────────────────────────────────────────

interface ChainNodeData {
  eyebrow: string;
  title: string;
  subtitle?: string;
  pills?: string[];
  selected?: boolean;
  [key: string]: unknown;
}

type ChainNode = Node<ChainNodeData>;

function ChainNodeComponent({ data }: NodeProps<ChainNode>) {
  return (
    <div className={`rv-assertion-lnode${data.selected ? " rv-assertion-lnode--selected" : ""}`}>
      <span className="rv-assertion-lnode__eyebrow">{data.eyebrow}</span>
      <strong className="rv-assertion-lnode__title">{data.title}</strong>
      {data.subtitle && <code className="rv-assertion-lnode__subtitle">{data.subtitle}</code>}
      {data.pills && data.pills.length > 0 && (
        <div className="rv-assertion-lnode__pills">
          {data.pills.map((pill) => (
            <span key={pill} className="it-chip">{pill}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Inference node ───────────────────────────────────────────────────────────

interface InferenceNodeData {
  text: string;
  inputs: readonly string[];
  [key: string]: unknown;
}

type InferenceNode = Node<InferenceNodeData>;

function InferenceNodeComponent({ data }: NodeProps<InferenceNode>) {
  return (
    <div className="rv-assertion-lnode rv-assertion-lnode--inference">
      <span className="rv-assertion-lnode__inference-label" aria-hidden="false">
        INFERENCE · DERIVED
      </span>
      <span className="rv-assertion-lnode__title">{data.text}</span>
      {data.inputs.length > 0 && (
        <code className="rv-assertion-lnode__inputs">Inputs: {data.inputs.join(", ")}</code>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = {
  assertionChain: ChainNodeComponent,
  assertionInference: InferenceNodeComponent,
};

// ── Keyboard/mobile list alternative ────────────────────────────────────────

/**
 * Adapts the assertion chain to the established LineageList contract. This
 * keeps the existing tree keyboard controls, focus treatment, and hierarchy
 * affordances rather than maintaining a second list implementation.
 */
function buildAssertionLineageList(
  packet: EvidencePacket | undefined,
  lineage: AssertionLineage | undefined,
): LineageNode[] {
  const { nodes } = buildFlowElements(packet, lineage);
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const toListNode = (id: string): LineageNode | undefined => {
    const node = byId.get(id);
    if (!node) return undefined;
    const isInference = node.type === "assertionInference";
    const data = node.data as ChainNodeData | InferenceNodeData;
    const inferenceData = data as InferenceNodeData;
    const chainData = data as ChainNodeData;
    const kind: LineageNodeKind = id === "edition"
      ? "source"
      : id === "passage"
        ? "extraction"
        : id === "uses"
          ? "report"
          : "claim";
    const label = isInference
      ? "Inference · derived"
      : id === "edition"
        ? "Source edition"
        : id === "passage"
          ? "Passage"
          : id === "assertion"
            ? "Source assertion"
            : "Report / run uses";
    const title = isInference ? inferenceData.text : chainData.title;
    return {
      id,
      kind,
      title: `${label} · ${title}`,
      subtitle: isInference ? undefined : chainData.subtitle,
      chips: isInference ? inferenceData.inputs.map((input) => `Input: ${input}`) : chainData.pills,
      children: [],
    };
  };

  const edition = toListNode("edition");
  const passage = toListNode("passage");
  const assertion = toListNode("assertion");
  if (!edition || !passage || !assertion) return [];

  edition.children = [passage];
  passage.children = [assertion];
  const inferences = nodes
    .filter((node) => node.id.startsWith("inference-"))
    .map((node) => toListNode(node.id))
    .filter((node): node is LineageNode => Boolean(node));
  const uses = toListNode("uses");
  assertion.children = uses ? [...inferences, uses] : inferences;
  return [edition];
}

// ── Relationship classification (defensive, mirrors selectPacketSubject) ─────

function isInferenceRelationship(relationship: Record<string, unknown>): boolean {
  const rawKind = relationship.kind ?? relationship.record_type ?? relationship.type;
  return rawKind === "inference" || rawKind === "inference_record";
}

function buildFlowElements(
  packet: EvidencePacket | undefined,
  lineage: AssertionLineage | undefined,
): { nodes: ChainNode[] | (ChainNode | InferenceNode)[]; edges: Edge[] } {
  const nodes: (ChainNode | InferenceNode)[] = [];
  const edges: Edge[] = [];
  if (!packet) return { nodes, edges };

  const sourceEdition = selectPacketObject(packet, "source_edition");
  const passage = selectPacketObject(packet, "passage");
  const subject = selectPacketSubject(packet);
  const assertionText = subject.kind === "source-assertion" ? readString(subject.assertion, "text", "assertion_text") : undefined;

  const editionId = readString(sourceEdition, "edition_id", "id", "source_edition_id");
  const passageId = readString(passage, "passage_id", "id");
  // normalized_text is the production EvidencePacket key.  Older aliases are
  // only fallbacks for legacy packets, never a fabricated passage.
  const passageText = readString(passage, "normalized_text", "text", "quote", "excerpt");
  const access = accessScopeDisplay(packet.access_scope);

  nodes.push({
    id: "edition",
    type: "assertionChain",
    position: { x: 0, y: 80 },
    draggable: false,
    selectable: false,
    data: { eyebrow: "Source edition", title: editionId ?? "Not recorded", subtitle: undefined, pills: [access.label] },
  });

  nodes.push({
    id: "passage",
    type: "assertionChain",
    position: { x: 260, y: 80 },
    draggable: false,
    selectable: false,
    data: { eyebrow: "Passage", title: passageText ?? "Not recorded", subtitle: passageId },
  });

  nodes.push({
    id: "assertion",
    type: "assertionChain",
    position: { x: 540, y: 80 },
    draggable: false,
    selectable: false,
    data: {
      eyebrow: "Source assertion",
      title: assertionText ?? "Source assertion",
      subtitle: assertionSignature(packet.assertion_id, packet.assertion_version),
      selected: true,
    },
  });

  edges.push(
    { id: "e-edition-passage", source: "edition", target: "passage", markerEnd: { type: MarkerType.ArrowClosed } },
    { id: "e-passage-assertion", source: "passage", target: "assertion", markerEnd: { type: MarkerType.ArrowClosed } },
  );

  // An unresolved/denied lineage is not evidence of zero downstream uses.
  // Render its labelled unavailable state separately instead of laundering it
  // into zero counts in a graph node.
  if (lineage) {
    const runCount = lineage.run_uses.length;
    const reportCount = lineage.report_uses.length;
    nodes.push({
      id: "uses",
      type: "assertionChain",
      position: { x: 820, y: 80 },
      draggable: false,
      selectable: false,
      data: {
        eyebrow: "Report / run uses",
        title: "Downstream uses",
        pills: [`${runCount} run${runCount === 1 ? "" : "s"}`, `${reportCount} report revision${reportCount === 1 ? "" : "s"}`],
      },
    });
    edges.push({ id: "e-assertion-uses", source: "assertion", target: "uses", markerEnd: { type: MarkerType.ArrowClosed } });
  }

  const relationships = lineage?.relationships ?? [];
  const inferenceRelationships = relationships.filter(isInferenceRelationship);
  inferenceRelationships.forEach((relationship, index) => {
    const id = `inference-${index}`;
    const text = readString(relationship, "text", "summary") ?? "Inference derived from linked assertions.";
    const inputs = readStringArray(relationship, "inputs", "source_assertion_ids", "from_assertions");
    nodes.push({
      id,
      type: "assertionInference",
      position: { x: 540, y: 280 + index * 160 },
      draggable: false,
      selectable: false,
      data: { text, inputs },
    });
    edges.push({
      id: `e-${id}-assertion`,
      source: id,
      target: "assertion",
      style: { stroke: "var(--it-purple-400)", strokeDasharray: "5,4" },
    });
  });

  return { nodes, edges };
}

// ── Inspector sections (spec §6.E) ───────────────────────────────────────────

function AssertionOnlyInspector({
  packet,
  lineage,
  onOpenProvenance,
  onViewPriorUses,
}: {
  packet: EvidencePacket;
  lineage: AssertionLineage | undefined;
  onOpenProvenance?: (assertionId: string) => void;
  onViewPriorUses?: (assertionId: string) => void;
}) {
  const lifecycleState = selectPacketLifecycle(packet);
  const lifecycle = lifecycleDisplay(lifecycleState);
  const access = accessScopeDisplay(packet.access_scope);
  const rights = packet.rights_decision && typeof packet.rights_decision.allowed === "boolean"
    ? packet.rights_decision
    : undefined;
  const reuse = reuseDecisionDisplay(rights);
  const qualifiers = selectPacketObject(packet, "qualifiers");
  const qualifierRows = qualifiers
    ? Object.entries(qualifiers).filter((entry): entry is [string, string | number] => typeof entry[1] === "string" || typeof entry[1] === "number")
    : [];
  const runCount = lineage?.run_uses.length;
  const reportCount = lineage?.report_uses.length;
  const priorUsesTotal = runCount !== undefined && reportCount !== undefined ? runCount + reportCount : undefined;

  return (
    <aside className="rv-lineage-detail" data-testid="assertion-only-inspector">
      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Durable identity</span>
        <div className="rv-assertion-lineage-detail__copy-row">
          <code>{packet.assertion_id}</code>
        </div>
      </div>

      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Lifecycle</span>
        <span className={`it-chip ${lifecycle.color}`.trim()}>
          {lifecycle.label}
        </span>
      </div>

      {qualifierRows.length > 0 && (
        <div className="rv-assertion-lineage-detail__section">
          <span className="rv-assertion-lineage-detail__label">Qualifiers</span>
          <dl className="rv-inspector-dl">
            {qualifierRows.map(([label, value]) => (
              <div key={label}>
                <dt>{humanizeLabel(label)}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Access</span>
        <span className={`it-chip ${access.color}`.trim()}>{access.label}</span>
      </div>

      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Reuse decision</span>
        <span className={`it-chip ${reuse.color}`.trim()}>
          {reuse.label}
        </span>
      </div>

      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Rights</span>
        {rights ? <div className="rv-assertion-lnode__pills">
          <span className={`it-chip ${reuse.color}`.trim()}>{rights.allowed ? "Reuse allowed" : "Reuse denied"}</span>
          {rights.reason_code && <span className="rv-assertion-muted">{rights.reason_code}</span>}
        </div> : <span className="rv-assertion-muted">Unavailable</span>}
      </div>

      <div className="rv-assertion-lineage-detail__section">
        <span className="rv-assertion-lineage-detail__label">Prior uses</span>
        {priorUsesTotal === undefined ? <span className="rv-assertion-muted">Unavailable</span> : onViewPriorUses ? <button
          type="button"
          className="it-btn ghost xs"
          onClick={() => onViewPriorUses(packet.assertion_id)}
          data-testid="view-prior-uses-btn"
        >
          {priorUsesTotal} total
        </button> : <span>{priorUsesTotal} total</span>}
      </div>

      {(onOpenProvenance || onViewPriorUses) && <div className="rv-lineage-detail__actions">
        {onOpenProvenance && <button type="button" className="it-btn ghost xs" onClick={() => onOpenProvenance(packet.assertion_id)}>
          Open provenance
        </button>}
        {onViewPriorUses && <button type="button" className="it-btn ghost xs" onClick={() => onViewPriorUses(packet.assertion_id)}>
          View prior uses
        </button>}
      </div>}
    </aside>
  );
}

function humanizeLabel(label: string): string {
  return label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Top-level component ───────────────────────────────────────────────────────

export function AssertionOnlyLineage({ assertionId, onOpenProvenance, onViewPriorUses }: AssertionOnlyLineageProps) {
  // Keep the incoming ID as a deliberate deep-link/selected-claim override,
  // but never carry that candidate across a workspace or auth-scope boundary.
  // The query hook's scoped cache key is not sufficient on its own: it would
  // otherwise issue a fresh request for the prior assertion under the new
  // authority before the user has selected it there.
  const [activeAssertionId, setActiveAssertionId] = useState<string | null>(assertionId);
  const [viewMode, setViewMode] = useState<"list" | "graph">("graph");
  const [selectedLineageNodeId, setSelectedLineageNodeId] = useState<string | null>(null);
  const [expandedListNodes, setExpandedListNodes] = useState<Set<string>>(new Set());
  const auth = useAuth();
  const assertionScope = !auth.isLoading && (auth.authMode === "none" || auth.identity !== null)
    ? `${auth.identity?.workspace_id ?? "public"}:${auth.identity ? `${auth.identity.user_id}:${auth.identity.roles.join(",")}` : auth.authMode}`
    : undefined;
  useEffect(() => {
    setActiveAssertionId(assertionId);
  }, [assertionId, assertionScope]);
  const clearActiveAssertion = useCallback(() => setActiveAssertionId(null), []);
  useClearAssertionStateOnWorkspaceChange(clearActiveAssertion);

  const { state: packetState } = useEvidencePacket(activeAssertionId);
  const { state: lineageState } = useAssertionLineage(activeAssertionId);
  const canonicalEnabled = isCanonicalClaimsEnabled();

  const packet = packetState.kind !== "loading" && packetState.kind !== "denied" && packetState.kind !== "error-with-retry"
    ? packetState.data
    : undefined;
  const lineage = lineageState.kind === "ready" ? lineageState.data : undefined;
  const lineageUnavailable =
    lineageState.kind === "denied" || lineageState.kind === "unavailable" || lineageState.kind === "error-with-retry" ||
    packetState.kind === "denied" || packetState.kind === "unavailable" || packetState.kind === "error-with-retry";

  const { nodes, edges } = useMemo(() => buildFlowElements(packet, lineage), [packet, lineage]);
  const listNodes = useMemo(() => buildAssertionLineageList(packet, lineage), [packet, lineage]);
  useEffect(() => {
    setExpandedListNodes(new Set(flattenLineageNodeIds(listNodes)));
  }, [listNodes]);
  const toggleListNode = useCallback((nodeId: string) => {
    setExpandedListNodes((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  return (
    <div className="rv-lineage rv-assertion-lineage" data-testid="assertion-only-lineage">
      <div className="rv-lineage-explorer__toolbar">
        <div>
          <span className="rv-kicker">Source-first lineage</span>
          <h2>Evidence to assertions and uses</h2>
        </div>
        <div className="rv-lineage-explorer__toolbar-right">
          <div className="rv-lineage-view-toggle it-seg" role="group" aria-label="Assertion lineage view mode">
            <button
              type="button"
              className={viewMode === "list" ? "active" : ""}
              aria-pressed={viewMode === "list"}
              data-testid="assertion-lineage-view-list"
              onClick={() => setViewMode("list")}
            >
              List
            </button>
            <button
              type="button"
              className={viewMode === "graph" ? "active" : ""}
              aria-pressed={viewMode === "graph"}
              data-testid="assertion-lineage-view-graph"
              onClick={() => setViewMode("graph")}
            >
              Graph
            </button>
          </div>
        </div>
      </div>

      {/* Never a disabled control or empty canonical lane — an info notice only (spec §5.4). */}
      {!canonicalEnabled && (
        <div className="rv-assertion-only-notice" data-testid="assertion-only-notice">
          <span className="rv-assertion-only-notice__icon" aria-hidden="true">
            <InfoIcon />
          </span>
          <div className="rv-assertion-only-notice__copy">
            <strong>Assertion-only mode</strong>
            <span>Canonical claim grouping is disabled pending an independently labeled merge audit.</span>
          </div>
        </div>
      )}

      {/* Distinct from assertion-only mode: canonical enabled but no data (spec §5.4). */}
      {canonicalEnabled && (
        <div className="rv-assertion-only-notice" data-testid="canonical-relationship-absent-notice">
          <div className="rv-assertion-only-notice__copy">
            <strong>No canonical relationship recorded</strong>
          </div>
        </div>
      )}

      <div className="rv-lineage-workspace">
        <div className="rv-lineage-main">
          {lineageUnavailable && (
            <p className="rv-assertion-lineage-unavailable" role="status" data-testid="assertion-lineage-unavailable">
              Lineage unavailable{lineageState.kind === "denied" ? `: ${lineageState.reasonCopy}` : "."}
            </p>
          )}
          <div className={`rv-assertion-lineage__canvas${viewMode === "list" ? " rv-assertion-lineage__canvas--hidden" : ""}`} data-testid="assertion-lineage-canvas">
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                panOnDrag
                zoomOnScroll
                fitView
                fitViewOptions={{ padding: 0.2, maxZoom: 1.1 }}
                proOptions={{ hideAttribution: true }}
              >
                <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="var(--it-border-subtle)" />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
          <div className={`rv-assertion-lineage__list${viewMode === "graph" ? " rv-assertion-lineage__list--hidden" : ""}`}>
            <LineageList
              roots={listNodes}
              ariaLabel="Assertion lineage explorer"
              expanded={expandedListNodes}
              onToggle={toggleListNode}
              selectedNodeId={selectedLineageNodeId}
              onSelectNode={setSelectedLineageNodeId}
            />
          </div>
        </div>

        {packet ? (
          <AssertionOnlyInspector
            packet={packet}
            lineage={lineage}
            onOpenProvenance={onOpenProvenance}
            onViewPriorUses={onViewPriorUses}
          />
        ) : (
          <div className="rv-lineage-detail rv-lineage-detail--empty" data-testid="assertion-only-inspector-empty">
            <p className="rv-lineage-detail__empty">Select a source assertion to inspect its lineage.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function flattenLineageNodeIds(nodes: readonly LineageNode[]): string[] {
  return nodes.flatMap((node) => [node.id, ...flattenLineageNodeIds(node.children)]);
}

function InfoIcon() {
  return (
    <svg width={18} height={18} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" />
      <line x1="8" y1="7" x2="8" y2="11" strokeLinecap="round" />
      <circle cx="8" cy="4.8" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export default AssertionOnlyLineage;
