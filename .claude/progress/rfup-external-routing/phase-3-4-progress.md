---
type: progress
schema_version: 2
doc_type: progress
prd: "rfup-external-routing"
feature_slug: "rfup-external-routing"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
execution_model: batch-parallel
phase: "3-4"
title: "Exact-Passage Eligibility (P3) + Quote-Fidelity Gate (P4) + Seam Regression (SEAM-001)"
status: "pending"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

model_usage:
  primary: "sonnet"
  external: []

integration_owner: "python-backend-engineer"
seam_tasks: ["SEAM-001"]

tasks:
  - id: "P3-001"
    description: "Clinical-eligibility filter: assertion_kind == threshold AND (pediatric_cds block present on a cited card OR existing sensitivity tag) -> force exact_passage_mode: strict for that claim, independent of the run's configured/CLI mode."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-001", "P2-002", "P2-003"]
    estimated_effort: "2pts"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P3-002"
    description: "Default policy wiring: document the default in config/claim_policy.yaml (and/or CLI default) so pediatric/CDS runs get P3-001's behavior without an explicit --exact-passage strict flag."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-001"]
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-003"
    description: "Eligibility regression tests: 0 false-positive hard-gates against existing non-clinical warn-mode runs; positive case (threshold+clinical-eligible claim lacking a locator fails closed)."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-002"]
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-001"
    description: "Quote-vs-source diff check: new check function comparing an extracted quote's characters against the stored full-text source rendering; distinct from check_anchor_hash_match (post-hoc tampering detection, not extraction-time corruption)."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-001", "P2-002", "P2-003"]
    estimated_effort: "2pts"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-002"
    description: "Two-stage normalization policy: Stage 1 allowlist (NFKC normalization, whitespace collapsing, quote-mark style) applied before diffing; Stage 2 treats any residual difference as material (flag/fail), never silently auto-corrects."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-001"]
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-003"
    description: "locator_only card handling: cards with extraction_status: locator_only emit a warn-level, distinguishable, non-blocking finding — not skip, not fail."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-001"]
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-004"
    description: "Fidelity fixtures (H3 — 5 scenarios): author superscript-corruption / NFKC-safe / curly-quote-safe / locator-only-warn / clean-pass fixtures and validate against the 7 verified bundles (0 false positives)."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-002", "P4-003"]
    estimated_effort: "1pt"
    priority: "high"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "SEAM-001"
    description: "rf verify gate-composition regression: with P2+P3+P4 all active simultaneously, run the full regression (7 verified bundles + P2/P4 red-team/corruption fixtures); assert no masking, no double-counting, all 7 bundles pass end-to-end. Mandatory seam task for the declared integration_owner; explicit prerequisite for the Wave-3 karen milestone."
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-003", "P4-004"]
    estimated_effort: "1pt"
    priority: "critical"
    assigned_model: "sonnet"
    model_effort: "extended"

parallelization:
  batch_1: ["P3-001", "P4-001"]
  batch_2: ["P3-002", "P4-002", "P4-003"]
  batch_3: ["P3-003", "P4-004"]
  batch_4: ["SEAM-001"]
  critical_path: ["P3-001", "P3-002", "P3-003", "SEAM-001"]
  estimated_total_time: "10pts"

blockers: []

success_criteria:
  - { id: "SC-1", description: "P3: threshold+clinical-eligible claims default to strict passage mode; 0 regressions on non-clinical warn-mode runs", status: "pending" }
  - { id: "SC-2", description: "P4: PMC superscript fixture detected; 0 false positives against the 7 verified bundles", status: "pending" }
  - { id: "SC-3", description: "SEAM-001: full rf verify regression proves all 3 gates (P2/P3/P4) compose without masking or double-counting", status: "pending" }
  - { id: "SC-4", description: "task-completion-validator pass for P3 and P4 individually, then one consolidated karen milestone for the cluster after SEAM-001 is green", status: "pending" }

files_modified: []

notes: "Wave 3 (P3 || P4, both depends_on: [P2]), then SEAM-001 after both land. integration_owner: python-backend-engineer (R-P3 — >=2 owner specialties + files_affected intersection on verification.py). ONE karen milestone runs after this cluster (SEAM-001 green) — overrides the decisions-block's per-phase exit-gate column which lists karen at P2 and P4 individually; do not add separate passes."
---

# rfup-external-routing - Phase 3-4: Exact-Passage Eligibility + Quote-Fidelity Gate Cluster (+ SEAM-001)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/rfup-external-routing/phase-3-4-progress.md -t P3-001 -s completed --started <ISO8601> --completed <ISO8601> --evidence "commit:<sha>"
```

---

## Objective

Add two new hard-gates to `rf verify` — an eligibility-driven auto-strict exact-passage default for threshold/clinical claims (P3), and a character-level quote-fidelity check against source corruption (P4) — then prove via SEAM-001 that both compose cleanly with the P2 schema gate without masking or double-counting findings.

---

## Implementation Notes

### Architectural Decisions

P3 and P4 touch disjoint functions within `verification.py` (P3 extends `exact_passage_present` at lines 712-753; P4 adds a wholly new check function in a new `quote_fidelity.py` module) — this is why they run in the same wave rather than being serialized. SEAM-001 exists specifically to prove that disjointness holds at runtime.

Eligibility trigger for P3 is `assertion_kind == threshold` AND an explicit clinical-sensitivity signal (pediatric_cds block present OR sensitivity tag) — NOT threshold alone (resolves PRD OQ-1). P4's fidelity policy is two-stage: normalization allowlist first, then any residual difference is material (resolves PRD OQ-3).

### Patterns and Best Practices

Full task detail, ACs (AC-P3-1 through AC-P3-7, AC-P4-1 through AC-P4-14, AC-SEAM-1 through AC-SEAM-4), and quality gates: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-3-4-clinical-gate-cluster.md`.

### Known Gotchas

- P3's eligibility signal defaults to non-eligible (fail-safe toward warn-only) when undeterminable — the opposite fail direction from P4, which fails toward visibility (warn) for undeterminable fidelity status. Do not conflate the two asymmetries.
- P4's `locator_only` handling is a warn, not a skip and not a fail — silently skipping would hide a coverage hole; failing would incorrectly hard-gate a retrieval-completeness gap this check wasn't designed to catch.
- SEAM-001 is a hard prerequisite for the Wave-3 `karen` milestone — do not proceed to that review until SEAM-001 is green.

### Development Setup

None beyond the existing `.venv`; run tests via `./.venv/bin/python -m pytest`.

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
