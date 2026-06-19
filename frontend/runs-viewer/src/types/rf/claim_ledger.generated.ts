/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A ledger of claims with status, materiality, sources, and verification state.
 */
export interface ClaimLedger {
  id: string;
  intent_id: string;
  report_ref?: string;
  verification_status?: "pending" | "passed" | "failed";
  claims?: {
    claim_id?: string;
    text?: string;
    materiality?: "material" | "background" | "style";
    claim_type?:
      | "factual"
      | "causal"
      | "comparative"
      | "quantitative"
      | "attribution"
      | "recommendation"
      | "prediction";
    status?: "supported" | "mixed" | "contradicted" | "inference" | "speculation" | "unsupported";
    confidence?: "low" | "medium" | "high";
    sources?: {
      source_card_id?: string;
      evidence_id?: string;
      relation?: "supports" | "contradicts" | "context";
      locator?: string;
      [k: string]: any;
    }[];
    inference_basis?: {
      from_claims?: string[];
      reasoning_summary?: string | null;
      [k: string]: any;
    };
    report_locations?: {
      file?: string;
      heading?: string;
      paragraph_id?: string;
      [k: string]: any;
    }[];
    reviewer_notes?: string;
    [k: string]: any;
  }[];
  unresolved_questions?: {
    question?: string;
    why_unresolved?: string;
    recommended_next_source?: string | null;
    [k: string]: any;
  }[];
  [k: string]: any;
}
