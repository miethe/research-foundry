---
type: progress
schema_version: 2
doc_type: progress
prd: source-metadata-propagation
feature_slug: source-metadata-propagation
milestone: "M4"
phase: 4
title: "Queryable, tri-state honest, and non-regressive"
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

total_tasks: 9
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

# Gate plan carried from the source plan's wave_plan.phases[] entry (id: M4) — do not re-derive.
gate_lens: [security, validator]
gate_lens_reason: irreversible-outward
mode_d_halt: true    # M4 performs a catalog schema migration — halt for explicit human approval before landing
karen_required_this_milestone: true    # M4 is the plan's C3 milestone — gets its OWN karen pass, in
                                        # addition to (not instead of) the single end-of-feature karen that
                                        # M1-M3 (C2) rely on. Do not apply a per-milestone karen pass to M1-M3.

tasks:
  - id: "SMP-4.0-HALT"
    description: "MODE-D HALT: obtain explicit human approval for the catalog schema migration before landing any catalog column or sqlite row-builder change. Per plan: 'M4 performs a catalog schema migration: ... halt.' Do not proceed to SMP-4.1+ without recorded approval."
    status: "pending"
    dependencies: []

  - id: "SMP-4.1"
    description: "Resolve OQ-2 at entry (is the catalog sqlite migration path established, or rebuild-only) and record the decision in the execution ledger — M4 sizing rests on it."
    status: "pending"
    dependencies: ["SMP-4.0-HALT"]

  - id: "SMP-4.2"
    description: "Add catalog columns for the new attributes (catalog_service.py:557-572,850-889,1341-1349). Named risk from plan: catalog_service.py is 2242 lines (H7) and already carries a 2x multiplier — do not re-plan this task small."
    status: "pending"
    dependencies: ["SMP-4.1"]

  - id: "SMP-4.3"
    description: "Implement sqlite row builders for the new attributes, per the OQ-2 migration-path decision."
    status: "pending"
    dependencies: ["SMP-4.1"]

  - id: "SMP-4.4"
    description: "Implement rollup logic: monotone only (best/weakest_source_rank); refuse numeric averaging across assertion_kinds; cross-source values propagate as set-union keyed by (asserter_id, assertion_kind). Consumes both M1's hydration and M2's records."
    status: "pending"
    dependencies: ["SMP-4.2", "SMP-4.3"]

  - id: "SMP-4.5"
    description: "Implement the tri-state coverage query surface: present / absent / not-yet-assessed, reporting 'N of M sources assessed'. No backfill — this ships WITH the query surface, per the plan's accepted decision."
    status: "pending"
    dependencies: ["SMP-4.4"]

  - id: "SMP-4.6"
    description: "Regression-fixture scaffolding for catalog attribution coverage tests."
    status: "pending"
    dependencies: ["SMP-4.5"]

  - id: "SMP-4.7"
    description: "Live non-regression check: assert a COUNTED sweep of all 7 committed pediatric_cds bundles verifies — not merely a loop exit code. Use: `set -euo pipefail; n=0; for r in runs/*pediatric_cds*/; do ./.venv/bin/rf verify \"$(basename $r)\"; n=$((n+1)); done; test \"$n\" -eq 7`. A `for` loop over a glob matching zero bundles exits 0 vacuously — `test \"$n\" -eq 7` is the actual gate. Named risk from plan: the exploration code-traced this, never ran it live."
    status: "pending"
    dependencies: ["SMP-4.2", "SMP-4.3"]

  - id: "SMP-4.G"
    description: "Milestone gate (security + validator lens, irreversible-outward) PLUS this milestone's own karen pass: a catalog filter on a new attribute returns rows plus an N-of-M coverage line; all 7 bundles exit 0."
    status: "pending"
    dependencies: ["SMP-4.6", "SMP-4.7"]

parallelization:
  batch_1: ["SMP-4.0-HALT"]
  batch_2: ["SMP-4.1"]
  batch_3: ["SMP-4.2", "SMP-4.3"]
  batch_4: ["SMP-4.4", "SMP-4.7"]
  batch_5: ["SMP-4.5"]
  batch_6: ["SMP-4.6"]
  batch_7: ["SMP-4.G"]
  critical_path: ["SMP-4.0-HALT", "SMP-4.1", "SMP-4.2", "SMP-4.4", "SMP-4.5", "SMP-4.6", "SMP-4.G"]

