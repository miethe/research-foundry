---
doc_type: phase_plan
schema_version: 2
it_schema: 1
title: "Rights & Evidence-Item Entity Model — Phases 0-2 (Schema Substrate, Evidence Taxonomy, Mirror + Validator)"
status: draft
created: 2026-07-21
phase: "P0-P2"
phase_title: "Rights Substrate / Evidence Taxonomy / Rights Summary Mirror + Validator"
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
feature_slug: rights-entity-model
entry_criteria:
  - "PRD and decisions block approved (both exist and are read-only inputs to this phase file)"
exit_criteria:
  - "5 substrate schemas + rights_summary mirror + divergence validator all pass task-completion-validator review"
---

# Phases 0-2: Rights Substrate, Evidence Taxonomy, Rights Summary Mirror + Validator

[← Back to parent plan](../rights-entity-model-v1.md)

**Column conventions**: `Estimate` = story points (never Effort). `Model` = `sonnet` for every task in this plan (haiku hard-errors in this environment — always override). `Effort` = `extended` for algorithmic/correctness-critical tasks, `adaptive` otherwise, per Model column.

---

## Phase 0: Rights Substrate

**Duration**: ~8 pts
**Dependencies**: None (root of the critical path — gates every other phase)
**Assigned Subagent(s)**: data-layer-expert (primary), python-backend-engineer (secondary — Registry wiring)
**Risk note**: This phase owns 6 of the 10 §9 schema-conflict adjudications. Each row below names its owning adjudication ID(s) explicitly — do not re-litigate the resolutions (they are locked in the decisions block).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P0-1 | Port `rights_record.schema.yaml` | Port the v1.0 baseline into `schemas/rights_record.schema.yaml` (Draft 2020-12, strict family: `additionalProperties: false`, nullable via `type: [T, "null"]`, `schema_version` const). Apply §9.3 (`access.basis` + `unknown` member), §9.4 (unify `access.automated_retrieval_allowed`/`text_and_data_mining_allowed`/`model_training_allowed` + `contract.bulk_retrieval`/`model_training` into one `allowed\|allowed_with_conditions\|prohibited\|not_addressed\|unknown` enum), §9.5 (`record_scope: first_party` + `overall_status: OWNED` + conditionally-optional `source_id` when `record_scope==first_party`), §9.6a (`pattern: "^https?://"` replaces `format: uri` on `access.terms_url`/`copyright.license_url`), §9.6b (when `contract` is non-null, all 7 restriction sub-fields required, each accepting `unknown`; empty `{}` fails validation), §9.7 (canonical 6-member `review.review_status` enum, shared textually with `content_reuse_assessment.review.review_status` — P0-3), §9.8 (`component_decisions[].component_type` unified singular vocabulary + `abstract`/`supplementary_material` members). | Schema validates via `jsonschema.Draft202012Validator`; valid + invalid instance fixtures exist for each of the 7 adjudication rows above; §9.6b's empty-`contract`-object case has a dedicated invalid fixture (fail-open regression guard). | 2 | data-layer-expert | sonnet | extended | None |
| P0-2 | Port `rights_extension.schema.yaml` | Port as the fuller entity-level extension record. Explicit negative-space requirement (§9.1 boundary, set here even though §9.1's positive resolution lands in P1): this schema must NOT define `evidence_item_type`/`judgment_basis`/any taxonomy field — it is a rights container only. | Schema validates; a dedicated test asserts `rights_extension.schema.yaml`'s property set has zero overlap with the P1 `evidence_taxonomy` field names (guards against future drift re-coupling the two axes). | 1 | data-layer-expert | sonnet | extended | None |
| P0-3 | Port `content_reuse_assessment.schema.yaml` | Port with the unified `component_type` vocabulary (§9.2/§9.8 — same enum as P0-1's `component_decisions[].component_type`) and the shared `review_status`/`decision.status` enums (§9.7/§9.10 — `decision.status`/`decision.release_gate` enum values defined here match `rights_record.overall_status`'s value set; the *authorization enforcement* that no agent path can write a `CLEARED_*` value to this field is deferred to P5-2, not built here — this task only needs the enum values correct). | Schema validates; `component_type` enum is byte-identical (as a literal list, not by `$ref`) to P0-1's; `review_status` enum is byte-identical to P0-1's `review.review_status`; both identity checks have a dedicated unit test (this is the seed for P6-1's full consistency sweep). | 2 | data-layer-expert | sonnet | extended | None |
| P0-4 | Port `permission_record.schema.yaml` + `rights_failure.schema.yaml` | Port both as-is structurally — no §9 conflicts named against either in the handoff review. | Both schemas validate; each has ≥1 valid + ≥1 invalid instance fixture. | 1 | data-layer-expert | sonnet | adaptive | None |
| P0-5 | Registry wiring + test builders | Extend `SchemaRegistry`/`EXPECTED_SCHEMA_NAMES` in `src/research_foundry/schemas.py` and `tests/test_schema_validation.py` builders to cover all 5 new schemas (P0-1..P0-4). | All 5 schemas appear in `test_registry_lists_all_schemas`; each has a passing valid-instance test and a failing invalid-instance test in `test_schema_validation.py`. | 2 | python-backend-engineer | sonnet | extended | P0-1, P0-2, P0-3, P0-4 |

**Phase 0 Quality Gates:**
- [ ] All 5 schemas register in `SchemaRegistry` and pass `test_registry_lists_all_schemas`
- [ ] All 7 owned §9 adjudication rows (§9.2 is owned by P1, not here) have a passing fixture demonstrating the fix and a failing fixture demonstrating the pre-fix defect would be caught
- [ ] `./.venv/bin/python -m pytest tests/test_schema_validation.py` green
- [ ] **Reviewer gate**: `task-completion-validator`

---

## Phase 1: Evidence Taxonomy (C2)

**Duration**: ~6 pts
**Dependencies**: P0 complete (schema conventions established; no direct field dependency, but sequenced after P0 per decisions-block risk conservatism — shared evidence-entity file)
**Assigned Subagent(s)**: data-layer-expert (primary), python-backend-engineer (secondary — no-derivation guard)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P1-1 | Add `evidence_item_type` to `source_assertion.schema.yaml` | Add as a required enum (`observed_finding \| reference_interval_value \| equation_or_method \| guideline_recommendation \| instrument_or_questionnaire \| bibliographic_metadata \| derived_synthesis \| other`) inside a new `extensions.evidence_taxonomy` sibling block — never nested under `rights_extension` (§9.1 resolution). | Field lives at `extensions.evidence_taxonomy.evidence_item_type`; a dedicated test asserts it is NOT reachable via any `rights_extension`-rooted path (positive counterpart to P0-2's negative-space guard). **R-P2 implicit AC**: any consumer reading a pre-existing `source_assertion` instance authored before this phase must treat an absent `evidence_item_type` as `other`/unclassified, never crash or silently coerce to a specific member. | 2 | data-layer-expert | sonnet | adaptive | P0-5 |
| P1-2 | Add `judgment_basis` to the same block | Add as a required enum (`measured \| derived_from_measured \| expert_judgment \| mixed \| unassessed`), independent axis, default `unassessed`. Enum naming is domain-general per OQ-RF-2's base-axis resolution (not clinical-only terms). | Field lives alongside `evidence_item_type` in `extensions.evidence_taxonomy`; default value is `unassessed`. **R-P2 implicit AC**: absence on a pre-existing instance is treated as `unassessed` (fail-closed — blocks commercial release per P5-3, never silently treated as `measured`). | 1.5 | data-layer-expert | sonnet | adaptive | P1-1 |
| P1-3 | No-derivation static guard | Add a code-review checklist item plus an automated static test asserting no function in `src/research_foundry/` computes `evidence_item_type` from `judgment_basis` (or vice versa), and neither is computed from any existing `component_type`-shaped field. Three-axes invariant (FR-8). | Static test scans the codebase (AST or grep-based) for any function whose signature/body derives one field from another named field; test fails if such a derivation is found; passes on current (derivation-free) codebase. | 1.5 | python-backend-engineer | sonnet | adaptive | P1-1, P1-2 |
| P1-4 | `other`-extensibility test (OQ-RF-2) | Add a test proving `evidence_item_type: other` validates and that the enum is documented as domain-extensible (not a closed clinical list) — the base axis a future domain (e.g., Evidence-Foundry) specializes rather than replaces. | Test constructs a valid `source_assertion` instance with `evidence_item_type: other`; schema doc-comment states the extensibility contract. | 1 | data-layer-expert | sonnet | adaptive | P1-1 |

**Phase 1 Quality Gates:**
- [ ] `evidence_item_type` and `judgment_basis` are independent, required fields with correct defaults
- [ ] No-derivation static test passes
- [ ] `other`-extensibility test passes
- [ ] **Reviewer gate**: `task-completion-validator`

---

## Phase 2: Rights Summary Mirror + Validator (C1)

**Duration**: ~9 pts
**Dependencies**: P1 complete
**Assigned Subagent(s)**: data-layer-expert (schema tasks), python-backend-engineer (validator + CLI)
**H3 flag**: P2-3 is the algorithmic core of this phase — a time-parameterized, never-wall-clock divergence validator. Enumerated test scenarios below satisfy the ≥5-scenario H3 requirement.

#### AC P2-A: rights_summary mirror attaches to BOTH `source_card` AND `source_assertion` (multi-surface propagation)

- **target_surfaces**:
  - `schemas/source_card.schema.yaml`
  - `schemas/source_assertion.schema.yaml`
- **propagation_contract**: The `rights_summary` object (identical shape at both attach points: `mirror_of_record_id`, `mirror_derived_at`, `mirror_is_authoritative: const false`, `rights_record_ids[]`, `reuse_assessment_ids[]`/`permission_record_ids[]`, `copyright_status`, `access_basis`, `restrictions{}` ≤6 sub-fields, `clearance_status`, `review_status`) is defined once as the same field shape and applied independently to both schemas — there is no cross-schema `$ref` (RF's `SchemaRegistry` has no resolver support; each schema carries its own literal copy, consistency enforced by P6-1's byte-identical-list test).
- **resilience**: A `source_card` or `source_assertion` instance authored before this phase (missing `rights_summary` entirely) is not a validation failure at read time — the P2-5 backfill migration is the mechanism that brings existing instances into compliance; the validator (P2-3) treats a genuinely absent `rights_summary` on an unmigrated legacy instance as a distinct, non-fatal "needs backfill" state, not a divergence failure.
- **visual_evidence_required**: false (no UI surface in this feature)
- **verified_by**: [P2-1, P2-2, P2-5, P6-1]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P2-1 | Add `rights_summary` to `source_card.schema.yaml` | Attach point 1 of AC P2-A. All fields default `unknown`/`null`; `mirror_is_authoritative` schema-pinned `const: false`; `rights_record_ids[]` required non-empty whenever any restriction/status field below is non-`unknown`. | Schema validates; a fixture with a non-`unknown` `access_basis` and empty `rights_record_ids` fails validation (link-before-assert invariant); `mirror_is_authoritative` cannot be set to `true` by any fixture. | 2 | data-layer-expert | sonnet | extended | P1-4 |
| P2-2 | Add `rights_summary` to `source_assertion.schema.yaml` | Attach point 2 of AC P2-A — identical field shape to P2-1, applied to the evidence-item-level entity. | Same acceptance bar as P2-1, on `source_assertion`; a test confirms the two schemas' `rights_summary` field lists are identical (feeds P6-1). | 2 | data-layer-expert | sonnet | extended | P2-1 |
| P2-3 | `check_rights_divergence` validator | Build `src/research_foundry/services/rights_validation.py::check_rights_divergence(paths, *, as_of, ...)`. **Must accept `--as-of` as a required, explicit parameter and must NEVER call `datetime.now()`/`time.time()`/`date.today()` internally.** Enumerated test scenarios (H3, ≥5 required): (1) non-`unknown` mirror value with no linked `rights_record_id` → fail; (2) mirror value diverges from its linked `rights_record`'s actual value → fail; (3) mirror absent entirely on a legacy (pre-backfill) instance → distinct non-fatal "needs backfill" result, not a divergence failure; (4) `rights_record.next_review_at` before `--as-of` → flagged as stale (record-the-debt surface for OQ-RF-5, not blocking); (5) two invocations with identical `--as-of` and unchanged inputs → byte-identical output (reproducibility). | All 5 scenarios have a passing test; a dedicated test monkeypatches `datetime.now`/`time.time`/`date.today` to raise and asserts `check_rights_divergence` never triggers them; reproducibility test runs the function twice and diffs output byte-for-byte. | 3 | python-backend-engineer | sonnet | extended | P2-1, P2-2 |
| P2-4 | `rf rights validate --as-of` CLI + `rights_app` skeleton | Wire the validator as `rf rights validate --as-of YYYY-MM-DD` (required flag, no implicit wall-clock default — the CLI itself must reject invocation without `--as-of`). Scaffold the `rights_app` Typer sub-app (modeled on the existing `assertion_app` pattern) with `inspect`/`list`/`validate` subcommands; `inspect`/`list` are completed in P4-5, `validate` is completed here. **H7 flag**: `cli_commands.py` is 2,755 lines — use `grep -n "assertion_app"` to locate the insertion pattern; do not read the whole file; budget ≤40 tool uses; STOP-and-report-partial if exhausted. | `rf rights validate` without `--as-of` exits non-zero with a clear error (no default date is ever computed); `rf rights validate --as-of <date>` runs `check_rights_divergence` and reports pass/fail. | 1 | python-backend-engineer | sonnet | extended | P2-3 |
| P2-5 | Backfill migration | Existing `source_card`/`source_assertion` instances without `rights_summary` get an all-`unknown` fail-closed summary (valid by construction — never a silent skip). Run the existing corpus through P2-3's validator as the phase exit gate. | Backfill script (or `rf rights` subcommand — implementer's choice per decisions-block OQ-5) produces all-`unknown` summaries for every pre-existing instance; post-backfill, `rf rights validate --as-of <today>` reports 0 divergences on the existing corpus. | 1 | python-backend-engineer | sonnet | extended | P2-3, P2-4 |

**Phase 2 Quality Gates:**
- [ ] `rights_summary` attaches identically to both `source_card` and `source_assertion` (AC P2-A satisfied)
- [ ] `check_rights_divergence` is time-parameterized and never reads wall-clock time (reproducibility test passes)
- [ ] Backfill migration brings the existing corpus to 0 divergences
- [ ] `rf rights validate --as-of` rejects invocation without the flag
- [ ] **Reviewer gate**: `task-completion-validator`

---

[← Back to parent plan](../rights-entity-model-v1.md) | [Next: Phases 3-4 →](./phase-3-4-capture.md)
