---
type: report
schema_version: 2
doc_type: report
report_category: plan-completion
feature_slug: wksp-304-workspace-isolation-enforcement
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
status: completed
created: 2026-07-09
updated: 2026-07-09
tier: 2
risk_level: high
reviewer_verdict: APPROVED
commit_refs: ["2208927","d179fd4","80ec586","3449b1c","1e93a37","caec975","53eb359","5418568","8bf9666","3d24b6d","eba75ab","c74e1cc"]
---

# WKSP-304 — Plan Completion Report

Row-level workspace isolation flipped from advisory logging to fail-closed, query-layer
enforcement behind the orthogonal `workspace_isolation_enforcement` flag. Executed via
`/dev:execute-plan` (wave-driven phase-owner orchestration, plain `Task()` workflow).

## Per-Wave Summary

| Wave | Phase | Isolation (actual) | Result | Reviewer |
|------|-------|--------------------|--------|----------|
| 1 | P1+P2 — config flag + fail-closed resolver + identity threading (6 routers) | on-branch `main` | ✅ | task-completion-validator PASS (1 remediation: reports.py verify_draft indirect builder_service reach) |
| 2 | P3 — query-layer `workspace_id` scoping (3 services) + JOIN/tombstone (AC-4) | on-branch `main` | ✅ | task-completion-validator PASS |
| 3 | P4 — enforcing flip + deny paths (Mode-D core) | on-branch `main` | ✅ | task-completion-validator PASS |
| 4 | P5 — enforcement regression matrix (79 tests) | on-branch `main` | ✅ | validator PASS after P5.5b unblock |
| 5 | P6 — docs/CHANGELOG/runbook + finalize | on-branch `main` | ✅ | **karen APPROVED** (end-of-feature) after remediation |

## Isolation Override (documented deviation)

Plan declared `isolation: worktree` for P3/P4. Executed **on-branch with per-wave
`.wave-N-checkpoint` rollback targets** instead: single-phase sequential waves give zero
parallelism benefit, this `src/`-layout editable install has documented worktree/PYTHONPATH
friction, and checkpoints give equivalent clean rollback. Consistent base with P1-2 (already on main).

## Mode-D Findings & Escalations

1. **P5.5b (self-deny bug, fixed autonomously — in-scope):** `create_draft` didn't thread
   identity → drafts got `workspace_id=None` → self-denied the legitimate owner under enforcement.
   Fixed (`5418568`); mirrors the `identity is None` short-circuit; single-operator byte-identical.
2. **P6 karen gate (cross-workspace READ LEAK — escalated to user):** `create_draft_from_run` /
   `create_draft_from_collection` unthreaded + unscoped `catalog_service.get_item()` leaked a
   foreign-workspace item. Revealed the P3 scoping enumeration was incomplete (the "100% coverage"
   gate passed against an under-enumerated set). **User chose bounded fix + deferral.** Fixed
   (`eba75ab`) with leak-closure regression tests; karen re-APPROVED.

## Security Invariants Verified

- `identity=None` single-operator short-circuit is structurally first (AC-6, Critical) — verified.
- Cross-workspace read → **404 + list-omit** (decision D5 locked; was pending gate).
- Cross-workspace mutation denied (AC-5); share tokens decoupled from workspace enforcement (fail-closed).
- Full suite: **914 passed, 1 xfailed, 0 failed**; single-operator baseline unmodified.
- Pre-existing 5-failure `tests/test_serve_api.py` cluster confirmed unrelated across P3/P4/P5.

## Deferred (tracked hard gate)

**DI-1 / OQ-4:** Full workspace-data-access completeness audit (ALL read/create/list/delete
service paths — the enumeration proved unreliable). **MUST close before any shared-store
multi-tenant deploy.** Not urgent: enforcement defaults to advisory and is not yet armed in prod.

## Merge / "squash to main"

Feature is fully integrated on `main` as a clean, conventional-commit per-phase series (12 commits).
No separate feature branch exists to squash-merge (on-branch execution). A literal 12→1 squash would
require rewriting shared `main` history — which now includes unrelated interleaved commits
(`8708373`, `a4abd4f` http-run-launch) from concurrent activity — so it was **not** performed
(git-workflow rule forbids destructive rewrites of shared branches). Left for explicit direction.

## Follow-ups

- **DI-1** completeness audit before multi-tenant deploy (hard gate).
- Push to origin is gated — not performed (no explicit request).
