---
type: finding
doc_type: validator_gate
prd: research-foundry-operator-mcp
milestone: M2
tree: b4c335c (worktree-operator-mcp-v1, fix cycle 1 applied)
reviewer: task-completion-validator (Mode E, fresh context)
date: 2026-07-31
---

# M2 Validator Gate — "The stdio surface exists and provably cannot execute"

Tree: commit `b4c335c` on `worktree-operator-mcp-v1`. Interpreter: `./.venv/bin/python`. Read-only review.

## V1 — Run every M2 AC->command->evidence row

All three M2 rows executed for real, on this tree, plus the M1 `rg` row the work order specifically
flagged for the vacuous-path hazard.

| Row | Command | Real result |
|---|---|---|
| M1 — no CLI reach | Verified `src/research_foundry/operator_mcp/` and `.../operator_mcp_adapters/` **exist** first, then `rg -n "typer\|cli_commands\|subprocess\|os\.system\|shell=True"` over both | 11 matches, **all in docstrings/comments** stating the absence (e.g. "It never imports Typer..."); zero real code hits |
| M2 — exact tool inventory | `pytest tests/integration/test_operator_mcp_server.py -q -k "inventory or introspect"` | **1 passed** (`test_exact_14_tool_inventory` only — see VAL-1) |
| M2 — preview cannot execute | `pytest tests/integration/test_operator_mcp_writeback_preview.py -q` | **4 passed** |
| M2 — optional-SDK behavior | `python -c "sys.modules['mcp']=None; import research_foundry"` then `rf --help` | `base ok`, `rf --help` exit 0 |

**Verdict: PASS**, with VAL-1 (the literal `-k` filter under-selects; see findings).

## V2 — AC-to-evidence tracing

Each M2 AC bullet traced to real, independently-verified evidence (not merely asserted):

1. **Closed inventory, zero KMCP overlap, no wildcard** — `test_exact_14_tool_inventory` +
   `test_zero_overlap_with_knowledge_mcp_tool_names` (both pass; ran with broadened `-k`).
   Independently re-derived from source: `operator_mcp_policy.OPERATION_KINDS` = 13 entries +
   `operation.preflight` = 14; `knowledge_access.TOOL_NAMES` = 8 (`search`, `fetch`, `rf_*`) — zero
   string overlap by construction. `build_server()` fail-loud test present
   (`test_build_server_fails_loud_when_an_operation_kind_has_no_adapter`). **Genuine.**
2. **Zero network/client/mirror/accept_job/shell/subprocess reach** — static: `rg` scan above
   (zero real hits). Runtime: `_spy_all_integration_seams` in
   `test_operator_mcp_writeback_preview.py` monkeypatches `IntentTreeClient`, `ArcClient`,
   `get_notebooklm_client`, `get_meatywiki_client`, `urllib.request.urlopen` and asserts empty call
   lists across **4 outcome paths** (happy/degraded/missing-bundle/review-required-denial), not just
   the happy path. `accept_job`: zero matches anywhere in `operator_mcp/` or `operator_mcp_adapters/`.
   **Genuine.**
3. **Preview reason codes for missing/degraded/review-required, zero effect** — `test_invoke_preview_missing_bundle_is_governed_result_zero_files_staged`,
   review-required denial tests (`test_invoke_preview_review_required_denies_before_preview_writeback_runs`,
   `test_preview_review_required_denial_zero_client_calls`), degraded path test — all present, pass,
   and assert `_run()`/`preview_writeback` is never invoked on the denial path. **Genuine.**
4. **Base import + CLI work without SDK, one install hint, no network at startup** — directly
   re-run (V1 row 3), plus `test_build_server_raises_single_hint_runtime_error_without_sdk` asserts
   both install-hint strings appear **exactly once** each. **Genuine.**
5. **Bounded/redacted/safe envelopes, retryable + audit-delivery disposition** — `test_oversized_payload_maps_to_payload_too_large_envelope`,
   `test_internal_error_envelope_for_genuine_adapter_exception`, wrong-workspace `not_found`
   two-shape rule (inherited P1/P3, exercised across every `test_operator_mcp_adapter_*.py` file).
   `build_audit_delivery`/`retryable` confirmed as real, pre-existing substrate symbols (not
   invented for this claim). **Genuine.**
6. **Wheel/editable entrypoint, no auto-start/daemon/listener** — Leg C's
   `test_pyproject_declares_operator_mcp_script_and_mcp_extra_pin` (exact-list equality, not
   substring) + `test_import_performs_no_auto_start_side_effects` (thread-count, socket trap, AST
   scan, stdout scan for JSON-RPC framing) — both pass. **Genuine.**

**Verdict: PASS.** No AC is evidenced only by a test that would pass with the behavior absent.

## V3 — Test-quality audit (highest-value item)

The pre-gate's core finding (47 green tests, 3 blocking defects, because nothing drove
`server.call_tool` as a **sequence**) is the exact defect class this section hunts for.

