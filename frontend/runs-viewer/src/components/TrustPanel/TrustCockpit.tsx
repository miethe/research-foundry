import type { RFClaim, RFRunExport, RFStatusDerived } from "@/types/rf";
import {
  STATUS_LABEL,
  countVerificationChecks,
  formatDateTime,
  getClaimTotal,
  getInferenceTotal,
  getSpeculationTotal,
  getSupportedTotal,
  summarizeRunAttention,
} from "@/lib/runs";
import { ClaimStatusDonut } from "./ClaimStatusDonut";
import { TimelineStepper } from "./TimelineStepper";
import { VerificationChecklist } from "./VerificationChecklist";

interface TrustCockpitProps {
  run: RFRunExport;
  onOpenAudit?: (claimId?: string) => void;
}

const LIFECYCLE: { id: RFStatusDerived | "review"; label: string }[] = [
  { id: "planned", label: "Planned" },
  { id: "sources_ingested", label: "Data Collection" },
  { id: "extracted", label: "Processing" },
  { id: "claim_mapped", label: "Analysis" },
  { id: "synthesized", label: "Report Draft" },
  { id: "verified", label: "Verification" },
  { id: "review", label: "Review" },
  { id: "published", label: "Published" },
];

const STATUS_INDEX: Record<RFStatusDerived, number> = {
  planned: 0,
  sources_ingested: 1,
  extracted: 2,
  claim_mapped: 3,
  synthesized: 4,
  verified: 5,
  published: 7,
};

function statusTone(run: RFRunExport): string {
  if (run.verification?.present && run.verification.passed === false) return "blocked";
  if (run.status_derived === "verified" || run.status_derived === "published") return "done";
  if (run.status_derived === "planned") return "idle";
  return "progress";
}

function claimTone(claim: RFClaim): string {
  if (claim.status === "unsupported" || claim.status === "contradicted") return "red";
  if (claim.status === "mixed" || claim.status === "speculation") return "orange";
  if (claim.status === "inference") return "blue";
  return "green";
}

function contextText(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "string") return value;
  if (value == null) return "Not exported";
  return String(value);
}

