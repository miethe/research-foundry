/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A structured research intent extending the Agentic OS intent model.
 */
export interface ResearchIntent {
  id: string;
  title: string;
  owner?: string;
  created_at?: string;
  status?: "proposed" | "active" | "paused" | "completed" | "archived";
  type?: string;
  objective: string;
  motivation?: string;
  desired_output?: {
    artifact_type?:
      | "evidence_bundle"
      | "report"
      | "brief"
      | "source_note"
      | "market_scan"
      | "technical_memo"
      | "literature_review";
    audience?: "self" | "public" | "executive" | "technical" | "client" | "work_internal";
    depth?: "skim" | "standard" | "deep" | "exhaustive";
    [k: string]: any;
  };
  scope?: {
    in?: string[];
    out?: string[];
    [k: string]: any;
  };
  research_questions?: {
    primary?: string[];
    secondary?: string[];
    [k: string]: any;
  };
  constraints?: {
    hard?: string[];
    soft?: string[];
    [k: string]: any;
  };
  success_criteria?: {
    criterion?: string;
    measure?: string;
    [k: string]: any;
  }[];
  governance?: {
    sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
    key_profile_allowed?: "personal" | "work_approved" | "client_approved" | "offline_only";
    requires_human_review?: boolean;
    allowed_writebacks?: string[];
    [k: string]: any;
  };
  ibom_ref?: string;
  intenttree_node_ref?: string;
  /**
   * NotebookLM notebook id back-linked when intake originated from NLM.
   */
  notebooklm_notebook_ref?: string;
  /**
   * Project slug associating this intent with a named research project.
   */
  project?: string;
  /**
   * NotebookLM notebook id resolved for this intent; null until the writeback or sourcing layer creates/links a notebook.
   */
  notebook_id?: string | null;
  [k: string]: any;
}
