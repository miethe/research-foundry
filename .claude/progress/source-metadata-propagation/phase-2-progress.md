---
type: progress
schema_version: 2
doc_type: progress
prd: source-metadata-propagation
feature_slug: source-metadata-propagation
milestone: "M2"
phase: 2
title: "The attribution entity exists with a value-free, recompute-only mirror"
status: planning
created: '2026-08-02'
updated: '2026-08-02'
prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md
commit_refs: []
pr_refs: []

# Routing note: this plan is authored under the Claude-5 plan doctrine — routing_constraints in
# the plan resolve model/agent selection at dispatch time. Do NOT pin owners/assigned_to here.

started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

# Gate plan carried from the source plan's wave_plan.phases[] entry (id: M2) — do not re-derive.
gate_lens: [validator]
mode_d_halt: false
karen_required_this_milestone: false   # M1-M3 are C2 — only the single end-of-feature karen pass

tasks:
  - id: "SMP-2.2"
    description: "Author schemas/source_attribution.schema.yaml as the authoritative record (additionalProperties: false), shaped on the landed rights_record.schema.yaml pattern per the plan's accepted decision (new top-level entity, not an extension of source_assertion.schema.yaml). Minimum shape: {source, value, observed_at, license_basis}."
    status: "pending"
    dependencies: []

  - id: "SMP-2.3"
    description: "Add an attribution_summary mirror to schemas/source_card.schema.yaml carrying attribution_ids, counts, and the monotone rollups ONLY — never a raw third-party value — recomputed from authoritative records at export. This RESOLVES OQ-3 per the plan's accepted decision (no longer an open entry-blocker). Shares the file M1 also edits — file-hygiene sequencing only, not a hard dependency (see Sequencing note); confirm no concurrently-open M1 edit before landing to avoid a merge conflict."
    status: "pending"
    dependencies: ["SMP-2.2"]

  - id: "SMP-2.4"
    description: "Implement attribution_triage.py following the rights_triage.py:90-113 pattern."
    status: "pending"
    dependencies: ["SMP-2.2"]

  - id: "SMP-2.5"
    description: "Implement check_attribution_divergence(as_of=...) following the rights_validation.py:128 injected-clock pattern — the validator must read no wall clock."
    status: "pending"
    dependencies: ["SMP-2.3", "SMP-2.4"]

  - id: "SMP-2.6"
    description: "Add tests/test_attribution_record_schema_fixtures.py case: a hand-written raw third-party value written directly into attribution_summary is a validation error — the value-free-mirror invariant."
    status: "pending"
    dependencies: ["SMP-2.3"]

  - id: "SMP-2.7"
    description: "Add tests/test_attribution_rollups.py: asserts best=max/weakest=min, cross-source values propagate as a canonically-sorted set-union stable across two independent runs, and confirms no numeric-averaging code path exists. Rollups are monotone only per the plan's accepted decision."
    status: "pending"
    dependencies: ["SMP-2.3"]

  - id: "SMP-2.8"
    description: "Add tests/test_attribution_staleness.py: asserts a refresh creates a NEW authoritative record and the prior record is left unmodified (append-only invariant) — staleness must not read as currency."
    status: "pending"
    dependencies: ["SMP-2.4"]

  - id: "SMP-2.G"
    description: "Milestone gate (validator lens): a record round-trips against its schema; a raw value in attribution_summary is a validation error; a mirror without its authoritative record fails validation; rollups are monotone and stably sorted; a refresh is append-only; divergence is detected with an injected as_of and the validator reads no wall clock."
    status: "pending"
    dependencies: ["SMP-2.5", "SMP-2.6", "SMP-2.7", "SMP-2.8"]

parallelization:
  batch_1: ["SMP-2.2"]
  batch_2: ["SMP-2.3", "SMP-2.4"]
  batch_3: ["SMP-2.5", "SMP-2.6", "SMP-2.7", "SMP-2.8"]
  batch_4: ["SMP-2.G"]
  critical_path: ["SMP-2.2", "SMP-2.3", "SMP-2.5", "SMP-2.G"]

blockers: []

