import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RFClaim, RFResolvedSource, RFRunExport } from "@/types/rf";
import { shouldRedactSource } from "@/lib/runs";
import { ClaimLedgerTable } from "./ClaimLedgerTable";
import { LedgerFacets } from "./LedgerFacets";
import { ProvenanceModal } from "@/components/ProvenanceModal/ProvenanceModal";
import type { ProvenanceModalHandle } from "@/components/ProvenanceModal/ProvenanceModal";
import { ReportRenderer } from "@/components/ReportOverlay/ReportRenderer";

interface ClaimAuditWorkbenchProps {
  run: RFRunExport;
  initialClaimId?: string | null;
  onClaimChange?: (claimId: string) => void;
}

export function ClaimAuditWorkbench({ run, initialClaimId, onClaimChange }: ClaimAuditWorkbenchProps) {
  const modalRef = useRef<ProvenanceModalHandle>(null);
  const firstClaimId = run.claims[0]?.claim_id ?? null;
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(initialClaimId ?? firstClaimId);
  const [filteredClaims, setFilteredClaims] = useState<RFClaim[]>(run.claims);

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

  const selectClaim = useCallback((claimId: string, openModal = false) => {
    setSelectedClaimId(claimId);
    onClaimChange?.(claimId);
    if (openModal) modalRef.current?.open(claimId);
  }, [onClaimChange]);

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
          <LedgerFacets claims={run.claims} onFiltered={setFilteredClaims} />
          <ClaimLedgerTable
            claims={filteredClaims}
            selectedClaimId={selectedClaimId}
            onClaimSelect={(claimId) => selectClaim(claimId, true)}
          />
        </aside>

        <main className="rv-audit-report it-card" aria-label="Report">
          <div className="rv-pane-title">
            <h3>Report</h3>
            <span>{selectedClaimId ? `Selected ${selectedClaimId}` : "No claim selected"}</span>
          </div>
          <ReportRenderer
            markdown={run.report_draft ?? ""}
            claims={run.claims}
            selectedClaimId={selectedClaimId}
            onClaimSelect={(claimId) => selectClaim(claimId)}
            compact
          />
        </main>

        <ClaimInspector
          claim={selectedClaim}
          threshold={run.sensitivity_threshold}
          onOpenModal={(claimId) => modalRef.current?.open(claimId)}
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
    </section>
  );
}

function ClaimInspector({
  claim,
  threshold,
  onOpenModal,
  onSelectClaim,
}: {
  claim: RFClaim | null;
  threshold: RFRunExport["sensitivity_threshold"];
  onOpenModal: (claimId: string) => void;
  onSelectClaim: (claimId: string) => void;
}) {
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

  const primarySource = claim.sources[0] ?? null;
  const redacted = primarySource ? shouldRedactSource(primarySource, threshold) : false;
  const dangling = claim.sources.some((source) => source.dangling || source.resolved === false);
  const emptyInference =
    (claim.claim_type === "inference" || claim.status === "inference") &&
    (claim.inference_basis?.from_claims ?? []).length === 0;

  return (
    <aside className="rv-claim-inspector it-card" data-testid="claim-inspector" data-claim-id={claim.claim_id}>
      <div className="rv-pane-title">
        <h3>Selected Claim</h3>
        <button className="it-btn ghost sm" type="button" onClick={() => onOpenModal(claim.claim_id)}>
          Open modal
        </button>
      </div>

      <div className="rv-inspector-head">
        <code>{claim.claim_id}</code>
        {claim.claim_type && <span className={`it-chip ${claim.claim_type === "factual" ? "" : claim.claim_type === "inference" ? "blue" : "orange"}`}>{claim.claim_type}</span>}
        {claim.status && <span className={`it-chip ${statusTone(claim.status)}`}>{claim.status}</span>}
        {claim.confidence && <strong>{confidenceScore(claim.confidence)}%</strong>}
      </div>

      <section className="rv-inspector-section">
        <h4>Claim</h4>
        <p>{claim.text}</p>
      </section>

      <section className="rv-inspector-section">
        <h4>Source Card</h4>
        {primarySource ? <SourceSummary source={primarySource} redacted={redacted} /> : <p className="rv-muted">No source cards linked.</p>}
      </section>

      {primarySource && (
        <section className="rv-inspector-section">
          <h4>Quote</h4>
          {primarySource.dangling ? (
            <Warning label="Dangling Source" message={`Missing source card: ${primarySource.source_card_id}`} />
          ) : redacted ? (
            <Warning label="Redacted Evidence" message={`Evidence text is hidden by threshold ${threshold ?? "public"}.`} />
          ) : (
            <blockquote className="rv-inspector-quote">
              {primarySource.quote || primarySource.summary || "No quote or summary exported for this source."}
            </blockquote>
          )}
          <dl className="rv-inspector-dl">
            <div>
              <dt>Locator</dt>
              <dd>{primarySource.evidence_locator ?? primarySource.locator ?? "Not exported"}</dd>
            </div>
            <div>
              <dt>Trust</dt>
              <dd>{primarySource.trust?.source_rank ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Usage</dt>
              <dd>{primarySource.usage?.citation_required ? "Citation required" : "No usage note"}</dd>
            </div>
          </dl>
        </section>
      )}

      {(claim.inference_basis?.reasoning_summary || emptyInference) && (
        <section className="rv-inspector-section">
          <h4>Inference Basis</h4>
          {emptyInference ? (
            <Warning label="Empty inference basis" message="This inference has no declared basis claims." />
          ) : (
            <>
              <p>{claim.inference_basis?.reasoning_summary}</p>
              <div className="rv-linked-claims">
                {(claim.inference_basis?.from_claims ?? []).map((claimId) => (
                  <button key={claimId} type="button" className="it-btn ghost xs" onClick={() => onSelectClaim(claimId)}>
                    {claimId}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {(dangling || emptyInference || redacted || claim.status === "mixed" || claim.status === "contradicted") && (
        <section className="rv-inspector-section">
          <h4>Warnings</h4>
          <div className="rv-warning-stack">
            {dangling && <Warning label="Dangling source" message="At least one source reference could not be resolved." />}
            {emptyInference && <Warning label="Inference gap" message="No basis claims are linked." />}
            {redacted && <Warning label="Redacted source" message="Evidence text is present but hidden by policy." />}
            {(claim.status === "mixed" || claim.status === "contradicted") && (
              <Warning label="Conflicting evidence" message={`Claim status is ${claim.status}.`} />
            )}
          </div>
        </section>
      )}
    </aside>
  );
}

function SourceSummary({ source, redacted }: { source: RFResolvedSource; redacted: boolean }) {
  return (
    <div className={`rv-source-summary${source.dangling ? " rv-source-summary--dangling" : ""}`}>
      <strong>{source.title ?? source.source_card_id}</strong>
      <span>{source.source_type ?? "source"} · {source.locator ?? source.evidence_locator ?? "No locator"}</span>
      <div>
        <span className={`it-chip ${source.relation === "contradicts" ? "red" : source.relation === "supports" ? "green" : "blue"}`}>
          {source.relation}
        </span>
        {redacted && <span className="it-chip orange">Redacted</span>}
      </div>
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

function confidenceScore(confidence: RFClaim["confidence"]): number {
  if (confidence === "high") return 92;
  if (confidence === "medium") return 74;
  return 45;
}

export default ClaimAuditWorkbench;
