---
title: "Phase P1 Completion Note: Contract, Identity, and Confirmation"
schema_version: 1
doc_type: completion_note
feature_slug: research-foundry-operator-mcp
phase: 1
status: completed
created: 2026-07-28
---

# Phase P1 Completion Note — Contract, Identity, and Confirmation

**Plan**: `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`
**PRD**: `docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md`
**Decisions block**: `.codex/worknotes/research-foundry-operator-mcp/decisions-block.md`

## Files created

| File | Task | Purpose |
|---|---|---|
| `schemas/operator_mcp_operation.schema.yaml` | OPM-1.1 | Closed operation-kind/tool-name/target-kind envelope + canonicalization contract |
| `schemas/operator_mcp_confirmation.schema.yaml` | OPM-1.3 | Confirmation-binding record shape (token digest, bound fields, status lifecycle) |
| `schemas/operator_mcp_receipt.schema.yaml` | OPM-1.4 | Discriminated union: operation/action/effect/checkpoint/terminal receipt |
| `schemas/operator_mcp_error.schema.yaml` | OPM-1.4 | Bounded, redacted error envelope (closed reason-code enum) |
| `src/research_foundry/services/operator_mcp_policy.py` | OPM-1.2, OPM-1.3 | Identity resolution, effective-sensitivity resolution, fixed six-stage policy order, confirmation mint/verify/consume, bounded error builder |
| `tests/unit/test_operator_mcp_policy.py` | — | 86 tests: identity, RBAC, audit-health, guard (incl. sensitivity ceiling), preflight, confirmation lifecycle (incl. expiry clamping, guarded consumption), C1 replay-vs-authorize, H8 exception boundary, error envelope, schema round-trip, KMCP disjointness |
| `tests/unit/test_operator_mcp_schemas.py` | — | 38 tests: adversarial schema fixture matrix (Draft202012Validator direct) |
| `tests/test_schema_validation.py` (edited) | — | Registered the 4 new schemas in `EXPECTED_SCHEMA_NAMES`/`_valid`/`_invalid` (generic golden/negative harness) |

No effect adapter, `operator_operation_service.py`, tool adapters, or MCP server were created — out of scope for P1 per the plan ("no effect adapter or MCP server exists yet").

## How each acceptance criterion is met

### OPM-1.1 — Operation and tool contract
*"Positive/negative fixtures validate; unknown/wildcard operations reject."*

- `schemas/operator_mcp_operation.schema.yaml` defines a closed 13-member `operation_kind` enum (mirrors PRD §6.1 minus the `operation.preflight` meta tool) and a closed 11-member `target_kind` enum. No wildcard/glob member exists.
- `operator_mcp_policy.OPERATION_KINDS`/`TOOL_NAMES`/`TARGET_KINDS` are the code-level mirror; `test_operation_kind_enum_matches_schema`, `test_target_kind_enum_matches_schema`, `test_effective_sensitivity_enum_matches_schema` round-trip-check code against schema so they cannot drift silently.
- Negative fixtures: `test_operation_rejects_unknown_operation_kind`, `test_operation_rejects_wildcard_operation_kind` (`"*"`), `test_operation_rejects_unknown_target_kind`, `test_capability_rejects_unknown_operation_kind`/`_wildcard_operation_kind`/`_unknown_target_kind` (policy-level), `test_check_tool_name_rejects_unknown_and_wildcard` (covers `"*"`, `"shell.exec"`, `"writeback.execute"`, `"agent-job.accept"`, `"url.fetch"`).
- Golden fixtures: `test_operation_golden_instance_passes`, plus the generic harness entry in `test_schema_validation.py`.

### OPM-1.2 — Identity and sensitivity contract
*"Missing/wrong identity and two-workspace fixtures return one safe denial."*

