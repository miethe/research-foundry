/**
 * G5-settings tests — viewerSettings unit tests + SettingsScreen component tests.
 *
 * Covers:
 *   1. getViewerSettings — reads defaults when keys absent
 *   2. getViewerSettings — write→read round-trip for each key
 *   3. getViewerSettings — invalid-value fallback for each key
 *   4. setViewerSetting — serializes booleans correctly
 *   5. SettingsScreen — renders all four controls with defaults
 *   6. SettingsScreen — toggling sensitivity switch writes rv_show_all
 *   7. SettingsScreen — selecting a default tab makes coerceDetailTab(null) return it
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";

import {
  getViewerSettings,
  setViewerSetting,
  applyTheme,
} from "@/lib/viewerSettings";
import { coerceDetailTab } from "@/components/RunDetail/detailTabs";
import { SettingsScreen } from "@/screens/SettingsScreen";

// ── Reset localStorage between every test ─────────────────────────────────────

beforeEach(() => {
  localStorage.clear();
});

// ── (1) getViewerSettings — defaults when no keys present ─────────────────────

describe("getViewerSettings — defaults", () => {
  it("showAll defaults to false", () => {
    expect(getViewerSettings().showAll).toBe(false);
  });

  it("theme defaults to 'system'", () => {
    expect(getViewerSettings().theme).toBe("system");
  });

  it("defaultTab defaults to 'overview'", () => {
    expect(getViewerSettings().defaultTab).toBe("overview");
  });

  it("dataPath defaults to '/data'", () => {
    expect(getViewerSettings().dataPath).toBe("/data");
  });
});

// ── (2) write → read round-trips ─────────────────────────────────────────────

describe("getViewerSettings — write/read round-trips", () => {
  it("round-trip showAll=true", () => {
    setViewerSetting("showAll", true);
    expect(getViewerSettings().showAll).toBe(true);
  });

  it("round-trip showAll=false after true", () => {
    setViewerSetting("showAll", true);
    setViewerSetting("showAll", false);
    expect(getViewerSettings().showAll).toBe(false);
  });

  it("round-trip theme='dark'", () => {
    setViewerSetting("theme", "dark");
    expect(getViewerSettings().theme).toBe("dark");
  });

  it("round-trip theme='light'", () => {
    setViewerSetting("theme", "light");
    expect(getViewerSettings().theme).toBe("light");
  });

  it("round-trip defaultTab='trust'", () => {
    setViewerSetting("defaultTab", "trust");
    expect(getViewerSettings().defaultTab).toBe("trust");
  });

  it("round-trip defaultTab='report'", () => {
    setViewerSetting("defaultTab", "report");
    expect(getViewerSettings().defaultTab).toBe("report");
  });

  it("round-trip dataPath='/custom/path'", () => {
    setViewerSetting("dataPath", "/custom/path");
    expect(getViewerSettings().dataPath).toBe("/custom/path");
  });
});

// ── (3) invalid-value fallbacks ───────────────────────────────────────────────

describe("getViewerSettings — invalid value fallbacks", () => {
  it("bad theme value falls back to 'system'", () => {
    localStorage.setItem("rv_theme", "ultraviolet");
    expect(getViewerSettings().theme).toBe("system");
  });

  it("empty theme string falls back to 'system'", () => {
    localStorage.setItem("rv_theme", "");
    expect(getViewerSettings().theme).toBe("system");
  });

  it("bad defaultTab value falls back to 'overview'", () => {
    localStorage.setItem("rv_default_tab", "nonexistent_tab");
    expect(getViewerSettings().defaultTab).toBe("overview");
  });

  it("empty defaultTab string falls back to 'overview'", () => {
    localStorage.setItem("rv_default_tab", "");
    expect(getViewerSettings().defaultTab).toBe("overview");
  });

  it("empty dataPath falls back to '/data'", () => {
    localStorage.setItem("rv_data_path", "");
    expect(getViewerSettings().dataPath).toBe("/data");
  });

  it("whitespace-only dataPath falls back to '/data'", () => {
    localStorage.setItem("rv_data_path", "   ");
    expect(getViewerSettings().dataPath).toBe("/data");
  });

  it("non-'true' showAll value returns false", () => {
    localStorage.setItem("rv_show_all", "yes");
    expect(getViewerSettings().showAll).toBe(false);
  });

  it("'1' as showAll returns false (only exact 'true' is truthy)", () => {
    localStorage.setItem("rv_show_all", "1");
    expect(getViewerSettings().showAll).toBe(false);
  });

  it("'TRUE' (uppercase) as showAll returns false (case-sensitive)", () => {
    localStorage.setItem("rv_show_all", "TRUE");
    expect(getViewerSettings().showAll).toBe(false);
  });
});

// ── (4) setViewerSetting serialization ───────────────────────────────────────

describe("setViewerSetting — serialization", () => {
  it("serializes boolean true as string 'true'", () => {
    setViewerSetting("showAll", true);
    expect(localStorage.getItem("rv_show_all")).toBe("true");
  });

  it("serializes boolean false as string 'false'", () => {
    setViewerSetting("showAll", false);
    expect(localStorage.getItem("rv_show_all")).toBe("false");
  });

  it("writes theme string verbatim", () => {
    setViewerSetting("theme", "dark");
    expect(localStorage.getItem("rv_theme")).toBe("dark");
  });

  it("writes dataPath string verbatim", () => {
    setViewerSetting("dataPath", "/my/path");
    expect(localStorage.getItem("rv_data_path")).toBe("/my/path");
  });
});

// ── (5) applyTheme — attribute manipulation ───────────────────────────────────

describe("applyTheme", () => {
  it("'dark' sets data-theme=dark on documentElement", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    // cleanup
    document.documentElement.removeAttribute("data-theme");
  });

  it("'light' removes data-theme attribute", () => {
    document.documentElement.setAttribute("data-theme", "dark");
    applyTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBeNull();
  });

  it("'system' sets or removes data-theme based on prefers-color-scheme", () => {
    // jsdom matchMedia always returns false for prefers-color-scheme: dark
    applyTheme("system");
    // In jsdom prefers-color-scheme is light (matchMedia returns false)
    expect(document.documentElement.getAttribute("data-theme")).toBeNull();
  });
});

// ── (6) SettingsScreen — renders all four controls ───────────────────────────

describe("SettingsScreen — renders with defaults", () => {
  it("renders the settings screen container", () => {
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='settings-screen']")).not.toBeNull();
  });

  it("renders the sensitivity toggle (show-all-toggle)", () => {
    const { container } = render(<SettingsScreen />);
    const toggle = container.querySelector("[data-testid='show-all-toggle']");
    expect(toggle).not.toBeNull();
    expect((toggle as HTMLInputElement).type).toBe("checkbox");
  });

  it("sensitivity toggle is unchecked by default", () => {
    const { container } = render(<SettingsScreen />);
    const toggle = container.querySelector("[data-testid='show-all-toggle']") as HTMLInputElement;
    expect(toggle.checked).toBe(false);
  });

  it("renders the theme selector", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector("[data-testid='theme-select']");
    expect(select).not.toBeNull();
  });

  it("theme selector defaults to 'system'", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector("[data-testid='theme-select']") as HTMLSelectElement;
    expect(select.value).toBe("system");
  });

  it("renders the default-tab selector", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector("[data-testid='default-tab-select']");
    expect(select).not.toBeNull();
  });

  it("default-tab selector defaults to 'overview'", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector(
      "[data-testid='default-tab-select']",
    ) as HTMLSelectElement;
    expect(select.value).toBe("overview");
  });

  it("renders the data-path input", () => {
    const { container } = render(<SettingsScreen />);
    const input = container.querySelector("[data-testid='data-path-input']");
    expect(input).not.toBeNull();
  });

  it("data-path input defaults to '/data'", () => {
    const { container } = render(<SettingsScreen />);
    const input = container.querySelector(
      "[data-testid='data-path-input']",
    ) as HTMLInputElement;
    expect(input.value).toBe("/data");
  });

  it("renders the Save button for data path", () => {
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='data-path-save']")).not.toBeNull();
  });

  it("reload notice is absent before Save is clicked", () => {
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='data-path-reload-notice']")).toBeNull();
  });

  it("reload notice appears after Save is clicked", () => {
    const { container } = render(<SettingsScreen />);
    const saveBtn = container.querySelector(
      "[data-testid='data-path-save']",
    ) as HTMLElement;
    act(() => {
      fireEvent.click(saveBtn);
    });
    expect(
      container.querySelector("[data-testid='data-path-reload-notice']"),
    ).not.toBeNull();
  });
});

// ── (7) SettingsScreen — toggling sensitivity writes rv_show_all ──────────────

describe("SettingsScreen — sensitivity toggle writes localStorage", () => {
  it("toggling ON sets rv_show_all='true' in localStorage", () => {
    const { container } = render(<SettingsScreen />);
    const toggle = container.querySelector(
      "[data-testid='show-all-toggle']",
    ) as HTMLInputElement;
    act(() => {
      fireEvent.click(toggle);
    });
    expect(localStorage.getItem("rv_show_all")).toBe("true");
  });

  it("toggling OFF after ON sets rv_show_all='false' in localStorage", () => {
    const { container } = render(<SettingsScreen />);
    const toggle = container.querySelector(
      "[data-testid='show-all-toggle']",
    ) as HTMLInputElement;
    // toggle ON
    act(() => { fireEvent.click(toggle); });
    expect(localStorage.getItem("rv_show_all")).toBe("true");
    // toggle OFF
    act(() => { fireEvent.click(toggle); });
    expect(localStorage.getItem("rv_show_all")).toBe("false");
  });
});

// ── (8) SettingsScreen — default tab selection wires to coerceDetailTab ───────

describe("SettingsScreen — default tab select wires to coerceDetailTab", () => {
  it("selecting 'trust' makes coerceDetailTab(null) return 'trust'", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector(
      "[data-testid='default-tab-select']",
    ) as HTMLSelectElement;
    act(() => {
      fireEvent.change(select, { target: { value: "trust" } });
    });
    // coerceDetailTab reads the stored default via getViewerSettings()
    expect(coerceDetailTab(null)).toBe("trust");
  });

  it("selecting 'report' makes coerceDetailTab(null) return 'report'", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector(
      "[data-testid='default-tab-select']",
    ) as HTMLSelectElement;
    act(() => {
      fireEvent.change(select, { target: { value: "report" } });
    });
    expect(coerceDetailTab(null)).toBe("report");
  });

  it("selecting 'lineage' makes coerceDetailTab(null) return 'lineage'", () => {
    const { container } = render(<SettingsScreen />);
    const select = container.querySelector(
      "[data-testid='default-tab-select']",
    ) as HTMLSelectElement;
    act(() => {
      fireEvent.change(select, { target: { value: "lineage" } });
    });
    expect(coerceDetailTab(null)).toBe("lineage");
  });

  it("coerceDetailTab(null) returns 'overview' when no default is stored (existing tests regression check)", () => {
    // no localStorage entry → default is 'overview'
    expect(coerceDetailTab(null)).toBe("overview");
  });

  it("coerceDetailTab explicit value overrides stored default (explicit values always win)", () => {
    setViewerSetting("defaultTab", "trust");
    // An explicit valid string bypasses the fallback entirely
    expect(coerceDetailTab("report")).toBe("report");
  });
});

// ── (9) Data path save ────────────────────────────────────────────────────────

describe("SettingsScreen — data path save", () => {
  it("clicking Save writes rv_data_path to localStorage", () => {
    const { container } = render(<SettingsScreen />);
    const input = container.querySelector(
      "[data-testid='data-path-input']",
    ) as HTMLInputElement;
    const saveBtn = container.querySelector(
      "[data-testid='data-path-save']",
    ) as HTMLElement;

    act(() => {
      fireEvent.change(input, { target: { value: "/my/runs" } });
    });
    act(() => {
      fireEvent.click(saveBtn);
    });

    expect(localStorage.getItem("rv_data_path")).toBe("/my/runs");
  });

  it("saving an empty input persists '/data' (fallback)", () => {
    const { container } = render(<SettingsScreen />);
    const input = container.querySelector(
      "[data-testid='data-path-input']",
    ) as HTMLInputElement;
    const saveBtn = container.querySelector(
      "[data-testid='data-path-save']",
    ) as HTMLElement;

    act(() => {
      fireEvent.change(input, { target: { value: "" } });
    });
    act(() => {
      fireEvent.click(saveBtn);
    });

    expect(localStorage.getItem("rv_data_path")).toBe("/data");
  });
});
