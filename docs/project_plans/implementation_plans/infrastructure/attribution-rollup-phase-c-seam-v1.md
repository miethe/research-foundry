---
it_schema: 1
feature_slug: attribution-rollup-phase-c-seam
title: "Attribution Rollup Relocation, Partial-Coverage Fix & Phase C Seam (inert) — implementation plan"
doc_type: implementation_plan
status: completed
planning_maturity: shipped
merge_commit: 3c77e92720f9056d61d6b51732c6bd29434365a9   # squash of all 3 waves + the W2 gate remediation into main
merge_branch: main
tier: 3
priority: P2
points: 25
risk_level: high
context_class: C3
created: 2026-08-03
updated: 2026-08-03
changelog_required: false
prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
plan_ref: null
spike_ref: null
related_documents:
  - docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md
  - docs/project_plans/human-briefs/source-metadata-propagation.md
  - docs/dev/architecture/rf-run-export-schema.json
  - docs/dev/architecture/adr-rights-entity-model.md
commit_refs:
  - 3c77e92720f9056d61d6b51732c6bd29434365a9   # only main-reachable sha; the 7 branch commits went orphan on squash
pr_refs: []
files_affected:
  - src/research_foundry/services/attribution_triage.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/attribution_fetch/__init__.py
  - src/research_foundry/services/attribution_fetch/openalex.py
  - src/research_foundry/services/attribution_fetch/crossref.py
  - src/research_foundry/services/attribution_fetch/semantic_scholar.py
  - src/research_foundry/config.py
  - src/research_foundry/cli_commands.py
  - tests/test_attribution_triage.py
  - tests/test_catalog_attribution_columns.py
  - tests/test_attribution_fetch_seam.py
  - tests/test_attribution_fetch_cli.py
merge_commit: null
merge_branch: null
worktree: .claude/worktrees/autopilot-attribution-rollup-phase-c-seam
base_commit: 462df01
branch: autopilot/attribution-rollup-phase-c-seam
request_log_id: node_01KZ1T5MC56SE65071SC6FJ2W4   # same ITT node as the shipped parent plan; this is a logged follow-up, not a new node
deferred_items_spec_refs: []
findings_doc_ref: null
routing_constraints:
  - "Wave 2's merge-semantics correctness MUST stay claude-primary — it repairs a tri-state honesty guarantee the parent plan named as a hard go-precondition."
  - "Wave 3's non-egress / non-laundering guarantees MUST stay claude-primary — authorization/governance-adjacent, even though the surface is inert."
  - "Wave 1's mechanical relocation is offload-eligible."
  - "Second-opinion/code-review lens per wave gate: codex (agent_type codex-executor, model gpt-5.6-terra) primary; on no-verdict, fall back to gemini-3.6-flash[1m], then claude-sonnet-5. The Claude reviewer gate (task-completion-validator / karen) is the REAL gate regardless of what the cross-model lens reports — never report a no-verdict lens as having run (known trap in this repo: `codex-exec-review-fails-in-rf.md`)."
open_questions:   # both RESOLVED at M2 entry; evidence in commit 80cbdac's body
  - "RESOLVED (Wave 2 entry) OQ-A: NO export-contract change. RFClaim is additionalProperties:false with no claim-level `attribution_summary` property (rf-run-export-schema.json:482-521); the merge is catalog-internal, reaching only the sqlite `payload_json` TEXT column. RFResolvedSource.attribution_summary (:454) is a DIFFERENT per-card mirror produced by triage_records, untouched. rf-run-export-schema.json was therefore NOT versioned and no legacy fixture was needed — the planning-time default expectation held."
  - "RESOLVED (Wave 2 entry) OQ-B: NO catalog SCHEMA_VERSION bump, so `rf catalog rebuild` is NOT a required post-deploy step for this plan (unlike the parent plan's M4). `_attribution_count_of()` reads only the top-level `count`, which is numerically unchanged; the new cardinality fields ride inside the pre-existing free-form payload_json column, so there is no DDL change. Proven end-to-end, not just at the merge function: attribution_count stays 2 (partial) / 3 (full), matching pre-fix values. The operator had pre-approved a bump under full Mode D authority; it turned out not to be needed."
