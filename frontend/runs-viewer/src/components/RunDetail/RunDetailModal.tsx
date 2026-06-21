import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useRunDetail } from "@/hooks";
import { ProvenanceModal } from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";
import { DetailModal } from "./DetailModal";
import type { DetailModalPayload } from "./DetailModal";
import type { LineageNode } from "@/components/LineageGraph/lineageTree";
import {
  countVerificationChecks,
  deriveRunTitle,
  formatDateTime,
  getClaimTotal,
  hasWritebackExport,
  summarizeRunAttention,
} from "@/lib/runs";
import { RunDetailWorkspace } from "./RunDetailWorkspace";
import { coerceDetailTab, tabToQuery, type DetailTab } from "./detailTabs";

export interface RunDetailModalProps {
  runId: string | null;
  onClose: () => void;
}

export function RunDetailModal({ runId, onClose }: RunDetailModalProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [claimModalOpen, setClaimModalOpen] = useState(false);
  const [detailModalPayload, setDetailModalPayload] = useState<DetailModalPayload | null>(null);
  const modalRef = useRef<ProvenanceModalHandle>(null);
  const { data: run, isLoading, error } = useRunDetail(runId ?? "");

  useEffect(() => {
    if (!runId) {
      setActiveTab("overview");
      setSelectedClaimId(null);
      setClaimModalOpen(false);
      setDetailModalPayload(null);
    }
  }, [runId]);

  const handleTabChange = useCallback((tab: DetailTab, claimId?: string | null) => {
    setActiveTab(coerceDetailTab(tab));
    setSelectedClaimId(claimId ?? null);
  }, []);

  const handleOpenProvenance = useCallback((claimId: string) => {
    setSelectedClaimId(claimId);
    setClaimModalOpen(true);
    modalRef.current?.open(claimId);
  }, []);

  const handleExpandNode = useCallback((node: LineageNode) => {
    setDetailModalPayload({ kind: "node", node });
  }, []);

  const fullPageHref = useMemo(() => {
    if (!runId) return "/runs";
    const params = new URLSearchParams();
    params.set("view", tabToQuery(activeTab));
    if (selectedClaimId) params.set("claim", selectedClaimId);
    return `/runs/${encodeURIComponent(runId)}?${params.toString()}`;
  }, [activeTab, runId, selectedClaimId]);

  const detailModalOpen = detailModalPayload !== null;

  useEffect(() => {
    if (!runId) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !claimModalOpen && !detailModalOpen) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [claimModalOpen, detailModalOpen, onClose, runId]);

  if (!runId) return null;

  const attention = run ? summarizeRunAttention(run) : null;
  const writebackAvailable = run ? hasWritebackExport(run) : false;

  return (
    <div
      className="rv-run-modal-overlay"
      data-testid="run-detail-modal-overlay"
      onClick={(event) => {
        if (event.target === event.currentTarget && !claimModalOpen && !detailModalOpen) onClose();
      }}
      role="presentation"
    >
      <section
        className="rv-run-modal"
        role="dialog"
        aria-modal="true"
        aria-label={run ? `Run detail for ${run.run_id}` : `Run detail for ${runId}`}
        data-testid="run-detail-modal"
        data-run-id={runId}
      >
        <header className="rv-run-modal__header">
          <div className="rv-run-modal__identity">
            <span className="rv-kicker">Run Detail</span>
            <h2>{run ? deriveRunTitle(run) : runId}</h2>
            <code>{runId}</code>
            {/* P5 DISP-003: metadata sub-header — omit entirely when all fields null */}
            {run && (run.linked_projects?.length || run.category || run.tags?.length) ? (
              <div className="rv-run-modal__meta-line" data-testid="run-modal-meta-line">
                {run.linked_projects?.length ? (
                  <span className="it-chip blue rv-project-badge" data-testid="modal-project-badge">
                    {run.linked_projects.join(", ")}
                  </span>
                ) : null}
                {run.category ? (
                  <span className="rv-run-modal__category" data-testid="modal-category">
                    {run.category}
                  </span>
                ) : null}
                {run.tags?.map((tag) => (
                  <span key={tag} className="it-chip rv-tag-chip" data-testid="modal-tag-chip">
                    {tag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
          <div className="rv-run-modal__actions">
            <Link className="it-btn secondary sm" to={fullPageHref} data-testid="run-modal-open-full-page">
              Open full page
            </Link>
            <button type="button" className="it-btn ghost sm" onClick={onClose} data-testid="run-modal-close">
              Close
            </button>
          </div>
        </header>

        {isLoading && (
          <div className="rv-loading" data-testid="run-detail-modal-loading">
            <p>Loading run {runId}...</p>
          </div>
        )}

        {error && (
          <div className="rv-error" data-testid="run-detail-modal-error">
            <p>Error: {error instanceof Error ? error.message : "Unknown error"}</p>
          </div>
        )}

        {run && (
          <>
            <div className="rv-run-modal__chips" aria-label="Run state">
              <span className="it-chip blue">{run.status_derived}</span>
              <span className="it-chip">{run.sensitivity ?? "public"}</span>
              <span className={`it-chip ${run.verification?.passed ? "green" : run.verification?.passed === false ? "red" : ""}`}>
                {run.verification?.passed ? "verified" : run.verification?.passed === false ? "verification failed" : "verification pending"}
              </span>
              <span className={`it-chip ${run.governance?.approved_for_writeback ? "green" : "orange"}`}>
                {run.governance?.approved_for_writeback ? "writeback approved" : "writeback gated"}
              </span>
            </div>

            <dl className="rv-run-modal__summary" data-testid="run-modal-summary">
              <div><dt>Created</dt><dd>{formatDateTime(run.created_at)}</dd></div>
              <div><dt>Claims</dt><dd>{getClaimTotal(run.claim_counts, run.claims).toLocaleString()}</dd></div>
              <div><dt>Failed checks</dt><dd>{countVerificationChecks(run.verification, "fail")}</dd></div>
              <div><dt>Redacted</dt><dd>{attention?.redactedSources ?? 0}</dd></div>
              <div><dt>Dangling</dt><dd>{attention?.danglingSources ?? 0}</dd></div>
              <div><dt>Attention</dt><dd>{attentionLabel(attention)}</dd></div>
            </dl>

            {!writebackAvailable && activeTab === "writeback" && (
              <p className="rv-muted">This run does not export writeback targets yet.</p>
            )}

            <RunDetailWorkspace
              run={run}
              activeTab={activeTab}
              selectedClaimId={selectedClaimId}
              mode="modal"
              onTabChange={handleTabChange}
              onOpenProvenance={handleOpenProvenance}
              onExpandNode={handleExpandNode}
            />

            <ProvenanceModal
              ref={modalRef}
              claims={run.claims}
              sensitivityThreshold={run.sensitivity_threshold}
              stacked
              onOpenChange={setClaimModalOpen}
              onChainClick={setSelectedClaimId}
            />

            <DetailModal
              payload={detailModalPayload}
              stacked
              onClose={() => setDetailModalPayload(null)}
            />
          </>
        )}
      </section>
    </div>
  );
}

function attentionLabel(attention: ReturnType<typeof summarizeRunAttention> | null): string {
  if (!attention) return "Loading";
  if (attention.failedChecks > 0) return "Failed verification";
  if (attention.danglingSources > 0) return "Dangling sources";
  if (attention.redactedSources > 0) return "Redacted evidence";
  if (attention.emptyInferenceBasis > 0) return "Inference gaps";
  return "Clear";
}

export default RunDetailModal;
