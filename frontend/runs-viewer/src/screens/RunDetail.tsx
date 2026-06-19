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
import { TrustCockpit }                      from "@/components/TrustPanel/TrustCockpit";
import { ClaimAuditWorkbench }               from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { ReportOverlay }                     from "@/components/ReportOverlay/ReportOverlay";
import { ArtifactLineageGraph }              from "@/components/LineageGraph/LineageGraph";
import { formatDateTime }                    from "@/lib/runs";

// ── Tab types ─────────────────────────────────────────────────────────────────

type DetailTab = "trust" | "ledger" | "report" | "lineage" | "writeback";

function coerceDetailTab(value: string | null): DetailTab {
  if (value === "audit" || value === "ledger") return "ledger";
  if (value === "report" || value === "lineage" || value === "writeback") return value;
  return "trust";
}

function tabToQuery(tab: DetailTab): string {
  return tab === "ledger" ? "audit" : tab;
}

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
        <h1 className="rv-detail__run-id">
          {run.run_id}
        </h1>
        {run.created_at && (
          <span className="rv-detail__created">
            {formatDateTime(run.created_at)}
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
            { id: "trust",   label: "Trust"  },
            { id: "ledger",  label: `Audit${run.claims.length > 0 ? ` (${run.claims.length})` : ""}` },
            { id: "report",  label: "Report"          },
            { id: "lineage", label: "Lineage"         },
            { id: "writeback", label: "Writeback"     },
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
          <TrustCockpit
            run={run}
            onOpenAudit={(claimId) => setActiveTab("ledger", claimId)}
          />
        </div>
      )}

      {/* Ledger tab */}
      {activeTab === "ledger" && (
        <div role="tabpanel" aria-label="Claim Ledger" data-testid="tabpanel-ledger">
          <ClaimAuditWorkbench
            run={run}
            initialClaimId={selectedClaimId}
            onClaimChange={(claimId) => setActiveTab("ledger", claimId)}
          />
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

      {activeTab === "writeback" && (
        <div role="tabpanel" aria-label="Writeback" data-testid="tabpanel-writeback">
          <section className="rv-writeback-workspace it-card">
            <h2>Writeback Readiness</h2>
            <p>
              {run.writebacks
                ? "Writeback summary is available in this export."
                : "Writeback preview is not exported for this run yet."}
            </p>
            <dl>
              <div>
                <dt>Governance</dt>
                <dd>{run.governance?.approved_for_writeback ? "Approved" : "Not approved or unavailable"}</dd>
              </div>
              <div>
                <dt>Required fix</dt>
                <dd>{run.writebacks?.required_fix ?? "No required fix exported"}</dd>
              </div>
              <div>
                <dt>Targets</dt>
                <dd>{run.writebacks?.targets?.length ? `${run.writebacks.targets.length} target(s)` : "Not exported"}</dd>
              </div>
            </dl>
          </section>
        </div>
      )}
    </div>
  );
}

export default RunDetailScreen;
