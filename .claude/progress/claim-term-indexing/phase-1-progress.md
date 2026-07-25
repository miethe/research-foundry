---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 1
title: Vocabulary + Write-Path Core
status: completed
created: '2026-07-24'
updated: '2026-07-25'
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
commit_refs:
- ab282f2
pr_refs: []
started: 2026-07-24T18:00Z
completed: 2026-07-25T02:00Z
overall_progress: 100
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ica-executor
contributors:
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-1.1
  description: 'Vocabulary file format + loader: create vocab/pediatric-terms.yaml
    (canonical term ID -> surface-form aliases); loader stamps vocabulary_version;
    jsonschema-validate at load time (OQ-D: malformed vocab fails closed and blocks
    claim-map; missing vocab warns and skips indexing)'
  status: completed
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
- id: TASK-1.2
  description: 'Deterministic term matcher: adapt CARP''s case-folded, word-boundary
    substring/token matcher (catalog_retrieval.py:385-419) as a pure function taking
    claim text + loaded vocabulary, returning matched canonical term IDs; no Aho-Corasick
    dependency per D5'
  status: completed
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-1.1
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
- id: TASK-1.3
  description: 'Usage-role classifier: rule-based regex context-window classifier
    (threshold vs background) plus pediatric_cds structured threshold{value,units_ucum}
    field keying; zero model/embedding calls (D6, FR-3)'
  status: completed
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-1.1
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
- id: TASK-1.4
  description: 'Attach _term_index in claim_mapping.build_claim_ledger: wire matcher
    + classifier into build_claim_ledger (services/claim_mapping.py); write _term_index:{terms,usage_roles,vocabulary_version}
    per claim item under the single namespaced key; never emit a bare usage_role field
    (D2, FR-4, FR-5)'
  status: completed
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-1.2
  - TASK-1.3
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
- id: TASK-1.5
  description: 'report_frontmatter rollup field: add additive _term_index-shaped rollup
    field to report_frontmatter.schema.yaml (union of terms/roles across a report''s
    claims), computed at the same write time as claim-map (OQ-E); update claim_ledger.schema.yaml/report_frontmatter.schema.yaml
    docs for the new additive key'
  status: completed
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-1.4
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
- id: TASK-1.6
  description: 'Guard tests (ENTRY-BLOCKING EXIT GATE): (a) fingerprint regression
    test asserting source_assertion_fingerprint() is byte-identical with/without an
    injected _term_index key, failing loudly if _term_index is ever added to SOURCE_ASSERTION_MATERIAL_FIELDS;
    (b) fixture-based rf verify before/after regression suite across >=2 runs (87-claim
    pediatric ledger + one synthetic zero-hit fixture), asserting byte-identical console
    output and 0 status flips'
  status: completed
  assigned_to:
  - ica-executor
  - task-completion-validator
  dependencies:
  - TASK-1.4
  - TASK-1.5
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-24T18:00Z
  completed: 2026-07-25T02:00Z
  evidence:
  - commit: ab282f2
  verified_by:
  - task-completion-validator
parallelization:
  batch_1:
  - TASK-1.1
  batch_2:
  - TASK-1.2
  - TASK-1.3
  batch_3:
  - TASK-1.4
  batch_4:
  - TASK-1.5
  batch_5:
  - TASK-1.6
  critical_path:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.4
  - TASK-1.5
  - TASK-1.6
  estimated_total_time: 3 pts
blockers: []
success_criteria:
- _term_index writes deterministically with zero model/network calls (grep-verified)
- Fingerprint regression test (AC-2) gates CI and fails loudly on a future material-fields
  change
- Verify byte-inertness fixture suite (>=2 runs, AC-3/OQ-A) passes with 0 status flips
- Malformed vocab fails closed; missing vocab warns and skips (OQ-D)
- task-completion-validator review passed -- P2 does not start until this gate is
  green
files_modified:
- vocab/pediatric-terms.yaml
- src/research_foundry/services/claim_mapping.py
- src/research_foundry/schemas/claim_ledger.schema.yaml
- src/research_foundry/schemas/report_frontmatter.schema.yaml
notes: 'Entry-blocking exit gate for the whole plan: TASK-1.6 must pass before any
  P2 task begins.'
