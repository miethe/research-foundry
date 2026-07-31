---
name: m3-pregate-ica
review: empirical, commit a107d84 (diff base a4e320e)
---

# ICA-M3 pre-gate empirical review — commit a107d84

**Verdict: no BLOCKING or HIGH findings. 1 MED, 0 LOW.** The commit's two production
fixes (server.py confirmation-kwarg routing; swarm_start.py F6 existence-leak fix) both
hold up under adversarial empirical testing beyond what the new test suites cover.
Severity counts: BLOCKING 0, HIGH 0, MED 1, LOW 0.

The one MED finding (ICA-M3-1) is **not** a security/existence leak — every foreign-vs-missing
comparison I ran, across every path, was byte-identical after stripping `occurred_at`. It is a
functional/reliability defect: the exact `TypeError → internal_error` misreporting pattern this
commit's own server.py fix explicitly calls out and partially fixes (for `job.status`'s
`confirmation_record`/`presented_token`) recurs, unfixed, for **8 of the 13** operation kinds'
own kind-specific required parameters, when a direct tool call omits one.

---

## ICA-M3-1 — MED — required-field omission still masks as `internal_error` for 8/13 tools (sibling of the fix this commit ships)

**File/behavior:** `src/research_foundry/operator_mcp/server.py:747-756` (`_operation_tool`'s
`invoke_kwargs` construction) + the `except Exception` D7 boundary at
`src/research_foundry/operator_mcp/server.py:563`. When a caller invokes an operation tool
directly (skipping `operation.preflight`) and omits a kind-specific required `input_payload`
key that the real `invoke*` function has no Python default for, `adapter.invoke(**invoke_kwargs)`
raises a raw `TypeError: invoke_X() missing 1 required keyword-only argument: 'Y'`. This is
caught by the same broad `except Exception` at line 563 and reported as a generic
`internal_error` (`retryable=True`) — **the exact same class of bug** this commit's own
docstring (lines 721-746) says was "discovered empirically via `server.call_tool("job.status",
...)`" for `confirmation_record`/`presented_token`, but the fix only closes that one
(kind, parameter) pair. The pattern is unfixed for every other adapter whose `invoke*` has its
own non-defaulted, kind-specific parameter.

**Confirmed indistinguishable from foreign-vs-missing (not a leak):** calling `writeback.preview`
without `targets` produces `internal_error` for BOTH a foreign-workspace run_id and a genuinely
missing run_id — identical envelopes. The bug fires before any rbac/ownership check ever runs
(the Python call itself never completes), so it cannot leak existence information. It is a
reliability/UX defect, not a security one: `retryable: true` on what is actually a permanent
caller-input error (repeating the call will fail identically forever), and it bypasses the
would-be `capability`-stage schema-shaped denial a caller would reasonably expect.

**Exact repro** (throwaway `/tmp` script, `./.venv/bin/python`, deleted after use):

```
$ ./.venv/bin/python /tmp/opm_m3_probe1.py
...
{
  "writeback.preview": {
    "foreign": {
      "schema_version": "1.0", "type": "operator_mcp_error",
      "reason_code": "internal_error",
      "message": "An internal error occurred while processing this operation.",
      "retryable": true, "operation_id": null, "receipt_ref": null
    },
    "missing": {  <-- byte-identical to "foreign" above (both hit the SAME TypeError) -->
      "schema_version": "1.0", "type": "operator_mcp_error",
      "reason_code": "internal_error",
      "message": "An internal error occurred while processing this operation.",
      "retryable": true, "operation_id": null, "receipt_ref": null
    }
  }
}
```
The call that produced this: `server.call_tool("writeback.preview", {"idempotency_key": "wb-foreign", "input_payload": {"run_id": run_a}})` — `targets` (required, no default in `writeback_preview.invoke_preview`) was omitted. Re-running with `targets: ["meatywiki"]` supplied produces the correct, clean `not_found` denial for both foreign and missing (confirmed — see the D5 section below).

**Scope — this affects 8 of 13 operation kinds**, enumerated via AST inspection of every
adapter's `invoke*` signature (kind-specific required kwarg beyond the universal
`run_id`/`idempotency_key`/`confirmation_record`/`presented_token`/`dry_run`):

| kind | extra required param(s) |
|---|---|
| `run.plan` | `intent_id` |
| `swarm.start` | `adapter_ids` |
| `job.status` | `operation_id` |
| `job.cancel` | `operation_id` |
| `job.resume` | `operation_id` |
| `external_report.import` | `packet_dir`, `workspace_id` |
| `source.ingest` | `locator` |
| `writeback.preview` | `targets` |

(`run.extract`/`run.claim_map`/`run.synthesize`/`run.verify`/`run.bundle` have no
*extra* required param beyond `run_id`, which every kind already treats as
universal — those five are lower-risk for this specific class, though a caller
omitting even `run_id` would hit the identical `TypeError`→`internal_error` path.)

**Fix direction:** generalize what this commit already did for `job.status` — either (a)
validate `input_payload` against each kind's own required-field set (the schema already
enumerates this per operation kind in `schemas/operator_mcp_operation.schema.yaml`; running that
validation before `adapter.invoke(**invoke_kwargs)` would convert this class of `TypeError` into
a proper `capability`/`schema_invalid`-shaped denial with `retryable=False`), or (b) narrow the
D7 `except Exception` boundary to catch `TypeError` from the `adapter.invoke(**invoke_kwargs)`
call specifically and map it to a non-retryable reason code. Option (a) is preferable — it also
protects future adapters that add their own required parameter.

---

## Task 1 — workspace-isolation matrix, 3 additional tools

Drove `server.call_tool` for the three OPERATION_KINDS not covered by
`tests/integration/test_operator_mcp_workspace_isolation.py`: `run.verify`, `source.ingest`,
`writeback.preview` (target `run.plan` was excluded — it has no required target kind at all,
`_REQUIRED_TARGET_KINDS["run.plan"] == frozenset()`, so it structurally cannot exercise a
foreign-vs-missing *target* comparison; `external_report.import` was excluded for time — see
Coverage boundaries).

Setup: identity A seeds a real run (`_build_run`, same helper `test_operator_mcp_writeback_preview.py`
uses); identity B calls each tool with `run_id=<A's real run>` (foreign) vs
`run_id="run_zzz_never_existed_00000000"` (missing), no confirmation presented on either call.

