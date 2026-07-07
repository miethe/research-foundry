/**
 * EvidenceIntakePanel — P4.5 UI-5.6.
 *
 * Renders staged artifacts from a completed agent job and allows the
 * researcher to selectively accept them into the catalog.
 *
 * SECURITY (defense-in-depth, AC-3.5 / exit-7 HUMAN_REVIEW path):
 *   This is the ONLY code path that promotes staged artifacts to the catalog.
 *   "Catalogued" state is reached ONLY when useAcceptAgentJobArtifacts.mutate()
 *   completes successfully. No variable, state update, or render branch in this
 *   file sets catalog-implying state without that API call completing.
 *
 * AC-3.5 resilience: claim_proposal items whose source_candidates is
 *   missing (undefined) or null render an "incomplete proposal — review
 *   before accepting" warning badge rather than crashing or being silently
 *   omitted.
 *
 * Job history: listAgentJobs does NOT exist in agentJobsClient.ts (no
 *   list-all endpoint has been implemented yet). JobHistoryList renders a
 *   placeholder stub rather than an empty live query.
 */

import { useState } from "react";
import {
  useAgentJobArtifacts,
  useAcceptAgentJobArtifacts,
} from "@/hooks/useAgentJobs";
import type { AcceptResponse, AgentJobArtifact } from "@/api/agentJobsClient";

// ── Helpers ──────────────────────────────────────────────────────────────────

