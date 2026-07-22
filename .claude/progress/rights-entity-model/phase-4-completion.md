## Phase 4 Completion Note — Capture Emission + Substitutability (C4)

### Status: COMPLETE — karen APPROVED (2nd verdict, fix-cycle closed)

### Summary

All 5 phase tasks (P4-1 … P4-5) landed. The first karen gate returned FIX-REQUIRED on two gaps;
a fix-cycle (interrupted once by a host disk-full `ENOSPC`, then resumed) closed all three
remediation items. A second karen gate returned **APPROVED** after independent on-disk verification.
Authoritative scoped regression: **196 passed / 0 failed**.

### Tasks

- [x] P4-1 → python-backend-engineer — capture-time `rights_summary` emission (`ingest_source`,
  `_prepare_one`). Disclosed deviation (all-`unknown` value rather than literal
  `review_status: agent_triage_only`, forced by the P2 `rights_record_ids` linkage requirement) —
  karen-adjudicated acceptable; remains a PRD/AC **wording** follow-up, not a code fix.
- [x] P4-2 → python-backend-engineer — terms snapshotting (content-addressed, export-excluded).
- [x] P4-3 → python-backend-engineer — structural snapshot-failure recording (`TermsSnapshotFailure`).
- [x] P4-4 → python-backend-engineer — substitutability search service, wired into BOTH real capture
  paths (`source_cards.py::ingest_source`, `assertion_materialization.py::_prepare_one`), persisted
  as a top-level `substitutability` field.
- [x] P4-5 → python-backend-engineer — `rf rights inspect`/`list` CLI.

### Fix-cycle (closed) — karen's two findings + one bug

1. **Rights-triage failure record (Finding 1) — CLOSED.** `compute_capture_rights_summary()`
   (`services/rights_triage.py`) catches any classifier exception, degrades to the all-`unknown`
   mirror **and** attaches `rights_triage_failure {reason:"classification_error", detail,
   attempted_at}` — a structural record, never a silent absence (AC P4-A resilience NFR, mirrors
   `TermsSnapshotFailure`). Field added + correctly nested in both `source_card.schema.yaml` and
   `source_assertion.schema.yaml`, and deliberately excluded from the link-before-assert `allOf`
   (a failure asserts no rights posture). Forced-failure test proves schema acceptance.
2. **Substitutability wiring (Finding 2) — CLOSED.** `maybe_assess_substitutability()` invoked in
   both real capture paths after `compute_capture_rights_summary()`; persisted top-level. Tests
   assert real captures populate a `substitutability` block on both paths.
3. **Schema indentation bug — CLOSED.** `substitutability` in `source_card.schema.yaml` had been at
   column 0 (a stray sibling of `properties:`/`required:`, therefore unreachable — invalid content
   would never fail validation). Re-indented to nest under `properties:` (sibling of
   `rights_summary:`). `source_assertion.schema.yaml` was already correct. New regression-guard tests
   in `tests/test_schema_validation.py` lock in reachability + content enforcement.

### Validator Verdict

- karen (Mode E), 1st pass: **FIX-REQUIRED** (Findings 1 & 2 above).
- karen (Mode E), 2nd pass: **APPROVED** — independently verified both findings closed, the
  `substitutability` property reachable/enforced by both schemas, and the failure record structural.

### Files Changed

- `src/research_foundry/services/rights_triage.py` — capture-time emission (P4-1) +
  substitutability seam (P4-4) + structural `rights_triage_failure`.
- `src/research_foundry/services/source_cards.py` — `ingest_source` rights_summary + substitutability.
- `src/research_foundry/services/assertion_materialization.py` — `_prepare_one` rights_summary +
  substitutability.
- `src/research_foundry/services/terms_snapshot.py` — content-addressed snapshots (P4-2) +
  `TermsSnapshotFailure`/`access_terms_snapshot_status()` (P4-3).
- `src/research_foundry/services/rights_substitutability.py` — substitutability search service (P4-4).
- `src/research_foundry/paths.py` — `RunPaths.rights`/`rights_terms_snapshots` (P4-2).
- `src/research_foundry/cli_commands.py` — `rf rights inspect`/`list` (P4-5).
- `schemas/rights_record.schema.yaml` — `access.terms_snapshot_failure` (P4-3).
- `schemas/source_card.schema.yaml` — `substitutability` (indentation fixed) + `rights_triage_failure`.
- `schemas/source_assertion.schema.yaml` — `substitutability` + `rights_triage_failure`.
- New/extended tests: `tests/test_rights_capture_emission.py`, `tests/test_rights_terms_snapshot.py`,
  `tests/test_rights_substitutability.py`, `tests/test_cli_rights.py`,
  `tests/test_rights_record_schema_fixtures.py`, `tests/test_schema_validation.py`.

### Deviations & Risks (carry-forward, non-blocking)

1. AC P4-A's literal `review_status: agent_triage_only` wording is unimplementable under the P2
   `rights_record_ids` linkage requirement; capture-time emission uses all-`unknown`. **PRD/AC text
   correction owed** (documentation, not code).

### Commits

Landed under the plan-orchestrator single-committer on `feat/rights-entity-model` (WIP `6970cf2`
superseded by the phase-complete commit recorded in the progress file `commit_refs`).
