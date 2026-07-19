/**
 * RF Run Export Types — hand-written to match the frozen run.json contract.
 *
 * Source of truth: docs/dev/architecture/rf-run-export-schema.json (JSON Schema draft-07)
 * Bound to schema_version "1.6".
 *
 * Codegen evaluated (P1/SCH-003): json-schema-to-typescript was tested against
 * rf-run-export-schema.json. Rejected because: (1) codegen inlines all
 * RFSensitivity / RFClaimType / RFSourceType enums as anonymous unions on every
 * property instead of producing reusable named types; (2) additionalProperties:true
 * objects (RFTimelineEvent, RFResolvedSource.*) emit `unknown` fields that lose
 * domain intent; (3) hand-written types already carry richer doc-comments and
 * a cleaner component interface. Manual sync against the JSON schema is enforced
 * by PR review. See SCH-003 in phase-1-3-schema-derivation-creation.md.
 *
 * These types define the denormalized claim-graph shape emitted by
 * `rf run export --json`. They are intentionally separate from the
 * 20 auto-generated schema types so that the export contract can evolve
 * independently (with schema-version bumps) while the source schemas remain
 * stable for other consumers.
 *
 * Do NOT edit generated types (*.generated.ts). This file is hand-maintained.
 */

// ── Sensitivity ──────────────────────────────────────────────────────────────

/**
 * Sensitivity level ordering: public < personal < work_sensitive < client_sensitive.
 * Absent sensitivity is treated as public (safe to render).
 * Unrecognized labels are fail-closed (stricter than any known threshold).
 */
export type RFSensitivity =
  | "public"
  | "personal"
  | "work_sensitive"
  | "client_sensitive";

// ── Derived Status ───────────────────────────────────────────────────────────

/**
 * Derived status (OQ-2). Computed from on-disk artifacts, not run.yaml.status.
 * Monotonically increasing: each rung's condition overwrites lower ones.
 */
export type RFStatusDerived =
  | "planned"
  | "sources_ingested"
  | "extracted"
  | "claim_mapped"
  | "synthesized"
  | "verified"
  | "published";

// ── Claim Types and Statuses ─────────────────────────────────────────────────

export type RFClaimType    = "factual" | "inference" | "speculation";
export type RFClaimStatus  =
  | "supported"
  | "mixed"
  | "contradicted"
  | "inference"
  | "speculation"
  | "unsupported";
export type RFClaimConfidence = "low" | "medium" | "high";
export type RFMateriality  = "core" | "background" | "style" | "material";
export type RFSourceRelation = "supports" | "contradicts" | "context";
export type RFSourceType =
  | "official_doc"
  | "paper"
  | "standard"
  | "repo"
  | "news"
  | "blog"
  | "book"
  | "personal_note"
  | "internal_doc"
  | "other";
export type RFSourceRank = "primary" | "secondary" | "tertiary" | "unknown";

// ── Resolved Source (§6.1) ───────────────────────────────────────────────────

/**
 * A fully-resolved source entry within a claim. Joins:
 *   claim_ledger source_ref → source_card YAML → extracted_points[].
 *
 * resolved=false / dangling=true when the referenced card or evidence is absent.
 * Never silently dropped; surfaced so the UI can flag broken provenance.
 */
export interface RFResolvedSource {
  source_card_id:   string;
  evidence_id:      string;
  relation:         RFSourceRelation;
  locator?:         string | null;
  resolved:         boolean;
  dangling:         boolean;
  /** Whether the backend redacted this source at export time (sensitivity > threshold). Optional; absent means false. */
  redacted?:        boolean;

  // Card-level fields (null when dangling=true)
  title?:           string | null;
  source_type?:     RFSourceType | null;
  url?:             string | null;

  trust?: {
    source_rank?:       RFSourceRank;
    reliability_notes?: string;
    known_limitations?: string[];
  } | null;

