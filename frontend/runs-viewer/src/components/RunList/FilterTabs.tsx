/**
 * FilterTabs — tab bar for the run list filter, plus collapsible metadata facet sections.
 *
 * Four status tabs: All | Verified | Needs Review | Planned
 * Three metadata facet sections (P6): Project | Category | Tags
 *
 * Tab selection is purely local display state lifted to RunListScreen.
 * Metadata filters use checkbox lists derived dynamically from the loaded run summaries.
 *
 * Uses .it-seg segmented control from components.css.
 */

import { useState } from "react";
import type { RunFilterState } from "./RunCard";
import { TagFilterPanel } from "./TagFilterPanel";

export type FilterTab = "all" | RunFilterState;

const TABS: { id: FilterTab; label: string }[] = [
  { id: "all",          label: "All" },
  { id: "verified",     label: "Verified" },
  { id: "needs-review", label: "Needs Review" },
  { id: "planned",      label: "Planned" },
];

// ── Metadata facet props ──────────────────────────────────────────────────────

export interface MetadataFilterState {
  activeLinkedProjects: string[];
  activeCategories: string[];
  activeTags: string[];
}

export interface MetadataFilterOptions {
  linkedProjects: string[];
  categories: string[];
  tags: string[];
}

// ── Main FilterTabs props ─────────────────────────────────────────────────────

interface FilterTabsProps {
  active: FilterTab;
  counts: Partial<Record<FilterTab, number>>;
  onChange: (tab: FilterTab) => void;

  // Optional metadata filter props (P6) — when omitted, facet sections are hidden
  metadataFilters?: MetadataFilterState;
  metadataOptions?: MetadataFilterOptions;
  onMetadataFilterChange?: (next: MetadataFilterState) => void;
}

// ── Collapsible facet section ─────────────────────────────────────────────────

function FacetSection({
  title,
  options,
  active,
  onToggle,
}: {
  title: string;
  options: string[];
  active: string[];
  onToggle: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);

  // Don't render when no options are available
  if (options.length === 0) return null;

  return (
    <div className="rv-facet-section" data-testid={`facet-section-${title.toLowerCase()}`}>
      <button
        type="button"
        className="rv-facet-header"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>{title}</span>
        {active.length > 0 && (
          <span className="rv-facet-badge" aria-label={`${active.length} selected`}>
            {active.length}
          </span>
        )}
        <span className="rv-facet-chevron" aria-hidden="true">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <fieldset className="rv-facet-list" role="group">
          <legend className="rv-facet-legend">{title} filter options</legend>
          {options.map((opt) => {
            const checked = active.includes(opt);
            return (
              <div key={opt} className="rv-facet-list-item">
                <label className={`rv-facet-option${checked ? " active" : ""}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggle(opt)}
                    aria-label={opt}
                    data-testid={`facet-option-${title.toLowerCase()}-${opt}`}
                  />
                  <span className="rv-facet-label">{opt}</span>
                </label>
              </div>
            );
          })}
        </fieldset>
      )}
    </div>
  );
}

// ── Collapsible Tags section wrapping TagFilterPanel ─────────────────────────

function CollapsibleTagSection({
  options,
  active,
  onToggle,
}: {
  options: string[];
  active: string[];
  onToggle: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rv-facet-section" data-testid="facet-section-tags">
      <button
        type="button"
        className="rv-facet-header"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>Tags</span>
        {active.length > 0 && (
          <span className="rv-facet-badge" aria-label={`${active.length} selected`}>
            {active.length}
          </span>
        )}
        <span className="rv-facet-chevron" aria-hidden="true">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <TagFilterPanel options={options} active={active} onToggle={onToggle} />
      )}
    </div>
  );
}

// ── FilterTabs ────────────────────────────────────────────────────────────────

export function FilterTabs({
  active,
  counts,
  onChange,
  metadataFilters,
  metadataOptions,
  onMetadataFilterChange,
}: FilterTabsProps) {
  const hasMetadata =
    metadataFilters !== undefined &&
    metadataOptions !== undefined &&
    onMetadataFilterChange !== undefined;

  function toggleLinkedProject(value: string) {
    if (!hasMetadata) return;
    const next = metadataFilters!.activeLinkedProjects.includes(value)
      ? metadataFilters!.activeLinkedProjects.filter((v) => v !== value)
      : [...metadataFilters!.activeLinkedProjects, value];
    onMetadataFilterChange!({ ...metadataFilters!, activeLinkedProjects: next });
  }

  function toggleCategory(value: string) {
    if (!hasMetadata) return;
    const next = metadataFilters!.activeCategories.includes(value)
      ? metadataFilters!.activeCategories.filter((v) => v !== value)
      : [...metadataFilters!.activeCategories, value];
    onMetadataFilterChange!({ ...metadataFilters!, activeCategories: next });
  }

  function toggleTag(value: string) {
    if (!hasMetadata) return;
    const next = metadataFilters!.activeTags.includes(value)
      ? metadataFilters!.activeTags.filter((v) => v !== value)
      : [...metadataFilters!.activeTags, value];
    onMetadataFilterChange!({ ...metadataFilters!, activeTags: next });
  }

  return (
    <div className="rv-filter-tabs-wrap">
      {/* Status tabs — existing behaviour unchanged */}
      <div className="it-seg rv-filter-tabs" role="tablist" aria-label="Filter runs by status">
        {TABS.map(({ id, label }) => {
          const count = counts[id];
          return (
            <button
              key={id}
              role="tab"
              aria-selected={active === id}
              className={active === id ? "active" : ""}
              onClick={() => onChange(id)}
              data-testid={`filter-tab-${id}`}
            >
              {label}
              {count != null && (
                <span className="rv-tab-count">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Metadata facet sections (P6) — only when props provided */}
      {hasMetadata && (
        <div className="rv-facet-sections" aria-label="Filter by metadata">
          <FacetSection
            title="Project"
            options={metadataOptions!.linkedProjects}
            active={metadataFilters!.activeLinkedProjects}
            onToggle={toggleLinkedProject}
          />
          <FacetSection
            title="Category"
            options={metadataOptions!.categories}
            active={metadataFilters!.activeCategories}
            onToggle={toggleCategory}
          />
          {/* Tags — inline-searchable colored pill panel */}
          {metadataOptions!.tags.length > 0 && (
            <CollapsibleTagSection
              active={metadataFilters!.activeTags}
              options={metadataOptions!.tags}
              onToggle={toggleTag}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default FilterTabs;
