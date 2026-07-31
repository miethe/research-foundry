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

# M1 remainder, leg C — `run.verify` + `run.bundle` adapters (completion note)

## What was built

Two files, exactly as scoped, nothing else touched:

- `src/research_foundry/services/operator_mcp_adapters/verify_bundle.py` — `run.verify`
  (`invoke_verify`) and `run.bundle` (`invoke_bundle`) adapters in one module (mirrors
  `job_lifecycle.py`'s multi-adapter-per-file convention), following the `run_plan.py`/
  `swarm_start.py` shape exactly: `PolicyContext` → `ActionSpec` sequence → `action_manifest` →
  `build_result` callback → `base.run_pipeline`.
- `tests/unit/test_operator_mcp_adapter_verify_bundle.py` — 13 tests.

Neither `operator_mcp_adapters/__init__.py` nor any canonical service was touched; the two new
adapters are not yet registered into the package (integration owner's job, per the hard
boundaries) — verified by importing `verify_bundle` directly and confirming
`base.get_adapter("run.verify")`/`base.get_adapter("run.bundle")` resolve once that module is
imported.

## Design decisions implemented (§D1, D4, D5, D6, D7)

- **§D1**: no `sensitivity_ceiling` parameter on either `invoke_*`; both resolve it via
  `resolve_local_sensitivity_ceiling(resolved_paths)` (lazy import inside the function body,
  same as `run_plan.py`/`swarm_start.py`). Sensitivity/workspace are read-only resolutions from
  the target run's own `run.yaml`, mirroring `swarm_start._resolve_run_context` (trimmed to the
  two fields these two adapters need).
- **§D4 (`run.verify`)**: `_run()` for `verify_report` ALWAYS returns normally, regardless of
  `.passed` — a non-passing verdict is `ok=True` with `result["passed"] is False`, never a
  denial, never a raise. Proven by
  `test_invoke_verify_non_passing_is_ok_true_with_passed_false` (injects a real unsupported
  claim into a real ledger, drives the real `verify_report`, asserts `ok=True`/`passed=False`).
  Missing report/claim ledger (no explicit path given, nothing on disk) denies at a
  PREREQUISITE stage (`_verify_prerequisites_met`), before `ctx` is constructed, zero effects —
  `verify_report` is never called, so `reviews/verification.yaml` is never written and
  `rp.ensure_scaffold()`'s directory-creation side effect never fires either.
  (See "questionable contract detail" below re: "quarantine".)
- **§D5 (`run.bundle`)**: `_bundle_prerequisites_met` reads `reviews/verification.yaml` directly
  and requires `passed is True` before `build_bundle` is ever called — absent file, unparsable
  content, or `passed: False` all deny `preflight_failed`, zero effects, `build_bundle` never
  invoked (proven with two tests: no verification at all, and an on-disk non-passing
  verification). The live-path re-check inspects `BundleResult.verified` after calling
  `build_bundle(run_id, verify=True, ...)`; when `False` (simulating the documented race — see
  below), `_run()` raises, which `run_or_replay`'s own exception-based failure channel (U1) turns
  into a governed `ok=False` (`reason_code="internal_error"`, since there is no dedicated
  `CLOSED_REASON_CODES` member for this and minting one is out of scope — confirmed
  `CLOSED_REASON_CODES` is closed and validated by `build_error`).
- **§D6 (parity)**: `test_invoke_verify_result_matches_direct_verify_report_call` and
  `test_invoke_bundle_result_matches_direct_build_bundle_call` spy on the real service (wrap,
  never double-call) and assert the adapter's bounded result carries the same canonical fields
  field-by-field.
- **§D7 (retry)**: `test_invoke_verify_exact_retry_does_not_recall_verify_report` and
  `test_invoke_bundle_exact_retry_does_not_recall_build_bundle` present the SAME confirmation
  record/token/idempotency_key twice and assert the wrapped service is called exactly once and
  both results share the same `operation_id`.
- **H7**: both adapters get a negative fixture proving the above-ceiling guard fires and is
  shape-identical to another denial. See the next section for why the comparator differs from
  the literal exemplar.

## Known limitation stated in the module docstring (§D5, as required)

