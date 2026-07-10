## Phase 6 Completion Note

**Status**: BLOCKED
**Validator verdict**: `task-completion-validator` — FIX-REQUIRED (Phase 6's own docs content verified accurate, but the phase's own exit criterion "karen end-of-feature review passes" was unmet). `karen` (end-of-feature gate, dispatched as remediation) — **NOT APPROVED**.
**Isolation**: shared
**Branch**: main (no worktree)

### Escalation Reason

This is a **Mode-D escalation**, not a Phase 6 docs defect. All five Phase 6 tasks (TASK-6.1
through TASK-6.5) were completed and their content independently verified accurate by
`task-completion-validator`:

- TASK-6.2 (CHANGELOG.md `[Unreleased]` entry) — accurate, correctly categorized.
- TASK-6.3 (workspace-migration-runbook.md "Enforcement Flag Reference" section) — accurate
  against `config.py`.
- TASK-6.4 (config.py docstring parity, commit `3d24b6d`) — docstring-only, zero executable-line
  diff, verified via `git show 3d24b6d --stat`.
- TASK-6.1 (final regression sign-off) — 830 unit tests passed (+1 xfailed), 79/79 dedicated
  WKSP-304 regression tests passed, 0 failures.
- TASK-6.5 (plan frontmatter finalization) — correctly populated `commit_refs`, locked decision
  D5, resolved the decision_gate.

However, the phase's own stated exit criterion (phase-6-docs-changelog.md line 12, restated in
phase-6-progress.md's "Closing gate") requires `karen`'s end-of-feature review to pass before the
phase — and the feature — can be considered complete. `task-completion-validator` caught that this
gate had not run despite the plan being marked `completed`/`shipped`; I dispatched `karen` as the
required remediation cycle.

**`karen`'s verdict: NOT APPROVED.** She confirmed AC-6 (single-operator identity=None fallback)
and AC-7 (config fail-closed validation) both hold structurally — not merely in prose — and that
the query-layer scoping and 404/mutation-deny paths are correctly wired on the surfaces she spot-
checked. But the sibling-gap hunt she was asked to run (given the P5.5b precedent) turned up two
real, HIGH-severity gaps in **already-merged Phase 4/5 code**, not in anything Phase 6 touched:

1. **`create_draft_from_collection`** (`src/research_foundry/services/builder_service.py:1096`)
   calls `catalog_service.get_item(...)` with **no `identity`** — an unscoped read. Under
   enforcement, a caller in workspace A can seed a draft from a workspace-B `catalog_item_id` and
   have its content embedded into their own draft. This is an actual cross-workspace read leak
   under the exact enforcement this feature ships to add.
2. **`create_draft_from_run` / `create_draft_from_collection`** (`reports.py:244-254`, `:265-275`
   → `builder_service.py:988-1038`, `:1064-1092`) never thread caller identity into the inner
   `create_draft` call — the same failure class already fixed once for the identity-less
   `create_draft` blank-create path in the P5.5b escalation. Under enforcement this either denies
   the draft to its own creator (workspace_id=None) or lets a caller plant a draft into an
   arbitrary named workspace via a client-supplied `workspace_id`.

Both gaps touch the multi-tenant boundary enforcement this feature exists to add — squarely a
**Mode-D trigger** per my own operating rules. `karen` herself flagged that these fixes require
explicit Opus/user authorization before any edit, mirroring the P5.5b precedent. I did **not**
attempt to fix them; that would violate the Mode-D boundary. I have not committed anything beyond
what individual implementers auto-committed under the project's git-workflow rule (one commit,
`3d24b6d`, docstring-only and unaffected by this finding).

**Note on current risk exposure**: enforcement defaults to advisory (`provider="none"`) today, so
these code paths are currently byte-identical to pre-feature behavior — this is not a live
production incident. But it is a landmine under the exact `enabled`/`auto`+provider!="none" flip
this feature exists to enable, and must close (or be explicitly, honestly tracked as a deferred
item with a corrected AC-1 coverage claim) before the feature can be marked `completed`.

### Corrective actions already taken (accurate-state bookkeeping, not fixes)

Because the plan and progress frontmatter had already been advanced to `completed`/`shipped`
(TASK-6.5, before the karen gate ran), I reverted those specific claims so they don't stand false
while blocked — via CLI only, no direct YAML edits to progress frontmatter (per
`.claude/rules/progress-cli-only.md`):

