/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A bundle assembling all artifacts, counts, governance, and lineage for a research run.
 */
export interface EvidenceBundle {
  id: string;
  intent_id: string;
  run_id: string;
  created_at?: string;
  status?: "draft" | "verified" | "published" | "archived";
  artifacts?: {
    research_brief?: string;
    swarm_plan?: string;
    source_cards_dir?: string;
    extraction_cards_dir?: string;
    claim_ledger?: string;
    report?: string;
    verification?: string;
    ccdash_event?: string;
    [k: string]: any;
  };
  counts?: {
    source_cards?: number;
    extraction_cards?: number;
    claims_total?: number;
    claims_supported?: number;
    claims_inference?: number;
    claims_speculation?: number;
    claims_unsupported?: number;
    [k: string]: any;
  };
  governance?: {
    sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
    approved_for_writeback?: boolean;
    approved_by?: string | null;
    approval_timestamp?: string | null;
    [k: string]: any;
  };
  lineage?: {
    raw_idea_ids?: string[];
    intent_id?: string;
    ibom_id?: string;
    intenttree_node_id?: string;
    skillbom_ids_used?: string[];
    /**
     * NotebookLM notebook id that received sources from this run
     */
    notebooklm_notebook_id?: string | null;
    /**
     * Source cards successfully pushed to NotebookLM
     */
    notebooklm_source_ids?: {
      /**
       * NotebookLM-assigned source id
       */
      nlm_source_id: string;
      /**
       * RF source card id that was pushed
       */
      rf_source_card_id: string;
      [k: string]: any;
    }[];
    [k: string]: any;
  };
  [k: string]: any;
}
