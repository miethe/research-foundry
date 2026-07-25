/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Front-matter schema for a research report Markdown document.
 */
export interface ReportFrontMatter {
  schema_version?: string;
  type: "research_report";
  report_id: string;
  title: string;
  intent_id?: string;
  evidence_bundle_id?: string;
  created_at?: string;
  status?: "draft" | "verified" | "published" | "archived";
  audience?: "self" | "technical" | "executive" | "public" | "client";
  sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
  claim_policy?: string;
  verification_status?: "pending" | "passed" | "failed";
  /**
   * Additive, non-authoritative rollup of terms/usage-roles across this report's claims (union), computed at the same write time as claim-map's own attach (docs/project_plans/design-specs/claim-term-indexing.md, OQ-E). Never participates in verification or governance. Absent when no claim in this report carries a `_term_index`.
   */
  _term_index?: {
    terms?: string[];
    usage_roles?: {
      [k: string]: string[];
    };
    vocabulary_version?: string | null;
    [k: string]: any;
  };
  [k: string]: any;
}
