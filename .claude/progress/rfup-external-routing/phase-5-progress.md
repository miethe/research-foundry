---
type: progress
schema_version: 2
doc_type: progress
prd: rfup-external-routing
feature_slug: rfup-external-routing
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
execution_model: batch-parallel
phase: 5
title: Native-Adapter SPIKE + ADR-0008 Verdict (Eval-Only)
status: completed
started: '2026-07-22T00:00:00Z'
completed: '2026-07-22T00:00:00Z'
commit_refs:
- 8a2a2eb
- 702ae95
- 987a37b
- c18cc18
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- spike-writer
contributors:
- search-specialist
model_usage:
  primary: opus
  external: []
tasks:
- id: P5-001
  description: 'Static metadata review of litellm: maintainer activity, release cadence,
    CVE history (public advisory databases, no auth), dependency count via PyPI''s
    published metadata.'
  status: completed
  assigned_to:
  - spike-writer
  - search-specialist
  dependencies: []
  estimated_effort: 1pt
  priority: high
  assigned_model: opus
  model_effort: adaptive
- id: P5-002
  description: 'pip download --no-deps litellm inspection: obtain wheel/sdist without
    installing; inspect declared dependency tree (METADATA/requires.txt) and top-level
    code surface (module list, no import/execution).'
  status: completed
  assigned_to:
  - spike-writer
  dependencies:
  - P5-001
  estimated_effort: 1pt
  priority: high
  assigned_model: opus
  model_effort: adaptive
- id: P5-003
  description: Cross-reference existing litellm_router.py adapter (incl. the 2d198a8
    ICA-provider mapping fix) against P5-001/P5-002 findings to assess integration
    weight if accepted.
  status: completed
  assigned_to:
  - spike-writer
  dependencies:
  - P5-002
  estimated_effort: 1pt
  priority: high
  assigned_model: opus
  model_effort: adaptive
- id: P5-004
  description: Accept/reject/conditional verdict + (unexecuted) install/wiring plan,
    synthesizing P5-001 through P5-003; evaluation-method limitations documented explicitly.
  status: completed
  assigned_to:
  - spike-writer
  dependencies:
  - P5-003
  estimated_effort: 2pts
  priority: high
  assigned_model: opus
  model_effort: adaptive
parallelization:
  batch_1:
  - P5-001
  batch_2:
  - P5-002
  batch_3:
  - P5-003
  batch_4:
  - P5-004
  critical_path:
  - P5-001
  - P5-002
  - P5-003
  - P5-004
  estimated_total_time: 5pts
blockers: []
success_criteria:
- id: SC-1
  description: Accept/reject verdict recorded with an install/wiring plan
  status: pending
- id: SC-2
  description: 0 live external calls, 0 credentials used during evaluation
  status: pending
- id: SC-3
  description: task-completion-validator pass
  status: pending
files_modified: []
notes: "Wave 1 (parallel with P1, no shared files). EVAL-ONLY (Hard Constraint 2):\
  \ no install, no live external calls, no credentials \u2014 the ADR-0008 accept/reject\
  \ verdict is the sole deliverable. This phase doubles as the plan's Tier-3 SPIKE-equivalent."
progress: 100
updated: '2026-07-22'
---

# rfup-external-routing - Phase 5: Native-Adapter SPIKE + ADR-0008 Verdict (Eval-Only)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/rfup-external-routing/phase-5-progress.md -t P5-001 -s completed --started <ISO8601> --completed <ISO8601> --evidence "artifact:.claude/worknotes/rfup-external-routing/litellm-router-eval.md"
```

---

## Objective

Evaluate `litellm_router` (static-only: PyPI/GitHub metadata + `pip download --no-deps` inspection) and produce a citable accept/reject/conditional verdict against ADR-0008 (`pediatric-anemia-site`, currently `proposed`), plus an unexecuted install/wiring plan.

---

## Implementation Notes

### Architectural Decisions

Evaluation method is static-only per parent plan decision: PyPI/GitHub metadata review + `pip download --no-deps` dependency-tree/code-surface inspection — satisfies the hard no-install/no-live-call/no-credentials constraint while still producing a non-hand-wavy verdict.

### Patterns and Best Practices

Full task detail, ACs (AC-P5-1 through AC-P5-15), and quality gates: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-5-adapter-eval.md`.

### Known Gotchas

- `pip download --no-deps litellm` must run in a scratch/temp location, never the project venv; `import litellm` is never executed.
- The `2d198a8` ICA-provider mapping fix (pre-dates this branch) is forward-compat correctness work for *when* `litellm` is later installed — factor it into the verdict, don't treat the adapter as a from-scratch install.
- Working artifact is `.claude/worknotes/rfup-external-routing/litellm-router-eval.md`; it feeds P6-003 (DOC-006b), which formalizes the verdict into the durable design-spec.

### Development Setup

None beyond a scratch/temp directory for the `pip download` step.

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
