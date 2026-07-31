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

# M2 fix cycle 1, Leg 2 completion note — adapters/writeback

Scope: F2.1 (TERRA-3), F2.2 (TERRA-7), F2.3 (TERRA-8), F2.4. Files touched:
`src/research_foundry/services/operator_mcp_adapters/run_plan.py`,
`src/research_foundry/services/operator_mcp_adapters/writeback_preview.py`,
`src/research_foundry/services/writeback.py`,
`tests/unit/test_operator_mcp_adapter_run_plan.py`,
`tests/unit/test_operator_mcp_adapter_writeback_preview.py`. No other files
edited; hard boundaries (`operator_mcp_policy.py`,
`operator_operation_service.py`, `operator_cancel_resume_service.py`,
`adapters/base.py`, `knowledge_mcp/`, `operator_mcp/server.py`) untouched.

## Finding-by-finding disposition

| Finding | Disposition |
|---|---|
| **F2.1 / TERRA-3** — `retrieval_limits` reaches `planning.plan_run` but not the canonical `input_payload` | **FIXED** in `run_plan.py`. Full 13-adapter audit performed (table below) — **0 new instances found beyond the one TERRA-3 already named.** |
| **F2.2 / TERRA-7** — unbounded `writeback.preview` target cardinality/name length, response amplification | **FIXED** in `writeback_preview.py` (adapter-level pre-normalization gate) + `writeback.py` (new closed `WRITEBACK_TARGET_NAMES` constant). |
| **F2.3 / TERRA-8** — staged preview artifacts not namespaced per operation, cross-operation overwrite/confusion | **FIXED** in `writeback.py` (`preview_writeback(..., operation_ref=...)`) + `writeback_preview.py` (passes `ctx.canonical_digest()`). Replay/cleanup semantics documented below. |
| **F2.4** — re-prove negative evidence on every outcome path | **RE-PROVEN.** Full pre-existing zero-client-construction/network suite still green unmodified; new denial path (`target_invalid`) is structurally pre-`ctx`/pre-render so it inherits the same guarantee for free, proven via `_must_not_run` monkeypatches. |

**Count of NEW digest-omission instances found beyond TERRA-3's own named instance: 0.** All 13 operation kinds audited (see table). TERRA-3 was the only instance of this defect class in this leg's file scope.

## F2.1 — full 13-adapter parameter × canonical-digest table

For each adapter: every caller-supplied parameter that reaches the wrapped canonical service, and whether it appears in the `PolicyContext.input_payload` that feeds `canonical_digest()`.

| # | operation_kind | File | Caller params forwarded to canonical service | In `input_payload`? |
|---|---|---|---|---|
| 1 | `run.plan` | `run_plan.py` | `intent_id`, `depth`, `audience`, `max_cost_usd`, `max_runtime_minutes`, `freshness_days`, `profile`, `project`, `retrieval_policy`, **`retrieval_limits`** | all ✓ (`retrieval_limits` **was ✗ — FIXED**) |
| 2 | `external_report.import` | `external_import.py` | `packet_dir`, `workspace_id`, `target_run_id`, `resume` | all ✓ |
| 3 | `writeback.preview` | `writeback_preview.py` | `run_id`, `targets` (normalized → `input_payload["targets"]` + `ctx.writeback_targets`) | all ✓ (`now` also reaches `preview_writeback` but only sets the result's `generated_at` field — never affects which targets render or their content; same non-authorization-relevant treatment D8 documents for every other adapter's `now`) |
| 4 | `source.ingest` | `source_ingest.py` | `locator`, `run_id`, `source_type`, `sensitivity`, `title`, `created_by_agent`, `fetch`, `content` (→ `content_digest`), `extra_limitations`, `extraction_status` | all ✓ |
| 5 | `job.status` | `job_lifecycle.py` | `operation_id` (bypasses `run_pipeline` entirely — bounded read, `CONFIRMATION_NOT_REQUIRED_KINDS`) | ✓ |
| 6 | `job.cancel` | `job_lifecycle.py` | `operation_id` | ✓ |
| 7 | `job.resume` | `job_lifecycle.py` | `operation_id` | ✓ |
| 8 | `run.extract` | `research_stages.py` | `run_id`, `model_profile` | all ✓ |
| 9 | `run.claim_map` | `research_stages.py` | `run_id`, `intent_id` | all ✓ |
| 10 | `run.synthesize` | `research_stages.py` | `run_id`, `model_profile`, `final`, `audience`, `sensitivity`, `llm` | all ✓ |
| 11 | `run.verify` | `verify_bundle.py` | `run_id`, `report_path`, `claim_ledger_path`, `fail_on_unsupported`, `exact_passage_override`, `disposition`, `evidence_judgment_bases` | all ✓ |
| 12 | `run.bundle` | `verify_bundle.py` | `run_id` | ✓ |
| 13 | `swarm.start` | `swarm_start.py` | `run_id`, `adapter_ids` (`profile`/`budget_usd`/`timeout_minutes` are STRUCTURALLY resolved from `run.yaml`, never caller-supplied, but included anyway) | all ✓ |

