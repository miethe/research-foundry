/**
 * useCollapseState — lightweight hook for panel collapse/expand state.
 *
 * Persists to sessionStorage so state survives navigate-to-list → navigate-back
 * within the same browser session, but resets to collapsed on page reload (per OQ-2).
 *
 * Key format: `rf:context-panel:${runId}:${panelId}`
 *
 * Default: collapsed=true (panels start closed).
 * If sessionStorage is unavailable (private browsing, quota exceeded, SSR),
 * the hook silently falls back to in-memory state without crashing.
 */

import { useState } from "react";

// ── Storage helpers ───────────────────────────────────────────────────────────

function ssGet(key: string): string | null {
  try {
    if (typeof window === "undefined") return null;
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function ssSet(key: string, value: string): void {
  try {
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem(key, value);
  } catch {
    // ignore — unavailable or quota exceeded
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface CollapseState {
  collapsed: boolean;
  toggle: () => void;
}

/**
 * Returns collapse state and a toggle for a single context panel.
 *
 * @param runId   - The run_id of the current run (scopes the key).
 * @param panelId - Short stable identifier for the panel (e.g. 'routing_decision').
 */
export function useCollapseState(runId: string, panelId: string): CollapseState {
  const key = `rf:context-panel:${runId}:${panelId}`;

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    // Read sessionStorage once on mount (resets to true on page reload when absent)
    const stored = ssGet(key);
    if (stored === "false") return false;
    return true; // default: collapsed
  });

  function toggle(): void {
    setCollapsed((prev) => {
      const next = !prev;
      ssSet(key, next ? "true" : "false");
      return next;
    });
  }

  return { collapsed, toggle };
}
