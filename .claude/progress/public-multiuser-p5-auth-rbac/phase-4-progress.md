---
schema_version: 2
doc_type: progress
prd: public-multiuser-p5-auth-rbac
feature_slug: public-multiuser-p5-auth-rbac
phase: 4
status: completed
created: 2026-07-07
updated: '2026-07-07'
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
phase_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-4-clerk-adapter.md
commit_refs: []
pr_refs: []
completion_ref: .claude/progress/public-multiuser-p5-auth-rbac/phase-4-completion.md
owners:
- backend-architect
- ui-engineer-enhanced
contributors: []
tasks:
- id: CLK-4.1
  title: ClerkAuthProvider JWKS verify
  status: completed
  assigned_to:
  - backend-architect
  dependencies: []
  files_affected:
  - src/research_foundry/api/auth/adapters/clerk.py
  - tests/fixtures/auth/clerk_jwks_fixture.json
  - tests/unit/test_clerk_adapter.py
  started: null
  completed: null
  verified_by: []
  evidence:
  - note: 22/22 unit tests pass; ruff clean; commit 4807927
- id: CLK-4.2
  title: Clerk Organizations role mapping
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CLK-4.1
  files_affected:
  - src/research_foundry/api/auth/adapters/clerk.py
  - tests/unit/test_clerk_adapter.py
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: CLK-4.3
  title: Config-flag dark-by-default wiring
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CLK-4.1
  - CLK-4.2
  files_affected:
  - src/research_foundry/api/auth/adapters/clerk.py
  - src/research_foundry/config.py
  - foundry.yaml
  - tests/unit/test_clerk_adapter.py
  started: null
  completed: null
  verified_by: []
  evidence: []
- id: CLK-4.4
  title: OIDC seam Protocol conformance cross-check
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CLK-4.1
  files_affected:
  - tests/unit/test_auth_provider_protocol_conformance.py
  started: null
  completed: null
  verified_by: []
  evidence:
  - note: 23 passed, 1 xfailed (oidc registry, as expected); all conformance checks
      green
- id: CLK-4.5
  title: Minimal FE Clerk login hook (useClerkAuth.ts)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CLK-4.1
  files_affected:
  - frontend/runs-viewer/src/auth/useClerkAuth.ts
  - frontend/runs-viewer/src/auth/useClerkAuth.test.ts
  started: '2026-07-07T18:30:00Z'
  completed: '2026-07-07T18:40:00Z'
  verified_by: []
  evidence:
  - test: frontend/runs-viewer/src/auth/useClerkAuth.test.ts
  - note: 9/9 vitest pass; hook + test files created
- id: CLERK-900
  title: "Seam verification \u2014 FE Clerk login flow round-trips against backend\
    \ JWKS verify"
  status: completed
  assigned_to:
  - backend-architect
  - ui-engineer-enhanced
  dependencies:
  - CLK-4.1
  - CLK-4.5
  files_affected:
  - tests/integration/test_clerk_login_seam.py
  started: null
  completed: null
  verified_by: []
  evidence: []
parallelization:
  batch_1:
  - CLK-4.1
  batch_2:
  - CLK-4.2
  - CLK-4.4
  - CLK-4.5
  batch_3:
  - CLK-4.3
  batch_4:
  - CLERK-900
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 4: Clerk Adapter + OIDC Seam Cross-Check + Minimal FE Login Hook

**Phase**: P5.4 (Clerk Adapter — opt-in provider)
**Status**: in_progress
**Worktree branch**: worktree-agent-a8f505b7becbcdd13

## Progress

| Batch | Task | Status | Agent |
|-------|------|--------|-------|
| 1 | CLK-4.1 | pending | backend-architect |
| 2 | CLK-4.2 | pending | backend-architect |
| 2 | CLK-4.4 | pending | backend-architect |
| 2 | CLK-4.5 | pending | ui-engineer-enhanced |
| 3 | CLK-4.3 | pending | backend-architect |
| 4 | CLERK-900 | pending | backend-architect + ui-engineer-enhanced |

## Gate #3 status
Human Gate #3 NOT triggered — all work uses JWKS fixture only, no real Clerk secrets.
