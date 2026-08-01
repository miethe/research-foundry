---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: completed
created: '2026-07-31'
updated: '2026-07-31'
---

# Fix cycle 1 — M1 remainder pre-gate findings F2/F3/F4 (source.ingest, external_report.import)

Fixed three defects from `.claude/findings/m1-remainder-pregate-consolidated.md` in the two files
owned by this leg. All three have a regression test that was verified to FAIL on pre-fix code and
PASS on fixed code (real transcripts below, not fabricated).

## F3 — BLOCKING — `source.ingest` trusted caller-selected sensitivity

**What was wrong**: `source_ingest.py` derived `effective_sensitivity` (the value `_check_guard`
compares against `ctx.sensitivity_ceiling`) from the caller-supplied `sensitivity` parameter
(permissive default `"personal"`). A caller under a `public` ceiling could label sensitive content
`sensitivity="public"` and pass the ceiling guard on their own say-so.

**Fix**: Added `_RunContext`/`_resolve_run_context` (mirrors `swarm_start._resolve_run_context`'s
identical pattern) to read the target run's own `run.yaml` `sensitivity` field, read-only,
structurally, before authorization. `effective_sensitivity` is now
`policy.resolve_effective_sensitivity(run_ctx.sensitivity)` — the run's own governed sensitivity,
never the caller's claim. The caller-supplied `sensitivity` parameter is unchanged everywhere else
(still forwarded to `ingest_source` as the new source card's own content classification, still in
`input_payload`) — it is simply no longer what the ceiling guard evaluates. A missing/foreign run
resolves to `None`, which fails closed to the strictest label via `resolve_effective_sensitivity`'s
existing contract.