decisions:
  - decision: "Waves execute relocate -> fix -> seam, inverting the operator's listed order."
    rationale: "Relocating first keeps the pure-refactor claim independently verifiable with fixtures untouched; the conflation fix then owns its own blast radius instead of the two changes tangling in one diff."
  - decision: "The partial-coverage fix counts DISTINCT source_card_ids, via a changed input contract ((source_card_id, summary) pairs, deduped inside the function) rather than deduping at the call site behind a documented precondition."
    rationale: "Closes a blocking gate finding from an independent gpt-5.6 lens. The call-site fix would have passed every test, but the plan family's rubric rejects a control a future caller can defeat — 'if a control can be defeated by choosing a different field name, it is the wrong control' applies equally to a precondition a second caller can violate. Scope was widened during adjudication: the lens flagged only sources_total, but sources_assessed had the identical defect (recurring sibling-field class)."
  - decision: "Phase C ships as mechanism only; DEF-1 and DEF-6 stay OPEN."
    rationale: "Both preconditions are legal determinations, not code: DEF-1 is per-provider license terms verified for bundle redistribution, DEF-6 is live ToS re-verification for Semantic Scholar / NCBI (explicitly not legal advice). Neither has a code referent. The seam is inert — the package imports no networking library at all — so only the legal gate remains. No license posture is asserted anywhere. NOTE: the IntentTree nodes for both gates (node_01KZ1T9G2P6JH8Y0JAZQJ5HF9T, node_01KZ1T9GWJ6GN9GW2DV17TWSF3) read status:completed from an unrelated bulk deferral sweep and MUST NOT be cited as evidence either gate is cleared."
  - decision: "Validation runs hybrid — main checkout as cwd (real data plane), worktree as source via PYTHONPATH — with modified test files addressed by worktree-absolute path and unmodified data-dependent files MAIN-relative, in SEPARATE pytest invocations."
    rationale: "A worktree-only pytest run reports 19 phantom failures (FoundryPaths.discover() finds no run data), and 10 of them are the very pediatric/verification tests that assert the 7-bundle guarantee — which would have made Wave 2's central AC unfalsifiable. PYTHONPATH redirects the package import but NOT test-file resolution, so a MAIN-relative path to a worktree-modified test silently runs the stale copy. Mixing both conventions in one invocation dies on ImportPathMismatchError (exit 4)."
wave_plan:
  waves: [["phase-1"], ["phase-2"], ["phase-3"]]
  phases:
    - id: phase-1
      title: "Relocate _merge_attribution_summaries (pure refactor)"
      depends_on: []
      context_class: C2
      review_intensity: standard
      gate_lens: [validator]
    - id: phase-2
      title: "Fix claim-level partial-coverage conflation"
      depends_on: [phase-1]
      context_class: C3
      review_intensity: tier3
      gate_lens: [security, validator]
      gate_lens_reason: "irreversible-outward (conditional catalog SCHEMA_VERSION bump / exported-contract version bump) — the explicitly strictest gate of the three waves"
      karen: true
    - id: phase-3
      title: "Scaffold Phase C attribution-fetch seam, gate held shut"
      depends_on: [phase-2]
      context_class: C3
      review_intensity: tier3
      gate_lens: [security, validator]
      gate_lens_reason: "authz-boundary (must not weaken the M3 structural guard; must not launder untrusted third-party values into an RF-authored fact) + untrusted-input (provider payload shape, even though inert this wave)"
      karen: true
---

# Implementation Plan — Attribution Rollup Relocation, Partial-Coverage Fix & Phase C Seam

