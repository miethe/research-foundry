/**
 * reportAnchors.test.ts — P2 Wave C unit tests for report_anchors consumption
 * utilities: block_id position lookup, per-block/per-section coverage
 * aggregation, and anchor filter matching.
 *
 * R1 fix (bug #2): the paragraph<->block_id RENDER-ORDER correlation
 * (formerly `buildParagraphAnchorSequence`, a buggy markdown-text heuristic)
 * has been removed from this module — that correlation now lives in
 * ReportRenderer.tsx via a React Context flag set by the `li`/`blockquote`
 * custom renderers (ground truth: the actual rendered tree). See
 * p4-components.test.tsx for the render-order regression tests (loose list,
 * blockquote, and post-list realignment).
 */

import { describe, it, expect } from "vitest";
import {
  buildAnchorPositionMap,
  computeAnchorFilterMatches,
  computeBlockCoverage,
  computeOverallCoverage,
  computeSectionCoverage,
  findAnchorBlock,
} from "./reportAnchors";
import type { RFClaim, RFReportAnchorBlock } from "@/types/rf";

function makeClaim(id: string, overrides: Partial<RFClaim> = {}): RFClaim {
  return {
    claim_id: id,
    text: `Claim ${id}`,
    status: "supported",
    sources: [],
    ...overrides,
  };
}

function makeBlock(overrides: Partial<RFReportAnchorBlock> & { block_id: string }): RFReportAnchorBlock {
  return {
    section_id: null,
    paragraph_ordinal: 0,
    text_hash: "abc123def456",
    claim_links: [],
    ...overrides,
  };
}

describe("buildAnchorPositionMap", () => {
  it("keys by (section_id, paragraph_ordinal)", () => {
    const anchors = [makeBlock({ block_id: "b0", section_id: "s1", paragraph_ordinal: 2 })];
    const map = buildAnchorPositionMap(anchors);
    expect(map.get("s1::2")?.block_id).toBe("b0");
  });

  it("returns an empty map for null/undefined input", () => {
    expect(buildAnchorPositionMap(null).size).toBe(0);
    expect(buildAnchorPositionMap(undefined).size).toBe(0);
  });
});

// ── computeBlockCoverage / computeSectionCoverage ────────────────────────────

describe("computeBlockCoverage", () => {
  const claims: RFClaim[] = [
    makeClaim("clm_supported", { status: "supported" }),
    makeClaim("clm_contradicted", { status: "contradicted" }),
    makeClaim("clm_inference", { status: "inference" }),
    makeClaim("clm_speculation", { status: "speculation" }),
    makeClaim("clm_unsupported", { status: "unsupported" }),
  ];

  it("classifies each resolved link by the linked claim's status", () => {
    const anchors: RFReportAnchorBlock[] = [
      makeBlock({
        block_id: "b0",
        claim_links: [
          { claim_id: "clm_supported", span_start: 0, span_end: 5, relation: "supports", link_status: "linked" },
          { claim_id: "clm_contradicted", span_start: 6, span_end: 11, relation: "contradicts", link_status: "linked" },
          { claim_id: "clm_inference", span_start: 12, span_end: 17, relation: "inferred_from", link_status: "linked" },
          { claim_id: "clm_speculation", span_start: 18, span_end: 23, relation: "inferred_from", link_status: "linked" },
          { claim_id: "clm_unsupported", span_start: 24, span_end: 29, relation: "context", link_status: "linked" },
        ],
      }),
    ];
    const [coverage] = computeBlockCoverage(anchors, claims);
    expect(coverage).toMatchObject({
      supported: 1,
      contradicted: 1,
      inference: 1,
      speculation: 1,
      unsupported: 1,
      stale: 0,
      missing: 0,
    });
    expect(coverage!.claimIds).toHaveLength(5);
  });

  it("counts missing_claim links separately and excludes them from claimIds", () => {
    const anchors: RFReportAnchorBlock[] = [
      makeBlock({
        block_id: "b0",
        claim_links: [
          { claim_id: "clm_dangling", span_start: 0, span_end: 5, relation: null, link_status: "missing_claim" },
        ],
      }),
    ];
    const [coverage] = computeBlockCoverage(anchors, claims);
    expect(coverage!.missing).toBe(1);
    expect(coverage!.claimIds).toHaveLength(0);
  });

  it("counts stale links (still classified by claim status too)", () => {
    const anchors: RFReportAnchorBlock[] = [
      makeBlock({
        block_id: "b0",
        claim_links: [
          { claim_id: "clm_supported", span_start: 0, span_end: 5, relation: "supports", link_status: "stale" },
        ],
      }),
    ];
    const [coverage] = computeBlockCoverage(anchors, claims);
    expect(coverage!.stale).toBe(1);
    expect(coverage!.supported).toBe(1);
  });

  it("dedupes claimIds when the same claim is linked twice in one block", () => {
    const anchors: RFReportAnchorBlock[] = [
      makeBlock({
        block_id: "b0",
        claim_links: [
          { claim_id: "clm_supported", span_start: 0, span_end: 5, relation: "supports", link_status: "linked" },
          { claim_id: "clm_supported", span_start: 10, span_end: 15, relation: "supports", link_status: "linked" },
        ],
      }),
    ];
    const [coverage] = computeBlockCoverage(anchors, claims);
    expect(coverage!.claimIds).toEqual(["clm_supported"]);
    expect(coverage!.supported).toBe(2); // link-count, not claim-count
  });

  it("returns [] for null anchors", () => {
    expect(computeBlockCoverage(null, claims)).toEqual([]);
  });
});