- `phase-6-progress.md`: `status: completed` → `status: blocked` (via `update-field.py`).
  Markdown body table updated to show all 5 tasks completed (they are) and the closing-gate line
  updated to record karen's NOT APPROVED verdict (direct edit to markdown body, permitted).
- Plan file (`wksp-304-workspace-isolation-enforcement-v1.md`): `status: completed` → `blocked`;
  `planning_maturity: shipped` → `scoped`; added `OQ-4` documenting the two gaps, owner `nick`,
  `status: open`. `commit_refs`, `changelog_ref`, the D5 decision lock, and the decision_gate
  resolution were left as-is (those findings are unrelated and still correct — the 404-not-403
  design decision is not in question).

Individual task-level statuses in `phase-6-progress.md` remain `completed` (TASK-6.1 through
TASK-6.5 genuinely are — the phase-level status is what's blocked, on the unmet karen gate).

### Files Changed (uncommitted — awaiting Opus/user decision)

- `CHANGELOG.md` — new `[Unreleased]` entry (TASK-6.2, content verified accurate).
- `docs/dev/architecture/workspace-migration-runbook.md` — new "Enforcement Flag Reference"
  section (TASK-6.3, content verified accurate).
- `docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`
  — TASK-6.5 finalization fields plus this session's corrective revert + OQ-4.
- `.claude/progress/wksp-304-workspace-isolation-enforcement/phase-6-progress.md` — all 5 task
  statuses `completed`; phase-level `status: blocked`.

### Files Changed (committed)

- `src/research_foundry/config.py` — docstring-only, commit `3d24b6d` (TASK-6.4, self-committed by
  the implementer per the project's git-workflow rule; verified zero executable-line diff).

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | TASK-6.2, TASK-6.3, TASK-6.4 | completed | changelog-generator, documentation-writer (×2) |
| 2 | TASK-6.1 | completed | python-backend-engineer |
| 3 | TASK-6.5 | completed | documentation-writer |
| gate | task-completion-validator | FIX-REQUIRED (karen gate missing) | task-completion-validator |
| gate | karen (end-of-feature, remediation dispatch) | NOT APPROVED | karen |

### Follow-Up Recommendations

1. **Opus/user must explicitly authorize** a Mode-D remediation task (new, out of Phase 6's own
   scope) mirroring the P5.5b pattern: add a keyword-only `identity` parameter to
   `create_draft_from_run` and `create_draft_from_collection` in `builder_service.py`, wire
   `identity=identity` at both call sites in `reports.py`, and thread `identity` into the
   unscoped `catalog_service.get_item()` call inside `create_draft_from_collection`.
2. After that fix lands: add a targeted cross-workspace collection-seed regression test, re-run
   the `-k "workspace or isolation or enforcement"` suite, then re-dispatch both
   `task-completion-validator` and `karen` for a clean re-gate.
3. Only after karen's re-gate returns APPROVED should the plan/progress frontmatter be re-advanced
   to `status: completed` / `planning_maturity: shipped` — do not re-apply those values manually
   without a fresh karen pass.
4. The uncommitted Phase 6 doc changes (CHANGELOG, runbook, plan frontmatter, progress file) are
   content-accurate and validator-confirmed; Opus may choose to commit them now as
   "Phase 6 docs (blocked pending Mode-D fix)" or hold them until the fix lands and commit
   everything together — either is reasonable; I deferred that call rather than committing under
   a Mode-D block per my operating rules.

---

## Remediation Update (phase-owner, Mode C within phase scope; Mode-D fix authorized)

**Status**: PASS — phase unblocked.
**Validator verdict**: `karen` (end-of-feature re-gate) — **APPROVED**.
**Isolation**: shared
**Branch**: main (no worktree)

### Authorized scope

Opus/the user reviewed karen's NOT APPROVED verdict above and authorized a **bounded fix**: close
exactly the two named HIGH-severity gaps now; defer the full-surface completeness audit karen's
finding implied to a tracked follow-up (not open-endedly audit/refactor beyond the two named paths).

### What was fixed

1. **Identity threading** — `create_draft_from_run` and `create_draft_from_collection`
   (`src/research_foundry/services/builder_service.py:999`, `:1085`) now accept
   `identity: AuthIdentity | None = None`, mirroring `create_draft`'s existing AC-6 contract, and
   forward it into the inner `create_draft()` call. `src/research_foundry/api/routers/reports.py`
   call sites (`:252`, `:273`) now pass `identity=identity`; the stale P4 TODO comments were removed.
2. **Cross-workspace read leak closed** — `create_draft_from_collection` now passes
   `identity=identity` into `catalog_service.get_item(...)` (`builder_service.py:1120`), which
   already had genuine fail-closed workspace scoping (P3) — it just wasn't being given the caller's
   identity. A cross-workspace catalog item now resolves to `None` and falls through the existing
   "unresolved ids are skipped" path instead of being embedded.

New regression tests in `tests/test_workspace_isolation_enforcement.py`
(`TestCreateDraftFromRunAndCollectionIdentityThreading`): legit-owner-allowed for both functions,
the critical leak-closed test (`test_create_draft_from_collection_cross_workspace_catalog_item_not_embedded`),
and `identity=None` byte-identical baselines for both functions (AC-6).

### Verification (all four held before commit)

1. New leak/deny tests pass — 5/5 new tests green; the discriminating pair (legit-owner-allowed vs.
   cross-workspace-not-embedded) genuinely proves the leak closed (confirmed independently by
   `karen`, not just by the implementer).
2. Full suite via `.venv/bin/python -m pytest`: **914 passed, 1 xfailed, 0 failed**
   (`tests/unit/` + `tests/test_workspace_isolation_enforcement.py` +
   `tests/test_config_workspace_enforcement.py`); `tests/test_serve_api.py` untouched, excluded per
   the known pre-existing baseline.
3. AC-6 (single-operator `identity=None` fallback): re-confirmed unbroken via two explicit baseline
   tests plus the full-suite pass.
4. `karen` re-ran the end-of-feature gate independently (own verification, not just reading the
   implementer's report) and returned **APPROVED**, explicitly confirming: (a) both named gaps
   correctly and completely fixed, (b) the leak-closed test is discriminating (fails against the
   pre-fix code), (c) AC-6 baseline provably intact, (d) the deferral bookkeeping (OQ-4 / DI-1) is
   honest and gate-worthy. She found no new leak inside the reviewed code. Two non-blocking nits
   (OQ-4 wording said "P3 commits" before the commit existed; `deferred_items_spec_refs` empty)
   were addressed in finalization below.

### Deferral bookkeeping (recorded, not silently dropped)

- Plan file OQ-4 (`open_questions[3]`): `status` → `resolved-bounded-fix`; text now names commit
  `eba75ab` and karen's APPROVED re-gate, and points at DI-1 for the remaining deferral.
- Plan file "Deferred Items" section: replaced the stale "N/A — no deferred items" claim with
  **DI-1: Full workspace-data-access completeness audit** (all read/create/list/delete service
  paths, every service) — marked a **hard pre-deploy gate for any shared-store multi-tenant
  deployment**. Original FR-1..FR-10 / AC-1..AC-7 scope remains fully covered; DI-1 is a new
  deferral discovered by end-of-feature review, not an original-scope gap.

### Commits

- `eba75ab` — `fix(wksp-304): thread identity into create_draft_from_run/from_collection + scope
  get_item leak` (source: `builder_service.py`, `reports.py`; tests:
  `test_workspace_isolation_enforcement.py`).
- `docs(wksp-304): P6 CHANGELOG + runbook + finalize plan (defer full-surface audit)` — docs +
  progress + plan finalization + this note (committed immediately after this note is written).

### Batch Summary (remediation round)

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | Fix identity threading + close leak + tests | completed | python-backend-engineer |
| 1 | Deferral bookkeeping (OQ-4 + DI-1) | completed | documentation-writer |
| gate | End-of-feature re-gate | APPROVED | karen |

### Final Status

Phase 6 `status: completed`. Plan `status: completed`, `planning_maturity: shipped`. All five
Phase 6 tasks (TASK-6.1–6.5) remain `completed` from the original round; this remediation closes
the previously-unmet exit criterion ("karen end-of-feature review passes").

### Follow-Up Recommendations

1. DI-1 (full workspace-data-access completeness audit) is a **hard pre-deploy gate** — must close
   before any shared-store multi-tenant deployment. Not urgent while enforcement defaults to
   advisory (`provider="none"`), but must not be forgotten before that flip.
2. Consider populating `deferred_items_spec_refs` with a dedicated DI-1 spec doc if/when that audit
   is scheduled, so `ac-coverage-report.py`/CCDash can track it structurally (currently DI-1 lives
   inline in the plan body only — karen flagged this as a non-blocking nit).
