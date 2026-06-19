/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A research node in the IntentTree preserving abstraction levels.
 */
export interface IntentTreeNode {
  node_id: string;
  level?: string;
  title: string;
  parent?: string;
  intent_id: string;
  status?: "ready" | "active" | "blocked" | "completed" | "archived";
  priority?: "low" | "medium" | "high";
  dependencies?: {
    node_id?: string;
    [k: string]: any;
  }[];
  blockers?: string[];
  required_agent_postures?: string[];
  required_skill_stack?: string[];
  required_context?: string[];
  expected_artifacts?: string[];
  success_criteria?: string[];
  reusable_output_candidates?: string[];
  [k: string]: any;
}
