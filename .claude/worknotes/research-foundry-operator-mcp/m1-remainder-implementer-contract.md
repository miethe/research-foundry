---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
---

# M1 remainder — implementer contract (DECIDED)

Authoritative for the three implementation legs. Design questions are **already decided here** —
do not re-open them; if you believe a decision is wrong, STOP and report rather than deviating.

Companion reading (read both before writing code):
- `m1-remainder-scoping.md` — exemplar adapter anatomy, per-service table, test patterns, fixtures.
- `m1-remainder-unknowns.md` — the traced code facts these decisions rest on (U1–U5).

## Scope

Seven new adapters in `src/research_foundry/services/operator_mcp_adapters/`, following the landed
`run_plan.py` / `swarm_start.py` / `job_lifecycle.py` pattern exactly. All seven canonical services
already exist and are plain, typed, `paths`-injectable functions — **no service extraction is
required**, and none is permitted. All seven `operation_kind` strings already exist in the closed
`OPERATION_KINDS` enum and are already classified `_MUTATION_ROLES`; **no policy edit is needed or
allowed**.

| operation_kind | canonical service |
|---|---|
| `external_report.import` | `external_research_import.import_external_report()` |
| `source.ingest` | `source_cards.ingest_source()` |
| `run.extract` | `extraction.extract_run()` |
| `run.claim_map` | `claim_mapping.build_claim_ledger()` |
| `run.synthesize` | `synthesis.synthesize_report()` |
| `run.verify` | `verification.verify_report()` |
| `run.bundle` | `writeback.build_bundle()` |

## Hard boundaries (violating any of these is a STOP-and-report, not a judgment call)

1. **Do not edit** `operator_mcp_policy.py`, `operator_operation_service.py`,
   `operator_cancel_resume_service.py`, or `operator_mcp_adapters/base.py`. These carry the P1/P2
   confirmation and authorization semantics, which are MUST-stay-primary and already gated.
2. **Do not edit** any canonical service (`writeback.py`, `verification.py`, `source_cards.py`, …).
   M1 wraps them; it does not change them. `writeback.py` is additionally a declared serialization
   barrier shared with M2.
3. **Do not edit** `operator_mcp_adapters/__init__.py`. The integration owner registers the new
   adapters there. Write your modules; leave registration alone.
4. **Do not edit** `cli_commands.py`. M1's AC requires CLI parity to hold.
5. No Typer, `cli_commands`, `subprocess`, `os.system`, or `shell=True` anywhere in an adapter call
   path. Not even in a comment-as-example.

## Decisions

### D1 — `sensitivity_ceiling` is resolved, never accepted (MANDATORY, every adapter)

Reproduce the `8b694d5` pattern verbatim. The adapter takes **no** `sensitivity_ceiling` parameter.
It resolves structurally:

```python
from . import resolve_local_sensitivity_ceiling  # lazy import, avoids circular import

resolved_paths = paths or FoundryPaths.discover()
sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
```

`resolve_local_sensitivity_ceiling` fail-closes to `"public"` and never raises. A caller-supplied
ceiling is a fail-open hole — that exact defect was found at all five P3 adapter boundaries and is
the single most likely way this milestone regresses.

**Each of the seven adapters gets an H7 negative fixture**, modelled on
`test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_intent`
(`test_operator_mcp_adapter_run_plan.py:460-`): write a lower-than-default ceiling into
`tmp_foundry`'s `foundry.yaml`, submit an above-ceiling target, and assert the denial is
**shape-identical to a missing-target denial** (proves the guard fires *and* leaks no existence
information).

### D2 — `source.ingest` workspace binding

`assertion_registry_workspace_id = ctx.identity.workspace_id`. The literal string `"default"` must
not appear in the adapter module. `cli_commands.py:354` currently hardcodes
`resolve_or_deny("default")`; **do not copy it, and do not fix it** — changing the shipped CLI's
workspace resolution is a behavior change outside M1 (AC requires CLI parity). It is logged as a
follow-up.

Required tests: (a) a non-default identity workspace threads through to `ingest_source`;
(b) a source-level assertion that `"default"` appears nowhere in the module.

### D3 — `external_report.import` dry-run: ONE dry-run concept, the substrate's

`base.run_pipeline`'s dry-run path (`base.py:263-269`) runs the five non-confirmation policy stages
and **never invokes `actions` at all**. `import_external_report` also has its own native `dry_run`
which is likewise a true zero-effect plan (U3).

**Decision: the adapter surface exposes exactly one dry-run — the substrate's.** On the live path
call `import_external_report(..., dry_run=False, ...)`. The service's own `dry_run` is deliberately
unreachable from the adapter. Two dry-run concepts on one governed surface is a footgun, and the AC
that matters ("dry-run produces zero effects") is the substrate's.

`resume` **is** forwarded as a distinct adapter parameter — it is a real, separate live-path
concept (bypasses the `PendingImportError` pending-checkpoint guard and continues from the stored
cursor). Document in the module docstring that adapter-`dry_run` short-circuits before the service,
so `resume` is meaningful only when `dry_run=False`.

