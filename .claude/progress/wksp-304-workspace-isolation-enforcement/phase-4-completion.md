## Phase 4 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 8 Phase-4 quality gates verified against actual code (not just progress-file claims); full suite shows exactly the 5 known pre-existing `tests/test_serve_api.py` baseline failures, zero regressions; fail-closed smoke check reproduced live (cross-workspace mismatch + enforcing resolver → `allowed=False`).
**Isolation**: shared (worked directly on `main`, no worktree, per orchestration instructions)
**Branch**: main
**Worktree path**: N/A

### Resume context
This phase-owner run was a RESUME. A prior P4 phase-owner completed TASK-4.1 (flip `require_workspace_scope` to enforcing + D3 ordering proof) but was killed mid-flight before TASK-4.2/4.3/4.4. Its work — plus, on inspection, most of TASK-4.2's service-layer wiring — was intact and uncommitted on `main`. This run verified that prior work, closed the remaining gaps, completed TASK-4.2/4.3/4.4, ran the mandatory validator gate, and produced this note + the single commit.

### Files Changed (Phase 4 scope; Phase 1-3 changes were already present/committed separately per prior phase notes)
- `src/research_foundry/api/auth/scope.py` — TASK-4.1 (enforcing flip, D3 ordering, prior instance): `require_workspace_scope()` now denies (`allowed=False, reason="workspace_mismatch_denied"`) on an enforcing-mode mismatch (including null `workspace_id`, never defaulted to allowed); `identity is None` short-circuit remains the literal first statement. TASK-4.2/entry-criteria(c) (this run): added `resolve_workspace_isolation_active(paths)` — the single shared implementation the 3 services now delegate to (was duplicated 3x).
- `src/research_foundry/services/catalog_service.py` — `get_item()` audit-logs an enforcing-mode deny (distinct ERROR log vs. WKSP-301 advisory WARNING) only when the record exists in another workspace (never for genuinely-missing). This run: generalized `_log_enforced_denial_if_exists_elsewhere()` (table/id_column params) and wired the same audit-log parity into `get_draft_index()` — closing the last gap of the "require_workspace_scope wired at only 2/6 effective deny paths" Phase-3 finding (now 6/6: `get_item`, `get_draft_index`, `load_draft` + delegators `list_drafts`/`export_markdown`, `load_job`). `_isolation_active()` now delegates to `scope.resolve_workspace_isolation_active()`.
- `src/research_foundry/services/builder_service.py` — `load_draft()` (prior instance): same deny + audit-log-parity pattern (file-canonical equivalent of the WHERE-clause check). This run: `_isolation_active()` now delegates to the shared helper.
- `src/research_foundry/services/agent_job_service.py` — `load_job()` (prior instance): same pattern, closing the one Phase-3 gap where this service never called `require_workspace_scope` at all. This run: `AgentJobService._isolation_active()` delegates to the shared helper.
- `src/research_foundry/api/routers/reports.py` — TASK-4.3 (this run): added resolve-then-check pre-flight (`bsvc.load_draft(paths, report_id, identity=identity)`, `NotFoundError` → `_not_found`) before the mutating call in `create_version`, `restore_version`, `add_block`, `reorder_blocks`, `update_block`, `delete_block`, `add_claim_link`, `remove_claim_link`, `add_source_link`, `remove_source_link`. `delete_draft` special-cased: identity-scoped probe, then a fallback `identity=None` probe to distinguish "genuinely missing" (idempotent 204, unchanged) from "exists in another workspace" (404, delete never called) — preserves the pre-existing idempotency contract while fail-closing the cross-workspace case. Entry-criteria (b): `resolve_share_link` now passes `identity=None` explicitly to `load_draft`/`export_markdown` (the share token is the sole authorization boundary — a share link must never be narrowed or broadened by the viewer's own workspace); `create_share_link` unchanged (still creator-identity-scoped).
- `src/research_foundry/api/routers/agent_jobs.py` — no diff this phase; `cancel_job`/`accept_job` already resolve-before-mutate via `_load_job_or_404(..., identity=identity)` from Phase 3's forward-seam closure — confirmed satisfies AC-5, no work needed.
- `src/research_foundry/api/routers/catalog.py` — no diff; catalog items are read-only derived data, no per-record mutation endpoints exist.
- Tests: `tests/unit/test_workspace_migration_service.py`, `tests/unit/test_catalog_service.py`, `tests/unit/test_builder_service.py`, `tests/unit/test_agent_job_service.py` (D3 ordering proof, deny/audit-log-parity regression tests, `identity=None`/inactive byte-identity tests), `tests/unit/test_reports_api.py` (10-case parametrized zero-write mutation-deny proof + dedicated `delete_draft` cross-workspace test), `tests/unit/test_share_token_auth_exemption.py` (share-link viewer-workspace-independence proof).

### Decisions made this phase
1. **Entry-criteria (a) — 6 deny paths**: closed. All 6 effective single-record deny paths (`get_item`, `get_draft_index`, `load_draft` + its 2 delegators, `load_job`) now emit audit-log parity on an enforcing-mode deny.
2. **Entry-criteria (b) — share-link semantics** (Mode-D-adjacent judgment call, resolved without escalation): a share link's authorization is the token itself, not the viewer's workspace. `resolve_share_link` explicitly decouples workspace-isolation enforcement from the share mechanism (`identity=None` passed to the two service calls it makes) — this is the FAIL-CLOSED choice consistent with "never broaden or narrow visibility beyond the specifically-shared resource." `create_share_link` remains creator-identity-scoped (a cross-workspace caller still cannot mint a link for someone else's draft).
3. **Entry-criteria (c) — `_isolation_active()` consolidation**: closed. Single implementation (`scope.resolve_workspace_isolation_active`); the 3 services delegate to it with zero behavior change (verified by the full existing test suite passing unmodified).
4. **TASK-4.4 (optional, non-blocking) — deny-event telemetry (OQ-2): DEFERRED.** `audit_service.py` only soft-imports the OTel *trace* API for mutation spans; no Counter/meter metrics primitive exists today. Building a real deny-event counter would require either a new OTel metrics instrument or extending the mutation-oriented audit ledger schema to a new read-denial event type — both nontrivial new infrastructure, not a quick fit per the plan's own "drop if it introduces new dependencies" allowance. The existing ERROR-level `workspace_scope_enforced_denial` structured JSON log (already distinct from the advisory WARNING) is the interim signal a log-aggregation/security-monitoring pipeline can alert or count on.

### Batch Summary
| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 (prior instance, resumed) | TASK-4.1 | completed | backend-architect |
| 2 | TASK-4.2 gap-closure (audit-log parity on `get_draft_index`), entry-criteria (c) consolidation, TASK-4.4 decision | completed | backend-architect |
| 3 | TASK-4.3 (mutation-deny wiring in reports.py), entry-criteria (b) share-link fix | completed | python-backend-engineer |
| — | Phase exit validator gate | PASS | task-completion-validator |

### Escalation Reason
N/A — no Mode-D trigger encountered. The share-link semantics question was Mode-D-adjacent (a multi-tenant boundary judgment call) but was resolvable from the plan's own OQ-1 fail-closed precedent and the PRD's explicit share-link design note (D5: "read-only, sensitivity-scoped share primitive") without requiring human sign-off — documented above rather than escalated.

### Follow-Up Recommendations
1. TASK-4.4 (deny-event telemetry / OQ-2) is deferred, not abandoned — worth a small follow-up item once a metrics/counter primitive exists elsewhere in the codebase (currently none does).
2. The validator's minor quality note: `catalog_service.get_item()`'s trailing `require_workspace_scope(...)` call is now redundant in the enforcing path (the query-layer check already denied first) — kept intentionally for advisory-mode parity with the other services' call shape. Not a defect; candidate for a future simplification pass, not urgent.
3. Phase 5 (regression matrix) can now proceed — this phase's fail-closed invariants (D3 ordering, 6/6 deny-path audit-log parity, AC-5 mutation-deny, AC-6 single-operator fallback) are validator-confirmed as the foundation to test against. The `workspace_isolation_enforcement` flag itself remains OFF by default — Phase 4 armed the mechanism, it did not flip the production default.

**Next step**: commit this phase to `main` (validated per git-workflow rule — tests green modulo the known unrelated baseline, validator PASS).
