/**
 * BuilderCatalogPane — left column of the Report Builder (P3 Wave F).
 *
 * Reuses the SAME data hooks as CatalogScreen (useCatalogStats/useCatalogSearch,
 * src/hooks/useCatalog.ts — dual-mode via api/client.ts, unchanged by Wave F)
 * rather than the full `CatalogResultsTable` (a 7-column table meant for a
 * full-width screen; the mockup's Builder search pane is a ~320px compact
 * card list). Same tab/status/sensitivity vocabulary and `it-chip`/`it-pill`
 * classes as CatalogScreen, just a different result-row layout.
 *
 * Checking a row toggles Claim Basket membership (mirrors the mockup: the
 * checked catalog rows are exactly the rows shown in the Claim Basket strip).
 *
 * DEMO FALLBACK (polish-pass F5/"demo data"): when the real catalog search
 * comes back with zero results in static mode (a fresh deployment with no
 * bundled run exports), this pane falls back to lib/builderMocks.ts's 6-item
 * demo set so the search/filter/basket flow stays demonstrable without a
 * live server. The fallback never engages in loopback mode or once real data
 * exists — see `useDemoFallback` below.
 *
 * F5 note: the Materiality/Confidence/Type/"More" pills are visual scaffolding
 * matching the mockup's filter row — only Status is wired to a real query
 * param today (the catalog API/static index doesn't expose the others yet).
 */
import { useEffect, useState } from "react";
import { isLoopbackEnabled } from "@/api/client";
import { useCatalogSearch, useCatalogStats } from "@/hooks";
import type { CatalogItemSummary, CatalogItemType } from "@/types/rf/catalog";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatDateTime } from "@/lib/runs";
import { filterMockCatalog, MOCK_CATALOG_STATS_COUNTS } from "@/lib/builderMocks";

type CatalogTabId = Extract<CatalogItemType, "claim" | "source" | "inference">;
type SortId = "updated" | "title" | "confidence";

const TABS: { id: CatalogTabId; label: string }[] = [
  { id: "claim", label: "Claims" },
  { id: "source", label: "Sources" },
  { id: "inference", label: "Inferences" },
];

function capitalize(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const STATUS_CHIP: Record<string, string> = {
  supported: "green",
  verified: "green",
  mixed: "orange",
  contradicted: "red",
  unsupported: "red",
  inference: "blue",
  speculation: "orange",
};

const CONFIDENCE_CHIP: Record<string, string> = { high: "green", medium: "orange", low: "red" };

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

function isRowActionTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && Boolean(target.closest("button,a,input,select,textarea"));
}

export interface BuilderCatalogPaneProps {
  basketIds: Set<string>;
  onToggleBasket: (item: CatalogItemSummary) => void;
  onExpand?: (item: CatalogItemSummary) => void;
  onShowInstances?: (item: CatalogItemSummary, refs: string[]) => void;
  linkedRefsByItemId?: Map<string, string[]>;
}

