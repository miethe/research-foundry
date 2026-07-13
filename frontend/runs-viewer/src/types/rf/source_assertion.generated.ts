/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable statement limited to one exact passage. This object is not a canonical claim and cannot carry inferred reasoning as source evidence.
 */
export interface SourceAssertion {
  schema_version: "1.0";
  type: "source_assertion";
  assertion_id: string;
  assertion_version: number;
  source_edition_id: string;
  passage_id: string;
  assertion_text: string;
  assertion_text_sha256: string;
  qualifiers: {
    modality?: string | null;
    negation?: boolean | null;
    population?: string | null;
    geography?: string | null;
    timeframe?: string | null;
    intervention_or_exposure?: string | null;
    outcome?: string | null;
  };
  /**
   * Unknown optional qualifiers preserved verbatim and included in the identity payload.
   */
  qualifier_extensions: {
    [k: string]: any;
  };
  extraction_provenance: {
    extractor: string;
    provider?: string | null;
    model?: string | null;
    prompt_version?: string | null;
    schema_version: string;
    code_version?: string | null;
    observed_at: string;
  };
  predecessor_assertion_id?: string | null;
  predecessor_assertion_version?: number | null;
  lifecycle_state: "eligible" | "stale" | "invalidated" | "tombstoned";
  identity: {
    algorithm: "sha256-canonical-json-v1";
    fingerprint: string;
    material_fields: any[];
  };
}
