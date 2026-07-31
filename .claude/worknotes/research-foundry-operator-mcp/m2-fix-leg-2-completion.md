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