describe("computeSectionCoverage / computeOverallCoverage", () => {
  const claims: RFClaim[] = [
    makeClaim("clm_a", { status: "supported" }),
    makeClaim("clm_b", { status: "contradicted" }),
  ];

  const anchors: RFReportAnchorBlock[] = [
    makeBlock({
      block_id: "b0",
      section_id: "intro",
      paragraph_ordinal: 0,
      claim_links: [{ claim_id: "clm_a", span_start: 0, span_end: 5, relation: "supports", link_status: "linked" }],
    }),
    makeBlock({
      block_id: "b1",
      section_id: "findings",
      paragraph_ordinal: 0,
      claim_links: [{ claim_id: "clm_b", span_start: 0, span_end: 5, relation: "contradicts", link_status: "linked" }],
    }),
    makeBlock({ block_id: "b2", section_id: "findings", paragraph_ordinal: 1, claim_links: [] }),
  ];

  it("aggregates per-section counts and preserves section order of first appearance", () => {
    const blockCoverage = computeBlockCoverage(anchors, claims);
    const sections = computeSectionCoverage(blockCoverage);
    expect(sections.map((s) => s.sectionId)).toEqual(["intro", "findings"]);
    expect(sections[0]).toMatchObject({ paragraphs: 1, supported: 1, coveragePct: 100 });
    expect(sections[1]).toMatchObject({ paragraphs: 2, contradicted: 1 });
  });

  it("computeOverallCoverage rolls every block up into a single summary", () => {
    const blockCoverage = computeBlockCoverage(anchors, claims);
    const overall = computeOverallCoverage(blockCoverage);
    expect(overall.paragraphs).toBe(3);
    expect(overall.supported).toBe(1);
    expect(overall.contradicted).toBe(1);
  });

  it("coveragePct is 0 when a section has zero resolved links (no crash / no NaN)", () => {
    const emptyBlocks = computeBlockCoverage(
      [makeBlock({ block_id: "b0", section_id: "empty", claim_links: [] })],
      claims,
    );
    const [section] = computeSectionCoverage(emptyBlocks);
    expect(section!.coveragePct).toBe(0);
  });
});

// ── computeAnchorFilterMatches ────────────────────────────────────────────────

describe("computeAnchorFilterMatches", () => {
  const claims: RFClaim[] = [
    makeClaim("clm_a", { status: "supported" }),
    makeClaim("clm_b", { status: "contradicted" }),
  ];
  const anchors: RFReportAnchorBlock[] = [
    makeBlock({
      block_id: "b0",
      claim_links: [{ claim_id: "clm_a", span_start: 0, span_end: 5, relation: "supports", link_status: "linked" }],
    }),
    makeBlock({
      block_id: "b1",
      claim_links: [{ claim_id: "clm_b", span_start: 0, span_end: 5, relation: "contradicts", link_status: "linked" }],
    }),
  ];
  const blockCoverage = computeBlockCoverage(anchors, claims);

  it("returns empty sets when no filters are active", () => {
    const { blockIds, claimIds } = computeAnchorFilterMatches(blockCoverage, new Set());
    expect(blockIds.size).toBe(0);
    expect(claimIds.size).toBe(0);
  });

  it("matches only blocks with a link in the active category (OR across filters)", () => {
    const { blockIds, claimIds } = computeAnchorFilterMatches(blockCoverage, new Set(["contradicted"]));
    expect(blockIds).toEqual(new Set(["b1"]));
    expect(claimIds).toEqual(new Set(["clm_b"]));
  });
});

// ── findAnchorBlock ───────────────────────────────────────────────────────────

describe("findAnchorBlock", () => {
  it("finds a block by block_id", () => {
    const anchors = [makeBlock({ block_id: "b0" }), makeBlock({ block_id: "b1" })];
    expect(findAnchorBlock(anchors, "b1")?.block_id).toBe("b1");
  });

  it("returns null when not found or anchors is null", () => {
    expect(findAnchorBlock([makeBlock({ block_id: "b0" })], "missing")).toBeNull();
    expect(findAnchorBlock(null, "b0")).toBeNull();
  });
});
