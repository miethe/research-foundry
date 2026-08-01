---
type: findings
schema_version: 2
doc_type: findings
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: closed
created: '2026-07-31'
updated: '2026-07-31'
reviewer: task-completion-validator (Mode E)
tree: 76f5a29
---

# M1 remainder — milestone gate verdict (tree `76f5a29`)

## 1. VERDICT: **APPROVED**

All six pre-gate findings (F1-F6) are genuinely closed on the current tree, not merely test-pinned.
F7 is honestly documented rather than "fixed" with an invented field, which is the correct call for
a LOW-severity, non-exploitable, provably-inert duplicate. All seven M1 AC pass with direct evidence
(commands run below). Full unit suite reproduces exactly the documented 3-test pre-existing baseline
failure and no others. One new LOW-severity observation (redundant policy evaluation, not a security
defect) and one UNVERIFIED item (symlink TOCTOU) are recorded below — neither blocks M1.

## 2. AC-by-AC

| # | AC | Verdict | Evidence |
|---|----|---------|----------|
| 1 | No registered tool path reaches Typer/cli_commands/shell/subprocess; adapter IDs allowlisted; unknown denies | **PASS** | `grep -n "cli_commands\|typer\|Typer\|subprocess\|os\.system\|shell=True" src/research_foundry/services/operator_mcp_adapters/{external_import,source_ingest,research_stages,verify_bundle,__init__}.py` → 4 hits, all in docstring prose (`external_import.py:31`, `source_ingest.py:10,12`, `research_stages.py:11`), zero in executable code. Paths confirmed to exist before grepping (not a hollow-evidence scan). `cli_commands.py` has zero diff across this whole delta (`git diff --stat fcfcd89^ 76f5a29 -- src/research_foundry/cli_commands.py` → empty) — the adapters are pure wrappers, not a parallel reimplementation that could drift. `operator_mcp_adapters.all_adapters()` returns exactly 12 registered kinds (5 P3 + 7 new); `base.get_adapter()` returns `None` for anything else (unmodified P3 code, out of this delta's scope). **Own reading on the accepted item**: importing the adapters package transitively pulls in `subprocess` via `job_lifecycle → agent_job_service` (`agent_job_service.py:48`) — confirmed by grep. I agree with the plan's own framing: AC 1 governs the *dispatch path* a caller-supplied `operation_kind`/payload can reach, not the *import graph*. `agent_job_service.Popen` spawns a locally-configured agent job through its own typed interface; it is not reachable by unsanitized caller input threading through an adapter's `invoke()` parameters, and none of the four new adapters call into `agent_job_service` at all. Not a violation. |
| 2 | CLI parity holds; dry-run zero effects | **PASS** | CLI unmodified (above). Dry-run zero-effects proven per-adapter with spy tests that assert the wrapped canonical service is never called: `test_invoke_dry_run_never_calls_ingest_source` (`test_operator_mcp_adapter_source_ingest.py:240`), `test_invoke_dry_run_never_calls_import_external_report` (`test_operator_mcp_adapter_external_import.py:134`), `test_invoke_extract_dry_run_never_calls_extract_run`/`_claim_map_.../_synthesize_...` (`test_operator_mcp_adapter_research_stages.py:147,413,713`), `test_invoke_verify_dry_run_never_calls_verify_report`/`test_invoke_bundle_dry_run_never_calls_build_bundle` (`test_operator_mcp_adapter_verify_bundle.py:485,874`). All 7 pass (`./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q` → 109 passed, 0 failed). |
| 3 | Direct-service vs adapter parity for import + all 6 stages | **PASS** | One spy-based parity test per operation kind, each capturing the REAL canonical-service call and asserting field-for-field equivalence: `test_invoke_result_matches_direct_ingest_call` (source_ingest.py:106), `test_invoke_result_matches_direct_import_call` (external_import.py:79), `test_invoke_extract_result_matches_direct_extract_run_call`/`_claim_map_.../_synthesize_...` (research_stages.py:87,355,656), `test_invoke_verify_result_matches_direct_verify_report_call`/`test_invoke_bundle_result_matches_direct_build_bundle_call` (verify_bundle.py:140,811). All assert `len(captured_direct) == 1` (exactly-once call) before comparing fields — not merely "both returned ok=True". |
| 4 | Exact retry creates no duplicate artifact | **PASS** | One `exact_retry_does_not_*` test per operation kind present in all 4 files (`test_exact_retry_does_not_duplicate_source_card`, `test_exact_retry_does_not_duplicate_import_receipt`, `test_invoke_extract_exact_retry_does_not_reexecute` +claim_map+synthesize, `test_invoke_verify_exact_retry_does_not_recall_verify_report`, `test_invoke_bundle_exact_retry_does_not_recall_build_bundle`). This is inherited `run_or_replay` idempotency machinery from P3 (`operator_cancel_resume_service.py`, unmodified), exercised per-adapter rather than reinvented. |
| 5 | Verify failure is a governed result, not an exception; quarantine/missing-input deny with reason codes | **PASS** | `run.verify` non-passing verdict returns `ok=True, result["passed"]=False` (`test_invoke_verify_non_passing_is_ok_true_with_passed_false`, verify_bundle.py:205) — never mapped to a denial, matching D4. Missing-input cases (`_verify_prerequisites_met`/`_bundle_prerequisites_met`/`_extract_prerequisites_met`/`_claim_map_prerequisites_met`/`_synthesize_prerequisites_met`) all return `False` on any exception (never raise from the check function itself) and the CALL SITE converts that into an externally-observed `ok=False` + `reason_code` (`"preflight_failed"` for research_stages, `"internal_error"` via the exception→U1 channel for verify_bundle — see note below). "Quarantine": confirmed no run-level quarantine concept exists anywhere in this codebase (own grep confirms module docstring's claim: `grep -rn "quarantine" src/research_foundry/services/verification.py src/research_foundry/services/writeback.py` → no hits); the module's documented reasoning (quarantine is an ERI-only / crash-recovery-only concept) is correct and not a gap. **Judgment on `run.verify`/`run.bundle`'s raise-then-catch shape**: the AC's literal text is "deny with reason codes rather than raising" — internally these two prerequisite checks are implemented as a raise caught by `run_or_replay`'s U1 exception channel, converted to `ok=False, reason_code="internal_error"` before ever crossing the adapter's public return boundary. Externally this satisfies the AC (never an unhandled exception reaches the caller); the reason code is coarser (`internal_error` vs `preflight_failed`) than `research_stages.py`'s sibling implementation, which is a legitimate, documented D4 distinction (verify/bundle's prerequisite gate lives inside the action closure for F6 reasons — see finding re-attack below — so it cannot use the same pre-run_pipeline `_preflight_denial` helper `research_stages.py` uses). Acceptable at M1; the reason-code granularity asymmetry between the two files is a **LOW** polish item, not a defect. |
| 6 | `job.status`/`cancel`/`resume` bounded and identity-scoped, not regressed | **PASS** | Zero diff to `job_lifecycle.py`/`agent_job_service.py` in this delta (not in `files_affected` for `fcfcd89`/`76f5a29`, confirmed by `git show --stat` on both commits). `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_job_lifecycle.py -q` → 31 passed, 0 failed. |
| 7 | No hard-coded default workspace in the ingest path | **PASS** | `grep -n '"default"' src/research_foundry/services/operator_mcp_adapters/source_ingest.py` → no match. `assertion_registry_workspace_id=ctx.identity.workspace_id` (source_ingest.py:264) — structurally resolved, never the CLI's `cli_commands.py:354` literal. Regression-tested directly: `test_default_literal_absent_from_source_ingest_module` (source_ingest.py:510) plus `test_non_default_identity_workspace_threads_through_to_ingest_source` (source_ingest.py:443), which uses a non-`"default"` identity and asserts it threads through to the real `ingest_source` call via a spy. |

## 3. Finding re-attack (F1-F6)

- **F1 (BLOCKING, research_stages.py) — CLOSED.** Re-attacked the exact original scenario: a valid,
  owned run with zero extraction cards / zero claim ledger. Code path: `invoke_claim_map`/
  `invoke_synthesize` now call `policy.evaluate_policy(ctx, ...)` directly, and only on
  `allowed=True` call `_claim_map_prerequisites_met`/`_synthesize_prerequisites_met`
  (`research_stages.py:499-505`, `:626-632`), which does a real on-disk existence check
  (`rp.extractions.glob("*.yaml")` / `rp.claim_ledger.exists()`) and denies `preflight_failed`
  before the canonical service is ever called. Verified via spy tests that assert the canonical
  service function itself raises `AssertionError` if called (`test_invoke_claim_map_denies_preflight_failed_when_no_extraction_cards`,
  `test_invoke_synthesize_denies_preflight_failed_when_no_claim_ledger`) — not merely "returned
  ok=False" but "never reached the vulnerable call at all". `run.extract`'s one-hop-upstream sibling
  (checklist item 2, silent `ExtractResult(cards=[], count=0)`) is gated identically and tested
  (`test_invoke_extract_denies_preflight_failed_when_no_source_cards`). No remaining variant found:
  I checked all three `_*_prerequisites_met` functions for the same "absent, empty, or unreadable
  denies" contract — all three deny on `Exception`, absent directory, and zero matching files.
- **F2 (HIGH, external_import.py) — CLOSED.** Re-attacked: `workspace_id="ws-mine"` (own, passes H3)
  + `target_run_id` owned by `ws-other`. `external_import.py:230-236` now independently resolves
  `target_run_id`'s own owning workspace via `_resolve_run_workspace_id` and adds it as a SECOND
  `TargetRef`, so H3's existing per-target RBAC loop denies unless BOTH match. Verified with a REAL
  foreign run (not a mock) in `test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id`
  (external_import.py:306), which asserts `import_external_report` is never called. Checked the
  sibling `packet_dir`/`resume` parameters for the same class of gap: `packet_dir` only feeds
  `_target_ref_for`'s hash (not a live reference an RBAC check could authorize against — the packet's
  own workspace claim is what H3 already checks), and `resume` carries no target reference at all —
  neither is a plausible F2 variant.
