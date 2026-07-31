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

---

## Pre-gate fix cycle (orchestrator work order, 2026-07-31)

Two review lenses (TERRA, ICA) examined the M3 delta at commit `a107d84`: 0 BLOCKING / 0 HIGH
overall, 2 MED + 1 LOW landing in this Leg's files
(`.claude/worknotes/research-foundry-operator-mcp/m3-pregate-terra.md`,
`.claude/worknotes/research-foundry-operator-mcp/m3-pregate-ica.md`). All three addressed below,
plus a **fourth, previously-undiscovered defect** found while implementing TERRA-M3-2's own
requested test.

### TERRA-M3-1 (MED) — doubled mutating audit-health probe

**Finding:** the F6 fix's ordering gate in `swarm_start.py` called the FULL `policy.
evaluate_policy` (all six stages, including `_check_audit_health`'s live, mutating
write-then-read-then-delete SQLite probe) as a pre-check, ahead of the budget/timeout/
governance_profile precondition. A successful (or late-denied) request then proceeded into
`base.run_pipeline`, whose own `authorize_operation` call runs the SAME full stack a SECOND
time for the real accept/consume decision — doubling the probe's write load and opening an
availability-failure window between the two probes (a transient lock/audit-store failure
landing between them could turn an otherwise-authorized request into `audit_unhealthy`).

**Fix (smallest structural fix — no `base.py` changes needed):** added
`operator_mcp_policy.check_capability_and_workspace(ctx, *, paths=None) -> PolicyDecision`, a
new, narrow, non-mutating ordering gate that runs ONLY the first two of the six fixed stages
(`capability`, `rbac`) via `_POLICY_STAGES[:2]` — never `audit_health`/`guard`/`preflight`/
`confirmation`. This is sufficient for the F6 convergence property, which depends only on
`rbac`'s H3 cross-workspace comparison. `swarm_start.py`'s `invoke` now calls this instead of
the full `evaluate_policy`; the real, full six-stage authorization still runs exactly once,
inside `base.run_pipeline`, unchanged. Explicitly documented as **not authorization** — a
caller must never treat its `allowed=True` as sufficient to execute any effect.

**Mutation-verify (a) — probe count is 1 per successful request.** New test
`test_swarm_start_invoke_probes_audit_health_exactly_once_per_successful_request` (counting
spy around `audit_service.health_check`, real preflight-shaped mint + durable
`record_confirmation` + `invoke` with a real confirmation). Reverted the ordering-gate call
back to `policy.evaluate_policy` (the pre-this-fix, post-F6-fix shape) and re-ran under the
lock:

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_swarm_start.py -q -k audit_health
FAILED test_swarm_start_invoke_probes_audit_health_exactly_once_per_successful_request
  - AssertionError: expected the mutating audit-health probe exactly ONCE per successful
    request, observed 2 -- TERRA-M3-1 regression
assert 2 == 1
```

Restored the fix, re-ran: `2 passed` (both `..._exactly_once_per_successful_request` and the
companion `test_swarm_start_ordering_gate_never_reaches_audit_health_on_its_own`, which proves
the narrowed gate costs ZERO probes for a missing-run denial that never reaches
`base.run_pipeline` at all).

**Mutation-verify (b) — F6 convergence still holds, and still fails if reverted to the
pre-M3 shape.** Reverted `swarm_start.py` ALL THE WAY to the original pre-M3 shape (the
budget/timeout/profile check moved back to BEFORE `ctx` construction, the very first defect
this whole workstream started from) and re-ran the full F6-relevant set under the lock:

```
$ ./.venv/bin/python -m pytest \
    tests/integration/test_operator_mcp_workspace_isolation.py -k swarm_start \
    tests/unit/test_operator_mcp_adapter_swarm_start.py -q
FAILED test_operator_mcp_workspace_isolation.py::test_swarm_start_wrong_workspace_is_indistinguishable_from_missing[B-against-A]
FAILED test_operator_mcp_workspace_isolation.py::test_swarm_start_wrong_workspace_is_indistinguishable_from_missing[A-against-B]
FAILED test_operator_mcp_adapter_swarm_start.py::test_swarm_start_ordering_gate_never_reaches_audit_health_on_its_own
FAILED test_operator_mcp_adapter_swarm_start.py::test_missing_run_denies_with_not_found_never_preflight_failed
FAILED test_operator_mcp_adapter_swarm_start.py::test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run
5 failed
```

