import { expect, test } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

test.describe("Runs frontend facelift v2.1", () => {
  test("portfolio command center renders honest shell, metrics, lanes, table, and run modal", async ({ page }) => {
    await page.goto("/runs");

    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reports" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Ledger" })).toBeEnabled();
    await expect(page.getByRole("button", { name: /Library: Library route is not implemented/i })).toBeDisabled();
    await expect(page.getByText("Portfolio Command Center")).toBeVisible();
    await expect(page.getByText("Total Runs")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Attention Queue" })).toBeVisible();
    await expect(page.getByTestId("portfolio-run-table")).toBeVisible();

    const firstSelect = page.locator(".rv-table-link").first();
    await firstSelect.click();
    await expect(firstSelect).toHaveAttribute("aria-pressed", "true");

    await page.locator(".rv-table-open").first().click();
    await expect(page.getByTestId("run-detail-modal")).toBeVisible();
    await expect(page.getByTestId("run-modal-summary")).toBeVisible();
  });

  test("shell report and ledger targets use the selected portfolio run", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });

    const firstSelect = page.locator(".rv-table-link").first();
    const runId = (await firstSelect.textContent())?.trim();
    expect(runId).toBeTruthy();
    await firstSelect.click();

    await page.getByRole("button", { name: "Reports" }).click();
    await expect(page).toHaveURL(new RegExp(`/runs/${encodeURIComponent(runId!)}\\?view=report`));

    await page.goto("/runs");
    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });
    await firstSelect.click();
    await page.getByRole("button", { name: "Ledger" }).click();
    await expect(page).toHaveURL(new RegExp(`/runs/${encodeURIComponent(runId!)}\\?view=audit`));
  });

  test("report tab inside run modal opens stacked claim modal and closes in order", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });

    await page.locator(".rv-table-open").first().click();
    const runModal = page.getByTestId("run-detail-modal");
    await expect(runModal).toBeVisible();

    await runModal.getByTestId("detail-tab-report").click();
    await expect(runModal.getByTestId("tabpanel-report")).toBeVisible();

    await runModal.locator("button[data-testid^='claim-chip-']").first().click();
    await expect(page.getByTestId("provenance-modal")).toBeVisible();
    await expect(runModal).toBeVisible();
    await expect(runModal.getByTestId("run-modal-open-full-page")).toHaveAttribute("href", /claim=clm_/);

    await page.keyboard.press("Escape");
    await expect(page.getByTestId("provenance-modal")).not.toBeVisible();
    await expect(runModal).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(runModal).not.toBeVisible();
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
    await expect(page.getByTestId("provenance-modal")).not.toBeVisible();
    await expect(page).toHaveURL(/view=audit.*claim=clm_043/);
  });

  test("absent writeback context disables unavailable writeback tab", async ({ page }) => {
    await page.goto(`/runs/${RUN_ID}?view=trust`);

    await expect(page.getByTestId("context-panel-routing")).toContainText("Routing context is absent");
    await expect(page.getByTestId("context-panel-writeback")).toContainText("Not exported");

    await expect(page.getByTestId("detail-tab-writeback")).toBeDisabled();
    await expect(page.getByTestId("detail-tab-writeback")).toHaveAttribute("aria-disabled", "true");
  });
});
