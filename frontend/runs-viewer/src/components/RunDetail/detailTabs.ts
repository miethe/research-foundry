import { getViewerSettings } from "../../lib/viewerSettings";

export type DetailTab = "overview" | "trust" | "ledger" | "report" | "lineage" | "writeback" | "context";

export function coerceDetailTab(value: string | null): DetailTab {
  if (value === "audit" || value === "ledger") return "ledger";
  // "swarm" is a legacy alias — forward to "context" (FR-14 tab rename).
  if (value === "swarm") return "context";
  if (
    value === "overview" ||
    value === "trust" ||
    value === "report" ||
    value === "lineage" ||
    value === "writeback" ||
    value === "context"
  ) {
    return value;
  }
  // G5: Read stored default tab before falling back to 'overview' (AC G5-05).
  // getViewerSettings() validates and defaults to 'overview' — safe to return directly.
  return getViewerSettings().defaultTab;
}

export function tabToQuery(tab: DetailTab): string {
  return tab === "ledger" ? "audit" : tab;
}
