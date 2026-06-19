import { expect, test } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

test.describe("Runs frontend facelift v2", () => {
  test("portfolio command center renders metrics, lanes, table, and inspector", async ({ page }) => {
    await page.goto("/runs");

    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Portfolio Command Center")).toBeVisible();
    await expect(page.getByText("Total Runs")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Attention Queue" })).toBeVisible();
    await expect(page.getByTestId("portfolio-run-table")).toBeVisible();
    await expect(page.getByTestId("selected-run-inspector")).toBeVisible();

    const firstSelect = page.locator(".rv-table-link").first();
    await firstSelect.click();
    await expect(firstSelect).toHaveAttribute("aria-pressed", "true");
  });

  test("detail view honors query-state audit workspace and selected claim", async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}?view=audit&claim=clm_043`);

    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    await expect(page.getByTestId("tabpanel-ledger")).toBeVisible();
    await expect(page.getByTestId("claim-audit-workbench")).toBeVisible();
    await expect(page.getByTestId("claim-inspector")).toHaveAttribute("data-claim-id", "clm_043");
    await expect(page.locator("[data-testid='ledger-row-clm_043']")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("report-renderer")).not.toContainText("schema_version:");
  });

  test("report chip selection synchronizes the audit workbench inspector", async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}?view=audit`);

    await expect(page.getByTestId("claim-audit-workbench")).toBeVisible({ timeout: 10_000 });
    const chip = page.locator("button[data-testid^='claim-chip-']").first();
    await expect(chip).toBeVisible();
    const claimId = await chip.getAttribute("data-claim-id");
    expect(claimId).toBeTruthy();

    await chip.click();
    await expect(page.getByTestId("claim-inspector")).toHaveAttribute("data-claim-id", claimId!);
    await expect(chip).toHaveAttribute("data-selected", "true");
    await expect(page).toHaveURL(new RegExp(`view=audit.*claim=${claimId}`));
  });

  test("ledger row selection updates copied URL state", async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}?view=audit`);

    await expect(page.getByTestId("claim-audit-workbench")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("ledger-row-clm_043").click();
    await expect(page.getByTestId("claim-inspector")).toHaveAttribute("data-claim-id", "clm_043");
    await expect(page).toHaveURL(/view=audit.*claim=clm_043/);
  });

  test("absent writeback context renders graceful states", async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}?view=trust`);

    await expect(page.getByTestId("context-panel-routing")).toContainText("Routing context is absent");
    await expect(page.getByTestId("context-panel-writeback")).toContainText("Not exported");

    await page.getByTestId("detail-tab-writeback").click();
    await expect(page.getByTestId("tabpanel-writeback")).toContainText("Writeback preview is not exported");
  });
});
