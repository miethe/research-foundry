import type {
  RFClaim,
  RFClaimCounts,
  RFReportLocation,
  RFResolvedSource,
  RFRunExport,
  RFRunSummary,
  RFSensitivity,
  RFStatusDerived,
  RFVerification,
  RFWritebackTarget,
} from "@/types/rf";

export type RunHealthBucket = "verified" | "needs-review" | "failed" | "planned" | "published";

const SENSITIVITY_ORDER: Record<RFSensitivity, number> = {
  public: 0,
  personal: 1,
  work_sensitive: 2,
  client_sensitive: 3,
};

export const STATUS_LABEL: Record<RFStatusDerived, string> = {
  planned: "Planned",
  sources_ingested: "Sources Ingested",
  extracted: "Extracted",
  claim_mapped: "Claim Mapped",
  synthesized: "Synthesized",
  verified: "Verified",
  published: "Published",
};

export function getClaimTotal(counts?: RFClaimCounts | null, claims?: RFClaim[]): number {
  return counts?.total ?? counts?.claims_total ?? claims?.length ?? 0;
}

export function getSupportedTotal(counts?: RFClaimCounts | null): number {
  return counts?.supported ?? counts?.claims_supported ?? 0;
}

export function getInferenceTotal(counts?: RFClaimCounts | null): number {
  return counts?.inference ?? counts?.claims_inference ?? 0;
}

export function getSpeculationTotal(counts?: RFClaimCounts | null): number {
  return counts?.speculation ?? counts?.claims_speculation ?? 0;
}

export function getUnsupportedTotal(counts?: RFClaimCounts | null): number {
  return counts?.claims_unsupported ?? 0;
}

export function getMixedTotal(counts?: RFClaimCounts | null): number {
  return (counts?.claims_mixed ?? 0) + (counts?.claims_contradicted ?? 0);
}

export function getRunBucket(run: RFRunSummary | RFRunExport): RunHealthBucket {
  if ("verification" in run && run.verification?.present && run.verification.passed === false) {
    return "failed";
  }
  if (getUnsupportedTotal(run.claim_counts) > 0 || getMixedTotal(run.claim_counts) > 0) {
    return "failed";
  }
  if (run.status_derived === "published") return "published";
  if (run.status_derived === "verified") return "verified";
  if (run.status_derived === "planned") return "planned";
  return "needs-review";
}

export function countVerificationChecks(
  verification: RFVerification | null | undefined,
  status: "pass" | "fail" | "skip",
): number {
  return verification?.checks?.filter((check) => check.status === status).length ?? 0;
}

export function countWarningChecks(verification: RFVerification | null | undefined): number {
  return verification?.checks?.filter((check) => check.severity === "warning").length ?? 0;
}

export function sourceExceedsThreshold(
  sourceSensitivity: RFSensitivity | null | undefined,
  threshold: RFSensitivity | null | undefined,
): boolean {
  if (!sourceSensitivity) return false;
  const sourceLevel = SENSITIVITY_ORDER[sourceSensitivity];
  const thresholdLevel = threshold ? SENSITIVITY_ORDER[threshold] : SENSITIVITY_ORDER.public;
  if (sourceLevel == null || thresholdLevel == null) return true;
  return sourceLevel > thresholdLevel;
}

export function sourceHasRedactedText(source: RFResolvedSource): boolean {
  const quote = source.quote ?? "";
  const summary = source.summary ?? "";
  return quote.startsWith("[redacted") || summary.startsWith("[redacted");
}

export function shouldRedactSource(
  source: RFResolvedSource,
  threshold?: RFSensitivity | null,
): boolean {
  if (source.dangling) return false;
  if (sourceHasRedactedText(source)) return true;
  return sourceExceedsThreshold(source.sensitivity, threshold ?? "public");
}

/**
 * Schema versions that the viewer fully understands. Neither '1.1' nor '1.2'
 * triggers a mismatch badge; only genuinely unknown or future-incompatible
 * versions do.  Update this set when a breaking schema bump is released.
 */
const KNOWN_VALID_SCHEMA_VERSIONS = new Set(["1.1", "1.2"]);

/**
 * Returns true when a run's schema_version is at least "1.3".
 * Uses simple numeric version comparison on the first two semver parts.
 * Falls back to false when version is absent or unparseable (safe default).
 *
 * Shared by ContextPane (schema guard for rendering context panels) and
 * useRunContext (DFR-001 lazy-load hook — gates the live-fetch path so a
 * pre-1.3 run, whose context is always discarded by the render guard, never
 * fires a network request in the first place).
 */
export function isSchemaAtLeast13(schemaVersion: string | undefined): boolean {
  if (!schemaVersion) return false;
  const parts = schemaVersion.split(".").map(Number);
  const major = parts[0] ?? 0;
  const minor = parts[1] ?? 0;
  // 1.3, 1.4, 2.x, etc. are all >= 1.3
  if (major > 1) return true;
  if (major === 1 && minor >= 3) return true;
  return false;
}