| tool | foreign envelope | missing envelope | indistinguishable |
|---|---|---|---|
| `run.verify` | `not_found` / `retryable:false` | `not_found` / `retryable:false` | **yes** |
| `source.ingest` | `not_found` / `retryable:false` | `not_found` / `retryable:false` | **yes** |
| `writeback.preview` (targets omitted) | `internal_error` / `retryable:true` | `internal_error` / `retryable:true` | yes (but see ICA-M3-1 — both sides are wrong for a different reason) |
| `writeback.preview` (targets supplied) | `not_found` / `retryable:false` | `not_found` / `retryable:false` | **yes** |

No existence leak on any of the four call shapes. `run.verify` and `source.ingest` both build
`ctx`/authorize BEFORE their own domain-specific prerequisite checks run (confirmed by reading
`verify_bundle.py`'s `invoke_verify` — the prerequisite check lives inside the `_run()` closure,
which `base.run_pipeline` only invokes after authorization; same for `source_ingest.py`), so
neither reproduces the F6 shape `swarm_start.py` had. This is independent confirmation that F6
was specific to `swarm_start.py` (as the M3 fix's own commentary claims), not a wider pattern
across the adapter family.

---

## Task 2 — zero-effect harness coverage (positive-control claim)

**Part A — does the harness see a REAL mutating operation's effects?** Copied
`_snapshot_stores`/`_snapshot_audit_health` verbatim from
`tests/unit/test_operator_mcp_policy.py` into a throwaway script, ran a full legitimate
`operation.preflight` + `run.extract` execute cycle (not a bare `evaluate_policy` call — this
module's own tests never go this far, by design; see below), and diffed before/after with the
identical harness code:

```
{
  "operation_id": "opm_0443803737c924df29429e8feb5166de644218a2a5da82043df515bcfeaa1f03",
  "file_diff": {
    "added": [
      ".rf_state/operator_operations.db",
      "runs/.../extractions/ext_20260613_b2beaa34_001.yaml"
    ],
    "removed": [],
    "changed": ["runs/.../telemetry/run_trace.jsonl"]
  },
  "audit_events_before_count": 1,
  "audit_events_after_count": 2,
  "audit_events_delta": 1,
  "audit_health_changed": true,
  "operator_operations_db_in_added_or_changed": true
}
```

The harness's file-hash walk **does** catch `.rf_state/operator_operations.db`'s creation
(only `paths.rbac_db` is excluded from that walk, and `operator_operations_db` is a distinct
physical file), and the `audit_events` list genuinely grows. This confirms the module
docstring's claim ("the manifest/receipt/job/attempt/confirmation-store durable rows... do not
exist AT THIS LAYER... exercised by the sibling `test_operator_operation_service.py` suite") is
mechanically sound: `evaluate_policy` alone never reaches the adapter/execute path, so
`operator_operations.db` legitimately never exists in any test in that file — but *if* it did
exist and change, this exact harness code would notice. `test_operator_operation_service.py`
does independently carry its own D2 zero-effect assertions (confirmed present at lines
~2648-2685, e.g. `test_h3_07_cancel_before_first_action_produces_canceled_receipt_with_zero_effects`)
— I did not deep-audit that file's own harness for equivalent rigor (see Coverage boundaries).

**Part B — 3 specific adversarial tests, stage/audit_health-instrumented:**

| test | stage reached | reason_code | audit_health changed | files/audit_events delta |
|---|---|---|---|---|
| `test_missing_identity_denied_with_identity_denied_code` | rbac | `identity_denied` | **no** | zero |
| `test_rbac_denies_insufficient_role_for_mutating_kind` | rbac | `rbac_denied` | **no** | zero |
| `test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape` (3 sub-cases) | wrong-workspace: rbac; genuinely-missing: rbac; **above-ceiling: guard** | all `not_found` | wrong-workspace: no; genuinely-missing: no; **above-ceiling: yes** | zero (files/audit_events) in all 3 |

This is the key result: the exclusion of `audit_health` from `_assert_zero_effect`'s comparison
is **stage-appropriate, not a blanket cover-up** — it only actually changes for the one
sub-case (`above_ceiling_ctx`) whose denial genuinely reaches the `guard` stage (which runs
after the unconditional `audit_health` probe in the pipeline order
capability→rbac→audit_health→guard→preflight→confirmation). The two `rbac`-stage denials in
the same batch correctly show `audit_health_changed: false`, proving the module's own exclusion
isn't silently absorbing an effect that should have been caught. (My first pass at this probe
had a self-inflicted setup bug — I called the un-monkeypatched `policy.resolve_operator_identity()`
with no `paths=` kwarg, which resolves against the real repo CWD via `FoundryPaths.discover()`
instead of my tmp workspace, and got a false "above_ceiling denies at rbac too" result. Fixing
the identity-patch ordering to match the real file's autouse `_default_operator_identity`
fixture reproduced the expected `guard`-stage denial. Flagging this here as a reminder that this
harness pattern is fragile to get right outside the real fixture — not a product finding.)

**Conclusion:** the D2 zero-effect harness is not vacuous and its one documented exclusion is
correctly scoped. No finding.

---

## Task 3 — receipt-schema sweep + completeness-gate exemptions

`./.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py -q` (under the mkdir
lock): **141 collected, exit 0, zero `FAILED` lines** (checked with ANSI stripped, per the
known "FAILED carries ANSI, `grep "^FAILED"` returns 0 on a red suite" trap).

Four properties are exempted from the D3 "every open string is bounded or closed" completeness
gate: `generated_at`, `started_at`, `completed_at`, `updated_at`
(`_FORMAT_DATE_TIME_EXEMPT_PROPERTIES`, `tests/unit/test_operator_mcp_schemas.py:1019-1021`).

- **Justified in a comment?** Yes — a clear docstring (lines 1008-1018) explains: this repo's
  `jsonschema.Draft202012Validator` usage never attaches a `FormatChecker`, so `format:
  date-time` is annotation-only and unenforced at runtime; wiring one is out of this schema
  file's scope; tracked as a deferred follow-up (`OPM-2.3/a`).
- **Bounded elsewhere?** Empirically, yes, in the current codebase. I traced every assignment
  site of these four field names in `operator_receipt_service.py` and
  `operator_cancel_resume_service.py`:
  - `started_at`/`completed_at` (action/effect/checkpoint/terminal receipts) are always sourced
    from a local `started_at = ids.now_iso()` variable (line 772 in
    `operator_cancel_resume_service.py`) or `_iso_utc(moment)` — never from caller-supplied
    MCP input.
  - `generated_at` (effect receipt) and `updated_at` (checkpoint) are likewise always
    `_iso_utc(moment)`-derived.
  - The receipt-building methods themselves also validate non-emptiness
    (`if not isinstance(started_at, str) or not started_at: raise ValueError(...)`), so even
    though the JSON-schema `format: date-time` constraint is unenforced, no caller-controlled,
    unbounded-length string can reach these fields today — the ONLY producers are two
    canonical-clock helper functions.

**No finding** — the gap is real (schema-level format enforcement is genuinely absent) but is
correctly documented, tracked, and currently has no live exposure since nothing but the
internal clock ever populates these fields. Worth re-checking if a future change ever threads a
caller-supplied timestamp into a receipt field without its own bound.

---

## Task 4 — swarm.start additional denial paths (existence-ordering check)

Seeded a real run for identity A, corrupted its `run.yaml` in two ways (`profile.max_cost_usd`
set to a non-numeric string; `intent_id` repointed to a dangling reference so
`governance_profile` resolves to `None`), then as identity B compared each corrupted-foreign-run
denial against a genuinely-missing-run denial, plus a no-confirmation-supplied variant:

```
=== bad_budget: foreign_vs_missing === indistinguishable=True
=== bad_governance: foreign_vs_missing === indistinguishable=True
=== no_confirmation: foreign_vs_missing === indistinguishable=True
```

All three: `not_found` / `retryable:false`, byte-identical after stripping `occurred_at`.

**Positive control** (proves the comparison isn't vacuous): identity A calling `swarm.start`
against its OWN corrupted-budget run gets a genuinely different envelope —
`preflight_failed` / `retryable:true` (the malformed-budget domain check, reached only because
this caller IS authorized) — confirming the F6 fix in this commit generalizes correctly beyond
"missing run.yaml" / "well-formed foreign run.yaml" to **malformed** run.yaml fields too: an
unauthorized caller is denied at `rbac` before ever learning whether the target run's
budget/governance fields are even well-formed.

**No finding** — the swarm_start.py F6 fix holds under every denial-path variant I tried.

---

## Coverage boundaries (what I did NOT try)

- **`external_report.import`** was not empirically probed (task 1 asked for 2-3 tools; I
  covered `run.verify`/`source.ingest`/`writeback.preview`). Its adapter has TWO extra required
  params (`packet_dir`, `workspace_id`) and its own `target_run_id` sibling-parameter history
  (F2 fix, referenced in its module docstring) — a plausible place for a similar existence-leak
  or required-field-omission recurrence; not checked here.
- **`run.plan`, `job.status`, `job.cancel`, `job.resume`, `run.claim_map`, `run.synthesize`,
  `run.bundle`** were not driven through the D5 foreign-vs-missing comparison myself (beyond
  what the existing `test_operator_mcp_workspace_isolation.py` suite already covers for
  `job.status`/`run.extract`/`job.cancel`/`swarm.start`).
- **ICA-M3-1's blast radius** — I confirmed the TypeError→internal_error pattern for exactly one
  tool (`writeback.preview`/`targets`) via live repro. The table of 8 affected kinds is derived
  from static AST inspection of each adapter's `invoke*` signature, not 8 independent live
  repros — I did not empirically fire the omission for `run.plan`/`swarm.start`/`job.status`/
  `job.cancel`/`job.resume`/`external_report.import`/`source.ingest` individually. I judge the
  static evidence sufficient to establish the class exists and is not writeback.preview-specific,
  but each individual kind's exact failure text/behavior is unverified.
- **`test_operator_operation_service.py`'s own D2 zero-effect mechanism** (task 2's claim that
  it "exercises" the manifest/receipt/job-store checks this policy-layer file's harness
  structurally cannot reach) — I confirmed such assertions exist in that file (grep hits at
  lines ~1871, ~2644-2685) but did not read or empirically re-verify that suite's own harness
  for the same rigor (non-vacuousness, stage-appropriateness) I applied to
  `test_operator_mcp_policy.py`'s harness. This is exactly the shape of gap the M2 retro flagged
  for my lane before (a clean bill on one seam missing a defect one layer over) — flagging it
  explicitly rather than implying full coverage.
- **Mutation-testing** the two production fixes themselves (reverting each and confirming the
  new/existing tests go red) was not performed — I relied on live black-box `server.call_tool`
  probes against the current tree instead. `tests/integration/test_operator_mcp_workspace_isolation.py`
  and `tests/unit/test_operator_mcp_adapter_swarm_start.py`/`tests/unit/test_operator_mcp_policy.py`
  were not run as full files under the lock (only `test_operator_mcp_schemas.py`, per the
  assignment's explicit instruction to run that one file; the others were exercised via my own
  copy-pasted-logic throwaway scripts instead, per the assignment's task 1/2/4 instructions).
- I did not review the non-code parts of this commit (docs, `.claude/worknotes/*`,
  `interrupted_operations.json` fixture, `README.md`/`CHANGELOG.md` diffs) at all.
