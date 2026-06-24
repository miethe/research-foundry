/**
 * PoliciesScreen — Governance + Per-Run Governance (G2, Wave-2 Policies tab).
 *
 * Accessible at /policies. Displays:
 *   1. Global Governance Panel — key profiles + policy rules from governance.json
 *      (static snapshot baked at build time from config/governance.yaml).
 *   2. Per-Run Governance Table — runs from index.json with per-run governance
 *      columns drawn from RFGovernanceBlock (sensitivity, approved_for_writeback,
 *      allowed_writebacks, requires_human_review).
 *
 * Graceful empty states:
 *   - If governance.json is absent/empty: shows "No governance config found" message.
 *   - If a run has no governance block: all columns show "—" for that row.
 *   - If index is empty: shows "No runs found" message.
 *
 * Data dependency: allowed_writebacks and requires_human_review require
 * export_service.py AC-4 changes + re-export. Older runs will show "—" for
 * these two columns; this is expected and documented behavior.
 */

import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import { fetchGovernanceConfig, fetchRunList, fetchRunDetail } from "@/api/client";
import type { GovernanceConfig, GovernancePolicyRule } from "@/types/governance";
import type { RFRunSummary } from "@/types/rf";
import type { RFGovernanceBlock } from "@/types/rf/run-export";
import "@/styles/policies.css";

// ── Governance Config hook ────────────────────────────────────────────────────

// eslint-disable-next-line react-refresh/only-export-components
export const governanceConfigQueryKey = ["rf", "governance", "config"] as const;

function useGovernanceConfig() {
  return useQuery<GovernanceConfig, Error>({
    queryKey: governanceConfigQueryKey,
    queryFn: fetchGovernanceConfig,
    staleTime: 300_000, // 5 min — static file
  });
}

// ── Per-run governance data hook ──────────────────────────────────────────────

interface RunGovernanceRow {
  run_id: string;
  governance: RFGovernanceBlock | null;
  loading: boolean;
}

function useRunGovernanceRows(summaries: RFRunSummary[]): RunGovernanceRow[] {
  // Single useQueries call — stable hook count regardless of summaries.length.
  // (A per-item useQuery loop violates Rules of Hooks and crashes when the
  //  run-list query resolves and the array length changes between renders.)
  const results = useQueries({
    queries: summaries.map((s) => ({
      queryKey: ["rf", "runs", "detail", s.run_id],
      queryFn: () => fetchRunDetail(s.run_id),
      staleTime: 60_000,
    })),
  });
  return summaries.map((s, i) => ({
    run_id: s.run_id,
    governance: (results[i]?.data?.governance as RFGovernanceBlock | null | undefined) ?? null,
    loading: results[i]?.isLoading ?? false,
  }));
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Render a boolean governance field as Yes / No / — */
function boolCell(value: boolean | null | undefined): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "—";
}

/** Render allowed_writebacks as comma-joined list or — */
function writebacksCell(value: string[] | null | undefined): string {
  if (!value || value.length === 0) return "—";
  return value.join(", ");
}

/** Render sensitivity or — */
function sensitivityCell(value: string | null | undefined): string {
  return value ?? "—";
}

// ── Sort state ────────────────────────────────────────────────────────────────

type SortKey = "sensitivity" | "approved_for_writeback";
type SortDir = "asc" | "desc";

// Matches RFSensitivity union values; higher rank = more sensitive
const SENSITIVITY_RANK: Record<string, number> = {
  public: 0,
  personal: 1,
  work_sensitive: 2,
  client_sensitive: 3,
};

function sensitivityRank(s: string | null | undefined): number {
  return SENSITIVITY_RANK[s ?? ""] ?? -1;
}

// ── Sub-components ────────────────────────────────────────────────────────────

// ── Global Governance Panel ──

interface GlobalGovernancePanelProps {
  config: GovernanceConfig | undefined;
  isLoading: boolean;
  error: Error | null;
}

