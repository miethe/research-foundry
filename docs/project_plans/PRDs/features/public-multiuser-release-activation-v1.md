---
title: "PRD: Public Multi-User Release Activation — Deployment Modes, Non-Human Principals, DI-1 Gate"
schema_version: 2
doc_type: prd
it_schema: 1
description: >
  Activates the auth/RBAC/workspace-isolation substrate shipped under public-multiuser-p5-auth-rbac-v1
  by (1) composing its five independent config knobs into two validated, fail-closed deployment-mode
  presets (single_user | multi_user), (2) introducing dynamic non-human principals — service accounts
  and user-scoped PATs — backed by a new SQLite token store, and (3) closing the DI-1 full-surface
  workspace-scoping audit as a hard pre-multi-tenant deploy gate, plus the admin UI to manage both.
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
feature_version: v1
tier: 3
effort_estimate: "~34-42 pts (Tier 3, rough bottom-up by capability area; final H1-H6 sanity check deferred to the implementation plan per estimation-heuristics.md)"
prd_ref: null
plan_ref: null
related_documents:
  - docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/human-briefs/public-release-phase5-gap-closure.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/skills/planning/references/ac-schema.md
  related_prds:
    - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: []
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
owner: nick
contributors: []
priority: high
risk_level: high
category: "product-planning"
tags: [prd, planning, feature, auth, rbac, multi-user, activation, service-accounts, pat, di-1]
milestone: "public-multiuser-activation"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/config.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/services/token_service.py
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/services/agent_job_service.py
  - src/research_foundry/api/middleware/auth.py
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/api/auth/scope.py
  - src/research_foundry/api/routers/admin.py
  - src/research_foundry/api/routers/agent_jobs.py
  - frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx
  - frontend/runs-viewer/src/auth/AuthContext.tsx
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
open_questions:
  - q: "Does multi_user preset hard-require auth.provider=clerk, or does it accept local_static as a valid human-auth layer (existing multi-token model)?"
    owner: nick
    status: resolved-in-prd
  - q: "Should service-account tokens support fine-grained tool/data-scope allowlists (beyond a single role), matching P4's agent-permission model?"
    owner: nick
    status: deferred
decisions:
  - decision: "multi_user preset's fail-closed gate checks auth.provider != 'none' (not a specific provider) plus rbac_enforcement=enforced, workspace_isolation_enforcement=enforced, and an explicit DI-1 acknowledgment flag."
    rationale: "local_static already satisfies 'server-verifiable non-none identity' for closed-beta multi-user deployments without Clerk procurement (FU-3 open); decoupling the gate from a specific provider keeps the preset usable today."
    status: accepted
  - decision: "Token store extends the existing rbac.db (SQLite) rather than introducing a new datastore."
    rationale: "Matches the assumption carried from the parent P5 plan; avoids a second source of truth for identity data; Postgres migration is an explicit future-scale item, not this feature's scope."
    status: accepted
success_metrics:
  - "Operator can select a deployment mode via one config key (or --mode flag) instead of tuning 5 independent knobs by hand."
  - "100% of enumerated workspace-write surfaces have a DI-1 audit verdict (accepted or remediated) before multi_user is startable."
  - "Service accounts and PATs are issuable, listable, and revocable via the admin API and admin UI with zero plaintext secrets persisted."
  - "100% of agent_jobs launched while deployment_mode=multi_user resolve to a service-account execution identity in the audit log."
agent_title: "Activate public multi-user mode: deployment presets, non-human principals, DI-1 gate"
agent_summary: >
  Compose the shipped P5 auth/RBAC/isolation knobs into a validated single_user|multi_user preset,
  add a dynamic service-account/PAT token store + admin API/UI, and close the DI-1 full-surface
  workspace-scoping audit as a hard gate before multi_user can start.
---

# Feature Brief & Metadata

**Feature Name:**

> Public Multi-User Release Activation

**Filepath Name:**

> `public-multiuser-release-activation-v1`

**Date:**

> 2026-07-22

**Author:**

> Claude (Opus 4.8, prd-writer)

**Related Epic(s)/PRD ID(s):**

> Parent: `public-multiuser-p5-auth-rbac-v1` (status: completed — substrate this PRD activates)

**Related Documents:**

> - `docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md` — parent PRD; auth port, RBAC, WKSP-304 isolation, audit log, and admin API all shipped under this
> - `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` — §11/§12 Phase 5 release gates; Screens 7–10 (catalog/builder/agents) already shipped
> - `docs/project_plans/human-briefs/public-release-phase5-gap-closure.md` — existing gap-closure inventory; this PRD converts its Mode D items into executable scope
> - `docs/projects/research-foundry/SERVICE_CONTRACT.md` — DI-1 audit references at §14/§17/§18 (write-site scoping surfaces)
> - `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` — ADR-001 `AuthProvider` port design

---

## 1. Executive Summary

Research Foundry's P5 hardening work shipped a complete auth/RBAC/workspace-isolation substrate, but activating it for a real public multi-user deployment today means an operator hand-tunes five independent config knobs with no validated composition, and there is no concept of a non-human principal — every agent job and machine caller either rides the single-operator-trust bypass or a static config-time token. This PRD delivers a `deployment_mode` preset (`single_user` | `multi_user`) that composes the existing knobs into two fail-closed profiles, a dynamic service-account/PAT token store for machine and delegated-human identities, the admin surfaces to manage them, and closes the DI-1 full-surface scoping audit as the hard gate multi_user cannot start without.

**Priority:** HIGH

