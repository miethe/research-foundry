---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: complete
created: '2026-07-31'
updated: '2026-07-31'
---

# M3 Leg C — AC -> command -> evidence reconciliation

Scope: every row of the "AC -> command -> evidence" matrix in
`docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`
(lines 607-624). Mode A, read-only. All commands run from repo root with
`./.venv/bin/python`. Real command output pasted below — nothing fabricated.

**Headline: two rows are genuinely broken, not merely noisy, and a third could not be
honestly closed out.** Row "M1 — retry/cancel idempotency" selects **zero tests** (its `-k`
filter has no live term against the file it names). Row "AC OPM-7 — bounded transport"
silently drops the oversized-payload test and cannot evidence its own "wrong-workspace" claim
from the named file at all. Both are detailed below with the VAL-1-style diagnostic proof
(same defect class the matrix itself already documents for the M2 tool-inventory row). Third:
the "Whole-suite regression" row's full-suite run hit severe cross-agent contention in this
same worktree (94% swap, a concurrent sibling pytest process) and surfaced 23 FAILED nodes
including one on the operator surface — which then passed cleanly in isolation. That row needs
a clean single-tenant re-run before its baseline claim can be trusted either way; see the
dedicated section near the end of this document.

---

## Row: M1 — closed dispatch, no CLI reach

**Command:** `rg -n "typer\|cli_commands\|subprocess\|os\.system\|shell=True" src/research_foundry/services/operator_mcp_adapters/` (+ `src/research_foundry/operator_mcp/`)

**Exists-check:** both paths exist.
```
src/research_foundry/services/operator_mcp_adapters  -> EXISTS
src/research_foundry/operator_mcp                     -> EXISTS
```

