---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 3
title: Backfill
status: pending
created: '2026-07-24'
updated: '2026-07-24'
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ica-executor
contributors:
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-3.1
  description: 'term_index_backfill.py service: new service modeled on services/rights_backfill.py;
    dry-run by default, idempotent, additive-only; re-runs the deterministic claim-map
    extraction function (TASK-1.2/1.3) against existing claim_ledger.yaml files
    and writes _term_index in place; never touches verification_status, status,
    or any already-attested field (FR-14)'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 1.0 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-3.2
  description: 'CLI wiring + rf catalog rebuild follow-up: wire the backfill into
    cli_commands.py as a new subcommand; document the mandatory rf catalog rebuild
    follow-up pass so derived catalog tables regenerate from the newly-additive
    source files'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-3.1
  estimated_effort: 0.25 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-3.3
  description: 'Validate against pediatric-CDS bundle population: exercise the backfill''s
    dry-run mode against the 7 existing pediatric-CDS bundles (highest-stakes corpus,
    private data repo); review the dry-run diff before any wet run; wet-run first
    against fixtures only in this task'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-3.2
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-3.4
  description: 'Idempotency + non-clobber tests (EXIT GATE): re-running the backfill
    against an already-indexed ledger with an unchanged vocabulary version is a
    no-op (0 writes); before/after rf verify regression on the real 87-claim pediatric-CDS
    ledger confirms no status change; an interrupted-then-re-run backfill converges
    to the same end state with no duplicate/partial writes'
  status: pending
  assigned_to:
  - ica-executor
  - task-completion-validator
  dependencies:
  - TASK-3.3
  estimated_effort: 0.25 pts
  assigned_model: sonnet
  model_effort: adaptive
parallelization:
  batch_1:
  - TASK-3.1
  batch_2:
  - TASK-3.2
  batch_3:
  - TASK-3.3
  batch_4:
  - TASK-3.4
  critical_path:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  estimated_total_time: 2 pts
blockers:
- id: BLOCKER-P2-GATE
  title: Phase 2 exit gate (TASK-2.7) must be green before this phase starts
  severity: critical
  blocking:
  - TASK-3.1
  resolution: Confirm Phase 2 task-completion-validator review passed before dispatching
    any Phase 3 task
  created: '2026-07-24'
success_criteria:
- Dry-run mode is the default; wet run requires explicit flag
- Idempotent against an unchanged vocabulary version (0 writes on rerun)
- verification_status/status/attested fields never touched (Risk 4 mitigation)
- Dry-run diff against the real 7-bundle pediatric-CDS population reviewed before
  any wet run
- task-completion-validator review passed
files_modified:
- src/research_foundry/services/term_index_backfill.py
- src/research_foundry/cli_commands.py
notes: 'Runs in parallel with Phase 4 (disjoint file ownership -- no shared file
  in either phase''s files_affected). Both fork from the Phase 2 exit gate and join
  at Phase 5.'
---

# claim-term-indexing - Phase 3: Backfill

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-3-progress.md -t TASK-3.1 -s completed
```

---

## Objective

Build an idempotent, dry-run-safe backfill service (modeled on `rights_backfill.py`) that reindexes existing `claim_ledger.yaml` files with `_term_index`, validate it against the real 7-bundle pediatric-CDS population, and prove idempotency + non-clobber of attested fields before any wet run against production data.

---

## Task Table

| Task ID | Task Name | Depends On | Assigned To | Estimate |
|---------|-----------|------------|-------------|----------|
| TASK-3.1 | `term_index_backfill.py` service | Phase 2 | ica-executor | 1.0 pts |
| TASK-3.2 | CLI wiring + `rf catalog rebuild` follow-up | TASK-3.1 | ica-executor | 0.25 pts |
| TASK-3.3 | Validate against pediatric-CDS bundle population | TASK-3.2 | ica-executor | 0.5 pts |
| TASK-3.4 | Idempotency + non-clobber tests (exit gate) | TASK-3.3 | ica-executor + task-completion-validator | 0.25 pts |

---

## Quick Reference — Dispatch Commands

```text
Task(
  subagent_type="ica-executor",
  description="TASK-3.1 + TASK-3.2 backfill service and CLI",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-3.1 and TASK-3.2 from docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (§Phase 3). Requires Phase 2 TASK-2.7 green. Model on services/rights_backfill.py: dry-run default, idempotent, additive-only, never touches verification_status/status/attested fields. Profile: python-backend-engineer."
)

Task(
  subagent_type="ica-executor",
  description="TASK-3.3 dry-run validation against pediatric-CDS bundles",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-3.3 from the claim-term-indexing-v1 implementation plan (§Phase 3): dry-run the backfill against the 7 existing pediatric-CDS bundles and record the reviewed diff; wet-run only against fixtures in this task. Depends on TASK-3.2 being complete."
)

Task(
  subagent_type="task-completion-validator",
  description="TASK-3.4 idempotency + non-clobber gate review",
  prompt="Mode: E — Reviewer. Verify TASK-3.4 idempotency, verify-unchanged, and interrupt-safe convergence properties are proven per docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md Phase 3 acceptance criteria."
)
```

---

## Quality Gates

- [ ] Dry-run mode is the default; wet run requires explicit flag
- [ ] Idempotent against an unchanged vocabulary version (0 writes on rerun)
- [ ] `verification_status`/`status`/attested fields never touched (Risk 4 mitigation)
- [ ] Dry-run diff against the real 7-bundle pediatric-CDS population reviewed before any wet run
- [ ] task-completion-validator review passed

---

## Validation Commands

```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_term_index_backfill.py -v
```

---

## Completion Notes

Fill in when phase is complete: what was built, key learnings, unexpected challenges, recommendations for Phase 5.
