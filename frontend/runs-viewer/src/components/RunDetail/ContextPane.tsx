/**
 * ContextPane — consolidated context tab pane for RunDetailWorkspace (FR-14).
 *
 * Renders 4 collapsible sections in order, each collapsed by default.
 * Collapse state is persisted per run × panel in sessionStorage (resets on reload).
 *
 * Sections:
 *   1. Routing Decision  — model profile, rationale, est cost vs budget, sensitivity tier
 *   2. Research Brief    — renders research_brief_md via ReportRenderer (frontmatter stripped)
 *   3. Swarm Plan        — two-level collapsible tree (adapters → steps) + "Show raw" escape hatch
 *   4. Upstream Entities — badge links for intent_id / ibom_id / intenttree_node_id
 *
 * Schema guard: when schema_version < "1.3" OR run.context absent, renders a
 * single "Context not available for this run" empty-state instead of panels.
 *
 * Each section shows its own empty-state ("… not available for this run") when
 * its backing field is null/undefined — NEVER hard-destructures run.context.
 *
 * OQ-3 (SwarmPlan tree): two-level collapsible list (adapters → steps), depth
 * cap 3 levels, "Show raw" escape hatch for shapes beyond the typed tree.
 */

import { useState } from "react";
import type { RFRunExport } from "@/types/rf";
import type { RFRunContextSummary } from "@/types/rf/run-export";
import { RoutingDecisionCard, SwarmPlanSection } from "@/screens/SwarmScreen";
import { ReportRenderer } from "@/components/ReportOverlay/ReportRenderer";
import { ChevronDown, ChevronRight } from "@/components/LineageGraph/kindIcons";
import { useCollapseState } from "@/hooks/useCollapseState";
import "@/styles/context-pane.css";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ContextPaneProps {
  run: RFRunExport;
}

// ── Schema version helper ─────────────────────────────────────────────────────

/**
 * Returns true when the run's schema_version is at least "1.3".
 * Uses simple numeric version comparison on the first two semver parts.
 * Falls back to false when version is absent or unparseable (safe default).
 */
function isSchemaAtLeast13(schemaVersion: string | undefined): boolean {
  if (!schemaVersion) return false;
  const parts = schemaVersion.split(".").map(Number);
  const major = parts[0] ?? 0;
  const minor = parts[1] ?? 0;
  // 1.3, 1.4, 2.x, etc. are all >= 1.3
  if (major > 1) return true;
  if (major === 1 && minor >= 3) return true;
  return false;
}

// ── CollapsibleSection ────────────────────────────────────────────────────────

interface CollapsibleSectionProps {
  runId: string;
  panelId: string;
  title: string;
  /** Stable heading id suffix for aria-labelledby */
  headingId: string;
  children: React.ReactNode;
  testId?: string;
}