blockers:
  - id: "BLOCKER-M4-1"
    title: "Mode-D halt: catalog schema migration requires explicit human approval"
    severity: "critical"
    blocking: ["SMP-4.1", "SMP-4.2", "SMP-4.3", "SMP-4.4", "SMP-4.5", "SMP-4.6", "SMP-4.7", "SMP-4.G"]
    resolution: "Awaiting explicit human sign-off before landing catalog columns / sqlite row builders, per the plan's Mode-D note and execution ledger."
    created: "2026-08-02"

success_criteria: [
  { id: "AC-M4-1", description: "A catalog filter on a new attribute returns rows plus an N-of-M coverage line.", status: "pending" },
  { id: "AC-M4-2", description: "All 7 pediatric_cds bundles verify on a live, COUNTED sweep — `test \"$n\" -eq 7` is the gate, not the loop's exit code.", status: "pending" },
  { id: "AC-M4-3", description: "This milestone receives its own karen pass in addition to the single end-of-feature karen (M1-M3 do not get a per-milestone karen).", status: "pending" }
]

files_modified: []
---

# source-metadata-propagation - Phase 4 (M4): Queryable, tri-state honest, and non-regressive

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/source-metadata-propagation/phase-4-progress.md -t SMP-4.0-HALT -s completed
```

---

## MODE-D HALT — read this before assigning any task in this file

**This milestone performs a catalog schema migration.** Per the plan's execution ledger: "Mode-D always
halts for explicit human approval — auth · payments · schema migrations · data deletion · secret rotation
· infrastructure. **... M4 performs a catalog schema migration: both halt.**" No task past `SMP-4.0-HALT`
may start without recorded, explicit human approval.

## Per-milestone karen pass (this milestone only)

This plan's `context_class` is `C3`, dominated by M4 (`catalog_service.py` at 2242 lines + 7-bundle
fan-out). Per the plan frontmatter (`karen: true` on the M4 `wave_plan` entry), **M4 gets its own karen
pass** on top of the plan's single end-of-feature karen review. **M1, M2, and M3 are C2 and do NOT get a
per-milestone karen** — they rely solely on that final tree-wide pass. Do not schedule a karen review on
M1-M3's gates; do schedule one here.

## Objective

Catalog columns and sqlite rows carry the new attributes; the query surface reports coverage as
`present` / `absent` / `not-yet-assessed` and states "N of M sources assessed". All 7 pediatric bundles
verify live.

## Entry criteria

- **M3 completed.** `wave_plan.phases[].depends_on: ["M3"]` — "M4's rollups and columns consume both M1's
  hydration and M2's records."
- **Mode-D halt cleared.** Explicit human approval recorded before any catalog-schema-migration work
  (`SMP-4.1` onward) begins.

## Exit criteria (verbatim from plan)

"Catalog filters on the new attributes and reports N-of-M coverage; all 7 pediatric bundles verify live."

## Gate lens

`security`, `validator` — `gate_lens_reason: irreversible-outward` (per plan `wave_plan.phases[3]`), plus
this milestone's dedicated karen pass (see above).

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| Tri-state coverage surfaced | `./.venv/bin/python -m pytest tests/test_catalog_attribution_coverage.py` | exit 0; `absent` and `not-yet-assessed` assert as distinct values |
| All 7 bundles non-regressive | `set -euo pipefail; n=0; for r in runs/*pediatric_cds*/; do ./.venv/bin/rf verify "$(basename $r)"; n=$((n+1)); done; test "$n" -eq 7` | the `test -eq 7` is the gate — a glob that matches nothing makes a `for` loop exit 0 vacuously; the prior `ls \| grep` form was exactly this vacuity risk |

## Named risks relevant to this milestone (from plan)

- No-backfill result-set bias: pre-existing cards read "no data" indistinguishably from "verified zero"
  until this milestone's tri-state coverage ships — this is the fix, not a deferred concern.
- `catalog_service.py` is 2242 lines (H7); the plan already carries a 2x multiplier for it — do not
  compress this milestone's estimate.
- The 7-bundle non-regression is currently unproven (code-traced only, never run live) — `SMP-4.7` closes
  that gap.
- **A `for` loop over `grep`/glob output exits 0 on zero matches.** The sweep must assert a *count*
  (`test "$n" -eq 7`), not just a clean loop exit — the prior `for r in $(ls runs | grep pediatric_cds)`
  form was exactly this vacuity risk and has been replaced in the AC table above.

## Implementation Notes

Deviations, the OQ-2 resolution, and rationale go in
`.claude/worknotes/source-metadata-propagation/implementation-notes.md` (execution ledger), not here —
including the record of when/how Mode-D approval was obtained.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges, and the outcome
of this milestone's dedicated karen pass plus the plan's final end-of-feature karen pass.