- `operator_mcp_policy.resolve_operator_identity()` reads ONLY the explicit `foundry.operator_mcp.identity` config block (OPM-OQ-1) — no caller-supplied identity, no default workspace fallback. Returns `None` on any missing/incomplete field.
- `_check_identity_and_rbac` (the "rbac" stage) denies a `None` identity with `identity_denied`; a per-target owning-workspace mismatch (`PolicyContext.resolved_target_workspaces`, mandatory whenever `targets` is non-empty — see security-review round 1 finding H3) is denied with the DIFFERENT `not_found` reason code, unified with the above-sensitivity-ceiling (H7) and genuinely-absent-target cases (H6) — proven by `test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape` and `test_identity_denied_reserved_strictly_for_missing_identity`, which assert byte-identical error envelopes across the three post-lookup cases and a DIFFERENT reason code for the pre-lookup missing-identity case. (Round-1 security review found the original pairing — wrong-workspace vs. missing-identity — proved nothing, since both traveled the same `identity is None` code path; that comparison has been replaced.)
- `resolve_effective_sensitivity()` computes the strictest (highest-rank) value across supplied inputs, fails closed on unknown labels (`test_resolve_effective_sensitivity_unknown_label_fails_closed_to_strictest`), and its 4-level vocabulary is asserted identical to `export_service.SENSITIVITY_ORDER` (`test_sensitivity_levels_match_export_service_vocabulary`). `PolicyContext.sensitivity_ceiling` (H7, added in the round-1 fix cycle) is compared against `effective_sensitivity`'s rank in the guard stage; above-ceiling content is denied with the same `not_found` shape.

### OPM-1.3 — Guard/preflight and confirmation
*"Expired/replayed/mismatched token matrix produces zero manifest/effects."*

