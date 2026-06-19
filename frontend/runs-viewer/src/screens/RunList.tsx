/**
 * RunListScreen — run list surface (P3).
 *
 * Renders one RunCard per run returned by useRunList().
 * Filter tabs (All | Verified | Needs Review | Failed | Planned) filter the
 * displayed cards without page navigation.
 *
 * Navigation: clicking a RunCard navigates to /runs/:runId (RunDetailScreen).
 *
 * Data: useRunList() returns RFRunSummary[] sourced from the static fixture
 * (or loopback API). The 4 nested runs/runs/ runs appear here when the
 * fixture/API includes them; this screen renders whatever useRunList returns.
 *
 * R-P1 compliance: propagation_contract for "all runs" (FR-3) is enforced by
 * the data layer (useRunList → fetchRunList); this screen renders the full
 * returned set before filtering.
 */

import { useState, useMemo } from "react";
import { useNavigate }        from "react-router-dom";
import { useRunList }          from "@/hooks";
import { RunCard, deriveFilterState } from "@/components/RunList/RunCard";
import type { RunCardData }    from "@/components/RunList/RunCard";
import { FilterTabs }          from "@/components/RunList/FilterTabs";
import type { FilterTab }      from "@/components/RunList/FilterTabs";

// ── Component ─────────────────────────────────────────────────────────────────

export function RunListScreen() {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useRunList();

  const [activeTab, setActiveTab] = useState<FilterTab>("all");

  // Map RFRunSummary → RunCardData (adding optional fields that may be absent
  // in summary mode — they default to undefined which renders gracefully).
  const cards: RunCardData[] = useMemo(
    () =>
      (runs ?? []).map((r) => ({
        ...r,
        // schema_version_mismatch is not in RFRunSummary but RunCardData accepts it
        // as optional — renders badge only when explicitly true.
      })),
    [runs],
  );

  // Compute per-tab counts for the tab badges
  const tabCounts = useMemo(() => {
    const counts: Partial<Record<FilterTab, number>> = { all: cards.length };
    for (const card of cards) {
      const state = deriveFilterState(card.status_derived);
      counts[state] = (counts[state] ?? 0) + 1;
    }
    return counts;
  }, [cards]);

  // Filtered set
  const visible = useMemo(() => {
    if (activeTab === "all") return cards;
    return cards.filter(
      (c) => deriveFilterState(c.status_derived) === activeTab,
    );
  }, [cards, activeTab]);

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="rv-run-list">
        <div className="rv-loading" data-testid="run-list-loading">
          <p>Loading runs…</p>
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className="rv-run-list">
        <div className="rv-error" data-testid="run-list-error">
          <p>Error loading runs: {error instanceof Error ? error.message : "Unknown error"}</p>
        </div>
      </div>
    );
  }

  // ── Empty list ──
  if (cards.length === 0) {
    return (
      <div className="rv-run-list">
        <div className="rv-run-list__header">
          <h1 className="rv-run-list__title">Research Runs</h1>
        </div>
        <div className="rv-run-list__empty" data-testid="run-list-empty">
          <p>No runs found. Run <code>rf run export --json --all</code> to generate run exports.</p>
        </div>
      </div>
    );
  }

  // ── Full list ──
  return (
    <div className="rv-run-list" data-testid="run-list">
      {/* Page header */}
      <div className="rv-run-list__header">
        <h1 className="rv-run-list__title">Research Runs</h1>
        <span className="rv-run-list__count" data-testid="run-count">
          {cards.length} {cards.length === 1 ? "run" : "runs"}
        </span>
      </div>

      {/* Filter tabs */}
      <FilterTabs
        active={activeTab}
        counts={tabCounts}
        onChange={setActiveTab}
      />

      {/* Cards */}
      {visible.length === 0 ? (
        <div className="rv-run-list__no-match" data-testid="run-list-no-match">
          <p>No runs match the selected filter.</p>
        </div>
      ) : (
        <ul className="rv-run-list__grid" role="list" data-testid="run-list-grid">
          {visible.map((card) => (
            <li key={card.run_id}>
              <RunCard
                run={card}
                onClick={(runId) => navigate(`/runs/${encodeURIComponent(runId)}`)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default RunListScreen;
