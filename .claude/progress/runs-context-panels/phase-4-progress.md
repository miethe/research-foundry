---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-context-panels"
feature_slug: "runs-context-panels"
prd_ref: "docs/project_plans/PRDs/features/runs-context-panels-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
execution_model: sequential
phase: 4
title: "Tests, Docs & Validation"
status: pending
created: 2026-06-23
updated: 2026-06-23
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: on-track

total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: ["documentation-writer", "changelog-generator", "karen"]

model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "P4-001"
    description: "Complete backend test suite for _build_context() and export pipeline: BE-001 (all-present), BE-002 (each-absent-independently for all 4 fields), BE-003 (redaction: routing_decision + swarm_plan + research_brief_md), BE-004 (export pipeline integration round-trip). pytest suite green."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-004"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P4-002"
    description: "Complete frontend test suite: FE-001 (each panel null-context → empty-state, no error), FE-002–FE-005 (populated context for each panel), FE-006 (RunDetailWorkspace integration with real context fixture), FE-007 (schema 1.2 fixture → existing views unaffected). tsc --noEmit + test runner green."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-006"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P4-003"
    description: "Finalize docs/dev/architecture/rf-run-export-schema.md §9 with complete v1.3 context contract: all field names, types, nullability, source artifact per field, graceful-degradation contract, sensitivity redaction coverage. Update §Changelog with v1.3 row."
    status: pending
    assigned_to: ["documentation-writer"]
    dependencies: ["P4-001"]
    estimated_effort: "0.5 pts"
    priority: medium
    assigned_model: haiku
    model_effort: adaptive

  - id: "P4-004"
    description: "Add CHANGELOG.md [Unreleased] entry under 'Added': 'Run context panels (Routing Decision, Research Brief, Swarm Plan, Upstream Entities) in the run detail view; run.json schema 1.3 context block.' Set changelog_ref: CHANGELOG.md in plan frontmatter."
    status: pending
    assigned_to: ["changelog-generator"]
    dependencies: ["P4-003"]
    estimated_effort: "0.5 pts"
    priority: medium
    assigned_model: haiku
    model_effort: adaptive

  - id: "DOC-006"
    description: "Author docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md with maturity: shaping. Document v2 lazy-load optimization: trigger condition (run.json size threshold), delivery via loopback API GET /runs/{run_id}/context, hybrid embed+lazy-load, offline fallback semantics, frozen-schema implications. Append path to deferred_items_spec_refs in plan frontmatter."
    status: pending
    assigned_to: ["documentation-writer"]
    dependencies: ["P4-003"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P4-005"
    description: "Update plan frontmatter: status: completed, populate commit_refs, files_affected, updated, changelog_ref, deferred_items_spec_refs."
    status: pending
    assigned_to: ["documentation-writer"]
    dependencies: ["DOC-006"]
    estimated_effort: "0.25 pts"
    priority: medium
    assigned_model: haiku
    model_effort: adaptive

  - id: "P4-006"
    description: "karen feature-end gate: review frozen-schema invariant, offline-viewer invariant, sensitivity redaction coverage (context.* fields), and feature ACs AC-CP-1 through AC-CP-4. Output PASS or FAIL with specific items."
    status: pending
    assigned_to: ["karen"]
    dependencies: ["P4-005"]
    estimated_effort: "—"
    priority: critical
    assigned_model: opus
    model_effort: extended

parallelization:
  # P4-001 and P4-002 can run in parallel (BE tests ∥ FE tests)
  batch_1: ["P4-001", "P4-002"]
  batch_2: ["P4-003"]
  # P4-004 and DOC-006 can run in parallel after P4-003
  batch_3: ["P4-004", "DOC-006"]
  batch_4: ["P4-005"]
  batch_5: ["P4-006"]
  critical_path: ["P4-001", "P4-003", "DOC-006", "P4-005", "P4-006"]
  estimated_total_time: "1-2 days"

blockers: []

success_criteria:
  - id: "SC-P4-1"
    description: "pytest suite green (backend: BE-001 through BE-004; no regressions)"
    status: pending
  - id: "SC-P4-2"
    description: "FE unit + integration tests green (FE-001 through FE-007; no regressions)"
    status: pending
  - id: "SC-P4-3"
    description: "tsc --noEmit clean"
    status: pending
  - id: "SC-P4-4"
    description: "Schema doc fully finalized (§9 + §Changelog)"
    status: pending
  - id: "SC-P4-5"
    description: "CHANGELOG [Unreleased] entry present"
    status: pending
  - id: "SC-P4-6"
    description: "DFR-001 design spec authored at target path; deferred_items_spec_refs updated"
    status: pending
  - id: "SC-P4-7"
    description: "Plan frontmatter complete"
    status: pending
  - id: "SC-P4-8"
    description: "karen feature-end gate PASS (hard gate — final seal requires this)"
    status: pending

files_modified:
  - "docs/dev/architecture/rf-run-export-schema.md"
  - "CHANGELOG.md"
  - "docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md"
  - "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
---

# runs-context-panels - Phase 4: Tests, Docs & Validation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/runs-context-panels/phase-4-progress.md -t P4-001 -s completed
```

---

## Objective

Harden test suites, finalize schema documentation, add the CHANGELOG entry, author the DFR-001 deferred-item design spec, update plan frontmatter, and pass the `karen` feature-end gate. P4 cannot be sealed until all 8 success criteria pass, including the karen hard gate.

---

## Implementation Notes

### Architectural Decisions

- ICA free-tier delegation candidate for P4-001 and P4-002 (bounded, well-specified test authoring). Re-run authoritative pytest + tsc in-session after ICA completes.
- P4 entry requires P3 karen milestone PASS — do not start P4 without that gate cleared.
- `karen` (P4-006) uses opus + extended effort — runs last, after all other tasks complete.

### Patterns and Best Practices

- P4-001 and P4-002 can run in parallel (BE tests and FE tests are independent).
- P4-004 (CHANGELOG) and DOC-006 (DFR-001 design spec) can run in parallel after P4-003 (schema doc finalization).
- `deferred_items_spec_refs` in plan frontmatter must be updated before P4-005 runs.

### Known Gotchas

- P4 quality gate: `deferred_items_spec_refs` must contain the DFR-001 spec path AND `findings_doc_ref` must be null or finalized before the plan can be sealed.
- `karen` outputs PASS or FAIL with specific items — any FAIL blocks the seal; resolve all issues before re-running.
- feature-guide.md (post-seal deliverable) is authored after P4 is sealed, not as part of P4.

---

## Completion Notes

_(Fill when phase complete)_