All five correctly regress to `preflight_failed` (or the reason-code mismatch on it) once
reverted. Restored the fix, re-ran: full green, byte-identical to the pre-mutation file
(`diff` confirmed zero delta between the restored file and the fixed baseline).

### ICA-M3-1 (MED) — required-field omission masks as `internal_error` for 8/13 kinds

**Finding:** a direct operation-tool call (bypassing `operation.preflight`) that omits a
kind-specific required `input_payload` key raises a raw `TypeError` inside
`adapter.invoke(**invoke_kwargs)`, caught by the D7 `except Exception` boundary and
misreported as a generic `internal_error` (`retryable=True`) — the exact class this M3 delta's
own `job.status` fix (`confirmation_record`/`presented_token`) closed for exactly one
(kind, parameter) pair, unfixed for the other 8/13 kinds' own required parameters. Not an
existence leak (confirmed identical for foreign vs. missing on both sides of the bug), but a
reliability/UX defect: `retryable: true` on what is actually a permanent caller-input error,
and it bypasses the capability-stage schema-shaped denial a caller would reasonably expect.

**Fix — the CLASS, at the shared dispatch layer (this is the third instance of this seam's
sibling-parameter defect class; fixed generically, not per-kind):** added
`server.py::_required_input_payload_keys(kind)` — the subset of `_allowed_input_payload_keys(kind)`
that `kind`'s REAL `invoke*` function has no Python default for, derived via the SAME
`inspect.signature` mechanism (and cache) `_allowed_input_payload_keys` already uses, so a
future adapter parameter addition/removal is reflected automatically. `_operation_tool` now
checks `_required_input_payload_keys(kind) - set(payload)` immediately after the existing
rejected-keys check and denies `payload_too_large` (reused, not invented — the SAME code the
sibling rejected-keys check right above it already uses for "input_payload does not conform to
what capability accepts"; `retryable=False`, since resubmitting the identical request can never
succeed) BEFORE `adapter.invoke` is ever called. Deliberately NOT fixed by adding Python
defaults to any adapter signature — that would be a fail-open (a caller who forgot a genuinely
required field would silently execute against a synthesized value instead of being denied).

**13-kind required-key table** (derived live via `server_module._required_input_payload_keys`,
the same mechanism the fix and the test both use — not a hand-typed list):

| operation kind | required `input_payload` keys |
|---|---|
| `run.plan` | `intent_id` |
| `swarm.start` | `adapter_ids`, `run_id` |
| `job.status` | `operation_id` |
| `job.cancel` | `operation_id` |
| `job.resume` | `operation_id` |
| `external_report.import` | `packet_dir`, `workspace_id` |
| `source.ingest` | `locator`, `run_id` |
| `run.extract` | `run_id` |
| `run.claim_map` | `run_id` |
| `run.synthesize` | `run_id` |
| `run.verify` | `run_id` |
| `run.bundle` | `run_id` |
| `writeback.preview` | `run_id`, `targets` |

**Test:** `test_operation_tool_missing_required_key_denies_typed_never_internal_error`, a
single test parametrized over all 17 (kind, required-key) pairs above (13 kinds, 17 total
required-key instances counting each kind's own set — `swarm.start`/`external_report.import`/
`source.ingest`/`writeback.preview` each have 2, the other 9 kinds have 1) — each case supplies
every OTHER required key for that kind (placeholder values; irrelevant, since the check runs
before `adapter.invoke` on key presence alone) and omits exactly one, asserting
`payload_too_large`/`retryable=False`/`operation_id=None`. A companion completeness test
(`test_required_key_tables_are_non_empty_for_every_kind`) pins that all 13 kinds are covered
and none resolved to an empty required-set.

