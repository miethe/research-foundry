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

# M2 fix cycle 1 — Leg 1 (server/transport) completion note

Scope: `src/research_foundry/operator_mcp/server.py`,
`tests/integration/test_operator_mcp_server.py`, and a new
`tests/integration/test_operator_mcp_preflight_execute_e2e.py`. No other
file touched. F2.1–F2.4 (Leg 2, adapters/writeback) not touched or
re-litigated here; Leg 2's own completion note (`m2-fix-leg-2-completion.md`)
covers that side, and this note's e2e tests (writeback.preview scenarios)
exercise Leg 2's landed code as a black box.

## Finding-by-finding disposition

| Finding | Task | Disposition |
|---|---|---|
| TERRA-1 (BLOCKING) preflight never persists confirmation | F1.1 | **FIXED.** `_preflight_tool` now calls `operations.record_confirmation(issued.record)` before returning. |
| TERRA-2 (HIGH) `writeback.preview` preflight always drops `writeback_targets` | F1.2 | **FIXED.** Sourced from `input_payload["targets"]`, normalized identically to `invoke_preview`, validated against Leg 2's `writeback.WRITEBACK_TARGET_NAMES`. |
| TERRA-4 (HIGH) generic dispatcher exposes DI/reserved keys | F1.3 | **FIXED.** Per-kind allowlist derived via `inspect.signature` of the real adapter function; enforced at both `operation.preflight` and every operation tool. |
| TERRA-6 (MED) `RecursionError` escapes the D7 boundary | F1.4 | **FIXED.** Explicit-stack depth cap (`_mapping_depth`) before `json.dumps`; the whole `call_tool` body now sits inside one `try/except`. |
| ICA E2 (LOW) D4 misread as "server rejects unknown fields" | F1.4 | **FIXED as a claim correction** + pinned with a new test (silent-drop, not reject, confirmed unrelated to `payload_too_large` behavior — different layer). |
| TERRA-5 (BLOCKING→documentation) unbound base-class call bypasses the stdio guard | F1.6 | **Scoped, not redesigned**, per the orchestrator adjudication. Docstring now states the guard's exact reachability boundary; a new test pins the bypass as a known, accepted limitation. Left for the security gate, unresolved, by design. |
| F1.5 (the key test) | — | **DELIVERED.** `tests/integration/test_operator_mcp_preflight_execute_e2e.py`, 8 tests: `run.plan` (mutation kind) and `writeback.preview`, each preflight→execute, plus drift (payload, idempotency_key, expiry, replay-is-idempotent-success, target-set, cross-run/workspace) — every one proven to fail against pre-fix `server.py` first (see below). |

## A companion fix discovered while proving F1.5 (not one of the six named findings, but required for F1.1/F1.5 to actually work)

`mint_confirmation` was being called with no `now=` argument, so it fell back
to its own internal `datetime.now(timezone.utc)` — a **different clock
source** than `OperatorOperationService.consume_and_create_operation`, which
always uses `research_foundry.ids.now()` (this repo's one injectable clock,
pinned by `tests/conftest.py`'s autouse `_fixed_clock` fixture for the whole
suite). Under the pinned clock, every confirmation minted via the bare
wall-clock default has an `issued_at` **in the future relative to** the
consume-side `moment` — `operator_mcp_policy._record_expiry`'s NEW-7
anti-forgery check (`if issued_at > moment: return None`) then treats it as
unconditionally expired, regardless of elapsed time. Fixed by threading
`now=ids.now()` into the one `mint_confirmation` call site in `server.py`
(no edit to `operator_mcp_policy.py` or `operator_operation_service.py` —
this is entirely a "which clock does *this* caller pass" fix, inside my own
file). Flagging this explicitly because it is exactly the kind of gap
TERRA-1/F1.5 exists to catch — a persistence fix alone would still have
failed end-to-end without it, and no prior test caught it because nothing
before this fix cycle ever drove preflight→execute through the transport at
all.

## F1.3 — per-kind `input_payload` allowlist (derived, not hand-typed)

