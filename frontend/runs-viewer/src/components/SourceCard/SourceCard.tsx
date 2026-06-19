/**
 * SourceCard — renders a single resolved source with trust badge, source-type
 * icon, usage-permission pills, and an expandable verbatim quote section.
 *
 * SENSITIVITY GATE (R9 defense-in-depth, AC P4-SOURCE-CARD-1):
 *   If the source's `sensitivity` field is "work_sensitive" or "client_sensitive",
 *   the quote AND summary sections are replaced by a redaction placeholder.
 *   This is defense-in-depth — the export service already redacts at the JSON
 *   level (P1-SENS-001); the UI gate catches any residual sensitive content.
 *
 *   If `sensitivity` is absent, treat as "public" (safe default — renders quote).
 *   Unrecognized sensitivity labels are treated as fail-closed (redacted).
 */

import { useState } from "react";
import type { RFResolvedSource, RFSensitivity, RFSourceType, RFSourceRank } from "@/types/rf";

// ── Sensitivity threshold ─────────────────────────────────────────────────────

const SENSITIVITY_ORDER: Record<RFSensitivity, number> = {
  public:           0,
  personal:         1,
  work_sensitive:   2,
  client_sensitive: 3,
};

/** Returns true if the source should have its quote/summary redacted. */
function isRedacted(sensitivity: RFSensitivity | null | undefined): boolean {
  if (!sensitivity) return false; // absent → public → safe
  const level = SENSITIVITY_ORDER[sensitivity];
  if (level === undefined) return true; // unknown → fail-closed
  return level >= SENSITIVITY_ORDER.work_sensitive;
}

// ── Badge maps ────────────────────────────────────────────────────────────────

const RANK_CHIP: Record<RFSourceRank, string> = {
  primary:   "green",
  secondary: "blue",
  tertiary:  "",
  unknown:   "",
};

const RANK_LABEL: Record<RFSourceRank, string> = {
  primary:   "Primary",
  secondary: "Secondary",
  tertiary:  "Tertiary",
  unknown:   "Unknown rank",
};

const SOURCE_TYPE_ICON: Record<RFSourceType, string> = {
  official_doc:  "D",
  paper:         "P",
  standard:      "S",
  repo:          "G",
  news:          "N",
  blog:          "B",
  book:          "K",
  personal_note: "J",
  internal_doc:  "I",
  other:         "?",
};

const SOURCE_TYPE_LABEL: Record<RFSourceType, string> = {
  official_doc:  "Official Doc",
  paper:         "Paper",
  standard:      "Standard",
  repo:          "Repository",
  news:          "News",
  blog:          "Blog",
  book:          "Book",
  personal_note: "Personal Note",
  internal_doc:  "Internal Doc",
  other:         "Other",
};

// ── Props ─────────────────────────────────────────────────────────────────────

export interface SourceCardProps {
  source: RFResolvedSource;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function SourceCard({ source }: SourceCardProps) {
  const [quoteExpanded, setQuoteExpanded] = useState(false);

  const redacted = isRedacted(source.sensitivity);

  const rank      = source.trust?.source_rank;
  const rankChip  = rank ? RANK_CHIP[rank]  ?? "" : "";
  const rankLabel = rank ? RANK_LABEL[rank] ?? rank : null;

  const srcType      = source.source_type;
  const srcTypeIcon  = srcType ? SOURCE_TYPE_ICON[srcType]  ?? "?" : "?";
  const srcTypeLabel = srcType ? SOURCE_TYPE_LABEL[srcType] ?? srcType : null;

  // Dangling source: referenced card not found in export
  if (source.dangling) {
    return (
      <div
        className="rv-source-card rv-source-card--dangling"
        data-testid={`source-card-${source.source_card_id}`}
        data-sensitivity={source.sensitivity ?? "unknown"}
      >
        <span className="rv-source-card__dangling-msg">
          Source not found: {source.source_card_id}
        </span>
      </div>
    );
  }

  return (
    <div
      className="rv-source-card it-card"
      data-testid={`source-card-${source.source_card_id}`}
      data-sensitivity={source.sensitivity ?? "public"}
      data-redacted={redacted ? "true" : "false"}
    >
      {/* ── Header: type icon + title + trust badge ── */}
      <div className="rv-source-card__header">
        {/* Source type tile */}
        <div
          className="rv-source-card__type-tile it-tile sm"
          aria-label={srcTypeLabel ?? "Source"}
          title={srcTypeLabel ?? "Source"}
        >
          <span className="rv-source-card__type-icon" aria-hidden="true">
            {srcTypeIcon}
          </span>
        </div>

        {/* Title + URL */}
        <div className="rv-source-card__title-block">
          <span className="rv-source-card__title">
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rv-source-card__title-link"
                data-testid={`source-card-url-${source.source_card_id}`}
              >
                {source.title ?? source.source_card_id}
              </a>
            ) : (
              source.title ?? source.source_card_id
            )}
          </span>
          {source.locator && (
            <span className="rv-source-card__locator">
              {source.locator}
            </span>
          )}
        </div>

