---
title: "Quick Feature: Builder claim-preview loading affordance (consume isLoading)"
schema_version: 2
doc_type: quick_feature
status: completed
created: 2026-08-02
updated: 2026-08-02
feature_slug: builder-claim-previews-loading-affordance
category: enhancements
estimated_points: 3
tier: 0
owner: nick
risk_level: low
parent_contract: docs/project_plans/feature_contracts/enhancements/runs-viewer-builder-live-claim-previews.md
branch: feat/builder-previews-loading
files_affected:
  - frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.ts
  - frontend/runs-viewer/src/screens/BuilderScreen.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderDraftCard.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderBlockEditor.tsx
  - frontend/runs-viewer/src/styles/builder.css
  - frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.test.tsx
  - frontend/runs-viewer/src/test/builder-screen.test.tsx
---

# Quick Feature: Builder claim-preview loading affordance

## Problem

`useBuilderClaimPreviewResolver()` returns `{ resolve, isLoading }`
(`hooks/useBuilderClaimPreviews.ts`), but `BuilderScreen.tsx:113` destructures only
`resolve` and drops `isLoading` on the floor.

Consequence in loopback mode: while the per-claim `GET /catalog/items/{id}` fetches are
in flight, `resolve()` returns `CLAIM_PREVIEW_UNKNOWN` for every pending claim. Because
that sentinel is *also* the legitimate "this claim is unresolvable" answer (AC-3 of the
parent contract), the audit surfaces render **confident-looking but wrong** state for the
duration of the fetch:

- `BuilderAuditInspector` shows `Unresolved: N`, an `Unresolved claims` issue row, and a
  low/0% coverage pill.
- `BuilderBlockEditor` renders every claim chip in the unresolved treatment.

…then all of it flips to real values when the queries settle. That is the flicker, and it
is worse than a flicker: for ~one round trip the Builder asserts "these claims could not
be resolved from the catalog", which is a false claim on a verification surface. RF's
posture is that unsupported material is *labeled*, not inferred — a pending fetch is not
an unresolvable claim.

## Approach

Distinguish **pending** from **unresolvable**, and render pending as pending.

1. **`useBuilderClaimPreviews.ts`** — additive: alongside `resolve` and `isLoading`, expose
   `isPending(claimId): boolean`. `isLoading` is the draft-wide aggregate (section-level
   affordances); `isPending` is per-claim (chip-level). Per-claim is necessary because a
   claim link with **no** `catalog_item_id` resolves to UNKNOWN *immediately* and is never
   pending — labeling it "resolving" just because a sibling claim is in flight would swap
   one wrong label for another. In static (non-loopback) mode `isPending` is always `false`.

2. **`BuilderScreen.tsx`** — destructure `isLoading: previewsLoading` and `isPending`;
   thread both to `BuilderDraftCard` and `BuilderAuditInspector`.

3. **`BuilderAuditInspector`** — new optional `previewsLoading?: boolean` (default `false`).
   While true:
   - Coverage/paragraph-summary section: pending affordance instead of numbers — reuse the
     existing `isApplicable === false` treatment (`—`/`…`, no 0%-filled bar), and replace
     the `StatRow` list with one "Resolving claims…" line.
   - Issues section: "Resolving claims…" instead of issue rows; categories are not
     clickable while pending. Suppressed wholesale rather than per-category — 3 of the 5
     categories (`unresolved_claim`, `confidence_unknown`, `weak_confidence`) are
     preview-derived, and a partially-correct issue list is exactly the false-confidence
     failure this change exists to remove.
   - Linked-sources section: pending line instead of an empty list.
   - `aria-busy="true"` on the pending sections.
   - **Verify / Publish stay enabled.** The backend computes verification independently of
     the client-side resolver; disabling them would be an unnecessary functional
     restriction. This change is presentational only.

4. **`BuilderDraftCard`** — pass `previewsLoading` + `isPending` through to the editor.

5. **`BuilderBlockEditor`** — claim chips: when `isPending(claim_id)`, render a neutral
   "resolving" chip rather than the unresolved treatment. Section coverage bar: when
   `previewsLoading`, render `…` instead of a 0%-filled bar (mirrors the existing
   `isApplicable` handling at `BuilderBlockEditor.tsx:374-376`).

