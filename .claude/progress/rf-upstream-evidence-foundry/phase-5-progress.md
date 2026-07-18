---
type: progress
schema_version: 2
doc_type: progress
prd: "rf-upstream-evidence-foundry"
feature_slug: "rf-upstream-evidence-foundry"
prd_ref: "docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md"
execution_model: "batch-parallel"
phase: 5
title: "Parameterize Path-B workflow (RFUP-1)"
status: "not_started"
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["ai-artifacts-engineer"]
contributors: []
model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "TASK-5.1"
    description: "Replace hard-coded paths with config/args"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-5.2"
    description: "Run-date computed at invocation"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["TASK-5.1"]
    estimated_effort: "1h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-5.3"
    description: "Validation + registry update"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["TASK-5.2"]
    estimated_effort: "1h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-5.4"
    description: "Phase 5 quality gate - task-completion-validator"
    status: "pending"
    assigned_to: ["task-completion-validator"]
    dependencies: ["TASK-5.3"]
    estimated_effort: "0.5h"
    priority: "critical"
    assigned_model: "sonnet"
    model_effort: "adaptive"

parallelization:
  batch_1: ["TASK-5.1"]
  batch_2: ["TASK-5.2"]
  batch_3: ["TASK-5.3"]
  batch_4: ["TASK-5.4"]
  critical_path: ["TASK-5.1", "TASK-5.2", "TASK-5.3", "TASK-5.4"]
  estimated_total_time: "4h"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "node --check passes"
    status: "pending"
  - id: "SC-2"
    description: "Dry-run with explicit args reproduces prior default behavior on this machine"
    status: "pending"
  - id: "SC-3"
    description: "No literal absolute machine paths remain (grep-verifiable)"
    status: "pending"
  - id: "SC-4"
    description: "Date stamp computed at invocation time (distinct stamps across two dry-run dates)"
    status: "pending"
  - id: "SC-5"
    description: "task-completion-validator sign-off recorded"
    status: "pending"

files_modified:
  - ".claude/workflows/rf-run-execute.js"
---

# Phase 5: Parameterize Path-B workflow (RFUP-1)

**Anchor**: `knitwit-run-execute.js` generalization (same workflow, already partially generalized once)
**Duration**: ~2 days (4 pts)
**Dependencies**: Phase 1 (soft/scheduling only — see wave_plan P5 `agent_context` — no technical coupling)
**Model**: Sonnet (adaptive)
**Skills Required**: `workflow-authoring` (four-constraints checklist)
**Wave Placement**: Deliberately scheduled in wave 3 (after Python phases P1-4) to avoid contending with Python work in review bandwidth

This is the JS/workflow-scripting phase. It parameterizes the `.claude/workflows/rf-run-execute.js` Path-B workflow by replacing hard-coded machine paths and date stamps with configurable args/invocation-time values.

---

## Objective

Replace hard-coded constants in `.claude/workflows/rf-run-execute.js` (RF binary path, repo checkout path, TMP working dir, date stamp) with configurable args, each defaulting to current behavior on this machine. Preserve the TMP→cp write-safety pattern unchanged.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-5.1 (ai-artifacts-engineer, sonnet, adaptive, ~2h, workflow-authoring skill)
**Batch 2**: TASK-5.2 (ai-artifacts-engineer, sonnet, adaptive, ~1h) — depends on TASK-5.1
**Batch 3**: TASK-5.3 (ai-artifacts-engineer, sonnet, adaptive, ~1h, includes four-constraints checklist) — depends on TASK-5.2
**Batch 4**: TASK-5.4 (task-completion-validator, sonnet, adaptive, ~0.5h gate) — depends on TASK-5.3

---

## Implementation Notes

### Current Hard-Coded Constants (lines 18-21)

```javascript
// Lines 18-20: Hard-coded paths
const RF_BIN = '/Users/miethe/.venv/bin/rf';
const REPO_PATH = '/Users/miethe/dev/research-foundry';
const TMP_DIR = '/tmp/rf-run-execute';

// Line 21: Baked date stamp
const RUN_DATE = '20260613';
```

### TASK-5.1: Replace Paths with Args

