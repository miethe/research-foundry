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

---

## Fix cycle 1 (post-pregate review, F5 + F6)

Two independent adversarial lenses (gpt-5.6-terra + ICA claude-sonnet-5) re-read the tree and
found two real HIGH defects in this leg's own files (`.claude/findings/
m1-remainder-pregate-consolidated.md`). H6 ("`run.bundle` can report false success") was
explicitly **refuted** by both lenses, and the §D5 prerequisite design was confirmed correct —
only the pre-authorization *timing* of the prerequisite checks, and the unvalidated explicit-path
sibling parameters, were the actual holes.

### F5 — explicit inputs escaped authorization (fixed)

`verify_report`'s own explicit-path resolution (`_resolve_explicit_path`) accepts an absolute
path as-is if it exists, with **no ownership/workspace check at all**. An authorized caller for
run A could pass an absolute `report_path`/`claim_ledger_path` under run B (a different run,
possibly a different workspace); `verify_report` would read B's report, verify it under A's
authorization, and write `verification_status` back into **B's** `claim_ledger.yaml` — with no
policy target ever representing or authorizing those two parameters.

**Fix**: `_explicit_path_within_run(run_root, candidate)` — a **purely structural** containment
check (never queries whether the resolved foreign path *exists*, since that would itself be an
F6-shaped existence oracle over data the caller isn't authorized to see). It resolves `candidate`
exactly the way `verify_report` would (absolute-as-is, relative-against-run-dir) but requires the
result to be contained within the authorized run's own directory tree in *both* cases, and does
**not** honor `verify_report`'s own cwd-relative fallback at all (the process CWD isn't
workspace-scoped either — no legitimate reason for a caller to reach it through this adapter).
Applied inside `_run()`, before `verify_report` is ever called, for both `report_path` and
`claim_ledger_path`.

**Defect-class-checklist item 2 applied**: enumerated every other caller-supplied parameter
`invoke_verify`/`invoke_bundle` forward into their canonical services for the same bypass shape.
`invoke_verify` forwards `fail_on_unsupported` (bool, no reference semantics),
`exact_passage_override` (str, validated against a closed 2-value vocabulary by
`resolve_exact_passage_mode` itself — not a path/reference), and `evidence_judgment_bases` (list
of str tags, not a path/reference) — none of these name another resource, so none admit the F5
bypass shape. `invoke_bundle` forwards only `run_id`, which is already the sole authorized target.
No sibling parameter beyond `report_path`/`claim_ledger_path` needed the same fix.

### F6 — prerequisite checks leaked target existence before authorization (fixed)

`_verify_prerequisites_met`/`_bundle_prerequisites_met` used to run **before** `ctx` was even
constructed (mirroring `swarm_start.py`'s own budget/timeout preflight shape verbatim). This let
an **unauthorized** caller distinguish a foreign run that HAS the required artifacts (fell through
the pre-ctx check, denied later at the rbac/guard stage with `reason_code="not_found"`) from one
that does NOT (denied immediately by the pre-ctx check, `reason_code="preflight_failed"`, before
authorization ever ran) — an existence/state oracle over a run the caller has no claim to.

**Fix**: moved BOTH prerequisite checks **inside `_run()`** — they now execute only after
`base.run_pipeline`'s fixed authorize → consume → execute order has already authorized and
durably consumed the operation. An unauthorized caller is denied at the RBAC/guard stage exactly
like any other unauthorized target reference, before either prerequisite check ever runs; the
prerequisite check still guarantees the canonical service (`verify_report`/`build_bundle`) is
never invoked when unmet — only the *denial reason* changed, from a bespoke `preflight_failed`
pre-`ctx` denial to the normal `run_or_replay` exception-based failure channel (U1), which yields
`ok=False`/`reason_code="internal_error"` (matching `run_plan.py`'s own missing-intent
precedent — an authorized-but-failing operation legitimately creates a real operation manifest,
which is not itself a leak since it happens uniformly for every operation regardless of outcome).

Fixing F6 is what let the **H7 tests revert to the literal exemplar comparison** (above-ceiling
denial vs. a genuinely *missing* `run_id`, both `not_found`, both reachable under `dry_run=True`
now that neither adapter's prerequisite check runs pre-authorization) instead of the earlier
wrong-workspace substitute — exactly as flagged. Both H7 tests were rewritten accordingly
(`test_invoke_verify_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run`,
`test_invoke_bundle_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run`).

### Regression tests added (5 new, all confirmed to fail pre-fix)

- `test_invoke_verify_foreign_report_path_denies_and_does_not_touch_foreign_run` (F5)
- `test_invoke_verify_foreign_claim_ledger_path_denies_and_does_not_touch_foreign_run` (F5)
- `test_explicit_path_within_run_rejects_traversal_and_absolute_foreign_paths` (F5, direct unit
  test of the guard itself — relative `../` traversal and an absolute foreign path)
- `test_invoke_verify_foreign_run_state_does_not_leak_before_authorization_f6` (F6)
- `test_invoke_bundle_foreign_run_state_does_not_leak_before_authorization_f6` (F6)

Three pre-existing tests also had to change shape (not new regressions — the F6 fix moved their
own denial off the `dry_run=True` path entirely, since `dry_run` never reaches `_run()`):
`test_invoke_verify_missing_report_denies_after_authorization_zero_effects`,
`test_invoke_bundle_denies_when_no_passing_verification_zero_effects`,
`test_invoke_bundle_denies_when_prior_verification_failed_zero_effects` — all three now drive a
real (non-dry-run) confirmation cycle and assert `reason_code="internal_error"` instead of a
`dry_run=True` call asserting `reason_code="preflight_failed"`.

**Pre-fix verification (as required)**: `git stash push -- src/.../verify_bundle.py` to restore
the pre-fix module on disk (tests unchanged), ran `pytest -k "f6 or foreign_report_path or
foreign_claim_ledger_path or explicit_path_within_run"` — all 5 new regression tests failed
(`AssertionError: assert True is False` for the F5 tests and the two shape-mismatch prerequisite
tests, `AttributeError: ... has no attribute '_explicit_path_within_run'` for the direct guard
unit test, `AssertionError` on differing `reason_code`/`message` for the two F6 leak tests), then
`git stash pop` to restore the fix. Real transcript excerpt:

```
FAILED tests/unit/test_operator_mcp_adapter_verify_bundle.py::test_invoke_verify_foreign_report_path_denies_and_does_not_touch_foreign_run - AssertionError: assert True is False
FAILED tests/unit/test_operator_mcp_adapter_verify_bundle.py::test_invoke_verify_foreign_claim_ledger_path_denies_and_does_not_touch_foreign_run - AssertionError: assert True is False
FAILED tests/unit/test_operator_mcp_adapter_verify_bundle.py::test_explicit_path_within_run_rejects_traversal_and_absolute_foreign_paths - AttributeError: module 'research_foundry.services.operator_mcp_adapters.ver...
FAILED tests/unit/test_operator_mcp_adapter_verify_bundle.py::test_invoke_verify_foreign_run_state_does_not_leak_before_authorization_f6 - AssertionError: assert {'message': '...t_found', ...} == {'message': '..._f...
FAILED tests/unit/test_operator_mcp_adapter_verify_bundle.py::test_invoke_bundle_foreign_run_state_does_not_leak_before_authorization_f6 - AssertionError: assert {'message': '...t_found', ...} == {'message': '..._f...
```

### Validation (real output, post-fix)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_verify_bundle.py -q
..................                                                      [100%]
```
(18 passed — 13 original + 5 new; visually confirmed no `FAILED`/red output, including with
`| cat -v` to rule out ANSI-hidden failures per the "don't trust `grep ^FAILED`" instruction.)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_verify_bundle.py tests/unit/test_operator_mcp_adapter_run_plan.py tests/unit/test_operator_mcp_adapter_swarm_start.py tests/unit/test_operator_mcp_adapter_base.py -q
..............................................................................
                                                                          [100%]
```
(47 passed, no failures.)

`flake8 --select=E9,F63,F7,F82` on both files: clean (exit 0).

### Module docstring updated

`verify_bundle.py`'s module docstring now has a dedicated "Fix cycle 1 (post-pregate review, F5 +
F6)" section spelling out both defects and fixes, plus a rewritten "H7 negative fixture" section
pointing at the restored exemplar comparison. D4/D5 prose and both `invoke_*` docstrings were
updated to describe the new post-authorization checkpoint ordering.

No hard boundary was touched — `operator_mcp_policy.py`, `operator_operation_service.py`,
`operator_cancel_resume_service.py`, `base.py`, `__init__.py`, and every canonical service
(including `verification.py`) remain untouched by this fix cycle.
