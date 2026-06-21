/**
 * G2-policies tests — PoliciesScreen component tests + isActiveNav coverage for Policies.
 *
 * Covers:
 *   SMOKE-G2-01: Policies nav item is enabled (state="enabled", not disabled)
 *   SMOKE-G2-02: Policies nav item has aria-current="page" at /policies
 *   SMOKE-G2-03: Policies nav item does NOT have aria-current="page" elsewhere
 *   SMOKE-G2-04: PoliciesScreen renders without crash (empty state)
 *   SMOKE-G2-05: PoliciesScreen renders without crash when governance config absent
 *   TEST-G2-01: Global Governance Panel shows "No governance config found" when config is empty
 *   TEST-G2-02: Global Governance Panel renders key_profiles and policy_rules when present
 *   TEST-G2-03: Per-Run Governance Table renders "No runs found" when index is empty
 *   TEST-G2-04: Per-Run Governance Table renders run rows with governance columns
 *   TEST-G2-05: Per-Run Governance Table shows "—" when governance block is absent
 *   TEST-G2-06: isActiveNav returns false for Policies at /runs
 *   TEST-G2-07: enabling Policies does not break Alerts active state at /alerts
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PoliciesScreen, governanceConfigQueryKey } from "@/screens/PoliciesScreen";
import { AppShell } from "@/app/AppShell";
import { runListQueryKey } from "@/hooks";
import type { RFRunExport, RFRunSummary } from "@/types/rf";
import type { GovernanceConfig } from "@/types/governance";

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

function makeRunExport(runId: string, governance: RFRunExport["governance"] = null): RFRunExport {
  return {
    schema_version: "1.1",
    run_id: runId,
    status_derived: "verified",
    claims: [],
    claim_counts: null,
    verification: null,
    governance,
    timeline: null,
  };
}

const MOCK_GOVERNANCE_CONFIG: GovernanceConfig = {
  key_profiles: {
    standard: { allowed_sensitivity: ["public", "internal"], writeback_enabled: true },
    restricted: { allowed_sensitivity: ["public"], writeback_enabled: false },
  },
  policy_rules: [
    { id: "GOV-001", severity: "error", description: "Sensitivity threshold must be met." },
    { id: "GOV-002", severity: "warning", description: "Human review recommended for restricted runs." },
  ],
};

// ── Test helpers ───────────────────────────────────────────────────────────────

function makePoliciesQC(opts: {
  govConfig?: GovernanceConfig;
  summaries?: RFRunSummary[];
  runExports?: RFRunExport[];
}): QueryClient {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });

  // Pre-seed governance config
  qc.setQueryData(governanceConfigQueryKey, opts.govConfig ?? {});

  // Pre-seed run list
  qc.setQueryData(runListQueryKey, opts.summaries ?? []);

  // Pre-seed per-run detail entries
  for (const run of opts.runExports ?? []) {
    qc.setQueryData(["rf", "runs", "detail", run.run_id], run);
  }

  return qc;
}

function renderPolicies(qc: QueryClient) {
  return render(
    <MemoryRouter initialEntries={["/policies"]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route path="/policies" element={<PoliciesScreen />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

// ── SMOKE-G2-01 / SMOKE-G2-02 / SMOKE-G2-03: Nav item ───────────────────────

describe("isActiveNav — Policies nav item (AC-1, SMOKE-G2-01..03)", () => {
  it("Policies nav button has data-state='enabled', not 'disabled'", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const policiesBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    );
    expect(policiesBtn).not.toBeUndefined();
    expect(policiesBtn!.getAttribute("data-state")).toBe("enabled");
  });

  it("Policies nav button is NOT disabled (HTML disabled=false)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const policiesBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    ) as HTMLButtonElement | undefined;
    expect(policiesBtn).not.toBeUndefined();
    expect(policiesBtn!.disabled).toBe(false);
  });

  it("Policies nav button has aria-current='page' at /policies", () => {
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
  });

  it("Policies nav button does NOT have aria-current='page' at /runs (TEST-G2-06)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const policiesBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    );
    expect(policiesBtn!.getAttribute("aria-current")).toBeNull();
  });

  it("enabling Policies does not break Alerts active state at /alerts (TEST-G2-07)", () => {
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
    const policiesBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Policies",
    );
    expect(policiesBtn!.getAttribute("aria-current")).toBeNull();
  });
});

// ── SMOKE-G2-04 / TEST-G2-01: Empty state with no governance config ───────────

describe("PoliciesScreen — empty state (AC-2, SMOKE-G2-04..05, TEST-G2-01)", () => {
  it("renders without crash when governance config is empty (SMOKE-G2-04)", () => {
    const qc = makePoliciesQC({ govConfig: {} });
    expect(() => renderPolicies(qc)).not.toThrow();
  });

  it("renders the policies screen container", () => {
    const qc = makePoliciesQC({ govConfig: {} });
    const { container } = renderPolicies(qc);
    expect(container.querySelector("[data-testid='policies-screen']")).not.toBeNull();
  });

  it("renders 'No governance config found' when config is empty (TEST-G2-01)", () => {
    const qc = makePoliciesQC({ govConfig: {} });
    const { container } = renderPolicies(qc);
    const emptyPanel = container.querySelector("[data-testid='policies-gov-panel-empty']");
    expect(emptyPanel).not.toBeNull();
    expect(emptyPanel!.textContent).toContain("No governance config found");
  });

  it("renders 'No governance config found' when config has null fields (SMOKE-G2-05)", () => {
    const qc = makePoliciesQC({ govConfig: { key_profiles: null, policy_rules: null } });
    const { container } = renderPolicies(qc);
    const emptyPanel = container.querySelector("[data-testid='policies-gov-panel-empty']");
    expect(emptyPanel).not.toBeNull();
    expect(emptyPanel!.textContent).toContain("No governance config found");
  });

  it("renders 'No runs found' when index is empty (TEST-G2-03)", () => {
    const qc = makePoliciesQC({ govConfig: {}, summaries: [] });
    const { container } = renderPolicies(qc);
    const empty = container.querySelector("[data-testid='policies-runs-empty']");
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain("No runs found");
  });
});

// ── TEST-G2-02: Global Governance Panel with data ─────────────────────────────

describe("PoliciesScreen — Global Governance Panel with data (AC-2, TEST-G2-02)", () => {
  it("renders the governance panel when config is present", () => {
    const qc = makePoliciesQC({ govConfig: MOCK_GOVERNANCE_CONFIG });
    const { container } = renderPolicies(qc);
    expect(container.querySelector("[data-testid='policies-gov-panel']")).not.toBeNull();
  });

  it("renders key_profiles subsection", () => {
    const qc = makePoliciesQC({ govConfig: MOCK_GOVERNANCE_CONFIG });
    const { container } = renderPolicies(qc);
    expect(container.querySelector("[data-testid='policies-key-profiles']")).not.toBeNull();
  });

  it("renders policy_rules subsection", () => {
    const qc = makePoliciesQC({ govConfig: MOCK_GOVERNANCE_CONFIG });
    const { container } = renderPolicies(qc);
    expect(container.querySelector("[data-testid='policies-policy-rules']")).not.toBeNull();
  });

  it("renders policy rule IDs in the rules table", () => {
    const qc = makePoliciesQC({ govConfig: MOCK_GOVERNANCE_CONFIG });
    const { container } = renderPolicies(qc);
    const rulesSection = container.querySelector("[data-testid='policies-policy-rules']");
    expect(rulesSection!.textContent).toContain("GOV-001");
    expect(rulesSection!.textContent).toContain("GOV-002");
  });

  it("renders profile names in the key profiles table", () => {
    const qc = makePoliciesQC({ govConfig: MOCK_GOVERNANCE_CONFIG });
    const { container } = renderPolicies(qc);
    const profileSection = container.querySelector("[data-testid='policies-key-profiles']");
    expect(profileSection!.textContent).toContain("standard");
    expect(profileSection!.textContent).toContain("restricted");
  });
});

// ── TEST-G2-04 / TEST-G2-05: Per-Run Governance Table ────────────────────────

describe("PoliciesScreen — Per-Run Governance Table (AC-3, AC-4, TEST-G2-04, TEST-G2-05)", () => {
  it("renders run rows when summaries are present (TEST-G2-04)", () => {
    const run = makeRunExport("rf_run_test_001", {
      sensitivity: "public",
      approved_for_writeback: true,
      allowed_writebacks: ["meatywiki", "ccdash"],
      requires_human_review: false,
    });
    const summary = makeRunSummary("rf_run_test_001");
    const qc = makePoliciesQC({
      govConfig: MOCK_GOVERNANCE_CONFIG,
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const rows = container.querySelectorAll("[data-testid='policies-run-row']");
    expect(rows.length).toBe(1);
  });

  it("renders sensitivity column for run row", () => {
    const run = makeRunExport("rf_run_test_002", {
      sensitivity: "work_sensitive",
      approved_for_writeback: false,
    });
    const summary = makeRunSummary("rf_run_test_002");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const sensitivityCells = container.querySelectorAll("[data-testid='policies-cell-sensitivity']");
    expect(sensitivityCells.length).toBe(1);
    expect(sensitivityCells[0].textContent).toBe("work_sensitive");
  });

  it("renders approved_for_writeback as 'Yes' when true", () => {
    const run = makeRunExport("rf_run_test_003", {
      approved_for_writeback: true,
    });
    const summary = makeRunSummary("rf_run_test_003");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const approvedCells = container.querySelectorAll("[data-testid='policies-cell-approved']");
    expect(approvedCells[0].textContent).toBe("Yes");
  });

  it("renders allowed_writebacks as comma list when present", () => {
    const run = makeRunExport("rf_run_test_004", {
      allowed_writebacks: ["meatywiki", "ccdash"],
    });
    const summary = makeRunSummary("rf_run_test_004");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const wbCells = container.querySelectorAll("[data-testid='policies-cell-writebacks']");
    expect(wbCells[0].textContent).toBe("meatywiki, ccdash");
  });

  it("renders 'No' for requires_human_review when false", () => {
    const run = makeRunExport("rf_run_test_005", {
      requires_human_review: false,
    });
    const summary = makeRunSummary("rf_run_test_005");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const hrCells = container.querySelectorAll("[data-testid='policies-cell-human-review']");
    expect(hrCells[0].textContent).toBe("No");
  });

  it("renders '—' for all governance columns when governance block is null (TEST-G2-05, AC-3)", () => {
    const run = makeRunExport("rf_run_test_006", null);
    const summary = makeRunSummary("rf_run_test_006");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const sensitivityCells = container.querySelectorAll("[data-testid='policies-cell-sensitivity']");
    const approvedCells = container.querySelectorAll("[data-testid='policies-cell-approved']");
    const wbCells = container.querySelectorAll("[data-testid='policies-cell-writebacks']");
    const hrCells = container.querySelectorAll("[data-testid='policies-cell-human-review']");
    expect(sensitivityCells[0].textContent).toBe("—");
    expect(approvedCells[0].textContent).toBe("—");
    expect(wbCells[0].textContent).toBe("—");
    expect(hrCells[0].textContent).toBe("—");
  });

  it("renders run ID as a link to /runs/:runId", () => {
    const run = makeRunExport("rf_run_test_007", null);
    const summary = makeRunSummary("rf_run_test_007");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    const { container } = renderPolicies(qc);
    const link = container.querySelector("[data-testid='policies-run-link']") as HTMLAnchorElement | null;
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toContain("rf_run_test_007");
  });

  it("does not throw when governance block is absent (no crash, AC-3)", () => {
    const run = makeRunExport("rf_run_test_008", null);
    const summary = makeRunSummary("rf_run_test_008");
    const qc = makePoliciesQC({
      govConfig: {},
      summaries: [summary],
      runExports: [run],
    });
    expect(() => renderPolicies(qc)).not.toThrow();
  });
});

// ── Regression guard: existing nav items not broken ───────────────────────────

describe("Policies nav — no regression on existing nav items", () => {
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

  it("Settings is still active at /settings", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const settingsBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Settings",
    );
    expect(settingsBtn!.getAttribute("aria-current")).toBe("page");
  });

  it("Swarm is still contextual (not disabled or enabled) at /runs/run_abc/swarm", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/runs/run_abc/swarm"]}>
        <AppShell />
      </MemoryRouter>,
    );
    const navButtons = container.querySelectorAll(".rv-shell-nav__item");
    const swarmBtn = Array.from(navButtons).find(
      (btn) => btn.querySelector("strong")?.textContent === "Swarm",
    );
    expect(swarmBtn!.getAttribute("data-state")).toBe("contextual");
  });
});
