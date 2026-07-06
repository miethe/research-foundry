/**
 * RF Report Builder API Client — P3 Wave F.
 *
 * Unlike api/client.ts (the read-only run/catalog viewer client), this
 * module performs MUTATIONS (create draft, edit blocks, link claims, verify,
 * publish-preview) — that's why it is intentionally split out rather than
 * added to client.ts's "NO POST/PUT/DELETE" contract.
 *
 * DUAL-MODE, BUT LOOPBACK-ONLY FOR WRITES (spec §8, Wave F handoff D-choice):
 *   - Loopback mode (VITE_RUNS_FRONTEND_LOOPBACK_API=true): full read/write
 *     against the spec §10 report endpoints on the local `rf serve` API.
 *   - Static mode (default, no server): the Builder is READ-ONLY. Every
 *     mutation function throws BuilderStaticModeError immediately (never
 *     silently no-ops) so the UI can catch it and show why the action is
 *     disabled. Reads return a bundled demo draft (lib/builderMocks.ts) —
 *     this stands in for "read-only published drafts" per the handoff brief
 *     (§5 Wave F notes: "static mode shows read-only published drafts or a
 *     disabled state — document the choice"). We chose the demo-draft path
 *     over a bare disabled screen so the Builder's layout/interactions are
 *     still visible for visual QA in a static deployment; BuilderScreen.tsx
 *     renders a persistent banner explaining the read-only reason.
 *
 * CONTRACT CAVEAT: Wave E (the actual HTTP router — POST /api/reports etc.)
 * has not merged as of this writing. The request/response shapes here match
 * schemas/report_draft.schema.yaml and builder_service.py/verification.py
 * (see types/rf/report_draft.ts header) but the literal endpoint paths are
 * inferred from the Wave F handoff brief's "BUILDER API CONTRACT" section.
 * Reconcile here first if Wave E's router uses different paths/verbs.
 */

import { getLoopbackAuthHeaders, getLoopbackBase, isLoopbackEnabled } from "./client";
import { MOCK_REPORT_DRAFT, MOCK_REPORT_DRAFT_LIST } from "@/lib/builderMocks";
import type {
  AddBlockRequest,
  AddClaimLinkRequest,
  AddSourceLinkRequest,
  CreateDraftRequest,
  CreateRevisionRequest,
  ReportDraft,
  ReportDraftSummary,
  ReportPublishPreviewResult,
  ReportRevisionPointer,
  ReportVerifyResult,
  UpdateBlockRequest,
} from "@/types/rf/report_draft";

export class BuilderStaticModeError extends Error {
  constructor(action: string) {
    super(
      `Report Builder is read-only in static mode: cannot ${action}. ` +
        `Run against a loopback RF API (VITE_RUNS_FRONTEND_LOOPBACK_API=true) to edit drafts.`,
    );
    this.name = "BuilderStaticModeError";
  }
}

export { isLoopbackEnabled as isBuilderLoopbackEnabled };

// ── Loopback transport ────────────────────────────────────────────────────────

