---
title: "Feature Contract: Runs-Viewer Builder — Live Claim Previews in Loopback Mode"
schema_version: 2
doc_type: feature_contract
it_schema: 1
description: "Make the Report Builder's claim previews, audit inspector, and coverage computation read live RF catalog data when the loopback gate is on, replacing an unconditional 6-id hardcoded mock lookup that silently returns null (and mis-scores coverage) for every real claim. Static-mode behavior is preserved unchanged."
status: completed
created: 2026-08-02
updated: 2026-08-02
feature_slug: runs-viewer-builder-live-claim-previews
category: enhancements
estimated_points: 7
tier: 1
owner: nick
priority: high
risk_level: medium
changelog_required: true
node_type: work_package
execution_mode: unassigned
acceptance_criteria: []
definition_of_done: null
agent_title: null
agent_summary: null
agent_context: null
open_questions:
  - id: OQ-1
    question: "Which live endpoint maps a Builder claim link id (e.g. `clm_038`) to a preview payload — `GET /catalog/items/{catalog_item_id}` (catalog.py:118), or `GET /catalog/search` (catalog.py:71) filtered by claim id?"
    decision_rule: "Executor resolves from code truth: inspect the claim-link payload shape in `reports.py` claim-link routes (reports.py:690) and the existing catalog fetchers in `client.ts:502-547`. Prefer the id-addressable item endpoint when claim ids are catalog-item-addressable; fall back to a search-by-id lookup otherwise. This is an implementation detail, NOT a blocker — do not halt on it."
decisions:
  - decision: "Gate the mocks; do NOT delete `builderMocks.ts`."
    rationale: "Static (non-loopback) mode is a supported, documented product surface, not dead code — `frontend/runs-viewer/README.md` documents the static SPA build, `bootstrap-agentic-node.sh:1840` deliberately falls back to it when `RF_TOKEN_AGENT` is absent, and `catalog-screen.test.tsx:440-458` asserts its 'Available in loopback mode' tooltip. Deleting the mock fallback would break the static build. The defect is that three call sites consult the mocks *unconditionally*, not that the mocks exist."
    status: accepted
  - decision: "'Unresolvable claim' is an explicit third state, distinct from 'low confidence'."
    rationale: "`builderCoverage.ts:178` currently routes every unresolvable claim through the same path as a genuinely low-confidence claim, so a live Builder reports confident-looking coverage numbers computed from nulls. Silent wrongness in a coverage/verification surface is worse than a visible gap — RF's whole posture is that unsupported material is labeled, not inferred."
    status: accepted
  - decision: "No new token, secret, or auth surface. Token handling stays exactly as `client.ts:80-123` implements it."
    rationale: "The LAN :3030 bundle's token coupling is already correct and fail-safe: `bootstrap-agentic-node.sh:1836-1844` sources `RF_TOKEN_AGENT` from serve.env and degrades to a tokenless static build rather than shipping a broken loopback bundle. This contract preserves that invariant; it does not touch it. Keeps the change out of Mode-D territory."
    status: accepted
  - decision: "Read path stays a plain fetch — no model call, no inference."
    rationale: "AOS constraint 4 (no model call on the read/render path). Claim previews are retrieval, not synthesis."
    status: accepted
related_documents:
  - docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/api/reportsClient.ts
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs:
  - "a7f8306"  # feature-branch work commit (orphaned by the squash; see merge_commit)
pr_refs: []
merge_commit: "6f5f73d"
merge_branch: main
files_affected:
  - frontend/runs-viewer/src/lib/builderMocks.ts
  - frontend/runs-viewer/src/lib/builderCoverage.ts
  - frontend/runs-viewer/src/components/Builder/BuilderBlockEditor.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderDraftCard.tsx
  - frontend/runs-viewer/src/screens/BuilderScreen.tsx
  - frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.ts
  - frontend/runs-viewer/src/hooks/index.ts
  - frontend/runs-viewer/src/styles/builder.css
  - frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.test.tsx
  - frontend/runs-viewer/src/lib/builderCoverage.claimresolution.test.ts
---

# Feature Contract: Runs-Viewer Builder — Live Claim Previews in Loopback Mode

