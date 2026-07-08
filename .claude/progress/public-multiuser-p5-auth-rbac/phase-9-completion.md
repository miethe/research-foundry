## Phase 9 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 7 phase-9 tasks independently verified (validator ran the regression suite, tsc, eslint, and cross-referenced runbook links itself rather than trusting the progress file); zero blocking findings
**REVIEW-001 must-fix**: CLOSED — audit-health gate wired into exposure paths (see "REVIEW-001 Remediation" section below)
**Isolation**: worktree
**Branch**: worktree-agent-a59c116617e21d3f8
**Worktree path**: .claude/worktrees/agent-a59c116617e21d3f8

---

### Files Changed

**New files:**
- `tests/integration/test_p5_regression_suite.py` (1188 lines) — provider×mode regression suite: sensitivity, catalog-visibility, job-permission/credential-firewall (FULL_COMPOSITION mode — P4 confirmed shipped), writeback-approval, audit-exposure-gate cross-check, RBAC-006 CLI-mutation-surface re-confirmation
- `frontend/runs-viewer/e2e/p5-auth-rbac.spec.ts` (392 lines) — login-per-provider, role-bounded catalog/builder actions, sharing scenario; static mode always runs, live mode explicitly `.skip()`'d with documented reason (no RF API server / no live Clerk tenant in this environment)
- `frontend/runs-viewer/tsconfig.e2e.json` — standalone tsconfig for `e2e/` (types: node + @playwright/test); NOT wired into root `tsconfig.json` references, so it does not affect `pnpm run build`
- `docs/dev/architecture/auth-rbac-operator-guide.md` — 5-role model, capability matrix, Clerk enablement prerequisites, audit/rate-limit config location
- `docs/dev/architecture/workspace-migration-runbook.md` — operator-facing dry-run/enforce/rollback procedure, cross-references Phase 3's internal rollback runbook
- `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` — FU-2 design-spec, `maturity: idea`, `open_questions` includes on-prem-IdP-consumer promotion trigger
- `.claude/evidence/phase-9/auth-context-{clerk,local-static,none}.png` — AC-5 runtime-smoke screenshots (R-P4 gate for P5.8's UI surfaces)

**Modified files:**
- `frontend/runs-viewer/e2e/w1-claim-audit.spec.ts` — extended (diff-only) for authenticated context + AC-5a no-chrome guard; also fixes 2 pre-existing test bugs surfaced during the run (selectClaim toggle-off behavior from `fae65aa`; unscoped SourceCard locator resolving to sidebar copy instead of modal)
- `frontend/runs-viewer/e2e/w3-report-chip-navigation.spec.ts` — extended (diff-only) for authenticated context + AC-5a no-chrome guard
- `frontend/runs-viewer/tsconfig.app.json` — added `exclude` for vitest test files (confirmed necessary: `tsc -b` fails on `src/test/p5-auth-header.test.ts` type errors without it)
- `foundry.yaml` — extended `auth.provider` comment block to document all 4 values (none/local_static/clerk/oidc) with fail-closed rationale, matching `viewer.sensitivity_threshold` density
- `CHANGELOG.md` — `[Unreleased]` entry summarizing the full P5 feature (Added: AuthProvider port, 5-role RBAC, workspace migration, audit log, rate limits, admin settings, fail-closed sharing, frontend auth-context; Security: RBAC route gating, credential-firewall composition; known-follow-up note on the audit-exposure-gate xfail finding)

---

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | TEST-001 | completed | python-backend-engineer |
| 1 | TEST-002 (drafted; budget-terminated mid-commit) | completed | python-backend-engineer |
| 1 | DOC-002 | completed | documentation-writer |
| 1 | DOC-003 | completed | documentation-writer |
| 1 | DOC-004 | completed | documentation-writer |
| 2 | DOC-001 | completed | changelog-generator |
| remediation | TEST-002 fixup (e2e tsconfig + typecheck + Playwright run + commit) | completed | python-backend-engineer |
| gate | REVIEW-001 | orchestrator-run (deferred to plan-level coordinator) | codex-gpt-5.5 (not dispatched by this phase) |
| gate | task-completion-validator | PASS | task-completion-validator |

**Note on TEST-002 delivery**: the initial dispatch was terminated mid-run by a team budget cap (`Current cost: 3210.32, Max budget: 3200.0`) after producing complete, on-disk spec files but before committing. Once budget was restored, a remediation dispatch: (a) diagnosed and fixed the e2e typecheck gap (neither existing tsconfig covered `e2e/`; `@types/node` was already a dependency — this was an `include`/`types` gap, not a missing package), (b) ran the full Playwright suite — **32 passed, 4 skipped** (skips are the documented live-mode limitation), (c) fixed 2 pre-existing test bugs in `w1-claim-audit.spec.ts` unrelated to this phase's scope, surfaced only because the extension exercised those code paths, (d) committed the complete scope with explicit `git add <path>` per file (no `-A`).

---

### Verification Performed

- **TEST-001**: `PYTHONPATH=<worktree>/src .venv/bin/python -m pytest tests/integration/test_p5_regression_suite.py` → 56 passed (validator's own count, run independently), 2 xfail. Existing suites (`test_cli_mutation_surface.py`, `test_sensitivity_redaction.py`, `test_export_service.py`) confirmed still green.
- **TEST-002**: `npx tsc -p tsconfig.e2e.json --noEmit` clean; `npx eslint` on all 3 spec files clean; Playwright run 32 passed / 4 skipped (documented). Screenshots visually inspected by validator — `none` and `local-static` show real rendered UI; `clerk` shows a blank lazy-load state consistent with "no live Clerk tenant" limitation (not a defect).
- **Known finding (not a blocker)**: 2 `xfail(strict=False)` tests in TEST-001 (`test_p5_regression_suite.py:975,1045`) document that P5.6 never actually wired `is_healthy_for_exposure()` (P5.5 AUDIT-004) into the sharing/publish-preview flow — the check exists but isn't called before exposure. This is the coordination-note gap flagged in both the P5.5 and P5.6 phase files, now confirmed and tracked. Surfaced in CHANGELOG's "Known follow-up" bullet. **Recommend this becomes a fast-follow task before/alongside REVIEW-001 triage** — it is exactly the class of finding REVIEW-001 is scoped to catch (AUDIT-004/P5.6 wiring), so the plan-level coordinator should treat it as a pre-confirmed REVIEW-001 finding rather than rediscovering it.
- **Mode-D boundary check**: `git show --stat` on all 7 phase commits confirmed scope limited to docs, `foundry.yaml` comments, test/e2e files, tsconfig, and PNG evidence. Zero production auth/RBAC/migration code changed. Zero `ccdash/events/*`, `runs/rf_run_*/*`, `.rf_state/*` files touched.

---

### REVIEW-001 Remediation (post-hoc, plan-wide Codex adversarial pass)

The plan-level coordinator ran REVIEW-001 (Codex, read-only) after this phase's initial completion and returned one must-fix, exactly matching the finding this phase's own regression suite had already surfaced via 2 documented `xfail(strict=False)` tests (see "Verification Performed" above). The coordinator routed the fix to this phase-owner as a fail-closed **tightening** (adds a denial gate, does not weaken anything) — safe to implement without a fresh Mode-D gate.

**Fix delivered** (dispatched to `python-backend-engineer`, commits `4882436` + `3bff1b6`):
- Wired `audit_service.is_healthy_for_exposure(paths)` into **three** exposure points in `src/research_foundry/api/routers/reports.py`: `publish_preview()` (after the success audit event, before the final 200 return), `create_share_link()` (before minting a token), and `resolve_share_link()` (before returning the shared draft — the GET endpoint the regression tests actually exercise, discovered by the implementer while verifying the two xfail tests against real code rather than assuming the delegation prompt's literal line numbers). Each returns `HTTPException(503, "Audit log unavailable")` when audit health is degraded.
- Invariants preserved: the publish-preview sensitivity 422 gate stays absolute/role-independent (untouched); `rbac_enforcement=disabled` does not bypass the new 503 gate (unconditional check, independent of the RBAC-toggle branch); `record_event()` calls remain fail-open and unmodified.
- **Tests**: flipped both `xfail(strict=False)` tests in `tests/integration/test_p5_regression_suite.py` to real passing assertions (also fixed a latent bug in one — it pointed at a draft that was never created via the API, which would have 404'd before reaching any gate); added `test_healthy_audit_leaves_share_resolution_and_publish_preview_unaffected` to prove the gate is conditional, not an unconditional deny.
- **Docs**: `CHANGELOG.md`'s `[Unreleased]` entry moved the item from "Known follow-up" into **Security** as FIXED, generic wording (no function names).
- **Validation**: `test_p5_regression_suite.py` → 57 passed, 0 xfail remaining. Full must-stay-green suite (`test_rbac*.py`, `test_rate_limit.py`, `test_admin_api.py`, `test_publish_preview_role_independence.py`, `test_share_token_auth_exemption.py`, `test_workspace_migration_service.py`) → 284 passed, 0 failures.
- Committed with explicit `git add <path>` per file (no `-A`); working tree clean; still on `worktree-agent-a59c116617e21d3f8`, not merged.

### Escalation Reason

N/A — no Mode-D trigger encountered (the audit-health fix is an additive fail-closed tightening, explicitly pre-cleared by the coordinator as safe).

### Follow-Up Recommendations

1. ~~**Audit-exposure-gate wiring gap**~~ — **RESOLVED** in REVIEW-001 remediation above (commits `4882436`/`3bff1b6`).
2. **Parent plan frontmatter**: `deferred_items_spec_refs` in `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md` needs `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` appended (DOC-004's flagged follow-up, explicitly out of this phase's scope).
3. **Plan-level karen end-of-feature sign-off** is still outstanding — coordinator-run, not part of this phase. (REVIEW-001 itself is now closed.)
4. Minor validator-flagged nits (non-blocking, pre-existing at initial PASS): unused local var in one monkeypatch test (`test_p5_regression_suite.py:1023`, may have shifted line numbers after the remediation edits).
