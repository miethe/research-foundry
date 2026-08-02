---
type: progress
schema_version: 2
doc_type: progress
prd: source-metadata-propagation
feature_slug: source-metadata-propagation
milestone: "M3"
phase: 3
title: "The provenance boundary is structurally closed"
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

# Gate plan carried from the source plan's wave_plan.phases[] entry (id: M3) — do not re-derive.
gate_lens: [security, validator]
gate_lens_reason: authz-boundary
mode_d_halt: true    # M3 changes an authorization boundary — halt for explicit human approval before landing the guard
karen_required_this_milestone: false   # M1-M3 are C2 — only the single end-of-feature karen pass

tasks:
  - id: "SMP-3.0-HALT"
    description: "MODE-D HALT: obtain explicit human approval for the authorization-boundary change before landing the schema's structural if/then (SMP-3.2B) or the defence-in-depth name guards (SMP-3.1/3.2). Per plan: 'M3 changes an authorization boundary and ... halt.' Do not proceed to SMP-3.1+ without recorded approval."
    status: "pending"
    dependencies: []

  - id: "SMP-3.1"
    description: "Add no_agent_authored_attribution_value to the guard set in governance.py. DEFENCE-IN-DEPTH ONLY per the plan's redesign — the primary control is the schema's structural shape (SMP-3.2B), not this name-based rule."
    status: "pending"
    dependencies: ["SMP-3.0-HALT"]

  - id: "SMP-3.2"
    description: "Extend _RIGHTS_GOVERNED_FIELDS (governance.py:35-40) to cover the new attribution fields. DEFENCE-IN-DEPTH ONLY. Named risk from plan: a name list is structurally blind by construction — it would still miss a sibling field like trust.third_party_citation_rank, which is exactly why SMP-3.2B's structural control is primary."
    status: "pending"
    dependencies: ["SMP-3.0-HALT"]

  - id: "SMP-3.2B"
    description: "Add the PRIMARY structural control to schemas/source_attribution.schema.yaml: additionalProperties: false plus 'if asserter_type startsWith third_party_ then retrieval_evidence_ref required'. This schema shape — not the governance.py name guards — IS the authorization-boundary change the Mode-D halt gates."
    status: "pending"
    dependencies: ["SMP-3.0-HALT"]

  - id: "SMP-3.3"
    description: "Write negative tests: an agent-writable path writing asserter_type: third_party_* with null retrieval_evidence_ref is rejected — primarily by the schema's structural if/then (SMP-3.2B), with the name-based guards (SMP-3.1/3.2) as defence-in-depth."
    status: "pending"
    dependencies: ["SMP-3.1", "SMP-3.2", "SMP-3.2B"]

  - id: "SMP-3.3B"
    description: "Write the sibling-field bypass negative test: an agent writing trust.third_party_citation_rank (a field name NOT on the guarded list) must ALSO be rejected. This is the test that proves the control is structural, not name-based — and the one a name-list-only design would fail."
    status: "pending"
    dependencies: ["SMP-3.2B"]

  - id: "SMP-3.4"
    description: "Mutation-verify the PRIMARY control: remove the schema if/then added in SMP-3.2B, re-run SMP-3.3 and SMP-3.3B; confirm the suite goes RED (proves non-vacuity — a still-green suite proves the control was never load-bearing). Restore the if/then afterward."
    status: "pending"
    dependencies: ["SMP-3.3", "SMP-3.3B"]

  - id: "SMP-3.5"
    description: "Verify the pediatric_cds namespace stays clean: the writer never emits pediatric_cds.<new_key>. Named risk from plan: both oneOf branches in pediatric_cds.schema.json:18-24 are additionalProperties: false, so a stray key is a hard ExitCode.SCHEMA(2)."
    status: "pending"
    dependencies: ["SMP-3.1", "SMP-3.2B"]

  - id: "SMP-3.G"
    description: "Milestone gate (security + validator lens, authz-boundary): a third_party_* value without retrieval_evidence_ref is rejected by schema shape; a sibling-field bypass attempt (trust.third_party_citation_rank) is rejected too; removing the schema if/then turns the suite RED (mutation-verified, not just green)."
    status: "pending"
    dependencies: ["SMP-3.4", "SMP-3.5"]

