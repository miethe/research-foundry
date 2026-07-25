/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A control-plane routing decision selecting node, postures, skills, tools, and writebacks.
 */
export type RoutingDecision = {
  [k: string]: any;
} & {
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
  /**
   * CARP (catalog-assisted-research-planning) additive field: the retrieval policy in effect for this routing decision. Absent means disabled (the v1 default and every legacy decision). See docs/dev/architecture/carp-contract-freeze.md.
   *
   */
  retrieval_policy?: "disabled" | "catalog_only" | "catalog_then_discovery";
  /**
   * The exact residual-question-id set this decision may route to discovery providers (AC CARP-4: provider requests equal this set, never more).
   *
   */
  residual_question_ids?: string[];
  [k: string]: any;
};
