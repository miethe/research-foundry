## Phase 6 Completion Note — Testing / Docs / Fixtures / Finalization

### Summary

Phase 6 closes out the rights & evidence-item entity model feature (P0–P6). It formalized four
test sweeps that finalize invariants seeded earlier in the plan (enum consistency, the §9.10
negative-write-path boundary, the release-gate predicate, and divergence-validator determinism),
regenerated example fixtures with the new rights fields plus the §9.9 moot-determination note,
landed the mandatory CHANGELOG entry and doc updates, authored all 3 DOC-006 deferred-item design
specs, and finalized the parent plan's frontmatter. A karen end-of-feature review surfaced two real
regressions from earlier phases (a wall-clock leak and a CLI contract-drift gap) plus a metadata gap
(`verified_by`) and a stale ADR phrase; all four were fixed and re-verified before final APPROVED
sign-off.

### Tasks

- [x] P6-1 → python-backend-engineer — new `tests/test_rights_enum_consistency.py`; 3 byte-identical
      enum assertions read live schema via `SchemaRegistry`, no hardcoded duplicate lists.
- [x] P6-2 → python-backend-engineer — new `tests/unit/test_negative_write_path_consolidated.py`
      consolidates P3-4 + P5-2 in one CI-run invocation with a genuine monkeypatched-regression guard.
- [x] P6-3 → python-backend-engineer — new `tests/test_release_gate_integration.py`, full
      capture→taxonomy→synthesis→verify pipeline, both directions tested explicitly.
- [x] P6-4 → python-backend-engineer — new `tests/test_rights_validate_determinism_integration.py`,
      CLI-level byte-identical + wall-clock-raise coverage for `rf rights validate --as-of`.
- [x] P6-5 → python-backend-engineer — regenerated fixtures in
      `tests/integration/test_assertion_reuse.py` and `tests/test_reusable_assertion_ledger_phase1.py`;
      §9.9 moot-determination note in `tests/test_schema_validation.py`.
- [x] P6-6 → changelog-generator — `[Unreleased]` entry in `CHANGELOG.md`; `changelog_ref` set.
- [x] P6-7 → documentation-writer — `README.md`, `docs/projects/research-foundry/SERVICE_CONTRACT.md`,
      `docs/dev/architecture/artifact-type-reference.md`, `CLAUDE.md` pointer (3 lines).
- [x] P6-8a → documentation-writer — `docs/project_plans/design-specs/rights-runtime-resolution-api.md`
      (DI-RIGHTS-1/OQ-3).
- [x] P6-8b → documentation-writer — `docs/project_plans/design-specs/rights-surveillance-loop.md`
      (DI-RIGHTS-3/OQ-RF-5).
- [x] P6-8c → documentation-writer — `docs/project_plans/design-specs/rights-counsel-workflow.md`
      (DI-RIGHTS-4/OQ-RF-6).
- [x] P6-9 → documentation-writer — parent plan frontmatter: `status: completed`, `adr_refs`
      populated, `deferred_items_spec_refs` verified (exactly 3 entries), `changelog_ref` confirmed.

### Validator Verdict

**karen (Mode E, end-of-feature sign-off across P0–P6): APPROVED** — 2 fix cycles.

- **Cycle 1 (FIX-REQUIRED):** confirmed the §9.10 security invariant passes cleanly, but flagged 4
  items: [Critical] wall-clock leak in `rights_triage.py::maybe_assess_substitutability` breaking
  capture-time reproducibility; [High] 4 new `rf rights` CLI `--json` sites violating the
  machine-surface contract-drift guard; [Medium] missing `verified_by` on all 11 P6 tasks + 3 P1
  tasks (phase-completion gate failure); [Low] stale "(not yet written)" ADR wording for the now-
  shipped DOC-006 specs.
