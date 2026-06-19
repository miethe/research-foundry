/**
 * P4-VITEST-INFERENCE fixtures: inference claim scenarios for ProvenanceModal.
 *
 * Provides:
 *   INFERENCE_WITH_BASIS   — status=inference, from_claims=[clm_010, clm_022]
 *                            Expected: linked chain renders (modal-from-claims)
 *
 *   INFERENCE_EMPTY_BASIS  — status=inference, from_claims=[]
 *                            Expected: RIB-018 warning renders (modal-rib018-warning)
 *
 *   BASIS_CLAIM_010        — supporting factual claim (clm_010)
 *   BASIS_CLAIM_022        — supporting factual claim (clm_022)
 */

import type { RFClaim } from "@/types/rf";

/** Supporting claim referenced as inference basis. */
export const BASIS_CLAIM_010: RFClaim = {
  claim_id:    "clm_010",
  text:        "The Python SDK hook events include PreToolUse and PostToolUse for tool lifecycle observation.",
  materiality: "core",
  claim_type:  "factual",
  status:      "supported",
  confidence:  "high",
  inference_basis: { from_claims: [], reasoning_summary: null },
  sources: [],
};

/** Supporting claim referenced as inference basis. */
export const BASIS_CLAIM_022: RFClaim = {
  claim_id:    "clm_022",
  text:        "SubagentStart and SubagentStop events are available in the Python SDK for tracking subagent lifecycle.",
  materiality: "core",
  claim_type:  "factual",
  status:      "supported",
  confidence:  "high",
  inference_basis: { from_claims: [], reasoning_summary: null },
  sources: [],
};

/** Inference claim WITH a populated from_claims basis — chain must render. */
export const INFERENCE_WITH_BASIS: RFClaim = {
  claim_id:    "clm_050",
  text:        "The Python SDK can monitor the complete lifecycle of both tools and subagents using available hook events.",
  materiality: "core",
  claim_type:  "inference",
  status:      "inference",
  confidence:  "medium",
  inference_basis: {
    from_claims:       ["clm_010", "clm_022"],
    reasoning_summary: "Combining tool-lifecycle and subagent-lifecycle hooks covers the full execution graph.",
  },
  sources: [],
};

/** Inference claim with EMPTY from_claims — RIB-018 warning must render. */
export const INFERENCE_EMPTY_BASIS: RFClaim = {
  claim_id:    "clm_051",
  text:        "The agent SDK allows comprehensive observability without any documented basis claims.",
  materiality: "background",
  claim_type:  "inference",
  status:      "inference",
  confidence:  "low",
  inference_basis: {
    from_claims:       [],
    reasoning_summary: null,
  },
  sources: [],
};

/** Convenience: all claims needed to render the basis chain scenario. */
export const INFERENCE_CLAIMS_WITH_BASIS = [
  BASIS_CLAIM_010,
  BASIS_CLAIM_022,
  INFERENCE_WITH_BASIS,
];

/** Convenience: claims for the empty-basis scenario. */
export const INFERENCE_CLAIMS_EMPTY_BASIS = [INFERENCE_EMPTY_BASIS];
