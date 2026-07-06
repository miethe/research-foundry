/**
 * ReportCoverageStrip — P2 Wave C (report_anchors, schema 1.4).
 *
 * Renders above the report pane in ClaimAuditWorkbench when `run.report_anchors`
 * is present (D9: absent entirely in legacy mode, no UI regression for
 * pre-1.4 exports):
 *   - An overall coverage summary + 5 anchor filter chips (unsupported,
 *     contradicted, inference, speculation, stale). These are INDEPENDENT of
 *     LedgerFacets' claim-level status facet — they classify report
 *     PARAGRAPHS by the anchor claim_links actually present in that
 *     paragraph's text, not "any claim anywhere with this status".
 *   - A per-section coverage strip (one pill per h2/h3 section) that scrolls
 *     the report to that heading on click.
 *
 * Pure presentational component — all derivation lives in lib/reportAnchors.ts.
 */

import type { AnchorFilterKey, SectionCoverage } from "@/lib/reportAnchors";

export interface ReportCoverageStripProps {
  sections:        SectionCoverage[];
  overall:         SectionCoverage;
  activeFilters:   Set<AnchorFilterKey>;
  onFilterToggle:  (key: AnchorFilterKey) => void;
  onSectionClick?: (sectionId: string | null) => void;
}

const FILTER_OPTIONS: { key: AnchorFilterKey; label: string; chip: string }[] = [
  { key: "unsupported",  label: "Unsupported",  chip: "red"    },
  { key: "contradicted", label: "Contradicted", chip: "red"    },
  { key: "inference",    label: "Inference",    chip: "blue"   },
  { key: "speculation",  label: "Speculation",  chip: "orange" },
  { key: "stale",        label: "Stale",        chip: "gold"   },
];

function countFor(section: SectionCoverage, key: AnchorFilterKey): number {
  if (key === "unsupported")  return section.unsupported;
  if (key === "contradicted") return section.contradicted;
  if (key === "inference")    return section.inference;
  if (key === "speculation")  return section.speculation;
  return section.stale;
}

export function ReportCoverageStrip({ sections, overall, activeFilters, onFilterToggle, onSectionClick }: ReportCoverageStripProps) {
  if (sections.length === 0) return null;

  return (
    <div className="rv-coverage-strip" data-testid="report-coverage-strip">
      <div className="rv-coverage-strip__header">
        <div className="rv-coverage-strip__score" data-testid="coverage-overall-score">
          <span className="rv-coverage-strip__score-value">{overall.coveragePct}%</span>
          <span className="rv-coverage-strip__score-label">covered</span>
        </div>

        <div className="rv-coverage-strip__filters" role="group" aria-label="Anchor coverage filters">
          {FILTER_OPTIONS.map((opt) => {
            const count = countFor(overall, opt.key);
            const isActive = activeFilters.has(opt.key);
            return (
              <button
                key={opt.key}
                type="button"
                className={`rv-anchor-filter-pill ${opt.chip}${isActive ? " rv-anchor-filter-pill--active" : ""}`}
                data-testid={`anchor-filter-${opt.key}`}
                data-active={isActive ? "true" : "false"}
                aria-pressed={isActive}
                disabled={count === 0}
                onClick={() => onFilterToggle(opt.key)}
              >
                {opt.label}
                <span className="rv-anchor-filter-pill__count">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rv-coverage-strip__sections" data-testid="coverage-section-strip">
        {sections.map((section) => {
          const hasIssues = section.contradicted > 0 || section.stale > 0 || section.missing > 0;
          return (
            <button
              key={section.sectionId ?? "__intro__"}
              type="button"
              className={`rv-coverage-pill${hasIssues ? " rv-coverage-pill--issues" : ""}`}
              data-testid={`coverage-section-${section.sectionId ?? "intro"}`}
              onClick={() => onSectionClick?.(section.sectionId)}
              title={`${section.sectionId ?? "Introduction"} — ${section.coveragePct}% covered`}
            >
              <span className="rv-coverage-pill__label">{section.sectionId ?? "Intro"}</span>
              <span className="rv-coverage-pill__bar">
                <span
                  className="rv-coverage-pill__bar-fill"
                  style={{ width: `${section.coveragePct}%` }}
                />
              </span>
              {hasIssues && (
                <span className="rv-coverage-pill__issue-count">
                  {section.contradicted + section.stale + section.missing}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ReportCoverageStrip;
