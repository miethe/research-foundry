---
doc_type: phase_plan
schema_version: 2
it_schema: 1
title: "Rights & Evidence-Item Entity Model — Phases 3-4 (Derived Synthesis, Capture Emission + Substitutability)"
status: draft
created: 2026-07-21
phase: "P3-P4"
phase_title: "Derived Synthesis / Capture Emission + Substitutability"
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
feature_slug: rights-entity-model
entry_criteria:
  - "Phase 2 (rights_summary mirror + validator) exit gate passed"
exit_criteria:
  - "Both karen milestones (P3, P4) pass"
---

# Phases 3-4: Derived Synthesis, Capture Emission + Substitutability

[← Phases 0-2](./phase-0-2-schema.md) | [Back to parent plan](../rights-entity-model-v1.md) | [Next: Phases 5-6 →](./phase-5-6-governance-finalize.md)

**Column conventions**: `Estimate` = story points. `Model` = `sonnet` for every task (haiku hard-errors here — always override). `Effort` = `extended` for algorithmic/correctness-critical tasks (all tasks in this file are `extended` — both phases are Mode-D-adjacent or H3-flagged).

**Mode-D-adjacency note**: P3-4 and P4's capture emission touch the authorization boundary this entire feature exists to protect. Both phases end with a **karen** milestone, not just `task-completion-validator` — silence from karen is never a pass (per the project's silent-reviewer rule); the phase owner must receive an explicit verdict.

---

## Phase 3: Derived Synthesis (C3)

