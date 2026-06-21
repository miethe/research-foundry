/**
 * G4-library tests — LibraryScreen component tests + isActiveNav coverage for Library.
 *
 * Covers:
 *   SMOKE-G4-01: Library nav item is enabled (state="enabled", not disabled)
 *   SMOKE-G4-02: Library nav item has aria-current="page" at /library
 *   SMOKE-G4-03: Library nav item does NOT have aria-current="page" elsewhere
 *   SMOKE-G4-04: LibraryScreen renders without crash (empty state, no run data)
 *   TEST-G4-01: Published Reports section shows empty-state when no qualifying runs
 *   TEST-G4-02: Published Reports section renders qualifying run entries
 *   TEST-G4-03: Writeback Artifacts section shows empty-state when no targets
 *   TEST-G4-04: Writeback Artifacts section renders entries with status badge
 *   TEST-G4-05: Reusable Outputs section shows pre-F5 empty-state when field absent
 *   TEST-G4-06: Reusable Outputs section renders entries with SkillBOM badge when present
 *   TEST-G4-07: LibraryScreen does NOT throw when writebacks is null AND
 *               reusable_output_candidates is undefined (primary resilience AC)
 *   TEST-G4-08: isActiveNav returns false for Library at /runs
 *   TEST-G4-09: enabling Library does not break other nav active states
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LibraryScreen } from "@/screens/LibraryScreen";
import { AppShell } from "@/app/AppShell";
import { runListQueryKey } from "@/hooks";
import type { RFRunExport, RFRunSummary } from "@/types/rf";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeRunSummary(runId: string): RFRunSummary {
  return {
    run_id: runId,
    status_derived: "verified",
    created_at: "2026-01-01",
    sensitivity: "public",
    claim_counts: null,
    title: null,
    linked_projects: null,
    category: null,
    tags: null,
  };
}

/** Minimal run with no writebacks and no reusable_output_candidates. */
function makeRunEmpty(runId: string): RFRunExport {
  return {
    schema_version: "1.1",
    run_id: runId,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: null,
    governance: null,
    timeline: null,
    writebacks: null,
    // reusable_output_candidates deliberately absent
  };
}

/** Run that qualifies as a Published Report (report_draft present + approved_for_writeback). */
function makeRunPublished(runId: string): RFRunExport {
  return {
    ...makeRunEmpty(runId),
    title: "My Published Report",
    report_draft: "# My Published Report\n\nSome content here.",
    writebacks: {
      targets: [{ name: "MeatyWiki", destination: "meatywiki://kb", status: "published" }],
      approved_for_writeback: true,
    },
  };
}

/** Run with writeback targets but not approved for writeback. */
function makeRunWithWritebacks(runId: string): RFRunExport {
  return {
    ...makeRunEmpty(runId),
    title: "Run With Writebacks",
    writebacks: {
      targets: [
        { name: "NLM", destination: "notebooklm://", status: "pending" },
        { name: "SkillMeat", destination: "skillmeat://", status: "failed", url: "https://example.com/skill" },
      ],
      approved_for_writeback: false,
    },
  };
}

/** Run with reusable_output_candidates (post-F5 export). */
function makeRunWithReusableOutputs(runId: string): RFRunExport {
  return {
    ...makeRunEmpty(runId),
    reusable_output_candidates: [
      {
        description: "Structured knowledge on RF claim pipeline",
        is_skillbom_candidate: true,
        source_run_id: runId,
      },
      {
        description: "Notes on NLM integration patterns",
        is_skillbom_candidate: false,
        source_run_id: runId,
      },
    ],
  };
}

// ── Test helpers ───────────────────────────────────────────────────────────────

function makeQC(opts: {
  summaries?: RFRunSummary[];
  runExports?: RFRunExport[];
}): QueryClient {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  if (opts.summaries) {
    qc.setQueryData(runListQueryKey, opts.summaries);
  }
  if (opts.runExports) {
    for (const run of opts.runExports) {
      qc.setQueryData(["rf", "runs", "detail", run.run_id], run);
    }
  }
  return qc;
}