**Real output:**
```
$ rg -n "typer|cli_commands|subprocess|os\.system|shell=True" src/research_foundry/services/operator_mcp_adapters/
external_import.py:31:...cli_commands.py's intake_external_report...
source_ingest.py:10,12:...cli_commands.py's own ingest command...
job_lifecycle.py:4,7:...AgentJobService subprocess record...
swarm_start.py:9:...never imports a CLI/Typer/subprocess path...
base.py:57,67:...No CLI / Typer / subprocess import...
run_plan.py:88:...# still imports cleanly without the [serve] extra...

$ rg -n "typer|cli_commands|subprocess|os\.system|shell=True" src/research_foundry/operator_mcp/
server.py:9,10:...It never imports Typer, cli_commands, subprocess, os.system, or uses shell=True...
```
9 hits in the adapters tree, 2 in the server tree. **Classification table** (opened every hit
line ±3 lines and confirmed against each file's docstring-close line via `awk`):

| File:line | Text | Classification |
|---|---|---|
| external_import.py:31 | `cli_commands.py`'s `intake_external_report` | docstring (closes L83) |
| source_ingest.py:10 | `cli_commands.py`'s own `ingest` command | docstring (closes L68) |
| source_ingest.py:12 | `cli_commands.py:354` | docstring (closes L68) |
| job_lifecycle.py:4 | `AgentJobService` subprocess record | docstring (closes L103) |
| job_lifecycle.py:7 | subprocess spawn-model | docstring (closes L103) |
| swarm_start.py:9 | never imports a CLI/Typer/subprocess path | docstring (closes L113) |
| base.py:57 | No CLI / Typer / subprocess import | docstring (closes L69) |
| base.py:67 | subprocess-blocked boundary test | docstring (closes L69) |
| run_plan.py:88 | `# still imports cleanly...` | `#` comment |
| server.py:9 | never imports Typer, cli_commands... | docstring (closes L189) |
| server.py:10 | ...subprocess, os.system, shell=True... | docstring (closes L189) |

**Verdict: SOUND.** All 11 hits are inside module docstrings or `#` comments, zero live-code
matches. The row's own caveat ("verify the paths exist first") is satisfied — both paths exist
— and the zero-live-code claim holds under manual inspection, not just `rg`'s own count.

---

## Row: M1 — adapter/service parity

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q`

**Exists-check:** glob resolves to 9 files, all present (`base`, `external_import`,
`job_lifecycle`, `research_stages`, `run_plan`, `source_ingest`, `swarm_start`,
`verify_bundle`, `writeback_preview`).

**Collect count:** 150 tests, no `-k` filter (whole files run).

**Verdict: SOUND, with a scope nuance.** The evidence claim ("Parity assertions compare
canonical refs from direct-service vs adapter and match") is literally true for 6 of the 9
files, which carry an explicit `test_invoke_*_result_matches_direct_*_call` test:
`external_import`, `research_stages` (×3 stages), `run_plan`, `source_ingest`,
`verify_bundle` (×2). The other 3 — `base.py` (registry mechanics, no direct-service
counterpart to compare), `job_lifecycle.py` (job.status/cancel/resume — no literal
direct-comparison test; covered instead by ceiling/wrong-workspace/locked-store assertions),
and `swarm_start.py` (has `test_invoke_dispatches_each_adapter_via_run_swarm_and_merges_
candidates`, which wraps the real `run_swarm` but does not assert a canonical-ref-match in the
same explicit form) — do not carry that specific assertion shape. Since the row has no `-k`
filter, all 150 tests run regardless, so this is a labeling nuance, not a vacuous filter.

---

## Row: M1 — CLI unchanged after extraction

**Command:** `./.venv/bin/python -m pytest tests/test_search_router_router.py tests/integration/test_run_launch_reuse.py -q`

**Exists-check:** both files exist.

**Collect count:** 66 tests (3 in `test_run_launch_reuse.py`, 63 in `test_search_router_router.py`).

**Real output:**
```
66 passed, 18 warnings in 5.91s
```

**Verdict: SOUND.** All 66 pass; the only warnings are FastAPI's `on_event` deprecation
notice, unrelated to this AC.

---

## Row: M1 — retry/cancel idempotency ⚠️ VACUOUS

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q -k "retry or cancel or resume or duplicate"`

**Exists-check:** file exists.

**Real output:**
```
no tests collected (33 deselected) in 0.11s
```

**Zero tests selected.** This is a hard vacuity, not the softer VAL-1 shape (which at least
selects a subset). The full file's 33 test names (pasted below) contain **none** of the four
filter terms:
```
test_consume_creates_operation_and_consumes_confirmation
test_same_confirmation_presented_twice_is_exact_replay_of_same_operation
test_fresh_confirmation_same_idempotency_key_and_digest_is_exact_replay
test_changed_manifest_same_idempotency_key_is_idempotency_conflict
test_non_issued_confirmation_status_denies_with_zero_manifest[expired-confirmation_expired]
test_non_issued_confirmation_status_denies_with_zero_manifest[revoked-confirmation_mismatch]
test_consumed_confirmation_with_mismatched_bindings_denies_as_conflict
test_binding_mismatch_on_issued_confirmation_denies
test_expired_confirmation_denies_with_zero_manifest
test_missing_confirmation_id_denies
test_wrong_workspace_operation_lookup_indistinguishable_from_missing
test_concurrent_consumers_of_one_confirmation_yield_one_success_one_conflict
test_consume_locked_is_only_ever_invoked_with_an_already_open_transaction
test_two_real_os_processes_racing_the_same_confirmation_yield_one_success_one_conflict
test_two_real_os_processes_genuinely_block_on_begin_immediate_not_merely_interleave
test_missing_authorization_denies_without_touching_storage
test_authorization_denied_at_rbac_cannot_be_bypassed_by_a_valid_confirmation
test_authorization_bound_to_a_different_ctx_denies
test_manifest_schema_validation_failure_is_governed_not_raw
test_record_confirmation_rejects_missing_status
test_record_confirmation_rejects_non_issued_status
test_record_confirmation_rejects_missing_issued_at
test_record_confirmation_column_and_json_status_never_diverge
test_dur1_cas_invariant_violation_returns_governed_denial_not_raw_exception
test_expiry_checked_after_lock_acquired_not_before_the_wait_for_it
test_lock_acquisition_timeout_returns_governed_denial_not_raw_exception
test_operational_error_inside_locked_transaction_returns_governed_denial_not_raw_exception
test_db_rejects_out_of_vocabulary_confirmation_status_at_insert
test_db_rejects_out_of_vocabulary_confirmation_status_at_update
test_db_rejects_update_of_an_operations_row
test_db_rejects_delete_of_an_operations_row
test_record_confirmation_lock_acquisition_timeout_raises_bounded_error_not_raw
test_record_confirmation_lock_contention_inside_transaction_raises_bounded_error_not_raw
```
This file is entirely about the confirmation/replay/idempotency-key layer (P2's
`operator_operation_service.py`), not "cancel"/"resume" lifecycle at all — those live in
`tests/unit/test_operator_mcp_adapter_job_lifecycle.py` (`test_job_cancel_*`,
`test_job_resume_*`), and "exact retry" / "duplicate" coverage lives in the P3 adapters
(`test_exact_retry_does_not_duplicate_import_receipt`,
`test_invoke_extract_exact_retry_does_not_reexecute`,
`test_invoke_claim_map_exact_retry_does_not_reexecute`,
`test_invoke_synthesize_exact_retry_does_not_reexecute`). Confirmed by grepping every operator
file for `def test_.*retry|cancel|resume|duplicate`: every adapter file and
`test_operator_mcp_policy.py` matches; `test_operator_operation_service.py` is the **one** file
in the whole operator surface with zero matches.

**Verdict: VACUOUS.** The command names the one file that cannot possibly prove the row's
claim by its own test names, and the filter is a hard 0/33. The row's evidence claim
("Exact retry yields prior state; no duplicate card/claim/receipt/candidate") is real and IS
tested — just in different files. **Expected but absent from this command:** every
`*_exact_retry_*`/`*_does_not_duplicate_*`/`test_job_cancel_*`/`test_job_resume_*` test named
above. Recommend repointing this row at the adapter files (or at minimum
`tests/unit/test_operator_mcp_adapter_job_lifecycle.py` for cancel/resume plus a `-k` term that
actually matches `exact_retry`/`does_not_duplicate` in the adapter files) rather than
`test_operator_operation_service.py`.

---

## Row: M2 — exact tool inventory

**Command:** `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py -q -k "inventory or introspect or overlap"`

**Exists-check:** file exists.

**Real output:**
```
2/38 tests collected (36 deselected) in 0.52s
```
Selected: `test_exact_14_tool_inventory`, `test_zero_overlap_with_knowledge_mcp_tool_names`.

**Verdict: SOUND — matches the plan's own documented state exactly.** This is the row the
plan already flags as VAL-1 (M2 validator gate): without `overlap` the filter would collapse to
1/38 and silently drop the zero-overlap proof. With `overlap` present, 2/38 is correct and
proves both halves of the row's claim. Independently reproduced: **2 passed** as documented.

---

## Row: M2 — preview cannot execute

**Command:** `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py -q`

**Exists-check:** file exists. **Collect count:** 4 (no `-k` filter):
```
test_preview_full_matrix_staged_zero_client_calls_with_content_assertions
test_preview_degraded_path_zero_client_calls
test_preview_missing_bundle_zero_client_calls_zero_files
test_preview_review_required_denial_zero_client_calls
```
**Run:** `4 passed` (`....`, 100%).

**Verdict: SOUND.** Names describe exactly the zero-effect claim; all 4 pass.

---

## Row: M2 — optional-SDK behavior

**Command:** `./.venv/bin/python -c "import sys; sys.modules['mcp']=None; import research_foundry; print('base ok')"` then `./.venv/bin/rf --help`

**Real output:**
```
base ok   (exit 0)
rf --help exit=0   (full Typer help text rendered, including term-index command)
```

**Verdict: SOUND.** Both halves pass as documented.

---

## Row: AC OPM-1 — confirmation binding

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q -k "confirm or replay or expiry or drift"`

**Exists-check:** file exists.

**Real output:**
```
32/131 tests collected (99 deselected) in 0.07s
```
(full 32-name list captured during the run — includes `test_verify_confirmation_expired_token`,
`test_exact_replay_after_consumption_is_not_an_error_but_is_non_accepting`,
`test_verify_confirmation_mismatched_bound_field_denies[...]` ×7 parametrizations,
`test_consume_confirmation_*` ×5, `test_mint_confirmation_*` ×7, etc.)

**Dead-term check:** isolating `-k "drift"` alone against the same file selects **0** tests
(`no tests collected (131 deselected)`), and `-k "confirm or replay or expiry"` (drift removed)
selects the identical 32/131. `drift` contributes nothing to the union — it is inert, exactly
the "extra term casts no net but reads as coverage" shape, inverse of VAL-1 (there the missing
term silently dropped tests; here a present-but-dead term implies a "drift" case is
purpose-tested when no test is named for it by that word). Semantic drift coverage does exist
under a different name — `test_verify_confirmation_mismatched_bound_field_denies
[policy_snapshot_version]` is a policy-snapshot-drift case — so the AC's substance is covered,
but the row's `-k` term list overstates what "drift" itself buys.

**Verdict: SOUND (substance), MINOR-NOISE (mechanics).** All 32 selected tests are real
adversarial confirmation cases with explicit zero-manifest/zero-effect assertions in their
names/bodies. Flag the dead `drift` term for cleanup, not correctness.

---

## Row: AC OPM-2 — workspace/sensitivity ⚠️ FILE MISSING

**Command:** `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py -q`

**Exists-check:**
```
$ ls tests/integration/test_operator_mcp_workspace_isolation.py
ls: tests/integration/test_operator_mcp_workspace_isolation.py: No such file or directory
```
**Confirmed missing**, per the task brief's prior knowledge. `rg`/`ls` on this path exits
non-zero (an actual pytest invocation would fail to collect at all — this is a harder failure
mode than the silent-pass "missing path reads as zero matches" hazard the M1 row already
warns about for `rg`, since pytest errors loudly on a missing file argument rather than
returning 0 matches).

**Nearest-equivalent coverage today** (grepped for `wrong_workspace`/`cross_workspace`/
`workspace` test names across every operator-mcp-specific test file):

| File | Relevant node names |
|---|---|
| `tests/unit/test_operator_mcp_adapter_job_lifecycle.py` | `test_job_status_wrong_workspace_indistinguishable_from_missing`, `test_job_cancel_wrong_workspace_indistinguishable_from_missing_dry_run`, `test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run`, `test_missing_operation_denies_via_h3_gate_not_a_fabricated_workspace_match` |
| `tests/unit/test_operator_mcp_adapter_external_import.py` | `test_invoke_denies_above_ceiling_for_cross_workspace_target`, `test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id`, `test_invoke_denies_packet_dir_outside_workspace_tree`, `test_invoke_allows_packet_dir_inside_workspace_tree`, `test_resolve_run_workspace_id_denies_traversal_before_read` |
| `tests/unit/test_operator_mcp_adapter_source_ingest.py` | `test_non_default_identity_workspace_threads_through_to_ingest_source`, `test_invoke_denies_local_locator_outside_workspace_tree`, `test_invoke_allows_local_locator_inside_workspace_tree`, `test_invoke_never_reads_cwd_relative_canary_after_chdir_outside_workspace` |
| `tests/unit/test_operator_mcp_policy.py` | `test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape`, `test_matching_resolved_target_workspace_is_not_denied`, `test_context_rejects_target_count_mismatch_with_resolved_workspaces` |

**Verdict: MISSING, but not zero-coverage.** The AC's substance (wrong-workspace lookups
returning safe non-existence, no cross-workspace leak) is exercised **per-adapter, at unit
level, with mocked services** — 4 files, ~12 relevant node names. What is genuinely absent is
the row's specific claim: a **two-identity integration matrix** exercised across the real
assembled MCP server surface (the way `test_operator_mcp_server.py` exercises transport/error
bounds end-to-end). The fragmented unit coverage does not substitute for that — it proves each
adapter individually denies a wrong workspace, not that the live server, given two real
configured identities, can never leak a cross-workspace derived detail through the full
preflight→invoke path.

---

## Row: AC OPM-3 — idempotent/cancel/resume

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q` (whole file, no `-k`)

**Collect count:** 33 (same file as the broken M1 row above, but run unfiltered here).

**Verdict: SOUND.** Because this row has no `-k` filter, it runs the whole file and is
unaffected by the retry/cancel/resume/duplicate dead-filter problem that breaks the M1 row
above — the H3 ten-scenario matrix (confirmation replay, idempotency-key conflict, concurrent
consumers, real-OS-process race) is genuinely exercised. This makes the M1 row's choice to
add a doomed `-k` filter on top of the exact same file even more clearly a self-inflicted
defect rather than a file-selection problem.

---

## Row: AC OPM-4 — closed adapters

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q` + handler call-path scan

**Verdict: SOUND.** Same 150-test collection as the M1 parity row (see above — same nuance on
which 6/9 files carry an explicit direct-service-comparison test). The "handler call-path
scan" is not given its own literal command in the matrix; it resolves to the same `rg` scan
already verified SOUND above (zero live-code matches for `typer|cli_commands|subprocess|
os\.system|shell=True` in both `operator_mcp_adapters/` and `operator_mcp/`).

---

## Row: AC OPM-5 — import/stage seams

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q -k "import or stage or prerequisite"`

**Real output:**
```
46/150 tests collected (104 deselected)
```

**Verdict: SOUND but noisy.** The selection genuinely includes the load-bearing tests for this
AC's claim: `test_invoke_bundle_raises_when_build_bundle_reports_unverified_despite_passing_
prerequisite` (verify-failure blocks bundle), `test_invoke_claim_map_denies_preflight_failed_
when_no_extraction_cards`, `test_invoke_synthesize_denies_preflight_failed_when_no_claim_
ledger`, `test_invoke_extract_denies_preflight_failed_when_no_source_cards`,
`test_invoke_claim_map_denies_preflight_failed_for_unauthorized_caller_without_leaking_
prerequisite_state` — all present. But `stage` is a very broad substring: it also pulls in
~18 unrelated `*_h7_guard_stage_indistinguishable_from_missing_*` sensitivity-ceiling tests
(matched on the literal word "stage" inside "guard_stage", not the research-stage concept the
AC means) across every adapter file. This dilutes the row's signal-to-noise but does not drop
anything — the term is over-inclusive, not under-inclusive, so it is not vacuous, just imprecise.

---

## Row: AC OPM-6 — preview-only

**Command:** `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py -q` + call-path scan

**Verdict: SOUND.** Identical to the M2 "preview cannot execute" row (4/4 passing, see above).
The "call-path scan" again resolves to the same verified-SOUND `rg` scan.

---

## Row: AC OPM-7 — bounded transport ⚠️ INCOMPLETE

**Command:** `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py -q -k "limit or error or redact"`

**Real output:**
```
4/38 tests collected (34 deselected) in 0.56s
```
Selected: `test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error`,
`test_transport_size_check_exception_maps_to_internal_error_not_uncaught`,
`test_internal_error_envelope_for_genuine_adapter_exception`,
`test_preflight_mint_is_rate_limited_per_workspace_with_zero_effect_on_throttle`.

**What the filter misses in its own file** — confirmed by direct check:
```
$ ... -k "limit or error or redact" --collect-only | grep -c oversized
0
```
`test_oversized_payload_maps_to_payload_too_large_envelope` — the file's primary oversize-
payload envelope test — matches none of `limit`/`error`/`redact` and is silently dropped.
`test_reserved_input_payload_key_maps_to_payload_too_large_envelope` and
`test_di_only_input_payload_keys_are_rejected_before_reaching_the_adapter` are dropped too.

**What the row claims but the named file cannot prove at all** — the evidence column says
"Oversize/internal-error/**wrong-workspace**-all return bounded redacted envelopes," but:
```
$ grep -c "wrong_workspace" tests/integration/test_operator_mcp_server.py
0
```
There is no wrong-workspace test in `test_operator_mcp_server.py` full-stop — that coverage
lives in `test_operator_mcp_adapter_job_lifecycle.py` (see the OPM-2 row above). The command as
written cannot evidence one-third of its own claim regardless of the `-k` filter.

Also worth noting: `redact` matches zero test names in this file (`grep -in redact` on the
`def test_` lines returns nothing) — a second dead term, same shape as `drift` in the OPM-1 row.

**Verdict: INCOMPLETE.** Not zero-selected like the M1 row, but two real problems stack: (1)
the filter drops the file's own primary oversized-payload test, and (2) the row's
"wrong-workspace" claim is not testable from this file at all — it needs a second command
against the adapter/job-lifecycle file, the same way OPM-4 needed its own adapter-file command.
**Expected but absent:** `test_oversized_payload_maps_to_payload_too_large_envelope`,
`test_reserved_input_payload_key_maps_to_payload_too_large_envelope`, and a companion command
against `tests/unit/test_operator_mcp_adapter_job_lifecycle.py -k wrong_workspace`.

---

## Row: Whole-suite regression

**Command:** `./.venv/bin/python -m pytest`

Run in background (the full suite takes several minutes on this tree); result appended below
once it completed — see **Full-suite run** subsection at the end of this document for the
literal captured output and pass/fail/skip counts, compared against the plan's documented
baseline (4258 passing pre-operator-mcp, 4410+ with the operator surface added, "same 16
known-failing nodes, none on the operator surface").

## Row: Lint gate ⚠️ COMMAND NOT RUNNABLE AS WRITTEN

**Command:** `flake8 src/research_foundry --select=E9,F63,F7,F82`

**Real output:**
```
$ ./.venv/bin/python -m flake8 src/research_foundry --select=E9,F63,F7,F82
/.../.venv/bin/python: No module named flake8
```
`flake8` is not installed in the project venv and is not a project dependency —
`pyproject.toml`'s dev deps list `ruff>=0.6` only (`grep -n "flake8" pyproject.toml` → 0 hits
outside the `[tool.ruff.lint.flake8-bugbear]` config-section name). The command as literally
written in the matrix cannot be executed through `./.venv/bin/python`, the exact execution
mode the matrix's own preamble mandates ("Run from the repo root with the project venv").

Falling back to the global pyenv-shim `flake8` (`/Users/miethe/.pyenv/shims/flake8`, v7.3.0) —
the same shim the matrix's own Field Notes warn is unsafe for pytest because it cannot import
`research_foundry` — happens to work here only because `--select=E9,F63,F7,F82` is a pure
AST/syntax check that never imports the target package:
```
$ /Users/miethe/.pyenv/shims/flake8 src/research_foundry --select=E9,F63,F7,F82
(zero output, exit 0)
```
**Verdict: INCOMPLETE / DOCUMENTATION GAP.** The lint-gate result itself is a genuine pass (0
E9/F63/F7/F82 violations), but the command as written is not executable via the mandated
project-venv path, and the only way to run it at all requires the pyenv shim the plan's own
Field Notes flag as a trap for a different tool. The row should either add `flake8` to project
dev deps, or explicitly state (as it does for pytest) that the shim is safe for this
particular flake8 invocation because it performs no import.

---

## Receipt schema property coverage (`schemas/operator_mcp_receipt.schema.yaml`)

**Command:** `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py --collect-only -q`

**Collect count:** 98 tests (no `-k` filter; whole file).

The file covers four schemas (confirmation, operation, **receipt**, error) in one module.
Mapping every `operator_mcp_receipt` `$def` property to its test coverage (verified by reading
both the schema file and the test bodies, not just grepping test names):

| `$def` | Property | Negative-test coverage | Status |
|---|---|---|---|
| `audit_delivery` | `status` (enum) | `test_audit_delivery_builder_rejects_unknown_status_and_overlong_event_id` | covered |
| `audit_delivery` | `audit_event_id` (not:pattern) | `test_audit_delivery_audit_event_id_rejects_absolute_filesystem_path`, `..._rejects_raw_traceback`, `..._null_still_passes`, `..._genuine_uuid_passes`, `test_audit_delivery_builder_redacts_path_shaped_audit_event_id` | covered |
| `audit_delivery` | `detail` (not:pattern, closed vocab) | `test_audit_delivery_detail_rejects_a_raw_traceback`, `..._site_packages_path`, `..._absolute_filesystem_path`, `test_audit_delivery_builder_rejects_unknown_detail_code`, `test_audit_delivery_builder_never_leaks_exception_derived_content` | covered |
| `operation_receipt` | `schema_version` (const) | none | **NO NEGATIVE TEST** |
| `operation_receipt` | `kind` (const) | `test_receipt_rejects_unknown_kind_discriminator`, `test_receipt_rejects_missing_kind_discriminator` (generic, cross-kind) | covered |
| `operation_receipt` | `operation_id` (pattern) | `test_receipt_operation_receipt_operation_id_rejects_malformed_value` | covered |
| `operation_receipt` | `workspace_id` (not:pattern) | `test_receipt_operation_receipt_workspace_id_rejects_path_shaped_value` | covered |
| `operation_receipt` | `operation_kind` (enum) | `test_receipt_operation_receipt_operation_kind_rejects_unknown_value` | covered |
| `operation_receipt` | `status` (enum) | `test_receipt_operation_receipt_status_rejects_unknown_value` | covered |
| `operation_receipt` | `idempotency_key` (pattern) | `test_receipt_operation_receipt_idempotency_key_rejects_path_shaped_value`, `..._rejects_traceback_shaped_value`, `..._golden_value_passes`, `..._matches_operation_schema_pattern` | covered |
| `operation_receipt` | `canonical_input_digest` (pattern) | none (only appears as a fixture value at L112/L230) | **NO NEGATIVE TEST** |
| `operation_receipt` | `generated_at` (format date-time) | none — **documented, deliberate exemption** (see below) | exempted (documented) |
| `operation_receipt` | `denial_reason_code` (enum + allOf) | `test_receipt_operation_receipt_denied_requires_reason_code_key_to_be_present`, `..._denied_with_null_reason_code_rejected`, `..._denied_with_reason_code_passes`, `..._accepted_forbids_reason_code`, `..._accepted_with_absent_reason_code_still_passes`, `..._accepted_with_null_reason_code_passes`, `..._every_closed_reason_code_is_accepted` | covered (thoroughly) |
| `operation_receipt` | `additionalProperties: false` | `test_receipt_rejects_additional_properties` (this test only, targets `operation_receipt` specifically) | covered (for this `$def` only — see gap below) |
| `action_receipt` | `schema_version` | none | **NO NEGATIVE TEST** |
| `action_receipt` | `operation_id` (pattern) | `test_receipt_action_receipt_operation_id_rejects_malformed_value` | covered |
| `action_receipt` | `action_id` (not:pattern) | `test_receipt_action_receipt_action_id_rejects_path_shaped_value` | covered |
| `action_receipt` | `action_index` (integer, min 0) | none (only a fixture value at L251) | **NO NEGATIVE TEST** |
| `action_receipt` | `status` (enum) | `test_receipt_action_receipt_status_rejects_unknown_value` | covered |
| `action_receipt` | `attempt_ref` (not:pattern) | `test_receipt_action_receipt_attempt_ref_rejects_path_shaped_value` | covered |
| `action_receipt` | `started_at`/`completed_at` (date-time) | none — documented exemption | exempted (documented) |
| `action_receipt` | `reason_code` (enum + allOf) | `test_receipt_action_receipt_with_closed_reason_code_passes`, `test_receipt_action_reason_code_rejects_value_outside_closed_enum`, `..._rejects_near_miss_of_a_real_code`, `..._failed_requires_reason_code_key_to_be_present`, `..._skipped_requires_reason_code_key_to_be_present`, `..._failed_with_null_reason_code_rejected`, `..._failed_with_reason_code_passes`, `..._completed_forbids_reason_code`, `..._completed_with_absent_reason_code_still_passes`, `..._completed_with_null_reason_code_passes` | covered (thoroughly) |
| `action_receipt` | `retryable` (boolean) | none (only a fixture value at L958) | **NO NEGATIVE TEST** |
| `effect_receipt` | `schema_version` | none | **NO NEGATIVE TEST** |
| `effect_receipt` | `operation_id` (pattern) | `test_receipt_effect_receipt_operation_id_rejects_malformed_value` | covered |
| `effect_receipt` | `action_id` (not:pattern) | `test_receipt_effect_receipt_action_id_rejects_path_shaped_value` | covered |
| `effect_receipt` | `effect_kind` (pattern, snake_case) | `test_receipt_effect_kind_rejects_non_snake_case` | covered |
| `effect_receipt` | `effect_digest` (pattern sha256-hex) | none (fixture value only, `_SHA` constant) | **NO NEGATIVE TEST** |
| `effect_receipt` | `effect_ref` (pattern) | none (fixture value only) | **NO NEGATIVE TEST** |
| `effect_receipt` | `generated_at` (date-time) | none — documented exemption | exempted (documented) |
| `checkpoint` | `schema_version` | none | **NO NEGATIVE TEST** |
| `checkpoint` | `operation_id` (pattern) | `test_receipt_checkpoint_operation_id_rejects_malformed_value` | covered |
| `checkpoint` | `workspace_id` (not:pattern) | `test_receipt_checkpoint_workspace_id_rejects_path_shaped_value` | covered |
| `checkpoint` | `status` (enum) | `test_receipt_checkpoint_status_rejects_unknown_value` | covered |
| `checkpoint` | `next_action_index` (allOf coupling) | `test_receipt_checkpoint_pending_with_null_next_action_index_rejected`, `..._pending_with_non_null_next_action_index_passes`, `..._converged_requires_null_next_action_index`, `..._converged_with_null_next_action_passes` | covered |
| `checkpoint` | `completed_action_count`/`total_action_count` (integer, min 0) | none (fixture values only) | **NO NEGATIVE TEST** |
| `checkpoint` | `non_cancelable` (boolean, one-way coupling) | `test_receipt_checkpoint_converged_rejects_non_cancelable_true` (only the `converged`→must-be-false direction; `pending` + arbitrary `non_cancelable` untested, but schema doesn't constrain that direction either) | partially covered |
| `checkpoint` | `updated_at` (date-time) | none — documented exemption | exempted (documented) |
| `terminal_receipt` | `schema_version` | none | **NO NEGATIVE TEST** |
| `terminal_receipt` | `operation_id` (pattern) | `test_receipt_terminal_receipt_operation_id_rejects_malformed_value` | covered |
| `terminal_receipt` | `workspace_id` (not:pattern) | `test_receipt_terminal_receipt_workspace_id_rejects_path_shaped_value` | covered |
| `terminal_receipt` | `operation_kind` (enum) | `test_receipt_terminal_receipt_operation_kind_rejects_unknown_value` | covered |
| `terminal_receipt` | `status` (enum) | `test_receipt_terminal_receipt_status_rejects_unknown_value` | covered |
| `terminal_receipt` | `effect_receipt_refs` (array, maxItems 200, item pattern) | none (fixture value `[]` only) | **NO NEGATIVE TEST** |
| `terminal_receipt` | `action_count_total`/`action_count_completed` (integer, min 0) | none (fixture values only) | **NO NEGATIVE TEST** |
| `terminal_receipt` | `denial_reason_code` (enum + allOf) | `test_receipt_terminal_denied_requires_reason_code`, `..._requires_reason_code_key_to_be_present`, `..._with_reason_code_passes`, `test_receipt_terminal_completed_forbids_reason_code`, `test_receipt_denial_reason_code_rejects_value_outside_closed_enum`, `..._rejects_near_miss_of_a_real_code`, `..._enum_matches_code_closed_reason_codes`, `test_receipt_every_closed_reason_code_is_accepted` | covered (thoroughly) |
| `terminal_receipt` | `audit_delivery` (`$ref`) | covered transitively via `audit_delivery` rows above | covered |
| `terminal_receipt` | `completed_at` (date-time) | none — documented exemption | exempted (documented) |

**Two categories of gap, and they are not equivalent:**

1. **Documented, rational exemption — date-time fields** (`generated_at`, `started_at`,
   `completed_at`, `updated_at` across all five `$def`s). The test file itself explains why at
   L763-775 (comment tag `P2R-NB-3`): `jsonschema.Draft202012Validator` is used without a
   `FormatChecker` attached anywhere in this repo (`_errors()` in this file, and
   `research_foundry.schemas.SchemaRegistry.validate`), confirmed by grep returning zero hits
   for `format_checker|FormatChecker`. `format: date-time` is therefore annotation-only today —
   a malformed value validates regardless of the schema's content, so a negative fixture here
   would assert behavior the validator cannot currently provide. This is called out honestly in
   the test file as a real residual risk, not silently absent.

2. **Undocumented gaps — no equivalent rationale exists for these:**
   - `schema_version` (const `"1.0"`) — untested across **all five** `$def`s. A receipt with
     `schema_version: "2.0"` (or a missing one, if `required` were violated) has no test proving
     rejection.
   - `canonical_input_digest`, `effect_digest`, `effect_ref` — pattern-anchored fields
     (sha256-hex / opaque-ref regex) with zero negative fixtures; only ever populated with a
     valid fixture value.
   - `action_index`, `completed_action_count`, `total_action_count`, `action_count_total`,
     `action_count_completed` — every `integer, minimum: 0` field in the schema is untested for
     a negative value or wrong type.
   - `retryable` (boolean) — untested entirely; no fixture ever sets it to a non-boolean.
   - `effect_receipt_refs` (array, `maxItems: 200`, item-pattern) — untested for oversized array
     or a malformed item hash; only ever populated as `[]`.
   - **`additionalProperties: false` is verified for `operation_receipt` only** —
     `test_receipt_rejects_additional_properties` adds `unexpected_field` to an
     `operation_receipt` instance exclusively. `action_receipt`, `effect_receipt`, `checkpoint`,
     and `terminal_receipt` have no equivalent test, despite each `$def` independently declaring
     `additionalProperties: false`.

---

## Gaps summary

**VACUOUS:**
- **M1 — retry/cancel idempotency.** `-k "retry or cancel or resume or duplicate"` against
  `tests/unit/test_operator_operation_service.py` selects **0/33** tests. The named file has no
  test containing any of the four terms; the AC's real evidence lives in
  `test_operator_mcp_adapter_job_lifecycle.py` (cancel/resume) and the P3 adapter files' `*_exact_retry_*`/`*_does_not_duplicate_*` tests. This row currently proves nothing.

**INCOMPLETE:**
- **AC OPM-7 — bounded transport.** `-k "limit or error or redact"` drops the file's own
  `test_oversized_payload_maps_to_payload_too_large_envelope` and two sibling oversize tests
  (4/38 selected, but missing the primary oversize case), and the row's "wrong-workspace" claim
  cannot be evidenced from `test_operator_mcp_server.py` at all — 0 wrong-workspace tests exist
  in that file; that coverage is in the job-lifecycle adapter file instead.
- **AC OPM-2 — workspace/sensitivity.** `tests/integration/test_operator_mcp_workspace_
  isolation.py` does not exist. Nearest-equivalent coverage is fragmented across 4 unit-level
  adapter/policy files (~12 relevant node names, listed above) with mocked services — real but
  not the row's claimed two-identity integration matrix against the assembled server.
- **Lint gate.** `flake8` is not installed in the project venv (`pyproject.toml` only lists
  `ruff`); the command as written cannot run via `./.venv/bin/python`. Passes (0 violations)
  only via the global pyenv shim, which the matrix's own Field Notes flag as unsafe for a
  different reason (pytest import failures) — that caveat doesn't obviously transfer, but the
  matrix doesn't say so.
- **Whole-suite regression.** Not reproducible cleanly this session: 23 FAILED nodes surfaced
  (vs. the documented 16-node baseline), including one on the operator surface
  (`test_operator_mcp_adapter_job_lifecycle.py::test_job_cancel_wrong_workspace_
  indistinguishable_from_missing_dry_run`) that passes cleanly when re-run in isolation. A
  concurrent sibling agent was actively running pytest in this same worktree throughout
  (confirmed via `ps aux`), alongside 94% system swap usage — the known "second agent in the
  same worktree" contention hazard. The run never printed a final pass/fail summary line
  (process gone, log truncated after the FAILED list). This row needs a single-tenant re-run
  before its "4410+ passing, same 16 failing, none on operator surface" claim can be trusted.

**Dead/noisy filter terms (not vacuous, but overstate or understate what they buy):**
- `drift` in the OPM-1 confirmation-binding row: 0 tests match it standalone; contributes
  nothing to the 32/131 union. Semantic drift coverage exists under
  `..._mismatched_bound_field_denies[policy_snapshot_version]` instead.
- `redact` in the OPM-7 row: 0 test names in `test_operator_mcp_server.py` match it.
- `stage` in the OPM-5 import/stage-seams row: over-broad — pulls in ~18 unrelated
  `*_h7_guard_stage_indistinguishable_from_missing_*` sensitivity-ceiling tests alongside the
  genuine research-stage tests. Not vacuous (nothing needed is dropped), just noisy.

**Receipt-schema properties with no negative test** (from the table above, excluding the
documented date-time exemption): `schema_version` (all 5 `$def`s), `canonical_input_digest`,
`effect_digest`, `effect_ref`, `action_index`, `completed_action_count`, `total_action_count`,
`action_count_total`, `action_count_completed`, `retryable`, `effect_receipt_refs`, and
`additionalProperties: false` for `action_receipt`/`effect_receipt`/`checkpoint`/
`terminal_receipt` (verified only for `operation_receipt`).

**Confirmed missing file (task item 4):** `tests/integration/test_operator_mcp_workspace_
isolation.py` does not exist on disk. See the OPM-2 row above for nearest-equivalent coverage.

---

## Full-suite run (Row: Whole-suite regression) ⚠️ COULD NOT CLEANLY REPRODUCE

**Command:** `./.venv/bin/python -m pytest` from repo root, `./.venv/bin/python`. Run in the
background because of runtime (real terminal output below, not a self-report — this is not a
"trust the agent" claim, it is the literal captured stream, including its incomplete ending).

**Environmental confound, observed and worth reporting rather than hiding:** while this ran,
`ps aux` showed a second/third concurrent process actively running pytest inside this exact
same worktree (`./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q`, PID
14086, plus a lock-guarded `test_operator_mcp_policy.py` run queued behind
`/tmp/opm-m3-pytest.lock`, plus a concurrent `artifact-tracking` test run) — almost certainly
sibling Leg A/B agents from this same M3 fan-out. `sysctl vm.swapusage` read **17.4 GB of 18.4
GB swap used (94%)** during the run. This is the exact "concurrency hazard: a second agent in
the same worktree" trap flagged in prior-session memory for this workstream.

**Real captured output:** the log grew to 730 lines then stopped — no closing
`N passed, M failed ... in Xs` summary line ever appeared, and the background process (PID
69506) was gone by the time I checked. The last thing written was the `short test summary
info` FAILED list (23 entries, unanchored-`FAILED` grep per the Field Notes ANSI trap — real
matches, not a stale/colored false negative):

```
FAILED tests/test_cli_rights.py::test_rights_validate_requires_as_of
FAILED tests/test_contract_drift_rf_schema_version.py::test_cli_json_dumps_sites_fully_accounted_for
FAILED tests/test_contract_drift_rf_schema_version.py::test_cli_json_dumps_site_counts_match_pinned_baseline
FAILED tests/test_deployment_mode_cli_and_app.py::TestServeModeFlag::test_mode_multi_user_without_provider_refuses_before_binding
FAILED tests/test_pdf_extractor.py::test_extract_pdf_with_text_layer_returns_full_text
FAILED tests/test_pdf_extractor.py::test_extract_pdf_without_text_layer_returns_locator_only
FAILED tests/test_pdf_extractor.py::test_extract_pdf_corrupted_input_returns_locator_only_without_raising
FAILED tests/test_pdf_fixture_suite.py::test_pdf_with_text_layer_surfaces_full_text_end_to_end
FAILED tests/test_pediatric_cds_redteam_fixtures.py::test_seven_verified_bundles_zero_false_positives
FAILED tests/test_search_router_pdf_wiring.py::test_pdf_url_with_text_layer_is_not_degraded
FAILED tests/test_serve_api.py::test_get_run_detail_known_run_returns_200
FAILED tests/test_serve_api.py::test_get_claims_non_empty
FAILED tests/test_serve_api.py::test_get_claims_empty_ledger_returns_empty_list
FAILED tests/test_serve_api.py::test_get_source_found
FAILED tests/test_serve_api.py::test_sensitivity_gate_parity_work_sensitive_claim
FAILED tests/test_swarm_drive.py::test_cli_drive_json_output
FAILED tests/test_swarm_drive.py::test_cli_drive_ica_json
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_zero_eligible_claims
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_exact_passage_present_never_hard_gated_by_p3
FAILED tests/test_verification_seam001_gate_composition.py::test_seven_verified_bundles_pass_verify_report_with_all_three_gates_active
FAILED tests/unit/test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off
FAILED tests/unit/test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default
FAILED tests/unit/test_operator_mcp_adapter_job_lifecycle.py::test_job_cancel_wrong_workspace_indistinguishable_from_missing_dry_run
FAILED tests/unit/test_report_anchors.py::test_schema_version_bumped_for_report_anchors
```

That is **23** failures, above the documented "same 16 known-failing nodes" baseline, and one
of them — `tests/unit/test_operator_mcp_adapter_job_lifecycle.py::test_job_cancel_wrong_
workspace_indistinguishable_from_missing_dry_run` — is squarely **on the operator MCP
surface**, directly contradicting this row's "none on the operator surface" claim at face
value.

**Isolation re-test (the honest next step, not a self-report):** re-ran that one operator-
surface failure alone, with no contention:
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_job_lifecycle.py::test_job_cancel_wrong_workspace_indistinguishable_from_missing_dry_run -q
.                                                                        [100%]
```
**It passes cleanly in isolation.** Given 94% swap usage and multiple competing pytest
processes hitting SQLite-backed fixtures in the same worktree simultaneously, the most likely
explanation is a contention-induced flake (a lock-timeout or filesystem race under memory
pressure), not a real regression — but I am reporting the observed full-suite failure as-is
rather than silently substituting the clean isolated re-run, per the "never fabricate a
validation transcript" rule. The other 22 failures were not individually re-verified in
isolation in this pass; several look plausibly pre-existing/environmental on inspection
(`test_pdf_extractor.py`/`test_pdf_fixture_suite.py` reference a missing `pypdf` dependency;
`test_pediatric_cds_redteam_fixtures.py`/`test_verification_clinical_eligibility_regression.py`/
`test_verification_seam001_gate_composition.py` reference missing local fixture directories —
consistent with the plan's own note that these three depend on local corpus data this repo
doesn't ship), but that is an inference, not a verified fact, and is explicitly flagged as such.

**Verdict: NOT CLEANLY REPRODUCIBLE THIS SESSION — needs a single-tenant re-run.** The
row's literal command was executed and produced real output, but under observed heavy
cross-agent contention in the same worktree the run neither completed nor produced a trustworthy
"4410+ passing, same 16 failing, none on operator surface" result. The one operator-surface
failure it did surface does not reproduce in isolation. **This row cannot be marked SOUND from
this session's evidence** — it needs to be re-run with no sibling agent active in this
worktree, to completion, before its claim can be trusted either way.
