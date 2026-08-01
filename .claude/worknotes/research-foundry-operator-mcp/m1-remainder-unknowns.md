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

# M1 remainder — resolved unknowns (code facts, traced 2026-07-31)

Facts only, with file:line evidence. Decisions derived from these live in
`m1-remainder-implementer-contract.md`.

## U1 — `run_or_replay` / `ActionSpec` failure contract

`ActionSpec.run` (`operator_cancel_resume_service.py:207`) returns `ActionEffect | None`. As far as
`run_actions` (`:629`) is concerned the closure has exactly **two** outcomes:

- **returns normally** → recorded `status="completed"` (`:890-933`), regardless of the payload's
  content;
- **raises** → `except Exception` (`:797`) records a `failed` action receipt with
  `reason_code="internal_error"`, writes a `"converged"` checkpoint, finalizes the terminal receipt
  `status="failed"`, and returns `ExecutionOutcome("failed", ...)`.

`ExecutionOutcome.status` (`:262`) is `Literal["completed","canceled","failed","denied"]`;
`run_or_replay` (`:1063`) adds no fifth status, and `"denied"` there means corrupt receipt-store
state, not an authorization denial.

`base.run_pipeline` maps this straight through (`base.py:346-354`): `ok=False` for
`status in ("failed","denied")`, `ok=True` for `("completed","canceled")`.

**ANSWER:** there is **no channel** for "the action ran fine but its governed verdict did not pass."
An adapter that wants `ok=False` on a non-passing governed result must **raise** inside its `run`
closure; anything that returns normally is `ok=True`.

## U2 — `build_bundle` verify-blocking

`writeback.py:204-260`. When `verify=True` and the internal `verify_report` returns `passed=False`
— **or raises** — `build_bundle` does **not** raise, does **not** return a blocking status, and does
**not** stop writing:

```python
verified = False
if verify:
    try:
        from .verification import verify_report
        vr = verify_report(run_id, paths=paths)
        verified = bool(vr.passed)
    except Exception:  # noqa: BLE001 - verification optional / degrades
        verified = False
    ...
    bundle = {..., "status": "verified" if verified else "draft", ...,
              "governance": {..., "approved_for_writeback": verified, ...}}
    _schema_or_raise(bundle, "evidence_bundle")
    dump_yaml(bundle, rp.evidence_bundle)          # <- unconditional
    return BundleResult(..., verified=verified)
```

`_schema_or_raise`/`dump_yaml` (`:251-252`) run unconditionally — `evidence_bundle.yaml` is written
to disk whether verification passed, failed, or threw. The blocking that *does* exist is downstream,
in the separate `writeback()`/dispatch gate reading `governance.approved_for_writeback`
(`writeback.py:619`, `~:2234-2236`).

**ANSWER:** `build_bundle` never blocks on verify failure; it always writes the bundle and merely
marks it `status="draft"` / `approved_for_writeback=False`. Its bare `except Exception` also
**swallows a verify crash into "just not verified"** — a fail-open degrade.

## U3 — `import_external_report` dry_run / resume

Docstring (`external_research_import.py:356-360`) and every `dry_run` site:

- `:487` — batching/limiting disabled when `dry_run=True`.
- `:492-526` — the `if dry_run:` branch calls `interchange.stage(..., dry_run=True)` and returns
  immediately, skipping the receipt-identity lease (`:537`), the `PendingImportError` guard
  (`:545-555`), and the run-timeline write.
- `:611` — `if target_run_id is not None and not dry_run:` gates
  `record_external_report_import_activity`.
- Inside `interchange.stage()` (`external_research_interchange.py:2027-2028`, `:2053-2070`) both
  `dry_run` checks return a `StageResult(..., dry_run=True, checkpoint=None)` before any write path.

**Writes under `dry_run=True`: none** — no receipt, checkpoint, staging artifact/effect, timeline
event, or lease acquisition.

`resume=True` is consulted **only on the non-dry-run path**, inside the
`interchange._receipt_lease(receipt_digest)` block (`:537-588`): without it, a pre-existing
`pending` checkpoint for the same identity raises `PendingImportError` (`:551-555`); with it, that
guard is skipped and `stage(..., _lease_already_held=True)` continues from the checkpoint's stored
cursor. No effect on a fresh import, and no effect at all when `dry_run=True`.

**ANSWER:** the service's native `dry_run` is already a true zero-effect plan; `resume` only
bypasses the pending-checkpoint guard on the live path.

## U4 — `_OPERATION_ROLES` for the seven kinds

`operator_mcp_policy.py:600-644`. Buckets: `_AGENT_JOB_ROLES={owner,admin}`,
`_MUTATION_ROLES={owner,admin,researcher}`, `_READ_ROLES={owner,admin,researcher,reviewer}`.

| operation_kind | classification | line |
|---|---|---|
| `external_report.import` | `_MUTATION_ROLES` | 616 |
| `source.ingest` | `_MUTATION_ROLES` | 617 |
| `run.extract` | `_MUTATION_ROLES` | 618 |
| `run.claim_map` | `_MUTATION_ROLES` | 619 |
| `run.synthesize` | `_MUTATION_ROLES` | 620 |
| `run.verify` | `_MUTATION_ROLES` | 621 |
| `run.bundle` | `_MUTATION_ROLES` | 622 |

**ANSWER:** all seven are `_MUTATION_ROLES`; none is misclassified read-only. No policy change
needed — and none is permitted at M1 regardless (MUST-stay boundary).

## U5 — `resolve_local_sensitivity_ceiling`

`operator_mcp_adapters/__init__.py:110`:
`def resolve_local_sensitivity_ceiling(paths: FoundryPaths | None = None) -> str:`

Reads `operator_mcp.sensitivity_ceiling` from `foundry.yaml`; returns it only when it is a `str`
member of `policy.SENSITIVITY_LEVELS`. On **any** failure — missing block/key, non-string, unknown
label, or any exception including `FoundryPaths.discover()` — it returns `SENSITIVITY_LEVELS[0]`
(`"public"`), the most restrictive ceiling. Declared "Never raises" (`:122`).

Landed call site (`run_plan.py:197-201`):

```python
from . import resolve_local_sensitivity_ceiling  # lazy, avoids circular import

resolved_paths = paths or FoundryPaths.discover()
sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
```

**ANSWER:** fail-closed to `"public"`, never raises, resolved structurally from config — never a
caller-supplied parameter.
