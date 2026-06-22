import { useMemo } from "react";
import type { RFRunExport } from "@/types/rf";
import type { LineageNode } from "@/components/LineageGraph/lineageTree";
import { ClaimAuditWorkbench } from "@/components/ClaimLedger/ClaimAuditWorkbench";
import { ArtifactLineageGraph } from "@/components/LineageGraph/LineageGraph";
import { ReportOverlay } from "@/components/ReportOverlay/ReportOverlay";
import { TrustCockpit } from "@/components/TrustPanel/TrustCockpit";
import { SwarmPane } from "./SwarmPane";
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
  /** Called when the user double-clicks a lineage row or clicks ⤢ in LineageDetailPanel. */
  onExpandNode?: (node: LineageNode) => void;
}

export function RunDetailWorkspace({
  run,
  activeTab,
  selectedClaimId,
  mode,
  onTabChange,
  onOpenProvenance,
  onExpandNode,
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
        { id: "swarm", label: "Swarm" },
        { id: "writeback", label: "Writeback", disabled: !writebackAvailable && activeTab !== "writeback" },
      ] as { id: DetailTab; label: string; disabled?: boolean }[],
    [activeTab, run.claims.length, writebackAvailable],
  );

  return (
    <div className={`rv-detail-workspace rv-detail-workspace--${mode}`} data-testid="run-detail-workspace" data-mode={mode}>
      {/*
       * D5 STICKY CHROME: The tab bar is a flex-shrink:0 sibling ABOVE the scroll container.
       * In modal mode this bar is pulled out of the scrolling region via CSS.
       * In page mode RunDetail.tsx wraps nav+header+tabbar in .rv-detail__sticky.
       *
       * STAGE-3 CONTRACT: The scrollable content area has class .rv-detail-workspace__body.
       * The modal scroll container is .rv-run-modal .rv-detail-workspace (overflow:auto set by CSS).
       * Page scroll container is .rv-detail__body (set by RunDetail.tsx).
       * Outline's IntersectionObserver anchors to the nearest scroll container with that class.
       */}
      <div
        className="rv-detail__tabs it-seg rv-detail-workspace__tab-bar"
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
            aria-current={activeTab === tab.id ? "true" : undefined}
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

      {/* Scrollable content body — Stage 3 anchors its outline IntersectionObserver here */}
      <div className="rv-detail-workspace__body">
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
              onExpandNode={onExpandNode}
            />
          </div>
        )}

        {activeTab === "swarm" && (
          <div role="tabpanel" aria-label="Swarm" data-testid="tabpanel-swarm">
            <SwarmPane run={run} />
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
    </div>
  );
}