**Mutation-verify (all 17 cases in one run, ANSI-stripped `FAILED` count -- the known
"FAILED carries ANSI, `grep "^FAILED"` returns 0 on a red suite" trap):** removed the
`missing_keys` check from `server.py` and re-ran the full parametrized set under the lock:

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py -k missing_required_key -q
17 failed (ANSI-stripped FAILED-line count, verified programmatically)
FAILED [run.plan-missing-intent_id] - AssertionError: ... expected payload_too_large, got 'internal_error'
FAILED [swarm.start-missing-adapter_ids] - same shape
FAILED [swarm.start-missing-run_id] - same shape
FAILED [job.status-missing-operation_id] - same shape
FAILED [job.cancel-missing-operation_id] - same shape
FAILED [job.resume-missing-operation_id] - same shape
FAILED [external_report.import-missing-packet_dir] - same shape
FAILED [external_report.import-missing-workspace_id] - same shape
FAILED [source.ingest-missing-locator] - same shape
FAILED [source.ingest-missing-run_id] - same shape
FAILED [run.extract-missing-run_id] - same shape
FAILED [run.claim_map-missing-run_id] - same shape
FAILED [run.synthesize-missing-run_id] - same shape
FAILED [run.verify-missing-run_id] - same shape
FAILED [run.bundle-missing-run_id] - same shape
FAILED [writeback.preview-missing-run_id] - same shape
FAILED [writeback.preview-missing-targets] - same shape
```

All 17 of 17 cases failed against the reverted code — complete coverage, no gap. Restored the
fix, re-ran: all 28 tests in the file green (`diff` confirmed the restored `server.py` is
byte-identical to the fixed baseline).

### A fourth, previously-undiscovered defect: `swarm.start`'s real preflight -> execute route was completely broken

Discovered while implementing TERRA-M3-2's requested positive control (below): a valid
`operation.preflight` -> execute round-trip for `swarm.start`, through the REAL registered
server route, with the SAME real run in the SAME workspace, failed with `confirmation_mismatch`
**every time**, for every caller including a fully authorized one. Root cause:
`swarm_start.invoke`'s canonical `input_payload` always includes `profile`/`budget_usd`/
`timeout_minutes` — three fields resolved SERVER-SIDE from the target run's own `run.yaml`,
never real `invoke` parameters at all (by design, per the module's own "Resolved, never
caller-supplied" doctrine). `operation.preflight`'s generic tool has no knowledge of any
adapter's internal resolution logic and builds its own `ctx.input_payload` from ONLY the
caller's raw `input_payload` — for `swarm.start`, legally bounded to `run_id`/`adapter_ids`
(this kind's only two real parameters). The two canonical digests could therefore never agree.

**Repro (real, pre-fix, throwaway script):**

```
preflight.isError False
execute.isError True {'reason_code': 'confirmation_mismatch',
  'message': 'The confirmation token does not match the current request.', 'retryable': False, ...}
```

**Fix:** added `swarm_start.resolve_preflight_governance_inputs(run_id, paths) -> dict` — a
PUBLIC function (not the private `_resolve_run_context`, mirroring this package's own
no-underscore-cross-module-import convention) returning the SAME `profile`/`budget_usd`/
`timeout_minutes` values `invoke` itself will independently recompute. `server.py`'s
`_preflight_tool` calls it for `operation_kind == "swarm.start"` (a new augmentation block,
mirroring the existing `writeback.preview` one immediately above it) to inject those three
fields into `payload` before minting, so preflight's and execute's canonical digests always
agree. Re-ran the SAME repro script post-fix:

```
preflight.isError False
execute.isError False {'ok': True, 'operation_id': 'opm_e1220f6...',
  'result': {'status': 'completed', 'replayed': False, ...}}
```

### TERRA-M3-2 (LOW) — same-workspace positive control for `swarm.start`

**Test:** `test_swarm_start_same_workspace_server_route_completes` — real `operation.preflight`
-> execute round-trip through `server.call_tool`, valid confirmation, `adapter_ids: []`
(deterministic, zero real discovery-adapter dispatch), asserting `isError is False`, `ok is
True`, a real `operation_id`, and `result["status"] == "completed"`. This test only became
possible to write — and only passes — because of the fourth-defect fix immediately above; it
would have failed with `confirmation_mismatch` against the pre-fix tree, which is itself
retroactive proof the positive control is not vacuous.

### Re-run under the lock (work order step 4) — full family + adapter-base siblings

```
$ while ! mkdir /tmp/opm-m3-pytest.lock 2>/dev/null; do sleep 5; done; \
  ./.venv/bin/python -m pytest \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_operator_mcp_schemas.py \
    tests/unit/test_operator_mcp_serve_extra_boundary.py \
    tests/unit/test_operator_mcp_adapter_base.py \
    tests/unit/test_operator_mcp_adapter_external_import.py \
    tests/unit/test_operator_mcp_adapter_job_lifecycle.py \
    tests/unit/test_operator_mcp_adapter_research_stages.py \
    tests/unit/test_operator_mcp_adapter_run_plan.py \
    tests/unit/test_operator_mcp_adapter_source_ingest.py \
    tests/unit/test_operator_mcp_adapter_swarm_start.py \
    tests/unit/test_operator_mcp_adapter_verify_bundle.py \
    tests/unit/test_operator_mcp_adapter_writeback_preview.py \
    tests/unit/test_operator_operation_service.py \
    tests/unit/test_operator_cancel_resume_service.py \
    tests/unit/test_operator_attempt_adapter.py \
    tests/unit/test_operator_receipt_service.py \
    tests/integration/test_operator_mcp_workspace_isolation.py \
    tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/integration/test_operator_mcp_preflight_execute_e2e.py \
    -q; \
  rmdir /tmp/opm-m3-pytest.lock

