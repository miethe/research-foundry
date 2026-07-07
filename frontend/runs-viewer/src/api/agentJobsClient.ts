/**
 * RF Agent Jobs API Client — P4.5.
 *
 * LOOPBACK-ONLY: Agent job operations (launch, cancel, accept, stream) only
 * make sense against a live RF API server. Unlike api/client.ts (read-only,
 * dual-mode) and api/reportsClient.ts (dual-mode with static demo fallback),
 * this module has NO static-mode read path.
 *
 * Every exported function throws AgentsStaticModeError if isLoopbackEnabled()
 * is false. AgentsScreen gates on isAgentsLoopbackEnabled() before rendering
 * any interactive surface, so these throws are a safety net only.
 *
 * SSE events (GET /api/agent-jobs/{id}/events) are consumed via EventSource
 * directly in hooks/useAgentJobs.ts — not here. SSE payloads arrive
 * already-redacted by the server (P4.4 redact_payload gate); never log or
 * display raw payload values.
 *
 * Error discrimination (AC-4.4): governance rejections (HTTP 422 / 400) are
 * thrown as AgentJobsApiError with a GovernanceRejection-shaped body. Use
 * isGovernanceRejection(err.body) in callers to distinguish them.
 */

import { getLoopbackAuthHeaders, getLoopbackBase, isLoopbackEnabled } from "./client";

export { isLoopbackEnabled as isAgentsLoopbackEnabled };

// ── Error classes ─────────────────────────────────────────────────────────────

export class AgentsStaticModeError extends Error {
  constructor(action: string) {
    super(
      `Agent Jobs require a running RF API server (loopback mode): cannot ${action}. ` +
        `Start rf serve and set VITE_RUNS_FRONTEND_LOOPBACK_API=true to use agent jobs.`,
    );
    this.name = "AgentsStaticModeError";
  }
}

export class AgentJobsApiError extends Error {
  readonly status: number;
  readonly body: unknown;
  constructor(method: string, path: string, status: number, statusText: string, body: unknown) {
    super(`Agent Jobs API ${method} ${path} failed: ${status} ${statusText}`);
    this.name = "AgentJobsApiError";
    this.status = status;
    this.body = body;
  }
}

// ── Domain types (API-4.6 contract) ──────────────────────────────────────────

/** AC-4.4: Governance policy violation from launch rejection. */
export interface PolicyViolation {
  rule_id: string;
  severity: string;
  message: string;
  detail?: string | null;
}

/**
 * AC-4.4: Body shape for HTTP 422 (exit_code=3, GOVERNANCE block)
 * or HTTP 400 (exit_code=7, HUMAN_REVIEW) from POST /api/agent-jobs.
 * Discriminated on error: "governance_rejected".
 */
export interface GovernanceRejection {
  error: "governance_rejected";
  exit_code: number; // 3 = GOVERNANCE, 7 = HUMAN_REVIEW
  violations: PolicyViolation[];
}

/**
 * AC-4.5: policy_snapshot sub-fields are nullable — render "not recorded" for null.
 * All sub-fields explicitly nullable per D12 and AC-4.5 contract.
 */
export interface PolicySnapshot {
  provider?: string | null;
  model?: string | null;
  tools?: string[] | null;
  budget_usd?: number | null;
  sensitivity?: string | null;
}

/**
 * AC-4.5: Full agent job detail including policy_snapshot.
 * workspace_id and created_by are always nullable (D12 — auth deferred P5).
 * status is kept as string so future unknown statuses degrade gracefully.
 */
export interface AgentJobDetail {
  agent_job_id: string;
  status: string; // open-ended — unknown values must render gracefully
  created_at: string;
  updated_at: string;
  workspace_id: string | null; // D12: always nullable until P5 auth
  created_by: string | null; // D12: always nullable until P5 auth
  policy_snapshot: PolicySnapshot | null;
  exit_code?: number | null;
  error_message?: string | null;
}

/**
 * POST /api/agent-jobs — launch request body.
 * Aligns to backend LaunchJobBody (openapi.json confirmed).
 * tools/sensitivity are nested inside policy_snapshot, not top-level.
 */
export interface LaunchAgentJobRequest {
  provider: string;
  model_profile: string;          // backend field name (was "model")
  request_kind: string;           // e.g. "research"
  policy_snapshot: {
    allowed_tools: string[];      // was top-level "tools"
    data_scopes: string[];        // was top-level "sensitivity" (wrapped in array)
    [key: string]: unknown;
  };
  input_claim_ids?: string[];
  input_report_id?: string | null;
  budget_usd?: number | null;
  workspace_id?: string | null;
  created_by?: string | null;
}

