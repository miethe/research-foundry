/**
 * P5-RBAC: Auth/RBAC E2E suite — static + live modes (TEST-002).
 *
 * Covers:
 *   1. provider=none (default / static-export): read-only public degradation,
 *      no login form, no role-gating (AC-5a regression guard).
 *   2. provider=local_static: login form gates all content; UI shape verified.
 *      Full login flow requires RF API server (documented limitation).
 *   3. provider=clerk: ClerkShell lazy-loaded; UI shape verified.
 *      Full Clerk flow requires live Clerk tenant (documented limitation).
 *   4. Role-bounded assertions:
 *      - auth_mode=none: Catalog/Builder accessible, Settings accessible (no role gate AC-5a)
 *      - local_static pre-login: all content blocked (login form = role-denied state)
 *      - post-login RBAC (viewer/admin): documented as live-mode limitation
 *   5. Sharing scenario: fail-closed on sensitivity (AC-2)
 *   6. Screenshots for AC-5 provider states saved to .claude/evidence/phase-9/
 *
 * LIVE MODE LIMITATION:
 * Full login → role-bounded → sharing flow for local_static and Clerk providers
 * requires a running RF API server (VITE_RUNS_LOOPBACK_API_TOKEN set + backend).
 * This Playwright environment has no backend; those scenarios are documented here
 * but marked .skip to prevent false-green silence. Run them in a live dev
 * environment with: VITE_AUTH_PROVIDER=local_static pnpm run dev (+ rf serve).
 *
 * Static mode ALWAYS runs — it exercises the public-degradation guarantee that
 * must hold regardless of provider configuration (AC-5, AC-5a, AC-5c).
 *
 * Runs on static fixture: rf_run_20260613_what_is_the_current_release_state
 */

import * as path from "path";
import * as fs from "fs";
import { test, expect } from "@playwright/test";

const RUN_ID = "rf_run_20260613_what_is_the_current_release_state";

/**
 * Evidence dir for AC-5 runtime-smoke screenshots (R-P4 gate).
 * Convention: .claude/evidence/phase-9/auth-context-<provider>.png
 * Path: process.cwd() is the Playwright project root (frontend/runs-viewer/).
 * Going 2 levels up reaches the worktree root; then .claude/evidence/phase-9/.
 */
const EVIDENCE_DIR = path.resolve(process.cwd(), "../../.claude/evidence/phase-9");

function ensureEvidenceDir(): void {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

// ── 1. Provider=none (default / static-export mode) ──────────────────────────
//
// auth_mode=none: identity=null, no login UI, no role-gating.
// Preserves current single-operator behavior exactly (AC-5a regression guard).

test.describe("P5-RBAC: provider=none — public degradation (AC-5a)", () => {
  test.beforeEach(async ({ page }) => {
    // Explicitly clear any provider key so auth_mode=none is active.
    await page.addInitScript(() => {
      window.localStorage.removeItem("rv_auth_provider");
    });
  });

  test("app loads without login form in auth_mode=none (AC-5a)", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });
    // No login form — auth_mode=none is the passthrough mode
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
    await expect(page.getByRole("form", { name: "Sign in" })).not.toBeVisible();
  });

  test("portfolio accessible as read-only public (allowed action)", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByTestId("run-list")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Portfolio Command Center")).toBeVisible();
    // No auth barrier
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
  });

  test("Settings nav accessible in auth_mode=none — role gate bypassed (AC-5a)", async ({
    page,
  }) => {
    // AppShell.tsx:116: roleGated = authMode !== 'none' && isRoleGated(item)
    // When authMode='none', roleGated=false always — Settings is NOT disabled.
    await page.goto("/runs");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible({ timeout: 10_000 });
    // Scope to primary navigation to avoid any other "Settings" button on the page
    const settingsBtn = nav.getByRole("button", { name: "Settings" });
    await expect(settingsBtn).toBeVisible();
    await expect(settingsBtn).not.toBeDisabled();
    await expect(settingsBtn).not.toHaveAttribute("aria-disabled", "true");
  });

  test("run detail accessible without auth (sharing public-degradation, AC-5)", async ({
    page,
  }) => {
    // In auth_mode=none the run URL is publicly accessible.
    // Sensitivity fail-closed guarantee (AC-2) is verified by TEST-001's regression
    // suite; here we confirm no auth barrier blocks the public-degradation path.
    await page.goto(`/runs/${RUN_ID}`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
  });

  test("screenshot: auth-context-none — R-P4 visual evidence (AC-5 smoke)", async ({
    page,
  }) => {
    ensureEvidenceDir();
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/runs");
    // Wait for app shell to render — portfolio or any visible app element
    await page.waitForSelector('[aria-label="Research Foundry navigation"], [data-testid="run-list"]', {
      timeout: 15_000,
    });
    // Allow React rendering to settle before screenshot
    await page.waitForTimeout(500);
    const screenshotPath = path.join(EVIDENCE_DIR, "auth-context-none.png");
    await page.screenshot({ path: screenshotPath, fullPage: false });
    expect(fs.existsSync(screenshotPath)).toBe(true);
  });
});

