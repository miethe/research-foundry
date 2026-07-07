/**
 * PolicyGateSummary — P4.5 UI-5.3 (updated UI-5.7).
 *
 * Renders the policy_snapshot from an AgentJobDetail above the launch form
 * so the researcher can see governance gates before and after launching.
 *
 * AC-4.5: ALL sub-fields of PolicySnapshot may be null — render "not recorded"
 * per field, never crash. job.status is rendered with an "(unrecognized)" badge
 * when the value is not in the known status set (UI-5.7 R-P2).
 *
 * D12: workspace_id and created_by are always null until P5 auth; render "not recorded".
 */

import type { AgentJobDetail } from "@/api/agentJobsClient";

export interface PolicyGateSummaryProps {
  /** null = show "No active job" state; once a job is launched, pass its detail */
  job: AgentJobDetail | null;
}

const NOT_RECORDED = "not recorded";

/**
 * Known job status values — any string outside this set is considered
 * unrecognized and renders with an "(unrecognized)" badge (UI-5.7 R-P2).
 */
const KNOWN_JOB_STATUSES = new Set([
  "queued",
  "running",
  "streaming",
  "completed",
  "failed",
  "cancelled",
]);

function toolsLabel(tools: string[] | null | undefined): string {
  if (!tools || tools.length === 0) return NOT_RECORDED;
  return tools.join(", ");
}

function budgetLabel(budget: number | null | undefined): string {
  if (budget == null) return NOT_RECORDED;
  return `$${budget.toFixed(2)} USD`;
}

export function PolicyGateSummary({ job }: PolicyGateSummaryProps) {
  if (!job) {
    return (
      <div
        className="rv-policy-gate rv-policy-gate--empty"
        data-testid="policy-gate-summary"
        aria-label="Policy gates — no active job"
      >
        <p className="rv-policy-gate__placeholder">Launch a job to see policy gates</p>
      </div>
    );
  }

  const snap = job.policy_snapshot;

  return (
    <div className="rv-policy-gate" data-testid="policy-gate-summary" aria-label="Policy gates">
      <p className="rv-policy-gate__header">Policy Gates</p>
      <table className="rv-policy-gate__table">
        <tbody>
          <tr>
            <th scope="row">Provider</th>
            <td data-testid="policy-gate-value-provider">
              {snap?.provider ?? NOT_RECORDED}
            </td>
          </tr>
          <tr>
            <th scope="row">Model</th>
            <td data-testid="policy-gate-value-model">
              {snap?.model ?? NOT_RECORDED}
            </td>
          </tr>
          <tr>
            <th scope="row">Tools</th>
            <td data-testid="policy-gate-value-tools">
              {toolsLabel(snap?.tools)}
            </td>
          </tr>
          <tr>
            <th scope="row">Budget</th>
            <td data-testid="policy-gate-value-budget">
              {budgetLabel(snap?.budget_usd)}
            </td>
          </tr>
          <tr>
            <th scope="row">Sensitivity</th>
            <td data-testid="policy-gate-value-sensitivity">
              {snap?.sensitivity ?? NOT_RECORDED}
            </td>
          </tr>
          <tr>
            <th scope="row">Status</th>
            <td data-testid="policy-gate-value-status">
              {/* Always render raw string; add badge for unrecognized values (UI-5.7 R-P2) */}
              <code>{job.status}</code>
              {!KNOWN_JOB_STATUSES.has(job.status) && (
                <span
                  className="rv-policy-gate__badge rv-policy-gate__badge--unrecognized"
                  data-testid="policy-gate-status-unrecognized"
                  aria-label="Status not recognized by this version of the viewer"
                >
                  {" "}(unrecognized)
                </span>
              )}
            </td>
          </tr>
          <tr>
            <th scope="row">Workspace</th>
            <td data-testid="policy-gate-value-workspace">
              {/* D12: always null pre-P5 */}
              {job.workspace_id ?? NOT_RECORDED}
            </td>
          </tr>
          <tr>
            <th scope="row">Created by</th>
            <td data-testid="policy-gate-value-created-by">
              {/* D12: always null until P5 auth */}
              {job.created_by ?? NOT_RECORDED}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default PolicyGateSummary;
