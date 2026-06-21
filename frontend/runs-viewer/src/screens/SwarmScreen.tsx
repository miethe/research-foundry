/**
 * SwarmScreen — swarm orchestration visualizer (Wave-2 Swarm tab).
 *
 * Accessible at /runs/:runId/swarm. Displays:
 *   1. Routing Decision card  — context.routing_decision (agent name + rationale)
 *   2. Swarm Plan section     — context.swarm_plan (structured or raw-JSON fallback)
 *   3. Agents list            — deduplicated agent names derived from both fields
 *
 * Graceful empty states:
 *   - When context is null/absent (pre-F5 runs): shows a single full-page
 *     placeholder ("Swarm data not available. Re-export…").
 *   - When individual sub-fields are absent: shows a muted placeholder per card.
 *
 * Data dependency: context.swarm_plan / context.routing_decision are only
 * populated after F5 Phase 7 threads them into the export. This screen handles
 * the pre-F5 case gracefully via the empty-state guard.
 */

import { useParams } from "react-router-dom";
import { useRunDetail } from "@/hooks";
import { deriveRunTitle, titleFromSlug } from "@/lib/runs";
import type { RFRunContextSummary } from "@/types/rf/run-export";
import "@/styles/swarm.css";

// ── Type helpers ──────────────────────────────────────────────────────────────

/**
 * Minimal interface matching the context.routing_decision shape defined in
 * RFRunContextSummary. We re-use the typed field directly rather than redefining.
 */
type RoutingDecision = NonNullable<RFRunContextSummary["routing_decision"]>;

/**
 * A single swarm plan entry when swarm_plan is an array of objects.
 */
interface SwarmPlanEntry {
  agent?: string | null;
  task?: string | null;
  status?: string | null;
  [k: string]: unknown;
}

// ── Type guards ───────────────────────────────────────────────────────────────

function isRoutingDecision(v: unknown): v is RoutingDecision {
  return typeof v === "object" && v !== null;
}

function isSwarmPlanArray(v: unknown): v is SwarmPlanEntry[] {
  return Array.isArray(v);
}

function isSwarmPlanObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

// ── Agent extraction ──────────────────────────────────────────────────────────

/**
 * Derive a deduplicated list of agent names from routing_decision and swarm_plan.
 * Returns an empty array when no agent names can be found.
 */
