---
type: progress
schema_version: 2
doc_type: progress
prd: "rfup-external-routing"
feature_slug: "rfup-external-routing"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
execution_model: batch-parallel
phase: 1
title: "Path-B Test Hardening"
status: "pending"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 2
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "P1-001"
    description: "rf-run-execute.js date + path tests: node:test suite covering stampFromTimestamp() (valid ISO/malformed/absent) and resolvePath()-driven arg precedence (rf_bin, repo, tmp_dir, run_id); no live rf invocation or network access."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P1-002"
    description: "rf-pediatric-cds-run-execute.js date + path tests: same coverage pattern as P1-001 applied to STAMP/REPO/RF/TMP resolution; assert RF fallback is the direct local venv binary path, not the ~/.local/bin/rf shim."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

parallelization:
  batch_1: ["P1-001", "P1-002"]
  critical_path: []
  estimated_total_time: "2pts"

blockers: []

success_criteria:
  - { id: "SC-1", description: "node --test .claude/workflows/__tests__/rf-run-execute.test.js passes", status: "pending" }
  - { id: "SC-2", description: "node --test .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js passes", status: "pending" }
  - { id: "SC-3", description: "Neither script's runtime logic is modified (diff on each .js file is empty)", status: "pending" }

files_modified: []

notes: "Wave 1 (parallel with P5, no shared files). Tests only — no script logic changes. task-completion-validator gate at phase end. No standalone karen pass at P1 (parent plan's karen milestones are after Wave 3 and after P6 only)."
---

# rfup-external-routing - Phase 1: Path-B Test Hardening

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/rfup-external-routing/phase-1-progress.md -t P1-001 -s completed --started <ISO8601> --completed <ISO8601> --evidence "test:.claude/workflows/__tests__/rf-run-execute.test.js"
```

---

## Objective

Add regression-test coverage (`node:test`) for the two already-args-driven Path-B orchestration scripts (`rf-run-execute.js`, `rf-pediatric-cds-run-execute.js`) — date-stamp fallback behavior and path/arg-precedence — with zero script logic changes. Unblocks `DF-E1-02` (scheduled/unattended Path-B cadence).

---

## Implementation Notes

### Architectural Decisions

Test harness is Node's built-in `node:test` + `node --test` (no `--experimental-*` flag; confirmed on Node 20.19.3). No existing JS test harness elsewhere in the repo. New `__tests__/` directory under `.claude/workflows/`.

### Patterns and Best Practices

Full task detail, ACs (AC-P1-1 through AC-P1-10), and quality gates: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-1-pathb-tests.md`.

### Known Gotchas

- `rf-pediatric-cds-run-execute.js`'s `RF` fallback is the direct local venv binary path, distinct from `rf-run-execute.js`'s `~/.local/bin/rf` shim fallback — tests must assert this distinction, not collapse it.
- Mock/stub resolved paths only; zero live `rf` invocations, zero network calls in either suite.

### Development Setup

None beyond Node 20.19.3 (already available in this environment).

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
