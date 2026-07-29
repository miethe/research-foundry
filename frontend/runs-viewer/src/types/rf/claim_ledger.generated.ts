/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A ledger of claims with status, materiality, sources, and verification state.
 */
export interface ClaimLedger {
  id: string;
  intent_id: string;
  report_ref?: string;
  verification_status?: "pending" | "passed" | "failed";
  claims?: {
    claim_id?: string;
    text?: string;
    materiality?: "material" | "background" | "style";
    claim_type?:
      | "factual"
      | "causal"
      | "comparative"
      | "quantitative"
      | "attribution"
      | "recommendation"
      | "prediction";
    status?: "supported" | "mixed" | "contradicted" | "inference" | "speculation" | "unsupported";
    confidence?: "low" | "medium" | "high";
    sources?: {
      source_card_id?: string;
      evidence_id?: string;
      relation?: "supports" | "contradicts" | "context";
      locator?: string;
      [k: string]: any;
    }[];
    inference_basis?: {
      from_claims?: string[];
      reasoning_summary?: string | null;
      [k: string]: any;
    };
    /**
     * Optional durable-ledger links. Legacy run-local claims omit this block and require no synthetic persistent IDs.
     */
    persistent_references?: {
      source_edition_id?: string | null;
      passage_id?: string | null;
      source_assertion_id?: string | null;
      assertion_version?: number | null;
      canonical_claim_id?: string | null;
      canonical_claim_version?: number | null;
      inference_id?: string | null;
      /**
       * RPC SOL-11 additive amendment (F17, research-provenance-continuity P1). Optional companion to inference_id, mirroring the existing canonical_claim_id+canonical_claim_version pair.
       * SOL-17 (round 2, REVERTED the round-1 schema conditional): round 1 added a schema-level `allOf` requiring inference_version whenever inference_id was non-null. That conditional REJECTED a baseline-valid legacy instance (`{persistent_references: {inference_id: "legacy-inf"}}` with no version field at all) -- exactly the pre-existing, version-absent reference shape this repo's own read paths must keep tolerating (RPC-DF-1/AC RPC-3's "legacy_unresolved" resilience framing applies here too). A shipped-schema amendment MUST stay additive against every baseline-valid instance, not merely against instances this document itself invented -- the round-1 conditional broke that. No schema conditional remains here as of round 2: `inference_version` is a plain optional integer, exactly like `canonical_claim_version`'s own field before any pairing rule existed.
       * The atomic-pair rule (inference_id + inference_version written together or not at all) is now a WRITER-LEVEL MUST instead of a schema-level conditional -- enforced by P4's `persistent_references` write path (freeze doc §17.1 item 4) and verified by the P7 gate task RPC-7.16 (freeze doc §17.9), never by this schema. Read semantics for a row carrying inference_id with no inference_version (whether a genuinely pre-P4 legacy row, or a row a non-conforming writer produced): a reader MUST treat the reference as AMBIGUOUS-VERSION, never resolve it to "the latest" inference_version implicitly, and MUST report it using the same `legacy_unresolved`-class typed skip AC RPC-3 already names for a missing/absent persistent reference (freeze doc §13.6 example (e)) -- an inference_id without a version is not usable as an exact persistent reference, but it is not a validation failure either.
       */
      inference_version?: number | null;
    } | null;
    report_locations?: {
      file?: string;
      heading?: string;
      paragraph_id?: string;
      [k: string]: any;
    }[];
    reviewer_notes?: string;
    /**
     * Additive, non-authoritative, write-time term/usage-role index computed by claim-map (docs/project_plans/design-specs/claim-term-indexing.md). Never participates in verification, identity hashing, or rights governance, and never added outside this namespaced key (no bare `usage_role`). Absent when the claim has zero vocabulary hits or no vocabulary file was loaded.
     */
    _term_index?: {
      terms?: string[];
      usage_roles?: {
        [k: string]: string;
      };
      vocabulary_version?: string | null;
      [k: string]: any;
    };
    [k: string]: any;
  }[];
  unresolved_questions?: {
    question?: string;
    why_unresolved?: string;
    recommended_next_source?: string | null;
    [k: string]: any;
  }[];
  [k: string]: any;
}
