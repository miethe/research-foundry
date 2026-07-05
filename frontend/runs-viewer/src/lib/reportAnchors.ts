/**
 * reportAnchors.ts — pure utilities for consuming `report_anchors` (schema
 * 1.4, §16) in the audit UI: paragraph <-> DOM correlation, per-block/
 * per-section coverage aggregation, and anchor-driven highlight filter sets.
 *
 * D7/D9 discipline: the backend is the sole source of anchor DERIVATION
 * (which claims link where, relation inference, drift detection). This
 * module never re-derives that. It only:
 *   (a) positionally correlates ReportRenderer's rendered `<p>` elements back
 *       to the backend-provided `block_id`, using the SAME
 *       heading-slug/ordinal-tracking approach reportOutlineUtils.ts already
 *       uses to mirror the backend's section_id computation for DOM anchor
 *       ids — this is precedent already established in this codebase, not a
 *       new re-derivation of claim/relation semantics; and
 *   (b) aggregates the anchor data the backend already computed into
 *       UI-shaped coverage summaries.
 *
 * KNOWN GAP (matches the backend's own documented v1.4 scope, see
 * export_service.py::derive_report_anchors docstring): only top-level
 * paragraphs are anchored. buildParagraphAnchorSequence() degrades
 * gracefully (returns `blockId: null`, never throws) for content it cannot
 * confidently position — a blockquoted paragraph still consumes a render
 * slot (react-markdown renders it as a nested `<p>`) but is never anchored;
 * a *tight* list item does not render as `<p>` at all (react-markdown
 * renders it inline inside `<li>`) so it is excluded from the sequence
 * entirely. Loose lists are an edge case this module does not attempt to
 * disambiguate from tight ones (the backend doesn't handle them either); a
 * mispositioned tail after a loose list is a bounded, self-correcting-at-
 * next-section-boundary degradation, not a crash.
 *
 * Consumers: ReportRenderer.tsx, auditStateMachine.ts, ClaimAuditWorkbench.tsx.
 */

import type { RFClaim, RFReportAnchorBlock } from "@/types/rf";
import { slugify } from "@/components/ReportOverlay/reportOutlineUtils";

// ── Paragraph <-> block_id positional correlation ────────────────────────────

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

export interface ParagraphAnchorSlot {
  blockId: string | null;
}

/**
 * Walks the raw report markdown and returns, IN THE SAME ORDER react-markdown
 * invokes the `p()` custom renderer, the resolved `block_id` (or null) for
 * each rendered paragraph. See module docstring for the documented gap on
 * blockquote/list nesting.
 */
export function buildParagraphAnchorSequence(
  markdown: string,
  anchors: RFReportAnchorBlock[] | null | undefined,
): ParagraphAnchorSlot[] {
  // D9 legacy-mode short-circuit: no anchors to correlate, no work to do.
  if (anchors == null) return [];

  const positionMap = buildAnchorPositionMap(anchors);
  const sequence: ParagraphAnchorSlot[] = [];

  const lines = markdown.split(/\r?\n/);
  let inFence = false;
  let sectionId: string | null = null;
  const sectionSlugCounts: Record<string, number> = {};
  const ordinalBySection: Record<string, number> = {};

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i] ?? "";
    const trimmed = rawLine.trim();

    if (/^```/.test(trimmed)) {
      inFence = !inFence;
      i += 1;
      continue;
    }
    if (inFence) { i += 1; continue; }
    if (!trimmed) { i += 1; continue; }

    const headingMatch = rawLine.match(/^(#{2,3})\s+(.+)$/);
    if (headingMatch) {
      const rawText = (headingMatch[2] ?? "")
        .trim()
        .replace(/\*\*(.+?)\*\*/g, "$1")
        .replace(/\*(.+?)\*/g, "$1")
        .replace(/`(.+?)`/g, "$1")
        .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");
      const baseSlug = slugify(rawText);
      if (baseSlug) {
        const count = sectionSlugCounts[baseSlug] ?? 0;
        sectionSlugCounts[baseSlug] = count + 1;
        sectionId = count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;
      }
      i += 1;
      continue;
    }

    // Gather a block of consecutive non-blank, non-heading, non-fence lines.
    const blockLines: string[] = [];
    while (
      i < lines.length &&
      (lines[i] ?? "").trim() &&
      !/^```/.test((lines[i] ?? "").trim()) &&
      !/^(#{2,3})\s+/.test(lines[i] ?? "")
    ) {
      blockLines.push(lines[i] ?? "");
      i += 1;
    }
    if (blockLines.length === 0) { i += 1; continue; }

    const firstLine = (blockLines[0] ?? "").trimStart();
    const isBlockquote = firstLine.startsWith(">");
    const isListItem = /^(\s*)([-*+]|\d+[.)])\s+/.test(blockLines[0] ?? "");

    if (isListItem) {
      // Tight-list assumption: react-markdown renders this inline inside
      // <li>, never as a standalone <p> — no sequence slot is consumed.
      continue;
    }

    if (isBlockquote) {
      // Renders as a nested <p> (consumes a slot) but is never anchored.
      sequence.push({ blockId: null });
      continue;
    }

    const sectionKey = sectionId ?? "";
    const ordinal = ordinalBySection[sectionKey] ?? 0;
    ordinalBySection[sectionKey] = ordinal + 1;
    const block = positionMap.get(positionKey(sectionId, ordinal));
    sequence.push({ blockId: block?.block_id ?? null });
  }

  return sequence;
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
