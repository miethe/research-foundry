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

import { useCallback }                       from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useRunDetail }                      from "@/hooks";
import { RunDetailWorkspace }                from "@/components/RunDetail/RunDetailWorkspace";
import { coerceDetailTab, tabToQuery, type DetailTab } from "@/components/RunDetail/detailTabs";
import { deriveRunTitle, formatDateTime }    from "@/lib/runs";

// ── Component ─────────────────────────────────────────────────────────────────

export function RunDetailScreen() {
  const { runId }    = useParams<{ runId: string }>();
  const navigate     = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: run, isLoading, error } = useRunDetail(runId ?? "");
  const activeTab = coerceDetailTab(searchParams.get("view"));
  const selectedClaimId = searchParams.get("claim");

  const setActiveTab = useCallback(
    (tab: DetailTab, claimId?: string | null) => {
      const next = new URLSearchParams(searchParams);
      next.set("view", tabToQuery(tab));
      if (claimId) next.set("claim", claimId);
      else next.delete("claim");
      setSearchParams(next, { replace: false });
    },
    [searchParams, setSearchParams],
  );

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
          Back to runs
        </button>
      </div>

      {/* Run identity header */}
      <div className="rv-detail__header">
        <div>
          <h1 className="rv-detail__title">{deriveRunTitle(run)}</h1>
          <code className="rv-detail__run-id">{run.run_id}</code>
        </div>
        {run.created_at && (
          <span className="rv-detail__created">
            {formatDateTime(run.created_at)}
          </span>
        )}
      </div>

      <RunDetailWorkspace
        run={run}
        activeTab={activeTab}
        selectedClaimId={selectedClaimId}
        mode="page"
        onTabChange={setActiveTab}
      />
    </div>
  );
}

export default RunDetailScreen;
