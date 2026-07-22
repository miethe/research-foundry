---
type: progress
schema_version: 2
doc_type: progress
prd: public-multiuser-release-activation
feature_slug: public-multiuser-release-activation
title: "Phase 2: Non-Human Principal Store + Auth Resolution"
phase: 2
status: pending
created: 2026-07-22
updated: 2026-07-22
prd_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
commit_refs: []
pr_refs: []

owners: ["python-backend-engineer", "data-layer-expert"]
contributors: []

tasks:
  - id: "ACT-201"
    description: "Token store schema — service_accounts + access_tokens tables in rbac_store.py (OQ-2 discriminator resolved)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ACT-101"]
  - id: "ACT-202"
    description: "Token issue/verify/revoke service (token_service.py) — hash-at-rest, constant-time verify, PAT role-ceiling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-201"]
  - id: "ACT-203"
    description: "Composite auth chain — AuthProviderMiddleware resolves access_tokens first, falls through to configured provider"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-202"]
  - id: "ACT-204"
    description: "Agent-job identity binding — execution identity resolves to service account under multi_user only"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-203", "ACT-101"]
  - id: "ACT-205"
    description: "Composite-auth + resilience test suite — AC-2 (4 credential states), AC-4, AC-5"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ACT-202", "ACT-203", "ACT-204"]
  - id: "ACT-206"
    description: "[SEAM] Schema<->service integration verification (round-trip issue -> store -> verify -> revoke -> verify-denied)"
    status: "pending"
    assigned_to: ["python-backend-engineer", "data-layer-expert"]
    dependencies: ["ACT-201", "ACT-202"]

parallelization:
  batch_2: ["ACT-201", "ACT-202", "ACT-203", "ACT-204", "ACT-205", "ACT-206"]
---

# Phase 2: Non-Human Principal Store + Auth Resolution

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update via CLI:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/public-multiuser-release-activation/phase-2-progress.md -t ACT-201 -s completed
```

## Task Table

| Task ID | Task Name | Assigned To | Dependencies | Status |
|---------|-----------|-------------|---------------|--------|
| ACT-201 | Token store schema | data-layer-expert | ACT-101 | pending |
| ACT-202 | Token issue/verify/revoke service | python-backend-engineer | ACT-201 | pending |
| ACT-203 | Composite auth chain | python-backend-engineer | ACT-202 | pending |
| ACT-204 | Agent-job identity binding | python-backend-engineer | ACT-203, ACT-101 | pending |
| ACT-205 | Composite-auth + resilience test suite | python-backend-engineer | ACT-202, ACT-203, ACT-204 | pending |
| ACT-206 | [SEAM] Schema<->service integration verification | python-backend-engineer, data-layer-expert | ACT-201, ACT-202 | pending |

## Reviewer Gates

| Gate ID | Reviewer | Mode | Trigger | Status |
|---------|----------|------|---------|--------|
| REV-P2-001 | senior-code-reviewer | E — Reviewer | ACT-202 (token secret handling) | pending |
| REV-P2-002 | karen (security-sensitive milestone) | E — Reviewer | ACT-205 + REV-P2-001 | pending |
| REV-P2-003 | task-completion-validator | E — Reviewer | REV-P2-002 | pending |

## Exit Criteria

- AC-2 (4 credential states) green.
- karen milestone review passed (security-sensitive).
- `task-completion-validator` pass.

## Notes

- Runs in parallel with Phase 4's DI-1 audit (ACT-401/ACT-402) within `batch_2` — do not block on Phase 4.
- Security-sensitive core of the feature: zero plaintext secrets may ever be logged or persisted (static-scan test required).
- `python-backend-engineer` is the declared `integration_owner` for this phase (R-P3 seam: ACT-206).
- Do not proceed to Phase 3 without the karen milestone pass (REV-P2-002) — treat silence as a blocker, not a pass.
