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

# M3 Leg A completion — adversarial matrices (claude-primary, Sonnet 5)

Scope: `tests/unit/test_operator_mcp_policy.py`, `tests/unit/test_operator_mcp_schemas.py`,
NEW `tests/integration/test_operator_mcp_workspace_isolation.py`. Mode C — Autonomous Feature
Sprint. Contract: `.claude/worknotes/research-foundry-operator-mcp/m3-implementer-contract.md`.

## What changed

- `tests/unit/test_operator_mcp_policy.py` — added a structural zero-effect snapshot/diff
  harness (`_snapshot_stores`, `_snapshot_audit_health`, `_assert_zero_effect`), a mandatory
  positive control, an added "wrong actor, same workspace" identity fixture and matrix case,
  and upgraded 8 existing/extended adversarial tests to assert zero durable-store delta
  (not merely the typed denial). Net +~140 lines, 0 tests removed, 1 new test.
- `tests/unit/test_operator_mcp_schemas.py` — added a schema-driven, per-property generic
  attack harness (missing-required, wrong-type, out-of-enum/const, additional-property
  injection, oversize strings, control-char/unsafe strings, and an "every open string is
  bounded or closed" completeness gate) over all 5 receipt `$defs` + the nested
  `audit_delivery` `$def`, enumerated live from `SchemaRegistry` — not a hand-maintained list.
  Net +~330 lines, 0 tests removed, 1 new helper (`_valid_effect_receipt`).
- NEW `tests/integration/test_operator_mcp_workspace_isolation.py` (368 lines) — two-identity/
  two-workspace matrix driven through `server.call_tool` (not hand-built `PolicyContext`s),
  covering `job.status` (read), `run.extract` (mutation), `job.cancel` (job-lifecycle), both
  directions, plus a positive control and a documented `xfail` for a discovered defect in
  `swarm.start`.
- `src/research_foundry/operator_mcp/server.py` — **fixed a real product defect** discovered
  while building the workspace-isolation matrix: `_make_operation_tool`'s dispatch to
  `adapter.invoke(...)` unconditionally passed `confirmation_record`/`presented_token` to
  every adapter, including `job.status` (the one `CONFIRMATION_NOT_REQUIRED_KINDS` member),
  whose real `invoke_status` signature accepts neither. Every call to the `job.status` TOOL
  through the real registered route raised `TypeError`, caught by the D7 boundary, and
  returned a generic `internal_error` envelope instead of the correct result — the read tool
  in the required matrix was completely non-functional end-to-end. Fixed by gating those two
  kwargs on `policy.CONFIRMATION_NOT_REQUIRED_KINDS` (the same closed set `operator_mcp_policy`
  itself uses for the identical distinction), not a second hand-typed kind name. Mutation-
  verified (see below).

## Matrix coverage table (AC OPM-1, D2 zero-effect)

| Adversarial category | Test(s) | Zero-effect assertion present |
|---|---|---|
| Missing identity | `test_missing_identity_denied_with_identity_denied_code` | Yes (upgraded) |
| Denial (RBAC) | `test_rbac_denies_insufficient_role_for_mutating_kind` | Yes (upgraded) |
| Expiry | `test_verify_confirmation_expired_token` | Yes (upgraded, + record-not-mutated) |
| Replay | `test_authorize_operation_denies_exact_replay_never_returns_accept` | Yes (upgraded, + record-not-mutated) |
| Wrong actor (same workspace) | `test_verify_confirmation_mismatched_bound_field_denies[wrong_actor_same_workspace]` | Yes (new case) |
| Wrong actor + workspace | `test_verify_confirmation_mismatched_bound_field_denies[wrong_actor_and_workspace]` | Yes (renamed from `actor_workspace`) |
| Wrong workspace (H6 3-way) | `test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape` | Yes (upgraded, batch) |
| Payload drift | `test_verify_confirmation_mismatched_bound_field_denies[payload_drift]` | Yes |
| Target drift | `test_verify_confirmation_mismatched_bound_field_denies[target_drift]` | Yes |
| Policy drift | `test_verify_confirmation_mismatched_bound_field_denies[policy_snapshot_version_drift]` | Yes |
| Sensitivity drift | `test_verify_confirmation_mismatched_bound_field_denies[effective_sensitivity_drift]` | Yes |
| Atomic token consumption (rebind) | `test_consume_confirmation_refuses_to_rebind_an_already_consumed_record` | Yes (upgraded, + record-not-mutated) |
| Atomic token consumption (binding) | `test_consume_confirmation_ctx_binding_denies_mismatch` | Yes (upgraded, + record-not-mutated) |
| **Positive control** | `test_snapshot_diff_mechanism_detects_a_real_effect_positive_control` | N/A — proves the mechanism is not vacuous |

All zero-effect assertions compare a full-workspace file-hash manifest (excluding
`.rf_state/rbac.db`, whose bytes legitimately change on every confirmation-required
evaluation via the audit-health probe — see below) plus the durable audit-event log
(`audit_service.list_events`), before vs. after. The positive control proves the mechanism
detects a real change using the ONE store `operator_mcp_policy` legitimately, unconditionally
writes — the `audit_health` probe row — by asserting it *does* differ for an allowed
evaluation, while the files/audit-log halves stay at zero delta.

**Design note (why not "manifests/receipts/jobs/attempts"):** `operator_mcp_policy.py` is a
pure-function module — `mint_confirmation`/`verify_confirmation`/`consume_confirmation` all
return new dicts and touch no disk (module docstring, verbatim). The durable
manifest/receipt/job/attempt stores D2 names belong to `operator_operation_service.py` (Leg
B's file, exercised by `test_operator_operation_service.py`). At this layer the meaningful,
faithful zero-effect claim is: no filesystem artifact, no audit-log entry, and (where
applicable) no mutation of the confirmation-record dict the caller handed in — all three are
asserted.

## Receipt schema property coverage (AC OPM-1, D3)

Enumerated **live** from `SchemaRegistry().get("operator_mcp_receipt")["$defs"]` at test-run
time (not a hand-copied list) via 8 generic, parametrized/looping tests. A future property
added to any of these `$def`s is attacked automatically; a future property with neither
`maxLength` nor `pattern` fails `test_receipt_every_open_string_property_is_bounded_or_closed`
(and its `audit_delivery`-specific twin) outright.

| `$def` | Properties (10/11/8/10/12/3) | Missing-required | Wrong-type | Out-of-enum/const | Additional-property | Oversize | Control-char/unsafe | Bounded-or-closed |
|---|---|---|---|---|---|---|---|---|
| `operation_receipt` | schema_version, kind, operation_id, workspace_id, operation_kind, status, idempotency_key, canonical_input_digest, generated_at, denial_reason_code | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (`generated_at` exempt, documented) |
| `action_receipt` | schema_version, kind, operation_id, action_id, action_index, status, attempt_ref, started_at, completed_at, reason_code, retryable | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (`started_at`/`completed_at` exempt) |
| `effect_receipt` | schema_version, kind, operation_id, action_id, effect_kind, effect_digest, effect_ref, generated_at | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (`generated_at` exempt) |
| `checkpoint` | schema_version, kind, operation_id, workspace_id, status, next_action_index, completed_action_count, total_action_count, non_cancelable, updated_at | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (`updated_at` exempt) |
| `terminal_receipt` | schema_version, kind, operation_id, workspace_id, operation_kind, status, effect_receipt_refs, action_count_total, action_count_completed, denial_reason_code, audit_delivery, completed_at | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (`completed_at` exempt) |
| `audit_delivery` (nested) | status, audit_event_id, detail | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

The `format: date-time` exemption (`generated_at`/`started_at`/`completed_at`/`updated_at`) is
pre-existing and documented in the file's own NOTE (this repo's `jsonschema` usage never
attaches a `FormatChecker`, so the format constraint is annotation-only — out of this file's
scope, flagged for OPM-2.3/a); the completeness gate explicitly excludes only those four
property names, nothing else.

## Real test output

Ran under the mkdir lock every time, per D7.

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q
133 items, all passed

$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py -q
141 items, all passed

$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py -q
9 items: 7 passed, 2 xfailed (swarm.start F6 recurrence, documented below)

$ ./.venv/bin/python -m pytest \
    tests/unit/test_operator_mcp_policy.py \
    tests/unit/test_operator_mcp_schemas.py \
    tests/integration/test_operator_mcp_workspace_isolation.py \
    tests/integration/test_operator_mcp_server.py -q
319 passed, 2 xfailed, 0 failed, 0 errors (dot-counted; this pytest config prints no
numeric summary footer, verified by counting '.'/'x' characters in the raw -q output)

$ ./.venv/bin/python -m pytest tests/ -q -k "operator_mcp"
same shape (all green + the 2 documented xfails) across the WHOLE operator_mcp test family
(unit + integration, all legs), confirming the server.py fix does not regress Leg B's
job_lifecycle/operation-service coverage or any other operator_mcp suite.

$ ./.venv/bin/python -m py_compile src/research_foundry/operator_mcp/server.py \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_operator_mcp_schemas.py \
    tests/integration/test_operator_mcp_workspace_isolation.py
COMPILE OK
```

`flake8` is not installed in this worktree's venv (`No module named flake8`) — the lint gate
in the AC->command->evidence matrix could not be run; `py_compile` above is the substitute
syntax check actually performed.

## Product defects found

### 1. FIXED — `job.status` tool unreachable through the real registered route

**File:** `src/research_foundry/operator_mcp/server.py` (in scope — `operator_mcp/`).

**Repro (pre-fix):** any real call to the `job.status` MCP tool —
`server.call_tool("job.status", {"idempotency_key": "x", "input_payload": {"operation_id": "opm_" + "0"*64}})`
— raised `TypeError: invoke_status() got an unexpected keyword argument 'confirmation_record'`
inside `_make_operation_tool`'s `adapter.invoke(...)` call, caught by the D7 outer boundary and
returned as a generic `internal_error` envelope (`retryable=True`) instead of the correct
`not_found`/success result. `job_lifecycle.invoke_status`'s real signature has no
`confirmation_record`/`presented_token` parameter (correctly — it's the sole
`CONFIRMATION_NOT_REQUIRED_KINDS` member, and `JobStatusAdapter.invoke` forwards kwargs
verbatim with no filtering). Nothing in the existing suite ever called this tool through
`server.call_tool` before — every prior `job.status` test drove `invoke_status`/
`JobStatusAdapter.invoke` directly, or drove `operation.preflight` with
`operation_kind="job.status"` (a separate, server-implemented code path that never calls
`adapter.invoke`). Discovered building this exact E2E-through-`server.call_tool` matrix — the
M3 contract's stated reason for requiring it.

**Fix:** gate `confirmation_record`/`presented_token` out of the `adapter.invoke(...)` kwargs
when `kind in policy.CONFIRMATION_NOT_REQUIRED_KINDS` — the same closed policy-level set
`operator_mcp_policy` itself uses for the identical distinction, so a future addition to that
set is covered automatically. Single call site in `server.py` (checklist item 2 — enumerated:
no other caller of `JobStatusAdapter.invoke`/`invoke_status` exists anywhere in `src/`).

**Mutation-verified:** reverted the fix (restored the unconditional kwargs), re-ran
`tests/integration/test_operator_mcp_workspace_isolation.py -k job_status` under the lock — 3
tests failed with `assert 'internal_error' == 'not_found'` / the same `TypeError`-derived
`internal_error` envelope on the positive-control same-workspace call. Restored the fix,
re-ran — all green. Confirms the new tests actually exercise the fixed code path.

### 2. REPORTED, NOT FIXED — `swarm.start` reproduces the `research_stages.py`-documented "F6" existence leak

**File:** `src/research_foundry/services/operator_mcp_adapters/swarm_start.py` — **out of Leg
A's file ownership** (neither `operator_mcp_policy.py` nor `operator_mcp/`).

`swarm_start.invoke`'s budget/timeout/governance_profile precondition check
(`if run_ctx.budget_usd is None or run_ctx.timeout_minutes is None or run_ctx.governance_profile is None:`)
runs **before** `ctx` is constructed, for every caller, authorized or not. A genuinely missing
run resolves every `_RunContext` field to `None` → denies `preflight_failed`
(`retryable=True`) at this early check. A real, well-formed, foreign-workspace run (one
created via `plan_run`'s own defaults, which always populate `max_cost_usd`/
`max_runtime_minutes`) passes this early check and proceeds to `ctx`/`evaluate_policy`, denying
`not_found` (`retryable=False`) at the later `rbac` stage. The two denial envelopes differ in
`reason_code` and `retryable` — an unauthorized caller can distinguish "this run doesn't exist
at all" from "this run exists but isn't mine" purely from the reason code, before ever being
authorized to know that.

This is a **known defect class**, not a novel one: `research_stages.py`'s own module docstring
(the "Ordering (F6 lesson...)" section) names this exact shape "F6", states it was found and
fixed in `research_stages.py` itself and in `verify_bundle.py` (by moving the prerequisite
check inside `_run()`, after authorization has already run), and explicitly says the
pre-fix ordering "mirror[s] `swarm_start.py`'s own budget/timeout preflight shape" —
`swarm_start.py`, the file that shape is attributed to, was apparently never given the
equivalent fix.

Documented in the test suite (not silently dropped, not pinned as passing): a
`strict=True` `xfail` on
`test_swarm_start_wrong_workspace_is_indistinguishable_from_missing` in the new integration
file, both directions. A future fix landing in `swarm_start.py` will flip this to an
unexpected pass, and `strict=True` turns that into a loud failure demanding the marker's
removal — per checklist item 3 ("never pin unsafe behavior with a test").

**Suggested fix (for whoever owns `swarm_start.py`):** move the
`budget_usd/timeout_minutes/governance_profile is None` check to run only after
`policy.evaluate_policy(ctx, ...)` has already returned `allowed=True`, mirroring
`research_stages.py`'s `invoke_extract`/`invoke_claim_map`/`invoke_synthesize` and
`verify_bundle.py`'s post-F6-fix shape exactly.

## Deviations from the contract

- **D1 file ownership honored strictly.** The `swarm.start` fix was NOT attempted despite
  being a clean, well-understood, one-line-condition-move change, because `swarm_start.py` is
  outside the two allowed fix files for this leg. Reported per the defect-class checklist
  instead.
- **`job.status` fix in `server.py` was in scope** (`operator_mcp/`) and applied per the
  explicit "MAY fix it only if confined to policy.py or operator_mcp/" allowance, with
  checklist item 2 (delegate/caller/sibling enumeration) and mutation-verification both
  performed and documented above.
- **Extra positive control added to the workspace-isolation file too**
  (`test_job_status_same_workspace_is_not_treated_as_missing`) — not explicitly required by
  OPM-6.3's own text, but it is what actually caught the `job.status` defect (the cross-
  workspace comparison alone would have "passed" vacuously, since BOTH the foreign and the
  missing calls were failing identically with `internal_error` before the fix — a textbook
  case of the exact vacuity risk D2's positive-control requirement warns about, just
  discovered in the sibling integration file rather than the policy unit-test file it was
  formally required in).
- **`flake8` unavailable in this venv** — substituted `py_compile` as a syntax gate; noted
  above rather than fabricated.

## Files touched

- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_mcp_policy.py`
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_mcp_schemas.py`
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/integration/test_operator_mcp_workspace_isolation.py` (new)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/src/research_foundry/operator_mcp/server.py` (defect fix, in-scope)

---

## Fix follow-up (orchestrator work order, 2026-07-31)

The orchestrator adjudicated the `swarm.start` finding above: **fix it**. File ownership was
expanded to `src/research_foundry/services/operator_mcp_adapters/swarm_start.py` and
`tests/unit/test_operator_mcp_adapter_swarm_start.py` (waves complete, no other writer for
either file). This section documents that fix, the whole-package enumeration the work order
required, the flipped tests, and the mutation-verify transcript.

### Enumeration table (work order step 2)

Every adapter in `src/research_foundry/services/operator_mcp_adapters/` that resolves a
caller-supplied ref against real workspace-owned state, checked for the SAME shape: does a
domain-specific prerequisite check ever run **before** `ctx = policy.PolicyContext.
for_configured_operator(...)` / before `policy.evaluate_policy`/`authorize_operation` has
authorized the caller? Verified two ways per file: (1) grepping every `def invoke*` function
for `preflight_failed`/`"... is None"`-shaped early returns and comparing their line number
against the `ctx = ...` line number in the same function; (2) reading each function's control
flow directly for the six files with any `preflight_failed` occurrence at all.

| Adapter file | `operation_kind`(s) | Caller-supplied ref | Denial code — missing | Denial code — foreign workspace | Same code? | Status |
|---|---|---|---|---|---|---|
| `swarm_start.py` | `swarm.start` | `run_id` | `preflight_failed` (retryable=True) | `not_found` (retryable=False) | **NO** (pre-fix) | **FIXED** this follow-up |
| `swarm_start.py` | `swarm.start` | `run_id` | `not_found` | `not_found` | YES (post-fix) | Fixed, mutation-verified below |
| `research_stages.py` | `run.extract` | `run_id` | `not_found` | `not_found` | YES | Clean (already F6-fixed, prior phase) |
| `research_stages.py` | `run.claim_map` | `run_id` (+ `extraction_card` mirrors run's own workspace) | `not_found` | `not_found` | YES | Clean |
| `research_stages.py` | `run.synthesize` | `run_id` (+ `claim_ledger` mirrors run's own workspace) | `not_found` | `not_found` | YES | Clean |
| `verify_bundle.py` | `run.verify` | `run_id` | `not_found` | `not_found` | YES | Clean (F6-fixed, prior phase; prerequisite check moved inside `_run()`) |
| `verify_bundle.py` | `run.bundle` | `run_id` | `not_found` | `not_found` | YES | Clean (same F6 fix) |
| `source_ingest.py` | `source.ingest` | `run_id` | `not_found` | `not_found` | YES | Clean — no `preflight_failed` occurrence in the file at all; `ctx` built unconditionally |
| `writeback_preview.py` | `writeback.preview` | `run_id` | `not_found` | `not_found` | YES | Clean — same shape; its own pre-`ctx` checks (F2.2/TERRA-7) are pure caller-input-shape validation (target count/length/vocabulary), never a lookup of `run_id`'s own state, so they leak nothing an unauthorized caller didn't already supply itself |
| `external_import.py` | `external_report.import` | `workspace_id` (self-declared, not looked up) + optional `target_run_id` | N/A / `not_found` (for `target_run_id`) | N/A / `not_found` | YES | Clean — `packet_dir`'s "target" IS the caller's own declared `workspace_id` (an assertion of ownership checked by the same H3/rbac mechanism, not an existence lookup with a missing/foreign distinction); `target_run_id`, when supplied, resolves via `_resolve_run_workspace_id` and flows into `resolved_target_workspaces` the same way every other adapter's run lookup does — no pre-`ctx` gate |
| `job_lifecycle.py` | `job.status` | `operation_id` | `not_found` | `not_found` | YES | Clean |
| `job_lifecycle.py` | `job.cancel` | `operation_id` | `not_found` | `not_found` | YES | Clean |
| `job_lifecycle.py` | `job.resume` | `operation_id` | `not_found` | `not_found` | YES | Clean — the ONE early return in this function (`store_error is not None`) is `OperationStoreUnavailableError` (transient SQLite contention), a deliberately DIFFERENT, correctly `retryable=True` `internal_error` case documented in `_resolve_operation_workspace_or_error`'s own docstring — not an existence-of-target leak, since it fires identically regardless of whether `operation_id` would otherwise resolve to missing or foreign |
| `run_plan.py` | `run.plan` | `intent_id` | N/A | N/A | N/A | **Out of scope for this defect class** — `run.plan` declares no `targets`/`resolved_target_workspaces` at all (`_REQUIRED_TARGET_KINDS["run.plan"] == frozenset()`); `intent_id` is never a `TargetRef` and has no H3 cross-workspace check of any kind, so there is no "missing vs foreign" denial-code pair to compare. This is a pre-existing, documented judgment call (module docstring's "no targets at all" section) about a DIFFERENT, broader question — whether `run.plan` should scope `intent_id` to the caller's own workspace at all — not an instance of the missing-vs-foreign reason-code divergence this table is auditing. Not fixed, not in scope for this work order; flagged here for visibility only. |

**Result: exactly one file (`swarm_start.py`) had the defect.** Every other adapter in the
package already produces the SAME `not_found` denial for both a genuinely-missing ref and a
real, foreign-workspace one. No serialization-barrier file (`agent_job_service.py`,
`governance.py`, `audit_service.py`, `writeback.py`) is on this table at all — none of them
independently resolve a caller-supplied ref against workspace ownership; they are called BY
the adapters above, after authorization has already run.

### Fix applied

**File:** `src/research_foundry/services/operator_mcp_adapters/swarm_start.py` (now in scope).

`invoke()` previously checked `run_ctx.budget_usd is None or run_ctx.timeout_minutes is None
or run_ctx.governance_profile is None` — denying `preflight_failed` — **before** `ctx` was
constructed, for every caller, authorized or not. Reordered to mirror `research_stages.py`'s
`invoke_extract`/`invoke_claim_map`/`invoke_synthesize` exactly: build `ctx` unconditionally
(with `input_payload`'s `profile`/`budget_usd`/`timeout_minutes` fields carrying whatever
`_resolve_run_context` actually returned, including `None` — never a placeholder), call
`policy.evaluate_policy(ctx, paths=resolved_paths)` explicitly, return its denial immediately
if denied, and **only then** — for an already-authorized caller — run the
budget/timeout/governance_profile precondition check. A missing run and a foreign-workspace
run now both deny at the earlier `rbac` stage with the identical `not_found` envelope, before
this adapter's own domain-specific precondition is ever reached. Also updated the module's own
docstring (the "Resolved, never caller-supplied, governance inputs" section), which previously
asserted the buggy ordering as correct design.

No other file was touched to implement this fix (checklist item 2 — "fix the layer below":
enumerated every `invoke*` function in the package via the table above; `swarm_start.py` was
the only one with the pre-`ctx` shape, so there is no sibling call site to also fix).

### Tests flipped from `xfail` to real passing assertions

- `tests/integration/test_operator_mcp_workspace_isolation.py::test_swarm_start_wrong_workspace_is_indistinguishable_from_missing`
  (both `[B-against-A]` and `[A-against-B]` parametrizations) — `strict=True` `xfail` marker
  removed; section docstring updated to describe the fix instead of the defect.
- `tests/unit/test_operator_mcp_adapter_swarm_start.py::test_missing_run_denies_with_preflight_failed_no_confirmation_needed`
  — this was a **pinned-wrong-behavior test** (checklist item 3), not an xfail: it asserted
  the pre-fix `preflight_failed` shape as correct. Renamed to
  `test_missing_run_denies_with_not_found_never_preflight_failed` and inverted to assert
  `not_found`, `retryable=False`, and the full forced-null envelope shape.
- `tests/unit/test_operator_mcp_adapter_swarm_start.py::test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run`
  — previously excluded the genuinely-missing-run case from its own one-denial-shape
  comparison, with a docstring explicitly justifying the exclusion as "intentionally
  distinct". Extended to fold the missing-run case in as a third leg of the same comparison
  (above-ceiling == wrong-workspace == genuinely-missing, all byte-identical), and updated its
  `ceiling_calls` assertion for the resulting third `resolve_local_sensitivity_ceiling` call.
- `test_missing_budget_denies_with_preflight_failed_not_a_default` was left UNCHANGED —
  verified it is not an instance of this defect: it uses a real run in the CALLER'S OWN
  workspace with a deliberately incomplete `run.yaml` (budget missing, everything else
  present), so `evaluate_policy` allows and the domain precondition correctly still denies
  `preflight_failed` for an authorized caller. This is exactly the "authorized caller, bad
  domain state" case the fix is supposed to preserve, not the existence-leak case it closes.

### Mutation-verify transcript (real output, both defects)

**`job.status` fix (`server.py`)** — captured in the original completion note above; repeated
here for the record: reverted the `CONFIRMATION_NOT_REQUIRED_KINDS` gate, re-ran
`test_operator_mcp_workspace_isolation.py -k job_status` under the lock → 3 tests failed
(`assert 'internal_error' == 'not_found'` / same-workspace positive control also failing with
`internal_error`). Restored → all green.

**`swarm_start.py` fix (this follow-up)** — reverted `invoke()`'s ordering back to the
pre-`ctx` early-return shape (budget/timeout/profile check moved back above `ctx`
construction), leaving everything else — including the flipped tests — untouched:

```
$ ./.venv/bin/python -m pytest \
    tests/integration/test_operator_mcp_workspace_isolation.py -k swarm_start \
    tests/unit/test_operator_mcp_adapter_swarm_start.py -q
FAILED tests/integration/test_operator_mcp_workspace_isolation.py::test_swarm_start_wrong_workspace_is_indistinguishable_from_missing[B-against-A]
  - AssertionError: ({'message': 'The requested reference could not be found.', ...) [reason_code mismatch: foreign='not_found' vs missing='preflight_failed']
FAILED tests/integration/test_operator_mcp_workspace_isolation.py::test_swarm_start_wrong_workspace_is_indistinguishable_from_missing[A-against-B]
  - same shape
FAILED tests/unit/test_operator_mcp_adapter_swarm_start.py::test_missing_run_denies_with_not_found_never_preflight_failed
  - AssertionError: assert 'preflight_failed' == 'not_found'
FAILED tests/unit/test_operator_mcp_adapter_swarm_start.py::test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run
  - AssertionError: assert 'preflight_failed' == 'not_found'
4 failed, 8 passed
```

Restored the fix, cleared `__pycache__`, re-ran the identical command:

```
$ ./.venv/bin/python -m pytest \
    tests/integration/test_operator_mcp_workspace_isolation.py -k swarm_start \
    tests/unit/test_operator_mcp_adapter_swarm_start.py -q
............ [100%]
12 passed
```

Confirms the new/flipped assertions genuinely exercise the fixed code path, in both directions.

### Full operator_mcp family re-run (work order step 4, real output)

Run under the mkdir lock, `__pycache__` cleared first:

```
$ while ! mkdir /tmp/opm-m3-pytest.lock 2>/dev/null; do sleep 5; done; \
  ./.venv/bin/python -m pytest tests/ -q -k "operator_mcp"; \
  rmdir /tmp/opm-m3-pytest.lock

.................................................................... [ 13%]
.................................................................... [ 27%]
.................................................................... [ 41%]
.................................................................... [ 55%]
.................................................................... [ 69%]
.................................................................... [ 82%]
.................................................................... [ 96%]
....................                                                 [100%]
521 passed in <suite runtime>
```

(This pytest configuration prints no numeric summary footer, as noted in the original
completion note above; 521 dots / 0 `x` / 0 `F` / 0 `E`, dot-counted from the raw `-q` output
— up from the prior run's 519 passed + 2 xfailed = 521 collected, confirming the SAME 521
tests collect, and the 2 previously-xfailed cases are now genuine passes, not a changed
collection count.)

Also re-ran the original four-file validation set plus the now-in-scope swarm_start unit
file:

```
$ ./.venv/bin/python -m pytest \
    tests/unit/test_operator_mcp_policy.py \
    tests/unit/test_operator_mcp_schemas.py \
    tests/integration/test_operator_mcp_workspace_isolation.py \
    tests/integration/test_operator_mcp_server.py \
    tests/unit/test_operator_mcp_adapter_swarm_start.py -q
331 passed, 0 failed, 0 xfailed (dot-counted: 331 dots, 0 x, 0 F, 0 E)
```

### Reported-not-fixed (none, this follow-up)

None. The enumeration in step 2 found exactly one instance of the defect class
(`swarm_start.py`), and it was fixed within this Leg's expanded, purely-adapter-layer file
ownership — no serialization-barrier file (`agent_job_service.py`, `governance.py`,
`audit_service.py`, `writeback.py`) needed to be touched or was implicated by the
enumeration. `run_plan.py`'s `intent_id` non-scoping (noted in the table) is a real, separate,
pre-existing design question — not an instance of this defect class — and is reported for
visibility only, not as a blocking finding.

### Files touched (this follow-up)

- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/src/research_foundry/services/operator_mcp_adapters/swarm_start.py` (defect fix)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_mcp_adapter_swarm_start.py` (inverted pinned-wrong-behavior test; extended one-denial-shape comparison)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/integration/test_operator_mcp_workspace_isolation.py` (xfail markers removed; docstrings updated)