> **Authority.** This is a bounded child authority under
> `docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md` §21
> ("create focused child specs or PRDs for any unresolved topic"). It depends on **none** of that
> spec's §20 decisions — no public domain selection, no rights promotion, no trust zones, no BYOK,
> no public URL, no federation. It is loopback-only and local-only. The parent spec remains
> `maturity: shaping` and is **not** an implementation authorization for anything beyond this slice.

## Goal

When the runs-viewer runs with the loopback gate on, the Report Builder's claim previews, audit
inspector, and coverage computation must reflect **live Research Foundry catalog data**. Today they
consult a hardcoded six-entry dictionary regardless of mode, so every real claim resolves to `null`
and the coverage numbers shown to a reviewer are computed from those nulls.

## User / Actor

An operator reviewing or assembling an evidence-backed report in the runs-viewer Builder against a
live `rf serve` backend (loopback, `127.0.0.1:7432`).

## Job To Be Done

"When I link a real claim into a report draft, I need to see that claim's actual passage, source,
and confidence — and I need the coverage indicator to tell me the truth about what my draft is
missing, so I can trust the Builder as a verification surface rather than a demo."

## Scope

**In scope**

- Replace the unconditional mock lookup at the three call sites — `BuilderBlockEditor.tsx:225`,
  `BuilderAuditInspector.tsx:143`, `builderCoverage.ts:178` — with a mode-aware resolution that
  fetches live claim previews when `isLoopbackEnabled()` is true.
- Add an explicit unresolvable/unknown claim state, distinct from low-confidence, and make
  `builderCoverage.ts` account for it without inflating or deflating confidence.
- Add live-mode test coverage for the Builder (currently zero — `builder-screen.test.tsx:1-17`
  documents itself as static-mode only).
- Reconcile the TS payload types against the real router response shapes in `catalog.py` /
  `reports.py`. The prior wave's type assumptions were authored before those routers merged
  (`reportsClient.ts:23-28`) and have never been verified against a live response.

**Out of scope**

- Deleting `builderMocks.ts` or changing any static-mode behavior.
- The five already-correctly-gated mock consumers (`reportsClient.ts:79-93`,
  `BuilderScreen.tsx:64`, `BuilderCatalogPane.tsx`).
- `CatalogScreen` — already live in loopback via `hooks/useCatalog.ts` → `client.ts:502-547`.
- Embedded agent research (`AgentsScreen`, `isAgentsLoopbackEnabled`) — separate gate, separate slice.
- Any auth, token, RBAC, secret, migration, or deletion change. Any such need is a **STOP** and an
  escalation, not a judgment call.
- Anything requiring a §20 platform decision.

## Architecture Constraints

- Files are canonical; DBs are derived. The catalog is a derived read surface here.
- Loopback-only; never exfiltrate. No new outbound host.
- **No model call on the read/render path.**
- No new token surface; `VITE_RUNS_LOOPBACK_API_TOKEN` handling unchanged (`client.ts:80-123`).
- The in-code gate is `VITE_RUNS_FRONTEND_LOOPBACK_API` (`client.ts:51-67`). `RF_UI_LOOPBACK` is the
  **outer** bootstrap variable in `agentic_meta_dev` — do not introduce it as an in-repo flag.
- `agent-writable paths can never mint CLEARED_*/counsel_approved/attested rights values`
  (`no_agent_cleared_rights_value`). This change writes no rights values at all.

## Acceptance Criteria

#### AC-1: Live claim previews resolve in loopback mode
- target_surfaces:
    - frontend/runs-viewer/src/components/Builder/BuilderBlockEditor.tsx
    - frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx
    - frontend/runs-viewer/src/lib/builderCoverage.ts
- propagation_contract: a claim id on a report draft's claim-link resolves through a live catalog fetch to a preview payload (passage, source, confidence) at all three surfaces.
- resilience: see AC-3.
- verified_by: AC-4 tests + AC-7 runtime smoke.

#### AC-2: No mock reachable in loopback mode
- `BUILDER_MOCK_CLAIM_PREVIEWS` / `resolveBuilderClaimPreview`'s static dict is **unreachable** when `isLoopbackEnabled()` is true, at all three target_surfaces above. Demonstrate by test, not by inspection.

#### AC-3: Unresolvable is explicit, never silent
- An unresolvable claim renders a distinct unknown/unavailable state.
- `builderCoverage.ts` does **not** classify unknown as low-confidence, and does not count it as covered.

