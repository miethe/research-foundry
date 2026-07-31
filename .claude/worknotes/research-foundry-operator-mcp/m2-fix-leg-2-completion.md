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

<!-- FIX CYCLE 2 SECTION APPENDED BELOW THE ORIGINAL FIX-CYCLE-1 NOTE -->


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

---

# Fix cycle 2 — SEC-1 (BLOCKING) + SEC-7 (MED) + path-containment sweep

Security gate: `.claude/findings/m2-security-gate.md`. Scope: SEC-1
(BLOCKING, `external_import.py` `packet_dir`), SEC-7 (MED, `verify_bundle.py`
`report_path`/`claim_ledger_path`), and the full 13-adapter path-containment
enumeration the coordinator's fix-cycle-2 message required (the actual
point of this cycle, mirroring F2.1's treatment). No hard-boundary file
edited; `operator_mcp/server.py` untouched (Leg 1's concurrent territory).

## SEC-1 / SEC-7 disposition

| Finding | Disposition |
|---|---|
| **SEC-1 (BLOCKING)** — `packet_dir` unbounded arbitrary-path reach | **FIXED.** `external_import.py`'s `_run()` now requires `packet_dir` to resolve (symlinks included) inside `resolved_paths.root` before `import_external_report` is ever called. Containment root is the WHOLE configured workspace tree (`paths.root`), re-derived, never caller-supplied — not merely one run's directory, since staging-only imports (`target_run_id=None`) have no run tree to bind to. Two pre-existing tests (`test_invoke_result_matches_direct_import_call`, `test_exact_retry_does_not_duplicate_import_receipt`) had their `packet_dir` fixture moved from a sibling `tmp_path` location to inside `tmp_foundry.root` — flagged loudly (boundary rule 5: "invert a test that pins wrong behavior") — those two are the ONLY pre-existing tests that reach `_run()` for a real execution; the other four are `dry_run=True` and were never affected. |
| **SEC-7 (MED)** — `report_path`/`claim_ledger_path` unusable over MCP; F5 guard dead code on that route | **FIXED via coerce-then-guard** (the first of the gate's two offered directions). `invoke_verify`'s `_run()` now coerces both to real `Path` objects (`Path(value)`, wrapped so a genuinely uncoercible JSON type denies the same way a containment violation does) BEFORE either the prerequisite check or the F5 `_explicit_path_within_run` guard ever inspects them — making that guard actually EXECUTE on the MCP route (JSON strings) instead of type-crashing before it can run. Chose coercion over "reject those keys on the MCP route" because rejecting would remove real, documented functionality (explicit report/ledger overrides) that has nothing wrong with it once the guard actually runs. |

## Full 13-adapter path-containment table

For every adapter: every caller-supplied value that becomes, joins, or resolves to a filesystem path, and what structurally bounds it.

| # | operation_kind | File | Path-bearing input(s) | Reaches | Bound by |
|---|---|---|---|---|---|
| 1 | `run.plan` | `run_plan.py` | `intent_id` | `planning.load_intent` (`paths.intents_active / f"{intent_id}.yaml"` — an f-string join; absolute `intent_id` DISCARDS the left operand entirely, per `Path.__truediv__` semantics) | **FIXED (NEW instance)** — `_resolved_within(paths.intents_active, ...)` in BOTH `_resolve_intent_sensitivity` (pre-auth) AND again inside `_run()` (closes the residual exposure: a permissive ceiling could otherwise let `_run()` reach `planning.plan_run`, which calls `load_intent` a second time) |
| 2 | `external_report.import` | `external_import.py` | `packet_dir`; `target_run_id` | `import_external_report` (recursive `os.scandir`); `_resolve_run_workspace_id` → `run_dir` | **FIXED**: `packet_dir` = SEC-1 (this cycle's assigned BLOCKING finding). `target_run_id` = **NEW instance**, `_resolved_within(paths.runs, ...)` in `_resolve_run_workspace_id`, before the read |
| 3 | `writeback.preview` | `writeback_preview.py` | `run_id` | `_resolve_run_context` → `run_dir`; ALSO a write-side exposure — `writeback.preview_writeback`'s own staging root derives from the same unguarded `run_dir` | **FIXED (NEW instance)** — `_resolved_within(paths.runs, ...)`; closes both the read (context resolution) and, transitively, the write (RBAC denies before `_run()`/`preview_writeback` for a `None` workspace_id) |
| 4 | `source.ingest` | `source_ingest.py` | `run_id`; `locator` | `_resolve_run_context` → `run_dir`; `source_cards.ingest_source` (`Path(locator).exists()` — unconditionally reads ANY existing local file as full text content, no containment at all, whenever `content` is not already supplied) | **FIXED (2 NEW instances)** — `run_id` via `_resolved_within(paths.runs, ...)`; `locator` via `_resolved_within(paths.root, ...)` inside `_run()`, gated on `content is None and not _looks_like_url(locator)` (URL locators and caller-supplied content are unaffected) |
| 5 | `job.status` | `job_lifecycle.py` | `operation_id` | `OperatorOperationService`/`OperatorReceiptService`/`OperatorAttemptAdapter` — SQLite-backed (`operator_operations.db`), no filesystem path built from `operation_id` anywhere | **Checked, safe — no fix needed.** Empty row. |
| 6 | `job.cancel` | `job_lifecycle.py` | `operation_id` | same DB-only surface | **Checked, safe — no fix needed.** |
| 7 | `job.resume` | `job_lifecycle.py` | `operation_id` | same DB-only surface | **Checked, safe — no fix needed.** |
| 8 | `run.extract` | `research_stages.py` | `run_id` | `_resolve_run_context` → `run_dir` (shared helper, also used by `run.claim_map`/`run.synthesize`) | **FIXED (NEW instance)** — `_resolved_within(paths.runs, ...)` |
| 9 | `run.claim_map` | `research_stages.py` | `run_id`; `intent_id` | `run_id` as above; `intent_id` reaches `claim_mapping.build_claim_ledger` but is stored ONLY as a plain metadata string field in the ledger YAML — traced its full use, never reaches `Path(...)`/`open`/anywhere | `run_id` FIXED (shared helper above); **`intent_id` checked, safe — no fix needed** (verified by reading `claim_mapping.py` end to end: `intent_id` is written into `{"intent_id": intent_id}` dict entries only) |
| 10 | `run.synthesize` | `research_stages.py` | `run_id`; `model_profile` | `run_id` as above; `model_profile` reaches `synthesis.synthesize_report` but is "recorded for provenance only" (per that module's own docstring) — never path-joined | `run_id` FIXED (shared helper above); **`model_profile` checked, safe — no fix needed** |
| 11 | `run.verify` | `verify_bundle.py` | `run_id`; `report_path`; `claim_ledger_path` | `run_id` via `_resolve_run_context` → `run_dir` (shared with `run.bundle`); `report_path`/`claim_ledger_path` via `verification.verify_report` (F5's own pre-existing containment target) | `run_id` **FIXED (NEW instance)** — reused THIS module's own `_explicit_path_within_run` (F5's primitive, generic over its `run_root` argument, applied here to `paths.runs`) instead of duplicating a new helper. `report_path`/`claim_ledger_path` = **SEC-7** (coerce-then-guard, above) |
| 12 | `run.bundle` | `verify_bundle.py` | `run_id` | `_resolve_run_context` → `run_dir` (same shared helper as #11) | **FIXED** (same fix as #11, shared helper) |
| 13 | `swarm.start` | `swarm_start.py` | `run_id`; `intent_id` (read from `run.yaml`, not directly caller-supplied); `adapter_ids` | `run_id` via `_resolve_run_context` → `run_dir`; `intent_id` via `planning.load_intent` (same vulnerable f-string join as #1, reached one hop indirectly); `adapter_ids` reaches `swarm_service.run_swarm`, which checks each id against a REGISTRY/allowlist gate (`swarm_service.py`'s own docstring) — never path-joined, confirmed by reading `run_swarm`'s own validation | `run_id` **FIXED (NEW instance)** — `_resolved_within(paths.runs, ...)`. `intent_id` **FIXED (NEW instance, defense-in-depth)** — same `_resolved_within` helper applied before the intent lookup inside `_resolve_run_context`; sourced from an already-contained `run.yaml`, not directly caller-reachable today, but this module does not assume that pipeline integrity holds forever. `adapter_ids` **checked, safe — no fix needed** |

**Count of NEW unbounded-path instances found beyond `packet_dir` (SEC-1): 9** — `external_import.target_run_id`, `writeback_preview.run_id`, `source_ingest.run_id`, `source_ingest.locator`, `run_plan.intent_id`, `swarm_start.run_id`, `swarm_start.intent_id` (defense-in-depth), `research_stages.run_id`, `verify_bundle.run_id`. (SEC-7's `report_path`/`claim_ledger_path` was already the coordinator's OWN assigned finding, not counted as a "new" discovery here.) Every adapter's declared caller-facing parameters were traced end-to-end to their canonical-service call site or metadata-only use before being marked "safe" — three rows (`run.claim_map.intent_id`, `run.synthesize.model_profile`, `swarm.start.adapter_ids`) are explicit checked-safe results, not omissions.

## Method

For every `invoke*`/`_resolve_run_context`-style function: traced every caller-supplied parameter to (a) whether it is ever passed to `Path(...)`, `open`, `os.scandir`, `.exists()`, `.glob()`, or a canonical-service function whose OWN docstring/body does so, and (b) whether ANY structural check bounds it before that point. The `run_id` class was found by re-deriving `FoundryPaths.run_dir`'s implementation (`self.runs / run_id`) and noting `Path.__truediv__`'s two hazards: an absolute right-hand operand discards the left entirely, and `".."`/`"."` are legal single-path-component strings that `operator_mcp_policy._TARGET_REF_PATTERN` (no `/` allowed) does not reject — but that pattern only runs during `_check_capability`, well AFTER every `_resolve_run_context`-style function has already attempted its read. The `intent_id` class was found the same way, one hop through `planning.load_intent`'s own `paths.intents_active / f"{intent_id}.yaml"` join. The `locator` class was found by reading `source_cards.ingest_source`'s full body (not just its signature) and noting the unconditional `Path(locator).exists() and .is_file()` branch.

## Containment helper — one shape, six independent copies

Every fix uses the SAME resolve-then-contain shape `verify_bundle.py`'s pre-existing F5 `_explicit_path_within_run` established: resolve both root and candidate (symlinks included), require the candidate to land at or beneath root, never probe existence on a path outside the boundary (an existence check itself would be an F6/H6-shaped oracle). Duplicated independently in `external_import.py`, `source_ingest.py`, `run_plan.py`, `swarm_start.py`, and `research_stages.py` as `_resolved_within`; `verify_bundle.py` and `writeback_preview.py` reuse/mirror the SAME shape (`verify_bundle.py` literally reuses its own pre-existing `_explicit_path_within_run` for the new `run_id` check rather than duplicating; `writeback_preview.py` has its own `_resolved_within` copy). This is deliberate, matching the established "adapter modules do not cross-import each other's private helpers" convention this whole family already follows — flagged in case the security lens would prefer a shared module instead.

## Mutation-verification evidence (per new guard, done INSIDE this fix step)

All 12 guards below were verified by reverting ONLY that guard's specific condition (`if not X:` → `if False and not X:`, or removing the coercion block) in the live source file (never `git stash`), clearing `__pycache__` before AND after every iteration (per the coordinator's explicit note that stale `.pyc` has produced false greens in this repo before), running the specific new test(s), confirming a REAL failure, then restoring from an in-memory backup and clearing `__pycache__` again.

**A design flaw was caught and fixed during this process itself**: the first mutation pass (all 12) showed EVERY guard's tests still passing under mutation — a false "mutation survived" signal. Root cause: several "denies X" tests used an assertion-RAISING spy (`_must_not_run`) on the canonical service, and that spy's OWN crash converges to the exact SAME `ok=False`/`internal_error` envelope a genuine guard denial produces (via `run_actions`'s shared exception boundary) — so the reason-code assertion alone could not distinguish "the guard denied" from "the guard was removed and the trap fired instead." Separately, several direct-unit-level tests (`_resolve_run_context("..", ...)` → asserts `None`) were VACUOUSLY true even with the guard removed, because the escape target (`tmp_foundry.root`, one level above `runs/`) normally has no `run.yaml` of its own — the pre-existing exception handler masked the missing guard by returning `None` anyway, for an unrelated reason. Both classes of test were redesigned: (1) assertion-raising spies converted to RECORDING spies plus an explicit `assert calls == []`, and (2) direct-unit tests now PLANT a real, well-formed YAML file AT the escape target with content that would produce a REAL, non-`None` result if read unguarded. After the redesign, the SAME 12-mutation sweep killed every single one:

```
M1  external_import.py packet_dir guard (SEC-1)              -> KILLED (2 tests failed)
M2  external_import.py target_run_id guard                   -> KILLED (assert 'ws-mine' is None)
M3  source_ingest.py run_id guard                             -> KILLED (assert 'ws-mine' is None)
M4  source_ingest.py locator guard                            -> KILLED (1 test failed)
M5  run_plan.py intent_id pre-auth guard                      -> KILLED (2 tests failed, assert 'public' is None)
M6  run_plan.py intent_id residual _run() guard                -> KILLED (1 test failed)
M7  swarm_start.py run_id guard                                -> KILLED (_RunContext mismatch)
M8  swarm_start.py intent_id defense-in-depth guard            -> KILLED (assert 'personal' is None)
M9  research_stages.py run_id guard                            -> KILLED (assert 'public' is None)
M10 verify_bundle.py run_id guard                              -> KILLED (assert 'public' is None)
M11 verify_bundle.py SEC-7 coercion                             -> KILLED (AttributeError surfaced, ok flipped False)
M12 writeback_preview.py run_id guard                          -> KILLED (assert 'public' is None)
```

12 of 12 mutations killed, zero survivors, zero vacuous passes, on the SECOND pass (after the test-design fix above). The FIRST pass's 12-of-12 false-survival result is itself reported here rather than silently corrected, per the coordinator's own standard ("a fix whose test passes against the reverted source is not fixed") — the tests, not the source fixes, were the defect that pass caught.

## Test counts (post-redesign, full files)

```
external_import.py:    12 tests (6 pre-existing + 6 new: SEC-1 x3, target_run_id x2, +1 shared)
source_ingest.py:      12 tests (8 pre-existing + 4 new: locator x2, run_id x1, +existing extended)
run_plan.py:           17 tests (14 pre-existing F2.1 + 3 new: intent_id x3)
swarm_start.py:        11 tests (9 pre-existing + 2 new: run_id x1, intent_id x1)
research_stages.py:    18 tests (17 pre-existing + 1 new: run_id x1)
verify_bundle.py:      22 tests (19 pre-existing F2.1 + 3 new: SEC-7 x2, run_id x1)
writeback_preview.py:  17 tests (15 pre-existing F2.1-F2.4 + 2 new: run_id x1, +1 F2.1 leftover)
```

## Full validation run (post fix cycle 2)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/test_operator_mcp_offline_import.py \
    tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_packaging.py \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_knowledge_mcp_registry.py
344 passed in 18.15s          # up from fix-cycle-1's 311

$ flake8 src/research_foundry --select=E9,F63,F7,F82
(clean, exit 0)

$ ./.venv/bin/python -m pytest tests -q -k "writeback" \
    --ignore=tests/test_search_router_mcp_launcher.py \
    --ignore=tests/test_verification_pediatric_cds.py \
    --ignore=tests/test_verification_seam001_gate_composition.py
(all green, unmodified count from fix cycle 1)
```

## Test inversions (boundary rule 5, flagged loudly)

Two pre-existing tests in `test_operator_mcp_adapter_external_import.py` had their `packet_dir` fixture moved from outside the workspace to inside it (`test_invoke_result_matches_direct_import_call`, `test_exact_retry_does_not_duplicate_import_receipt`) — documented in a new module-docstring paragraph in that test file explaining WHY (SEC-1 determined the old, unbounded-by-design behavior was a defect, not intended design). No other pre-existing test in any of the 7 touched files needed modification — everywhere else, the fix's containment root (workspace/`runs/`/`intents/`) already matched what every existing fixture already used.

## What the security gate should attack first

1. **The workspace-root containment scope decision for `packet_dir`** (SEC-1) — re-verify this reading is what was actually wanted: containment to `paths.root` (the WHOLE workspace), not something narrower. The gate's own evidence included "packet_dir pointed at another run in the same workspace still causes 8 recursive scandirs" — this fix does NOT add per-run isolation for `packet_dir` (judged out of scope: in this single-trusted-operator system, all runs under one workspace already belong to the one caller who could reach any of them by other means anyway) — confirm this reading, or push back.
2. **The `_resolved_within`/`_explicit_path_within_run` helper's SIX independent copies** — verify none of the 6 duplicates drifted from the canonical shape during the mechanical repetition across 7 files.
3. **SEC-7's coercion boundary** — confirm `Path(value)` for a caller-supplied JSON value cannot itself be abused (e.g. a very long string, unusual Unicode) in a way the subsequent `_explicit_path_within_run` call doesn't already bound.
4. **The count-9 "new instances beyond packet_dir" claim** — independently re-derive at least 2-3 of the 9 from source, the same spot-check discipline the gate applied to Leg 2's F2.1 table last round.
5. **`swarm_start.intent_id`'s "not directly caller-reachable today" claim** (row 13) — independently confirm there is truly no path from an MCP-supplied parameter to a caller-controlled `run.yaml`'s `intent_id` field that this fix's own `run_id` containment doesn't already close first.

Nothing disputed. SEC-1 and SEC-7 fixed exactly as the coordinator specified (coerce-then-guard chosen for SEC-7, with rationale). All 9 newly-found instances fixed. No STOP-and-report triggered — no hard-boundary file needed editing, and the "genuinely requires an out-of-workspace packet directory" question resolved in favor of the coordinator's own default direction (workspace-tree containment) rather than escalating, since no functional requirement for out-of-workspace packets was found in the codebase, docs, or PRD beyond CLI convenience.

---

# Fix cycle 3 (FINAL) — F3.1/SEC2-1 + F3.2/SEC2-2: narrow the surface, don't guard it again

Security re-gate: `.claude/findings/m2-security-regate.md`, sections SEC2-1 + SEC2-2 (both
BLOCKING). Coordinator's explicit direction: no fourth guard layer — remove what can be removed,
and where a value must survive (`packet_dir`), make the containment check AUTHORITATIVE
(resolve-and-substitute) rather than advisory (bool-returning). SEC2-3 handled by the coordinator
directly (not touched here). SEC2-4/SEC2-5 (MED) and SEC2-6/7/8 (LOW) — reported below, not fixed
(scope discipline per the coordinator's explicit "do not expand scope for the LOW items").

## What was removed vs. what was guarded

**Removed (F3.1, run.verify):** `report_path`/`claim_ledger_path` deleted from `invoke_verify`'s
own signature in `verify_bundle.py` — not merely rejected, GONE. Since `operator_mcp/server.py`'s
`_allowed_input_payload_keys` derives its per-kind allowlist from `inspect.signature` of the real
adapter function, this shrinks the real MCP-reachable surface with no server.py logic change
needed. `verify_report`'s own default (`None` → auto-discover from the run's own directory, the
same anchor the prerequisite check already uses) now runs unconditionally — there is no second
anchor left to mismatch, because there is no caller-supplied path left to mismatch it with.
`_verify_prerequisites_met` simplified to match (no more explicit-path skip branch). The F5
containment helper (`_explicit_path_within_run`) is KEPT, unmodified — it is still reused for
`run_id`'s own containment (cycle 2's fix), which the re-gate confirmed has no anchor-mismatch
problem (both sides of that check share the same `paths`-derived anchor).

**One necessary cross-boundary touch, disclosed:** `tests/integration/test_operator_mcp_server.py`'s
`test_allowed_input_payload_keys_is_pinned_per_kind` hardcodes an exact frozenset per kind — its
whole job is to mirror the real signature-derived allowlist, so removing the two parameters broke
it mechanically. Updated the ONE `run.verify` entry (removed `report_path`/`claim_ledger_path`)
with a comment explaining why; touched nothing else in that file or `server.py` itself. Fix cycle
2's boundary explicitly named `operator_mcp/server.py` off-limits for "Leg 1 concurrent work"
reasons; this cycle's boundary list did not repeat that file, the working tree showed no
in-flight Leg 1 changes (fix cycle 2 already merged, `5025e97`), and the edit is a direct,
mechanical, one-entry consequence of an explicitly directed fix — flagged here for the record
rather than silently done.

**Guarded, authoritatively (F3.1, `packet_dir` in `external_import.py`):** `_resolved_within` now
RETURNS the resolved, root-anchored `Path` (was `bool`) — SEC2-1's core finding was that a
bool-returning check and the caller's SEPARATE forwarding of the raw string could disagree about
what a relative value means (the check resolved it against the workspace root; `import_external_
report` then resolved the caller's original unresolved string against the server process's CWD).
`_run()` now (a) rejects a relative `packet_dir` OUTRIGHT — no ambiguity to resolve if only an
already-unambiguous absolute value is ever accepted — and (b) forwards the RESOLVED `Path`,
never the caller's raw string, to `import_external_report`. `target_run_id`'s own containment call
site (a pure decision, never a forwarded value) updated to the new `is None` check; unaffected
otherwise, since the re-gate confirmed `run_id`-class values have no anchor-mismatch exposure.

**Guarded, authoritatively (F3.1, `locator` in `source_ingest.py`, local-path branch):** same
resolve-and-substitute treatment, but WITHOUT rejecting relative values outright (unlike
`packet_dir`, a relative `locator` — e.g. "sources/foo.pdf" — is a legitimate, expected shape for
this operation) — the resolved path is forwarded to `ingest_source` instead of the raw string, so
a relative locator is now anchored at the WORKSPACE ROOT, never the process CWD.

**Refused outright (F3.2/SEC2-2, `locator` scheme in `source_ingest.py`):** new
`_ALLOWED_LOCATOR_SCHEMES = frozenset({"http", "https"})`, checked UNCONDITIONALLY at the top of
`_run()`, before any dispatch, regardless of `fetch`/`content`. `"file"` removed from
`_looks_like_url`'s own scheme tuple (previously `http`/`https`/`file` — the ORIGINAL M2-wave-1
defect this re-gate found: "file" was never a network scheme, so treating it as one routed it
straight around the local-path containment branch). `source_cards._fetch_url`'s own missing
scheme allowlist is a canonical-service defect outside this leg's files — the coordinator is
filing it separately; this fix does not depend on that file changing, since the ADAPTER now
refuses the scheme before `ingest_source` is ever called at all.

## Reproduction results — the coordinator's exact 5 attacks, through real `server.call_tool`

Driven via `build_server(paths=...)` → `operation.preflight` → execute, each with a genuinely
minted confirmation, mirroring `test_operator_mcp_preflight_execute_e2e.py`'s own pattern (scratch
script, not committed — `/tmp/m2-fix-leg2-mutation/repro_cycle3.py`, deleted after use):

```
packet_dir="." (after chdir outside workspace, canary planted at CWD):
  preflight: allowed=True (preflight never runs _run())
  execute:   isError=True reason_code=internal_error -- REFUSED, zero effect
             (relative packet_dir rejected outright; no scandir of anything)

report_path="pwn_report.md" (run.verify):
  preflight: isError=True reason_code=payload_too_large -- REFUSED AT PREFLIGHT
             (key no longer in the allowlist at all -- never even reaches minting)

claim_ledger_path="pwn_ledger.yaml" (run.verify):
  preflight: isError=True reason_code=payload_too_large -- REFUSED AT PREFLIGHT (same)

locator="secret.txt" (source.ingest, after chdir outside workspace, canary planted at CWD):
  preflight: allowed=True
  execute:   isError=False ok=True degraded=True extraction_status=locator_only
             (resolved against the WORKSPACE ROOT -> nonexistent path -> never read)
  canary content leaked into any source card: False

locator="file:///etc/passwd" fetch=True (source.ingest):
  preflight: allowed=True
  execute:   isError=True reason_code=internal_error -- REFUSED, zero effect
             (scheme rejected before ingest_source/urlopen ever called)
  /etc/passwd content leaked into any source card: False
```

All 5 refused with zero effect through the genuine registered route. `file://localhost/...`,
`FILE://...`, `file:/...` variants also covered (parametrized unit test, all four scheme forms
denied identically — `urlparse` lowercases the scheme, matching the re-gate's own finding).

## F3.3 — the CWD test-harness blind spot, closed and mutation-verified

Every pre-existing test in this whole leg ran with CWD inside the workspace tree, so none of them
could ever observe an anchor mismatch — proven by the FIRST mutation pass of this fix cycle (see
below) initially reporting FALSE test failures for the wrong reason before the tests themselves
were corrected. New CWD-outside tests added (5 new tests across 2 files): `test_invoke_denies_
relative_packet_dir_outright` + its positive counterpart (external_import.py, chdir + planted
canary packet at CWD); `test_invoke_never_reads_cwd_relative_canary_after_chdir_outside_workspace`
(source_ingest.py, chdir + planted canary file, asserts the resolved locator is workspace-root-
anchored and the canary content never appears in any source card); 4-variant parametrized
`test_invoke_denies_file_scheme_locator_variants_with_fetch_true` (spies on BOTH `ingest_source`
and `urllib.request.urlopen`, asserts neither is ever called) + `test_looks_like_url_no_longer_
accepts_file_scheme` (direct unit proof).

**Mutation-verified with CWD outside the tree** (the coordinator's own explicit requirement — "a
mutation test run from inside the tree proves nothing here"): for `packet_dir`'s relative-
rejection, reverted `if not packet_path.is_absolute():` to `if False:` in a scratch copy — the CWD
test failed (`import_external_report` reached, canary packet's own directory scanned). For
`locator`'s scheme allowlist, reverted `_ALLOWED_LOCATOR_SCHEMES` membership check to always pass
— the file-scheme test failed (`urlopen` reached). For `locator`'s resolve-and-substitute, reverted
`effective_locator = str(resolved_locator)` to forward the raw `locator` string instead — the CWD
canary test failed (`captured_locator` no longer matched the workspace-root-anchored path; the
real CWD-relative canary file would have been read by the unmocked `ingest_source` had the test
continued). All three killed cleanly; `__pycache__` purged before and after each iteration.

## Test counts (post fix cycle 3)

```
external_import.py:    14 tests (12 pre-existing (cycle 2) + 2 new: relative-rejection x2)
source_ingest.py:      18 tests (12 pre-existing (cycle 2) + 6 new: CWD-canary x1, file-scheme x4
                                  parametrized, _looks_like_url direct x1)
verify_bundle.py:       20 tests (22 pre-existing (cycle 2) - 4 removed (obsolete F5/SEC-7 explicit-
                                  path tests, surface no longer exists) + 2 new (signature-absence
                                  proof + run-id-only positive case))
```

Full validation set: **358 passed** (up from cycle 2's 344; includes `test_operator_mcp_preflight_
execute_e2e.py`, not run as part of cycle 2's own count). `flake8 --select=E9,F63,F7,F82` clean.
Broader `-k "writeback or source_ingest"` sweep across the whole test tree: all green, unchanged
count from prior cycles.

## SEC2-4 / SEC2-5 — investigated, not fixed (reporting per the coordinator's instruction)

**SEC2-4 (phantom write on `internal_error`):** confirmed real by re-reading `source_ingest.py`'s
`_run()` and `operator_receipt_service`'s effect-digest uniqueness check ordering — `ingest_source`
writes the source card to disk BEFORE the effect-receipt uniqueness check can reject a colliding
`effect_digest` (same title+locator, different operation). The write is not transactional/rolled-
back on receipt rejection. Closing this properly requires either reordering the uniqueness check
before the write (inside `source_cards.ingest_source`, a canonical service — OFF LIMITS this
cycle) or making the write itself transactional (also inside that same off-limits file). **Did not
fall out cheaply** — every fix shape touches a file outside this leg's boundary. Reporting for a
follow-up, not fixed.

**SEC2-5 (`content`-supplied ingest permanently unconsumable):** confirmed real — `invoke`'s own
`input_payload` construction binds `content` via `content_digest` (F4, cycle-1-era fix), but
`operation.preflight`'s canonicalization (in `server.py`) hashes the caller's RAW `content` value
directly (since `content` is itself an allowlisted real parameter name). The two canonical
payloads can never match, so every content-bearing `source.ingest` call denies
`confirmation_mismatch` before `_run()`, unconditionally. Confirmed via a scratch reproduction
(preflight with `input_payload={"content": "x", ...}` vs. execute with the same — digests differ).
**Did not fall out cheaply either** — the correct fix (per the finding's own "fix direction") is
to change WHAT `operation.preflight` canonicalizes in `server.py`, i.e., make preflight digest
`content` the SAME way `invoke()` does (via `content_digest`) before computing its own canonical
payload — that is `operator_mcp/server.py` logic, a materially larger and more central change than
the one mechanical test-frozenset edit made for F3.1, and risks the SAME kind of unreviewed
allowlist-mechanism change the coordinator did not ask for this cycle. Reporting for a follow-up,
not fixed. (Its own accidental silver lining — masking `source_cards.py:222`'s unconditional
`Path(locator).exists()`/`.is_file()` stat when `content` is supplied — is now moot regardless,
since that stat path is exactly what F3.1's own `locator` resolve-and-substitute fix already
re-examined and closed.)

## Not touched (LOW, explicit scope discipline)

SEC2-6 (containment helpers catch only `OSError`, not `ValueError` for NUL-byte paths — absorbed
safely one layer up regardless), SEC2-7 (SEC-7's `except TypeError` coercion block is now MOOT,
not merely dead — the parameters it coerced no longer exist), SEC2-8 (`schemas.default_registry()`
process-wide CWD-coupled cache) — all read and understood, none touched, per the coordinator's
explicit "do not expand scope for the LOW items."

## What the security gate should attack first

1. **The `test_operator_mcp_server.py` cross-boundary edit** — confirm the one-entry `run.verify`
   frozenset change is the ONLY change in that file (verified here via `git diff` scoped to that
   file — one entry, plus the explanatory comment — but independent confirmation is warranted
   given the file's normal off-limits status).
2. **`packet_dir`'s "reject relative outright" vs. `locator`'s "resolve-and-substitute" asymmetry**
   — independently confirm this split is correct: is there a legitimate MCP use case for a
   relative `packet_dir` this fix now forecloses? (Research during this cycle found none — CLI
   parity was never claimed for `packet_dir`'s relative form specifically, only for absolute
   paths — but this is exactly the kind of judgment call worth a second look.)
3. **SEC2-4/SEC2-5's "did not fall out cheaply" claim** — independently verify both genuinely
   require an off-limits file, not merely that this leg judged the risk/reward unfavorable.

Nothing disputed on F3.1/F3.2 themselves. No STOP-and-report triggered.
