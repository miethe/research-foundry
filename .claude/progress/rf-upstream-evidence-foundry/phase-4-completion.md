## Phase 4 Completion Note — Council normalization + run lineage (RFUP-5, RFUP-7)

### Summary

Phase 4 normalized `arc_council` adapter verdicts into a controlled `approve|concern|block` enum
(non-destructive — raw text always retained) and added run-seal tamper-evidence: an additive
`--seal` flag on the existing `rf run export` CLI path, a content digest computed over the run's
evidence chain (claim ledger + source cards + report, reusing `assertion_registry.py`'s
atomic-write/digest patterns), and an append-only lineage record. All 5 tasks completed; validator
gate returned an explicit **APPROVED** verdict.

### Tasks

- [x] TASK-4.1 → python-backend-engineer — `CouncilVerdict` enum + `normalize_council_verdict()` in
      `adapters/arc_council.py`; raw `arc_verdict` retained; fail-toward-caution (unparseable →
      `concern`/`low`); no `run-export.ts` change (OQ-4 honored, confirmed empty diff by validator).
- [x] TASK-4.2 → python-backend-engineer + data-layer-expert — `--seal` additive flag on
      `rf run export` (`cli_commands.py`); `RunPaths.lineage` property (`paths.py`); `--seal --all`
      fails closed. OQ-2 resolution honored (no new CLI command needed — clean attach point found).
- [x] TASK-4.3 → data-layer-expert + python-backend-engineer — `seal_run()` / `recompute_digest()`
      in new `services/run_seal.py`; manifest-based sha256 digest over claim ledger + source cards +
      report_final (best-effort); reuses `assertion_registry.py`'s `_digest`/`_atomic_dump` directly
      (import, not reimplementation); append-only lineage entries.
- [x] TASK-4.4 → python-backend-engineer — tamper-evidence tests (per-file independent mutation
      detection), unsealed-run-unaffected regression, no-chmod invariant, missing-lineage resilience.
      Interrupted mid-validation by a monthly spend-limit error; resumed and completed after reset —
      all reported results independently re-verified by a follow-up verification pass.
- [x] TASK-4.5 → task-completion-validator — Phase 4 quality gate. **Verdict: APPROVED.**

### Validator Verdict

**task-completion-validator: APPROVED** (0 fix cycles). All AC-RFUP5-1..5 and AC-RFUP7-1..5 verified
against the diff and re-run test suite (not trusted from implementer self-reports alone — validator
independently ran `pytest -k "run_seal or seal or council_verdict"` and got 60 passed, 0 failed,
correcting a minor mis-stated per-file breakdown in an implementer report; aggregate count and pass
status were accurate). OQ-2 (additive CLI flag, not a new command) and OQ-4 (no `run-export.ts`
change, no schema bump) both explicitly confirmed compliant.

Validator flagged one **Low severity, non-blocking** cosmetic item: `paths.py`'s `lineage` property
docstring and the `--seal` CLI help string in `cli_commands.py` still reference "TASK-4.3 owns the
real digest logic" — stale now that TASK-4.3 landed. Does not affect behavior; left as a follow-up
cleanup item rather than blocking or re-dispatching for a one-line doc-string edit.

### Files Changed

- `src/research_foundry/adapters/arc_council.py` — python-backend-engineer (TASK-4.1): `CouncilVerdict`
  enum, `normalize_council_verdict()`, wired into `run()` non-destructively.
- `src/research_foundry/paths.py` — python-backend-engineer (TASK-4.2): `RunPaths.lineage` property.
- `src/research_foundry/cli_commands.py` — python-backend-engineer (TASK-4.2): `--seal` flag on
  `run_export`, fail-closed on `--seal --all`.
- `src/research_foundry/services/run_seal.py` (new) — data-layer-expert (TASK-4.3): `seal_run()`,
  `recompute_digest()`; reuses `assertion_registry.py` private helpers via import.
- `tests/test_council_verdict_normalization.py` (new) — TASK-4.1, 39 tests.
- `tests/test_seal_cli_flag.py` (new) — TASK-4.2, 3 tests.
- `tests/test_run_seal_lineage.py` (new) — TASK-4.3, 5 tests.
- `tests/test_run_seal_tamper_evidence.py` (new) — TASK-4.4, 13 tests.

Total targeted suite: 60 passed, 0 failed (`pytest -k "run_seal or seal or council_verdict"`).
Full-suite regression: 13 pre-existing failures unrelated to this phase (RF_SCHEMA_VERSION
contract-drift assumptions invalidated by Phase 1 already landing, `test_serve_api.py` 404s
self-acknowledged as pre-existing in the test file's own docstrings, `test_assertion_rollout.py`
default-flag mismatches tied to concurrent Phase-3/other work on `config/claim_policy.yaml`,
`test_report_anchors.py` schema-version-bump assumption) — none touch run_seal/lineage/council-verdict
code paths; isolated and confirmed deterministic outside the full-suite run.

### Deviations & Risks

- **Spend-limit interruption**: TASK-4.4's original agent hit a monthly spend-limit API error
  mid-validation-run. Resumed after the coordinator confirmed the limit reset; on-disk state was
  verified intact before resuming (git status confirmed all TASK-4.1–4.3 files present and
  unmodified by the interruption), and a dedicated verification pass independently re-ran both the
  targeted and full test suites rather than trusting the partial pre-interruption report.
- **Baseline failure count**: the task prompt cited "8 pre-existing baseline failures"; actual count
  in this worktree is 13 (this worktree has accumulated more uncommitted concurrent-phase work since
  that baseline was set). All 13 were individually isolated and confirmed unrelated to Phase 4's
  files — documented here rather than treated as a discrepancy requiring escalation.
- **Cosmetic stale docstrings**: see Validator Verdict above — non-blocking, not fixed in this phase.
- No Mode D triggers encountered. No files outside the phase's owned set
  (`adapters/arc_council.py`, `paths.py`, `services/assertion_registry.py` [reused, not modified],
  `cli_commands.py`) were touched. `services/search_router/router.py`, `services/source_cards.py`,
  and `pyproject.toml` (Phase 3's files) were not touched by any Phase 4 task.

### Commits

None — per the phase dispatch contract for this run (`Isolation: none`), the orchestrator does not
commit; work remains uncommitted on the current worktree branch (`worktree-rf-upstream-evidence-foundry`)
for the calling orchestrator to commit at the wave boundary.