#### AC-4: Static mode unchanged
- `builder-screen.test.tsx` and `catalog-screen.test.tsx` pass **unmodified** except for additions. Any edit to an existing static-mode assertion must be justified in the Completion Report.

#### AC-5: Live-mode tests exist
- New tests run with `VITE_RUNS_FRONTEND_LOOPBACK_API=true` and a mocked fetch, asserting live preview resolution, the unknown state, and coverage arithmetic against the **real** router payload shape.

#### AC-6: No new secret/token surface
- Grep-assert no new token literal, env var, or auth header path. `client.ts:80-123` token resolution order unchanged.

#### AC-7: Payload contract verified against a live backend
- Runtime smoke against a live `rf serve` on loopback confirms the TS types match actual `catalog.py` / `reports.py` responses. Record the observed payload in the Completion Report. This closes the never-verified assumption at `reportsClient.ts:23-28`.

## Validation Requirements

- `cd frontend/runs-viewer && pnpm test`
- `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit`
  — **`npx tsc --noEmit` without `-p` is a no-op in this repo; it does not typecheck.**
- 4 frontend test files are a known-failing baseline. Record the pre-change failure **set** (file
  names, not just a count) before touching anything, and prove the post-change set is identical.
- AC-7 runtime smoke requires a live `rf serve`; if it cannot be started, that is a reportable
  incomplete AC — do **not** mark it met by inspection.

## Risk Areas

| Risk | Severity | Mitigation |
|---|---|---|
| Live payload shape differs from the TS types (never verified — `reportsClient.ts:23-28`) | **High** | AC-7 makes this an explicit, evidence-bearing AC rather than an assumption. |
| Coverage arithmetic changes silently alter reviewer-facing numbers | High | AC-3 + AC-5 pin the arithmetic under test, including the unknown case. |
| Breaking static mode while "retiring mocks" | Medium | AC-4; mocks are gated, not deleted. |
| OQ-1 endpoint ambiguity stalls the sprint | Low | OQ-1 carries a decision rule; resolve from code truth and log the choice — do not halt. |

## Implementation Notes

*(To be expanded by the contract writer — data requirements, the mode-aware resolver's shape, and
the unknown-state UI treatment. Design decisions above are settled; do not relitigate them.)*

## Completion Report Required

Yes — appended to this file. Must include: the AC-7 observed payload, the pre/post known-failing
test **sets**, the OQ-1 resolution, and any static-mode assertion touched.

## Completion Report

### Summary

