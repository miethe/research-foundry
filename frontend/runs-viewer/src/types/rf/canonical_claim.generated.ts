/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Optional mutable grouping concept. It references immutable source assertions by ID and version and never mutates their evidence or lifecycle.
 */
export type CanonicalClaim = {
  [k: string]: any;
} & {
  schema_version: "1.0";
  type: "canonical_claim";
  canonical_claim_id: string;
  canonical_claim_version: number;
  state: "proposed" | "reviewed" | "active" | "split" | "superseded" | "rolled_back";
  statement: string;
  /**
   * RPC-1.4 additive field (research-provenance-continuity P1, SOL-12/18, round 2; WIDENED round 3, SOL-25/26/RC-2). OPTIONAL, additive, service-internal integrity value -- NOT part of `canonical_claim_id`'s own identity (which stays stable across versions, freeze doc §15.2). `sha256-canonical-json-v1` over `{statement, source_assertion_refs, inference_refs, state, canonical_claim_version, replaces, replacement_claims, reversal}` AT THE CURRENT `canonical_claim_version` (freeze doc §15.2 item 3's per-version digest, now persisted as a real field rather than left unstored). Round 3 (RC-2) ADDS `canonical_claim_version`/`replaces`/`replacement_claims`/`reversal` to the round-2 formula -- SOL-26's accepted attack: the round-2 formula omitted the version integer and the reversal/replacement fields entirely, so `canonical_claim_version` could change (e.g. `1 -> 999`) or `replaces`/`replacement_claims`/`reversal.resulting_claims` could be substituted with NO digest change. A P4 writer under this contract MUST populate it on every record it writes; a reader/replay path MUST validate it when present (recompute over the same eight fields and compare); legacy absence (a record written before this field existed) is tolerated read-only, never required retroactively. The generation-manifest entry recorded at promotion time (freeze doc §17.7a, RC-2) is the tamper-evidence ROOT this digest is checked against on read/replay -- not merely the record's own stored field. See freeze doc §15.2/§17.7a for the exact formula, the worked test vector, and the P7 verifying task.
   */
  version_digest?: string | null;
  /**
   * @minItems 1
   */
  source_assertion_refs: [
    {
      assertion_id: string;
      assertion_version: number;
      relation: "supports" | "contradicts" | "context";
    },
    ...{
      assertion_id: string;
      assertion_version: number;
      relation: "supports" | "contradicts" | "context";
    }[]
  ];
  /**
   * RPC-1.4 additive field (research-provenance-continuity P1, F3). Optional, supplementary support refs to exact inference_record versions. RPC-4.3's canonical-claim materializer must be able to publish a canonical claim from "exact assertion/inference support refs" together, but the shipped v1 schema only had `source_assertion_refs` (a provable, concrete gap). This field is purely additive: it is OPTIONAL and has no `minItems`, so a legacy or assertion-only canonical claim that never populates it remains fully valid with the field absent. `source_assertion_refs` below stays `minItems: 1` and REQUIRED, unchanged -- every canonical claim must still ground in at least one exact, immutable source_assertion; `inference_refs` can only ever ADD supplementary reasoning-based support, never substitute for direct assertion grounding. If a future phase proves a concrete need for an inference-only canonical claim (zero source_assertion_refs), that is a separate, separately-justified amendment -- not something this freeze pre-authorizes.
   */
  inference_refs?: {
    inference_id: string;
    inference_version: number;
    relation: "supports" | "contradicts" | "context";
  }[];
  replaces?: {
    canonical_claim_id: string;
    canonical_claim_version: number;
  }[];
  /**
   * Versioned canonical claims that replace this split or rolled-back claim.
   *
   * @minItems 1
   */
  replacement_claims?: [
    {
      canonical_claim_id: string;
      canonical_claim_version: number;
    },
    ...{
      canonical_claim_id: string;
      canonical_claim_version: number;
    }[]
  ];
  reversal?: {
    event_id: string;
    reason: string;
    provenance: {
      recorded_by: string;
      recorded_at: string;
    };
    /**
     * @minItems 1
     */
    resulting_claims: [
      {
        canonical_claim_id: string;
        canonical_claim_version: number;
      },
      ...{
        canonical_claim_id: string;
        canonical_claim_version: number;
      }[]
    ];
  };
};
