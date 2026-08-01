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

# M1 remainder, leg B — completion note

Scope: `external_report.import` and `source.ingest` adapters, per
`m1-remainder-implementer-contract.md`.

## What was built

- `src/research_foundry/services/operator_mcp_adapters/external_import.py` --
  `external_report.import` adapter wrapping
  `external_research_import.import_external_report`.
- `src/research_foundry/services/operator_mcp_adapters/source_ingest.py` --
  `source.ingest` adapter wrapping `source_cards.ingest_source`.
- `tests/unit/test_operator_mcp_adapter_external_import.py` (5 tests).
- `tests/unit/test_operator_mcp_adapter_source_ingest.py` (6 tests).

Both follow `run_plan.py`'s exact anatomy: `PolicyContext` construction ->
`ActionSpec`/closure -> `action_manifest` -> `build_result` -> hand all four
to `base.run_pipeline`. Neither `operator_mcp_adapters/__init__.py`,
`operator_mcp_adapters/base.py`, `operator_mcp_policy.py`,
`operator_operation_service.py`, `operator_cancel_resume_service.py`, any
canonical service, nor `cli_commands.py` was touched.

### D1 (sensitivity_ceiling resolved, never accepted)

Reproduced verbatim in both: no `sensitivity_ceiling` parameter; each
`invoke()` calls `resolve_local_sensitivity_ceiling(resolved_paths)` via the
same lazy `from . import resolve_local_sensitivity_ceiling` before
constructing `ctx`. Each adapter has its own H7 negative fixture
(`test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_target`
/ `..._missing_run`), each proving the above-ceiling denial and a
missing-target denial are byte-identical `operator_mcp_error` envelopes.

### D2 (`source.ingest` workspace binding)

`assertion_registry_workspace_id=ctx.identity.workspace_id` in
`source_ingest.py`'s `_run()` closure. The literal string this decision
names does not appear anywhere in the module (verified both by `grep -i` on
disk and by a source-level test,
`test_default_literal_absent_from_source_ingest_module`, which reads
`inspect.getsource(source_ingest)` and asserts the lowercased substring is
absent). A second test,
`test_non_default_identity_workspace_threads_through_to_ingest_source`,
spies on `source_cards.ingest_source` with a deliberately-not-the-CLI's-own
identity workspace (`"ws-not-the-cli-literal"`) and asserts the exact kwarg
value threaded through. `cli_commands.py:354` was read, confirmed unchanged,
and is not touched (CLI parity preserved).

### D3 (`external_report.import` -- one dry-run concept)

`invoke()`'s own `dry_run` is the only dry-run this adapter exposes; the
live-path call inside `_run()` always passes `dry_run=False` to
`import_external_report`. `resume` is forwarded as a separate parameter,
consulted only on the live path (proven by
`test_invoke_dry_run_never_calls_import_external_report`, which passes
`resume=True` alongside `dry_run=True` and asserts the wrapped service is
never called at all). `ImportOutcome.safe_dict()` (which already carries
`workspace_id`, `target_run_id`, `packet_digest`, `receipt_id`,
`receipt_digest`, `status`, plus `complete`/`replayed`/`dry_run`/
`block_reason`/`counts`/`cursor`) is returned as the bounded result,
superset over the six named refs.

## Defect-class checklist, applied to this leg's own work

