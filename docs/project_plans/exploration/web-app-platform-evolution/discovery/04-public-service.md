---
doc_type: report
report_category: investigation
title: "Research Foundry Public / Multi-User Service Posture — Discovery"
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
---

# Research Foundry Public / Multi-User Service Posture

Factual inventory of what takes Research Foundry beyond single-operator personal use, and
what still blocks a real shared/multi-tenant deployment. No solutioning — findings only.

## 1. Capability Table

| Capability | Status | Default posture | Key file path(s) |
|---|---|---|---|
| Auth (bearer token / provider registry) | shipped-enforced | `auth.provider=none` (no middleware added; single-operator-trust) | `src/research_foundry/api/middleware/auth.py:132` (`AuthProviderMiddleware`), `src/research_foundry/api/auth/provider.py:70` (registry + `AuthIdentity`), `src/research_foundry/config.py:365` (`auth_provider()`) |
| Auth adapters (local_static / clerk / oidc) | local_static + clerk shipped-enforced; oidc gap (recognised vocab, raises `ValueError`, not implemented) | `none` | `src/research_foundry/api/auth/adapters/local_static.py`, `.../adapters/clerk.py`, `.../adapters/oidc.py`, `config.py:401` (`_IMPLEMENTED_AUTH_PROVIDERS`) |
| RBAC (5-role capability matrix + `require_role`) | shipped-enforced (when `auth.provider != none`); shipped-advisory-passthrough on `provider=none` | enforced only when identity present; `rbac_enforcement=auto` | `src/research_foundry/api/auth/rbac.py:84` (`ROLE_PERMISSIONS`), `:128` (`require_role`), `config.py:513` (`auth_rbac_enforcement`), `:544` (`resolve_rbac_enforced`) |
| RBAC disable toggle (P5.6 T5) | shipped, fail-closed | `auto` | `config.py:30` (`AuthRbacEnforcement` enum), `:576-585` (loopback-only `disabled` gate — raises `ValueError` on non-loopback bind) |
| Workspace isolation (WKSP-304 row-level scoping) | shipped-enforced when armed; shipped-advisory by default | `workspace_isolation_enforcement=auto` → **advisory** while `auth.provider=none` | `src/research_foundry/api/auth/scope.py:56` (`resolve_workspace_isolation_active`), `:113` (`require_workspace_scope`), `config.py:67` (`WorkspaceIsolationEnforcement` enum), `:605` (`workspace_isolation_enforcement()`), `:641` (`resolve_workspace_isolation_enforced`) |
| Workspace isolation scoping-enumeration completeness | **gap** (DI-1 open) | N/A | `.claude/progress/wksp-304-workspace-isolation-enforcement/plan-completion.md:59-63` (deferred hard gate); 2 leaks found post-hoc and fixed in `eba75ab`, but the enumeration method itself is not proven exhaustive |
| Multi-tenant store (shared DB, N workspaces, one deployment) | **deferred / gap** | Isolation today = **separate filesystem roots per deployment**, not row-level multi-tenancy in one store | `.claude/progress/public-multiuser-p5-auth-rbac/plan-completion.md:47` ("Isolation is currently by separate filesystem roots per deployment, not row-level `workspace_id` scoping") |
| Identity threading into service calls | shipped-enforced (post `eba75ab`), previously a leak vector | `identity=None` default = byte-identical pre-WKSP-304 behavior | `src/research_foundry/services/builder_service.py:988` (`create_draft_from_run`), `:1074` (`create_draft_from_collection`), `:455` (`create_draft`), `src/research_foundry/services/catalog_service.py:1518` (`get_item`) |
| Rate limiting (per-identity + per-route) | shipped-enforced | enabled by default; exempt when `auth.provider=none` | `src/research_foundry/api/middleware/rate_limit.py`, `config.py:476` (`auth_rate_limit`) |
| Audit log | shipped | on | `src/research_foundry/services/audit_service.py`, `src/research_foundry/api/routers/audit.py` |
| Sharing (report share tokens) | shipped-enforced (token-is-credential; re-checked for sensitivity) | route-exempt for `GET /api/reports/shares/{token}` only | `src/research_foundry/api/middleware/auth.py:55-59, 168-178`, `src/research_foundry/services/share_store.py` |
| Frontend auth UI (login, admin panels) | shipped (P5.8) | rendered only when `auth.provider != none` | `frontend/runs-viewer/src/auth/AuthContext.tsx`, `frontend/runs-viewer/src/components/AdminSettings/{AuthProviderStatusPanel,RbacStatusPanel,RoleAssignmentPanel,WorkspaceMembersPanel,RateLimitConfigPanel}.tsx` |
| Workspace switcher UI (one identity, multiple workspaces) | **gap** (does not exist) | N/A | no `WorkspaceSwitcher`/`switchWorkspace` symbol found in `frontend/runs-viewer/src` — consistent with the one-token-to-one-workspace `local_static` model |
| Embedded agent jobs (P4) | shipped, feature-flagged off + auth/isolation dependent | `agents.enabled=false` | `config.py:296-327` (`agents_enabled()`); `.claude/progress/public-multiuser-p4-agents/plan-completion.md:61-63` ("Release Constraint (hard)": `openai_agents` must not be enabled for any multi-user-reachable deployment until P5.2+P5.3 are both sealed) |