In the `run.bundle` live-path race (prerequisite check passes, but `build_bundle`'s own internal
verify returns `verified=False` by the time it actually runs), `build_bundle` has *already
written* a draft `evidence_bundle.yaml` to disk before this module's own check raises. The failed
`run.bundle` operation is therefore **not perfectly zero-effect** in that one race window.
Closing it requires changing `writeback.build_bundle` itself, which is out of this task's file
ownership (declared serialization barrier shared with M2). Proven directly in
`test_invoke_bundle_raises_when_build_bundle_reports_unverified_despite_passing_prerequisite`
(stubs `build_bundle` to return `verified=False`, drives a real non-dry-run confirmation cycle,
asserts `ok=False`/`reason_code=internal_error`).

## Contract decision I found questionable (reported, not silently deviated from)

**§D4's "quarantine" phrase.** I ran a dedicated research pass (Agent, `codebase-explorer`) for
any run-level quarantine concept across `verification.py`, `governance.py`, `source_cards.py`,
`extraction.py`, `claim_mapping.py`, `synthesis.py`, `paths.py`, and test files. Result: **no
such concept exists anywhere.** `quarantine`/`quarantined` only appears for (a) ERI
(`external_research_import`/`external_research_interchange`) action-level outcomes and (b)
canonical-claim/inference/envelope crash-recovery directories — neither touches `verify_report`
or has any relationship to a `run_id`'s own state. The most likely explanation:
`m1-remainder-scoping.md`'s own §(e) lists the `ImportOutcome.status` enum
(`"completed"|"completed_with_quarantine"|"blocked"|"pending"`) in the section immediately
adjacent to where the run-verify/run-bundle sections were likely drafted from, and "quarantine"
bled over. I implemented `run.verify`'s prerequisite stage covering exactly the two conditions
the codebase actually supports (missing report/claim ledger, H7 ceiling) and documented this
finding in the module docstring rather than inventing a quarantine check against a concept that
does not exist (which would itself have been a fabricated behavior).

## Deviation from the literal H7 exemplar (documented, mirrors an existing precedent)

`run_plan.py`'s own H7 test compares an above-ceiling denial to a genuinely-*missing*-target
denial (both reach the `guard` stage). That comparison does not hold for either of my two
adapters: BOTH have their own prerequisite check that intercepts a target with unmet
prerequisites and denies `preflight_failed` **before** `ctx` — and therefore the ceiling — is
ever constructed. This is the exact same situation `swarm_start.py`'s own H7 test already
documents and adapts to (its budget/timeout/profile preflight intercepts a missing run first,
for the identical structural reason). I followed `swarm_start.py`'s own precedent: compare an
above-ceiling denial for a REAL, prerequisite-satisfied target against a WRONG-WORKSPACE denial
for the same real target (guard stage vs. rbac stage, byte-identical `not_found` shape) — proving
the one-denial-shape guarantee without the target-existence confound. This is called out
explicitly in the module docstring under "H7 negative-fixture adaptation" so a reviewer does not
mistake it for a missed requirement.

## Validation (real output)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_verify_bundle.py -q
.............                                                           [100%]
13 passed

$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_verify_bundle.py tests/unit/test_operator_mcp_adapter_run_plan.py tests/unit/test_operator_mcp_adapter_swarm_start.py tests/unit/test_operator_mcp_adapter_base.py -q
..............................................................              [100%]
```

Full `tests/unit/` suite (run from worktree root, `.venv/bin/python`, matches contract's baseline
note): the only failures are the 3 documented pre-existing ones —
`test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off`,
`test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default`,
`test_report_anchors.py::test_schema_version_bumped_for_report_anchors` — all reproduce on `main`
independent of this change; none touch anything in scope here.

`flake8 --select=E9,F63,F7,F82` on both new files: clean. `mypy` on `verify_bundle.py`: the two
new findings (`Argument 1 to "register" has incompatible type "RunVerifyAdapter"/"RunBundleAdapter"`)
are the SAME pre-existing `frozen dataclass field vs. Protocol expecting a settable attribute`
class every sibling adapter module (`run_plan.py:313`, `swarm_start.py:482`,
`job_lifecycle.py:798-800`) already has — not a new defect class introduced here.

## Things I could not do (by design, per the hard boundaries)

- Did not register the two adapters in `operator_mcp_adapters/__init__.py` — integration owner's
  job.
- Did not fix `writeback.build_bundle`'s own non-blocking verify behavior (U2) or its bare
  `except Exception` swallowing a verify crash — out of file ownership, documented as a
  follow-up in the module docstring per §D5.
