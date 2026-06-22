/**
 * SwarmPane — run-scoped swarm detail tab pane.
 *
 * Embedded in RunDetailWorkspace as the "swarm" tab (D6).
 * Reads context.swarm_plan and context.routing_decision directly from the run prop;
 * no additional data fetching required (SPA static export).
 *
 * Reuses sub-components from SwarmScreen (exported for this purpose):
 *   - RoutingDecisionCard
 *   - SwarmPlanSection
 *   - AgentsList
 *   - extractAgents
 *
 * Graceful empty state when context is absent (pre-F5 exports).
 * No page-level header — this is a tab pane, not a standalone screen.
 */

import type { RFRunExport } from "@/types/rf";
import { RoutingDecisionCard, SwarmPlanSection, AgentsList } from "@/screens/SwarmScreen";
import { extractAgents } from "@/screens/swarmUtils";

export interface SwarmPaneProps {
  run: RFRunExport;
}

export function SwarmPane({ run }: SwarmPaneProps) {
  const context = run.context;

  // Full empty state — context block absent (pre-F5 exports)
  if (!context) {
    return (
      <div
        className="rv-swarm rv-swarm--pane"
        data-testid="swarm-pane"
        role="status"
        aria-label="Swarm data not available"
      >
        <div
          className="rv-swarm__empty-state"
          data-testid="swarm-pane-context-empty"
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
    <div className="rv-swarm rv-swarm--pane" data-testid="swarm-pane">
      {/* ── Routing Decision ── */}
      <section
        className="rv-swarm__section"
        aria-labelledby="swarm-pane-routing-title"
        data-testid="swarm-pane-routing-section"
      >
        <h3 id="swarm-pane-routing-title" className="rv-swarm__section-title">
          Routing Decision
        </h3>
        <RoutingDecisionCard decision={routingDecision} />
      </section>

      {/* ── Swarm Plan ── */}
      <section
        className="rv-swarm__section"
        aria-labelledby="swarm-pane-plan-title"
        data-testid="swarm-pane-plan-section"
      >
        <h3 id="swarm-pane-plan-title" className="rv-swarm__section-title">
          Swarm Plan
        </h3>
        <SwarmPlanSection swarmPlan={swarmPlan} />
      </section>

      {/* ── Agents ── */}
      {agents.length > 0 && (
        <section
          className="rv-swarm__section"
          aria-labelledby="swarm-pane-agents-title"
          data-testid="swarm-pane-agents-section"
        >
          <h3 id="swarm-pane-agents-title" className="rv-swarm__section-title">
            Agents
          </h3>
          <AgentsList agents={agents} />
        </section>
      )}
    </div>
  );
}

export default SwarmPane;
