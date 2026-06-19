/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Candidate record for a Research Foundry → IntentTree outbound writeback. Always written to runs/<run>/writebacks/intenttree_update.yaml; pushed live only when IntentTree is reachable and the key profile permits.
 *
 */
export interface IntentTreeUpdateCandidate {
  /**
   * IntentTree node id (from intent.intenttree_node_ref)
   */
  node_id?: string;
  evidence_bundle_id?: string;
  run_id: string;
  /**
   * ISO-8601 timestamp of this candidate generation
   */
  update_timestamp: string;
  /**
   * Node status to set (e.g. in_progress, completed, verified)
   */
  status: string;
  claims_total?: number;
  claims_supported?: number;
  verification_passed?: boolean;
  /**
   * Artifact types flagged as reusable (e.g. evidence_bundle, meatywiki_writeback)
   */
  reusable_output_candidates?: string[];
  artifact_links?: {
    type: string;
    path: string;
    label?: string;
    [k: string]: any;
  }[];
  /**
   * Blocking issues preventing promotion (from verification failures)
   */
  blocked_by?: string[];
  /**
   * Whether the live HTTP push was attempted and its outcome
   */
  push_status?: "proposed" | "pushed" | "skipped_offline" | "skipped_requires_review" | "skipped_no_node";
  [k: string]: any;
}
