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

# M1 remainder, Leg A — completion note (`run.extract` / `run.claim_map` / `run.synthesize`)

## What was built

Two new files only (per file-ownership boundary), nothing else touched:

- `src/research_foundry/services/operator_mcp_adapters/research_stages.py` — three adapters
  (`invoke_extract`, `invoke_claim_map`, `invoke_synthesize`) following `run_plan.py`'s exact
  shape (`PolicyContext` → `ActionSpec` → `action_manifest` → `build_result` → `base.run_pipeline`),
  each self-registering via `base.register(...)` at module import time (mirrors
  `job_lifecycle.py`'s multi-adapter-per-file convention, since `__init__.py` is off-limits).
- `tests/unit/test_operator_mcp_adapter_research_stages.py` — 12 tests, 4 per adapter: (a) the D6
  parity/spy check against the real canonical service, (b) dry-run zero-effects, (c) the D7
  exact-retry-does-not-reexecute check, (d) the D1/H7 above-ceiling-vs-missing-run indistinguishable-
  denial fixture.

Both adapters reproduce D1 verbatim: no `sensitivity_ceiling` parameter; resolved via
`resolve_local_sensitivity_ceiling(resolved_paths)` before `ctx` is built. Both reuse the
`_default_sensitivity_ceiling`/`_recording_ceiling` fixtures from `test_operator_mcp_adapter_run_plan.py`
and the `_default_operator_identity` autouse fixture from `test_operator_mcp_policy.py`, per D6.

## Real pytest output

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_research_stages.py -v --color=no
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.13.0
collected 12 items

tests/unit/test_operator_mcp_adapter_research_stages.py ............     [100%]

============================== 12 passed in 1.45s ==============================
```

Also ran the full `tests/unit/` suite afterward to check for collateral damage (not required by the
contract, done as a sanity check since a self-registering module changes global adapter-registry
state for the rest of the pytest process):

```
$ timeout 300 ./.venv/bin/python -m pytest tests/unit -q --color=no
...
FAILED tests/unit/test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off
FAILED tests/unit/test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default
FAILED tests/unit/test_report_anchors.py::test_schema_version_bumped_for_report_anchors
```

Exactly the 3 pre-existing baseline failures the contract's environment notes name — no new failures,
no regressions in `test_operator_mcp_adapter_run_plan.py` / `test_operator_mcp_adapter_swarm_start.py` /
`test_operator_mcp_adapter_job_lifecycle.py` / `test_operator_mcp_adapter_base.py` /
`test_operator_mcp_policy.py` (192 passed, run separately too).

`(venv note: this worktree had no `.venv` at session start — created it with `uv sync --extra dev
--extra serve` before running anything, per the environment notes' "run tests as `./.venv/bin/python
-m pytest`" instruction. This is `uv`'s normal lazy `.venv` creation, not a deviation.)`

## Contract decisions I found questionable / gaps the contract didn't cover

1. **A real gap in the scoping doc, not a design disagreement.** Neither
   `m1-remainder-implementer-contract.md` nor `m1-remainder-scoping.md` mentions that
   `operator_mcp_policy._REQUIRED_TARGET_KINDS` declares `run.claim_map` requires
   `{"run", "extraction_card"}` and `run.synthesize` requires `{"run", "claim_ledger"}` — TWO target
   kinds, not one, unlike `run.extract`'s `{"run"}` (the same single-target shape `swarm.start`
   uses). I traced `_check_preflight`/`_check_identity_and_rbac` myself: the preflight stage only
   checks that a `TargetRef` of each required KIND is present (never that the referenced artifact
   exists on disk); the rbac stage then requires one `resolved_target_workspaces` entry per target,
   denying `not_found` for any `None`/mismatched entry. Since neither `extraction_card` nor
   `claim_ledger` is individually addressable at invoke time (a run has a whole SET of extraction
   cards; exactly one claim-ledger singleton) and neither carries its own persisted owning-workspace
   field, I made a judgment call, documented in the module docstring: use `run_id` itself as the
   `target_ref` for the secondary kind, and resolve its owning workspace to the SAME
   `run_ctx.workspace_id` the `"run"` target resolves to. This is a real design decision the
   contract didn't pre-decide — please have the integration owner (or a reviewer) sanity-check it
   before treating it as settled; it doesn't touch any file outside my ownership, but it's new
   reasoning, not a reproduction of an existing pattern.

2. **`run.synthesize`'s own `sensitivity` parameter is a name collision worth a second look.**
   `synthesis.synthesize_report(sensitivity=...)` is the synthesized report's own content-
   classification label (falls back to the intent's `governance.sensitivity`, then `"personal"`) —
   NOT this operation's `effective_sensitivity`/`sensitivity_ceiling`, which I resolve structurally
   from the run's own `run.yaml`, same as the other two adapters. I forwarded it straight through as
   a plain optional adapter parameter (same tier as `audience`/`model_profile`/`final`/`llm`) since
   the per-service table in the scoping doc lists it as part of the canonical signature to wrap, and
   nothing in the decided contract singles it out the way D1 singles out `sensitivity_ceiling`. I
   don't think this is a defect — the field only affects report front-matter, not authorization — but
   it's a plausible confusion point for a future reader, so I documented it explicitly in the module
   docstring rather than silently forwarding it.

3. **Pre-existing type-checker limitation, not something I introduced.** `mypy`/`pyright` both flag
   `base.register(ADAPTER)` at the bottom of my module: `RunExtractAdapter`/etc. (frozen dataclasses
   with `operation_kind: str = ...`) are reported incompatible with the `OperatorAdapter` Protocol
   because Pyright/mypy treat a plain Protocol attribute as read-write, while a frozen dataclass field
   is read-only. I confirmed this is NOT new: running `mypy` against the unmodified `run_plan.py`
   produces the identical error at its own `base.register(ADAPTER)` line. Since `base.py`'s
   `OperatorAdapter` Protocol is a hard-boundary file I may not edit, and the exemplar itself already
   ships with this diagnostic, I left it as-is rather than "fixing" something outside my file
   ownership. Flagging per the LSP-diagnostics rule so it isn't mistaken for a regression.

4. Ran `ruff check --fix` on both new files after authoring them (import-order/typing-import
   auto-fixes only, no logic changes) — `ruff check` is now clean on both.

## Anything I could not do

Nothing was blocked. All three adapters are implemented, all mandatory tests (D6 parity, D7 retry,
D1/H7 ceiling) pass per adapter, plus a dry-run zero-effects test per adapter. No hard boundary was
touched (`operator_mcp_policy.py`, `operator_operation_service.py`,
`operator_cancel_resume_service.py`, `base.py`, `__init__.py`, any canonical service, and
`cli_commands.py` are all unmodified — confirmed via `git status`/diff scope, not just intent).