parallelization:
  batch_1: ["SMP-3.0-HALT"]
  batch_2: ["SMP-3.1", "SMP-3.2", "SMP-3.2B"]
  batch_3: ["SMP-3.3", "SMP-3.3B", "SMP-3.5"]
  batch_4: ["SMP-3.4"]
  batch_5: ["SMP-3.G"]
  critical_path: ["SMP-3.0-HALT", "SMP-3.2B", "SMP-3.3B", "SMP-3.4", "SMP-3.G"]

blockers:
  - id: "BLOCKER-M3-1"
    title: "Mode-D halt: authorization-boundary change requires explicit human approval"
    severity: "critical"
    blocking: ["SMP-3.1", "SMP-3.2", "SMP-3.2B", "SMP-3.3", "SMP-3.3B", "SMP-3.4", "SMP-3.5", "SMP-3.G"]
    resolution: "Awaiting explicit human sign-off before landing the schema's structural if/then (SMP-3.2B) or the defence-in-depth name guards (no_agent_authored_attribution_value / _RIGHTS_GOVERNED_FIELDS extension), per the plan's Mode-D note and execution ledger."
    created: "2026-08-02"

success_criteria: [
  { id: "AC-M3-1", description: "A third_party_* value without retrieval_evidence_ref is rejected by schema shape (the primary structural control).", status: "pending" },
  { id: "AC-M3-1B", description: "A sibling-field bypass (trust.third_party_citation_rank) is also rejected — proves the control is structural, not name-based.", status: "pending" },
  { id: "AC-M3-2", description: "The negative test suite fails closed (goes RED) when the schema if/then is removed (mutation-verified) — proves non-vacuity.", status: "pending" }
]

files_modified: []
---

# source-metadata-propagation - Phase 3 (M3): The provenance boundary is structurally closed

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/source-metadata-propagation/phase-3-progress.md -t SMP-3.0-HALT -s completed
```

---

## MODE-D HALT — read this before assigning any task in this file

**This milestone changes an authorization boundary.** Per the plan's execution ledger: "Mode-D always
halts for explicit human approval — auth · payments · schema migrations · data deletion · secret rotation
· infrastructure. **M3 changes an authorization boundary ... : both halt.**" The actual boundary change is
the schema's structural `if/then` requirement (`SMP-3.2B`), not the governance.py name guards. No task past
`SMP-3.0-HALT` may start without recorded, explicit human approval.

## Objective

The authoritative record schema enforces `if asserter_type startsWith third_party_ then
retrieval_evidence_ref required` — this structural shape is the **primary** control. The name-based
`no_agent_authored_attribution_value` guard and the `_RIGHTS_GOVERNED_FIELDS` extension remain as
defence-in-depth, explicitly **not** the primary control: a name list is defeated by any sibling field an
agent chooses not to name, which is exactly what `SMP-3.3B`'s bypass test proves.

## Entry criteria

- **M2 completed.** `wave_plan.phases[].depends_on: ["M2"]` — this is a genuine semantic dependency (M3
  enforces a shape M2 defines), unlike the M1→M2 file-hygiene sequencing.
- **Mode-D halt cleared.** Explicit human approval recorded before any guard-landing work (`SMP-3.1`
  onward) begins.

## Exit criteria (verbatim from plan)

"A third_party_* value without retrieval_evidence_ref is rejected by schema shape; sibling-field bypass
attempts are rejected too; removing the control turns the suite RED."

## Gate lens

`security`, `validator` — `gate_lens_reason: authz-boundary` (per plan `wave_plan.phases[2]`).

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| Provenance is structural | `./.venv/bin/python -m pytest tests/test_governance_adversarial.py -q -k attribution` | exit 0; includes a **sibling-field bypass** case (`trust.third_party_citation_rank`) that must also be rejected |
| Control is non-vacuous | remove the schema `if/then`, re-run the row above | suite must go **RED**; a still-green suite proves the control was never load-bearing |
| Pediatric namespace clean | `./.venv/bin/python -m pytest tests/ -q -k pediatric_namespace` | exit 0; asserts the writer never emits `pediatric_cds.<new_key>` |

## Implementation Notes

Deviations and rationale go in `.claude/worknotes/source-metadata-propagation/implementation-notes.md`
(execution ledger), not here — including the record of when/how Mode-D approval was obtained.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges, recommendations
for M4 — including anything relevant to M4's own Mode-D halt (catalog schema migration) and its per-milestone
karen pass.