`_ADAPTER_INVOKE_TARGETS` maps each of the 13 `OPERATION_KINDS` to
`(adapter module attribute, real function name)`; `_allowed_input_payload_keys`
introspects that REAL function's signature via `inspect.signature` and
subtracts two fixed sets: `_SERVER_SUPPLIED_KEYS` (`idempotency_key`,
`confirmation_record`, `presented_token`, `dry_run`, `paths` — already
threaded explicitly by the server) and `_DI_ONLY_KEYS` (`now`, `operations`,
`cancel_resume`, `receipts`, `attempts` — dependency-injection/test-only,
never caller-facing). An import-time invariant asserts
`_ADAPTER_INVOKE_TARGETS`'s keys equal `policy.OPERATION_KINDS` exactly (no
silent partial coverage). Resulting allowlist, computed live against this
tree:

```
external_report.import: ['packet_dir', 'resume', 'target_run_id', 'workspace_id']
job.cancel:              ['operation_id']
job.resume:               ['operation_id']
job.status:                ['operation_id']
run.bundle:                  ['run_id']
run.claim_map:                ['intent_id', 'run_id']
run.extract:                    ['model_profile', 'run_id']
run.plan:                         ['audience', 'depth', 'freshness_days', 'intent_id',
                                    'max_cost_usd', 'max_runtime_minutes', 'profile',
                                    'project', 'retrieval_limits', 'retrieval_policy']
run.synthesize:                     ['audience', 'final', 'llm', 'model_profile', 'run_id', 'sensitivity']
run.verify:                           ['claim_ledger_path', 'disposition',
                                        'evidence_judgment_bases', 'exact_passage_override',
                                        'fail_on_unsupported', 'report_path', 'run_id']
source.ingest:                          ['content', 'created_by_agent', 'extra_limitations',
                                          'extraction_status', 'fetch', 'locator', 'run_id',
                                          'sensitivity', 'source_type', 'title']
swarm.start:                              ['adapter_ids', 'run_id']
writeback.preview:                          ['run_id', 'targets']
```

Applied identically at `operation.preflight` (so a caller cannot mint a
confirmation for an `input_payload` execute would later reject) and at
every `_operation_tool`. Rejection reason code: `payload_too_large` — a
reused, not invented, code: `operator_mcp_policy._check_capability` already
uses the SAME code for its own sibling "`input_payload` does not conform to
what capability accepts" condition (the `maxProperties` bound). Flagged for
the security gate to weigh in on if a sharper reason code is preferred.

## Test inversion (contract hard boundary 5 — loud, not silent)

