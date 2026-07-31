# M1-remainder pre-gate review — `fcfcd89` (import + six research-stage adapters)

Reviewer: independent code-review pass (no fixes applied). Scope: the four new adapter
modules (`external_import.py`, `source_ingest.py`, `research_stages.py`, `verify_bundle.py`),
their registration in `__init__.py`, and their four test files. Compared against the
already-landed exemplars `run_plan.py` / `swarm_start.py` / `job_lifecycle.py`.

All empirical claims below were verified by running real code against a real `tmp_foundry`-shaped
workspace (scratch repro scripts, not committed to the tree) — not by code-reading alone. The
full new-adapter suite (97 tests, `test_operator_mcp_adapter_{external_import,source_ingest,
research_stages,verify_bundle}.py`) was re-run and is green, which is itself part of Finding 1's
evidence: the defect below is real and the suite does not catch it.

---

## Findings

### 1. [BLOCKING] `run.claim_map` / `run.synthesize` silently **succeed** on missing prerequisite input instead of denying — directly contradicts the M1 AC and this same commit's own `run.verify` implementation

- **File:** `src/research_foundry/services/operator_mcp_adapters/research_stages.py:289-382` (`invoke_claim_map`) and `:389-503` (`invoke_synthesize`)
- **What is wrong:** `operator_mcp_policy._REQUIRED_TARGET_KINDS` (`operator_mcp_policy.py:571-572`) declares `run.claim_map` requires `{"run","extraction_card"}` and `run.synthesize` requires `{"run","claim_ledger"}`. `_check_preflight` (`operator_mcp_policy.py:1453-1499`) only checks that a `TargetRef` of the required *kind* is present in `ctx.targets` — never that the referenced artifact exists on disk (this is explicit in that function's own comment, `operator_mcp_policy.py:558-561`, and in `research_stages.py`'s own module docstring, lines 42-67). `research_stages.py` unconditionally constructs the secondary `TargetRef` (`policy.TargetRef("extraction_card", run_id)` at line 329; `policy.TargetRef("claim_ledger", run_id)` at line 443) regardless of whether that artifact actually exists — so the preflight "required kind present" check is trivially, permanently satisfied by construction, no matter what state the run is in. There is **no adapter-level existence check** the way `verify_bundle.py` (same commit, leg C) implements one for `run.verify`/`run.bundle` via `_verify_prerequisites_met`/`_bundle_prerequisites_met` (`verify_bundle.py:236-317`).
  Worse: the wrapped canonical services do not raise for this case either, so there is no fallback safety net via `run_or_replay`'s exception→`"failed"` conversion:
  - `claim_mapping.build_claim_ledger` (`claim_mapping.py:213-244`) only raises `NotFoundError` if the **run itself** is missing (`claim_mapping.py:223-224`); if the run exists but has zero extraction cards, `sorted(run_paths.extractions.glob("*.yaml"))` is simply empty and the function returns a `ClaimMapResult` with `claims_total=0`.
  - `synthesis.synthesize_report` (`synthesis.py:231-340`) calls `_load_ledger` (`synthesis.py:44-49`), which returns `{"claims": [], "unresolved_questions": []}` when `claim_ledger.yaml` does not exist — no exception anywhere in the call chain.
- **Concrete failing scenario (empirically verified):**
  - A run that has been planned + ingested + extracted but never claim-mapped, invoked via `invoke_synthesize`: `result.ok == True`, producing a fully "completed" draft `report_draft.md` with `claims_cited: []` and body sections reading `<!-- No supported findings were established for this run. -->` — a valid-looking synthesized report from a run with **no claim ledger at all**.
  - A freshly planned run (zero extraction cards) invoked via `invoke_claim_map`: `result.ok == True`, `result.result == {"status": "completed", ..., "claims_total": 0, "by_status": {}}` — a governed operation records "completed" for an operation that had nothing to map.
  - Neither produces an `ok=False` denial, a `preflight_failed` reason code, or a raised exception anywhere in the chain.
