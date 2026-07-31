# M1 Remainder Scoping — External Import Adapter + Six Canonical Research-Stage Adapters

Scope: `external_report.import`, `source.ingest`, `run.extract`, `run.claim_map`,
`run.synthesize`, `run.verify`, `run.bundle` (the seven `OPERATION_KINDS` members not yet
wrapped by an `operator_mcp_adapters` module). Repo root:
`/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1`.

Landed P3 adapters (the pattern to extend): `run.plan`, `swarm.start`, `job.status`,
`job.cancel`, `job.resume` — commits 70c8a6f, c88e77e, 9ddb087, 8fe3a2c, 415fb5e, 22a75cc,
8b694d5, 90abeff, living in `src/research_foundry/services/operator_mcp_adapters/`.

**Naming correction vs. the task brief**: the module is
`src/research_foundry/services/operator_mcp_adapters/` (a package: `base.py`, `run_plan.py`,
`swarm_start.py`, `job_lifecycle.py`, `__init__.py`), **not**
`operator_tool_adapters.py`/`test_operator_tool_adapters.py` — no such files exist anywhere
in the tree (`find` confirms). The M1 plan text itself
(`docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md:493-496`)
also names `operator_tool_adapters.py` as a declared serialization barrier shared with M2 — that
is either aspirational/stale naming in the plan or a rename M1 itself performs; as of this
worktree's HEAD the real package is `operator_mcp_adapters/`. Treat any reference to
`operator_tool_adapters.py` in planning docs as referring to this package.

---

## (a) Exemplar adapter anatomy — `run_plan.py` (`run.plan`)

File: `src/research_foundry/services/operator_mcp_adapters/run_plan.py` (313 lines).
Substrate it builds on: `src/research_foundry/services/operator_mcp_adapters/base.py` (371
lines) — the ONE `run_pipeline` seam every adapter calls.

**Anatomy, in the order `invoke()` performs it** (`run_plan.py:156-299`):

1. **Signature** — no identity, no workspace_id, no `AuthIdentity`-shaped parameter, no
   `sensitivity_ceiling` parameter (removed by 8b694d5, see (b) below):
   ```python
   def invoke(
       *,
       intent_id: str,
       idempotency_key: str,
       confirmation_record: Mapping[str, Any] | None,
       presented_token: str | None,
       depth: str = "standard",
       audience: str = "technical",
       max_cost_usd: float = 5.0,
       max_runtime_minutes: int = 60,
       freshness_days: int = 180,
       profile: str | None = None,
       project: str | None = None,
       retrieval_policy: str | None = None,
       retrieval_limits: Mapping[str, Any] | None = None,
       dry_run: bool = False,
       paths: FoundryPaths | None = None,
       now: datetime | None = None,
       operations: OperatorOperationService | None = None,
       cancel_resume: OperatorCancelResumeService | None = None,
   ) -> base.OperatorAdapterResult:
   ```
   (`run_plan.py:156-176`)

2. **Bind sensitivity ceiling (structural, not caller-suppliable)**:
   ```python
   from . import resolve_local_sensitivity_ceiling  # lazy, avoids circular import
   resolved_paths = paths or FoundryPaths.discover()
   sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
   ```
   (`run_plan.py:197-201`)

3. **Bind effective sensitivity** — read-only, pre-authorization lookup of the *target's*
   declared sensitivity, swallowing every exception to the strictest label:
   ```python
   intent_sensitivity = _resolve_intent_sensitivity(intent_id, resolved_paths)
   effective_sensitivity = policy.resolve_effective_sensitivity(intent_sensitivity)
   ```
   (`run_plan.py:203-204`; `_resolve_intent_sensitivity` at `run_plan.py:132-153` returns
   `None` on ANY exception, never a permissive default.)

4. **Build the canonical `input_payload`** (only non-`None` optionals, so two callers omitting
   the same optional collapse to the same idempotency digest) and construct `ctx` via the ONE
   sanctioned constructor, which resolves **identity** internally:
   ```python
   ctx = policy.PolicyContext.for_configured_operator(
       operation_kind=OPERATION_KIND,
       idempotency_key=idempotency_key,
       effective_sensitivity=effective_sensitivity,
       sensitivity_ceiling=sensitivity_ceiling,
       input_payload=input_payload,
       paths=resolved_paths,
   )
   ```
   (`run_plan.py:223-230`) — `for_configured_operator` is the only way to obtain a `ctx` whose
   `.identity` is populated; no adapter accepts identity as a parameter (P3 hardening
   invariant, `base.py:32-39`).

