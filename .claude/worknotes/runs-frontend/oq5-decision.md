# OQ-5 Decision: runs-viewer Styling / Component-Library Posture

**Phase:** 2 (Data Layer) · **Task:** P2-AUDIT-OQ5 · **Date:** 2026-06-19 · **Status:** resolved

## Question

The implementation plan assumed the IntentTree Web fork would carry Tailwind config and
`@miethe/ui` peer requirements that needed compatibility auditing before P3 component work.

## Finding

The audit of the fork source (`~/dev/homelab/development/intenttree/web`) shows the assumption
is **inaccurate**. The source SPA:

- Does **not** depend on Tailwind (no `tailwind`/`postcss` in `package.json`, no `tailwind.config.*`).
- Does **not** depend on `@miethe/ui` (not in `package.json`).
- Uses a **hand-written, plain-CSS design system**: per-feature `src/styles/*.css` files plus a
  central design-token sheet.

## Decision

**The runs-viewer adopts the IntentTree plain-CSS design system as-is. No Tailwind, no `@miethe/ui`.**
P3/P4 components style with the existing `--it-*` design tokens and the `.it-*` / `.rv-*` class
conventions — not utility classes and not an external component library.

### Base CSS carried into `frontend/runs-viewer/src/styles/`

| File | Role |
|------|------|
| `tokens.css` | Full `--it-*` token set (color, type, spacing, radius, shadow, motion, z-index; light + dark). |
| `components.css` | Reusable primitives: `.it-btn`, `.it-badge`, `.it-card`, nav, chip. |
| `app.css` | `.app-shell` grid layout, sidebar, density classes. |
| `index.css` | Global resets / entry. |
| `runs-viewer.css` | New `.rv-*` classes for the RF viewer shell; P3/P4 expand this. |

## Implications for P3/P4

- Build new components against the `--it-*` tokens and `.rv-*` namespace; reuse `.it-card` /
  `.it-badge` primitives for the trust panel, claim ledger, and provenance modal.
- No peer-dependency compatibility work is required — there is no external UI library to reconcile.
- This is a single-operator, read-only viewer; the vanilla-CSS approach keeps the bundle lean
  (P2 build: 377 KB JS / 53 KB CSS) and avoids a build-time CSS framework dependency.
