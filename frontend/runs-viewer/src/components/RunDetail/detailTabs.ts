export type DetailTab = "overview" | "trust" | "ledger" | "report" | "lineage" | "writeback";

export function coerceDetailTab(value: string | null): DetailTab {
  if (value === "audit" || value === "ledger") return "ledger";
  if (value === "overview" || value === "trust" || value === "report" || value === "lineage" || value === "writeback") {
    return value;
  }
  return "trust";
}

export function tabToQuery(tab: DetailTab): string {
  return tab === "ledger" ? "audit" : tab;
}
