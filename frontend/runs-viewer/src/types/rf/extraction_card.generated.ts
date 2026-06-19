/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Structured extraction of facts, definitions, metrics, and cautions from a source card.
 */
export interface ExtractionCard {
  id: string;
  source_card_id: string;
  created_at?: string;
  extractor_agent?: string;
  model_profile?: string;
  extracted_facts?: {
    evidence_id?: string;
    text?: string;
    locator?: string;
    confidence?: "low" | "medium" | "high";
    quote_available?: boolean;
    notes?: string;
    [k: string]: any;
  }[];
  extracted_definitions?: {
    term?: string;
    definition?: string;
    locator?: string;
    [k: string]: any;
  }[];
  extracted_metrics?: {
    metric_name?: string;
    value?: string | number;
    unit?: string | null;
    date_context?: string | null;
    locator?: string;
    [k: string]: any;
  }[];
  contradictions_or_cautions?: {
    text?: string;
    locator?: string;
    [k: string]: any;
  }[];
  [k: string]: any;
}
