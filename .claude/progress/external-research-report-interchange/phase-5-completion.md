---
type: report
schema_version: 2
doc_type: report
title: "Phase 5 Completion — Resumable Importer and CLI"
report_category: other
feature_slug: external-research-report-interchange
created: 2026-07-27
status: completed
owners: ["python-backend-engineer"]
related_documents:
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/dev/architecture/external-research-handoff-contract.md
  - .claude/findings/eri-p1-contract-audit-gpt56.md
  - .claude/progress/external-research-report-interchange/phase-4-completion.md
  - .claude/progress/external-research-report-interchange/phase-5-progress.md
---

# Phase 5 Completion — Resumable Importer and CLI

## Files changed

New:
- `src/research_foundry/services/external_research_import.py` (415 lines) — ERI-5.1/5.2/5.4 orchestrator (`import_external_report`), `DEFAULT_ACQUISITION_POLICY`, `ImportOutcome`, `PendingImportError`.
- `tests/integration/test_external_research_import.py` (23 tests) — end-to-end orchestration, batching/resume, cancellation, provenance seam.
- `tests/unit/test_external_research_cli.py` (15 tests) — CLI argument wiring, exit codes, machine-output shape (service mocked).

Additive edits to existing files:
- `src/research_foundry/services/external_research_interchange.py` — `ActionResolution` gained a defaulted `canonical_refs: Mapping[str, str] = field(default_factory=dict)` field; `_effect_digest` now folds it in instead of hardcoding `{}` (closes the "canonical_refs / effect_digest gap" flagged in `phase-4-completion.md`'s deferred items). No other line changed; every existing 3-positional `ActionResolution(...)` call site is unaffected by the new defaulted 4th field.
- `src/research_foundry/services/external_research_resolution.py` — **real bug found and fixed** (see below): extracted `_existing_edition_reuse` (read-only registry lookup, previously inlined in `_resolve_source_impl`) and added `_ensure_source_outcome`, called from `resolve_candidate` before `_resolve_candidate_impl`, to make cross-batch-call candidate resolution correct.
- `src/research_foundry/services/export_service.py` — added `record_external_report_import_activity()` (ERI-5.4 seam), reusing the codebase's existing `_trace(rp, stage=..., **fields)` idiom via `append_jsonl`/`now_iso`.
- `src/research_foundry/cli_commands.py` — added `rf intake external-report` under the existing `intake_app` Typer group (additive only; no other command touched).

## A real bug found and fixed (Phase-5-critical)

While building the "interrupted vs. uninterrupted convergence" test the plan's quality gate requires, discovered that `ExternalResearchResolver._source_outcomes` is **per-resolver-instance, per-call memory**, populated only when `resolve_source` actually runs. Since `import_external_report` constructs a fresh resolver on every call, and `ExternalResearchInterchange._execute` never re-invokes `resolve_source` for a source whose effect is already durably persisted (correct resume behavior), a candidate citing a source that was resolved in an **earlier** batched call — but processed in a **later** call — would falsely quarantine `citation_unresolved`, even though the source's edition/passage were already durably registered in `AssertionRegistry`. This silently broke resumability correctness for exactly the packets Phase 5 exists to make resumable (any packet whose source count exceeds one `--limit` batch).

Fix (`external_research_resolution.py`): extracted the existing "contract §2.4 step 3, existing-edition reuse" read-only lookup out of `_resolve_source_impl` into `_existing_edition_reuse(normalized, source_key)` (zero behavior change — same logic, now callable independently), and added `_ensure_source_outcome(ref, sources_by_id)`, called for every `resolvable_ref` at the top of `resolve_candidate`. It is a no-op when the ref is already known; otherwise it re-derives the source's outcome via the same read-only registry lookup (never network I/O, never a registry write) — safe because the packet's canonical action order guarantees every source action has already run (in this call or an earlier one) by the time any candidate is resolved. Caught directly by `tests/integration/test_external_research_import.py::TestBatchingAndResume::test_interrupted_and_uninterrupted_runs_converge_to_identical_receipt`, which failed before the fix (one candidate diverged: `completed_with_quarantine` vs. `completed`, `passage_resolved` vs. `None`) and passes after it, with `effect_digest` equality asserted per action.

## Task-by-task

**ERI-5.1 (deterministic action orchestration).** Confirmed `ExternalResearchInterchange.stage()` (Phase 2) already builds the sorted, bounded action set from the canonical manifest and resumes at the first incomplete action by construction (`_execute` skips any action whose immutable effect file already exists) — Phase 5 adds no second identity/ordering authority (contract §3.5). `import_external_report` pre-derives the SAME `packet_digest`/`policy_digest`/`governance_policy_digest`/`action_manifest_digest`/`receipt_digest` formulas `stage()` computes internally (imported directly from `external_research_interchange`, not reimplemented) so a caller can inspect pending state before deciding whether to proceed — this is what the `resume=`/`PendingImportError` guard is built on.

**ERI-5.2 (chunking and cancellation).** Implemented entirely by wrapping the `resolve_source`/`resolve_candidate` callables passed into `stage()` with a shared counter that raises an internal `_BatchLimitReached` signal once `limit` (default 100, ERI-OQ-4) fresh resolutions have run in one call — **zero changes to `stage()`/`_execute`'s internals**. Because `stage()` already durably persists each action's effect + an updated `pending` checkpoint before resolving the next action, this signal propagating out of `stage()` leaves exactly the same on-disk state a genuine cancellation would. Batching is disabled entirely during `dry_run` (a dry run resolves every action in one pass with zero writes, matching `stage(dry_run=True)`'s existing behavior). Genuine cancellation (`KeyboardInterrupt` mid-acquisition, not a deliberate `--limit`) is tested separately (`TestCancellation`) via a fake `acquire` that raises for one specific locator — proves the interrupt propagates uncaught, the checkpoint stays pending, a bare re-call without `--resume` is refused (`PendingImportError`), and `--resume` completes cleanly with zero duplicate effect files.

**ERI-5.3 (CLI and machine output).** `rf intake external-report PACKET_DIR --workspace ... [--run ...] [--dry-run] [--resume] [--limit N] [--json]` added to the existing `intake_app` Typer group. `--limit 0` maps to unlimited (`None`). Machine (`--json`) output is `ImportOutcome.safe_dict()` — workspace/target-run ids, safe generated ids (`packet_digest`/`receipt_id`/`receipt_digest`), `status`, `complete`/`replayed`/`dry_run`, `block_reason` (packet family only), aggregate `counts`, and `cursor` — never the full receipt, never packet-derived free text, never a private absolute path, never the 14-code source/citation/candidate reason-code vocabulary (contract §4.6). Exit code `ExitCode.SCHEMA` (2) on a `blocked` receipt; exit 0 for `completed`/`completed_with_quarantine`/pending-batch-limit (all legitimate, non-error outcomes per the contract); `PendingImportError`/`ValueError` route through the existing `_fail()` helper.

**ERI-5.4 (provenance/export seam).** `export_service.record_external_report_import_activity(paths, run_id, receipt=..., provenance_origin=...)` appends one best-effort, try/except-wrapped event (`stage: "external_report_import"`) to the target run's **existing** `telemetry/run_trace.jsonl` — the same mechanism `source_cards`/`writeback`/`verification`/`synthesis`/etc. already use, not a new telemetry channel. Called only when `target_run_id` is set and the call is not a `dry_run` (a dry run must never mutate anything, including a run's timeline — asserted directly by `test_dry_run_never_records_provenance_event`; staging-only imports never even attempt the call — asserted by `test_staging_only_seam_is_not_invoked`, monkeypatching the seam to raise if called). `provenance_origin` is an optional, nullable, opaque string — RPC's real `provenance_origin` schema does not exist on this tree yet (contract §3.1); no structure is invented for it. `import_external_report` itself is the intended Operator-MCP seam: a plain, typed, non-CLI-coupled function — no MCP tool was built (out of scope per the task).

## Test counts

- `tests/integration/test_external_research_import.py`: 23 passed (new).
- `tests/unit/test_external_research_cli.py`: 15 passed (new).
- Combined new-surface run: **38 passed**.
- Full specified regression gate (`test_external_research_schemas.py` + `test_external_research_interchange.py` + `test_external_research_profiles.py` + `test_source_acquisition_policy.py` + `test_external_research_resolution.py` + `test_schema_validation.py` + the two new Phase 5 files): **456 passed, 0 failed** — up from the pre-Phase-5 baseline of 79 (interchange 48 + resolution 31) across just those two files; zero existing tests modified.
- Additional targeted check on `export_service.py` (touched file, broadly depended-on): `test_export_service.py` + `test_export_service_term_index.py` + `test_export_round_trip.py` — 138 passed, 4 skipped (pre-existing, reference-run-not-present skips, unrelated).
- `ruff check` on every new/changed file: clean. (`external_research_interchange.py` has one pre-existing `UP012` finding on line 1392, inside the Phase-2-era `_receipt_lease` token construction — not on any line this phase touched, left as-is.)
- `mypy --ignore-missing-imports` on every new/changed file individually: **0 errors attributable to this phase's changes** (`export_service.py` initially showed 3 union-attr errors on the lines I added — fixed by narrowing `counts` through a named local rather than a repeated `.get()` call in a ternary; `cli_commands.py` still shows 2 pre-existing errors on unrelated lines (1494, 2030/2035) from before this phase, confirmed via `git diff --stat` showing only insertions).
- `rf intake external-report --help` via the real `rf` console-script entry point: loads and renders correctly (verified directly, not only via `CliRunner`).

## Byte-identical convergence evidence (AC ERI-5 / Phase 5 quality gate)

`TestBatchingAndResume.test_interrupted_and_uninterrupted_runs_converge_to_identical_receipt`: a 3-source/3-candidate packet (6 canonical actions) is imported two ways, on two independent on-disk storage roots (same `workspace_id`/policy/packet, so the same `receipt_digest` is expected):

1. **Interrupted**: three separate `import_external_report` calls with `limit=2`, the last two with `resume=True` (2 actions per call: sources 0-1, then 2-3, then 4-5).
2. **Uninterrupted**: one `import_external_report` call with `limit=None`.

Assertions: `receipt_digest` equal; full receipt dict equal **except `created_at`** (excluded because it is deliberately not a `receipt_digest` input, contract §1.3, and legitimately differs between two independently-timestamped completions — this is not a residual gap, it is what the contract's own identity formula specifies); and, separately, every action's `effect_digest` (which now folds in `canonical_refs` per this phase's fix) matches between the two runs — the literal "identical canonical effects" requirement, not just top-level receipt equality. This test is what caught the `_source_outcomes` cross-batch bug above; it failed before the fix and passes after it.

`TestCancellation.test_keyboard_interrupt_preserves_pending_checkpoint_and_resume_completes` covers the same convergence property under a genuine (non-deliberate) interruption rather than a configured `--limit`.

## Unresolved / deferred — for Phase 6 and beyond

1. **Timing-uniformity floor (contract §4.3.1) not implemented.** The contract's one v1-mandatory timing guarantee (fresh acquisition and stored-identity reuse routed through the same configurable minimum-latency floor) is explicitly Phase 4/6 hardening scope, not named in Phase 5's own task list; not touched here.
2. **`governance_policy_digest` remains the Phase-2 placeholder.** Unaffected by this phase; still requires a real Step 0 caller/workspace authorization gate (audit finding #9) before it can be more than `_GOVERNANCE_PLACEHOLDER_RULESET`.
3. **Non-PDF byte-accepting extractor's HTML stripping is stdlib-only (`html.parser`).** Unrelated to Phase 5; carried over from Phase 4, still adequate for the fixtures exercised so far.
4. **No `--policy-file` CLI override.** `rf intake external-report` always uses `DEFAULT_ACQUISITION_POLICY` (the frozen v1 defaults). Deliberately out of scope — the plan's ERI-5.3 deliverable names only workspace/run/dry-run/resume/limit/machine-output, and an operator-configurable policy override is not among them; adding one is a natural, small Phase 6+ extension if a real need for a non-default policy configuration arises.
5. **`ERI-5.G` (exact-tree importer gate) is `pending`**, per its own dependency on `task-completion-validator` then Karen review — not something this implementation task can mark complete itself.