function renderLibrary(opts: { summaries?: RFRunSummary[]; runExports?: RFRunExport[] } = {}) {
  const qc = makeQC(opts);
  return render(
    <MemoryRouter initialEntries={["/library"]}>
      <QueryClientProvider client={qc}>
        <LibraryScreen />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

// ── SMOKE-G4-01: Library nav item enabled ─────────────────────────────────────

describe("isActiveNav — Library nav item (AC G4-1, AC G4-2, SMOKE-G4-01)", () => {
  it("Library nav button is NOT disabled at /library", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/library"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    ) as HTMLButtonElement | undefined;
    expect(libBtn).not.toBeUndefined();
    expect(libBtn!.disabled).toBe(false);
  });

  it("Library nav button does NOT have data-state='disabled' at /library", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/library"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    );
    expect(libBtn!.getAttribute("data-state")).toBe("enabled");
  });

  // SMOKE-G4-02: aria-current at /library
  it("Library nav button has aria-current='page' at /library", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/library"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    );
    expect(libBtn).not.toBeUndefined();
    expect(libBtn!.getAttribute("aria-current")).toBe("page");
  });

  // SMOKE-G4-03: aria-current NOT set elsewhere
  it("Library nav button does NOT have aria-current='page' at /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    );
    expect(libBtn!.getAttribute("aria-current")).toBeNull();
  });
});

// ── TEST-G4-08 / TEST-G4-09: isActiveNav regressions ────────────────────────

describe("Library nav — regression on existing nav items (TEST-G4-08, TEST-G4-09)", () => {
  it("Portfolio is still active at /runs", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const pfBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Portfolio",
    );
    expect(pfBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Alerts is still active at /alerts and Library is not", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/alerts"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const alertsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Alerts",
    );
    expect(alertsBtn!.getAttribute("aria-current")).toBe("page");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    );
    expect(libBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("Policies is still active at /policies and Library is not", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/policies"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const policiesBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    );
    expect(policiesBtn!.getAttribute("aria-current")).toBe("page");
    const libBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Library",
    );
    expect(libBtn!.getAttribute("aria-current")).toBeNull();
  });
});

// ── SMOKE-G4-04: LibraryScreen renders without crash (empty state) ────────────

describe("LibraryScreen — render without crash (SMOKE-G4-04)", () => {
  it("renders the library screen container with no run data", () => {
    const { container } = renderLibrary();
    expect(container.querySelector("[data-testid='library-screen']")).not.toBeNull();
  });

  it("renders all three section headings", () => {
    const { container } = renderLibrary();
    expect(container.querySelector("[data-testid='library-reports-section']")).not.toBeNull();
    expect(container.querySelector("[data-testid='library-writebacks-section']")).not.toBeNull();
    expect(container.querySelector("[data-testid='library-reusable-section']")).not.toBeNull();
  });

  it("does NOT throw when called with no run data at all", () => {
    expect(() => renderLibrary()).not.toThrow();
  });
});

// ── TEST-G4-01 / TEST-G4-02: Published Reports section ───────────────────────

describe("LibraryScreen — Published Reports section (AC G4-3, TEST-G4-01, TEST-G4-02)", () => {
  it("shows empty-state for Published Reports when no qualifying runs", () => {
    const summary = makeRunSummary("run_no_pub");
    const run = makeRunEmpty("run_no_pub");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    expect(container.querySelector("[data-testid='library-reports-empty']")).not.toBeNull();
  });

  it("shows empty-state when approved_for_writeback is false", () => {
    const summary = makeRunSummary("run_not_approved");
    const run = makeRunWithWritebacks("run_not_approved");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    expect(container.querySelector("[data-testid='library-reports-empty']")).not.toBeNull();
  });

  it("renders Published Report card for a qualifying run", () => {
    const summary = makeRunSummary("run_pub");
    const run = makeRunPublished("run_pub");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    expect(container.querySelector("[data-testid='library-report-card']")).not.toBeNull();
  });

  it("shows run title in Published Report card", () => {
    const summary = makeRunSummary("run_pub_title");
    const run = makeRunPublished("run_pub_title");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const card = container.querySelector("[data-testid='library-report-card']");
    expect(card?.textContent).toContain("My Published Report");
  });

  it("shows link to run report tab for Published Report", () => {
    const summary = makeRunSummary("run_pub_link");
    const run = makeRunPublished("run_pub_link");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const link = container.querySelector("[data-testid='library-report-link']") as HTMLAnchorElement | null;
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toContain("view=report");
  });
});

// ── TEST-G4-03 / TEST-G4-04: Writeback Artifacts section ─────────────────────

