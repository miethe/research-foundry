/**
 * RunDetailScreen — full run detail surface (P3 seam file + P4 tabs).
 *
 * Integration owner: ui-engineer-enhanced
 *
 * Tab navigation (P4):
 *   - "trust"   → TrustPanel (P3)
 *   - "ledger"  → ClaimLedger view (P4)
 *   - "report"  → ReportOverlay (P4)
 *   - "lineage" → ArtifactLineageGraph (P4, should-have)
 *
 * Composes TrustPanel via useRunDetail(runId).
 * Shows GRACEFUL empty-states for all 9 optional entities:
 *   source_candidates, report_final, critic_review, council_review,
 *   governance_review, raw_idea, research_intent, ibom, intenttree_node.
 *
 * Navigation seam (P3-SEAM-001):
 *   runId comes from useParams<{ runId: string }>.
 *   TrustPanel receives the full RFRunExport with the correct runId.
 *   Failing check deep-links from VerificationChecklist resolve to #clm_NNN.
 */

import { useState, useRef, useCallback }    from "react";
import { useParams, useNavigate }            from "react-router-dom";
import { useRunDetail }                      from "@/hooks";
import { TrustPanel }                        from "@/components/TrustPanel/TrustPanel";
import { EmptyState }                        from "@/components/shared/EmptyState";
import { ClaimLedgerTable }                  from "@/components/ClaimLedger/ClaimLedgerTable";
import { LedgerFacets }                      from "@/components/ClaimLedger/LedgerFacets";
import { ProvenanceModal }                   from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle }        from "@/components/ProvenanceModal/ProvenanceModal";
import { ReportOverlay }                     from "@/components/ReportOverlay/ReportOverlay";
import { ArtifactLineageGraph }              from "@/components/LineageGraph/LineageGraph";
import type { RFClaim }                      from "@/types/rf";

// ── Tab types ─────────────────────────────────────────────────────────────────

type DetailTab = "trust" | "ledger" | "report" | "lineage";

// ── The 9 optional entity definitions ────────────────────────────────────────

const OPTIONAL_ENTITIES = [
  { id: "source_candidates", label: "Source Candidates",  msg: "No source candidates found for this run." },
  { id: "report_final",      label: "Final Report",       msg: "No final report available for this run." },
  { id: "critic_review",     label: "Critic Review",      msg: "No critic review available for this run." },
  { id: "council_review",    label: "Council Review",     msg: "No council review available for this run." },
  { id: "governance_review", label: "Governance Review",  msg: "No governance review available for this run." },
  { id: "raw_idea",          label: "Raw Idea",           msg: "No raw idea recorded for this run." },
  { id: "research_intent",   label: "Research Intent",    msg: "No research intent recorded for this run." },
  { id: "ibom",              label: "Intelligence BOM",   msg: "No iBOM available for this run." },
  { id: "intenttree_node",   label: "IntentTree Node",    msg: "No IntentTree node linked to this run." },
] as const;

// ── Component ─────────────────────────────────────────────────────────────────

