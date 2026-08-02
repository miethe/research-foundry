/**
 * builderCoverage.claimresolution.test.ts — AC-3/AC-5 coverage for the
 * runs-viewer-builder-live-claim-previews fix.
 *
 * builderCoverage.ts's audit-summary and issue functions used to import
 * lib/builderMocks.ts's resolveBuilderClaimPreview() directly and call it
 * UNCONDITIONALLY — so a real (loopback) claim, absent from the six-entry
 * mock dict, silently resolved to null and its confidence/materiality was
 * never consulted (weakConfidence always false for real claims; no distinct
 * "unresolved" signal existed at all).
 *
 * These tests exercise the pure functions directly with a fake
 * ClaimPreviewResolver — no React, no network — asserting:
 *   1. AC-3: an unresolved claim is counted in its own bucket, is NEVER
 *      folded into "supported" or "weak confidence", and lowers (never
 *      inflates) coveragePct.
 *   2. AC-5: coverage arithmetic matches expectations against a resolver
 *      shaped like the real router payload (confidence/materiality/status
 *      values straight from a live `rf serve` /catalog/items/{id} response
 *      recorded in this contract's Completion Report).
 */
import { describe, expect, it } from "vitest";
import { computeBlockAuditSummary, computeDraftAuditSummary, computeDraftIssues } from "./builderCoverage";
import { CLAIM_PREVIEW_UNKNOWN } from "./builderMocks";
import type { BuilderClaimPreview, ClaimPreviewResolver } from "./builderMocks";
import type { ReportBlock, ReportClaimLink } from "@/types/rf/report_draft";

function makeBlock(overrides: Partial<ReportBlock> & { block_id: string }): ReportBlock {
  return {
    block_type: "paragraph",
    order: 0,
    markdown: "",
    materiality: "material",
    linked_claim_ids: [],
    linked_source_ids: [],
    coverage_status: "supported",
    risk_flags: [],
    ...overrides,
  };
}

function makeLink(overrides: Partial<ReportClaimLink> & { claim_link_id: string; block_id: string; claim_id: string }): ReportClaimLink {
  return {
    source_run_id: null,
    catalog_item_id: `ci_${overrides.claim_id}`,
    relation: "supports",
    span_start: 0,
    span_end: 10,
    quote_text_hash: null,
    link_status: "linked",
    ...overrides,
  };
}

function makePreview(overrides: Partial<BuilderClaimPreview> & { claim_id: string }): BuilderClaimPreview {
  return {
    text: "Preview text",
    status: "supported",
    confidence: "medium",
    materiality: "material",
    sources: [],
    ...overrides,
  };
}

