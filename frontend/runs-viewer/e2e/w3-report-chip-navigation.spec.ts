/**
 * P5-E2E-W3: Report chip navigation smoke test.
 *
 * Navigates to run detail → Report tab, asserts:
 *   1. At least one [claim:clm_NNN] chip is rendered in the report.
 *   2. Clicking a chip opens ProvenanceModal with claim data.
 *   3. ProvenanceModal has the expected claim ID in its data attribute.
 *
 * Runs on static fixture: rf_run_20260613_what_is_the_current_release_state
 */

import { test, expect } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

test.describe("P5-E2E-W3: W3 report chip navigation to ProvenanceModal", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });

    // Switch to Report tab
    await page.getByTestId("detail-tab-report").click();
    await expect(page.getByTestId("tabpanel-report")).toBeVisible();
  });

  test("at least one claim chip renders in the report overlay", async ({ page }) => {
    // ClaimChips have data-testid="claim-chip-<claimId>"
    const chips = page.locator("[data-testid^='claim-chip-']");
    const count = await chips.count();
    expect(count).toBeGreaterThan(0);
  });

  test("clicking a claim chip opens ProvenanceModal", async ({ page }) => {
    // Get the first visible, clickable chip (buttons — not span.rv-claim-chip--missing)
    const chip = page.locator("button[data-testid^='claim-chip-']").first();
    await expect(chip).toBeVisible();

    const claimId = await chip.getAttribute("data-claim-id");
    expect(claimId).toBeTruthy();

    await chip.click();

    // ProvenanceModal overlay and dialog must appear
    await expect(page.getByTestId("provenance-modal-overlay")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("provenance-modal")).toBeVisible();
  });

  test("ProvenanceModal shows claim data after chip click", async ({ page }) => {
    const chip = page.locator("button[data-testid^='claim-chip-']").first();
    const claimId = await chip.getAttribute("data-claim-id");

    await chip.click();

    const modal = page.getByTestId("provenance-modal");
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Modal must show the correct claim-id in its data attribute
    const modalClaimId = await modal.getAttribute("data-claim-id");
    expect(modalClaimId).toBe(claimId);

    // Modal body should be present (not "claim not found")
    await expect(page.getByTestId("modal-body")).toBeVisible();
  });

  test("ProvenanceModal can be closed", async ({ page }) => {
    const chip = page.locator("button[data-testid^='claim-chip-']").first();
    await chip.click();
    await expect(page.getByTestId("provenance-modal")).toBeVisible({ timeout: 5_000 });

    // Close via close button
    await page.getByTestId("modal-close").click();
    await expect(page.getByTestId("provenance-modal-overlay")).not.toBeVisible({ timeout: 3_000 });
  });
});
