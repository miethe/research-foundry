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

# M2 leg A completion note — `writeback.preview` (task OPM-5.3)

**Delta (post-orchestrator-adjudication of JC-2)**: `preview_writeback` now
supports FIVE targets, not three — `meatywiki`/`skillmeat` added via a
destination-override on the existing live render functions (never
duplicated assembly). `ccdash` confirmed staying `unsupported_target`
(file-ownership boundary), filed by the orchestrator as a follow-up ITT
node. See "JC-2 — RESOLVED" below and the updated D8 table/test counts.

## What was built

1. **Layer-below refactor in `writeback.py`** (D6). `_render_intenttree_update`,
   `_render_arc_council`, `_render_notebooklm_update` each split into a pure
   payload function (`_intenttree_update_payload`, `_arc_review_payload`,
   `_notebooklm_update_payload`) + the existing live wrapper recomposed as
   pure-render → write → live-push. `_notebooklm_update_payload` never
   constructs a client itself — it accepts an already-resolved
   `notebook_id`/`notebook_title`; the live wrapper still calls
   `notebook_correlation.resolve_notebook(..., client=<real client>,
   create=True, ...)` UNCHANGED (preserving its create-on-first-push
   behavior exactly), while the preview seam resolves correlation via the
   READ-ONLY `notebook_correlation.notebook_for_run` instead (never creates
   a notebook, never writes the correlation registry — genuinely
   structurally client-free, not merely "doesn't call `.available()`").
   Live behavior is byte-identical: every pre-existing `writeback`-keyword
   test stays green **unmodified** (155 passed, see Validation below).
2. **New public seam** `writeback.preview_writeback(run_id, *, targets,
   paths=None, now=None) -> WritebackPreviewResult` — validates the run,
   renders per-target candidates using ONLY the pure payload functions
   above, and stages them under `<run_dir>/staging/writeback_preview/
   <target>.json`. Zero integration-client import/construction/call
   anywhere in its call graph for every supported target. New closed
   vocabularies: `WRITEBACK_PREVIEW_TARGET_STATUSES` (`staged`,
   `missing_bundle`, `unsupported_target`, `degraded`) and
   `WRITEBACK_PREVIEW_SUPPORTED_TARGETS` (`{intenttree, arc, notebooklm}`).
3. **New adapter** `operator_mcp_adapters/writeback_preview.py` — `invoke_preview`
   + `WritebackPreviewAdapter`, registered via `base.register(PREVIEW_ADAPTER)`,
   mirroring `verify_bundle.py`'s exact shape (`PolicyContext` →
   `ActionSpec` → `action_manifest` → `build_result` → `base.run_pipeline`).
4. **Registration**: one import line added to `operator_mcp_adapters/__init__.py`
   (matches the existing lines 91-97 pattern) — `from . import
   writeback_preview as _writeback_preview  # noqa: F401`.
5. **Tests**: `tests/unit/test_operator_mcp_adapter_writeback_preview.py`
   (10 tests) + `tests/integration/test_operator_mcp_writeback_preview.py`
   (4 tests, extended assertions) — 14 tests, all passing.
6. **JC-2 extension — `meatywiki`/`skillmeat` preview support** (per
   orchestrator adjudication). `_render_meatywiki`/`_render_skillbom` each
   gained two new keyword parameters, `dest: Path | None = None` and
   `stage_only: bool = False`, both defaulting to the pre-existing behavior
   (every pre-existing call site in `writeback()`/`skillbom_propose()`
   omits them, so live behavior is unchanged — proven below). `preview_
   writeback` calls these SAME functions with `dest=<staging path>,
   stage_only=True`: the write is redirected to the staging root and BOTH
   the local-workspace mirror (`paths.meatywiki/sources/`,
   `paths.skillmeat/skillboms/`) and — for skillmeat specifically — the
   SkillBOM registry upsert (`Registry.open(SKILLBOM_INDEX, ...).upsert
   (...)`) are unconditionally suppressed. `WRITEBACK_PREVIEW_SUPPORTED_
   TARGETS` is now `{intenttree, arc, notebooklm, meatywiki, skillmeat}` —
   `ccdash` is the sole remaining `unsupported_target` member of
   `writeback()`'s six-member vocabulary.

## Judgment calls (flagged, not silently made)

### JC-1 — "operation staging root" does not exist as a filesystem concept in this codebase

