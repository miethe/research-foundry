/**
 * viewerSettings — client-side viewer preferences persisted to localStorage.
 *
 * Keys (all prefixed with `rv_` to avoid origin collisions):
 *   rv_show_all    — 'true' | 'false'        (default 'false')
 *   rv_theme       — 'light' | 'dark' | 'system' (default 'system')
 *   rv_default_tab — a valid DetailTab string  (default 'overview')
 *   rv_data_path   — string path               (default '/data')
 *
 * All localStorage access is wrapped in try/catch so that if localStorage is
 * unavailable or throws (private-browsing restrictions, quota exceeded, etc.),
 * the module returns documented defaults without crashing.
 *
 * Note on circular imports: this module imports DetailTab as a TYPE-ONLY import
 * from detailTabs.ts (erased at runtime). detailTabs.ts may import getViewerSettings
 * as a runtime import, which is fine because the type-only import here creates
 * no runtime cycle.
 */

import { useState } from "react";
import type { DetailTab } from "../components/RunDetail/detailTabs";

// ── Storage keys ──────────────────────────────────────────────────────────────

const KEYS = {
  showAll:    "rv_show_all",
  theme:      "rv_theme",
  defaultTab: "rv_default_tab",
  dataPath:   "rv_data_path",
} as const;

// ── Types ────────────────────────────────────────────────────────────────────

export type ThemeSetting = "light" | "dark" | "system";

export interface ViewerSettings {
  showAll:    boolean;
  theme:      ThemeSetting;
  defaultTab: DetailTab;
  dataPath:   string;
}

// ── Validation helpers ────────────────────────────────────────────────────────

const VALID_THEMES  = new Set<string>(["light", "dark", "system"]);
const VALID_TABS    = new Set<string>(["overview", "trust", "ledger", "report", "lineage", "writeback", "context"]);

function isValidTheme(v: string): v is ThemeSetting {
  return VALID_THEMES.has(v);
}

function isValidDetailTab(v: string): v is DetailTab {
  return VALID_TABS.has(v);
}

// ── Safe localStorage helpers ─────────────────────────────────────────────────

function lsGet(key: string): string | null {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function lsSet(key: string, value: string): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, value);
  } catch {
    // ignore — quota exceeded, private browsing, etc.
  }
}

// ── Defaults ─────────────────────────────────────────────────────────────────

const DEFAULTS: ViewerSettings = {
  showAll:    false,
  theme:      "system",
  defaultTab: "overview",
  dataPath:   "/data",
} as const;

// ── getViewerSettings ─────────────────────────────────────────────────────────

/**
 * Reads the four viewer settings from localStorage, validates each value, and
 * returns a fully-populated ViewerSettings object. Returns documented defaults
 * for any key that is absent, malformed, or causes localStorage to throw.
 */
export function getViewerSettings(): ViewerSettings {
  const rawShowAll    = lsGet(KEYS.showAll);
  const rawTheme      = lsGet(KEYS.theme);
  const rawDefaultTab = lsGet(KEYS.defaultTab);
  const rawDataPath   = lsGet(KEYS.dataPath);

  const showAll: boolean =
    rawShowAll === "true";

  const theme: ThemeSetting =
    rawTheme && isValidTheme(rawTheme) ? rawTheme : DEFAULTS.theme;

  const defaultTab: DetailTab =
    rawDefaultTab && isValidDetailTab(rawDefaultTab) ? rawDefaultTab : DEFAULTS.defaultTab;

  const dataPath: string =
    rawDataPath && rawDataPath.trim() !== "" ? rawDataPath.trim() : DEFAULTS.dataPath;

  return { showAll, theme, defaultTab, dataPath };
}

// ── setViewerSetting ──────────────────────────────────────────────────────────

/** Maps ViewerSettings field names to their localStorage keys. */
const FIELD_TO_KEY: Record<keyof ViewerSettings, string> = {
  showAll:    KEYS.showAll,
  theme:      KEYS.theme,
  defaultTab: KEYS.defaultTab,
  dataPath:   KEYS.dataPath,
};

/**
 * Persists a single viewer setting to localStorage.
 * Booleans are serialized as 'true' / 'false'. All other values use String().
 * Silently swallows localStorage errors (unavailable, quota exceeded).
 */
export function setViewerSetting<K extends keyof ViewerSettings>(
  key: K,
  value: ViewerSettings[K],
): void {
  const lsKey = FIELD_TO_KEY[key];
  const serialized =
    typeof value === "boolean" ? (value ? "true" : "false") : String(value);
  lsSet(lsKey, serialized);
}

// ── applyTheme ────────────────────────────────────────────────────────────────

/**
 * Applies a theme to document.documentElement via the data-theme attribute.
 *
 * tokens.css defines:
 *   :root              — light theme (default, no attribute required)
 *   [data-theme="dark"] — dark theme overrides
 *
 * So:
 *   'light'  → remove data-theme (restores :root defaults)
 *   'dark'   → set data-theme="dark"
 *   'system' → resolve from prefers-color-scheme media query
 */
export function applyTheme(theme: ThemeSetting): void {
  if (typeof document === "undefined") return;
  const html = document.documentElement;
  if (theme === "dark") {
    html.setAttribute("data-theme", "dark");
  } else if (theme === "light") {
    html.removeAttribute("data-theme");
  } else {
    // system — follow prefers-color-scheme
    const prefersDark =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      html.setAttribute("data-theme", "dark");
    } else {
      html.removeAttribute("data-theme");
    }
  }
}

// ── useViewerSettings ─────────────────────────────────────────────────────────

/**
 * React hook for viewer settings.
 *
 * Returns [currentSettings, updateSetting].
 *
 * updateSetting(key, value):
 *   1. Calls setViewerSetting to persist the change to localStorage
 *   2. Updates React state (triggers re-render)
 *   3. If the changed key is 'theme', calls applyTheme immediately
 *
 * State is seeded from getViewerSettings() on first render (picks up any
 * values already in localStorage).
 */
export function useViewerSettings(): [
  ViewerSettings,
  <K extends keyof ViewerSettings>(key: K, value: ViewerSettings[K]) => void,
] {
  const [settings, setSettings] = useState<ViewerSettings>(() => getViewerSettings());

  function updateSetting<K extends keyof ViewerSettings>(
    key: K,
    value: ViewerSettings[K],
  ): void {
    setViewerSetting(key, value);
    setSettings((prev) => ({ ...prev, [key]: value }));
    if (key === "theme") {
      applyTheme(value as ThemeSetting);
    }
  }

  return [settings, updateSetting];
}
