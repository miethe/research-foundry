/**
 * Reusable safe copy for generated/server reason codes. Keep the code visible
 * in UI. Impact surfaces use both fields so their blocking headline and
 * explanation remain governed by the DTO reason rather than a packet guess.
 */
export type AssertionReasonCopy = Readonly<{
  headline: string;
  description: string;
}>;

export const assertionReasonCopy: Readonly<Record<string, AssertionReasonCopy>> = {
  access_denied: {
    headline: "Assertion unavailable — access denied",
    description: "You do not have access to this assertion.",
  },
  impact_unavailable: {
    headline: "Impact data unavailable",
    description: "Impact data is unavailable.",
  },
  lifecycle_unknown: {
    headline: "Reuse blocked — lifecycle unavailable",
    description: "The assertion lifecycle cannot be verified.",
  },
  access_scope_unknown: {
    headline: "Reuse blocked — access scope unavailable",
    description: "The assertion access scope cannot be verified.",
  },
  rights_denied: {
    headline: "Reuse blocked — rights decision denied",
    description: "Your current rights do not allow this assertion.",
  },
  dependency_manifest_missing: {
    headline: "Reuse blocked — dependency manifest missing",
    description: "The dependency manifest required to verify downstream impact is missing, so reuse remains blocked.",
  },
  dependency_manifest_invalid: {
    headline: "Reuse blocked — dependency manifest invalid",
    description: "The dependency manifest cannot be validated, so reuse remains blocked.",
  },
  dependency_graph_unknown: {
    headline: "Reuse blocked — impact dependencies unavailable",
    description: "The downstream impact graph could not be verified, so reuse remains blocked.",
  },
};

const fallbackReasonCopy: AssertionReasonCopy = {
  headline: "Reuse blocked — governed policy decision",
  description: "This governed assertion is unavailable.",
};

export function safeReasonCopy(reasonCode: string): string {
  return (assertionReasonCopy[reasonCode] ?? fallbackReasonCopy).description;
}

export function safeReasonHeadline(reasonCode: string | null | undefined): string {
  const copy = reasonCode ? assertionReasonCopy[reasonCode] : undefined;
  return (copy ?? fallbackReasonCopy).headline;
}
