---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
created: '2026-07-31'
updated: '2026-07-31'
---

# Fix 2 completion — F1/F7 in `research_stages.py` (M1 remainder pre-gate)

Source finding: `.claude/findings/m1-remainder-pregate-consolidated.md` (F1, F7).
Files owned/touched: `src/research_foundry/services/operator_mcp_adapters/research_stages.py`,
`tests/unit/test_operator_mcp_adapter_research_stages.py`. No other file was edited.

## What was wrong (F1, BLOCKING)

`run.claim_map` (requires target kinds `{"run", "extraction_card"}`) and `run.synthesize`
(requires `{"run", "claim_ledger"}`) declared those secondary target kinds but never checked
that the underlying artifact actually existed on disk — `_check_preflight` only verifies a
`TargetRef` of each *kind* is present, never that the referenced extraction card(s)/claim
ledger exist. Consequence (both empirically reproduced by the two pre-gate lenses):

- a valid, owned run with **zero extraction cards** → `run.claim_map` returned
  `ok=True, claims_total=0`;
- a valid, owned run with **no claim ledger** → `run.synthesize` returned `ok=True` with a
  fully "completed" placeholder report (`synthesis._load_ledger` silently substitutes an empty
  ledger instead of raising).

Neither denied with a reason code — silent success, strictly worse than a crash, since a
placeholder report is indistinguishable from a real one downstream.

## What was wrong (F7, LOW)

The secondary `extraction_card`/`claim_ledger` `TargetRef` reuses `run_id` as its own ref and
resolves to the same workspace as the primary `run` target, so its own RBAC check is a provable
no-op. It looked like an independent check but never was one — and that apparent redundancy is
part of what let F1 through unnoticed.

## The fix

Added three read-only, best-effort, fail-closed prerequisite checks
(`_extract_prerequisites_met`, `_claim_map_prerequisites_met`, `_synthesize_prerequisites_met`)
plus a `_preflight_denial` helper (a narrow, module-private duplicate of
`verify_bundle._preflight_denial` — not imported, since that module is out of this task's file
ownership).

**Ordering is the important part, and it deliberately does NOT copy `verify_bundle.py`'s own
shape.** `verify_bundle.py`'s sibling prerequisite gate runs *before* `ctx` is even constructed —
for any caller, authorized or not — which is exactly the F6 finding (an unauthorized caller can
distinguish "run exists but lacks the artifact" from "not found/not yours" by reason code alone,
across a real workspace boundary). Since another agent was fixing F6 in `verify_bundle.py`
concurrently, and that file is out of bounds here, I did not reproduce the same ordering in
`research_stages.py`. Instead, each `invoke_extract`/`invoke_claim_map`/`invoke_synthesize` now:

1. builds `ctx` as before;
2. calls `policy.evaluate_policy(ctx, paths=resolved_paths)` itself — the same
   capability → rbac → audit_health → guard → preflight stack `base.run_pipeline`'s dry-run path
   and `authorize_operation` both already re-run (`authorize_operation`'s own docstring: "policy
   may have drifted since mint time" — re-evaluation is an established, tolerated pattern here,
   not a shortcut I invented);
3. returns that decision's denial verbatim if it denies (byte-identical to what
   `base.run_pipeline` would have produced, just short-circuited earlier);
4. **only if `evaluate_policy` returned `allowed=True`** — i.e. only for a caller already proven
   to own this run's workspace — runs the new on-disk existence check, denying `preflight_failed`
   if the artifact is missing;
5. otherwise proceeds to `base.run_pipeline(...)` exactly as before.

This closes F1 (governed `ok=False`/`preflight_failed` denial, canonical service never invoked,
zero effects) without opening F6's leak: an unauthorized caller still denies at
`rbac`/`not_found` exactly as before and never reaches the new branch, proven by a new test (see
below). The gate runs regardless of `dry_run`, mirroring `verify_bundle.py`'s own
"gate-before-execution, dry run or not" shape.

F7 is documented, not "fixed" by inventing a new field: the module docstring now states plainly
that the secondary target is a kind-label required by `_REQUIRED_TARGET_KINDS`, not an
independent check, and that the real existence check is the new prerequisite-gate functions.

## Checklist item 2 applied to `run.extract` ("fix the layer below")

