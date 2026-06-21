import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RFClaim, RFRunExport } from "@/types/rf";
import { deriveClaimTitle, deriveReportLocationTitle, deriveSourceTitle, shouldRedactSource, titleFromSlug } from "@/lib/runs";
import { deriveAuditHighlight, isFacetEmpty } from "@/lib/auditStateMachine";
import type { LedgerFacetState } from "@/components/ClaimLedger/LedgerFacets";
import { ClaimLedgerTable } from "./ClaimLedgerTable";
import { LedgerFacets } from "./LedgerFacets";
import { ProvenanceModal } from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";
import { DetailModal } from "@/components/RunDetail/DetailModal";
import type { DetailModalPayload } from "@/components/RunDetail/DetailModal";
import { ReportRenderer } from "@/components/ReportOverlay/ReportRenderer";
import { SourceCard } from "@/components/SourceCard/SourceCard";

interface ClaimAuditWorkbenchProps {
  run: RFRunExport;
  initialClaimId?: string | null;
  onClaimChange?: (claimId: string) => void;
  onOpenProvenance?: (claimId: string) => void;
}

export function ClaimAuditWorkbench({ run, initialClaimId, onClaimChange, onOpenProvenance }: ClaimAuditWorkbenchProps) {
  const modalRef = useRef<ProvenanceModalHandle>(null);
  const firstClaimId = run.claims[0]?.claim_id ?? null;
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(initialClaimId ?? firstClaimId);
  const [filteredClaims, setFilteredClaims] = useState<RFClaim[]>(run.claims);
  const [detailModalPayload, setDetailModalPayload] = useState<DetailModalPayload | null>(null);
  const [activeFacets, setActiveFacets] = useState<LedgerFacetState>({
    status: new Set(), materiality: new Set(), claim_type: new Set(), confidence: new Set(),
  });

  useEffect(() => {
    setFilteredClaims(run.claims);
    setSelectedClaimId((current) => {
      if (initialClaimId && run.claims.some((claim) => claim.claim_id === initialClaimId)) {
        return initialClaimId;
      }
      if (current && run.claims.some((claim) => claim.claim_id === current)) return current;
      return run.claims[0]?.claim_id ?? null;
    });
  }, [initialClaimId, run.claims]);

  const selectedClaim = useMemo(
    () => run.claims.find((claim) => claim.claim_id === selectedClaimId) ?? null,
    [run.claims, selectedClaimId],
  );

  // Derive the state machine output (highlight mode, active IDs, text flag)
  const auditHighlight = useMemo(
    () => deriveAuditHighlight(activeFacets, selectedClaimId, run.claims),
    [activeFacets, selectedClaimId, run.claims],
  );

  const selectClaim = useCallback((claimId: string) => {
    // Toggle: clicking the already-selected claim deselects it
    setSelectedClaimId((prev) => {
      const next = prev === claimId ? null : claimId;
      if (next !== null) onClaimChange?.(next);
      return next;
    });
  }, [onClaimChange]);

  const clearSelection = useCallback(() => {
    setSelectedClaimId(null);
  }, []);

  const reportTitle = run.title ?? titleFromSlug(run.run_id) ?? run.run_id;

  const openClaimModal = useCallback((claimId: string) => {
    if (onOpenProvenance) onOpenProvenance(claimId);
    else modalRef.current?.open(claimId);
  }, [onOpenProvenance]);

  const openDetailModal = useCallback((claimId: string) => {
    setDetailModalPayload({ kind: "claim", claimId, claims: run.claims });
  }, [run.claims]);

  if (run.claims.length === 0) {
    return (
      <div className="rv-audit-empty it-card" data-testid="claim-audit-workbench">
        <h2>Claim Audit</h2>
        <p>No claims are exported for this run.</p>
      </div>
    );
  }

  return (
    <section className="rv-audit-workbench" data-testid="claim-audit-workbench" aria-label="Claim audit workbench">
      <div className="rv-audit-toolbar">
        <div>
          <span className="rv-kicker">Claim Audit</span>
          <h2>Audit claims against sources, evidence, and report locations</h2>
        </div>
        <div className="rv-audit-toolbar__meta">
          <span>Run: <code>{run.run_id}</code></span>
          <span>Schema: {run.schema_version}</span>
          <span>Threshold: {run.sensitivity_threshold ?? "public"}</span>
        </div>
      </div>

      <div className="rv-audit-grid">
        <aside className="rv-audit-ledger it-card" aria-label="Claim ledger">
          <div className="rv-pane-title">
            <h3>Ledger</h3>
            <span>{filteredClaims.length} of {run.claims.length}</span>
          </div>
          <LedgerFacets claims={run.claims} onFiltered={setFilteredClaims} onFacetChange={setActiveFacets} />
          <ClaimLedgerTable
            claims={filteredClaims}
            selectedClaimId={selectedClaimId}
            onClaimSelect={selectClaim}
            onExpandClaim={openDetailModal}
          />
        </aside>

        <main className="rv-audit-report it-card" aria-label="Report">
          <div className="rv-audit-report__header">
            <div className="rv-pane-title">
              <h3>Report</h3>
              <span className="rv-audit-report__run-meta">
                <code>{run.run_id}</code>
                {reportTitle && <span className="rv-audit-report__run-title">{reportTitle}</span>}
              </span>
            </div>
            <button
              type="button"
              className="it-btn ghost xs rv-audit-report__clear-btn"
              aria-label="Clear claim selection"
              disabled={selectedClaimId === null && isFacetEmpty(activeFacets)}
              onClick={clearSelection}
            >
              Clear
            </button>
          </div>
          <div className="rv-audit-report__body">
            <ReportRenderer
              markdown={run.report_draft ?? ""}
              claims={run.claims}
              selectedClaimId={selectedClaimId}
              activeClaimIds={auditHighlight.activeClaimIds}
              highlightMode={auditHighlight.highlightMode}
              highlightText={auditHighlight.highlightText}
              onClaimSelect={(claimId) => selectClaim(claimId)}
              compact
            />
          </div>
        </main>

        <ClaimInspector
          runClaims={run.claims}
          claim={selectedClaim}
          threshold={run.sensitivity_threshold}
          runMeta={{ tags: run.tags, category: run.category }}
          onOpenModal={openClaimModal}
          onExpandClaim={openDetailModal}
          onSelectClaim={(claimId) => selectClaim(claimId)}
        />
      </div>

      <SelectedClaimLineage
        run={run}
        claim={selectedClaim}
        onSelectClaim={(claimId) => selectClaim(claimId)}
      />

      <ProvenanceModal
        ref={modalRef}
        claims={run.claims}
        onChainClick={(claimId) => selectClaim(claimId)}
      />

      <DetailModal
        payload={detailModalPayload}
        stacked
        onClose={() => setDetailModalPayload(null)}
      />
    </section>
  );
}