  usage?: {
    allowed_for_public_output?:      boolean;
    allowed_for_work_output?:        boolean;
    allowed_for_personal_meatywiki?: boolean;
    citation_required?:              boolean;
    quote_limit_notes?:              string;
  } | null;

  sensitivity?:      RFSensitivity | null;

  // Evidence-point fields (null when dangling=true or sensitivity-redacted)
  evidence_locator?: string | null;
  summary?:          string | null;   // "[redacted:sensitivity]" when above threshold
  quote?:            string | null;   // "[redacted:sensitivity]" when above threshold
}

// ── Claim (§6) ───────────────────────────────────────────────────────────────

export interface RFInferenceBasis {
  from_claims:       string[];          // [] for factual claims
  reasoning_summary?: string | null;
}

export interface RFReportLocation {
  file?:         string;
  heading?:      string;
  paragraph_id?: string;
}

/** Optional durable identity links for a run-local claim. Legacy exports omit it. */
export interface RFPersistentReferences {
  source_edition_id?:       string | null;
  passage_id?:              string | null;
  source_assertion_id?:     string | null;
  assertion_version?:       number | null;
  canonical_claim_id?:      string | null;
  canonical_claim_version?: number | null;
  inference_id?:            string | null;
}

// ── Report Anchors (§16, schema 1.4 — P2 Wave A/D7-D8) ───────────────────────
//
// Backend-derived (markdown-it-py AST, never regex) block/paragraph anchors +
// claim spans for report_draft. Additive/nullable field on RFRunExport;
// entirely ABSENT (key omitted, not merely null) on pre-1.4 exports — that is
// the frontend's "legacy mode" trigger (D9), never a link_status value.
//
// Source of truth: docs/dev/architecture/rf-run-export-schema.md §16 and
// src/research_foundry/services/export_service.py::derive_report_anchors().

/** A bare [claim:...] tag carries no relation of its own — inferred from the
 * linked claim's status at export time. `null` only when link_status is
 * "missing_claim" (the tag did not resolve to a claim in claims[]). */
export type RFReportAnchorRelation = "supports" | "contradicts" | "inferred_from" | "context";

export interface RFReportAnchorClaimLink {
  claim_id:      string;
  /** Offset into the *normalized* block text (" ".join(raw.split())). */
  span_start:    number;
  span_end:      number;
  relation:      RFReportAnchorRelation | null;
  /**
   * "stale" is a capability of derive_report_anchors() (hash-drift detection
   * against a previously-derived anchor set) that export_run() does not wire
   * up yet — every resolved link is "linked" in current exports. Frontend
   * must still branch on it defensively (D13 will start emitting it).
   */
  link_status:   "linked" | "stale" | "missing_claim";
}

export interface RFReportAnchorBlock {
  /** sha1(section_id + normalized_text + ordinal)[:12] — stable DOM anchor id. */
  block_id:          string;
  /** Nearest preceding h2/h3 slug (mirrors reportOutlineUtils.slugify exactly); null before the first heading. */
  section_id:        string | null;
  /** 0-based index of this paragraph within its section. */
  paragraph_ordinal: number;
  /** sha1(normalized_text)[:12] — drift-detection hash; never the prose itself (no new redaction surface). */
  text_hash:         string;
  claim_links:       RFReportAnchorClaimLink[];
}

export interface RFClaim {
  claim_id:          string;
  text:              string;
  materiality?:      RFMateriality;
  claim_type?:       RFClaimType;
  status?:           RFClaimStatus;
  confidence?:       RFClaimConfidence;
  report_locations?: RFReportLocation[];
  inference_basis?:  RFInferenceBasis;
  persistent_references?: RFPersistentReferences | null;
  sources:           RFResolvedSource[];
}

// ── Claim Counts ─────────────────────────────────────────────────────────────

export interface RFClaimCounts {
  source_cards?:          number;
  extraction_cards?:      number;
  claims_total?:          number;
  claims_supported?:      number;
  claims_mixed?:          number;
  claims_contradicted?:   number;
  claims_inference?:      number;
  claims_speculation?:    number;
  claims_unsupported?:    number;
  // Top-level aliases (shorthand on the export)
  total?:                 number;
  supported?:             number;
  inference?:             number;
  speculation?:           number;
}