        {/* Trust badge */}
        {rankLabel && (
          <span
            className={`it-chip ${rankChip} rv-source-card__rank`}
            data-testid={`source-card-rank-${source.source_card_id}`}
          >
            {rankLabel}
          </span>
        )}

        {/* Relation badge */}
        <span
          className={`it-chip ${source.relation === "supports" ? "green" : source.relation === "contradicts" ? "red" : ""} rv-source-card__relation`}
          data-testid={`source-card-relation-${source.source_card_id}`}
        >
          {source.relation}
        </span>
      </div>

      {/* ── Usage permission pills ── */}
      {source.usage && (
        <div className="rv-source-card__usage" data-testid={`source-card-usage-${source.source_card_id}`}>
          {source.usage.allowed_for_public_output && (
            <span className="it-chip green rv-source-card__usage-pill">Public OK</span>
          )}
          {source.usage.allowed_for_work_output && (
            <span className="it-chip blue rv-source-card__usage-pill">Work OK</span>
          )}
          {source.usage.allowed_for_personal_meatywiki && (
            <span className="it-chip purple rv-source-card__usage-pill">Personal wiki OK</span>
          )}
          {source.usage.citation_required && (
            <span className="it-chip gold rv-source-card__usage-pill">Citation req'd</span>
          )}
        </div>
      )}

      {/* ── Trust reliability notes ── */}
      {source.trust?.reliability_notes && !redacted && (
        <p className="rv-source-card__reliability" data-testid={`source-card-reliability-${source.source_card_id}`}>
          {source.trust.reliability_notes}
        </p>
      )}

      {/* ── Sensitivity gate: redaction placeholder ── */}
      {redacted ? (
        <div
          className="rv-source-card__redacted"
          data-testid={`source-card-redacted-${source.source_card_id}`}
          role="note"
          aria-label="Content redacted"
        >
          <span className="rv-source-card__redacted-icon" aria-hidden="true">⊘</span>
          <span>
            Content redacted — sensitivity: <code>{source.sensitivity}</code>
          </span>
        </div>
      ) : (
        /* ── Expandable verbatim quote section ── */
        (source.quote || source.summary) && (
          <div className="rv-source-card__quote-section">
            <button
              type="button"
              className="rv-source-card__quote-toggle it-btn ghost xs"
              data-testid={`source-card-quote-toggle-${source.source_card_id}`}
              aria-expanded={quoteExpanded}
              onClick={() => setQuoteExpanded((e) => !e)}
            >
              {quoteExpanded ? "Hide quote" : "Show verbatim quote"}
            </button>

            {quoteExpanded && (
              <div className="rv-source-card__quote-body" data-testid={`source-card-quote-${source.source_card_id}`}>
                {source.quote &&
                  !source.quote.startsWith("[redacted") && (
                    <blockquote className="rv-source-card__quote">
                      {source.quote}
                    </blockquote>
                  )}
                {source.summary && !source.summary.startsWith("[redacted") && (
                  <p className="rv-source-card__summary">
                    <strong>Summary:</strong> {source.summary}
                  </p>
                )}
                {source.evidence_locator && (
                  <p className="rv-source-card__ev-locator">
                    <strong>Locator:</strong> {source.evidence_locator}
                  </p>
                )}
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}

export default SourceCard;