export function BuilderCatalogPane({ basketIds, onToggleBasket, onExpand, onShowInstances, linkedRefsByItemId }: BuilderCatalogPaneProps) {
  const { data: stats } = useCatalogStats();
  const [tab, setTab] = useState<CatalogTabId>("claim");
  const [searchInput, setSearchInput] = useState("");
  const debouncedQuery = useDebouncedValue(searchInput, 250);
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<SortId>("updated");
  const [showMoreFilters, setShowMoreFilters] = useState(false);

  const { data, isLoading } = useCatalogSearch({
    item_type: tab,
    q: debouncedQuery || undefined,
    status: status || undefined,
    page: 1,
    page_size: 25,
    sort,
  });

  // Demo fallback engages only in static mode with a genuinely empty result set.
  const useDemoFallback = !isLoopbackEnabled() && !isLoading && (data?.total ?? 0) === 0;
  const demo = useDemoFallback ? filterMockCatalog(tab, debouncedQuery, status || undefined) : null;

  const items = demo ? demo.items : data?.items ?? [];
  const total = demo ? demo.items.length : data?.total ?? 0;
  const statusOptions = demo ? demo.facets.statuses : data?.facets.statuses ?? [];

  function tabCount(id: CatalogTabId): number | null {
    const real = stats?.counts[id];
    if (real) return real;
    return useDemoFallback ? MOCK_CATALOG_STATS_COUNTS[id] || null : real ?? null;
  }

  return (
    <section className="rv-builder-catalog it-card" aria-label="Catalog search" data-testid="builder-catalog-pane">
      <div className="rv-pane-title">
        <h3>Catalog Search</h3>
      </div>

      <div className="it-seg rv-builder-catalog__tabs" role="tablist" aria-label="Catalog item type">
        {TABS.map(({ id, label }) => {
          const count = tabCount(id);
          return (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
              data-testid={`builder-catalog-tab-${id}`}
            >
              {label}
              {count != null && <span className="rv-catalog-tab-count">{count.toLocaleString()}</span>}
            </button>
          );
        })}
      </div>

      <div className="rv-builder-catalog__searchrow">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={`Search ${tab}s…`}
          aria-label={`Search ${tab}s`}
          data-testid="builder-catalog-search"
        />
        <button
          type="button"
          className="rv-builder-catalog__filter-icon"
          aria-label="More filters"
          aria-expanded={showMoreFilters}
          title="More filters"
          onClick={() => setShowMoreFilters((v) => !v)}
          data-testid="builder-catalog-filter-toggle"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M2 3h12M4.5 8h7M7 13h2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div className="rv-builder-catalog__pill-row">
        <label className="rv-builder-catalog__pill" data-testid="builder-catalog-status-pill">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status" data-testid="builder-catalog-status">
            <option value="">All</option>
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {capitalize(s)}
              </option>
            ))}
          </select>
        </label>
        {showMoreFilters && (
          <>
            <span className="rv-builder-catalog__pill rv-builder-catalog__pill--static" title="Coming soon">
              Materiality ▾
            </span>
            <span className="rv-builder-catalog__pill rv-builder-catalog__pill--static" title="Coming soon">
              Confidence ▾
            </span>
            <span className="rv-builder-catalog__pill rv-builder-catalog__pill--static" title="Coming soon">
              Type ▾
            </span>
          </>
        )}
        <button
          type="button"
          className="rv-builder-catalog__pill rv-builder-catalog__pill--static"
          onClick={() => setShowMoreFilters((v) => !v)}
          data-testid="builder-catalog-more-filters"
        >
          More {showMoreFilters ? "▴" : "▾"}
        </button>
      </div>

      <div className="rv-builder-catalog__sort-row">
        <span data-testid="builder-catalog-count">
          {total.toLocaleString()} result{total === 1 ? "" : "s"}
        </span>
        <label className="rv-builder-catalog__sort">
          <span>Sort:</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortId)} aria-label="Sort results">
            <option value="updated">Updated</option>
            <option value="title">Title</option>
            <option value="confidence">Confidence</option>
          </select>
        </label>
      </div>

      <div className="rv-builder-catalog__list" data-testid="builder-catalog-list">
        {isLoading && !useDemoFallback && <p className="rv-muted">Searching…</p>}
        {!isLoading && items.length === 0 && <EmptyState label="No results" message="No catalog items match the current search." />}
        {items.map((item) => {
          const inBasket = basketIds.has(item.catalog_item_id);
          const statusChip = item.status ? STATUS_CHIP[item.status] ?? "" : "";
          const confidenceChip = item.confidence ? CONFIDENCE_CHIP[item.confidence] ?? "" : "";
          const linkedRefs = linkedRefsByItemId?.get(item.catalog_item_id) ?? linkedRefsByItemId?.get(item.local_ref) ?? [];
          return (
            <div
              key={item.catalog_item_id}
              className={`rv-builder-catalog-row${inBasket ? " rv-builder-catalog-row--selected" : ""}`}
              data-testid={`builder-catalog-row-${item.local_ref}`}
              onClick={() => onToggleBasket(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (isRowActionTarget(e.target)) return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onToggleBasket(item);
                }
              }}
            >
              <input
                type="checkbox"
                checked={inBasket}
                readOnly
                aria-label={`Add ${item.local_ref} to Claim Basket`}
                data-testid={`builder-catalog-checkbox-${item.local_ref}`}
              />
              <div className="rv-builder-catalog-row__body">
                <div className="rv-builder-catalog-row__badges">
                  {item.status && <span className={`it-chip ${statusChip}`}>{capitalize(item.status)}</span>}
                  {item.confidence && <span className={`it-chip ${confidenceChip}`}>{capitalize(item.confidence)}</span>}
                  {linkedRefs.length > 0 && (
                    <span
                      className="it-chip blue rv-builder-catalog-card__linked"
                      title={`Linked in draft: ${linkedRefs.join(", ")}`}
                      data-testid="builder-catalog-linked-count"
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: highlight or scroll to the concrete draft instances after block-level navigation lands.
                        onShowInstances?.(item, linkedRefs) ?? onExpand?.(item);
                      }}
                    >
                      {linkedRefs.length} in report
                    </span>
                  )}
                </div>
                <p className="rv-builder-catalog-row__title" title={item.title}>
                  {item.title}
                </p>
                <div className="rv-builder-catalog-row__meta">
                  <span>Sources: {item.source_count}</span>
                  <span>Updated: {formatDateTime(item.updated_at)}</span>
                </div>
              </div>
              <button
                type="button"
                className="rv-builder-catalog-row__expand"
                aria-label={`Expand ${item.local_ref}`}
                title="Expand catalog item"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand?.(item);
                }}
                data-testid={`builder-catalog-expand-${item.local_ref}`}
              >
                ⤢ <span>Expand</span>
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default BuilderCatalogPane;
