/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A proposed writeback of research output into MeatyWiki.
 */
export interface MeatyWikiWriteback {
  id: string;
  evidence_bundle_id: string;
  target_page?: string;
  writeback_type?: "source_note" | "concept_update" | "decision_record" | "pattern" | "project_update" | "insight";
  status?: "proposed" | "approved" | "written" | "rejected";
  summary?: string;
  key_claims?: {
    claim_id?: string;
    include?: boolean;
    [k: string]: any;
  }[];
  links?: {
    source_cards?: string[];
    related_pages?: string[];
    [k: string]: any;
  };
  approval?: {
    required?: boolean;
    reason?: string;
    approved_by?: string | null;
    [k: string]: any;
  };
  [k: string]: any;
}
