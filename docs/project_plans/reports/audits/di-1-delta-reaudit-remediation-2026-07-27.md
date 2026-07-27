---
title: "DI-1 Delta Re-Audit — Remediation Summary (findings F1–F7, G1, G2)"
doc_type: audit
schema_version: 2
report_category: security-audit
feature_slug: public-multiuser-release-activation
phase: delta-reaudit-remediation
created: 2026-07-27
updated: 2026-07-27
status: remediated_in_code_pending_reaudit
requirement_ids: [DF-004, ACT-406]
gates: [DI-1, "Mode D (blocked-external, human-only)"]
remediates: docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md
audited_head_before: 77fe327
remediation_head: "single squash commit on main (this file's introducing commit; find via git log)"
branch: feat/di1-delta-reaudit-remediation (squashed into main; per-phase SHAs below are pre-squash / reflog-only)
method:
  - "8 claude-primary implementation phases (Mode D held claude-primary per delegation-router)"
  - "3 claude read-only verification passes (finding confirmation before fixing)"
  - "5 Codex gpt-5.6-sol cross-model adversarial review rounds (read-only, second-opinion class)"
  - "Independent Opus adversarial runtime probes for F1 bind-gate and F2 transport lockout"
  - "NO live two-workspace adversarial runtime test performed — see Residuals"
signoff:
  decision: PENDING
  note: >
    This is a remediation-summary artifact. It does NOT clear DI-1, enable any deployment, or
    self-sign the Mode-D decision. It records what was fixed so a fresh delta re-audit can be run
    against the post-remediation HEAD. The DI-1 / adversarial-multi-tenant decision remains a
    human-only Mode-D decision (audit §"Mode-D Decision Block — HUMAN ONLY").
---

# DI-1 Delta Re-Audit — Remediation Summary

Remediates every code/governance defect in `di-1-delta-reaudit-2026-07-26.md`. Operator gave Mode-D
approval to remediate **before** enabling the deployment; enabling remains a separate human decision
after a re-audit. **DI-1 is untouched and still BLOCKED.**

## Method note — why this took cross-model review

Each finding was (1) confirmed against code by a read-only pass before any fix, (2) fixed by a
claude-primary implementer (Mode-D work is MUST-stay-primary per `delegation-router` — no external
offload), (3) adversarially re-reviewed by Codex `gpt-5.6-sol`. The cross-model gate caught **five**
real defects the single-model (Claude) passes missed or mis-cleared — see the F2 and "neighbors" rows.

## Finding → fix → verdict

> The `Commit` column lists the pre-squash feat-branch phase commits for traceability; all were
> squashed into a **single** commit on `main`, whose full diff (`77fe327..`) is the complete
> remediation for re-audit purposes. The granular SHAs live only in the branch reflog.

| # | Sev | Fix (file) | Commit | Verdict |
|---|-----|-----------|--------|---------|
| F1(1) | HIGH | CLI `--bind-host` now written to `config.viewer["bind_host"]` so isolation guards no longer read a stale loopback value (`cli_commands.py`) | d9eeefd | CLOSED (runtime probe + `test_serve_cli`) |
| F1(2) | HIGH | non-loopback + no-auth gate moved into `create_app` itself, not only the CLI (`api/_bind_gate.py`, `app.py`) | d9eeefd | CLOSED (`test_bind_gate`, runtime probe) |
| F2-identity | HIGH | MCP tools bind a server-authoritative launch principal; client-supplied `workspace_id` mismatch rejected; server-side sensitivity ceiling (`mcp_launcher.py`) | d9eeefd | CLOSED |
| F2-transport | HIGH | `build_server()` returns a **FastMCP subclass** whose network-transport methods raise + run() is stdio-only. Superseded 3 leaky proxy attempts (`.run()`-only → `sse_app` → `_wrapped` → bound-method `__self__`) | 7417805, 24538ee, **82afccf** | CLOSED (independent probe: every non-base-explicit vector raises) |
| F3 | HIGH | builder "from run" threads identity into `export_run` + None-guard → 404 (`builder_service.py`) | d9eeefd | CLOSED |
| F4 | MED | `verify_draft` takes identity → fail-closed `load_draft`; `verify`/`publish-preview` thread it (`verification.py`, `reports.py`) | d9eeefd | CLOSED |
| F5-override | MED | rate-limit overrides keyed by `workspace_id` (`admin.py`, `rate_limit.py`) | 2f8d79a | CLOSED |
| F5-counter | MED | sliding-window **counter** key now `(workspace_id, user_id, route)` (`rate_limit.py`) — Codex neighbor | 7cddacf | CLOSED (dedicated isolation test) |
| F6 | LOW | `peek_catalog_generation_id` gains identity + `require_workspace_scope` (`catalog_retrieval.py`) | 2f8d79a | CLOSED |
| F7a-global | LOW | `build_global_source_index` filters runs via `_run_read_allowed` (`verification.py`) | 2f8d79a | CLOSED |
| F7a-per-run | LOW | `check_report_body_sensitivity` (per-run) also gates declared runs via `_run_read_allowed` (`verification.py`) — Codex neighbor | 7cddacf | CLOSED |
| F7b | LOW | `_resolve_claim`/`add_claim_link` gain identity + gate catalog/ledger reads (`builder_service.py`) | 2f8d79a | CLOSED |
| F7c-cursor | LOW | audit `list_events` cursor lookup scoped by `actor_workspace_id` (`audit_service.py`) | 2f8d79a | CLOSED |
| F7c-DELETE | LOW→MED | cross-workspace `delete_draft` returns **204** (indistinguishable from missing), not 404, without touching the foreign file — Codex neighbor (a prior Claude pass **mis-cleared** this) | 7cddacf | CLOSED |
| G1 | gov | `deployment_mode` inferred `multi_user` on non-loopback+auth bind; explicit `trusted_single_operator_posture` escape hatch (fail-closed on half-declaration). **Precedence fix:** explicit `single_user` on public+auth bind rejected at load unless posture declared — Codex neighbor (`config.py`) | d9eeefd, 7417805 | CLOSED |
| G2 | gov | `_di1_audit_accepted` verifies audit `audited_head` against current HEAD (staleness detection), not just the literal `status:` string (`config.py`) | d9eeefd | CLOSED |

