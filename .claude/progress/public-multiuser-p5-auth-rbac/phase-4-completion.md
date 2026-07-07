## Phase 4 Completion Note

**Status**: PASS
**Validator verdict**: PASS — 90 backend tests pass (1 xfailed expected), 9 frontend tests pass, TypeScript clean, flake8 clean, Gate #3 compliant.
**Isolation**: worktree
**Branch**: worktree-agent-a8f505b7becbcdd13
**Worktree path**: .claude/worktrees/agent-a8f505b7becbcdd13

### Files Changed

- `src/research_foundry/api/auth/adapters/clerk.py` — NEW: ClerkAuthProvider JWKS verify, CLERK_ROLE_MAP role mapping, available() dark-by-default gate
- `src/research_foundry/config.py` — auth.provider: clerk schema + clerk_frontend_api + clerk_outbound_internet_enabled + startup validation gate
- `foundry.yaml` — documented opt-in clerk example (commented out, dark by default)
- `src/research_foundry/api/auth/provider.py` — read-only reference (no changes)
- `tests/fixtures/auth/clerk_jwks_fixture.json` — NEW: locally-generated RSA-2048 JWKS + signed test JWTs + bad-sig keypair
- `tests/unit/test_clerk_adapter.py` — NEW: 48 unit tests covering JWKS verify, role mapping, caching, available() gate, dark-by-default regression
- `tests/unit/test_auth_provider_protocol_conformance.py` — NEW: 23 passed + 1 xfailed (oidc not registered — expected); parametrized conformance across local_static, clerk, oidc stub
- `tests/integration/test_clerk_login_seam.py` — NEW: CLERK-900 seam contract test; 19 tests covering positive round-trip, header contract, negative cases, identity JSON shape invariant
- `frontend/runs-viewer/src/auth/useClerkAuth.ts` — NEW: minimal FE Clerk login hook returning {identity, loading, error}; fetchIdentityWithToken() exported for testability
- `frontend/runs-viewer/src/auth/useClerkAuth.test.ts` — NEW: 9 vitest unit tests; fixture-based, no live Clerk dependency; AC P5.4-B covered
- `frontend/runs-viewer/package.json` — @clerk/clerk-react ^5.0.0 added to devDependencies
- `pyproject.toml` / `uv.lock` — pyjwt[crypto]>=2.8 and cryptography>=43.0 added
- `.claude/progress/public-multiuser-p5-auth-rbac/phase-4-progress.md` — created and updated to completed

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | CLK-4.1 | completed | backend-architect |
| 2 | CLK-4.2, CLK-4.4, CLK-4.5 | completed | backend-architect (CLK-4.2, CLK-4.4), ui-engineer-enhanced (CLK-4.5) |
| 3 | CLK-4.3 | completed | backend-architect |
| 4 | CLERK-900 | completed | backend-architect |

### Test Results

**Backend (pytest)**:
- `tests/unit/test_clerk_adapter.py` + `tests/unit/test_auth_provider_protocol_conformance.py` + `tests/integration/test_clerk_login_seam.py`
- Result: **90 passed, 1 xfailed** (oidc not registered in registry — expected per CLK-4.4 design)

**Frontend (vitest)**:
- `frontend/runs-viewer/src/auth/useClerkAuth.test.ts`
- Result: **9 passed**

**TypeScript**: clean (`npx tsc --noEmit`)
**flake8/ruff**: clean on new/changed Python files

### Escalation Reason

N/A — Gate #3 was NOT triggered. All work used the checked-in JWKS fixture only. No real Clerk secrets were hardcoded, committed, or used anywhere. foundry.yaml has clerk as a commented-out example (not enabled).

### AC Status

- AC P5.4-A (FE Clerk login round-trips against backend JWKS verify): PASS — verified by CLERK-900 (tests/integration/test_clerk_login_seam.py)
- AC P5.4-B (FE handles missing/malformed identity): PASS — verified by useClerkAuth.test.ts and CLERK-900
- AC P5.4-C (clerk and oidc satisfy AuthProvider Protocol identically): PASS — verified by test_auth_provider_protocol_conformance.py

### Runtime Smoke

`runtime_smoke: skipped` — Full-UI screenshot evidence deferred to P5.8 (AuthContext.tsx / login screen build); this phase's smoke equivalent is the CLERK-900 contract test.

### Human Gate #3

Gate #3 was not triggered during this phase. All implementation and testing used only the locally-generated JWKS fixture. Before `auth.provider: clerk` is ever flipped on in a real deployment's `foundry.yaml`, Human Gate #3 sign-off is required per the phase doc (covering: where secrets are stored, how JWKS is cached, what is logged). This has NOT been granted — it is a blocker for any production Clerk activation, not for this phase's completion.

### Commit References

- `4807927` — feat(auth): CLK-4.1 — ClerkAuthProvider JWKS verify core
- `45b9313` — feat(auth): CLK-4.2 — formalise Clerk org role-mapping table
- `6b21b1a` — test(auth): CLK-4.4 OIDC seam Protocol conformance cross-check
- `1bbaad3` — feat(auth): CLK-4.5 — minimal FE Clerk login hook useClerkAuth.ts
- `ffcfeb7` — feat(auth): CLK-4.3 config-flag dark-by-default wiring for Clerk provider
- `6be3d5c` — test(auth): add CLERK-900 seam contract test — FE↔BE Clerk login round-trip

### Deviations

- `available()` check is config-driven (not network-probed) — operator must explicitly set `auth.clerk_outbound_internet_enabled: true`. This is intentional (YAGNI; lightweight explicit over heavyweight probe).
- JWKS caching is in-process with no TTL invalidation. Documented as known limitation in clerk.py docstring; TTL refresh deferred to post-P5.9 follow-up.
- CLERK-900 test-only `/auth/identity` route is defined inline in the seam test file, not wired into app.py — that wiring is P5.5's scope.

### Follow-Up Recommendations

1. P5.5: Wire the real `/auth/identity` endpoint in app.py for the live Clerk flow.
2. P5.8: Build AuthContext.tsx wrapping useClerkAuth.ts; this phase's hook is the stable import surface.
3. P5.9: Add JWKS TTL/ETag cache refresh path (post-P5.9 follow-up noted in clerk.py docstring).
4. Human Gate #3 sign-off required before any production Clerk activation.