// ── 2. Provider=local_static (UI shape + limitation documented) ───────────────
//
// Sets rv_auth_provider=local_static in localStorage → AuthProvider renders
// LocalLoginForm when identity is null (no login has occurred).
// Full login → role-bounded flow documented as limitation (no backend).

test.describe("P5-RBAC: provider=local_static — login gate renders", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("rv_auth_provider", "local_static");
    });
  });

  test("LocalLoginForm appears (role-denied state: all content blocked)", async ({ page }) => {
    await page.goto("/runs");
    // Login form is the entire UI — role-denied action: app content inaccessible
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
    // Portfolio run-list is NOT accessible pre-login
    await expect(page.getByTestId("run-list")).not.toBeVisible();
  });

  test("login form has username, password fields and submit button", async ({ page }) => {
    await page.goto("/runs");
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
    // Verify all form elements render correctly
    await expect(page.locator("#rv-login-username")).toBeVisible();
    await expect(page.locator("#rv-login-password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeDisabled(); // username empty
  });

  test("login form submit button enabled after typing username", async ({ page }) => {
    await page.goto("/runs");
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
    await page.locator("#rv-login-username").fill("testuser");
    await expect(page.getByRole("button", { name: "Sign in" })).not.toBeDisabled();
  });

  test("screenshot: auth-context-local-static — R-P4 visual evidence (AC-5 smoke)", async ({
    page,
  }) => {
    ensureEvidenceDir();
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/runs");
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
    const screenshotPath = path.join(EVIDENCE_DIR, "auth-context-local-static.png");
    await page.screenshot({ path: screenshotPath, fullPage: false });
    expect(fs.existsSync(screenshotPath)).toBe(true);
  });

  // LIVE MODE LIMITATION
  // ──────────────────────────────────────────────────────────────────────────
  // Full login → role-bounded → sharing flow requires a running RF API server.
  // Skipped here; documented for execution in a live environment.
  //
  // To run live:
  //   VITE_AUTH_PROVIDER=local_static pnpm run dev (+ rf serve on :8765)
  //   then: pnpm exec playwright test p5-auth-rbac.spec.ts --grep "LIVE MODE"
  test(
    "LIVE MODE: local_static full login → viewer role-bounded → sharing [RF API server required]",
    async ({ page }) => {
      test.skip(true, "Live-mode limitation: requires RF API server at VITE_RUNS_LOOPBACK_API_TOKEN URL. " +
        "Steps: fill username=viewer/password → submit → verify Settings nav disabled (viewer role denied) " +
        "→ Catalog/Builder accessible (viewer allowed) → navigate to sharing URL → verify sensitivity-gated " +
        "run is blocked (AC-2 fail-closed). " +
        "For admin role: Settings nav enabled (admin allowed). " +
        "Run in a live environment with backend.");
      void page;
    },
  );

  test(
    "LIVE MODE: local_static admin role Settings accessible (role-allowed action) [RF API server required]",
    async ({ page }) => {
      test.skip(true, "Live-mode limitation: requires RF API server. " +
        "Steps: login as admin role user → verify Settings nav enabled (allowedRoles includes admin) → " +
        "verify Catalog enabled → verify Builder enabled (all viewer-tier allowed). " +
        "This is the 'allowed' role-tier action complement to the viewer 'denied' case above.");
      void page;
    },
  );
});

// ── 3. Provider=clerk (UI shape + limitation documented) ─────────────────────
//
// Sets rv_auth_provider=clerk → AuthProvider lazy-loads ClerkShell.
// Without VITE_CLERK_PUBLISHABLE_KEY, Clerk will error; screenshot captures state.
// Full Clerk flow documented as limitation (requires live Clerk tenant).

test.describe("P5-RBAC: provider=clerk — ClerkShell lazy-loads", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("rv_auth_provider", "clerk");
    });
  });

  test("ClerkShell loads without RF LocalLoginForm (Clerk owns UI when provider=clerk)", async ({
    page,
  }) => {
    // Collect page errors to avoid test crash on Clerk missing-key error
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    await page.goto("/runs");
    // Wait for initial load to complete
    await page.waitForLoadState("domcontentloaded");
    // LocalLoginForm (rv auth overlay) must NOT render when provider=clerk —
    // ClerkShell owns the auth UI surface in this mode.
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible({ timeout: 5_000 });
    // Page must survive (no fatal crash before DOMContentLoaded)
    // Note: Clerk error with missing key is expected — screenshot still valid.
  });

  test("screenshot: auth-context-clerk — R-P4 visual evidence (AC-5 smoke)", async ({
    page,
  }) => {
    ensureEvidenceDir();
    // Suppress page errors — Clerk will warn/error without a publishable key
    page.on("pageerror", () => {});

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/runs");
    // Wait briefly for Clerk lazy-load to settle (or error)
    await page.waitForTimeout(2_000);
    const screenshotPath = path.join(EVIDENCE_DIR, "auth-context-clerk.png");
    await page.screenshot({ path: screenshotPath, fullPage: false });
    expect(fs.existsSync(screenshotPath)).toBe(true);
  });

  // LIVE MODE LIMITATION
  test(
    "LIVE MODE: Clerk full login → role-bounded → sharing [live Clerk tenant required]",
    async ({ page }) => {
      test.skip(true, "Live-mode limitation: requires VITE_CLERK_PUBLISHABLE_KEY set to a real Clerk " +
        "organization key + paid Clerk plan for custom roles (FU-3). " +
        "Steps: Clerk SignIn renders → sign in as viewer/admin → useClerkAuth resolves identity → " +
        "AuthContext wires Clerk JWT token → role-bounded nav assertions (viewer: Settings disabled; " +
        "admin: Settings enabled) → sharing URL with sensitivity-gated run → verify blocked (AC-2). " +
        "Run with: VITE_AUTH_PROVIDER=clerk VITE_CLERK_PUBLISHABLE_KEY=pk_... pnpm run dev (+ rf serve).");
      void page;
    },
  );
});

