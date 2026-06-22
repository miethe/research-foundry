# React Component Patterns — runs-viewer

**Scope**: `frontend/runs-viewer/src/components/`

## Conventions (observed from codebase)

1. **Feature directories** — each major feature is a directory:
   `RunList/`, `RunDetail/`, `ClaimLedger/`, `LineageGraph/`, `TrustPanel/`, `SourceCard/`, `ReportOverlay/`, `ProvenanceModal/`, `shared/`

2. **Plain function components** — no class components; exported as named functions.

3. **TypeScript props interfaces** — co-located above the component (`interface RunCardProps { … }`).

4. **Type imports from `@/types/rf`** — generated types mirror Python schemas (e.g. `RFRunSummary`, `RFStatusDerived`, `RFSensitivity`).

5. **CSS class naming** — `rv-` prefix for runs-viewer; `it-` prefix for shared design tokens (`it-card`, `it-pill`, `it-chip`, `it-btn`). No CSS-in-JS; no Tailwind; plain `.css` files in `src/styles/`.

6. **Graceful degradation** — optional fields render nothing when null/absent (never crash on partial data).

7. **Data hooks** — components consume data via hooks (`useRunList`, `useRunDetail`, `useClaimLedger`, `useSourceCard`) which wrap React Query + the `api/client.ts` fetchers.

8. **No external component library** — no shadcn, no Radix, no `@miethe/ui`. Components are bespoke with semantic HTML and ARIA attributes.

9. **Test IDs** — `data-testid` attributes on key elements for Vitest assertions.

## Example: RunCard

`components/RunList/RunCard.tsx` renders a clickable card with lifecycle badge, sensitivity chip, claim counts, governance verdict, and tags — all conditional on data presence.
