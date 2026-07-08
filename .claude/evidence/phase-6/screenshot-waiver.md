# AC-5 Visual Evidence Waiver

**Phase**: 6 (P5.6)
**AC**: AC-5 (visual_evidence_required: before/after screenshots for GATE-900 rate-limit badge absence and GATE-901 panel disabled states — each of the 4 admin panels independently)
**Date**: 2026-07-08

## Why screenshots cannot be captured in this phase

This SPA is a static-export build with no live server. The worktree context has no browser runtime. Screenshots require:
1. A running dev server (`pnpm dev` in frontend/runs-viewer)
2. A browser with the correct env vars set for each panel state (data-absent, error, network-fail)
3. A responsive viewport at >=1440px

None of these are available in the automated agent execution context.

## Visual coverage in Phase 9

Phase 9's `p5-auth-rbac.spec.ts` Playwright suite explicitly covers:
- GATE-900: AppShell with absent rate-limit headers → no badge rendered (static and live-API modes)
- GATE-901: All 4 admin panels in disabled state — each triggered independently with targeted fetch failures
- Desktop viewport sizes (Playwright default includes >=1440px runs)

This is per the phase plan: "GATE-900 and GATE-901 runtime smoke is the phase-local pre-check, explicitly cross-referenced to Phase 9 in its Completion Report note."

## Code-path verification (substitute evidence)

The AC-5 visual states are verified by code-path analysis and unit tests:

- **GATE-900 absence**: `gate-900-evidence.md` in this directory documents the `getRateLimitState() → null → badge condition false` path verified by `p5-auth-header.test.ts` describe block `"GATE-900 — rate-limit header contract"`.

- **GATE-901 panel disabled states**: `gate-901-evidence.md` in this directory documents all 4 panels' independent disabled-state tests in `p5-admin-settings.test.tsx`, including the cascade-guard test `"RbacStatusPanel disabled state does not cascade to WorkspaceMembersPanel (GATE-901 independence)"`.

Full Playwright visual regression: Phase 9.
