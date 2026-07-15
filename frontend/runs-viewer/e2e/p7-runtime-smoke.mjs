/**
 * P7-004 local runtime evidence runner.
 *
 * Starts no services itself: callers provide the already-running loopback
 * viewer/API endpoints and the deterministic synthetic fixture manifest. This
 * keeps a real browser/API trace reviewable without conflating it with an
 * owner-held private-data approval.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const [manifestPath, evidenceDir] = process.argv.slice(2);
if (!manifestPath || !evidenceDir) {
  throw new Error("usage: node e2e/p7-runtime-smoke.mjs <manifest.json> <evidence-dir>");
}

const fixture = JSON.parse(await readFile(manifestPath, "utf8"));
const aliceBaseUrl = process.env.P7_ALICE_BASE_URL ?? "http://127.0.0.1:5175";
const malloryBaseUrl = process.env.P7_MALLORY_BASE_URL ?? "http://127.0.0.1:5176";
const executablePath = process.env.P7_BROWSER_EXECUTABLE ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
await mkdir(evidenceDir, { recursive: true });

const browser = await chromium.launch({ executablePath, headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const results = [];

async function visible(testId) {
  await page.getByTestId(testId).waitFor({ state: "visible", timeout: 15_000 });
}

async function capture(name, checks) {
  await page.screenshot({ path: `${evidenceDir}/${name}.png`, fullPage: false });
  results.push({ name, viewport: "1440x900", checks });
}

try {
  // CatalogScreen and its full evidence-packet inspector.
  await page.goto(`${aliceBaseUrl}/catalog`, { waitUntil: "networkidle" });
  await page.getByTestId("catalog-tab-assertions").click();
  await visible("assertion-results-table");
  await page.getByTestId(`assertion-row-${fixture.full_assertion}`).click();
  await visible("assertion-packet-inspector");
  await capture("full-catalog", ["CatalogScreen", "full packet", "AssertionPacketInspector"]);

  // Absence is preserved as legacy-missing, never invented as an empty map.
  await page.getByTestId(`assertion-row-${fixture.legacy_assertion}`).click();
  await visible("assertion-packet-inspector");
  await page.getByText("Legacy packet: some fields were not recorded.").waitFor({ state: "visible" });
  await capture("legacy-missing", ["CatalogScreen", "legacy-missing qualifier_extensions"]);

  // RunDetailWorkspace, ClaimAuditWorkbench, and keyboard/focus behavior of
  // the ProvenanceModal.  The modal must focus its close control and restore
  // focus to the opener after Escape.
  await page.goto(`${aliceBaseUrl}/runs/${fixture.full_run}?view=ledger`, { waitUntil: "networkidle" });
  await visible("run-detail");
  await page.getByTestId("detail-tab-ledger").click();
  await visible("claim-audit-workbench");
  const row = page.locator("[data-testid^='ledger-row-']").first();
  await row.click();
  await row.click();
  const opener = page.getByRole("button", { name: "Open modal" });
  await opener.click();
  await visible("provenance-modal");
  const dialog = page.getByTestId("provenance-modal");
  if (await dialog.getAttribute("role") !== "dialog" || await dialog.getAttribute("aria-modal") !== "true") {
    throw new Error("provenance modal lost required dialog semantics");
  }
  const close = page.getByTestId("modal-close");
  if (await close.getAttribute("aria-label") !== "Close provenance modal") {
    throw new Error("provenance modal close control lost its accessible name");
  }
  if (!(await close.evaluate((element) => document.activeElement === element))) {
    throw new Error("provenance modal did not place keyboard focus on its close control");
  }
  await capture("provenance-focus", ["ClaimAuditWorkbench", "ProvenanceModal", "role=dialog aria-modal=true", "named close control", "dialog initial focus"]);
  await page.keyboard.press("Escape");
  await page.getByTestId("provenance-modal").waitFor({ state: "hidden" });
  if (!(await opener.evaluate((element) => document.activeElement === element))) {
    throw new Error("provenance modal did not restore focus to its opener after Escape");
  }
  results.push({ name: "provenance-keyboard", checks: ["Escape closes dialog", "focus restored to Open modal"] });

  // Stale packets remain historically readable in the audit surface.
  await page.goto(`${aliceBaseUrl}/runs/${fixture.stale_run}?view=ledger`, { waitUntil: "networkidle" });
  await page.getByTestId("detail-tab-ledger").click();
  await visible("claim-audit-workbench");
  await page.getByText("Stale").first().waitFor({ state: "visible" });
  await capture("stale-audit", ["RunDetailWorkspace", "ClaimAuditWorkbench", "stale packet"]);

  // Assertion-only lineage remains explicit while canonical merge is off.
  // The selected claim is the durable assertion context on the page route.
  // Make it explicit in the route so this remains a deterministic browser
  // check rather than depending on retained component state between tabs.
  await page.goto(`${aliceBaseUrl}/runs/${fixture.stale_run}?view=lineage&claim=clm_001`, { waitUntil: "networkidle" });
  await visible("assertion-only-lineage");
  await visible("assertion-only-notice");
  await capture("assertion-only-lineage", ["RunDetailWorkspace", "LineageDetailPanel path", "assertion-only mode"]);

  // A distinct workspace token produces a denied catalog with no result rows.
  await page.goto(`${malloryBaseUrl}/catalog`, { waitUntil: "networkidle" });
  await page.getByTestId("catalog-tab-assertions").click();
  await visible("assertion-denied-panel");
  if (await page.locator("[data-testid^='assertion-row-']").count()) {
    throw new Error("denied assertion catalog rendered candidate rows");
  }
  await capture("denied-catalog", ["CatalogScreen", "denied state", "zero candidate rows"]);
} finally {
  await browser.close();
}

await writeFile(`${evidenceDir}/runtime-results.json`, JSON.stringify({
  fixture,
  browser: "system Google Chrome via Playwright",
  owner_private_status: "not_executed",
  results,
}, null, 2) + "\n");
