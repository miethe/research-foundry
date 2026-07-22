---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 5
phase_id: P5
title: "Phase 5: Governance Gate + Canonical ADR \u2014 Progress"
status: completed
created: '2026-07-21'
updated: '2026-07-21'
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-5-6-governance-finalize.md
commit_refs:
- 0868aea
pr_refs: []
execution_model: batch-parallel
reviewer_gate: task-completion-validator
overall_progress: 100
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
- documentation-writer
contributors: []
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P5-1
  title: 'governance.py guard rule: agent-write ban'
  description: "New guard rule in services/governance.py (following the existing work_writeback_requires_review/intenttree_writeback_requires_review\
    \ pattern) blocking any agent-writable code path from producing CLEARED_*, counsel_approved,\
    \ or attestation.status=attested on: rights_record.overall_status, content_reuse_assessment.decision.status,\
    \ rights_extension.clearance_status, synthesis.attestation.status (the last already\
    \ guarded by P3-3/P3-4 at the service layer \u2014 this rule is the governance-layer\
    \ backstop covering all 4 fields uniformly)."
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-4
  estimated_effort: 2 pts
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-21T00:00Z
  completed: 2026-07-21T00:45Z
  evidence:
  - commit: pending
  - test: tests/test_governance_adversarial.py
  verified_by:
  - task-completion-validator
- id: P5-2
  title: 'Negative test: agent path to cleared rights values is unreachable'
  description: "Mandatory per the binding authorization-boundary requirement \u2014\
    \ the P5 counterpart to P3-4. Enumerate every code path that can write rights_record.overall_status,\
    \ content_reuse_assessment.decision.status, content_reuse_assessment.decision.release_gate,\
    \ and rights_extension.clearance_status, and assert none can produce a CLEARED_*/counsel_approved/OWNED-without-first-party-basis\
    \ value from an agent identity. Independent test suite from P3-4 (different fields,\
    \ different write paths) \u2014 must not be collapsed into or treated as redundant\
    \ with P3-4."
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P5-1
  estimated_effort: 2 pts
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  started: 2026-07-21T02:00Z
  completed: 2026-07-21T04:00Z
  evidence:
  - test: tests/unit/test_rights_status_write_ceiling.py
  - test: tests/unit/test_synthesis_attestation_write_ceiling.py
  verified_by:
  - task-completion-validator
- id: P5-3
  title: 'Release-gate rule: judgment_basis: unassessed'
  description: "Add the bidirectional release-gate predicate. Resolves decisions-block\
    \ OQ-6: predicate lives in governance.py (policy ownership); verification.py::verify_report\
    \ calls it as a new named check in its existing check sequence at verify-time\
    \ (governance.py owns the boolean logic, verification.py is a caller \u2014 not\
    \ a duplicate implementation). Blocks commercial-release disposition evaluation\
    \ when judgment_basis: unassessed; non-blocking for internal-capture writes."
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-4
  - P5-1
  estimated_effort: 1 pt
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-21T01:00Z
  completed: 2026-07-21T02:00Z
  evidence:
  - test: tests/test_release_gate_judgment_basis.py
  verified_by:
  - task-completion-validator
- id: P5-4
  title: Author canonical rights ADR
  description: "Author docs/dev/architecture/adr-rights-entity-model.md, following\
    \ adr-runs-read-path.md's frontmatter/section pattern. Must record: all 10 \xA7\
    9 adjudications (table, reusing the decisions-block's adjudication table as base\
    \ content), resolves: [OQ-RF-1, OQ-RF-2, OQ-RF-3, OQ-RF-4], and an explicit 'Known\
    \ Gaps' section naming OQ-RF-5 (surveillance execution) and OQ-RF-6 (counsel/rights-owner\
    \ role) as named debt, cross-referencing the P6-8 DOC-006 design specs for each.\
    \ May start once P3 lands (parallel to P4); does not require P4/P5-1/P5-2/P5-3\
    \ complete."
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P3-4
  estimated_effort: 2 pts
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-21T00:00Z
  completed: 2026-07-21T00:30Z
  evidence:
  - file: docs/dev/architecture/adr-rights-entity-model.md
  verified_by:
  - task-completion-validator
parallelization:
  batch_1:
  - P5-1
  - P5-4
  batch_2:
  - P5-2
  - P5-3
  critical_path:
  - P5-1
  - P5-2
  estimated_total_time: 7 pts (plan bottom-up estimate)
blockers: []
success_criteria:
- id: P5-SC1
  description: governance.py guard rule enumerates all 4 named fields explicitly (rights_record.overall_status,
    content_reuse_assessment.decision.status, rights_extension.clearance_status, synthesis.attestation.status)
  status: pending
- id: P5-SC2
  description: "P5-2's negative test is independent of P3-4 (different fields/paths)\
    \ and passes \u2014 combined, the \xA79.10 gap is closed over both write paths"
  status: pending