## 2. Auth Model Detail

- **Bearer-token contract**: `AuthProviderMiddleware` (`api/middleware/auth.py:132`) is only added to the app when `auth.provider != "none"` — a true no-op otherwise (security invariant explicitly documented at `auth.py:17-18, 33`). `GET /health` is always exempt (`auth.py:53, 86, 165`).
- **Identity value object**: `AuthIdentity(user_id, workspace_id, roles: tuple[str, ...])` (`api/auth/provider.py:34-62`), resolved onto `request.state.identity`. Absent-identity (`None`) is the canonical "no auth configured" signal, not an error (`provider.py:8-18`).
- **Config nesting**: auth lives under `foundry.auth` in `foundry.yaml` (canonical, P5.1), superseding the legacy `foundry.viewer.auth_mode`/`auth_token_env` single-token scheme (`config.py:329-363`). `auth.local_static.tokens[]` entries are `{token_env, user_id, workspace_id, roles}` triples — the token *value* always lives in an env var, never inline (`config.py:420-445`, `adapters/local_static.py:5-21`).
- **Node deployment** (per user memory / operator practice): `research-foundry-api.service` runs `local_static` with a single owner-scoped token mirrored to `~/.config/research-foundry/serve.env` as `RF_TOKEN_AGENT`; agents call `Authorization: Bearer $RF_TOKEN_AGENT` against `http://10.42.10.76:7432/api/*`.
- **Providers**: `none` (default, zero middleware), `local_static` (multi-token map, air-gapped/LAN multi-user), `clerk` (JWKS/JWT, **dark-by-default** — requires both `auth.clerk_frontend_api` and `auth.clerk_outbound_internet_enabled=true` explicitly set or `ValueError` at startup, `config.py:406-417`), `oidc` (recognised vocabulary, **not implemented** — raises `ValueError`, `config.py:401-405`).
- **Rate limiting**: `auth.rate_limit` block, per-`(user_id, route)` sliding window, default `60` req/`60`s; `provider=none` deployments are automatically exempt (`config.py:474-509`).

## 3. RBAC Detail

- **5-role capability matrix** (`api/auth/rbac.py:10-29, 84-120`): `owner`/`admin` (full mutation + publish), `researcher` (create/update, no delete/publish), `reviewer` (read-only + comment), `viewer` (zero permissions).
- **`require_role(*allowed_roles)`** (`rbac.py:128-183`) is a FastAPI dependency:
  - `identity is None` → **allow unconditionally** (single-operator-trust; explicit "do NOT raise here" contract, `rbac.py:139-144`).
  - `identity` present, no role intersection → `403 Insufficient role`.
  - Empty `roles=()` → `403` (valid "no role assigned" state, not an error).
