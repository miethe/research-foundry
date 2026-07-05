/**
 * ReportRenderer — renders report_draft.md as Markdown with interactive
 * [claim:clm_NNN] chip overlays.
 *
 * Transforms [claim:clm_NNN] patterns into <ClaimChip> components that fire
 * onClaimSelect(claimId) when clicked.
 *
 * Color-codes sentences that start with **Inference:** or **Speculation:**
 * (and the backing claim's status) using rv-sentence--inference/speculation CSS classes.
 *
 * AC P4-REPORT-001-1: every [claim:clm_NNN] pattern renders as a ClaimChip.
 *
 * P2 Wave C (report_anchors, schema 1.4, D9): when `reportAnchors` is
 * provided (non-null), each top-level paragraph is keyed to its backend
 * `block_id` (DOM `id` + `data-block-id`), enabling paragraph selection
 * (`onParagraphSelect`) and block-based highlighting (`selectedBlockId` /
 * `activeBlockIds`) independent of claim-id text matching. When
 * `reportAnchors` is absent/null (pre-1.4 export), this component behaves
 * EXACTLY as before — the legacy regex chip/highlight path is unchanged.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm     from "remark-gfm";
import type { RFClaim, RFReportAnchorBlock } from "@/types/rf";
import { ClaimChip }    from "./ClaimChip";
import { slugify }      from "./reportOutlineUtils";
import { buildParagraphAnchorSequence } from "@/lib/reportAnchors";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ReportRendererProps {
  /** Markdown source (report_draft.md content) */
  markdown:       string;
  claims:         RFClaim[];
  onClaimSelect:  (claimId: string) => void;
  /** Deprecated alias retained for older tests/callers; these are active IDs. */
  dimmedClaimIds?: Set<string> | null;
  /** Active claim IDs for composition or selected-claim highlighting. */
  activeClaimIds?: Set<string> | null;
  highlightMode?: "none" | "composition" | "selected-claim" | "selected-paragraph" | "anchor-filter";
  highlightText?: boolean;
  selectedClaimId?: string | null;
  compact?: boolean;
  /** P2 Wave C: schema-1.4 report_anchors block list. Null/undefined = legacy mode (D9). */
  reportAnchors?: RFReportAnchorBlock[] | null;
  /** P2 Wave C: block_id of the currently-selected paragraph, or null. Forces highlight-by-block-id. */
  selectedBlockId?: string | null;
  /** P2 Wave C: block_ids matching the active anchor filter set. A defined Set (even empty) activates block-based dim/highlight. */
  activeBlockIds?: Set<string> | null;
  /** P2 Wave C: fired when an anchored paragraph is clicked (block_id resolved). */
  onParagraphSelect?: (blockId: string) => void;
}

// ── Claim chip regex ──────────────────────────────────────────────────────────

const CLAIM_PATTERN = /\[claim:(clm_[a-zA-Z0-9_]+)\]/g;
/** Non-global version used only for .test() guards to avoid lastIndex mutation. */
const CLAIM_PATTERN_TEST = /\[claim:(clm_[a-zA-Z0-9_]+)\]/;

function stripReportMetadata(markdown: string): string {
  let text = markdown.trimStart();

  if (text.startsWith("---")) {
    const lines = text.split(/\r?\n/);
    const endIndex = lines.findIndex((line, index) => index > 0 && line.trim() === "---");
    if (endIndex > 0) {
      text = lines.slice(endIndex + 1).join("\n").trimStart();
    }
  }

  const lines = text.split(/\r?\n/);
  let firstContentIndex = 0;
  while (
    firstContentIndex < lines.length &&
    (/^\s*$/.test(lines[firstContentIndex] ?? "") ||
      /^[A-Za-z][A-Za-z0-9_-]*:\s+/.test(lines[firstContentIndex] ?? ""))
  ) {
    firstContentIndex += 1;
  }

  return lines.slice(firstContentIndex).join("\n").trimStart();
}

/**
 * Split a text string on [claim:clm_NNN] patterns and return an array of
 * React elements (plain strings interleaved with ClaimChip components).
 */