async function loopbackRequest<T>(method: "GET" | "POST" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  const url = `${getLoopbackBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = getLoopbackAuthHeaders();
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  if (!res.ok) {
    throw new Error(`Report Builder API ${method} ${url} failed: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function assertLoopback(action: string): void {
  if (!isLoopbackEnabled()) throw new BuilderStaticModeError(action);
}

// ── Reads ─────────────────────────────────────────────────────────────────────

export async function fetchReportDraftList(): Promise<ReportDraftSummary[]> {
  if (isLoopbackEnabled()) return loopbackRequest<ReportDraftSummary[]>("GET", "/reports");
  return MOCK_REPORT_DRAFT_LIST;
}

export async function fetchReportDraft(reportDraftId: string): Promise<ReportDraft> {
  if (isLoopbackEnabled()) return loopbackRequest<ReportDraft>("GET", `/reports/${encodeURIComponent(reportDraftId)}`);
  if (reportDraftId === MOCK_REPORT_DRAFT.report_draft_id) return MOCK_REPORT_DRAFT;
  throw new Error(`Static mode: no read-only draft found for ${reportDraftId}`);
}

export async function listReportVersions(reportDraftId: string): Promise<ReportRevisionPointer[]> {
  if (isLoopbackEnabled()) return loopbackRequest<ReportRevisionPointer[]>("GET", `/reports/${encodeURIComponent(reportDraftId)}/versions`);
  return MOCK_REPORT_DRAFT.revisions;
}

// ── Mutations (loopback-only — throw BuilderStaticModeError in static mode) ───

export async function createReportDraft(payload: CreateDraftRequest): Promise<ReportDraft> {
  assertLoopback("create a draft");
  return loopbackRequest<ReportDraft>("POST", "/reports", payload);
}

export async function deleteReportDraft(reportDraftId: string): Promise<void> {
  assertLoopback("delete a draft");
  return loopbackRequest<void>("DELETE", `/reports/${encodeURIComponent(reportDraftId)}`);
}

export async function addReportBlock(reportDraftId: string, payload: AddBlockRequest): Promise<ReportDraft> {
  assertLoopback("add a block");
  return loopbackRequest<ReportDraft>("POST", `/reports/${encodeURIComponent(reportDraftId)}/blocks`, payload);
}

export async function updateReportBlock(reportDraftId: string, blockId: string, payload: UpdateBlockRequest): Promise<ReportDraft> {
  assertLoopback("update a block");
  return loopbackRequest<ReportDraft>(
    "PATCH",
    `/reports/${encodeURIComponent(reportDraftId)}/blocks/${encodeURIComponent(blockId)}`,
    payload,
  );
}

export async function deleteReportBlock(reportDraftId: string, blockId: string): Promise<ReportDraft> {
  assertLoopback("delete a block");
  return loopbackRequest<ReportDraft>(
    "DELETE",
    `/reports/${encodeURIComponent(reportDraftId)}/blocks/${encodeURIComponent(blockId)}`,
  );
}

export async function reorderReportBlocks(reportDraftId: string, blockIds: string[]): Promise<ReportDraft> {
  assertLoopback("reorder blocks");
  // Wave E API reconciliation: this is a PATCH on Wave E's router, not a POST
  // (everything else in this client already matched Wave E's routes as-built).
  return loopbackRequest<ReportDraft>("PATCH", `/reports/${encodeURIComponent(reportDraftId)}/blocks/reorder`, { block_ids: blockIds });
}

export async function addReportClaimLink(reportDraftId: string, payload: AddClaimLinkRequest): Promise<ReportDraft> {
  assertLoopback("link a claim");
  return loopbackRequest<ReportDraft>("POST", `/reports/${encodeURIComponent(reportDraftId)}/claim-links`, payload);
}

export async function removeReportClaimLink(reportDraftId: string, claimLinkId: string): Promise<ReportDraft> {
  assertLoopback("remove a claim link");
  return loopbackRequest<ReportDraft>(
    "DELETE",
    `/reports/${encodeURIComponent(reportDraftId)}/claim-links/${encodeURIComponent(claimLinkId)}`,
  );
}

export async function addReportSourceLink(reportDraftId: string, payload: AddSourceLinkRequest): Promise<ReportDraft> {
  assertLoopback("link a source");
  return loopbackRequest<ReportDraft>("POST", `/reports/${encodeURIComponent(reportDraftId)}/source-links`, payload);
}

export async function removeReportSourceLink(reportDraftId: string, sourceLinkId: string): Promise<ReportDraft> {
  assertLoopback("remove a source link");
  return loopbackRequest<ReportDraft>(
    "DELETE",
    `/reports/${encodeURIComponent(reportDraftId)}/source-links/${encodeURIComponent(sourceLinkId)}`,
  );
}

export async function createReportVersion(reportDraftId: string, payload: CreateRevisionRequest = {}): Promise<ReportRevisionPointer> {
  assertLoopback("save a version");
  return loopbackRequest<ReportRevisionPointer>("POST", `/reports/${encodeURIComponent(reportDraftId)}/versions`, payload);
}

export async function restoreReportVersion(reportDraftId: string, reportVersionId: string): Promise<ReportDraft> {
  assertLoopback("restore a version");
  return loopbackRequest<ReportDraft>(
    "POST",
    `/reports/${encodeURIComponent(reportDraftId)}/versions/${encodeURIComponent(reportVersionId)}/restore`,
  );
}

// ── Verification / publish gate (D13) ─────────────────────────────────────────

export async function verifyReportDraft(reportDraftId: string): Promise<ReportVerifyResult> {
  assertLoopback("verify the draft");
  return loopbackRequest<ReportVerifyResult>("POST", `/reports/${encodeURIComponent(reportDraftId)}/verify`);
}

export async function publishPreviewReportDraft(reportDraftId: string): Promise<ReportPublishPreviewResult> {
  assertLoopback("run publish preview");
  return loopbackRequest<ReportPublishPreviewResult>("POST", `/reports/${encodeURIComponent(reportDraftId)}/publish-preview`);
}