describe("LibraryScreen — Writeback Artifacts section (AC G4-4, TEST-G4-03, TEST-G4-04)", () => {
  it("shows empty-state for Writeback Artifacts when no runs have targets", () => {
    const summary = makeRunSummary("run_no_wb");
    const run = makeRunEmpty("run_no_wb");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    expect(container.querySelector("[data-testid='library-writebacks-empty']")).not.toBeNull();
  });

  it("renders Writeback Artifact cards for a run with targets", () => {
    const summary = makeRunSummary("run_wb");
    const run = makeRunWithWritebacks("run_wb");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const cards = container.querySelectorAll("[data-testid='library-writeback-card']");
    expect(cards.length).toBe(2);
  });

  it("renders status badge on Writeback Artifact card", () => {
    const summary = makeRunSummary("run_wb_badge");
    const run = makeRunWithWritebacks("run_wb_badge");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const badges = container.querySelectorAll("[data-testid='library-writeback-status']");
    expect(badges.length).toBeGreaterThan(0);
    const texts = Array.from(badges).map((b) => b.textContent);
    expect(texts).toContain("pending");
  });

  it("renders target name in Writeback Artifact card", () => {
    const summary = makeRunSummary("run_wb_name");
    const run = makeRunWithWritebacks("run_wb_name");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const cards = container.querySelectorAll("[data-testid='library-writeback-card']");
    const text = Array.from(cards).map((c) => c.textContent).join(" ");
    expect(text).toContain("NLM");
  });

  it("renders URL link when target has a url field", () => {
    const summary = makeRunSummary("run_wb_url");
    const run = makeRunWithWritebacks("run_wb_url");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const urlLink = container.querySelector("[data-testid='library-writeback-url']") as HTMLAnchorElement | null;
    expect(urlLink).not.toBeNull();
    expect(urlLink!.getAttribute("href")).toBe("https://example.com/skill");
  });
});

// ── TEST-G4-05 / TEST-G4-06: Reusable Outputs section ────────────────────────

describe("LibraryScreen — Reusable Outputs section (AC G4-5, TEST-G4-05, TEST-G4-06)", () => {
  it("shows pre-F5 empty-state when reusable_output_candidates is absent on all runs", () => {
    const summary = makeRunSummary("run_no_roc");
    const run = makeRunEmpty("run_no_roc"); // field is absent
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const emptyEl = container.querySelector("[data-testid='library-reusable-empty-pref5']");
    expect(emptyEl).not.toBeNull();
    expect(emptyEl!.textContent).toContain("run-metadata-enrichment");
  });

  it("shows pre-F5 empty-state message text specifically about F5", () => {
    const summary = makeRunSummary("run_no_roc2");
    const run = makeRunEmpty("run_no_roc2");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const msg = container.querySelector("[data-testid='library-reusable-empty-message']");
    expect(msg).not.toBeNull();
    expect(msg!.textContent).toContain("Re-export runs to populate");
  });

  it("renders Reusable Output cards when field is present with data", () => {
    const summary = makeRunSummary("run_roc");
    const run = makeRunWithReusableOutputs("run_roc");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const cards = container.querySelectorAll("[data-testid='library-reusable-card']");
    expect(cards.length).toBe(2);
  });

  it("renders SkillBOM badge when is_skillbom_candidate is true", () => {
    const summary = makeRunSummary("run_roc_badge");
    const run = makeRunWithReusableOutputs("run_roc_badge");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const badge = container.querySelector("[data-testid='library-skillbom-badge']");
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toContain("SkillBOM candidate");
  });

  it("renders candidate description in Reusable Output card", () => {
    const summary = makeRunSummary("run_roc_desc");
    const run = makeRunWithReusableOutputs("run_roc_desc");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const cards = container.querySelectorAll("[data-testid='library-reusable-card']");
    const text = Array.from(cards).map((c) => c.textContent).join(" ");
    expect(text).toContain("Structured knowledge on RF claim pipeline");
  });
});

// ── TEST-G4-06b: AC G4-7 stale-run guard for Reusable Outputs ────────────────

