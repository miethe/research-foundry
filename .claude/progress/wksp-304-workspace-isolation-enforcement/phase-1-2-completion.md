## Phase 1-2 Completion Note

**Status**: PASS
**Validator verdict**: PASS — remediation cycle (1) closed the single completeness gap found on first gate; all in-scope tasks verified against exit criteria and full test suite.
**Isolation**: shared (worked directly on `main`, no worktree)
**Branch**: n/a (shared isolation)
**Worktree path**: n/a (shared isolation)

### Scope Note

TASK-2.4 ("Seam task: P2->P3 propagation verification") is a **forward seam** — it depends on
TASK-3.1/3.2/3.3, which live in Phase 3 and have not run yet. Per the caller's explicit scoping
instruction, TASK-2.4 was left `status: pending` and NOT dispatched. Phase progress `status` was
set to `completed` with TASK-1.1, TASK-1.2, TASK-2.1, TASK-2.2, TASK-2.3 done and validator-reviewed,
per that same instruction. **The P3 wave closes TASK-2.4** once its own service signatures
(TASK-3.1/3.2/3.3) land — the P3 phase-owner should re-open the seam verification at that point.

### Files Changed

- `src/research_foundry/config.py` — added `WorkspaceIsolationEnforcement` enum (auto/enabled/disabled),
  `Config.workspace_isolation_enforcement()` parser, `Config.resolve_workspace_isolation_enforced(provider, bind_host)`
  resolver (fail-closed `ValueError` on `disabled` + non-loopback; reuses existing `_is_loopback()`).
  Structurally mirrors the shipped `auth.rbac_enforcement` pattern per plan spec.
- `src/research_foundry/api/app.py` — wired `app.state.workspace_isolation_enforced` at app-create
  time, immediately after the existing `app.state.rbac_enforced` block. Inert — zero consumers.
- `src/research_foundry/api/routers/catalog.py` — threaded `identity = getattr(request.state, "identity", None)`
  into all 5 endpoints reaching `catalog_service`; TODO(WKSP-304 P3) markers at each call site (service
  signatures don't accept the kwarg yet — Phase 3 lands that).
- `src/research_foundry/api/routers/agent_jobs.py` — same pattern, 6 endpoints reaching `agent_job_service`.
- `src/research_foundry/api/routers/reports.py` — same pattern, 21 endpoints reaching `builder_service`
  (directly or, in one case — `verify_draft_endpoint` — indirectly via `verify_draft()` → `builder_service.load_draft`).
  One pre-existing real-use site (`publish_preview`, line ~802) already consumed `identity` for RBAC
  and was left untouched.
- `tests/unit/test_workspace_isolation_enforcement_flag.py` (new) — 14 tests total: 8 parser tests
  (TASK-1.1) + 6 resolver tests (TASK-1.2), all passing.
- `admin.py`, `audit.py`, `auth_identity.py` — verified (TASK-2.3), zero changes needed; grep-confirmed
  no calls to `catalog_service`/`agent_job_service`/`builder_service` in any of the three files.

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | TASK-1.1, TASK-2.1, TASK-2.2, TASK-2.3 | completed (TASK-1.1 & TASK-2.2 required one retry each due to transient Bedrock 503s — no partial state, clean re-dispatch) | python-backend-engineer |
| 2 | TASK-1.2 | completed | python-backend-engineer |
| remediation | TASK-2.2 (verify_draft_endpoint gap) | completed | python-backend-engineer |
| gate 1 | phase validation | FAIL (1 fix: missing identity resolution in `verify_draft_endpoint`) | task-completion-validator |
| gate 2 | re-validation | PASS | task-completion-validator |

### Behavioral Invariant Confirmed

Both phases are 100% inert, as required:
- `app.state.workspace_isolation_enforced` is set but has zero consumers anywhere in `src/` (grep-confirmed).
- No router change adds an `identity=` kwarg to any service call whose signature doesn't already
  support it — every site either passes the real kwarg (none do yet, since Phase 3 hasn't landed) or
  leaves a `# TODO(WKSP-304 P3)` marker for Phase 3 to pick up.
- No query-scoping, deny, or enforcement logic was added anywhere.

### Test Results

Full suite run via `/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/ -q`:
exactly 5 failures, all in `tests/test_serve_api.py`, confirmed via `git stash`/`git stash pop`
comparison to pre-change `main` HEAD to be a pre-existing baseline unrelated to this phase's changes.
Zero regressions introduced. New test file (14 tests) passes 14/14.

### Escalation Reason

N/A — no Mode D triggers encountered.

### Follow-Up Recommendations

1. **P3 must close TASK-2.4** — the seam verification task deferred out of this phase's scope.
2. Validator flagged (optional, non-blocking): 21 near-identical inert `identity = getattr(...)`
   blocks in `reports.py` is repetitive; a shared FastAPI dependency to resolve `identity` once could
   reduce duplication when Phase 3 wires the real kwarg through. Worth considering during P3, not a
   blocker for this phase.
3. Uncommitted working-tree changes for this phase are ready to commit per `.claude/rules/git-workflow.md`
   (validated + reviewer-approved). Proceeding to commit on `main` (shared isolation, no worktree merge
   needed); push remains gated per that rule.