Thread these `ImportOutcome` refs into the bounded result: `workspace_id`, `target_run_id`,
`packet_digest`, `receipt_id`, `receipt_digest`, `status`.

### D4 — `run.verify`: non-passing is a governed RESULT, not an execution failure

Per U1 the substrate has no third channel: a closure that returns is `completed`/`ok=True`, one
that raises is `failed`/`ok=False`.

- **Verification ran and returned `passed=False`** → the closure **returns normally**. The bounded
  result carries `passed: False` plus the unsupported/failed-claim summary and a reason code. The
  adapter result is `ok=True` with `result["passed"] is False`. Rationale: the operation was
  performed correctly and produced a verdict; `ok=False` means "could not be performed".
  This is what the AC's "verify failure is a **typed governed result**" names.
- **Missing input** (no report, no claim ledger) and **quarantine** → denied at the **prerequisite
  stage**, before the action runs, with a reason code and **zero effects**. Never raise for these;
  the AC is explicit that they "deny with reason codes rather than raising".
- Do not raise on `passed=False`. Do not map it to `ok=False`.

### D5 — `run.bundle`: the block is a PREREQUISITE, not a delegated check

**Do not rely on `build_bundle(verify=True)` to block.** U2 established that it never blocks: it
writes `evidence_bundle.yaml` unconditionally, marks it `status="draft"` /
`approved_for_writeback=False`, and its bare `except Exception` swallows a verify *crash* into the
same "not verified" state.

The `run.bundle` adapter therefore enforces the block itself, as a **prerequisite stage**:

1. Before the action runs, require an existing **passing** verification for the run. Absent or
   non-passing → deny with reason code (e.g. `verification_not_passed`), action never invoked,
   **zero effects**. This is the AC's "unsupported verification blocks dependent bundle action".
2. On the live path, call `build_bundle(run_id, verify=True, paths=...)` and then **inspect
   `BundleResult.verified`**. If it is `False`, verification state changed between the prerequisite
   check and the action — raise inside the closure so the operation terminates `failed`
   (`ok=False`) rather than reporting a draft bundle as success.

**Known limitation to state plainly in the module docstring and the completion report** (do not
paper over it): in that race, `build_bundle` has *already written* `evidence_bundle.yaml` before
returning, so the failed operation is not perfectly zero-effect. Closing that requires changing
`writeback.py`, which is out of M1 scope and a shared serialization barrier. It is logged as a
follow-up.

### D6 — parity tests: spy, do not double-call

Reuse the exemplar pattern (`test_operator_mcp_adapter_run_plan.py:264-352`): `monkeypatch.setattr`
a spy that wraps the **real** service and captures its single call, then assert the adapter's
bounded `result.result` carries the **same canonical ids/paths** the direct result object holds,
field by field. Do not call the service twice — every one of these seven mints fresh artifact ids
per call, so a double-call equivalence check is meaningless.

Reuse `tests.unit.test_operator_cancel_resume_service._consume` for interrupted/resumed scenarios,
and the standard identity injection:

```python
identity = AuthIdentity("alice", "ws-mine", ("owner",))
monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
```

### D7 — retry idempotency

Exact retry of any of the seven must create no duplicate source card, claim, import receipt, or
candidate artifact. This comes from the substrate's idempotency-key handling — do **not** add your
own dedup layer. Add a test per adapter proving exact retry returns the prior state.

## Defect-class checklist (MANDATORY — carried verbatim from the plan)

1. **No fail-open defaults.** No permissive default on a security-relevant field, no
   `None`-means-skip, no unknown-label fallback that grants rather than denies. Check the
   *producer* of a value, not just the field.
2. **Fix the layer below.** After hardening a symbol, enumerate its delegates, callers, and
   siblings in `__all__` and ask whether reaching for any of them yields the unsafe behavior.
3. **Never pin unsafe behavior with a test.** If a test asserts current behavior and the current
   behavior is wrong, the test is wrong — say so and invert it.
4. **Never fabricate a validation transcript.** Paste real output or report the failure.

## Environment notes (each has already burned a round)

- Run tests as `./.venv/bin/python -m pytest ...` from the worktree root. The pyenv shim cannot
  import `research_foundry`.
- `pyproject.toml` sets `[tool.pytest.ini_options] pythonpath = ["src"]`, inserted **ahead** of the
  `PYTHONPATH` env var. A `PYTHONPATH=$PWD/src` prefix is decorative and provides no isolation.
- **`FAILED` lines carry ANSI codes** — `grep "^FAILED"` returns 0 on a red suite. Match unanchored
  or strip ANSI before concluding a suite is green.
- Baseline: the full unit suite has 3 known pre-existing failures
  (`test_assertion_rollout.py` ×2, `test_report_anchors.py` ×1). They reproduce on `main`. Do not
  chase them; do not count them as yours.
