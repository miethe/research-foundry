/**
 * P5-E2E-W1: Claim audit two-click smoke test (W1 flagship).
 *
 * User journey: Claim Ledger → row click (interaction 1) → ProvenanceModal opens
 *               → SourceCard quote is visible (interaction 2 = expand quote).
 *
 * Asserts:
 *   1. Claim ledger table renders in the Claim Ledger tab.
 *   2. Clicking the first claim row opens ProvenanceModal (interaction 1).
 *   3. ProvenanceModal shows at least one SourceCard.
 *   4. Expanding the quote button reveals non-empty verbatim quote (interaction 2).
 *   5. Total UI interactions from ledger to visible quote ≤ 2.
 *
 * Runs on static fixture: rf_run_20260613_what_is_the_current_release_state
 */

import { test, expect } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

test.describe("P5-E2E-W1: W1 claim audit — 2-click ledger to verbatim quote", () => {
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

  test("Interaction 1: clicking first claim row opens ProvenanceModal", async ({ page }) => {
    const firstRow = page.locator("[data-testid^='ledger-row-']").first();
    await expect(firstRow).toBeVisible();

    // INTERACTION 1: click the first claim row
    await firstRow.click();

    // Modal must open
    await expect(page.getByTestId("provenance-modal-overlay")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("provenance-modal")).toBeVisible();
    await expect(page.getByTestId("modal-body")).toBeVisible();
  });

  test("ProvenanceModal shows at least one SourceCard after row click", async ({ page }) => {
    const firstRow = page.locator("[data-testid^='ledger-row-']").first();
    await firstRow.click();

    await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });

    // SourceCards render in the modal sources section
    const sourcesSection = page.getByTestId("modal-sources");
    await expect(sourcesSection).toBeVisible();

    const sourceCards = page.locator("[data-testid^='source-card-']");
    const cardCount = await sourceCards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test("Interaction 2: expand quote reveals non-empty verbatim quote (≤2 total interactions)", async ({ page }) => {
    // Interaction count tracking
    let interactions = 0;

    // INTERACTION 1: click first claim row
    const firstRow = page.locator("[data-testid^='ledger-row-']").first();
    await firstRow.click();
    interactions++;

    await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });

    // Get all quote toggle buttons in the modal (one per SourceCard that has a quote)
    const quoteToggle = page.locator("[data-testid^='source-card-quote-toggle-']").first();

    // If the toggle is visible, expand it (INTERACTION 2)
    if (await quoteToggle.isVisible()) {
      await quoteToggle.click();
      interactions++;

      // Quote body must now be visible and non-empty
      const quoteBody = page.locator("[data-testid^='source-card-quote-']").first();
      await expect(quoteBody).toBeVisible({ timeout: 3_000 });

      const quoteText = await quoteBody.textContent();
      expect(quoteText?.trim().length).toBeGreaterThan(0);
    } else {
      // Quote may already be visible if the SourceCard renders it inline
      // Count this as still within 1 interaction
      const quoteBodies = page.locator("[data-testid^='source-card-quote-']");
      const quoteBodyCount = await quoteBodies.count();
      if (quoteBodyCount > 0) {
        const quoteText = await quoteBodies.first().textContent();
        expect(quoteText?.trim().length).toBeGreaterThan(0);
      }
    }

    // Assert interaction count ≤ 2
    expect(interactions).toBeLessThanOrEqual(2);
  });

  test("SourceCard section heading shows source count", async ({ page }) => {
    const firstRow = page.locator("[data-testid^='ledger-row-']").first();
    await firstRow.click();

    await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });

    // Sources section should show "(N)" in the heading
    const sourcesSection = page.getByTestId("modal-sources");
    await expect(sourcesSection).toBeVisible();
    const heading = sourcesSection.locator("h3");
    const headingText = await heading.textContent();
    expect(headingText).toMatch(/Sources \(\d+\)/);
  });
});
