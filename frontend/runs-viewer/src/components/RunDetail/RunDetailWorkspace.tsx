import { useMemo } from "react";
import type { RFRunExport } from "@/types/rf";
import { ClaimAuditWorkbench } from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { ArtifactLineageGraph } from "@/components/LineageGraph/LineageGraph";
import { ReportOverlay } from "@/components/ReportOverlay/ReportOverlay";
import { TrustCockpit } from "@/components/TrustPanel/TrustCockpit";
import {
  deriveRunTitle,
  formatDateTime,
  getClaimTotal,
  hasWritebackExport,
  summarizeRunAttention,
} from "@/lib/runs";
import type { DetailTab } from "./detailTabs";

export interface RunDetailWorkspaceProps {
  run: RFRunExport;
  activeTab: DetailTab;
  selectedClaimId?: string | null;
  mode: "page" | "modal";
  onTabChange: (tab: DetailTab, claimId?: string | null) => void;
  onOpenProvenance?: (claimId: string) => void;
}

export function RunDetailWorkspace({
  run,
  activeTab,
  selectedClaimId,
  mode,
  onTabChange,
  onOpenProvenance,
}: RunDetailWorkspaceProps) {
  const writebackAvailable = hasWritebackExport(run);
  const tabs = useMemo(
    () =>
      [
        { id: "overview", label: "Overview" },
        { id: "trust", label: "Trust" },
        { id: "ledger", label: `Audit${run.claims.length > 0 ? ` (${run.claims.length})` : ""}` },
        { id: "report", label: "Report" },
        { id: "lineage", label: "Lineage" },
        { id: "writeback", label: "Writeback", disabled: !writebackAvailable && activeTab !== "writeback" },
      ] as { id: DetailTab; label: string; disabled?: boolean }[],
    [activeTab, run.claims.length, writebackAvailable],
  );

  return (
    <div className={`rv-detail-workspace rv-detail-workspace--${mode}`} data-testid="run-detail-workspace" data-mode={mode}>
      <div
        className="rv-detail__tabs it-seg"
        role="tablist"
        aria-label="Run detail views"
        data-testid="detail-tabs"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className={activeTab === tab.id ? "active" : ""}
            aria-selected={activeTab === tab.id}
            aria-disabled={tab.disabled ? "true" : undefined}
            disabled={tab.disabled}
            title={tab.disabled ? "Writeback preview is not exported for this run." : tab.label}
            data-testid={`detail-tab-${tab.id}`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div role="tabpanel" aria-label="Overview" data-testid="tabpanel-overview">
          <RunOverview run={run} onOpenAudit={(claimId) => onTabChange("ledger", claimId)} />
        </div>
      )}

      {activeTab === "trust" && (
        <div role="tabpanel" aria-label="Trust Overview" data-testid="tabpanel-trust">
          <TrustCockpit
            run={run}
            onOpenAudit={(claimId) => onTabChange("ledger", claimId)}
          />
        </div>
      )}

      {activeTab === "ledger" && (
        <div role="tabpanel" aria-label="Claim Ledger" data-testid="tabpanel-ledger">
          <ClaimAuditWorkbench
            run={run}
            initialClaimId={selectedClaimId}
            onClaimChange={(claimId) => onTabChange("ledger", claimId)}
            onOpenProvenance={onOpenProvenance}
          />
        </div>
      )}

      {activeTab === "report" && (
        <div role="tabpanel" aria-label="Report" data-testid="tabpanel-report">
          <ReportOverlay
            run={run}
            reportDraft={run.report_draft ?? null}
            onOpenProvenance={onOpenProvenance}
          />
        </div>
      )}

      {activeTab === "lineage" && (
        <div role="tabpanel" aria-label="Lineage Graph" data-testid="tabpanel-lineage">
          <ArtifactLineageGraph
            run={run}
            selectedClaimId={selectedClaimId}
            onSelectClaim={(claimId) => onTabChange("lineage", claimId)}
            onOpenProvenance={onOpenProvenance}
          />
        </div>
      )}

      {activeTab === "writeback" && (
        <div role="tabpanel" aria-label="Writeback" data-testid="tabpanel-writeback">
          <section className="rv-writeback-workspace it-card">
            <h2>Writeback Readiness</h2>
            <p>
              {writebackAvailable
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

function RunOverview({ run, onOpenAudit }: { run: RFRunExport; onOpenAudit: (claimId: string) => void }) {
  const attention = summarizeRunAttention(run);
  const topClaims = run.claims.slice(0, 4);

  return (
    <section className="rv-run-overview" data-testid="run-overview">
      <div className="rv-run-overview__hero it-card">
        <div>
          <span className="rv-kicker">Run Overview</span>
          <h2>{deriveRunTitle(run)}</h2>
          <code>{run.run_id}</code>
        </div>
        <dl>
          <div><dt>Created</dt><dd>{formatDateTime(run.created_at)}</dd></div>
          <div><dt>Claims</dt><dd>{getClaimTotal(run.claim_counts, run.claims).toLocaleString()}</dd></div>
          <div><dt>Failed checks</dt><dd>{attention.failedChecks}</dd></div>
          <div><dt>Redacted sources</dt><dd>{attention.redactedSources}</dd></div>
          <div><dt>Dangling sources</dt><dd>{attention.danglingSources}</dd></div>
          <div><dt>Top attention</dt><dd>{topAttentionLabel(attention)}</dd></div>
        </dl>
      </div>

      <div className="rv-run-overview__claims it-card">
        <div className="rv-pane-title">
          <h3>Review Starting Points</h3>
          <span>{topClaims.length} claims</span>
        </div>
        <ul>
          {topClaims.map((claim) => (
            <li key={claim.claim_id}>
              <button type="button" onClick={() => onOpenAudit(claim.claim_id)}>
                <strong>{claim.claim_id}</strong>
                <span>{claim.text}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function topAttentionLabel(attention: ReturnType<typeof summarizeRunAttention>): string {
  if (attention.failedChecks > 0) return "Failed verification";
  if (attention.danglingSources > 0) return "Dangling sources";
  if (attention.redactedSources > 0) return "Redacted evidence";
  if (attention.emptyInferenceBasis > 0) return "Inference basis gaps";
  if (attention.warningChecks > 0) return "Verification warnings";
  return "No attention flags";
}

export default RunDetailWorkspace;
