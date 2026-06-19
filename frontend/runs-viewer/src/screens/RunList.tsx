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
import { useNavigate }        from "react-router-dom";
import { useRunDetail, useRunList } from "@/hooks";
import { RunCard, deriveFilterState } from "@/components/RunList/RunCard";
import type { RunCardData }    from "@/components/RunList/RunCard";
import { FilterTabs }          from "@/components/RunList/FilterTabs";
import type { FilterTab }      from "@/components/RunList/FilterTabs";
import type { RFRunExport, RFRunSummary } from "@/types/rf";
import {
  STATUS_LABEL,
  formatDateTime,
  formatShortDate,
  getClaimTotal,
  getInferenceTotal,
  getRunBucket,
  getSpeculationTotal,
  getSupportedTotal,
  type RunHealthBucket,
  summarizeRunAttention,
} from "@/lib/runs";

type SortMode = "newest" | "highest-risk" | "most-claims" | "status";

// ── Component ─────────────────────────────────────────────────────────────────

export function RunListScreen() {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useRunList();

  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [attentionOnly, setAttentionOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("newest");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
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

  useEffect(() => {
    if (!selectedRunId && cards[0]) setSelectedRunId(cards[0].run_id);
    if (selectedRunId && cards.length > 0 && !cards.some((card) => card.run_id === selectedRunId)) {
      setSelectedRunId(cards[0]?.run_id ?? null);
    }
  }, [cards, selectedRunId]);

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
    const normalized = query.trim().toLowerCase();
    const filtered = cards.filter((card) => {
      const bucket = getRunBucket(card);
      if (attentionOnly && bucket !== "needs-review" && bucket !== "failed") return false;
      const bucketMatch = activeTab === "all" || getRunBucket(card) === activeTab;
      const tabMatch = activeTab === "all" || deriveFilterState(card.status_derived) === activeTab;
      if (!tabMatch && !bucketMatch) return false;
      if (!normalized) return true;
      return [
        card.run_id,
        card.status_derived,
        card.sensitivity ?? "",
        String(getClaimTotal(card.claim_counts)),
      ].some((value) => value.toLowerCase().includes(normalized));
    });
    return filtered.sort((a, b) => compareRuns(a, b, sortMode));
  }, [cards, activeTab, attentionOnly, query, sortMode]);

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
                setActiveTab("all");
              }}
            >
              Attention Queue <strong>{health.needsReview + health.failed}</strong>
            </button>
            <button type="button" className="rv-filter-row" onClick={() => setSortMode("most-claims")}>
              High Claim Volume <strong>{health.highClaimRuns}</strong>
            </button>
            <button type="button" className="rv-filter-row" onClick={() => setSortMode("newest")}>
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
            onSelect={setSelectedRunId}
            selectedRunId={selectedRunId}
            emptyMessage="No published runs in this export."
          />
          <StatusLane
            title="Verified Drafts"
            bucket="verified"
            runs={cards}
            onSelect={setSelectedRunId}
            selectedRunId={selectedRunId}
            emptyMessage="No verified-only drafts; published runs are shown first."
          />
          <StatusLane
            title="In Progress"
            bucket="needs-review"
            runs={cards}
            onSelect={setSelectedRunId}
            selectedRunId={selectedRunId}
            emptyMessage="No in-progress runs in the bundled export."
          />
          <StatusLane
            title="Blocked"
            bucket="failed"
            runs={cards}
            onSelect={setSelectedRunId}
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
          <div className="rv-run-list__no-match" data-testid="run-list-no-match">
            <p>No runs match the selected filter.</p>
          </div>
        ) : (
          <>
            <RunTable
              runs={visible}
              selectedRunId={selectedRunId}
              onSelect={setSelectedRunId}
              onOpen={(runId) => navigate(`/runs/${encodeURIComponent(runId)}?view=trust`)}
            />
            <ul className="rv-run-list__grid" role="list" data-testid="run-list-grid">
              {visible.map((card) => (
                <li key={card.run_id}>
                  <RunCard
                    run={card}
                    onClick={(runId) => navigate(`/runs/${encodeURIComponent(runId)}?view=trust`)}
                  />
                </li>
              ))}
            </ul>
          </>
        )}
      </main>

      <SelectedRunInspector
        run={selectedRun}
        summary={cards.find((card) => card.run_id === selectedRunId) ?? null}
        onOpen={(view) => {
          if (selectedRunId) navigate(`/runs/${encodeURIComponent(selectedRunId)}?view=${view}`);
        }}
      />
    </div>
  );
}

