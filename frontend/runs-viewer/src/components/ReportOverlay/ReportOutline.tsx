/**
 * ReportOutline — navigable table-of-contents for the report sidebar.
 *
 * Renders h2/h3 headings extracted from the report markdown as a clickable
 * outline. Clicking a heading scrolls the report body to that section via
 * getElementById + scrollIntoView. The active heading is highlighted via
 * IntersectionObserver managed by the parent (ReportOverlay).
 *
 * D5: outline in right sidebar; active section highlighted on scroll.
 *
 * Utilities (slugify, extractHeadings, OutlineHeading type) live in
 * reportOutlineUtils.ts (split to satisfy react-refresh/only-export-components).
 */

export type { OutlineHeading } from "./reportOutlineUtils";

// ── Props ─────────────────────────────────────────────────────────────────────

import type { OutlineHeading } from "./reportOutlineUtils";

export interface ReportOutlineProps {
  headings:    OutlineHeading[];
  activeSlug?: string | null;
  onHeadingClick?: (slug: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportOutline({ headings, activeSlug, onHeadingClick }: ReportOutlineProps) {
  if (headings.length === 0) {
    return (
      <nav
        className="rv-report-outline rv-report-outline--empty"
        aria-label="Report outline"
        data-testid="report-outline"
      >
        <p className="rv-report-outline__empty">No headings found.</p>
      </nav>
    );
  }

  function handleClick(slug: string) {
    // Scroll the heading into view in the document
    const el = document.getElementById(slug);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    onHeadingClick?.(slug);
  }

  function handleKeyDown(event: React.KeyboardEvent, slug: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick(slug);
    }
  }

  return (
    <nav
      className="rv-report-outline"
      aria-label="Report outline"
      data-testid="report-outline"
    >
      <h4 className="rv-report-outline__title">Contents</h4>
      <ol className="rv-report-outline__list" data-testid="report-outline-list">
        {headings.map((h) => {
          const isActive = h.slug === activeSlug;
          return (
            <li
              key={h.slug}
              className={`rv-report-outline__item rv-report-outline__item--h${h.level}${isActive ? " rv-report-outline__item--active" : ""}`}
              style={{ "--level": h.level - 2 } as React.CSSProperties}
            >
              <button
                type="button"
                className="rv-report-outline__link"
                aria-current={isActive ? "true" : undefined}
                data-testid={`outline-item-${h.slug}`}
                onClick={() => handleClick(h.slug)}
                onKeyDown={(e) => handleKeyDown(e, h.slug)}
                title={h.text}
              >
                {h.text}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default ReportOutline;