**Key Outcomes:**
- Outcome 1: An operator flips one switch (`deployment_mode: multi_user` or `rf serve --mode multi_user`) instead of independently tuning `auth.provider`, `auth.rbac_enforcement`, `workspace_isolation_enforcement`, bind host, and rate limits — and the switch refuses to start if the composition is unsafe.
- Outcome 2: Non-human callers (background agent jobs, integrations, CI) get named, role-scoped, revocable **service accounts**; humans can self-issue role-capped **PATs** — both dynamic, DB-backed, and distinct from static config-time tokens.
- Outcome 3: The DI-1 full-project write-site audit — previously only feature-scoped — is completed repo-wide and becomes a startup-enforced precondition for `multi_user`, closing the exact gap the WKSP-304 AAR flagged (a prior "100% coverage" claim on this surface was later found incomplete).

---

## 2. Context & Background

### Current State

Everything this PRD builds on is **already shipped** (code-truth, verified 2026-07-22):

- **Auth port**: `src/research_foundry/api/auth/provider.py` — `AuthProvider` Protocol, `AuthIdentity{user_id, workspace_id, roles}`, adapter registry. Adapters: `local_static.py` (multi static config-time Bearer tokens, `hmac.compare_digest`), `clerk.py` (RS256 JWKS, dark-by-default), `oidc.py` (registered stub, unimplemented). Default `auth.provider = "none"`. Selected via `foundry.yaml` `auth.provider`; middleware at `api/middleware/auth.py` (`AuthProviderMiddleware`).
- **RBAC**: `api/auth/rbac.py` — 5 roles (`owner`/`admin`/`researcher`/`reviewer`/`viewer`), `require_role()` per-route dependency. Toggle `auth.rbac_enforcement = auto|enforced|disabled`, fail-closed on `disabled` + non-loopback bind.
- **Workspace isolation (WKSP-304)**: `api/auth/scope.py`, flag `workspace_isolation_enforcement = auto|enforced|disabled`; `identity=None` → single-operator-trust (always allowed). **Known gap (DI-1)**: full-surface scoping enumeration is incomplete — two Mode-D leaks (`create_draft_from_run`/`create_draft_from_collection`, `catalog_service.get_item`) were found and fixed **after** a prior "100% coverage" sign-off (`eba75ab`). This is the hard gate before enforcing isolation on a shared multi-tenant store.
- **Store**: `services/rbac_store.py` — SQLite `.rf_state/rbac.db` (`workspaces`, `users`, `roles`, `memberships` tables). Audit: `services/audit_service.py` (append-only, fail-open). Rate limits: `middleware/rate_limit.py`. Admin API: `api/routers/admin.py` (workspace members, role updates, auth-provider status, rate-limit config, RBAC status). `rf serve` flags: `--port --bind-host --auth-mode(none|token) --sensitivity-threshold`.
- **What does not exist**: a `deployment_mode` preset of any kind (single-user vs. multi-user behavior emerges from tuning ~5 independent knobs by hand); any service-account or PAT concept (only static config-time tokens — no dynamic issue/rotate/expire/revoke, no `principal_type` distinction between human and machine callers); a repo-wide (as opposed to feature-scoped) DI-1 audit.

### Problem Space

The substrate is complete but **inert**: nothing tells an operator what a "safe multi-user configuration" looks like, and nothing stops them from starting a public bind with an unsafe combination (e.g., `auth.provider=clerk` but `workspace_isolation_enforcement=disabled`). Separately, the only non-human identity mechanism is a static token minted at deploy time and pasted into `foundry.yaml` — there is no way to name a machine principal, scope it to a role, issue it a token at runtime, or revoke it without a redeploy. Agent jobs (`agent_jobs.py`) currently run under whatever identity launched them (or none), which defeats the credential-isolation goal the P4 SPIKE (SEAM-2) established.

### Current Alternatives / Workarounds

Operators today manually set five `foundry.yaml` keys and hope they compose correctly; there is no startup validation that catches an inconsistent combination beyond the two independent `auto` idioms on RBAC and isolation. Non-human callers reuse the operator's own static token, which means agent jobs, CI, and any future integration are indistinguishable from the human operator in the audit log and cannot be scoped to a narrower role.

### Architectural Context

Research Foundry is a thin, file-backed control plane — Markdown/YAML as source of truth, SQLite (`rbac.db`, `catalog.db`) as derived/operational stores. This PRD:
- **Config layer** (`config.py`) — adds a composed preset resolver alongside the existing per-knob resolvers (`auth_provider()`, `auth_rbac_enforcement()`, `workspace_isolation_enforcement()`).
- **Services layer** — extends `rbac_store.py` with two new tables (`service_accounts`, `access_tokens`); no new datastore.
- **Middleware layer** — `AuthProviderMiddleware` gains a token-store precedence check ahead of the configured provider adapter (composite/chained resolution).
- **Admin API/UI** — additive routes/panels on the existing `api/routers/admin.py` and `frontend/runs-viewer/src/components/AdminSettings/` surfaces; no new frontend route tree.

---

## 3. Problem Statement

**User Story Format:**
> "As an operator preparing Research Foundry for a shared multi-user deployment, when I try to turn on multi-user mode today, I have to hand-tune five independent config knobs with no validation that they compose safely, and I have no way to give an autonomous agent job or a delegated human a named, revocable, role-scoped credential — instead of one validated mode switch and a dynamic principal store."