5. **Bind prerequisites/budgets** — for `run.plan` these are caller-supplied args
   (`max_cost_usd`, `max_runtime_minutes`, `freshness_days`) that flow straight into the
   canonical service call; `swarm_start.py` is the sharper example of a *derived* (non-defaulted)
   budget/prerequisite bind — see `_resolve_run_context` at `swarm_start.py:160-185` and its
   deny-not-default handling at `swarm_start.py:346-353` (`run_ctx.budget_usd is None -> deny
   preflight_failed`, never a fallback budget).

6. **Call the canonical service**, capturing its result via closure so `_build_result` can read
   real canonical refs after `run_or_replay` executes the action:
   ```python
   captured: list["planning.PlanResult"] = []
   def _run() -> ActionEffect:
       result = planning.plan_run(intent_id, depth=depth, ..., identity=ctx.identity,
                                    paths=resolved_paths)
       captured.append(result)
       effect_ref = _effect_ref_for(result)          # f"{OPERATION_KIND}:{result.run_id}"
       return ActionEffect(effect_kind="run_planned",
                            effect_digest=hashlib.sha256(effect_ref.encode()).hexdigest(),
                            effect_ref=effect_ref)
   ```
   (`run_plan.py:238-262`)

7. **Map into the common operation+receipt envelope** via `base.run_pipeline`, which is the
   fixed authorize → consume → execute → bounded-result sequence:
   ```python
   return base.run_pipeline(
       ctx=ctx, confirmation_record=confirmation_record, presented_token=presented_token,
       action_manifest=action_manifest, actions=(ActionSpec(action_id="plan_run", run=_run),),
       build_result=_build_result, dry_run=dry_run, paths=resolved_paths, now=now,
       operations=operations, cancel_resume=cancel_resume,
   )
   ```
   (`run_plan.py:287-299`)

8. **Typed denials** — `base.run_pipeline` (`base.py:208-370`) is the ONLY place denials are
   built, always via `policy.build_error(decision, now=now)` where `decision` is a
   `policy.PolicyDecision`. Three denial sources, in order:
   - `authorize_for_consumption` returns a non-`"confirmation"`-stage decision (capability/
     RBAC/audit-health/guard/preflight) → propagated verbatim (`base.py:278-284`).
   - `consume_and_create_operation` returns `"denied"`/`"idempotency_conflict"` → wrapped via
     the module-local `_denial(reason_code, retryable=..., stage="confirmation")` helper
     (`base.py:196-205`, `301-313`).
   - `run_or_replay` (cancel/resume service) returns `status in ("failed", "denied")` → wrapped
     the same way, reading `execution.terminal_receipt["denial_reason_code"]` (`base.py:346-354`).
   - A single blanket `except Exception` at the bottom of `run_pipeline` logs only
     `type(exc).__name__` (never `str(exc)`) and returns `_denial("internal_error",
     retryable=True)` (`base.py:359-370`).
   Every `OperatorAdapterResult(ok=False, ...)` therefore carries a schema-valid
   `operator_mcp_error` envelope, never a raw exception/traceback/unbounded detail
   (`base.py:104-131`, requirement 3).

9. **Registration** — a frozen dataclass implementing the `OperatorAdapter` Protocol, registered
   at import time as a module-level side effect:
   ```python
   @dataclass(frozen=True)
   class RunPlanAdapter:
       operation_kind: str = OPERATION_KIND
       def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
           return invoke(**kwargs)
   ADAPTER = RunPlanAdapter()
   base.register(ADAPTER)
   ```
   (`run_plan.py:302-313`)

