---
schema_version: 2
doc_type: phase_plan
title: "WKSP-304 Phase 1-2: Config Flag + Identity Threading"
status: draft
created: 2026-07-08
phase: "P1-P2"
phase_title: "Config flag + fail-closed validation; identity threading router -> service"
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
feature_slug: wksp-304-workspace-isolation-enforcement
entry_criteria: ["None — wave 1, no dependencies"]
exit_criteria:
  - "P1: flag resolves correctly across all provider/bind permutations; ValueError raised on the forbidden combo"
  - "P2: every in-scope router passes identity to the service layer; existing suite unmodified-green; seam task confirms propagation reaches the P3 signature"
---

# Phase 1-2: Config Flag + Identity Threading

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md)

**Duration**: ~1.5-2 days combined (P1: ~0.5-1 day, P2: ~1-1.5 days)
**Dependencies**: None — both phases run in wave 1 (parallelizable slice; disjoint files, both inert per D4)
**Assigned Subagent(s)**: python-backend-engineer (both phases, solo)

Both phases are grouped in one file because they are the plan's only parallel slice, both inert (no behavior change — D4), and both mechanical relative to P3/P4.

---

## Phase 1: Config Flag + Fail-Closed Validation

**Scope**: Add `workspace_isolation_enforcement` (`auto|enabled|disabled`) to `src/research_foundry/config.py`, structurally mirroring the shipped `auth.rbac_enforcement` pattern (`config.py:471-560`) exactly — same enum shape, same `resolve_*_enforced(provider, bind_host)` method signature, same two fail-closed invariants (non-loopback + disabled -> `ValueError`; `auto` keyed on `auth.provider`).

**Verifies**: AC-7 (Config fail-closed invariants) — target_surfaces: `src/research_foundry/config.py`.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|-------------|-------|--------|---------------|
| TASK-1.1 | Flag enum + parser | Add a `WorkspaceIsolationEnforcement`-equivalent enum (`auto\|enabled\|disabled`) and `Config.workspace_isolation_enforcement()` parse method, structurally mirroring `Config.auth_rbac_enforcement()`. Invalid enum value raises `ValueError` listing valid values (mirrors `config.py:494-502`). | Parser accepts all 3 valid values; raises `ValueError` with the valid-values list on any other input; unit test covers both branches. | 0.5 pt | python-backend-engineer | sonnet | adaptive | None |
| TASK-1.2 | Resolver + fail-closed validation | Add `Config.resolve_workspace_isolation_enforced(provider, bind_host)`, called once at app-create time, result cached on `app.state.workspace_isolation_enforced` (mirrors `app.state.rbac_enforced`). Raises `ValueError` at startup when `workspace_isolation_enforcement=disabled` AND `bind_host` is non-loopback. `auto` resolves to enforcing when `auth.provider != "none"`, advisory when `provider == "none"` (mirrors `config.py:536-556`). Reuses the existing `_is_loopback()` helper — no new helper introduced. | `ValueError` raised on 100% of tested non-loopback + `disabled` combinations; `auto` resolution matches the provider-keyed truth table in both directions; unit test covers loopback x enforcement-value x provider matrix at the config-module level (full integration matrix deferred to TASK-5.6). | 0.5 pt | python-backend-engineer | sonnet | adaptive | TASK-1.1 |

**Phase 1 Quality Gates:**
- [ ] `workspace_isolation_enforcement` flag resolves identically in shape/behavior to `auth.rbac_enforcement` for the equivalent inputs.
- [ ] Startup `ValueError` fires on every tested forbidden combination.
- [ ] `app.state.workspace_isolation_enforced` is set once at app-create time, not re-resolved per-request.
- [ ] `task-completion-validator` phase-end pass.

**Key files**: `src/research_foundry/config.py` (single-file phase; no cross-owner seam — `integration_owner` not required for P1).

---

## Phase 2: Identity Threading, Router -> Service

**Scope**: Thread `identity: AuthIdentity | None` from `request.state.identity` through the 6 in-scope routers into the service call signatures added (inert) in Phase 3. No behavior change — this phase only adds a parameter that nothing yet consumes for a deny decision.

