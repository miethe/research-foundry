/**
 * TagFilterPanel — inline-searchable, colored tag filter panel.
 *
 * Renders a text input for client-side search and a wrap of colored
 * tag pills. Each pill uses tagColorClass() for deterministic hue
 * assignment matching the chips on RunCard. Active tags get .is-active
 * styling (stronger bg + white text) and a ✓ prefix.
 *
 * No tag CREATION — this is a read-only static viewer; persistence is
 * impossible without a backend.
 *
 * Accessibility:
 *   - Input has aria-label="Search tags"
 *   - Pills are <button> elements with aria-pressed reflecting active state
 *   - No-match state shows a muted message
 */

import { useState, useMemo } from "react";
import { tagColorClass } from "./tagColor";

interface TagFilterPanelProps {
  options: string[];
  active: string[];
  onToggle: (tag: string) => void;
}

export function TagFilterPanel({ options, active, onToggle }: TagFilterPanelProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((t) => t.toLowerCase().includes(q));
  }, [options, query]);

  if (options.length === 0) return null;

  return (
    <div className="rv-tag-filter-panel">
      {/* Search input */}
      <div className="rv-tag-filter-panel__search">
        <input
          type="text"
          className="rv-tag-filter-panel__input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tags…"
          aria-label="Search tags"
        />
      </div>

      {/* Tag pills */}
      {filtered.length === 0 ? (
        <p className="rv-tag-filter-panel__empty">No matching tags</p>
      ) : (
        <div className="rv-tag-filter-panel__pills" role="group" aria-label="Tag filter options">
          {filtered.map((tag) => {
            const isActive = active.includes(tag);
            const colorCls = tagColorClass(tag);
            return (
              <button
                key={tag}
                type="button"
                className={`rv-tag-filter-pill ${colorCls}${isActive ? " is-active" : ""}`}
                aria-pressed={isActive}
                onClick={() => onToggle(tag)}
                data-testid={`tag-filter-pill-${tag}`}
              >
                {isActive && <span className="rv-tag-filter-pill__check" aria-hidden="true">✓ </span>}
                {tag}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default TagFilterPanel;
