/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * An Intent Bill of Materials snapshot for a research intent.
 */
export interface IBOM {
  id: string;
  intent_id: string;
  created_at?: string;
  snapshot_status?: "draft" | "locked" | "superseded";
  context_snapshot?: string;
  sources_seeded?: {
    id?: string;
    kind?: "url" | "pdf" | "note" | "book" | "paper" | "repo" | "conversation" | "unknown";
    locator?: string;
    sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
    notes?: string;
    [k: string]: any;
  }[];
  assumptions?: {
    id?: string;
    text?: string;
    risk?: "low" | "medium" | "high";
    should_verify?: boolean;
    [k: string]: any;
  }[];
  known_constraints?: string[];
  tools_available?: string[];
  model_policy?: {
    extraction_profile?: string;
    synthesis_profile?: string;
    verification_profile?: string;
    [k: string]: any;
  };
  relevant_memory?: {
    meatywiki_ref?: string;
    reason?: string;
    [k: string]: any;
  }[];
  open_questions?: string[];
  security_boundaries?: string[];
  [k: string]: any;
}