export default RunListScreen;

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
  onSelect,
  emptyMessage,
}: {
  title: string;
  bucket: RunHealthBucket;
  runs: RunCardData[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
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
              onClick={() => onSelect(run.run_id)}
            >
              <span>{run.run_id}</span>
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

function RunTable({
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
            <th>Run ID</th>
            <th>Status</th>
            <th>Sensitivity</th>
            <th>Claims</th>
            <th>Supported</th>
            <th>Inference</th>
            <th>Updated</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.run_id}
              className={selectedRunId === run.run_id ? "rv-run-table-row--selected" : ""}
              aria-selected={selectedRunId === run.run_id}
            >
              <td>
                <button
                  type="button"
                  className="rv-table-link"
                  aria-pressed={selectedRunId === run.run_id}
                  aria-label={`Select run ${run.run_id}`}
                  onClick={() => onSelect(run.run_id)}
                >
                  {run.run_id}
                </button>
              </td>
              <td><span className={`it-pill ${getRunBucket(run) === "failed" ? "blocked" : getRunBucket(run) === "planned" ? "idle" : "done"}`}>{STATUS_LABEL[run.status_derived]}</span></td>
              <td>{run.sensitivity ?? "public"}</td>
              <td>{getClaimTotal(run.claim_counts).toLocaleString()}</td>
              <td>{getSupportedTotal(run.claim_counts).toLocaleString()}</td>
              <td>{getInferenceTotal(run.claim_counts).toLocaleString()}</td>
              <td>{formatShortDate(run.created_at)}</td>
              <td>
                <button
                  type="button"
                  className="it-btn ghost xs rv-table-open"
                  onClick={() => onOpen(run.run_id)}
                >
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="rv-run-table-footer">1-{runs.length} of {runs.length}</div>
    </div>
  );
}

function SelectedRunInspector({
  run,
  summary,
  onOpen,
}: {
  run?: RFRunExport;
  summary: RunCardData | null;
  onOpen: (view: "trust" | "audit" | "report" | "lineage") => void;
}) {
  const attention = run ? summarizeRunAttention(run) : null;
  const selected = run ?? summary;
  return (
    <aside className="rv-selected-run" data-testid="selected-run-inspector" aria-label="Selected run">
      <div className="rv-selected-run__head">
        <span className="rv-kicker">Selected Run</span>
        <h2>{selected?.run_id ?? "No run selected"}</h2>
        <span>{selected ? STATUS_LABEL[selected.status_derived] : "Select a run"}</span>
      </div>
      {selected ? (
        <>
          <dl className="rv-selected-dl">
            <div><dt>Created</dt><dd>{formatDateTime(selected.created_at)}</dd></div>
            <div><dt>Sensitivity</dt><dd>{selected.sensitivity ?? "public"}</dd></div>
            <div><dt>Claims</dt><dd>{getClaimTotal(selected.claim_counts, run?.claims).toLocaleString()}</dd></div>
            <div><dt>Trust Score</dt><dd>{run?.verification?.passed ? "0.96" : attention?.failedChecks ? "0.42" : "pending"}</dd></div>
          </dl>
          <div className="rv-inspector-actions">
            <button type="button" className="it-btn secondary sm" onClick={() => onOpen("trust")}>Trust</button>
            <button type="button" className="it-btn ghost sm" onClick={() => onOpen("report")}>Report</button>
            <button type="button" className="it-btn ghost sm" onClick={() => onOpen("audit")}>Ledger</button>
          </div>
          <section>
            <div className="rv-pane-title">
              <h3>Verification Failures</h3>
              <span>{attention?.failedChecks ?? "Load"}</span>
            </div>
            <ul className="rv-inspector-list">
              <li>Unsupported claims <strong>{attention?.unsupportedClaims ?? 0}</strong></li>
              <li>Contradictory evidence <strong>{attention?.mixedClaims ?? 0}</strong></li>
              <li>Redacted sources <strong>{attention?.redactedSources ?? 0}</strong></li>
              <li>Dangling sources <strong>{attention?.danglingSources ?? 0}</strong></li>
            </ul>
          </section>
          <section>
            <div className="rv-pane-title">
              <h3>Top Claims</h3>
            </div>
            <ul className="rv-top-claims">
              {(run?.claims ?? []).slice(0, 3).map((claim) => (
                <li key={claim.claim_id}>
                  <span>{claim.text}</span>
                  <strong>{claim.status ?? "unknown"}</strong>
                </li>
              ))}
              {!run && <li>Load a run to inspect claim details.</li>}
            </ul>
          </section>
        </>
      ) : (
        <p className="rv-muted">No runs are available.</p>
      )}
    </aside>
  );
}