**Technical Root Cause:**
- `auth.provider`, `auth.rbac_enforcement`, `workspace_isolation_enforcement`, `viewer.bind_host`, and `auth.rate_limit.enabled` are five independently-resolved config reads (`config.py:437,585,677` + CLI `--bind-host`/`--auth-mode`) with no single validated composition function.
- `local_static.py` tokens are parsed once from `foundry.yaml` at startup — there is no runtime issue/list/revoke path, no expiry, and no `principal_type` field distinguishing a human operator's token from a machine's.
- `agent_job_service.py` launches jobs under the caller's resolved identity (or `None`); there is no mechanism binding a job's execution identity to a dedicated, named service-account principal.
- DI-1 (per `SERVICE_CONTRACT.md` §14/§17/§18) has only ever been audited at feature scope (assertion-ledger); no repo-wide enumeration of workspace-write surfaces exists.

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Deployment-mode activation**
- Compose the five independent knobs into two validated, fail-closed presets: `single_user` (today's LAN/NUC default — single-operator-trust, minimal friction, must remain the default with zero behavior change) and `multi_user` (human auth on, RBAC enforced, isolation enforced, rate limits on, DI-1 cleared).
- Startup refuses to boot `multi_user` if the composition cannot be safely enforced.

**Goal 2: Non-human and delegated-human principals**
- Standalone named service accounts (`principal_type=service`) with a role, DB-backed, non-interactive — agent jobs run under one in `multi_user` mode.
- User-scoped PATs (`principal_type=user_pat`), role capped at ≤ the issuing user's role.
- Dynamic issue/list/revoke/expiry for both, opaque secret hashed at rest, shown once.

**Goal 3: Close the DI-1 gate**
- Enumerate every workspace-write surface repo-wide, close the two known leaks plus any newly found, and wire the audit's acceptance into the `multi_user` startup gate.

**Goal 4: Admin UI parity**
- Expose service-account/PAT issue/revoke and role management in the runs-viewer admin surface; auth-context reflects Clerk human session vs. service/PAT principal.

### Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Deployment-mode knobs | 5 independently tuned config keys, 0 presets | 1 config key / CLI flag, 2 validated presets | `deployment_mode` config resolver unit tests + `rf serve --mode` integration test |
| DI-1 audit coverage | Feature-scoped only (assertion-ledger) | 100% of enumerated workspace-write surfaces have a recorded verdict | Audit report row count vs. grep-derived surface inventory (cross-checked) |
| Non-human principal issuance | 0 (static tokens only) | Service accounts + PATs issuable/listable/revocable via admin API | Admin API test suite (issue → verify → revoke → verify-denied) |
| Agent-job identity binding | Human/static-token or `None` | 100% of `agent_jobs` launched under `deployment_mode=multi_user` resolve to a service-account identity in `audit_event` | Audit-log query against `agent_jobs` launches in a multi_user test run |
| Secret-at-rest exposure | N/A (no dynamic tokens exist) | 0 plaintext secrets persisted anywhere (DB, logs, audit) | Static scan (`git grep`-style check in test) + code review checklist |

---

## 5. User Personas & Journeys

### Personas

**Primary Persona: Self-hosted operator (Nick / homelab)**
- Role: Runs RF on a LAN node, single human, agent-heavy usage.
- Needs: Zero-friction default (`single_user`) must not regress; a clean upgrade path to `multi_user` when opening the deployment up.
- Pain Points: Today, "turning on multi-user" is an undocumented, error-prone sequence of raw config edits.

**Secondary Persona: Public-deployment admin (future SaaS operator)**
- Role: Owns a shared multi-tenant RF instance; onboards other humans and machine integrations.
- Needs: A way to name and scope machine callers (CI, agents, third-party integrations) without minting a static token per caller and redeploying.
- Pain Points: No revocation path for a compromised static token short of redeploy; no distinction between "the operator" and "the nightly agent job" in the audit log.

### High-level Flow

```mermaid
graph TD
    A[Bearer credential on request] --> B{Matches an access_tokens row?}
    B -- yes, not expired/revoked --> C[Resolve identity from token store\nprincipal_type=service|user_pat]
    B -- no --> D{deployment_mode / auth.provider}
    D -- clerk --> E[Verify RS256 JWT via JWKS]
    D -- local_static --> F[Compare against config-time tokens]
    D -- none --> G[identity=None, single-operator-trust]
    C --> H[RBAC + workspace-scope checks]
    E --> H
    F --> H
    G --> H
    H --> I[Route handler / agent-job launch]
```

---

## 6. Requirements

### 6.1 Functional Requirements

| ID | Requirement | Priority | Notes |
| :-: | ----------- | :------: | ----- |
| FR-1 | Add `deployment_mode: single_user \| multi_user` to `foundry.yaml` (default `single_user`), resolved via a new `Config.deployment_mode()` method. | Must | Sibling key to `auth:` and `workspace_isolation_enforcement`, per WKSP-304 precedent. |
| FR-2 | `single_user` preset is behaviorally identical to today's un-set default (`auth.provider=none`, both enforcement flags `auto`, loopback-friendly). | Must | Zero regression for the LAN/NUC default — explicit test asserts byte-identical resolved config vs. pre-feature baseline. |
| FR-3 | `multi_user` preset resolves defaults of `auth.rbac_enforcement=enforced`, `workspace_isolation_enforcement=enforced`, `auth.rate_limit.enabled=true`; individual knobs remain independently overridable in `foundry.yaml`. | Must | Preset sets *defaults*, not hard-coded values — explicit per-knob overrides win. |
| FR-4 | Startup fail-closed gate: refuse to start when `deployment_mode=multi_user` and (a) `auth.provider=="none"`, or (b) RBAC cannot resolve to `enforced`, or (c) workspace isolation cannot resolve to `enforced`, or (d) the DI-1 acknowledgment flag (FR-13) is not `true`. | Must | Raises `ValueError` at boot, mirrors existing `auth_rbac_enforcement()` fail-closed pattern. |
| FR-5 | `rf serve --mode single_user\|multi_user` CLI flag mirrors and overrides the config-file `deployment_mode`. | Must | Follows existing `--auth-mode`/`--bind-host` flag conventions at `cli_commands.py:2601`. |
| FR-6 | Extend `rbac_store.py` with `service_accounts` (id, name, workspace_id, role, description, created_by, created_at, disabled_at) and `access_tokens` (id, principal_type, principal_id, workspace_id, role, token_hash, token_prefix, created_by, created_at, expires_at, revoked_at, last_used_at) tables, `CREATE TABLE IF NOT EXISTS` per existing idempotent-migration convention. | Must | No new datastore; SQLite extension only per assumption. |
| FR-7 | Token issuance generates an opaque random secret (≥256 bits entropy), returns it plaintext exactly once in the API response, and persists only a salted hash (`hmac`/`hashlib.sha256`) plus a short non-secret prefix for lookup/display. | Must | Same constant-time-compare discipline as `local_static.py`; never log or persist plaintext. |
| FR-8 | Service accounts: `principal_type=service`, named, assigned exactly one role, workspace-scoped, non-interactive (no login), issued/listed/revoked via admin API. | Must | "Named role but autonomous" — no human session backs it. |
| FR-9 | PATs: `principal_type=user_pat`, issued by/for a human user, role must be ≤ the issuing user's current role (enforced at issuance time; re-checked at each resolution in case the issuing user's role was since downgraded). | Must | Prevents privilege escalation via a stale PAT after a role downgrade. |
| FR-10 | Revocation: setting `revoked_at` immediately invalidates the token for all subsequent requests (checked at resolution, not cached). Expiry (`expires_at`, optional) is enforced the same way. | Must | Revocation must not require a restart. |
| FR-11 | `AuthProviderMiddleware` resolves Bearer credentials by first checking the access_tokens store (indexed prefix lookup + hash compare); on a hit it resolves identity directly (no provider adapter invoked); on a miss it falls through to the configured `auth.provider` adapter (e.g., Clerk JWT verification). | Must | Composite/chained resolution — humans via Clerk, machines via tokens, coexisting without a new `auth.provider` enum value. |
| FR-12 | `agent_jobs` launch path: when `deployment_mode=multi_user`, the job's execution identity is resolved from a configured default service account (`agents.default_service_account_id`) rather than the triggering caller's identity; `audit_event` records both the triggering identity and the executing service-account identity. | Must | Decouples human-triggered launch from machine execution identity per P4 SEAM-2 credential-isolation intent. |
| FR-13 | New config flag `auth.di1_audit_acknowledged: bool` (default `false`); `multi_user` startup additionally verifies the referenced audit report (`docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`) frontmatter `status: accepted`. Both must hold. | Must | Belt-and-suspenders: an operator boolean plus a machine-checkable artifact status, so neither a stale doc nor an unread flag alone can satisfy the gate. |
| FR-14 | DI-1 full-surface audit: enumerate every function/route that reads or writes workspace-scoped rows (catalog, builder/report-drafts, agent-jobs, admin, sharing) via a repo-wide backward-trace from every `AuthIdentity`/`workspace_id` construction site to its `resolve_workspace_isolation_enforced()`/`require_workspace_scope()` call, following the assertion-ledger DI-1-scoped audit's method. | Must | Template method already exists and is referenced in the human brief §5. |
| FR-15 | Admin API: `POST/GET /api/admin/service-accounts`, `DELETE /api/admin/service-accounts/{id}`, `POST /api/admin/service-accounts/{id}/tokens` (rotate); `POST/GET /api/admin/pats`, `DELETE /api/admin/pats/{id}`; `GET /api/admin/deployment-mode-status`. All mutation routes gated with `require_role`; PAT self-issue/list/revoke additionally scoped to the caller's own PATs unless caller is owner/admin. | Must | Response contracts never include raw secrets except the one-time issuance response. |
| FR-16 | Admin UI: `ServiceAccountsPanel.tsx` and `PersonalAccessTokensPanel.tsx` (issue/list/revoke, one-time-secret display with copy-and-dismiss UX), `AuthContext.tsx` extended to expose `principalType: "human" | "service" | "user_pat"` to consuming components. | Must | Additive to existing `AdminSettings/RoleAssignmentPanel.tsx`; no new route tree. |
| FR-17 | Audit log entries for: service-account/PAT issuance, revocation, rotation, and role change — same `audit_event` table/shape used by existing P5 audit logging. | Must | Consistent with §11 of the release-handoff spec ("who changed what"). |
| FR-18 | Public-sharing/publish-preview gates and report-body sensitivity fail-closed checks are re-verified under `deployment_mode=multi_user` with a real Clerk/local_static human session, confirming they still hold with enforcement flipped on (regression, not new logic). | Should | Carried from the gap-closure human brief §2 (already-shipped `share_store.py` needs a hardening/regression pass, not new code). |

