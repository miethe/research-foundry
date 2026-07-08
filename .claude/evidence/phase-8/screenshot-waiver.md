# AC-5 Visual Evidence Waiver

**Phase**: 8 (P5.8)
**AC**: AC-5 (visual_evidence_required: before/after screenshots at desktop >=1440px for each of the 3 provider states: clerk, local_static, none)
**Date**: 2026-07-07

## Why screenshots cannot be captured in this phase

This SPA is a static-export build with no live server. The worktree context has no browser runtime. Screenshots require:
1. A running dev server (`pnpm dev` in frontend/runs-viewer)
2. A browser with the correct env vars set for each provider mode
3. A responsive viewport at >=1440px

None of these are available in the automated agent execution context.

## Visual coverage in Phase 9

Phase 9's `p5-auth-rbac.spec.ts` Playwright suite explicitly covers:
- All 3 provider states in both static-export and live-API modes
- Desktop viewport sizes (Playwright default includes >=1440px runs)

This is per the phase plan: "FEAUTH-901's runtime smoke is the phase-local pre-check, explicitly cross-referenced to Phase 9 in its Completion Report note."

## Code-path verification (substitute evidence)

The AC-5 visual states are verified by code-path analysis in `.claude/evidence/phase-8/feauth-901-smoke.md`:

- `none` mode: `AuthContext.tsx:79-81` detects `VITE_RUNS_STATIC_EXPORT="true"` → `IS_STATIC_EXPORT=true`.
  `AuthContext.tsx:106-110` (inside `getAuthConfig()`): `if (IS_STATIC_EXPORT) { return { provider: "none", authMode: "none" }; }`
  forces `authMode="none"` regardless of configured provider.
  `AuthContext.tsx:281-287`: `authMode === "none"` branch is a pure passthrough — renders children
  directly with `identity=null`, no login UI rendered whatsoever (AC-5a).

- `local_static` mode: `AuthContext.tsx:311-323`: when `provider=local_static` and `!identity`,
  renders `<LocalLoginForm onSubmit={handleLocalLogin} isLoading={isLoading} error={loginError} />`.
  `LocalLoginForm.tsx` renders the username/password form. Post-login, `AuthContext.tsx:324-328`
  renders children inside `<AuthContext.Provider value={{ ...contextValue, identity }}>`.

- `clerk` mode: `AuthContext.tsx:134-136`: `LazyClerkShell = React.lazy(() => import("./ClerkShell"))`.
  `AuthContext.tsx:291-308`: `provider=clerk` branch wraps `<LazyClerkShell>` in
  `<React.Suspense fallback={null}>` — Clerk SDK never bundled unconditionally.
  `ClerkShell.tsx:73-80`: `ClerkAuthInner` returns `<div className="rv-auth-overlay"><SignIn /></div>`
  when `!identity` (unauthenticated state).

Full Playwright visual regression: Phase 9.