// ── 4. Role-bounded catalog / builder actions ─────────────────────────────────
//
// auth_mode=none: all nav items accessible (no role gate per AC-5a).
// local_static pre-login: all content blocked by login form (denied state).
// Post-login role assertions: documented as live-mode limitation above.

test.describe("P5-RBAC: role-bounded catalog/builder actions", () => {
  test("auth_mode=none: Catalog nav accessible (viewer-allowed action, no role gate)", async ({
    page,
  }) => {
    await page.addInitScript(() => window.localStorage.removeItem("rv_auth_provider"));
    await page.goto("/runs");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible({ timeout: 10_000 });
    // Scope to navigation to avoid matching run-title buttons with "Catalog" in label
    const catalogBtn = nav.getByRole("button", { name: "Catalog" });
    await expect(catalogBtn).toBeVisible();
    await expect(catalogBtn).not.toBeDisabled();
  });

  test("auth_mode=none: Builder nav accessible (viewer-allowed action, no role gate)", async ({
    page,
  }) => {
    await page.addInitScript(() => window.localStorage.removeItem("rv_auth_provider"));
    await page.goto("/runs");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible({ timeout: 10_000 });
    const builderBtn = nav.getByRole("button", { name: "Builder" });
    await expect(builderBtn).toBeVisible();
    await expect(builderBtn).not.toBeDisabled();
  });

  test("provider=local_static pre-login: Catalog inaccessible (all content denied)", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("rv_auth_provider", "local_static");
    });
    await page.goto("/catalog");
    // Login form blocks all content — catalog denied (login gate)
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
    // Primary nav is not rendered (login form replaces entire app)
    await expect(
      page.getByRole("navigation", { name: "Primary" }),
    ).not.toBeVisible();
  });

  test("provider=local_static pre-login: Settings inaccessible (all content denied)", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("rv_auth_provider", "local_static");
    });
    await page.goto("/settings");
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).toBeVisible({ timeout: 10_000 });
  });
});

// ── 5. Sharing scenario: fail-closed on sensitivity (AC-2) ───────────────────
//
// In auth_mode=none (public degradation): run URL is accessible.
// Sensitivity fail-closed guarantee (AC-2) is enforced server-side and verified
// by TEST-001's regression suite. Here we confirm the public-path is intact and
// no auth barrier incorrectly blocks the degraded-public access path.

test.describe("P5-RBAC: sharing scenario (AC-2 fail-closed surface)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => window.localStorage.removeItem("rv_auth_provider"));
  });

  test("run detail shareable URL accessible in auth_mode=none (no auth barrier)", async ({
    page,
  }) => {
    // Static-export mode public degradation: run is accessible without login.
    // AC-2 sensitivity fail-closed is a server-side invariant; E2E verifies
    // the UI path is open and no auth barrier blocks public-degradation mode.
    await page.goto(`/runs/${RUN_ID}`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
  });

  test("report tab accessible in auth_mode=none (sharing read-only public view)", async ({
    page,
  }) => {
    await page.goto(`/runs/${RUN_ID}?view=report`);
    await expect(page.getByTestId("run-detail")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("tabpanel-report")).toBeVisible();
    // No login form blocking the shared report view
    await expect(
      page.locator('[role="main"][aria-label="Research Foundry login"]'),
    ).not.toBeVisible();
  });

  // LIVE MODE: sensitivity-scoped share link with over-threshold run
  test(
    "LIVE MODE: sensitivity-gated run fails closed on share link (AC-2) [RF API server required]",
    async ({ page }) => {
      test.skip(true, "Live-mode limitation: requires RF API server with a run whose sensitivity " +
        "exceeds viewer.sensitivity_threshold. Steps: navigate to /runs/<over-threshold-run-id> " +
        "→ verify run detail is blocked/redacted per P5.7 sensitivity-gate (AC-2 fail-closed). " +
        "The static fixture run has sensitivity=below-threshold; this test requires a real run.");
      void page;
    },
  );
});
