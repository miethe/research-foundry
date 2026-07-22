---
type: progress
schema_version: 2
doc_type: progress
prd: "rfup-external-routing"
feature_slug: "rfup-external-routing"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
execution_model: batch-parallel
phase: 6
title: "Docs / Deferrals Finalization (DOC-006)"
status: "pending"
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

owners: ["documentation-writer", "changelog-generator"]
contributors: []

model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "P6-001"
    description: "CHANGELOG [Unreleased] entry covering P1 (test coverage), P2 (schema hard-gate), P3 (auto-strict eligibility default), P4 (new quote-fidelity check), P5 (ADR-0008 verdict) — categorized per .claude/specs/changelog-spec.md."
    status: "pending"
    assigned_to: ["changelog-generator"]
    dependencies: ["P1-001", "P1-002", "P3-003", "P4-004", "SEAM-001", "P5-004"]
    estimated_effort: "0.5pt"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P6-002"
    description: "(DOC-006a) Update rfup-6-native-discovery-adapters.md in place with the P5 verdict on litellm_router and reaffirmed defer-until triggers for the remaining 5 adapters (gpt_researcher, notebooklm, openai_agents, paperqa2, opencode)."
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-004"]
    estimated_effort: "1pt"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P6-003"
    description: "(DOC-006b) Author new design-spec at docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md (maturity: shaping) documenting P5's verdict + install/wiring plan; explicitly states the ADR-0008 status transition in pediatric-anemia-site is out of scope here."
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5-004"]
    estimated_effort: "1pt"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P6-004"
    description: "Context-file pointers: add <=3-line CLAUDE.md/key-context pointers for the new rf verify gate behavior introduced by P2/P3/P4 (schema hard-gate, eligibility default, fidelity check)."
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P3-003", "P4-004"]
    estimated_effort: "0.5pt"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P6-005"
    description: "Finalize plan frontmatter: set parent plan status: completed, populate commit_refs/files_affected/updated, append both DOC-006a/DOC-006b spec paths to deferred_items_spec_refs."
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P6-001", "P6-002", "P6-003", "P6-004"]
    estimated_effort: "0.5pt"
    priority: "medium"
    assigned_model: "sonnet"
    model_effort: "adaptive"

parallelization:
  batch_1: ["P6-001", "P6-002", "P6-003", "P6-004"]
  batch_2: ["P6-005"]
  critical_path: ["P6-002", "P6-005"]
  estimated_total_time: "3pts"

blockers: []

success_criteria:
  - { id: "SC-1", description: "CHANGELOG [Unreleased] entry present", status: "pending" }
  - { id: "SC-2", description: "Both deferred-items triage-table rows have an authored design-spec (deferred_items_spec_refs populated)", status: "pending" }
  - { id: "SC-3", description: "task-completion-validator pass, then end-of-feature karen pass", status: "pending" }

files_modified: []

notes: "Wave 4, final (depends_on: [P1, P3, P4, P5]). Haiku override: both changelog-generator and documentation-writer route on sonnet in this environment (haiku-model default agents hard-error here — see project memory haiku-subagents-inaccessible), overriding this repo's standard haiku-default convention for this phase. End-of-feature karen pass runs after this phase — the second and final karen checkpoint for the whole feature."
---

# rfup-external-routing - Phase 6: Docs / Deferrals Finalization (DOC-006)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/rfup-external-routing/phase-6-progress.md -t P6-001 -s completed --started <ISO8601> --completed <ISO8601> --evidence "commit:<sha>"
```

---

## Objective

Close out the plan: a CHANGELOG entry covering all five preceding phases' operator-facing changes, authored design-specs for both Deferred Items Triage Table rows (DF-RFUP-EXT-01, DF-RFUP-EXT-02), context-file pointers for the new `rf verify` gate behavior, and a finalized parent-plan frontmatter.

---

## Implementation Notes

### Architectural Decisions

`rfup-6-native-discovery-adapters.md` is updated **in place**, not replaced — the 5 unevaluated adapters' `maturity: idea` framing must be retained/reaffirmed (P5 evaluated only `litellm_router`; this phase does not promote the other 5).

### Patterns and Best Practices

Full task detail, ACs (AC-P6-1 through AC-P6-15), and quality gates: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-6-docs-deferrals.md`.

### Known Gotchas

- Do not let DOC-006a accidentally promote the 5 unevaluated adapters out of `idea` maturity.
- `deferred_items_spec_refs` on the parent plan must end up populated with both `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` and `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md` — no triage-table row left with an unresolved Target Spec Path placeholder.
- `findings_doc_ref` must remain `null` (no findings occurred) OR, if populated during execution, be finalized to `status: accepted` before this phase is sealed.

### Development Setup

None.

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
