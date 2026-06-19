/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A research brief defining questions, source strategy, and output requirements.
 */
export interface ResearchBrief {
  id: string;
  intent_id: string;
  title: string;
  audience?: "self" | "technical" | "executive" | "public" | "client";
  research_depth?: "skim" | "standard" | "deep" | "exhaustive";
  questions?: {
    primary?: {
      id?: string;
      question?: string;
      [k: string]: any;
    }[];
    secondary?: {
      id?: string;
      question?: string;
      [k: string]: any;
    }[];
    [k: string]: any;
  };
  source_strategy?: {
    include_source_types?: string[];
    exclude_source_types?: string[];
    freshness?: {
      required?: boolean;
      max_age_days?: number;
      exceptions?: string[];
      [k: string]: any;
    };
    [k: string]: any;
  };
  output_requirements?: {
    format?: string;
    include_claim_ledger?: boolean;
    include_source_cards?: boolean;
    include_inference_log?: boolean;
    include_open_questions?: boolean;
    [k: string]: any;
  };
  [k: string]: any;
}