function truncateArtifactId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 10)}…`; // …
}

/**
 * AC-3.5: A claim_proposal is incomplete when source_candidates is absent
 * (undefined) or null. An empty array is NOT incomplete — the backend may
 * emit an empty array for a valid proposal with no candidates yet staged.
 */
function isIncompleteProposal(artifact: AgentJobArtifact): boolean {
  return (
    artifact.artifact_kind === "claim_proposal" &&
    artifact.source_candidates == null
  );
}

// ── Job history stub ─────────────────────────────────────────────────────────

/**
 * JobHistoryList — stub sub-component.
 *
 * listAgentJobs is not implemented in agentJobsClient.ts (no GET /api/agent-jobs
 * list endpoint exists yet). Renders a "coming soon" placeholder until the
 * endpoint ships.
 */
function JobHistoryList() {
  return (
    <div
      className="rv-intake-panel__history"
      data-testid="intake-job-history"
      aria-label="Previous agent jobs"
    >
      <p className="rv-intake-panel__history-title">Job History</p>
      <p
        className="rv-intake-panel__history-placeholder"
        data-testid="intake-job-history-placeholder"
      >
        Job history coming soon
      </p>
    </div>
  );
}

// ── Artifact row ─────────────────────────────────────────────────────────────

interface ArtifactItemProps {
  artifact: AgentJobArtifact;
  selected: boolean;
  onToggle: (artifactId: string) => void;
}

function ArtifactItem({ artifact, selected, onToggle }: ArtifactItemProps) {
  const incomplete = isIncompleteProposal(artifact);
  return (
    <li
      className={`rv-intake-panel__item${incomplete ? " rv-intake-panel__item--incomplete" : ""}`}
      data-testid={`intake-artifact-${artifact.artifact_id}`}
      data-incomplete={incomplete ? "true" : "false"}
    >
      <label className="rv-intake-panel__item-label">
        <input
          type="checkbox"
          className="rv-intake-panel__item-checkbox"
          data-testid={`intake-checkbox-${artifact.artifact_id}`}
          checked={selected}
          onChange={() => onToggle(artifact.artifact_id)}
          aria-label={`Select artifact ${artifact.artifact_id}`}
        />
        <span
          className="rv-intake-panel__kind-badge"
          data-testid={`intake-kind-badge-${artifact.artifact_id}`}
        >
          {artifact.artifact_kind}
        </span>
        <span
          className="rv-intake-panel__artifact-id"
          data-testid={`intake-artifact-id-${artifact.artifact_id}`}
          title={artifact.artifact_id}
        >
          {truncateArtifactId(artifact.artifact_id)}
        </span>
        {incomplete && (
          <span
            className="rv-intake-panel__warning-badge"
            data-testid={`intake-incomplete-badge-${artifact.artifact_id}`}
            role="alert"
            aria-label="Incomplete proposal — review before accepting"
          >
            incomplete proposal — review before accepting
          </span>
        )}
      </label>
    </li>
  );
}

// ── EvidenceIntakePanel ───────────────────────────────────────────────────────

export interface EvidenceIntakePanelProps {
  jobId: string;
  /** Called on successful acceptance with the AcceptResponse summary. */
  onAccepted?: (summary: AcceptResponse) => void;
}

export function EvidenceIntakePanel({ jobId, onAccepted }: EvidenceIntakePanelProps) {
  const { data: artifacts, isLoading, isError } = useAgentJobArtifacts(jobId);
  // SECURITY: acceptMutation is the SOLE mechanism that promotes staged
  // artifacts to catalogued state. No branch in this component writes to any
  // catalog-implying state without this mutation completing successfully.
  const acceptMutation = useAcceptAgentJobArtifacts();

  // selectedIds: set of artifact_ids the user has chosen to accept.
  // Default is empty — the researcher must actively select each artifact.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  // rejected: true when the researcher clicks "Reject all" without accepting.
  const [rejected, setRejected] = useState(false);

  function toggleSelect(artifactId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  }

  function handleAccept() {
    if (selectedIds.size === 0) return;
    // Backend accepts ALL staged artifacts for the job when POST /accept is called.
    // Selective acceptance is deferred to P5. Checkboxes above are for user review only.
    acceptMutation.mutate(
      { jobId, req: {} },
      {
        onSuccess: (response) => {
          onAccepted?.(response);
        },
      },
    );
  }

  function handleReject() {
    setRejected(true);
    setSelectedIds(new Set());
  }

  // ── Accepted success state (SECURITY: only rendered via acceptMutation.isSuccess) ──
  if (acceptMutation.isSuccess) {
    const summary = acceptMutation.data;
    return (
      <div
        className="rv-intake-panel rv-intake-panel--accepted"
        data-testid="intake-panel"
        aria-label="Evidence intake — accepted"
      >
        <p
          className="rv-intake-panel__success"
          data-testid="intake-accepted-summary"
        >
          Accepted{" "}
          <span data-testid="intake-accepted-count">
            {summary.accepted_artifact_count}
          </span>{" "}
          artifact{summary.accepted_artifact_count !== 1 ? "s" : ""} — acceptance
          ID:{" "}
          <code data-testid="intake-acceptance-id">{summary.acceptance_id}</code>
        </p>
        <JobHistoryList />
      </div>
    );
  }

  // ── Rejected / dismissed state ────────────────────────────────────────────
  if (rejected) {
    return (
      <div
        className="rv-intake-panel rv-intake-panel--rejected"
        data-testid="intake-panel"
        aria-label="Evidence intake — rejected"
      >
        <p
          className="rv-intake-panel__rejected"
          data-testid="intake-rejected-message"
        >
          No artifacts accepted for this job.
        </p>
        <JobHistoryList />
      </div>
    );
  }

  // ── Primary state: review + accept/reject ─────────────────────────────────
  return (
    <div
      className="rv-intake-panel"
      data-testid="intake-panel"
      aria-label="Evidence intake"
    >
      <p className="rv-intake-panel__title">Review Staged Artifacts</p>

      {isLoading && (
        <p
          className="rv-intake-panel__loading"
          data-testid="intake-loading"
          aria-live="polite"
        >
          Loading artifacts…
        </p>
      )}

      {isError && (
        <p
          className="rv-intake-panel__error"
          data-testid="intake-error"
          role="alert"
        >
          Failed to load artifacts. Please try again.
        </p>
      )}

      {/* Accept mutation error — displayed above the action row */}
      {acceptMutation.isError && (
        <p
          className="rv-intake-panel__error"
          data-testid="intake-accept-error"
          role="alert"
        >
          Accept failed: {acceptMutation.error?.message ?? "Unknown error"}
        </p>
      )}

      {artifacts && artifacts.length === 0 && (
        <p
          className="rv-intake-panel__empty"
          data-testid="intake-empty"
        >
          No staged artifacts for this job.
        </p>
      )}

      {artifacts && artifacts.length > 0 && (
        <ul
          className="rv-intake-panel__list"
          data-testid="intake-artifact-list"
          aria-label="Staged artifacts"
        >
          {artifacts.map((artifact) => (
            <ArtifactItem
              key={artifact.artifact_id}
              artifact={artifact}
              selected={selectedIds.has(artifact.artifact_id)}
              onToggle={toggleSelect}
            />
          ))}
        </ul>
      )}

      <div className="rv-intake-panel__actions" data-testid="intake-actions">
        <button
          type="button"
          className="it-btn agent"
          data-testid="intake-accept-btn"
          disabled={selectedIds.size === 0 || acceptMutation.isPending}
          onClick={handleAccept}
          aria-label="Accept all staged artifacts"
        >
          {acceptMutation.isPending ? "Accepting…" : "Accept all staged"}
        </button>
        <p className="rv-intake-panel__p5-note">
          (Backend accepts all staged artifacts; selective acceptance in P5)
        </p>
        <button
          type="button"
          className="rv-intake-panel__reject-btn"
          data-testid="intake-reject-btn"
          onClick={handleReject}
          aria-label="Reject all — do not accept any artifacts"
        >
          Reject all / don&apos;t accept
        </button>
      </div>

      <JobHistoryList />
    </div>
  );
}

export default EvidenceIntakePanel;
