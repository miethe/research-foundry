---
title: "Phase 1: Path-B Test Hardening"
schema_version: 2
doc_type: phase_plan
status: draft
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
phase: 1
phase_title: "Path-B test hardening"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
entry_criteria: []
exit_criteria:
  - "node --test .claude/workflows/__tests__/rf-run-execute.test.js passes"
  - "node --test .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js passes"
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces: []
seam_tasks: []
owner: null
contributors: []
priority: high
risk_level: low
category: enhancements
tags: [phase-plan, testing, path-b]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - .claude/workflows/__tests__/rf-run-execute.test.js
  - .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js
---

# Phase 1: Path-B Test Hardening

**Parent Plan**: [rfup-external-routing-v1.md](../rfup-external-routing-v1.md)
**Wave**: 1 (∥ P5, no shared files)
**Effort**: 2 pts
**Dependencies**: None
**Agents**: python-backend-engineer (sonnet, adaptive)

## Phase Overview

Both `.claude/workflows/rf-run-execute.js` and `.claude/workflows/rf-pediatric-cds-run-execute.js` are already fully args-driven (per state-audit: `resolvePath()`, `stampFromTimestamp()`, no `Date.now()`/`new Date()` in either script body). **This phase adds test coverage only — no script logic changes.** Zero test files reference either script today (confirmed via repo-wide grep at planning time).

### Goals

- Cover `stampFromTimestamp()` parsing behavior (valid ISO, malformed, absent→fallback) for both scripts.
- Cover path-injection / override-precedence behavior (`rf_bin`/`repo`/`tmp_dir`/`run_id` args win over literal fallback defaults; no path-traversal escape from invocation cwd) for both scripts.
- Unblock `DF-E1-02` (scheduled/unattended Path-B cadence) per the PRD's Outcome 3.

### Decisions in force (from parent plan frontmatter — do not re-litigate)

- **Test harness**: Node's built-in `node:test` + `node --test`. No `--experimental-*` flag needed; confirmed available on Node 20.19.3 in this environment. No existing JS test harness elsewhere in the repo to match instead.
- **File locations**: `.claude/workflows/__tests__/rf-run-execute.test.js` and `.claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js` (new `__tests__/` directory — none exists in `.claude/workflows/` today).

## Task Breakdown

| Task ID | Task Name | Description | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------|-------------|-------|--------|--------------|
| P1-001 | `rf-run-execute.js` date + path tests | Author `node:test` suite covering `stampFromTimestamp()` (valid ISO/malformed/absent) and `resolvePath()`-driven arg precedence (`rf_bin`, `repo`, `tmp_dir`, `run_id`) with no live `rf` invocation or network access — mock/stub the resolved paths, assert only resolution/precedence logic. | 1 pt | python-backend-engineer | sonnet | adaptive | None |
| P1-002 | `rf-pediatric-cds-run-execute.js` date + path tests | Same coverage pattern as P1-001, applied to `rf-pediatric-cds-run-execute.js`'s `STAMP`/`REPO`/`RF`/`TMP` resolution (note: this script's `RF` fallback is the direct local venv binary path, not the `~/.local/bin/rf` shim — assert that distinction is preserved, not collapsed). | 1 pt | python-backend-engineer | sonnet | adaptive | None |

## Detailed Task Specifications

### Task P1-001: `rf-run-execute.js` date + path tests

**Estimate**: 1 pt · **Model**: sonnet · **Effort**: adaptive · **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-P1-1: `stampFromTimestamp()` returns the expected stamp for a valid ISO-8601 `timestamp` arg.
- [ ] AC-P1-2: `stampFromTimestamp()` falls back to the literal default (`'20260613'`) for a malformed `timestamp` arg (not a thrown error — matches existing fallback behavior, not new behavior).
- [ ] AC-P1-3: `stampFromTimestamp()` falls back to the literal default when `timestamp` is absent entirely.
- [ ] AC-P1-4: `resolvePath()`-driven args (`rf_bin`, `repo`, `tmp_dir`) resolved from explicit input override their literal fallback defaults — assert precedence, not just non-throwing.
- [ ] AC-P1-5: No path-traversal escape from invocation cwd is exercised by any of the above resolution paths (assert the resolved path stays within/relative-to the expected base, per the existing `resolvePath()` contract — this is a regression assertion on existing behavior, not new hardening).
- [ ] AC-P1-6: Test suite makes zero live `rf` binary invocations and zero network calls (mock/stub only) — satisfies PRD Risk mitigation "P1's new tests exercise real rf/filesystem paths and become flaky."

**Files Involved**:
- `.claude/workflows/__tests__/rf-run-execute.test.js` (new) — the test suite itself.
- `.claude/workflows/rf-run-execute.js` (read-only reference; not edited).

### Task P1-002: `rf-pediatric-cds-run-execute.js` date + path tests

**Estimate**: 1 pt · **Model**: sonnet · **Effort**: adaptive · **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-P1-7: `STAMP` resolution covers valid-arg, malformed-arg→fallback (`'20260718'`), and absent-arg→fallback cases, mirroring P1-001's pattern for this script's own arg names.
- [ ] AC-P1-8: `REPO`/`RF`/`TMP` override precedence is asserted, including the explicit distinction that this script's `RF` fallback resolves to the direct local venv binary (`REPO + '/.venv/bin/rf'`), NOT the `~/.local/bin/rf` shim used by `rf-run-execute.js` — a test that doesn't distinguish these two scripts' differing fallback conventions would pass falsely.
- [ ] AC-P1-9: No path-traversal escape from invocation cwd.
- [ ] AC-P1-10: Zero live `rf` invocations, zero network calls in the test suite.

**Files Involved**:
- `.claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js` (new).
- `.claude/workflows/rf-pediatric-cds-run-execute.js` (read-only reference; not edited).

## Quality Gates

This phase is complete when:

- [ ] **Functional**: `node --test .claude/workflows/__tests__/*.test.js` exits 0 for both new suites.
- [ ] **Testing**: All 10 ACs above (AC-P1-1 through AC-P1-10) have a corresponding assertion.
- [ ] **No regressions**: Neither `.js` script's runtime logic is modified — a diff on either script file should be empty.
- [ ] **Security**: Confirmed zero live `rf` invocations and zero network calls in either suite (grep the test files for `child_process`, `fetch`, `http` — none expected).
- [ ] **Architecture**: Follows this repo's workflow-authoring four-constraints checklist (no `Date.now()`/`new Date()` introduced in tests either, to avoid non-determinism).

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Tests exercise real filesystem/`rf` paths and become flaky/environment-coupled (PRD Risks table) | Low | Mock `rf_bin`/`repo`/`tmp` args; assert only resolution/precedence logic, per AC-P1-6/AC-P1-10. |
| `node:test` unfamiliar to reviewers vs. a Python-first convention | Low | Document the harness choice inline in both test files' header comments, referencing this phase's decision. |

## Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0 · **Last Updated**: 2026-07-22

[Return to Parent Plan](../rfup-external-routing-v1.md)