success_criteria: [
  { id: "AC-M2-1", description: "An attribution record round-trips against its schema.", status: "pending" },
  { id: "AC-M2-2", description: "A hand-written raw third-party value in attribution_summary is a validation error (value-free-mirror invariant).", status: "pending" },
  { id: "AC-M2-3", description: "A mirror without its authoritative record fails validation (recompute-only invariant).", status: "pending" },
  { id: "AC-M2-4", description: "Divergence is detected with an injected as_of; the validator reads no wall clock.", status: "pending" },
  { id: "AC-M2-5", description: "Rollups are monotone (best=max/weakest=min) and canonically sorted, stable across two independent runs; no averaging path exists.", status: "pending" },
  { id: "AC-M2-6", description: "A refresh creates a NEW record; the prior record is left unmodified (append-only).", status: "pending" }
]

files_modified: []
---

# source-metadata-propagation - Phase 2 (M2): The attribution entity exists with a value-free, recompute-only mirror

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/source-metadata-propagation/phase-2-progress.md -t SMP-2.2 -s completed
```

---

## Objective

`schemas/source_attribution.schema.yaml` lands as the authoritative record (`additionalProperties: false`),
carrying `{source, value, observed_at, license_basis}` at minimum. The card's `attribution_summary` mirror
carries `attribution_ids`, counts, and the monotone rollups only — **never a raw third-party value** — and
is recomputed from authoritative records at export, so a hand-written value there is a validation error.
`attribution_triage.py` and `check_attribution_divergence(as_of=…)` follow the rights-entity patterns.

## Entry criteria

- **OQ-3 is resolved — no longer an entry-blocker.** The plan settles the mirror shape at plan-authoring
  time (`attribution_summary` = ids + counts + monotone rollups only, recompute-only); there is nothing
  left to decide at M2 entry.
- **M1 → M2 is merge-conflict hygiene, not a dependency (load-bearing, from plan).** Both milestones are
  additive under existing open seams in `schemas/source_card.schema.yaml`, and M2 could land first if
  convenient. It is sequenced only to keep two agents off one schema file — do not treat `M1` as a
  semantic blocker for this milestone. Confirm no concurrently-open edit to that file before landing
  `SMP-2.3` to avoid a merge conflict.

## Exit criteria

"An attribution record round-trips against its schema; the card's `attribution_summary` mirror carries
only `attribution_ids`, counts, and monotone rollups (never a raw value) and is recompute-only from
authoritative records; a refresh is append-only; divergence is detectable with an injected `as_of`."

## Gate lens

`validator` (per plan `wave_plan.phases[1].gate_lens`). No `gate_lens_reason` given for M2.

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| Record + value-free mirror | `./.venv/bin/python -m pytest tests/test_attribution_record_schema_fixtures.py -q` | exit 0; a mirror containing a raw value RAISES; a mirror without its authoritative record RAISES |
| Rollups monotone + sorted | `./.venv/bin/python -m pytest tests/test_attribution_rollups.py -q` | exit 0; asserts best=max/weakest=min, set-union order is stable across two runs, and no averaging path exists |
| Divergence uses injected clock | `./.venv/bin/python -m pytest tests/test_attribution_divergence.py -q` then `rg -n 'datetime\.now\|time\.time\|now_iso' src/research_foundry/services/attribution_*.py` | pytest exit 0 AND the `rg` returns **zero matches** — includes this repo's real idiom `now_iso()` (`ids.py:41`), not just `datetime.now` |
| Staleness is append-only | `./.venv/bin/python -m pytest tests/test_attribution_staleness.py -q` | exit 0; asserts a refresh creates a NEW record and the prior record is unmodified |

## Implementation Notes

Deviations and rationale go in `.claude/worknotes/source-metadata-propagation/implementation-notes.md`
(execution ledger), not here. OQ-3 is already resolved at plan-authoring time — no ledger entry needed for
it, only for genuine deviations from the plan's accepted decision.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges, recommendations
for M3 — including anything relevant to the M3 Mode-D halt (M3's control is now the schema's structural
`if/then` shape, not a field-name list; the name-based guards are defence-in-depth only).
