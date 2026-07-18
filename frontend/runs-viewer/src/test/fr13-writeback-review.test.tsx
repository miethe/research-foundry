/**
 * fr13-writeback-review.test.tsx — FR-13 Writeback Review Governance View tests.
 *
 * Covers the acceptance criteria from
 * docs/project_plans/feature_contracts/features/runs-writeback-review-view.md:
 *   - Governance panel renders approval state / reviewer_notes / required_fix,
 *     each with an explicit "Not set" state when null (never a blank row).
 *   - One candidate card per writebacks.previews[] entry.
 *   - .md candidates render as formatted Markdown; .yaml candidates render as
 *     a pre-formatted structured block, not raw unwrapped text.
 *   - Empty-state (no writeback files) is preserved unchanged in meaning.
 *   - Pre-1.6-schema exports (previews/reviewer_notes/required_fix keys
 *     entirely absent) degrade gracefully — no crash, sensible fallback.
 *   - Read-only invariant: no button/form in the tab can mutate governance
 *     state.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { RunDetailWorkspace } from "@/components/RunDetail/RunDetailWorkspace";
import type { RFRunExport } from "@/types/rf";
import type { RFRunWritebacksSummary } from "@/types/rf/run-export";

import scaffoldRunRaw from "@/test/fixtures/scaffold-run.json";

const scaffoldRun = scaffoldRunRaw as unknown as RFRunExport;

// ── Test helpers ──────────────────────────────────────────────────────────────

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

let _runIdCounter = 0;
function makeRun(writebacks: RFRunWritebacksSummary | null, runIdSuffix?: string): RFRunExport {
  const id = runIdSuffix ?? String(++_runIdCounter);
  const approved = writebacks?.approved_for_writeback;
  return {
    schema_version: "1.6",
    run_id: `rf_run_fr13_${id}`,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: { present: false, passed: null, exit_code: null, checks: [] },
    // RFGovernanceBlock.approved_for_writeback is `boolean | undefined` (no
    // explicit null) — omit the key entirely rather than assigning null.
    governance: approved == null ? {} : { approved_for_writeback: approved },
    timeline: null,
    writebacks,
  };
}

const FULL_WRITEBACKS: RFRunWritebacksSummary = {
  targets: [
    { name: "meatywiki", status: "present" },
    { name: "ccdash", status: "present" },
  ],
  approved_for_writeback: false,
  reviewer_notes: "Council flagged a blocking concern.",
  required_fix: "Resolve the failing verification check before publishing.",
  previews: [
    {
      target: "meatywiki",
      filename: "meatywiki_writeback.md",
      content_type: "markdown",
      content: "# MeatyWiki Candidate\n\nThis is **bold** writeback content with a [link](https://example.test).",
    },
    {
      target: "ccdash",
      filename: "ccdash_event.yaml",
      content_type: "yaml",
      content: "event: writeback\nstatus: pending\n",
    },
  ],
};

function renderWorkspace(run: RFRunExport) {
  return render(
    <RunDetailWorkspace run={run} activeTab="writeback" mode="page" onTabChange={() => {}} />,
    { wrapper: makeWrapper() },
  );
}

// ── Empty state (no writeback files) ─────────────────────────────────────────

describe("FR-13 — empty state (no writeback files)", () => {
  it("shows the unchanged empty-state message when writebacks is null", () => {
    const run = makeRun(null);
    const { container } = renderWorkspace(run);
    const empty = container.querySelector("[data-testid='writeback-empty-state']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("Writeback preview is not exported for this run yet.");
  });

  it("shows the empty state for the pre-migration scaffold fixture (schema 1.0, no writebacks key)", () => {
    const { container } = renderWorkspace(scaffoldRun);
    expect(container.querySelector("[data-testid='writeback-empty-state']")).not.toBeNull();
  });

  it("does not render the governance panel or candidate cards in the empty state", () => {
    const run = makeRun(null);
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-governance-panel']")).toBeNull();
    expect(container.querySelector("[data-testid='writeback-candidates']")).toBeNull();
  });
});

// ── Governance panel ─────────────────────────────────────────────────────────

describe("FR-13 — governance status panel", () => {
  it("renders approval state, reviewer notes, and required fix when populated", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const panel = container.querySelector("[data-testid='writeback-governance-panel']");
    expect(panel).not.toBeNull();
    expect(
      container.querySelector("[data-testid='writeback-approval-state']")!.textContent,
    ).toContain("Not approved");
    expect(
      container.querySelector("[data-testid='writeback-reviewer-notes']")!.textContent,
    ).toContain("Council flagged a blocking concern.");
    expect(
      container.querySelector("[data-testid='writeback-required-fix']")!.textContent,
    ).toContain("Resolve the failing verification check before publishing.");
  });

  it("shows 'Approved' chip when approved_for_writeback is true", () => {
    const run = makeRun({ ...FULL_WRITEBACKS, approved_for_writeback: true });
    const { container } = renderWorkspace(run);
    expect(
      container.querySelector("[data-testid='writeback-approval-state']")!.textContent,
    ).toContain("Approved");
  });

  it("shows explicit 'Not set' for reviewer_notes/required_fix when null (never a blank row)", () => {
    const run = makeRun({
      ...FULL_WRITEBACKS,
      reviewer_notes: null,
      required_fix: null,
    });
    const { container } = renderWorkspace(run);
    const notes = container.querySelector("[data-testid='writeback-reviewer-notes']");
    const fix = container.querySelector("[data-testid='writeback-required-fix']");
    expect(notes!.textContent).toBe("Not set");
    expect(fix!.textContent).toBe("Not set");
  });

  it("shows 'Not set' for approval state when approved_for_writeback is null", () => {
    const run = makeRun({ ...FULL_WRITEBACKS, approved_for_writeback: null });
    const { container } = renderWorkspace(run);
    expect(
      container.querySelector("[data-testid='writeback-approval-state']")!.textContent,
    ).toContain("Not set");
  });
});

// ── Candidate cards ───────────────────────────────────────────────────────────

describe("FR-13 — writeback candidate cards", () => {
  it("renders one candidate card per previews[] entry", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-candidate-meatywiki']")).not.toBeNull();
    expect(container.querySelector("[data-testid='writeback-candidate-ccdash']")).not.toBeNull();
  });

  it("renders .md candidates as formatted Markdown (headings, bold, links)", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const md = container.querySelector("[data-testid='writeback-candidate-markdown-meatywiki']");
    expect(md).not.toBeNull();
    expect(md!.querySelector("h1")).not.toBeNull();
    expect(md!.querySelector("strong")).not.toBeNull();
    expect(md!.querySelector("a")).not.toBeNull();
  });

  it("renders .yaml candidates as a pre-formatted structured block, not raw unwrapped text", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const yamlBlock = container.querySelector("[data-testid='writeback-candidate-yaml-ccdash']");
    expect(yamlBlock).not.toBeNull();
    expect(yamlBlock!.tagName.toLowerCase()).toBe("pre");
    expect(yamlBlock!.textContent).toContain("event: writeback");
  });

  it("shows the no-previews message when targets are present but previews[] is empty", () => {
    const run = makeRun({ ...FULL_WRITEBACKS, previews: [] });
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-candidates']")).toBeNull();
    expect(container.querySelector("[data-testid='writeback-no-previews']")).not.toBeNull();
  });
});

// ── Legacy (pre-1.6) degradation ──────────────────────────────────────────────

describe("FR-13 — pre-1.6-schema legacy degradation", () => {
  it("renders without error when previews/reviewer_notes/required_fix keys are entirely absent", () => {
    // Simulates a pre-1.6 export: targets present, but the new schema-1.6
    // keys are omitted from the object entirely (not just null).
    const legacyWritebacks = { targets: [{ name: "ccdash", status: "present" }] } as RFRunWritebacksSummary;
    const run = makeRun(legacyWritebacks);
    expect(() => renderWorkspace(run)).not.toThrow();
    const { container } = renderWorkspace(run);
    expect(container.querySelector("[data-testid='writeback-governance-panel']")).not.toBeNull();
    expect(container.querySelector("[data-testid='writeback-no-previews']")).not.toBeNull();
    // Absent (not null) reviewer_notes/required_fix still render the "Not set" fallback
    expect(
      container.querySelector("[data-testid='writeback-reviewer-notes']")!.textContent,
    ).toBe("Not set");
  });
});

// ── Read-only invariant ───────────────────────────────────────────────────────

describe("FR-13 — read-only invariant", () => {
  it("the writeback tab content contains no <form> element", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const tabContent = container.querySelector("[data-testid='writeback-tab-content']");
    expect(tabContent).not.toBeNull();
    expect(tabContent!.querySelector("form")).toBeNull();
  });

  it("the writeback tab content contains no <button> element", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const tabContent = container.querySelector("[data-testid='writeback-tab-content']");
    expect(tabContent!.querySelector("button")).toBeNull();
  });

  it("the writeback tab content contains no input/select/textarea elements", () => {
    const run = makeRun(FULL_WRITEBACKS);
    const { container } = renderWorkspace(run);
    const tabContent = container.querySelector("[data-testid='writeback-tab-content']");
    expect(tabContent!.querySelector("input, select, textarea")).toBeNull();
  });
});
