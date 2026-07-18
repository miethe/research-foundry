/**
 * RunListScreen — run list surface (P3).
 *
 * Renders one RunCard per run returned by useRunList().
 * Filter tabs (All | Verified | Needs Review | Planned) filter the
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

import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import type { ShellSelectionContext } from "@/app/shellContext";
import { useRunDetail, useRunList } from "@/hooks";
import { RunDetailModal }      from "@/components/RunDetail/RunDetailModal";
import { RunCard, deriveFilterState } from "@/components/RunList/RunCard";
import type { RunCardData }    from "@/components/RunList/RunCard";
import { FilterTabs }          from "@/components/RunList/FilterTabs";
import type { FilterTab, MetadataFilterOptions, MetadataFilterState } from "@/components/RunList/FilterTabs";
import type { RFRunSummary } from "@/types/rf";
import {
  STATUS_LABEL,
  formatShortDate,
  getClaimTotal,
  getInferenceTotal,
  getRunBucket,
  getSpeculationTotal,
  getSupportedTotal,
  titleFromSlug,
  type RunHealthBucket,
  summarizeRunAttention,
} from "@/lib/runs";

type SortMode = "newest" | "highest-risk" | "most-claims" | "status";

// ── Component ─────────────────────────────────────────────────────────────────

export function RunListScreen() {
  const { data: runs, isLoading, error } = useRunList();
  const shellSelection = useOutletContext<ShellSelectionContext | null>();

  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [attentionOnly, setAttentionOnly] = useState(false);
  const [highClaimOnly, setHighClaimOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("newest");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [modalRunId, setModalRunId] = useState<string | null>(null);

  // P6 — metadata filter state (FILT-001)
  const [metadataFilters, setMetadataFilters] = useState<MetadataFilterState>({
    activeLinkedProjects: [],
    activeCategories: [],
    activeTags: [],
  });
  const { data: selectedRun } = useRunDetail(selectedRunId ?? "");

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

  // P6 — derive facet option lists dynamically from loaded runs (FILT-002).
  // Null-safe: runs missing a field don't contribute to the option list.
  const metadataOptions: MetadataFilterOptions = useMemo(() => {
    const projects = new Set<string>();
    const categories = new Set<string>();
    const tags = new Set<string>();
    for (const card of cards) {
      card.linked_projects?.forEach((p) => p && projects.add(p));
      if (card.category) categories.add(card.category);
      card.tags?.forEach((t) => t && tags.add(t));
    }
    return {
      linkedProjects: Array.from(projects).sort(),
      categories: Array.from(categories).sort(),
      tags: Array.from(tags).sort(),
    };
  }, [cards]);

  useEffect(() => {
    if (!selectedRunId && cards[0]) setSelectedRunId(cards[0].run_id);
    if (selectedRunId && cards.length > 0 && !cards.some((card) => card.run_id === selectedRunId)) {
      setSelectedRunId(cards[0]?.run_id ?? null);
    }
  }, [cards, selectedRunId]);

  useEffect(() => {
    shellSelection?.setSelectedRunId(selectedRunId);
  }, [selectedRunId, shellSelection]);

  useEffect(() => () => shellSelection?.setSelectedRunId(null), [shellSelection]);

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
    const { activeLinkedProjects, activeCategories, activeTags } = metadataFilters;
    const normalized = query.trim().toLowerCase();
    const filtered = cards.filter((card) => {
      const bucket = getRunBucket(card);
      if (attentionOnly && bucket !== "needs-review" && bucket !== "failed") return false;
      if (highClaimOnly && getClaimTotal(card.claim_counts) < 75) return false;
      const bucketMatch = activeTab === "all" || getRunBucket(card) === activeTab;
      const tabMatch = activeTab === "all" || deriveFilterState(card.status_derived) === activeTab;
      if (!tabMatch && !bucketMatch) return false;

      // P6 — AND-logic metadata filter (FILT-003).
      // Runs with null fields fail a non-empty filter (they have no matching values).
      if (activeLinkedProjects.length > 0) {
        const runProjects = card.linked_projects ?? [];
        const hasMatch = runProjects.some((p) => activeLinkedProjects.includes(p));
        if (!hasMatch) return false;
      }
      if (activeCategories.length > 0) {
        if (!card.category || !activeCategories.includes(card.category)) return false;
      }
      if (activeTags.length > 0) {
        const runTags = card.tags ?? [];
        const hasMatch = runTags.some((t) => activeTags.includes(t));
        if (!hasMatch) return false;
      }

      if (!normalized) return true;
      return [
        card.title ?? "",
        card.run_id,
        card.status_derived,
        card.sensitivity ?? "",
        String(getClaimTotal(card.claim_counts)),
      ].some((value) => value.toLowerCase().includes(normalized));
    });
    return filtered.sort((a, b) => compareRuns(a, b, sortMode));
  }, [cards, activeTab, attentionOnly, highClaimOnly, query, sortMode, metadataFilters]);

  const health = useMemo(() => summarizePortfolio(cards), [cards]);

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

  // ── Full portfolio ──
  return (
    <div className="rv-portfolio" data-testid="run-list">
      <aside className="rv-portfolio-rail" aria-label="Portfolio navigation">
        <div className="rv-rail-brand">
          <span className="rv-mark" aria-hidden="true">RF</span>
          <div>
            <strong>Research Runs</strong>
            <span>Evidence operations</span>
          </div>
        </div>
        <div className="rv-rail-section">
          <h2>Saved Views</h2>
          <FilterTabs
            active={activeTab}
            counts={tabCounts}
            onChange={(tab) => {
              setAttentionOnly(false);
              setActiveTab(tab);
            }}
            metadataFilters={metadataFilters}
            metadataOptions={metadataOptions}
            onMetadataFilterChange={setMetadataFilters}
          />
        </div>
        <div className="rv-rail-section">
          <h2>Filters</h2>
          <div className="rv-filter-stack">
            <button
              type="button"
              className={`rv-filter-row${attentionOnly ? " active" : ""}`}
              onClick={() => {
                setAttentionOnly(true);
                setHighClaimOnly(false);
                setActiveTab("all");
              }}
            >
              Attention Queue <strong>{health.needsReview + health.failed}</strong>
            </button>
            <button
              type="button"
              className={`rv-filter-row${highClaimOnly ? " active" : ""}`}
              onClick={() => {
                setHighClaimOnly((current) => !current);
                setAttentionOnly(false);
                setActiveTab("all");
                setSortMode("most-claims");
              }}
              aria-pressed={highClaimOnly}
            >
              High Claim Volume <strong>{health.highClaimRuns}</strong>
            </button>
            <button
              type="button"
              className="rv-filter-row rv-filter-row--disabled"
              disabled
              aria-disabled="true"
              title="This export does not include a stable current-week window."
            >
              This Week <strong>{cards.length}</strong>
            </button>
          </div>
        </div>
        <div className="rv-threshold-card">
          <span>Sensitivity threshold</span>
          <strong>{selectedRun?.sensitivity_threshold ?? cards[0]?.sensitivity ?? "public"}</strong>
        </div>
      </aside>

      <main className="rv-portfolio-main">
        <div className="rv-portfolio-header">
          <div>
            <span className="rv-kicker">Portfolio Command Center</span>
            <h1>Research Runs</h1>
            <p>Evidence-first research runs at a glance</p>
          </div>
          <div className="rv-portfolio-controls">
            <label className="rv-search">
              <span>Search runs</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Run id, status, sensitivity..."
                data-testid="portfolio-search"
              />
            </label>
            <label className="rv-select">
              <span>Sort</span>
              <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)} data-testid="portfolio-sort">
                <option value="newest">Newest</option>
                <option value="highest-risk">Highest risk</option>
                <option value="most-claims">Most claims</option>
                <option value="status">Status</option>
              </select>
            </label>
          </div>
        </div>

        <section className="rv-health-strip" aria-label="Corpus health metrics">
          <HealthTile label="Total Runs" value={cards.length} detail={`${visible.length} visible`} />
          <HealthTile label="Verified" value={health.verified} tone="green" detail={`${health.published} published`} />
          <HealthTile label="Needs Review" value={health.needsReview} tone="orange" detail="Derived from lifecycle" />
          <HealthTile label="Failed" value={health.failed} tone="red" detail="Claims or checks flagged" />
          <HealthTile label="Total Claims" value={health.claims} tone="blue" detail={`${health.sources} source cards`} />
          <HealthTile label="Evidence Items" value={health.evidence} tone="teal" detail="Source + extraction counts" />
        </section>

        <section className="rv-status-lanes" aria-label="Status lanes">
          <StatusLane
            title="Published / Verified"
            bucket="published"
            runs={cards}
            onOpen={(runId) => {
              setSelectedRunId(runId);
              setModalRunId(runId);
            }}
            selectedRunId={selectedRunId}
            emptyMessage="No published runs in this export."
          />
          <StatusLane
            title="Verified Drafts"
            bucket="verified"
            runs={cards}
            onOpen={(runId) => {
              setSelectedRunId(runId);
              setModalRunId(runId);
            }}
            selectedRunId={selectedRunId}
            emptyMessage="No verified-only drafts; published runs are shown first."
          />
          <StatusLane
            title="In Progress"
            bucket="needs-review"
            runs={cards}
            onOpen={(runId) => {
              setSelectedRunId(runId);
              setModalRunId(runId);
            }}
            selectedRunId={selectedRunId}
            emptyMessage="No in-progress runs in the bundled export."
          />
          <StatusLane
            title="Blocked"
            bucket="failed"
            runs={cards}
            onOpen={(runId) => {
              setSelectedRunId(runId);
              setModalRunId(runId);
            }}
            selectedRunId={selectedRunId}
            emptyMessage="No failed or blocked runs in the bundled export."
          />
        </section>

        <section className="rv-attention-queue it-card" aria-label="Attention queue">
          <div className="rv-pane-title">
            <h2>Attention Queue</h2>
            <button
              type="button"
              className="it-btn ghost sm"
              onClick={() => {
                setAttentionOnly(true);
                setHighClaimOnly(false);
                setActiveTab("all");
              }}
            >
              Open queue
            </button>
          </div>
          <div className="rv-attention-grid">
            <AttentionCard label="Schema Drift" value={health.schemaDrift} />
            <AttentionCard label="Redacted Evidence" value={selectedRun ? summarizeRunAttention(selectedRun).redactedSources : 0} />
            <AttentionCard label="Low Trust Score" value={health.failed + health.needsReview} />
          </div>
        </section>

        {visible.length === 0 ? (
          <MetadataEmptyState
            hasMetadataFilters={
              metadataFilters.activeLinkedProjects.length > 0 ||
              metadataFilters.activeCategories.length > 0 ||
              metadataFilters.activeTags.length > 0
            }
            onClearFilters={() =>
              setMetadataFilters({ activeLinkedProjects: [], activeCategories: [], activeTags: [] })
            }
          />
        ) : (
          <>
            <RunTable
              runs={visible}
              selectedRunId={selectedRunId}
              onSelect={setSelectedRunId}
              onOpen={(runId) => {
                setSelectedRunId(runId);
                setModalRunId(runId);
              }}
            />
            <ul className="rv-run-list__grid" role="list" data-testid="run-list-grid">
              {visible.map((card) => (
                <li key={card.run_id}>
                  <RunCard
                    run={card}
                    onClick={(runId) => {
                      setSelectedRunId(runId);
                      setModalRunId(runId);
                    }}
                    onExpandRun={(runId) => {
                      setSelectedRunId(runId);
                      setModalRunId(runId);
                    }}
                  />
                </li>
              ))}
            </ul>
          </>
        )}
      </main>

      <RunDetailModal runId={modalRunId} onClose={() => setModalRunId(null)} />
    </div>
  );
}

export default RunListScreen;

// ── P6: Graceful empty state when metadata filters match 0 runs (FILT-004) ────

function MetadataEmptyState({
  hasMetadataFilters,
  onClearFilters,
}: {
  hasMetadataFilters: boolean;
  onClearFilters: () => void;
}) {
  if (hasMetadataFilters) {
    return (
      <div className="rv-run-list__no-match rv-run-list__no-match--filters" data-testid="run-list-filter-empty">
        <p>No runs match the selected filters.</p>
        <button
          type="button"
          className="it-btn ghost sm"
          onClick={onClearFilters}
          data-testid="clear-filters-btn"
        >
          Clear filters
        </button>
      </div>
    );
  }
  return (
    <div className="rv-run-list__no-match" data-testid="run-list-no-match">
      <p>No runs match the selected filter.</p>
    </div>
  );
}

function compareRuns(a: RFRunSummary, b: RFRunSummary, sortMode: SortMode): number {
  if (sortMode === "most-claims") return getClaimTotal(b.claim_counts) - getClaimTotal(a.claim_counts);
  if (sortMode === "highest-risk") return riskScore(b) - riskScore(a);
  if (sortMode === "status") return getRunBucket(a).localeCompare(getRunBucket(b));
  return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
}

function riskScore(run: RFRunSummary): number {
  const bucket = getRunBucket(run);
  return (bucket === "failed" ? 1000 : bucket === "needs-review" ? 500 : 0) +
    getSpeculationTotal(run.claim_counts) * 4 +
    getInferenceTotal(run.claim_counts) * 2 +
    getClaimTotal(run.claim_counts);
}

function summarizePortfolio(runs: RFRunSummary[]) {
  return runs.reduce(
    (acc, run) => {
      const bucket = getRunBucket(run);
      if (bucket === "verified") acc.verified += 1;
      if (bucket === "published") {
        acc.verified += 1;
        acc.published += 1;
      }
      if (bucket === "needs-review") acc.needsReview += 1;
      if (bucket === "failed") acc.failed += 1;
      acc.claims += getClaimTotal(run.claim_counts);
      acc.sources += run.claim_counts?.source_cards ?? 0;
      acc.evidence += (run.claim_counts?.source_cards ?? 0) + (run.claim_counts?.extraction_cards ?? 0);
      if (getClaimTotal(run.claim_counts) >= 75) acc.highClaimRuns += 1;
      return acc;
    },
    { verified: 0, published: 0, needsReview: 0, failed: 0, claims: 0, sources: 0, evidence: 0, highClaimRuns: 0, schemaDrift: 0 },
  );
}

function HealthTile({ label, value, detail, tone = "neutral" }: { label: string; value: number; detail: string; tone?: string }) {
  return (
    <div className={`rv-health-tile rv-health-tile--${tone}`}>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <small>{detail}</small>
    </div>
  );
}

function StatusLane({
  title,
  bucket,
  runs,
  selectedRunId,
  onOpen,
  emptyMessage,
}: {
  title: string;
  bucket: RunHealthBucket;
  runs: RunCardData[];
  selectedRunId: string | null;
  /** Called on click — should both set selectedRunId AND open the modal. */
  onOpen: (runId: string) => void;
  emptyMessage: string;
}) {
  const laneRuns = runs.filter((run) => getRunBucket(run) === bucket).slice(0, 3);
  return (
    <div className={`rv-status-lane rv-status-lane--${bucket}`}>
      <div className="rv-status-lane__head">
        <h2>{title}</h2>
        <strong>{runs.filter((run) => getRunBucket(run) === bucket).length}</strong>
      </div>
      {laneRuns.length > 0 ? (
        <div className="rv-status-lane__items">
          {laneRuns.map((run) => (
            <button
              key={run.run_id}
              type="button"
              className={`rv-lane-run${selectedRunId === run.run_id ? " rv-lane-run--selected" : ""}`}
              onClick={() => onOpen(run.run_id)}
            >
              <span>{run.title ?? titleFromSlug(run.run_id) ?? run.run_id}</span>
              <strong>{getClaimTotal(run.claim_counts).toLocaleString()}</strong>
            </button>
          ))}
        </div>
      ) : (
        <p>{emptyMessage}</p>
      )}
    </div>
  );
}

function AttentionCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rv-attention-card">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}

export function RunTable({
  runs,
  selectedRunId,
  onSelect,
  onOpen,
}: {
  runs: RunCardData[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
  onOpen: (runId: string) => void;
}) {
  return (
    <div className="rv-run-table-wrap it-card" data-testid="portfolio-run-table">
      <table className="rv-run-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th className="rv-run-table__col-project">Project</th>
            <th>Sensitivity</th>
            <th>Claims</th>
            <th>Supported</th>
            <th>Inference</th>
            <th>Updated</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const projectText = run.linked_projects?.length
              ? run.linked_projects.join(", ")
              : null;
            const isSelected = selectedRunId === run.run_id;
            return (
              // D1: Entire row is keyboard-accessible and opens the run modal on click.
              // Inner buttons (title link, Open) use stopPropagation so they still work independently.
              <tr
                key={run.run_id}
                className={`rv-run-table-row--clickable${isSelected ? " rv-run-table-row--selected" : ""}`}
                aria-selected={isSelected}
                tabIndex={0}
                role="row"
                aria-label={`Open run: ${run.title ?? titleFromSlug(run.run_id) ?? run.run_id}`}
                onClick={() => onOpen(run.run_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onOpen(run.run_id);
                  }
                }}
                data-testid="run-table-row"
                data-run-id={run.run_id}
              >
                <td>
                  <button
                    type="button"
                    className="rv-table-link"
                    aria-pressed={isSelected}
                    aria-label={`Select run ${run.title ?? titleFromSlug(run.run_id) ?? run.run_id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(run.run_id);
                    }}
                  >
                    {run.title ?? titleFromSlug(run.run_id) ?? run.run_id}
                  </button>
                  <span className="rv-muted rv-table-run-id">{run.run_id}</span>
                </td>
                <td><span className={`it-pill ${getRunBucket(run) === "failed" ? "blocked" : getRunBucket(run) === "planned" ? "idle" : "done"}`}>{STATUS_LABEL[run.status_derived]}</span></td>
                <td className="rv-run-table__col-project" data-testid="run-table-project">
                  {projectText
                    ? <span className="it-chip blue rv-project-badge">{projectText}</span>
                    : <span className="rv-muted">—</span>}
                </td>
                <td>{run.sensitivity ?? "public"}</td>
                <td>{getClaimTotal(run.claim_counts).toLocaleString()}</td>
                <td>{getSupportedTotal(run.claim_counts).toLocaleString()}</td>
                <td>{getInferenceTotal(run.claim_counts).toLocaleString()}</td>
                <td>{formatShortDate(run.created_at)}</td>
                <td>
                  {/* Keep 'Open' as a secondary affordance; stopPropagation avoids double-fire */}
                  <button
                    type="button"
                    className="it-btn ghost xs rv-table-open"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(run.run_id);
                    }}
                    aria-label={`Open run ${run.title ?? titleFromSlug(run.run_id) ?? run.run_id}`}
                  >
                    Open
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="rv-run-table-footer">1-{runs.length} of {runs.length}</div>
    </div>
  );
}
