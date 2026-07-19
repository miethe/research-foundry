---
type: progress
schema_version: 2
doc_type: progress
prd: rf-upstream-evidence-foundry
feature_slug: rf-upstream-evidence-foundry
prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
execution_model: batch-parallel
phase: 4
title: Council normalization + run lineage (RFUP-5, RFUP-7)
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- data-layer-expert
contributors: []
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-4.1
  description: Council verdict normalization enum (4a)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-18T00:00Z
  completed: 2026-07-18T00:30Z
  evidence:
  - test: tests/test_council_verdict_normalization.py
  verified_by:
  - python-backend-engineer
- id: TASK-4.2
  description: Seal trigger surface (4b, OQ-2)
  status: completed
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies: []
  estimated_effort: 1h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-18T00:00Z
  completed: 2026-07-18T00:45Z
  evidence:
  - test: tests/test_seal_cli_flag.py
  verified_by:
  - python-backend-engineer
- id: TASK-4.3
  description: Content digest + append-only lineage record
  status: completed
  assigned_to:
  - data-layer-expert
  - python-backend-engineer
  dependencies:
  - TASK-4.2
  estimated_effort: 1.5h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-18T00:45Z
  completed: 2026-07-18T01:30Z
  evidence:
  - test: tests/test_run_seal_lineage.py
  verified_by:
  - data-layer-expert
- id: TASK-4.4
  description: Tamper-evidence + pre-seal-unaffected regression
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.3
  estimated_effort: 0.5h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-18T01:30Z
  completed: 2026-07-18T02:15Z
  evidence:
  - test: tests/test_run_seal_tamper_evidence.py
  verified_by:
  - python-backend-engineer
- id: TASK-4.5
  description: Phase 4 quality gate - task-completion-validator
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-4.1
  - TASK-4.4
  estimated_effort: 0.5h
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-18T02:15Z
  completed: 2026-07-18T02:45Z
  evidence:
  - verdict: APPROVED
  verified_by:
  - task-completion-validator
parallelization:
  batch_1:
  - TASK-4.1
  - TASK-4.2
  batch_2:
  - TASK-4.3
  batch_3:
  - TASK-4.4
  batch_4:
  - TASK-4.5
  critical_path:
  - TASK-4.2
  - TASK-4.3
  - TASK-4.4
  - TASK-4.5
  estimated_total_time: 5h
blockers: []
success_criteria:
- id: SC-1
  description: Council verdict enum present in machine output; raw ARC text always
    retained
  status: pending
- id: SC-2
  description: No field added to run-export.ts by this phase (OQ-4 default confirmed)
  status: pending
- id: SC-3
  description: Sealed-run mutation attempt detected by digest re-check
  status: pending
- id: SC-4
  description: Unsealed-run workflow (rf tail, report iteration) unaffected
  status: pending
- id: SC-5
  description: task-completion-validator sign-off recorded
  status: pending
files_modified:
- src/research_foundry/adapters/arc_council.py
- src/research_foundry/paths.py
- src/research_foundry/services/assertion_registry.py
- src/research_foundry/cli_commands.py
progress: 100
updated: '2026-07-18'
---

# Phase 4: Council normalization + run lineage (RFUP-5, RFUP-7)

**Anchor**: council normalization is S (~2pt); lineage digest reuses assertion-registry atomic-write/digest patterns → 5 combined
**Duration**: ~2-3 days (5 pts)
**Dependencies**: Phase 1 (soft — needs schema stamping in place)
**Model**: Sonnet (adaptive)

This phase is split into two sub-areas: 4a (Council normalization) and 4b (Run lineage). Council normalization converts free-form `arc_council` adapter verdicts into a controlled enum. Run lineage adds seal trigger + append-only lineage tracking for tamper-evidence.

---

## Objective

Normalize `arc_council` adapter verdicts into a controlled `approve|concern|block` enum while retaining raw text (non-destructive). Add run seal functionality with tamper-evident content digest and append-only lineage record.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-4.1 (python-backend-engineer, sonnet, adaptive, ~2h) and TASK-4.2 (python-backend-engineer + data-layer-expert, sonnet, adaptive, ~1h) in parallel
**Batch 2**: TASK-4.3 (data-layer-expert + python-backend-engineer, sonnet, adaptive, ~1.5h) — depends on TASK-4.2
**Batch 3**: TASK-4.4 (python-backend-engineer, sonnet, adaptive, ~0.5h) — depends on TASK-4.3
**Batch 4**: TASK-4.5 (task-completion-validator, sonnet, adaptive, ~0.5h gate) — depends on TASK-4.1 and TASK-4.4

---

## Implementation Notes

### 4a: Council Verdict Normalization (TASK-4.1)

**Scope**: Normalize `adapters/arc_council.py` free-form `verdict` string into a controlled enum:
```python
class CouncilVerdict(str, Enum):
    approve = "approve"
    concern = "concern"
    block = "block"
```