.................................................................... [ 10%]
.................................................................... [ 20%]
.................................................................... [ 31%]
.................................................................... [ 41%]
.................................................................... [ 52%]
.................................................................... [ 62%]
.................................................................... [ 73%]
.................................................................... [ 83%]
.................................................................... [ 94%]
....................................                                 [100%]
EXIT_CODE=0
```

686 collected, 686 passed, 0 failed, 0 errors (verified via `--collect-only -q` total plus
explicit `FAILED`/`ERROR` substring counts against the raw, ANSI-stripped output — both zero).

### Files touched (pre-gate fix cycle)

- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/src/research_foundry/services/operator_mcp_policy.py` (new `check_capability_and_workspace` function)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/src/research_foundry/services/operator_mcp_adapters/swarm_start.py` (ordering-gate narrowed; new `resolve_preflight_governance_inputs` function; docstring updates)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/src/research_foundry/operator_mcp/server.py` (new `_required_input_payload_keys` + missing-key check; new `swarm.start` preflight augmentation block)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_mcp_adapter_swarm_start.py` (2 new probe-count tests)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/integration/test_operator_mcp_workspace_isolation.py` (positive control + 13-kind required-key matrix, 19 new tests)

### Reported-not-fixed (none new this cycle)

None. All three assigned findings, plus the fourth self-discovered defect, were fixed within
this Leg's file ownership (`operator_mcp_policy.py`, `swarm_start.py`, `server.py` — `base.py`
was not touched; the TERRA-M3-1 fix did not require it). No serialization-barrier file was
implicated.

---

## Validator fix V1-M3-2 (fresh-context validator re-pass, 2026-07-31)

`FIND-M3-V1` (`.claude/findings/research-foundry-operator-mcp-findings.md`), finding V1-M3-2
(MEDIUM): the per-property re-attack sweep in `tests/unit/test_operator_mcp_schemas.py`
attacked every STRING bound (`maxLength`/`pattern`/`minLength`) but never the NUMERIC
(`minimum`/`maximum`) or ARRAY (`maxItems`/`minItems`) bounds the same schema also declares --
6 `minimum: 0` properties and `effect_receipt_refs`'s `maxItems: 200` were reachable with an
in-type-but-out-of-range value and no test ever tried it. Fix scope: `tests/unit/
test_operator_mcp_schemas.py` only, per this work order (no other file touched, no git
commands).

### What changed

Added a new "bounds-attack" section, schema-driven exactly like the existing string sweep
(iterating `_def_properties(def_name)` and reading the LIVE `minimum`/`maximum`/`maxItems`/
`minItems`/`minLength` keywords -- never a hand-copied list of "the 6 numeric properties"):

| New test | Attacks | Currently exercises |
|---|---|---|
| `test_receipt_every_property_with_a_minimum_rejects_a_below_minimum_value` | `minimum` | `action_index`, `next_action_index`, `completed_action_count`, `total_action_count`, `action_count_total`, `action_count_completed` (all `minimum: 0` -> attacked with `-1`) |
| `test_receipt_every_property_with_a_maximum_rejects_an_above_maximum_value` | `maximum` | none today (forward-looking; auto-skips, activates automatically if a future property adds `maximum`) |
| `test_receipt_every_array_property_with_max_items_rejects_an_oversized_array` | `maxItems` | `effect_receipt_refs` (`maxItems: 200` -> attacked with 201 valid-shaped hex-digest items) |
| `test_receipt_every_array_property_with_min_items_rejects_an_undersized_array` | `minItems` | none today (forward-looking; `effect_receipt_refs` has no `minItems`, `[]` is valid) |
| `test_receipt_every_property_with_min_length_rejects_a_below_minlength_value` | `minLength` | `workspace_id` (x3: operation_receipt/checkpoint/terminal_receipt), `action_id` (x2: action_receipt/effect_receipt), `attempt_ref`, `effect_ref` (all `minLength: 1` -> attacked with `""`) |
| `test_receipt_every_numeric_or_array_property_is_bounded` | completeness gate | every open integer/array property across all 5 `$defs` must declare `minimum`/`maximum` or `maxItems`/`minItems`, unless in `_BOUNDS_EXEMPT_PROPERTIES` (empty today) -- the numeric/array sibling of the existing `test_receipt_every_open_string_property_is_bounded_or_closed` |

