/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable, content-addressed rendition of a source. A new material byte sequence is a new edition; mutable source metadata is intentionally outside this record.
 */
export interface SourceEdition {
  schema_version: "1.0";
  type: "source_edition";
  source_edition_id: string;
  content_sha256: string;
  source_id: string;
  media_type?: string;
  captured_at: string;
  retrieval_locator?: {
    [k: string]: any;
  };
  predecessor_edition_id?: string | null;
  access_scope?: string;
  /**
   * Preserved non-identity metadata; never included in content identity.
   */
  metadata_extensions?: {
    [k: string]: any;
  };
}
