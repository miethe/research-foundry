/**
 * CancelJobControl — ARLS-2.1 / 2.2 / 2.3 (P4.5 hardening, M2).
 *
 * Wires the previously-dead `useCancelAgentJob()` hook (useAgentJobs.ts:89)
 * into a visible cancel affordance for a running agent job. Before this
 * component existed, the hook had zero callers anywhere in the render tree
 * (FR-5/FR-6/FR-7 in the PRD).
 *
 * Mounting contract: only render this component when a job exists (e.g.
 * inside AgentsScreen's `{activeJob && (...)}` block). It calls
 * `useAgentJob()` and `useCancelAgentJob()` unconditionally at its own top
 * level per the rules of hooks — callers must NOT render it for a null jobId.
 *
 * ARLS-2.1: visible only for a cancellable job. "Cancellable" is the same
 * RUNNING_STATUSES set AgentJobEventPanel uses to decide whether the SSE
 * stream is active (queued / running / streaming) — imported from there so
 * the two surfaces can never disagree about which statuses are "running".
 * The *live* status (via useAgentJob, kept fresh by the query invalidation
 * below) takes priority over the caller-supplied `jobStatus` prop, so a job
 * that has already gone terminal on the server hides the control even if
 * the caller's local state hasn't caught up yet.
 *
 * ARLS-2.2: an explicit two-step confirm gates the dispatch. The first click
 * only arms a confirm/abort pair — cancelAgentJob() cannot fire without the
 * second, explicit click. Both buttons are plain <button> elements, so they
 * are keyboard-reachable (Tab + Enter/Space) with no extra wiring.
 *
 * ARLS-2.3: `useCancelAgentJob()`'s `onSuccess` (useAgentJobs.ts) already
 * invalidates `agentJobQueryKey(jobId)`. This component subscribes to that
 * same query via `useAgentJob(jobId)`, so once the invalidated query
 * refetches with a terminal status, `effectiveStatus` leaves
 * RUNNING_STATUSES and the control disappears on its own re-render — no
 * manual page refresh needed. On failure, `cancelMutation.isError` renders
 * an inline alert and the confirm step stays armed so the operator can
 * retry; a failed cancel never looks successful.
 */

import { useState } from "react";
import { useAgentJob, useCancelAgentJob } from "@/hooks/useAgentJobs";
import { RUNNING_STATUSES } from "./AgentJobEventPanel";

export interface CancelJobControlProps {
  /** The job this control cancels. */
  jobId: string;
  /**
   * Fallback status — typically the caller's last-known job status (e.g. the
   * launch response). Used until the live useAgentJob() query resolves, and
   * as a safety net if that query is disabled or still loading.
   */
  jobStatus: string;
}

export function CancelJobControl({ jobId, jobStatus }: CancelJobControlProps) {
  const [confirming, setConfirming] = useState(false);

  // Live status — refetches automatically once useCancelAgentJob's onSuccess
  // invalidates this same query key (ARLS-2.3).
  const jobQuery = useAgentJob(jobId);
  const cancelMutation = useCancelAgentJob();

  const effectiveStatus = jobQuery.data?.status ?? jobStatus;

  // ARLS-2.1: hidden entirely once the job is not in a cancellable state.
  if (!RUNNING_STATUSES.has(effectiveStatus)) return null;

  function handleCancelClick(): void {
    setConfirming(true);
  }

  function handleAbort(): void {
    setConfirming(false);
  }

  function handleConfirm(): void {
    // ARLS-2.2: cancelAgentJob() is dispatched ONLY from this handler, which
    // is only reachable after the confirm step is armed by handleCancelClick.
    cancelMutation.mutate(jobId, {
      onSuccess: () => setConfirming(false),
    });
  }

  return (
    <div className="rv-cancel-job" data-testid="cancel-job-control">
      {!confirming ? (
        <button
          type="button"
          className="it-btn danger sm"
          data-testid="cancel-job-btn"
          aria-label="Cancel agent job"
          onClick={handleCancelClick}
          disabled={cancelMutation.isPending}
        >
          Cancel Job
        </button>
      ) : (
        <div
          className="rv-cancel-job__confirm"
          role="group"
          aria-label="Confirm job cancellation"
        >
          <span className="rv-cancel-job__confirm-text">
            Cancel this job? This cannot be undone.
          </span>
          <button
            type="button"
            className="it-btn danger sm"
            data-testid="cancel-job-confirm-btn"
            aria-label="Confirm cancel agent job"
            onClick={handleConfirm}
            disabled={cancelMutation.isPending}
          >
            {cancelMutation.isPending ? "Cancelling…" : "Confirm Cancel"}
          </button>
          <button
            type="button"
            className="it-btn ghost sm"
            data-testid="cancel-job-abort-btn"
            aria-label="Keep job running"
            onClick={handleAbort}
            disabled={cancelMutation.isPending}
          >
            Never Mind
          </button>
        </div>
      )}

      {cancelMutation.isError && (
        <p className="rv-cancel-job__error" role="alert" data-testid="cancel-job-error">
          Failed to cancel job: {cancelMutation.error?.message ?? "unknown error"}
        </p>
      )}
    </div>
  );
}

export default CancelJobControl;
