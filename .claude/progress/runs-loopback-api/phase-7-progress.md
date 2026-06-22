---
type: progress
schema_version: 2
doc_type: progress
prd: runs-loopback-api
feature_slug: runs-loopback-api
phase: 7
title: Deploy & Docs
status: completed
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
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- documentation-writer
contributors:
- python-backend-engineer
- changelog-generator
execution_model: batch-parallel
model_usage:
  primary: haiku
  external: []
tasks:
- id: DOC-001
  description: 'Add entries under [Unreleased] in CHANGELOG.md: Added rf serve command,
    Added Loopback API mode, Added Gated LAN exposure. Follow Keep A Changelog format.
    Set changelog_ref: CHANGELOG.md in plan frontmatter.'
  status: completed
  assigned_to:
  - changelog-generator
  dependencies:
  - P6-quality-gates
  estimated_effort: 0.2 pts
  priority: high
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: Three Added entries under [Unreleased]; no Released date set; changelog_ref
    frontmatter updated
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-002
  description: 'Update docs/dev/architecture/adr-runs-read-path.md to record dual-mode
    read path: (1) static export via rf run export --json, (2) live loopback API via
    rf serve. Link to PRD and threat model from P4-004. Update ADR status to amended.'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P4-004
  estimated_effort: 0.2 pts
  priority: medium
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: ADR records both read paths; threat model linked; ADR status updated to
    amended
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-003
  description: 'Update project README.md with rf serve usage: basic loopback mode,
    LAN mode with token, env vars table, port defaults, note on MeatyWiki conflict.'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - DOC-001
  estimated_effort: 0.2 pts
  priority: medium
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: README includes rf serve section with loopback and LAN examples; port default
    7432 documented; env vars table present
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-004
  description: Author systemd/rf-serve.service unit file. Unit runs rf serve as agentic-nuc
    user with RUNS_FRONTEND_LOOPBACK_API=true and RF_SERVE_TOKEN sourced from env
    file. Include Restart=on-failure, RestartSec=5. Not auto-enabled.
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DOC-003
  estimated_effort: 0.2 pts
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  ac_ref: Unit file syntactically valid (systemd-analyze verify); environment file
    pattern documented; not auto-enabled
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-005
  description: 'Update docs/project_plans/design-specs/runs-loopback-api.md: set maturity:promoted,
    prd_ref set. Annotate deferred item DEF-03 (fs-watch hot-reload) in ## Deferred
    (v2) section. Append spec path to deferred_items_spec_refs in plan frontmatter.'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - DOC-001
  estimated_effort: 0.1 pts
  priority: medium
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: maturity:promoted, prd_ref set, deferred fs-watch annotated; deferred_items_spec_refs
    updated
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-006
  description: 'Update docs/project_plans/design-specs/runs-auth-lan.md: set maturity:promoted,
    prd_ref set. Annotate deferred items DEF-01 (mTLS) and DEF-02 (SSH-tunnel) in
    ## Deferred (v2) section with rationale and promotion trigger. Append spec path
    to deferred_items_spec_refs.'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - DOC-001
  estimated_effort: 0.1 pts
  priority: medium
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: maturity:promoted, prd_ref set; mTLS and SSH-tunnel deferred sections annotated
    with rationale and promotion condition; deferred_items_spec_refs updated
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
- id: DOC-007
  description: Set status:completed, populate commit_refs, files_affected, deferred_items_spec_refs
    (three design spec paths), updated date in implementation plan frontmatter.
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - DOC-005
  - DOC-006
  estimated_effort: 0.1 pts
  priority: medium
  assigned_model: haiku
  model_effort: adaptive
  ac_ref: Plan frontmatter reflects completed state; all three deferred spec refs
    present
  started: '2026-06-22T16:22:00Z'
  completed: '2026-06-22T16:29:00Z'
  evidence:
  - commit: pending-wave6
parallelization:
  batch_1:
  - DOC-001
  - DOC-002
  batch_2:
  - DOC-003
  - DOC-005
  - DOC-006
  batch_3:
  - DOC-004
  batch_4:
  - DOC-007
  critical_path:
  - DOC-001
  - DOC-003
  - DOC-004
  - DOC-007
  estimated_total_time: 0.5 days
blockers: []
success_criteria:
- id: SC-P7-1
  description: CHANGELOG [Unreleased] has all three Added entries
  status: pending
- id: SC-P7-2
  description: ADR records dual-mode read path and links threat model
  status: pending
- id: SC-P7-3
  description: README documents rf serve usage with examples
  status: pending
- id: SC-P7-4
  description: systemd unit file authored and syntactically valid
  status: pending
- id: SC-P7-5
  description: Both design specs promoted (maturity:promoted, prd_ref set)
  status: pending
- id: SC-P7-6
  description: 'Both specs have ## Deferred (v2) sections with annotated deferred
    items'
  status: pending
- id: SC-P7-7
  description: deferred_items_spec_refs in plan frontmatter has three paths
  status: pending
- id: SC-P7-8
  description: Plan frontmatter finalized (status:completed)
  status: pending
files_modified:
- CHANGELOG.md
- docs/dev/architecture/adr-runs-read-path.md
- README.md
- systemd/rf-serve.service
- docs/project_plans/design-specs/runs-loopback-api.md
- docs/project_plans/design-specs/runs-auth-lan.md
- docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
progress: 100
---

# runs-loopback-api - Phase 7: Deploy & Docs

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## Objective

Complete CHANGELOG, ADR, README, systemd unit, promote both design specs with deferred-item annotations, and finalize plan frontmatter. Wave 6; requires P6 complete with all quality gates green.

## Implementation Notes

- documentation-writer (haiku) handles ADR/CHANGELOG/specs (DOC-001 to DOC-006 except DOC-004).
- python-backend-engineer (sonnet) handles the systemd unit (DOC-004).
- DOC-001 and DOC-002 can run in parallel (first batch).
- DOC-003, DOC-005, DOC-006 can run in parallel after DOC-001 (second batch).
- DOC-004 depends on DOC-003 for README context.
- DOC-007 depends on DOC-005 and DOC-006 (both spec paths must be set before finalizing).

**P7 cannot be sealed until**:
- All three deferred items (DEF-01, DEF-02, DEF-03) have their design-spec annotation tasks completed.
- If `findings_doc_ref` is populated, findings doc is finalized and advanced to `accepted`.

**Deferred items reference**:
- DEF-01: mTLS auth mode -> runs-auth-lan.md Deferred (v2)
- DEF-02: SSH-tunnel auth mode -> runs-auth-lan.md Deferred (v2)
- DEF-03: Filesystem-watch hot-reload cache -> runs-loopback-api.md Deferred (v2)
