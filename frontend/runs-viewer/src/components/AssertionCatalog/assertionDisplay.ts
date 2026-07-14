/**
 * Display-derivation helpers for the reusable assertion ledger reviewer
 * experience (P6-002 — Catalog + Provenance packet discovery/detail).
 *
 * These are pure functions only. They never fabricate values: unknown enum
 * members render `Unavailable (<value>)` (spec §4.2/§8) and absent fields are
 * simply omitted by the caller rather than defaulted here.
 *
 * Packet lifecycle selection belongs to `useAssertions.ts::selectPacketLifecycle`
 * so all packet consumers use the same assertion-first, freshness-fallback
 * interpretation.
 */
import type { RightsDecision } from "@/types/rf/assertions_api.generated";

export interface ChipDisplay {
  label: string;
  color: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Narrow, defensive string read from a Record<string, unknown> packet map. Tries keys in order. */
export function readString(obj: Record<string, unknown> | undefined, ...keys: string[]): string | undefined {
  if (!obj) return undefined;
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return undefined;
}

export function readNumber(obj: Record<string, unknown> | undefined, ...keys: string[]): number | undefined {
  if (!obj) return undefined;
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === "number") return value;
  }
  return undefined;
}

export function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

const LIFECYCLE_DISPLAY: Record<string, ChipDisplay> = {
  eligible: { label: "Current", color: "green" },
  stale: { label: "Stale", color: "orange" },
  invalidated: { label: "Invalid", color: "red" },
  tombstoned: { label: "Retracted", color: "red" },
  blocked: { label: "Blocked", color: "red" },
};

export function lifecycleDisplay(state: string | null | undefined): ChipDisplay {
  if (!state) return { label: "Unavailable", color: "" };
  return LIFECYCLE_DISPLAY[state] ?? { label: `Unavailable (${state})`, color: "" };
}

// ── Access scope ─────────────────────────────────────────────────────────────
// Real values per src/research_foundry/services/assertion_catalog.py::_rights_decision:
// public | personal | work_sensitive | client_sensitive | private. (The mockup's
// "Access: Workspace" label does not correspond to any of these — see report.)

const ACCESS_SCOPE_DISPLAY: Record<string, ChipDisplay> = {
  public: { label: "Public", color: "green" },
  personal: { label: "Personal", color: "blue" },
  work_sensitive: { label: "Work sensitive", color: "orange" },
  client_sensitive: { label: "Client sensitive", color: "red" },
  private: { label: "Private", color: "purple" },
};

export function accessScopeDisplay(scope: string | null | undefined): ChipDisplay {
  if (!scope) return { label: "Unavailable", color: "" };
  return ACCESS_SCOPE_DISPLAY[scope] ?? { label: `Unavailable (${scope})`, color: "" };
}

// ── Reuse decision (rights_decision) ──────────────────────────────────────────

export function reuseDecisionDisplay(rights: RightsDecision | null | undefined): ChipDisplay & { reasonCode?: string } {
  if (!rights) return { label: "Unavailable", color: "" };
  if (rights.allowed) return { label: "Eligible for reuse", color: "green" };
  return { label: "Reuse blocked", color: "red", reasonCode: rights.reason_code };
}

// ── Evaluation ───────────────────────────────────────────────────────────────

const EVALUATION_KIND_LABEL: Record<string, string> = {
  grounding: "Grounding",
  atomicity: "Atomicity",
  qualifier_completeness: "Qualifier completeness",
  human_review: "Human review",
  reuse_eligibility: "Reuse eligibility",
};

export function evaluationKindLabel(kind: unknown): string {
  if (typeof kind !== "string" || !kind) return "Unavailable";
  return EVALUATION_KIND_LABEL[kind] ?? `Unavailable (${kind})`;
}

const VERDICT_DISPLAY: Record<string, ChipDisplay> = {
  pass: { label: "Pass", color: "green" },
  fail: { label: "Fail", color: "red" },
  needs_review: { label: "Needs review", color: "orange" },
  abstain: { label: "Abstain", color: "" },
};

export function verdictDisplay(verdict: unknown): ChipDisplay {
  if (typeof verdict !== "string" || !verdict) return { label: "Unavailable", color: "" };
  return VERDICT_DISPLAY[verdict] ?? { label: `Unavailable (${verdict})`, color: "" };
}

// ── Qualifiers ───────────────────────────────────────────────────────────────
// Known fields per SourceAssertion.qualifiers (source_assertion.generated.ts).
// The mockup's "Population / Metric / Comparator / Timeframe" labels do not
// match this generated schema (no "metric"/"comparator" qualifier exists) —
// rendered from the real field names instead (see report).

const QUALIFIER_FIELDS: { key: string; label: string }[] = [
  { key: "population", label: "Population" },
  { key: "geography", label: "Geography" },
  { key: "timeframe", label: "Timeframe" },
  { key: "modality", label: "Modality" },
  { key: "intervention_or_exposure", label: "Intervention / exposure" },
  { key: "outcome", label: "Outcome" },
  { key: "negation", label: "Negation" },
];

export interface DisplayRow {
  label: string;
  value: string;
}

export function knownQualifierRows(qualifiers: Record<string, unknown> | undefined): DisplayRow[] {
  if (!qualifiers) return [];
  const rows: DisplayRow[] = [];
  for (const { key, label } of QUALIFIER_FIELDS) {
    const value = qualifiers[key];
    if (value === null || value === undefined || value === "") continue;
    rows.push({ label, value: typeof value === "boolean" ? (value ? "Yes" : "No") : String(value) });
  }
  return rows;
}

export function humanizeKey(key: string): string {
  return key
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Unknown qualifier_extensions keys, rendered after known qualifiers (spec §5.2). */
export function extensionRows(extensions: Record<string, unknown> | undefined): DisplayRow[] {
  if (!extensions) return [];
  return Object.entries(extensions)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => ({
      label: humanizeKey(key),
      value: typeof value === "string" ? value : typeof value === "boolean" ? (value ? "Yes" : "No") : JSON.stringify(value),
    }));
}

// ── Passage locator ────────────────────────────────────────────────────────

export function passageSelectorLocator(selectors: unknown): string | null {
  if (!Array.isArray(selectors) || selectors.length === 0) return null;
  const parts = selectors
    .map((s) => (isRecord(s) ? asString(s.value) : undefined))
    .filter((v): v is string => Boolean(v));
  return parts.length ? parts.join(" · ") : null;
}
