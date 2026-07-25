/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable statement limited to one exact passage. This object is not a canonical claim and cannot carry inferred reasoning as source evidence.
 */
export type SourceAssertion = {
  [k: string]: any;
} & {
  schema_version: "1.0";
  type: "source_assertion";
  assertion_id: string;
  assertion_version: number;
  source_edition_id?: string | null;
  passage_id?: string | null;
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
  extensions: {
    evidence_taxonomy: {
      /**
       * Domain-extensible evidence-quality taxonomy axis, independent from the rights axis (see rights_extension.schema.yaml, which must never define or reference this field). Classifies the kind of evidence this source_assertion instance represents. `other` exists as an extension point, not as a closed clinical list — a future domain-specific schema (e.g. an Evidence-Foundry) is expected to specialize this taxonomy rather than replace it. `judgment_basis` (below) is a sibling, INDEPENDENT axis in this same `evidence_taxonomy` block — never derive one from the other.
       */
      evidence_item_type:
        | "observed_finding"
        | "reference_interval_value"
        | "equation_or_method"
        | "guideline_recommendation"
        | "instrument_or_questionnaire"
        | "bibliographic_metadata"
        | "derived_synthesis"
        | "other";
      /**
       * Domain-general axis (per OQ-RF-2 — not clinical-only naming) classifying how this source_assertion's value was arrived at. INDEPENDENT from `evidence_item_type` above — do not derive either field from the other anywhere in this codebase. This repo's schemas do not use a JSON Schema `default:` keyword elsewhere, so the default is documented here instead: the conceptual default is `unassessed`. Fail-closed contract: any consumer that encounters a source_assertion instance predating this field's introduction (i.e. `judgment_basis` absent) MUST treat it as `unassessed`, never as `measured` — this backstops later commercial-release gates that key off `judgment_basis`.
       */
      judgment_basis: "measured" | "derived_from_measured" | "expert_judgment" | "mixed" | "unassessed";
    };
  };
  rights_summary?: {
    [k: string]: any;
  };
  synthesis?: {
    /**
     * @minItems 2
     */
    input_refs?: [
      {
        source_assertion_id: string;
        rights_record_id?: string | null;
        contribution: "anchor" | "corroborating" | "contradicting" | "scope_limiting";
      },
      {
        source_assertion_id: string;
        rights_record_id?: string | null;
        contribution: "anchor" | "corroborating" | "contradicting" | "scope_limiting";
      },
      ...{
        source_assertion_id: string;
        rights_record_id?: string | null;
        contribution: "anchor" | "corroborating" | "contradicting" | "scope_limiting";
      }[]
    ];
    method?: string;
    divergence_notes?: string[];
    reproduces_source_arrangement?: boolean;
    first_party_rights_holder?: string | null;
    attestation?: {
      attested_by?: string | null;
      attested_at?: string | null;
      attestation_ref?: string | null;
      status?: "candidate" | "attested";
    };
  };
  substitutability?: {
    searched_at: string | null;
    status: "substitute_found" | "no_substitute_found" | "not_searched";
    candidate_source_ids: string[];
    coverage_notes: string;
  } | null;
};