6. **`styles/builder.css`** — minimal `--pending` variants, consistent with the existing
   `rv-loading` / `rv-muted` idiom. No new design language.

### Non-goals

- No change to static-mode behavior (`isLoading`/`isPending` are constant `false` there).
- No change to `builderCoverage.ts`'s pure functions or the `BuilderClaimPreviewOrUnknown`
  type union. Pending is a *render-time* distinction; the coverage math keeps treating an
  unresolved claim as not-covered.
- No new endpoint, token, or auth surface.

## Acceptance criteria

- **AC-1** `BuilderScreen.tsx` consumes the resolver's `isLoading`; no destructured-and-
  dropped return value remains.
- **AC-2** While claim-item fetches are in flight in loopback mode, the audit inspector
  renders a pending affordance and does **not** render an `Unresolved claims` count or a
  coverage percentage.
- **AC-3** After the fetches settle, the inspector renders the real coverage/issue values
  with no intermediate wrong-value paint.
- **AC-4** A claim link with no `catalog_item_id` is reported as unresolvable, not pending,
  even while sibling claims are still loading.
- **AC-5** Static (non-loopback) mode renders functionally and visually identically to
  before this change. (Not *byte*-identically: the pending affordances are gated behind
  `previewsLoading`, which is constant `false` in static mode, but the change also adds one
  unconditional `data-testid` on the section-coverage value — test instrumentation with no
  visual or behavioral effect. Reviewer nit, accepted as written.)
- **AC-6** Pending sections carry `aria-busy`.
- **AC-7** Gates green: `tsc -p tsconfig.app.json --noEmit`, `vitest run` (no new failures
  vs. baseline), `eslint src --max-warnings=0`, `vite build`.

## Baseline (pre-change, this worktree)

- `tsc -p tsconfig.app.json --noEmit` → clean (exit 0)
- `vitest run` → **2 failed test files / 45 passed**, **1 failed test / 1069 passed**
  - `codegen/generate-types.contract.test.mjs` — standalone mjs script, no vitest suite
    (pre-existing collection artifact)
  - `src/test/provenance-correctness.test.ts` — needs the private data-plane fixture, which
    is not present in a worktree (environmental)

## Outcome

**Landed.** Gates green on the final tree:

| Gate | Result |
|------|--------|
| `tsc -p tsconfig.app.json --noEmit` | exit 0, clean |
| `vitest run` | 1072 passed / 1 failed (baseline: 1069 / 1) — +3 new tests, no new failures |
| `eslint src --max-warnings=0` | 0 problems in `Builder/`, `hooks/`, `screens/`; the 10 pre-existing problems in `auth/**` + `ClaimLedger/**` are byte-identical to baseline |
| `vite build` | ✓ (pre-existing chunk-size warning only) |

Reviewer verdict: **APPROVE-WITH-NITS** (`senior-code-reviewer`, Mode E). Both nits closed:

1. AC-5's "byte-identical" wording softened above — one new unconditional `data-testid`.
2. The pending claim chip's ⤢ expand button now carries `disabled={pending}`. It previously
   fired `onOpenClaim()` for an id that `draftClaims` filters out by construction (every
   pending claim resolves to `CLAIM_PREVIEW_UNKNOWN`), so expanding a resolving chip opened
   a modal for a claim absent from the collection it searches — the same
   offering-an-affordance-we-can't-back defect class this feature removes.

Independently confirmed during review (both were the load-bearing risks):

- **Pending cannot hang.** The global query config is `retry: 1` (`src/api/queryClient.ts`),
  and `fetchCatalogItem` returns `null` rather than throwing on a 404 — so a failed or
  missing catalog item settles to the honest "unresolvable" answer instead of leaving the
  inspector permanently in "Resolving claims…", which would have been a worse regression
  than the flicker.
- **The new tests are not vacuous.** Both hold the fetch open via a manually-resolved
  promise and assert mid-flight state before settling it, so the pending window genuinely
  opens (a synchronous mock would have false-greened the whole anti-flicker assertion).