- **Global RBAC enforcement flag** — `app.state.rbac_enforced`, resolved once at `create_app` time via `resolve_rbac_enforced(provider, bind_host)` (`config.py:544-601`) and read by every `require_role` call (`rbac.py:161-172`).
- **Fail-closed invariants that must never be weakened**:
  1. `auth.rbac_enforcement=disabled` is **only honoured on a loopback bind** (`127.0.0.1`, `::1`, `localhost`, `127.*`); on any non-loopback `bind_host` (e.g. `0.0.0.0` / LAN IP) `create_app` **refuses to start** with `ValueError` (`config.py:544, 576-585`). You cannot disable RBAC on a public bind.
  2. `AUTO` mode's `require_role` identity-None passthrough is deliberately **not** implemented by making `resolve_rbac_enforced` return `False` for `provider=none` — it always returns `True`, and the identity-None short-circuit inside `require_role` itself is what provides single-operator-trust semantics. This is called out explicitly (`config.py:587-601`) to avoid silently breaking role enforcement if a test fixture or future middleware injects an identity under `provider=none`.
- **CLI/service-direct mutation surface** (`rf ingest`, `rf catalog rebuild`, `rf writeback`) bypasses the HTTP router and `require_role` entirely — classified as *single-operator-trust*, not RBAC-gated (`rbac.py:35-56`).
- **Forward-compat marker**: `agent_job:launch` permission exists in the matrix pre-P4 (`RBAC-FORWARD-COMPAT`, `rbac.py:57-69`) — every P4 `agent_jobs.py` mutation route must carry `Depends(require_role("owner","admin"))` at minimum.

## 4. Workspace Isolation (WKSP-304) Detail

- **Two orthogonal gates**: `auth.rbac_enforcement` (who can act) and top-level `workspace_isolation_enforcement` (whose rows they can see/touch) are structurally parallel `auto|disabled|enabled` enums but deliberately independent — never conflated (`config.py:59-97, 603-625`).
- **`require_workspace_scope(identity, record, ..., resolve_enforcement=None)`** (`api/auth/scope.py:113-222`):
  - `identity is None` is the **literal first statement** — returns `allowed=True, reason="single_operator_trust"` before `resolve_enforcement` is ever read/called (D3 invariant, "Critical, no partial credit"; proven by a named test, `scope.py:19-25`).
  - Exact `workspace_id` match → always allowed, no log.
  - Mismatch/null `workspace_id`, **enforcing**: `allowed=False, reason="workspace_mismatch_denied"` — a `None` record `workspace_id` is treated as a mismatch, never defaulted to allowed.
  - Mismatch/null, **advisory** (default when no resolver passed, or `provider=none`): structured JSON `WARNING` log (`workspace_scope_advisory_mismatch`), still `allowed=True, reason="advisory_mode"`.
- **`resolve_workspace_isolation_enforced(provider, bind_host)`** (`config.py:641-715`) `AUTO` branch differs from RBAC's: it is the **literal provider-keyed truth table** — enforcing when `provider != "none"`, advisory when `provider == "none"` — because (unlike RBAC) there is no separate identity-None short-circuit doing the enforcement decision; the enum resolution itself carries the semantics.
- **Same fail-closed loopback gate** as RBAC: `disabled` is refused on non-loopback binds (`config.py:697-706`).
- **Scoping-enumeration completeness problem (the core finding of this section)**: Phase 3 (query-layer scoping) was signed off as "100% coverage" against an enumerated set of read/create/list/delete paths. End-of-feature (`karen`) review in Phase 6 found the enumeration was **incomplete** — two Mode-D-class cross-workspace leaks in already-merged Phase 4/5 code, not touched by Phase 6 itself:
  1. `create_draft_from_collection` (`builder_service.py:1096` pre-fix) called `catalog_service.get_item(...)` with **no identity** — an unscoped read; a caller in workspace A could seed a draft from a workspace-B `catalog_item_id`.
  2. `create_draft_from_run` / `create_draft_from_collection` (`reports.py:244-254,265-275` → `builder_service.py:988-1038,1064-1092`) never threaded caller identity into the inner `create_draft` call — same failure class as an earlier P5.5b fix on the plain `create_draft` path.
  - **Disposition**: user authorized a *bounded* fix (both named gaps only, commit `eba75ab`) rather than an open-ended re-audit, and explicitly deferred the full-surface completeness audit as **DI-1** — see `.claude/progress/wksp-304-workspace-isolation-enforcement/plan-completion.md:59-63, 73-76` and the plan file's `OQ-4` (`status: resolved-bounded-fix`, pointing at DI-1 for the remainder).
  - **DI-1** = "Full workspace-data-access completeness audit (ALL read/create/list/delete service paths — the enumeration proved unreliable)." Explicitly marked: **"MUST close before any shared-store multi-tenant deploy."** Not urgent today only because enforcement defaults to advisory and is not armed in production.

