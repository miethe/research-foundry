---
title: "Quick Feature: enforce BuilderIssue key exhaustiveness in deriveIssueItems"
schema_version: 2
doc_type: quick_feature
status: completed
created: 2026-08-03
updated: 2026-08-03
feature_slug: builder-issue-key-exhaustiveness
category: enhancements
estimated_points: 2
tier: 0
owner: nick
risk_level: low
tracker_node: node_01KZ49SDK5TR82G0AP2BPMG7RF
branch: feat/builder-issue-key-exhaustiveness
files_affected:
  - frontend/runs-viewer/src/screens/BuilderScreen.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx
---

# Quick Feature: enforce BuilderIssue key exhaustiveness

## Problem

`BuilderScreen.deriveIssueItems` ended in:

```ts
default:
  // TODO: replace with real issue-level data when the RF API exposes it.
  return [];
```

The comment reads as work blocked on an RF API capability. It is not. `BuilderIssue["key"]`
is exactly five members and `deriveIssueItems` has a real `case` for all five, each derived
client-side. `computeDraftIssues()` is the only producer and can only emit those five keys —
so the `default:` branch was unreachable and the TODO actively misdescribed the code.

The real defect was that the branch could not be *reached by the type checker* either.
`BuilderIssueCategory.key` was widened to `string` and cast back via
`switch (category.key as BuilderIssue["key"])`, which defeats exhaustiveness checking. A
future 6th issue category would have compiled cleanly and silently fallen through to
`return []` — surfacing an issue category whose detail list is *confidently empty*.

Same defect class as `f1fb900` ("render pending claim previews as pending, not unresolved"):
an audit surface rendering a confident-looking-but-wrong result instead of signalling the
unknown.

## Approach

1. Narrow `BuilderIssueCategory` to `{ key: BuilderIssue["key"]; severity: BuilderIssueSeverity; … }`.
2. Drop the `as BuilderIssue["key"]` cast on the `switch`.
3. Replace the `default:` body with `return assertNever(category.key)` (module-scope helper);
   delete the stale TODO.

Two follow-on fixes the narrowing surfaced, both genuine rather than silenced:

- `issueSeverity` compared `category.severity === "error"` — a literal with no overlap
  against `BuilderIssueSeverity` (`"critical" | "warning"`), i.e. dead code (TS2367).
  Simplified to `category.severity === "critical" ? "error" : "warning"`; behaviour
  unchanged.
- `BuilderAuditInspector.onOpenIssueCategory` carried its own duplicate widened inline type.
  Narrowed to `(category: BuilderIssue) => void` — structurally identical to
  `BuilderIssueCategory`, and the inspector's only call site (`onOpenIssueCategory(issue)`)
  was already passing a real `BuilderIssue`, so this makes the prop type accurate rather
  than re-casting to satisfy it.

### Non-goals

No new issue category, and no RF API change. This task only makes the seam fail loudly.

## Acceptance criteria

- **AC-1** No `default:` branch silently returning `[]`; an unhandled key is a compile error. ✅
- **AC-2** The stale "when the RF API exposes it" TODO is removed. ✅
- **AC-3** `npx tsc -p tsconfig.app.json --noEmit` clean (bare `npx tsc --noEmit` is a NO-OP
  in this package). ✅
- **AC-4** Positive control: adding a 6th `BuilderIssue["key"]` member produces ≥1 `error TS`. ✅
- **AC-5** Existing builder tests pass. ✅

## Outcome

**Landed.** Gates re-run independently by the orchestrator (not taken from the implementer's report):

| Gate | Result |
|------|--------|
| `tsc -p tsconfig.app.json --noEmit` | exit 0, clean |
| `vitest run` (3 builder files) | 3 files / **23 tests passed** |
| Positive control (`\| "probe_new_key"`) | `BuilderScreen.tsx(334,28): error TS2345: Argument of type '"probe_new_key"' is not assignable to parameter of type 'never'.` |
| Post-revert `tsc` | exit 0, clean; `probe_new_key` absent; tree clean |

Test-file paths differ from the node's shorthand — actual locations are
`src/test/builder-screen.test.tsx`, `src/hooks/useBuilderClaimPreviews.test.tsx`,
`src/lib/builderCoverage.claimresolution.test.ts` (not co-located under `__tests__/`).