// ── Verification (§5) ────────────────────────────────────────────────────────

export interface RFVerificationCheck {
  id:         string;
  severity:   "error" | "warning" | "info";
  status:     "pass" | "fail" | "skip";
  detail?:    string;
  locations?: unknown[];
}

/**
 * Derived summary of `verify_report()`'s output embedded in the run export —
 * NOT a 1:1 mirror of `verification.yaml`. `services/verification.py`'s
 * `rf_schema_version` top-level field (PRD FR-4.1) is therefore intentionally
 * absent here; it is not threaded through this subset by export_service.py.
 */
export interface RFVerification {
  present:    boolean;
  passed:     boolean | null;
  exit_code:  number | null;
  checks:     RFVerificationCheck[];
}

// ── Governance ───────────────────────────────────────────────────────────────

export interface RFGovernanceBlock {
  sensitivity?:              RFSensitivity;
  approved_for_writeback?:   boolean;
  approved_by?:              string | null;
  approval_timestamp?:       string | null;
  /** AC-4: threaded from run.yaml governance.allowed_writebacks */
  allowed_writebacks?:       string[] | null;
  /** AC-4: threaded from run.yaml governance.requires_human_review */
  requires_human_review?:    boolean | null;
}

// ── Timeline Event ───────────────────────────────────────────────────────────

export interface RFTimelineEvent {
  ts?:        string;
  event?:     string;
  detail?:    unknown;
}

// ── Artifact Schema Versions ─────────────────────────────────────────────────

export interface RFArtifactSchemaVersions {
  run?:              string;
  evidence_bundle?:  string;
  claim_ledger?:     string;
  [k: string]:       string | undefined;
}

// ── Optional v2 Context / Writeback Summaries ────────────────────────────────

export interface RFRunContextSummary {
  routing_decision?: {
    decision?: string | null;
    rationale?: string | null;
    [k: string]: unknown;
  } | null;
  research_brief_md?: string | null;
  swarm_plan?: {
    swarm?: string | null;
    agents?: string[] | string | null;
    adapters?: string[] | string | null;
    [k: string]: unknown;
  } | null;
  upstream_entities?: Record<string, unknown> | null;
}

export interface RFWritebackTarget {
  name?: string | null;
  destination?: string | null;
  status?: string | null;
  url?: string | null;
  [k: string]: unknown;
}

/**
 * A single rendered writeback candidate (schema 1.6, FR-13). One entry per
 * present file in the backend's `_WRITEBACK_TARGETS` mapping
 * (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`,
 * `intenttree_update.yaml`, `arc_review_request.yaml`,
 * `notebooklm_update.yaml`). `content` has already passed through the
 * export's sensitivity redaction pass — the same gate applied to every
 * other exported text field.
 */
export interface RFWritebackPreview {
  target: string;
  filename: string;
  content_type: "markdown" | "yaml";
  content: string;
}

export interface RFRunWritebacksSummary {
  targets?: RFWritebackTarget[] | null;
  approved_for_writeback?: boolean | null;
  /** Schema 1.6 (FR-13). Sourced from the council review packet, not evidence_bundle.governance. */
  reviewer_notes?: string | null;
  /** Schema 1.6 (FR-13). Newline-joined from the review packet's output.concerns[].required_fix entries. */
  required_fix?: string | null;
  /** Schema 1.6 (FR-13). Null/absent on pre-1.6 exports (key omitted, not present-but-null). */
  previews?: RFWritebackPreview[] | null;
}

// ── AOS Correlation Metadata ─────────────────────────────────────────────────

export type RFAOSNativeAliasMap = Record<string, string | number | boolean | null | undefined>;

// ── Run Export (top-level) ───────────────────────────────────────────────────

