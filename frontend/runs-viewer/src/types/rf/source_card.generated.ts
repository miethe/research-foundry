/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Front-matter schema for a source card Markdown document.
 */
export interface SourceCard {
  schema_version?: string;
  type: "source_card";
  source_card_id: string;
  created_at?: string;
  created_by_agent?: string;
  sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
  source: {
    title?: string;
    source_type?:
      | "official_doc"
      | "paper"
      | "standard"
      | "repo"
      | "news"
      | "blog"
      | "book"
      | "personal_note"
      | "internal_doc"
      | "other";
    locator?: {
      url?: string | null;
      file_path?: string | null;
      doi?: string | null;
      repo?: string | null;
      [k: string]: any;
    };
    authors?: string[];
    publisher?: string | null;
    published_at?: string | null;
    accessed_at?: string;
    version?: string | null;
    [k: string]: any;
  };
  trust?: {
    source_rank?: "primary" | "secondary" | "tertiary" | "unknown";
    reliability_notes?: string;
    known_limitations?: string[];
    conflicts_with?: {
      source_card_id?: string;
      reason?: string;
      [k: string]: any;
    }[];
    [k: string]: any;
  };
  usage?: {
    allowed_for_public_output?: boolean;
    allowed_for_work_output?: boolean;
    allowed_for_personal_meatywiki?: boolean;
    citation_required?: boolean;
    quote_limit_notes?: string;
    [k: string]: any;
  };
  extracted_points?: {
    evidence_id?: string;
    locator?: string;
    summary?: string;
    quote?: string | null;
    supports_potential_claims?: string[];
    [k: string]: any;
  }[];
  [k: string]: any;
}
