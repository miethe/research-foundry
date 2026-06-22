/**
 * report-outline.test.tsx
 *
 * D5 — ReportOutline unit tests.
 *
 * Coverage:
 *   (1) extractHeadings: correct slug/text/level extraction from markdown
 *   (2) extractHeadings: deduplicates slugs (-2, -3, …)
 *   (3) extractHeadings: ignores h1 headings and code fence contents
 *   (4) ReportOutline: renders list of headings
 *   (5) ReportOutline: clicking a heading fires onHeadingClick
 *   (6) ReportOutline: active item has --active class and aria-current
 *   (7) ReportOutline: empty state renders gracefully (no error, no list)
 */

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent }         from "@testing-library/react";
import { ReportOutline }                    from "@/components/ReportOverlay/ReportOutline";
import { extractHeadings }                 from "@/components/ReportOverlay/reportOutlineUtils";
import type { OutlineHeading }             from "@/components/ReportOverlay/reportOutlineUtils";

// ── (1) extractHeadings: basic extraction ────────────────────────────────────

describe("extractHeadings", () => {
  it("extracts h2 and h3 headings with correct slug, text, level", () => {
    const md = `
# Introduction

## Background

Some text here.

### Sub-section One

More text.

## Methodology
`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(3);
    expect(headings[0]).toMatchObject({ slug: "background",       text: "Background",       level: 2 });
    expect(headings[1]).toMatchObject({ slug: "sub-section-one",  text: "Sub-section One",  level: 3 });
    expect(headings[2]).toMatchObject({ slug: "methodology",      text: "Methodology",      level: 2 });
  });

  // ── (2) deduplication ─────────────────────────────────────────────────────

  it("deduplicates repeated slugs by appending -2, -3", () => {
    const md = `
## Results

## Results

## Results
`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(3);
    expect(headings[0]!.slug).toBe("results");
    expect(headings[1]!.slug).toBe("results-2");
    expect(headings[2]!.slug).toBe("results-3");
  });

  // ── (3) ignores h1 and code fences ───────────────────────────────────────

  it("ignores h1 headings", () => {
    const md = `
# Title

## Section A
`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0]!.level).toBe(2);
  });

  it("ignores headings inside code fences", () => {
    const md = `
## Real Heading

\`\`\`
## Fake Heading in Code
\`\`\`

## Another Real Heading
`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(2);
    expect(headings.map((h) => h.text)).toEqual(["Real Heading", "Another Real Heading"]);
  });

  it("strips inline markdown from display text", () => {
    const md = "## **Bold** and `code` heading\n";
    const headings = extractHeadings(md);
    expect(headings[0]!.text).toBe("Bold and code heading");
  });

  it("returns empty array for empty markdown", () => {
    expect(extractHeadings("")).toHaveLength(0);
    expect(extractHeadings("   ")).toHaveLength(0);
  });
});

// ── (4) ReportOutline: renders list of headings ───────────────────────────────

describe("ReportOutline", () => {
  const headings: OutlineHeading[] = [
    { slug: "background",      text: "Background",      level: 2 },
    { slug: "sub-section-one", text: "Sub-section One", level: 3 },
    { slug: "methodology",     text: "Methodology",     level: 2 },
  ];

  it("renders all heading items", () => {
    const { getByTestId, getAllByRole } = render(
      <ReportOutline headings={headings} />,
    );
    const outline = getByTestId("report-outline");
    expect(outline).toBeTruthy();

    // Each heading renders as a button
    const buttons = getAllByRole("button");
    expect(buttons).toHaveLength(3);
    expect(buttons[0]!.textContent).toBe("Background");
    expect(buttons[1]!.textContent).toBe("Sub-section One");
    expect(buttons[2]!.textContent).toBe("Methodology");
  });

  // ── (5) click fires onHeadingClick ───────────────────────────────────────

  it("clicking a heading button fires onHeadingClick with its slug", () => {
    const onHeadingClick = vi.fn();
    const { getByTestId } = render(
      <ReportOutline headings={headings} onHeadingClick={onHeadingClick} />,
    );

    const btn = getByTestId("outline-item-background");
    fireEvent.click(btn);
    expect(onHeadingClick).toHaveBeenCalledTimes(1);
    expect(onHeadingClick).toHaveBeenCalledWith("background");
  });

  it("clicking another heading fires onHeadingClick with its slug", () => {
    const onHeadingClick = vi.fn();
    const { getByTestId } = render(
      <ReportOutline headings={headings} onHeadingClick={onHeadingClick} />,
    );

    const btn = getByTestId("outline-item-methodology");
    fireEvent.click(btn);
    expect(onHeadingClick).toHaveBeenCalledWith("methodology");
  });

  // ── (6) active item ───────────────────────────────────────────────────────

  it("active item has --active class and aria-current='true'", () => {
    const { getByTestId } = render(
      <ReportOutline headings={headings} activeSlug="methodology" />,
    );

    // The active button has aria-current="true"
    const activeBtn = getByTestId("outline-item-methodology");
    expect(activeBtn.getAttribute("aria-current")).toBe("true");

    // Its parent <li> has the --active class
    const li = activeBtn.closest("li");
    expect(li?.classList.contains("rv-report-outline__item--active")).toBe(true);

    // Other items do NOT have aria-current
    const inactiveBtn = getByTestId("outline-item-background");
    expect(inactiveBtn.getAttribute("aria-current")).toBeNull();
  });

  it("no item has --active class when activeSlug is null", () => {
    const { container } = render(
      <ReportOutline headings={headings} activeSlug={null} />,
    );
    const activeItems = container.querySelectorAll(".rv-report-outline__item--active");
    expect(activeItems).toHaveLength(0);
  });

  // ── (7) empty state ───────────────────────────────────────────────────────

  it("renders empty state gracefully when headings array is empty", () => {
    const { getByTestId, queryByRole } = render(
      <ReportOutline headings={[]} />,
    );
    const outline = getByTestId("report-outline");
    expect(outline).toBeTruthy();

    // No list items / buttons
    const buttons = queryByRole("button");
    expect(buttons).toBeNull();
  });

  // ── h3 indentation ────────────────────────────────────────────────────────

  it("h3 items have level 1 (--level=1) and h2 items have level 0 (--level=0)", () => {
    const { getByTestId } = render(
      <ReportOutline headings={headings} />,
    );

    const h2li = getByTestId("outline-item-background").closest("li");
    const h3li = getByTestId("outline-item-sub-section-one").closest("li");

    // CSS custom properties are set inline via style
    expect((h2li as HTMLElement).style.getPropertyValue("--level")).toBe("0");
    expect((h3li as HTMLElement).style.getPropertyValue("--level")).toBe("1");
  });
});
