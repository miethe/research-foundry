---
type: progress
schema_version: 2
doc_type: progress
prd: source-metadata-propagation
feature_slug: source-metadata-propagation
milestone: "M1"
phase: 1
title: "First-party source metadata is real, contract-versioned, and reaches the bundle"
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

# Gate plan carried from the source plan's wave_plan.phases[] entry (id: M1) — do not re-derive.
# Escalated to two lenses post-review: M1 threads externally-controlled provider strings into
# cards that reach exported claim JSON (untrusted-input).
gate_lens: [security, validator]
gate_lens_reason: untrusted-input
mode_d_halt: false
karen_required_this_milestone: false   # M1-M3 are C2 — only the single end-of-feature karen pass

tasks:
  - id: "SMP-1.1"
    description: "Resolve OQ-1 (which search-router providers return DOI/citation counts/structured authors today) and OQ-4 (is trust.source_rank derivation deterministic, or does it need a capture-time model call) at entry; record both resolutions in the execution ledger."
    status: "pending"
    dependencies: []

  - id: "SMP-1.2"
    description: "Thread structured provider metadata (authors/DOI/publisher/version) onto the card in ingest_source(), replacing the hardcoded-empty fields at source_cards.py:322-338."
    status: "pending"
    dependencies: ["SMP-1.1"]

  - id: "SMP-1.3"
    description: "Implement genuine trust.source_rank derivation. Per plan: if source_rank cannot be derived deterministically it stays unknown and is set only by an explicit write recorded with provenance — never silently inferred."
    status: "pending"
    dependencies: ["SMP-1.1"]

  - id: "SMP-1.6"
    description: "Bound and type-check externally-controlled provider strings at the ingest boundary (length limits + type validation) before they reach the card. This is the untrusted-input control that motivated escalating this milestone's gate to [security, validator]. Include a malformed/oversized provider-string case that must be rejected."
    status: "pending"
    dependencies: ["SMP-1.1"]

  - id: "SMP-1.4"
    description: "Widen _resolve_source() hydration (export_service.py:580-661,1333) so authors/DOI/publisher/version/source_rank surface at claim level in an exported bundle."
    status: "pending"
    dependencies: ["SMP-1.2", "SMP-1.3", "SMP-1.6"]

  - id: "SMP-1.5"
    description: "Verify recomputability: call export_run() TWICE in-process, del the telemetry timeline from both outputs, canonical-sort, and assert equal. Must NOT use rf verify — verification.py never calls export_run(). No persisted derived state, no cached judgment, no wall-clock read on this path."
    status: "pending"
    dependencies: ["SMP-1.4"]

  - id: "SMP-1.7"
    description: "Add tests/test_source_rank_derivation.py: asserts a known source_type maps to a known trust.source_rank, and an unknown source_type stays unknown."
    status: "pending"
    dependencies: ["SMP-1.3"]

  - id: "SMP-1.8"
    description: "Version docs/dev/architecture/rf-run-export-schema.json for the changed exported payload shape, and add a legacy fixture in tests/test_schema_validation.py (-k export_schema) proving a pre-change export still validates against the bumped schema. This task was previously in no milestone at all — it is now part of M1's exit bar."
    status: "pending"
    dependencies: ["SMP-1.4"]

  - id: "SMP-1.G"
    description: "Milestone gate (security + validator lens, untrusted-input): a card ingested post-change carries populated, bounded authors/DOI/publisher; export hydration surfaces them at claim level; the exported contract is versioned with a passing legacy fixture."
    status: "pending"
    dependencies: ["SMP-1.5", "SMP-1.7", "SMP-1.8"]

parallelization:
  batch_1: ["SMP-1.1"]
  batch_2: ["SMP-1.2", "SMP-1.3", "SMP-1.6"]
  batch_3: ["SMP-1.4"]
  batch_4: ["SMP-1.5", "SMP-1.7", "SMP-1.8"]
  batch_5: ["SMP-1.G"]
  critical_path: ["SMP-1.1", "SMP-1.2", "SMP-1.4", "SMP-1.8", "SMP-1.G"]

blockers: []

