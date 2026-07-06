/**
 * reportAnchors.ts — pure utilities for consuming `report_anchors` (schema
 * 1.4, §16) in the audit UI: a block_id position lookup, per-block/
 * per-section coverage aggregation, and anchor-driven highlight filter sets.
 *
 * D7/D9 discipline: the backend is the sole source of anchor DERIVATION
 * (which claims link where, relation inference, drift detection). This
 * module never re-derives that — it only aggregates the anchor data the
 * backend already computed into UI-shaped coverage summaries.
 *
 * R1 FIX (bug #2, HIGH): paragraph<->block_id RENDER-ORDER correlation used
 * to live here as `buildParagraphAnchorSequence()`, a markdown-text heuristic
 * that guessed which paragraphs were "top-level" (not inside a list item or
 * blockquote) by regex-matching list/blockquote MARKERS on raw source lines.
 * That heuristic assumed every list item consumes ZERO render slots — true
 * only for TIGHT lists. A LOOSE list (blank line between items — common in
 * LLM-generated markdown) renders a real `<p>` PER ITEM, desyncing the flat
 * paragraph counter for the rest of the document after the list. It has been
 * REMOVED. The correlation now lives in ReportRenderer.tsx itself, using a
 * React Context flag set by the `li`/`blockquote` custom renderers (ground
 * truth: the ACTUAL rendered React tree, not a markdown-text guess) so a
 * `<p>` rendered inside either container never consumes an anchor slot,
 * regardless of tight vs. loose lists or nested blockquotes. This exactly
 * mirrors the backend's `container_depth == 0` rule.
 *
 * Consumers: ReportRenderer.tsx, auditStateMachine.ts, ClaimAuditWorkbench.tsx.
 */

import type { RFClaim, RFReportAnchorBlock } from "@/types/rf";

// ── Position lookup (used by callers that need a block by (section, ordinal)) ─

function positionKey(sectionId: string | null, ordinal: number): string {
  return `${sectionId ?? ""}::${ordinal}`;
}

/** Builds a (section_id, paragraph_ordinal) -> block lookup from report_anchors. */
export function buildAnchorPositionMap(
  anchors: RFReportAnchorBlock[] | null | undefined,
): Map<string, RFReportAnchorBlock> {
  const map = new Map<string, RFReportAnchorBlock>();
  for (const block of anchors ?? []) {
    map.set(positionKey(block.section_id, block.paragraph_ordinal), block);
  }
  return map;
}

// ── Coverage aggregation ──────────────────────────────────────────────────────

export type AnchorFilterKey = "unsupported" | "contradicted" | "inference" | "speculation" | "stale";

export interface BlockCoverage {
  blockId: string;
  sectionId: string | null;
  paragraphOrdinal: number;
  supported: number;
  contradicted: number;
  inference: number;
  speculation: number;
  unsupported: number;
  /** Count of claim_links with link_status="stale" (drift — text changed since anchoring). */
  stale: number;
  /** Count of claim_links with link_status="missing_claim" (dangling [claim:] tag). */
  missing: number;
  /** De-duplicated claim_ids with a resolved (non-missing) link in this block. */
  claimIds: string[];
}

function classifyClaim(
  claim: RFClaim | undefined,
): "supported" | "contradicted" | "inference" | "speculation" | "unsupported" {
  const status = claim?.status;
  if (status === "supported" || status === "mixed") return "supported";
  if (status === "contradicted") return "contradicted";
  if (status === "inference") return "inference";
  if (status === "speculation") return "speculation";
  return "unsupported";
}

/** Per-paragraph coverage summary, one entry per report_anchors block. */
export function computeBlockCoverage(
  anchors: RFReportAnchorBlock[] | null | undefined,
  claims: RFClaim[],
): BlockCoverage[] {
  const claimsById = new Map(claims.map((c) => [c.claim_id, c] as const));
  return (anchors ?? []).map((block) => {
    const coverage: BlockCoverage = {
      blockId: block.block_id,
      sectionId: block.section_id,
      paragraphOrdinal: block.paragraph_ordinal,
      supported: 0,
      contradicted: 0,
      inference: 0,
      speculation: 0,
      unsupported: 0,
      stale: 0,
      missing: 0,
      claimIds: [],
    };
    const seen = new Set<string>();
    for (const link of block.claim_links) {
      if (link.link_status === "missing_claim") {
        coverage.missing += 1;
        continue;
      }
      if (link.link_status === "stale") coverage.stale += 1;
      const bucket = classifyClaim(claimsById.get(link.claim_id));
      coverage[bucket] += 1;
      if (!seen.has(link.claim_id)) {
        seen.add(link.claim_id);
        coverage.claimIds.push(link.claim_id);
      }
    }
    return coverage;
  });
}

