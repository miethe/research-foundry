---
type: progress
schema_version: 2
doc_type: progress
prd: "rf-upstream-evidence-foundry"
feature_slug: "rf-upstream-evidence-foundry"
prd_ref: "docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md"
execution_model: "batch-parallel"
phase: 6
title: "Validation, docs & deferral"
status: "not_started"
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["documentation-writer", "changelog-generator", "prd-writer"]
contributors: ["python-backend-engineer"]
model_usage:
  primary: "haiku"
  external: []

tasks:
  - id: "TASK-6.1"
    description: "Full cross-phase regression suite"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "critical"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-6.2"
    description: "Machine-surface inventory finalization + service-contract docs"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-6.1"]
    estimated_effort: "0.5h"
    priority: "high"
    assigned_model: "haiku"
    model_effort: "adaptive"
    
  - id: "TASK-6.3"
    description: "CHANGELOG update"
    status: "pending"
    assigned_to: ["changelog-generator"]
    dependencies: ["TASK-6.1"]
    estimated_effort: "0.5h"
    priority: "high"
    assigned_model: "haiku"
    model_effort: "adaptive"
    
  - id: "TASK-6.4"
    description: "RFUP-6 design spec authoring (deferred item)"
    status: "pending"
    assigned_to: ["prd-writer"]
    dependencies: []
    estimated_effort: "0.5h"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-6.5"
    description: "IntentTree node status writebacks"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-6.1", "TASK-6.4"]
    estimated_effort: "0.5h"
    priority: "medium"
    assigned_model: "haiku"
    model_effort: "adaptive"
    
  - id: "TASK-6.6"
    description: "Phase 6 completion validator gate"
    status: "pending"
    assigned_to: ["task-completion-validator"]
    dependencies: ["TASK-6.2", "TASK-6.3", "TASK-6.4", "TASK-6.5"]
    estimated_effort: "1h"
    priority: "critical"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-6.7"
    description: "karen feature-end checkpoint"
    status: "pending"
    assigned_to: ["karen"]
    dependencies: ["TASK-6.6"]
    estimated_effort: "1h"
    priority: "critical"
    assigned_model: "opus"
    model_effort: "adaptive"

parallelization:
  batch_1: ["TASK-6.1"]
  batch_2: ["TASK-6.2", "TASK-6.3"]
  batch_3: ["TASK-6.4"]
  batch_4: ["TASK-6.5"]
  batch_5: ["TASK-6.6"]
  batch_6: ["TASK-6.7"]
  critical_path: ["TASK-6.1", "TASK-6.2", "TASK-6.3", "TASK-6.4", "TASK-6.5", "TASK-6.6", "TASK-6.7"]
  estimated_total_time: "3h"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Full regression suite green under venv; flake8 errors-only clean"
    status: "pending"
  - id: "SC-2"
    description: "Machine-surface inventory doc finalized"
    status: "pending"
  - id: "SC-3"
    description: "CHANGELOG [Unreleased] entry present for all new user-facing surfaces"
    status: "pending"
  - id: "SC-4"
    description: "RFUP-6 design spec authored; deferred_items_spec_refs populated"
    status: "pending"
  - id: "SC-5"
    description: "IntentTree node statuses updated (or best-effort-skipped and logged)"
    status: "pending"
  - id: "SC-6"
    description: "task-completion-validator sign-off recorded (TASK-6.6)"
    status: "pending"
  - id: "SC-7"
    description: "karen feature-end sign-off recorded (TASK-6.7)"
    status: "pending"

files_modified:
  - "CHANGELOG.md"
  - "docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md"
---

# Phase 6: Validation, docs & deferral

**Duration**: ~1-2 days (3 pts)
**Dependencies**: Phases 2, 3, 4, 5 complete
**Model**: Haiku (adaptive) for docs tasks; Sonnet for RFUP-6 design spec; Opus for karen milestone
**Milestone**: karen feature-end checkpoint (Tier 3 end-of-feature review)

This is the finalization phase. It runs the full cross-phase regression suite, finalizes documentation, updates the CHANGELOG, authors the RFUP-6 deferral design spec, updates IntentTree node statuses, and gates the feature completion with validator + karen sign-offs.

---

## Objective