success_criteria: [
  { id: "AC-M1-1", description: "A card ingested post-change has non-empty, bounded/type-checked authors/DOI/publisher; a malformed/oversized provider-string case is rejected.", status: "pending" },
  { id: "AC-M1-2", description: "The same values appear in the exported claim rows.", status: "pending" },
  { id: "AC-M1-3", description: "Two in-process export_run() calls over unchanged files produce equal output once the telemetry timeline is del'd and both are canonical-sorted.", status: "pending" },
  { id: "AC-M1-4", description: "trust.source_rank is derived deterministically for a known source_type; an unknown source_type stays unknown.", status: "pending" },
  { id: "AC-M1-5", description: "rf-run-export-schema.json is versioned for the changed payload shape; a pre-change legacy fixture still validates.", status: "pending" }
]

files_modified: []
---

# source-metadata-propagation - Phase 1 (M1): First-party source metadata is real, contract-versioned, and reaches the bundle

**YAML frontmatter is the source of truth for tasks, status, and gate plan.** Do not duplicate in markdown.

Update progress via CLI (see `.claude/rules/progress-cli-only.md`):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/source-metadata-propagation/phase-1-progress.md -t SMP-1.1 -s completed
```

---

## Objective

`ingest_source()` threads structured provider metadata onto the card, bounding/type-checking those
externally-controlled strings at the ingest boundary before they reach a card; `trust.source_rank` is
genuinely derived (or explicitly left `unknown`); `_resolve_source()` hydration widens so those values
appear at claim level in an exported bundle; and the exported payload shape change is versioned in
`rf-run-export-schema.json` with a passing legacy fixture — all with zero persisted derived state.

## Entry criteria

None declared (`depends_on: []` in the plan's `wave_plan`). This is the first milestone.

## Exit criteria (verbatim from plan)

"A card ingested post-change carries populated authors/DOI/publisher; export hydration surfaces them at
claim level; the exported contract is versioned with a passing legacy fixture."

## Gate lens

`security`, `validator` — `gate_lens_reason: untrusted-input` (per plan `wave_plan.phases[0]`, escalated
post-review). Provider strings are externally controlled and thread into cards that reach exported claim
JSON, so this milestone carries a security lens in addition to validator.

## AC -> command -> evidence (from plan)

| AC | Command | Evidence of pass |
|---|---|---|
| Metadata populated, bounded | `./.venv/bin/python -m pytest tests/test_source_metadata_capture.py -q` | exit 0 AND collected>0; includes a malformed/oversized provider-string case that must be rejected |
| source_rank derived | `./.venv/bin/python -m pytest tests/test_source_rank_derivation.py -q` | exit 0; asserts a known `source_type` maps to a known rank, and unknown stays `unknown` |
| Export is recomputable | `./.venv/bin/python -m pytest tests/test_export_recomputability.py -q` | calls `export_run()` **twice in-process**, `del`s the telemetry `timeline`, canonical-sorts, asserts equal. Must NOT use `rf verify` — `verification.py` never calls `export_run()` |
| Export contract versioned | `./.venv/bin/python -m pytest tests/test_schema_validation.py -q -k export_schema` | exit 0; a pre-change legacy export fixture still validates against the bumped `rf-run-export-schema.json` |

## Sequencing note (load-bearing, from plan)

M1 and M2 both edit `schemas/source_card.schema.yaml`. **This is merge-conflict hygiene, not a semantic
dependency** — both milestones are additive under existing open seams in that file, and M2 could land
first if convenient. It is sequenced only to keep two agents off one schema file at once; do not treat it
as an immovable barrier. (M2 → M3 → M4 remain genuine semantic dependencies — see those phases' files.)

## Named risks relevant to this milestone (from plan)

- No-backfill result-set bias is certain by construction — pre-existing cards will read "no data"
  indistinguishably from "verified zero" until M4 ships tri-state coverage. Not this milestone's fix,
  but do not paper over it here.
- Provider strings are untrusted input (motivates this milestone's `security` gate lens): bound and
  type-check at the ingest boundary (`SMP-1.6`) — do not let an oversized or malformed provider string
  reach the card unchecked.
- Any change to the exported payload shape must version `rf-run-export-schema.json` and ship a legacy
  fixture (`SMP-1.8`) — the current resolved-source schema permits arbitrary properties, so undocumented
  output can otherwise ship silently.

## Implementation Notes

Deviations, OQ-1/OQ-4 resolutions, and rationale go in
`.claude/worknotes/source-metadata-propagation/implementation-notes.md` (execution ledger), not here.

## Completion Notes

Fill in when this phase is complete: what was built, key learnings, unexpected challenges, recommendations
for M2.
