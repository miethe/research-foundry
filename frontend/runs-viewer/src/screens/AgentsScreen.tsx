/**
 * P4.5 Agents screen — job launch + policy gates + live event stream + evidence intake.
 *
 * Loopback-only surface: isAgentsLoopbackEnabled() must be true to reach this
 * screen (AppShell gates the nav entry). A direct navigation to /agents in
 * static mode renders the informational state below.
 */

import { useState } from "react";
import { useLocation } from "react-router-dom";
import { isAgentsLoopbackEnabled } from "@/hooks/useAgentJobs";
import { AgentJobLaunchForm } from "@/components/Agents/AgentJobLaunchForm";
import { AgentJobEventPanel } from "@/components/Agents/AgentJobEventPanel";
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
        <section className="rv-agents__events" aria-label="Live event stream">
          <AgentJobEventPanel
            jobId={activeJob.agent_job_id}
            jobStatus={activeJob.status}
          />
        </section>
      )}

      {activeJob && (
        <section className="rv-agents__intake" aria-label="Evidence intake">
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