**Verifies**: AC-1 (Identity threading across all in-scope routers) — target_surfaces: `catalog.py`, `agent_jobs.py`, `reports.py`, `admin.py`, `audit.py`, `auth_identity.py`.

**Integration owner**: `python-backend-engineer` (declared per R-P3 — this phase's files intersect with Phase 3's `files_affected` at the call-signature seam; the owner is responsible for the seam task below).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|-------------|-------|--------|---------------|
| TASK-2.1 | Thread identity: catalog.py, agent_jobs.py | Resolve `identity = getattr(request.state, "identity", None)` (existing pattern) in every endpoint of `catalog.py` and `agent_jobs.py` that calls into `catalog_service`/`agent_job_service`; pass `identity` as an explicit keyword argument. Never omit the argument when `identity is None` — pass it explicitly. | Every endpoint in both routers that reaches a scoped service method passes `identity` explicitly; no endpoint silently omits it. | 0.5 pt | python-backend-engineer | sonnet | adaptive | None |
| TASK-2.2 | Thread identity: reports.py | Same pattern for `reports.py`'s calls into `builder_service` (draft-to-report build paths). | Every `builder_service` call site in `reports.py` passes `identity` explicitly. | 0.4 pt | python-backend-engineer | sonnet | adaptive | None |
| TASK-2.3 | Thread identity-adjacent surfaces: admin.py, audit.py, auth_identity.py | These 3 routers already resolve identity for their own endpoints and do not call the 3 in-scope services directly today (confirmed via exploration grep). Verify no hidden call exists; if `admin.py` gains any future service call, identity must already be in scope at the call site — this task documents the current no-op status per router (AC-1 target_surfaces completeness, not new plumbing). | Grep-confirmed: no `catalog_service`/`builder_service`/`agent_job_service` calls in these 3 routers today. If any is found, treat as a Risk-4 finding and escalate before closing this task. | 0.3 pt | python-backend-engineer | sonnet | adaptive | None |
| TASK-2.4 | Seam task: P2->P3 propagation verification | **R-P3 seam task.** For each router/service pair (`catalog.py`->`catalog_service`, `agent_jobs.py`->`agent_job_service`, `reports.py`->`builder_service`), write a lightweight call-signature test or static check confirming the `identity` argument threaded in TASK-2.1/2.2 actually lands on the corresponding service method's `identity` parameter added in Phase 3 (not dropped, not shadowed, not defaulted away). This task is the formal handoff proof between the two phase owners. | For every router/service pair in scope, a test or inspection artifact demonstrates the identity value passed at the router boundary is the exact value received at the service boundary. | 0.3 pt | python-backend-engineer | sonnet | adaptive | TASK-2.1, TASK-2.2, Phase 3 signatures (TASK-3.1/3.2/3.3) must exist to complete verification — coordinate timing with P3 owner. |

**Phase 2 Quality Gates:**
- [ ] All 6 in-scope routers pass `identity` explicitly (never an omitted/defaulted argument) into any scoped service call.
- [ ] Existing test suite passes unmodified (no behavior change introduced).
- [ ] TASK-2.4 seam verification completes once Phase 3 signatures land (may close slightly after P3 begins — the seam task's *verification* half depends on P3's signatures existing, but its *router-side* half is completable within P2's wave).
- [ ] `task-completion-validator` phase-end pass.

**Key files**: `src/research_foundry/api/routers/catalog.py`, `agent_jobs.py`, `reports.py`, `admin.py`, `audit.py`, `auth_identity.py`.

**Note on TASK-2.4 sequencing**: TASK-2.4 is listed here (Phase 2's seam responsibility) but its full closure requires Phase 3's service signatures to exist. In practice: author the router-side identity threading in P2's wave; close the seam verification once P3's TASK-3.1/3.2/3.3 land, before P3's exit-gate checklist (TASK-3.6) signs off. This is not a violation of the P3->P4 invariant — it is a P2<->P3 handoff, not the P3->P4 arming boundary.

---

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Next: Phase 3](./phase-3-query-layer-scoping.md)