Complete cross-phase regression testing, finalize documentation and machine-surface inventory, author the RFUP-6 deferral design spec, update IntentTree, and gate feature completion with task-completion-validator and karen milestone reviews.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-6.1 (python-backend-engineer, sonnet, adaptive, ~1h, REGRESSION SUITE)
**Batch 2**: TASK-6.2 (documentation-writer, haiku, adaptive, ~0.5h) and TASK-6.3 (changelog-generator, haiku, adaptive, ~0.5h) in parallel — both depend on TASK-6.1
**Batch 3**: TASK-6.4 (prd-writer, sonnet, adaptive, ~0.5h, RFUP-6 spec) — independent
**Batch 4**: TASK-6.5 (documentation-writer, haiku, adaptive, ~0.5h, IntentTree writebacks) — depends on TASK-6.1 and TASK-6.4
**Batch 5**: TASK-6.6 (task-completion-validator, sonnet, adaptive, ~1h gate) — depends on TASK-6.2, TASK-6.3, TASK-6.4, TASK-6.5
**Batch 6**: TASK-6.7 (karen, opus, adaptive, ~1h MILESTONE GATE) — depends on TASK-6.6

---

## Implementation Notes

### TASK-6.1: Full Cross-Phase Regression Suite (CRITICAL)

Run every test from all previous phases in a single pass under venv:

```bash
# Full regression (all phases)
./.venv/bin/python -m pytest

# Alternatively, run specific phase test suites in sequence:
./.venv/bin/python -m pytest -k contract_drift           # Phase 1
./.venv/bin/python -m pytest -k exact_passage           # Phase 2
./.venv/bin/python -m pytest -k pdf_extraction          # Phase 3
./.venv/bin/python -m pytest -k "run_seal or council_verdict" # Phase 4
# Phase 5: .js only, syntax check covers it

# Lint check (errors-only)
flake8 src/research_foundry --select=E9,F63,F7,F82
```

**Expected outcome**: All tests green. Flake8 clean. Any failures → investigate before proceeding to later tasks.

### TASK-6.2: Machine-Surface Inventory Finalization

Finalize the machine-surface inventory doc scaffolded in Phase 1 TASK-1.1:
- List all 6 enumerated surfaces (CLI `--json` outputs, verify YAML/JSON, LAN API, run export, etc.)
- Record final stamped `rf_schema_version` value
- Cross-check: all surfaces have been stamped; no renames/removals
- Update any docs referencing `rf fetch`, `rf verify`, council adapter usage
- Create service contract doc if needed (Phase 1 TASK-1.2 should have authored this)

### TASK-6.3: CHANGELOG Update

Add `[Unreleased]` section entries for user-facing new surfaces:
```markdown
## [Unreleased]

### Added
- `verify.exact_passage` config key and `--exact-passage` CLI override flag for hard-gating exact-passage eligibility checks
- `extraction_status` field on source cards (`full_text|partial|locator_only`) replacing implicit `degraded` boolean
- Council verdict normalization (`approve|concern|block` enum) in `rf verify` output
- Run seal functionality via `--seal` flag on finalize/export path (or new `rf seal` command if OQ-2 fallback)
```

Per `.claude/specs/changelog-spec.md`, categorize as `Added` (new capability surfaces). Set `changelog_ref` frontmatter in this progress file to the CHANGELOG.md path.

### TASK-6.4: RFUP-6 Design Spec Authoring (Deferred Item)

Author `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md`:
- `doc_type: design_spec`
- `maturity: idea` (not yet ready for implementation)
- `prd_ref`: points to the parent PRD
- Sections:
  - Defer-until trigger: "Measured value gap OR security/governance gap"
  - Adapter shortlist: `gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`, `opencode`, `litellm_router` (the 6 non-`arc_council`/non-native adapters per current-state.md)
  - Why deferred: Path-B (RFUP-1, now in scope) is the proven live-discovery lane
  - Trigger conditions: measured value signal OR security gap audit

After authoring, set `deferred_items_spec_refs` frontmatter in this plan to point to the spec path.

### TASK-6.5: IntentTree Node Status Writebacks

Update IntentTree node statuses for the RFUP-1,2,3,4,5,7 nodes (from plan frontmatter `intenttree_workspace` + `intenttree_tree`):
- Mark RFUP-1,2,3,4,5,7 nodes as `complete` or `done`
- Mark RFUP-6 node to note deferral with the TASK-6.4 design-spec path

**Non-fatal**: If the IntentTree API is unreachable, log and skip (best-effort).

### Quality Gate Chain (TASK-6.6 & TASK-6.7)

