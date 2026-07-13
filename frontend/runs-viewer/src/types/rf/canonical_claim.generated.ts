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
