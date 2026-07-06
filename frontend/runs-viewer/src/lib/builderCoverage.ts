/**
 * builderCoverage.ts — pure derivation helpers for the Report Builder UI
 * (public-multiuser-p2p3, Phase 3 / Wave F).
 *
 * Unlike lib/reportAnchors.ts (which aggregates BACKEND-derived anchors from
 * an exported run.json), a builder draft already carries its own
 * backend-computed per-block `coverage_status` (builder_service.py::
 * _compute_coverage_status) — there is no re-derivation to do there. What
 * IS purely a frontend concern is turning `blocks[]` + `claim_links[]` into
 * the UI shapes the mockup calls for: a heading outline, a paragraph-level
 * audit summary (counts + %), and an issues list. None of this overrides or
 * second-guesses coverage_status; it only reads it.
 */

import type { ReportBlock, ReportClaimLink } from "@/types/rf/report_draft";
import { resolveBuilderClaimPreview } from "./builderMocks";

// ── Outline ───────────────────────────────────────────────────────────────────

export interface BuilderOutlineSection {
  headingBlockId: string;
  /** 1-based top-level ordinal shown in the mockup ("1.", "2.", "3.1", …). */
  numberLabel: string;
  text: string;
  level: 2 | 3;
  /** Non-heading blocks belonging to this section, in document order (up to the next heading). */
  bodyBlockIds: string[];
}

/**
 * Strips a heading's own markdown hashes AND any pre-baked ordinal prefix
 * ("1.", "3.2", "1)") the author may already have typed — numbering is
 * this module's job (numberLabel), so a heading that already embeds one
 * (as every section in the mockup/demo draft does) must not double up when
 * numberLabel + text are rendered together ("2. 2. Architecture overview").
 */
function headingText(markdown: string): { level: 2 | 3; text: string } {
  const m = /^(#{2,3})\s+(.*)$/.exec(markdown.trim());
  const raw = m ? m[2].trim() : markdown.trim();
  const level: 2 | 3 = m && m[1].length === 3 ? 3 : 2;
  const text = raw.replace(/^\d+(?:\.\d+)*[.)]?\s+/, "");
  return { level, text };
}

/** Builds a numbered outline (h2/h3) from ordered draft blocks, grouping body blocks under their nearest preceding heading. */
export function buildOutline(blocks: ReportBlock[]): BuilderOutlineSection[] {
  const sorted = [...blocks].sort((a, b) => a.order - b.order);
  const sections: BuilderOutlineSection[] = [];
  let h2Counter = 0;
  let h3Counter = 0;
  let current: BuilderOutlineSection | null = null;

  for (const b of sorted) {
    if (b.block_type === "heading") {
      const { level, text } = headingText(b.markdown);
      let numberLabel: string;
      if (level === 2) {
        h2Counter += 1;
        h3Counter = 0;
        numberLabel = `${h2Counter}.`;
      } else {
        h3Counter += 1;
        numberLabel = `${h2Counter}.${h3Counter}`;
      }
      current = { headingBlockId: b.block_id, numberLabel, text, level, bodyBlockIds: [] };
      sections.push(current);
    } else if (current) {
      current.bodyBlockIds.push(b.block_id);
    }
  }
  return sections;
}

/** Body (non-heading) blocks belonging to a section, ordered, plus the heading block itself. */
export function sectionBlockIds(section: BuilderOutlineSection): string[] {
  return [section.headingBlockId, ...section.bodyBlockIds];
}

// ── Paragraph / section audit summary ─────────────────────────────────────────

export interface ParagraphAuditSummary {
  supported: number;
  inferences: number;
  unsupported: number;
  contradicted: number;
  citationNeeded: number;
  coveragePct: number;
  /**
   * False for a purely narrative/background block with zero claim links — a
   * bare 0%-filled bar there would read as "this failed verification" rather
   * than "no evidence expected here" (F3/F8 fix: the coverage bar must not
   * look broken for a block with no chips). Callers should render "—" / a
   * neutral state instead of a 0-width bar when this is false.
   */
  isApplicable: boolean;
}

const EMPTY_SUMMARY: ParagraphAuditSummary = {
  supported: 0,
  inferences: 0,
  unsupported: 0,
  contradicted: 0,
  citationNeeded: 0,
  coveragePct: 0,
  isApplicable: false,
};

