# Plan Completion Report — runs-context-panels-v1 (FR-14)

**Status**: COMPLETED — karen feature-end gate PASS. Sealed for squash-merge to `main`.
**Date**: 2026-06-24
**Branch**: `feat/runs-context-panels-v1` (worktree, off local HEAD `b1e3dfa`)
**Execution**: `/dev:execute-plan` — direct Opus wave-orchestration with ICA delegation for bounded mechanical waves.

## Per-wave summary

| Wave | Phase | What landed | Isolation | Gate verdicts |
|------|-------|-------------|-----------|---------------|
| 1 | P1 — Schema & Contract | `EXPORT_SCHEMA_VERSION` 1.2→1.3; `_context_summary()` extended to the 4-key shape (research_brief_md + upstream_entities as null placeholders); schema-doc §9 stub; 3 backward-compat tests. TS `RFRunContextSummary` already existed (no-op). | shared (worktree) | frozen-schema governance **APPROVED**; task-completion **APPROVED** |
| 2 | P2 (ICA) ∥ P3-scaffold | P2: populate research_brief_md + upstream_entities, null-fill semantics, `_redact_str_values()` pass over context.* (reuses threshold model), structured stderr; +13 BE tests. P3-scaffold: `useCollapseState` hook + `ContextPane` (4 collapsible sections) + swarm→context tab swap + schema guard. | shared | serialization-barrier (P2-005) keys 1:1 ✓; task-completion **APPROVED** |
| 3 | P3 — FE Context Panels | OQ-3 `SwarmPlanTree`+`SwarmPlanSubTree` (2-level, depth-cap 3, "Show raw" escape hatch); RoutingDecisionSection cost/budget/sensitivity; ReportRenderer brief (frontmatter strip); offline-safe Upstream badges; 38 FE tests (FE-001..006); fixtures→schema 1.3; TEST-SMOKE (populated + pre-1.3 + offline build). | shared | karen **mid-feature PASS**; task-completion **APPROVED** |
| 4 | P4 — Tests, Docs & Validation | P4-001 (ICA): production-threshold pass-through self-doc test. Schema-doc finalized; CHANGELOG FR-14 entry; DFR-001 lazy-load v2 design spec; plan frontmatter finalized. | shared | karen **feature-end PASS** |

## Commit history (branch)
- `c732b53` P1 schema 1.3 shape-freeze
- `dc8d222` P2 export wiring + redaction & P3 Context-tab scaffold
- `53a9b92` P3 panels complete — OQ-3 swarm tree, FE tests, smoke
- `79a6b02` P4 docs, governance test & plan finalize

## Final validation (authoritative, in-session)
- Backend: `pytest tests/unit/test_export_service.py tests/integration/test_export_round_trip.py` → **101 passed, 1 failed**. The single failure (`test_default_public_threshold_redacts_personal_and_above`) is **pre-existing on main** (claim-quote redaction vs the distribution `foundry.yaml client_sensitive` threshold; unrelated to FR-14).
- Frontend: `tsc -b --noEmit` clean; `pnpm test` **614 passed / 0 failed** (25 files); `pnpm build` offline static build **succeeds**.

## Key reconciliations vs the as-written plan (all evidence-backed; P3 approach user-approved)
1. **Plan paths were wrong.** Real paths: backend `services/export_service.py` (dict-based, no `run_export.py` dataclass); FE `frontend/runs-viewer/src/...`. See `ground-truth-correction.md`.
2. **Feature was ~60% pre-shipped.** TS context types (`RFRunContextSummary`) already existed; `SwarmPane` already rendered routing+swarm. **User approved the "reconcile / extend existing" approach**: one consolidated "Context" tab with 4 collapsible sections (reusing existing cards + ReportRenderer + new tree), NOT 4 standalone panels.
3. **`_context_summary()` extended, not duplicated** (plan's `_build_context()` was the same function).

## Governance note (redaction)
At the production threshold (`foundry.yaml viewer.sensitivity_threshold: client_sensitive`, rank 3), `work_sensitive` (rank 2) context content passes through **unredacted** — the operator's deliberate config choice. Now self-documented by `test_context_work_sensitive_not_redacted_at_production_threshold`.

## Deviations / deferrals
- **Upstream-entities reachability ping deferred** (static badges, zero network calls) to preserve the offline-static-SPA invariant. AC P2-R4 ("never blocks render") fully met; online-navigability is the only deferred bit. Accepted by both karen gates.
- **DFR-001 lazy-load via loopback API** deferred to v2 by OQ-1; design spec authored at `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md` (maturity: shaping).

## Follow-ups (non-blocking, out of FR-14 scope)
- `SwarmPane.tsx` is now unwired (the Context tab replaced its RunDetail usage). Candidate for deletion in a future cleanup; left in place to avoid touching `SwarmScreen` exports out-of-scope.
- Pre-existing `test_default_public_threshold_redacts_personal_and_above` failure: a test/config mismatch (test expects `public` default; distribution `foundry.yaml` pins `client_sensitive`). Predates FR-14; worth a separate fix.
- Pre-existing >500 KB vite chunk-size warning (unrelated).