D6/OPM-OQ-7 both phrase the staging location as `<operation_dir>/staging/
writeback_preview/<target>.md|.json`, "colocated with where
`operator_operation_service` writes manifests/receipts." I read
`operator_operation_service.py` end to end as instructed: **operator
operations are DB-only** — every manifest, attempt, action/effect receipt,
and terminal receipt lives in `operator_operations.db` under `.rf_state/`
(`paths.FoundryPaths.operator_operations_db`). There is no per-operation
filesystem directory anywhere in this codebase; `operation_id` never maps
to a directory. The contract's literal phrasing does not correspond to
anything that exists.

**Resolution**: staging anchors under the run's OWN directory tree instead
— `<run_dir>/staging/writeback_preview/<target>.json` — the one filesystem
container every other adapter already treats as the authorized/workspace-
scoped boundary (`verify_bundle.py`'s F5 fix, `_explicit_path_within_run`,
uses exactly this same run-root containment guarantee). It is **not**
namespaced by `operation_id` (the `preview_writeback` signature the
contract itself specifies has no such parameter): a second preview call for
the same run overwrites the prior staged files — the same idempotent-
overwrite convention every other writeback candidate file in `writeback.py`
already follows (`_render_meatywiki`, `_render_skillbom`, etc. all
overwrite unconditionally on each call).

**Consequence for exact-replay**: on a genuine exact-replay of an
already-terminal `writeback.preview` operation, `_run()` is never invoked a
second time (same substrate behavior every adapter in this family
documents), so the staged files on disk reflect the MOST RECENT preview
call for that run, not necessarily the exact-replayed operation's own
point-in-time state. This is the same "replay result-recovery gap" every
other M1/M2 adapter already reports as a known limitation, not a new one.

**Recommend the security lens verify**: that overwriting staged files
across concurrent/differently-scoped operations for the same run cannot
leak one caller's preview content to a differently-authorized caller who
happens to read the staging directory directly (out of band from the
`OperatorAdapterResult` envelope) — the staging directory itself has no
independent access-control check beyond "inside the run directory," same
as every other artifact under `runs/<run_id>/`.

### JC-2 — RESOLVED by orchestrator adjudication: `meatywiki`/`skillmeat` now supported; `ccdash` stays a follow-up

Original flag: `writeback()` has six target names (`meatywiki`,
`skillmeat`, `ccdash`, `intenttree`, `arc`, `notebooklm`); this leg
initially supported only the three D6 names for the layer-below split. The
orchestrator adjudicated:

1. **EXTEND to `meatywiki`/`skillmeat`** — done (see "What was built" §6
   above). Preserves live behavior byte-identically: `dest`/`stage_only`
   are new OPTIONAL keyword parameters on `_render_meatywiki`/
   `_render_skillbom` that default to the pre-existing call shape;
   `writeback()`'s and `skillbom_propose()`'s existing call sites are
   unmodified and pass neither, so `dest=None -> target_write = rp.
   meatywiki_writeback` (or `rp.skillbom_candidate`) and `stage_only=False`
   runs the mirror/registry write exactly as before. Proven both by the
   pre-existing `writeback`-keyword test suite staying green unmodified
   (156 tests, up from 155 after the JC-2 extension) and by a dedicated
   scratch-revert regression proof (see Validation below) showing the two
   NEW meatywiki/skillmeat-specific tests genuinely fail without this
   change.
2. **`ccdash` stays `unsupported_target`** — its live render path
   (`telemetry.emit_ccdash_event`) also constructs a client
   (`CCDashClient`, lazy import at `telemetry.py:266-270`), but
   `telemetry.py` is outside both this leg's file ownership AND M2's
   declared `files_affected`. The orchestrator is filing this as a
   follow-up ITT node rather than carrying it here as an open gap — no
   further action needed from this leg.
3. Test coverage extended per orchestrator instruction #4: the integration
   test's `_spy_all_integration_seams` fixture (already autouse, already
   spying `get_meatywiki_client`/`urlopen` globally) now has its "full
   matrix" / "missing-bundle" / "review-required" test bodies request
   `meatywiki`/`skillmeat` alongside the original three targets, so the
   zero-client-construction proof now covers all five supported targets
   across every outcome branch (staged, missing-bundle, review-required
   denial), not just the original three.

### JC-6 — new: skillmeat preview candidate omits the real `ccdash_event_id`

