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
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportOverlay({ run, reportDraft }: ReportOverlayProps) {
  const modalRef = useRef<ProvenanceModalHandle>(null);
  const [dimmedClaimIds, setDimmedClaimIds] = useState<Set<string> | null>(null);

  const handleClaimSelect = useCallback((claimId: string) => {
    modalRef.current?.open(claimId);
  }, []);

  const handleFilterChange = useCallback((activeIds: Set<string> | null) => {
    setDimmedClaimIds(activeIds);
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
            dimmedClaimIds={dimmedClaimIds}
          />
        </div>

        {/* Composition sidebar */}
        <aside className="rv-report-overlay__sidebar" data-testid="report-overlay-sidebar">
          <CompositionSidebar
            claimCounts={run.claim_counts}
            claims={run.claims}
            onFilterChange={handleFilterChange}
          />
        </aside>
      </div>

      {/* Provenance modal (single instance, opened by chip clicks) */}
      <ProvenanceModal
        ref={modalRef}
        claims={run.claims}
      />
    </div>
  );
}

export default ReportOverlay;