`run.extract` declares only the single `{"run"}` target kind (no secondary target to
under-check, unlike the other two) — so it's not literally F1's shape. But it has the exact same
defect *class*, one hop upstream: `extraction.extract_run` raises `NotFoundError` for a wholly
missing run (unaffected — RBAC already denies that before reaching this code), but for a run
that exists with **zero `sources/*.md` cards**, it silently returns
`ExtractResult(cards=[], count=0)`, `ok=True`. Since this is the same file I own and the same
class of bug, I gated it too (`_extract_prerequisites_met`), using the identical
authorize-then-check pattern, rather than leaving a known-equivalent silent-success path open
right next to the one I was fixing.

## Regression tests (all fail pre-fix, verified)

Added to `tests/unit/test_operator_mcp_adapter_research_stages.py`:

- `test_invoke_extract_denies_preflight_failed_when_no_source_cards`
- `test_invoke_claim_map_denies_preflight_failed_when_no_extraction_cards`
- `test_invoke_claim_map_denies_preflight_failed_for_unauthorized_caller_without_leaking_prerequisite_state`
  (F6 lesson: proves an unauthorized/wrong-workspace caller against a run with zero extraction
  cards still denies `not_found`, never `preflight_failed`)
- `test_invoke_synthesize_denies_preflight_failed_when_no_claim_ledger`

Each of the three `preflight_failed` tests mints a **real, valid confirmation** (mirroring the
existing `_result_matches_direct_*_call` tests' own pattern) so the pre-fix run actually reaches
execution — without a valid confirmation, a pre-fix call denies `confirmation_missing` for an
unrelated reason and never proves anything about F1.

**Pre-fix verification (real command output, `git stash` on the source file only, tests kept):**

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_research_stages.py \
    -k "preflight_failed or leaking_prerequisite"
...
FAILED ...test_invoke_extract_denies_preflight_failed_when_no_source_cards - AssertionError: assert 'internal_error' == 'preflight_failed'
FAILED ...test_invoke_claim_map_denies_preflight_failed_when_no_extraction_cards - AssertionError: assert 'internal_error' == 'preflight_failed'
FAILED ...test_invoke_synthesize_denies_preflight_failed_when_no_claim_ledger - AssertionError: assert 'internal_error' == 'preflight_failed'
3 failed, 1 passed, 12 deselected in 0.51s
```

(The `internal_error`/failed outcome, not `ok=True`, is a side effect of the test's own
`_must_not_run` spy raising `AssertionError` inside the canonical-service call site — proof the
pre-fix adapter *did* call the canonical service for a missing-prerequisite run, which is exactly
the F1 defect; without the spy it would have returned `ok=True` with the placeholder/zero
result, as both lenses reported. The 4th test, the F6-lesson unauthorized-caller test, passed
pre-fix too, as expected — it's a pre-existing RBAC path, unrelated to this fix.)

No existing test in this file asserted or otherwise pinned the missing-prerequisite silent-
success behavior (checklist item 3) — every pre-existing test already seeds the required
artifacts via `_extracted_run`/`_claim_mapped_run` before invoking the adapter under test, so
none needed inverting.

## Post-fix validation (real command output)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_research_stages.py -v
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
rootdir: .../research-foundry/.claude/worktrees/operator-mcp-v1
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.13.0
collected 16 items

tests/unit/test_operator_mcp_adapter_research_stages.py ................ [100%]

============================== 16 passed in 1.43s ==============================
```

16/16 passed (12 pre-existing + 4 new), 0 failures, 0 errors, no `FAILED` lines. Ran under
`./.venv/bin/python`, not the pyenv shim. Confirmed the module still imports cleanly
(`python -c "import research_foundry.services.operator_mcp_adapters.research_stages"` → OK) and
no other test file imports `research_stages` directly (grep-verified), so no cross-file blast
radius from this change.

## Hard boundaries respected

Only `research_stages.py` and its own test file were edited. Did not touch
`operator_mcp_policy.py`, `operator_operation_service.py`,
`operator_cancel_resume_service.py`, `base.py`, `__init__.py`, `verify_bundle.py`,
`synthesis.py`, `claim_mapping.py`, `extraction.py`, or `cli_commands.py` — read several of them
(`base.py`, `operator_mcp_policy.py`, `operator_cancel_resume_service.py`, `extraction.py`,
`claim_mapping.py`, `synthesis.py`, `paths.py`) to confirm the fix's correctness (e.g. that
raising inside an `ActionSpec.run()` closure always collapses to a generic `internal_error`
reason code with no way to inject a specific one — which is why the fix denies *before*
`base.run_pipeline`/the action closure is ever reached, rather than inside it).