### 6.2 Non-Functional Requirements

**Performance:**
- Token-store lookup adds ≤5ms p50 to request latency (indexed prefix lookup + single hash compare, in-process SQLite).
- DI-1 audit tooling runs as an offline/CI script, not a request-path dependency.

**Security:**
- Zero plaintext secrets persisted in `rbac.db`, logs, or `audit_event` rows — hash-at-rest, shown-once-in-response only.
- Constant-time hash comparison (`hmac.compare_digest`) for all token verification, matching `local_static.py`'s existing pattern.
- `multi_user` startup gate is fail-closed: any of the four FR-4 conditions unmet → refuse to boot, not "boot with a warning."
- PAT role-ceiling (FR-9) is re-checked at resolution time, not only at issuance.

**Reliability:**
- Revocation and expiry take effect immediately (no cache staleness window beyond the current request).
- `single_user` preset must be provably behavior-identical to pre-feature default (FR-2) — regression risk is the top concern for the LAN/NUC deployment.

**Accessibility:**
- New admin panels (`ServiceAccountsPanel`, `PersonalAccessTokensPanel`) meet WCAG 2.1 AA, matching the existing `RoleAssignmentPanel`/`AuthProviderStatusPanel` baseline.

**Observability:**
- Every issue/list/revoke/rotate/role-change action produces a structured `audit_event` row with actor identity, target principal, and outcome.
- Startup logs the resolved `deployment_mode` and which knobs were preset-defaulted vs. explicitly overridden.

