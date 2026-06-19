/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Candidate record for a Research Foundry → NotebookLM outbound writeback. Always written to runs/<run>/writebacks/notebooklm_update.yaml; sources are pushed live only when NotebookLM is reachable and the key profile permits. node_id provides an optional back-link to the originating IntentTree node.
 *
 */
export interface NotebookLMUpdateCandidate {
  /**
   * RF run identifier (e.g. rf_run_20260613_...)
   */
  run_id: string;
  /**
   * ISO-8601 timestamp of this candidate generation
   */
  update_timestamp: string;
  /**
   * Lifecycle status of this writeback candidate
   */
  status: "proposed" | "integrated" | "live_pushed";
  /**
   * Whether the live NotebookLM source push was attempted and its outcome
   */
  push_status: "proposed" | "pushed" | "skipped_offline" | "skipped_requires_review" | "skipped_no_notebook";
  /**
   * NotebookLM notebook id resolved for this run (null if not yet resolved)
   */
  notebook_id?: string | null;
  /**
   * Human-readable notebook title at time of writeback generation
   */
  notebook_title?: string | null;
  /**
   * RF project slug used to resolve the notebook via correlation registry
   */
  project?: string | null;
  /**
   * Evidence bundle that backs the sources being pushed
   */
  evidence_bundle_id?: string | null;
  /**
   * Source cards successfully pushed as NotebookLM sources
   */
  pushed_source_ids?: {
    /**
     * NotebookLM-assigned source id returned by add_source()
     */
    nlm_source_id: string;
    /**
     * RF source card id that was pushed
     */
    rf_source_card_id: string;
    [k: string]: any;
  }[];
  /**
   * Run artifacts relevant to this writeback (report, evidence bundle, etc.)
   */
  artifact_links?: {
    /**
     * Artifact type (e.g. report, evidence_bundle, source_card)
     */
    type: string;
    /**
     * Relative path under the run directory
     */
    path: string;
    /**
     * Human-readable label for the artifact
     */
    label?: string;
    /**
     * Optional task id that produced this artifact
     */
    task_id?: string;
    [k: string]: any;
  }[];
  /**
   * Optional IntentTree node back-link (mirrors intenttree_update.node_id); null when this run was not launched from an IntentTree intent.
   *
   */
  node_id?: string | null;
  [k: string]: any;
}
