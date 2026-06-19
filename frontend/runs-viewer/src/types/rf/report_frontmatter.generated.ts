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
  [k: string]: any;
}