/**
 * AC-3.5: Staged artifact from GET /api/agent-jobs/{id}/artifacts.
 * artifact_kind is fully typed (no `any`). source_candidates missing =
 * render "incomplete proposal" badge in EvidenceIntakePanel.
 */
export interface AgentJobArtifact {
  artifact_id: string;
  artifact_kind: string; // fully typed per AC-3.5 — no any escape hatch
  accepted: boolean;
  source_candidates?: unknown[] | null; // absent → "incomplete proposal" badge
  [key: string]: unknown;
}

/**
 * AC-2.3: SSE event frame shape (already-redacted by server P4.4).
 * payload is Record<string, unknown> — never log or display raw values.
 */
export interface AgentJobEvent {
  event_type: string;
  payload: Record<string, unknown>; // pre-redacted; never surface raw values
  sequence?: number | null;
}

/**
 * POST /api/agent-jobs/{id}/accept — request body.
 * Aligns to backend AcceptJobBody: only accepted_by + notes.
 * Backend accepts ALL staged artifacts for the job; selective acceptance is P5.
 */
export interface AcceptRequest {
  accepted_by?: string | null;
  notes?: string | null;
}

/** POST /api/agent-jobs/{id}/accept — success response (AC-3.5). */
export interface AcceptResponse {
  agent_job_id: string;
  acceptance_id: string;
  accepted_artifact_count: number;
  artifact_ids: string[];
  accepted_by: string | null;
  accepted_at: string;
}

// ── Type guard ────────────────────────────────────────────────────────────────

/** Discriminates a GovernanceRejection from any error body (AC-4.4). */
export function isGovernanceRejection(body: unknown): body is GovernanceRejection {
  return (
    typeof body === "object" &&
    body !== null &&
    (body as Record<string, unknown>)["error"] === "governance_rejected"
  );
}

// ── Loopback transport ────────────────────────────────────────────────────────

async function loopbackRequest<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${getLoopbackBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = getLoopbackAuthHeaders();
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let errorBody: unknown = null;
    try {
      errorBody = await res.json();
    } catch {
      /* non-JSON error body — leave null */
    }
    throw new AgentJobsApiError(method, path, res.status, res.statusText, errorBody);
  }
  // All endpoints return HTTP 200 with a JSON body (openapi.json confirmed).
  // No 204 special-case needed.
  return res.json() as Promise<T>;
}

function assertLoopback(action: string): void {
  if (!isLoopbackEnabled()) throw new AgentsStaticModeError(action);
}

// ── API functions ─────────────────────────────────────────────────────────────

/** POST /api/agent-jobs — launch a new agent job. */
export async function launchAgentJob(req: LaunchAgentJobRequest): Promise<AgentJobDetail> {
  assertLoopback("launch an agent job");
  return loopbackRequest<AgentJobDetail>("POST", "/agent-jobs", req);
}

/** GET /api/agent-jobs/{job_id} — fetch job detail including policy_snapshot (AC-4.5). */
export async function getAgentJob(jobId: string): Promise<AgentJobDetail> {
  assertLoopback("get agent job detail");
  return loopbackRequest<AgentJobDetail>("GET", `/agent-jobs/${encodeURIComponent(jobId)}`);
}

/** GET /api/agent-jobs/{job_id}/artifacts — list staged artifacts (AC-3.5). */
export async function listAgentJobArtifacts(jobId: string): Promise<AgentJobArtifact[]> {
  assertLoopback("list agent job artifacts");
  return loopbackRequest<AgentJobArtifact[]>(
    "GET",
    `/agent-jobs/${encodeURIComponent(jobId)}/artifacts`,
  );
}

/** POST /api/agent-jobs/{job_id}/cancel — request job cancellation (204 → void). */
export async function cancelAgentJob(jobId: string): Promise<void> {
  assertLoopback("cancel an agent job");
  return loopbackRequest<void>("POST", `/agent-jobs/${encodeURIComponent(jobId)}/cancel`);
}

/**
 * POST /api/agent-jobs/{job_id}/accept — accept staged artifacts (AC-3.5).
 * Returns an AcceptResponse confirming accepted_artifact_count.
 */
export async function acceptAgentJobArtifacts(
  jobId: string,
  req: AcceptRequest,
): Promise<AcceptResponse> {
  assertLoopback("accept agent job artifacts");
  return loopbackRequest<AcceptResponse>(
    "POST",
    `/agent-jobs/${encodeURIComponent(jobId)}/accept`,
    req,
  );
}

// Note: SSE event stream (GET /api/agent-jobs/{id}/events) is consumed via
// EventSource directly in hooks/useAgentJobs.ts#useAgentJobEvents — not here.
// Use getLoopbackBase() from ./client to build the SSE URL in that hook.