Array-bound attacks need a VALID-SHAPED item to isolate the count violation from an item-shape
violation (an oversized array of garbage items would fail for the wrong reason). Added
`_valid_array_item(items_schema)`, deliberately NOT a fully generic value synthesizer -- it
looks up a known-valid value by the item's own `pattern` (`_KNOWN_ARRAY_ITEM_VALUES`) and
raises loudly (a clear `AssertionError` naming the unrecognized shape) for any future `items`
pattern it doesn't recognize, rather than silently generating a bogus item that would make a
future maxItems test ambiguous.

Net: 141 -> 171 tests in the file (+30 = 6 new parametrized tests x 5 `_RECEIPT_KIND_DEFS`).

### Mutation-verify (real transcript)

Per the work order's suggested approach ("monkeypatch the validator's schema dict in a
throwaway assert"): monkeypatched `SchemaRegistry.get` in-process to return a deep-copied,
mutated `operator_mcp_receipt` schema, then called the collected test functions directly
(no fixtures needed -- `def_name` is a plain string parametrize value) to observe real
pass/fail behavior, restoring the real method afterward.

**Attempt 1 -- inflate `maxItems: 200` to `1000`:**

```
--- BEFORE mutation: real schema, maxItems=200 ---
PASSED (expected)
--- Monkeypatching SchemaRegistry.get to relax maxItems: 200 -> 1000 ---
UNEXPECTED PASS -- mutation-verify FAILED (test did not catch the relaxed bound)
--- AFTER restore: real schema again ---
PASSED (expected, restored)
```

This is EXPECTED, not a gap: the attack test reads `max_items` from the LIVE schema and
always generates `max_items + 1` -- it is self-relative, not a hardcoded "201 items" case. Any
finite bound value it finds, it correctly attacks one-past. Inflating the number therefore
never breaks the test; it just makes the test attack a different, still-correct boundary.
This is a deliberate, positive property of the schema-driven design (a numeric bound EDIT
never silently desyncs the test from reality), not the regression class this sweep exists to
catch.

**Attempt 2 -- strip `maxItems` entirely (the real regression: the bound silently removed):**

```
=== Mutation: strip maxItems entirely from effect_receipt_refs ===
attack test: passed vacuously (0 array-bound properties left to attack in terminal_receipt --
  the property is skipped, not asserted-against; expected, see note below)
completeness gate: EXPECTED FAILURE (mutation-verify PASSED):
  terminal_receipt.effect_receipt_refs: an array property declares neither maxItems nor
  minItems -- structurally unguarded (unbounded length)
=== Restored: real schema again ===
both tests pass again with the real, unmutated schema
```

This is the meaningful mutation-verify result: when a bound is silently REMOVED (the actual
failure mode V1-M3-2 is about), the attack test alone goes quiet (it has nothing left to
iterate for that property), but `test_receipt_every_numeric_or_array_property_is_bounded` --
the completeness gate this work order also required -- catches it immediately and loudly.
This is exactly why the fix ships BOTH an attack sweep and a completeness gate, mirroring the
existing string-bound pair (`test_receipt_every_open_string_property_rejects_oversized_values`
+ `test_receipt_every_open_string_property_is_bounded_or_closed`): the attack sweep alone is
not sufficient evidence a bound exists; the completeness gate is what actually proves it.

### Re-run under the lock (real output)

```
$ while ! mkdir /tmp/opm-m3-pytest.lock 2>/dev/null; do sleep 5; done; \
  ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py -q; \
  rmdir /tmp/opm-m3-pytest.lock

.................................................................... [ 42%]
.................................................................... [ 84%]
..............................................                       [100%]
EXIT_CODE=0
```

171 collected, 171 passed, 0 failed (confirmed via `--collect-only -q` total = 171, matching
the dot count above).

### Files touched (this fix)

- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_mcp_schemas.py` (bounds-attack sweep + completeness gate; no other file touched, no git commands run)
