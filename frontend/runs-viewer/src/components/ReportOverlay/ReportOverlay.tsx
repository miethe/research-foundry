/**
 * ReportOverlay — two-column composite of ReportRenderer + CompositionSidebar.
 *
 * Wires:
 *   - ReportRenderer chip click → ProvenanceModal.open(claimId)
 *   - CompositionSidebar filter → dimmedClaimIds → ReportRenderer dim chips
 *
 * ProvenanceModal is rendered inside this component (portalled logically;
 * physically mounted at the ReportOverlay DOM level for stacking context).
 *
 * The run-detail tab panel switches between TrustPanel and ReportOverlay.
 */

import { useRef, useState, useCallback } from "react";
import type { RFRunExport } from "@/types/rf";
import { ReportRenderer }    from "./ReportRenderer";
import { CompositionSidebar } from "./CompositionSidebar";
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

  const handleClaimSelect = useCallback((claimId: string) => {
    if (onOpenProvenance) onOpenProvenance(claimId);
    else modalRef.current?.open(claimId);
  }, [onOpenProvenance]);

  const handleFilterChange = useCallback((activeIds: Set<string> | null, filter: "supported" | "inference" | "speculation" | null) => {
    setActiveClaimIds(activeIds);
    setCompositionFilter(filter);
    if (!activeIds) setHighlightText(false);
  }, []);

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

        {/* Composition sidebar */}
        <aside className="rv-report-overlay__sidebar" data-testid="report-overlay-sidebar">
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
