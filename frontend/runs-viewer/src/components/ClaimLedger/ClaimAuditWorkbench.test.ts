/**
 * ClaimAuditWorkbench.test.ts — Unit tests for deriveCanonicalMergeGroup().
 *
 * P5-02 (assertion-ledger-activation-v1): canonical-claim merge-review
 * grouping is derived entirely from already-loaded run.claims (no fetch), so
 * the pure helper is the right unit under test — it covers the same logic
 * ClaimAuditWorkbench's ClaimInspector renders against, without needing to
 * mount the full workbench tree (which pulls in several hook-backed panels
 * unrelated to this contract).
 *
 * Covers:
 * - null when the claim has no persistent_references
 * - null when persistent_references.canonical_claim_id is absent
 * - sibling claims sharing the same canonical_claim_id are found, self excluded
 * - claims with a *different* canonical_claim_id are excluded
 * - canonicalClaimVersion falls back to null when absent
 */

import { describe, it, expect } from "vitest";
import { deriveCanonicalMergeGroup } from "./ClaimAuditWorkbench";
import type { RFClaim } from "@/types/rf";

function makeClaim(id: string, overrides: Partial<RFClaim> = {}): RFClaim {
  return {
    claim_id: id,
    text: `Text for ${id}`,
    sources: [],
    ...overrides,
  };
}

describe("deriveCanonicalMergeGroup", () => {
  it("returns null for a null claim", () => {
    expect(deriveCanonicalMergeGroup([], null)).toBeNull();
  });

  it("returns null when the claim has no persistent_references", () => {
    const claim = makeClaim("clm_001");
    expect(deriveCanonicalMergeGroup([claim], claim)).toBeNull();
  });

  it("returns null when persistent_references.canonical_claim_id is absent", () => {
    const claim = makeClaim("clm_001", {
      persistent_references: { source_assertion_id: "ast_1" },
    });
    expect(deriveCanonicalMergeGroup([claim], claim)).toBeNull();
  });

  it("finds sibling claims sharing the same canonical_claim_id, excluding self", () => {
    const selected = makeClaim("clm_001", {
      persistent_references: { canonical_claim_id: "ccl_demo", canonical_claim_version: 2 },
    });
    const sibling = makeClaim("clm_002", {
      persistent_references: { canonical_claim_id: "ccl_demo", canonical_claim_version: 2 },
    });
    const unrelated = makeClaim("clm_003", {
      persistent_references: { canonical_claim_id: "ccl_other" },
    });
    const noRefs = makeClaim("clm_004");

    const group = deriveCanonicalMergeGroup([selected, sibling, unrelated, noRefs], selected);

    expect(group).not.toBeNull();
    expect(group?.canonicalClaimId).toBe("ccl_demo");
    expect(group?.canonicalClaimVersion).toBe(2);
    expect(group?.siblingClaims.map((c) => c.claim_id)).toEqual(["clm_002"]);
  });

  it("returns an empty siblingClaims array when no other claim shares the canonical_claim_id", () => {
    const selected = makeClaim("clm_001", {
      persistent_references: { canonical_claim_id: "ccl_solo" },
    });
    const group = deriveCanonicalMergeGroup([selected], selected);
    expect(group).not.toBeNull();
    expect(group?.siblingClaims).toEqual([]);
    expect(group?.canonicalClaimVersion).toBeNull();
  });
});
