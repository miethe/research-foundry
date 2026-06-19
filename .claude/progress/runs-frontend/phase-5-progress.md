---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-frontend"
feature_slug: "runs-frontend"
phase: 5
title: "Testing, Build, and Documentation"
status: "pending"
created: 2026-06-19
updated: 2026-06-19
prd_ref: "docs/project_plans/PRDs/features/runs-frontend-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-frontend-v1.md"
commit_refs: []
pr_refs: []
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 13
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["documentation-writer", "changelog-generator", "backend-architect"]

execution_model: batch-parallel

model_usage:
  primary: "sonnet"
  external: []

tasks:
  # E2E + Build track (ui-engineer-enhanced)
  - id: "P5-E2E-W2"
    description: "Playwright E2E: navigate to run detail; assert TrustPanel renders named verification checklist; assert failing check renders href=#clm_NNN anchor; run on static export fixture"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-E2E-W3"
    description: "Playwright E2E: navigate to report overlay tab; assert [claim:clm_NNN] chip rendered; click chip; assert ProvenanceModal opens with claim data; run on static export fixture"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-E2E-W1"
    description: "Playwright E2E: navigate to claim ledger; click first claim row; assert ProvenanceModal opens; assert SourceCard visible with non-empty quote; ≤2 UI interactions from ledger to quote"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-PROVENANCE-CORRECT"
    description: "Correctness test: parse report_draft.md for all [claim:clm_NNN] patterns; assert each exists in run.json claims[]; supported claims have non-empty sources[].quote; no orphaned chip references"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-BUILD"
    description: "Wire static SPA build: pre-build runs rf run export --all → frontend/runs-viewer/public/data/; vite build → dist/; add npm run build:runs-viewer to project scripts"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  # Documentation track (parallel with E2E)
  - id: "P5-ADR"
    description: "backend-architect authors docs/dev/architecture/adr-runs-read-path.md: static export as primary read path; R9 sensitivity invariant; read-only invariant (GET-only, no form elements); FoundryPaths.discover() invariant; status: accepted"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-README"
    description: "documentation-writer updates README.md CLI reference: add rf run export --json [--run-id ID|--all] and rf run list --json sub-command docs with examples; ≤20 lines"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "haiku"
    model_effort: "adaptive"

  - id: "P5-CHANGELOG"
    description: "changelog-generator adds [Unreleased] entry to CHANGELOG: rf run export --json, rf run list --json, runs frontend SPA, provenance drill-down, verification checklist, run corpus portfolio; set changelog_ref in plan frontmatter"
    status: "pending"
    assigned_to: ["changelog-generator"]
    dependencies: []
    estimated_effort: "0.25 pts"
    assigned_model: "haiku"
    model_effort: "adaptive"

  # Deferred design specs + frontmatter (sequential, after P5-ADR)
  - id: "P5-DOC-OQ4"
    description: "Author docs/project_plans/design-specs/runs-auth-lan.md: doc_type design_spec, maturity idea; captures OQ-4 ask, deferral rationale (loopback-only sufficient for v1), promotion trigger"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-ADR"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-DOC-OQ6"
    description: "Author docs/project_plans/design-specs/runs-loopback-api.md: doc_type design_spec, maturity idea; FR-11 scope, deferral rationale, RUNS_FRONTEND_LOOPBACK_API flag status, promotion trigger"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-ADR"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-DOC-FR13"
    description: "Author docs/project_plans/design-specs/runs-writeback-preview.md: doc_type design_spec, maturity idea; FR-13 scope (writeback-review governance view), deferral reason, promotion trigger"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-ADR"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-DOC-FR14"
    description: "Author docs/project_plans/design-specs/runs-context-panels.md: doc_type design_spec, maturity idea; FR-14 scope (routing decision, research brief, swarm plan, upstream entity panels), deferral reason, promotion trigger"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-ADR"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P5-FRONTMATTER"
    description: "Update runs-frontend-v1.md frontmatter: status completed, commit_refs, files_affected, updated date, deferred_items_spec_refs (4 design spec paths), changelog_ref: CHANGELOG.md"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-DOC-FR14", "P5-CHANGELOG"]
    estimated_effort: "0.25 pts"
    assigned_model: "haiku"
    model_effort: "adaptive"

parallelization:
  batch_1:
    - "P5-E2E-W2"
    - "P5-E2E-W3"
    - "P5-E2E-W1"
    - "P5-PROVENANCE-CORRECT"
    - "P5-BUILD"
    - "P5-ADR"
    - "P5-README"
    - "P5-CHANGELOG"
  batch_2:
    - "P5-DOC-OQ4"
    - "P5-DOC-OQ6"
    - "P5-DOC-FR13"
    - "P5-DOC-FR14"
  batch_3: ["P5-FRONTMATTER"]
  critical_path: ["P5-ADR", "P5-DOC-OQ4", "P5-FRONTMATTER"]
  estimated_total_time: "1-2 days"

blockers: []

success_criteria:
  - "E2E smoke: W1 (claim drill-down from report chip to verbatim quote) — Playwright green on static export fixture"
  - "E2E smoke: W2 (verification checklist rendering) — Playwright green on static export fixture"
  - "E2E smoke: W3 (report chip navigation to claim modal) — Playwright green on static export fixture"
  - "Provenance correctness test: every [claim:clm_NNN] in report_draft.md resolves to valid ledger entry and at least one source card"
  - "Runtime smoke covers all P3 + P4 target_surfaces"
  - "Static SPA build pipeline wired to rf run export --all; build completes cleanly"
  - "ADR authored at docs/dev/architecture/adr-runs-read-path.md; R9 sensitivity invariant + read-only constraint recorded; status: accepted"
  - "README CLI reference updated for rf run export and rf run list"
  - "CHANGELOG [Unreleased] entry added; changelog_ref set in plan frontmatter"
  - "All 4 deferred design specs authored (OQ-4, OQ-6, FR-13, FR-14) at target paths; deferred_items_spec_refs populated"
  - "Plan frontmatter updated: status completed, commit_refs, files_affected, updated"
  - "task-completion-validator P5 phase review passed"
  - "karen feature-end review passed"
---

# runs-frontend - Phase 5: Testing, Build, and Documentation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/runs-frontend/phase-5-progress.md -t P5-E2E-W1 -s completed --force
```

---

## Objective

Harden and close the feature. E2E smoke tests cover W1/W2/W3 workflows; provenance correctness assertion verifies every claim chip resolves; static SPA build wired to `rf run export --all`; ADR captures read-path and read-only decisions (including R9 sensitivity invariant); all four deferred items get design spec stubs. Documentation tasks run in parallel with E2E and ADR.

---

## Parallel Execution Structure

**Batch 1 (all parallel)**: E2E + Build track (P5-E2E-W2, P5-E2E-W3, P5-E2E-W1, P5-PROVENANCE-CORRECT, P5-BUILD) ∥ Docs track (P5-ADR, P5-README, P5-CHANGELOG)

**After P5-ADR**: Deferred design specs (P5-DOC-OQ4, P5-DOC-OQ6, P5-DOC-FR13, P5-DOC-FR14 — can run in parallel)

**Final**: P5-FRONTMATTER (after all deferred specs + P5-CHANGELOG)

---

## Reviewer Gates

| Reviewer | Trigger | Blocks |
|----------|---------|--------|
| `task-completion-validator` | All P5 quality gates pass | karen review |
| `karen` | All phases complete; deferred specs authored; frontmatter final | PR merge + feature guide authoring |
