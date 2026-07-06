/**
 * RF Report Builder Draft Types — Phase 3 (public-multiuser-p2p3, Wave F).
 *
 * Hand-written to mirror the file-canonical draft contract (plan D10):
 *   schemas/report_draft.schema.yaml
 *   src/research_foundry/services/builder_service.py (BLOCK_TYPES, RELATIONS,
 *     LINK_STATUSES, MATERIALITY_VALUES, AUDIENCES, ORIGINS constants, plus
 *     create_draft/add_block/update_block/add_claim_link/add_source_link
 *     kwarg shapes)
 *   src/research_foundry/services/verification.py::verify_draft() (the
 *     `{report_draft_id, passed, exit_code, generated_at, checks[]}` record)
 *
 * Wave D (backend draft store + D13 verification) is merged; Wave E (the
 * HTTP API surface — POST /api/reports etc., spec §10) has NOT landed yet.
 * The request/response shapes below follow the wire contract given in the
 * P3 Wave F handoff brief exactly where the brief is explicit (e.g.
 * `collection_id` on create); everywhere else they mirror builder_service.py
 * verbatim since Wave E is expected to pass those kwargs straight through.
 * TREAT AS AN INFERRED CONTRACT — reconcile against the real router once
 * Wave E merges (see BuilderScreen.tsx module docstring).
 */

import type { RFSensitivity } from "./run-export.js";

// ── Enums (mirror builder_service.py module-level tuples) ───────────────────

export type ReportDraftOrigin = "blank" | "template" | "run" | "collection";
export type ReportAudience = "self" | "technical" | "executive" | "public" | "client";
export type ReportDraftStatus = "draft" | "verified" | "published" | "archived";
export type ReportBlockType = "heading" | "paragraph" | "table" | "quote" | "callout" | "evidence_summary";
export type ReportBlockMateriality = "material" | "narrative" | "background";
/** Denormalized per-block rollup — recomputed by _recompute_block_coverage() on every link mutation. */
export type ReportCoverageStatus = "supported" | "unsupported" | "contradicted" | "narrative" | "needs_review";
export type ReportClaimRelation = "supports" | "contradicts" | "context" | "inferred_from" | "cited_nearby";
export type ReportLinkStatus = "linked" | "stale" | "missing_claim" | "missing_source" | "needs_review";

// ── Blocks ────────────────────────────────────────────────────────────────────

export interface ReportBlock {
  block_id: string;
  block_type: ReportBlockType;
  order: number;
  markdown: string;
  materiality: ReportBlockMateriality;
  linked_claim_ids: string[];
  linked_source_ids: string[];
  coverage_status: ReportCoverageStatus;
  risk_flags: string[];
}

// ── Claim / source links ──────────────────────────────────────────────────────

export interface ReportClaimLink {
  claim_link_id: string;
  block_id: string;
  claim_id: string;
  source_run_id: string | null;
  catalog_item_id: string | null;
  relation: ReportClaimRelation;
  /** Offset into the block's *normalized* markdown (" ".join(raw.split())) — spec §7 Report Location V2. */
  span_start: number | null;
  span_end: number | null;
  quote_text_hash: string | null;
  link_status: ReportLinkStatus;
}

export interface ReportSourceLink {
  source_link_id: string;
  block_id: string | null;
  source_card_id: string;
  run_id: string | null;
  catalog_item_id: string | null;
  relation: string | null;
}

// ── Revisions ─────────────────────────────────────────────────────────────────

export interface ReportRevisionPointer {
  report_version_id: string;
  created_at: string;
  created_by: string | null;
  note: string | null;
}

export interface ReportReviewState {
  status?: string;
  reviewers?: string[];
  [k: string]: unknown;
}

// ── Draft (full detail) ───────────────────────────────────────────────────────

export interface ReportDraft {
  schema_version: number;
  type: "report_draft";
  report_draft_id: string;
  title: string;
  origin: ReportDraftOrigin;
  source_run_id: string | null;
  source_template_id: string | null;
  source_collection_id: string | null;
  audience: ReportAudience;
  sensitivity: RFSensitivity;
  status: ReportDraftStatus;
  workspace_id: string | null;
  project_id: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  current_version_id: string | null;
  blocks: ReportBlock[];
  claim_links: ReportClaimLink[];
  source_links: ReportSourceLink[];
  comments: unknown[];
  review_state: ReportReviewState;
  revisions: ReportRevisionPointer[];
}

/** List-row shape — mirrors builder_service.py::_summary_of(). */
export interface ReportDraftSummary {
  report_draft_id: string;
  title: string;
  status: ReportDraftStatus | null;
  sensitivity: RFSensitivity | null;
  audience: ReportAudience | null;
  origin: ReportDraftOrigin | null;
  project_id: string | null;
  workspace_id: string | null;
  created_by: string | null;
  current_version_id: string | null;
  block_count: number;
  claim_link_count: number;
  source_link_count: number;
  created_at: string | null;
  updated_at: string | null;
}

// ── Verification / publish-preview (D13) ──────────────────────────────────────

/** Mirrors verification.py::CheckResult / the dict verify_draft() serializes. */
export interface ReportVerifyCheck {
  id: string;
  severity: "error" | "warning";
  status: "pass" | "fail" | "warn" | "skip";
  detail: string;
  locations: string[];
}

/** Mirrors the `record` dict returned/written by verification.py::verify_draft(). */
export interface ReportVerifyResult {
  report_draft_id: string;
  passed: boolean;
  exit_code: number;
  generated_at: string;
  checks: ReportVerifyCheck[];
}

/**
 * publish-preview response — INFERRED (Wave E not yet built). Expected to be
 * verify_draft()'s result plus a fail-closed publish gate: `publishable` is
 * false whenever any error-severity check fails (mirrors `passed`, kept as a
 * distinct field so a future non-verification publish rule — e.g. workspace
 * approval — can flip it independently of the verifier).
 */
export interface ReportPublishPreviewResult extends ReportVerifyResult {
  publishable: boolean;
  blocking_reasons: string[];
}

// ── Request payloads ──────────────────────────────────────────────────────────

/** POST /api/reports body — field names per the Wave F handoff brief's API contract. */
export interface CreateDraftRequest {
  origin: ReportDraftOrigin;
  title?: string;
  source_run_id?: string | null;
  collection_id?: string | null;
  audience?: ReportAudience;
  sensitivity?: RFSensitivity;
  project_id?: string | null;
}

export interface AddBlockRequest {
  block_type?: ReportBlockType;
  markdown?: string;
  order?: number;
  materiality?: ReportBlockMateriality;
}

/** PATCH /api/reports/{id}/blocks/{block_id} body — mirrors update_block() kwargs. */
export interface UpdateBlockRequest {
  markdown?: string;
  block_type?: ReportBlockType;
  materiality?: ReportBlockMateriality;
  order?: number;
  risk_flags?: string[];
}

/** POST /api/reports/{id}/claim-links body — mirrors add_claim_link() kwargs. */
export interface AddClaimLinkRequest {
  block_id: string;
  claim_id: string;
  relation?: ReportClaimRelation;
  source_run_id?: string | null;
  catalog_item_id?: string | null;
  span_start?: number | null;
  span_end?: number | null;
}

/** Source-link analog of AddClaimLinkRequest — mirrors add_source_link() kwargs. */
export interface AddSourceLinkRequest {
  source_card_id: string;
  block_id?: string | null;
  run_id?: string | null;
  catalog_item_id?: string | null;
  relation?: string | null;
}

export interface CreateRevisionRequest {
  note?: string | null;
}