/**
 * The complete denormalized run.json document emitted by `rf run export --json`.
 *
 * Only schema_version, run_id, status_derived, and claims are guaranteed non-null.
 * All others may be null/absent when the underlying artifact is absent.
 * Consumers MUST use optional access (?.) throughout.
 */
export interface RFRunExport {
  schema_version:            string;
  /**
   * Canonical cross-surface contract version (PRD FR-4.1 / AC-RFUP4-1;
   * `RF_SCHEMA_VERSION` in `research_foundry/__init__.py`, currently "1.0.0").
   * Distinct from `schema_version` above (the narrower, independently-versioned
   * run-export document schema, "1.5") — this field is additive and stamped by
   * the LAN API (`GET /api/runs/{run_id}` returns this exact document shape).
   * Absent on exports produced before this field was introduced.
   */
  rf_schema_version?:        string;
  run_id:                    string;
  intent_id?:                string | null;
  created_at?:               string | null;
  status_derived:            RFStatusDerived;
  status_raw?:               string | null;
  /**
   * Human-readable title derived from the report_draft frontmatter `title:` key,
   * or a slug-humanized string when the frontmatter title is absent.
   * Added in schema_version 1.1 export; absent in older cached run.json files.
   * Mirrors the same field on RFRunSummary so consumers can use either type uniformly.
   */
  title?:                    string | null;
  sensitivity?:              RFSensitivity | null;
  sensitivity_threshold?:    RFSensitivity | null;
  claim_counts?:             RFClaimCounts | null;
  verification?:             RFVerification | null;
  governance?:               RFGovernanceBlock | null;
  timeline?:                 RFTimelineEvent[] | null;
  claims:                    RFClaim[];
  artifact_schema_versions?: RFArtifactSchemaVersions | null;
  /** Markdown report draft emitted by the synthesizer step. Null when not yet generated. */
  report_draft?:             string | null;
  /** Optional v2 context stack (schema 1.3: shape frozen with 4 keys). Absent in schema 1.1 exports. */
  context?:                  RFRunContextSummary | null;
  /** Optional v2 writeback summary. Absent in schema 1.1 exports. */
  writebacks?:               RFRunWritebacksSummary | null;

  /**
   * AST-derived report block/paragraph anchors + claim spans (schema 1.4, §16).
   * Null when report_draft is null. KEY ABSENT ENTIRELY on pre-1.4 exports —
   * that absence (not a null value) is the frontend's legacy-regex-fallback
   * trigger (D9). Use optional access: `run.report_anchors`.
   */
  report_anchors?:           RFReportAnchorBlock[] | null;

  // ── AOS Correlation IDs (optional additive rollout) ───────────────────────
  // Each scope has its own UUID. Missing/unknown values are valid and should
  // render as unresolved/not available instead of failing the viewer.

  aos_run_uuid?:              string | null;
  aos_session_uuid?:          string | null;
  aos_feature_uuid?:          string | null;
  aos_artifact_uuid?:         string | null;
  aos_trace_uuid?:            string | null;
  /** RF-native IDs preserved as AOS aliases, e.g. { rf_run_id: run_id }. */
  native_aliases?:            RFAOSNativeAliasMap | null;

  // ── Run Metadata Enrichment fields (schema 1.2) ────────────────────────────
  // All fields below are optional/nullable — absent on pre-migration runs (schema < 1.2).
  // Consumers MUST use optional access (?.) throughout. Populated in P2 (backfill)
  // and P3 (creation path). Threaded through export in P4.

  /**
   * List of project slugs this run is linked to. Derived from backlog idea.suggested_project
   * at run creation or via backfill migration. Null/absent on pre-migration runs.
   */
  linked_projects?:          string[] | null;

  /**
   * Research pillar / category string. Derived from backlog idea.pillar.
   * Examples: 'AI Engineering', 'Frontend Tooling'. Null/absent on pre-migration runs.
   */
  category?:                 string | null;