1. **No fail-open defaults.** Verified: no `sensitivity_ceiling` param on
   either adapter; `effective_sensitivity` for `external_report.import` is
   ALWAYS `policy.resolve_effective_sensitivity()` with no arguments (the
   producer's own strictest-label fail-closed default -- there is no
   pre-existing object to read a real sensitivity signal from before a
   packet is inspected, and inspecting it ourselves would be a second,
   redundant `inspect_packet` call outside `import_external_report`'s
   single-inspection contract). `source.ingest`'s `effective_sensitivity`
   uses the caller-declared `sensitivity` kwarg (the only available signal,
   since the source card doesn't exist yet) fed through
   `resolve_effective_sensitivity`, which itself fails closed to the
   strictest label on any unrecognized value -- checked the *producer*
   (`resolve_effective_sensitivity`'s own `SENSITIVITY_ORDER` membership
   check), not merely the field.
2. **Fix the layer below / enumerate siblings.** Both new adapters import
   their wrapped SERVICE MODULE (`external_research_import`, `source_cards`)
   rather than importing the function name directly -- this was a real
   defect I caught and fixed in my own first draft: `from research_foundry.
   services.external_research_import import import_external_report` bound
   the function as a local name in the adapter module at import time, which
   would make it un-spy-able by any test (or future caller) that
   monkeypatches the SOURCE module's attribute, since the adapter's own
   bound reference would stay pointed at the original object. Fixed to
   `from research_foundry.services import external_research_import` (and
   the `source_cards` equivalent), calling `external_research_import.
   import_external_report(...)` by module attribute at call time -- the
   same convention `run_plan.py`/`swarm_start.py` use for `planning`/
   `swarm_service`.
3. **Never pin unsafe behavior with a test.** No test in either new file
   asserts a denial-leaking-existence-information shape or a fail-open
   default; every H7/H3 fixture asserts the CLOSED, no-leak envelope.
4. **Never fabricate a validation transcript.** Pytest output below is
   real, captured in this session.

## A contract decision I found genuinely underspecified (not wrong, just not written down)

Neither `m1-remainder-implementer-contract.md` nor the scoping/unknowns docs
address `_REQUIRED_TARGET_KINDS`: `external_report.import` requires an
`import_packet` target and `source.ingest` requires a `run` target
(`operator_mcp_policy.py:562-576`, traced during this leg, not in U1-U5).
Declaring these is mandatory -- omitting them denies every call with
`preflight_failed` regardless of anything else being correct -- and the
`resolved_target_workspaces` H3 cross-workspace gate that comes with a
declared target has real design consequences neither doc anticipated:

- For `source.ingest`, the target is the run itself, so I resolved its
  OWNING workspace from `run.yaml` (mirroring
  `swarm_start._resolve_run_context`'s identical field) rather than
  inventing anything new. Low-risk, clearly the intended shape.
- For `external_report.import`, there is no pre-existing object to resolve
  an owning workspace from -- the import is bringing NEW content into a
  workspace, not acting on one that already exists. I resolved this by
  treating the adapter's own `workspace_id` parameter (caller-supplied,
  mirroring the CLI's own required `--workspace` option, `cli_commands.py`'s
  `intake_external_report`) as the DECLARED target workspace, threaded
  as-is into `resolved_target_workspaces`. The actual enforcement is not
  this declaration -- it's `_check_identity_and_rbac`'s independent
  re-derivation of the real configured identity, which denies unless the
  caller's declared `workspace_id` matches it. I'm confident this is safe
  (it reduces to "you can only import into the one configured operator's
  own workspace," which is the correct single-tenant invariant for this
  phase), and I added a dedicated test
  (`test_invoke_denies_above_ceiling_for_cross_workspace_target`) proving a
  mismatched `workspace_id` denies. But this is a genuine design choice I
  made under the contract's silence, not a decision I found already written
  down -- worth a reviewer's eyes given it's the one place this leg
  introduces a caller-supplied value into an H3-gated field.

## What I could not do

Nothing was left undone within this leg's stated scope (the two adapters,
their four required test categories each, plus D1/D2/D3). The pre-existing
"replay result-recovery gap" (both new adapters report a bounded partial
result on exact-replay of an already-terminal operation, same as
`run_plan.py`/`swarm_start.py`) and `run.bundle`'s `writeback.py`
verify-block gap (D5, out of scope -- belongs to the `run.bundle` leg) are
not this leg's concern and were not touched.

## Real pytest output

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_external_import.py tests/unit/test_operator_mcp_adapter_source_ingest.py -v
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.13.0
collected 11 items

tests/unit/test_operator_mcp_adapter_external_import.py .....            [ 45%]
tests/unit/test_operator_mcp_adapter_source_ingest.py ......             [100%]

============================== 11 passed in 1.04s ==============================
```

Full family regression (existing P3 adapters + policy + the two new
modules), also green:

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_run_plan.py tests/unit/test_operator_mcp_adapter_swarm_start.py tests/unit/test_operator_mcp_adapter_job_lifecycle.py tests/unit/test_operator_mcp_adapter_base.py tests/unit/test_operator_mcp_adapter_external_import.py tests/unit/test_operator_mcp_adapter_source_ingest.py tests/unit/test_operator_mcp_policy.py -q
... (all dots, no F) ...
```

Full unit suite (`tests/unit`), confirming ONLY the three pre-existing
baseline failures the contract documented (none of them touched by this
leg, none introduced by it):

```
$ ./.venv/bin/python -m pytest tests/unit -q
...
=========================== short test summary info ============================
FAILED tests/unit/test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off - AssertionError: assert True is False
FAILED tests/unit/test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default - AssertionError: assert 'eligible' == 'automated_reuse_disabled'
FAILED tests/unit/test_report_anchors.py::test_schema_version_bumped_for_report_anchors - AssertionError: assert '1.8' == '1.4'
```

Also verified: `grep -n -i "default" src/research_foundry/services/operator_mcp_adapters/source_ingest.py` returns no matches (exit 1).
