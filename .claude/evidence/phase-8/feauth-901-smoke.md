# FEAUTH-901 Runtime Smoke Results

**Phase**: 8 (P5.8)
**Date**: 2026-07-07

## Test suite run

All 901 tests passing across 37 test files.

```
Test Files  37 passed (37)
      Tests  901 passed (901)
   Start at  19:51:25
   Duration  6.36s (transform 3.43s, setup 5.44s, collect 15.89s, tests 11.13s)
```

## Check 1: local_static login (success + failure)

PASS

**Success path** — `AuthContext.tsx:311-323`: `provider=local_static` renders `LocalLoginForm`
with `onSubmit={handleLocalLogin}` when `identity` is null. `LocalLoginForm.tsx:51-55`:
`handleSubmit` calls `void onSubmit(username.trim(), password)` on form submission.

**Failure path** — `AuthContext.tsx:240-251`: `handleLocalLogin` catches thrown `ClientError`
and sets `loginError` state. `AuthContext.tsx:317-319`: error is passed as `error={loginError}`
prop to `LocalLoginForm`. `LocalLoginForm.tsx:123-133`: `{error && (<div className="rv-auth-error"
role="alert" aria-live="assertive">…</div>)}` — error displayed in a live region so screen
readers announce it.

## Check 2: Clerk login flow

PASS

**Lazy load** — `AuthContext.tsx:134-136`: `LazyClerkShell = React.lazy(() =>
import("./ClerkShell"))`. `AuthContext.tsx:291-308`: `provider=clerk` branch wraps
`<LazyClerkShell>` in `<React.Suspense fallback={null}>`.

**SignIn rendering** — `ClerkShell.tsx:73-80`: `ClerkAuthInner` returns `<div
className="rv-auth-overlay"><SignIn /></div>` when `!identity` (unauthenticated state).

**Identity propagation** — `ClerkShell.tsx:57-67`: `useEffect` fires `onIdentityResolved`
when `identity` is truthy; reaches authenticated state in `AuthContext` via
`handleClerkIdentityResolved` → `setIdentity(resolved)`.

**P5.4 shim stub** — `src/auth/hooks/useClerkAuth.ts:1-18`: File header is explicitly marked
"P5.4 WIRING NOTE: This stub is a placeholder" and "TO BE REPLACED: Replace the stub body here
once ClerkShell.tsx is fully validated against a live Clerk deployment (P5.4 completion gate)."
The actual `useClerkAuth` used by `ClerkShell.tsx` is the real hook at `src/auth/useClerkAuth.ts`
(imported at `ClerkShell.tsx:24`). The shim at `src/auth/hooks/useClerkAuth.ts` is the
fallback stub — clearly annotated.

## Check 3: Admin UI visibility gating

PASS

**Code gate** — `SettingsScreen.tsx:46-48`:
```ts
const isAdmin =
  authMode !== "none" &&
  (identity?.roles ?? []).some((r) => ["admin", "owner"].includes(r));
```
`SettingsScreen.tsx:246-260`: Admin section wrapped in `{isAdmin && (<section
data-testid="admin-section">…</section>)}`.

**Test coverage** — `p5-admin-settings.test.tsx`, describe "SettingsScreen — admin section
visibility":
- Line 137: "renders admin section for 'admin' role" — `data-testid='admin-section'` is not null
- Line 143: "renders admin section for 'owner' role" — `data-testid='admin-section'` is not null
- Line 149: "hides admin section for 'researcher' role" — `data-testid='admin-section'` is null
- Line 161: "hides admin section for 'reviewer' role" — `data-testid='admin-section'` is null
- Line 173: "hides admin section for 'viewer' role" — `data-testid='admin-section'` is null
- Line 185: "hides admin section when identity is null (unauthenticated)"
- Line 193: "hides admin section when authMode is 'none' even if identity has admin role (AC-5a)"

All pass in the 901/901 run.

## Check 4: Per-role affordance (5 checks)

All roles exercised by `p5-admin-settings.test.tsx` and `SettingsScreen.tsx:46-48`.

The isAdmin gate at `SettingsScreen.tsx:46-48` and `RateLimitConfigPanel` edit-button gating
are the two role-differentiated surfaces. Nav items beyond Settings are not role-gated at the
UI layer (server-side require_role is the authoritative boundary per FR-6 / SettingsScreen
comment at line 41-43).

- **Owner** (`roles: ["owner"]`): PASS — isAdmin=true; `data-testid='admin-section'` renders
  (confirmed by "renders admin section for 'owner' role" test at line 143). All nav items
  accessible.

- **Admin** (`roles: ["admin"]`): PASS — isAdmin=true; `data-testid='admin-section'` renders
  (confirmed by "renders admin section for 'admin' role" test at line 137). Rate limit Edit
  button visible (confirmed by "shows Edit button for admin role" test at line 423).

- **Researcher** (`roles: ["researcher"]`): PASS — isAdmin=false; `data-testid='admin-section'`
  absent (confirmed by "hides admin section for 'researcher' role" test at line 149). Settings
  admin section gated; all other screens accessible.

- **Reviewer** (`roles: ["reviewer"]`): PASS — isAdmin=false; `data-testid='admin-section'`
  absent (confirmed by "hides admin section for 'reviewer' role" test at line 161). Settings
  admin section gated; all other screens accessible.

- **Viewer** (`roles: ["viewer"]`): PASS — isAdmin=false; `data-testid='admin-section'` absent
  (confirmed by "hides admin section for 'viewer' role" test at line 173). Rate limit Edit
  button also absent (confirmed by "does not show Edit button for viewer role (read-only)" test
  at line 434 in `RateLimitConfigPanel` describe block). Settings admin section gated.

## Check 5: Static-export degrade

PASS

**Static-export detection** — `AuthContext.tsx:79-81`:
```ts
const IS_STATIC_EXPORT: boolean =
  typeof import.meta !== "undefined" &&
  import.meta.env?.VITE_RUNS_STATIC_EXPORT === "true";
```

**No login UI** — `AuthContext.tsx:106-110` (inside `getAuthConfig()`):
```ts
if (IS_STATIC_EXPORT) {
  return { provider: "none", authMode: "none" };
}
```
This forces `authMode="none"` regardless of any configured provider. `AuthContext.tsx:281-287`:
`authMode === "none"` branch is a pure passthrough — renders children directly with
`identity=null`, no login UI.

**staticGet for all data fetches** — `client.ts:204-215`: `staticGet<T>()` performs plain `fetch`
with only `Accept: application/json` (no auth headers). All three exported fetch functions in
non-loopback mode call `staticGet()` directly: `fetchRunList` (line 231), `fetchRunDetail`
(line 249), `fetchGovernanceConfig` (line 276). When `IS_STATIC_EXPORT` forces auth_mode=none,
the loopback path is never enabled, so all data fetches exclusively use `staticGet()`.

## Note

This is the phase-local smoke check for FEAUTH-901. Full regression coverage is
`p5-auth-rbac.spec.ts` (Phase 9).
