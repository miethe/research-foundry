/**
 * RF Run Export Types — hand-written to match the frozen run.json contract.
 *
 * Source of truth: docs/dev/architecture/rf-run-export-schema.md (status: frozen)
 * Bound to schema_version "1.0".
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
}