- **How verified:** ran real code (not mocked) through `research_stages.invoke_synthesize`/`invoke_claim_map` against a `tmp_foundry`-style workspace, with a real minted confirmation via `policy.mint_confirmation`, exactly mirroring the test suite's own pattern. Output reproduced above verbatim (adapter result dict + report file contents). Confirmed the test suite has **no test** exercising either case — every "missing" test in `test_operator_mcp_adapter_research_stages.py` (`:233`, `:444`, `:652`) is a missing/foreign **run**, never a missing secondary target — a genuine "the test suite avoids the case" per the defect-class-3/4 hunt criteria.
- **Why this matters relative to the AC:** `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md:528-529` states the M1 AC explicitly: *"Verify failure is a typed governed result that blocks the dependent bundle action; quarantine and missing-input cases deny with reason codes rather than raising."* And the implementer contract (`m1-remainder-implementer-contract.md`, D4) requires exactly this shape for `run.verify`'s own missing-input case — which `verify_bundle.py` (same commit) correctly implements via a pre-`ctx` prerequisite gate. `research_stages.py` had the identical remediation pattern available, in the same commit, in a sibling file, and did not apply it to `run.claim_map`/`run.synthesize`'s own secondary targets.

**Verdict on H1: CONFIRMED, and worse than hypothesized.** The hypothesis framed this as "reaches `synthesize_report()` and raises" — it does not raise at all; it completes successfully. This is a stronger, more dangerous fail-open than a raise-that-gets-converted-to-a-governed-failure would have been, since a raise would at least have produced `ok=False`.

---

### 2. [HIGH] `run.verify`/`run.bundle`'s pre-`ctx` prerequisite gate leaks foreign-workspace run progress state to unauthorized callers