  /**
   * List of topic tags. Derived from backlog idea.tags or set explicitly at run creation.
   * Null/absent on pre-migration runs.
   */
  tags?:                     string[] | null;

  /**
   * Backlog idea ID in RIB-NNN format (e.g. 'RIB-042').
   * References an entry in backlog/research_idea_backlog.yaml.
   * Null when run was not created from a backlog idea.
   */
  backlog_idea_ref?:         string | null;

  /**
   * Reverse slug of the backlog idea (matches idea.id field in the backlog YAML).
   * Null when backlog_idea_ref is null.
   */
  backlog_idea_id?:          string | null;

  // ── Enrichment Extras (schema 1.2, P7 — ENR-001, ENR-002) ─────────────────
  // Threaded from run.yaml.profile and aggregated from source cards.
  // All null/absent on pre-enrichment runs. FE must use optional access (?.).

  /**
   * Actual or budgeted cost of the run in USD. Sourced from run.yaml.profile.max_cost_usd.
   * Null when no profile block is present (pre-enrichment runs).
   */
  cost_usd?:                 number | null;

  /**
   * Model and resource profile settings for the run. Sourced from run.yaml.profile.
   * Contains extraction_model_profile, synthesis_model_profile, verification_model_profile,
   * max_cost_usd, max_runtime_minutes, freshness_days. Null when profile absent.
   */
  model_profiles?: {
    max_cost_usd?:                  number | null;
    extraction_model_profile?:      string | null;
    synthesis_model_profile?:       string | null;
    verification_model_profile?:    string | null;
    max_runtime_minutes?:           number | null;
    freshness_days?:                number | null;
    [k: string]: unknown;
  } | null;

  /**
   * Count of source cards by source_type (e.g. { official_doc: 3, paper: 1 }).
   * Aggregated from all source cards in the run's sources/ directory.
   * Null when no source cards are present.
   */
  source_count_by_type?:     Record<string, number> | null;

  /**
   * Reusable output candidates from the backlog idea's intenttree block.
   * Threaded by F5 Phase 7 (run-metadata-enrichment). Absent/null on pre-F5 exports.
   * Consumers MUST treat this field as optional and guard every access.
   */
  reusable_output_candidates?: ReusableOutputCandidate[] | null;
}

// ── Reusable Output Candidate (F5/P7, schema 1.2+) ──────────────────────────

/**
 * A single reusable output candidate surfaced from the backlog idea's intenttree block.
 * Threaded into RFRunExport by F5 Phase 7. All fields except `description` are optional
 * because older export runs will not have populated them.
 */
export interface ReusableOutputCandidate {
  /** Short description of the reusable output. */
  description: string;
  /** When true, this candidate is labeled as a SkillBOM candidate in the Library view. */
  is_skillbom_candidate?: boolean;
  /** The run_id that produced this candidate (may differ from the current run in aggregated views). */
  source_run_id?: string;
}

// ── Run Summary (from `rf run list --json`) ──────────────────────────────────

/**
 * Lightweight run summary as emitted by `rf run list --json`.
 * Used for the RunList view without loading the full claim graph.
 */
export interface RFRunSummary {
  run_id:          string;
  status_derived:  RFStatusDerived;
  created_at?:     string | null;
  sensitivity?:    RFSensitivity | null;
  claim_counts?:   RFClaimCounts | null;
  /**
   * Human-readable title derived from the report_draft frontmatter `title:` key,
   * or a slug-humanized string when the frontmatter title is absent.
   * Added in schema_version 1.1 export; absent in older cached run.json files.
   * Falls back to titleFromSlug(run_id) in the FE when absent or null.
   */
  title?:          string | null;

  // Metadata enrichment stubs (schema 1.2) — populated in P4 (export threading + index.json).
  // Absent on pre-migration runs; consumers must use optional access (?.).
  linked_projects?: string[] | null; // populated in P4
  category?:        string | null;   // populated in P4
  tags?:            string[] | null; // populated in P4
}
