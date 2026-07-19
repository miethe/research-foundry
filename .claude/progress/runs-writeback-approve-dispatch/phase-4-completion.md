## Phase 4 Completion Note — Tests, Hardening & Docs

### Summary

Phase 4 closes out the runs-writeback-approve-dispatch-v1 feature with the full RBAC/governance/
audit hardening matrix, a frontend test suite for the Phase 3 UI action, a full validation-suite
pass, the required CHANGELOG entry, and the three deferred-item design specs. Rather than
re-deriving coverage that Phases 1-2 already built (ordering assertion, per-target isolation, audit
row wiring), this phase's own gap analysis identified the genuine holes — explicit RBAC on/off
toggle test, real-http-stack (unmocked) ordering + audit verification, and idempotent re-invocation
— and added exactly those, avoiding duplicate-maintenance test sprawl. Both the
`task-completion-validator` gate (VAL-4) and the mandatory Tier-2 `karen` feature-end gate (KAREN-1)
returned **PASS** verdicts, independently re-verifying the work rather than trusting self-reports.

### Tasks

- [x] TEST-001 → python-backend-engineer — RBAC on/off matrix. New
      `TestWritebackApproveRBACEnforcementToggle` class in `tests/test_writeback_router.py`: toggles
      `app.state.rbac_enforced` directly post-construction and asserts insufficient-role identities
      get 200 when disabled, plus an explicit-enforced no-identity passthrough case. Existing
      `TestWritebackApproveRBAC` (Phase 2) already covered the default-enforced 403/200 cases.
- [x] TEST-002 → python-backend-engineer — governance ordering through the real HTTP stack. New
      `test_guard_check_precedes_dispatch_through_real_http_stack` (parametrized pass/block/
      human_review) in `tests/test_writeback_hardening.py` drives the real (unmocked)
      `approve_and_dispatch` via `TestClient.post()` with a call-order spy on `guard_check` + the
      three per-target dispatch primitives — this is the "not just code inspection" ordering
      assertion at the integration layer, complementing Phase 1's service-level
      `test_guard_check_runs_before_any_target_dispatch`.
- [x] TEST-003 → python-backend-engineer — idempotent re-invocation (the one gap Phase 1 explicitly
      deferred). New `test_idempotent_reinvocation_ids_and_paths_stable` calls the real service twice
      sequentially for the same `run_id` and asserts `bundle_id`, the ccdash `event_id`, and
      meatywiki/skillbom front-matter IDs plus the full `writebacks/` file set are identical across
      both calls. Per-target isolation itself was already covered by Phase 1's
      `test_per_target_isolation_one_failure_does_not_block_others`.
- [x] TEST-004 → python-backend-engineer — audit-row-per-outcome. Existing
      `TestAuditOneRowPerOutcome` (Phase 2, mocked-dispatch) already covers all 4 classes with
      exactly one `record_event` call each; new `test_real_success_path_records_exactly_one_audit_row`
      adds the unmocked-path proof (confirms the real service doesn't introduce a hidden second
      audit call — `approve_and_dispatch()` itself never calls `record_event`, only the router does).
- [x] TEST-005 → ui-engineer-enhanced — new `frontend/runs-viewer/src/test/approve-dispatch-action.test.tsx`,
      17 tests across visibility (4), confirmation dialog (4), outcome rendering (5, including
      malformed/partial-payload fallback cases), and governance-vs-generic-error discrimination (4).
      `fr13-writeback-review.test.tsx` re-run unmodified, 15/15 pass, confirmed byte-unchanged via
      `git status`.
- [x] TEST-006 → ui-engineer-enhanced — runtime smoke, **partially live-exercised with a documented
      limitation**. The real `rf serve` API was brought up in this worktree (`127.0.0.1:17432`) and
      `POST /api/runs/{run_id}/writeback/approve` confirmed registered and live in `/openapi.json`.
      **Not exercised live**: driving the actual React UI against that running API through a real
      browser — no DOM-automation tool was available in this sandbox, and the worktree has zero
      seed run data (producing one requires the full discovery-swarm pipeline, out of scope here).
      Compensating coverage: TEST-005's 17 vitest cases exercise every response shape the real API
      can produce; TEST-001..004 exercise the real route + service via `TestClient` against the
      actual app object. VAL-4 independently judged this a reasonable substitute, not a gap.
- [x] TEST-007 → **run directly by the phase-owner** (per the delegation contract's Bash carve-out
      for "running the validation suite" — not product-code implementation). Backend:
      `pytest tests/test_writeback_router.py tests/test_approve_and_dispatch.py tests/test_writeback_hardening.py`
      → 34/34 pass; `ruff`/`flake8 --select=E9,F63,F7,F82` clean. Frontend:
      `tsc -p tsconfig.app.json --noEmit` clean; `eslint` clean on the 3 touched files (9 pre-existing
      problems remain, all in files this feature never touched); `pnpm test` → 1018/1019 pass (the 2
      known pre-existing baseline failures only, no new failures); `pnpm build` succeeds.
- [x] DOC-001 → changelog-generator (dispatched with `model=sonnet` — haiku not accessible in this
      environment) — `[Unreleased]` → `Added` → "Writeback Approve & Dispatch" entry in
      `CHANGELOG.md`; plan frontmatter `changelog_ref` set to `CHANGELOG.md`.
