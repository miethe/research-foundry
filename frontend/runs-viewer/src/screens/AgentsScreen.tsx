/**
 * P4.5 Agents screen — job launch + policy gates + live event stream + evidence intake.
 *
 * Loopback-only surface: isAgentsLoopbackEnabled() must be true to reach this
 * screen (AppShell gates the nav entry). A direct navigation to /agents in
 * static mode renders the informational state below.
 */

import { useState } from "react";
import { useLocation } from "react-router-dom";
import { isAgentsLoopbackEnabled, useAgentJob } from "@/hooks/useAgentJobs";
import { AgentJobLaunchForm } from "@/components/Agents/AgentJobLaunchForm";
import { AgentJobEventPanel } from "@/components/Agents/AgentJobEventPanel";
import { CancelJobControl } from "@/components/Agents/CancelJobControl";
import { EvidenceIntakePanel } from "@/components/Agents/EvidenceIntakePanel";
import { PolicyGateSummary } from "@/components/Agents/PolicyGateSummary";
import type { AgentJobDetail } from "@/api/agentJobsClient";

interface AgentsLocationState {
  input_claim_ids?: string[];
  input_report_id?: string | null;
}

export function AgentsScreen() {
  if (!isAgentsLoopbackEnabled()) {
    return (
      <div className="rv-agents-static-info" role="status">
        <h1>Governed Agent Research</h1>
        <p>
          The Agents screen requires a running RF API server (loopback mode).
          Start <code>rf serve</code> and set{" "}
          <code>VITE_RUNS_FRONTEND_LOOPBACK_API=true</code> to use agent jobs.
        </p>
      </div>
    );
  }

  return <AgentsScreenLoopback />;
}

/**
 * ActiveJobPanel — the per-job event stream + cancel affordance.
 *
 * Mounted ONLY inside AgentsScreenLoopback's `{activeJob && (...)}` guard
 * (never unconditionally at the top of AgentsScreenLoopback). All 7 protected
 * `agents-*.test.tsx` files mock `@/hooks/useAgentJobs` with a narrow export
 * set that omits `useAgentJob`, and none of them ever let `activeJob` become
 * non-null (their mocked `useLaunchAgentJob().mutate` never invokes its
 * onSuccess callback) — so this component, and the `useAgentJob` call inside
 * it, never mount under any of those files' mocks. Same reasoning
 * CancelJobControl.tsx's docstring already documents and relies on; this
 * component follows it exactly rather than introducing a new exposure.
 *
 * M2-review fix — AC-M2-3 (live status reaches the event panel, not just the
 * cancel control): before this component existed, AgentJobEventPanel was
 * handed `activeJob.status` — a snapshot frozen at launch time — while only
 * CancelJobControl subscribed to the live `useAgentJob(jobId)` query that
 * useCancelAgentJob's onSuccess invalidates. A successful cancel therefore
 * updated CancelJobControl (which hid itself once the query resolved
 * terminal) but never reached AgentJobEventPanel, which kept rendering
 * "running" forever. This component calls `useAgentJob(jobId)` ONCE and
 * hands the resulting live status to both children, so a terminal
 * transition — delivered by the query, not a manually-passed prop — reaches
 * the panel exactly the way it already reached the cancel control.
 */
interface ActiveJobPanelProps {
  activeJob: AgentJobDetail;
}

function ActiveJobPanel({ activeJob }: ActiveJobPanelProps) {
  const jobId = activeJob.agent_job_id;
  // Live status — the SAME query key useCancelAgentJob's onSuccess
  // invalidates (agentJobQueryKey(jobId) in useAgentJobs.ts). Falls back to
  // the launch-time snapshot until the query resolves (first render /
  // disabled-in-static-mode / still loading).
  const jobQuery = useAgentJob(jobId);
  const effectiveStatus = jobQuery.data?.status ?? activeJob.status;

  return (
    <>
      <AgentJobEventPanel jobId={jobId} jobStatus={effectiveStatus} />
      <CancelJobControl jobId={jobId} jobStatus={effectiveStatus} />
    </>
  );
}

/**
 * Inner component — only rendered when loopback is enabled.
 * Hooks live here to satisfy the rules-of-hooks invariant (no hook after
 * conditional returns in the outer shell).
 */
function AgentsScreenLoopback() {
  const location = useLocation();
  const state = (location.state ?? {}) as AgentsLocationState;
  const [activeJob, setActiveJob] = useState<AgentJobDetail | null>(null);

  return (
    <div className="rv-agents">
      <h1 className="rv-agents__title">Governed Agent Research</h1>

      <section className="rv-agents__policy" aria-label="Policy gates">
        <PolicyGateSummary job={activeJob} />
      </section>

      <section className="rv-agents__launch" aria-label="Launch agent job">
        <AgentJobLaunchForm
          inputClaimIds={state.input_claim_ids ?? null}
          inputReportId={state.input_report_id ?? null}
          onLaunchSuccess={(job) => setActiveJob(job)}
        />
      </section>

      {activeJob && (
        // CONFIRM-LEAK-01 (M2 review; same class as M1's JOBID-LEAK-01):
        // keying this subtree by jobId makes React unmount/remount the whole
        // job-scoped subtree — including CancelJobControl's `confirming`
        // state and ActiveJobPanel's own live-status query — on every job
        // transition, instead of reusing the previous job's component
        // instances with updated props. Fixing this at the call site (here)
        // rather than inside CancelJobControl closes the defect CLASS: any
        // future per-job child mounted in this slot inherits the same
        // guarantee for free, with no per-component reset logic required.
        <section
          className="rv-agents__events"
          aria-label="Live event stream"
          key={`events-${activeJob.agent_job_id}`}
        >
          <ActiveJobPanel activeJob={activeJob} />
        </section>
      )}

      {activeJob && (
        // Same CONFIRM-LEAK-01 keying applied to the intake subtree:
        // EvidenceIntakePanel carries its own per-job `selectedIds`/`rejected`
        // state (untouched by this fix cycle) that would otherwise survive a
        // relaunch across this slot the same way `confirming` did.
        <section
          className="rv-agents__intake"
          aria-label="Evidence intake"
          key={`intake-${activeJob.agent_job_id}`}
        >
          <EvidenceIntakePanel
            jobId={activeJob.agent_job_id}
            onAccepted={() => {
              // No-op: job detail re-fetched via React Query on acceptance
            }}
          />
        </section>
      )}
    </div>
  );
}

export default AgentsScreen;