**`job.status`/`job.cancel`/`job.resume` are the deliberate exception**: `job.status` bypasses
`base.run_pipeline` entirely because it is the sole `CONFIRMATION_NOT_REQUIRED_KINDS` member —
calling `run_pipeline` for it would always deny with `confirmation_missing` (see the detailed
rationale in `job_lifecycle.py`'s module docstring, lines ~1-70). It instead calls
`operator_operation_service.authorize_for_consumption` directly and performs a bounded read
itself, never durably creating a manifest (`OperatorAdapterResult.operation_id` is always
`None` for this kind). This is a **documented, load-bearing deviation** the new adapters should
NOT need — none of the seven remaining kinds are in `CONFIRMATION_NOT_REQUIRED_KINDS`
(`operator_mcp_policy.py:464`), so all seven should follow the `run_plan.py` shape (full
`base.run_pipeline` call), not the `job_lifecycle.invoke_status` shape.

---

## (b) Mandatory `sensitivity_ceiling` pattern (commit 8b694d5)

`git show 8b694d5 --stat`:
```
 src/research_foundry/services/operator_mcp_adapters/__init__.py     | 68 +++++++++++++++++
 src/research_foundry/services/operator_mcp_adapters/job_lifecycle.py| 33 +++++++--
 src/research_foundry/services/operator_mcp_adapters/run_plan.py     | 10 ++-
 src/research_foundry/services/operator_mcp_adapters/swarm_start.py  | 11 ++-
 (+ two progress-tracker/test files)
```

**The defect**: all five P3 entry points declared `sensitivity_ceiling: str =
"client_sensitive"` as a caller-supplied kwarg defaulting to the HIGHEST rank in
`SENSITIVITY_LEVELS`. `_check_guard`'s only above-ceiling denial is
`rank(effective) > rank(ceiling)`; pinning the ceiling to the max makes that comparison
permanently false for any caller that didn't override it — a structural no-op guard.

**The fix — exact code shape, mandatory for every new adapter**:

1. **No `sensitivity_ceiling` parameter anywhere in an adapter's public `invoke*` signature.**
   Not un-defaulted, not made a monotonic-only override — removed entirely. Same doctrine as
   identity: "a value a caller can lower is also a value a caller-side bug or omission can leave
   at its permissive extreme."

2. **A new resolver, `operator_mcp_adapters.resolve_local_sensitivity_ceiling`**
   (`operator_mcp_adapters/__init__.py`, added by 8b694d5):
   ```python
   _CEILING_CONFIG_SECTION = "operator_mcp"
   _CEILING_CONFIG_KEY = "sensitivity_ceiling"

   def resolve_local_sensitivity_ceiling(paths: FoundryPaths | None = None) -> str:
       resolved_paths = paths if paths is not None else FoundryPaths.discover()
       try:
           foundry_block = FoundryConfig(paths=resolved_paths).foundry
       except Exception as exc:
           _logger.warning(
               "operator_mcp_adapters.resolve_local_sensitivity_ceiling: config load "
               "failed (%s) -- resolving to %r (deny above it)",
               type(exc).__name__, policy.SENSITIVITY_LEVELS[0],
           )
           return policy.SENSITIVITY_LEVELS[0]
       section = foundry_block.get(_CEILING_CONFIG_SECTION) if isinstance(foundry_block, dict) else None
       ceiling = section.get(_CEILING_CONFIG_KEY) if isinstance(section, dict) else None
       if isinstance(ceiling, str) and ceiling in policy.SENSITIVITY_LEVELS:
           return ceiling
       return policy.SENSITIVITY_LEVELS[0]
   ```
   Fails closed to `SENSITIVITY_LEVELS[0]` (`"public"`, strictest) on: absent block, absent key,
   non-string value, unknown label, or ANY exception loading `foundry.yaml`. Never raises. Never
   returns a value outside `SENSITIVITY_LEVELS` (so `PolicyContext.__post_init__` can never
   raise `ValueError` from a value this resolver produced).

3. **Call site pattern, identical in every adapter** — a LAZY import (to avoid the circular
   import `operator_mcp_adapters/__init__.py` itself creates by importing every adapter module
   for registration) inside the `invoke*` function body, immediately followed by the resolve
   call, BEFORE building `input_payload`/`ctx`:
   ```python
   from . import resolve_local_sensitivity_ceiling  # lazy: avoids circular import
   resolved_paths = paths or FoundryPaths.discover()
   sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
   ```
   Applied verbatim at `run_plan.py:198-201`, `swarm_start.py:313-314`,
   `job_lifecycle.py` (invoke_status/invoke_cancel/invoke_resume, three near-identical sites).

4. **Every new adapter (`external_report.import`, `source.ingest`, `run.extract`,
   `run.claim_map`, `run.synthesize`, `run.verify`, `run.bundle`) MUST reproduce this exact
   pattern** — no `sensitivity_ceiling` parameter, resolve via
   `resolve_local_sensitivity_ceiling(resolved_paths)` before constructing `ctx`. Getting this
   wrong reproduces the exact HIGH finding 8b694d5 closed.

5. **Test-side corollary** (from the fix's commit message, verified against
   `test_operator_mcp_adapter_run_plan.py:74-260`): a naive `monkeypatch.setattr(adapters_pkg,
   "resolve_local_sensitivity_ceiling", ...)` autouse fixture masks the resolver's OWN
   fail-closed behavior. The corrected fixture pattern instead WRITES the ceiling key into
   `foundry.yaml` under `tmp_foundry` (`test_operator_mcp_adapter_run_plan.py:42-77`) so the
   real resolver code path executes, and a SEPARATE small set of tests
   (`test_resolve_local_sensitivity_ceiling_*`, `run_plan.py:129-263`) directly unit-tests the
   resolver's five failure/success branches without going through any adapter. New adapter
   tests must reuse the config-writing fixture shape, not a resolver monkeypatch, or they will
   not exercise the H7 guard at all.

---

## (c) Per-service table

| service | module:line | signature | canonical service exists? | extraction needed? |
|---|---|---|---|---|
| `external_report.import` | `src/research_foundry/services/external_research_import.py:321` | `import_external_report(packet_dir: str \| Path, *, workspace_id: str, target_run_id: str \| None = None, policy: Mapping \| None = None, limits: Limits \| None = None, dry_run: bool = False, resume: bool = False, limit: int \| None = DEFAULT_BATCH_SIZE, paths: FoundryPaths \| None = None, resolver: ExternalResearchResolver \| None = None, authorization_policy: AuthorizationPolicy \| None = None, acquire: AcquireFn \| None = None, promote: Promote \| None = default_promote, provenance_origin: str \| None = None, caller: CallerContext \| None = None) -> ImportOutcome` | **Yes.** Docstring explicitly: "This is the intended service seam for a future Operator MCP tool and for `rf intake external-report` alike — plain, typed, and free of any CLI/argparse coupling" (`external_research_import.py:342-344`). Already supports dry-run and resume natively. | **No.** Wrap directly; supply `workspace_id=ctx.identity.workspace_id`, `dry_run` forwarded from adapter's own `dry_run` (though note: this service's own internal `dry_run` semantics differ from the adapter substrate's dry-run-means-zero-effects contract — reconcile carefully, see (f)). |
| `source.ingest` (CLI: `ingest`) | `src/research_foundry/services/source_cards.py:178` | `ingest_source(locator: str, *, run_id: str, source_type: str = "other", sensitivity: str = "personal", title: str \| None = None, created_by_agent: str = "rf_source_carder", fetch: bool = False, content: str \| None = None, extra_limitations: list[str] \| None = None, assertion_registry_workspace_id: str \| None = None, paths: FoundryPaths \| None = None, extraction_status: str \| None = None) -> IngestResult` | **Yes.** Same shape as `plan_run`/`run_swarm` — no identity param, run-scoped. | No extraction of new logic; the adapter must bind `assertion_registry_workspace_id` from `ctx.identity.workspace_id` (see (f) — the CLI's own call site hardcodes `"default"` here, which the adapter must NOT copy). |
| `run.extract` (CLI: `extract`) | `src/research_foundry/services/extraction.py:81` | `extract_run(run_id: str, *, model_profile: str = "rf_extract_cheap", paths: FoundryPaths \| None = None) -> ExtractResult` | **Yes.** | No. |
| `run.claim_map` (CLI: `claim-map`) | `src/research_foundry/services/claim_mapping.py:213` | `build_claim_ledger(run_id: str, *, intent_id: str \| None = None, paths: FoundryPaths \| None = None) -> ClaimMapResult` | **Yes.** | No. |
| `run.synthesize` (CLI: `synthesize`) | `src/research_foundry/services/synthesis.py:231` | `synthesize_report(run_id: str, *, model_profile: str = "rf_synthesize_deep", final: bool = False, audience: str \| None = None, sensitivity: str \| None = None, llm: bool = False, paths: FoundryPaths \| None = None) -> SynthResult` | **Yes.** | No. |
| `run.verify` (CLI: `verify`) | `src/research_foundry/services/verification.py:821` | `verify_report(run_id: str, *, report_path: Path \| None = None, claim_ledger_path: Path \| None = None, fail_on_unsupported: bool = True, exact_passage_override: str \| None = None, paths: FoundryPaths \| None = None, disposition: str = "internal_capture", evidence_judgment_bases: Sequence[str] \| None = None) -> VerificationResult` | **Yes.** Returns a `VerificationResult` with a governed `exit_code`/`passed` — NOT an exception on failure (matches the M1 AC "verify failure must be a typed governed result, not an exception"). | No, but the adapter's `_build_result`/denial mapping must translate a non-`passed` `VerificationResult` into a governed `ok=False` (or a bounded `ok=True` with `passed=False`, TBD — see (f)) rather than letting `run_or_replay` treat a raised exception as `"failed"`; `verify_report` itself does not raise on verification failure, so the adapter's action closure must inspect `.passed` explicitly. |
| `run.bundle` (CLI: `bundle`) | `src/research_foundry/services/writeback.py:180` | `build_bundle(run_id: str, *, verify: bool = True, paths: FoundryPaths \| None = None) -> BundleResult` | **Yes.** Internally calls `verify_report` when `verify=True` (`writeback.py:206-210`) — this is the dependency the M1 AC means by "verify failure... blocks the dependent bundle action." | No, but the adapter must confirm `build_bundle`'s own internal verify-failure handling actually blocks (sets `verified=False`/`governance.approved_for_writeback=False`) rather than silently proceeding — read `writeback.py:180-` fully before wrapping; this task did not fully trace `build_bundle`'s post-verify branch (see (f)). |

**Bottom line, correcting the task brief's framing**: none of the seven require extracting new
logic out of `cli_commands.py` into a service — every one of the six research-stage functions
plus `import_external_report` already exists as a plain, typed, paths-injectable function with
no CLI/Typer coupling, matching exactly the P3 exemplar's starting conditions (`planning.plan_run`,
`swarm_service.run_swarm`). `cli_commands.py`'s `ingest`/`extract`/`claim_map`/`synthesize`/
`verify`/`bundle`/(intake `external-report`, not directly grepped but implied) commands are all
thin wrappers that already call these same functions (`cli_commands.py:330-522`). The M1 work is
adapter-authoring (repeating the `run_plan.py`/`swarm_start.py` pattern seven times), not
service-extraction — the "load-bearing sequence" note in the plan
(`research-foundry-operator-mcp-v1.md:514-517`, "the swarm-service extraction lands before any
adapter that dispatches through it") describes work already done in the P3 half, not work
remaining here.

`policy.OPERATION_KINDS` (`operator_mcp_policy.py:438-452`) already lists all seven kind strings
verbatim — no schema/enum change needed for these seven; they are already part of the closed,
validator-checked vocabulary (`operator_mcp_policy.py:659-670`'s import-time invariant that
`OPERATION_KINDS` and `_OPERATION_ROLES` classify the exact same set — check `_OPERATION_ROLES`
already has entries for these seven kinds before wiring the RBAC stage, not verified in this pass,
see (f)).

---

## (d) Test patterns + reusable fixtures

Existing suite: `tests/unit/test_operator_mcp_adapter_base.py` (357 lines),
`test_operator_mcp_adapter_run_plan.py` (553 lines), `test_operator_mcp_adapter_swarm_start.py`
(554 lines), `test_operator_mcp_adapter_job_lifecycle.py` (1294 lines). **No
`test_operator_tool_adapters.py` exists** (confirms (a)'s naming correction).

**Parity-test pattern (direct-service vs. adapter canonical refs)** —
`test_invoke_result_matches_direct_plan_run_call`
(`tests/unit/test_operator_mcp_adapter_run_plan.py:264-352`):
1. Build the identity/ctx exactly as the adapter would (same `idempotency_key`,
   `effective_sensitivity`, `sensitivity_ceiling`, `input_payload`) so the confirmation minted
   against it binds to the same canonical digest the adapter recomputes internally.
2. Mint + record a confirmation via `policy.mint_confirmation` +
   `OperatorOperationService.record_confirmation` — mirrors the not-yet-built P5 transport.
3. **Spy, don't double-call**: `monkeypatch.setattr(planning_module, "plan_run", _spy_plan_run)`
   wraps the REAL `plan_run` and captures its one call — because `plan_run` is not idempotent
   (mints a fresh `run_id`/`disambiguate_id` per call), calling it twice (once direct, once via
   adapter) would not be a meaningful equivalence check. This spy pattern is the one to reuse
   for every new adapter whose underlying service is similarly non-idempotent per raw call
   (`ingest_source`, `extract_run`, `build_claim_ledger`, `synthesize_report` likely all qualify
   — each mints new artifact ids on every call).
4. Assert the adapter's bounded `result.result` dict carries the SAME canonical ids/paths the
   spied-on direct result object holds, field by field — proving the adapter's `_build_result`
   is a lossless, non-mangling view, not an independently reconstructed one.

**Retry/cancel idempotency pattern** — swarm_start's
`test_interrupted_then_resumed_execution_does_not_duplicate_or_lose_candidates`
(`tests/unit/test_operator_mcp_adapter_swarm_start.py:271-` ) and
`test_merge_with_existing_true_is_required_for_non_duplication`
(`:393-`), explicitly "adapted from `operator_cancel_resume_service.py`'s own scenario-7
resumed fixture" and reusing `from tests.unit.test_operator_cancel_resume_service import
_consume` (`swarm_start.py` test file: line 45). This is the reusable helper new adapter tests
for `run.extract`/`run.claim_map`/etc. should import rather than reimplementing: `_consume` in
`tests/unit/test_operator_cancel_resume_service.py` drives an interrupted-then-resumed
`run_or_replay` scenario against a real `OperatorCancelResumeService`.

**H7 negative-fixture pattern** (post-8b694d5, mandatory for every new adapter per (b)):
`test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_intent`
(`run_plan.py` tests, `:460-`) and its swarm_start sibling (`:446-`) — write a LOWER-than-default
`sensitivity_ceiling` into `tmp_foundry`'s `foundry.yaml` via the autouse fixture override, submit
an above-ceiling-sensitivity target, and assert the denial is identical in shape to a
missing-target denial (proves the guard fires, and that it doesn't leak existence information).

**Reusable fixtures a new test module should reuse** (all defined per-test-file today, not yet
centralized — check whether M1 wants a shared `conftest.py` extraction, not investigated here):
- The `tmp_foundry`-writing autouse `sensitivity_ceiling` fixture (`run_plan.py` tests:
  `:42-127`) — writes the ceiling into `foundry.yaml` rather than monkeypatching the resolver.
- `_make_intent(...)` helper for constructing a fixture intent (`run_plan.py` tests, referenced
  at `:283`) — analogous helpers will be needed for a fixture run/source-card/claim-ledger for
  the six research-stage adapters.
- `AuthIdentity("alice", "ws-mine", ("owner",))` + `monkeypatch.setattr(policy,
  "resolve_operator_identity", lambda *a, **kw: identity)` — the standard way tests inject a
  deterministic identity without touching `foundry.yaml`'s real identity block.
- `tests.unit.test_operator_cancel_resume_service._consume` for interrupted/resumed execution
  scenarios.
- `tests/unit/test_operator_mcp_policy.py`'s identity fixtures (referenced at
  `test_operator_mcp_adapter_swarm_start.py:12`, not independently re-read in this pass).

---

## (e) Ref types to thread through

**ERI (`external_research_import`/`external_research_interchange`) refs** —
`ImportOutcome` (`external_research_import.py:236-266`):
`workspace_id`, `target_run_id`, `packet_digest`, `receipt_id`, `receipt_digest`, `status`
(`"completed"|"completed_with_quarantine"|"blocked"|"pending"`), `replayed`, `dry_run`,
`block_reason`, `counts`, `cursor`, plus the full `receipt`/`checkpoint` documents. `.safe_dict()`
(`:263-282`) is the redaction-matrix-compliant subset — the new `external_report.import` adapter's
`_build_result` should almost certainly return `.safe_dict()`'s shape (or a superset the operator
receipt envelope is happy with), not the raw dict, mirroring the "never packet-derived free text"
constraint already documented on the service itself.

**RPC (Research Provenance Contract, C1, landed on main `65d658d`) refs** —
`src/research_foundry/services/provenance_envelope.py` owns three record families:
`provenance_origin` (`origin_id`, content-addressed over `ORIGIN_MATERIAL_FIELDS` including
`external_receipt_ref`), `research_run_envelope` (`envelope_id`, over
`ENVELOPE_MATERIAL_FIELDS` including `origin_ref`/`aos_refs`), and `search_activity_receipt`
(`activity_id`). **These are NOT currently threaded into any of the six research-stage canonical
services** — `grep` for `provenance_envelope`/`origin_id`/`envelope_id` across
`source_cards.py`, `extraction.py`, `claim_mapping.py`, `synthesis.py`, `verification.py`,
`writeback.py` returned zero hits. Whether M1's new adapters are expected to newly mint/bind an
`origin_ref`/`envelope_ref` when calling these services, or whether RPC refs remain out of scope
for M1 and are a later integration, is **not resolved by this investigation** — flagged under (f).

**Operator-receipt refs** (already the substrate's own concern, not new per-adapter work) —
`ActionEffect(effect_kind, effect_digest, effect_ref)` from `operator_cancel_resume_service.py`,
persisted by `operator_receipt_service.py`'s `record_effect_receipt(..., effect_ref: str, ...)`
(`operator_receipt_service.py:634-683`) and read back only as digests via
`effect_receipt_refs` (never the raw ref) — the exact "replay result-recovery gap" `run_plan.py`'s
own docstring documents (`run_plan.py:33-48`); every new adapter will hit the same gap and should
document it the same way rather than attempt to close it (out of file-ownership per the P3
implementer contract's convention).

---

## (f) Risks / unknowns not resolved by this pass

1. **`_OPERATION_ROLES` RBAC classification for the seven new kinds** — confirmed
   `operator_mcp_policy.py:659-670` enforces `OPERATION_KINDS == _OPERATION_ROLES.keys()` at
   import time (would hard-fail at import if any of the seven were missing a role classification),
   so the classification MUST already exist for the module to import cleanly today — but this
   pass did not read `_OPERATION_ROLES`'s actual per-kind role/capability values for
   `external_report.import`/`source.ingest`/`run.extract`/`run.claim_map`/`run.synthesize`/
   `run.verify`/`run.bundle` to confirm they are sane (e.g., that `run.verify`/`run.bundle`
   aren't accidentally classified as read-only when they have real effects). Read
   `operator_mcp_policy.py` around wherever `_OPERATION_ROLES` is defined before authoring the
   adapters.

2. **`import_external_report`'s own `dry_run` vs. the adapter substrate's `dry_run` contract** —
   `base.run_pipeline`'s dry-run path (`base.py:263-269`) runs ONLY the five non-confirmation
   policy stages and NEVER invokes `actions` (i.e., never calls the wrapped service at all). But
   `import_external_report` has its OWN native `dry_run: bool` parameter with its own semantics
   (stage without projecting, presumably still writing SOME receipt/checkpoint state — not
   verified). If the `external_report.import` adapter's `dry_run=True` is meant to reach
   `run_pipeline`'s dry-run short-circuit, the service's own `dry_run` parameter becomes
   unreachable/irrelevant from the adapter surface entirely, OR the adapter needs a second,
   non-substrate dry-run concept layered on top. This is a real design decision this
   investigation surfaced but did not resolve — read `import_external_report`'s full docstring
   (`external_research_import.py:339-` onward, only partially read here) and `ImportOutcome`'s
   `dry_run`/`complete`/`pending` semantics before wiring the adapter.

3. **`run.verify`'s failure-as-governed-result vs. `ActionSpec.run`'s exception-based failure
   contract** — `verify_report` returns a `VerificationResult` with `.passed`/`.exit_code`
   rather than raising on a failed verification. `ActionSpec.run` closures in the landed
   adapters (`_run()` in `run_plan.py`/`swarm_start.py`) return an `ActionEffect` on success;
   this investigation did not trace how `run_or_replay`/`OperatorCancelResumeService`
   distinguishes a "the action ran and produced a non-passing but still governed result" from an
   actual failure — i.e., does the `run.verify` adapter's closure need to raise an exception
   when `!result.passed` to get `run_or_replay` to mark the operation `"failed"` with a proper
   `denial_reason_code`, or does it return a "successful" `ActionEffect` with `passed=False`
   baked into `_build_result`'s payload (making a failed verification `ok=True` at the
   `OperatorAdapterResult` level, just with `result["passed"] == False`)? The M1 AC text
   ("Verify failure is a typed governed result that blocks the dependent bundle action") reads
   as the latter, but this needs to be confirmed against `operator_cancel_resume_service.py`'s
   `run_or_replay`/`ExecutionOutcome` contract (not read in this pass) before implementation.

4. **`build_bundle`'s internal verify-blocking behavior** — only partially read
   (`writeback.py:180-210`); did not trace what `build_bundle` actually does with a failed
   `verify_report` result past setting `verified = bool(vr.passed)` (line ~210) — whether
   `governance.approved_for_writeback` or bundle `status` is set to a blocking value, and
   whether the function raises or returns a "draft" `BundleResult` on verify failure. The M1 AC
   "verify failure... blocks the dependent bundle action" needs this traced fully before the
   `run.bundle` adapter can decide what a verify-failed bundle attempt returns.

5. **`source.ingest`'s workspace binding** — `ingest_source`'s `assertion_registry_workspace_id`
   parameter is currently resolved by the CLI command as a **literal hardcoded string
   `"default"`** passed through `assertion_workspace.resolve_or_deny("default")`
   (`cli_commands.py:354`, `resolve_or_deny` docstring at
   `src/research_foundry/services/assertion_workspace.py:119-129` confirms `"default"` is the
   documented P1-01 single-operator resolution rule — the CALL SITE's job to resolve, not a bug
   in `resolve_or_deny` itself). The M1 AC "No hard-coded default workspace anywhere in the
   ingest path" almost certainly targets exactly this: the new `source.ingest` adapter MUST
   resolve `assertion_registry_workspace_id` from `ctx.identity.workspace_id` (the pattern every
   other landed adapter uses — e.g. `job_lifecycle.py:569,709` reading
   `ctx.identity.workspace_id`), never repeat the CLI's `"default"` literal. Whether the CLI's
   own `ingest` command *also* needs to change (to keep CLI/adapter parity, per the M1 AC "CLI
   parity holds after extraction") — i.e. whether the CLI should now resolve workspace from its
   own configured identity rather than a hardcoded string — was not resolved here; flagged as a
   design question for the M1 implementer, not merely the adapter's own concern.

6. **`test_operator_tool_adapters.py` does not exist** — the task brief's item 5 asked to
   describe it; confirmed via `find`/`ls tests/unit/` that no such file exists anywhere in the
   tree. All test-pattern findings in (d) are drawn from the four
   `test_operator_mcp_adapter_*.py` files instead.

7. **`operator_operation_service.py`/`OperatorOperationService` full API surface** — only the
   subset relevant to `base.run_pipeline`'s own call pattern was read in depth
   (`record_confirmation`, `authorize_for_consumption`, `consume_and_create_operation`,
   `OperationOutcome`, `load_operation`). Names confirmed present via `grep`:
   `_connect`, `_ensure_schema`, `_mint_manifest`, `AuthorizationProof`, `OperationRecord`,
   `_consume_locked`, `_fetch_operation`. No new methods appear needed for the seven new
   adapters beyond what `base.run_pipeline` already calls — but this was not exhaustively
   verified against every one of the seven services' specific needs (e.g. whether `run.bundle`
   needs anything beyond the standard pipeline given it composes `verify_report` internally).
