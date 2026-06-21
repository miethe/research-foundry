/**
 * RunCard — per-run card for the RunListScreen.
 *
 * Renders:
 *   - Derived lifecycle badge (status_derived → verified / needs-review / failed / planned)
 *   - Sensitivity badge (when sensitivity is non-null)
 *   - Linked Projects badge (PRIMARY metadata, P5 DISP-001) — when linked_projects non-null
 *   - Tags chips (top 3 + overflow badge, P5 DISP-001) — when tags non-null
 *   - Claim counts (supported / inference / speculation)
 *   - Verification pass/fail indicator (when verification data present)
 *   - Governance verdict (when governance.approved_for_writeback present)
 *   - Optional schema-version mismatch badge (OQ-7: only when schema_version_mismatch: true)
 *
 * All optional fields degrade gracefully — no crash on partial data.
 * Uses RFRunSummary from useRunList() for the list view.
 *
 * R-P2: linked_projects/tags null/absent → nothing rendered; no console error.
 */

import type { RFRunSummary, RFStatusDerived, RFSensitivity } from "@/types/rf";
import { getRunBucket, titleFromSlug, type RunHealthBucket } from "@/lib/runs";

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Maps status_derived → the 3-state filter bucket used by filter tabs. */
export type RunFilterState = "verified" | "needs-review" | "planned";

// eslint-disable-next-line react-refresh/only-export-components
export function deriveFilterState(status: RFStatusDerived): RunFilterState {
  if (status === "verified" || status === "published") return "verified";
  if (
    status === "synthesized" ||
    status === "claim_mapped" ||
    status === "extracted" ||
    status === "sources_ingested"
  )
    return "needs-review";
  return "planned";
}

const STATUS_LABEL: Record<RFStatusDerived, string> = {
  planned:          "Planned",
  sources_ingested: "Sources",
  extracted:        "Extracted",
  claim_mapped:     "Mapped",
  synthesized:      "Synthesized",
  verified:         "Verified",
  published:        "Published",
};

const HEALTH_PILL_CLASS: Record<RunHealthBucket, string> = {
  verified:       "done",
  published:      "done",
  "needs-review": "progress",
  failed:         "blocked",
  planned:        "idle",
};

const SENSITIVITY_CHIP_CLASS: Record<RFSensitivity, string> = {
  public:           "",
  personal:         "blue",
  work_sensitive:   "orange",
  client_sensitive: "red",
};

const SENSITIVITY_LABEL: Record<RFSensitivity, string> = {
  public:           "Public",
  personal:         "Personal",
  work_sensitive:   "Work",
  client_sensitive: "Client",
};

// ── RunCard extended summary type (allows schema_version_mismatch) ─────────────