- **F3 (BLOCKING, source_ingest.py) — CLOSED.** Re-attacked: caller declares `sensitivity="public"`
  on a run whose real `run.yaml` sensitivity is `"personal"`. `source_ingest.py:201`
  (`effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)`) reads
  structurally from the target run's own governed state; the caller's `sensitivity` parameter is
  still forwarded to `ingest_source` (correctly — it's the new card's own content label, a
  distinct/legitimate use) but never reaches the ceiling comparison. Verified with a real planned
  run and a caller-supplied mislabel in `test_invoke_denies_caller_mislabeled_public_sensitivity_on_sensitive_run`
  (source_ingest.py:335), which asserts `ingest_source` is never called. I checked the sibling
  fields threaded into `PolicyContext` for the same "check the producer, not the field" gap this
  finding warns about: `sensitivity_ceiling` (resolved structurally, H5-confirmed), `run_workspace_id`
  (resolved structurally from `run.yaml`, H3-confirmed) — no remaining caller-controlled
  authorization-relevant field found in this adapter.
- **F4 (BLOCKING, source_ingest.py) — CLOSED, correctly (inversion, not extension).** Re-read the
  parity test lineage: `test_invoke_result_matches_direct_ingest_call` (source_ingest.py:106) now
  mints its confirmation WITH matching content — a genuine parity case — and a NEW,
  purpose-built test (`test_invoke_denies_when_confirmed_content_differs_from_supplied_content`,
  source_ingest.py:172) isolates exactly the original bypass: mints a confirmation against the
  pre-fix payload shape (no `content_digest`/`created_by_agent`), then invokes WITH real content,
  and asserts `confirmation_mismatch` + the spy on `ingest_source` never fires. Checked every
  parameter that reaches `ingest_source` (`_run()`, source_ingest.py:252-267) against
  `input_payload` (source_ingest.py:211-222): `locator`, `run_id`, `source_type`, `sensitivity`,
  `title`, `fetch`, `extraction_status` are bound verbatim; `content` is bound via `content_digest`;
  `extra_limitations`/`created_by_agent` are bound verbatim. No unbound parameter reaches the
  effect — the original defect class ("content reaches the effect without being bound") has no
  remaining sibling in this file.
