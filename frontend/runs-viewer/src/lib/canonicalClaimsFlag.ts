/**
 * canonicalClaimsFlag.ts — P6/P7 reviewer-experience canonical-claims signal.
 *
 * Read-only build-time flag mirroring the isLoopbackEnabled() pattern in
 * src/api/client.ts (see LOOPBACK_ENABLED there). This module intentionally
 * does not import client.ts to avoid touching the frozen P6-001 seam; it
 * reads the same import.meta.env surface directly.
 *
 * Default (env var absent, unset, or any value other than "true"/true) is
 * DISABLED — assertion-only mode. This is a deliberate fail-closed default:
 * the reviewer experience must never imply an enabled canonical-merge
 * capability that the deployment has not explicitly turned on.
 *
 * Per docs/project_plans/design-specs/reusable-assertion-ledger-reviewer-experience-v1.md
 * §5.4 and §7 ("Optional merge review"): merge-candidate controls require ALL
 * of (a) this flag, (b) generated contract fields being present on the
 * relevant DTO, and (c) authorization — never this flag alone.
 */

const CANONICAL_CLAIMS_ENABLED =
  typeof import.meta !== "undefined" &&
  (import.meta.env?.VITE_RF_CANONICAL_CLAIMS_ENABLED === "true" ||
    import.meta.env?.VITE_RF_CANONICAL_CLAIMS_ENABLED === true);

/** True only when the deployment has explicitly opted into canonical-claim grouping. */
export function isCanonicalClaimsEnabled(): boolean {
  return CANONICAL_CLAIMS_ENABLED;
}
