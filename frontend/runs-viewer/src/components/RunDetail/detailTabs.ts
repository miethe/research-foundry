import { getViewerSettings } from "../../lib/viewerSettings";

export type DetailTab = "overview" | "trust" | "ledger" | "report" | "lineage" | "writeback" | "swarm";

export function coerceDetailTab(value: string | null): DetailTab {
  if (value === "audit" || value === "ledger") return "ledger";
  if (
    value === "overview" ||
    value === "trust" ||
    value === "report" ||
    value === "lineage" ||
    value === "writeback" ||
    value === "swarm"
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
