# GATE-900 Rate-Limit-State Absence Evidence

**Phase**: 6 (P5.6)
**Gate**: GATE-900 (rate-limit header contract — absent headers → no badge rendered)
**Date**: 2026-07-08

## Reactive path in AppShell

`AppShell` subscribes to rate-limit state using a `useState` + `useEffect` + `subscribeRateLimitState`
pattern. The badge condition is:

```
rlState?.retryAfter !== undefined
```

`rlState` is the value returned by `getRateLimitState()` from `frontend/runs-viewer/src/api/client.ts`.
It starts as `null` (module-level default). `subscribeRateLimitState` fires only when a response
updates the stored state. When the upstream API returns **no** `X-RateLimit-*` headers,
`getRateLimitState()` remains `null` throughout the page lifecycle — the badge condition evaluates
to `false` and no badge element is rendered.

The only path that causes a badge is a `429` response with a `Retry-After` header, which sets
`rlState.retryAfter` to a positive integer.

## Unit-test verification (p5-auth-header.test.ts)

Test file: `frontend/runs-viewer/src/test/p5-auth-header.test.ts`
Describe block: `"GATE-900 — rate-limit header contract"`

| Test name | What it verifies |
|-----------|-----------------|
| `absent X-RateLimit headers → getRateLimitState() returns null → AppShell no badge` | 200 response with no X-RateLimit headers → `getRateLimitState()` is `null` → badge condition false |
| `present-and-under-budget (remaining > 0, no Retry-After) → no badge (retryAfter absent)` | X-RateLimit headers present but no `Retry-After` → `state.retryAfter` is `undefined` → badge condition false |
| `present-and-exceeded (429 + Retry-After) → getRateLimitState().retryAfter set → AppShell badge shows value` | Positive control: 429 + `Retry-After: 42` → `state.retryAfter === 42` → badge would render |

The first two tests directly verify the **absence** case: no badge when `Retry-After` is not present.
The third test is the positive control confirming the badge-render path activates only on 429+header.

## Code references

- `frontend/runs-viewer/src/api/client.ts` — `getRateLimitState()` / `subscribeRateLimitState` exported from client module; state updated inside `loopbackGet()` response handler
- `frontend/runs-viewer/src/components/AppShell.tsx` — badge render gated on `rlState?.retryAfter !== undefined`

## Visual evidence deferred

Visual regression (screenshot of AppShell with no badge vs. badge rendered) is deferred to
Phase 9's `p5-auth-rbac.spec.ts` Playwright suite per the P5.8 waiver pattern.
See `screenshot-waiver.md` in this directory.
