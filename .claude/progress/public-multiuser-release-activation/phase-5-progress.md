---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release-activation
feature_slug: public-multiuser-release-activation
title: "Phase 5: Admin UI"
phase: 5
status: pending
created: 2026-07-22
updated: 2026-07-22
prd_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
commit_refs: []
pr_refs: []

owners: ["ui-engineer-enhanced"]
contributors: []

tasks:
  - id: "ACT-501"
    description: "Admin UI — service accounts panel (issue/list/revoke/rotate, one-time-secret display with copy-and-dismiss UX)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3 sealed"]
  - id: "ACT-502"
    description: "Admin UI — PATs panel + AuthContext.tsx principalType extension"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3 sealed"]
  - id: "ACT-503"
    description: "[R-P4] Runtime smoke + a11y pass — issue/list/revoke/rotate round-trip against live API + WCAG 2.1 AA (jest-axe)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced", "a11y-sheriff"]
    dependencies: ["ACT-501", "ACT-502"]

parallelization:
  batch_4: ["ACT-501", "ACT-502", "ACT-503"]
---

# Phase 5: Admin UI

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update via CLI:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/public-multiuser-release-activation/phase-5-progress.md -t ACT-501 -s completed
```

## Task Table

| Task ID | Task Name | Assigned To | Dependencies | Status |
|---------|-----------|-------------|---------------|--------|
| ACT-501 | Admin UI — service accounts panel | ui-engineer-enhanced | P3 sealed | pending |
| ACT-502 | Admin UI — PATs panel + auth-context | ui-engineer-enhanced | P3 sealed | pending |
| ACT-503 | [R-P4] Runtime smoke + a11y pass | ui-engineer-enhanced, a11y-sheriff | ACT-501, ACT-502 | pending |

## Reviewer Gates

| Gate ID | Reviewer | Mode | Trigger | Status |
|---------|----------|------|---------|--------|
| REV-P5-001 | task-completion-validator | E — Reviewer | ACT-503 | pending |

## Exit Criteria

- AC-1 (one-time-secret UX + principal-type surfacing) green.
- a11y smoke (WCAG 2.1 AA) passed.
- `task-completion-validator` pass.

## Notes

- Deliberately sequenced last among backend-adjacent phases — must not ship ahead of the backend (decisions-block §3 risk).
- Highest-risk UI element: the plaintext one-time secret must never persist beyond local component state (verified in ACT-503).
- Additive to the existing `AdminSettings/RoleAssignmentPanel.tsx` surface — no new route tree.