---

## 7. Scope

### In Scope

- `deployment_mode` config preset (`single_user` | `multi_user`) composing the five existing P5 knobs, plus `rf serve --mode`.
- Fail-closed startup validation for `multi_user`, including the DI-1 acknowledgment gate.
- Dynamic service-account principals (`principal_type=service`) — DB-backed, named, role-scoped, non-interactive.
- Dynamic user-scoped PATs (`principal_type=user_pat`) — role ≤ issuing user's role.
- New `service_accounts` + `access_tokens` tables extending `rbac.db`.
- Composite/chained auth resolution (token store precedence, then configured provider) in `AuthProviderMiddleware`.
- Binding `agent_jobs` execution identity to a configured service account under `multi_user`.
- Admin API: issue/list/revoke/rotate for both principal types, role assignment, audit logging of issuance/revocation.
- Admin UI: service-account/PAT panels, auth-context principal-type reflection.
- DI-1 repo-wide full-surface workspace-scoping audit and remediation of any findings.
- Regression verification of sharing/publish-preview and report-body sensitivity fail-closed behavior under `multi_user`.

### Out of Scope

- **OIDC adapter live implementation** — deferred (FU-2/FU-3); `oidc.py` remains a registered seam only. This PRD does not implement or validate it.
- **Local self-managed human user store / signup flow** — Clerk (or an equivalent future human-auth provider) owns human signup; this PRD does not build one.
- **Rebuilding Screens 7–10** (catalog/builder/agents UI) — already shipped; only identity/role admin UI is net-new here.
- **Postgres migration of `rbac.db`** — noted as a future scale item; this PRD assumes SQLite is sufficient for the token store at current scale.
- **Fine-grained per-service-account tool/data-scope allowlists** — deferred; a service account gets exactly one role, matching the existing 5-role model, not a bespoke permission matrix (open question, deferred).
- **Live Clerk validation against a paid-plan tenant** — procurement-gated (FU-3); this PRD's `multi_user` gate does not hard-require Clerk specifically (see Decision log).

---

## 8. Dependencies & Assumptions

### External Dependencies

- **Clerk (optional)**: RS256 JWKS verification already implemented (`clerk.py`); paid-plan procurement (FU-3) remains unresolved and is not a blocker for this PRD, since `multi_user`'s gate does not hard-require a specific provider.
- **SQLite**: token store extends the existing `rbac.db`; no new external dependency.

### Internal Dependencies

- **public-multiuser-p5-auth-rbac-v1**: status `completed`; this PRD's entire scope is additive on top of it.
- **WKSP-304 workspace isolation**: status `shipped, flag-gated`; this PRD's DI-1 work is its explicitly-named pre-deploy hard gate.
- **assertion-ledger DI-1-scoped audit**: provides the audit *method* template (backward-trace from construction site to `resolve_or_deny` gate) this PRD expands repo-wide.

### Assumptions

- Token store extends the existing SQLite `rbac.db` (no new datastore) — per task scope.
- Tokens are opaque random secrets, hashed at rest, shown once at issuance — per task scope.
- `multi_user` middleware chains token-store lookup first, then the configured provider (Clerk) — per task scope; this does not introduce a new `auth.provider` enum value.
- `multi_user`'s fail-closed gate checks `auth.provider != "none"` (not a specific provider) — decouples the gate from Clerk procurement status (Decision log).
- The DI-1 audit's acceptance criterion is a two-part check (operator ack flag + artifact `status: accepted`) rather than a single boolean, to prevent either a stale document or an unread flag from silently satisfying the gate alone.

### Feature Flags

