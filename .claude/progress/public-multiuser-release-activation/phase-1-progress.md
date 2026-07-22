---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release-activation
feature_slug: public-multiuser-release-activation
title: "Phase 1: Deployment-Mode Presets"
phase: 1
status: pending
created: 2026-07-22
updated: 2026-07-22
prd_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
commit_refs: []
pr_refs: []

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "ACT-101"
    description: "Deployment-mode resolver (Config.deployment_mode(); compose single_user/multi_user presets over the 5 existing per-knob resolvers)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ACT-102"
    description: "`rf serve --mode` CLI flag + startup gate stub (Config.deployment_mode_validate(), conditions a-c only)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-101"]

parallelization:
  batch_1: ["ACT-101", "ACT-102"]
---

# Phase 1: Deployment-Mode Presets

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update via CLI:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/public-multiuser-release-activation/phase-1-progress.md -t ACT-101 -s completed
```

## Task Table

| Task ID | Task Name | Assigned To | Dependencies | Status |
|---------|-----------|-------------|---------------|--------|
| ACT-101 | Deployment-mode resolver | python-backend-engineer | None | pending |
| ACT-102 | `--mode` CLI flag + startup gate stub | python-backend-engineer | ACT-101 | pending |

## Reviewer Gates

| Gate ID | Reviewer | Mode | Trigger | Status |
|---------|----------|------|---------|--------|
| REV-P1-001 | task-completion-validator | E — Reviewer | After ACT-101, ACT-102 | pending |

## Exit Criteria

- FR-2 byte-identical resolved-config regression test green.
- `task-completion-validator` pass (REV-P1-001).

## Notes

- Highest-severity risk in this phase: `single_user` preset must remain byte-identical to today's default (LAN/NUC) behavior — see plan Risk Mitigation table.
- `cli_commands.py` (2,755 lines, H7 flag) is touched by ACT-102 — anti-blow guardrail applies (grep -n + sed only, no whole-file read, budget ≤40 tool uses).
- Does not wire the DI-1 acknowledgment condition (d) — that lands in Phase 4 (ACT-402); this phase ships the gate stub only.