describe("LibraryScreen — Reusable Outputs stale-run guard (AC G4-7)", () => {
  it("renders a plain span (not a Link) when source_run_id is NOT in the summary index", () => {
    // The run that contains the candidate IS loaded, but its source_run_id points to a
    // different run ('stale_run_xyz') that is NOT in the summary index.
    const summary = makeRunSummary("run_roc_stale_host");
    const run: RFRunExport = {
      ...makeRunEmpty("run_roc_stale_host"),
      reusable_output_candidates: [
        {
          description: "Output from a stale source run",
          is_skillbom_candidate: false,
          source_run_id: "stale_run_xyz", // NOT in summaryIds
        },
      ],
    };
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    // Must render a card
    const card = container.querySelector("[data-testid='library-reusable-card']");
    expect(card).not.toBeNull();
    // Must render the stale-run plain-text span, not a link
    const staleSpan = container.querySelector("[data-testid='library-reusable-run-text']");
    expect(staleSpan).not.toBeNull();
    // Must NOT render a react-router Link anchor for the run reference
    const runLink = container.querySelector("[data-testid='library-reusable-run-link']");
    expect(runLink).toBeNull();
  });

  it("renders a Link when source_run_id IS in the summary index", () => {
    const summary = makeRunSummary("run_roc_indexed");
    const run: RFRunExport = {
      ...makeRunEmpty("run_roc_indexed"),
      reusable_output_candidates: [
        {
          description: "Output from an indexed run",
          is_skillbom_candidate: true,
          source_run_id: "run_roc_indexed", // IS in summaryIds
        },
      ],
    };
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const runLink = container.querySelector("[data-testid='library-reusable-run-link']");
    expect(runLink).not.toBeNull();
    const staleSpan = container.querySelector("[data-testid='library-reusable-run-text']");
    expect(staleSpan).toBeNull();
  });

  it("falls back to runId check when source_run_id is absent and runId IS in index", () => {
    const summary = makeRunSummary("run_roc_fallback");
    const run: RFRunExport = {
      ...makeRunEmpty("run_roc_fallback"),
      reusable_output_candidates: [
        {
          description: "Output with no source_run_id",
          is_skillbom_candidate: false,
          // source_run_id absent — should fall back to run.run_id which IS in summaryIds
        },
      ],
    };
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    const runLink = container.querySelector("[data-testid='library-reusable-run-link']");
    expect(runLink).not.toBeNull();
  });
});

// ── TEST-G4-07: Primary resilience — no crash when writebacks null + reusable absent ─

describe("LibraryScreen — resilience (AC G4-5, unit-G4-resilience, TEST-G4-07)", () => {
  it("does NOT throw when writebacks is null AND reusable_output_candidates is undefined", () => {
    const summary = makeRunSummary("run_resilience");
    const run = makeRunEmpty("run_resilience"); // writebacks: null, reusable_output_candidates: absent
    expect(() => renderLibrary({ summaries: [summary], runExports: [run] })).not.toThrow();
  });

  it("renders all three sections without crash when data is fully absent", () => {
    const summary = makeRunSummary("run_resilience2");
    const run = makeRunEmpty("run_resilience2");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    // All three section containers must render
    expect(container.querySelector("[data-testid='library-reports-section']")).not.toBeNull();
    expect(container.querySelector("[data-testid='library-writebacks-section']")).not.toBeNull();
    expect(container.querySelector("[data-testid='library-reusable-section']")).not.toBeNull();
  });

  it("does NOT render a blank white area when all data absent — shows empty states", () => {
    const summary = makeRunSummary("run_resilience3");
    const run = makeRunEmpty("run_resilience3");
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    // At least one [role=note] empty-state must be present in each section
    const notes = container.querySelectorAll("[role='note']");
    expect(notes.length).toBeGreaterThanOrEqual(3);
  });

  it("shows empty-states (not crash) when run has writebacks=null", () => {
    const summary = makeRunSummary("run_wb_null");
    const run: RFRunExport = { ...makeRunEmpty("run_wb_null"), writebacks: null };
    const { container } = renderLibrary({ summaries: [summary], runExports: [run] });
    expect(container.querySelector("[data-testid='library-writebacks-empty']")).not.toBeNull();
    expect(container.querySelector("[data-testid='library-reports-empty']")).not.toBeNull();
  });

  it("does NOT throw when multiple runs all have no data fields", () => {
    const summaries = ["run_r1", "run_r2", "run_r3"].map(makeRunSummary);
    const runs = ["run_r1", "run_r2", "run_r3"].map(makeRunEmpty);
    expect(() => renderLibrary({ summaries, runExports: runs })).not.toThrow();
  });
});