function RunOverview({ run, onOpenAudit }: { run: RFRunExport; onOpenAudit: (claimId: string) => void }) {
  const attention = summarizeRunAttention(run);
  const topClaims = run.claims.slice(0, 4);

  // P5 DISP-004: determine which metadata fields are present
  const hasMetadata =
    (run.linked_projects?.length ?? 0) > 0 ||
    run.category != null ||
    (run.tags?.length ?? 0) > 0 ||
    run.backlog_idea_ref != null;

  // P7 ENR-005: determine which enrichment widgets to show
  const hasCost = run.cost_usd != null;
  const hasModelProfiles = run.model_profiles != null;
  const hasSourceCountByType =
    run.source_count_by_type != null &&
    Object.keys(run.source_count_by_type).length > 0;
  const hasClaimDistribution =
    run.claim_counts != null &&
    (run.claim_counts.total ?? 0) > 0;
  const hasWritebacks =
    run.writebacks?.targets != null && run.writebacks.targets.length > 0;
  const hasEnrichment =
    hasCost || hasModelProfiles || hasSourceCountByType || hasClaimDistribution || hasWritebacks;

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

      {/* P5 DISP-004: Run Metadata section — renders only rows with data; section omits when all null */}
      <div className="rv-run-overview__metadata it-card" data-testid="run-overview-metadata">
        <div className="rv-pane-title">
          <h3>Run Metadata</h3>
        </div>
        {hasMetadata ? (
          <dl className="rv-metadata-dl">
            {run.linked_projects?.length ? (
              <div className="rv-metadata-dl__row" data-testid="metadata-linked-projects">
                <dt>Linked Projects</dt>
                <dd>
                  <div className="rv-metadata-dl__chips">
                    {run.linked_projects.map((project) => (
                      <span key={project} className="it-chip blue rv-project-badge">
                        {project}
                      </span>
                    ))}
                  </div>
                </dd>
              </div>
            ) : null}
            {run.category ? (
              <div className="rv-metadata-dl__row" data-testid="metadata-category">
                <dt>Category</dt>
                <dd><span className="rv-run-modal__category">{run.category}</span></dd>
              </div>
            ) : null}
            {run.tags?.length ? (
              <div className="rv-metadata-dl__row" data-testid="metadata-tags">
                <dt>Tags</dt>
                <dd>
                  <div className="rv-metadata-dl__chips">
                    {run.tags.map((tag) => (
                      <span key={tag} className="it-chip rv-tag-chip">
                        {tag}
                      </span>
                    ))}
                  </div>
                </dd>
              </div>
            ) : null}
            {run.backlog_idea_ref ? (
              <div className="rv-metadata-dl__row" data-testid="metadata-backlog-ref">
                <dt>Backlog Ref</dt>
                <dd>
                  <a
                    href={`#backlog-${run.backlog_idea_ref}`}
                    className="rv-backlog-link"
                    title={run.backlog_idea_id ?? run.backlog_idea_ref}
                  >
                    {run.backlog_idea_ref}
                  </a>
                  {run.backlog_idea_id ? (
                    <span className="rv-muted"> ({run.backlog_idea_id})</span>
                  ) : null}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p className="rv-muted" data-testid="metadata-empty">No run metadata available for this export.</p>
        )}
      </div>

      {/* P7 ENR-005: Enrichment section — each widget shown only when its data field non-null */}
      {hasEnrichment ? (
        <div
          className="rv-run-overview__enrichment it-card"
          data-testid="run-overview-enrichment"
        >
          <div className="rv-pane-title">
            <h3>Run Enrichment</h3>
          </div>
          <div className="rv-enrichment-widgets">

            {/* Cost widget */}
            {hasCost ? (
              <div className="rv-enrichment-widget" data-testid="enrichment-cost">
                <span className="rv-enrichment-widget__label">Cost</span>
                <span className="rv-enrichment-widget__value it-numeric">
                  {`$${(run.cost_usd as number).toFixed(4)}`}
                </span>
              </div>
            ) : null}

            {/* Model Profiles widget */}
            {hasModelProfiles ? (
              <div className="rv-enrichment-widget rv-enrichment-widget--wide" data-testid="enrichment-model-profiles">
                <span className="rv-enrichment-widget__label">Model Profiles</span>
                <table className="rv-enrichment-table" aria-label="Model profile settings">
                  <tbody>
                    {run.model_profiles!.extraction_model_profile != null ? (
                      <tr>
                        <th>Extraction</th>
                        <td><code>{run.model_profiles!.extraction_model_profile}</code></td>
                      </tr>
                    ) : null}
                    {run.model_profiles!.synthesis_model_profile != null ? (
                      <tr>
                        <th>Synthesis</th>
                        <td><code>{run.model_profiles!.synthesis_model_profile}</code></td>
                      </tr>
                    ) : null}
                    {run.model_profiles!.verification_model_profile != null ? (
                      <tr>
                        <th>Verification</th>
                        <td><code>{run.model_profiles!.verification_model_profile}</code></td>
                      </tr>
                    ) : null}
                    {run.model_profiles!.max_runtime_minutes != null ? (
                      <tr>
                        <th>Max runtime</th>
                        <td>{run.model_profiles!.max_runtime_minutes} min</td>
                      </tr>
                    ) : null}
                    {run.model_profiles!.freshness_days != null ? (
                      <tr>
                        <th>Freshness</th>
                        <td>{run.model_profiles!.freshness_days} days</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            ) : null}

            {/* Source Count by Type widget */}
            {hasSourceCountByType ? (
              <div className="rv-enrichment-widget rv-enrichment-widget--wide" data-testid="enrichment-source-count">
                <span className="rv-enrichment-widget__label">Sources by Type</span>
                <div className="rv-enrichment-source-counts">
                  {Object.entries(run.source_count_by_type!).map(([type, count]) => (
                    <div key={type} className="rv-enrichment-source-count-row">
                      <span className="it-chip rv-tag-chip">{type.replace(/_/g, " ")}</span>
                      <span className="rv-enrichment-count it-numeric">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Confidence + Materiality distribution widget (from claim_counts) */}
            {hasClaimDistribution ? (
              <div className="rv-enrichment-widget rv-enrichment-widget--wide" data-testid="enrichment-claim-distribution">
                <span className="rv-enrichment-widget__label">Claim Distribution</span>
                <div className="rv-enrichment-distributions">
                  <ClaimDistributionBars counts={run.claim_counts!} />
                </div>
              </div>
            ) : null}

            {/* Writeback targets + status widget */}
            {hasWritebacks ? (
              <div className="rv-enrichment-widget rv-enrichment-widget--wide" data-testid="enrichment-writebacks">
                <span className="rv-enrichment-widget__label">Writeback Targets</span>
                <ul className="rv-enrichment-writeback-list">
                  {run.writebacks!.targets!.map((target, idx) => {
                    const key = target.name ?? target.destination ?? String(idx);
                    const statusClass = writebackStatusClass(target.status ?? null);
                    return (
                      <li key={key} className="rv-enrichment-writeback-row">
                        <span className="rv-enrichment-writeback-name">
                          {target.name ?? target.destination ?? "—"}
                        </span>
                        {target.status ? (
                          <span className={`it-chip ${statusClass}`}>
                            {target.status}
                          </span>
                        ) : null}
                        {target.url ? (
                          <a
                            href={target.url}
                            className="rv-enrichment-writeback-link"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Open ${target.name ?? "writeback target"}`}
                          >
                            ↗
                          </a>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}

          </div>
        </div>
      ) : null}

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

// ── Enrichment sub-components ─────────────────────────────────────────────────

/**
 * Renders confidence and materiality progress bars from claim_counts.
 * Each bar shows the proportion of that category relative to total claims.
 * Only renders bars for categories with non-zero counts.
 */
function ClaimDistributionBars({ counts }: { counts: NonNullable<RFRunExport["claim_counts"]> }) {
  const total = counts.total ?? counts.claims_total ?? 0;
  if (total === 0) return null;

  const rows: Array<{ label: string; value: number; colorClass: string; testId: string }> = [
    { label: "Supported",    value: counts.supported ?? counts.claims_supported ?? 0,    colorClass: "",         testId: "dist-supported" },
    { label: "Inference",    value: counts.inference ?? counts.claims_inference ?? 0,    colorClass: "blue",     testId: "dist-inference" },
    { label: "Speculation",  value: counts.speculation ?? counts.claims_speculation ?? 0, colorClass: "gold",    testId: "dist-speculation" },
    { label: "Contradicted", value: counts.claims_contradicted ?? 0,                      colorClass: "purple",  testId: "dist-contradicted" },
    { label: "Unsupported",  value: counts.claims_unsupported ?? 0,                       colorClass: "",        testId: "dist-unsupported" },
  ].filter((r) => r.value > 0);

  return (
    <div className="rv-enrichment-dist-bars" data-testid="claim-distribution-bars">
      {rows.map(({ label, value, colorClass, testId }) => {
        const pct = Math.round((value / total) * 100);
        return (
          <div key={label} className="rv-enrichment-dist-row" data-testid={testId}>
            <span className="rv-enrichment-dist-label">{label}</span>
            <div
              className={`it-progress${colorClass ? ` ${colorClass}` : ""} rv-enrichment-dist-bar`}
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${label}: ${value} of ${total} (${pct}%)`}
            >
              <div className="fill" style={{ width: `${pct}%` }} />
            </div>
            <span className="rv-enrichment-dist-count it-numeric">{value}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Maps writeback status string to an it-chip color class. */
function writebackStatusClass(status: string | null): string {
  if (!status) return "";
  const s = status.toLowerCase();
  if (s === "published" || s === "success" || s === "complete" || s === "completed") return "green";
  if (s === "pending" || s === "approved" || s === "ready") return "blue";
  if (s === "draft" || s === "in_progress" || s === "processing") return "orange";
  if (s === "failed" || s === "error" || s === "blocked") return "red";
  return "";
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
