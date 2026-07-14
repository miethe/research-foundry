/**
 * AssertionCatalogPane — CatalogScreen's "Source assertions" tab (P6-002).
 *
 * Owns local search/filter/selection state and wires the frozen
 * useAssertionSearch/useEvidencePacket seam (P6-001) into the new results
 * table + docked packet inspector. A denied search replaces the filters,
 * results, and inspector together with the bounded AssertionDeniedPanel
 * (spec §6.C, AC UX-3) — nothing candidate-derived remains.
 *
 * Pagination follows the real `next_cursor` (cursor-based) contract in
 * AssertionSearchResponse — there is no `total` field, so this renders
 * Previous/Next over a cursor stack rather than the numbered pager used by
 * the legacy catalog tabs (see report).
 */
import { useEffect, useMemo, useState } from "react";
import {
  useAssertionSearch,
  useClearAssertionStateOnWorkspaceChange,
  useEvidencePacket,
} from "@/hooks/useAssertions";
import type { AssertionSearchRequest } from "@/types/rf/assertions_api.generated";
import { EmptyState } from "@/components/shared/EmptyState";
import { AssertionResultsTable } from "./AssertionResultsTable";
import { AssertionPacketInspector } from "./AssertionPacketInspector";
import { AssertionDeniedPanel } from "./AssertionDeniedPanel";
import { accessScopeDisplay } from "./assertionDisplay";

const LIFECYCLE_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "eligible", label: "Current" },
  { value: "stale", label: "Stale" },
  // No backing lifecycle_state value exists yet for "Corrected" in the frozen
  // schema (SourceAssertion.lifecycle_state is eligible|stale|invalidated|
  // tombstoned) — the option is kept per spec §5.1's literal IA and will
  // simply return zero rows until the backend adds it. See report.
  { value: "corrected", label: "Corrected" },
  { value: "tombstoned", label: "Retracted" },
  { value: "invalidated", label: "Invalid" },
];

const PAGE_LIMIT = 20;

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

export function AssertionCatalogPane() {
  const [searchInput, setSearchInput] = useState("");
  const debouncedQuery = useDebouncedValue(searchInput, 250);
  const [lifecycleFilter, setLifecycleFilter] = useState("");
  const [accessFilter, setAccessFilter] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(() => typeof window === "undefined" || window.innerWidth >= 1100);
  const [cursorStack, setCursorStack] = useState<Array<string | null>>([null]);
  const [selectedAssertionId, setSelectedAssertionId] = useState<string | null>(null);

  useEffect(() => {
    setCursorStack([null]);
  }, [debouncedQuery, lifecycleFilter, accessFilter]);

  const cursor = cursorStack[cursorStack.length - 1] ?? null;

  const request: AssertionSearchRequest = useMemo(
    () => ({
      q: debouncedQuery || undefined,
      lifecycle_state: lifecycleFilter || undefined,
      access_scope: accessFilter || undefined,
      limit: PAGE_LIMIT,
      cursor: cursor ?? undefined,
    }),
    [debouncedQuery, lifecycleFilter, accessFilter, cursor],
  );

  const search = useAssertionSearch(request);

  const clearSelection = () => setSelectedAssertionId(null);
  useClearAssertionStateOnWorkspaceChange(clearSelection);

  const accessOptions = search.data?.facets.access_scopes ?? [];
  const searchState = search.state;
  // Denial is an atomic candidate-state boundary. Passing null immediately
  // disables the packet query; the effect then clears the retained local ID.
  const activeAssertionId = searchState.kind === "denied" ? null : selectedAssertionId;
  const packet = useEvidencePacket(activeAssertionId, clearSelection);

  useEffect(() => {
    if (searchState.kind === "denied") clearSelection();
  }, [searchState.kind]);

  if (searchState.kind === "denied") {
    return <AssertionDeniedPanel reasonCode={searchState.reasonCode} />;
  }

  return (
    <>
      <details
        className="rv-catalog-filters rv-assertion-filters"
        open={filtersOpen}
        onToggle={(event) => setFiltersOpen(event.currentTarget.open)}
      >
        <summary className="rv-assertion-filters__summary">Filters</summary>
        <div className="rv-assertion-filters__controls" role="search" aria-label="Filter source assertions">
        <label className="rv-catalog-filter rv-catalog-filter--search">
          <span>Search source assertions</span>
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search source assertions…"
            data-testid="assertion-search-input"
          />
        </label>
        <label className="rv-catalog-filter">
          <span>Lifecycle</span>
          <select
            value={lifecycleFilter}
            onChange={(e) => setLifecycleFilter(e.target.value)}
            data-testid="assertion-filter-lifecycle"
          >
            {LIFECYCLE_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="rv-catalog-filter">
          <span>Access scope</span>
          <select
            value={accessFilter}
            onChange={(e) => setAccessFilter(e.target.value)}
            data-testid="assertion-filter-access"
          >
            <option value="">All</option>
            {accessOptions.map((scope) => (
              <option key={scope} value={scope}>
                {accessScopeDisplay(scope).label}
              </option>
            ))}
          </select>
        </label>
        </div>
      </details>

      <div className="rv-catalog-content">
        <div className="rv-catalog-main">
          {searchState.kind === "loading" ? (
            <p className="rv-assertion-muted" role="status" data-testid="assertion-search-loading">
              Loading source assertions…
            </p>
          ) : searchState.kind === "error-with-retry" ? (
            <div className="rv-assertion-error" data-testid="assertion-search-error">
              <p>Source assertions could not be loaded.</p>
              <button type="button" className="it-btn secondary sm" onClick={() => void searchState.retry()}>
                Retry
              </button>
            </div>
          ) : (
            <>
              <AssertionResultsTable
                items={search.data?.items ?? []}
                selectedId={selectedAssertionId}
                onSelect={setSelectedAssertionId}
                isFetching={search.isFetching}
              />
              <div className="rv-catalog-pagination" data-testid="assertion-pagination">
                <button
                  type="button"
                  className="it-btn ghost sm"
                  disabled={cursorStack.length <= 1}
                  onClick={() => setCursorStack((stack) => stack.slice(0, -1))}
                  data-testid="assertion-page-prev"
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="it-btn ghost sm"
                  disabled={!search.data?.next_cursor}
                  onClick={() =>
                    setCursorStack((stack) => (search.data?.next_cursor ? [...stack, search.data.next_cursor] : stack))
                  }
                  data-testid="assertion-page-next"
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>

        {selectedAssertionId ? (
          <AssertionPacketInspector state={packet.state} onClose={clearSelection} />
        ) : (
          <aside className="rv-catalog-inspector" data-testid="assertion-inspector-empty">
            <EmptyState
              label="Source assertion"
              message="Select a row to inspect its edition, passage, qualifiers, evaluation, and uses."
            />
          </aside>
        )}
      </div>
    </>
  );
}

export default AssertionCatalogPane;
