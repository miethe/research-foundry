## Phase 2 Completion Note — API Layer: Auth, Audit, Governance Gate

### Summary

Phase 2 adds the first-ever HTTP-gated path for `rf writeback`'s approve-and-dispatch flow:
`POST /api/runs/{run_id}/writeback/approve` in a new `src/research_foundry/api/routers/writeback.py`,
RBAC-gated identically to the `POST /agent-jobs` precedent, wrapping (not modifying) Phase 1's
`approve_and_dispatch()` service function. The route maps the governance-block outcome to the same
`governance_rejected` error envelope the codebase already uses, records exactly one audit row per
invocation across all four outcome classes (success/partial/blocked/unexpected exception — the
plan's single highest-risk item), and threads resolved caller identity into both
`AuditEvent.actor_user_id` and `approve_and_dispatch()`'s `approved_by` population. `rbac.py`'s
classification docstring was updated to reflect that `rf writeback` is no longer purely
single-operator-trust/CLI-only. A design-review checkpoint (API-006, backend-architect) and a
validator gate (VAL-2, task-completion-validator) both returned clean PASS verdicts before this
phase closed.

### Tasks

- [x] API-001 → python-backend-engineer — new route file, RBAC gate
      (`Depends(require_role("owner","admin"))`, module-level `_RBAC_WRITEBACK` constant matching
      `agent_jobs.py`'s pattern), unconditional registration in `app.py` (no feature-flag gate,
      unlike `agent_jobs_router`).
- [x] API-002 → python-backend-engineer — `governance_rejected` 422/400 mapping sourced from
      `ApproveDispatchResult.guard_result`; handles the edge case where the combined gate blocks
      purely on `council_decision == "required_block"` (guard itself passed) via a synthetic
      `council_required_block` violation entry appended to the existing `violations` list — no new
      top-level response field.
- [x] API-003 → python-backend-engineer — audit wiring for all four outcome classes, verified by
      direct control-flow trace (not just test presence) by both the design reviewer and the
      validator: `NotFoundError` and generic `Exception` branches each record one row then raise (no
      fallthrough); success/partial/blocked share a single post-try/except `record_event` call.
      `overall_status` → `AuditEvent.result` mapping: `success`→`success`, `partial`→`failure`,
      `blocked`→`denied` (judgment call, signed off by both reviewers given `AuditEvent.result`'s
      3-value contract).
- [x] API-004 → python-backend-engineer — `request.state.identity` → `actor_user_id` (None when
      absent, not an error) and the same resolved identity threaded into `approve_and_dispatch()`'s
      `approver_identity` param, closing the loop Phase 1 left open (identity resolved-but-discarded
      elsewhere in the codebase; this route is the first to actually use it).
- [x] API-005 → python-backend-engineer — `rbac.py` docstring updated (~lines 57-71) to note the new
      HTTP-gated path alongside the still-single-operator-trust bare-CLI `writeback()` classification.
- [x] API-006 → backend-architect — design-review checkpoint (5/5 review bullets PASS, no blockers)
      + OpenAPI polish: added `ViolationOut`, `GuardResultOut`, `ApproveDispatchResponse`,
      `GovernanceRejectedDetail`, `GovernanceRejectedResponse` Pydantic models and wired
      `response_model=`/`responses={...}` on the route decorator, following `assertions.py`'s
      existing convention. Verified live via `TestClient` + `/openapi.json` inspection (schemas and
      response codes render correctly), not just code reading.
- [x] VAL-2 → task-completion-validator — **PASS**. Independently re-verified all 5 Phase 2 Quality
      Gates against code (not self-reports), confirmed `services/writeback.py` has zero uncommitted
      changes (Phase 1 lock held), re-ran the test suite itself (26/26 passing), and traced the
      audit-wiring control flow directly.

### Validator Verdict

**PASS** (task-completion-validator, Mode E). No required fixes. One correction for the record: the
implementer's self-report claimed "33 tests" in `tests/test_writeback_router.py`; the validator's
independent count is **18** tests in that file (26 total across `test_writeback_router.py` +
`test_approve_and_dispatch.py`). All 18 are substantive and cover every required scenario (RBAC gate,
governance_rejected mapping including the synthetic-violation branch, one-audit-row-per-outcome ×5,
actor_user_id threading, targets body handling) — this is a self-report accuracy issue, not a
functionality gap, but is recorded here so it doesn't propagate uncorrected into Phase 4/feature-end
tracking. Zero fix cycles were needed.

### Files Changed

- `src/research_foundry/api/routers/writeback.py` — **NEW**. `POST /api/runs/{run_id}/writeback/approve`
  route, RBAC gate, governance_rejected mapping, audit wiring, identity threading, response/error
  Pydantic models (added during API-006).
- `src/research_foundry/api/app.py` — router import (~line 74) + unconditional registration
  (~lines 428-431) + endpoint-table docstring update.
- `src/research_foundry/api/auth/rbac.py` — docstring-only update (~lines 57-71); no logic changes.
- `tests/test_writeback_router.py` — **NEW**, 18 tests.

### Deviations & Risks

- None from plan scope. `src/research_foundry/services/writeback.py` (Phase 1's locked
  `approve_and_dispatch()` contract) is byte-unchanged — confirmed independently by both the
  backend-architect review and the validator via `git diff`.
- Non-blocking note carried forward from both reviewers: the `overall_status="partial"` audit row
  carries no per-target failure detail (only `target_status` elsewhere would show which target(s)
  failed) — flagged as a Phase 4 hardening consideration, not a Phase 2 blocker.
- Self-report accuracy issue noted above (18 vs. claimed "33" tests) — corrected here; no code
  impact.

### Commits

None — this phase ran with **Isolation: none** (shared worktree, no nested worktree created). Per
the phase-owner contract, Opus is the single committer for this run; no commit was made by the
phase-owner. Working tree state at hand-off (beyond this phase's own files):
- `M frontend/runs-viewer/src/api/client.ts` — pre-existing, not part of Phase 2 scope
- `M frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` — pre-existing, not part
  of Phase 2 scope
- `M src/research_foundry/api/app.py`
- `M src/research_foundry/api/auth/rbac.py`
- `?? src/research_foundry/api/routers/writeback.py`
- `?? tests/test_writeback_router.py`
