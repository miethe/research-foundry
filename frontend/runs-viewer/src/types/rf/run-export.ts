/**
 * RF Run Export Types — hand-written to match the frozen run.json contract.
 *
 * Source of truth: docs/dev/architecture/rf-run-export-schema.json (JSON Schema draft-07)
 * Bound to schema_version "1.2".
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

export interface RFClaim {
  claim_id:          string;
  text:              string;
  materiality?:      RFMateriality;
  claim_type?:       RFClaimType;
  status?:           RFClaimStatus;
  confidence?:       RFClaimConfidence;
  report_locations?: RFReportLocation[];
  inference_basis?:  RFInferenceBasis;
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

export interface RFRunWritebacksSummary {
  targets?: RFWritebackTarget[] | null;
  approved_for_writeback?: boolean | null;
  reviewer_notes?: string | null;
  required_fix?: string | null;
  previews?: unknown[] | null;
}

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
  /** Optional v2 context stack. Absent in schema 1.1 exports. */
  context?:                  RFRunContextSummary | null;
  /** Optional v2 writeback summary. Absent in schema 1.1 exports. */
  writebacks?:               RFRunWritebacksSummary | null;

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
