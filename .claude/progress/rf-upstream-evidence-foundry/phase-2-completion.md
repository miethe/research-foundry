## Phase 2 Completion Note — Exact-passage hard-gating in `rf verify` (RFUP-3)

### Summary

Added a new `exact_passage_present` eligibility check to `rf verify`, distinct from the existing
`source_cards_have_locators` check, that fails claims citing a source card without a resolvable
exact quote/passage anchor. The check is gated by a new `verify.exact_passage: warn|strict` flag
(config default `warn`, run-level `--exact-passage` CLI override that wins on conflict, per OQ-1).
Default (`warn`) mode is fully backward-compatible — zero change to `passed`/`exit_code` behavior;
`strict` mode hard-blocks. A dedicated `exact_passage_violations` field was added to verify output,
optional/absent-safe for existing consumers. All work built cleanly on Phase 1's stamped schema
without touching Phase 3's concurrently-owned files.

### Tasks

- [x] TASK-2.1 → python-backend-engineer — `verify.exact_passage` config key (`config/claim_policy.yaml`)
      + `resolve_exact_passage_mode()` resolver + `--exact-passage` CLI override wired through
      `cli_commands.py`; CLI-wins-over-config precedence unit-tested explicitly (10 tests).
- [x] TASK-2.2 → python-backend-engineer — new `exact_passage_present` eligibility check in
      `verify_report()`; warn mode never touches `unsupported`/`passed`/`exit_code`, strict mode
      blocks. `_index_source_cards()` extended with `has_quote`. 4 new tests, 14 total passing.
- [x] TASK-2.3 → python-backend-engineer — `exact_passage_violations` field persisted in
      `reviews/verification.yaml` + `VerificationResult` (absent-safe default). Real-corpus
      regression: the actual 2,835-assertion backfilled corpus is **not present in this worktree**
      (data-plane split — private data repo not mounted); substituted the largest available
      existing multi-claim fixture (`test_claim_verifier` LEDGER) and explicitly documented the
      substitution rather than fabricating corpus-scale coverage. 20 tests total, all passing.
- [x] TASK-2.4 → task-completion-validator — **APPROVED**, explicit verdict (not silent). See below.

### Validator Verdict

**PASS (APPROVED)**. The validator independently re-ran `pytest -k exact_passage` (20 passed),
`test_claim_verifier.py` + `test_verifier_adversarial.py` (21 passed, zero regressions), and
`test_contract_drift_rf_schema_version.py` (5 failed / 21 passed — confirmed pre-existing baseline
via its own `git stash` check, not taken on faith). Zero fix cycles required.

Non-blocking follow-ups flagged by the validator (see Deviations below):
1. The real-corpus substitution (item 4 above) should be re-run against the actual 2,835-assertion
   corpus once the private data repo is mounted, before treating strict-mode rollout as fully
   de-risked.
2. `tests/test_contract_drift_rf_schema_version.py:462-476` (`test_keydiff_verify_report_record_vs_head`,
   out of Phase 2 scope, already red for an unrelated pre-existing `rf_schema_version` drift reason)
   will need its expected key-delta updated to include `exact_passage_violations` when that
   pre-existing drift is eventually reconciled — not a new regression, but noted so it isn't lost.
3. No CLI-level (`_invoke_cli`) end-to-end test drives `rf verify --exact-passage ...` through the
   actual Typer command; coverage stops at `verify_report(exact_passage_override=...)`. Low risk
   (one-line passthrough) but worth closing later.

### Files Changed

- `config/claim_policy.yaml` — added `verify: { exact_passage: warn }` section + `exact_passage_present`
  entry in `verifier_checks` (TASK-2.1, TASK-2.2)
- `src/research_foundry/services/verification.py` — `resolve_exact_passage_mode()`, `VerificationResult`
  gained `exact_passage_mode` + `exact_passage_violations` fields, `verify_report()` gained
  `exact_passage_override` param, new `exact_passage_present` check block, `_index_source_cards()`
  extended with `has_quote` (TASK-2.1, TASK-2.2, TASK-2.3)
- `src/research_foundry/cli_commands.py` — `verify` command gained `--exact-passage` option (TASK-2.1)
- `tests/test_verification_exact_passage.py` (new) — 20 tests across all three implementation tasks

### Deviations & Risks

- **Real-corpus regression scope (AC-RFUP3-3)**: the plan's specified 2,835-assertion backfilled
  sample + prior KnitWit/other runs is not physically present in this worktree (data-plane split;
  private data repo lives outside the mounted checkout). TASK-2.3 substituted the largest available
  in-suite fixture and documented this explicitly; the validator accepted this as a reasonable,
  honestly-flagged interim gate but recommends a follow-up re-run against the real corpus before
  strict-mode is considered fully de-risked for downstream (Evidence Foundry) consumers. This should
  be tracked — not silently dropped — likely as a Phase 6 cross-phase regression follow-up or a
  dedicated in-flight finding.
- No Mode D triggers encountered. No file-ownership conflicts with concurrently-running Phase 3
  (confirmed via `git diff --stat` scoping before dispatching the validator gate — only Phase 2's
  four files were touched by this phase's implementers).

### Commits (worktree runs)

- Not committed by this phase-owner — per the isolation instructions for this run ("Isolation: none
  ... do NOT commit — the orchestrator commits at wave boundaries"), commit is deferred to the
  parent orchestrator at the wave boundary.
