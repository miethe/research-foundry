/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable evaluation or reviewer decision for one source assertion version.
 */
export interface AssertionEvaluation {
  schema_version: "1.0";
  type: "assertion_evaluation";
  evaluation_id: string;
  assertion_id: string;
  assertion_version: number;
  evaluation_kind: "grounding" | "atomicity" | "qualifier_completeness" | "human_review" | "reuse_eligibility";
  verdict: "pass" | "fail" | "abstain" | "needs_review";
  evaluator: {
    kind: "human" | "model" | "rule";
    id: string;
    version?: string | null;
  };
  evaluated_at: string;
  details?: {
    [k: string]: any;
  };
}
