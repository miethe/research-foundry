---
title: "Feature Contract: Runs-Viewer Builder — Live Claim Previews in Loopback Mode"
schema_version: 2
doc_type: feature_contract
it_schema: 1
description: "Make the Report Builder's claim previews, audit inspector, and coverage computation read live RF catalog data when the loopback gate is on, replacing an unconditional 6-id hardcoded mock lookup that silently returns null (and mis-scores coverage) for every real claim. Static-mode behavior is preserved unchanged."
status: draft
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
commit_refs: []
pr_refs: []
files_affected:
  - frontend/runs-viewer/src/lib/builderMocks.ts
  - frontend/runs-viewer/src/lib/builderCoverage.ts
  - frontend/runs-viewer/src/components/Builder/BuilderBlockEditor.tsx
  - frontend/runs-viewer/src/components/Builder/BuilderAuditInspector.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/test/builder-screen.test.tsx
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