- **The gap is closed for real, not just claimed.** `tests/integration/test_operator_mcp_preflight_execute_e2e.py`
  (520 lines, 8 tests) drives `asyncio.run(server.call_tool(name, arguments))` — the actual
  registered dispatch path — for `operation.preflight` then the corresponding execute call, for
  both a mutation kind (`run.plan`) and `writeback.preview`, including drift scenarios (payload,
  idempotency key, expiry, replay, target set, cross-workspace). Read the file directly: it is not
  a hand-built `PolicyContext` shortcut anywhere.
- **Pre-fix failure proof is real, not narrated.** `m2-fix-leg-1-completion.md` records 15 named
  pre-fix failures with real tracebacks; cross-checked via `git diff a759aa6 b4c335c` — the exact
  test functions named as new/changed in the diff match the note's claims 1:1 (e.g.
  `test_reserved_input_payload_key_maps_to_payload_too_large_envelope` is a genuine rename+inversion
  of `test_internal_error_envelope_for_unexpected_exception`, with real `internal_error` coverage
  restored by a **new**, separate test — not a silent weakening; hard boundary 5 honored).
- **Unit adapter tests still hand-build `PolicyContext` directly** — correct and expected at unit
  scope (each adapter's own domain logic), not a defect, now that the e2e file covers the
  integrated route.
- **No test found that pins unsafe behavior** (mint-one-way/invoke-another-and-assert-success). One
  near-miss is self-reported and already corrected in-session:
  `m2-fix-leg-1-completion.md` documents a **draft** replay test that wrongly assumed denial: it was
  corrected before it ever ran green, to assert the repo's actual documented idempotent-replay
  semantics (zero *additional* effect, not zero effect / not a denial). Verified the corrected
  version, `test_run_plan_execute_replayed_confirmation_is_a_zero_additional_effect_idempotent_success`,
  exists and its assertions match the stated semantics.
- **`test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run`** — confirmed order/
  pollution-sensitive per the coordinator's report (fails only under a polluted concurrent run,
  passes 31/31 isolated); consistent with this file's own 31-test file size. Real evidence of test
  suite order-sensitivity worth a follow-up, but not a defect in M2's own logic.

**Verdict: PASS.** The structural gap that caused 4/8 pre-gate defects is genuinely closed with a
real end-to-end test, not a relabeled proxy.

## V4 — Progress artifact honesty

`phase-5-progress.md`: OPM-5.1..5.5 `completed`, OPM-5.6 (this gate) correctly still `pending` — an
honest reflection of reality, not a premature self-close. Evidence fields name real, existing test
files (verified above). Minor observation, not a defect: completion timestamps cluster near-identical
across declared parallel batches (e.g. 5.1/5.2/5.4/5.5 all `14:40:00Z`, 5.3 at `14:30:00Z`) —
plausible given parallel dispatch, but imprecise; not a null/batch-flip pattern (timestamps are
present and per-task). Progress file was not re-touched after fix cycle 1 (expected: fix-cycle work
is tracked in `m2-fix-*` worknotes + the commit message, and OPM-5.6 — this gate — is exactly what
carries that forward).

**Verdict: PASS.**

## V5 — Whole-suite honesty

Ran `./.venv/bin/python -m pytest -p no:cacheprovider` **once, alone** (confirmed via `pgrep` that no
other pytest process held this worktree before starting), full 11m50s run to completion:

```
23 failed, 4691 passed, 5 skipped, 1 xfailed, 1382 warnings in 710.58s (0:11:50)
```

(Note: extracting `FAILED` lines from the raw log hit a **second** trap beyond the known ANSI-code
one — the log contains non-UTF8 bytes that make `sed`+`grep -c` silently return 0. Used
`LC_ALL=C perl -pe 's/\e\[[0-9;]*[A-Za-z]//g'` + `grep -a` instead; sanity-checked against a positive
control before trusting any zero.)

- **Zero of the 23 failures are on the operator_mcp surface** — grepped for `operator_mcp`/
  `operator-mcp` in the failure list: 0 matches.
- **Confirmed 2 of 23 in isolation directly** (not just trusted the list):
  `test_schema_version_bumped_for_report_anchors` (`1.8` != `1.4`) and
  `test_cli_json_dumps_site_counts_match_pinned_baseline` (`28` != `27`) both reproduce standalone —
  real, not order-dependent.
- **Independently cross-checked the M1-vs-M2 baseline diff the orchestrator reported**: read
  `/Users/miethe/.claude/jobs/fc494ecc/tmp/fail-set.txt` (M2 HEAD) and `baseline-fail-set.txt` (M1
  head `053a2c8`, scratch worktree confirmed at that exact commit) — `diff` is byte-identical, and
  my own independently-extracted 23-line failure-ID list matches both files exactly. **23/23
  failures pre-exist at the M1 baseline; zero new, zero fixed, zero regressions.**
- **No true pre-2d40f1f whole-tree baseline exists** — confirmed independently: the M1-head scratch
  worktree cannot even collect without the 2-line sibling-import fix this milestone shipped, proving
  every historical "full suite" figure in this workstream's notes was `tests/unit`-only.
