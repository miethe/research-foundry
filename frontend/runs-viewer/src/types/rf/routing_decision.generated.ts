/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A control-plane routing decision selecting node, postures, skills, tools, and writebacks.
 */
export interface RoutingDecision {
  id: string;
  intent_id: string;
  active_node_id: string;
  selected_abstraction_level?: string;
  selected_posture_chain?: string[];
  selected_skillbom?: string;
  selected_context_packs?: string[];
  selected_tools?: string[];
  human_required?: boolean;
  rationale?: string;
  expected_output?: string;
  validation?: string[];
  writebacks?: {
    target?: string;
    type?: string;
    [k: string]: any;
  }[];
  [k: string]: any;
}
