## Phase 6 Completion Note

**Status**: PASS
**Validator verdict**: PASS (cycle 2) — both cycle-1 issues resolved (X-RateLimit-Limit header added; evidence directory created)
**Karen public-exposure milestone verdict**: PASS (cycle 2) — all 3 cycle-1 security findings resolved (sensitivity gates on export/versions; auth.provider=none+non-loopback gate auditable; rate-limit `enabled` field truthful)
**Isolation**: worktree
**Branch**: main (worktree branch on local main @ 18b6c17)
**Worktree path**: .claude/worktrees/agent-a6225171c74590a59

---

### Files Changed

**New source/service files:**
- `src/research_foundry/api/middleware/rate_limit.py` — SlidingWindowRateLimiter + RateLimitMiddleware; X-RateLimit-Remaining/Limit/Reset + Retry-After headers; per-(user_id, route) keys; in-process; auth_mode=none exempt
- `src/research_foundry/api/routers/admin.py` — 6 admin endpoints matching P5.8 contract; `require_role` on all mutation routes; no credentials in auth-provider-status; `enabled` is startup-only; `/api/admin/rbac-status` read-only for all authenticated users
- `src/research_foundry/services/share_store.py` — Durable share-link store in `.rf_state/rbac.db`; token expiry + revocation enforced at resolve time

**Modified source files:**
- `src/research_foundry/config.py` — `auth_rate_limit_*` accessors; `AuthRbacEnforcement` enum; `resolve_rbac_enforced()` fail-closed (disabled+non-loopback raises ValueError)
- `src/research_foundry/api/app.py` — rate-limit middleware wired; admin router wired; `app.state.rbac_enforced` resolved at create time; NOTE comment pointing to `_validate_nonloopback_bind` for auth.provider=none+non-loopback gate
- `src/research_foundry/api/auth/rbac.py` — `require_role()` checks `app.state.rbac_enforced`; when False → passthrough
- `src/research_foundry/api/routers/reports.py` — `publish_preview` role-independence hardening; share-link endpoints (POST + GET); sensitivity gates added to `export_draft`, `list_versions`, `get_version` (karen fix)
- `src/research_foundry/services/rbac_store.py` — `list_workspace_members()`, `get_workspace()`, `update_member_role()`
- `src/research_foundry/api/middleware/__init__.py` — middleware registry updated
- `src/research_foundry/cli/__init__.py` — merged from cli.py (resolves cli.py vs cli/ package conflict; pyproject.toml entry point `research_foundry.cli:app` now resolves)
- `src/research_foundry/cli.py` — redirected/emptied (package conflict resolved)
- `foundry.yaml` — `auth.rate_limit` block documented; `auth.rbac_enforcement` documented; `enabled` STARTUP-ONLY comment added

**Frontend files:**
- `frontend/runs-viewer/src/components/AdminSettings/RbacStatusPanel.tsx` (NEW) — RBAC status read-only display; GATE-901 degradation
- `frontend/runs-viewer/src/screens/SettingsScreen.tsx` — RbacStatusPanel added as 5th admin panel
- `frontend/runs-viewer/src/api/client.ts` — `subscribeRateLimitState()` pub-sub; `getRbacStatus()`; reactive `_rateLimitState`; `Retry-After` parsing
- `frontend/runs-viewer/src/app/AppShell.tsx` — reactive `rateLimitState` (useState + useEffect + subscribe); badge only on 429+Retry-After

**Test files (new):**
- `tests/unit/test_rate_limit.py` — 22 tests (SW algorithm + middleware)
- `tests/unit/test_publish_preview_role_independence.py` — 10 tests (all 5 roles × sensitivity violation)
- `tests/integration/test_sharing_flow.py` — 13 tests (durable store, re-check at resolution, revocation)
- `tests/unit/test_admin_api.py` — role gating, no-secrets, round-trip, RBAC-status shape
- `tests/unit/test_rbac_enforcement_toggle.py` — 5 mandatory T5 scenarios (a–e) + 4 auth.provider=none+non-loopback tests (27 total)
- `tests/unit/test_cli_workspace_help.py` — smoke test: rf workspace migrate-dry-run --help exits 0
- `frontend/runs-viewer/src/test/p5-auth-header.test.ts` — GATE-900 3 new tests (absent headers, under-budget, 429+Retry-After)
- `frontend/runs-viewer/src/test/p5-admin-settings.test.tsx` — GATE-901: RbacStatusPanel positive + 4 disabled-state tests (per-panel independence)

