---
title: "DI-1 Delta Re-Audit — Adversarial Multi-Tenant Isolation (HEAD d71a261)"
doc_type: audit
schema_version: 2
report_category: security-audit
feature_slug: public-multiuser-release-activation
phase: delta-reaudit
created: 2026-07-26
updated: 2026-07-26
status: pending_human_mode_d_decision
requirement_ids: [DF-004, ACT-406]
gates: [DI-1, "Mode D (blocked-external, human-only)"]
supersedes_scope_of: docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
prior_audit_baseline: "60f40c8 (P1) + worktree state; accepted 2026-07-22 for TRUSTED-COHORT multi_user only — explicitly NOT adversarial multi-tenant isolation for runs/evidence"
audited_head: d71a261d85cf6eb05f12f250c244e7ef253b759e
delta_window: "60f40c8 -> d71a261; material isolation change = 08559a0 (DF-004), + four later commits (95e8419/d824290 CARP C3, feab7de/d71a261 claim-term-index)"
method:
  - "4 parallel adversarial surface probes (Claude, read-only Mode E) — runs/writeback, enforcement-default, agent-jobs/term-index, catalog/share"
  - "1 independent cross-model adversarial validation (Codex gpt-5.6-sol, read-only, xhigh) — session 019f9ffc-0ff6-76d3-b54a-66447fed6f0d"
  - "100% static code + config trace; NO live adversarial runtime test was performed"
signoff:
  decision: PENDING
  note: >
    This document is a findings artifact. The DI-1 / adversarial-multi-tenant signoff is a
    human-only Mode-D decision and has NOT been made. Nothing in this file certifies adversarial
    multi-tenant safety, owner-data qualification, public deployment readiness, clinical validation,
    or a released hosted service. It is NOT self-signed.
evidence_bundle: .claude/reports/di1-reaudit/
---

# DI-1 Delta Re-Audit — Adversarial Multi-Tenant Isolation

## Executive verdict

**HEAD `d71a261` is NOT adversarially multi-tenant safe. The DI-1 gate must remain BLOCKED.
Do not certify an untrusted / adversarial multi-tenant or public deployment.**

Two things are simultaneously true, and both matter:

1. **The prior audit's accepted headline residual risk was genuinely remediated.** DF-004 (`08559a0`)
   added a real `workspace_id` concept to runs/claims/evidence and wired every enumerated read/write
   path through a single `require_workspace_scope` choke point. Prior-audit rows 9–12 are **CONFINED
   when isolation is enforcing**, with server-side (never client-supplied) ownership stamping and
   test coverage. This closes the exact gap the 2026-07-22 acceptance flagged as deferred.

2. **The re-audit nonetheless surfaces enough new and confirmed cross-tenant exposure to reject a
   safety claim.** An independent second model (Codex gpt-5.6-sol) **refuted** the "fail-closed on a
   public bind" conclusion the Claude probes had reached, and found **cross-workspace report
   read/write paths the four probes missed** — including a high-severity report-builder exfiltration
   path. There is also an unremediated MCP transport that trusts an unverified client identity, and
   two governance gaps that let a public multi-identity deployment run without ever triggering the
   intended human sign-off.

"Remediated in code for rows 9–12" is real. It is **not** the same statement as "this deployment
posture is adversarially safe" — which is precisely the distinction the standing guardrail on this
task forbids collapsing.

## Delta vs. the prior accepted audit

| Prior-audit residual (accepted 2026-07-22 as deferred) | Status at HEAD d71a261 | Evidence |
|---|---|---|
| Row 9 — agent-jobs client-supplied `workspace_id` → spoofable FR-12 attribution | **REMEDIATED** (CONFINED when enforcing) | `agent_job_service.py:865,872` recomputes `effective_workspace_id` from identity at the service layer; audit `actor_workspace_id` uses the same formula; no bulk-list endpoint. Tests 12/12 pass. |
| Rows 10–12 — runs/claims/evidence have no `workspace_id` at all; any caller reads/acts on every run | **REMEDIATED** (CONFINED when enforcing) | Launch stamping unconditional (`planning.py:747,984`, no client-suppliable field); 6 reads + writeback-approve gate via `require_workspace_scope`; 404-on-deny (no existence leak); writeback has no `public`-visibility bypass (`writeback.py:32-34`). |

The prior audit's `status: accepted` frontmatter is now **stale** — it predates DF-004, still lists
rows 10–12 as accepted residual risk, and the FR-13 gate that trusts it has no mechanism to detect
staleness (`config.py:979-1004` checks the literal `status:` string only). This re-audit is the
re-issued artifact for that scope; it does **not** alter the prior document's frontmatter.

