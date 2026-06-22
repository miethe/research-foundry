/**
 * ReportOverlay — two-column composite of ReportRenderer + CompositionSidebar.
 *
 * Wires:
 *   - ReportRenderer chip click → ProvenanceModal.open(claimId)
 *   - CompositionSidebar filter → dimmedClaimIds → ReportRenderer dim chips
 *   - ReportOutline (D5) → navigable table-of-contents with active-heading tracking
 *
 * ProvenanceModal is rendered inside this component (portalled logically;
 * physically mounted at the ReportOverlay DOM level for stacking context).
 *
 * The run-detail tab panel switches between TrustPanel and ReportOverlay.
 *
 * D5: navigable outline in the right sidebar; IntersectionObserver highlights
 * the active section as the user scrolls through the report body.
 * Observer root anchors to Stage-1's scroll container:
 *   - modal mode: .rv-detail-workspace__body
 *   - page mode:  .rv-detail__body (data-scroll-container="true")
 */

import { useRef, useState, useCallback, useEffect, useMemo } from "react";
import type { RFRunExport } from "@/types/rf";
import { ReportRenderer }    from "./ReportRenderer";
import { CompositionSidebar } from "./CompositionSidebar";
import { ReportOutline } from "./ReportOutline";
import { extractHeadings } from "./reportOutlineUtils";
import { ProvenanceModal }    from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ReportOverlayProps {
  run:          RFRunExport;
  /** Markdown content of the report_draft. Null/empty renders an empty-state via ReportRenderer. */
  reportDraft:  string | null;
  onOpenProvenance?: (claimId: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportOverlay({ run, reportDraft, onOpenProvenance }: ReportOverlayProps) {
  const modalRef = useRef<ProvenanceModalHandle>(null);
  const [activeClaimIds, setActiveClaimIds] = useState<Set<string> | null>(null);
  const [compositionFilter, setCompositionFilter] = useState<"supported" | "inference" | "speculation" | null>(null);
  const [highlightText, setHighlightText] = useState(false);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);

  // D5: Extract headings from the report draft for the outline
  const headings = useMemo(() => extractHeadings(reportDraft ?? ""), [reportDraft]);

  const handleClaimSelect = useCallback((claimId: string) => {
    if (onOpenProvenance) onOpenProvenance(claimId);
    else modalRef.current?.open(claimId);
  }, [onOpenProvenance]);

  const handleFilterChange = useCallback((activeIds: Set<string> | null, filter: "supported" | "inference" | "speculation" | null) => {
    setActiveClaimIds(activeIds);
    setCompositionFilter(filter);
    if (!activeIds) setHighlightText(false);
  }, []);

  // D5: IntersectionObserver — tracks which heading is currently visible.
  // rootMargin: -10% top (below sticky chrome), -80% bottom (heading must be in top 10–20%).
  // Guard: typeof IntersectionObserver checks prevent jsdom crashes in tests.
  useEffect(() => {
    if (headings.length === 0) return;
    if (typeof IntersectionObserver === "undefined") return;

    // Find the scroll container. In modal mode it is .rv-detail-workspace__body;
    // in page mode it is [data-scroll-container="true"] / .rv-detail__body.
    // We walk up from the overlay's own DOM node to find the nearest ancestor
    // that matches one of these classes. Fall back to null (viewport root).
    const overlayEl = document.querySelector("[data-testid='report-overlay']");
    let scrollRoot: Element | null = null;
    if (overlayEl) {
      let el: Element | null = overlayEl.parentElement;
      while (el) {
        if (
          el.classList.contains("rv-detail-workspace__body") ||
          el.classList.contains("rv-detail__body") ||
          el.getAttribute("data-scroll-container") === "true"
        ) {
          scrollRoot = el;
          break;
        }
        el = el.parentElement;
      }
    }

    const headingEls: Element[] = [];
    for (const h of headings) {
      const el = document.getElementById(h.slug);
      if (el) headingEls.push(el);
    }
    if (headingEls.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the first heading that is intersecting (topmost visible)
        // Sorted by top position in the document so we always get the current section.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActiveSlug(visible[0]!.target.id || null);
        }
      },
      {
        root: scrollRoot,
        rootMargin: "-10% 0px -80% 0px",
        threshold: 0,
      },
    );

    for (const el of headingEls) {
      observer.observe(el);
    }

    return () => observer.disconnect();
  }, [headings]);

  return (
    <div className="rv-report-overlay" data-testid="report-overlay">

      {/* Two-column layout: report + sidebar */}
      <div className="rv-report-overlay__columns">

        {/* Main report column */}
        <div className="rv-report-overlay__main" data-testid="report-overlay-main">
          <ReportRenderer
            markdown={reportDraft ?? ""}
            claims={run.claims}
            onClaimSelect={handleClaimSelect}
            activeClaimIds={activeClaimIds}
            highlightMode={compositionFilter ? "composition" : "none"}
            highlightText={highlightText}
          />
        </div>

        {/* Right sidebar: ReportOutline (D5) stacked above CompositionSidebar */}
        <aside className="rv-report-overlay__sidebar" data-testid="report-overlay-sidebar">
          {headings.length > 0 && (
            <ReportOutline
              headings={headings}
              activeSlug={activeSlug}
              onHeadingClick={setActiveSlug}
            />
          )}
          <CompositionSidebar
            claimCounts={run.claim_counts}
            claims={run.claims}
            onFilterChange={handleFilterChange}
            highlightText={highlightText}
            onHighlightTextChange={setHighlightText}
          />
        </aside>
      </div>

      {/* Provenance modal (single instance, opened by chip clicks) */}
      {!onOpenProvenance && (
        <ProvenanceModal
          ref={modalRef}
          claims={run.claims}
          sensitivityThreshold={run.sensitivity_threshold}
        />
      )}
    </div>
  );
}

export default ReportOverlay;