`test_internal_error_envelope_for_unexpected_exception` pinned the PRE-FIX
accident: an `input_payload` key colliding with a server-reserved keyword
(`dry_run`) reached `adapter.invoke(dry_run=..., **input_payload)` and raised
a raw `TypeError` (duplicate keyword), caught only *incidentally* by the D7
`internal_error` boundary — this never closed the sharper sibling (`now`,
which does NOT collide and reached the adapter completely silently — the
actual TERRA-4 vector). Renamed to
`test_reserved_input_payload_key_maps_to_payload_too_large_envelope` and its
assertion inverted to the correct, deliberate `payload_too_large` outcome.
D7's genuine `internal_error` coverage is restored under a real unexpected
exception in `test_internal_error_envelope_for_genuine_adapter_exception`
(monkeypatched adapter raises, mirrors ICA's E6). No other existing test
was weakened or deleted.

One test I *drafted* wrong and corrected before it ever ran green: an early
draft of the replay-drift e2e test asserted a second identical
preflight→execute call would be *refused* with `confirmation_replayed`.
That assumption was wrong about this repo's own, already-shipped, un-editable
DUR-1 design: `operator_mcp_policy`'s own module docstring states exact
replay is "NOT an error" — `consume_and_create_operation`'s `_consume_locked`
returns the already-completed prior operation again (`ok=True`,
`replayed=True`, same `operation_id`), which is the correct idempotency
semantics for presenting the same confirmation for the same request twice.
The test now asserts that (`test_run_plan_execute_replayed_confirmation_is_a_zero_additional_effect_idempotent_success`)
— zero *additional* effect (same operation, not a second one), not a denial.
Not a hard-boundary-5 case (nothing shipped pinned the wrong assumption),
but flagged per its spirit.

## TERRA-5 — do not mark closed

Per the orchestrator's adjudication, the stdio guard was **not** redesigned.
`server.py`'s module docstring gained a "Scope of the stdio-only guard"
section stating precisely what is and is not covered (every REACHABLE
activation path via bound-method dispatch — yes; an UNBOUND base-class call
requiring the caller to already be executing arbitrary Python in-process —
no, and structurally cannot be). A new test,
`test_transport_guard_unbound_base_class_call_bypasses_the_guard_by_design`,
pins the bypass as real (`FastMCP.sse_app(server)` / `FastMCP.
streamable_http_app(server)` both return live apps) so no future reader
mistakes the guard for a sandbox. **This goes to the security gate
unresolved, by design** — flagging explicitly, per the adjudication's
instruction, rather than silently resolving it. The identical limitation
exists in the already-shipped `knowledge_mcp` guard.

## Pre-fix failure proof (contract hard boundary 6 — never `git stash`)

Backed up the current (fixed) `server.py` to `/tmp/m2-leg1-scratch/server_fixed.py`,
overwrote the real file in place with the pre-fix content (the exact
pre-edit content this session's own first `Read` of the file captured —
never a `git` command), ran the full regression set, then restored from the
scratch copy. Every new/changed test failed pre-fix, each with the exact
symptom its finding predicts:

```
FAILED test_operator_mcp_preflight_execute_e2e.py::test_run_plan_preflight_confirmation_is_consumable_by_execute
  - confirmation_missing ("A valid confirmation token is required...")   [TERRA-1]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_run_plan_execute_with_changed_payload_is_refused_zero_effect
  - confirmation_missing != confirmation_mismatch (never reached binding)  [TERRA-1]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_run_plan_execute_with_changed_idempotency_key_is_refused_zero_effect
  - confirmation_missing != confirmation_mismatch                          [TERRA-1]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_run_plan_execute_expired_confirmation_is_refused
  - sqlite3.OperationalError: no such table: confirmations                 [TERRA-1]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_run_plan_execute_replayed_confirmation_is_a_zero_additional_effect_idempotent_success
  - confirmation_missing                                                   [TERRA-1]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_writeback_preview_preflight_confirmation_is_consumable_by_execute
  - preflight_failed ("writeback.preview requires at least one ...")      [TERRA-2]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_writeback_preview_execute_with_changed_targets_is_refused_zero_effect
  - preflight itself never allows (assert True is False)                  [TERRA-2]
FAILED test_operator_mcp_preflight_execute_e2e.py::test_writeback_preview_execute_with_changed_workspace_target_is_refused
  - preflight itself never allows                                         [TERRA-2]
FAILED test_operator_mcp_server.py::test_reserved_input_payload_key_maps_to_payload_too_large_envelope
  - internal_error != payload_too_large (the TypeError-accident path)     [TERRA-4]
FAILED test_operator_mcp_server.py::test_di_only_input_payload_keys_are_rejected_before_reaching_the_adapter
  - adapter.invoke WAS reached for 'now' (assertion on `invoked` list)    [TERRA-4]
FAILED test_operator_mcp_server.py::test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error
  - RecursionError: Stack overflow (used 8144 kB) ...                     [TERRA-6]
FAILED test_operator_mcp_server.py::test_preflight_persists_minted_confirmation_for_later_consumption
  - sqlite3.OperationalError: no such table: confirmations                [TERRA-1]
FAILED test_operator_mcp_server.py::test_preflight_writeback_preview_allows_with_valid_targets
  - preflight_failed                                                      [TERRA-2]
FAILED test_operator_mcp_server.py::test_preflight_writeback_preview_unknown_target_name_denies_target_invalid
  - preflight_failed != target_invalid (never reached target validation)  [TERRA-2]
FAILED test_operator_mcp_server.py::test_preflight_writeback_preview_malformed_targets_shape_denies_target_invalid
  - preflight_failed != target_invalid                                    [TERRA-2]
```

All restored and re-verified green (`diff -q` confirmed the restore was
byte-identical to the pre-restore fixed file; full re-run below).

## Real command tails (post-fix, current HEAD)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/integration/test_operator_mcp_preflight_execute_e2e.py \
    tests/test_operator_mcp_offline_import.py \
    tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_packaging.py -q
............................................................................ [ 39%]
............................................................................ [ 79%]
..............................................                             [100%]
182 passed in 14.74s

$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py tests/unit/test_knowledge_mcp_registry.py -q
.................................................................................. [ 48%]
.................................................................................. [ 97%]
.....                                                                       [100%]
(all passed)

$ uv run --with flake8 flake8 src/research_foundry --select=E9,F63,F7,F82
(clean, no output)
```

Whole-tree baseline (`./.venv/bin/python -m pytest -q`, full run, no path
filter): **23 pre-existing failures, zero on the operator_mcp surface**
(grepped every `FAILED` line for `operator_mcp`/`operator-mcp`: no match).
Every failing test is in an unrelated area this leg never touched:
`test_cli_rights`, `test_contract_drift_rf_schema_version` (2),
`test_deployment_mode_cli_and_app`, `test_pdf_extractor` (3),
`test_pdf_fixture_suite`, `test_pediatric_cds_redteam_fixtures`,
`test_search_router_pdf_wiring`, `test_serve_api` (5, all `404 == 200` on
run/claim/source detail lookups), `test_swarm_drive` (2),
`test_verification_clinical_eligibility_regression` (2),
`test_verification_seam001_gate_composition`, `test_assertion_rollout` (2),
`test_report_anchors`. **Note for the record**: the contract's own
"Whole-tree baseline for reference: 4694 collected, 5 pre-existing
failures" text does not match this tree's actual current state (23) — this
is pre-existing documentation staleness in `m2-fix-contract.md`, not
something this leg introduced or is positioned to reconcile; flagging
rather than silently absorbing the discrepancy. The exact terminal
"N passed, M failed in Ts" summary line was truncated by the validation
command's own `| tail -60` before capture; the 23-count above is a direct
`FAILED` line count from the captured output, not read off a summary line.

## What the security gate should attack first

1. **TERRA-5's scoped limitation** (unbound base-class transport call) —
   the adjudication says this stays open by design; the security gate is
   the intended next reviewer of it, not a rubber stamp.
2. **The `payload_too_large` reuse for F1.3's allowlist rejection** — a
   deliberate, documented judgment call (matches `_check_capability`'s own
   convention for a shape violation), but worth a second opinion on whether
   a caller misreading `payload_too_large` as "your request was too big in
   bytes" (rather than "an unrecognized/forbidden key") is an acceptable
   ambiguity.
3. **ICA E2's silent-drop-not-reject behavior** — documented and pinned,
   deliberately NOT closed (would require reaching into SDK-internal
   `func_metadata` construction); confirm this reading of "out of this fix
   cycle's proportional scope" holds.
4. **The clock-source companion fix** (`now=ids.now()`) — confirm this is
   the right long-term answer rather than a test-environment-only patch;
   in production both `datetime.now(timezone.utc)` and `ids.now()` resolve
   to real wall time, so the fix is behavior-neutral outside tests, but the
   underlying "two different default clocks across P1/P2" gap may be worth
   a P1/P2-level follow-up (out of this leg's file ownership to fix there).

## Cross-leg notes

- Leg 2 landed `writeback.WRITEBACK_TARGET_NAMES` (the 6-name closed
  vocabulary) specifically for this leg's F1.2 fix to import — used exactly
  as coordinated (see that constant's own docstring, which names this fix
  contract). No second, independently-typed vocabulary was created.
  `test_preflight_writeback_preview_unknown_target_name_denies_target_invalid`
  and `test_preflight_writeback_preview_malformed_targets_shape_denies_target_invalid`
  exercise it.
- Leg 2's F2.3 staging-path namespacing (`operation_ref=ctx.canonical_digest()`)
  was landed and consumed transparently by this leg's e2e tests — no shape
  assumption in `server.py` depends on the staged path, so no coordination
  break occurred.
- No defect found in Leg 2's files during this leg's work; the F2.1
  (`retrieval_limits`) and F2.2 (`WRITEBACK_TARGET_NAMES`/count/length caps)
  fixes were both already present and exercised correctly by this leg's
  `run.plan` and `writeback.preview` e2e tests.

---

# Fix cycle 2 — security gate CHANGES_REQUESTED response

Scope this cycle: SEC-2, SEC-3, SEC-4, SEC-5, SEC-6, SEC-8 (mine per the
coordinator's assignment; SEC-1 is Leg 2's, fixed concurrently in
`external_import.py`/`source_ingest.py` — not touched here). SEC-7/SEC-9/
SEC-10 were not assigned to me and are not addressed in this cycle.

The gate's TERRA-5 downgrade acceptance required no further action — it
independently re-derived the live allowlist for all 13 kinds and confirmed
no caller-reachable parameter is a callable/module/service instance, so
this leg's F1.6 scoping work stands unchanged.

## Per-SEC disposition

| SEC | Severity | Disposition |
|---|---|---|
| SEC-2 | HIGH | **Partial fix, residual filed.** Per-workspace sliding-window cap (`_PREFLIGHT_MINT_MAX_PER_WINDOW=20` per `_PREFLIGHT_MINT_WINDOW_SECONDS=60.0`) enforced entirely in `server.py`, in-memory, per `build_server()` instance. Denies with `preflight_failed` (reused, closed enum) BEFORE `mint_confirmation`/`record_confirmation` run — zero effect on the throttled call itself. **Residual (see "Residual for follow-up" below):** does not evict/reclaim rows already on disk, does not dedupe by `(canonical_input_digest, idempotency_key)`, resets on process restart. The durable fix (a TTL sweep or upsert) requires `operator_operation_service.py`, which stays OFF LIMITS this cycle. |
| SEC-3 | MED | **Fixed.** `server.py`'s module docstring and `__init__.py` no longer claim "(zero effect)" — corrected to "zero effect beyond one durable `confirmations` row". `test_preflight_allow_mints_confirmation_with_zero_effect` widened to snapshot `.rf_state`'s `confirmations` table before/after and assert exactly one new row (matching the returned `confirmation_id`, status `issued`), not merely `registries/`/`runs/`. |
| SEC-4 | HIGH | **Fixed, no longer vacuous.** `test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error` rewritten to nest the deep structure under `input_payload.retrieval_limits` (a real `run.plan` parameter) instead of a bare top-level `"n"` key that F1.3's allowlist rejected first for an unrelated reason. Added a direct `_mapping_depth` assertion and a new test covering M6b (`_check_transport_payload_size` raising is still caught by the outer boundary). |
| SEC-5 | MED | **Fixed via pinning test.** `test_allowed_input_payload_keys_is_pinned_per_kind` asserts `_allowed_input_payload_keys(kind) == <exact frozenset>` for all 13 kinds (values captured live off this tree, cross-checked with a standalone script before committing to the test body). Any future adapter signature drift for any kind now fails this test, converting the gate's S1 point-in-time negative into a durable one. Code mechanism unchanged (still a real positive derivation via `inspect.signature`, per the original F1.3 spec's "derived from the real adapter signature" — the gate's own concrete "Fix direction" text asked for exactly this test, not a mechanism rewrite). |
| SEC-6 | MED | **Fixed.** Added `test_preflight_di_only_input_payload_key_denies_before_minting_with_zero_effect` (mirrors the execute-side test, covers the preflight-side check the gate's M5b mutation found uncovered) — spies on `policy.mint_confirmation` to prove it is never called, and asserts zero new `confirmations` rows on the denial. Softened the "authorization bypass" language at three sites (`_DI_ONLY_KEYS`'s comment, the `_operation_tool` rejection comment, and two test docstrings) to what the gate actually demonstrated: a caller-supplied `now` arrives as a JSON `str` and dies with `internal_error` before reaching expiry logic — this is digest-poisoning/write-amplification hygiene, not a proven expiry-authorization bypass on this transport. |
| SEC-8 | LOW | **Fixed at all five named sites.** Added a scoping note to the M2 section body of the implementation plan (the substantive site) plus lightweight footnotes at the YAML `title:` field (line ~202) and the milestone summary table (line ~343); added a scoping note to `m2-implementer-contract.md`'s epigraph and `m2-delivery-notes.md`'s header. Disambiguated `test_operation_tool_without_confirmation_denies_confirmation_missing`'s docstring, which reused "provably cannot execute" for a different guarantee (no-effect-without-confirmation, not the transport-guard scope). |

## Mutation-verification evidence (every new/changed test)

All mutations applied via in-place edit of `src/research_foundry/operator_mcp/server.py`, `__pycache__` purged before each run (`find . -name "__pycache__" -path "*/research_foundry/*" -exec rm -rf {} +`), `PYTHONDONTWRITEBYTECODE=1` set, restored from a scratch copy (`/tmp/m2-leg1-fc2-scratch/server_fixed.py`, `diff -q`-verified byte-identical after each restore) — never `git stash`, no git commands run.

1. **M6** (delete the `_mapping_depth(...) > _MAX_ARGUMENT_DEPTH` block): `test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error` **FAILS** — `AssertionError: assert 'internal_error' == 'payload_too_large'` (no depth cap, `json.dumps`/downstream processing hits `RecursionError`, caught by the outer boundary as `internal_error` instead).
2. **M6b** (hoist name/size checks outside the `try`): `test_transport_size_check_exception_maps_to_internal_error_not_uncaught` **FAILS** — raw `RuntimeError: boom ...` propagates out of `asyncio.run(...)`, uncaught.
3. **SEC-5 drift simulation** (`_DI_ONLY_KEYS` with `"now"` removed): `test_allowed_input_payload_keys_is_pinned_per_kind` **FAILS** — `AssertionError: run.plan … Extra items in the left set: 'now'`.
4. **SEC-2** (`_preflight_mint_rate_limited` call short-circuited to always allow): `test_preflight_mint_is_rate_limited_per_workspace_with_zero_effect_on_throttle` **FAILS** — the throttled call succeeds (`isError=False`) instead of denying.
5. **SEC-6 / M5b** (preflight-side allowlist check replaced with `if False:`): `test_preflight_di_only_input_payload_key_denies_before_minting_with_zero_effect` **FAILS** — `assert False is True` (the DI-poisoned preflight now allows).
6. **SEC-3** (`operations.record_confirmation(issued.record)` call removed): `test_preflight_allow_mints_confirmation_with_zero_effect` **FAILS** on its new assertion — `assert 0 == (0 + 1)` (no new `confirmations` row).

Every mutation reverted and restored (`diff -q` clean) before the next; full suite re-confirmed green after final restore.

## Real command tails (post-fix-cycle-2, current HEAD)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/integration/test_operator_mcp_preflight_execute_e2e.py \
    tests/test_operator_mcp_offline_import.py \
    tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_packaging.py \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_knowledge_mcp_registry.py -q
............................................................................ [ 21%]
............................................................................ [ 42%]
............................................................................ [ 63%]
............................................................................ [ 84%]
..................................................                 [100%]
342 passed in 25.78s

$ uv run --with flake8 flake8 src/research_foundry --select=E9,F63,F7,F82
(clean, no output)
```

## Residual for follow-up (SEC-2)

The in-memory per-workspace mint cap is a genuine but PARTIAL bound. It does
NOT: reclaim/evict the rows a pre-fix-cycle-2 run may already have written;
dedupe repeated identical requests by `(canonical_input_digest,
idempotency_key)`; survive a process restart (counter resets to zero). The
durable fix — a `status='issued' AND expires_at < now` sweep on write, or a
dedupe-upsert — requires editing `operator_operation_service.py`
(`record_confirmation`'s own INSERT), which is OFF LIMITS this fix cycle
per the coordinator's hard boundary. Requesting this be filed as a
follow-up ITT node against that file, scoped narrowly to `record_confirmation`
and the `confirmations` table only (no other P2 surface).

## Disputed / flagged, with evidence

- None of the six assigned SEC items are disputed. SEC-6's "authorization
  bypass" language correction is a claim softening I fully agree with —
  the gate's own reproduction (a caller-supplied `now` dying as `str` before
  reaching expiry logic) is decisive and I found no counter-evidence.
- SEC-2's cap values (20 per 60s per workspace) are a judgment call, not
  independently validated against production traffic patterns — flagged
  for the security gate to weigh in on if a different ceiling is preferred;
  they are conservative enough that no existing test in the operator-mcp
  suite comes close to tripping them (verified: the full suite run above
  is green with these values in place).