## Findings introduced since the accepted audit (the actual delta)

Verdict vocabulary: **CONFIRMED** = corroborated by two independent models and/or a passing test;
**PLAUSIBLE** = single-model static code-read, concrete file:line, needs remediation-time (ideally
runtime) verification.

| # | Finding | Severity | Verdict | Evidence |
|---|---|---|---|---|
| F1 | **Public-bind enforcement bypass (bind-host split).** `rf serve` passes CLI `--bind-host` to Uvicorn but never copies it into the config `create_app`/isolation services inspect; `--bind-host 0.0.0.0` + `workspace_isolation_enforcement=disabled` binds public while isolation resolves **advisory** from the stale loopback value. `create_app` is also directly mountable (uvicorn/gunicorn/ASGI) with **no** non-loopback auth gate → `provider=none` ⇒ `identity=None` ⇒ `require_workspace_scope` short-circuits to allow. | **HIGH** | PLAUSIBLE (Codex; in tension with Probe 2 — see below) | `cli_commands.py:3054,3071,3120`; `app.py:110,250`; `scope.py:73,174`; `config.py:843,857` |
| F2 | **MCP transport trusts unverified client identity.** 7 CARP-5.2 MCP tools marshal a caller-supplied JSON `identity` (any `workspace_id`) **and** a self-declared `sensitivity_threshold` (no server ceiling on this transport) straight into the real workspace-partitioned `AssertionCatalog`; assertion IDs/versions/coverage return to the caller — a cross-workspace lexical enumeration oracle. | **HIGH** (topology-gated) | CONFIRMED (Probe 4 + Codex) | `mcp_server.py:80-104,127,274`; `router.py:344,586,796`; packaged topology = stdio (`.mcp.json:2`, `pyproject.toml:55`) but `build_server()` permits network transport and the isolating wrapper is not in-repo (`mcp_server.py:106`) |
| F3 | **Report Builder "from run" cross-workspace exfiltration.** An authenticated ws_b caller can name a private ws_a run; `export_run` receives **no identity** and its raw `report_draft` is copied into a new ws_b-owned draft. | **HIGH** | PLAUSIBLE (Codex; missed by all 4 probes) | `builder_service.py:1017`; `export_service.py:1159` |
| F4 | **Report verify / publish-preview cross-workspace read+write.** ws_b can unscoped-read ws_a drafts, receive verification metadata, and overwrite ws_a's derived `verification.yaml` before workspace/RBAC enforcement runs. | **MED** | PLAUSIBLE (Codex) | `reports.py:802,898`; `verification.py:1757` |
| F5 | **Workspace-local admin mutates process-global rate limits.** A ws_b admin can alter deployment-global limits applied to every tenant (cross-tenant throttling / weakening). | **MED** | PLAUSIBLE (Codex) | `admin.py:455`; `rate_limit.py:269` |
| F6 | **`peek_catalog_generation_id()` unscoped digest/existence oracle.** Identity-free file-read keyed by a raw `workspace_id` string; returns another workspace's catalog-projection existence + sha256 corpus digest. Both current callers align by convention, not an enforced invariant. | **LOW / latent** | CONFIRMED (Probe 4; no live HTTP path today) | `catalog_retrieval.py:185-212,595`; callers `planning.py:812`, `router.py:344` |
| F7 | **Lower-severity oracles.** Global verification source-card oracle on exact-quote match (`verification.py:339,1674`); identity-free claim-link resolution exposing another workspace's claim existence/status (`builder_service.py:676,745`); cross-workspace audit-cursor pagination + DELETE 404/204 draft-existence oracle (`audit_service.py:349`, `reports.py:385`). | **LOW** | PLAUSIBLE (Codex) | as cited |

**Confirmed CONFINED (no action):** catalog `retrieve()`/`catalog_receipt()`, `build_evidence_plan()`,
claim term-index (per-claim inline; `catalog_terms` scoped via join to `catalog_items.workspace_id`;
19/19 tests), HTTP `assertions.py`/`catalog.py` routers (identity server-derived), share-links
(opt-in / RBAC-gated / single-resource / re-checked at resolution), DF-004 public-visibility
(read-only, workspace-default, byte-unchanged). Caller-identity, admin token/account routes, and CLI
bulk-export paths came back **none-found** (workspace-scoped, or local-operator CLI outside the
network threat model).

## The Claude ↔ Codex tension on F1 (must be resolved at remediation, not here)

