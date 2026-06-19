import type {
  RFClaim,
  RFClaimCounts,
  RFResolvedSource,
  RFRunExport,
  RFRunSummary,
  RFSensitivity,
  RFStatusDerived,
  RFVerification,
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
    schemaMismatch: Boolean(run.schema_version && run.schema_version !== "1.1"),
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