export interface SectionCoverage {
  sectionId: string | null;
  paragraphs: number;
  supported: number;
  contradicted: number;
  inference: number;
  speculation: number;
  unsupported: number;
  stale: number;
  missing: number;
  /** (supported + inference) / all resolved claim-link classifications, 0-100. 0 when no links. */
  coveragePct: number;
}

/** Aggregates per-block coverage into per-section summaries, preserving first-seen section order. */
export function computeSectionCoverage(blocks: BlockCoverage[]): SectionCoverage[] {
  const order: (string | null)[] = [];
  const bySection = new Map<string | null, SectionCoverage>();
  for (const b of blocks) {
    let s = bySection.get(b.sectionId);
    if (!s) {
      s = {
        sectionId: b.sectionId,
        paragraphs: 0,
        supported: 0,
        contradicted: 0,
        inference: 0,
        speculation: 0,
        unsupported: 0,
        stale: 0,
        missing: 0,
        coveragePct: 0,
      };
      bySection.set(b.sectionId, s);
      order.push(b.sectionId);
    }
    s.paragraphs += 1;
    s.supported += b.supported;
    s.contradicted += b.contradicted;
    s.inference += b.inference;
    s.speculation += b.speculation;
    s.unsupported += b.unsupported;
    s.stale += b.stale;
    s.missing += b.missing;
  }
  for (const s of bySection.values()) {
    const total = s.supported + s.contradicted + s.inference + s.speculation + s.unsupported;
    s.coveragePct = total > 0 ? Math.round(((s.supported + s.inference) / total) * 100) : 0;
  }
  return order.map((id) => bySection.get(id)!);
}

/** Overall (whole-report) coverage rollup — the header summary of ReportCoverageStrip. */
export function computeOverallCoverage(blocks: BlockCoverage[]): SectionCoverage {
  const sections = computeSectionCoverage(blocks.map((b) => ({ ...b, sectionId: null })));
  return (
    sections[0] ?? {
      sectionId: null,
      paragraphs: 0,
      supported: 0,
      contradicted: 0,
      inference: 0,
      speculation: 0,
      unsupported: 0,
      stale: 0,
      missing: 0,
      coveragePct: 0,
    }
  );
}

/**
 * Resolves which block_ids / claim_ids match the active anchor filter set
 * (OR logic across filters — a paragraph matches if it has at least one
 * link in ANY active category). Empty filter set -> empty result (no
 * anchor-filter mode active; caller should treat this as "not filtering").
 */
export function computeAnchorFilterMatches(
  blocks: BlockCoverage[],
  filters: Set<AnchorFilterKey>,
): { blockIds: Set<string>; claimIds: Set<string> } {
  const blockIds = new Set<string>();
  const claimIds = new Set<string>();
  if (filters.size === 0) return { blockIds, claimIds };
  for (const b of blocks) {
    const matches =
      (filters.has("unsupported") && b.unsupported > 0) ||
      (filters.has("contradicted") && b.contradicted > 0) ||
      (filters.has("inference") && b.inference > 0) ||
      (filters.has("speculation") && b.speculation > 0) ||
      (filters.has("stale") && b.stale > 0);
    if (matches) {
      blockIds.add(b.blockId);
      for (const id of b.claimIds) claimIds.add(id);
    }
  }
  return { blockIds, claimIds };
}

/** Looks up a single anchor block by block_id. Returns null when absent. */
export function findAnchorBlock(
  anchors: RFReportAnchorBlock[] | null | undefined,
  blockId: string,
): RFReportAnchorBlock | null {
  return (anchors ?? []).find((b) => b.block_id === blockId) ?? null;
}
