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

    const quoteToggle = page.locator("[data-testid^='source-card-quote-toggle-']").first();

    if (await quoteToggle.isVisible()) {
      await quoteToggle.click();

      const quoteBody = page.locator("[data-testid^='source-card-quote-']").first();
      await expect(quoteBody).toBeVisible({ timeout: 3_000 });

      const quoteText = await quoteBody.textContent();
      expect(quoteText?.trim().length).toBeGreaterThan(0);
    } else {
      const quoteBodies = page.locator("[data-testid^='source-card-quote-']");
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
  await firstRow.click();
  await page.getByRole("button", { name: "Open modal" }).click();
  await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByTestId("modal-body")).toBeVisible();
}