- **The 416/416 operator-surface figure is independently re-verified**, not just trusted: ran the
  exact 17-file set myself → `416 passed` in one invocation (~20s).
- **The `test_job_resume_wrong_workspace_...` pollution failure is real but not part of this run's
  23** — it does not appear in my clean single-run failure list, consistent with it being an
  artifact of an earlier *concurrent* whole-suite run (the hazard the work order specifically warned
  about), not a defect in this tree.

**Verdict: PASS.** 23 pre-existing, zero new, zero on the operator surface, measured cleanly and
cross-verified two independent ways.

## V6 — Scope honesty

- **Deferred items are documented truthfully, findable, not overclaimed**: ccdash writeback-preview
  target (JC-2, filed as follow-up ITT node, `telemetry.py` genuinely out of file scope), MCP SDK
  2.0 migration (O-1, filed), stdio-guard unbound-base-call limitation (TERRA-5 — module docstring
  in `server.py` states the exact reachability boundary; a test pins it; explicitly left OPEN for
  the security gate "by design," not silently resolved), per-operation staging semantics (F2.3,
  replay/cleanup semantics stated plainly, no cleanup implemented and that's stated, not hidden).
- **No live/remote/deployment qualification is claimed anywhere** in the M2 code or worknotes I
  read — `server.py` mentions of "production" are code-behavior notes (clock-source discussion),
  not deployment claims. CHANGELOG.md has no operator-mcp M2 entry yet, which is **correct** — M3
  owns CHANGELOG/docs per the plan, not M2.
- **The "5 pre-existing failures" stale figure (flagged in advance by the task instructions)**:
  confirmed it originates in `m2-fix-contract.md:158` (a frozen, pre-fix-cycle contract — expected
  to stay as written, contracts are not living docs). It is **not** left uncorrected where a reader
  would trust it: `m2-fix-leg-1-completion.md` explicitly flags the mismatch (23 vs. 5) in-session,
  and the fix-cycle commit message (`b4c335c`) carries an explicit correction crediting it to a
  truncated-tail misread, further corrected by the orchestrator's own delivery notes (O-7/O-8). See
  VAL-2.

**Verdict: PASS.**

## Findings

**VAL-1 (Low)** — `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md:597`.
The M2 "exact tool inventory" matrix command (`pytest ... -k "inventory or introspect"`) selects
only `test_exact_14_tool_inventory`; it does **not** match `test_zero_overlap_with_knowledge_mcp_tool_names`,
which is the test that actually proves the "no Knowledge MCP overlap" half of that same row's
evidence claim. The underlying behavior is real and tested (confirmed by running with a broader
`-k`), so this is a matrix-precision defect, not a coverage gap — but a reader who runs the command
exactly as written and sees "1 passed" could believe both halves of the AC are covered by it.
**Fix direction**: widen the matrix's `-k` to `"inventory or introspect or overlap"`, or reference
both test names explicitly.

**VAL-2 (Informational)** — `.claude/worknotes/research-foundry-operator-mcp/m2-fix-contract.md:158`.
Stale "5 pre-existing failures" figure, superseded by this gate's own V5 measurement (23, byte-
identical to the M1 baseline). Already flagged and corrected downstream (see V6) — recorded here
only because the work order asked this gate to check for it explicitly. No action needed; contracts
are frozen historical records, not living docs.

**VAL-3 (Informational)** — `.claude/progress/research-foundry-operator-mcp/phase-5-progress.md`.
Completion timestamps for OPM-5.1/5.2/5.4/5.5 cluster at an identical `14:40:00Z` despite being
declared in different parallel batches; OPM-5.3 shows `14:30:00Z`. Plausible under real parallel
dispatch, but imprecise. Not a null-timestamp batch-flip; no action required.

## Verified clean

- 14-tool closed inventory, independently re-derived from `operator_mcp_policy.OPERATION_KINDS` +
  `PREFLIGHT_TOOL_NAME`; zero string overlap with Knowledge MCP's 8 tools, re-derived from source.
- Hard-boundary file protection: `git diff a759aa6 b4c335c` on `operator_mcp_policy.py`,
  `operator_operation_service.py`, `operator_cancel_resume_service.py`, `adapters/base.py`,
  `knowledge_mcp/` — zero changes across the entire fix cycle.
- Leg ownership was respected exactly (diff --stat matches Leg 1/Leg 2 file lists from the fix
  contract, no cross-contamination).
- flake8 `E9,F63,F7,F82` on `src/research_foundry` — clean, independently re-run.
- Operator-mcp 17-file surface: 416/416, independently re-run, ~20s.
- Whole-suite: 23 pre-existing failures, independently re-run once alone, cross-verified against an
  independent M1-baseline diff — byte-identical failure sets, zero new, zero on operator surface.
- TERRA-5 (unbound base-class transport bypass) correctly left open, explicitly, for the concurrent
  security gate — not silently resolved or falsely marked closed.

---

VALIDATOR GATE VERDICT: APPROVED