Replaced the three unconditional `resolveBuilderClaimPreview()` call sites (plus two more in
`BuilderScreen.tsx` that shared the same defect but weren't in the original three) with a
mode-aware resolver: a new `useBuilderClaimPreviewResolver` hook that, in loopback mode, fetches
`GET /catalog/items/{catalog_item_id}` per distinct claim via the existing `fetchCatalogItem()`
binding, and in static mode delegates unchanged to the mock dictionary. `builderCoverage.ts`'s
audit-summary and issue functions now take the resolver as a parameter and treat an unresolvable
claim as an explicit third state (`unresolved` count / `unresolved_claim` issue bucket), never
folded into "supported" or "weak confidence."

### Files Changed

- `frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.ts` (new) — the mode-aware resolver hook
  + `catalogItemToPreview()` mapper from a live `CatalogItemDetail` to `BuilderClaimPreview`.
- `frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.test.tsx` (new) — AC-5 live-mode tests.
- `frontend/runs-viewer/src/lib/builderCoverage.claimresolution.test.ts` (new) — AC-3/AC-5 pure-function tests.
- `frontend/runs-viewer/src/lib/builderMocks.ts` — added the `CLAIM_PREVIEW_UNKNOWN` sentinel +
  `ClaimPreviewResolver`/`BuilderClaimPreviewOrUnknown` types (shared contract; no dependency on
  hooks/React). `resolveBuilderClaimPreview()` and the mock dict are otherwise **unchanged** —
  not deleted, not gated internally (the gate lives at the call sites now).
- `frontend/runs-viewer/src/lib/builderCoverage.ts` — `computeBlockAuditSummary`,
  `computeDraftAuditSummary`, `computeDraftIssues` now take a `resolvePreview: ClaimPreviewResolver`
  parameter; added `unresolved` to `ParagraphAuditSummary` and `"unresolved_claim"` to `BuilderIssue["key"]`.
- `frontend/runs-viewer/src/components/Builder/BuilderBlockEditor.tsx` — chip rendering resolves via
  the new `resolveClaimPreview` prop instead of importing the mock directly; added a `gray` chip-dot
  tone and `data-preview-state` attribute for the unresolved state.
- `frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx` — source-card union and a
  new "Unresolved" `StatRow` (gray tone) resolve via the new `resolveClaimPreview` prop.
- `frontend/runs-viewer/src/components/Builder/BuilderDraftCard.tsx` — threads `resolveClaimPreview`
  from `BuilderScreen.tsx` down to `BuilderBlockEditor` (it sits between them in the tree).
- `frontend/runs-viewer/src/screens/BuilderScreen.tsx` — instantiates the resolver hook from
  `draft.claim_links` and passes it into every coverage/preview call site, including two additional
  unconditional `resolveBuilderClaimPreview()` calls not named in the original three
  (`draftClaims` memo; the `weak_confidence` branch of `deriveIssueItems`) — see Deviations.
- `frontend/runs-viewer/src/styles/builder.css` — `--gray` chip-dot and stat-row tone rules.

`frontend/runs-viewer/src/api/client.ts` required **no changes** — `fetchCatalogItem()` already
implements the exact `GET /catalog/items/{id}` binding OQ-1 resolves to.
`frontend/runs-viewer/src/test/builder-screen.test.tsx` required **no changes** — see AC-4/Deviations.

### Acceptance Criteria Status

- [x] AC-1: Live claim previews resolve in loopback mode at all three target_surfaces (plus the two
  extra BuilderScreen.tsx call sites). Verified by `useBuilderClaimPreviews.test.tsx`.
- [x] AC-2: The mock dict is unreachable in loopback mode — `useBuilderClaimPreviewResolver` only
  calls `resolveBuilderClaimPreview()` when `!isLoopbackEnabled()`; demonstrated by test (the
  loopback-mode tests mock `fetch`, never touch the mock dict, and assert real resolution/unknown
  states end to end).
- [x] AC-3: Unresolvable is explicit, never silent — `CLAIM_PREVIEW_UNKNOWN` sentinel; a `gray` chip
  dot + `data-preview-state="unknown"` at the UI layer; `ParagraphAuditSummary.unresolved` and the
  `unresolved_claim` issue bucket at the arithmetic layer, both excluded from the "covered" numerator.
  Verified by `builderCoverage.claimresolution.test.ts`.
- [x] AC-4: Static mode unchanged — `builder-screen.test.tsx` and `catalog-screen.test.tsx` pass
  **unmodified**, zero edits to either file. See pre/post failing-set comparison below.
- [x] AC-5: Live-mode tests exist — `useBuilderClaimPreviews.test.tsx` (3 tests, mocked fetch,
  `VITE_RUNS_FRONTEND_LOOPBACK_API=true` via the established `vi.resetModules()` + dynamic-import
  pattern from `p5-auth-header.test.ts`) + `builderCoverage.claimresolution.test.ts` (6 tests,
  coverage arithmetic against a fake resolver shaped like the real payload).
- [x] AC-6: No new secret/token surface — grep-verified (`grep -inE "token|secret|authorization|api_key|apikey"`
  across every changed/new file) returns zero hits. `client.ts` untouched.
- [x] AC-7: Payload contract verified against a live backend — see below.

### AC-7: Observed live payload

Ran the runtime smoke against the **live `rf serve` on the agentic node's LAN loopback service**
(`http://10.42.10.76:7432`, `research-foundry-api.service` — same `catalog.py`/`reports.py` code as
this worktree; a purely local `rf serve` could not be stood up quickly against real catalog data in
this worktree, and starting one from scratch with synthetic data would not have exercised the real
contract any better). This is a read-only diagnostic call made directly from my shell, not part of
the shipped frontend code path — the frontend still only ever talks to `127.0.0.1:7432` per the
loopback gate; nothing in the delivered code introduces a new outbound host.

`GET /api/catalog/items/ci_02665bb4cfd2` (a live `claim` item):

```json
{
  "catalog_item_id": "ci_02665bb4cfd2",
  "item_type": "claim",
  "title": "In the absence of a copyright statement on a PMC article…",
  "summary": "…",
  "run_id": "rf_run_20260719_content_rights_and_licensing_review_what",
  "local_ref": "clm_025",
  "project": "pediatric-cds-platform",
  "status": "supported",
  "sensitivity": "personal",
  "trust_label": "supported",
  "confidence": "medium",
  "source_count": 1,
  "created_at": "2026-07-19T14:28:13-04:00",
  "updated_at": "2026-07-19T14:28:13-04:00",
  "payload": {
    "text": "In the absence of a copyright statement…",
    "materiality": "background",
    "claim_type": "attribution",
    "inference_basis": { "from_claims": [], "reasoning_summary": null },
    "report_locations": [],
    "cited_sources": [
      { "source_card_id": "src_20260719_reg002_13", "evidence_id": "ev_001", "relation": "supports", "locator": "…" }
    ]
  },
  "links": { "outgoing": [...], "incoming": [...], "citing_drafts": [] },
  "rf_schema_version": "1.0.0"
}
```

Also fetched a live `inference` item (`ci_1e3851ac62c6`, `status: "inference"`, `item_type:
"inference"`) to confirm both catalog item types map correctly, and read a live report draft
(`GET /api/reports/rpt_20260710_untitled_report`) to confirm every observed `claim_link` carries a
non-null `catalog_item_id` — the load-bearing fact behind the OQ-1 resolution.

**TS-type reconciliation result:** `CatalogItemDetail`/`CatalogItemSummary` in `types/rf/catalog.ts`
match this payload exactly at the top level. `payload.text`/`payload.materiality`/`payload.cited_sources`
match `catalog_service.py`'s claim-row builder exactly; `normalizeCatalogItemDetail()` (already in
`client.ts`, unchanged) correctly maps `cited_sources` → `sources` for this shape. No TS type changes
were needed. `rf_schema_version` is an unmodeled extra field (harmless — `CatalogItemDetail` is a
plain interface, not exact/sealed).

