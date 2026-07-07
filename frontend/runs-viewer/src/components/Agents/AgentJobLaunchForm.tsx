/**
 * AgentJobLaunchForm — P4.5 UI-5.3.
 *
 * Controlled form for launching a governed agent job.
 *
 * AC-1.1: Context pre-population — when inputClaimIds/inputReportId are
 *   provided (from React Router location state set by ClaimAuditWorkbench /
 *   ReportOverlay in Batch 3), the Context section is read-only. When absent,
 *   show manual text inputs.
 *
 * AC-4.1: Explicit acknowledgment checkbox required — Launch button remains
 *   disabled until the governance acknowledgment is checked AND all required
 *   fields (provider, model, tools, sensitivity) are filled.
 *
 * AC-4.4: Governance rejection (HTTP 422 / 400) — shows violations banner
 *   with rule_id + message; form NOT cleared; PolicyGateSummary remains
 *   visible in AgentsScreen.
 */

import { useState } from "react";
import {
  AgentJobsApiError,
  isGovernanceRejection,
} from "@/api/agentJobsClient";
import type { AgentJobDetail, LaunchAgentJobRequest } from "@/api/agentJobsClient";
import { useLaunchAgentJob } from "@/hooks/useAgentJobs";

export interface AgentJobLaunchFormProps {
  /** Pre-populated from route state (AC-1.1) — null = manual context picker mode */
  inputClaimIds?: string[] | null;
  inputReportId?: string | null;
  /** Called on successful launch with the new job detail */
  onLaunchSuccess: (job: AgentJobDetail) => void;
}

interface FormState {
  // Manual context inputs (only shown when inputClaimIds/inputReportId are absent)
  manualClaimIds: string;
  manualReportId: string;
  // Core fields
  provider: string;
  model: string;
  toolsRaw: string;    // comma-separated, e.g. "search_web,extract_claims"
  budgetUsd: string;   // empty string = no budget
  sensitivity: string;
  // Governance acknowledgment
  acknowledged: boolean;
}

const DEFAULT_STATE: FormState = {
  manualClaimIds: "",
  manualReportId: "",
  provider: "claude",
  model: "",
  toolsRaw: "",
  budgetUsd: "",
  sensitivity: "public",
  acknowledged: false,
};