function briefObjective(markdown?: string | null): string {
  if (!markdown) return "Research brief summary is not exported in this run.";
  const line = markdown
    .split(/\r?\n/)
    .map((entry) => entry.replace(/^#+\s*/, "").trim())
    .find(Boolean);
  return line ?? "Research brief summary is present but empty.";
}

export function TrustCockpit({ run, onOpenAudit }: TrustCockpitProps) {
  const attention = summarizeRunAttention(run);
  const failedChecks = countVerificationChecks(run.verification, "fail");
  const passedChecks = countVerificationChecks(run.verification, "pass");
  const skippedChecks = countVerificationChecks(run.verification, "skip");
  const checkTotal = run.verification?.checks?.length ?? 0;
  const topUnsupported = run.claims
    .filter((claim) => claim.status === "unsupported" || claim.status === "mixed" || claim.status === "contradicted")
    .slice(0, 4);
  const statusLabel = STATUS_LABEL[run.status_derived] ?? run.status_derived;
  const currentIndex = STATUS_INDEX[run.status_derived] ?? 0;
  const rawMismatch = Boolean(run.status_raw && run.status_raw !== run.status_derived);
  const writebackApproved =
    run.writebacks?.approved_for_writeback ?? run.governance?.approved_for_writeback ?? null;
  const context = run.context;
  const writebacks = run.writebacks;

  return (
    <section className="rv-trust-cockpit" aria-label="Trust cockpit" data-testid="trust-panel">
      <div className="rv-cockpit-header">
        <div className="rv-cockpit-header__title">
          <span className="rv-kicker">Trust Cockpit</span>
          <h1 data-testid="detail-run-id">{run.run_id}</h1>
        </div>
        <div className="rv-cockpit-header__badges">
          <span className={`it-pill ${statusTone(run)}`} data-testid="tp-lifecycle-badge">
            {statusLabel}
          </span>
          {rawMismatch && (
            <span className="it-chip orange" data-testid="raw-status-mismatch">
              Raw: {run.status_raw}
            </span>
          )}
          <span className="it-chip blue" data-testid="sensitivity-threshold-badge">
            Threshold: {run.sensitivity_threshold ?? "public"}
          </span>
          {writebackApproved != null && (
            <span className={`it-chip ${writebackApproved ? "green" : "orange"}`} data-testid="tp-governance-badge">
              Governance: {writebackApproved ? "approved" : "not approved"}
            </span>
          )}
          <span className="rv-cockpit-header__created">
            Created<br />
            <strong>{formatDateTime(run.created_at)}</strong>
          </span>
        </div>
      </div>

      <div className="rv-trust-grid">
        <aside className="rv-lifecycle-panel it-card" aria-label="Run lifecycle">
          <h2>Lifecycle</h2>
          <ol className="rv-lifecycle-list">
            {LIFECYCLE.map((stage, index) => {
              const complete = index <= currentIndex;
              const current = index === currentIndex;
              const blocked = stage.id === "verified" && run.verification?.present && run.verification.passed === false;
              return (
                <li
                  key={stage.id}
                  className={`rv-lifecycle-item${complete ? " rv-lifecycle-item--complete" : ""}${current ? " rv-lifecycle-item--current" : ""}${blocked ? " rv-lifecycle-item--blocked" : ""}`}
                >
                  <span className="rv-lifecycle-dot" aria-hidden="true" />
                  <div>
                    <strong>{stage.label}</strong>
                    {current && <span>{formatDateTime(run.created_at)}</span>}
                    {stage.id === "verified" && failedChecks > 0 && <span>{failedChecks} failed checks</span>}
                    {stage.id === "published" && !complete && <span>Pending</span>}
                  </div>
                </li>
              );
            })}
          </ol>
          <div className="rv-lifecycle-timeline">
            <TimelineStepper timeline={run.timeline} />
          </div>
        </aside>

        <main className="rv-cockpit-main">
          <section className="rv-verification-card it-card" aria-label="Verification" data-testid="cockpit-verification">
            <div className="rv-panel-heading">
              <div>
                <h2>Verification</h2>
                <p>{checkTotal > 0 ? `${checkTotal} checks evaluated` : "No verification bundle exported"}</p>
              </div>
              <button className="it-btn ghost sm" type="button" onClick={() => onOpenAudit?.()}>
                View audit
              </button>
            </div>
            <div className="rv-check-summary">
              <Metric label="Passed" value={passedChecks} tone="green" />
              <Metric label="Failed" value={failedChecks} tone="red" />
              <Metric label="Warnings" value={attention.warningChecks} tone="orange" />
              <Metric label="Skipped" value={skippedChecks} tone="neutral" />
            </div>
            <VerificationChecklist verification={run.verification} />
          </section>

          <section className="rv-claim-mix-card it-card" aria-label="Claim mix">
            <div className="rv-panel-heading">
              <div>
                <h2>Claim Mix</h2>
                <p>{getClaimTotal(run.claim_counts, run.claims)} total claims</p>
              </div>
            </div>
            <div className="rv-claim-mix-layout">
              <ClaimStatusDonut claimCounts={run.claim_counts} />
              <dl className="rv-claim-mix-dl">
                <MetricRow label="Supported" value={getSupportedTotal(run.claim_counts)} tone="green" />
                <MetricRow label="Inference" value={getInferenceTotal(run.claim_counts)} tone="blue" />
                <MetricRow label="Speculation" value={getSpeculationTotal(run.claim_counts)} tone="orange" />
                <MetricRow label="Redacted sources" value={attention.redactedSources} tone="red" />
              </dl>
            </div>
          </section>

          <section className="rv-risk-card it-card" aria-label="Top unsupported claims">
            <div className="rv-panel-heading">
              <div>
                <h2>Top Unsupported Claims</h2>
                <p>Claims that need source repair or reviewer attention</p>
              </div>
              <button className="it-btn ghost sm" type="button" onClick={() => onOpenAudit?.(topUnsupported[0]?.claim_id)}>
                Open queue
              </button>
            </div>
            {topUnsupported.length > 0 ? (
              <div className="rv-risk-list">
                {topUnsupported.map((claim) => (
                  <button
                    type="button"
                    key={claim.claim_id}
                    className="rv-risk-row"
                    onClick={() => onOpenAudit?.(claim.claim_id)}
                    data-testid={`cockpit-risk-${claim.claim_id}`}
                  >
                    <span>{claim.text}</span>
                    <span className={`it-chip ${claimTone(claim)}`}>{claim.status ?? "review"}</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="rv-muted">No unsupported, mixed, or contradicted claims are exported for this run.</p>
            )}
          </section>
        </main>

        <aside className="rv-context-stack" aria-label="Context and writeback">
          <ContextPanel
            title="Routing"
            rows={[
              ["Decision", context?.routing_decision?.decision ?? "Not exported"],
              ["Rationale", context?.routing_decision?.rationale ?? "Routing context is absent from this export."],
            ]}
          />
          <ContextPanel
            title="Research Brief"
            rows={[
              ["Objective", briefObjective(context?.research_brief_md)],
              ["Scope", context?.research_brief_md ? "Embedded in static export" : "Not exported"],
            ]}
          />
          <ContextPanel
            title="Swarm"
            rows={[
              ["Swarm", context?.swarm_plan?.swarm ?? "Not exported"],
              ["Agents", contextText(context?.swarm_plan?.agents)],
              ["Adapters", contextText(context?.swarm_plan?.adapters)],
            ]}
          />
          <ContextPanel
            title="Writeback"
            rows={[
              ["Status", writebackApproved == null ? "Not exported" : writebackApproved ? "Ready" : "Blocked"],
              ["Blocking", writebacks?.required_fix ?? (failedChecks > 0 ? `${failedChecks} verification failures` : "No blocker exported")],
              ["Targets", writebacks?.targets?.length ? `${writebacks.targets.length} target(s)` : "Not exported"],
            ]}
          />
          <ContextPanel
            title="Downstream Targets"
            rows={[
              ["Direct", writebacks?.targets?.map((target) => target.name ?? target.destination).filter(Boolean).join(", ") || "Not exported"],
              ["Propagation", writebackApproved ? "Ready" : "Blocked or unavailable"],
            ]}
          />
        </aside>
      </div>
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: "green" | "red" | "orange" | "neutral" }) {
  return (
    <div className={`rv-metric rv-metric--${tone}`}>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}

function MetricRow({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <>
      <dt>
        <span className={`rv-tone-dot rv-tone-dot--${tone}`} />
        {label}
      </dt>
      <dd>{value.toLocaleString()}</dd>
    </>
  );
}

function ContextPanel({ title, rows }: { title: string; rows: [string, string | number][] }) {
  return (
    <section className="rv-context-panel it-card" data-testid={`context-panel-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <h2>{title}</h2>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default TrustCockpit;