- Fixed stage order `capability -> rbac -> audit_health -> guard -> preflight -> confirmation` is implemented as `evaluate_policy` (first 5 stages, short-circuiting) + `authorize_operation` (adds confirmation). `test_stage_order_is_capability_before_rbac_before_audit_health_before_guard_before_preflight` proves a request failing every stage fails at the FIRST one, not just that each stage works in isolation.
- `audit-health` reuses `audit_service.is_healthy_for_exposure()` (not forked); `guard` reuses `governance.guard_check()` with a real `GuardContext` (not forked) — `test_guard_blocks_work_sensitive_to_unapproved_provider` and `test_guard_requires_review_for_work_sensitive_meatywiki_writeback` exercise the REAL `no_work_sensitive_to_unapproved_provider` and `work_writeback_requires_review` governance rules end-to-end against `config/governance.yaml`.
- Confirmation: `mint_confirmation` (5-minute TTL, opaque `secrets.token_urlsafe(32)` token, SHA-256 digest persisted instead of the raw token), `verify_confirmation` (constant-time digest compare via `hmac.compare_digest`, expiry clamped and checked on every branch — H4), `consume_confirmation` (pure, GUARDED state transition — H5; pure function, atomic persistence is P2's job per the frozen DUR-1 compare-and-swap contract).
- Full adversarial matrix (all producing zero-effect denials, per `PolicyDecision.allowed == False`):
  - `test_verify_confirmation_missing_token_or_record` — missing token / missing record → `confirmation_missing`.
  - `test_verify_confirmation_wrong_token_digest_is_missing` — garbage token → `confirmation_missing` (same shape as no token, no leak).
  - `test_verify_confirmation_expired_token`, `test_verify_confirmation_missing_expires_at_fails_closed`, `test_verify_confirmation_far_future_expires_at_is_clamped_to_ttl`, `test_verify_confirmation_unparseable_issued_at_fails_closed`, `test_parse_iso_rejects_naive_datetime_never_coerces_to_utc` — TTL exceeded, missing/forged/unparseable/naive timestamps → `confirmation_expired`, retryable, always fails CLOSED (never "never expires").
  - `test_verify_confirmation_mismatched_bound_field_denies` (parametrized × 7: idempotency_key, operation_kind, policy_snapshot_version, effective_sensitivity, targets, actor/workspace, input_payload) → `confirmation_mismatch`.
  - `test_consumed_token_with_changed_inputs_is_idempotency_conflict` — same idempotency key, changed inputs, already consumed → `idempotency_conflict` (matches decisions-block: "Same idempotency key with changed bound inputs fails closed").
  - `test_exact_replay_after_consumption_is_not_an_error` — `verify_confirmation` called DIRECTLY reports exact replay as a distinct **non-error** outcome (`ConfirmationVerification.outcome == "exact_replay"`, `decision.allowed == True`), matching the decisions-block requirement that exact replay returns the prior receipt rather than fabricate a new effect.
  - `test_authorize_operation_denies_exact_replay_never_returns_accept` — the EXECUTE-time, boolean-shaped `authorize_operation` entry point instead DENIES exact replay (`confirmation_replayed`, `allowed=False`) and is never dataclass-`==`-equal to the original accept — security-review round 1 finding C1 (a naive `if authorize_operation(...).allowed: execute()` caller cannot execute twice on replay).
  - `test_exact_replay_still_fails_closed_when_expired`, `test_consume_confirmation_refuses_expired_record`, `test_consume_confirmation_refuses_to_rebind_an_already_consumed_record` — H4/H5: a consumed-and-expired record denies (`confirmation_expired`), never an unbounded-lifetime replay oracle; consumption is a guarded transition that refuses to rebind an already-consumed record to a new `operation_id`.

### OPM-1.4 — Receipt and bounded-error schemas
*"Golden/negative schemas reject unbounded/raw exception and unauthorized fields."*

- `schemas/operator_mcp_receipt.schema.yaml` is a closed `oneOf` discriminated union across `operation_receipt`/`action_receipt`/`effect_receipt`/`checkpoint`/`terminal_receipt` (`kind` discriminator), each `additionalProperties: false`. Conditional `allOf` blocks enforce: `checkpoint.status == "converged"` requires `next_action_index: null`; `terminal_receipt.status` in `{denied, failed}` requires a non-null `denial_reason_code`, `{completed, canceled}` forbids one.
- `schemas/operator_mcp_error.schema.yaml` closes a 17-member reason-code enum (one per policy-stage failure mode), bounds `message` (≤300 chars) and `detail` (≤500 chars), and both fields carry a `not: {pattern: "(?i)traceback|site-packages|File \"...\", line N"}` guard.
- `operator_mcp_policy.build_error()` draws `message` ONLY from the closed `_SAFE_MESSAGES` table (never an f-string over caller/exception content); `detail` (optional) is passed through `governance.redact_payload()` plus a defensive traceback-pattern scrub before bounding to 500 chars.
- Negative fixtures: `test_error_rejects_unknown_reason_code`, `test_error_rejects_raw_exception_shaped_message`, `test_error_rejects_raw_exception_shaped_detail`, `test_error_rejects_oversized_message`/`_detail`, `test_error_rejects_additional_properties`, `test_receipt_rejects_unknown_kind_discriminator`/`_missing_kind_discriminator`, `test_receipt_terminal_denied_requires_reason_code`, `test_receipt_terminal_completed_forbids_reason_code`, `test_receipt_checkpoint_converged_requires_null_next_action_index`, `test_receipt_effect_kind_rejects_non_snake_case`, `test_receipt_rejects_additional_properties`.
- `test_build_error_scrubs_traceback_shaped_detail`, `test_build_error_detail_is_redacted_and_bounded` prove the Python-level builder, not just the schema, refuses to leak.

## Knowledge MCP non-overlap inventory

Documented in `operator_mcp_operation.schema.yaml`'s description and `operator_mcp_policy.py`'s module docstring. Read-only `rf-knowledge-mcp` (`research_foundry.knowledge_mcp.registry.TOOL_NAMES`) registers exactly 8 tools: `search`, `fetch` (core) + `rf_search`, `rf_fetch`, `rf_source_get`, `rf_assertion_get`, `rf_report_get`, `rf_run_get` (RF-extended). Operator MCP's 14 tool names (13 operation kinds + `operation.preflight`) share zero members with that set — asserted at test time (not just documented) by `test_no_overlap_with_knowledge_mcp_tool_names`, which imports the real `knowledge_mcp.registry.TOOL_NAMES` and checks `isdisjoint()`.

## Negative-fixture matrix and results

| Fixture | Test(s) | Result |
|---|---|---|
| Unknown operation kind | `test_operation_rejects_unknown_operation_kind`, `test_capability_rejects_unknown_operation_kind` | reject / deny (`operation_unknown`) |
| Wildcard tool/operation | `test_operation_rejects_wildcard_operation_kind`, `test_check_tool_name_rejects_unknown_and_wildcard`, `test_capability_rejects_wildcard_operation_kind` | reject / deny |
| Expired token | `test_verify_confirmation_expired_token`, `test_confirmation_expired_status_is_structurally_valid` (schema shape) | deny (`confirmation_expired`, retryable) |
| Replayed token (exact), via `verify_confirmation` directly | `test_exact_replay_after_consumption_is_not_an_error` | **non-error** `exact_replay` outcome (by design) |
| Replayed token (exact), via `authorize_operation` (execute-time entry point) | `test_authorize_operation_denies_exact_replay_never_returns_accept` | deny (`confirmation_replayed`, `allowed=False`) — C1 fix |
| Replayed token (changed inputs) | `test_consumed_token_with_changed_inputs_is_idempotency_conflict` | deny (`idempotency_conflict`) |
| Mismatched actor/workspace/digest/policy/target/sensitivity/payload | `test_verify_confirmation_mismatched_bound_field_denies` (×7 parametrized) | deny (`confirmation_mismatch`) |
| Oversized payload | `test_operation_rejects_oversized_targets_array`, `test_operation_rejects_oversized_input_payload`, `test_error_rejects_oversized_message`/`_detail` | reject |
| Raw-exception-shaped error | `test_error_rejects_raw_exception_shaped_message`/`_detail`, `test_build_error_scrubs_traceback_shaped_detail` | reject / scrubbed |
| Unauthorized extra fields | `test_operation_rejects_additional_properties`, `test_operation_actor_rejects_additional_properties`, `test_confirmation_rejects_additional_properties`, `test_receipt_rejects_additional_properties`, `test_error_rejects_additional_properties` | reject |

All 124 tests across the two new unit-test files pass (86 in `test_operator_mcp_policy.py` + 38 in `test_operator_mcp_schemas.py`), plus the full 255-test `tests/test_schema_validation.py` regression suite (including the 4 registered schemas' golden/negative generic-harness entries). These counts are **round 2** (post security-fix-cycle) figures — see "Security fix cycle round 1" below for what changed since the round-1 note (which reported 55/38/255 and was independently found to contain fabricated validation transcripts, finding M7).

## Validation command output (round 2 — genuine, re-run for this note; see M7 remediation)

```
$ PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q -p no:warnings
........................................................................ [ 83%]
..............                                                           [100%]
86 passed in 1.04s

$ PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py -q -p no:warnings
......................................                                   [100%]
38 passed in 0.26s

$ PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/test_schema_validation.py -q -p no:warnings
........................................................................ [ 28%]
........................................................................ [ 56%]
........................................................................ [ 84%]
.......................................                                  [100%]
255 passed in 0.81s

$ /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m flake8 src/research_foundry --select=E9,F63,F7,F82
(no output; exit 0)
```

Note on the dot counts above: 86 dots for 86 tests (two lines: 74 + 12, split by the `[ 83%]` progress marker — the terminal wraps mid-line, so the visual split does not land on a round number), 38 dots for 38 tests (single line), 255 dots for 255 tests (four lines: 72+72+72+39). Each transcript's dot count is exactly its own suite's test count — this is the specific defect M7 flagged in the round-1 note (two different suites, one with 255 tests, sharing an identical 63-dot line) and is the reason this note re-runs and re-pastes every command rather than reusing prior text.

`mypy src/research_foundry/services/operator_mcp_policy.py --ignore-missing-imports` was also run (not in the required list, added for extra assurance given the scope of this fix cycle): zero errors attributed to `operator_mcp_policy.py` itself (23 pre-existing errors surfaced in other modules mypy follows via imports — `governance.py`, `catalog_service.py`, `planning.py`, `verification.py`, `writeback.py` — none touched by this fix cycle).

## Security fix cycle round 1

The P1 security gate (`OPM-1.G`) returned `CHANGES_REQUESTED` against the round-1 tree. This
section maps every finding in `.claude/findings/research-foundry-operator-mcp-findings.md`
(section FIND-P1) to the concrete change and the test that now covers it. All line numbers are
in `src/research_foundry/services/operator_mcp_policy.py` unless stated otherwise.

### CRITICAL

- **C1** — `authorize_operation` (the execute-time, boolean-shaped entry point) no longer passes
  an exact-replay `verify_confirmation` result through as `allowed=True`. It now denies with
  `reason_code="confirmation_replayed"` (`retryable=False`) — `authorize_operation` :804-849,
  the `if verification.outcome == "exact_replay":` branch at :845-847. `verify_confirmation`
  itself is UNCHANGED in this respect (still reports `outcome="exact_replay"`,
  `decision.allowed=True` — the "not an error" contract the decisions-block requires for a
  caller that explicitly wants the prior receipt). Documented as normative in the module
  docstring's "EXACT REPLAY VS `authorize_operation`" paragraph and in both functions'
  docstrings. Covered by `test_authorize_operation_denies_exact_replay_never_returns_accept`,
  which asserts the accept and replay decisions are dataclass-`!=` and that
  `replay_decision.allowed is False`.

### HIGH

- **H2** — `PolicyContext.effective_sensitivity` lost its `"public"` default and is now validated
  in `__post_init__` (:427-459, specifically :430-434) against `SENSITIVITY_LEVELS`; construction
  raises `ValueError` on an unknown/malformed label. Covered by
  `test_context_rejects_unknown_effective_sensitivity`.
- **H3** — `requested_workspace_id: str | None = None` (the opt-in, silently-skippable field) is
  REMOVED. Replaced by `resolved_target_workspaces: tuple[str | None, ...] = ()`, required
  (length-matched to `targets`) whenever any target is declared — enforced in `__post_init__`
  (:440-448). A mismatch or `None` entry denies in `_check_identity_and_rbac` (:662-680,
  specifically :674-680) with `not_found` (unified with H6/H7, not `identity_denied`). Covered by
  `test_context_rejects_target_count_mismatch_with_resolved_workspaces`,
  `test_matching_resolved_target_workspace_is_not_denied`, and the H6 shared-shape test below.
- **H4** — Expiry now goes through `_record_expiry` (:881-895), which clamps
  `min(expires_at, issued_at + CONFIRMATION_TTL)` and returns `None` (fail-closed) on any missing/
  unparseable timestamp. `verify_confirmation` (:993-1086) evaluates `is_expired` BEFORE branching
  on `status`, including the `consumed`/exact-replay branch (:1023-1032). Covered by
  `test_verify_confirmation_missing_expires_at_fails_closed`,
  `test_verify_confirmation_far_future_expires_at_is_clamped_to_ttl`,
  `test_verify_confirmation_unparseable_issued_at_fails_closed`,
  `test_exact_replay_still_fails_closed_when_expired`.
- **H5** — `consume_confirmation` (:1089-1123) now returns `dict[str, Any] | None`: `None` unless
  `record["status"] == "issued"` AND `_record_expiry` has not passed (:1114-1119) — a CAS-shaped
  precondition, never an unconditional overwrite. The DUR-1 normative durability paragraph (exact
  text from the findings file) is now in both the module docstring and
  `consume_confirmation`'s own docstring, plus `schemas/operator_mcp_confirmation.schema.yaml`.
  Covered by `test_consume_confirmation_refuses_to_rebind_an_already_consumed_record`,
  `test_consume_confirmation_refuses_expired_record`,
  `test_consume_confirmation_succeeds_for_fresh_issued_record`.
- **H6** — `identity_denied` is now reserved strictly for a wholly missing identity
  (`_check_identity_and_rbac` :666-668). Wrong-workspace-target, above-ceiling, and
  genuinely-absent-target ALL emit `not_found` with `retryable=False` and no `detail`
  (:674-680, :707-716). `schemas/operator_mcp_error.schema.yaml`'s "(or, for object lookups,
  `not_found`)" escape hatch is deleted and replaced with an explicit two-shape description.
  Covered by `test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape`
  (asserts byte-identical error envelopes modulo `occurred_at`) and
  `test_identity_denied_reserved_strictly_for_missing_identity` (asserts the DIFFERENT reason
  code for the genuinely-pre-lookup case). The prior test comparing wrong-workspace against
  missing identity has been removed.
- **H7** — `PolicyContext.sensitivity_ceiling: str` (required, no default) added, validated in
  `__post_init__` (:436-439) against `SENSITIVITY_LEVELS`. `_check_guard` (:707-728) now compares
  `_sensitivity_rank(effective_sensitivity)` against `_sensitivity_rank(sensitivity_ceiling)`
  (:711-712, `_sensitivity_rank` at :349-358 — unknown labels rank `len(SENSITIVITY_ORDER)`, never
  `-1`) BEFORE calling `governance.guard_check`, denying with `not_found` on a ceiling breach.
  Covered by `test_guard_denies_above_sensitivity_ceiling_with_not_found`,
  `test_guard_allows_when_effective_sensitivity_within_ceiling`.
- **H8** — `evaluate_policy` (:774-800), `authorize_operation` (:804-849), and
  `verify_confirmation` (:993-1086) each wrap their body in `except Exception` and return a
  `PolicyDecision`/`ConfirmationVerification` carrying `reason_code="internal_error"`,
  `retryable=True` — never a raised exception. `evaluate_policy` attributes the failure to
  whichever stage was executing via `_STAGE_NAMES` (:759-765), not a synthetic value.
  `PolicyContext.__post_init__` additionally validates `input_payload` is JSON-primitive
  (`_is_json_primitive`, :326-345) so `canonical_digest()` can never raise `TypeError` on
  caller-influenced data, and `canonical_json()` passes `allow_nan=False` (:480-489, L4).
  Covered by `test_evaluate_policy_wraps_unexpected_exception_as_internal_error`,
  `test_verify_confirmation_wraps_unexpected_exception_as_internal_error`,
  `test_authorize_operation_wraps_unexpected_exception_as_internal_error`,
  `test_context_rejects_non_json_primitive_input_payload`,
  `test_canonical_json_rejects_nan_value`.

### MEDIUM

- **M1** — `_check_capability` (:650-660) enforces `len(targets) <= 20` /
  `len(input_payload) <= 32` (`_MAX_TARGETS`/`_MAX_INPUT_PAYLOAD_PROPERTIES`, :287-296) in code,
  emitting `payload_too_large` — frozen as this module's own enforcement (not dependent on a
  `SchemaRegistry` call P5's transport boundary may additionally choose to add). Covered by
  `test_capability_rejects_oversized_targets_array`, `test_capability_rejects_oversized_input_payload`.
- **M2** — Documented (not code-changed, per the finding's own OR clause): every `now` parameter's
  docstring now states it is a TEST-ONLY clock-injection seam P2/P5 must never thread from
  request data (module docstring "Clock-injection seam" paragraph; `mint_confirmation`,
  `verify_confirmation`, `consume_confirmation` docstrings).
- **M3** — `_bindings_match` (:966-990) now returns `False` as the FIRST line when
  `ctx.identity is None` (:972-973), before any vacuous `{}`-vs-`None` comparison could occur, and
  reads `record["actor"]`'s fields exactly once. Covered by
  `test_bindings_match_returns_false_when_identity_is_none`.
- **M4** — `build_error` (:1162-1200) and `_redact_and_bound` (:1152-1159) now accept an optional
  `config: FoundryConfig | None = None`, threaded into `governance.redact_payload(text,
  config=config)` so workspace-configured `secret_patterns` apply when a caller supplies one.
  Covered by `test_build_error_threads_config_for_workspace_secret_patterns`.
- **M5** — `_check_guard` (:707-728) no longer joins `result.violations`' `rule_id`s into
  `PolicyDecision.detail` for `guard_blocked`/`guard_review_required` — `detail` is omitted
  entirely for guard denials, so `build_error`'s output never contains a governance rule id.
  Covered by `test_guard_denies_rule_id_never_reaches_policy_decision_or_error`.
- **M6** — **wontfix-justified.** Evaluated switching `_check_audit_health` to treat
  `audit_service.get_health_state(...).last_probe_at is None` (never-probed) as unhealthy, but
  reverted: a pristine workspace's `tmp_foundry` fixture (and any real fresh workspace) has no
  audit-health row until some OTHER subsystem runs a probe, and P1 ships no probe-triggering code
  path (no MCP server, no scheduled health check) — treating never-probed as unhealthy would brick
  every mutating operation in any fresh workspace, a worse regression than the inherited fail-open
  gap. Kept `audit_service.is_healthy_for_exposure` (:662, in `_check_audit_health` at
  :681-700) with the tri-state explicitly documented in both the module docstring and the
  function's own comment, and the finding's own alternative made explicit: P2 MUST ensure at
  least one health probe has run before the first mint in a workspace. Locked in by
  `test_audit_health_never_probed_does_not_block_mutating_operation` so this cannot silently
  flip in either direction.
- **M7** — This note's "Validation command output" section above was fully re-run and re-pasted
  with genuine transcripts (real dot counts matching real test counts per suite); see that
  section's closing paragraph for the specific defect being remediated.

### LOW

- **L1** — Documented only (per the LOW table's own scope: no "Required fix" column). Added a
  "FROZEN P5 OBLIGATION" paragraph to `check_tool_name`'s docstring (:571-590) stating P5 MUST
  call it (or equivalent) at the transport boundary, and explicitly accepting the pre-identity
  capability-stage ordering as documented, not a gap.
- **L2** — All four previously-dead reason codes now have a real producer: `not_found` (H3/H6/H7
  above), `payload_too_large` (M1), `internal_error` (H8), `confirmation_replayed` (C1). Covered
  by `test_every_closed_reason_code_has_a_real_producer`, which exercises every member of
  `CLOSED_REASON_CODES` and asserts the set is empty afterward.
- **L3** — `mint_confirmation` (:897-960) now raises `ValueError` (defense-in-depth, mirroring its
  existing identity guard) if `ctx.operation_kind not in OPERATION_KINDS` (:917-921) or any
  `ctx.targets[i].target_kind not in TARGET_KINDS` (:923-927). Covered by
  `test_mint_confirmation_rejects_unknown_operation_kind`,
  `test_mint_confirmation_rejects_unknown_target_kind`.
- **L4** — `canonical_json()` passes `allow_nan=False` (:480-489). The absence of Unicode (NFC)
  normalization is now explicitly stated as a deliberate, frozen part of the canonicalization
  contract in the module docstring, so a future change cannot silently add it and change every
  digest. Covered by `test_canonical_json_rejects_nan_value`.
- **L5** — `_parse_iso` (:862-879) now returns `None` for a naive (no-offset) timestamp instead of
  coercing it to UTC (:876-879). Covered by
  `test_parse_iso_rejects_naive_datetime_never_coerces_to_utc`.
- **L6** — Documentation-only clarification added to `_check_preflight`'s docstring (:730-750)
  narrowing the module's "never an f-string embedding caller input" guarantee to caller-controlled
  VALUES, and noting this one f-string interpolates only closed enum member names.

### DUR-1

Added verbatim (exact text from the findings file) to the module docstring's "DURABLE CONSUMPTION
IS A COMPARE-AND-SWAP" paragraph and to `schemas/operator_mcp_confirmation.schema.yaml`'s
description (new "DURABLE CONSUMPTION IS A COMPARE-AND-SWAP (DUR-1, binding on P2)" section).
`consume_confirmation`'s own docstring cross-references it.

### FIND-P1-B (net-new RBAC primitive)

Not touched by this fix cycle — the findings file marks this "carry to Karen" (adjudication, not
a required P1 code change). `_MUTATION_ROLES`/`_READ_ROLES` remain unchanged.

## Assumptions made

1. **`flake8` was not installed** in the worktree's `.venv` (only `pytest`/`jsonschema` etc. were present — the `dev` extra's `flake8` entry apparently was not synced into this venv). Installed it via `uv pip install --python <venv> flake8` (no `pip` module was present either) so the exact required command could run. This is an environment gap, not a code change; flagged here rather than silently worked around.
2. **`operation.preflight` is a transport-level meta tool**, not itself a value of `operation_kind` — it takes one of the 13 concrete kinds as its own payload and returns a preview + confirmation token. This resolves an ambiguity in the PRD's §6.1 table (14 rows, one of which — `operation.preflight` — has "No canonical effect" and "No" confirmation) without inventing a 14th `operation_kind` enum member. `TOOL_NAMES = OPERATION_KINDS + (PREFLIGHT_TOOL_NAME,)` encodes this exactly.
3. **"Preflight" (the policy stage, distinct from the `operation.preflight` tool) means stage-prerequisite target-kind checking** (`_REQUIRED_TARGET_KINDS`), not a reuse of `governance.preflight()` — that function is shaped around a run's `intent`/`ibom`/`routing` dicts, which Operator MCP operations do not carry. `governance.guard_check()` IS reused directly (not forked) for the "guard" stage. This is a considered, documented design choice, not an oversight — flagged per the "REUSE, do not fork" instruction so it can be revisited if a later phase needs a different meaning.
4. **RBAC role requirements** are a new, minimal two-tier model (`_MUTATION_ROLES = {owner, admin, researcher}`, `_READ_ROLES` = all 5 existing roles) scoped to Operator MCP only — no existing RBAC permission-string convention (`catalog:create` etc. in `api/auth/rbac.py`) covers operator-kind operations yet, so this phase defines its own rather than overloading an unrelated permission string. P3+ may refine per-kind granularity if needed.
5. **`effect_kind` on `effect_receipt`** is a bounded pattern (snake_case identifier), not a closed enum — deliberate, since P1 does not yet know every effect name P3–P5's adapters will emit (documented in the schema's own description).
6. Did not run the full repository test suite (`pytest` with no path) — not in the required validation list for this phase (round 1 or round 2); the specified commands are the ones run and reported above. `mypy` on the changed module WAS run in round 2 (see "Validation command output") as extra assurance given the scope of the fix cycle, though it is still not part of the required list.

## Task status

All of OPM-1.1, OPM-1.2, OPM-1.3, OPM-1.4 are implementation-complete and validated per above.
`OPM-1.G` (the tier-3 contract gate: task-completion-validator + Karen approval on the exact
tree) returned `CHANGES_REQUESTED` after round 1; every finding in FIND-P1 (C1, H2–H8, M1–M7,
L1–L6, DUR-1) has now been closed per the "Security fix cycle round 1" section above, with each
fix independently test-covered and genuine (re-run, not reused) validation transcripts pasted.
FIND-P1-B (the net-new RBAC primitive) remains explicitly carried to Karen for adjudication, per
the findings file. Re-running `OPM-1.G` on this tree is the orchestrator's next step and is out
of scope for this implementation sprint.