function GlobalGovernancePanel({ config, isLoading, error }: GlobalGovernancePanelProps) {
  if (isLoading) {
    return (
      <div className="rv-policies__panel" data-testid="policies-gov-panel-loading">
        <div className="rv-loading">
          <p>Loading governance configuration…</p>
        </div>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div
        className="rv-policies__panel rv-policies__panel--empty"
        data-testid="policies-gov-panel-empty"
        role="note"
      >
        <p className="rv-policies__muted">
          No governance config found — governance.json not present in this build.
        </p>
      </div>
    );
  }

  const hasProfiles = config.key_profiles && Object.keys(config.key_profiles).length > 0;
  const hasRules = config.policy_rules && config.policy_rules.length > 0;

  if (!hasProfiles && !hasRules) {
    return (
      <div
        className="rv-policies__panel rv-policies__panel--empty"
        data-testid="policies-gov-panel-empty"
        role="note"
      >
        <p className="rv-policies__muted">
          No governance config found — governance.json not present in this build.
        </p>
      </div>
    );
  }

  return (
    <div className="rv-policies__panel" data-testid="policies-gov-panel">
      {/* Key Profiles */}
      {hasProfiles && config.key_profiles && (
        <div className="rv-policies__subsection" data-testid="policies-key-profiles">
          <h3 className="rv-policies__subsection-title">Key Profiles</h3>
          <table className="rv-policies__table" role="table">
            <thead>
              <tr>
                <th scope="col">Profile</th>
                <th scope="col">Settings</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(config.key_profiles).map(([name, value]) => (
                <tr key={name} data-testid="policies-profile-row">
                  <td className="rv-policies__cell rv-policies__cell--name">
                    <code>{name}</code>
                  </td>
                  <td className="rv-policies__cell">
                    <pre className="rv-policies__pre">
                      {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Policy Rules */}
      {hasRules && config.policy_rules && (
        <div className="rv-policies__subsection" data-testid="policies-policy-rules">
          <h3 className="rv-policies__subsection-title">Policy Rules</h3>
          <table className="rv-policies__table" role="table">
            <thead>
              <tr>
                <th scope="col">Rule ID</th>
                <th scope="col">Severity</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {config.policy_rules.map((rule: GovernancePolicyRule) => (
                <tr key={rule.id} data-testid="policies-rule-row">
                  <td className="rv-policies__cell">
                    <code>{rule.id}</code>
                  </td>
                  <td className="rv-policies__cell">
                    <span
                      className={`rv-policies__severity rv-policies__severity--${rule.severity ?? "info"}`}
                    >
                      {rule.severity ?? "—"}
                    </span>
                  </td>
                  <td className="rv-policies__cell">{rule.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Per-Run Governance Table ──

interface RunGovernanceTableProps {
  summaries: RFRunSummary[];
  rows: RunGovernanceRow[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
}

function RunGovernanceTable({
  summaries,
  rows,
  sortKey,
  sortDir,
  onSort,
}: RunGovernanceTableProps) {
  if (summaries.length === 0) {
    return (
      <div
        className="rv-policies__panel rv-policies__panel--empty"
        data-testid="policies-runs-empty"
        role="status"
      >
        <p className="rv-policies__muted">No runs found.</p>
      </div>
    );
  }

  const sortedRows = [...rows].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "sensitivity") {
      cmp = sensitivityRank(a.governance?.sensitivity) - sensitivityRank(b.governance?.sensitivity);
    } else if (sortKey === "approved_for_writeback") {
      const av = a.governance?.approved_for_writeback;
      const bv = b.governance?.approved_for_writeback;
      // true < false < null so approved runs sort first when asc
      const rank = (v: boolean | null | undefined) => (v === true ? 0 : v === false ? 1 : 2);
      cmp = rank(av) - rank(bv);
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  function sortIndicator(key: SortKey) {
    if (sortKey !== key) return null;
    return <span aria-hidden="true">{sortDir === "asc" ? " ▲" : " ▼"}</span>;
  }

  return (
    <div className="rv-policies__panel" data-testid="policies-runs-table-wrap">
      <table className="rv-policies__table rv-policies__table--runs" role="table">
        <thead>
          <tr>
            <th scope="col">Run ID</th>
            <th
              scope="col"
              className="rv-policies__sortable"
              aria-sort={sortKey === "sensitivity" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
              onClick={() => onSort("sensitivity")}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSort("sensitivity"); }}
              tabIndex={0}
              role="columnheader"
            >
              Sensitivity{sortIndicator("sensitivity")}
            </th>
            <th
              scope="col"
              className="rv-policies__sortable"
              aria-sort={sortKey === "approved_for_writeback" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
              onClick={() => onSort("approved_for_writeback")}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSort("approved_for_writeback"); }}
              tabIndex={0}
              role="columnheader"
            >
              Writeback Approved{sortIndicator("approved_for_writeback")}
            </th>
            <th scope="col">Allowed Writebacks</th>
            <th scope="col">Requires Human Review</th>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => {
            const gov = row.governance;
            return (
              <tr key={row.run_id} data-testid="policies-run-row">
                <td className="rv-policies__cell rv-policies__cell--run-id">
                  <Link
                    to={`/runs/${encodeURIComponent(row.run_id)}`}
                    className="rv-policies__run-link"
                    data-testid="policies-run-link"
                  >
                    {row.run_id}
                  </Link>
                </td>
                <td className="rv-policies__cell" data-testid="policies-cell-sensitivity">
                  {row.loading ? (
                    <span className="rv-policies__muted" aria-label="Loading">…</span>
                  ) : (
                    sensitivityCell(gov?.sensitivity)
                  )}
                </td>
                <td className="rv-policies__cell" data-testid="policies-cell-approved">
                  {row.loading ? (
                    <span className="rv-policies__muted" aria-label="Loading">…</span>
                  ) : (
                    boolCell(gov?.approved_for_writeback)
                  )}
                </td>
                <td className="rv-policies__cell" data-testid="policies-cell-writebacks">
                  {row.loading ? (
                    <span className="rv-policies__muted" aria-label="Loading">…</span>
                  ) : (
                    writebacksCell(gov?.allowed_writebacks)
                  )}
                </td>
                <td className="rv-policies__cell" data-testid="policies-cell-human-review">
                  {row.loading ? (
                    <span className="rv-policies__muted" aria-label="Loading">…</span>
                  ) : (
                    boolCell(gov?.requires_human_review)
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export function PoliciesScreen() {
  const [sortKey, setSortKey] = useState<SortKey>("sensitivity");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const {
    data: govConfig,
    isLoading: govLoading,
    error: govError,
  } = useGovernanceConfig();

  const {
    data: summaries,
    isLoading: indexLoading,
  } = useQuery<RFRunSummary[], Error>({
    queryKey: ["rf", "runs", "list"],
    queryFn: fetchRunList,
    staleTime: 60_000,
  });

  const runSummaries = useMemo(() => summaries ?? [], [summaries]);
  const rows = useRunGovernanceRows(runSummaries);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <div className="rv-policies" data-testid="policies-screen">
      <header className="rv-policies__header">
        <h1 className="rv-policies__title">Policies</h1>
      </header>

      {/* ── Global Governance Panel ── */}
      <section
        className="rv-policies__section"
        aria-labelledby="policies-gov-title"
        data-testid="policies-gov-section"
      >
        <h2 id="policies-gov-title" className="rv-policies__section-title">
          Governance Configuration
        </h2>
        <GlobalGovernancePanel
          config={govConfig}
          isLoading={govLoading}
          error={govError}
        />
      </section>

      {/* ── Per-Run Governance Table ── */}
      <section
        className="rv-policies__section"
        aria-labelledby="policies-runs-title"
        data-testid="policies-runs-section"
      >
        <h2 id="policies-runs-title" className="rv-policies__section-title">
          Run Governance Summary
        </h2>
        {indexLoading ? (
          <div className="rv-policies__panel" data-testid="policies-runs-loading">
            <div className="rv-loading">
              <p>Loading runs…</p>
            </div>
          </div>
        ) : (
          <RunGovernanceTable
            summaries={runSummaries}
            rows={rows}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
          />
        )}
      </section>
    </div>
  );
}

export default PoliciesScreen;
