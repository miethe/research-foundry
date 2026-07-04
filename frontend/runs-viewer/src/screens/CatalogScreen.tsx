/**
 * CatalogScreen — Evidence Catalog (public-multiuser-p0p1, Phase 1 frontend).
 *
 * Accessible at /catalog (replaces the temporary LibraryScreen mount from
 * Phase 0). Shared claims, sources, inferences, and reports across runs and
 * projects — see docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md
 * § "Phase 1 frontend deliverables (Wave C)" and the mockup at
 * docs/project_plans/design-specs/assets/public-multiuser-release/mockup-evidence-catalog.png.
 *
 * Layout: header + tab strip (live counts) + filter row + dense results table
 * (main column) + selected-item inspector (right rail, collapses below ~1100px).
 *
 * "Report-ready" is a UI-only grouping tab (not a CatalogItemType) that
 * absorbs the old LibraryScreen's Reusable Outputs + Writeback Artifacts
 * sections — it renders two grouped sub-tables rather than one merged/sorted
 * table (kept simple: each sub-list is fetched with a generous page_size and
 * is not independently paginated; acceptable at personal/team scale).
 */

import { Fragment, useEffect, useMemo, useState } from "react";
import { useCatalogItem, useCatalogSearch, useCatalogStats } from "@/hooks";
import type { CatalogProvenance } from "@/lib/catalog";
import type {
  CatalogItemDetail,
  CatalogItemSummary,
  CatalogItemType,
  CatalogSearchFacets,
  CatalogSortKey,
} from "@/types/rf/catalog";
import type { RFResolvedSource } from "@/types/rf";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { RunDetailModal } from "@/components/RunDetail/RunDetailModal";
import { formatDateTime } from "@/lib/runs";
import "@/styles/catalog.css";

// ── Tabs ──────────────────────────────────────────────────────────────────────

type CatalogTabId = "claim" | "source" | "inference" | "report" | "report-ready";

const TABS: { id: CatalogTabId; label: string }[] = [
  { id: "claim", label: "Claims" },
  { id: "source", label: "Sources" },
  { id: "inference", label: "Inferences" },
  { id: "report", label: "Reports" },
  { id: "report-ready", label: "Report-ready" },
];

function tabCount(stats: { counts: Record<CatalogItemType, number> } | undefined, tab: CatalogTabId): number | null {
  if (!stats) return null;
  if (tab === "report-ready") return stats.counts.reusable_output + stats.counts.writeback;
  return stats.counts[tab];
}

// ── Display helpers ────────────────────────────────────────────────────────────