## Validation

- **Tests:** ~80 new security tests, all passing. Full suite = **8 pre-existing baseline failures only**
  (`test_serve_api.py` ×5 default-public sensitivity gate, `test_assertion_rollout.py` ×2,
  `test_report_anchors.py` ×1) — verified byte-identical at base `77fe327`. **Zero functional
  regressions.** (One additional test, `test_cli_rights::test_rights_validate_requires_as_of`,
  surfaces in full-suite runs as order-dependent — it fails identically in isolation at `77fe327`,
  so it is a pre-existing test-hygiene issue exposed by new-test collection order, NOT a remediation
  regression. See Follow-ups.)
- **Lint/type:** ruff neutral (49 vs 49 at baseline on changed files; new files clean); mypy net −4
  (F3's None-guard eliminated 4 pre-existing union-attr errors).
- **F1 runtime probe:** public+no-auth `create_app` refused; public+token allowed; loopback allowed.
- **F2 runtime probe:** every in-threat-model transport vector raises `UnsupportedTransportError`.

## Deployment interaction — REQUIRED before next `/redeploy` of the LAN node

The live node (`10.42.10.76:7432`) runs `rf serve --bind-host 0.0.0.0` (token auth, single-operator,
trusted LAN). After F1(1) + G1 land, that node WILL change startup behavior:
1. F1(1) propagates `bind_host=0.0.0.0` → the `config.py` non-loopback isolation guard now fires; if
   the node's `workspace_isolation_enforcement=disabled`, **startup raises**.
2. G1 infers `multi_user` on a non-loopback+auth bind → arms the FR-13 DI-1 gate → **refuses to start**
   (DI-1 is BLOCKED) **unless** the operator declares `foundry.trusted_single_operator_posture`.

**Action before redeploy:** add `foundry.trusted_single_operator_posture` (declared/rationale/
declared_at/declared_by) to the node's `foundry.yaml` and set `workspace_isolation_enforcement`
consistently, then verify `rf serve --bind-host 0.0.0.0` starts cleanly (a startup warning + audit
event will fire on every launch, by design).

## Residuals (stated, not chased)

- **No live adversarial two-workspace runtime test** was performed (audit item 5). This remains the
  real gate — static review + runtime probes cannot fully substitute. Required before any
  adversarial-tenancy sign-off.
- **F2 base-explicit escape:** `FastMCP.sse_app(server)` / `super(...).sse_app()` bypasses the subclass
  guard. Irreducible in Python, equivalent to constructing a fresh FastMCP — out of threat model. The
  real stdio-only guarantee is operational (the launcher only starts stdio + no network mount); the
  subclass guard is defense-in-depth against accidental/casual network mounts.
- **G1 audit event** for the trusted-single-operator posture is warning-only (a `config.py →
  audit_service` circular import blocks emitting a real audit event at config-load); TODO left in code.
- **`test_cli_rights` order-dependence** (pre-existing, unrelated subsystem) — worth a follow-up fix.

## Next steps (NOT part of this remediation)

1. **Run a fresh DI-1 delta re-audit** against the post-remediation HEAD.
2. **Commission the live two-workspace adversarial runtime test.**
3. Human Mode-D decision on DI-1 / deployment enablement (still reserved, still BLOCKED here).
