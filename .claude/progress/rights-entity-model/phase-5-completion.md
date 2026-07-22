## Phase 5 Completion Note — Governance Gate + Canonical ADR

### Summary

Closed the second half of the §9.10 authorization-boundary requirement (P3-4 closed the
`synthesis.attestation.status` write path in Phase 3; P5-1/P5-2 close
`rights_record.overall_status` / `content_reuse_assessment.decision.{status,release_gate}` /
`rights_extension.clearance_status`), added the bidirectional `judgment_basis: unassessed`
release-gate predicate (resolves decisions-block OQ-6), and authored RF's canonical rights ADR
recording all 10 §9 adjudications plus named debt for OQ-RF-5/OQ-RF-6.

### Tasks

- [x] P5-1 → python-backend-engineer — New governance-layer guard rule
      `no_agent_cleared_rights_value` in `governance.py`, enumerating the 4 named fields
      explicitly; blocks `CLEARED_*`/`counsel_approved`/`attested` via
      `GuardContext.proposed_field_writes`. Direct unit coverage added to
      `tests/test_governance_adversarial.py`.
- [x] P5-2 → python-backend-engineer (extended effort) — Independent negative-test suite
      `tests/unit/test_rights_status_write_ceiling.py` (19 tests), enumerating every
      agent-reachable write path across 9 modules. Verified independent of P3-4's
      `test_synthesis_attestation_write_ceiling.py` — no shared fixtures/imports, disjoint
      field/path sets. Combined run: 27 passed. Notable finding (not a gap): no Python writer
      for `rights_record`/`content_reuse_assessment`/`rights_extension` exists yet anywhere in
      the codebase — the boundary is proven vacuously-safe today and will gate any future writer.
- [x] P5-3 → python-backend-engineer — `release_gate_blocked_by_unassessed_judgment` predicate
      added to `governance.py`; `verification.py::verify_report` calls it as a new named check
      (`release_gate_judgment_basis_assessed`) — not a duplicate implementation. Bidirectional
      test in `tests/test_release_gate_judgment_basis.py`: commercial-release blocked,
      internal-capture unblocked, both asserted explicitly.
- [x] P5-4 → documentation-writer — `docs/dev/architecture/adr-rights-entity-model.md` authored,
      following `adr-runs-read-path.md`'s pattern. All 10 §9 adjudication rows present,
      `resolves: [OQ-RF-1..4]` with rationale, "Known Gaps" section naming OQ-RF-5/OQ-RF-6 with
      links to (not-yet-written) `rights-surveillance-loop.md` / `rights-counsel-workflow.md`
      (P6-8b/c).

### Validator Verdict

`task-completion-validator` (Mode E): **PASS**. All 5 verification items (P5-1..P5-4 + independent
regression run) confirmed directly against source/tests, not self-reports. Explicitly confirmed
P5-2's independence from P3-4 is authentic (the item most likely to be faked via collapse) — not a
rename or thin wrapper. One fix cycle (0 required — first-pass PASS).

Reviewer also flagged a low-severity, non-blocking hygiene item (see Deviations below).

### Files Changed

- `src/research_foundry/services/governance.py` — P5-1 guard rule + P5-3 predicate.
- `src/research_foundry/services/verification.py` — P5-3 caller wiring (`verify_report`).
- `tests/test_governance_adversarial.py` — P5-1 direct rule coverage.
- `tests/unit/test_rights_status_write_ceiling.py` (new) — P5-2 independent negative-test suite.
- `tests/test_release_gate_judgment_basis.py` (new) — P5-3 bidirectional test.
- `docs/dev/architecture/adr-rights-entity-model.md` (new) — P5-4 canonical ADR.
- `.claude/progress/rights-entity-model/phase-5-progress.md` — task/phase status tracking.

### Deviations & Risks

- **Minor, non-blocking**: the progress file's `success_criteria[].status` entries (P5-SC1..SC5)
  remain `pending` despite all 4 tasks being genuinely complete and validator-confirmed — the
  `artifact-tracking` CLI (`update-status.py`) only updates the `tasks:` list, not
  `success_criteria:`, and per `.claude/rules/progress-cli-only.md` direct YAML edits are
  prohibited for the phase-owner. Flagged by the reviewer as an artifact-tracking hygiene gap, not
  a functional gap. Recommend a follow-up to `artifact-tracking` scripts to support
  `success_criteria` status updates, or a manual `artifact-tracker` agent pass before Phase 6 sync
  reads this file.
- No other deviations. All 4 tasks match their plan-file AC and phase quality gates exactly.

### Commits

- `0868aea` — feat(rights): P5 — governance write-ceiling backstop + release-gate predicate + rights ADR
- `2b22f0e` — chore(progress): Phase 5 verified_by + status=completed (task-completion-validator PASS)