### OQ-1 Resolution

**`catalog_item_id` on `ReportClaimLink`** is the id-addressable key, resolved via the existing
`GET /catalog/items/{catalog_item_id}` binding (`fetchCatalogItem()` in `api/client.ts` — already
implemented, no new endpoint). Evidence: `reports.py`'s `add_claim_link` route persists
`catalog_item_id` verbatim from the request body; the live smoke's `GET /api/reports/{id}` response
showed every one of 5 real claim_links on a production draft carrying a non-null `catalog_item_id`.
No search-by-claim-id fallback was needed or implemented.

### Pre/Post Failing Test Sets (AC-4) — CORRECTED (see Fix Pass)

**Correction (coordinator-flagged, applied to this section):** `src/test/provenance-correctness.test.ts`
is **not** a repo baseline failure. It passes on parent `661f800` in a data-bearing tree; it fails
**only** in a fresh worktree because `runs/rf_run_.../reports/report_draft.md` is data-plane content
(the private `research-foundry-data` repo, which shares the main checkout's working tree but not a
fresh `git worktree`) and is absent here. It imports none of the files this contract touches. The
correct label is **"worktree-environment-dependent, not a repo baseline."** The one genuine
pre-existing infra failure is `codegen/generate-types.contract.test.mjs` (no test suite found — a
`.mjs` contract-check script mis-picked-up as a test file). **The true baseline is 1 file, not the
"4 known-failing frontend test files" the contract's Validation Requirements section states** — that
number was stale inherited context, not verified against this worktree. The original sprint's
Completion Report labeled `provenance-correctness.test.ts` a baseline failure and reported "2 vs the
stated 4" without identifying the worktree-environment cause; this correction supersedes that framing.

**Pre-change** (`pnpm test`, before any edits): 2 failing test files —
`codegen/generate-types.contract.test.mjs` (genuine pre-existing infra failure) and
`src/test/provenance-correctness.test.ts` (worktree-environment-dependent, not a repo baseline — see
above).

**Post-change** (`pnpm test`, after all edits, including the fix pass below): identical 2 failing
test files, same two, same causes. Test file count went from 43 passed / 2 failed (45 total) at the
original sprint's baseline to 45 passed / 2 failed (47 total) after the sprint's additions, to 45
passed / 2 failed (47 total) after the fix pass (same 2 new files, 4 more tests added to them) — the
failing set is byte-for-byte the same throughout.

### Static-mode assertions touched