export function RunDetailScreen() {
  const { runId }    = useParams<{ runId: string }>();
  const navigate     = useNavigate();
  const { data: run, isLoading, error } = useRunDetail(runId ?? "");

  // Tab state
  const [activeTab, setActiveTab] = useState<DetailTab>("trust");

  // Ledger state: filtered claims
  const [filteredClaims, setFilteredClaims] = useState<RFClaim[]>([]);

  // ProvenanceModal ref (ledger track)
  const modalRef = useRef<ProvenanceModalHandle>(null);

  const handleClaimSelect = useCallback((claimId: string) => {
    modalRef.current?.open(claimId);
  }, []);

  // ── No runId in URL ──
  if (!runId) {
    return (
      <div className="rv-detail" data-testid="run-detail-no-id">
        <p className="rv-error">No run ID in URL.</p>
      </div>
    );
  }

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="rv-detail" data-testid="run-detail-loading">
        <div className="rv-loading">
          <p>Loading run {runId}…</p>
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className="rv-detail" data-testid="run-detail-error">
        <div className="rv-error">
          <p>Error: {error instanceof Error ? error.message : "Unknown error"}</p>
          <button
            className="it-btn ghost"
            onClick={() => navigate("/runs")}
          >
            Back to runs
          </button>
        </div>
      </div>
    );
  }

  // ── No data (shouldn't happen but guard it) ──
  if (!run) {
    return (
      <div className="rv-detail" data-testid="run-detail-empty">
        <p className="rv-error">Run {runId} not found.</p>
      </div>
    );
  }

  return (
    <div className="rv-detail" data-testid="run-detail" data-run-id={run.run_id}>

      {/* Back nav */}
      <div className="rv-detail__nav">
        <button
          className="it-btn ghost"
          onClick={() => navigate("/runs")}
          aria-label="Back to run list"
        >
          ← Runs
        </button>
      </div>

      {/* Run identity header */}
      <div className="rv-detail__header">
        <h1 className="rv-detail__run-id" data-testid="detail-run-id">
          {run.run_id}
        </h1>
        {run.created_at && (
          <span className="rv-detail__created">
            {new Date(run.created_at).toLocaleString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      {/* ── Tab navigation (P4) ── */}
      <div
        className="rv-detail__tabs it-seg"
        role="tablist"
        aria-label="Run detail views"
        data-testid="detail-tabs"
      >
        {(
          [
            { id: "trust",   label: "Trust Overview"  },
            { id: "ledger",  label: `Claim Ledger${run.claims.length > 0 ? ` (${run.claims.length})` : ""}` },
            { id: "report",  label: "Report"          },
            { id: "lineage", label: "Lineage"         },
          ] as { id: DetailTab; label: string }[]
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className={activeTab === tab.id ? "active" : ""}
            aria-selected={activeTab === tab.id}
            data-testid={`detail-tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab panels ── */}

      {/* Trust tab */}
      {activeTab === "trust" && (
        <div role="tabpanel" aria-label="Trust Overview" data-testid="tabpanel-trust">
          <TrustPanel run={run} />

          {/* ── 9 Optional entity sections — all render graceful empty-states ── */}
          <section
            className="rv-optional-entities"
            aria-label="Optional run artifacts"
            data-testid="optional-entities"
          >
            <h2 className="rv-optional-entities__title">Run Artifacts</h2>
            <p className="rv-optional-entities__note">
              The following artifacts are generated during the research pipeline. They
              are shown here when available; P4 surfaces interactive views for each.
            </p>
            <div className="rv-optional-entities__grid">
              {OPTIONAL_ENTITIES.map(({ id, label, msg }) => (
                <div
                  key={id}
                  className="rv-optional-entity"
                  data-entity={id}
                  data-testid={`optional-entity-${id}`}
                >
                  <EmptyState label={label} message={msg} />
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* Ledger tab */}
      {activeTab === "ledger" && (
        <div role="tabpanel" aria-label="Claim Ledger" data-testid="tabpanel-ledger">
          <div className="rv-ledger-view">
            {run.claims.length === 0 ? (
              <EmptyState label="Claim Ledger" message="No claims in this run." />
            ) : (
              <>
                <LedgerFacets
                  claims={run.claims}
                  onFiltered={setFilteredClaims}
                />
                <ClaimLedgerTable
                  claims={filteredClaims.length > 0 || run.claims.length === 0
                    ? filteredClaims
                    : run.claims}
                  onClaimSelect={handleClaimSelect}
                />
              </>
            )}
          </div>

          {/* Provenance modal for ledger tab */}
          <ProvenanceModal ref={modalRef} claims={run.claims} />
        </div>
      )}

      {/* Report tab */}
      {activeTab === "report" && (
        <div role="tabpanel" aria-label="Report" data-testid="tabpanel-report">
          <ReportOverlay run={run} reportDraft={run.report_draft ?? null} />
        </div>
      )}

      {/* Lineage tab */}
      {activeTab === "lineage" && (
        <div role="tabpanel" aria-label="Lineage Graph" data-testid="tabpanel-lineage">
          <ArtifactLineageGraph run={run} />
        </div>
      )}
    </div>
  );
}

export default RunDetailScreen;
