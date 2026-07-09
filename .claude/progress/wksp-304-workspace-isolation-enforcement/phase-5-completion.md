## Phase 5 Completion Note

**Status**: BLOCKED
**Validator verdict**: BLOCKED — test-authoring work (TASK-5.1–5.4, 5.6, 5.7, 5.5(a)) is real, verified, 79/79 passing; but TASK-5.5(b)'s mandatory "break it if you dare" gate (AC-6, Critical) fails on a genuine production bug the tests correctly discovered, so Phase 5 cannot be waved into Phase 6 without an explicit fix-now-vs-defer decision.
**Isolation**: shared (branch `main`, no worktree)
**Commit**: `caec975` — `test(wksp-304): P5 regression + enforcement test matrix (79 tests)`

### Files Changed
- `tests/test_workspace_isolation_enforcement.py` (new, 1045 lines, 66 tests) — TASK-5.1 (2-workspace read/list/mutate x allowed/denied matrix), TASK-5.2 (6-router identity propagation), TASK-5.3 (join/tombstone leak coverage, mutation-tested with a durable revert→observe-fail→restore→observe-pass evidence block for 5 representative predicates, ~line 606-665), TASK-5.4 (mutation-deny spies), TASK-5.5(a) (~10 identity=None single-operator fallback tests), TASK-5.7 (SQL bind-param discipline, parametrized).
- `tests/test_config_workspace_enforcement.py` (new, 227 lines, 13 tests) — TASK-5.6 (app-integration-level config validation matrix: `auto|enabled|disabled` x loopback/non-loopback x provider).
- `.claude/progress/wksp-304-workspace-isolation-enforcement/phase-5-progress.md` — task statuses updated (6 completed, 1 blocked).
- No production code (`src/`) was modified — confirmed via `git diff --stat -- src/` (empty) at every checkpoint, including after the TASK-5.3 remediation cycle's temporary predicate reverts (each reverted and restored before the next step).

### Batch Summary
| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | TASK-5.1, 5.2, 5.3, 5.4, 5.5, 5.7 | completed (5.5 blocked) | python-backend-engineer (`tests/test_workspace_isolation_enforcement.py`) |
| 1 | TASK-5.6 | completed | python-backend-engineer (`tests/test_config_workspace_enforcement.py`) |
| validator | — | BLOCKED (Critical + Medium findings) | task-completion-validator |
| 2 (remediation) | TASK-5.3 evidence gap | completed | python-backend-engineer (`tests/test_workspace_isolation_enforcement.py`) |

### Validator Findings and Disposition

1. **Critical (unresolved — this is the escalation)**: TASK-5.5(b) full-suite-under-forced-enforcement gate fails. Reproduced independently by both the implementer and the validator:
   - Baseline (`workspace_isolation_enforcement` not forced): `tests/integration/test_p5_regression_suite.py` + `tests/unit/test_workspace_migration_service.py` → **85 passed, 0 failed**.
   - Forced globally enabled: **82 passed, 3 failed** — all 3 in `TestAuditExposureGate` (`test_forced_degraded_audit_makes_share_resolution_fail_closed`, `..._makes_publish_preview_fail_closed`, `..._healthy_audit_leaves_share_resolution_and_publish_preview_unaffected`).
   - Root cause (confirmed by validator against `src/research_foundry/services/builder_service.py:455-469`): `create_draft` takes no `identity` parameter, only an optional `workspace_id` the caller must pass explicitly; `reports.py`'s draft-creation path does not thread it. Under advisory (current default) this is invisible. Once enforcement is forced on, drafts created this way land with `workspace_id=None` and are then denied on read/mutation by AC-3's null-mismatch rule — including by their own creator. Log evidence: `workspace_scope_enforced_denial record_workspace_id=null identity_workspace_id="ws1"`.
   - This is a genuine gap in multi-tenant-boundary production code, not a test-quality defect, and not something invented by an overly strict test — the regression matrix did exactly what Phase 5 exists to do (AC-6 is explicitly flagged "Critical severity" in the plan).
   - **Not remediated in this phase**: fixing `builder_service.create_draft` / `reports.py` to thread identity is a change to multi-tenant boundary enforcement code, which is an explicit Mode-D escalation trigger for the phase-owner contract (`.claude/agents/dev/phase-owner.md` §Mode-D Escalation Triggers) — out of scope for a test-only phase, and requires an explicit human/Opus decision on whether to fix now or formally defer.
   - Cross-reference: this is the same load-bearing area flagged in project memory `public-multiuser-release-plan.md` — "WKSP-304 row-level enforcement DEFERRED — must land before shared-store multi-tenant deploy." This finding should factor into that deployment gate.

2. **Medium (resolved this session)**: TASK-5.3's mutation-test claim was originally unsubstantiated on disk (asserted only in an agent transcript, not in a durable artifact). Remediated: the implementer re-ran the actual mutation-test pass for all 5 predicates (temporary revert via `/tmp` backup → target test(s) observed to fail → restore via `cp` → `git diff --stat -- src/` confirmed empty → target test(s) observed to pass) and recorded the evidence as a permanent block in `tests/test_workspace_isolation_enforcement.py` immediately before `class TestJoinAndTombstoneLeaksClosed:` (~line 606-665).

### Task Status (final)

| Task | Status | Notes |
|------|--------|-------|
| TASK-5.1 | completed | 24 tests |
| TASK-5.2 | completed | 7 tests |
| TASK-5.3 | completed | 15 tests; mutation-test evidence now durable on disk |
| TASK-5.4 | completed | 4 tests |
| TASK-5.5 | **blocked** | 10 new identity=None tests pass (5.5a); full-suite-under-enforcement gate fails 3/85 (5.5b) — production bug, see above |
| TASK-5.6 | completed | 13 tests |
| TASK-5.7 | completed | 6 tests |

### Escalation Reason

Multi-tenant boundary enforcement gap discovered by TASK-5.5(b)'s hard gate: `builder_service.create_draft` / `reports.py` does not thread `identity`, so drafts created while enforcement is advisory get `workspace_id=None` and become unreadable/unmutable by their own creator once enforcement is switched to `enabled`. Per the phase-owner's Mode-D escalation triggers ("any change to multi-tenant boundary enforcement"), fixing this requires editing production workspace-scoping code outside this phase's test-only mandate. **Decision needed from Opus/user**: (a) dispatch a scoped fix now (thread `identity`/`workspace_id` through `create_draft` and its `reports.py` call site, re-run TASK-5.5(b), re-gate), or (b) formally defer with a tracked follow-up task and adjust this phase's exit criteria/AC-6 wording to reflect the deferral, consistent with the existing project memory note that WKSP-304 enforcement must fully land before any shared-store multi-tenant deploy.

### Follow-Up Recommendations

1. Resolve the escalation above before Phase 6 (docs/changelog) begins — Phase 6 should document the final AC-6 state accurately, whichever way it's resolved.
2. If fixed: re-run TASK-5.5(b)'s exact repro (`FoundryConfig.resolve_workspace_isolation_enforced` mocked to `True`) against the full pre-existing suite and confirm 85/85; re-run `task-completion-validator` for a clean PASS.
3. If deferred: file a tracked follow-up task referencing this Completion Note and update the PRD/plan's AC-6 status accordingly so it isn't silently forgotten before the shared-store multi-tenant deploy gate.