- `deployment_mode` (config key, default `single_user`) — this PRD's primary flag.
- `auth.di1_audit_acknowledged` (config key, default `false`) — operator acknowledgment half of the DI-1 gate.
- `agents.default_service_account_id` (config key, required when `agents.enabled=true` and `deployment_mode=multi_user`) — binds agent-job execution identity.

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
| ----- | :----: | :--------: | ---------- |
| `single_user` preset silently changes default behavior for the LAN/NUC deployment | High | Medium | FR-2 explicit regression test asserting byte-identical resolved config vs. pre-feature baseline; ship preset resolver additive-only. |
| DI-1 audit repeats the prior "100% coverage" false-complete claim (per WKSP-304 AAR) | Critical | Medium | Mode D per delegation-modes rule — human review of the audit's scope-boundary statement required before treating it as satisfied; FR-13's two-part gate (ack + artifact status) prevents self-certification alone from unlocking `multi_user`. |
| Token secret leaks via logging, error messages, or audit rows | Critical | Low | FR-7/NFR: hash-at-rest, shown-once, `_safe_artifact_stem()`-style credential-shape guards ported from `agent_job_service.py`'s existing pattern. |
| PAT privilege escalation after issuing-user role downgrade | High | Low | FR-9 re-checks the role ceiling at resolution time, not only issuance. |
| Composite auth chain (token-store-first) introduces a timing side channel distinguishing "valid prefix, bad hash" from "no matching prefix" | Medium | Low | Constant-time compare on the full lookup path (including a dummy-hash compare on prefix-miss) to avoid a measurable timing gap. |
| Agent-job service-account binding breaks existing single_user agent workflows (`agents.enabled=true`, `deployment_mode=single_user`) | Medium | Low | FR-12 binding only activates under `deployment_mode=multi_user`; `single_user` agent-job launches keep today's identity resolution unchanged. |
| Admin UI ships ahead of backend, exposing broken issue/revoke flows | Medium | Low | Sequenced last in Implementation Phases (Phase 5), after Phase 2/3 backend is tested. |

---

## 10. Target State (Post-Implementation)

**User Experience:**
- An operator sets `deployment_mode: multi_user` (or `rf serve --mode multi_user`) and either the server starts with the safe composed profile, or it refuses to start with a specific, actionable error naming which condition failed (missing DI-1 ack, provider still `none`, etc.).
- An admin issues a service account for a nightly agent job or a PAT for a delegated human from the admin UI; the secret is shown once, copied, and never retrievable again — only revocable.
- Agent-job launches in `multi_user` mode show up in the audit log under a named service account, not the triggering human.

**Technical Architecture:**
- `config.py` gains a `deployment_mode()` resolver and a composed-preset validator that both CLI and API paths consult at boot.
- `rbac_store.py` gains `service_accounts` + `access_tokens` tables with the same idempotent-migration discipline as existing tables.
- `AuthProviderMiddleware` performs a token-store lookup ahead of the configured provider adapter — a composite chain, not a new provider type.
- `agent_job_service.py` resolves execution identity from a configured default service account under `multi_user`.
- `docs/projects/research-foundry/SERVICE_CONTRACT.md` §14/§17/§18 DI-1 references are updated to point at the completed repo-wide audit artifact.

**Observable Outcomes:**
- `deployment_mode` and per-knob preset/override status are visible in `GET /api/admin/deployment-mode-status` and startup logs.
- `audit_event` shows issuance/revocation/rotation/role-change rows for both principal types.
- DI-1 audit report exists at `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` with `status: accepted` and a complete surface inventory.

---

## 11. Overall Acceptance Criteria (Definition of Done)

### Functional Acceptance

- [ ] `deployment_mode` config key + `rf serve --mode` flag implemented; `single_user` is behavior-identical to pre-feature default (FR-2).
- [ ] `multi_user` startup gate refuses to boot on any of the four FR-4 conditions, with a specific error message per condition.
- [ ] Service accounts and PATs: issue, list, revoke, rotate (service accounts only) all functional via admin API and admin UI.
- [ ] Composite auth resolution chain: token-store hit resolves without invoking the configured provider; miss falls through correctly.
- [ ] `agent_jobs` launched under `deployment_mode=multi_user` resolve execution identity to the configured default service account.
- [ ] DI-1 full-surface audit completed, all findings remediated, `status: accepted` in the audit artifact.

#### AC-1: Admin UI reflects principal type and secret lifecycle correctly across the identity-admin surface
- target_surfaces:
    - frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx
    - frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx
    - frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx
    - frontend/runs-viewer/src/auth/AuthContext.tsx
- propagation_contract: >
    `AuthContext.tsx` exposes `principalType` derived from the resolved identity's token-store row (service/user_pat) or Clerk session (human); `ServiceAccountsPanel`/`PersonalAccessTokensPanel` consume `GET /api/admin/service-accounts` and `GET /api/admin/pats` for list state, and the one-time plaintext secret is held only in local component state (never persisted to a store or URL) after a `POST` issue call, cleared on dismiss/navigation.
- resilience: >
    If `principalType` is absent from the resolved identity payload (e.g., older cached session), panels render the human-session default (no principal-type badge) rather than erroring; revoke/rotate buttons disable with a tooltip if the admin API call for status is unavailable.
- visual_evidence_required: false
- verified_by:
    - P5-ADMIN-UI-ISSUE-REVOKE-FLOW
    - P5-ADMIN-UI-SMOKE

#### AC-2: Composite auth resolution chain resolves correctly under all four credential states
- target_surfaces:
    - src/research_foundry/api/middleware/auth.py
    - src/research_foundry/services/token_service.py
    - src/research_foundry/api/auth/adapters/clerk.py
- propagation_contract: >
    `AuthProviderMiddleware` checks the Bearer credential against `access_tokens` (prefix lookup + hash compare) before invoking the configured provider adapter; a hit short-circuits to token-store identity resolution, a miss delegates to the configured provider.
- resilience: >
    An expired or revoked token resolves as "no match" (falls through to the configured provider, which will also reject it) rather than raising — the request ends in a normal 401, not a 500. A malformed/absent Authorization header never reaches the token-store lookup and resolves `identity=None` exactly as today.
- visual_evidence_required: false
- verified_by:
    - P5-AUTH-CHAIN-UNIT
    - P5-AUTH-CHAIN-INTEGRATION

#### AC-3: `multi_user` startup gate is fail-closed on every one of its four conditions independently
- target_surfaces:
    - src/research_foundry/config.py
    - src/research_foundry/api/app.py
