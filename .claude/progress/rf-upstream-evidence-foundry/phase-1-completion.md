## Phase 1 Completion Note — Machine contract & schema versioning (RFUP-4)

### Summary

Phase 1 lands `RF_SCHEMA_VERSION` ("1.0.0") as the canonical machine-contract version constant and stamps it additively across all 7 AC-RFUP4-1 target surfaces: CLI `--json` outputs, `rf verify` YAML/JSON output, the LAN API (`/api/runs`, `/api/reports`, `/api/catalog`), and the run-export generator (`export_service.export_run()`, previously missed in the first fix cycle — see Deviations). `errors.py`'s `ExitCode` enum is documented as the FR-4.2 exit-code contract rather than JSON-stamped (it has no JSON-emitting surface of its own). Contract drift tests (with real divergence-detection via monkeypatch, not tautological) and before/after key-diff tests confirm zero renamed/removed keys anywhere. No behavior change beyond the additive field; `run-export.ts` stayed at schema 1.5 (no dual-update bump needed, per plan's expected outcome).

### Tasks

- [x] TASK-1.1 → python-backend-engineer — `RF_SCHEMA_VERSION` constant (`src/research_foundry/__init__.py:23`) + machine-surface inventory doc (`docs/dev/architecture/machine-surface-inventory.md`), all 7 surfaces enumerated (PRD's AC-RFUP4-1 lists 7, plan table's "6" was stale — flagged and corrected).
- [x] TASK-1.2 → python-backend-engineer (impl) + api-designer (contract doc) — stamped ~26 dict-root `--json` CLI sites via a `_stamp()` helper; 2 array-root outputs (`rf run list`, `rf report draft list`) deliberately left unstamped (documented, additive-only rationale); authored `docs/dev/architecture/machine-contract-spec.md` (FR-4.2).
- [x] TASK-1.3 → python-backend-engineer — stamped `services/verification.py` (both `verify_report`/`verify_draft`), a new shared `api/response_stamp.py` helper used by all 3 API routers, and (after 2 fix cycles — see Deviations) `export_service.export_run()`. `run-export.ts` gained an optional `rf_schema_version?: string`; no 1.5→1.6 bump needed.
- [x] TASK-1.4 → python-backend-engineer — `tests/test_contract_drift_rf_schema_version.py` (26 tests): unit tests on the stamp helpers with real divergence-detection (monkeypatch), a structural scan classifying every CLI `--json` site, live presence/value smoke tests, and key-diff tests proving additive-only across all surfaces.
- [x] TASK-1.5 → task-completion-validator — 3 review passes; PASS on the third (see Validator Verdict).

### Validator Verdict

**PASS** (3rd pass) — all AC-RFUP4-1..5 met, verified independently by the validator (not from self-reports; it ran pytest/flake8 itself each time).

Fix cycles (2, within the "escalate after 2+ failed cycles" budget but resolved before requiring Opus escalation):
1. **Pass 1 → FIX-REQUIRED**: `export_service.export_run()` (the generator behind the runs-viewer's static `run.json` build, not just the LAN API response) was never stamped. Fixed: added `rf_schema_version` to its dict literal + a new drift/key-diff test.
2. **Pass 2 → FIX-REQUIRED**: the fix above caused a new regression — `docs/dev/architecture/rf-run-export-schema.json` has `additionalProperties: false` and didn't allowlist the new key, breaking `test_export_run_passes_strict_json_schema_validation`; also surfaced a latent `e.path_deque` AttributeError bug in that test's own diagnostics. Fixed: added `rf_schema_version` to the schema's `properties` (additive, not `required`), corrected the test to use `e.absolute_path`.
3. **Pass 3 → PASS**: full suite back to exactly the 8 pre-existing baseline failures (`tests/test_serve_api.py` x5, `tests/unit/test_assertion_rollout.py` x2, `tests/test_report_anchors.py` x1), zero new failures; `-k contract_drift` 26/26 passed; `flake8 --select=E9,F63,F7,F82` clean.

### Files Changed

- `src/research_foundry/__init__.py` — `RF_SCHEMA_VERSION = "1.0.0"` constant (TASK-1.1)
- `src/research_foundry/cli_commands.py` — `_stamp()` helper + ~26 stamped `--json` sites (TASK-1.2)
- `src/research_foundry/services/verification.py` — `VerificationResult` dataclass field + persisted record stamping (TASK-1.3)
- `src/research_foundry/api/response_stamp.py` (new) — shared `stamp()` helper (TASK-1.3)
- `src/research_foundry/api/routers/{runs,reports,catalog}.py` — stamped dict-root responses (TASK-1.3)
- `src/research_foundry/services/export_service.py` — `export_run()` stamped (TASK-1.3, fix cycle 1)
- `frontend/runs-viewer/src/types/rf/run-export.ts` — optional `rf_schema_version?: string` (TASK-1.3)
- `docs/dev/architecture/rf-run-export-schema.json` — `rf_schema_version` added to `properties` allowlist (fix cycle 2)
- `docs/dev/architecture/machine-surface-inventory.md` (new) — FR-4.1/AC-RFUP4-2 inventory (TASK-1.1, updated through fix cycles)
- `docs/dev/architecture/machine-contract-spec.md` (new) — FR-4.2 exit-code/JSON contract doc (TASK-1.2)
- `tests/test_contract_drift_rf_schema_version.py` (new) — 26 contract-drift/key-diff tests (TASK-1.4, extended through fix cycles)
- `tests/test_schema_validation.py` — `e.path_deque` → `e.absolute_path` fix (fix cycle 2)
- `tests/test_serve_catalog.py`, `tests/integration/test_run_launch_reuse.py` — 5 pre-existing exact-dict-equality assertions updated for the additive field (TASK-1.3)

### Deviations & Risks

- Plan's task table (line 289) says "6 target_surfaces" for AC-RFUP4-1; the PRD text and inventory doc correctly enumerate 7 (`errors.py`, `cli_commands.py`, `services/verification.py`, `run-export.ts`, `/api/runs`, `/api/reports`, `/api/catalog`). Cosmetic drift in the plan file only — noted by the validator as non-blocking, not corrected in this phase (out of scope for a phase-owner edit to the plan file).
- 2 fix cycles were required (see Validator Verdict) — both were narrow, mechanical, single-file corrections; neither required Opus escalation.
- 6 array-root surfaces (2 CLI, 4 API) deliberately left unstamped — wrapping a bare JSON array in an object would be a non-additive shape change under FR-4.4. Judged legitimate by the validator on both review passes.
- 8 pre-existing test failures (`test_serve_api.py` x5, `test_assertion_rollout.py` x2, `test_report_anchors.py` x1) predate this phase (confirmed via `git stash` isolation by two independent agents) — out of scope for Phase 1, not touched.

### Commits (worktree runs)

None — Isolation was `none` for this dispatch (session already inside the worktree on branch `worktree-rf-upstream-evidence-foundry`); per explicit instruction, the phase-owner does not commit — the orchestrator commits at wave boundaries. All Phase 1 work is present as uncommitted changes on the current branch, ready for the orchestrator's wave-boundary commit.