function splitWithClaimChips(
  text:          string,
  claims:        RFClaim[],
  onClaimSelect: (claimId: string) => void,
  activeClaimIds?: Set<string> | null,
  selectedClaimId?: string | null,
): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(CLAIM_PATTERN.source, "g");

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const claimId = match[1];
    parts.push(
      <ClaimChip
        key={`${claimId}-${match.index}`}
        claimId={claimId}
        claims={claims}
        onClaimSelect={onClaimSelect}
        dimmed={activeClaimIds ? !activeClaimIds.has(claimId) : false}
        selected={selectedClaimId === claimId}
      />
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

// ── Heading slug tracking (deduplicate within a render pass) ─────────────────

/**
 * A per-render slug counter is required to match the deduplication logic in
 * extractHeadings (ReportOutline). We build it once per buildComponents call
 * (which happens once per render since buildComponents is not memoized).
 */
function makeSlugCounter() {
  const counts: Record<string, number> = {};
  return function nextSlug(text: string): string {
    const base = slugify(text);
    if (!base) return "";
    const count = counts[base] ?? 0;
    counts[base] = count + 1;
    return count === 0 ? base : `${base}-${count + 1}`;
  };
}

// ── Sentence color detection ──────────────────────────────────────────────────

/**
 * Returns a CSS modifier class for the paragraph if its text begins with
 * an Inference or Speculation label pattern.
 */
function paragraphClass(text: string): string {
  const t = text.trim();
  if (/^\*{0,2}Inference:{0,1}\*{0,2}/i.test(t)) return "rv-report-p--inference";
  if (/^\*{0,2}Speculation:{0,1}\*{0,2}/i.test(t)) return "rv-report-p--speculation";
  return "";
}

function claimIdsInText(text: string): string[] {
  const ids: string[] = [];
  const re = new RegExp(CLAIM_PATTERN.source, "g");
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    if (match[1]) ids.push(match[1]);
  }
  return ids;
}

function blockHighlightClass(text: string, activeClaimIds: Set<string> | null | undefined, highlightText: boolean): string {
  if (!highlightText || !activeClaimIds || activeClaimIds.size === 0) return "";
  const ids = claimIdsInText(text);
  if (ids.length === 0) return "rv-report-block--dimmed";
  return ids.some((id) => activeClaimIds.has(id))
    ? "rv-report-block--highlighted"
    : "rv-report-block--dimmed";
}

/**
 * P2 Wave C — block_id-based highlight/dim, used instead of
 * blockHighlightClass() whenever anchor-mode (selectedBlockId or
 * activeBlockIds) is active. Highlights by block_id DIRECTLY so a paragraph
 * with zero claim_links (e.g. "citation needed") still highlights correctly
 * when it IS the selected paragraph — claim-id text matching alone cannot
 * express that.
 */
function anchorBlockClass(
  blockId: string | null,
  selectedBlockId: string | null | undefined,
  activeBlockIds: Set<string> | null | undefined,
  highlightText: boolean,
): string {
  if (!highlightText) return "";
  if (selectedBlockId) {
    return blockId === selectedBlockId ? "rv-report-block--highlighted rv-report-block--selected" : "rv-report-block--dimmed";
  }
  if (activeBlockIds) {
    // A defined Set (even empty — "filter matched nothing") activates
    // block-based dim/highlight; empty correctly dims every paragraph.
    return blockId && activeBlockIds.has(blockId) ? "rv-report-block--highlighted" : "rv-report-block--dimmed";
  }
  return "";
}

// ── Custom renderer ───────────────────────────────────────────────────────────

interface ParagraphProps {
  children?: React.ReactNode;
}

interface HeadingProps {
  children?: React.ReactNode;
}

/**
 * Builds the react-markdown custom components object. Needs claims and callbacks
 * in scope, so we recreate it per render (or memoize if needed).
 *
 * D5: h2/h3 renderers emit id={slug} so the ReportOutline anchor links work.
 * Slug generation mirrors extractHeadings (ReportOutline.ts) for consistency.
 */