Method: for every `invoke*` function, diffed its keyword-only signature against (a) every argument forwarded to the wrapped canonical-service call inside `_run()`, and (b) every key in the `input_payload` dict built before `PolicyContext.for_configured_operator(...)`. `paths`/`now`(substrate)/`operations`/`cancel_resume`/`confirmation_record`/`presented_token`/`dry_run` are DI/protocol plumbing, not semantic operation parameters, and are excluded from this table (matches D8's own convention, restated per-adapter here).

## F2.1 fix — `run_plan.py`

```python
"retrieval_limits": dict(retrieval_limits) if retrieval_limits is not None else None,
```
added to `input_payload` (before the existing None-drop), coerced to a plain
`dict` (never the caller's own `Mapping`) for `canonical_json()`'s
JSON-primitive shape. Mirror-image check: the pre-existing None-drop
(`{k: v for k, v in input_payload.items() if v is not None}`) still applies
to this key, so two callers who both omit `retrieval_limits` collapse to the
identical digest — verified by every PRE-EXISTING `run_plan` test that never
passes `retrieval_limits` staying green unmodified (16/16).

New tests: `test_invoke_retrieval_limits_bound_into_canonical_digest_confirmation_mismatch`
(negative — a confirmation minted with `retrieval_limits` omitted denies
`confirmation_mismatch` when execute supplies a real value; `plan_run` never
called) and `test_invoke_retrieval_limits_reaches_plan_run_when_confirmation_matches`
(positive — matching value authorizes and reaches `plan_run` unchanged).

**Pre-fix proof** (scratch copy via `git show HEAD:... > file`, never `git stash`, restored after):
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_run_plan.py -q -k retrieval_limits
FAILED ...test_invoke_retrieval_limits_bound_into_canonical_digest_confirmation_mismatch
  - AssertionError: assert 'internal_error' == 'confirmation_mismatch'
  (plan_run WAS called with the mismatched retrieval_limits pre-fix — the
  test's own _must_not_run double raised, proving the replay succeeded)
FAILED ...test_invoke_retrieval_limits_reaches_plan_run_when_confirmation_matches
  - AssertionError: {'reason_code': 'confirmation_mismatch', ...}
  (pre-fix, a MATCHING retrieval_limits value denied instead — since
  invoke()'s own input_payload never included the key, the digest built
  from a payload that DOES include it never matched)
```
Post-fix: both pass; full file 16/16 passed.

## F2.2 (TERRA-7) — bound `writeback.preview` targets before normalization

New `writeback.WRITEBACK_TARGET_NAMES: frozenset[str]` — the closed
**six**-member writeback target-name vocabulary (`meatywiki`, `skillmeat`,
`ccdash`, `intenttree`, `arc`, `notebooklm`), never previously named as a
single constant anywhere in `writeback.py` (`writeback()` itself only ever
tested `"X" in targets` membership per-name, no closed-set validation of its
own). **This is the constant Leg 1 imports for F1.2** (`operation.preflight`'s
"closed, canonical source for preview target names") — `from
research_foundry.services import writeback` then `writeback.WRITEBACK_TARGET_NAMES`.
It is a strict superset of the pre-existing `WRITEBACK_PREVIEW_SUPPORTED_TARGETS`
(five names — `ccdash` excluded, file-ownership boundary on `telemetry.py`).

In `writeback_preview.py`'s `invoke_preview`, before `normalized_targets` is
built: reject the WHOLE request with `target_invalid` (never a per-target
row) if the raw (pre-dedup) sequence exceeds `_MAX_PREVIEW_TARGETS` (32) or
any individual name exceeds `_MAX_TARGET_NAME_LENGTH` (64 chars) or is not a
member of `writeback.WRITEBACK_TARGET_NAMES`. `ccdash` (a recognized name
outside the *previewable* five) still clears this gate and reaches its
existing, honest per-target `unsupported_target` status — unchanged,
covered by the pre-existing `test_invoke_preview_unsupported_target_is_governed_result`.

New tests: `test_invoke_preview_too_many_targets_denies_target_invalid_before_preview_writeback_runs`,
`test_invoke_preview_unrecognized_target_name_denies_whole_request_not_a_per_target_status`,
`test_invoke_preview_overlong_target_name_denies_target_invalid`.

**Pre-fix proof:**
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_writeback_preview.py -q \
    -k "too_many_targets or unrecognized_target_name or overlong_target_name"
FAILED test_invoke_preview_too_many_targets... - AttributeError: module '...writeback_preview'
    has no attribute '_MAX_PREVIEW_TARGETS'
FAILED test_invoke_preview_unrecognized_target_name... - AssertionError: assert True is False
    (result.ok was True pre-fix -- the garbage name reached preview_writeback
    and got a normal ok=True result instead of being rejected)
FAILED test_invoke_preview_overlong_target_name... - AttributeError: ...'_MAX_TARGET_NAME_LENGTH'
```
Post-fix: all 3 pass.

## F2.3 (TERRA-8) — namespace staged artifacts by operation

`writeback.preview_writeback` gained a new, purely additive keyword
parameter `operation_ref: str | None = None`. When `None` (every
pre-existing direct caller/test — unmodified, byte-identical behavior),
staging stays at the old `<run_dir>/staging/writeback_preview/` root. When
supplied, staging nests one level deeper:
`<run_dir>/staging/writeback_preview/<operation_ref>/`.

`writeback_preview.py`'s `invoke_preview` ALWAYS passes
`operation_ref=ctx.canonical_digest()` — the same sha256 hex digest (64
lowercase hex chars, already path-safe) `PolicyContext.canonical_digest()`
computes from the FULL canonical request (`operation_kind`, `actor`,
`idempotency_key`, `targets`, `input_payload`, `policy_snapshot_version`,
`effective_sensitivity`), available before authorization/consumption.
`preview_writeback` itself validates `operation_ref` against
`_OPERATION_REF_PATTERN` (`^[A-Za-z0-9_-]{1,128}$`, single path segment
only) defensively, even though the one real caller always passes a
pattern-safe digest — the same "never trust a value merely because today's
caller happens to be safe" posture `verify_bundle.py`'s F5 fix documents.

**Replay/cleanup semantics chosen:** `idempotency_key` is PART of the
digest, so a genuine exact-replay (same `idempotency_key` + same canonical
payload) reuses the exact same `operation_ref` and therefore the same
staged files (idempotent-overwrite preserved WITHIN one operation's own
scope, unchanged). Two DIFFERENT operations for the same run (different
`idempotency_key`, or a different `targets`/`run_id` payload) get different
digests and therefore different sub-directories — they can never overwrite
or be read as each other's content. No automated cleanup of old
`operation_ref` sub-directories is added (out of scope; each is a bounded,
deterministic, content-addressed leaf, and the JC-1 flag from Leg A's own
completion note — "staging directory access boundary is only 'inside the
run directory'" — is unchanged by this fix and remains the security lens's
own item to re-examine).

New tests: `test_invoke_preview_two_different_operations_same_run_stage_under_different_paths`
(two operations, different targets/idempotency_key, stage under different
directories; first operation's content untouched by the second's write),
`test_invoke_preview_exact_replay_reuses_same_operation_ref_staged_path`
(replay reuses the identical digest-derived path; note `_run()` — and
therefore `preview_writeback` — is never invoked a second time on a genuine
replay, so this test verifies the INDEPENDENTLY recomputed digest matches
what the first, real call actually staged under, and that file is untouched
after the replay, rather than asserting on `second.result`, which is the
bounded "replayed" partial payload documented elsewhere in this file).

**Pre-fix proof:**
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_writeback_preview.py -q \
    -k "two_different_operations or exact_replay_reuses"
FAILED test_invoke_preview_two_different_operations... - AssertionError:
    assert PosixPath('staging/writeback_preview') != PosixPath('staging/writeback_preview')
    (both operations' arc/intenttree candidates staged at the SAME parent dir)
FAILED test_invoke_preview_exact_replay_reuses... - AssertionError:
    assert '<64-hex-digest>' in 'staging/writeback_preview/arc.json'
    (no digest segment present in the staged path at all, pre-fix)
```
Post-fix: both pass.

## F2.4 — negative evidence re-proof

Every pre-existing zero-client-construction/zero-network test in
`test_operator_mcp_adapter_writeback_preview.py` and
`test_operator_mcp_writeback_preview.py` (integration) stayed green
**unmodified** across every change above (14/14 pre-existing unit +
integration tests → still 14/14 post-fix, plus 5 new). The new
`target_invalid` denial path is structurally pre-`ctx`/pre-render (it
returns before `PolicyContext.for_configured_operator` is even called), so
it inherits the same "zero client construction" guarantee for free — proven
directly by each of the 3 new F2.2 tests' `_must_not_run` monkeypatch on
`writeback.preview_writeback` itself (never invoked). No new client-
reaching code path was introduced by any of this leg's changes.

## Full validation run (post all fixes)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/test_operator_mcp_offline_import.py \
    tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_packaging.py \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_knowledge_mcp_registry.py
311 passed in 24.39s

$ flake8 src/research_foundry --select=E9,F63,F7,F82
(clean, exit 0)
```

`tests/integration/test_operator_mcp_preflight_execute_e2e.py` (Leg 1's F1.5
deliverable) does not exist yet in this worktree snapshot — not run, not
this leg's file.

## Cross-leg note for Leg 1 (F1.2)

The closed writeback-target vocabulary constant is
**`research_foundry.services.writeback.WRITEBACK_TARGET_NAMES`**
(`frozenset[str]`, six members: `meatywiki`, `skillmeat`, `ccdash`,
`intenttree`, `arc`, `notebooklm`). Import it directly — do not duplicate
the list in `server.py`.

## What the security gate should attack first

1. **F2.3's digest-derived `operation_ref` collision surface** — `ctx.canonical_digest()`
   is a sha256 of the full canonical payload; independently confirm there is
   no realistic pre-image/collision concern for this use (path-namespacing,
   not a security boundary on its own — the real boundary is still
   "inside the run directory", per JC-1, unchanged).
2. **F2.2's reason-code choice** — `target_invalid` (an existing closed
   reason code, previously used only for `TargetRef.target_ref` pattern/
   length violations in `_check_capability`) is reused here for a
   `writeback_targets` name-vocabulary violation. No new reason code was
   added (the enum stays frozen), but confirm this reuse reads correctly
   to a caller debugging a rejected request.
3. **JC-1's still-open staging-directory access boundary** (Leg A's own
   flag, unchanged by this leg): F2.3 stops cross-OPERATION confusion but
   does not add any access control beyond "inside the run directory" —
   still worth an independent re-check, as Leg A originally recommended.
4. **The F2.1 audit's completeness claim** — 0 new instances found across
   all 13 adapters; independently re-derive at least 2-3 adapters' own
   parameter × digest tables from source to cross-check this leg's own
   audit methodology, not just trust the summary table above.

Nothing disputed. All four items (F2.1-F2.4) fixed as specified in the
contract; no STOP-and-report triggered (no hard-boundary file needed
editing).