export interface RunAttentionSummary {
  failedChecks: number;
  warningChecks: number;
  unsupportedClaims: number;
  mixedClaims: number;
  danglingSources: number;
  redactedSources: number;
  emptyInferenceBasis: number;
  schemaMismatch: boolean;
}

export function summarizeRunAttention(run: RFRunExport): RunAttentionSummary {
  const sources = run.claims.flatMap((claim) => claim.sources ?? []);
  return {
    failedChecks: countVerificationChecks(run.verification, "fail"),
    warningChecks: countWarningChecks(run.verification),
    unsupportedClaims: run.claims.filter((claim) => claim.status === "unsupported").length,
    mixedClaims: run.claims.filter((claim) => claim.status === "mixed" || claim.status === "contradicted").length,
    danglingSources: sources.filter((source) => source.dangling || source.resolved === false).length,
    redactedSources: sources.filter((source) => shouldRedactSource(source, run.sensitivity_threshold)).length,
    emptyInferenceBasis: run.claims.filter(
      (claim) =>
        (claim.claim_type === "inference" || claim.status === "inference") &&
        (claim.inference_basis?.from_claims ?? []).length === 0,
    ).length,
    schemaMismatch: Boolean(run.schema_version && !KNOWN_VALID_SCHEMA_VERSIONS.has(run.schema_version)),
  };
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "Not exported";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatShortDate(value?: string | null): string {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function deriveClaimTitle(claim: Pick<RFClaim, "claim_id" | "text">, maxLength = 96): string {
  const text = claim.text.trim().replace(/\s+/g, " ");
  if (!text) return claim.claim_id;
  if (text.length <= maxLength) return text;
  const clipped = text.slice(0, maxLength + 1);
  const lastSpace = clipped.lastIndexOf(" ");
  const boundary = lastSpace > 48 ? lastSpace : maxLength;
  return `${text.slice(0, boundary).trim()}...`;
}

export function deriveSourceTitle(source: Pick<RFResolvedSource, "source_card_id" | "title" | "url">): string {
  const explicit = source.title?.trim();
  if (explicit) return explicit;
  if (source.url) {
    try {
      const url = new URL(source.url);
      const path = url.pathname.replace(/\/$/, "");
      return path && path !== "/" ? `${url.hostname}${path}` : url.hostname;
    } catch {
      return source.url;
    }
  }
  return source.source_card_id;
}

export function deriveExtractionTitle(source: Pick<RFResolvedSource, "evidence_id" | "evidence_locator" | "locator" | "source_card_id" | "title" | "url">): string {
  return source.evidence_locator ?? source.locator ?? source.evidence_id ?? deriveSourceTitle(source);
}

export function deriveReportTitle(run: Pick<RFRunExport, "report_draft">): string {
  return firstMarkdownHeading(run.report_draft, 1) ?? firstMarkdownHeading(run.report_draft) ?? "Draft report";
}

export function deriveRunTitle(run: Pick<RFRunExport, "run_id" | "intent_id" | "report_draft" | "context">): string {
  return (
    firstMarkdownHeading(run.report_draft, 1) ||
    firstMarkdownHeading(run.report_draft) ||
    firstMarkdownHeading(run.context?.research_brief_md, 1) ||
    titleFromSlug(run.intent_id) ||
    titleFromSlug(run.run_id) ||
    run.run_id
  );
}

export function deriveReportLocationTitle(location: RFReportLocation): string {
  return location.heading ?? location.paragraph_id ?? location.file ?? "Report location";
}

export function deriveWritebackTitle(target: RFWritebackTarget): string {
  if (target.name?.trim()) return target.name.trim();
  if (target.destination?.trim()) return titleFromSlug(target.destination) ?? target.destination;
  if (target.url) {
    try {
      return new URL(target.url).hostname;
    } catch {
      return target.url;
    }
  }
  return "Writeback target";
}

export function hasWritebackExport(run: Pick<RFRunExport, "writebacks">): boolean {
  const writebacks = run.writebacks;
  return Boolean(
    writebacks &&
      ((writebacks.targets?.length ?? 0) > 0 ||
        (writebacks.previews?.length ?? 0) > 0 ||
        writebacks.required_fix ||
        writebacks.reviewer_notes ||
        writebacks.approved_for_writeback != null),
  );
}

function firstMarkdownHeading(markdown?: string | null, level?: number): string | null {
  if (!markdown) return null;
  const lines = markdown.split(/\r?\n/);
  for (const line of lines) {
    const match = /^(#{1,6})\s+(.+?)\s*$/.exec(line.trim());
    if (!match) continue;
    if (level != null && match[1]?.length !== level) continue;
    return match[2]?.replace(/\s+\[claim:[^\]]+\]/g, "").trim() || null;
  }
  return null;
}

export function titleFromSlug(value?: string | null): string | null {
  if (!value) return null;
  const normalized = value
    .replace(/^(rf_run|intent|intent_research)_?/i, "")
    .replace(/^\d{8,}_?/, "")
    .replace(/[_-]+/g, " ")
    .trim();
  if (!normalized) return value;
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}
