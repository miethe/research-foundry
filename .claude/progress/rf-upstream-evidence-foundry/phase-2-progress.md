---
type: progress
schema_version: 2
doc_type: progress
prd: rf-upstream-evidence-foundry
feature_slug: rf-upstream-evidence-foundry
prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
execution_model: batch-parallel
phase: 2
title: Exact-passage hard-gating in rf verify (RFUP-3)
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-2.1
  description: verify.exact_passage config key + run-level override (OQ-1)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T00:00:00Z'
  completed: '2026-07-18T00:30:00Z'
  evidence:
  - test: tests/test_verification_exact_passage.py
  - test: tests/test_verification_exact_passage.py
  verified_by:
  - TASK-2.4
- id: TASK-2.2
  description: New exact-passage eligibility check
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimated_effort: 1.5h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T00:30:00Z'
  completed: '2026-07-18T01:15:00Z'
  evidence:
  - test: tests/test_verification_exact_passage.py
  - test: tests/test_verification_exact_passage.py
  verified_by:
  - TASK-2.4
- id: TASK-2.3
  description: Violation list + real-corpus regression
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.2
  estimated_effort: 1.5h
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T01:15:00Z'
  completed: '2026-07-18T02:15:00Z'
  evidence:
  - test: tests/test_verification_exact_passage.py
  - test: tests/test_verification_exact_passage.py
  verified_by:
  - TASK-2.4
- id: TASK-2.4
  description: Phase 2 quality gate - task-completion-validator
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-2.3
  estimated_effort: 0.5h
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T02:15:00Z'
  completed: '2026-07-18T02:45:00Z'
  evidence:
  - validator: APPROVED
  verified_by:
  - TASK-2.4
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  batch_3:
  - TASK-2.3
  batch_4:
  - TASK-2.4
  critical_path:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  estimated_total_time: 4h
blockers: []
success_criteria:
- id: SC-1
  description: Strict mode blocks synthetic violation corpus; default mode unchanged
  status: pending
- id: SC-2
  description: Real-corpus regression sample shows zero new failures (default mode)
  status: pending
- id: SC-3
  description: exact_passage_violations field optional and non-breaking (AC-RFUP3-5)
  status: pending
- id: SC-4
  description: task-completion-validator sign-off recorded
  status: pending
files_modified:
- src/research_foundry/services/verification.py
progress: 100
updated: '2026-07-18'
---

# Phase 2: Exact-passage hard-gating in rf verify (RFUP-3)

**Anchor**: writeback-default-deny-gate exploration (flag-gated verify check, similar shape)
**Duration**: ~2 days (4 pts)
**Dependencies**: Phase 1 (soft rebase on stamped schema)
**Model**: Sonnet (adaptive)
**HIGH RISK**: Phase 2 introduces the `verify.exact_passage` flag that defaults to `warn` mode. Default mode must show zero new failures on the real-corpus regression sample (2,835 assertions).

This phase adds hard-gating eligibility checks requiring exact-passage/quote anchors on claims citing source cards, gated by a configurable `verify.exact_passage: warn|strict` flag (default `warn`).

---

## Objective

Implement a new exact-passage eligibility check in `rf verify` that can be configured at the global config level or overridden at the run level. Default mode (`warn`) produces zero new failures on the existing corpus; strict mode blocks 100% of violations.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-2.1 (python-backend-engineer, sonnet, adaptive, ~1h)
**Batch 2**: TASK-2.2 (python-backend-engineer, sonnet, adaptive, ~1.5h) — depends on TASK-2.1
**Batch 3**: TASK-2.3 (python-backend-engineer, sonnet, adaptive, ~1.5h, CRITICAL REGRESSION TEST) — depends on TASK-2.2
**Batch 4**: TASK-2.4 (task-completion-validator, sonnet, adaptive, ~0.5h gate) — depends on TASK-2.3

---

## Implementation Notes

### Critical: Default Mode = `warn`, NOT `strict`

Per decisions-block §3, the default is `warn` to avoid regressing the 2,835-assertion real corpus that's already backfilled. Evidence Foundry (downstream consumer) opts into strict per-run/profile.

### OQ-1 Resolution: Dual-Surface Default

The `verify.exact_passage` key is BOTH a config default AND a run-level CLI override:
- Config default: `research_foundry.yaml` or environment (default: `warn`)
- Run-level override: `--exact-passage strict|warn` CLI flag
- Rule: Run-level flag wins on conflict

### Eligibility Check Scope

The new exact-passage check is **distinct** from the existing `source_cards_have_locators` check. Both are eligibility checks in `services/verification.py`, but they target different concerns:
- `source_cards_have_locators`: Do we have source card references at all?
- `exact_passage`: Do citations include exact quotes/anchors from the source?

### Real-Corpus Regression Test (TASK-2.3 - CRITICAL)

The regression test runs the default-mode verify check over:
1. The 2,835-assertion backfilled sample
2. Prior KnitWit runs
3. Other prior rf runs

**Expected outcome**: Zero new failures in default mode. This is the HIGH risk mitigation. If any failures appear, investigate before proceeding.

### Patterns Used

- **Config gating** — similar to `writeback-default-deny` gate exploration pattern
- **Eligibility list** — verification output includes `exact_passage_violations` (analogous to existing `source_cards_have_locators_violations`)
- **Structured output** — YAML/JSON serialization in verify output

### Known Gotchas

- **Synthetic vs. real corpus**: The synthetic violation corpus (TASK-2.3 strict mode test) is separate from the real-corpus regression. Synthetic tests 100% block rate; real corpus tests zero new failure rate.
- **Backward compatibility**: The `exact_passage_violations` field is optional in the output. Consumers that don't understand it simply ignore it.
- **Flag precedence**: Run-level `--exact-passage` must override config. Document this clearly in CLI help.

### Development Setup

```bash
# Install and activate venv
source .venv/bin/activate

# Run Phase 2 exact-passage tests
./.venv/bin/python -m pytest -k exact_passage -v

# Run real-corpus regression (TASK-2.3)
./.venv/bin/python -m pytest -k exact_passage_corpus_regression -v

# Manual test with override flag
rf verify --run-id RUN_ID --exact-passage strict

# Check config default
rf config show | grep exact_passage
```

---

## Completion Notes

(To be filled in when phase is complete)

- [ ] `verify.exact_passage: warn|strict` config key implemented (default: `warn`)
- [ ] Run-level `--exact-passage` CLI override flag implemented
- [ ] Config → CLI precedence verified (CLI wins)
- [ ] New eligibility check in `services/verification.py` added
- [ ] Strict mode blocks 100% of synthetic violation corpus
- [ ] Default mode shows zero new failures on real-corpus regression sample
- [ ] `exact_passage_violations` field added to verify output (optional, non-breaking)
- [ ] Field properly stamped with `rf_schema_version` from Phase 1
- [ ] All Phase 2 acceptance criteria met (SC-1 through SC-4)
- [ ] task-completion-validator sign-off recorded

---

## Risk Mitigation

**HIGH Risk**: Strict passage gating breaks existing corpus (2,835 backfilled assertions; KnitWit + prior runs)

**Mitigation**: Flag/profile-gated, default `warn` (TASK-2.1). Strict is opt-in per run/profile. Regression test (TASK-2.3) runs default mode over a real-corpus sample and asserts zero new failures.

---

**Phase 2 Status**: Not Started
**Last Updated**: 2026-07-18
