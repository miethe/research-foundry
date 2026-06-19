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
 */

import ReactMarkdown from "react-markdown";
import remarkGfm     from "remark-gfm";
import type { RFClaim } from "@/types/rf";
import { ClaimChip }    from "./ClaimChip";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ReportRendererProps {
  /** Markdown source (report_draft.md content) */
  markdown:       string;
  claims:         RFClaim[];
  onClaimSelect:  (claimId: string) => void;
  /** Dimmed claim IDs from CompositionSidebar filter. All others are active. */
  dimmedClaimIds?: Set<string> | null;
  selectedClaimId?: string | null;
  compact?: boolean;
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
  dimmedClaimIds?: Set<string> | null,
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
        dimmed={dimmedClaimIds ? !dimmedClaimIds.has(claimId) : false}
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

// ── Custom renderer ───────────────────────────────────────────────────────────

interface ParagraphProps {
  children?: React.ReactNode;
}

/**
 * Builds the react-markdown custom components object. Needs claims and callbacks
 * in scope, so we recreate it per render (or memoize if needed).
 */
function buildComponents(
  claims:        RFClaim[],
  onClaimSelect: (claimId: string) => void,
  dimmedClaimIds?: Set<string> | null,
  selectedClaimId?: string | null,
) {
  /**
   * Walk a react-markdown children tree and expand any string nodes that
   * contain [claim:clm_NNN] patterns into [string, ClaimChip, string, ...].
   */
  function expandChildren(children: React.ReactNode): React.ReactNode {
    if (typeof children === "string") {
      if (!CLAIM_PATTERN_TEST.test(children)) return children;
      return splitWithClaimChips(children, claims, onClaimSelect, dimmedClaimIds, selectedClaimId);
    }
    if (Array.isArray(children)) {
      return children.flatMap((child, i) => {
        if (typeof child === "string") {
          const parts = splitWithClaimChips(child, claims, onClaimSelect, dimmedClaimIds, selectedClaimId);
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
      return (
        <p className={`rv-report-p${extraClass ? ` ${extraClass}` : ""}`}>
          {expandChildren(children)}
        </p>
      );
    },

    // Inline text within strong/em/etc — expand claim chips
    strong({ children }: ParagraphProps) {
      return <strong>{expandChildren(children)}</strong>;
    },

    li({ children }: ParagraphProps) {
      return <li className="rv-report-li">{expandChildren(children)}</li>;
    },
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportRenderer({ markdown, claims, onClaimSelect, dimmedClaimIds, selectedClaimId, compact = false }: ReportRendererProps) {
  const bodyMarkdown = stripReportMetadata(markdown);

  if (!bodyMarkdown) {
    return (
      <div className="rv-report-empty" data-testid="report-empty">
        <p>No report draft available for this run.</p>
      </div>
    );
  }

  return (
    <div className={`rv-report-content${compact ? " rv-report-content--compact" : ""}`} data-testid="report-renderer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={buildComponents(claims, onClaimSelect, dimmedClaimIds, selectedClaimId)}
      >
        {bodyMarkdown}
      </ReactMarkdown>
    </div>
  );
}

export default ReportRenderer;