/** Minimal run-level metadata passed to ClaimInspector for reference display (P5 DISP-005). */
interface RunMetaRef {
  tags?: string[] | null;
  category?: string | null;
}

function ClaimInspector({
  runClaims,
  claim,
  threshold,
  runMeta,
  onOpenModal,
  onExpandClaim,
  onSelectClaim,
}: {
  runClaims: RFClaim[];
  claim: RFClaim | null;
  threshold: RFRunExport["sensitivity_threshold"];
  runMeta?: RunMetaRef;
  onOpenModal: (claimId: string) => void;
  onExpandClaim?: (claimId: string) => void;
  onSelectClaim: (claimId: string) => void;
}) {
  // P5 DISP-005: reference chips — shown only when non-null
  const hasRunMeta = (runMeta?.tags?.length ?? 0) > 0 || runMeta?.category != null;

  if (!claim) {
    return (
      <aside className="rv-claim-inspector it-card" data-testid="claim-inspector">
        <div className="rv-pane-title">
          <h3>Selected Claim</h3>
        </div>
        <p className="rv-muted">Select a claim from the ledger or report.</p>
      </aside>
    );
  }

  const dangling = claim.sources.some((source) => source.dangling || source.resolved === false);
  const redactedSources = claim.sources.filter((source) => shouldRedactSource(source, threshold));
  const emptyInference =
    (claim.claim_type === "inference" || claim.status === "inference") &&
    (claim.inference_basis?.from_claims ?? []).length === 0;
  const isInference = claim.claim_type === "inference" || claim.status === "inference";
  const isSpeculation = claim.claim_type === "speculation" || claim.status === "speculation";
  const confidence = confidenceScore(claim.confidence);

  return (
    <aside className="rv-claim-inspector it-card" data-testid="claim-inspector" data-claim-id={claim.claim_id}>
      <div className="rv-pane-title">
        <h3>Selected Claim</h3>
        <div className="rv-pane-title__actions">
          <button className="it-btn ghost sm" type="button" onClick={() => onOpenModal(claim.claim_id)}>
            Open modal
          </button>
          {onExpandClaim && (
            <button
              className="it-btn ghost sm"
              type="button"
              data-testid="claim-inspector-expand"
              aria-label="Expand claim in modal"
              onClick={() => onExpandClaim(claim.claim_id)}
            >
              ⤢
            </button>
          )}
        </div>
      </div>

      {/* P5 DISP-005: run-level reference chips — context only, non-interactive */}
      {hasRunMeta && (
        <div className="rv-inspector-run-meta" data-testid="inspector-run-meta" aria-label="Run context">
          {runMeta?.category ? (
            <span className="rv-run-modal__category" data-testid="inspector-run-category">
              {runMeta.category}
            </span>
          ) : null}
          {runMeta?.tags?.map((tag) => (
            <span key={tag} className="it-chip rv-tag-chip rv-tag-chip--sm" data-testid="inspector-run-tag">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="rv-inspector-title">
        <h4>{deriveClaimTitle(claim)}</h4>
        <code>{claim.claim_id}</code>
      </div>

      <div className="rv-inspector-head">
        {claim.claim_type && <span className={`it-chip ${claim.claim_type === "factual" ? "" : claim.claim_type === "inference" ? "blue" : "orange"}`}>{claim.claim_type}</span>}
        {claim.status && <span className={`it-chip ${statusTone(claim.status)}`}>{claim.status}</span>}
        {claim.materiality && <span className="it-chip">{claim.materiality}</span>}
        <span className={`rv-confidence-ring rv-confidence-ring--${confidence.tone}`} title={`${confidence.label} confidence`}>
          {confidence.score}
        </span>
      </div>

      <section className="rv-inspector-section">
        <h4>Claim</h4>
        <p>{claim.text}</p>
      </section>

      <section className="rv-inspector-section">
        <h4>Metadata</h4>
        <dl className="rv-inspector-dl">
          <div><dt>Status</dt><dd>{claim.status ?? "Not exported"}</dd></div>
          <div><dt>Confidence</dt><dd>{claim.confidence ?? "unknown"}</dd></div>
          <div><dt>Materiality</dt><dd>{claim.materiality ?? "Not exported"}</dd></div>
          <div><dt>Type</dt><dd>{claim.claim_type ?? "Not exported"}</dd></div>
          <div><dt>Sources</dt><dd>{claim.sources.length}</dd></div>
          <div><dt>Locations</dt><dd>{claim.report_locations?.length ?? 0}</dd></div>
        </dl>
      </section>

      <section className="rv-inspector-section">
        <h4>Source Cards</h4>
        {claim.sources.length > 0 ? (
          <div className="rv-inspector-source-list">
            {claim.sources.map((source) => (
              <SourceCard
                key={`${source.source_card_id}-${source.evidence_id}`}
                source={source}
                sensitivityThreshold={threshold}
                compact
              />
            ))}
          </div>
        ) : (
          <p className="rv-muted">No source cards linked.</p>
        )}
      </section>

      <section className="rv-inspector-section">
        <h4>Report Locations</h4>
        {claim.report_locations?.length ? (
          <ul className="rv-report-location-list">
            {claim.report_locations.map((location, index) => (
              <li key={`${location.file ?? "report"}-${location.paragraph_id ?? index}`}>
                <strong>{deriveReportLocationTitle(location)}</strong>
                <span>{[location.file, location.paragraph_id].filter(Boolean).join(" / ") || "No locator exported"}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rv-muted">No report locations exported.</p>
        )}
      </section>

      {isInference && (
        <section className="rv-inspector-section">
          <h4>Inference Basis</h4>
          {emptyInference ? (
            <Warning label="Empty inference basis" message="This inference has no declared basis claims." />
          ) : (
            <ClaimBasisFlow
              claimIds={claim.inference_basis?.from_claims ?? []}
              claims={runClaims}
              reasoning={claim.inference_basis?.reasoning_summary}
              onSelectClaim={onSelectClaim}
            />
          )}
        </section>
      )}

      {isSpeculation && (
        <section className="rv-inspector-section">
          <h4>Speculation Basis</h4>
          <p className="rv-muted">No structured basis exported.</p>
          <button type="button" className="it-btn ghost xs" onClick={() => onOpenModal(claim.claim_id)}>
            Open provenance modal
          </button>
        </section>
      )}

      {(dangling || emptyInference || redactedSources.length > 0 || claim.status === "mixed" || claim.status === "contradicted") && (
        <section className="rv-inspector-section">
          <h4>Warnings</h4>
          <div className="rv-warning-stack">
            {dangling && <Warning label="Dangling source" message="At least one source reference could not be resolved." />}
            {emptyInference && <Warning label="Inference gap" message="No basis claims are linked." />}
            {redactedSources.length > 0 && (
              <Warning
                label="Redacted source"
                message={`${redactedSources.length} source(s) are hidden by policy: ${redactedSources.map(deriveSourceTitle).join(", ")}.`}
              />
            )}
            {(claim.status === "mixed" || claim.status === "contradicted") && (
              <Warning label="Conflicting evidence" message={`Claim status is ${claim.status}.`} />
            )}
          </div>
        </section>
      )}
    </aside>
  );
}

function ClaimBasisFlow({
  claimIds,
  claims,
  reasoning,
  onSelectClaim,
}: {
  claimIds: string[];
  claims: RFClaim[];
  reasoning?: string | null;
  onSelectClaim: (claimId: string) => void;
}) {
  if (claimIds.length === 0) return <p className="rv-muted">No basis claims exported.</p>;
  return (
    <div className="rv-basis-flow" data-testid="claim-basis-flow">
      <div className="rv-basis-flow__chain">
        {claimIds.map((claimId, index) => {
          const basisClaim = claims.find((candidate) => candidate.claim_id === claimId);
          return (
            <span key={claimId} className="rv-basis-flow__item">
              <button
                type="button"
                className="rv-basis-flow__claim"
                title={basisClaim ? `${basisClaim.text} | ${basisClaim.status ?? "unknown"} | ${basisClaim.confidence ?? "unknown"} | ${basisClaim.sources.length} source(s)` : "Claim not found"}
                onClick={() => onSelectClaim(claimId)}
                data-testid={`basis-claim-${claimId}`}
              >
                {claimId}
              </button>
              {index < claimIds.length - 1 && <span aria-hidden="true">to</span>}
            </span>
          );
        })}
      </div>
      {reasoning && <p>{reasoning}</p>}
    </div>
  );
}

function SelectedClaimLineage({
  run,
  claim,
  onSelectClaim,
}: {
  run: RFRunExport;
  claim: RFClaim | null;
  onSelectClaim: (claimId: string) => void;
}) {
  const source = claim?.sources[0] ?? null;
  return (
    <section className="rv-selected-lineage it-card" aria-label="Selected claim lineage" data-testid="selected-claim-lineage">
      <h3>Lineage</h3>
      {claim ? (
        <div className="rv-lineage-chain">
          <LineageNode label="Source Card" value={source?.title ?? source?.source_card_id ?? "No source"} />
          <LineageNode label="Extraction" value={source?.evidence_locator ?? source?.locator ?? "No locator"} />
          <button type="button" className="rv-lineage-node rv-lineage-node--button" onClick={() => onSelectClaim(claim.claim_id)}>
            <span>Claim</span>
            <strong>{claim.claim_id}</strong>
          </button>
          <LineageNode label="Report" value={claim.report_locations?.[0]?.heading ?? (run.report_draft ? "Draft report" : "No report")} />
          <LineageNode label="Writeback" value={run.writebacks?.targets?.[0]?.status ?? "Not exported"} />
        </div>
      ) : (
        <p className="rv-muted">Select a claim to inspect the provenance chain.</p>
      )}
    </section>
  );
}

function LineageNode({ label, value }: { label: string; value: string }) {
  return (
    <div className="rv-lineage-node">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Warning({ label, message }: { label: string; message: string }) {
  return (
    <div className="rv-audit-warning" role="note">
      <strong>{label}</strong>
      <span>{message}</span>
    </div>
  );
}

function statusTone(status: string): string {
  if (status === "supported") return "green";
  if (status === "inference") return "blue";
  if (status === "speculation" || status === "mixed") return "orange";
  if (status === "unsupported" || status === "contradicted") return "red";
  return "";
}

function confidenceScore(confidence: RFClaim["confidence"]): { score: string; label: string; tone: "green" | "amber" | "red" | "neutral" } {
  if (confidence === "high") return { score: "92%", label: "high", tone: "green" };
  if (confidence === "medium") return { score: "74%", label: "medium", tone: "amber" };
  if (confidence === "low") return { score: "45%", label: "low", tone: "red" };
  return { score: "?", label: "unknown", tone: "neutral" };
}

export default ClaimAuditWorkbench;