## 5. Release-State Summary (Public Multi-User Release)

Source spec: `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` (status: `draft`, `maturity: planning`, 2026-07-04) — frames the target ("public, multi-user evidence workspace") and the pre-existing gaps (no tenant/team/user/membership/RBAC model, no shared catalog API, no persisted builder state, no server-managed agent-job model).

| Phase | Scope | Status | Evidence |
|---|---|---|---|
| P0+P1 | Route/IA cleanup + shared evidence catalog read model (SQLite/FTS5, no auth/RBAC tables by design decision D6) | **merged** (PR #1, `1f19379`) | plan frontmatter (`docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md:4`) still reads `status: active` — stale bookkeeping vs. the merged PR; `D6`: "No auth/RBAC/workspace tables in this pass" |
| P2 | Granular Report Audit (paragraph/span-level claim links) | **completed** (PR #2, `8b9d8be`) | `.claude/progress/public-multiuser-release/phase-2-progress.md:7-8` |
| P3 | Report Builder (persisted draft/revision model) | **completed** (PR #3, `cb6af8b`) | `.claude/progress/public-multiuser-release/phase-3-progress.md:7-8`; AAR `docs/project_plans/aars/2026-07-05-public-multiuser-p2p3-execution.md` — notes R2 pre-merge caught a path-traversal primitive and a fail-open sensitivity gate before either could ship |
| P4 | Embedded Agent Research (job model, provider adapters, credential firewall) | **completed**, merged to main disabled-by-default | `.claude/progress/public-multiuser-p4-agents/plan-completion.md`; `agents.enabled=false` hard release constraint; real-provider-key Gates #2/#3 explicitly deferred (operational, need live keys) |
| P5 | Auth/RBAC/Isolation/Audit Hardening (9 sub-phases) | **completed**, `karen APPROVED`, merged to **local** `main`, **not pushed** | `.claude/progress/public-multiuser-p5-auth-rbac/plan-completion.md:9,14,20`; 17 genuine defects caught by adversarial Codex review across the plan and fixed pre-merge |
| WKSP-304 | Row-level workspace isolation enforcement (post-P5 follow-up, tracked as its own Tier 2 plan) | **completed**, `karen APPROVED` (after one remediation cycle) | `.claude/progress/wksp-304-workspace-isolation-enforcement/plan-completion.md`; DI-1 deferred as described in §4 |

Per user memory (`public-multiuser-release-plan.md` note): "P0–P5 ALL COMPLETE, pushed to origin 2026-07-08." Git log confirms P5 code landed on local `main` and WKSP-304 landed on top of it (12 further commits, `2208927`..`c8f1de6`); P5's own completion report says explicitly **not pushed** at P5-completion time, so the push-to-origin happened in a later, separate step not captured in these progress files.

## 6. Hard Gates Before Public Multi-Tenant Deploy

1. **DI-1 — full workspace-data-access completeness audit.** Every read/create/list/delete service path across every service, re-enumerated from scratch (the prior "100% coverage" claim was falsified post-hoc). Explicitly named as a hard pre-deploy gate in two places: `.claude/progress/wksp-304-workspace-isolation-enforcement/plan-completion.md:61-63,75` and the WKSP-304 plan's `OQ-4`/Deferred-Items section.
2. **Flip `workspace_isolation_enforcement` from `auto`/advisory to armed enforcement** for any deployment that is not single-operator-trust — currently the *default* behavior on `provider=none` is advisory-only (log, don't deny).
3. **Move off "separate filesystem roots per deployment" as the actual isolation mechanism.** P5's own completion report names this directly: today's real-world tenant boundary is one filesystem root per deployment, not row-level scoping in a single shared store — WKSP-304 makes row-level scoping *available* but does not, by itself, constitute a shared-store multi-tenant deployment.
4. **Gate #2/#3 for P4 embedded agents** (real-provider-key run + redaction verification on a real trace) remain operationally deferred — required before `agents.enabled=true` is safe outside loopback/single-operator mode, and `openai_agents`/live tool-loop is explicitly blocked from any multi-user-reachable deployment until P5.2 (RBAC) + P5.3 (isolation) are both sealed (`.claude/progress/public-multiuser-p4-agents/plan-completion.md:52-63`).
5. **OIDC/BYO adapter** is design-spec-only (`idea` maturity) — not a hard gate for `local_static`/`clerk`-only deployments, but a gap for any customer requiring their own IdP.
6. **Live E2E against a real Clerk tenant / real RF API** is unrun — P5 validation is 284 backend tests + 57/57 regression + static E2E (32 passed/4 skipped); no live-mode E2E exists yet.
7. **Push-then-redeploy discipline**: per project git-workflow rule, push to origin and any outward-facing deploy are explicit, separate, human-gated steps — not automatic on plan completion.

## 7. Implications for the Web App (UI/UX Surfaces)

What a genuine multi-user product implies, checked against what already exists in `frontend/runs-viewer/`:

**Already exists (P5.8, gated on `auth.provider != none`):**
- Login UI for both providers — Clerk-hosted sign-in and a local username/password form posting to `POST /api/auth/login` (`frontend/runs-viewer/src/auth/AuthContext.tsx:6-17`).
- Role/workspace-aware chrome that renders nothing extra under `auth_mode=none` (AC-5a, `AuthContext.tsx:17,219,369`).
- Admin panels: `AuthProviderStatusPanel`, `RbacStatusPanel`, `RoleAssignmentPanel`, `WorkspaceMembersPanel`, `RateLimitConfigPanel` (`frontend/runs-viewer/src/components/AdminSettings/`).
- `WorkspaceMembersPanel` lists members + roles **within the caller's own workspace** (`GET /api/admin/workspace`) — this is membership/role visibility, not cross-workspace administration.

**Does not exist yet (genuine gaps for a real multi-tenant product):**
- **Workspace switcher.** No `WorkspaceSwitcher` component or `switchWorkspace`/`active_workspace` concept anywhere in the frontend. This is consistent with the backend model: a `local_static` token maps to exactly one `(user_id, workspace_id, roles)` triple — there is no notion of one identity belonging to, or switching between, multiple workspaces.
- **Cross-workspace/tenant admin surface** (e.g. list all workspaces, create a new workspace, transfer ownership) — `WorkspaceMembersPanel` only ever shows the caller's own workspace.
- **Sharing/permissions UI beyond report share tokens.** Report-level share links exist (`share_store.py`) and are token-authenticated at the API layer, but there's no UI for inviting a specific user into a workspace, setting per-item permissions, or auditing who a report was shared with.
- **Self-service signup/invite flow.** `local_static` tokens are provisioned by editing `foundry.yaml`+env vars (operator action); Clerk delegates signup to Clerk's hosted UI. Neither path has an in-app "invite a teammate" flow.
- **DI-1-driven trust signal.** Once the completeness audit lands, the product may need to surface *which* surfaces are proven workspace-scoped vs. advisory — there's no current UI concept for that distinction (it lives only in backend log lines today).
- **Live wiring for the deployed runs-viewer.** Per P5 plan-completion deferrals, the LAN-deployed static SPA (`:3030`) is not yet wired to the live RF API (`:7432`) — it remains a static, redaction-at-export snapshot; live loopback mode requires a separate rebuild with `VITE_RUNS_FRONTEND_LOOPBACK_API=true` + token wiring. Any multi-user web app work should treat "live API-backed frontend" as a prerequisite, not an assumption.
