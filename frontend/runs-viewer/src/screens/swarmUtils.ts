/**
 * swarmUtils.ts — shared utility functions and types for SwarmScreen and SwarmPane.
 *
 * Separated from SwarmScreen.tsx to satisfy the react-refresh/only-export-components
 * ESLint rule (screens must export only components; utilities go in separate files).
 */

import type { RFRunContextSummary } from "@/types/rf/run-export";

// ── Types ─────────────────────────────────────────────────────────────────────

export type RoutingDecision = NonNullable<RFRunContextSummary["routing_decision"]>;

export interface SwarmPlanEntry {
  agent?: string | null;
  task?: string | null;
  status?: string | null;
  [k: string]: unknown;
}

// ── Type guards ───────────────────────────────────────────────────────────────

export function isRoutingDecision(v: unknown): v is RoutingDecision {
  return typeof v === "object" && v !== null;
}

export function isSwarmPlanArray(v: unknown): v is SwarmPlanEntry[] {
  return Array.isArray(v);
}

export function isSwarmPlanObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

// ── Agent extraction ──────────────────────────────────────────────────────────

/**
 * Derive a deduplicated list of agent names from routing_decision and swarm_plan.
 * Returns an empty array when no agent names can be found.
 */
export function extractAgents(
  routingDecision: RoutingDecision | null | undefined,
  swarmPlan: RFRunContextSummary["swarm_plan"],
): string[] {
  const names = new Set<string>();

  if (routingDecision?.decision && typeof routingDecision.decision === "string") {
    names.add(routingDecision.decision.trim());
  }

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

  if (isSwarmPlanArray(swarmPlan)) {
    swarmPlan.forEach((entry) => {
      if (entry.agent && typeof entry.agent === "string" && entry.agent.trim()) {
        names.add(entry.agent.trim());
      }
    });
  }

  return Array.from(names);
}