- **Fix cycle:** python-backend-engineer threaded the deterministic `now_iso()` clock through
  `maybe_assess_substitutability` and fixed a related corpus self-exclusion bug; wrapped 1 of 4 CLI
  sites in `_stamp()` and documented the other 3 as array-root exclusions (matching existing `rf run
  list` convention), updating the pinned baseline and `machine-surface-inventory.md`; phase-owner
  backfilled `verified_by` on P6 (11 tasks) and P1 (P1-2/P1-3/P1-4) via `update-status.py`
  (metadata-only); documentation-writer corrected the ADR wording.
- **Cycle 2 (APPROVED):** karen independently re-verified all 4 fixes at the code/doc level (not just
  self-reports), re-ran the affected test files, confirmed both `validate-phase-completion.py` gates
  pass with 0 violations, and re-ran the full authoritative suite — exactly 8 failures remain, all
  matching the pre-registered pre-existing/environmental set (`test_serve_api.py` sensitivity-gate
  default-public issue, `test_assertion_rollout.py` personal-checkout config divergence,
  `test_report_anchors.py` stale schema-version pin) — none introduced by this feature or its fix
  cycle.

### Files Changed

- `tests/test_rights_enum_consistency.py` — new (P6-1)
- `tests/unit/test_negative_write_path_consolidated.py` — new (P6-2)
- `tests/test_release_gate_integration.py` — new (P6-3)
- `tests/test_rights_validate_determinism_integration.py` — new (P6-4)
- `tests/integration/test_assertion_reuse.py`, `tests/test_reusable_assertion_ledger_phase1.py`,
  `tests/test_schema_validation.py` — fixture regen + §9.9 note (P6-5)
- `CHANGELOG.md` — `[Unreleased]` entry (P6-6)
- `README.md`, `docs/projects/research-foundry/SERVICE_CONTRACT.md`,
  `docs/dev/architecture/artifact-type-reference.md`, `CLAUDE.md` — doc updates (P6-7)
- `docs/project_plans/design-specs/rights-runtime-resolution-api.md`,
  `rights-surveillance-loop.md`, `rights-counsel-workflow.md` — new DOC-006 specs (P6-8a/b/c)
- `docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md` — frontmatter
  finalized (P6-9) + `changelog_ref` (P6-6)
- `src/research_foundry/services/rights_triage.py` — fix-cycle: deterministic clock threading +
  corpus self-exclusion
- `src/research_foundry/cli_commands.py` — fix-cycle: `_stamp()` wrap + array-root exclusion notes
- `tests/test_contract_drift_rf_schema_version.py`,
  `docs/dev/architecture/machine-surface-inventory.md` — fix-cycle: baseline/inventory update
- `docs/dev/architecture/adr-rights-entity-model.md` — fix-cycle: stale wording correction
- `.claude/progress/rights-entity-model/phase-1-progress.md` — fix-cycle: `verified_by` backfill
  (P1-2, P1-3, P1-4)
- `.claude/progress/rights-entity-model/phase-6-progress.md` — task status/evidence/verified_by,
  phase status `completed`

### Deviations & Risks

- P6-8a/8b/8c all append to the parent plan's `deferred_items_spec_refs` list field in parallel;
  each implementer re-read the field immediately before appending and confirmed no collision — final
  state has exactly the 3 required entries, no duplicates.
- The CLI contract-drift fix deviated from the literal "wrap all 4 sites in `_stamp()`" instruction:
  3 of the 4 new `rf rights --json` sites are list-rooted, so wrapping them in `_stamp()` would be an
  invalid/non-additive shape change. They were left as documented array-root exclusions instead,
  matching the file's existing `rf run list`/`rf report draft list` precedent — karen independently
  verified this is consistent with established convention, not a shortcut.
- 8 pre-existing/environmental test failures remain in the full suite (`test_serve_api.py` x5,
  `test_assertion_rollout.py` x2, `test_report_anchors.py` x1) — confirmed by karen as unrelated to
  this feature (sensitivity-threshold default-public gate, personal-checkout `foundry.yaml` opt-in,
  and an unrelated schema-version pin drift). Not chased per karen's explicit guidance.

### Commits (shared branch, no worktree isolation for this phase)

- `d9064c9` — feat(rights): P6 — test sweeps, fixtures, docs, DOC-006 specs; feature complete
