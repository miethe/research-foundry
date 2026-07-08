# GATE-901 Admin-Settings Field Absence Evidence

**Phase**: 6 (P5.6)
**Gate**: GATE-901 (admin-settings panel disabled state — each panel degrades independently)
**Date**: 2026-07-08

## Panel architecture

The admin section of `SettingsScreen` (`frontend/runs-viewer/src/screens/SettingsScreen.tsx`)
renders four independent panels. Each panel owns its own `fetch` call and its own
`disabled` / `loading` / `data` state. There is no shared state between panels — a failure
in one panel does not cascade to others.

### The 4 panels and their independent degradation tests

Test file: `frontend/runs-viewer/src/test/p5-admin-settings.test.tsx`

| Panel component | Describe block | Disabled-state test names |
|----------------|---------------|--------------------------|
| `WorkspaceMembersPanel` | `"WorkspaceMembersPanel — disabled state (GATE-901)"` | `"shows disabled panel when API returns null members array"` · `"shows disabled panel when fetch returns a non-2xx error"` · `"shows disabled panel when fetch throws (network error)"` |
| `RateLimitConfigPanel` | `"RateLimitConfigPanel — disabled state (GATE-900/GATE-901)"` | `"shows disabled panel when fetch returns a non-2xx error"` · `"shows disabled panel when fetch throws (network error)"` |
| `AuthProviderStatusPanel` | `"AuthProviderStatusPanel — disabled state (GATE-901)"` | `"shows disabled panel when fetch fails"` · `"shows disabled panel when fetch returns non-2xx"` |
| `RbacStatusPanel` | `"RbacStatusPanel — disabled state (GATE-901)"` | `"getRbacStatus() returns null → shows disabled panel without crashing"` · `"shows disabled panel when fetch returns a non-2xx error"` · `"shows disabled panel when fetch returns 404 (endpoint not available)"` |

## Panel independence test (cascade guard)

The key isolation test in `"RbacStatusPanel — disabled state (GATE-901)"`:

```
"RbacStatusPanel disabled state does not cascade to WorkspaceMembersPanel (GATE-901 independence)"
```

This test uses a `fetch` mock that rejects on `rbac-status` URLs but resolves with valid
`WORKSPACE_DATA` for all other URLs. It then renders both `RbacStatusPanel` and
`WorkspaceMembersPanel` independently and asserts:

- `RbacStatusPanel` shows `[data-testid='admin-rbac-panel-disabled']`
- `WorkspaceMembersPanel` shows `[data-testid='admin-members-panel']` (data loaded successfully)

This directly verifies that a disabled `RbacStatusPanel` does not cascade to
`WorkspaceMembersPanel` — confirming GATE-901 panel independence.

## Disabled UI state contract

Each panel renders a `data-testid` attribute in its disabled state:

| Panel | Disabled testid | Disabled text content |
|-------|-----------------|-----------------------|
| `WorkspaceMembersPanel` | `admin-members-panel-disabled` | Contains "Member data unavailable" |
| `RateLimitConfigPanel` | `admin-rate-limit-panel-disabled` | Contains "Rate limit config unavailable" |
| `AuthProviderStatusPanel` | `admin-auth-provider-panel-disabled` | Contains "Provider status unavailable" |
| `RbacStatusPanel` | `admin-rbac-panel-disabled` | Contains "RBAC status unavailable" |

All four tests assert the `data-testid` existence after `waitFor()` settling, ensuring the
disabled state is rendered rather than a loading spinner or crash.

## Code references

- `frontend/runs-viewer/src/components/AdminSettings/WorkspaceMembersPanel.tsx`
- `frontend/runs-viewer/src/components/AdminSettings/RateLimitConfigPanel.tsx`
- `frontend/runs-viewer/src/components/AdminSettings/AuthProviderStatusPanel.tsx`
- `frontend/runs-viewer/src/components/AdminSettings/RbacStatusPanel.tsx`
- `frontend/runs-viewer/src/screens/SettingsScreen.tsx` — admin section visibility gate

## Visual evidence deferred

Screenshots of each panel in its disabled state are deferred to Phase 9's
`p5-auth-rbac.spec.ts` Playwright suite per the P5.8 waiver pattern.
See `screenshot-waiver.md` in this directory.
