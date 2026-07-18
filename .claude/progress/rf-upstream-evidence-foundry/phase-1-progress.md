---
type: progress
schema_version: 2
doc_type: progress
prd: "rf-upstream-evidence-foundry"
feature_slug: "rf-upstream-evidence-foundry"
prd_ref: "docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md"
execution_model: "batch-parallel"
phase: 1
title: "Machine contract & schema versioning (RFUP-4)"
status: "not_started"
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["python-backend-engineer"]
contributors: ["api-designer"]
model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "TASK-1.1"
    description: "Schema-version constant & inventory scaffold"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-1.2"
    description: "Stamp CLI `--json` outputs + exit-code contract doc"
    status: "pending"
    assigned_to: ["python-backend-engineer", "api-designer"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "1.5h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-1.3"
    description: "Stamp verify output, run export, and LAN API payloads"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "1.5h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-1.4"
    description: "Contract drift tests + fixture key-diff"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2", "TASK-1.3"]
    estimated_effort: "1h"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"
    
  - id: "TASK-1.5"
    description: "Phase 1 quality gate - task-completion-validator"
    status: "pending"
    assigned_to: ["task-completion-validator"]
    dependencies: ["TASK-1.4"]
    estimated_effort: "0.5h"
    priority: "critical"
    assigned_model: "sonnet"
    model_effort: "adaptive"

parallelization:
  batch_1: ["TASK-1.1"]
  batch_2: ["TASK-1.2", "TASK-1.3"]
  batch_3: ["TASK-1.4"]
  batch_4: ["TASK-1.5"]
  critical_path: ["TASK-1.1", "TASK-1.2", "TASK-1.4", "TASK-1.5"]
  estimated_total_time: "5h"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "rf_schema_version present on all Phase-1-enumerated surfaces"
    status: "pending"
  - id: "SC-2"
    description: "Contract drift tests fail on divergence, pass on unmodified code"
    status: "pending"
  - id: "SC-3"
    description: "Zero renamed/removed keys in fixture key-diff"
    status: "pending"
  - id: "SC-4"
    description: "task-completion-validator sign-off recorded"
    status: "pending"

files_modified:
  - "src/research_foundry/errors.py"
  - "src/research_foundry/cli_commands.py"
  - "src/research_foundry/services/verification.py"
  - "frontend/src/types/run-export.ts"
---

# Phase 1: Machine contract & schema versioning (RFUP-4)

**Anchor**: assertion-ledger P3 forward-write driver (stamp+thread a field through emit paths)
**Duration**: ~2-3 days (5 pts)
**Dependencies**: None
**Model**: Sonnet (adaptive)

This phase establishes the machine contract foundation — adding the canonical `RF_SCHEMA_VERSION` constant and stamping it across every enumerated machine-readable surface (CLI outputs, verify YAML/JSON, LAN API payloads, run export). No behavior change; purely additive stamping.

---

## Objective

Add `RF_SCHEMA_VERSION` as the single source of truth for the machine contract, stamp it on all enumerated surfaces, and establish contract drift tests that fail when the version diverges or when existing fields are renamed/removed.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-1.1 (python-backend-engineer, sonnet, adaptive, ~1h)
**Batch 2**: TASK-1.2 (python-backend-engineer + api-designer, sonnet, adaptive, ~1.5h) and TASK-1.3 (python-backend-engineer, sonnet, adaptive, ~1.5h) in parallel
**Batch 3**: TASK-1.4 (python-backend-engineer, sonnet, adaptive, ~1h) — depends on Batch 2
**Batch 4**: TASK-1.5 (task-completion-validator, sonnet, adaptive, ~0.5h gate) — depends on Batch 3

---

## Implementation Notes

### Architectural Decisions

The `RF_SCHEMA_VERSION` constant is hardcoded in the source and incremented manually (semantic versioning). It is NOT computed from git tags or package version to avoid runtime dependencies on external state. The version is stamped on output, not embedded in code logic.

### Machine Surfaces to Stamp (Task 1.1 inventory scaffold)

1. **CLI `--json` outputs** (`cli_commands.py`) — all commands with `--json` flag
2. **Verify YAML/JSON output** (`services/verification.py`) — both plain YAML and `--json` modes
3. **LAN API payloads** — `/api/runs`, `/api/reports`, `/api/catalog` responses
4. **Runs-viewer run-export schema** (`run-export.ts`) — dual-update rule applies

### Critical: Dual-Update Rule (Task 1.3)

The `run-export.ts` schema has a dual-update rule: if a new field is added to `services/verification.py`'s output, TypeScript schema bumps from 1.5 → 1.6. **Expected outcome**: Phase 1 adds only the version constant on existing fields, so no bump expected. If a new field is introduced, flag as a deviation in Completion Report.

### Patterns Used

- **YAML serialization** (`dataclasses` + custom YAML emitter in `services/verification.py`)
- **CLI typer** for `--json` output formatting in `cli_commands.py`
- **Pydantic models** for API serialization in LAN API handlers

### Known Gotchas

- **Rich console vs. machine output**: The Rich console output is presentation-only; machine surfaces are the stable contract.
- **Backward compatibility**: The version constant is additive. Existing consumers without version-awareness simply ignore it.
- **Test fixtures**: Contract drift tests must run over realistic fixture runs, not just synthetic minimal cases. Use the 2,835-assertion sample as reference for fixture diversity.

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Activate venv
source .venv/bin/activate

# Run Phase 1 tests
./.venv/bin/python -m pytest -k contract_drift -v

# Verify stamping on a real run
rf run --intent "test" --json | jq '.rf_schema_version'
```

---

## Completion Notes

(To be filled in when phase is complete)

- [ ] Constant `RF_SCHEMA_VERSION` defined in a canonical module (e.g., `research_foundry/__init__.py`)
- [ ] Machine-surface inventory doc lists all 6 enumerated surfaces
- [ ] CLI `--json` outputs stamp the version
- [ ] Verify YAML/JSON output stamps the version
- [ ] LAN API payloads stamp the version
- [ ] run-export.ts checked for dual-update rule compliance (no new fields expected)
- [ ] Contract drift tests added and passing
- [ ] Fixture key-diff test confirms zero renamed/removed keys
- [ ] All Phase 1 acceptance criteria met (SC-1 through SC-4)
- [ ] task-completion-validator sign-off recorded

---

**Phase 1 Status**: Not Started
**Last Updated**: 2026-07-18
