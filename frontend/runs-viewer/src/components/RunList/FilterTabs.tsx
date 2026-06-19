/**
 * FilterTabs — tab bar for the run list filter.
 *
 * Four tabs: All | Verified | Needs Review | Planned
 * Tab selection is purely local display state lifted to RunListScreen.
 * Uses .it-seg segmented control from components.css.
 */

import type { RunFilterState } from "./RunCard";

export type FilterTab = "all" | RunFilterState;

const TABS: { id: FilterTab; label: string }[] = [
  { id: "all",          label: "All" },
  { id: "verified",     label: "Verified" },
  { id: "needs-review", label: "Needs Review" },
  { id: "planned",      label: "Planned" },
];

interface FilterTabsProps {
  active: FilterTab;
  counts: Partial<Record<FilterTab, number>>;
  onChange: (tab: FilterTab) => void;
}

export function FilterTabs({ active, counts, onChange }: FilterTabsProps) {
  return (
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
  );
}

export default FilterTabs;