**Regression test**: `test_invoke_denies_caller_mislabeled_public_sensitivity_on_sensitive_run`
(`tests/unit/test_operator_mcp_adapter_source_ingest.py`). Real run planned with a `"personal"`
intent (so `run.yaml`'s own `sensitivity` is `"personal"`); local ceiling forced to `"public"`;
caller declares `sensitivity="public"` (a self-attested claim below the run's real level). Asserts
denial (`reason_code == "not_found"`, the H7 shape) purely from the run's own resolved sensitivity —
the caller's claim has no bearing.

Verified pre-fix failure directly for the sibling F4 test (below); this test's own pre-fix run
(confirmed separately by re-running against the stashed pre-fix `source_ingest.py`) returned
`ok=True` — the caller's `sensitivity="public"` passed the ceiling check on its own say-so, exactly
the defect described. Post-fix: `ok=False`.

## F4 — BLOCKING — confirmation did not bind ingested content

**What was wrong**: `content`, `extra_limitations`, and `created_by_agent` were omitted from the
canonical `input_payload` the confirmation digest covers, but all three were forwarded unchanged to
`ingest_source` in `_run()`. A confirmation minted for absent/benign content could therefore
authorize executing with arbitrary replacement content. The existing parity test
(`test_invoke_result_matches_direct_ingest_call`) minted its confirmation via `_basic_ctx` with NO
`content` field in the payload, then invoked WITH `content=_SAMPLE_CONTENT` and asserted success —
pinning the bypass.

**Fix**: `content` is bound in via a `sha256` digest (`content_digest`), never raw text — this
avoids re-litigating the module's own documented rationale for keeping free text out of the hashed
canonical payload (64KiB capability-stage gate; avoiding packet/content-derived text in a
potentially-logged structure). `extra_limitations` and `created_by_agent` (both short/bounded) are
included directly. All three are now part of `input_payload`, therefore part of
`canonical_digest()`. A confirmation minted for one `content` value cannot be replayed against a
different one: a mismatch now denies at the confirmation stage (`reason_code ==
"confirmation_mismatch"`) before `_run()` — and therefore `ingest_source` — is ever reached.

**Test inversion (defect class 3)**: `_basic_ctx` (the shared fixture-builder) was changed to accept
a `content` parameter and bind its digest, so `test_invoke_result_matches_direct_ingest_call` now
mints its confirmation WITH matching content — it is now a genuine parity test rather than a
pinned-bypass test. The three other call sites that use `_basic_ctx`
(`test_invoke_result_matches_direct_ingest_call`,
`test_exact_retry_does_not_duplicate_source_card`,
`test_non_default_identity_workspace_threads_through_to_ingest_source`) were updated to pass matching
`content` so their confirmations still bind correctly post-fix.

**Regression test**: `test_invoke_denies_when_confirmed_content_differs_from_supplied_content`
(new). Deliberately does NOT reuse the (now content-aware) `_basic_ctx` — it builds the confirmation
context inline, reproducing the EXACT pre-fix payload shape (no `content`/`created_by_agent`/
`extra_limitations` keys at all), then invokes with real content. A spy on `ingest_source` asserts it
is never reached with non-empty captured content.

**Verified fails pre-fix** (real transcript, `git stash` of only `source_ingest.py`, test file kept
at HEAD):

```
tests/unit/test_operator_mcp_adapter_source_ingest.py::test_invoke_denies_when_confirmed_content_differs_from_supplied_content
>       assert result.ok is False
E       AssertionError: assert True is False
E        +  where True = OperatorAdapterResult(ok=True, operation_id='opm_1e4479c0...', ...).ok
FAILED tests/unit/test_operator_mcp_adapter_source_ingest.py::test_invoke_denies_when_confirmed_content_differs_from_supplied_content
1 failed in 0.28s
```

Post-fix: `1 passed`.

## F2 — HIGH — `external_report.import` could mutate a foreign run via `target_run_id`

**What was wrong**: `workspace_id` was correctly re-derived and RBAC-checked (H3), but
`target_run_id` — a sibling, optional parameter naming a pre-existing run that
`import_external_report` records import activity against (`external_research_import.py:611`) — was
never authorized at all. A caller could supply their own matching `workspace_id` (passes H3) with a
`target_run_id` owned by a different workspace, and the canonical service would still record import
activity against that foreign run.

**Fix**: Added `_resolve_run_workspace_id` (same read-only, fail-closed-to-`None` pattern as
`source_ingest`/`swarm_start`). When `target_run_id` is supplied, a second `TargetRef("run",
target_run_id)` is appended to `targets`, and its resolved owning workspace is appended to
`resolved_target_workspaces` (1:1, matching `PolicyContext.__post_init__`'s length invariant).
`_check_identity_and_rbac`'s existing per-entry loop (untouched — it already denies if ANY resolved
workspace differs from identity's own) now independently authorizes both the packet's declared
workspace AND the target run's real owning workspace.

**Regression test**: `test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id`
(`tests/unit/test_operator_mcp_adapter_external_import.py`, new). Plans a real run under a
DIFFERENT identity/workspace (`ws-other`), then invokes with `workspace_id="ws-mine"` (matching,
passes H3 on its own) and `target_run_id` pointing at the foreign run. Asserts denial
(`reason_code == "not_found"`) and that `import_external_report` is never called.

**Verified fails pre-fix** (real transcript, `git stash` of only `external_import.py`):

```
tests/unit/test_operator_mcp_adapter_external_import.py::test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id
>       assert result.ok is False
E       AssertionError: assert True is False
E        +  where True = OperatorAdapterResult(ok=True, ..., result={'dry_run': True, 'operation_kind': 'external_report.import'}, error=None).ok
FAILED tests/unit/test_operator_mcp_adapter_external_import.py::test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id
```

Post-fix: `ok=False`, `reason_code == "not_found"`.

`test_invoke_denies_caller_mislabeled_public_sensitivity_on_sensitive_run` (F3) was also confirmed
to fail pre-fix in the same `git stash` pass over `source_ingest.py` (grouped run, see the
`2 failed, 1 passed` batch transcript — the "1 passed" in that batch was the F4 test before its
final rewrite to avoid the `_basic_ctx` scaffolding artifact described above; F4 was re-verified
standalone afterward as shown).

## Sibling-bypass sweep (defect-class checklist item 2)

Applied to my own fixes:

- **F3's sibling**: `source_ingest.py` has no OTHER caller-supplied classification field besides
  `sensitivity` that reaches a policy-evaluated gate — `source_type`, `title`, `fetch`,
  `extraction_status` are all either non-governed metadata or already bound into the canonical
  payload unchanged. No further fail-open field found.
- **F4's sibling**: enumerated every parameter `_run()` forwards to `ingest_source` — `locator`,
  `run_id`, `source_type`, `sensitivity`, `title`, `fetch`, `content`, `extra_limitations`,
  `assertion_registry_workspace_id` (identity-derived, not caller-bound), `extraction_status`. All
  caller-supplied ones besides `content`/`extra_limitations`/`created_by_agent` were already in
  `input_payload` before this fix; those three are now added. No remaining unbound forwarded input.
- **F2's sibling**: `external_import.py`'s `invoke()` has exactly two run/workspace-shaped
  parameters, `workspace_id` and `target_run_id` — both now authorized. `resume` is a boolean
  control flag with no ownership semantics (not a target reference), and `packet_dir` is already
  digested into the `import_packet` target ref. No further unauthorized sibling target found.

## Validation (real output)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_source_ingest.py tests/unit/test_operator_mcp_adapter_external_import.py -v -p no:cacheprovider
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
rootdir: .../operator-mcp-v1
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.13.0
collected 14 items

tests/unit/test_operator_mcp_adapter_source_ingest.py ........           [ 57%]
tests/unit/test_operator_mcp_adapter_external_import.py ......           [100%]

============================== 14 passed in 1.01s ==============================
```

14/14 passed (8 in source_ingest: 6 pre-existing + 2 new; 6 in external_import: 5 pre-existing + 1
new). No ANSI-hidden `FAILED` lines (checked via `-v` name-by-name listing, per the environment
note's warning).

## Files changed

- `src/research_foundry/services/operator_mcp_adapters/source_ingest.py` — F3, F4 fixes
- `src/research_foundry/services/operator_mcp_adapters/external_import.py` — F2 fix
- `tests/unit/test_operator_mcp_adapter_source_ingest.py` — inverted the F4-pinning assertion in
  `test_invoke_result_matches_direct_ingest_call`; added
  `test_invoke_denies_when_confirmed_content_differs_from_supplied_content` (F4) and
  `test_invoke_denies_caller_mislabeled_public_sensitivity_on_sensitive_run` (F3)
- `tests/unit/test_operator_mcp_adapter_external_import.py` — added
  `test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id` (F2)

No edits outside the four owned files. No hard boundaries touched
(`operator_mcp_policy.py`/`operator_operation_service.py`/`operator_cancel_resume_service.py`/
`operator_mcp_adapters/base.py`/`operator_mcp_adapters/__init__.py`/any canonical service/
`cli_commands.py`).
