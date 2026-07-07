## Phase 1 Completion Note

**Status**: PASS
**Validator verdict**: PASS — 30 tests green (post all remediations), all exit criteria met
**Isolation**: worktree
**Branch**: feat/public-multiuser-p5-auth-rbac-p1
**Worktree path**: .claude/worktrees/public-multiuser-p5-auth-rbac-p1
**Commits**: 2ad5067 (initial), d1cec68 (P1 legacy-token bypass), 1fcd95c (P2 serve-gate + malformed-token), 3f126ec (P1 root-cause override-ordering)

### Files Changed

| File | Change | Owner |
|------|--------|-------|
| `src/research_foundry/api/auth/__init__.py` | NEW — package marker | backend-architect |
| `src/research_foundry/api/auth/provider.py` | NEW — AuthIdentity + AuthProvider Protocol + registry | backend-architect |
| `src/research_foundry/api/auth/adapters/__init__.py` | NEW — package marker | backend-architect |
| `src/research_foundry/api/auth/adapters/local_static.py` | NEW — multi-token→role adapter with full-scan hmac | backend-architect |
| `src/research_foundry/api/auth/adapters/oidc.py` | NEW — Protocol-conformance stub (FU-2 seam; does not self-register) | backend-architect |
| `src/research_foundry/services/rbac_store.py` | NEW — durable RBAC store at .rf_state/rbac.db; additive-only schema | data-layer-expert |
| `src/research_foundry/paths.py` | MODIFIED — added rf_state + rbac_db properties | data-layer-expert |
| `src/research_foundry/api/middleware/auth.py` | MODIFIED — added AuthProviderMiddleware; TokenAuthMiddleware kept (deprecated comment) | backend-architect |
| `src/research_foundry/api/app.py` | MODIFIED — create_app uses auth.provider registry lookup | backend-architect |
| `src/research_foundry/config.py` | MODIFIED — auth_provider() + auth_local_static_tokens() accessors | backend-architect |
| `foundry.yaml` | MODIFIED — new auth: block with provider=none default | backend-architect |
| `tests/test_serve_auth.py` | MODIFIED — provider matrix, AUTH-900 absent-identity, rebuild-survival; migrated TestTokenAuth from viewer.auth_mode → auth.provider | backend-architect |

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | AUTH-101, AUTH-103 | completed | backend-architect, data-layer-expert |
| 2 | AUTH-102, AUTH-105 | completed | backend-architect (parallel — disjoint files) |
| 3 | AUTH-104 | completed | backend-architect |
| 4 | AUTH-900 | completed | backend-architect |
| 5 | AUTH-106 | completed | backend-architect |

### Test Results

```
30 passed, 0 failed, 1 warning  (17→18→24→30 across remediation cycles)
```

Tests cover:
- `TestTokenAuth`: existing tests migrated to `auth.provider: local_static`
- `TestNoAuthProviderAbsentIdentity`: AUTH-900 contract — None on no-provider path
- `TestProviderMatrix`: provider-parametrized valid/invalid/missing header + middleware-stack assertion for `none`
- `TestRbacStoreRebuildSurvival`: seeds membership, calls `catalog_service.rebuild_schema()`, asserts rbac row untouched

### Exit Criteria Verification

| Criterion | Status |
|-----------|--------|
| Provider swap works via config (no code change required) | PASS — TestTokenAuth + TestProviderMatrix fixtures confirm |
| AuthIdentity flows into request.state | PASS — probe route asserts user_id/workspace_id/roles populated |
| Durable store survives catalog.db rebuild (test) | PASS — TestRbacStoreRebuildSurvival passes; D2 path-inequality assertion guards regression |
| task-completion-validator sign-off | PASS |

### MUST-STAY Invariants Preserved

- `auth.provider="none"` / `auth_mode="none"` no-op: zero middleware added when provider not configured
- No external provider secrets, no JWKS, no Clerk adapter wiring
- No Mode D triggers hit (no schema migration, no auth enforcement, no data deletion)
- Serialization barriers owned this phase (foundry.yaml, config.py, app.py) — no other wave members

### Escalation Reason

N/A — phase completed without Mode D escalation.

### Non-Blocking Follow-Up for Phase 2

1. **Low**: Add `auth.provider: oidc` config-rejection test (validator finding) — one test case asserting `ValueError` on `config.auth_provider()` when `oidc` is set. Low effort, closes AUTH-105 testing gap.
2. **Design seam**: `if _provider_name == "local_static"` in `create_app` (line ~130) to re-initialize the registry entry with actual token configs. Acceptable at P5.1 scope; revisit when a second concrete adapter lands in P5.4.

---

### Remediation — Codex P1 (legacy token-auth bypass)

**Reported by**: Codex cross-review post-commit
**Commit**: d1cec68
**Severity**: P1 auth bypass

**Defect**: After AUTH-104 wired `create_app` to read `auth.provider` instead of `viewer.auth_mode`, existing deployments using `viewer.auth_mode: token` without the new `foundry.auth` block silently lost all auth middleware. `create_app` defaulted `auth.provider` to `"none"` and added no middleware → endpoints the CLI reported as token-protected were exposed.