- **F5 (HIGH, verify_bundle.py) — CLOSED.** Re-attacked with two independent tests using REAL
  cross-workspace runs (not mocks): `test_invoke_verify_foreign_report_path_denies_and_does_not_touch_foreign_run`
  and the `claim_ledger_path` variant (verify_bundle.py:333,408) construct run A (authorized) and run
  B (a different workspace, with its own real report+ledger on disk), then invoke `run.verify` for A
  with an explicit `report_path`/`claim_ledger_path` pointing at B. Both assert `ok=False`,
  `reason_code="internal_error"`, AND — the load-bearing assertion — that B's `claim_ledger.yaml` is
  byte-identical before/after and B's `reviews/verification.yaml` was never created. `_explicit_path_
  within_run` (verify_bundle.py:261) is a purely structural containment check (never an existence
  oracle on the foreign side, correctly avoiding reintroducing an F6-shaped leak) with its own direct
  unit test for traversal (`../`) and absolute-foreign-path cases
  (`test_explicit_path_within_run_rejects_traversal_and_absolute_foreign_paths`, verify_bundle.py:461).
- **F6 (HIGH, verify_bundle.py) — CLOSED.** Re-attacked exactly the original scenario: an
  unauthorized caller (`ws-mine` identity) probing a foreign run (`ws-other`) that HAS the required
  artifacts vs. probing a nonexistent run. `test_invoke_verify_foreign_run_state_does_not_leak_before_
  authorization_f6` (verify_bundle.py:598) and its `invoke_bundle` mirror
  (`test_invoke_bundle_foreign_run_state_does_not_leak_before_authorization_f6`, verify_bundle.py:977)
  assert the two error envelopes are `==` (byte-identical), both `not_found`, under `dry_run=True` —
  proving the prerequisite check genuinely never runs before authorization for either code path. Code
  confirms the ordering: `_verify_prerequisites_met`/`_bundle_prerequisites_met` are called ONLY
  inside `_run()` (verify_bundle.py:497, 684), which `base.run_pipeline` invokes only after its own
  fixed authorize→consume→execute order has already run RBAC. `research_stages.py` independently
  reproduces the SAME non-leaking shape for its own three adapters via a different mechanism (a
  manual `policy.evaluate_policy()` call gating the prerequisite check, rather than deferring into
  the action closure) — cross-checked with `test_invoke_claim_map_denies_preflight_failed_for_
  unauthorized_caller_without_leaking_prerequisite_state` (research_stages.py:614), which uses a real
  foreign-workspace identity against a run with genuinely zero extraction cards and confirms
  `not_found`, not `preflight_failed`. I checked `run.extract`/`run.synthesize` for the same
  ordering by code inspection (both call `evaluate_policy` and check `decision.denied` before their
  own prerequisite function, `research_stages.py:385-391`, `:626-632`) — structurally identical to
  the tested `claim_map` case; not independently re-tested by name but not a gap, since all three
  share one code shape reviewed directly.

**F7** — re-confirmed as documented (not independently exploitable, no caller can select a foreign
extraction-card/ledger/verification object; both `research_stages.py`'s and `verify_bundle.py`'s
secondary targets resolve to the same `run_ctx.workspace_id` as the primary `run` target). Correctly
left as an honest doc note rather than an invented field — inventing a fake independent check here
would be worse than the current honest non-check.

## 4. New findings

**N1 — LOW — redundant `evaluate_policy()` call in `research_stages.py`'s three F1/F6 gates, not a
new security defect.** `invoke_extract`/`invoke_claim_map`/`invoke_synthesize` each call
`policy.evaluate_policy(ctx, paths=resolved_paths)` manually (research_stages.py:385, 499, 626) to
gate the new prerequisite check, then unconditionally call `base.run_pipeline(...)`, whose own
`authorize_operation` re-runs the identical 5-stage `evaluate_policy` internally (a documented,
accepted P3 pattern per `operator_mcp_policy.py`'s own NB-9 comment: "this probe runs AT LEAST TWICE
per mint→execute flow"). This adds a THIRD `evaluate_policy` call (and therefore a third
`audit_service.health_check` SQLite write-then-read probe) for these three operation kinds only,
compared to two for every sibling adapter. `health_check` is documented as cheap/idempotent/
never-raising, and NB-9 already accepts brief SQLite contention as self-resolving under the default
5s busy-timeout, so this is not a correctness or security issue — flagging as a minor efficiency/
consistency note for a future pass, not a blocker. `verify_bundle.py`'s F6 fix took the alternative
approach (defer the prerequisite check into the action closure, avoiding the extra call) — worth
reconciling the two shapes at M2/M3 for consistency, not required now.

**N2 — LOW/UNVERIFIED — symlink TOCTOU on `_explicit_path_within_run`, theoretical only.**
`verify_bundle.py:261`'s containment check resolves the candidate path once and compares against
`run_root_resolved`; if a symlink inside the authorized run's own tree were swapped between this
check and `verify_report`'s own subsequent read (an attacker would need local filesystem write
access to the run directory concurrently with the operation, which is already inside the trust
boundary for a "trusted single local operator" deployment per this project's stated posture — see
memory `di1-delta-reaudit-outcome` / `public-multiuser-release-plan`), the check could pass against
one target and the read could resolve a different one. I did not write an exploit or test for this —
it requires local-filesystem write races that are out of scope for the adversarial model this AC
targets (a caller providing a workspace/run_id/path string, not a caller with race-window write
access to the run directory itself). Labelled UNVERIFIED, not blocking.

## 5. Could not verify

- Exact total pass count for the full `tests/unit` suite (the custom pytest reporter in this repo
  does not print the standard `pytest -q` summary line — `pytest --collect-only -q` in this repo
  prints a per-file item count instead of a final total, and I could not get a definitive single
  number to cross-check against the plan's stated "2371 passed"). What IS verified directly: the
  `short test summary info` section of a full `tests/unit -q` run lists **exactly 3** `FAILED` lines
  (`test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off`,
  `test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default`,
  `test_report_anchors.py::test_schema_version_bumped_for_report_anchors`) — exactly the three named
  in the pre-existing baseline, and no others. Adapter suite: 109/109 passed (dot-count-verified,
  since the summary line is likewise suppressed by this repo's pytest config).
- I did not independently reproduce the 3 baseline failures against `main` in this session (the
  prompt states, and prior memory `operator-mcp-p1-gate-economics`/this repo's own git history
  corroborate, that these are a long-standing documented baseline — not re-verified against `main`
  here for time; low risk, since they are unrelated modules (`assertion_rollout`, `report_anchors`)
  never touched by this delta's `files_affected`).