/** The canonical RFRunSummary plus the optional OQ-7 mismatch flag. */
export interface RunCardData extends RFRunSummary {
  /** OQ-7: optional mismatch flag emitted when the run.json was created with a
   *  different schema_version than the viewer expects. Badge renders only when true. */
  schema_version_mismatch?: boolean;
  /** Optional governance verdict — not in RFRunSummary; subset of RunExport. */
  governance_approved?: boolean | null;
  /** Whether verification passed — derived from the run detail; passed in for card display. */
  verification_passed?: boolean | null;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface RunCardProps {
  run: RunCardData;
  onClick?: (runId: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RunCard({ run, onClick }: RunCardProps) {
  const filterState = getRunBucket(run);
  const pillClass   = HEALTH_PILL_CLASS[filterState];
  const statusLabel = STATUS_LABEL[run.status_derived] ?? run.status_derived;

  // Human-readable title: prefer exported title field, fall back to slug-humanized run_id.
  const displayTitle = run.title ?? titleFromSlug(run.run_id) ?? run.run_id;

  // Claim counts — support both top-level aliases and long keys
  const cc = run.claim_counts;
  const supported   = cc?.supported   ?? cc?.claims_supported   ?? null;
  const inference   = cc?.inference   ?? cc?.claims_inference   ?? null;
  const speculation = cc?.speculation ?? cc?.claims_speculation ?? null;
  const total       = cc?.total       ?? cc?.claims_total       ?? null;

  const hasCounts = total != null;

  // Sensitivity
  const sens = run.sensitivity;
  const sensChip = sens ? SENSITIVITY_CHIP_CLASS[sens] : null;
  const sensLabel = sens ? SENSITIVITY_LABEL[sens] : null;

  // Verification
  const hasVerifPassed  = run.verification_passed != null;
  const verifPassed     = run.verification_passed;

  // Governance
  const hasGovApproval  = run.governance_approved != null;
  const govApproved     = run.governance_approved;

  // Schema mismatch (OQ-7)
  const schemaMismatch = run.schema_version_mismatch === true;

  // Linked Projects (PRIMARY metadata — P5 DISP-001)
  const linkedProjects = run.linked_projects?.length ? run.linked_projects : null;

  // Tags chips — top 3, overflow badge (P5 DISP-001)
  const tags = run.tags?.length ? run.tags : null;
  const visibleTags = tags?.slice(0, 3) ?? null;
  const overflowCount = tags ? Math.max(0, tags.length - 3) : 0;

  // Date display
  const createdLabel = run.created_at
    ? new Date(run.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <article
      className="rv-run-card it-card"
      role="button"
      tabIndex={0}
      aria-label={`Run ${displayTitle}, status: ${statusLabel}`}
      onClick={() => onClick?.(run.run_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.(run.run_id);
        }
      }}
      data-testid="run-card"
      data-run-id={run.run_id}
      data-filter-state={filterState}
    >
      {/* Header row: lifecycle badge + optional mismatch badge */}
      <div className="rv-run-card__header">
        <span className={`it-pill ${pillClass}`} data-testid="lifecycle-badge">
          {statusLabel}
        </span>

        {schemaMismatch && (
          <span
            className="it-chip orange rv-run-card__schema-badge"
            data-testid="schema-mismatch-badge"
            title="Schema version mismatch — this run was exported with a different schema version"
          >
            Schema mismatch
          </span>
        )}
      </div>

      {/* Title row: human-readable run title as primary label */}
      <div className="rv-run-card__title-row">
        <strong className="rv-run-card__title" data-testid="run-title">{displayTitle}</strong>
        <span className="rv-run-card__run-id" data-testid="run-id">{run.run_id}</span>
      </div>

      {/* Linked Projects — PRIMARY metadata (P5 DISP-001). Omit when null/absent. */}
      {linkedProjects && (
        <div className="rv-run-card__projects" data-testid="run-card-projects">
          {linkedProjects.map((project) => (
            <span key={project} className="it-chip blue rv-project-badge" data-testid="project-badge">
              {project}
            </span>
          ))}
        </div>
      )}

      {/* Tags chips — top 3 + overflow. Omit when null/absent. */}
      {visibleTags && (
        <div className="rv-run-card__tags" data-testid="run-card-tags">
          {visibleTags.map((tag) => (
            <span key={tag} className="it-chip rv-tag-chip" data-testid="tag-chip">
              {tag}
            </span>
          ))}
          {overflowCount > 0 && (
            <span className="it-chip rv-tag-chip rv-tag-chip--overflow" data-testid="tag-overflow">
              +{overflowCount}
            </span>
          )}
        </div>
      )}

      {/* Meta row: sensitivity + date + governance */}
      <div className="rv-run-card__meta">
        {sens && sensLabel && sensChip !== null && (
          <span
            className={`it-chip ${sensChip} rv-sensitivity-badge`}
            data-testid="sensitivity-badge"
            data-sensitivity={sens}
          >
            {sensLabel}
          </span>
        )}

        {hasGovApproval && (
          <span
            className={`it-chip ${govApproved ? "green" : "red"} rv-gov-badge`}
            data-testid="governance-badge"
          >
            {govApproved ? "Approved" : "Not approved"}
          </span>
        )}

        {createdLabel && (
          <span className="rv-run-card__date" data-testid="run-date">
            {createdLabel}
          </span>
        )}
      </div>

      {/* Claim counts */}
      {hasCounts && (
        <div className="rv-run-card__counts" data-testid="claim-counts">
          <span className="rv-count-item rv-count--supported" title="Supported claims">
            <span className="rv-count-dot" />
            {supported ?? 0}
          </span>
          <span className="rv-count-item rv-count--inference" title="Inference claims">
            <span className="rv-count-dot" />
            {inference ?? 0}
          </span>
          <span className="rv-count-item rv-count--speculation" title="Speculation claims">
            <span className="rv-count-dot" />
            {speculation ?? 0}
          </span>
          <span className="rv-count-total" title="Total claims">
            {total} total
          </span>
        </div>
      )}

      {/* Verification indicator */}
      {hasVerifPassed && (
        <div className="rv-run-card__verif" data-testid="verification-indicator">
          {verifPassed ? (
            <span className="rv-verif-pass">Verification passed</span>
          ) : (
            <span className="rv-verif-fail">Verification failed</span>
          )}
        </div>
      )}
    </article>
  );
}

export default RunCard;
