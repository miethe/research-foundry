---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release-activation
feature_slug: public-multiuser-release-activation
title: "Phase 3: Admin API"
phase: 3
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
  - id: "ACT-301"
    description: "Admin API — service accounts (issue/list/revoke/rotate routes, require_role gated)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2 sealed"]
  - id: "ACT-302"
    description: "Admin API — PATs (self-issue/list/revoke, self-vs-admin scoping)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2 sealed"]
  - id: "ACT-303"
    description: "Admin API — deployment-mode-status endpoint + audit_event wiring on every mutation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-301", "ACT-302"]

parallelization:
  batch_3: ["ACT-301", "ACT-302", "ACT-303"]
---

# Phase 3: Admin API

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update via CLI:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/public-multiuser-release-activation/phase-3-progress.md -t ACT-301 -s completed
```

## Task Table

| Task ID | Task Name | Assigned To | Dependencies | Status |
|---------|-----------|-------------|---------------|--------|
| ACT-301 | Admin API — service accounts | python-backend-engineer | P2 sealed | pending |
| ACT-302 | Admin API — PATs | python-backend-engineer | P2 sealed | pending |
| ACT-303 | Admin API — deployment-mode-status + audit wiring | python-backend-engineer | ACT-301, ACT-302 | pending |

## Reviewer Gates

| Gate ID | Reviewer | Mode | Trigger | Status |
|---------|----------|------|---------|--------|
| REV-P3-001 | senior-code-reviewer (error-envelope + no-secret-leak) | E — Reviewer | ACT-301, ACT-302, ACT-303 | pending |
| REV-P3-002 | task-completion-validator | E — Reviewer | REV-P3-001 | pending |

## Exit Criteria

- `require_role` route sweep green.
- No raw secret in any response except one-time issuance.
- `task-completion-validator` pass.

## Notes

- Depends on Phase 2 being fully sealed (karen milestone REV-P2-002 passed) — `token_service.py` must exist and be reviewed before this phase starts.
- Thin, RBAC-gated CRUD surface over the already-reviewed P2 service layer — never touches the composite auth chain or token store schema directly.
- Blocks Phase 5 (Admin UI is deliberately sequenced last, consuming these endpoints).
