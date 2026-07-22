## Phase 1 Completion Note — Deployment-Mode Presets

**Status**: COMPLETED
**Validator verdict**: APPROVED (task-completion-validator, Mode E) — all Phase-1 ACs met, no scope creep, additive-only confirmed.
**Isolation**: none (executed directly inside worktree `feat/public-multiuser-release-activation` — no nested worktree)
**Branch**: feat/public-multiuser-release-activation
**Committer**: orchestrator (Opus), single-committer per wave.

> Note: an earlier phase-owner run stopped before dispatch (the nested `Task` tool was
> not enabled in that context) and left a "BLOCKED" note here. The orchestrator then
> dispatched `python-backend-engineer` directly; this note supersedes that stale record.

### Tasks
| Task | Status | Agent |
|------|--------|-------|
| ACT-101 — `deployment_mode()` resolver + single_user/multi_user preset composition | completed | python-backend-engineer |
| ACT-102 — `rf serve --mode` flag + `deployment_mode_validate()` gate stub (conditions a–c) | completed | python-backend-engineer |

### Files Changed
- `src/research_foundry/config.py` — `_VALID_DEPLOYMENT_MODES`, `_DEPLOYMENT_MODE_PRESETS`, `FoundryConfig.deployment_mode()`, `._deployment_mode_preset_default()`, `.deployment_mode_validate()`; `auth_rbac_enforcement()` / `workspace_isolation_enforcement()` / `auth_rate_limit_enabled()` consult the preset only when the knob is unset (explicit overrides still win).
- `src/research_foundry/cli_commands.py` — `--mode` option on `rf serve` + Step-1.5 gate call before any port opens (grep+sed edits only; anti-blow-up guardrail honored on the 2,755-line file).
- `src/research_foundry/api/app.py` — `deployment_mode_validate(bind_host=...)` as the first statement in `create_app()`.
- `tests/unit/test_deployment_mode.py` (20 tests), `tests/test_deployment_mode_cli_and_app.py` (7 tests) — new.

### Exit Gate — FR-2 byte-identical regression: GREEN
`TestFR2ByteIdenticalRegression` pins the exact pre-feature literal defaults and proves the unset-key path and explicit-`single_user` path are identical. `single_user`'s preset table is empty by construction, so the resolver always falls through to the original fallback — no existing default changed (verified additive-only).

### Validation
- Phase tests (validator re-run): `27 passed`.
- Implementer full-scope run: `245 passed` on config/CLI/app/rbac/isolation; the 8 pre-existing failures (`test_serve_api.py` sensitivity-gate, `test_assertion_rollout.py`, `test_report_anchors.py`) confirmed unrelated via clean-stash comparison.

### Evidence
- test:tests/unit/test_deployment_mode.py
- test:tests/test_deployment_mode_cli_and_app.py