- propagation_contract: >
    `Config.deployment_mode_validate()` (new) is called at API app startup and by `rf serve`; it evaluates all four FR-4 conditions and raises `ValueError` naming every unmet condition (not just the first).
- resilience: >
    If the DI-1 audit artifact file is missing entirely (not just `status != accepted`), the gate treats this identically to an unaccepted audit (fail-closed, not "assume passed" or "assume file doesn't apply").
- visual_evidence_required: false
- verified_by:
    - P5-STARTUP-GATE-UNIT

### Technical Acceptance

- [ ] Follows Research Foundry's layered pattern (routers → services → repositories); no ORM models leak past the service boundary.
- [ ] `service_accounts`/`access_tokens` tables created with `CREATE TABLE IF NOT EXISTS`, idempotent per existing `rbac_store.py` migration discipline.
- [ ] No plaintext secret appears in any persisted row, log line, or audit_event payload (verified by a static-scan test).
- [ ] Constant-time comparison used for all token verification paths.

### Quality Acceptance

- [ ] Unit tests cover: deployment-mode resolver (all preset/override combinations), token issue/verify/revoke/expire, PAT role-ceiling re-check, agent-job identity binding.
- [ ] Integration tests cover: composite auth chain (token hit, token miss→Clerk, token miss→no provider), admin API issue/list/revoke/rotate round-trips, startup fail-closed gate (all four conditions independently).
- [ ] DI-1 audit report reviewed by a human per Mode D (delegation-modes rule) before `status: accepted` is set.
- [ ] Sharing/publish-preview and report-body sensitivity regression pass green under `deployment_mode=multi_user` with a live human session.

### Documentation Acceptance

- [ ] `SERVICE_CONTRACT.md` §14/§17/§18 DI-1 references updated to point at the completed audit artifact.
- [ ] `foundry.yaml` reference docs document `deployment_mode`, `auth.di1_audit_acknowledged`, and `agents.default_service_account_id`.
- [ ] CHANGELOG `[Unreleased]` entry added (feature: deployment-mode presets, service accounts, PATs).
- [ ] Admin API endpoint docs (issue/list/revoke/rotate for both principal types) added alongside existing `admin.py` docstring contract.

---

## 12. Assumptions & Open Questions

### Assumptions

- See §8 Assumptions above (token store location, secret handling, chained middleware, provider-agnostic gate).

### Open Questions

- [x] **Q1**: Does `multi_user` hard-require `auth.provider=clerk`, or does it accept `local_static` as a valid human-auth layer?
  - **A**: Resolved — the gate checks `auth.provider != "none"`, not a specific provider (see Decision log). `local_static`'s existing multi-token model satisfies the requirement for closed-beta multi-user deployments without Clerk procurement.
