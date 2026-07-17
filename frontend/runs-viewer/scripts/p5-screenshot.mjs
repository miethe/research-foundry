/**
 * scripts/p5-screenshot.mjs — ad hoc P5-02 visual-evidence capture.
 *
 * Navigates the running `vite preview` server to a run's Audit tab and
 * captures a desktop (>=1440px) screenshot for the canonical-claims
 * merge-review AC-6 evidence (assertion-ledger-activation-v1). Not part of
 * the CI test suite — invoked manually against a locally built preview
 * server pointed at the flag-on / flag-off builds in turn.
 */
import { chromium } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";
const BASE = process.env.RF_PREVIEW_BASE ?? "http://localhost:5183";
const OUT = process.env.RF_SCREENSHOT_OUT ?? "/tmp/p5-canonical-claims-on.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

page.on("pageerror", (err) => console.log("[pageerror]", err.message));

await page.goto(`${BASE}/runs/${RUN_ID}`, { waitUntil: "networkidle" });
await page.click('[data-testid="detail-tab-ledger"]');
await page.waitForSelector('[data-testid="claim-audit-workbench"]');
// Default selection is claims[0] (clm_001), which carries the synthetic
// canonical_claim_id fixture (public/data is gitignored, patched locally).
await page.waitForSelector('[data-testid="claim-inspector"][data-claim-id="clm_001"]');

const sectionCount = await page.locator('[data-testid="canonical-claim-section"]').count();
const chipCount = await page.locator('[data-testid="canonical-claim-chip"]').count();
console.log("canonical-claim-section count:", sectionCount);
console.log("canonical-claim-chip count:", chipCount);

if (sectionCount > 0) {
  await page.locator('[data-testid="canonical-claim-section"]').scrollIntoViewIfNeeded();
}
await page.waitForTimeout(150);
await page.screenshot({ path: OUT, fullPage: false });
console.log("Saved screenshot to", OUT);

await browser.close();