`preview_writeback` calls `_render_skillbom(..., ccdash_event_id_value="",
...)` for the `skillmeat` target — an empty string, never the real CCDash
event id `writeback()`'s own call site derives from `telemetry.
emit_ccdash_event(...)`'s return value. This is deliberate, not an
oversight: computing the real value would require calling
`telemetry.emit_ccdash_event`, which constructs `CCDashClient` internally
(the same JC-2/ccdash file-ownership boundary). The staged skillmeat
candidate's `performance_evidence.ccdash_event_id` field and its body's
"CCDash event id:" line are therefore always empty in preview output — a
real, known content difference from what a subsequent live `writeback()`
call would produce for the same run. Flagged for the security/product
review: is an empty placeholder acceptable for a preview artifact, or
should this field be omitted/marked differently when it cannot be
resolved?

### JC-3 — no per-target `review_required` status; review-required denies the WHOLE operation one layer up

`writeback.preview_writeback` does **not** have a `review_required` member
in its own closed status vocabulary. `PolicyContext.writeback_targets`
(populated from the caller's requested `targets`, normalized) feeds
`governance.GuardContext.writeback_targets` inside
`operator_mcp_policy._check_guard`, which fires the SAME
`intenttree_writeback_requires_review`/`arc_writeback_requires_review`
rules every other writeback path already triggers. A request whose
sensitivity would trigger one of those rules denies with
`reason_code=guard_review_required` (retryable) **before** `_run()` — and
therefore before `writeback.preview_writeback` — is ever invoked. Proven by
`test_invoke_preview_review_required_denies_before_preview_writeback_runs`
(unit) and `test_preview_review_required_denial_zero_client_calls`
(integration): both spy on `writeback.preview_writeback` / every
integration client and assert zero calls on the denial path.

This reading of AC OPM-6's resilience row ("review-required sensitivity ...
produce preview reason codes") is that `guard_review_required` **is** one
of the "preview reason codes" — the standard closed `operator_mcp_error`
reason-code vocabulary, not a new member of my own per-target status set. I
believe this is the correct, intended reading (D6's own text: "the SAME ...
guard rules apply here as everywhere else" — i.e., denied the same way,
not downgraded to an informational flag), but flagging the alternative
reading for the security lens to confirm.

### JC-4 — "missing bundle" is a whole-operation governed condition, not per-target-selective

When `rp.evidence_bundle` does not exist on disk, **every** requested
target reports `missing_bundle` (not a mix of statuses) and **zero**
staging directory is created — `preview_writeback` never calls
`staging_root.mkdir(...)` on this path. This was a deliberate choice over
the alternative (deriving a deterministic `bundle_id` via `ids.bundle_id
(run_id)` even without an on-disk bundle, the way `writeback()`/
`build_bundle` themselves do, and rendering anyway) — I judged that
`writeback.preview`, unlike `writeback()`, must never implicitly stand in
for `run.bundle` having been called first; the AC explicitly lists "missing
bundle" as a blocking/degraded condition, and `_REQUIRED_TARGET_KINDS
["writeback.preview"] == frozenset({"evidence_bundle"})` in
`operator_mcp_policy.py` independently signals that a real evidence bundle
is the expected precondition.

### JC-5 — D9's "httpx" spy target does not exist in this codebase

D9 instructs monkeypatching `httpx` as one of the integration test's
network spies. This codebase has **no `httpx` dependency at all** —
`integrations/base.py`'s own module docstring: "No new required dependency
is introduced — all HTTP calls use the stdlib `urllib.request`/
`urllib.error` so the package installs without httpx." The integration test
instead spies on the REAL primitive, `urllib.request.urlopen`, which is a
strictly stronger proof (it would catch a hypothetical FOURTH client this
leg didn't anticipate, not just the three named ones).

## D8 — caller-input / authorization table (`writeback.preview` / `invoke_preview`)

| Caller-supplied input | Reaches | Authorized / bounded by |
|---|---|---|
| `run_id` | `TargetRef("run", run_id)` + `TargetRef("evidence_bundle", run_id)`; `writeback.preview_writeback(run_id, ...)` | RBAC stage matches BOTH `resolved_target_workspaces` entries (from `_resolve_run_context`, fail-closed to `(None, None)` on any `run.yaml` read/parse failure) against the caller's identity — a foreign/nonexistent run denies `not_found` before `_run()` ever executes (same F6 convention as every M1 adapter). |
| `idempotency_key` | `ctx.idempotency_key`; `op_service.consume_and_create_operation` | `operator_operation_service`'s `UNIQUE(workspace_id, idempotency_key)` + canonical-digest match/conflict logic (idempotency_conflict on digest mismatch); length/pattern-bounded in `_check_capability` (`_IDEMPOTENCY_KEY_MAX_LENGTH`/`_PATTERN`) — none of this owned or modified by this leg. |
| `targets` (`Sequence[str]`) | Sorted+deduplicated into `normalized_targets` → `ctx.writeback_targets` (feeds `GuardContext.writeback_targets`) AND `writeback.preview_writeback(targets=normalized_targets)` | Non-emptiness enforced by `_check_preflight` (BLOCK-7, `preflight_failed` if empty). Sensitivity-driven review-required guard rules fire on these SAME values at the guard stage (JC-3). Inside `preview_writeback`, EACH individual target string is re-validated against the closed `WRITEBACK_PREVIEW_SUPPORTED_TARGETS` set — an unrecognized/unsupported name never reaches ANY render or client call path, only the governed `unsupported_target` status (JC-2). |
| `confirmation_record` / `presented_token` | `authorize_for_consumption` → `consume_and_create_operation` | Standard confirmation TTL/single-use/mismatch checks in `operator_operation_service.py` — not owned or modified by this leg. |
| `dry_run` | `base.run_pipeline`'s branch | Fixed substrate behavior (`base.py`, not owned by this leg): policy-only evaluation; `_run()` (and therefore `writeback.preview_writeback`) is never invoked. |
| `now` | Threaded straight to `writeback.preview_writeback`'s own `generated_at` field only | Not authorization-relevant — a pure determinism/testability knob; never affects which targets render or their content, only the one timestamp field. |
| `paths` / `operations` / `cancel_resume` | Internal DI plumbing (test/server-construction only) | Not part of the MCP tool's caller-facing surface — same convention as every other adapter in this family; the real tool schema exposes only `run_id`/`targets`/`dry_run`. |

**New (post-JC-2-extension) internal parameters — verified NOT caller-reachable.**
`_render_meatywiki`/`_render_skillbom` gained `dest: Path | None` and
`stage_only: bool` keyword parameters. Neither is exposed anywhere on
`invoke_preview`'s signature, `PolicyContext`, or the MCP tool's caller-
facing surface — they exist ONLY on the two `writeback.py`-internal render
functions. What pins them inside `preview_writeback` (the only caller that
ever passes non-default values):

- `dest` is always `staging_root / f"{target}.md"`, where `staging_root =
  rp.run / "staging" / "writeback_preview"` (computed from `run_id`, not
  caller input) and `target` is a value ALREADY constrained to the closed
  `WRITEBACK_PREVIEW_SUPPORTED_TARGETS` membership check (`if target not in
  WRITEBACK_PREVIEW_SUPPORTED_TARGETS: ... continue`) performed earlier in
  the SAME loop iteration, before this branch is ever reached. By
  construction `target` can only be the literal string `"meatywiki"` or
  `"skillmeat"` at this call site — never arbitrary caller-influenced text
  — so there is no path-injection surface even though `dest` is
  syntactically a free `Path`.
- `stage_only` is always the literal `True` at this call site; there is no
  branch anywhere that could set it to `False` for a preview-originated
  call.
- `writeback()`/`skillbom_propose()` (the two live call sites) never pass
  either parameter, so `dest=None`/`stage_only=False` (their defaults) is
  the ONLY combination ever reachable from those two functions — no
  caller-facing input on the LIVE side reaches these parameters either.

**No `identity`/`workspace_id`/`sensitivity_ceiling` parameter exists anywhere
on `invoke_preview`** — identity resolves via `PolicyContext.
for_configured_operator` → `resolve_operator_identity`; the sensitivity
ceiling resolves via `resolve_local_sensitivity_ceiling(resolved_paths)`.
Full parameter enumeration was checked against `invoke_preview`'s actual
signature (not just the fields I remembered wiring) — this is the complete
caller-facing input set; there is no sibling parameter that bypasses any of
the above guards (M1's own top lesson: 3 of 6 defects there were an
incomplete parameter inventory, not a wrong guard).

## What the security lens should attack first

1. **JC-1's staging-directory access boundary** — is `<run_dir>/staging/
   writeback_preview/*.json` / `*.md` readable by anything other than the
   same authorized caller that generated it? (No new check was added
   beyond "inside the run directory" — same as every other run-scoped
   artifact.)
2. **JC-6's empty `ccdash_event_id` placeholder** in the staged skillmeat
   candidate — confirm an empty string is an acceptable "unresolvable"
   sentinel for a preview artifact rather than a misleading one.
3. **The `dest`/`stage_only` pinning argument in D8** — independently
   verify the claim that `target` is unconditionally constrained to the
   closed `WRITEBACK_PREVIEW_SUPPORTED_TARGETS` set before it is ever used
   to build `dest`, i.e. that there is truly no code path where a caller-
   influenced string reaches the `dest` parameter of either render
   function.
4. **The `evidence_bundle` target-ref reuse of `run_id`** (mirrors
   `run.bundle`'s own `TargetRef("verification", run_id)` precedent) — re-
   verify no guard/RBAC logic anywhere keys on `target_kind ==
   "evidence_bundle"` specifically or inspects its `target_ref` value, the
   same way `run.bundle`'s own security round confirmed for `"verification"`.
5. **`notebook_correlation.resolve_notebook`'s "explicit" correlation mode**
   — even the PRE-EXISTING live code path (unchanged by this leg) performs
   an unconditional local registry write in that mode whenever `project` is
   truthy, regardless of `create`. This leg's preview path deliberately
   avoids that mode entirely by using `notebook_for_run` (pure read) instead
   of `resolve_notebook`, so `writeback.preview`'s notebooklm target is
   unaffected — but worth independently confirming the write really is
   unreachable from preview's call graph, not merely believed to be.

## Test counts and commands run (real tails, post-JC-2-extension)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_writeback_preview.py tests/integration/test_operator_mcp_writeback_preview.py -q
..............                                                           [100%]
14 passed in 2.19s

$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q
[119 dots]                                                                [100%]
119 passed in 10.46s

$ ./.venv/bin/python -m pytest tests -q -k "writeback" \
    --ignore=tests/test_search_router_mcp_launcher.py \
    --ignore=tests/test_verification_pediatric_cds.py \
    --ignore=tests/test_verification_seam001_gate_composition.py
156 passed, 4477 deselected, 66 warnings in 15.17s
```

(Counts are +1 across all three suites vs. the pre-extension round: 1 new
test — `test_invoke_preview_meatywiki_skillmeat_staged_never_touch_live_paths_or_registry`
— plus the fix to `test_invoke_preview_unsupported_target_is_governed_result`
[now asserting `ccdash`, since `meatywiki` moved from `unsupported_target`
to `staged`] and extended assertions inside the 4 existing integration
tests, which do not change the collected test count.)

(The three `--ignore`d files are PRE-EXISTING collection errors unrelated
to this leg: `tests/test_search_router_mcp_launcher.py` needs the `mcp`
serve extra not installed in this venv; the other two do sibling-module
`import test_claim_verifier`/`import
test_pediatric_cds_redteam_fixtures`-style imports that only resolve when
pytest is invoked from inside `tests/`, not from the repo root — neither
touches `writeback.py` or any file this leg owns.)

```
$ uv run flake8 src/research_foundry/services/writeback.py \
    src/research_foundry/services/operator_mcp_adapters/ \
    --select=E9,F63,F7,F82
(clean, exit 0)
```

**Pre-change regression proof, round 1 — the whole `writeback.preview` seam**
(boundary rule 6 — scratch copy, never `git stash`): copied the post-change
`writeback.py` to `/tmp/m2-leg-a-scratch/writeback.py.after`, restored the
pre-change content via `git show HEAD:src/research_foundry/services/
writeback.py` into the working file, re-ran the 13 new tests (as they stood
before the JC-2 extension) — **10 of 13 failed** (`AttributeError: module
'research_foundry.services.writeback' has no attribute 'preview_writeback'`
/ the same surfaced as a governed `internal_error` through the adapter's H8
boundary). The 3 that still passed pre-change are exactly the ones that
never reach the new seam at all: the pure canonical-digest/ctx-
normalization test, the H7 above-ceiling `dry_run=True` test (denies before
`_run()`), and the review-required guard-denial test (also denies before
`_run()`, by design — JC-3). Restored from the scratch copy afterward.

**Pre-change regression proof, round 2 — the JC-2 meatywiki/skillmeat
extension specifically**: copied the round-1 post-change `writeback.py` to
`/tmp/m2-leg-a-scratch/writeback.py.after2`, reverted the working file to
the round-1 (pre-JC-2-extension) scratch copy, re-ran the two
meatywiki/skillmeat-specific tests
(`test_invoke_preview_meatywiki_skillmeat_staged_never_touch_live_paths_or_registry`,
`test_preview_full_matrix_staged_zero_client_calls_with_content_assertions`)
— **both failed** (`AssertionError: assert 'unsupported_target' ==
'staged'`, exactly the pre-extension behavior for a target not yet in
`WRITEBACK_PREVIEW_SUPPORTED_TARGETS`). Restored from the round-2 scratch
copy afterward and re-ran the full validation matrix
above to confirm it was byte-identical and green again.