**Test files (modified):**
- `tests/unit/test_rbac_route_sweep.py` — `_MANUALLY_GATED_ROUTES` exemption for publish-preview; count updated 14→15
- `tests/unit/test_cli_mutation_surface.py` — same `_MANUALLY_GATED_ROUTES` exemption

**Evidence files:**
- `.claude/evidence/phase-6/gate-900-evidence.md` — GATE-900 reactive path documentation + test inventory
- `.claude/evidence/phase-6/gate-901-evidence.md` — GATE-901 per-panel degradation documentation + testid contracts
- `.claude/evidence/phase-6/screenshot-waiver.md` — AC-5 visual evidence waiver; deferred to P5.9 Playwright spec

---

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | P5.6-T1, P5.6-T4, P5.6-CLI | completed | python-backend-engineer (×3 parallel) |
| 2 | P5.6-T2, P5.6-T5 | completed | python-backend-engineer (combined) |
| 3 | P5.6-T3, GATE-900, GATE-901 | completed | ui-engineer-enhanced |
| remediation-v1 | X-RateLimit-Limit header fix, evidence files | completed | python-backend-engineer (×2 parallel) |
| remediation-v2 | sensitivity gates (export/versions), auth.provider=none guard, rate-limit enabled truthfulness | completed | python-backend-engineer (×3 parallel) |

---

### Validator Gate Results

| Gate | Cycle | Verdict |
|------|-------|---------|
| task-completion-validator | 1 | FAIL — X-RateLimit-Limit header missing; evidence dir absent |
| task-completion-validator | 2 | PASS — both fixes confirmed; 22+33+2 spot-check tests pass |
| karen (public-exposure) | 1 | FAIL — export/versions sensitivity bypass; auth.provider=none gate not auditable; rate-limit `enabled` lie |
| karen (public-exposure) | 2 | PASS — all 3 required fixes confirmed; 71 tests pass |

---

### Delta Tasks (added during execution, not in original phase doc)

- **P5.6-T5**: RBAC enforcement toggle (`auth.rbac_enforcement: auto|disabled|enabled`); fail-closed on non-loopback; 5 mandatory test scenarios met
- **P5.6-CLI**: cli.py vs cli/ package conflict fix; `rf workspace migrate-dry-run --help` smoke test

---

### Test Coverage Summary

| Suite | Count | Status |
|-------|-------|--------|
| Python (pytest) — all | 736+ (before P5.6 additions) + ~90 new | all passing |
| Frontend (vitest) | 914/914 | PASS |
| TypeScript typecheck | 0 errors | PASS |
| test_rate_limit.py | 22/22 | PASS |
| test_rbac_enforcement_toggle.py | 27/27 | PASS |
| test_publish_preview_role_independence.py | 10/10 | PASS |
| test_sharing_flow.py | 13/13 | PASS |
| test_admin_api.py | 14/14 | PASS |
| test_cli_workspace_help.py | smoke | PASS |

---

### Escalation Reason

N/A — no Mode-D triggers encountered. All auth/RBAC changes were within the explicit phase-6 plan scope. Karen public-exposure fixes were in-scope remediations (sensitivity gate parity, startup-only documentation, auditable gate comment).

---

### Follow-Up Recommendations

1. **P5.9 E2E**: `p5-auth-rbac.spec.ts` Playwright suite must exercise rate-limit badge (positive path), share-link flow, and admin settings at ≥1440px — fulfills the screenshot-waiver.md visual evidence deferred here.
2. **AppShell badge dead-code cleanup**: `AppShell.tsx` rate-limit badge is now reactive but requires a live 429 from a rate-limited route to trigger. Consider a P5.9 integration test that intentionally fires a 429 to exercise the badge path.
3. **karen low-severity follow-ups** (not required for this phase merge):
   - `GET /admin/auth-provider-status` `details` field: sanitize exception class name from error messages
   - `GET /api/admin/rbac-status` open-to-authenticated: document as explicit design decision in ADR or foundry.yaml comment
4. **P5.4 ClerkShell shim**: `src/auth/hooks/useClerkAuth.ts` remains a stub. Replace with real P5.4 Clerk hook when that phase is confirmed.
