/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A research swarm plan defining budget, agents, and required outputs.
 */
export interface SwarmPlan {
  id: string;
  brief_id: string;
  intent_id: string;
  created_at?: string;
  status?: "planned" | "running" | "completed" | "failed" | "cancelled";
  budget?: {
    max_cost_usd?: number;
    max_runtime_minutes?: number;
    extraction_model_profile?: string;
    synthesis_model_profile?: string;
    verification_model_profile?: string;
    [k: string]: any;
  };
  agents?: {
    role?: string;
    posture?: string;
    tool?: string;
    model_profile?: string;
    task?: string;
    [k: string]: any;
  }[];
  required_outputs?: string[];
  [k: string]: any;
}