/** Classifies a single block's claim_links into the mockup's Audit Inspector count buckets. */
export function computeBlockAuditSummary(block: ReportBlock | null, claimLinks: ReportClaimLink[]): ParagraphAuditSummary {
  if (!block) return EMPTY_SUMMARY;
  const links = claimLinks.filter((cl) => cl.block_id === block.block_id);

  if (links.length === 0) {
    // Material-but-uncited is a real gap (citation needed); narrative/background
    // blocks with no links simply have nothing to score (isApplicable: false).
    if (block.materiality === "material") return { ...EMPTY_SUMMARY, citationNeeded: 1, isApplicable: true };
    return EMPTY_SUMMARY;
  }

  let supported = 0;
  let inferences = 0;
  let unsupported = 0;
  let contradicted = 0;
  for (const link of links) {
    if (link.relation === "contradicts") contradicted += 1;
    else if (link.link_status === "missing_claim" || link.link_status === "missing_source") unsupported += 1;
    else if (link.relation === "inferred_from") inferences += 1;
    else supported += 1;
  }
  const total = supported + inferences + unsupported + contradicted;
  const coveragePct = total > 0 ? Math.round(((supported + inferences) / total) * 100) : 0;
  return { supported, inferences, unsupported, contradicted, citationNeeded: 0, coveragePct, isApplicable: true };
}

/** Aggregates across all MATERIAL blocks — the Coverage Score shown when nothing is selected. */
export function computeDraftAuditSummary(blocks: ReportBlock[], claimLinks: ReportClaimLink[]): ParagraphAuditSummary {
  const materialBlocks = blocks.filter((b) => b.materiality === "material");
  const totals = materialBlocks.reduce(
    (acc, b) => {
      const s = computeBlockAuditSummary(b, claimLinks);
      acc.supported += s.supported;
      acc.inferences += s.inferences;
      acc.unsupported += s.unsupported;
      acc.contradicted += s.contradicted;
      acc.citationNeeded += s.citationNeeded;
      return acc;
    },
    { ...EMPTY_SUMMARY },
  );
  const total = totals.supported + totals.inferences + totals.unsupported + totals.contradicted;
  totals.coveragePct = total > 0 ? Math.round(((totals.supported + totals.inferences) / total) * 100) : 0;
  totals.isApplicable = materialBlocks.length > 0;
  return totals;
}

// ── Issues ────────────────────────────────────────────────────────────────────

/**
 * "critical" = a real contradiction (blocking, red). "warning" = a quality
 * signal that needs a human look but isn't necessarily wrong (amber) — F3
 * fix: only Contradictions is red; Weak/Low-confidence and Citation-needed
 * are both amber ⚠, not red.
 */
export type BuilderIssueSeverity = "critical" | "warning";

export interface BuilderIssue {
  key: "contradictions" | "weak_confidence" | "citation_needed";
  label: string;
  count: number;
  severity: BuilderIssueSeverity;
}

/** Draft-wide issue counters shown in the Audit Inspector's "Issues" panel. */
export function computeDraftIssues(blocks: ReportBlock[], claimLinks: ReportClaimLink[]): BuilderIssue[] {
  const contradictions = claimLinks.filter((cl) => cl.relation === "contradicts").length;
  const weakConfidence = blocks.reduce((n, b) => {
    const weakLink = claimLinks.some(
      (cl) => cl.block_id === b.block_id && resolveBuilderClaimPreview(cl.claim_id)?.confidence === "low",
    );
    return n + (weakLink || b.risk_flags.includes("weak_confidence") ? 1 : 0);
  }, 0);
  const citationNeeded = blocks.filter(
    (b) => b.materiality === "material" && !claimLinks.some((cl) => cl.block_id === b.block_id),
  ).length;

  return [
    { key: "contradictions", label: "Contradictions", count: contradictions, severity: "critical" },
    { key: "weak_confidence", label: "Weak/Low confidence", count: weakConfidence, severity: "warning" },
    { key: "citation_needed", label: "Citation needed", count: citationNeeded, severity: "warning" },
  ];
}

// ── Small display helpers (Report Builder specific — not generic enough for lib/format.ts) ─

/**
 * Draft schema_version is a plain integer (builder_service.py::BUILDER_SCHEMA_VERSION)
 * — the mockup shows a dotted "major.minor" style version string like other RF
 * artifacts. Rather than fabricate a minor version, pad with ".0" so the UI
 * never shows a bare integer (F8: "1.2" not "1" — our real value is int 1).
 */
export function formatSchemaVersion(version: number): string {
  return Number.isInteger(version) ? `${version}.0` : String(version);
}