function buildComponents(
  claims:        RFClaim[],
  onClaimSelect: (claimId: string) => void,
  activeClaimIds?: Set<string> | null,
  selectedClaimId?: string | null,
  highlightText = false,
  bodyMarkdown = "",
  reportAnchors?: RFReportAnchorBlock[] | null,
  selectedBlockId?: string | null,
  activeBlockIds?: Set<string> | null,
  onParagraphSelect?: (blockId: string) => void,
) {
  // Shared slug counter: deduplicates headings in the same order as extractHeadings
  const nextSlug = makeSlugCounter();
  // P2 Wave C: block_id per rendered <p>, in render order (D9 legacy mode
  // when reportAnchors is null/undefined — sequence is then all-null and a
  // no-op for every paragraph).
  const paragraphSequence = buildParagraphAnchorSequence(bodyMarkdown, reportAnchors);
  let pOrdinal = 0;
  /**
   * Walk a react-markdown children tree and expand any string nodes that
   * contain [claim:clm_NNN] patterns into [string, ClaimChip, string, ...].
   */
  function expandChildren(children: React.ReactNode): React.ReactNode {
      if (typeof children === "string") {
      if (!CLAIM_PATTERN_TEST.test(children)) return children;
      return splitWithClaimChips(children, claims, onClaimSelect, activeClaimIds, selectedClaimId);
    }
    if (Array.isArray(children)) {
      return children.flatMap((child, i) => {
        if (typeof child === "string") {
          const parts = splitWithClaimChips(child, claims, onClaimSelect, activeClaimIds, selectedClaimId);
          return parts.map((p, j) =>
            typeof p === "string" ? p : <span key={`${i}-${j}`}>{p}</span>
          );
        }
        return child;
      });
    }
    return children;
  }

  return {
    // Paragraph: color-code inference/speculation; expand claim chips
    p({ children }: ParagraphProps) {
      const textContent = typeof children === "string" ? children :
        Array.isArray(children) ? (children as React.ReactNode[]).map((c) => (typeof c === "string" ? c : "")).join("") : "";
      const extraClass = paragraphClass(textContent);

      // P2 Wave C: resolve this paragraph's block_id from the precomputed
      // render-order sequence (empty array / no-op in legacy mode).
      const blockId = paragraphSequence[pOrdinal]?.blockId ?? null;
      pOrdinal += 1;

      const anchorMode = selectedBlockId !== undefined || activeBlockIds !== undefined;
      const highlightClass = anchorMode
        ? anchorBlockClass(blockId, selectedBlockId, activeBlockIds, highlightText)
        : blockHighlightClass(textContent, activeClaimIds, highlightText);

      const anchored = blockId != null && typeof onParagraphSelect === "function";
      const anchoredClass = anchored ? " rv-report-p--anchored" : "";
      const className = `rv-report-p${extraClass ? ` ${extraClass}` : ""}${highlightClass ? ` ${highlightClass}` : ""}${anchoredClass}`;

      return (
        <p
          id={blockId ?? undefined}
          data-block-id={blockId ?? undefined}
          className={className}
          onClick={anchored ? () => onParagraphSelect!(blockId!) : undefined}
        >
          {expandChildren(children)}
        </p>
      );
    },

    // Inline text within strong/em/etc — expand claim chips
    strong({ children }: ParagraphProps) {
      return <strong>{expandChildren(children)}</strong>;
    },

    li({ children }: ParagraphProps) {
      const textContent = typeof children === "string" ? children :
        Array.isArray(children) ? (children as React.ReactNode[]).map((c) => (typeof c === "string" ? c : "")).join("") : "";
      const highlightClass = blockHighlightClass(textContent, activeClaimIds, highlightText);
      return <li className={`rv-report-li${highlightClass ? ` ${highlightClass}` : ""}`}>{expandChildren(children)}</li>;
    },

    // D5: h2/h3 heading renderers emit id={slug} for anchor-link navigation.
    // The slug is computed with the same deduplication counter as extractHeadings.
    h2({ children }: HeadingProps) {
      const rawText = typeof children === "string" ? children :
        Array.isArray(children) ? (children as React.ReactNode[]).map((c) => (typeof c === "string" ? c : "")).join("") : "";
      const slug = nextSlug(rawText);
      return <h2 id={slug || undefined} className="rv-report-h2" data-heading-slug={slug || undefined}>{children}</h2>;
    },

    h3({ children }: HeadingProps) {
      const rawText = typeof children === "string" ? children :
        Array.isArray(children) ? (children as React.ReactNode[]).map((c) => (typeof c === "string" ? c : "")).join("") : "";
      const slug = nextSlug(rawText);
      return <h3 id={slug || undefined} className="rv-report-h3" data-heading-slug={slug || undefined}>{children}</h3>;
    },
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportRenderer({
  markdown,
  claims,
  onClaimSelect,
  dimmedClaimIds,
  activeClaimIds,
  highlightMode = "none",
  highlightText = false,
  selectedClaimId,
  compact = false,
  reportAnchors,
  selectedBlockId,
  activeBlockIds,
  onParagraphSelect,
}: ReportRendererProps) {
  const bodyMarkdown = stripReportMetadata(markdown);
  const activeIds = activeClaimIds ?? dimmedClaimIds ?? (highlightMode === "selected-claim" && selectedClaimId ? new Set([selectedClaimId]) : null);

  if (!bodyMarkdown) {
    return (
      <div className="rv-report-empty" data-testid="report-empty">
        <p>No report draft available for this run.</p>
      </div>
    );
  }

  return (
    <div
      className={`rv-report-content${compact ? " rv-report-content--compact" : ""}${highlightText && activeIds ? " rv-report-content--highlighting" : ""}`}
      data-testid="report-renderer"
      data-highlight-mode={highlightMode}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={buildComponents(
          claims,
          onClaimSelect,
          activeIds,
          selectedClaimId,
          highlightText,
          bodyMarkdown,
          reportAnchors,
          selectedBlockId,
          activeBlockIds,
          onParagraphSelect,
        )}
      >
        {bodyMarkdown}
      </ReactMarkdown>
    </div>
  );
}

export default ReportRenderer;