**Duration**: ~7 pts
**Dependencies**: P2 complete. Also depends on P0-1's §9.5 fix (`record_scope: first_party` + `overall_status: OWNED` + conditional `source_id`) — already shipped in Phase 0; this phase consumes it, does not re-implement it.
**Assigned Subagent(s)**: python-backend-engineer (primary), data-layer-expert (secondary — conditional schema authoring)
**§9.10 note**: This phase owns **one of the two** enum write paths named in the handoff's §9.10 finding (the baseline guarded only one of two paths). P3-4 below closes the `synthesis.attestation.status` path. The *other* path (`rights_record.overall_status` / `content_reuse_assessment.decision.status` / `decision.release_gate`) is closed independently in P5-2 — **do not treat P3-4 as sufficient on its own; the boundary is only proven once both P3-4 and P5-2 pass.**

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P3-1 | Add conditional `synthesis` object | Add to `schemas/source_assertion.schema.yaml` via JSON Schema `if/then`, required iff `evidence_item_type == derived_synthesis`: `input_refs[]` (`minItems: 2`, each `{source_assertion_id, rights_record_id: [string,"null"], contribution: enum[anchor,corroborating,contradicting,scope_limiting]}`), `method` (required string), `divergence_notes[]`, `reproduces_source_arrangement` (required bool), `first_party_rights_holder` (`[string,"null"]`). | A valid `derived_synthesis` instance with 2 `input_refs` validates; an instance with only 1 `input_ref` fails (`minItems: 2` enforced); an instance with `evidence_item_type != derived_synthesis` and no `synthesis` object validates (conditional does not misfire on non-synthesis assertions — this is the PRD's Risk 3, "under-tested conditional silently permits malformed record": test both the positive and negative branch explicitly). | 2 | data-layer-expert | sonnet | extended | P2-5 |
| P3-2 | Nullable `source_edition_id`/`passage_id` conditional | Make `source_edition_id`/`passage_id` `[string, "null"]` (nullable) **only** when `evidence_item_type == derived_synthesis` — a `derived_synthesis` assertion may exist without a third-party source locator; every other `evidence_item_type` still requires them non-null. | A `derived_synthesis` instance with both fields `null` validates; a non-synthesis instance with either field `null` fails (regression guard against accidentally loosening the constraint for all evidence types). | 1 | data-layer-expert | sonnet | extended | P3-1 |
| P3-3 | `synthesis.attestation` object + schema-level write ceiling | Add `attestation{attested_by: [string,"null"], attested_at: [string,"null"], attestation_ref: [string,"null"], status: enum[candidate, attested]}` to the `synthesis` object. Schema alone cannot enforce *who* writes — pair the schema enum with a service-layer check in every code path that constructs a `source_assertion` with a `synthesis` block (`services/source_cards.py`), asserting the constructed value's `attestation.status` is always `candidate` when the caller is an agent identity. | Schema validates; a unit test constructs a `source_assertion` via every agent-invoked service function that can produce a `synthesis` block and asserts the resulting `attestation.status` is `candidate` in 100% of cases — no function signature accepts an `attestation.status` override. | 2 | python-backend-engineer | sonnet | extended | P3-1, P3-2 |
| P3-4 | **Negative test: agent path → `attestation.status=attested` is unreachable** | **Mandatory per this feature's binding authorization-boundary requirement.** Enumerate every code path in `services/source_cards.py` and `services/capture.py` that can write a `source_assertion` with a `synthesis` block, and assert that none of them — under any input, including adversarial/malformed input — can produce `attestation.status: attested`. This test closes the `synthesis.attestation.status` half of the §9.10 write-path gap (P5-2 closes the other half independently). | Test suite exhausts every agent-reachable write path to `synthesis.attestation.status` (enumerate function names in the test docstring/comment for auditability) and asserts each is fail-closed to `candidate`; test fails loudly (not silently skips) if a new write path is added without updating the enumeration — i.e., the test itself must be an allow-list, not a best-effort scan. | 2 | python-backend-engineer | sonnet | extended | P3-3 |

**Phase 3 Quality Gates:**
- [ ] `synthesis` object's conditional (`if/then`) validates both the positive (`derived_synthesis`) and negative (non-synthesis) branch correctly
- [ ] `derived_synthesis` assertions can exist without a third-party `source_id`/`source_edition_id`/`passage_id`
- [ ] P3-4's negative test passes and is written as an allow-list (fails loudly on new unenumerated write paths)
- [ ] **Reviewer gate**: **karen** milestone (Mode-D-adjacent — explicit verdict required, silence is never a pass)

---

## Phase 4: Capture Emission + Substitutability (C4)

**Duration**: ~9 pts
**Dependencies**: P3 complete
**Assigned Subagent(s)**: python-backend-engineer
**H3 flags**: P4-2 (content-addressing + re-snapshot diff) and P4-4 (substitute discovery/ranking) are both algorithmic-service flags carrying enumerated test-scenario lists below.

#### AC P4-A: capture-time `rights_summary` emission propagates to BOTH `source_card` AND `source_assertion` (multi-surface propagation, capture-time counterpart to AC P2-A)

- **target_surfaces**:
  - `src/research_foundry/services/source_cards.py` (`ingest_source`)
  - `src/research_foundry/services/capture.py` (`capture_idea`/`triage_idea`)
- **propagation_contract**: The same capture pass that creates a `source_card` and its associated `source_assertion`(s) emits a `rights_summary` on both, at `review_status: agent_triage_only`, using the schema shape defined in P2-1/P2-2 — this task wires the *emission*, the schema shape is not redefined here.
- **resilience**: If rights-triage logic itself fails (e.g., an internal exception during classification), the capture pass still completes and the source/evidence item is still ingested — the `rights_summary` degrades to an explicit all-`unknown` fail-closed value plus a structural failure record (P4-3), never a silent absence and never a blocked ingest (NFR: "Reliability — capture-time rights emission failures degrade to a structurally-recorded failure, never a silent absence").
- **visual_evidence_required**: false
- **verified_by**: [P4-1, P4-3, P6-2]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P4-1 | Capture-time `rights_summary` emission | Extend `ingest_source` (`source_cards.py`) and `capture_idea`/`triage_idea` (`capture.py`) to emit `rights_summary` at `review_status: agent_triage_only` in the same call that creates the source card/evidence item — no separate backfill sweep for newly-ingested entities. Satisfies AC P4-A. | 100% of newly ingested sources/evidence items carry a non-null `rights_summary` at `agent_triage_only` immediately after the capture call returns, in a post-condition test on `ingest_source`; no code path exists where a new ingest completes without the field populated. | 2 | python-backend-engineer | sonnet | extended | P3-4 |
| P4-2 | Terms snapshotting: content-addressed artifact | Content-addressed artifact (`terms_snapshot_sha256`) + `terms_verified_at`, stored under `runs/<run_id>/rights/terms_snapshots/`, excluded from exported/shipped bundles. Enumerated test scenarios (H3, ≥5): (1) first snapshot of a new terms URL → hash computed and stored; (2) re-snapshot with unchanged content → same hash, `terms_verified_at` updated; (3) re-snapshot with changed content → new hash + a diff record; (4) snapshot excluded from `rf run export` bundle (verify the export path skips `rights/terms_snapshots/`); (5) fetch failure during snapshot → handled by P4-3, not this task. | All 5 scenarios (except #5, owned by P4-3) have a passing test; export-exclusion test confirms `terms_snapshots/` is absent from an exported bundle's file listing. | 3 | python-backend-engineer | sonnet | extended | P4-1 |
| P4-3 | Structural snapshot-failure recording | Snapshot failure (fetch timeout, 4xx/5xx, malformed content) is recorded as a typed failure record (mirroring the existing `_IO_ERROR_SENTINEL_PREFIX` pattern in `verification.py`), never as an absent/null field. **R-P2 implicit AC**: any consumer reading `terms_snapshot_ref` must check for the presence of a `terms_snapshot_failure` object before assuming a successful snapshot exists — absence of `terms_snapshot_ref` alone is ambiguous (could mean "not yet attempted" or "attempted and failed") and every consumer path must resolve that ambiguity by checking the failure record, never by treating null as success. | A snapshot-fetch-failure test asserts `terms_snapshot_failure` is populated (never null) when the fetch fails, and `terms_snapshot_ref`/`terms_snapshot_sha256` remain `null`; a consumer-side test asserts code reading these fields checks `terms_snapshot_failure` before treating `terms_snapshot_ref: null` as "not applicable." | 1 | python-backend-engineer | sonnet | extended | P4-2 |
| P4-4 | Substitutability search trigger | A blocking triage status (`CONTRACT_RESTRICTED`, `PERMISSION_REQUIRED`, `PROHIBITED`, or use-blocking `UNKNOWN`) triggers a `substitutability` assessment: `searched_at`, `status: substitute_found \| no_substitute_found \| not_searched`, `candidate_source_ids[]`, `coverage_notes`. Enumerated test scenarios (H3, ≥5): (1) non-blocking triage status → `not_searched`, no search performed; (2) blocking status + a substitute exists in the existing corpus → `substitute_found` with `candidate_source_ids` populated; (3) blocking status + no substitute → `no_substitute_found` recorded as a **positive structured result**, not an absent field; (4) search itself errors → degrades to `not_searched` + a structural note, not a silent skip; (5) multiple candidate substitutes → all ranked and listed, not just the top one. | All 5 scenarios pass; the `no_substitute_found` case has a dedicated test asserting the field is present and non-null (guards against the "absence implies not searched" ambiguity). | 2 | python-backend-engineer | sonnet | extended | P4-1 |
| P4-5 | Complete `rf rights` CLI group (`inspect`, `list`) | Finish the `rights_app` skeleton from P2-4 with `inspect` (show a single entity's `rights_summary`/`substitutability`/`synthesis` state) and `list` (enumerate entities by triage/clearance status). **H7 flag**: `cli_commands.py` is 2,755 lines — reuse P2-4's insertion point; grep-only navigation, ≤40 tool uses, STOP-and-report-partial if exhausted. | `rf rights inspect <id>` prints the full rights posture for a given source/evidence item; `rf rights list --status agent_triage_only` filters correctly. | 1 | python-backend-engineer | sonnet | extended | P4-1, P4-4 |

**Phase 4 Quality Gates:**
- [ ] AC P4-A satisfied: capture-time emission reaches both `source_card` and `source_assertion` in the same pass
- [ ] Snapshot failure is always a structural record, never a bare absence
- [ ] `no_substitute_found` is a positive structured result in the substitutability object
- [ ] `rf rights` CLI group complete (`inspect`, `list`, `validate`)
- [ ] **Reviewer gate**: **karen** milestone (Mode-D-adjacent capture writeback — explicit verdict required)

---

[← Phases 0-2](./phase-0-2-schema.md) | [Back to parent plan](../rights-entity-model-v1.md) | [Next: Phases 5-6 →](./phase-5-6-governance-finalize.md)