- [x] DOC-006 → documentation-writer (dispatched with `model=sonnet`) — 3 design specs authored at
      `maturity: idea` for DI-WBAD-1/2/3 at the exact paths named in the plan's deferred-items table;
      plan frontmatter `deferred_items_spec_refs` populated with all 3 paths.
- [x] VAL-4 → task-completion-validator — **PASS**. Independently re-verified all 10 Phase 4 Quality
      Gates checklist items against code and re-ran the full test/validation suite itself (not
      trusting self-reports); zero required fixes.
- [x] KAREN-1 → karen (Tier-2 mandatory feature-end gate) — **PASS**. End-to-end reality check
      against PRD §11 acceptance criteria (verified by reading `approve_and_dispatch()` and the
      router source directly), the Mode D rollback/mitigation section (governance-gate-first
      ordering, per-target isolation, idempotent overwrite, advisory lock — all confirmed present in
      shipped code, not just promised in the plan), and the R7 scope-creep guard (diff stayed to a
      single approve+dispatch action; the 3 deferred items remain idea-stage stubs, not implemented).
      Two LOW-severity, non-blocking cleanup items noted below.

### Validator Verdicts

- **VAL-4 (task-completion-validator): PASS.** No required fixes.
- **KAREN-1 (karen, Tier-2 feature-end gate): PASS.** Feature judged functionally complete and
  correct. Two LOW-severity, non-blocking items flagged for awareness (not gating):
  1. A stale reference to a nonexistent `rf bundle --approve` CLI flag (PRD Decision #3 already
     establishes this flag does not exist) survives in `CHANGELOG.md`'s pre-existing FR-13 subsection
     and a code comment in `RunDetailWorkspace.tsx` (~line 57). Pre-existing text this feature did
     not introduce, but now sits awkwardly next to the new "Approve & Dispatch" entry. Left as-is
     per this phase's scope (Phase 4 didn't touch that FR-13 subsection or that comment); worth a
     follow-up cleanup pass.
  2. Karen's review ran before the phase-owner's final commit step and flagged the Phase 4 files as
     "uncommitted" — resolved by this hand-off: Isolation for this phase run is `none` (shared
     worktree), so per the phase-owner contract Opus remains the single committer. All Phase 4 work
     is left on disk, uncommitted, for Opus to commit.

### Files Changed

- `tests/test_writeback_router.py` — added `TestWritebackApproveRBACEnforcementToggle` (TEST-001).
- `tests/test_writeback_hardening.py` — **new file**: real-stack ordering test (TEST-002), idempotent
  re-invocation test (TEST-003), real-success-path audit test (TEST-004). 8 tests total.
- `frontend/runs-viewer/src/test/approve-dispatch-action.test.tsx` — **new file**, 17 tests (TEST-005).
- `CHANGELOG.md` — `[Unreleased]` → `Added` entry (DOC-001).
- `docs/project_plans/design-specs/runs-writeback-opt-in-targets-ui.md` — **new**, DI-WBAD-1 (DOC-006).
- `docs/project_plans/design-specs/writeback-dispatch-rollback.md` — **new**, DI-WBAD-2 (DOC-006).
- `docs/project_plans/design-specs/writeback-dispatch-distributed-lock.md` — **new**, DI-WBAD-3 (DOC-006).
- `docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md` —
  frontmatter: `changelog_ref: CHANGELOG.md`, `deferred_items_spec_refs` populated (3 paths).
- `.claude/progress/runs-writeback-approve-dispatch/phase-4-progress.md` — all 11 tasks completed
  with started/completed timestamps, evidence, and `verified_by` populated; phase gate PASSED
  (`validate-phase-completion.py`, 0 violations).

### Deviations & Risks

- None from the plan's Phase 4 scope. TEST-006's live-browser exercise was infeasible in this
  sandbox (no DOM-automation tool, no seed run data) — documented as a limitation and judged by both
  VAL-4 and KAREN-1 as reasonably compensated by TEST-001..005's coverage, not a required fix.
- Model overrides applied per the dispatch instructions: DOC-001 (changelog-generator) and DOC-006
  (documentation-writer) both ran on `model=sonnet` instead of their configured `haiku` default,
  since haiku-4-5 was not accessible in this environment.
- The two LOW-severity karen findings (stale `rf bundle --approve` reference; uncommitted Phase 4
  files at review time) are documented above — neither blocks phase completion per karen's own
  verdict.

### Commits

None — this phase ran with **Isolation: none** (shared worktree, no nested worktree created). Per
the phase-owner contract, Opus is the single committer for this run; no commit was made by the
phase-owner. Working tree state at hand-off (Phase 4's own files, beyond Phases 1-3 which are
already committed on this branch):
- `M .claude/progress/runs-writeback-approve-dispatch/phase-4-progress.md`
- `M tests/test_writeback_router.py`
- `M CHANGELOG.md`
- `M docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md`
- `?? tests/test_writeback_hardening.py`
- `?? frontend/runs-viewer/src/test/approve-dispatch-action.test.tsx`
- `?? docs/project_plans/design-specs/runs-writeback-opt-in-targets-ui.md`
- `?? docs/project_plans/design-specs/writeback-dispatch-rollback.md`
- `?? docs/project_plans/design-specs/writeback-dispatch-distributed-lock.md`
