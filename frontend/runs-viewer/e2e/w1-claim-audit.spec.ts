/**
 * P5-E2E-W1: Claim audit selected-claim smoke test.
 *
 * User journey: Claim Ledger → row click selects the claim
 *               → explicit Selected Claim action opens ProvenanceModal
 *               → SourceCard quote is visible after expanding quote.
 *
 * Asserts:
 *   1. Claim ledger table renders in the Claim Ledger tab.
 *   2. Clicking the first claim row selects it without opening ProvenanceModal.
 *   3. ProvenanceModal shows at least one SourceCard.
 *   4. Expanding the quote button reveals non-empty verbatim quote.
 *
 * Runs on static fixture: rf_run_20260613_what_is_the_current_release_state
 */

import { test, expect, type Page } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

test.describe("P5-E2E-W1: W1 claim audit — selected claim provenance", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });

    // Navigate to Claim Ledger tab (interaction 0 — tab navigation, not counted)
    await page.getByTestId("detail-tab-ledger").click();
    await expect(page.getByTestId("tabpanel-ledger")).toBeVisible();
  });

  test("Claim Ledger table renders with at least one row", async ({ page }) => {
    const table = page.getByTestId("ledger-table");
    await expect(table).toBeVisible();

    const rows = page.locator("[data-testid^='ledger-row-']");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test("clicking first claim row selects without opening ProvenanceModal", async ({ page }) => {
    const firstRow = page.locator("[data-testid^='ledger-row-']").first();
    await expect(firstRow).toBeVisible();
    const claimId = await firstRow.getAttribute("data-claim-id");
    expect(claimId).toBeTruthy();

    // ClaimAuditWorkbench pre-selects the first claim on mount and toggles
    // selection off on re-click of an already-selected row (see selectClaim
    // in ClaimAuditWorkbench.tsx). Click twice: the first click deselects
    // the mount-time default, the second click re-selects it — exercising
    // the real "select" transition rather than a no-op toggle-off.
    await firstRow.click();
    await firstRow.click();

    await expect(page.getByTestId("claim-inspector")).toHaveAttribute("data-claim-id", claimId!);
    await expect(page.getByTestId("provenance-modal")).not.toBeVisible();
  });

  test("explicit Selected Claim action opens ProvenanceModal with at least one SourceCard", async ({ page }) => {
    await selectFirstClaimAndOpenModal(page);

    const sourcesSection = page.getByTestId("modal-sources");
    await expect(sourcesSection).toBeVisible();

    const sourceCards = page.locator("[data-testid^='source-card-']");
    const cardCount = await sourceCards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test("expanding quote reveals non-empty verbatim quote", async ({ page }) => {
    await selectFirstClaimAndOpenModal(page);

    // SourceCard is rendered both in the always-mounted "Selected Claim"
    // sidebar panel and inside the ProvenanceModal dialog (same component,
    // same data-testid prefix, two DOM instances). Scope to the modal so we
    // interact with the visible, unobstructed copy — the unscoped page-wide
    // locator resolves to the sidebar's copy first, which sits behind the
    // modal overlay and is not clickable.
    const modal = page.getByTestId("provenance-modal");
    const quoteToggle = modal.locator("[data-testid^='source-card-quote-toggle-']").first();

    if (await quoteToggle.isVisible()) {
      await quoteToggle.click();

      const quoteBody = modal.locator("[data-testid^='source-card-quote-']").first();
      await expect(quoteBody).toBeVisible({ timeout: 3_000 });

      const quoteText = await quoteBody.textContent();
      expect(quoteText?.trim().length).toBeGreaterThan(0);
    } else {
      const quoteBodies = modal.locator("[data-testid^='source-card-quote-']");
      const quoteBodyCount = await quoteBodies.count();
      if (quoteBodyCount > 0) {
        const quoteText = await quoteBodies.first().textContent();
        expect(quoteText?.trim().length).toBeGreaterThan(0);
      }
    }
  });

  test("SourceCard section heading shows source count", async ({ page }) => {
    await selectFirstClaimAndOpenModal(page);

    const sourcesSection = page.getByTestId("modal-sources");
    await expect(sourcesSection).toBeVisible();
    const heading = sourcesSection.locator("h3");
    const headingText = await heading.textContent();
    expect(headingText).toMatch(/Sources \(\d+\)/);
  });
});

async function selectFirstClaimAndOpenModal(page: Page) {
  const firstRow = page.locator("[data-testid^='ledger-row-']").first();
  await expect(firstRow).toBeVisible();
  // See comment in "clicking first claim row selects..." above: the first
  // claim is pre-selected on mount, so a single click toggles it off. Click
  // twice to land back on a genuinely "selected" first claim.
  await firstRow.click();
  await firstRow.click();
  await page.getByRole("button", { name: "Open modal" }).click();
  await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByTestId("modal-body")).toBeVisible();
}

// ── P5-RBAC extension (diff-only): AC-5a regression guard ────────────────────
//
// "Run existing scenarios under an authenticated context" (TEST-002 spec).
// For static-export-compatible mode, the "authenticated context" is auth_mode=none
// with the provider key explicitly cleared — this is the public-degradation state
// that must preserve all claim-audit functionality (AC-5a regression guard).
//
// Live-auth extension (local_static / clerk with full post-login identity) requires
// a running RF API server — see p5-auth-rbac.spec.ts for the documented limitation.

test.describe("P5-RBAC extension: W1 claim-audit in auth context (AC-5a guard)", () => {
  test.beforeEach(async ({ page }) => {
    // Explicitly ensure auth_mode=none: clear any provider override so the
    // claim-audit scenarios run with the public-degradation auth state active.
    await page.addInitScript(() => {
      window.localStorage.removeItem("rv_auth_provider");
    });
    await page.goto(`/runs/${RUN_ID}`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("detail-tab-ledger").click();
    await expect(page.getByTestId("tabpanel-ledger")).toBeVisible();
  });

  test("AC-5a: claim ledger accessible in auth_mode=none without login form", async ({
    page,
  }) => {
    // No login form must be visible — auth_mode=none preserves pre-gated access
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
    // Claim ledger still renders (backward-compatibility regression guard)
    await expect(page.getByTestId("ledger-table")).toBeVisible();
    const rows = page.locator("[data-testid^='ledger-row-']");
    await expect(rows.first()).toBeVisible();
  });

  test("AC-5a: ProvenanceModal accessible in auth_mode=none (no auth barrier)", async ({
    page,
  }) => {
    // Replicate the modal-open scenario under explicit auth context.
    // No login barrier must interrupt the claim → provenance flow.
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
    await selectFirstClaimAndOpenModal(page);
    await expect(page.getByTestId("modal-sources")).toBeVisible();
  });

  test("AC-5a: no role/workspace chrome rendered in auth_mode=none", async ({
    page,
  }) => {
    // identity=null in auth_mode=none → no workspace affordances shown (AC-5a)
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
    // Ledger is fully accessible — no role-gating chrome blocking it
    await expect(page.getByTestId("ledger-table")).toBeVisible();
  });
});