function CollapsibleSection({
  runId,
  panelId,
  title,
  headingId,
  children,
  testId,
}: CollapsibleSectionProps) {
  const { collapsed, toggle } = useCollapseState(runId, panelId);

  return (
    <section
      className="rv-context-pane__section"
      aria-labelledby={headingId}
      data-testid={testId}
      data-panel-id={panelId}
    >
      {/* Collapsible header — full-width button following lineage-list chevron pattern */}
      <button
        type="button"
        className="rv-context-pane__section-header"
        id={headingId}
        aria-expanded={!collapsed}
        onClick={toggle}
        data-testid={`${testId}-toggle`}
      >
        <span className="rv-context-pane__section-chevron" aria-hidden="true">
          {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </span>
        <span className="rv-context-pane__section-title">{title}</span>
      </button>

      {/* Body — rendered only when expanded */}
      {!collapsed && (
        <div
          className="rv-context-pane__section-body"
          role="region"
          aria-labelledby={headingId}
          data-testid={`${testId}-body`}
        >
          {children}
        </div>
      )}
    </section>
  );
}

// ── Section empty-state ───────────────────────────────────────────────────────

function SectionEmpty({ label }: { label: string }) {
  return (
    <p className="rv-context-pane__field-empty" data-testid="context-section-empty">
      {label} not available for this run.
    </p>
  );
}

// ── RoutingDecisionSection ────────────────────────────────────────────────────

interface RoutingDecisionSectionProps {
  decision: RFRunContextSummary["routing_decision"] | null | undefined;
}

/**
 * Renders the routing decision card with model profile, rationale, estimated
 * cost vs budget, and sensitivity tier. Falls back to RoutingDecisionCard from
 * SwarmScreen for the core decision + rationale; appends extra metadata rows
 * for est_cost_usd/budget_usd/sensitivity_tier when present in the record.
 */
function RoutingDecisionSection({ decision }: RoutingDecisionSectionProps) {
  if (!decision) {
    return <SectionEmpty label="Routing decision" />;
  }

  // Extract extra metadata fields beyond the typed {decision, rationale} pair.
  const estCostUsd =
    typeof decision["est_cost_usd"] === "number" ? decision["est_cost_usd"] : null;
  const budgetUsd =
    typeof decision["budget_usd"] === "number" ? decision["budget_usd"] : null;
  const sensitivityTier =
    typeof decision["sensitivity_tier"] === "string" ? decision["sensitivity_tier"] : null;

  return (
    <div data-testid="context-routing-decision">
      <RoutingDecisionCard decision={decision} />
      {(estCostUsd != null || budgetUsd != null || sensitivityTier != null) && (
        <dl
          className="rv-context-pane__routing-meta"
          data-testid="context-routing-meta"
        >
          {estCostUsd != null && (
            <div className="rv-context-pane__routing-meta-row" data-testid="context-routing-cost">
              <dt>Est. Cost</dt>
              <dd className="it-numeric">${estCostUsd.toFixed(4)}</dd>
            </div>
          )}
          {budgetUsd != null && (
            <div className="rv-context-pane__routing-meta-row" data-testid="context-routing-budget">
              <dt>Budget</dt>
              <dd className="it-numeric">${budgetUsd.toFixed(2)}</dd>
            </div>
          )}
          {sensitivityTier != null && (
            <div className="rv-context-pane__routing-meta-row" data-testid="context-routing-sensitivity">
              <dt>Sensitivity</dt>
              <dd>
                <span
                  className="it-chip rv-context-pane__sensitivity-chip"
                  data-sensitivity={sensitivityTier}
                >
                  {sensitivityTier}
                </span>
              </dd>
            </div>
          )}
        </dl>
      )}
    </div>
  );
}

// ── SwarmPlanTree (OQ-3) ──────────────────────────────────────────────────────

/**
 * Two-level collapsible tree for swarm_plan (OQ-3).
 *
 * Renders a top-level list of "adapters" or plan keys, each expandable to show
 * nested step/field detail. Depth is capped at 3 levels of nesting.
 *
 * Falls back to a "Show raw" toggle with the raw-YAML/JSON view for shapes that
 * fall outside the typed two-level structure (e.g. array-of-steps, unknown keys).
 *
 * The typed adapters array from RFRunContextSummary.swarm_plan drives level-1;
 * each adapter's nested object properties drive level-2. Unknown-shape plans
 * show an inline "Show raw" toggle without forcing the full-raw view by default.
 */

interface SwarmPlanTreeProps {
  swarmPlan: RFRunContextSummary["swarm_plan"] | null | undefined;
}

function SwarmPlanTree({ swarmPlan }: SwarmPlanTreeProps) {
  const [showRaw, setShowRaw] = useState(false);

  if (!swarmPlan) {
    return <SectionEmpty label="Swarm plan" />;
  }

  const rawJson = JSON.stringify(swarmPlan, null, 2);

  // ── Top-level plan metadata rows ──────────────────────────────────────────
  const swarmName = typeof swarmPlan.swarm === "string" ? swarmPlan.swarm : null;
  const agents = swarmPlan.agents;
  const adapters = swarmPlan.adapters;

  // ── Level-1 expandable tree: "budget" block (nested object) ──────────────
  // We support one level of nesting for well-known structured sub-objects.
  // Unknown keys with object values get a generic sub-tree.

  // Gather extra keys beyond the typed ones (budget, required_outputs, etc.)
  const KNOWN_FLAT_KEYS = new Set(["swarm", "agents", "adapters"]);
  const extraKeys = Object.keys(swarmPlan).filter((k) => !KNOWN_FLAT_KEYS.has(k));

  const hasStructuredContent =
    swarmName || agents || adapters || extraKeys.length > 0;

  return (
    <div className="rv-context-pane__swarm-tree" data-testid="context-swarm-tree">
      {/* ── Top-level flat metadata ── */}
      {swarmName && (
        <div className="rv-context-pane__swarm-row" data-testid="swarm-tree-swarm-name">
          <span className="rv-context-pane__swarm-label">Swarm</span>
          <span className="rv-context-pane__swarm-value">{swarmName}</span>
        </div>
      )}
      {agents && (
        <div className="rv-context-pane__swarm-row" data-testid="swarm-tree-agents">
          <span className="rv-context-pane__swarm-label">Agents</span>
          <span className="rv-context-pane__swarm-value">
            {Array.isArray(agents) ? agents.join(", ") : String(agents)}
          </span>
        </div>
      )}
      {adapters && (
        <div className="rv-context-pane__swarm-row" data-testid="swarm-tree-adapters">
          <span className="rv-context-pane__swarm-label">Adapters</span>
          <span className="rv-context-pane__swarm-value">
            {Array.isArray(adapters) ? adapters.join(", ") : String(adapters)}
          </span>
        </div>
      )}

      {/* ── Level-2 expandable sub-trees for nested object keys ── */}
      {extraKeys.map((key) => {
        const value = (swarmPlan as Record<string, unknown>)[key];
        return (
          <SwarmPlanSubTree
            key={key}
            label={key}
            value={value}
            depth={1}
            testId={`swarm-tree-subtree-${key}`}
          />
        );
      })}

      {/* ── Raw escape hatch ── */}
      <div className="rv-context-pane__swarm-raw-toggle" data-testid="swarm-tree-raw-toggle-area">
        <button
          type="button"
          className="rv-context-pane__swarm-raw-btn"
          onClick={() => setShowRaw((v) => !v)}
          aria-expanded={showRaw}
          data-testid="swarm-tree-raw-btn"
        >
          {showRaw ? "Hide raw" : "Show raw"}
        </button>
        {showRaw && (
          <pre
            className="rv-context-pane__swarm-raw-block rv-swarm__raw-block"
            data-testid="swarm-tree-raw-block"
          >
            {rawJson}
          </pre>
        )}
      </div>

      {/* Fallback when nothing structured was rendered */}
      {!hasStructuredContent && !showRaw && (
        <SwarmPlanSection swarmPlan={swarmPlan} />
      )}
    </div>
  );
}

// ── SwarmPlanSubTree — level-2/3 expandable sub-tree ─────────────────────────

interface SwarmPlanSubTreeProps {
  label: string;
  value: unknown;
  depth: number;
  testId?: string;
}

/**
 * Renders a single named sub-tree node (expand/collapse).
 * Depth cap: stops rendering children beyond depth 3 (raw string instead).
 */
function SwarmPlanSubTree({ label, value, depth, testId }: SwarmPlanSubTreeProps) {
  const [open, setOpen] = useState(false);

  const isObject =
    typeof value === "object" && value !== null && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const hasChildren = isObject && Object.keys(value as Record<string, unknown>).length > 0;
  const canExpand = (hasChildren || isArray) && depth < 3;

  const displayValue =
    isArray
      ? (value as unknown[]).map((v) => (typeof v === "string" ? v : JSON.stringify(v))).join(", ")
      : isObject && !canExpand
      ? JSON.stringify(value)
      : null;

  return (
    <div
      className="rv-context-pane__swarm-subtree"
      data-testid={testId}
      data-depth={depth}
    >
      {canExpand ? (
        <>
          <button
            type="button"
            className="rv-context-pane__swarm-subtree-header"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            data-testid={testId ? `${testId}-toggle` : undefined}
          >
            <span className="rv-context-pane__swarm-subtree-chevron" aria-hidden="true">
              {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
            <span className="rv-context-pane__swarm-label">{label}</span>
          </button>
          {open && isObject && (
            <div
              className="rv-context-pane__swarm-subtree-body"
              data-testid={testId ? `${testId}-body` : undefined}
            >
              {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                <SwarmPlanSubTree
                  key={k}
                  label={k}
                  value={v}
                  depth={depth + 1}
                  testId={testId ? `${testId}-${k}` : undefined}
                />
              ))}
            </div>
          )}
          {open && isArray && (
            <div
              className="rv-context-pane__swarm-subtree-body"
              data-testid={testId ? `${testId}-body` : undefined}
            >
              {(value as unknown[]).map((item, i) => (
                <SwarmPlanSubTree
                  key={i}
                  label={String(i)}
                  value={item}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="rv-context-pane__swarm-row">
          <span className="rv-context-pane__swarm-label">{label}</span>
          <span className="rv-context-pane__swarm-value">
            {displayValue ?? (typeof value === "string" ? value : JSON.stringify(value))}
          </span>
        </div>
      )}
    </div>
  );
}

// ── UpstreamEntitiesSection ───────────────────────────────────────────────────

interface UpstreamEntitiesSectionProps {
  /** upstream_entities from RFRunContextSummary — typed Record<string,unknown> | null | undefined */
  upstream: Record<string, unknown> | null | undefined;
}

/**
 * Renders intent_id, ibom_id, intenttree_node_id as badge links.
 * Best-effort: plain text badges with aria-label tooltip text.
 * A reachability ping MUST never block render — badges are always static.
 * Empty-state when upstream_entities is null/absent or all IDs are null.
 */
function UpstreamEntitiesSection({
  upstream,
}: UpstreamEntitiesSectionProps) {
  if (!upstream) {
    return <SectionEmpty label="Upstream entities" />;
  }

  // Extract the three known entity IDs; upstream_entities is typed as
  // Record<string, unknown> | null so we guard each access.
  const intentId =
    typeof (upstream as Record<string, unknown>)["intent_id"] === "string"
      ? ((upstream as Record<string, unknown>)["intent_id"] as string)
      : null;
  const ibomId =
    typeof (upstream as Record<string, unknown>)["ibom_id"] === "string"
      ? ((upstream as Record<string, unknown>)["ibom_id"] as string)
      : null;
  const intenttreeNodeId =
    typeof (upstream as Record<string, unknown>)["intenttree_node_id"] === "string"
      ? ((upstream as Record<string, unknown>)["intenttree_node_id"] as string)
      : null;

  const hasAny = intentId || ibomId || intenttreeNodeId;
  if (!hasAny) {
    return <SectionEmpty label="Upstream entities" />;
  }

  return (
    <div
      className="rv-context-pane__upstream-entities"
      data-testid="context-upstream-entities"
    >
      {intentId && (
        <span
          className="rv-context-pane__entity-badge"
          data-testid="context-entity-intent-id"
          title={`Intent: ${intentId}`}
          aria-label={`Intent ID: ${intentId}`}
        >
          <span className="rv-context-pane__entity-label">Intent</span>
          <code className="rv-context-pane__entity-value">{intentId}</code>
        </span>
      )}
      {ibomId && (
        <span
          className="rv-context-pane__entity-badge"
          data-testid="context-entity-ibom-id"
          title={`iBOM: ${ibomId}`}
          aria-label={`iBOM ID: ${ibomId}`}
        >
          <span className="rv-context-pane__entity-label">iBOM</span>
          <code className="rv-context-pane__entity-value">{ibomId}</code>
        </span>
      )}
      {intenttreeNodeId && (
        <span
          className="rv-context-pane__entity-badge"
          data-testid="context-entity-intenttree-node-id"
          title={`IntentTree node: ${intenttreeNodeId}`}
          aria-label={`IntentTree node ID: ${intenttreeNodeId}`}
        >
          <span className="rv-context-pane__entity-label">ITNode</span>
          <code className="rv-context-pane__entity-value">{intenttreeNodeId}</code>
        </span>
      )}
    </div>
  );
}

// ── ContextPane ───────────────────────────────────────────────────────────────

export function ContextPane({ run }: ContextPaneProps) {
  // Schema guard: require 1.3+ AND a context block to show any panels.
  const hasContext = isSchemaAtLeast13(run.schema_version) && run.context != null;

  if (!hasContext) {
    return (
      <div
        className="rv-context-pane rv-context-pane--unavailable"
        data-testid="context-pane"
        role="status"
        aria-label="Context not available"
      >
        <div
          className="rv-context-pane__empty-state"
          data-testid="context-pane-unavailable"
        >
          <span className="rv-context-pane__empty-icon" aria-hidden="true">&#9767;</span>
          <p className="rv-context-pane__empty-message">
            Context not available for this run.
          </p>
          <p className="rv-context-pane__empty-sub">
            Re-export this run with schema 1.3+ to see context panels.
          </p>
        </div>
      </div>
    );
  }

  const runId = run.run_id;
  const context = run.context;

  return (
    <div className="rv-context-pane" data-testid="context-pane">

      {/* ── 1. Routing Decision ── */}
      <CollapsibleSection
        runId={runId}
        panelId="routing_decision"
        title="Routing Decision"
        headingId="context-pane-routing-heading"
        testId="context-section-routing"
      >
        <RoutingDecisionSection decision={context?.routing_decision} />
      </CollapsibleSection>

      {/* ── 2. Research Brief ── */}
      <CollapsibleSection
        runId={runId}
        panelId="research_brief"
        title="Research Brief"
        headingId="context-pane-brief-heading"
        testId="context-section-brief"
      >
        {context?.research_brief_md ? (
          <ReportRenderer
            markdown={context.research_brief_md}
            claims={[]}
            onClaimSelect={() => {/* no-op — brief is read-only */}}
            compact
          />
        ) : (
          <SectionEmpty label="Research brief" />
        )}
      </CollapsibleSection>

      {/* ── 3. Swarm Plan — OQ-3: two-level tree + raw escape hatch ── */}
      <CollapsibleSection
        runId={runId}
        panelId="swarm_plan"
        title="Swarm Plan"
        headingId="context-pane-swarm-heading"
        testId="context-section-swarm"
      >
        <SwarmPlanTree swarmPlan={context?.swarm_plan} />
      </CollapsibleSection>

      {/* ── 4. Upstream Entities ── */}
      <CollapsibleSection
        runId={runId}
        panelId="upstream_entities"
        title="Upstream Entities"
        headingId="context-pane-upstream-heading"
        testId="context-section-upstream"
      >
        <UpstreamEntitiesSection upstream={context?.upstream_entities} />
      </CollapsibleSection>

    </div>
  );
}

export default ContextPane;