function capitalize(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const TRUST_CHIP_COLOR: Record<string, string> = {
  supported: "green",
  verified: "green",
  published: "green",
  mixed: "orange",
  partially_supported: "orange",
  reviewing: "orange",
  contradicted: "red",
  refuted: "red",
  unsupported: "red",
};

function trustDisplay(item: CatalogItemSummary): { label: string; color: string } {
  if (item.item_type === "claim" || item.item_type === "inference") {
    return {
      label: item.status ? capitalize(item.status) : "—",
      color: item.status ? TRUST_CHIP_COLOR[item.status] ?? "" : "",
    };
  }
  return { label: item.trust_label ? capitalize(item.trust_label) : "—", color: "" };
}

const STATUS_PILL_CLASS: Record<string, string> = {
  supported: "done",
  published: "done",
  approved: "done",
  mixed: "warn",
  pending: "warn",
  draft: "warn",
  partially_supported: "warn",
  contradicted: "blocked",
  unsupported: "blocked",
  failed: "blocked",
  refuted: "blocked",
  inference: "progress",
  speculation: "progress",
  reviewing: "progress",
};

function statusPillClass(status: string | null): string {
  if (!status) return "idle";
  return STATUS_PILL_CLASS[status] ?? "idle";
}

function sensitivityChipColor(sensitivity: string | null): string {
  if (!sensitivity || sensitivity === "public") return "green";
  if (sensitivity === "personal") return "blue";
  if (sensitivity === "work_sensitive") return "orange";
  return "red"; // client_sensitive + any unrecognized (fail-closed) label
}

// ── Debounce ──────────────────────────────────────────────────────────────────

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

// ── Results table ─────────────────────────────────────────────────────────────

interface CatalogResultsTableProps {
  items: CatalogItemSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  emptyLabel: string;
  emptyMessage?: string;
}

function CatalogResultsTable({ items, selectedId, onSelect, emptyLabel, emptyMessage }: CatalogResultsTableProps) {
  if (items.length === 0) {
    return <EmptyState label={emptyLabel} message={emptyMessage ?? "No items match the current filters."} />;
  }

  return (
    <div className="rv-catalog-table-wrap" data-testid="catalog-results-table">
      <table className="rv-catalog-table" role="grid" aria-label="Evidence catalog results">
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Claim / Title</th>
            <th scope="col">Trust</th>
            <th scope="col">Sensitivity</th>
            <th scope="col">Status</th>
            <th scope="col">Project</th>
            <th scope="col">Updated</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const trust = trustDisplay(item);
            const isSelected = item.catalog_item_id === selectedId;
            return (
              <tr
                key={item.catalog_item_id}
                className={`rv-catalog-row${isSelected ? " rv-catalog-row--selected" : ""}`}
                data-testid={`catalog-row-${item.catalog_item_id}`}
                data-item-type={item.item_type}
                onClick={() => onSelect(item.catalog_item_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(item.catalog_item_id);
                  }
                }}
                tabIndex={0}
                role="row"
                aria-selected={isSelected}
              >
                <td className="rv-catalog-td rv-catalog-td--id">
                  <code>{item.local_ref}</code>
                </td>
                <td className="rv-catalog-td rv-catalog-td--title">
                  <span className="rv-catalog-title" title={item.title}>
                    {item.title}
                  </span>
                  {item.summary && <span className="rv-catalog-summary">{item.summary}</span>}
                </td>
                <td className="rv-catalog-td">
                  <span className={`it-chip ${trust.color}`}>
                    {trust.label}
                    {item.confidence != null && ` ${item.confidence}`}
                  </span>
                </td>
                <td className="rv-catalog-td">
                  <span className={`it-chip ${sensitivityChipColor(item.sensitivity)}`}>
                    {item.sensitivity ? capitalize(item.sensitivity) : "Public"}
                  </span>
                </td>
                <td className="rv-catalog-td">
                  <span className={`it-pill ${statusPillClass(item.status)}`}>
                    {item.status ? capitalize(item.status) : "—"}
                  </span>
                </td>
                <td className="rv-catalog-td">{item.project ?? "—"}</td>
                <td className="rv-catalog-td rv-catalog-td--updated">{formatDateTime(item.updated_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Provenance strip ──────────────────────────────────────────────────────────

const PROVENANCE_STAGES: { key: keyof CatalogProvenance; label: string }[] = [
  { key: "source_card", label: "Source Card" },
  { key: "extraction", label: "Extraction" },
  { key: "inference", label: "Inference" },
  { key: "report", label: "Report" },
  { key: "writeback", label: "Writeback" },
];

function ProvenanceStrip({ provenance }: { provenance: CatalogProvenance | null | undefined }) {
  if (!provenance) return null;
  return (
    <div className="rv-catalog-provenance" data-testid="catalog-provenance">
      {PROVENANCE_STAGES.map((stage, i) => (
        <Fragment key={stage.key}>
          <div
            className={`rv-catalog-provenance__stage${provenance[stage.key] ? " is-present" : ""}`}
            data-testid={`catalog-provenance-${stage.key}`}
          >
            <span className="rv-catalog-provenance__dot" aria-hidden="true" />
            <span className="rv-catalog-provenance__label">{stage.label}</span>
          </div>
          {i < PROVENANCE_STAGES.length - 1 && (
            <span className="rv-catalog-provenance__arrow" aria-hidden="true">
              →
            </span>
          )}
        </Fragment>
      ))}
    </div>
  );
}

// ── Usage policy chips ─────────────────────────────────────────────────────────

function UsagePolicyChips({ sources, sensitivity }: { sources: RFResolvedSource[]; sensitivity: string | null }) {
  const chips: { label: string; color: string }[] = [];
  if (sensitivity) chips.push({ label: capitalize(sensitivity), color: sensitivityChipColor(sensitivity) });
  if (sources.some((s) => s.usage?.citation_required)) chips.push({ label: "Attribution Required", color: "gold" });
  if (sources.length > 0 && sources.every((s) => s.usage?.allowed_for_public_output === false)) {
    chips.push({ label: "No Redistribute", color: "red" });
  }
  if (sources.some((s) => s.usage?.allowed_for_public_output)) chips.push({ label: "Public OK", color: "green" });
  if (sources.some((s) => s.usage?.allowed_for_work_output)) chips.push({ label: "Work OK", color: "blue" });
  if (sources.some((s) => s.usage?.allowed_for_personal_meatywiki)) {
    chips.push({ label: "Personal Wiki OK", color: "purple" });
  }
  if (chips.length === 0) return null;
  return (
    <div className="rv-catalog-usage-chips" data-testid="catalog-usage-policy">
      {chips.map((chip) => (
        <span key={chip.label} className={`it-chip ${chip.color}`}>
          {chip.label}
        </span>
      ))}
    </div>
  );
}

// ── Inspector ─────────────────────────────────────────────────────────────────

interface CatalogInspectorProps {
  item: CatalogItemDetail | null | undefined;
  isLoading: boolean;
  onOpenRun: (runId: string) => void;
  onSelectItem: (id: string) => void;
}

function CatalogInspector({ item, isLoading, onOpenRun, onSelectItem }: CatalogInspectorProps) {
  if (isLoading) {
    return (
      <aside className="rv-catalog-inspector" data-testid="catalog-inspector-loading">
        <div className="rv-loading">
          <p>Loading item…</p>
        </div>
      </aside>
    );
  }

  if (!item) {
    return (
      <aside className="rv-catalog-inspector" data-testid="catalog-inspector-empty">
        <EmptyState label="Selected Item" message="Select a row to inspect its provenance and evidence." />
      </aside>
    );
  }

  const isClaimLike = item.item_type === "claim" || item.item_type === "inference";
  const sources = isClaimLike ? ((item.payload.sources as RFResolvedSource[] | undefined) ?? []) : [];
  const provenance = isClaimLike ? (item.payload.provenance as CatalogProvenance | undefined) : undefined;
  const inferenceLinks = item.links.outgoing.filter((l) => l.relation === "inferred_from");
  const reasoningSummary = item.item_type === "inference" ? item.summary : null;

  return (
    <aside className="rv-catalog-inspector" data-testid="catalog-inspector" aria-label="Selected item">
      <header className="rv-catalog-inspector__header">
        <div>
          <code className="rv-catalog-inspector__ref" data-testid="catalog-inspector-ref">
            {item.local_ref}
          </code>
          <span className={`it-pill ${statusPillClass(item.status)}`}>
            {item.status ? capitalize(item.status) : "—"}
          </span>
        </div>
      </header>

      <h3 className="rv-catalog-inspector__title">{item.title}</h3>
      {item.summary && <p className="rv-catalog-inspector__summary">{item.summary}</p>}

      {isClaimLike && (
        <section className="rv-catalog-inspector__section">
          <h4>Provenance</h4>
          <ProvenanceStrip provenance={provenance} />
        </section>
      )}

      {isClaimLike && sources.length > 0 && (
        <section className="rv-catalog-inspector__section" data-testid="catalog-inspector-sources">
          <h4>Source Cards ({sources.length})</h4>
          <div className="rv-catalog-inspector__source-list">
            {sources.map((source) => (
              <SourceCard key={source.source_card_id} source={source} sensitivityThreshold={item.sensitivity} compact />
            ))}
          </div>
        </section>
      )}

      {item.item_type === "inference" && (
        <section className="rv-catalog-inspector__section" data-testid="catalog-inference-basis">
          <h4>Inference Basis</h4>
          <div className="rv-catalog-inspector__basis-chips">
            {inferenceLinks.length > 0 ? (
              inferenceLinks.map((link) => (
                <button
                  key={link.catalog_item_id}
                  type="button"
                  className="it-chip blue"
                  onClick={() => onSelectItem(link.catalog_item_id)}
                  data-testid={`catalog-inference-from-${link.catalog_item_id}`}
                >
                  {link.catalog_item_id}
                </button>
              ))
            ) : (
              <span className="rv-catalog-muted">No resolvable basis claims.</span>
            )}
          </div>
          {reasoningSummary && <p className="rv-catalog-inspector__reasoning">{reasoningSummary}</p>}
        </section>
      )}

      {isClaimLike && (
        <section className="rv-catalog-inspector__section">
          <h4>Usage Policy</h4>
          <UsagePolicyChips sources={sources} sensitivity={item.sensitivity} />
        </section>
      )}

      <footer className="rv-catalog-inspector__footer">
        <button
          type="button"
          className="it-btn primary"
          disabled
          title="Planned — Report Builder (Phase 3)"
          data-testid="catalog-action-add-to-report"
        >
          Add to Report
        </button>
        <button
          type="button"
          className="it-btn secondary"
          disabled
          title="Planned — Agent Research (Phase 4)"
          data-testid="catalog-action-followup-research"
        >
          Run Follow-up Research
        </button>
        <button
          type="button"
          className="it-btn ghost"
          onClick={() => onOpenRun(item.run_id)}
          data-testid="catalog-action-open-run"
        >
          Open run
        </button>
      </footer>
    </aside>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

const EMPTY_FACETS: CatalogSearchFacets = { projects: [], statuses: [], sensitivities: [] };
const PAGE_SIZE = 20;

export function CatalogScreen() {
  const { data: stats, isLoading: statsLoading } = useCatalogStats();

  const [tab, setTab] = useState<CatalogTabId>("claim");
  const [project, setProject] = useState("");
  const [status, setStatus] = useState("");
  const [sensitivity, setSensitivity] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const debouncedQuery = useDebouncedValue(searchInput, 250);
  const [sort, setSort] = useState<CatalogSortKey>("updated");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [openRunId, setOpenRunId] = useState<string | null>(null);

  // Reset to page 1 whenever the active filter set changes.
  useEffect(() => {
    setPage(1);
  }, [tab, project, status, sensitivity, debouncedQuery, sort]);

  const baseParams = useMemo(
    () => ({
      q: debouncedQuery || undefined,
      project: project || undefined,
      status: status || undefined,
      sensitivity: sensitivity || undefined,
      sort,
    }),
    [debouncedQuery, project, status, sensitivity, sort],
  );

  const mainParams = useMemo(
    () => ({
      ...baseParams,
      item_type: tab === "report-ready" ? undefined : tab,
      page,
      page_size: PAGE_SIZE,
    }),
    [baseParams, tab, page],
  );
  const reusableParams = useMemo(
    () => ({ ...baseParams, item_type: "reusable_output" as const, page: 1, page_size: 200 }),
    [baseParams],
  );
  const writebackParams = useMemo(
    () => ({ ...baseParams, item_type: "writeback" as const, page: 1, page_size: 200 }),
    [baseParams],
  );

  const mainResult = useCatalogSearch(mainParams);
  const reusableResult = useCatalogSearch(reusableParams);
  const writebackResult = useCatalogSearch(writebackParams);
  const selectedItem = useCatalogItem(selectedId);

  const facets: CatalogSearchFacets =
    mainResult.data?.facets ?? reusableResult.data?.facets ?? writebackResult.data?.facets ?? EMPTY_FACETS;

  function handleSelect(id: string) {
    setSelectedId(id);
  }

  function handleOpenRun(runId: string) {
    setOpenRunId(runId);
  }

  if (statsLoading && !stats) {
    return (
      <div className="rv-catalog" data-testid="catalog-screen">
        <div className="rv-loading" data-testid="catalog-loading">
          <p>Building evidence catalog index…</p>
        </div>
      </div>
    );
  }

  const total = tab === "report-ready" ? undefined : mainResult.data?.total;

  return (
    <div className="rv-catalog" data-testid="catalog-screen">
      <header className="rv-catalog__header">
        <h1 className="rv-catalog__title">Evidence Catalog</h1>
        <p className="rv-catalog__subtitle">
          Shared claims, sources, inferences, and reports across runs and projects.
        </p>
      </header>

      <div className="it-seg rv-catalog-tabs" role="tablist" aria-label="Catalog item type">
        {TABS.map(({ id, label }) => {
          const count = tabCount(stats, id);
          return (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
              data-testid={`catalog-tab-${id}`}
            >
              {label}
              {count != null && <span className="rv-catalog-tab-count">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="rv-catalog-filters" role="search" aria-label="Filter catalog">
        <label className="rv-catalog-filter">
          <span>Project</span>
          <select value={project} onChange={(e) => setProject(e.target.value)} data-testid="catalog-filter-project">
            <option value="">All Projects</option>
            {facets.projects.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="rv-catalog-filter">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} data-testid="catalog-filter-status">
            <option value="">All Statuses</option>
            {facets.statuses.map((s) => (
              <option key={s} value={s}>
                {capitalize(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="rv-catalog-filter">
          <span>Sensitivity</span>
          <select
            value={sensitivity}
            onChange={(e) => setSensitivity(e.target.value)}
            data-testid="catalog-filter-sensitivity"
          >
            <option value="">All Sensitivities</option>
            {facets.sensitivities.map((s) => (
              <option key={s} value={s}>
                {capitalize(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="rv-catalog-filter rv-catalog-filter--search">
          <span>Search</span>
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search claims, sources, reports…"
            data-testid="catalog-search-input"
          />
        </label>
        <label className="rv-catalog-filter">
          <span>Sort</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as CatalogSortKey)}
            data-testid="catalog-sort-select"
          >
            <option value="updated">Updated</option>
            <option value="title">Title</option>
            <option value="confidence">Confidence</option>
          </select>
        </label>
        {total != null && (
          <span className="rv-catalog-result-count" data-testid="catalog-result-count">
            {total} result{total === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="rv-catalog-content">
        <div className="rv-catalog-main">
          {tab === "report-ready" ? (
            <>
              <section className="rv-catalog-group" data-testid="catalog-group-reusable">
                <h3 className="rv-catalog-group__title">Reusable Outputs</h3>
                <CatalogResultsTable
                  items={reusableResult.data?.items ?? []}
                  selectedId={selectedId}
                  onSelect={handleSelect}
                  emptyLabel="Reusable Outputs"
                  emptyMessage="No reusable output candidates recorded in the loaded runs."
                />
              </section>
              <section className="rv-catalog-group" data-testid="catalog-group-writeback">
                <h3 className="rv-catalog-group__title">Writeback Artifacts</h3>
                <CatalogResultsTable
                  items={writebackResult.data?.items ?? []}
                  selectedId={selectedId}
                  onSelect={handleSelect}
                  emptyLabel="Writeback Artifacts"
                  emptyMessage="No writeback artifacts found."
                />
              </section>
            </>
          ) : (
            <>
              <CatalogResultsTable
                items={mainResult.data?.items ?? []}
                selectedId={selectedId}
                onSelect={handleSelect}
                emptyLabel={TABS.find((t) => t.id === tab)?.label ?? "Results"}
              />
              {mainResult.data && mainResult.data.total > PAGE_SIZE && (
                <div className="rv-catalog-pagination" data-testid="catalog-pagination">
                  <button
                    type="button"
                    className="it-btn ghost sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    data-testid="catalog-page-prev"
                  >
                    Previous
                  </button>
                  <span className="rv-catalog-page-indicator">
                    Page {page} of {Math.max(1, Math.ceil(mainResult.data.total / PAGE_SIZE))}
                  </span>
                  <button
                    type="button"
                    className="it-btn ghost sm"
                    disabled={page * PAGE_SIZE >= mainResult.data.total}
                    onClick={() => setPage((p) => p + 1)}
                    data-testid="catalog-page-next"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <CatalogInspector
          item={selectedItem.data}
          isLoading={selectedItem.isLoading}
          onOpenRun={handleOpenRun}
          onSelectItem={handleSelect}
        />
      </div>

      <RunDetailModal runId={openRunId} onClose={() => setOpenRunId(null)} />
    </div>
  );
}

export default CatalogScreen;