function parseTools(raw: string): string[] {
  return raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function AgentJobLaunchForm({
  inputClaimIds,
  inputReportId,
  onLaunchSuccess,
}: AgentJobLaunchFormProps) {
  const [form, setForm] = useState<FormState>(DEFAULT_STATE);
  const mutation = useLaunchAgentJob();

  const isContextPrePopulated =
    (inputClaimIds != null && inputClaimIds.length > 0) || inputReportId != null;

  const parsedTools = parseTools(form.toolsRaw);

  const isFormValid =
    form.provider.trim() !== "" &&
    form.model.trim() !== "" &&
    parsedTools.length > 0 &&
    form.sensitivity.trim() !== "" &&
    form.acknowledged;

  // Governance rejection discriminator (AC-4.4)
  const apiError =
    mutation.error instanceof AgentJobsApiError ? mutation.error : null;
  const governanceRejection =
    apiError != null && isGovernanceRejection(apiError.body) ? apiError.body : null;
  const genericError =
    mutation.isError && governanceRejection == null
      ? (mutation.error?.message ?? "An unexpected error occurred.")
      : null;

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isFormValid) return;

    const claimIds: string[] | undefined =
      inputClaimIds != null && inputClaimIds.length > 0
        ? inputClaimIds
        : form.manualClaimIds.trim()
          ? parseTools(form.manualClaimIds) // reuse split-and-trim
          : undefined;

    const reportId: string | null =
      inputReportId != null
        ? inputReportId
        : form.manualReportId.trim() || null;

    // Build conformant LaunchJobBody per openapi.json.
    // tools → policy_snapshot.allowed_tools; sensitivity → policy_snapshot.data_scopes.
    const req: LaunchAgentJobRequest = {
      provider: form.provider.trim(),
      model_profile: form.model.trim(),
      request_kind: "research",
      policy_snapshot: {
        allowed_tools: parsedTools,
        data_scopes: [form.sensitivity],
      },
      ...(claimIds !== undefined && { input_claim_ids: claimIds }),
      ...(reportId !== null && { input_report_id: reportId }),
      budget_usd: form.budgetUsd.trim() ? parseFloat(form.budgetUsd) : null,
    };

    mutation.mutate(req, {
      onSuccess: (job) => {
        onLaunchSuccess(job);
      },
    });
  }

  return (
    <div className="rv-launch-form__wrapper">
      {/* Governance rejection banner (AC-4.4) */}
      {governanceRejection && (
        <div
          className="rv-launch-form__rejection"
          role="alert"
          data-testid="launch-governance-rejection"
        >
          <strong>Governance Rejection</strong>
          <ul>
            {governanceRejection.violations.map((v) => (
              <li key={v.rule_id}>
                [{v.rule_id}] {v.severity}: {v.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Generic error banner */}
      {genericError && (
        <div
          className="rv-launch-form__error"
          role="alert"
          data-testid="launch-generic-error"
        >
          {genericError}
        </div>
      )}

      <form
        className="rv-launch-form"
        onSubmit={handleSubmit}
        data-testid="launch-form"
        aria-label="Launch agent job"
      >
        {/* ── Context section (AC-1.1) ────────────────────────────────────── */}
        <section className="rv-launch-form__section" aria-label="Research context">
          <p className="rv-launch-form__section-title">Context</p>
          {isContextPrePopulated ? (
            <div className="rv-launch-form__context-readonly" data-testid="launch-context-readonly">
              {inputClaimIds != null && inputClaimIds.length > 0 && (
                <div>
                  <p className="rv-launch-form__context-label">Claim IDs</p>
                  <span>{inputClaimIds.join(", ")}</span>
                </div>
              )}
              {inputReportId != null && (
                <div>
                  <p className="rv-launch-form__context-label">Report ID</p>
                  <span>{inputReportId}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="rv-launch-form__fields">
              <div className="rv-launch-form__field rv-launch-form__field--full">
                <label className="rv-launch-form__label" htmlFor="launch-claim-ids">
                  Claim IDs (comma-separated)
                </label>
                <input
                  id="launch-claim-ids"
                  name="manual_claim_ids"
                  type="text"
                  className="rv-launch-form__input"
                  placeholder="clm_001, clm_002"
                  value={form.manualClaimIds}
                  onChange={(e) => setField("manualClaimIds", e.target.value)}
                />
              </div>
              <div className="rv-launch-form__field rv-launch-form__field--full">
                <label className="rv-launch-form__label" htmlFor="launch-report-id">
                  Report ID (optional)
                </label>
                <input
                  id="launch-report-id"
                  name="manual_report_id"
                  type="text"
                  className="rv-launch-form__input"
                  placeholder="rf_run_..."
                  value={form.manualReportId}
                  onChange={(e) => setField("manualReportId", e.target.value)}
                />
              </div>
            </div>
          )}
        </section>

        {/* ── Provider / Model / Tools / Budget / Sensitivity ─────────────── */}
        <section className="rv-launch-form__section" aria-label="Agent configuration">
          <p className="rv-launch-form__section-title">Configuration</p>
          <div className="rv-launch-form__fields">
            <div className="rv-launch-form__field">
              <label className="rv-launch-form__label" htmlFor="launch-provider">
                Provider <span aria-hidden="true">*</span>
              </label>
              <select
                id="launch-provider"
                name="provider"
                className="rv-launch-form__select"
                value={form.provider}
                onChange={(e) => setField("provider", e.target.value)}
                required
              >
                <option value="claude">claude</option>
                <option value="openai">openai</option>
              </select>
            </div>

            <div className="rv-launch-form__field">
              <label className="rv-launch-form__label" htmlFor="launch-model">
                Model <span aria-hidden="true">*</span>
              </label>
              <input
                id="launch-model"
                name="model"
                type="text"
                className="rv-launch-form__input"
                placeholder="claude-sonnet-4-6"
                value={form.model}
                onChange={(e) => setField("model", e.target.value)}
                required
              />
            </div>

            <div className="rv-launch-form__field rv-launch-form__field--full">
              <label className="rv-launch-form__label" htmlFor="launch-tools">
                Tools <span aria-hidden="true">*</span>
              </label>
              <input
                id="launch-tools"
                name="tools"
                type="text"
                className="rv-launch-form__input"
                placeholder="search_web, extract_claims"
                value={form.toolsRaw}
                onChange={(e) => setField("toolsRaw", e.target.value)}
                required
              />
            </div>

            <div className="rv-launch-form__field">
              <label className="rv-launch-form__label" htmlFor="launch-budget">
                Budget USD (optional)
              </label>
              <input
                id="launch-budget"
                name="budget_usd"
                type="number"
                min="0"
                step="0.01"
                className="rv-launch-form__input"
                placeholder="10.00"
                value={form.budgetUsd}
                onChange={(e) => setField("budgetUsd", e.target.value)}
              />
            </div>

            <div className="rv-launch-form__field">
              <label className="rv-launch-form__label" htmlFor="launch-sensitivity">
                Sensitivity <span aria-hidden="true">*</span>
              </label>
              <select
                id="launch-sensitivity"
                name="sensitivity"
                className="rv-launch-form__select"
                value={form.sensitivity}
                onChange={(e) => setField("sensitivity", e.target.value)}
                required
              >
                <option value="public">public</option>
                <option value="internal">internal</option>
                <option value="restricted">restricted</option>
              </select>
            </div>
          </div>
        </section>

        {/* ── Governance acknowledgment (AC-4.1) ──────────────────────────── */}
        <section className="rv-launch-form__section" aria-label="Governance acknowledgment">
          <label className="rv-launch-form__acknowledge">
            <input
              type="checkbox"
              name="acknowledged"
              checked={form.acknowledged}
              onChange={(e) => setField("acknowledged", e.target.checked)}
              data-testid="launch-acknowledge"
              aria-describedby="launch-acknowledge-label"
            />
            <span id="launch-acknowledge-label" className="rv-launch-form__acknowledge-label">
              I have reviewed the governance gates above and consent to this launch
            </span>
          </label>
        </section>

        {/* ── Submit ───────────────────────────────────────────────────────── */}
        <div className="rv-launch-form__footer">
          <button
            type="submit"
            className="it-btn agent"
            disabled={!isFormValid || mutation.isPending}
            data-testid="launch-submit"
            aria-label="Launch agent job"
          >
            {mutation.isPending ? "Launching…" : "Launch Agent Job"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default AgentJobLaunchForm;