Probe 2 (Claude) concluded the public-bind path is fail-closed because `config.py:843-851` **raises
`ValueError`** on `workspace_isolation_enforcement=disabled` + a non-loopback `bind_host`. Codex
(gpt-5.6-sol) refuted this by finding that the CLI's `--bind-host` is **never propagated into the
config object** that guard reads — so the listener binds `0.0.0.0` while the config still sees
loopback and the `ValueError` never fires. These are not contradictory: Codex found a **bypass of the
very guard Probe 2 trusted**. If Codex's bind-host-split reading is accurate, F1 is a genuine
public-bind-with-advisory-isolation hole. This is the single most important item to verify at
remediation time (ideally with a live `rf serve --bind-host 0.0.0.0` test that inspects the resolved
`app.state.workspace_isolation_enforced`), and is a primary reason a code-read alone cannot certify
safety.

## Governance findings (process, not code defects — but they bear on the gate)

- **G1 — FR-13 DI-1 acknowledgment gate is bypassable.** `deployment_mode` defaults to `single_user`
  and is never inferred from bind host or auth provider; the human-acknowledgment gate only arms when
  the operator explicitly sets `deployment_mode: multi_user` (`config.py:1208-1210`). A public,
  token-authenticated, multi-identity deployment can therefore run indefinitely under `single_user`
  semantics, never triggering the intended sign-off, with RBAC/isolation only AUTO-derived rather
  than the hardened `enabled` literal.
- **G2 — the accepted audit artifact is stale and undetectably so** (see Delta section).

## What this re-audit explicitly does NOT establish

Per the standing Mode-D guardrail, none of the following were treated as evidence of adversarial
multi-tenant safety, and none are asserted here:

- Repository readiness / clean build / green fixtures — **not** proof of adversarial safety. (Probe
  tests that passed cover the *enforcing* path only; they do not exercise F1/F3/F4 adversarially.)
- Trusted-cohort acceptance (the 2026-07-22 sign-off) — explicitly scoped to trusted cohort, never to
  adversarial isolation.
- A healthy LAN endpoint — the node serves fully-open, single-user; it says nothing about tenant
  isolation.
- Owner-data qualification, public deployment, clinical validation, or a released hosted service —
  none are in scope or claimed.
- **No live adversarial runtime test was performed.** This is a 100% static trace. F1, F3, F4, F5
  in particular are single-model code-read (PLAUSIBLE) and require runtime confirmation.

## Recommended actions (for the human's consideration — not a decision)

1. **Do not clear DI-1 / do not enable an adversarial or public multi-tenant deployment** at this HEAD.
2. **Remediate the HIGH findings first:** F1 (propagate the real bind host into config so the
   non-loopback guard cannot be stale-bypassed; add a non-loopback gate to `create_app` itself, not
   only the CLI), F2 (require server-verified identity on the MCP transport or hard-constrain it to
   per-user stdio with a documented, in-repo isolating wrapper), F3 (thread identity into
   `export_run`/report-builder "from run"). 
3. **Then MED/LOW:** F4, F5, F6, F7.
4. **Close the governance gaps:** infer/force `deployment_mode=multi_user` (and its FR-13 gate) from a
   non-loopback bind (G1); add staleness detection to the FR-13 audit-artifact check (G2).
5. **Commission a live adversarial runtime test** (two real workspaces, cross-tenant read/write
   attempts against every surface above) before any future adversarial-tenancy sign-off — static
   review cannot substitute for it.
6. **Re-run this delta re-audit** against the post-remediation HEAD.

## Mode-D Decision Block — HUMAN ONLY

> This decision is reserved for the human operator. It has not been made and must not be
> self-signed by any agent. Repository readiness, trusted-cohort acceptance, fixture passes, and a
> healthy LAN endpoint do not constitute this decision.

- [ ] **Acknowledged** — findings reviewed; DI-1 remains BLOCKED for adversarial/public multi-tenant use; remediation to proceed.
- [ ] **Accept residual (scope-limited)** — specify the exact deployment posture being accepted and why the findings above are tolerable within it (e.g., a re-affirmed trusted-cohort-only posture). Must name F1–F7 explicitly.
- [ ] **Reject / escalate** — request changes to this audit or additional investigation before any decision.

Signed_by: ____________________  Date: __________  Decision: __________

_Findings method + full per-surface evidence: `.claude/reports/di1-reaudit/` (four probe reports +
the Codex validation transcript). Codex session `019f9ffc-0ff6-76d3-b54a-66447fed6f0d`._