**Rules**:
- Recognized "approve" phrasing → `approve` + `normalization_confidence: high`
- Unrecognized/ambiguous text → `concern` (fail-toward-caution) + `normalization_confidence: low`
- Raw string ALWAYS retained in `AdapterResult.artifacts["arc_verdict"]` (non-destructive)

**Key**: Normalization happens ONLY at the adapter boundary. ARC's own record is never mutated. The normalized enum is stored alongside (not replacing) the raw text.

**Per OQ-4**: The normalized enum is NOT added to `run-export.ts` (no 1.6 schema bump). Stays CLI/YAML-only.

### 4b: Run Lineage & Seal (TASK-4.2 and TASK-4.3)

**OQ-2 Resolution**: Seal trigger is additive flag on the existing finalize/export CLI path (smaller surface than a new command):
- Explore `paths.py` and `cli_commands.py` to find a clean attach point (e.g., `--seal` flag on `rf finalize` or `rf export`)
- If no clean attach point, fallback to new `rf seal <run>` command (flag the deviation in Completion Report)

**Seal Mechanism** (TASK-4.3):
1. Compute content digest over run's evidence chain:
   - Claim ledger entries
   - Source cards
   - Report (if present)
2. Reuse `services/assertion_registry.py`'s atomic-write pattern:
   - Write to temp file
   - fsync() for durability
   - os.replace() for atomicity
3. Store append-only lineage record:
   - Seal timestamp
   - Content digest
   - Sealer identity/context (if available)
   - Never rewrites history

**Key Invariant**: Append-only design. The lineage record is immutable once written. No file locking or OS-level write protection applied (permissions unchanged pre/post seal).

### Tamper-Evidence (TASK-4.4)

**Digest Re-check Test**: Post-seal, re-compute digest and compare against stored digest. Any mutation to covered files (claim ledger, source cards, report) produces a mismatched digest.

**Regression Test**: Unsealed run's existing workflow (rf tail, report iteration) is entirely unaffected by seal implementation. Seal applies no behavioral changes to unsealed runs.

**Resilience**: Consumers of run metadata treat absence of a lineage record as "unsealed" (no error, just no tamper-evidence).

### Known Gotchas

- **Council verdict parsing is fuzzy**: Different phrasing ("approved", "APPROVE", "approved with comments") must map to the enum. Add extensive test cases for edge cases.
- **Digest coverage**: What files/records should be digest-covered? Claim ledger: yes. Source cards: yes. Report: maybe (depends on report mutability). Lineage record itself: no (would create circular digest). Document the scope clearly.
- **Append-only enforcement**: No code logic enforces append-only (the filesystem gives this for free). Document via comments that re-sealing is NOT supported (seal once, never again for that run).
- **Date-based lineage**: Lineage timestamp is in UTC. Sealer identity context is optional (CLI runs: empty; API runs: user context, if available).

### Development Setup

```bash
# Activate venv
source .venv/bin/activate

# Run Phase 4 council tests
./.venv/bin/python -m pytest -k council_verdict -v

# Run seal tamper-evidence tests
./.venv/bin/python -m pytest -k run_seal -v

# Manual seal test
rf seal RUN_ID
rf show RUN_ID --json | jq '.lineage'

# Verify digest mismatch on mutation
rf show RUN_ID --json | jq '.lineage.digest' > digest_before.txt
# (manually edit a claim in the run's ledger)
python -c "from research_foundry.services.assertion_registry import compute_digest; print(compute_digest('RUN_ID'))" > digest_after.txt
diff digest_before.txt digest_after.txt
```

---

## Completion Notes

(To be filled in when phase is complete)

- [ ] Council verdict enum defined in `adapters/arc_council.py`
- [ ] Verdict normalization logic implemented (approve/concern/block rules)
- [ ] Raw `arc_verdict` text retained in artifacts (non-destructive)
- [ ] Normalization confidence flag added (`high` for recognized, `low` for ambiguous)
- [ ] Seal trigger surface identified and integrated (flag on finalize/export OR new `rf seal` command)
- [ ] Content digest computed over claim ledger + source cards + report
- [ ] Atomic-write pattern (temp file → fsync → os.replace) implemented
- [ ] Append-only lineage record stored with seal timestamp + digest + sealer context
- [ ] Digest re-check test detects post-seal mutation on all covered files
- [ ] Unsealed-run workflow (rf tail, report iteration) regression test passes
- [ ] All Phase 4 acceptance criteria met (SC-1 through SC-5)
- [ ] task-completion-validator sign-off recorded

---

## Risk Mitigation

**MEDIUM Risk**: Council normalization misclassifies free-form verdicts

**Mitigation**: Non-destructive — raw text always retained. Unparseable → `concern` (fail-toward-caution) + `normalization_confidence` flag.

**HIGH Risk**: Immutability breaks in-place run workflows (rf tail, report iteration)

**Mitigation**: Immutability applies only to explicitly sealed runs. Pre-seal behavior unchanged. Seal is additive metadata + digest, no file locking.

---

**Phase 4 Status**: Not Started
**Last Updated**: 2026-07-18