describe("computeBlockAuditSummary — AC-3 unresolved bucket", () => {
  it("counts an unresolvable claim as `unresolved`, not `supported`, and excludes it from the numerator", () => {
    const block = makeBlock({ block_id: "b1" });
    const links = [
      makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_ok" }),
      makeLink({ claim_link_id: "l2", block_id: "b1", claim_id: "clm_gone" }),
    ];
    const resolve: ClaimPreviewResolver = (claimId) =>
      claimId === "clm_ok" ? makePreview({ claim_id: "clm_ok", confidence: "high" }) : CLAIM_PREVIEW_UNKNOWN;

    const summary = computeBlockAuditSummary(block, links, resolve);

    expect(summary.supported).toBe(1);
    expect(summary.unresolved).toBe(1);
    // total = 1 supported + 1 unresolved = 2; coveragePct = supported / total = 50%,
    // NOT 100% (which is what a "silently treated as covered" bug would produce).
    expect(summary.coveragePct).toBe(50);
    expect(summary.isApplicable).toBe(true);
  });

  it("never classifies an unresolvable claim as low-confidence (AC-3 distinctness)", () => {
    const block = makeBlock({ block_id: "b1" });
    const links = [makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_gone" })];
    const resolve: ClaimPreviewResolver = () => CLAIM_PREVIEW_UNKNOWN;

    const summary = computeBlockAuditSummary(block, links, resolve);
    expect(summary.unresolved).toBe(1);
    expect(summary.supported).toBe(0);
    expect(summary.unsupported).toBe(0);
  });

  it("a fully-resolved block scores 100% (regression guard — resolver wiring doesn't break the happy path)", () => {
    const block = makeBlock({ block_id: "b1" });
    const links = [makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_ok" })];
    const resolve: ClaimPreviewResolver = () => makePreview({ claim_id: "clm_ok" });

    const summary = computeBlockAuditSummary(block, links, resolve);
    expect(summary.coveragePct).toBe(100);
    expect(summary.unresolved).toBe(0);
  });
});

describe("computeDraftAuditSummary — aggregation", () => {
  it("sums `unresolved` across material blocks and factors it into the aggregate coveragePct", () => {
    const blocks = [makeBlock({ block_id: "b1" }), makeBlock({ block_id: "b2" })];
    const links = [
      makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_ok" }),
      makeLink({ claim_link_id: "l2", block_id: "b2", claim_id: "clm_gone" }),
    ];
    const resolve: ClaimPreviewResolver = (claimId) =>
      claimId === "clm_ok" ? makePreview({ claim_id: "clm_ok" }) : CLAIM_PREVIEW_UNKNOWN;

    const summary = computeDraftAuditSummary(blocks, links, resolve);
    expect(summary.supported).toBe(1);
    expect(summary.unresolved).toBe(1);
    expect(summary.coveragePct).toBe(50);
  });
});

describe("computeDraftIssues — weak_confidence vs unresolved_claim distinctness (AC-3)", () => {
  it("routes a resolved low-confidence claim to weak_confidence and an unresolvable claim to unresolved_claim, never both", () => {
    const blocks = [makeBlock({ block_id: "b1" }), makeBlock({ block_id: "b2" })];
    const links = [
      makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_weak" }),
      makeLink({ claim_link_id: "l2", block_id: "b2", claim_id: "clm_gone" }),
    ];
    const resolve: ClaimPreviewResolver = (claimId) => {
      if (claimId === "clm_weak") return makePreview({ claim_id: "clm_weak", confidence: "low" });
      return CLAIM_PREVIEW_UNKNOWN;
    };

    const issues = computeDraftIssues(blocks, links, resolve);
    const weak = issues.find((i) => i.key === "weak_confidence");
    const unresolved = issues.find((i) => i.key === "unresolved_claim");

    expect(weak?.count).toBe(1);
    expect(unresolved?.count).toBe(1);
  });

  it("a resolver that always returns unknown never contributes to weak_confidence", () => {
    const blocks = [makeBlock({ block_id: "b1" })];
    const links = [makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_gone" })];
    const resolve: ClaimPreviewResolver = () => CLAIM_PREVIEW_UNKNOWN;

    const issues = computeDraftIssues(blocks, links, resolve);
    expect(issues.find((i) => i.key === "weak_confidence")?.count).toBe(0);
    expect(issues.find((i) => i.key === "unresolved_claim")?.count).toBe(1);
  });
});

describe("confidence-unknown sibling defect (fix pass, post-sprint) — never fabricated 'medium'", () => {
  it("a resolved claim with confidence 'unknown' is counted in `confidenceUnknown`, not `supported`, and is excluded from the coveragePct numerator", () => {
    const block = makeBlock({ block_id: "b1" });
    const links = [
      makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_scored" }),
      makeLink({ claim_link_id: "l2", block_id: "b1", claim_id: "clm_unscored" }),
    ];
    const resolve: ClaimPreviewResolver = (claimId) =>
      claimId === "clm_scored"
        ? makePreview({ claim_id: "clm_scored", confidence: "high" })
        : makePreview({ claim_id: "clm_unscored", confidence: "unknown" });

    const summary = computeBlockAuditSummary(block, links, resolve);

    expect(summary.supported).toBe(1);
    expect(summary.confidenceUnknown).toBe(1);
    // total = 1 supported + 1 confidenceUnknown = 2 -> 50%, not 100% (which is
    // what silently counting an unscored claim as "supported" would produce).
    expect(summary.coveragePct).toBe(50);
  });

  it("a resolved-but-unscored claim is never routed through weak_confidence (that was the original defect: medium != low let it escape entirely)", () => {
    const blocks = [makeBlock({ block_id: "b1" })];
    const links = [makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_unscored" })];
    const resolve: ClaimPreviewResolver = () => makePreview({ claim_id: "clm_unscored", confidence: "unknown" });

    const issues = computeDraftIssues(blocks, links, resolve);
    expect(issues.find((i) => i.key === "weak_confidence")?.count).toBe(0);
    expect(issues.find((i) => i.key === "confidence_unknown")?.count).toBe(1);
    // Distinct from unresolved_claim — the claim itself resolved fine.
    expect(issues.find((i) => i.key === "unresolved_claim")?.count).toBe(0);
  });

  it("computeDraftAuditSummary aggregates confidenceUnknown across material blocks", () => {
    const blocks = [makeBlock({ block_id: "b1" }), makeBlock({ block_id: "b2" })];
    const links = [
      makeLink({ claim_link_id: "l1", block_id: "b1", claim_id: "clm_scored" }),
      makeLink({ claim_link_id: "l2", block_id: "b2", claim_id: "clm_unscored" }),
    ];
    const resolve: ClaimPreviewResolver = (claimId) =>
      claimId === "clm_scored"
        ? makePreview({ claim_id: "clm_scored" })
        : makePreview({ claim_id: "clm_unscored", confidence: "unknown" });

    const summary = computeDraftAuditSummary(blocks, links, resolve);
    expect(summary.supported).toBe(1);
    expect(summary.confidenceUnknown).toBe(1);
    expect(summary.coveragePct).toBe(50);
  });
});