**TASK-6.6 (task-completion-validator)**:
- Reviews full regression result (all tests green)
- Reviews machine-surface inventory doc finalization
- Reviews CHANGELOG [Unreleased] entries
- Reviews RFUP-6 design spec (maturity: idea, defer-until trigger clear)
- Reviews IntentTree updates
- **Gate**: Deferred Items Triage row (in implementation plan) has its Target Spec Path populated (`deferred_items_spec_refs` set)
- **Gate**: `findings_doc_ref` remains null, OR findings doc exists with `status: accepted`

**TASK-6.7 (karen milestone)**:
- Tier 3 end-of-feature review
- Assesses actual completion state of all six phases against claimed status
- Confirms deferred-items quality gate
- Confirms no unresolved Mode D edges (lineage append-only check, immutability boundaries)
- **Sign-off**: Feature marked complete

### Known Gotchas

- **Regression test timing**: Full suite can take 30-60 seconds. Run early; don't rush.
- **Flake8 syntax vs. logic errors**: `--select=E9,F63,F7,F82` catches syntax errors only, not style issues. That's intentional.
- **IntentTree API downtime**: If IntentTree is unreachable, log clearly and skip (no hard failure).
- **RFUP-6 scope clarity**: The design spec should be crystal-clear about the defer-until trigger. "Not ready yet" is not enough; document the specific condition (measured value OR security gap).

### Development Setup

```bash
# Full regression suite
source .venv/bin/activate
./.venv/bin/python -m pytest --tb=short -v

# Linting (errors only)
flake8 src/research_foundry --select=E9,F63,F7,F82

# CHANGELOG validation
grep -A 20 "## \[Unreleased\]" CHANGELOG.md | head -25

# IntentTree status check (optional, may require API access)
# command to be determined based on available IntentTree CLI
```

---

## Completion Notes

(To be filled in when phase is complete)

- [ ] Full `./.venv/bin/python -m pytest` suite green
- [ ] `flake8 src/research_foundry --select=E9,F63,F7,F82` clean
- [ ] Machine-surface inventory doc finalized with all 6 surfaces enumerated
- [ ] Service contract docs updated (rf fetch, rf verify, council usage)
- [ ] CHANGELOG `[Unreleased]` entries added for all new surfaces (verify.exact_passage, extraction_status, council enum, seal)
- [ ] RFUP-6 design spec authored (`docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md`)
- [ ] Design spec includes defer-until trigger and adapter shortlist
- [ ] `deferred_items_spec_refs` frontmatter populated in implementation plan
- [ ] IntentTree nodes updated (or best-effort-skipped and logged)
- [ ] Deferred Items Triage row in implementation plan has Target Spec Path resolved
- [ ] `findings_doc_ref` remains null OR findings doc exists with `status: accepted`
- [ ] All Phase 6 acceptance criteria met (SC-1 through SC-7)
- [ ] task-completion-validator sign-off recorded (TASK-6.6)
- [ ] karen feature-end sign-off recorded (TASK-6.7)

---

## Quality Gate Chain

### Gate 1: task-completion-validator (TASK-6.6)

**Checks**:
- [ ] Regression suite fully green
- [ ] Inventory doc complete
- [ ] CHANGELOG entries cover all new surfaces
- [ ] RFUP-6 spec complete and ready
- [ ] Deferred Items quality gate met
- [ ] Findings doc status (null or accepted)

**Pass Condition**: All checks pass; validator sign-off recorded

### Gate 2: karen milestone (TASK-6.7)

**Checks**:
- [ ] Actual vs. claimed completion state aligned for all 6 phases
- [ ] No unresolved Mode D edges
- [ ] Deferred items properly documented
- [ ] Append-only lineage immutability boundaries clear

**Pass Condition**: karen sign-off recorded; feature marked complete

---

## Post-Completion

After Phase 6 sealing (karen sign-off):

1. **Feature Guide** (auto-triggered): Delegate to documentation-writer to create `.claude/worknotes/rf-upstream-evidence-foundry/feature-guide.md` with frontmatter and sections: What Was Built, Architecture Overview, How to Test, Test Coverage, Known Limitations.
2. **PR Creation** (auto-triggered): Create PR with the feature guide link and test checklist (full suite, real-corpus regression, PDF fixtures, seal digest, Path-B dry-run).

---

**Phase 6 Status**: Not Started
**Last Updated**: 2026-07-18