progress: 100
---

# claim-term-indexing - Phase 1: Vocabulary + Write-Path Core

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-1-progress.md -t TASK-1.1 -s completed
```

---

## Objective

Build the deterministic write-time core of `_term_index`: the versioned vocabulary format/loader, a pure case-folded word-boundary term matcher, a rule-based usage-role classifier, the attach point in `claim_mapping.build_claim_ledger`, an additive `report_frontmatter` rollup field, and the entry-blocking guard tests that prove the whole feature is inert to identity hashing and verification.

---

## Task Table

| Task ID | Task Name | Depends On | Assigned To | Estimate |
|---------|-----------|------------|-------------|----------|
| TASK-1.1 | Vocabulary file format + loader | None | ica-executor | 0.5 pts |
| TASK-1.2 | Deterministic term matcher | TASK-1.1 | ica-executor | 0.5 pts |
| TASK-1.3 | Usage-role classifier | TASK-1.1 | ica-executor | 0.5 pts |
| TASK-1.4 | Attach `_term_index` in `build_claim_ledger` | TASK-1.2, TASK-1.3 | ica-executor | 0.5 pts |
| TASK-1.5 | `report_frontmatter` rollup field | TASK-1.4 | ica-executor | 0.5 pts |
| TASK-1.6 | Guard tests (entry-blocking exit gate) | TASK-1.4, TASK-1.5 | ica-executor + task-completion-validator | 0.5 pts |

---

## Quick Reference — Dispatch Commands

```text
Task(
  subagent_type="ica-executor",
  description="TASK-1.1 vocabulary loader",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-1.1 from docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (§Phase 1). Create vocab/pediatric-terms.yaml + loader per the plan's acceptance criteria. Profile: python-backend-engineer."
)

Task(
  subagent_type="ica-executor",
  description="TASK-1.2 + TASK-1.3 matcher and classifier",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-1.2 and TASK-1.3 from the claim-term-indexing-v1 implementation plan (§Phase 1). Depends on TASK-1.1 (vocab loader) being complete. Profile: python-backend-engineer."
)

Task(
  subagent_type="ica-executor",
  description="TASK-1.4 attach _term_index",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-1.4 from the claim-term-indexing-v1 implementation plan (§Phase 1): wire matcher/classifier into services/claim_mapping.py build_claim_ledger. Profile: python-backend-engineer."
)

Task(
  subagent_type="ica-executor",
  description="TASK-1.5 report_frontmatter rollup",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-1.5 from the claim-term-indexing-v1 implementation plan (§Phase 1): additive rollup field on report_frontmatter.schema.yaml. Profile: python-backend-engineer."
)

Task(
  subagent_type="task-completion-validator",
  description="TASK-1.6 guard-test gate review",
  prompt="Mode: E — Reviewer. Verify TASK-1.6 guard tests (fingerprint byte-inertness + rf verify regression, >=2 fixtures) are green per docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md Phase 1 acceptance criteria before P2 may start."
)
```

Update status after each task:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-1-progress.md -t TASK-1.1 -s completed --started <ISO8601> --completed <ISO8601>
```

---

## Quality Gates

- [ ] `_term_index` writes deterministically with zero model/network calls (grep-verified)
- [ ] Fingerprint regression test (AC-2) gates CI and fails loudly on a future material-fields change
- [ ] Verify byte-inertness fixture suite (>=2 runs, AC-3/OQ-A) passes with 0 status flips
- [ ] Malformed vocab fails closed; missing vocab warns and skips (OQ-D)
- [ ] task-completion-validator review passed — **P2 does not start until this gate is green**

---

## Validation Commands

```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_claim_mapping_term_index.py tests/services/test_assertion_identity_term_index_regression.py tests/services/test_verify_byte_inertness.py -v
```

---

## Completion Notes

Fill in when phase is complete: what was built, key learnings, unexpected challenges, recommendations for Phase 2.