Create configurable arguments with sensible defaults:
```javascript
// Command-line args or environment defaults
const rfBin = argv.rfBin || process.env.RF_BIN || '/Users/miethe/.venv/bin/rf';
const repoPath = argv.repo || process.env.RF_REPO || '/Users/miethe/dev/research-foundry';
const tmpDir = argv.tmpDir || process.env.RF_TMP_DIR || '/tmp/rf-run-execute';
```

**Preservation**: The TMP→cp write-safety pattern (lines 97-100, 127, 164, 189, 212) must remain unchanged. This is the atomic-write mechanism that prevents partial/corrupt results in concurrent runs.

### TASK-5.2: Run-Date Computed at Invocation

Replace the baked `20260613` with date computed at invocation time:
```javascript
const runDate = new Date().toISOString().split('T')[0].replace(/-/g, '');
// Result: e.g., "20260718" on 2026-07-18
```

**Impact**: Each invocation now gets a distinct date stamp, enabling proper tracking across multiple runs on different dates.

### TASK-5.3: Validation & Registry Update

**Validation**:
1. `node --check .claude/workflows/rf-run-execute.js` (syntax check)
2. Dry-run with explicit `--rf-bin`, `--repo`, `--tmp-dir` args on a scratch run
3. Verify dry-run reproduces prior default behavior on this machine
4. Grep-based source scan: confirm no literal absolute paths remain

**Four-Constraints Checklist** (workflow-authoring skill):
Re-run the skill's four constraints after refactoring:
- Deterministic (same input → same output)
- Auditable (clear log trail)
- Idempotent (re-run is safe)
- Rollback-safe (cleanup on failure)

**Registry Update**: Update `.claude/workflows/workflow-registry.md` (if exists) to document the new config surface (args, env vars, defaults).

### Known Gotchas

- **Backslash escaping in JSON args**: Windows paths with backslashes need escaping when passed as JSON. Consider adding a path-normalization step.
- **Relative vs. absolute paths**: Allow both relative and absolute paths. Resolve relative paths against `process.cwd()` at invocation time.
- **Date format consistency**: Ensure the computed date format matches the existing format (YYYYMMDD with no separators). Test on dates with single-digit month/day (e.g., 2026-01-05 → 20260105).
- **Environment variable precedence**: Clearly document precedence: CLI args > env vars > hardcoded defaults.

### Development Setup

```bash
# Phase 5 JS validation
node --check .claude/workflows/rf-run-execute.js

# Dry-run with explicit args (test 1)
node .claude/workflows/rf-run-execute.js --rf-bin ~/.venv/bin/rf --repo ~/dev/research-foundry --tmp-dir /tmp/rf-test-1

# Dry-run with explicit args (test 2, different date)
# Run on a different date or manually set the date in the test
node .claude/workflows/rf-run-execute.js --rf-bin ~/.venv/bin/rf --repo ~/dev/research-foundry --tmp-dir /tmp/rf-test-2

# Verify distinct date stamps in output
grep "source_card_id" /tmp/rf-test-1/*.md /tmp/rf-test-2/*.md | grep -o "20[0-9]\{6\}" | sort | uniq -c

# Grep for absolute paths (should find zero new instances)
grep -n "^const.*=.*'/Users/" .claude/workflows/rf-run-execute.js
```

---

## Completion Notes

(To be filled in when phase is complete)

- [ ] Hard-coded RF binary path replaced with configurable arg (`--rf-bin`)
- [ ] Hard-coded repo path replaced with configurable arg (`--repo`)
- [ ] Hard-coded TMP dir replaced with configurable arg (`--tmp-dir`)
- [ ] All args have sensible defaults (current behavior on this machine)
- [ ] Date stamp computed at invocation time (not baked)
- [ ] `node --check` passes with no syntax errors
- [ ] Dry-run with explicit args reproduces prior default behavior
- [ ] No literal absolute machine paths remain (grep-verifiable)
- [ ] Four-constraints checklist re-run passes (workflow-authoring skill)
- [ ] `.claude/workflows/workflow-registry.md` updated with new config surface
- [ ] All Phase 5 acceptance criteria met (SC-1 through SC-5)
- [ ] task-completion-validator sign-off recorded

---

## Risk Mitigation

**MEDIUM Risk**: Workflow param refactor breaks the proven Path-B lane

**Mitigation**: Backward-compat default config reproduces current behavior on this machine. Dry-run gate before registry update. Four-constraints checklist re-run.

---

**Phase 5 Status**: Not Started
**Last Updated**: 2026-07-18