- [ ] **Q2**: Should service accounts support fine-grained tool/data-scope allowlists (matching P4's per-job agent-permission model) rather than a single role?
  - **A**: Deferred — out of scope for this PRD; a service account gets exactly one role from the existing 5-role model. Revisit if a future feature needs narrower machine-scoping than "researcher" or "viewer" affords.

---

## 13. Appendices & References

### Related Documentation

- Parent PRD: `docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md`
- Release handoff design spec: `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` (§11 Security/Sharing gates, §12 Phase 5 acceptance)
- Gap-closure human brief: `docs/project_plans/human-briefs/public-release-phase5-gap-closure.md` (Mode D inventory this PRD executes)
- Service contract: `docs/projects/research-foundry/SERVICE_CONTRACT.md` (§14 middleware/auth surface, §17 catalog scoping, §18 workspace migration)
- SPIKE: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` (ADR-001 `AuthProvider` port; SEAM-2 agent credential-isolation intent)

### Symbol References

- `ai/symbols-api.json` — auth/admin/rbac router and service symbols (regenerate post-implementation).

### Prior Art

- `services/rbac_store.py` migration pattern (versioned `_ensure_schema`, `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE` seeding).
- `api/auth/adapters/local_static.py` constant-time Bearer-token comparison pattern (reused for the new token store).
- Assertion-ledger DI-1-scoped audit method (backward-trace construction site → `resolve_or_deny` gate) — template for the repo-wide DI-1 audit.

---

## Implementation

### Phased Approach (capability-area grouped)

**Phase 1: Deployment-Mode Presets**
- `deployment_mode` config key + resolver (`config.py`), `rf serve --mode` flag, preset composition of the 5 existing knobs, `single_user` regression test (byte-identical to pre-feature default).
- Tasks:
  - [ ] Add `Config.deployment_mode()` resolver + `deployment_mode_validate()` fail-closed gate stub (DI-1 check wired in Phase 4).
  - [ ] Add `rf serve --mode` CLI flag; wire into existing `--auth-mode`/`--bind-host` resolution path.
  - [ ] Regression test: `single_user` resolved config == pre-feature default resolved config.

**Phase 2: Non-Human Principal Store + Auth Resolution**
- `service_accounts` + `access_tokens` tables in `rbac_store.py`; `token_service.py` (new) for issue/verify/revoke/expire with hash-at-rest and constant-time compare; `AuthProviderMiddleware` composite-chain change; `agent_job_service.py` execution-identity binding under `multi_user`.
- Tasks:
  - [ ] `rbac_store.py`: add tables + CRUD helpers (`create_service_account`, `create_access_token`, `verify_access_token`, `revoke_token`, `list_tokens`).
  - [ ] `token_service.py`: opaque-secret generation, hashing, prefix-lookup verification, PAT role-ceiling re-check.
  - [ ] `AuthProviderMiddleware`: token-store-first lookup, fall through to configured provider on miss.
  - [ ] `agent_job_service.py`: resolve execution identity from `agents.default_service_account_id` under `multi_user`; audit both triggering + executing identity.

**Phase 3: Admin API**
- New routes on `api/routers/admin.py`: service-account and PAT issue/list/revoke/rotate, `deployment-mode-status`.
- Tasks:
  - [ ] `POST/GET /api/admin/service-accounts`, `DELETE .../{id}`, `POST .../{id}/tokens` (rotate).
  - [ ] `POST/GET /api/admin/pats`, `DELETE /api/admin/pats/{id}` (self-scoped + admin-scoped).
  - [ ] `GET /api/admin/deployment-mode-status`.
  - [ ] Audit-log wiring for all mutation routes.

**Phase 4: DI-1 Audit + Enforcement Flip**
- Repo-wide full-surface workspace-scoping audit (Mode D — human-reviewed per delegation-modes rule); remediate findings; wire `auth.di1_audit_acknowledged` + artifact-status check into Phase 1's gate stub.
- Tasks:
  - [ ] Backward-trace every `AuthIdentity`/`workspace_id` construction site to its enforcement gate, repo-wide (extend the assertion-ledger DI-1-scoped method).
  - [ ] Produce `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`; human review of scope-boundary statement (Mode D) before `status: accepted`.
  - [ ] Remediate any findings; update `SERVICE_CONTRACT.md` §14/§17/§18 references.
  - [ ] Wire the two-part gate (`auth.di1_audit_acknowledged` + artifact `status: accepted`) into `deployment_mode_validate()`.
  - [ ] Regression pass: sharing/publish-preview + report-body sensitivity fail-closed under `multi_user` with a live session.

**Phase 5: Admin UI**
- `ServiceAccountsPanel.tsx`, `PersonalAccessTokensPanel.tsx`, `AuthContext.tsx` principal-type extension, `RoleAssignmentPanel.tsx` integration.
- Tasks:
  - [ ] `ServiceAccountsPanel.tsx`: issue (name+role) / list / revoke / rotate, one-time-secret display UX.
  - [ ] `PersonalAccessTokensPanel.tsx`: self-issue (role ≤ own role) / list / revoke.
  - [ ] `AuthContext.tsx`: expose `principalType`.
  - [ ] Accessibility pass (WCAG 2.1 AA) matching existing `AdminSettings` baseline.

**Phase 6: Testing & Docs**
- Full unit/integration coverage per §11 Quality Acceptance; CHANGELOG; `foundry.yaml` reference docs; SERVICE_CONTRACT.md updates.
- Tasks:
  - [ ] Unit + integration test suite (see §11).
  - [ ] E2E smoke: admin UI issue→revoke round-trip against a live API.
  - [ ] CHANGELOG `[Unreleased]` entry.
  - [ ] Docs: `foundry.yaml` reference, admin API endpoint docs, `SERVICE_CONTRACT.md` DI-1 reference updates.

### Epics & User Stories Backlog

| Story ID | Short Name | Description | Acceptance Criteria | Estimate |
|----------|-----------|-------------|-------------------|----------|
| ACT-101 | Deployment-mode resolver | Add `deployment_mode` config key + resolver, preset composition | FR-1, FR-2, FR-3 | 3 |
| ACT-102 | `--mode` CLI flag + startup gate stub | `rf serve --mode`; fail-closed gate skeleton (DI-1 wired later) | FR-4 (partial), FR-5 | 2 |
| ACT-201 | Token store schema | `service_accounts` + `access_tokens` tables in `rbac_store.py` | FR-6 | 3 |
| ACT-202 | Token issue/verify/revoke service | `token_service.py`, hash-at-rest, constant-time compare, expiry | FR-7, FR-8, FR-9, FR-10 | 5 |
| ACT-203 | Composite auth chain | `AuthProviderMiddleware` token-store-first resolution | FR-11 | 3 |
| ACT-204 | Agent-job identity binding | `agent_job_service.py` service-account execution identity under `multi_user` | FR-12 | 3 |
| ACT-301 | Admin API — service accounts | Issue/list/revoke/rotate routes | FR-15 (service-account subset) | 3 |
| ACT-302 | Admin API — PATs | Issue/list/revoke routes, self+admin scoping | FR-15 (PAT subset) | 3 |
| ACT-303 | Admin API — deployment-mode-status + audit wiring | Status route + audit_event logging for all mutations | FR-15 (status), FR-17 | 2 |
| ACT-401 | DI-1 full-surface audit | Repo-wide backward-trace, findings + remediation | FR-14 | 8 |
| ACT-402 | DI-1 gate wiring | `auth.di1_audit_acknowledged` + artifact-status check in `deployment_mode_validate()` | FR-4, FR-13 | 2 |
| ACT-403 | Sharing/sensitivity regression pass | Re-verify §18 gates under `multi_user` live session | FR-18 | 3 |
| ACT-501 | Admin UI — service accounts panel | `ServiceAccountsPanel.tsx` | FR-16 (service-account subset) | 3 |
| ACT-502 | Admin UI — PATs panel + auth-context | `PersonalAccessTokensPanel.tsx`, `AuthContext.tsx` principalType | FR-16 (PAT subset) | 3 |
| ACT-601 | Test suite + docs | Full coverage per §11, CHANGELOG, foundry.yaml docs | §11 Quality/Doc Acceptance | 5 |

---

**Progress Tracking:**

See progress tracking (once implementation plan exists): `.claude/progress/public-multiuser-release-activation/all-phases-progress.md`