**Fix** (`src/research_foundry/api/app.py`):
- Added fail-closed legacy fallback `elif` branch in `create_app`: when `auth.provider == "none"` AND `config.viewer_auth_mode() == "token"`, construct a single-entry LocalStaticAuthProvider from `config.viewer_auth_token_env()` and install `AuthProviderMiddleware` — identical behavior to explicit `auth.provider: local_static`
- Emits `WARNING` deprecation log directing operators to migrate to `foundry.auth.provider: local_static`

**Invariants preserved**:
- `auth.provider="none"` + `viewer.auth_mode` absent/"none" → zero middleware (unchanged)
- Explicit `auth.provider: local_static` → unchanged
- No external secrets, no Clerk, no JWKS

**Regression test** added (`TestLegacyTokenAuthBackwardCompat`):
- Config with ONLY `viewer.auth_mode: token` (no `foundry.auth` block) → 401 without token, 200 with token
- Would have caught the regression before merge

**Final test count**: 18 passed, 0 failed (was 17 before fix)

---

### Remediation 2 — Codex P2 (serve-gate + malformed-token)

**Reported by**: Codex cross-review post P1 fix
**Commit**: 1fcd95c
**Severity**: P2 (no auth bypass, but breaks canonical deployment path)

**Defect P2-a — serve pre-bind gate ignores new provider** (`cli_commands.py`, `config.py`):
The non-loopback safety check only accepted `viewer.auth_mode == "token"`. Any deployment using the new canonical `auth.provider: local_static` was rejected at startup with a spurious "no auth configured" error — the exact multi-user LAN scenario P5 enables.

Fix:
- `config.py`: added `is_auth_enabled()` — True when `auth.provider != "none"` OR `viewer.auth_mode == "token"` (legacy kept)
- `cli_commands.py`: replaced inline check with `_validate_nonloopback_bind()` helper; validates that at least one `local_static` token env var resolves to a non-empty value before allowing non-loopback bind (fail-closed with actionable message)

Note: `cli_commands.py` is outside the original `files_affected`; included as direct remediation consequence of this phase's auth.provider introduction.

**Defect P2-b — malformed token entry → 500** (`local_static.py`, `config.py`):
Missing `user_id`/`workspace_id` in a token config entry caused `KeyError` → 500 on every authenticated request.

Fix (two layers):
- `local_static.py __init__`: startup validation loop raises `ValueError` with index+field message on any malformed entry (config typo surfaces at startup, not request time)
- `local_static.py authenticate()`: defensive match-time guard — malformed matched entry logs WARNING and returns `None` instead of raising `KeyError` (belt-and-suspenders)

**Tests added** (6 new → 24 total):
- `TestServeGateNewProvider`: `is_auth_enabled()` + non-loopback gate for `auth.provider=local_static` with/without token env set
- `TestLocalStaticMalformedConfig`: startup `ValueError` + match-time `None` (never 500)

**Final test count**: 24 passed, 0 failed

---

### Remediation 3 — Codex P1 (override-ordering, root-cause)

**Reported by**: Codex cross-review after Remediation 2
**Commit**: 3f126ec
**Severity**: P1 auth bypass (introduced by the P2 spot-patch, fixed by root-cause fix)

**Root Cause**:
The P2 serve-gate fix (Remediation 2) moved the safety gate logic to `_validate_nonloopback_bind()`, but the gate was still called on the PRE-OVERRIDE config. The serve command applied `--auth-mode` CLI overrides to `config.viewer` AFTER the gate ran. Exploit: `foundry.yaml: viewer.auth_mode: token` + `rf serve --bind-host 0.0.0.0 --auth-mode none` → gate sees token config (passes), override sets none, `create_app` installs no middleware, server binds non-loopback unauthenticated.

**Root-Cause Fix (not a spot-patch)** (`cli_commands.py`):
Resolved the effective auth configuration ONCE — moved all CLI override application (--auth-mode, sensitivity_threshold) BEFORE the non-loopback safety gate. Both the gate and `create_app` now consume the same already-mutated `config` object. There is exactly ONE source of truth for "is auth on for this serve invocation." No re-reading of foundry.yaml after override mutation.

**Architecture invariant enforced**:
```
Step 1: apply CLI overrides to config (mutate config.viewer)
Step 2: run non-loopback gate (reads fully-resolved config)
Step 3: create_app(config) — same resolved config
```

**6-case test matrix** (`TestServeOrderingFix`):

| Case | Config | CLI Override | Expected |
|------|--------|-------------|----------|
| 1 | auth_mode=token | none | gate PASSES |
| 2 | auth_mode=token | --auth-mode=none | gate FAILS (bypass closed) |
| 3 | no auth | --auth-mode=token + token env | gate PASSES |
| 4 | auth.provider=local_static, token set | none | gate PASSES |
| 5 | auth.provider=local_static, token unset | none | gate FAILS |
| 6 | no auth anywhere | none | gate FAILS |

**Final test count**: 30 passed, 0 failed (24 → 30)

---

### Follow-Up Recommendations

Phase 2 (RBAC Enforcement) can now build on:
- `AuthIdentity` in `request.state` — all routes can call `getattr(request.state, "identity", None)` safely
- `rbac_store.py` + `FoundryPaths.rbac_db` — durable membership/role data ready for P5.2's `require_role` dependency
- Registry pattern — P5.4 (Clerk) simply registers a `ClerkAuthProvider` implementation, no core wiring changes needed