- id: P5-SC3
  description: Release-gate bidirectional test passes in both directions (commercial-release
    blocked, internal-capture unblocked)
  status: pending
- id: P5-SC4
  description: "ADR published with all 10 \xA79 rows + OQ-RF-1..4 resolved + OQ-RF-5/6\
    \ named as gaps with links to P6-8 design specs"
  status: pending
- id: P5-SC5
  description: 'Reviewer gate: task-completion-validator'
  status: pending
notes: "Parallel-slice: P5 depends on P3, not P4 (both P4 and P5 depend on P3 independently)\
  \ and may run\nalongside P4 with a different owner-file set (governance.py/verification.py/ADR\
  \ vs\nsource_cards.py/capture.py/cli_commands.py \u2014 no file overlap).\n\xA7\
  9.10 note: P5-1/P5-2 close the OTHER half of the two-write-path authorization gap\
  \ the handoff's\n\xA79.10 finding flagged (P3-4 closed the synthesis.attestation.status\
  \ path in Phase 3). The boundary\nis only fully proven once both P3-4 and P5-2 pass\
  \ \u2014 neither phase's negative test alone is\nsufficient (independent verification\
  \ of both paths, by design).\nP5-4 (ADR) can start once P3 lands and does not block\
  \ on P5-1/P5-2/P5-3 \u2014 owner is\ndocumentation-writer, not python-backend-engineer."
progress: 100
---

# rights-entity-model — Phase 5: Governance Gate + Canonical ADR

**YAML frontmatter is the source of truth.** Do not duplicate in markdown. Update via CLI only.

---

## Objective

Close the other half of the §9.10 authorization boundary (governance-layer guard rule +
independent negative test over `rights_record.overall_status` /
`content_reuse_assessment.decision.status` / `rights_extension.clearance_status`), add the
bidirectional `judgment_basis: unassessed` release-gate predicate, and author RF's canonical
rights ADR recording all 10 §9 adjudications plus named debt for OQ-RF-5/OQ-RF-6.

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1 (parallel — single message, 2 calls; P5-4 depends only on P3-4, different owner)
Task("python-backend-engineer", "P5-1: New guard rule in services/governance.py (following work_writeback_requires_review pattern) blocking agent-writable code paths from producing CLEARED_*/counsel_approved/attested on rights_record.overall_status, content_reuse_assessment.decision.status, rights_extension.clearance_status, synthesis.attestation.status. Full AC in docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-5-6-governance-finalize.md (P5-1 row). Depends on P3-4.", model="sonnet")

Task("documentation-writer", "P5-4: Author docs/dev/architecture/adr-rights-entity-model.md following adr-runs-read-path.md's pattern. Must record all 10 §9 adjudications (reuse decisions-block table), resolves: [OQ-RF-1..4], and a 'Known Gaps' section for OQ-RF-5/OQ-RF-6 linking to P6-8 design specs. Full AC in phase-5-6-governance-finalize.md (P5-4 row). May start once P3 lands.", model="sonnet")

# Batch 2 (parallel — single message, 2 calls; both depend on P5-1 only)
Task("python-backend-engineer", "P5-2 (mandatory, binding requirement): Independent negative test suite — enumerate every agent-reachable write path to rights_record.overall_status, content_reuse_assessment.decision.status, content_reuse_assessment.decision.release_gate, rights_extension.clearance_status; assert none can produce a cleared value from an agent identity. Must NOT be collapsed into or treated as redundant with P3-4. Full AC in phase-5-6-governance-finalize.md (P5-2 row).", model="sonnet")

Task("python-backend-engineer", "P5-3: Bidirectional release-gate predicate for judgment_basis: unassessed. Predicate lives in governance.py; verification.py::verify_report calls it as a new check at verify-time (resolves decisions-block OQ-6). Full AC in phase-5-6-governance-finalize.md (P5-3 row). Depends on P1-4, P5-1.", model="sonnet")
```

### Reviewer Gate (task-completion-validator)

```markdown
Task("task-completion-validator", "Verify Phase 5 (Governance Gate + Canonical ADR) of rights-entity-model against docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-5-6-governance-finalize.md Phase 5 quality gates. Confirm P5-2 is genuinely independent of P3-4 (different fields/paths, not a rename), and the ADR's 10 §9 rows + OQ-RF-1..4 resolutions + OQ-RF-5/6 named-gap section are all present.", model="sonnet")
```

---

## Implementation Notes

### Known Gotchas

- P5-2 must be an *independent* test suite from P3-4 — same discipline (allow-list enumeration of function names in the test docstring) but different fields/write-paths. Collapsing the two into one test suite fails the §9.10 exit condition even if all assertions pass.
- P5-4 (ADR) has no dependency on P5-1/P5-2/P5-3 — do not block its dispatch waiting on the governance-gate tasks.

---

## Completion Notes

_(Fill in when phase is complete.)_