- **File:** `src/research_foundry/services/operator_mcp_adapters/verify_bundle.py:236-285` (`_verify_prerequisites_met`), `:288-317` (`_bundle_prerequisites_met`), invoked at `:388-392` and `:552-554`, respectively, **before** `PolicyContext`/`ctx` is ever constructed and therefore before `_check_identity_and_rbac` ever runs.
- **What is wrong:** Both prerequisite functions do a raw filesystem existence/content check keyed **only** by `run_id` — `rp.run.exists()`, `rp.report_draft.exists() or rp.report_final.exists()`, `rp.claim_ledger.exists()` for verify; `rp.verification.exists()` + `record.get("passed") is True` for bundle — with **no workspace ownership check at all**. This runs strictly *before* authorization: `base.py`'s own stated substrate invariant #2 is "Authorization precedes any lookup of the target" (`base.py:250-253`), and this adapter-level gate defeats that principle by construction, even though it never touches `base.run_pipeline` itself. The result: an identity from workspace A can submit **any** `run_id`, including one that belongs to workspace B it has no access to, and learn — via which of two closed, distinguishable reason codes comes back — whether that foreign run has reached the report+claim-ledger stage (for `run.verify`) or has a passing verification (for `run.bundle`). This is precisely the class of leak the project's own H3/H6/H7 doctrine ("no distinguishing detail... an attacker forcing a value onto `ctx.identity` must learn nothing about how close it was", `operator_mcp_policy.py:1319-1323`) is designed to prevent everywhere else in this family.
- **Concrete failing scenario (empirically verified):** Built two runs both owned by workspace `ws-other` (identity `bob`), with the acting caller authenticated as `alice`/`ws-mine`:
  - Run A (`ws-other`, has `report_draft.md` + `claim_ledger.yaml`): `invoke_verify(run_id=run_A, ...)` as `ws-mine` → `{'reason_code': 'not_found', 'retryable': False, ...}` (denied at the RBAC stage, past the prerequisite gate).
  - Run B (`ws-other`, freshly planned, no report/ledger yet): `invoke_verify(run_id=run_B, ...)` as `ws-mine` → `{'reason_code': 'preflight_failed', 'retryable': True, ...}` (denied at the adapter's own pre-`ctx` gate, never reaching RBAC).
  - The two envelopes differ in **both** `reason_code` and `retryable` — a caller with zero authorization for `ws-other` can distinguish "that run reached the verify-eligible stage" from "that run has not," across the workspace boundary, on every single call, with no rate limiting concern beyond guessing/knowing a `run_id`.
  - Repeated identically for `run.bundle` against a run with a passing `reviews/verification.yaml` vs. one with none: same distinguishable pair (`not_found` vs. `preflight_failed`).
- **How verified:** ran real `verify_bundle.invoke_verify`/`invoke_bundle` calls (no mocking of the prerequisite functions) against two workspaces built with real `planning.plan_run`/`extraction.extract_run`/`claim_mapping.build_claim_ledger`/`synthesis.synthesize_report`/`verification.verify_report` calls, patching only `policy.resolve_operator_identity` to the acting caller's identity (`ws-mine`) — the same technique the test suite itself uses. Full output captured; both probes produce structurally different, non-`None`-detail-bearing error envelopes.
- **Scope note:** the same architectural shape (a `_resolve_run_context`-derived preflight decision made *before* `ctx`/RBAC exist) is already present in the previously-landed `swarm_start.py` (`test_missing_run_denies_with_preflight_failed_no_confirmation_needed`, `test_operator_mcp_adapter_swarm_start.py:205-223`), so this is not a wholly new pattern invented by this commit — but this commit is the one that **extends** it, unmitigated, to two more operation kinds (`run.verify`, `run.bundle`), and its own module docstring (lines 100-114) explicitly reasons about the comparability of denial shapes without ever noticing that the excluded preflight stage is exactly where the leak lives. (The `swarm_start.py` cross-workspace case was not independently re-verified here — out of this diff's scope — but the identical code shape makes it likely reachable there too.)

**Verdict on H4: CONFIRMED weaker than the exemplar, and the gap is real, not merely theoretical.** The substituted comparison (above-ceiling vs. wrong-workspace) *does* correctly prove that guard-stage and RBAC-stage denials are byte-identical for a target that has already cleared the adapter's own prerequisite gate — that narrow claim holds. But by construction it never exercises the preflight-stage denial at all, and that is precisely the stage this finding shows leaks existence/progress information across the workspace boundary. The AC's "no distinguishing leak" property, read as applying to the *whole* denial surface (not just the guard/RBAC pair), does not hold for `run.verify`/`run.bundle`.

---

### 3. [LOW] `run.claim_map`/`run.synthesize`'s second declared target is a provably redundant no-op, not an independent check (H2)

- **File:** `research_stages.py:327-331` (`invoke_claim_map`), `:441-445` (`invoke_synthesize`)
- **What is wrong (design smell, not a vulnerability):** both `extraction_card` and `claim_ledger` targets are declared with `target_ref=run_id` (the *same* string as the `"run"` target) and `resolved_target_workspaces` supplies `run_ctx.workspace_id` for *both* positions — i.e., the second target's RBAC comparison (`_check_identity_and_rbac`'s loop over `ctx.resolved_target_workspaces`, `operator_mcp_policy.py:1331-1333`) is mathematically guaranteed to reach the identical pass/fail verdict as the first, on every call, for every input. It cannot ever diverge.
- **Verdict on H2: REFUTED as an exploitable path.** There is no route by which an `extraction_card`/`claim_ledger` belonging to a workspace *different* from the run's own workspace could ever be reached: `claim_mapping.build_claim_ledger`/`synthesis.synthesize_report` both resolve their inputs exclusively via `paths.run_paths(run_id)` (the same `run_id` already gated by the first target), and there is no parameter anywhere in either adapter's signature that could name a different extraction-card-owning or claim-ledger-owning entity. The module's own docstring (lines 58-67) states this reasoning correctly. The duplicate target is inert, not unsafe — flagged only so it is not mistaken for providing independent defense-in-depth it does not actually provide.

---

### 4. [REFUTED] `external_report.import`'s `workspace_id` is not exploitable self-attestation (H3)

- **File:** `external_import.py:170-184`
- `resolved_target_workspaces=(workspace_id,)` does thread the caller's own declared value straight through, exactly as the module docstring (lines 26-38) describes — but `_check_identity_and_rbac` (`operator_mcp_policy.py:1300-1344`) independently re-derives the *real* configured operator identity via a fresh `resolve_operator_identity(paths)` call and denies (`not_found`) unless `owning_workspace == identity.workspace_id` for every entry in `resolved_target_workspaces`, including this one. In this codebase's single-configured-operator model there is exactly one valid value the caller could supply that would ever be accepted — the operator's own workspace — so "self-attestation" here cannot escalate into writing to an arbitrary workspace. **REFUTED** — this is the intended, already-hardened H3 doctrine (identity is *never* trusted from `ctx`, always re-derived), correctly applied.

---

### 5. [REFUTED] `sensitivity_ceiling` reproduction across all seven new boundaries (H5)

Grepped every `invoke*` signature in `external_import.py`, `source_ingest.py`, `research_stages.py`, `verify_bundle.py`: none accepts a `sensitivity_ceiling` parameter; all seven call `resolve_local_sensitivity_ceiling(resolved_paths)` and thread the *returned* value into `PolicyContext.for_configured_operator`. **Confirmed clean at all seven boundaries** — the H7 pattern (fail-closed to `"public"`, no caller override) is reproduced correctly and consistently.

---

### 6. [REFUTED] `run.bundle` cannot report success on a non-passing verification (H6)

- **File:** `verify_bundle.py:552-617`; canonical service at `writeback.py:180-262`
- `_bundle_prerequisites_met` gates on a **stale, on-disk** `reviews/verification.yaml`, but the live path (`writeback.build_bundle(run_id, verify=True, ...)`) unconditionally re-runs `verify_report` itself (`writeback.py:206-212`) and derives its own fresh `verified` boolean from *that* call, independent of whatever the prerequisite check read from disk. The adapter (`verify_bundle.py:593-610`) inspects `result.verified` from this fresh call and `raise`s (turning the operation into a governed `"failed"` outcome) if it is `False` — so even a stale-but-passing on-disk `verification.yaml` cannot smuggle a since-invalidated run past the live check. **REFUTED** — the one acknowledged gap (a draft `evidence_bundle.yaml` is left on disk in the specific race where verification flips between the prerequisite read and the live call) is honestly documented in the module docstring (lines 72-83) as a known, out-of-scope limitation in `writeback.py`, not a hidden defect, and does not itself cause governance to report `approved_for_writeback=True` on a non-passing verification — the losing race still produces `ok=False`.

---

## Summary

| # | Severity | Hypothesis | Verdict |
|---|----------|------------|---------|
| 1 | BLOCKING | H1 | CONFIRMED — worse than hypothesized (silent success, not a raise) |
| 2 | HIGH | H4 (extended) | CONFIRMED — verified cross-workspace progress-state leak via preflight-vs-RBAC reason-code divergence |
| 3 | LOW | H2 | REFUTED as exploitable; flagged as a documentation/clarity note only |
| 4 | — | H3 | REFUTED |
| 5 | — | H5 | REFUTED — clean at all 7 boundaries |
| 6 | — | H6 | REFUTED |

No other instances of the four hunted defect classes were found in `external_import.py` or `source_ingest.py` beyond what is covered above; both correctly resolve identity/workspace/sensitivity structurally and deny fail-closed on every traced path (D2/D3 requirements verified by direct inspection: no `"default"` literal in `source_ingest.py`, exactly one dry-run concept exposed in `external_import.py`).
