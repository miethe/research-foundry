/**
 * TrustPanel — composite "trust" overview panel for a run.
 *
 * Assembles:
 *   1. Header badges: derived status + sensitivity + governance verdict
 *   2. VerificationChecklist (per-check with deep-links to failing claims)
 *   3. ClaimStatusDonut (evidence_bundle.counts → donut)
 *   4. TimelineStepper (telemetry/run_trace.jsonl events)
 *   5. Governance block (evidence_bundle.governance approval info)
 *
 * All sub-components handle their own empty-states — TrustPanel never crashes
 * on partial data.
 *
 * Adapted from IntentTree WorkflowViewerScreen 4-panel layout.
 */

import type { RFRunExport, RFSensitivity, RFStatusDerived } from "@/types/rf";
import { VerificationChecklist } from "./VerificationChecklist";
import { ClaimStatusDonut }       from "./ClaimStatusDonut";
import { TimelineStepper }        from "./TimelineStepper";

// ── Badge helpers (duplicated from RunCard for component independence) ────────

const STATUS_LABEL: Record<RFStatusDerived, string> = {
  planned:          "Planned",
  sources_ingested: "Sources Ingested",
  extracted:        "Extracted",
  claim_mapped:     "Claim Mapped",
  synthesized:      "Synthesized",
  verified:         "Verified",
  published:        "Published",
};

const STATUS_PILL: Record<string, string> = {
  verified:         "done",
  published:        "done",
  synthesized:      "progress",
  claim_mapped:     "progress",
  extracted:        "progress",
  sources_ingested: "progress",
  planned:          "idle",
};

const SENSITIVITY_LABEL: Record<RFSensitivity, string> = {
  public:           "Public",
  personal:         "Personal",
  work_sensitive:   "Work Sensitive",
  client_sensitive: "Client Sensitive",
};

const SENSITIVITY_CHIP: Record<RFSensitivity, string> = {
  public:           "",
  personal:         "blue",
  work_sensitive:   "orange",
  client_sensitive: "red",
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface TrustPanelProps {
  run: RFRunExport;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function TrustPanel({ run }: TrustPanelProps) {
  const statusLabel = STATUS_LABEL[run.status_derived] ?? run.status_derived;
  const pillClass   = STATUS_PILL[run.status_derived] ?? "idle";

  const sens      = run.sensitivity;
  const sensLabel = sens ? SENSITIVITY_LABEL[sens] : null;
  const sensChip  = sens ? SENSITIVITY_CHIP[sens] : null;

  const gov = run.governance;
  const govApproved = gov?.approved_for_writeback;
  const govApprovedBy = gov?.approved_by;

  return (
    <section className="rv-trust-panel" aria-label="Trust overview" data-testid="trust-panel">

      {/* ── Header: status + sensitivity + governance badges ── */}
      <div className="rv-trust-panel__header">
        <h2 className="rv-trust-panel__title">Trust Overview</h2>

        <div className="rv-trust-panel__badges">
          {/* Lifecycle badge */}
          <span className={`it-pill ${pillClass}`} data-testid="tp-lifecycle-badge">
            {statusLabel}
          </span>

          {/* Sensitivity badge */}
          {sens && sensLabel && sensChip !== null && (
            <span
              className={`it-chip ${sensChip}`}
              data-testid="tp-sensitivity-badge"
              data-sensitivity={sens}
            >
              {sensLabel}
            </span>
          )}

          {/* Governance verdict */}
          {govApproved != null && (
            <span
              className={`it-chip ${govApproved ? "green" : "orange"}`}
              data-testid="tp-governance-badge"
            >
              {govApproved
                ? `Approved${govApprovedBy ? ` · ${govApprovedBy}` : ""}`
                : "Writeback not approved"}
            </span>
          )}
        </div>
      </div>

      {/* ── Body: 2-column grid on wider screens ── */}
      <div className="rv-trust-panel__body">

        {/* Left column: verification checklist */}
        <div className="rv-trust-panel__col rv-trust-panel__col--left">
          <h3 className="rv-trust-panel__section-title">Verification Checks</h3>
          <VerificationChecklist verification={run.verification} />
        </div>

        {/* Right column: donut + timeline */}
        <div className="rv-trust-panel__col rv-trust-panel__col--right">
          <h3 className="rv-trust-panel__section-title">Claim Distribution</h3>
          <ClaimStatusDonut claimCounts={run.claim_counts} />

          <h3 className="rv-trust-panel__section-title rv-trust-panel__section-title--timeline">
            Run Timeline
          </h3>
          <TimelineStepper timeline={run.timeline} />
        </div>
      </div>

      {/* ── Governance block (full-width) ── */}
      {gov && (
        <div className="rv-trust-panel__governance" data-testid="tp-governance-block">
          <h3 className="rv-trust-panel__section-title">Governance</h3>
          <dl className="rv-governance-dl">
            {gov.sensitivity && (
              <>
                <dt>Sensitivity</dt>
                <dd>{gov.sensitivity}</dd>
              </>
            )}
            {gov.approved_for_writeback != null && (
              <>
                <dt>Approved for writeback</dt>
                <dd>{gov.approved_for_writeback ? "Yes" : "No"}</dd>
              </>
            )}
            {gov.approved_by && (
              <>
                <dt>Approved by</dt>
                <dd>{gov.approved_by}</dd>
              </>
            )}
            {gov.approval_timestamp && (
              <>
                <dt>Approval time</dt>
                <dd>{gov.approval_timestamp}</dd>
              </>
            )}
          </dl>
        </div>
      )}
    </section>
  );
}

export default TrustPanel;