function extractAgents(
  routingDecision: RoutingDecision | null | undefined,
  swarmPlan: RFRunContextSummary["swarm_plan"],
): string[] {
  const names = new Set<string>();

  // From routing_decision.decision (often an agent name)
  if (routingDecision?.decision && typeof routingDecision.decision === "string") {
    names.add(routingDecision.decision.trim());
  }

  // From swarm_plan.agents
  if (swarmPlan?.agents) {
    const agents = swarmPlan.agents;
    if (Array.isArray(agents)) {
      agents.forEach((a) => {
        if (typeof a === "string" && a.trim()) names.add(a.trim());
      });
    } else if (typeof agents === "string" && agents.trim()) {
      names.add(agents.trim());
    }
  }

  // From array entries' agent field
  if (isSwarmPlanArray(swarmPlan)) {
    swarmPlan.forEach((entry) => {
      if (entry.agent && typeof entry.agent === "string" && entry.agent.trim()) {
        names.add(entry.agent.trim());
      }
    });
  }

  return Array.from(names);
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface RoutingDecisionCardProps {
  decision: RoutingDecision | null | undefined;
}

function RoutingDecisionCard({ decision }: RoutingDecisionCardProps) {
  if (!decision || !isRoutingDecision(decision)) {
    return (
      <div
        className="rv-swarm__card rv-swarm__card--empty"
        data-testid="swarm-routing-empty"
        role="note"
      >
        <p className="rv-swarm__placeholder">
          No routing decision recorded for this run.
        </p>
      </div>
    );
  }

  const agentName =
    typeof decision.decision === "string" && decision.decision
      ? decision.decision
      : null;
  const rationale =
    typeof decision.rationale === "string" && decision.rationale
      ? decision.rationale
      : null;

  return (
    <div
      className="rv-swarm__card"
      data-testid="swarm-routing-card"
      role="article"
      aria-label="Routing Decision"
    >
      {agentName && (
        <div className="rv-swarm__agent-name" data-testid="swarm-routing-agent">
          <span className="rv-swarm__label">Agent selected</span>
          <strong className="rv-swarm__value">{agentName}</strong>
        </div>
      )}
      {rationale && (
        <div className="rv-swarm__rationale" data-testid="swarm-routing-rationale">
          <span className="rv-swarm__label">Rationale</span>
          <p className="rv-swarm__prose">{rationale}</p>
        </div>
      )}
      {!agentName && !rationale && (
        <p className="rv-swarm__placeholder" data-testid="swarm-routing-partial">
          Routing decision present but fields are empty.
        </p>
      )}
    </div>
  );
}

interface SwarmPlanSectionProps {
  swarmPlan: RFRunContextSummary["swarm_plan"] | undefined;
}

function SwarmPlanSection({ swarmPlan }: SwarmPlanSectionProps) {
  if (!swarmPlan) {
    return (
      <div
        className="rv-swarm__card rv-swarm__card--empty"
        data-testid="swarm-plan-empty"
        role="note"
      >
        <p className="rv-swarm__placeholder">
          No swarm plan recorded for this run.
        </p>
      </div>
    );
  }

  // Typed swarm_plan from RFRunContextSummary — it has top-level swarm/agents/adapters fields
  const typedPlan = swarmPlan as RFRunContextSummary["swarm_plan"];

  // Array of plan entries
  if (isSwarmPlanArray(swarmPlan)) {
    return (
      <div className="rv-swarm__plan-list" data-testid="swarm-plan-entries">
        {swarmPlan.map((entry, i) => (
          <div
            key={i}
            className="rv-swarm__plan-entry"
            data-testid="swarm-plan-entry"
            role="article"
          >
            {entry.agent && (
              <div className="rv-swarm__entry-row">
                <span className="rv-swarm__entry-label">Agent</span>
                <span className="rv-swarm__entry-value">{String(entry.agent)}</span>
              </div>
            )}
            {entry.task && (
              <div className="rv-swarm__entry-row">
                <span className="rv-swarm__entry-label">Task</span>
                <span className="rv-swarm__entry-value">{String(entry.task)}</span>
              </div>
            )}
            {entry.status && (
              <div className="rv-swarm__entry-row">
                <span className="rv-swarm__entry-label">Status</span>
                <span className="rv-swarm__entry-value rv-swarm__status">{String(entry.status)}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Structured object with known swarm/agents/adapters fields
  if (typedPlan && (typedPlan.swarm || typedPlan.agents || typedPlan.adapters)) {
    const swarmName = typedPlan.swarm;
    const agents = typedPlan.agents;
    const adapters = typedPlan.adapters;

    return (
      <div className="rv-swarm__plan-structured" data-testid="swarm-plan-structured">
        {swarmName && (
          <div className="rv-swarm__entry-row">
            <span className="rv-swarm__entry-label">Swarm</span>
            <span className="rv-swarm__entry-value">{String(swarmName)}</span>
          </div>
        )}
        {agents && (
          <div className="rv-swarm__entry-row">
            <span className="rv-swarm__entry-label">Agents</span>
            <span className="rv-swarm__entry-value">
              {Array.isArray(agents) ? agents.join(", ") : String(agents)}
            </span>
          </div>
        )}
        {adapters && (
          <div className="rv-swarm__entry-row">
            <span className="rv-swarm__entry-label">Adapters</span>
            <span className="rv-swarm__entry-value">
              {Array.isArray(adapters) ? adapters.join(", ") : String(adapters)}
            </span>
          </div>
        )}
      </div>
    );
  }

  // Generic object or string — raw JSON fallback
  if (isSwarmPlanObject(swarmPlan) || typeof swarmPlan === "string") {
    return (
      <div className="rv-swarm__plan-raw" data-testid="swarm-plan-raw">
        <pre className="rv-swarm__raw-block">
          {typeof swarmPlan === "string"
            ? swarmPlan
            : JSON.stringify(swarmPlan, null, 2)}
        </pre>
      </div>
    );
  }

  return (
    <div
      className="rv-swarm__card rv-swarm__card--empty"
      data-testid="swarm-plan-empty"
      role="note"
    >
      <p className="rv-swarm__placeholder">
        No swarm plan recorded for this run.
      </p>
    </div>
  );
}

interface AgentsListProps {
  agents: string[];
}

function AgentsList({ agents }: AgentsListProps) {
  if (agents.length === 0) return null;

  return (
    <div className="rv-swarm__agents-list" data-testid="swarm-agents-list">
      {agents.map((name) => (
        <span key={name} className="rv-swarm__agent-chip" data-testid="swarm-agent-chip">
          {name}
        </span>
      ))}
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export function SwarmScreen() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading, error } = useRunDetail(runId ?? "");

  if (!runId) {
    return (
      <div className="rv-swarm" data-testid="swarm-screen">
        <p className="rv-error">No run ID in URL.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rv-swarm" data-testid="swarm-screen-loading">
        <div className="rv-loading">
          <p>Loading swarm data for {runId}…</p>
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="rv-swarm" data-testid="swarm-screen-error">
        <div className="rv-error">
          <p>Error loading run: {error instanceof Error ? error.message : "Unknown error"}</p>
        </div>
      </div>
    );
  }

  const title =
    (run.title && run.title !== run.run_id ? run.title : null) ??
    deriveRunTitle(run) ??
    titleFromSlug(run.run_id) ??
    run.run_id;

  const context = run.context;

  // Full empty state — context block absent (pre-F5 exports)
  if (!context) {
    return (
      <div className="rv-swarm" data-testid="swarm-screen">
        <header className="rv-swarm__header">
          <h1 className="rv-swarm__title">{title}</h1>
          <span className="rv-swarm__run-id" data-testid="swarm-run-id">{run.run_id}</span>
        </header>
        <div
          className="rv-swarm__empty-state"
          data-testid="swarm-context-empty"
          role="status"
          aria-label="Swarm data not available"
        >
          <span className="rv-swarm__empty-icon" aria-hidden="true">&#9767;</span>
          <p className="rv-swarm__empty-message">Swarm data not available.</p>
          <p className="rv-swarm__empty-sub">
            Re-export this run after updating to v2.2+ to see swarm details.
          </p>
        </div>
      </div>
    );
  }

  const routingDecision = context.routing_decision;
  const swarmPlan = context.swarm_plan;
  const agents = extractAgents(routingDecision, swarmPlan);

  return (
    <div className="rv-swarm" data-testid="swarm-screen">
      <header className="rv-swarm__header">
        <h1 className="rv-swarm__title">{title}</h1>
        <span className="rv-swarm__run-id" data-testid="swarm-run-id">{run.run_id}</span>
      </header>

      {/* ── Routing Decision ── */}
      <section
        className="rv-swarm__section"
        aria-labelledby="swarm-routing-title"
        data-testid="swarm-routing-section"
      >
        <h2 id="swarm-routing-title" className="rv-swarm__section-title">
          Routing Decision
        </h2>
        <RoutingDecisionCard decision={routingDecision} />
      </section>

      {/* ── Swarm Plan ── */}
      <section
        className="rv-swarm__section"
        aria-labelledby="swarm-plan-title"
        data-testid="swarm-plan-section"
      >
        <h2 id="swarm-plan-title" className="rv-swarm__section-title">
          Swarm Plan
        </h2>
        <SwarmPlanSection swarmPlan={swarmPlan} />
      </section>

      {/* ── Agents ── */}
      {agents.length > 0 && (
        <section
          className="rv-swarm__section"
          aria-labelledby="swarm-agents-title"
          data-testid="swarm-agents-section"
        >
          <h2 id="swarm-agents-title" className="rv-swarm__section-title">
            Agents
          </h2>
          <AgentsList agents={agents} />
        </section>
      )}
    </div>
  );
}

export default SwarmScreen;
