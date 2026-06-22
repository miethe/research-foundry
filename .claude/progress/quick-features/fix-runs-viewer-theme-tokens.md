---
slug: fix-runs-viewer-theme-tokens
title: Fix broken theme tokens in runs-viewer (dark/light token mix)
status: completed
type: quick-feature
created: 2026-06-21
owner: opus-orchestrator
files_affected:
  - frontend/runs-viewer/src/styles/tokens.css
tokens_defined: 12  # surface-bg, bg-primary, surface-raised, surface-sunken, success, warning, danger, accent-primary, amber-500, orange-700, radius-full, leading-relaxed
gates: { audit: pass (0 undefined), build: pass }
---

# Fix: runs-viewer broken theme tokens

## Symptom (confirmed live @ 10.42.10.76:3030)
`<html data-theme="dark">` is set, but content surfaces render light/white while text
uses the dark-mode near-white token (`--it-text-primary: #f4f6fb`) → near-white text on
near-white surface = invisible. "Combo of dark and light tokens."

## Root cause
Wave-2 tab-enablement screens (library/policies/swarm/alerts) + the portfolio dashboard
reference `--it-*` custom properties that were **never defined** in `tokens.css`
(`tokens.css` last touched at v1 scaffold 5b3ca15, never updated for the new screens).
Undefined vars fall back to hardcoded light hexes that have **no `[data-theme="dark"]`
override**, so dark mode breaks. Confirmed undefined at runtime: `--it-surface-sunken`,
`--it-surface-raised`, `--it-success`, `--it-warning`, `--it-danger`,
`--it-accent-primary`, `--it-amber-500`, `--it-leading-relaxed` (and any others found in a
full audit).

## Fix
Add every referenced-but-undefined `--it-*` token to `tokens.css` in BOTH `:root` (light)
and `[data-theme="dark"]` (dark), anchored to the existing palette/surface scale.

## Gates
- Full audit: zero `var(--it-*)` references resolve to undefined.
- `pnpm build` (runs-viewer) passes.
- Live re-verify in dark mode: text legible on all surfaces.

## Deliver
Commit to **main** (user-directed) + redeploy to 10.42.10.76:3030.