Three ORDERED follow-ups to the shipped `source-metadata-propagation-v1` plan (merge `794824d`), executed
in the existing worktree `.claude/worktrees/autopilot-attribution-rollup-phase-c-seam`
(`autopilot/attribution-rollup-phase-c-seam`, base `462df01`). The ordering is load-bearing: Wave 2 depends
on Wave 1's relocation having landed cleanly, and Wave 3's inert seam is meaningless to gate correctly
until Wave 2's tri-state honesty is real.

```json
autopilot-graph
{
  "tier": 3,
  "effort_points": 25,
  "wave_count": 3,
  "phase_count": 3,
  "file_count": 15,
  "mode_d": true,
  "mode_d_reasons": [
    "Wave 2 conditionally requires a catalog SCHEMA_VERSION bump (DB/catalog schema migration, mandatory `rf catalog rebuild` post-deploy) if the fix changes what's stored in the attribution_count-derived columns for claim rows — the parent plan's own M4 halted for the identical trigger.",
    "Wave 2 conditionally versions the exported run.json contract (rf-run-export-schema.json) if the fix changes any exported payload shape.",
    "Wave 3 sits directly adjacent to the M3 authorization-boundary structural guard (governance.py) — preservation-only, no edits to the guard permitted, but any diff touching governance.py or its adversarial tests should get explicit human sign-off before merge given Mode-D adjacency."
  ],
  "needs_spike": false,
  "spike_reasons": [],
  "single_pass_feasible": false,
  "plan_artifact_path": "docs/project_plans/implementation_plans/infrastructure/attribution-rollup-phase-c-seam-v1.md",
  "execution_target": "execute-plan",
  "slug": "attribution-rollup-phase-c-seam",
  "category": "infrastructure",
  "review_intensity": "tier3",
  "files_affected": [
    "src/research_foundry/services/catalog_service.py",
    "src/research_foundry/services/attribution_triage.py",
    "tests/test_catalog_attribution_columns.py",
    "tests/test_attribution_triage.py",
    "tests/test_catalog_attribution_regression.py",
    "docs/dev/architecture/rf-run-export-schema.json",
    "tests/fixtures/attribution/*.json",
    "src/research_foundry/services/attribution_fetch/__init__.py",
    "src/research_foundry/services/attribution_fetch/openalex.py",
    "src/research_foundry/services/attribution_fetch/crossref.py",
    "src/research_foundry/services/attribution_fetch/semantic_scholar.py",
    "src/research_foundry/config.py",
    "tests/test_attribution_fetch_seam.py",
    "src/research_foundry/cli_commands.py",
    "tests/test_attribution_fetch_cli.py"
  ],
  "escalation_recommendation": "effort_points (25) exceeds the single-pass ceiling (18) purely because two tasks are forced through the H7 large-file multiplier (catalog_service.py, 2653 lines, touched in Waves 1-2; cli_commands.py, 3480 lines, touched in Wave 3) — wave_count/phase_count/file_count (3/3/15) are all comfortably within ceiling and the 3-wave shape already matches the doctrine milestone structure. If the deterministic gate rejects on points alone, do not re-author a separate PRD+plan pair — confirm with the operator whether to proceed over the points ceiling given the cause is fully identified and file-size-driven, not scope-driven.",
  "execution_graph": {
    "waves": [
      {
        "id": "wave-1",
        "phases": [
          {
            "id": "phase-1",
            "title": "Relocate _merge_attribution_summaries (pure refactor)",
            "mode": "C",
            "review_intensity": "standard",
            "tasks": [
              {
                "id": "TASK-1.1",
                "assigned_to": "refactoring-expert",
                "effort": 4,
                "files_affected": [
                  "src/research_foundry/services/catalog_service.py",
                  "src/research_foundry/services/attribution_triage.py",
                  "tests/test_catalog_attribution_columns.py",
                  "tests/test_attribution_triage.py"
                ],
                "prompt": "Mode: C — Autonomous Feature Sprint (behavior-preserving refactor; halt and report if any behavior change would be required instead of a pure move).\n\nRelocate `_merge_attribution_summaries` (src/research_foundry/services/catalog_service.py:637-751, called at :1005-1007, referenced in a comment at :1033-1036) into src/research_foundry/services/attribution_triage.py, verbatim — do not change its logic, return shape, or docstring content beyond what the move itself requires (drop the now-self-referential docstring paragraph about being 'explicitly forbidden from editing attribution_triage.py', since that constraint no longer applies once it lives there; keep the rest). attribution_triage.py already owns cross-source rollup semantics per its module docstring's 'Cross-source rollups without a separate API' section and already defines `AttributionRollup` — this closes the duplicate-rollup-owner smell. Add the function to attribution_triage.py's `__all__`.\n\nIn catalog_service.py: delete the function body, remove the now-unused `from .attribution_triage import AttributionRollup` import (check whether `Iterable` is still used elsewhere in the file before removing that import too), update the call site at :1005 to call the relocated function with IDENTICAL arguments (match this file's existing import style for other attribution_triage symbols), and update the comment at :1033-1036 to point at the new home. Move the 6 tests at tests/test_catalog_attribution_columns.py:407-583 (`test_merge_attribution_summaries_returns_none_when_all_absent`, `test_merge_attribution_summaries_single_source_passthrough`, `test_merge_attribution_summaries_cross_source_ambiguous_key_refuses_to_pick_a_winner`, `test_merge_attribution_summaries_is_order_independent`, plus the `_ROLLUP_KEYS` constant) into tests/test_attribution_triage.py, updating `svc._merge_attribution_summaries(...)` references to match that file's own import convention. Update the docstring pointer at test_catalog_attribution_columns.py:379-386 ('see the _merge_attribution_summaries tests below') since they are no longer below.\n\nTHIS TASK MUST BE BEHAVIOR-PRESERVING with byte-identical outputs for identical inputs. Verify: run `find . -name __pycache__ -exec rm -rf {} +; PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -q` BEFORE any edit and capture the set of failing test node ids (this repo's pytest prints no 'N passed' summary line — use exit code + collected ids, not a naive count); repeat AFTER, clearing __pycache__ again first; diff the FAILURE SETS — they must be IDENTICAL. Then run `./.venv/bin/python -m pytest tests/test_attribution_triage.py tests/test_catalog_attribution_columns.py -q --cov=research_foundry`, `ruff check src/research_foundry/services/catalog_service.py src/research_foundry/services/attribution_triage.py`, and `mypy src/research_foundry/services/attribution_triage.py --ignore-missing-imports`. Use ./.venv/bin/python -m pytest, never the pyenv `python` shim (fails with 'No module named research_foundry'); in this worktree also set PYTHONPATH=<worktree>/src. Do NOT touch semantics — the partial-coverage conflation bug is Wave 2's job; if you notice it, name it in your completion report but do not fix it here. Do NOT git add/commit/push/stash."
              }
            ]
          }
        ]
      },
      {
        "id": "wave-2",
        "phases": [
          {
            "id": "phase-2",
            "title": "Fix claim-level partial-coverage conflation",
            "mode": "C",
            "review_intensity": "tier3",
            "tasks": [
              {
                "id": "TASK-2.1",
                "assigned_to": "python-backend-engineer",
                "effort": 10,
                "files_affected": [
                  "src/research_foundry/services/attribution_triage.py",
                  "src/research_foundry/services/catalog_service.py",
                  "tests/test_attribution_triage.py",
                  "tests/test_catalog_attribution_regression.py",
                  "docs/dev/architecture/rf-run-export-schema.json",
                  "tests/fixtures/attribution/*.json"
                ],
                "prompt": "Mode: C — Autonomous Feature Sprint, WITH a Mode-D halt condition (see below) — this is the strictest-gated wave of the plan.\n\nFix the claim-level partial-coverage conflation in `_merge_attribution_summaries` (post-Wave-1: src/research_foundry/services/attribution_triage.py; called from catalog_service.py's claim-row builder around :1005-1038). Bug: a claim citing BOTH an assessed source (attribution_summary is a dict) and an unassessed source (attribution_summary is None) currently reports as fully 'present', because the function silently filters None entries out of `valid` before merging — losing the unassessed half. This defeats the tri-state (present/absent/not-yet-assessed) honesty guarantee the parent plan named as a hard go-precondition ('No backfill; tri-state coverage ships WITH the first query surface'). Design a fix that makes partial coverage distinguishable from full coverage in the merged result WITHOUT adding any raw third-party value to the mirror (attribution_ids / counts / monotone rollups only). Preserve every existing tested invariant now living in tests/test_attribution_triage.py: None only when ALL inputs absent/non-dict; single-source passthrough keeps that source's own best/weakest pointers unchanged; a (asserter_id, assertion_kind) key contributed by 2+ DIFFERENT sources still refuses to pick a winner; order-independence; canonical sort on every id list. You will need to update tests that assert the exact returned dict via `==` to account for whatever new field you add — expected, not a regression, as long as the invariants above hold.\n\nRead-path discipline is absolute: no model call, no network call, no clock read, no persisted derived state.\n\nRESOLVE OQ-A/OQ-B (plan frontmatter) at entry, record resolution + evidence in your completion report: (1) does this fix require ANY change to the exported run.json contract? Grounding already established: RFClaim (rf-run-export-schema.json) is additionalProperties:false with no claim-level attribution_summary property today — the merge is catalog-internal. Default expectation: NO schema-version bump needed; verify against your actual fix and state the finding either way; only touch rf-run-export-schema.json + add a legacy fixture if export_run()'s emitted shape genuinely changes. (2) Does the fix change what's stored in the nullable `attribution_count` column for claim rows in a way requiring a catalog SCHEMA_VERSION bump? **If yes: STOP before merging — Mode-D catalog-schema-migration halt requiring explicit human approval, matching the parent plan's M4 precedent. Implement and validate up to that point, then report and wait.**\n\nCheck tests/test_catalog_attribution_regression.py's 4 frozen fixtures (tests/fixtures/attribution/*.json) individually — `_attribution_coverage_counts()` scopes to `item_type = 'source'` only, so the coverage tri-state fixture and the two resolved-source fixtures are grounded NOT to be affected by a claim-level-only fix; verify this against your actual change rather than assuming it, and regenerate ONLY fixtures that genuinely change (hand-freeze, never auto-regenerate a test's own expectation). State in your completion report EXACTLY which fixtures changed and why, or that none changed and why.\n\nProve all 7 committed pediatric_cds bundles still verify with a LIVE COUNTED sweep from the MAIN checkout, never from inside this worktree (FoundryPaths.discover() would silently build a fresh empty ledger there): `set -euo pipefail; n=0; for r in runs/*pediatric_cds*/; do ./.venv/bin/rf verify \"$(basename \"$r\")\" --workspace-root <main-checkout-absolute-path>; n=$((n+1)); done; test \"$n\" -eq 7`.\n\nValidate: `./.venv/bin/python -m pytest tests/test_attribution_triage.py tests/test_catalog_attribution_regression.py tests/test_catalog_attribution_columns.py tests/test_catalog_attribution_coverage.py tests/test_schema_validation.py -q --cov=research_foundry`, `ruff check`, `mypy --ignore-missing-imports` on touched files. PYTHONPATH=<worktree>/src; clear __pycache__ + PYTHONDONTWRITEBYTECODE=1 between mutation-verify iterations, and mutation-verify any guard your fix claims to close INSIDE this task, not in a later review round. Do NOT git add/commit/push/stash."
              }
            ]
          }
        ]
      },
      {
        "id": "wave-3",
        "phases": [
          {
            "id": "phase-3",
            "title": "Scaffold Phase C attribution-fetch seam, gate held shut",
            "mode": "C",
            "review_intensity": "tier3",
            "tasks": [
              {
                "id": "TASK-3.1",
                "assigned_to": "python-backend-engineer",
                "effort": 5,
                "files_affected": [
                  "src/research_foundry/services/attribution_fetch/__init__.py",
                  "src/research_foundry/services/attribution_fetch/openalex.py",
                  "src/research_foundry/services/attribution_fetch/crossref.py",
                  "src/research_foundry/services/attribution_fetch/semantic_scholar.py",
                  "src/research_foundry/config.py",
                  "tests/test_attribution_fetch_seam.py"
                ],
                "prompt": "Mode: C — Autonomous Feature Sprint. Escalate to Mode D (stop, do not implement, report + await approval) if you find yourself needing to enable a live network call by default, weaken governance.py's guard, or populate license_basis with any cleared/verified value — none of that is in scope.\n\nScaffold a NEW services/attribution_fetch/ package (__init__.py + one module per provider: openalex.py, crossref.py, semantic_scholar.py) implementing the deferred DEF-1 mechanism (PRD DEF-1..DEF-6, docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md) as fully INERT scaffolding. Add a new config flag `attribution_fetch_enabled: bool = False` to FoundryConfig (src/research_foundry/config.py, near the existing `ledger_write_enabled`/`automated_reuse_enabled` hard-off flags at :113-115 — same convention), defaulting off, with NO provider individually enabled by default even if the umbrella flag were set. HARD CONSTRAINT: no code path may issue an HTTP request under ANY input combination in this task — a provider adapter MAY structurally exist (typed request-builder/response-parser shapes) but its actual network call must be unreachable (raise NotImplementedError, or a structured disabled result, before any socket call) regardless of flag state. Never instantiate/call an HTTP client even if you import a type for typing.\n\nDesign the seam so an untrusted third-party value returned by a (currently unreachable) provider adapter can NEVER be laundered into an RF-authored fact: the adapter's return type must be shaped so a caller cannot write it directly into `source_attribution.value` or `trust.*` without going through the SAME schema-shape gate M3 already enforces (schemas/source_attribution.schema.yaml's `if asserter_type startsWith third_party_ then retrieval_evidence_ref required`). Do NOT extend governance.py's `_RIGHTS_GOVERNED_FIELDS` name tuple as your control — it is documented there (governance.py:32-51) as known-insufficient by construction; your control is the adapter's own return shape plus the existing schema. Record IN CODE, as a module-level docstring at the seam's entrypoint, the two open gates keeping this off: DEF-1 (per-provider license terms verified for bundle redistribution — not yet true) and DEF-6 (live ToS re-verification for Semantic Scholar/NCBI, explicitly not legal advice — not yet done). Do NOT mark DEF-1 or DEF-6 closed in any doc/tracker/register, and do NOT cite IntentTree nodes node_01KZ1T9G2P6JH8Y0JAZQJ5HF9T / node_01KZ1T9GWJ6GN9GW2DV17TWSF3 as evidence either gate is cleared even though their `status` field currently reads completed from an unrelated bulk sweep — treat both as OPEN.\n\nAdd tests/test_attribution_fetch_seam.py proving: the flag defaults False; every provider adapter's call path either raises or returns a structured disabled/no-op result with zero sockets opened (mock/patch the HTTP layer and assert it is never called, across flag on/off); no adapter return type has a bare string/value property governance's schema-shape check would need to catch.\n\nValidate: `./.venv/bin/python -m pytest tests/test_attribution_fetch_seam.py -q --cov=research_foundry`, `ruff check`, `mypy --ignore-missing-imports` on new files. PYTHONPATH=<worktree>/src. Do NOT git add/commit/push/stash."
              },
              {
                "id": "TASK-3.2",
                "assigned_to": "python-backend-engineer",
                "effort": 6,
                "depends_on": ["TASK-3.1"],
                "files_affected": [
                  "src/research_foundry/cli_commands.py",
                  "tests/test_attribution_fetch_cli.py"
                ],
                "prompt": "Mode: C — Autonomous Feature Sprint (depends on TASK-3.1 landing first in this phase — this task imports its flag/adapter interfaces).\n\nAdd an `rf attribution` CLI surface for the Phase C mechanism. IMPORTANT: `attribution_app` ALREADY EXISTS in src/research_foundry/cli_commands.py (:3135-3217, currently exposing `rf attribution validate`) — EXTEND that same Typer sub-app with a new subcommand (e.g. `rf attribution fetch` or `rf attribution status`); do NOT create a second `typer.Typer()` registered under the name 'attribution' — that collides with the existing registration. The new subcommand must, by default (flag off), print/return a clear 'disabled — see DEF-1/DEF-6' message and exit with a documented non-error code, and must NEVER attempt a network call regardless of arguments. Wire it to read `attribution_fetch_enabled` from FoundryConfig (TASK-3.1) and the provider adapters from services/attribution_fetch/. Follow the existing `rf search`/`rf fetch` CLI shape (src/research_foundry/services/search_router/cli.py) for command conventions, and the existing `attribution validate` command's `--json/--no-json` + Rich Table pattern in the same file for output consistency.\n\nAdd tests/test_attribution_fetch_cli.py (follow the `typer.testing.CliRunner` pattern already used in tests/test_attribution_divergence.py:20,35,455 for the sibling `attribution validate` command) proving: the command exists and is discoverable (`rf attribution --help` lists it); invoking it with the flag off produces the disabled message and attempts no network call (mock the adapter layer, assert zero calls); no combination of CLI arguments bypasses the disabled state.\n\nValidate: `./.venv/bin/python -m pytest tests/test_attribution_fetch_cli.py tests/test_attribution_divergence.py -q --cov=research_foundry`, `ruff check src/research_foundry/cli_commands.py`, `mypy --ignore-missing-imports src/research_foundry/cli_commands.py`. PYTHONPATH=<worktree>/src. Do NOT git add/commit/push/stash."
              }
            ]
          }
        ]
      }
    ]
  }
}
```

## Scope boundary

**In:** relocate the rollup helper (behavior-preserving); repair its partial-coverage conflation (semantics
change, versioned if it changes the export/catalog contract); scaffold the Phase C fetch/CLI mechanism
fully inert, hard-off, zero egress.

**Out (stated, not silently dropped):** live third-party network egress (any provider); enabling the
`attribution_fetch_enabled` flag anywhere; closing DEF-1/DEF-6; extending `_RIGHTS_GOVERNED_FIELDS` as a
control. All deferred behind the same licensing/ToS preconditions the parent PRD already named.

## Rubric — what "good" looks like

Wave 1 changes nothing observable. Wave 2 makes an honest tri-state claim-level signal exist without ever
minting a raw third-party value, and proves the 7 pediatric_cds bundles are non-regressive with a live
counted sweep — not an assertion. Wave 3 ships a mechanism that cannot, by construction, make a network
call or launder an untrusted value into an RF-authored fact, no matter what flag combination is passed;
"inert" is a property of the code shape, not of documentation saying so.

## Named risks

- **A partial fix reintroduces the exact bug it's meant to close.** If the Wave 2 fix only changes the
  return shape but the catalog call site still collapses partial→present when populating `attribution_count`
  (a single int column), the conflation survives one layer up. Verify the fix end-to-end through the
  catalog row, not just at the merge function's unit-test boundary.
- **Two consecutive review rounds finding the same defect class ⇒ change the design, not the review**
  (this repo's own operating rule). If Wave 2's reviewer gate finds the same partial-coverage miss twice,
  stop iterating the fix and re-derive the whole tri-state propagation path.
- **Cross-model review lenses have failed silently in this repo before** (codex and gemini both returned
  no verdict in a prior feature) — never report a no-verdict lens as having run; the Claude gate is the
  real gate regardless.
- **H7 file-size risk is real, not just an estimation multiplier**: catalog_service.py (2653 lines) and
  cli_commands.py (3480 lines) are both shared hot files touched by other in-flight work; re-check for
  concurrent edits before each wave, not just before Wave 1.

## AC → command → evidence

| AC | Command | Evidence of pass |
|---|---|---|
| Wave 1 behavior-preserving | diff of failing test-id sets, before vs. after, cleared `__pycache__` both times | sets IDENTICAL |
| Wave 1 relocation complete | `./.venv/bin/python -m pytest tests/test_attribution_triage.py tests/test_catalog_attribution_columns.py -q` | exit 0; `_merge_attribution_summaries` no longer defined in catalog_service.py (`grep -n "def _merge_attribution_summaries" src/research_foundry/services/catalog_service.py` returns nothing) |
| Wave 2 partial coverage distinguishable | new/updated tests in tests/test_attribution_triage.py | a claim citing one assessed + one unassessed source asserts a DIFFERENT merged value than a claim citing two assessed sources |
| Wave 2 invariants preserved | `./.venv/bin/python -m pytest tests/test_attribution_triage.py -q -k "ambiguous or order_independent or single_source"` | exit 0 |
| Wave 2 non-regression | live 7-of-7 counted `rf verify` sweep from the main checkout | `test "$n" -eq 7` passes; 7 individual verify calls exit 0 |
| Wave 2 fixture integrity | completion report names each changed fixture + rationale, or states none changed | reviewer can independently re-derive the claim from `_attribution_coverage_counts()`'s `item_type='source'` scoping |
| Wave 3 zero egress | `./.venv/bin/python -m pytest tests/test_attribution_fetch_seam.py tests/test_attribution_fetch_cli.py -q` with the HTTP layer mocked and asserted never-called | exit 0; mock assert_not_called across flag on/off |
| Wave 3 no CLI collision | `rf attribution --help` | lists both `validate` and the new subcommand under ONE `attribution_app` |
| Wave 3 deferral integrity | `grep -rn "DEF-1\|DEF-6" <new files>` | no occurrence marks either gate closed; module docstring names both as open |

## Sequencing

`Wave 1 → Wave 2 → Wave 3` is semantic, not house style: Wave 2 edits the function Wave 1 relocates (editing
it in two places at once is a merge-conflict risk, not a real dependency, but sequencing avoids it cheaply);
Wave 3's inert seam is not worth gating carefully until Wave 2's tri-state signal is actually honest — a
reviewer checking Wave 3's "never launders a value" property needs Wave 2's real merge semantics as ground
truth for what "value-free" means at the claim level.

## Review routing

Per-wave gate: `task-completion-validator` (base). Wave 2 and Wave 3 additionally carry `karen` (C3
context class) and a `security` lens (see `gate_lens_reason` per phase in frontmatter). Second-opinion /
code-review lens for every gate: **codex** (`codex-executor`, `gpt-5.6-terra`) first; on no verdict, fall
back to **gemini-3.6-flash[1m]**, then **claude-sonnet-5**. The Claude reviewer gate is the actual pass/fail
authority regardless of what the cross-model lens returns — do not report a silent/no-verdict lens as
having executed.

## Deferral integrity (Wave 3)

DEF-1 and DEF-6 stay OPEN through this plan's entire execution and after it lands. IntentTree nodes
`node_01KZ1T9G2P6JH8Y0JAZQJ5HF9T` and `node_01KZ1T9GWJ6GN9GW2DV17TWSF3` read `status: completed` from an
unrelated bulk deferral sweep — this plan does not treat that field as evidence either gate is cleared, and
no task in this plan may write a closing status to either node or backlog row.

## Execute handoff

> Execute: `/dev:execute-plan docs/project_plans/implementation_plans/infrastructure/attribution-rollup-phase-c-seam-v1.md`

Note before dispatch: `mode_d=true` (conditional catalog-schema-migration halt in Wave 2; authz-boundary
adjacency in Wave 3) and `single_pass_feasible=false` (points ceiling only, file-size-driven — see
`escalation_recommendation` in the autopilot-graph block). Confirm with the operator whether to proceed
over the points ceiling before dispatching Wave 1.
