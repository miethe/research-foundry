---
title: "Plan Completion: Runs Viewer — Live Loopback API + Gated LAN Exposure"
doc_type: report
report_category: completion
schema_version: 2
status: completed
created: 2026-06-22
updated: 2026-06-22
feature_slug: runs-loopback-api
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
findings_doc_ref: .claude/findings/runs-loopback-api-findings.md
owner: nick
---

# Plan Completion Report — runs-loopback-api-v1

**Outcome:** APPROVED. All 7 phases sealed; `task-completion-validator` end-to-end gate PASSED.
**Tier:** 2 (13 pts). **Execution:** wave-driven, single worktree (`worktree-runs-loopback-api-v1`),
squash-merged to `main`.

## Per-wave summary

| Wave | Phases | Owner(s) | Isolation | Result |
|------|--------|----------|-----------|--------|
| 1 | P1 API Foundation | python-backend-engineer | shared (single worktree) | ✅ app factory, `[serve]` extra, `rf serve` |
| 2 | P2 ∥ P3 Endpoints / Config | python-backend-engineer ×2 (parallel, file-disjoint) | shared | ✅ 5 endpoints via export_service; viewer.* config (7432) |
| 3 | P4 Auth & LAN | python-backend-engineer | shared* | ✅ token mw + allowlist + fail-closed bind |
| 4 | P5 Frontend | ui-engineer | shared | ✅ loopbackGet auth header; tsc clean; 519 FE tests |
| 5 | P6 Tests | python-backend-engineer | shared | ✅ 34/34 serve tests (TEST-006 parity, TEST-008 fail-closed) |
| 6 | P7 Deploy & Docs | changelog-generator + documentation-writer + python-backend-engineer (parallel) | shared | ✅ CHANGELOG, ADR, README, systemd, 2 spec promotions |

\* P4 declared `isolation: worktree` in the plan; per the operator instruction to run the whole job
in one worktree, phase isolation was `none` (the entire job was already isolated). P4 still received
single-owner treatment + a mandatory `senior-code-reviewer` pass + orchestrator behavioral verification.

## Reviewer gates

- **P4 security gate:** `senior-code-reviewer` → **APPROVED** (all 7 security invariants verified in
  code; adversarial checks on timing-safety, allowlist None-handling, Bearer casing, CORS credentials).
  `karen` checkpoint was dispatched but returned only idle notifications (no verdict delivered);
  substituted by direct orchestrator behavioral verification (token 401/401/200, /health bypass,
  auth_mode=none no-op, allowlist 403, fail-closed bind ×3) — all PASS.
- **Feature gate (Tier 2):** `task-completion-validator` → **APPROVED**. Independent re-run: 34/34 serve
  tests, TEST-006 + TEST-008 confirmed, tsc clean, security spot-check clean, only the 4 documented
  pre-existing failures in the full suite.

## Validation (final, integrated with current main `20b56c7`)

- `uv run --extra serve --extra dev pytest tests/test_serve_*.py` → **34 passed**.
- Full suite → **4 failed, 705 passed**; the 4 failures are pre-existing point-level redaction tests
  (`test_export_service.py`, `test_sensitivity_redaction.py`), confirmed identical on base `03c0468`
  and out of this plan's scope (see findings FIND-01).
- `npx tsc --noEmit` (runs-viewer) clean; `p5-auth-header` vitest 4/4.
- Core-import isolation: `import research_foundry` does not import fastapi.

## Deferred items (promoted into design specs)

- DEF-01 mTLS, DEF-02 SSH-tunnel → annotated in `docs/project_plans/design-specs/runs-auth-lan.md` (`## Deferred (v2)`).
- DEF-03 filesystem-watch hot-reload → annotated in `docs/project_plans/design-specs/runs-loopback-api.md`.
Both specs promoted (`maturity: promoted`, `prd_ref` set).

## Findings / caveats

- **FIND-01 (pre-existing, out of scope):** `export_service` under-redacts at the *point* level
  (4 failing unit tests, pre-existing on base). The loopback API achieves parity with the existing
  static-export path; it neither introduces nor worsens the bug. Recommend a separate `export_service`
  redaction fix. See `.claude/findings/runs-loopback-api-findings.md`.
- **FIND-02 (advisory):** operator-supplied CORS lists containing a bare `*` pass through; harden later.
- **P5-002 live browser smoke deferred-to-manual** (no live server in the isolated bg env); build-level
  verification + contract tests + documented manual steps substitute. Server side fully covered by P6.

## Scope deviations

- Router relocated `api/runs.py` → `api/routers/runs.py` in P2 to match the plan's `files_affected`
  and the `api/middleware/` layout (P1 stub path corrected).
- CORS config key reconciled: `app.py` now uses the canonical `config.viewer_cors_origins()` (P1 had
  used an ad-hoc `api_cors_origins`; folded into P4).
No unexplained scope creep (validator confirmed).
