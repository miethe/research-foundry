---
doc_type: phase_plan
schema_version: 2
it_schema: 1
title: "Rights & Evidence-Item Entity Model — Phases 5-6 (Governance Gate + Canonical ADR, Testing/Docs/Finalization)"
status: draft
created: 2026-07-21
phase: "P5-P6"
phase_title: "Governance Gate + Canonical ADR / Testing / Docs / Fixtures / Finalization"
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
feature_slug: rights-entity-model
entry_criteria:
  - "Phase 3 (derived synthesis, karen milestone) exit gate passed — P5 depends on P3, not P4, per the parallel-slice note below"
exit_criteria:
  - "karen end-of-feature sign-off; full test suite green; ADR published; deferred_items_spec_refs populated"
---

# Phases 5-6: Governance Gate + Canonical ADR, Testing / Docs / Fixtures / Finalization

[← Phases 3-4](./phase-3-4-capture.md) | [Back to parent plan](../rights-entity-model-v1.md)

**Column conventions**: `Estimate` = story points. `Model` = `sonnet` for every task (haiku hard-errors here — always override, including for `changelog-generator` and `documentation-writer` which default haiku). `Effort` = `adaptive` for both phases (P5-2's negative test is the one exception — `extended`, per the correctness-critical binding constraint on this task specifically).

**Parallel-slice note**: P5 depends on **P3**, not P4 (both P4 and P5 depend on P3 independently) — P5's governance-wiring and ADR-authoring tasks need the full §9 adjudication set and the P3 attestation-boundary decision, not P4's capture-emission implementation. This is the plan's one deliberate parallel slice: P5 (owner: `python-backend-engineer` + `documentation-writer`) may run alongside P4 (owner: `python-backend-engineer`, same specialty but no file overlap — `governance.py`/`verification.py`/the ADR vs. `source_cards.py`/`capture.py`/`cli_commands.py`).

---

## Phase 5: Governance Gate + Canonical ADR

**Duration**: ~7 pts
**Dependencies**: P3 complete (see parallel-slice note above)
**Assigned Subagent(s)**: python-backend-engineer (governance wiring + negative test), documentation-writer (ADR — legal-reasoning prose warrants sonnet, not haiku)
**§9.10 note**: This phase closes the **other** half of the two-write-path authorization gap the handoff's §9.10 finding flagged (P3-4 closed the `synthesis.attestation.status` path in the previous phase file). **The boundary is only fully proven once both P3-4 and P5-2 pass — neither phase's negative test alone is sufficient, and this is by design (independent verification of both paths, not one test covering both).**

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P5-1 | `governance.py` guard rule: agent-write ban | New guard rule in `services/governance.py` (following the existing `work_writeback_requires_review`/`intenttree_writeback_requires_review` pattern) blocking any agent-writable code path from producing `CLEARED_*`, `counsel_approved`, or `attestation.status=attested` on: `rights_record.overall_status`, `content_reuse_assessment.decision.status`, `rights_extension.clearance_status`, `synthesis.attestation.status` (the last one is already guarded by P3-3/P3-4 at the service layer — this rule is the governance-layer backstop covering all 4 fields uniformly, including the 3 not yet guarded). | `guard_check` returns `block` for any simulated agent-authored write attempting to set one of the 4 named fields to a `CLEARED_*`/`counsel_approved`/`attested` value; the rule enumerates all 4 fields by name (matching FR-23) so future fields must be added explicitly, not inferred. | 2 | python-backend-engineer | sonnet | adaptive | P3-4 |
| P5-2 | **Negative test: agent path → `rights_record.overall_status`/`content_reuse_assessment.decision.status` cleared value is unreachable** | **Mandatory per this feature's binding authorization-boundary requirement — the P5 counterpart to P3-4.** Enumerate every code path that can write `rights_record.overall_status`, `content_reuse_assessment.decision.status`, `content_reuse_assessment.decision.release_gate`, and `rights_extension.clearance_status`, and assert that none of them — under any input — can produce a `CLEARED_*`/`counsel_approved`/`OWNED`-without-first-party-basis value from an agent identity. This is an **independent** test suite from P3-4 (different fields, different write paths); it must not be collapsed into P3-4 or treated as redundant with it. | Test suite exhausts every agent-reachable write path to the 4 fields named in P5-1 (enumerate function names in the test docstring, allow-list style, same discipline as P3-4) and asserts each is fail-closed; combined with P3-4, this closes the `§9.10` gap over **both** write paths named in the handoff review. | 2 | python-backend-engineer | sonnet | extended | P5-1 |
| P5-3 | Release-gate rule: `judgment_basis: unassessed` | Add the bidirectional release-gate predicate. **Resolves decisions-block OQ-6**: the predicate itself lives in `governance.py` (policy ownership); `verification.py::verify_report` calls it as a new named check in its existing check sequence at verify-time (this is *not* a duplicate implementation — `governance.py` owns the boolean logic, `verification.py` is a caller). Blocks commercial-release disposition evaluation when `judgment_basis: unassessed`; is non-blocking for internal-capture writes. | Bidirectional test: a commercial-release verification run with an `unassessed` evidence item fails; an internal-capture write with the same `unassessed` item succeeds; both directions tested explicitly (never assumed from the other, per NFR "Release-gate asymmetry"). | 1 | python-backend-engineer | sonnet | adaptive | P1-4, P5-1 |
| P5-4 | Author canonical rights ADR | Author `docs/dev/architecture/adr-rights-entity-model.md`, following `adr-runs-read-path.md`'s frontmatter/section pattern. Must record: all 10 §9 adjudications (table, with RF's resolution for each — reuse the decisions-block's adjudication table as the base content, do not re-derive), `resolves: [OQ-RF-1, OQ-RF-2, OQ-RF-3, OQ-RF-4]`, and an explicit **"Known Gaps"** section naming OQ-RF-5 (surveillance execution) and OQ-RF-6 (counsel/rights-owner role) as named debt, cross-referencing the P6-8 DOC-006 design specs for each. May start once P3 lands (parallel to P4 — see phase-note above); does not require P4 or P5-1/P5-2/P5-3 to be complete, only the full §9/OQ resolution set which exists after P3. | ADR file exists with all 10 §9 rows, OQ-RF-1..4 marked resolved with rationale, OQ-RF-5/6 marked as named gaps with links to their P6-8 design specs; frontmatter `resolves` list populated. | 2 | documentation-writer | sonnet | adaptive | P3-4 |

**Phase 5 Quality Gates:**
- [ ] `governance.py` guard rule enumerates all 4 named fields explicitly
- [ ] P5-2's negative test is independent of P3-4 (different fields/paths) and passes — combined, the §9.10 gap is closed over both write paths
- [ ] Release-gate bidirectional test passes in both directions
- [ ] ADR published with all 10 §9 rows + OQ-RF-1..4 resolved + OQ-RF-5/6 named as gaps
- [ ] **Reviewer gate**: `task-completion-validator`

---

## Phase 6: Testing / Docs / Fixtures / Finalization

**Duration**: ~7 pts
**Dependencies**: P4 AND P5 both complete
**Assigned Subagent(s)**: python-backend-engineer (tests, fixture regen), documentation-writer (docs, DOC-006 specs), changelog-generator (CHANGELOG)
**§9.9 note**: This phase owns the one remaining unassigned §9 adjudication row — §9.9 (P6-5 below).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P6-1 | Enum-consistency test sweep | Formalize the byte-identical-list assertions seeded in P0-3/P2-2 into a dedicated consistency test module: `overall_status` == `decision.status`+`clearance_status` (value-set level); `review_status` byte-identical across `rights_record.review` and `content_reuse_assessment.review`; `component_type` byte-identical across `rights_record.component_decisions[]` and `content_reuse_assessment.component` (FR-26). | Dedicated test module asserts byte-identical enum lists for all 3 pairs named above; test fails loudly (not silently) if either schema file is edited without the other. | 1 | python-backend-engineer | sonnet | adaptive | P5-3 |
| P6-2 | Negative-write-path integration sweep | Consolidate P3-4 + P5-2 into one CI-run cross-check confirming both halves of the §9.10 boundary are covered end-to-end in a single suite run (regression guard against either negative test being accidentally skipped/marked `xfail` in isolation). | Combined suite run reports both P3-4's and P5-2's assertions passing in the same CI invocation; a deliberately-reintroduced write path (test-only) is caught by at least one of the two suites. | 0.5 | python-backend-engineer | sonnet | adaptive | P6-1 |
| P6-3 | Release-gate bidirectional integration test | Cross-phase integration test tying P1's taxonomy (`judgment_basis`) to P5-3's gate — exercises the full pipeline (capture → taxonomy assignment → release-gate evaluation) rather than P5-3's unit-level bidirectional test. | End-to-end test: a captured item with `judgment_basis: unassessed` blocks a simulated commercial-release check and passes a simulated internal-capture check, through the actual capture→verify pipeline (not mocked at the governance boundary). | 0.5 | python-backend-engineer | sonnet | adaptive | P6-1 |
| P6-4 | Divergence-validator determinism integration test | Finalize P2-3's unit-level reproducibility test at the integration level: two full `rf rights validate --as-of <date>` CLI invocations against the same corpus produce byte-identical stdout; monkeypatch wall-clock calls to raise, run through the CLI (not just the service function directly). | Two CLI invocations diff byte-identical; CLI-level monkeypatch test confirms no wall-clock call fires anywhere in the `rf rights validate` code path (service + CLI layer). | 0.5 | python-backend-engineer | sonnet | adaptive | P6-1 |
| P6-5 | Fixture regeneration + §9.9 note | Regenerate RF's example `source_card`/`source_assertion` fixtures (inline-dict test fixtures — RF has no checksum files, unlike the pediatric-repo's vendored JSON examples) to include `rights_summary`/taxonomy/`synthesis` fields where applicable. Document explicitly that §9.9's role-string-in-reviewer-field defect is **moot for RF** — RF ports schema structure only, never the pediatric-repo's vendored JSON example files, so there is no RF-side instance of that defect to correct. | All RF example fixtures touching `source_card`/`source_assertion` include the new fields where the entity's semantics warrant it; a one-line note in `tests/test_schema_validation.py` (or this phase's completion note) records the §9.9 moot determination for auditability. | 1.5 | python-backend-engineer | sonnet | adaptive | P6-1 |
| P6-6 | CHANGELOG `[Unreleased]` entry | Add entry under `[Unreleased]` per `.claude/specs/changelog-spec.md` categorization rules. `changelog_required: true` in this plan's frontmatter — this task is mandatory, not skippable. | Entry exists under `[Unreleased]` with correct categorization; plan frontmatter `changelog_ref` set to `CHANGELOG.md`. | 0.5 | changelog-generator | sonnet | adaptive | All P0-P5 phases |
| P6-7 | README / user-dev docs / context files | Update: `README.md` if the `rf rights` CLI group changed the documented command surface; user/dev docs under `docs/` for the new rights/taxonomy behavior; `docs/dev/architecture/artifact-type-reference.md` with an entry for the new rights entity types (`rights_record`, `rights_extension`, `content_reuse_assessment`, `permission_record`, `rights_failure`); `CLAUDE.md` pointer-only addition (≤3 lines) if agent-relevant behavior changed. | README/docs reflect the new CLI surface and entity types; `artifact-type-reference.md` has a new entry per the doc-policy convention; CLAUDE.md addition (if any) is a pointer, not a restatement. | 1 | documentation-writer | sonnet | adaptive | All P0-P5 phases |
| P6-8a | DOC-006: runtime resolution API design spec | Author `docs/project_plans/design-specs/rights-runtime-resolution-api.md` (`maturity: idea`, `prd_ref` set to this feature's PRD) capturing the OQ-3/DI-RIGHTS-1 alternative (a fast runtime resolution API vs. the mirror this plan ships) and when it would be worth building. Append path to this plan's `deferred_items_spec_refs`. | Design spec exists with `maturity: idea`, `prd_ref` set, and states the concrete trigger condition (a consumer needing sub-request-latency resolution at scale) named in the parent plan's Deferred Items table. | 0.5 | documentation-writer | sonnet | adaptive | P5-4 |
| P6-8b | DOC-006: surveillance loop design spec | Author `docs/project_plans/design-specs/rights-surveillance-loop.md` capturing OQ-RF-5/DI-RIGHTS-3 (a scheduled re-check loop against `next_review_at`). Append path to `deferred_items_spec_refs`. | Design spec exists, `prd_ref` set, names the trigger condition from the Deferred Items table. | 0.5 | documentation-writer | sonnet | adaptive | P5-4 |
| P6-8c | DOC-006: counsel/rights-owner workflow design spec | Author `docs/project_plans/design-specs/rights-counsel-workflow.md` capturing OQ-RF-6/DI-RIGHTS-4 (a formal rights-owner/counsel role + attestation workflow — currently no such role exists upstream; shipped as human-only-by-exclusion). Append path to `deferred_items_spec_refs`. | Design spec exists, `prd_ref` set, names the trigger condition from the Deferred Items table. | 0.5 | documentation-writer | sonnet | adaptive | P5-4 |
| P6-9 | Update plan frontmatter + progress tracking | Set `status: completed`, populate `commit_refs`/`files_affected`/`updated`, confirm `deferred_items_spec_refs` has all 3 P6-8 paths, confirm `adr_refs` includes P5-4's ADR path. | Frontmatter complete per the lifecycle spec; `deferred_items_spec_refs` has exactly 3 entries; `adr_refs` has 1 entry. | 0.5 | documentation-writer | sonnet | adaptive | P6-6, P6-7, P6-8a, P6-8b, P6-8c |

**Phase 6 Quality Gates:**
- [ ] Enum-consistency, negative-write-path, release-gate, and determinism test sweeps all green
- [ ] Fixture regeneration complete; §9.9 moot-determination documented
- [ ] CHANGELOG `[Unreleased]` entry present
- [ ] README/docs/context files/artifact-type-reference updated
- [ ] All 3 DOC-006 design specs authored and appended to `deferred_items_spec_refs`
- [ ] Plan frontmatter finalized
- [ ] **Reviewer gate**: **karen** end-of-feature (final sign-off across all 7 phases — explicit verdict required, silence is never a pass)

---

[← Phases 3-4](./phase-3-4-capture.md) | [Back to parent plan](../rights-entity-model-v1.md)
