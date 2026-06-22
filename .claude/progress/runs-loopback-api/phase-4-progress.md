---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 4
title: Auth & LAN (Gated)
status: pending
created: '2026-06-22'
updated: '2026-06-22'
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- senior-code-reviewer
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P4-001
  description: "Implement pre-bind validation in rf serve command. Before uvicorn.run(): if bind_host==0.0.0.0 and auth_mode!=token -> print error and sys.exit(1). If auth_mode==token and token env var not set -> print error and sys.exit(1)."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-001
  estimated_effort: "0.75 pts"
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  ac_ref: "rf serve --bind-host 0.0.0.0 --auth-mode none exits non-zero before binding; --auth-mode token with token unset exits non-zero; loopback with auth_mode=none starts normally"

- id: P4-002
  description: "Implement src/research_foundry/api/middleware/auth.py as Starlette middleware. When auth_mode==token: extract Authorization: Bearer <token>; compare with hmac.compare_digest; return 401 if missing/invalid. GET /health always unauthenticated. When auth_mode==none: no-op (do not add to app)."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P4-001
  estimated_effort: "1.0 pts"
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  ac_ref: "Valid token -> 200; missing header -> 401; invalid token -> 401; GET /health always 200; hmac.compare_digest used; no token in any log line"

- id: P4-003
  description: "Implement src/research_foundry/api/middleware/allowlist.py. When viewer.allowlist non-empty: extract client IP; if not in allowlist -> HTTP 403. When allowlist empty -> no-op. Wire into create_app() after CORS and before auth."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P4-002
  estimated_effort: "0.5 pts"
  priority: high
  assigned_model: sonnet
  model_effort: extended
  ac_ref: "Non-empty allowlist blocks unlisted IP with 403; empty allowlist allows all IPs; allowlist middleware applied before auth"

- id: P4-004
  description: "Add ## Threat Model section to docs/dev/architecture/adr-runs-read-path.md (or standalone threat model doc). Document 5 threats: unauthenticated LAN exposure, token timing attack, IP bypass, token in config file, auth_mode=none on 0.0.0.0."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P4-003
  estimated_effort: "0.25 pts"
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Threat model section exists with all 5 threats documented; linked from ADR"

- id: P4-SEAM
  description: "Define and document auth-header propagation contract for P5 in both api/middleware/auth.py (comment block) and client.ts (loopbackGet note). Contract: loopbackGet MUST send Authorization: Bearer ${token} when VITE_RUNS_LOOPBACK_API_TOKEN set (non-empty). No token -> header omitted. Zero-cost documentation task."
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P4-002
  estimated_effort: "0 pts"
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: "Contract comment exists in both files; P5 implementer can implement FE-side without ambiguity; no circular dependency"

parallelization:
  batch_1:
  - P4-001
  batch_2:
  - P4-002
  batch_3:
  - P4-003
  - P4-SEAM
  batch_4:
  - P4-004
  critical_path:
  - P4-001
  - P4-002
  - P4-003
  - P4-004
  estimated_total_time: "1.5 days"

blockers: []

success_criteria:
- id: SC-P4-1
  description: "rf serve --bind-host 0.0.0.0 --auth-mode none exits non-zero before binding"
  status: pending
- id: SC-P4-2
  description: "rf serve --bind-host 0.0.0.0 --auth-mode token with token unset exits non-zero"
  status: pending
- id: SC-P4-3
  description: "Valid token -> 200; missing/invalid token -> 401; GET /health always 200"
  status: pending
- id: SC-P4-4
  description: "IP allowlist blocks non-listed IPs with 403"
  status: pending
- id: SC-P4-5
  description: "hmac.compare_digest used for token comparison (senior-code-reviewer verified)"
  status: pending
- id: SC-P4-6
  description: "No token value appears in any log line or exception message"
  status: pending
- id: SC-P4-7
  description: "Threat model written and linked from ADR"
  status: pending
- id: SC-P4-8
  description: "Auth-header propagation contract documented (P4-SEAM)"
  status: pending
- id: SC-P4-9
  description: "karen checkpoint passed before P5 begins"
  status: pending

files_modified:
- src/research_foundry/api/middleware/auth.py
- src/research_foundry/api/middleware/allowlist.py
- src/research_foundry/api/app.py
- docs/dev/architecture/adr-runs-read-path.md
---

# runs-loopback-api - Phase 4: Auth & LAN (Gated)

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Implement fail-closed LAN bind gating, token auth middleware, IP allowlist middleware, written threat model, and auth-header propagation contract seam for P5. This is Wave 3, executed in an ISOLATED WORKTREE. Requires P2 and P3 complete.

## Implementation Notes

**This phase is Mode D-adjacent (network-exposure surface). An isolated worktree is MANDATORY.**
**A `karen` checkpoint is required after this phase passes before P5 begins.**

Security invariants that must hold at phase exit:
- `bind_host=0.0.0.0` without `auth_mode=token` + configured token -> server exits non-zero BEFORE binding
- Token comparison uses `hmac.compare_digest` exclusively
- No token logging (not in stdout, not in error messages, not in stack traces)
- IP allowlist (when non-empty) blocks unmatched IPs with HTTP 403

P4-SEAM and P4-003 can be executed in parallel after P4-002 completes — they are disjoint.