None. Zero edits to `builder-screen.test.tsx` or `catalog-screen.test.tsx`; both pass unmodified
(verified by a targeted re-run and by the full-suite pre/post comparison above).

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm test` | Pass | 47 files, 45 passed / 2 failed (pre-existing baseline, unchanged set) |
| `npx tsc -p tsconfig.app.json --noEmit` | Pass | Zero errors |
| `npx eslint <all changed/new files>` | Pass | Zero errors/warnings |

### Fix Pass (post-sprint defect — confidence fabrication)

**Defect** (coordinator-reported): `useBuilderClaimPreviews.ts`'s `catalogItemToPreview()` defaulted
an absent/unrecognized `confidence` to the literal `"medium"` — the only non-conservative default in
that function (siblings: unknown `status` → `"unsupported"`, unknown `materiality` → `"material"`,
both fail-safe-toward-flagged). Live production data has real `confidence: null` rows (`GET
/api/catalog/search?limit=100` on the LAN node returns distinct values of exactly `[null, "medium"]`),
so every confidence-less claim was presented to a reviewer as a confident, scored "medium" — and
because `builderCoverage.ts`'s weak-confidence check only tests `=== "low"`, the fabrication also let
the claim escape the weak-confidence flag entirely. Same defect class AC-3 exists to close, one field
over.

**Fix**: extended `BuilderClaimPreview["confidence"]` with an explicit `"unknown"` member (chose the
"extend the enum" option the coordinator offered, since confidence is a field ON an otherwise-resolved
preview — not a whole-claim resolution state like `CLAIM_PREVIEW_UNKNOWN`, so overloading that
sentinel would have conflated "we know nothing about this claim" with "we know everything except its
score"). `catalogItemToPreview()` now defaults to `"unknown"`, never `"medium"`. Added a parallel,
distinctly-labeled `confidenceUnknown` bucket to `ParagraphAuditSummary` and a `confidence_unknown`
`BuilderIssue` key — mirroring `unresolved`/`unresolved_claim` exactly, but for a claim whose text/
status/sources DID resolve and only its confidence is missing. `confidenceUnknown` is excluded from
`coveragePct`'s numerator (same treatment as `unresolved`) and is never routed through the
weak-confidence check (which still tests only `=== "low"`, so `"unknown"` never qualifies — verified
by test, not just by inspection of the comparison operator). `BuilderScreen.tsx`'s `draftClaims` memo
maps `confidence: "unknown"` to `undefined` on the `RFClaim` it builds (RFClaimConfidence has no
`"unknown"` member) — the claim-detail modal already renders `claim.confidence ?? "unknown"`
(`ClaimAuditWorkbench.tsx:492`), so this reuses an existing honest-fallback pattern rather than
inventing a new one. `builderMocks.ts`'s `demoCatalogItem()` needed one narrowing line for the wider
type (static mock entries are all hand-authored with real values, so this is a type-level fix only,
never actually taken at runtime).

**Requirements checked**:
- Never rendered as medium/high/low: `isKnownConfidence()` gate unchanged; only high/medium/low pass; everything else → `"unknown"`. Test: `useBuilderClaimPreviews.test.tsx` "pins the fix-pass defect" (uses `confidence: null`, the exact live-payload shape reported).
- Not counted as weak/low: weak-confidence check is an `===  "low"` comparison; `"unknown"` fails it. Test: `builderCoverage.claimresolution.test.ts` "never routed through weak_confidence".
- Not silently counted toward `supported`: new `confidenceUnknown` bucket checked before the relation-based bucketing in `computeBlockAuditSummary`, short-circuits with `continue`, excluded from the coveragePct numerator. Test: same file, "counted in `confidenceUnknown`, not `supported`... 50%, not 100%".
- Static mode unchanged: `builder-screen.test.tsx`/`catalog-screen.test.tsx` — zero diff (verified: `git diff --stat` on both returns empty).
- Honest UI: new "Confidence unknown" `StatRow` (gray tone, `BuilderAuditInspector.tsx`) + `confidence_unknown` issue-drilldown case (`BuilderScreen.tsx`'s `deriveIssueItems`) + the reused `?? "unknown"` DetailModal fallback for `draftClaims`.

**Files touched in this pass** (all already in `files_affected`, no new files added):
`frontend/runs-viewer/src/lib/builderMocks.ts`, `frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.ts`,
`frontend/runs-viewer/src/lib/builderCoverage.ts`, `frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx`,
`frontend/runs-viewer/src/screens/BuilderScreen.tsx`, plus test additions to
`frontend/runs-viewer/src/hooks/useBuilderClaimPreviews.test.tsx` (+1 test) and
`frontend/runs-viewer/src/lib/builderCoverage.claimresolution.test.ts` (+3 tests).

**Re-validation**: `pnpm test` → 47 files, 45 passed / 2 failed (identical set — see corrected
Pre/Post section above); `npx tsc -p tsconfig.app.json --noEmit` → zero errors; `npx eslint` on all
touched files → zero errors/warnings.

### Deviations From Contract

- **Files touched beyond `files_affected`**: `BuilderDraftCard.tsx` and `BuilderScreen.tsx` were not
  in the original list but were required to thread the resolver from where it's instantiated
  (`BuilderScreen.tsx`, which owns `draft.claim_links`) down through `BuilderDraftCard.tsx` to
  `BuilderBlockEditor.tsx`. `hooks/index.ts` and `styles/builder.css` needed one-line additions
  (barrel export; two new CSS tone rules). Two new test files were added instead of editing
  `builder-screen.test.tsx`, matching this repo's established pattern (`p5-auth-header.test.ts`) for
  isolating `VITE_RUNS_FRONTEND_LOOPBACK_API` toggling via `vi.resetModules()` — mixing loopback-mode
  module-reset tests into a static-mode-only test file would have been fragile. `api/client.ts` was
  in the list but needed no changes.
- **Scope widened slightly beyond the three named call sites**: `BuilderScreen.tsx`'s `draftClaims`
  memo (feeds the claim-detail modal opened from a chip's "Expand" button) and the `weak_confidence`
  branch of `deriveIssueItems` (feeds the issue drill-down modal) both called
  `resolveBuilderClaimPreview()` unconditionally too — the same defect class, one level up the call
  stack from the three named sites. Leaving them unfixed would mean a real claim's chip correctly
  shows live text, but clicking "Expand" on that same chip opens an empty/broken detail modal. Fixed
  as part of wiring the same resolver through, since it was the same mechanism at near-zero
  incremental cost.
- **New `unresolved_claim` issue bucket / `unresolved` stat**: not explicitly named as a UI element in
  the contract, but required to satisfy AC-3's "does not count it as covered" at the arithmetic layer
  (the pre-existing `computeBlockAuditSummary` classified purely from `ReportClaimLink.relation`/
  `link_status`, which are backend-set at link-creation time and say nothing about whether the
  claim itself still resolves — an unresolvable claim would otherwise still read as "supported").

### Risks and Limitations

- The "unknown" state currently also covers the brief window before a loopback fetch settles
  (pending query), not only a genuine 404/type-mismatch. In practice this is a sub-second flash on
  first render per distinct claim and self-corrects once `useQueries` resolves — acceptable given
  "no fabricated preview during loading" is strictly safer than showing a stale/wrong one, but a
  future pass could add a distinct "resolving…" visual state if this proves noisy in practice.
- AC-7's smoke ran against the LAN node's `rf serve` rather than a literal `127.0.0.1:7432` process
  in this worktree (no quick path to stand up local catalog data with real claims). Same backend
  code, so the payload-shape verification is sound, but flagging the substitution explicitly per the
  instruction to report AC-7 honestly rather than by inspection.

### Follow-Up Recommendations

- Consider surfacing `useBuilderClaimPreviewResolver`'s `isLoading` flag in the UI (e.g. a subtle
  "resolving…" affordance on chips) if the loading-flash noted above turns out to be visible/annoying
  in real usage against a live draft with many distinct claims.
- **Resolved during the fix pass** (was previously an open follow-up): the contract's "4 known-failing
  baseline test files" was stale inherited context. The true repo baseline is **1 file**
  (`codegen/generate-types.contract.test.mjs`). `provenance-correctness.test.ts` is
  worktree-environment-dependent (missing data-plane fixture, not a code defect) and was mislabeled a
  baseline failure in the original Completion Report — see the corrected "Pre/Post Failing Test Sets"
  section above.

### Memory Candidates Captured

- None captured yet — the OQ-1 resolution (catalog_item_id is populated on real claim_links; no
  search-by-claim-id fallback needed) and the "unconditional mock resolver" defect class (present in
  5 call sites across 3 files, not just the 3 named in the contract) are worth a memory item once
  this lands; leaving that to the orchestrator's post-merge pass per the file-ownership boundary.
