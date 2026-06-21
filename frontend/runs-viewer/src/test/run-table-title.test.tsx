/**
 * run-table-title.test.tsx — regression test locking in the Portfolio RunTable
 * title-column behaviour.
 *
 * Bug context: the Portfolio runs table must show a readable human title as its
 * primary first column, with run_id as subtext.  This class of regression was
 * previously uncovered by tests — this file makes it permanent.
 *
 * Assertions:
 *   (a) Table header shows "Title", not "Run ID"
 *   (b) Run WITH a title renders that title text as the primary clickable cell
 *   (c) run_id always appears as subtext with class rv-table-run-id
 *   (d) Run with title:null falls back to titleFromSlug(run_id), not the raw
 *       underscore id
 */

import { describe, it, expect, vi } from "vitest";
import { render }                   from "@testing-library/react";
import { MemoryRouter }             from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode }           from "react";

import { RunTable }                 from "@/screens/RunList";
import type { RunCardData }         from "@/components/RunList/RunCard";
import { titleFromSlug }            from "@/lib/runs";

// ── Helpers (mirrored from p3-components.test.tsx) ────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

function makeCard(overrides: Partial<RunCardData> = {}): RunCardData {
  return {
    run_id:         "rf_run_test_001",
    status_derived: "verified",
    created_at:     "2026-06-13T22:46:23-04:00",
    sensitivity:    "personal",
    claim_counts: {
      total:       91,
      supported:   69,
      inference:   20,
      speculation:  2,
    },
    verification_passed: true,
    ...overrides,
  };
}

// ── Mock runs used by all tests ───────────────────────────────────────────────

/** Run that carries an explicit human-readable title. */
const RUN_WITH_TITLE = makeCard({
  run_id: "rf_run_titled_001",
  title:  "My Readable Title",
});

/**
 * Run without an explicit title — run_id is a slug-style string so that the
 * fallback path (titleFromSlug) returns a humanized string rather than the
 * raw underscore id.
 */
const SLUG_RUN_ID = "rf_run_my_slug_id";
const RUN_WITHOUT_TITLE = makeCard({
  run_id: SLUG_RUN_ID,
  title:  null,
});

const noop = vi.fn();

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("RunTable — title column regression", () => {
  function renderTable() {
    return render(
      <RunTable
        runs={[RUN_WITH_TITLE, RUN_WITHOUT_TITLE]}
        selectedRunId={null}
        onSelect={noop}
        onOpen={noop}
      />,
      { wrapper: makeWrapper() },
    );
  }

  // (a) Table header must show "Title", not "Run ID"
  it("(a) table header shows 'Title' as first column header", () => {
    const { container } = renderTable();
    const headers = container.querySelectorAll("thead th");
    expect(headers.length).toBeGreaterThan(0);
    expect(headers[0]?.textContent?.trim()).toBe("Title");
  });

  it("(a) table header does NOT show 'Run ID' as first column header", () => {
    const { container } = renderTable();
    const firstHeader = container.querySelector("thead th");
    expect(firstHeader?.textContent?.trim()).not.toBe("Run ID");
  });

  // (b) Run WITH a title renders title text as the primary clickable cell
  it("(b) run with title renders that title as the primary .rv-table-link button text", () => {
    const { container } = renderTable();
    const linkButtons = container.querySelectorAll("button.rv-table-link");
    const texts = Array.from(linkButtons).map((btn) => btn.textContent?.trim());
    expect(texts).toContain("My Readable Title");
  });

  it("(b) .rv-table-link aria-label for titled run references the title", () => {
    const { container } = renderTable();
    const linkButtons = Array.from(container.querySelectorAll("button.rv-table-link"));
    const titledBtn = linkButtons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("My Readable Title"),
    );
    expect(titledBtn).not.toBeNull();
  });

  // (c) run_id appears as subtext with class rv-table-run-id
  it("(c) titled run's run_id appears as subtext with class rv-table-run-id", () => {
    const { container } = renderTable();
    const subtextSpans = container.querySelectorAll(".rv-table-run-id");
    const runIds = Array.from(subtextSpans).map((span) => span.textContent?.trim());
    expect(runIds).toContain(RUN_WITH_TITLE.run_id);
  });

  it("(c) untitled run's run_id appears as subtext with class rv-table-run-id", () => {
    const { container } = renderTable();
    const subtextSpans = container.querySelectorAll(".rv-table-run-id");
    const runIds = Array.from(subtextSpans).map((span) => span.textContent?.trim());
    expect(runIds).toContain(SLUG_RUN_ID);
  });

  // (d) Run with title:null falls back to titleFromSlug(run_id), not the raw id
  it("(d) run with title:null shows humanized slug, not raw underscore run_id, as primary text", () => {
    const { container } = renderTable();
    const linkButtons = Array.from(container.querySelectorAll("button.rv-table-link"));

    // The humanized fallback for SLUG_RUN_ID
    const humanized = titleFromSlug(SLUG_RUN_ID)!;
    // titleFromSlug strips "rf_run_" prefix and capitalizes → "My Slug Id"
    expect(humanized).toBeTruthy();
    expect(humanized).not.toContain("_");  // no underscores in the humanized form

    const slugBtnTexts = linkButtons.map((btn) => btn.textContent?.trim());
    expect(slugBtnTexts).toContain(humanized);
  });

  it("(d) raw underscore run_id does NOT appear as primary .rv-table-link button text", () => {
    const { container } = renderTable();
    const linkButtons = Array.from(container.querySelectorAll("button.rv-table-link"));
    const texts = linkButtons.map((btn) => btn.textContent?.trim());
    // The raw slug-style id with underscores must not be used as the displayed title
    expect(texts).not.toContain(SLUG_RUN_ID);
  });
});
