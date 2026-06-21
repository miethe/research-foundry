/**
 * G6-help tests — HelpScreen component tests + isActiveNav coverage for Help.
 *
 * Covers:
 *   UNIT-G6-screen: render HelpScreen and assert all four section headings present
 *   UNIT-G6-screen: assert all eight glossary terms are present
 *   UNIT-G6-screen: assert keyboard shortcuts table contains at least Escape
 *   UNIT-G6-screen: assert external links have target="_blank" and rel="noopener noreferrer"
 *   UNIT-G6-nav:   isActiveNav returns true for Help when pathname="/help"
 *   UNIT-G6-nav:   isActiveNav returns false for Help on other pathnames
 *
 * Note: isActiveNav is not exported from AppShell directly, so we test it
 * indirectly by confirming the NAV_ITEMS / Help nav item resolves /help and
 * that the function logic is consistent (verified via the rendered aria-current
 * attribute on the nav button when rendered with MemoryRouter at /help).
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { HelpScreen } from "@/screens/HelpScreen";
import { AppShell } from "@/app/AppShell";

// ── UNIT-G6-screen: HelpScreen renders all four sections ────────────────────

describe("HelpScreen — renders all four sections", () => {
  it("renders the help screen container", () => {
    const { container } = render(<HelpScreen />);
    expect(container.querySelector("[data-testid='help-screen']")).not.toBeNull();
  });

  it("renders the About section", () => {
    const { container } = render(<HelpScreen />);
    expect(container.querySelector("[data-testid='help-section-about']")).not.toBeNull();
  });

  it("renders the Keyboard Shortcuts section", () => {
    const { container } = render(<HelpScreen />);
    expect(container.querySelector("[data-testid='help-section-shortcuts']")).not.toBeNull();
  });

  it("renders the Glossary section", () => {
    const { container } = render(<HelpScreen />);
    expect(container.querySelector("[data-testid='help-section-glossary']")).not.toBeNull();
  });

  it("renders the Links section", () => {
    const { container } = render(<HelpScreen />);
    expect(container.querySelector("[data-testid='help-section-links']")).not.toBeNull();
  });

  it("renders the page heading 'Help'", () => {
    const { container } = render(<HelpScreen />);
    const h1 = container.querySelector("h1");
    expect(h1).not.toBeNull();
    expect(h1!.textContent).toBe("Help");
  });
});

// ── UNIT-G6-screen: all eight glossary terms present ────────────────────────

describe("HelpScreen — glossary contains all eight required terms", () => {
  const REQUIRED_TERMS = [
    "Claim",
    "Governance",
    "Lineage",
    "Run",
    "Sensitivity",
    "Source",
    "Verification",
    "Writeback",
  ];

  for (const term of REQUIRED_TERMS) {
    it(`glossary contains term: ${term}`, () => {
      const { container } = render(<HelpScreen />);
      const glossary = container.querySelector("[data-testid='help-section-glossary']");
      expect(glossary).not.toBeNull();
      const text = glossary!.textContent ?? "";
      expect(text).toContain(term);
    });
  }

  it("glossary terms appear in alphabetical order", () => {
    const { container } = render(<HelpScreen />);
    const termEls = container.querySelectorAll(".rv-help__term");
    const renderedTerms = Array.from(termEls).map((el) => el.textContent ?? "");
    const sorted = [...renderedTerms].sort((a, b) => a.localeCompare(b));
    expect(renderedTerms).toEqual(sorted);
  });
});

// ── UNIT-G6-screen: keyboard shortcuts table ────────────────────────────────

describe("HelpScreen — keyboard shortcuts table", () => {
  it("renders the shortcuts table", () => {
    const { container } = render(<HelpScreen />);
    const table = container.querySelector("[data-testid='help-section-shortcuts'] table");
    expect(table).not.toBeNull();
  });

  it("table has 'Key / Combo' and 'Action' column headers", () => {
    const { container } = render(<HelpScreen />);
    const headers = container.querySelectorAll(
      "[data-testid='help-section-shortcuts'] table th",
    );
    const headerTexts = Array.from(headers).map((h) => h.textContent);
    expect(headerTexts).toContain("Key / Combo");
    expect(headerTexts).toContain("Action");
  });

  it("Escape shortcut is documented", () => {
    const { container } = render(<HelpScreen />);
    const section = container.querySelector("[data-testid='help-section-shortcuts']");
    expect(section!.textContent).toContain("Escape");
  });

  it("Escape row describes closing overlay or detail pane", () => {
    const { container } = render(<HelpScreen />);
    const section = container.querySelector("[data-testid='help-section-shortcuts']");
    expect(section!.textContent).toMatch(/[Cc]lose.*overlay|detail pane|modal/);
  });
});

// ── UNIT-G6-screen: external links open safely ──────────────────────────────

describe("HelpScreen — external links open in new tab safely", () => {
  it("all anchor elements have target='_blank'", () => {
    const { container } = render(<HelpScreen />);
    const links = container.querySelectorAll(
      "[data-testid='help-section-links'] a",
    );
    expect(links.length).toBeGreaterThan(0);
    for (const link of Array.from(links)) {
      expect((link as HTMLAnchorElement).target).toBe("_blank");
    }
  });

  it("all anchor elements have rel='noopener noreferrer'", () => {
    const { container } = render(<HelpScreen />);
    const links = container.querySelectorAll(
      "[data-testid='help-section-links'] a",
    );
    for (const link of Array.from(links)) {
      expect((link as HTMLAnchorElement).rel).toContain("noopener");
      expect((link as HTMLAnchorElement).rel).toContain("noreferrer");
    }
  });
});

// ── UNIT-G6-screen: About section content ───────────────────────────────────

describe("HelpScreen — About section content", () => {
  it("About section contains non-empty descriptive text", () => {
    const { container } = render(<HelpScreen />);
    const about = container.querySelector("[data-testid='help-section-about']");
    expect(about!.textContent!.length).toBeGreaterThan(50);
  });

  it("About section mentions Research Foundry", () => {
    const { container } = render(<HelpScreen />);
    const about = container.querySelector("[data-testid='help-section-about']");
    expect(about!.textContent).toContain("Research Foundry");
  });
});

// ── UNIT-G6-nav: isActiveNav for Help ────────────────────────────────────────
// Test via rendered AppShell with MemoryRouter: the Help nav button should have
// aria-current="page" when pathname is /help, and not otherwise.

describe("isActiveNav — Help nav item active state", () => {
  it("Help nav button has aria-current='page' when pathname is /help", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/help"]}>
        <AppShell />
      </MemoryRouter>,
    );
    // Find the nav button whose text content includes "Help"
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const helpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    );
    expect(helpBtn).not.toBeUndefined();
    expect(helpBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Help nav button does NOT have aria-current='page' on /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const helpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    );
    expect(helpBtn).not.toBeUndefined();
    expect(helpBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("Help nav button does NOT have aria-current='page' on /settings", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const helpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    );
    expect(helpBtn).not.toBeUndefined();
    expect(helpBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("Help nav button is NOT disabled when pathname is /help", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/help"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const helpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    ) as HTMLButtonElement | undefined;
    expect(helpBtn).not.toBeUndefined();
    expect(helpBtn!.disabled).toBe(false);
  });

  it("Help nav button is NOT disabled when pathname is /runs (always-enabled)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const helpBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Help",
    ) as HTMLButtonElement | undefined;
    expect(helpBtn).not.toBeUndefined();
    expect(helpBtn!.disabled).toBe(false);
  });
});
