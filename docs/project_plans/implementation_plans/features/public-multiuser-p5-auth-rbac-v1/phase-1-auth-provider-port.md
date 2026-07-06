---
title: "Phase 1: Auth-Provider Port + local_static + Durable RBAC Store"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: v1
phase: 1
phase_title: "Auth-Provider Port + local_static + Durable RBAC Store"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria: ["None — first phase"]
exit_criteria:
  - "Provider swap works via config"
  - "AuthIdentity flows into request.state"
  - "Durable store survives a catalog.db rebuild (test)"
  - "task-completion-validator sign-off"
related_documents:
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: ["ADR-001 (see spike_ref — no standalone ADR file; decision retained in SPIKE + PRD)"]
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces: []
seam_tasks: []
owner: null
contributors: [backend-architect, data-layer-expert]
priority: high
risk_level: high
category: "product-planning"
tags: [phase-plan, implementation, auth, rbac, mode-d, must-stay, durable-store]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/auth/__init__.py
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/api/auth/adapters/__init__.py
  - src/research_foundry/api/auth/adapters/local_static.py
  - src/research_foundry/api/auth/adapters/oidc.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/paths.py
  - src/research_foundry/api/middleware/auth.py
  - src/research_foundry/api/app.py
  - src/research_foundry/config.py
  - foundry.yaml
  - tests/test_serve_auth.py
---

# Phase 1: Auth-Provider Port + local_static + Durable RBAC Store

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~3-4 days
**Effort**: 6 story points
**Dependencies**: None — first phase of P5 (P5.1 in the parent decisions block)
**Team Members**: `backend-architect` (Protocol/registry, local_static, oidc seam, wiring), `data-layer-expert` (durable RBAC store) — both primary, no secondary

---

> **MUST-STAY — Mode D (auth core). No ICA/Codex offload for any task in this phase.**
> Every task below stays on the Claude subscription (sonnet, extended effort by default). This is
> the P5 auth foundation every later phase (RBAC enforcement, workspace isolation, Clerk, audit,
> sharing) composes on top of — a defect here propagates everywhere. Per
> `.claude/skills/planning/references/multi-model-guidance.md` and the parent decisions block §6,
> P5.1–P5.4 are explicitly excluded from ICA Sonnet 4.6 / Codex offload; only P5.5/P5.7/P5.8
> (bounded, contract-clear work, behind a `task-completion-validator` gate) are offload-eligible.

> **Not a SPIKE Mode-D human-approval gate.** This phase does not enforce RBAC, does not migrate
> existing catalog/draft records, and does not touch Clerk — so none of the three SPIKE Mode-D
> sign-off gates (workspace-migration approval, RBAC-before-exposure sign-off, Clerk-secrets
> sign-off) apply here. Those fire at P5.3, P5.2 (end-of-phase, before exposure), and P5.4
> respectively. Quality gate for P5.1 is `task-completion-validator` only — see Quality Gates below.
> **Escalation rule**: if implementation work here starts to enforce RBAC on a route or backfill
> `workspace_id` on an existing record, STOP — that is P5.2/P5.3 scope and does require a human
> gate. Do not silently expand this phase's boundary (delegation-modes.md invariant 3).

---

## Phase Overview

This phase ships the `AuthProvider` **port** (ADR-001) that every later P5 phase builds on: a
`Protocol` + registry mirroring the existing `adapters/base.py` idiom, a provider-neutral
`AuthIdentity{user_id, workspace_id, roles}`, the `local_static` default adapter (generalizing
today's single-shared-bearer `TokenAuthMiddleware` into a multi-token → role mapping per D3), a
**new durable store** at `<workspace>/.rf_state/rbac.db` holding `users`/`workspaces`/
`memberships`/`roles` state (D2 — never `catalog.db`, which is disposable and drop-rebuilds on a
`PRAGMA user_version` mismatch), `foundry.yaml: auth.provider` config wiring, and a Protocol-only
seam for the future `oidc`/BYO adapter (FU-2, concrete implementation deferred).

No RBAC enforcement, no workspace-isolation migration, and no Clerk adapter land in this phase —
those are P5.2, P5.3, and P5.4 respectively. This phase's job is exactly: identity resolves,
flows into `request.state`, and survives a cache rebuild.

### Goals

- `AuthProvider` Protocol + registry at `api/auth/provider.py`, structurally identical to
  `adapters/base.py`'s `Protocol` + `module_available()`-style capability probe + registry
  (`register()`/`get_adapter()`) idiom — see FR-1.
- `local_static` (DEFAULT) generalizes `TokenAuthMiddleware` (`api/middleware/auth.py`) to a
  multi-token → `{user_id, workspace_id, roles}` mapping, preserving the existing
  `hmac.compare_digest` constant-time-comparison discipline per token — see FR-2, D3.
- New durable RBAC store (`services/rbac_store.py`, physically separate file from `catalog.db`)
  bootstraps `users`/`workspaces`/`memberships`/`roles` tables — see FR-8 (schema only; audit_event
  table itself is P5.5), D2.
- `foundry.yaml: auth.provider` (`none|local_static|clerk|oidc`) selects the provider at
  `create_app` time; route/RBAC code never branches on provider identity — see FR-5.
- Define (Protocol-conformance stub only) the `oidc`/BYO adapter seam — see FR-4, FU-2.
- Preserve all three existing security invariants: `auth_mode="none"` (now: `auth.provider="none"`)
  adds zero middleware; 401s stay generic; the no-existence-leak convention is untouched (still a
  route-layer decision over `request.state.identity`, not altered by this phase).

### Architecture Focus

- **Layer**: API (middleware/dependency resolution) + Service (durable store bootstrap) — this
  phase does not touch routers' business logic, only the identity-resolution substrate underneath
  them.
- **Pattern mirrored**: `src/research_foundry/adapters/base.py`'s `Protocol` + `runtime_checkable`
  + `module_available()` capability probe + module-level `_REGISTRY` dict + `register()`/
  `get_adapter()` free functions. `AuthProvider`/`get_provider()`/`register_provider()` should be
  structurally identical, not a bespoke shape (PRD Technical Acceptance).
- **Durability boundary**: `catalog_service.py`'s sqlite bootstrap (`_connect` at
  `catalog_service.py:251-258`, `_ensure_schema`/`_create_schema`/`_drop_schema` at
  `catalog_service.py:218-241`, path resolved via `FoundryPaths.rf_cache`/`catalog_db` in
  `paths.py:140-151`) is the **shape** to mirror (connection setup, `row_factory`, DDL-list
  pattern) — but explicitly **not** the drop-on-version-mismatch **policy**. See AUTH-103 below;
  this distinction is this phase's single most important gotcha.

---

## Task Breakdown

### Epic: Auth-Provider Port (P5.1)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|----------------------|-------|--------|--------------|
| AUTH-101 | AuthProvider Protocol + registry | `api/auth/provider.py`: `AuthIdentity` dataclass, `AuthProvider` Protocol, `register_provider()`/`get_provider(name)` | FR-1; structurally mirrors `adapters/base.py` | 1 | backend-architect | sonnet | extended | None |
| AUTH-103 | Durable RBAC store bootstrap | `services/rbac_store.py`: `users`/`workspaces`/`memberships`/`roles` tables at `<workspace>/.rf_state/rbac.db`; additive-only schema versioning | FR-8 (schema only), D2 | 1.5 | data-layer-expert | sonnet | extended | None (parallel with AUTH-101) |
| AUTH-102 | local_static adapter | Multi-token → `{user_id, workspace_id, roles}` mapping, config-driven; constant-time comparison preserved per token; upserts into rbac_store | FR-2, D3 | 1 | backend-architect | sonnet | extended | AUTH-101, AUTH-103 |
| AUTH-104 | foundry.yaml + config.py + app.py wiring | `auth.provider` config surface; `create_app` resolves middleware from the registry; preserve `auth_mode="none"` no-op invariant | FR-5 | 1 | backend-architect | sonnet | extended | AUTH-101, AUTH-102, AUTH-103 |
| AUTH-105 | oidc/BYO adapter seam (stub) | Protocol-conformance stub in `api/auth/adapters/oidc.py`; `available()` returns `False`; no verification logic | FR-4, FU-2 | 0.5 | backend-architect | sonnet | adaptive | AUTH-101 |
| AUTH-900 | AC: FE handles missing/absent AuthIdentity | Backend contract: `request.state` carries no `identity` (or explicit `None`) when `auth.provider="none"`; never a fabricated/default `AuthIdentity` | R-P2 resilience AC (PRD §11 FR-2 backend-field-resilience bullet 1) | 0.5 | backend-architect | sonnet | extended | AUTH-104 |
| AUTH-106 | Tests: provider-parametrized + rebuild-survival | Extend `tests/test_serve_auth.py`: provider-parametrized auth-header matrix, `auth.provider="none"` no-middleware assertion, rbac.db survives `catalog_service.rebuild_schema()` | Exit criteria 1-3 | 0.5 | backend-architect, data-layer-expert | sonnet | extended | AUTH-101, AUTH-102, AUTH-103, AUTH-104, AUTH-105, AUTH-900 |

**Total**: 6 points.

**Task ID convention note**: `AUTH-9xx` is reserved for R-P2-generated cross-phase resilience ACs
(auto-added when a phase introduces a new optional backend field) that a later phase references by
ID. `AUTH-900` is fixed by contract with the Phase 8 (frontend) phase file being authored in
parallel — **do not renumber it**.

---

## Detailed Task Specifications

### Task AUTH-101: AuthProvider Protocol + registry

**Estimate**: 1 point
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: None
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

**Description**:
Create `src/research_foundry/api/auth/provider.py` with:
- `AuthIdentity` (frozen dataclass or equivalent): `user_id: str`, `workspace_id: str`,
  `roles: tuple[str, ...]`.
- `AuthProvider` (`@runtime_checkable Protocol`): `id: str`; `authenticate(request: Request) ->
  AuthIdentity | None`; `available() -> bool` (mirrors `adapters/base.py`'s capability-probe shape —
  for `local_static` this is always `True`; for `clerk`/`oidc` it will later gate on outbound
  connectivity/config presence, but the Protocol member must exist now so P5.4 doesn't need to
  widen the interface).
- Module-level `_REGISTRY: dict[str, AuthProvider]`, `register_provider(provider) -> AuthProvider`,
  `get_provider(name: str) -> AuthProvider | None`, `all_providers() -> dict[str, AuthProvider]` —
  same shape as `adapters/base.py`'s `register`/`get_adapter`/`all_adapters`.

**Acceptance Criteria**:
- [ ] `AuthProvider` Protocol is `@runtime_checkable`; any adapter implementing it passes
      `isinstance(x, AuthProvider)`.
- [ ] Registry functions are idempotent (`register_provider` re-registering the same `id` replaces,
      does not duplicate or error).
- [ ] `AuthIdentity.roles` is a `tuple`, never a mutable `list`, to prevent downstream aliasing bugs
      once RBAC (P5.2) starts comparing/checking role membership.
- [ ] Zero references to a specific provider (`clerk`, `local_static`) anywhere in this file — the
      Protocol is provider-neutral by construction.

**Implementation Notes**:
- Mirror `adapters/base.py`'s `module_available()` helper if provider `available()` checks need an
  import-probe pattern (e.g., `clerk`/`oidc` checking for `PyJWT`/`cryptography` presence later);
  don't invent a second capability-probe convention.
- Do not import `local_static.py`/`oidc.py`/`clerk.py` from `provider.py` — adapters import and
  self-register against the Protocol module, not the reverse (avoids a circular-import surface).

**Files Involved**:
- `src/research_foundry/api/auth/__init__.py` - new, empty package marker
- `src/research_foundry/api/auth/provider.py` - new, Protocol + registry + `AuthIdentity`

---

### Task AUTH-103: Durable RBAC store bootstrap

**Estimate**: 1.5 points
**Assigned Subagent(s)**: data-layer-expert
**Model**: sonnet
**Effort**: extended
**Dependencies**: None (parallel with AUTH-101 — no code dependency; role-name vocabulary is
documented in the PRD FR-6, not sourced from `provider.py`)
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

**Description**:
Create `src/research_foundry/services/rbac_store.py`, a new durable sqlite store, physically
independent of `catalog.db`.

**Path resolution** (extend `paths.py`, mirroring the existing `rf_cache`/`catalog_db` pair at
`paths.py:140-151`):
- Add `FoundryPaths.rf_state` → `self.root / ".rf_state"` (sibling to `rf_cache`, at the workspace
  root, not nested under it — the two directories signal disposable-vs-durable at a glance).
- Add `FoundryPaths.rbac_db` → `self.rf_state / "rbac.db"`.

**Schema** (`users`, `workspaces`, `memberships`, `roles` — D2):
- `workspaces(id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)`
- `users(id TEXT PRIMARY KEY, display_name TEXT, created_at TEXT NOT NULL)` — provider-neutral;
  Clerk/OIDC-sourced identities (P5.4) populate this same table, not a parallel one.
- `roles(name TEXT PRIMARY KEY, description TEXT)` — seeded with the 5 canonical role names
  (`owner`, `admin`, `researcher`, `reviewer`, `viewer`) from PRD FR-6. This phase only seeds the
  lookup table; the capability matrix (which role can do what) is P5.2's job — do not encode
  permissions here.
- `memberships(user_id TEXT NOT NULL, workspace_id TEXT NOT NULL, role TEXT NOT NULL REFERENCES
  roles(name), created_at TEXT NOT NULL, PRIMARY KEY (user_id, workspace_id))` — one role per user
  per workspace (no PRD signal for multi-role-per-workspace; flag as an open question for P5.2 if
  this proves too narrow).

**Bootstrap function shape** (mirror `catalog_service.py`'s connection/DDL pattern, NOT its
version-mismatch policy — see the Gotcha below):
- `_connect(paths) -> sqlite3.Connection`: `paths.rf_state.mkdir(parents=True, exist_ok=True)`,
  `sqlite3.connect(str(paths.rbac_db), isolation_level=None)`, `row_factory = sqlite3.Row`.
- `_ensure_schema(conn)`: read `PRAGMA user_version`; run `CREATE TABLE IF NOT EXISTS` for all 4
  tables (idempotent, additive) regardless of version; **only** bump `PRAGMA user_version` forward
  when a real additive migration (new column/table) has been applied — never drop-and-recreate.

**Acceptance Criteria**:
- [ ] `rbac.db` is created under `<workspace>/.rf_state/`, never under `.rf_cache/` or inside
      `catalog.db`.
- [ ] Calling the bootstrap function twice in a row (simulating two app starts) does not lose any
      previously-inserted row (idempotent `CREATE TABLE IF NOT EXISTS`, no `DROP TABLE` anywhere in
      this module).
- [ ] `roles` table is seeded exactly once with the 5 canonical names; re-running the seed step is
      a no-op (`INSERT OR IGNORE` or equivalent), not a duplicate-row error.
- [ ] No function in `rbac_store.py` is named or shaped like `catalog_service.py`'s
      `_drop_schema`/`rebuild_schema` — that destructive-rebuild capability must not exist for this
      store at all in this phase.

**Implementation Notes**:
- **Gotcha (flag prominently in code review)**: `catalog_service.py`'s `_ensure_schema` (lines
  234-241) calls `_drop_schema(conn)` then recreates whenever `PRAGMA user_version` doesn't match
  `SCHEMA_VERSION` — that policy is correct for a disposable read-model cache but would be a
  **data-loss bug** if copy-pasted into `rbac_store.py`. The entire point of D2 is that this store
  survives a catalog rebuild; it must equally survive its *own* schema evolution without dropping
  rows. Mirror the connection/DDL-list *mechanics* only.
- Use ISO-8601 strings for all `created_at` columns (matches the rest of the codebase's
  JSON/YAML-first convention — avoid sqlite's native datetime ambiguity).
- Do not add foreign-key `ON DELETE CASCADE` from `memberships` to `users`/`workspaces` yet without
  an explicit product decision on what happens to audit rows (P5.5) referencing a deleted user —
  flag as a P5.5 dependency note, not something to resolve here.

**Files Involved**:
- `src/research_foundry/services/rbac_store.py` - new, schema + bootstrap + seed
- `src/research_foundry/paths.py` - add `rf_state`/`rbac_db` properties (mirrors `rf_cache`/
  `catalog_db` at lines 140-151); **not in the PRD's original `files_affected` list** — added here
  because `rbac_store.py` cannot resolve its durable path without it; grounded via direct
  `paths.py` read (2026-07-06).

---

### Task AUTH-102: local_static adapter

**Estimate**: 1 point
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: AUTH-101 (Protocol/`AuthIdentity` shape), AUTH-103 (durable store to upsert into)
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

**Description**:
`src/research_foundry/api/auth/adapters/local_static.py`: generalizes
`TokenAuthMiddleware` (`api/middleware/auth.py`) from a single shared bearer token to a
config-driven multi-token → `AuthIdentity` mapping (D3, FR-2).

Config shape (final field names confirmed during implementation, this is the recommended
shape consistent with FR-2/FR-5/D3):

```yaml
auth:
  provider: local_static   # none | local_static | clerk | oidc
  local_static:
    tokens:
      - token_env: RF_SERVE_TOKEN_ALICE
        user_id: alice
        workspace_id: default
        roles: [owner]
      - token_env: RF_SERVE_TOKEN_BOB
        user_id: bob
        workspace_id: default
        roles: [researcher]
```

Each entry's token *value* is read from the named environment variable at request time (never
stored in `foundry.yaml` itself — same discipline as today's `viewer.auth_token_env`).

On provider registration (app startup), `local_static` upserts its configured
`{user_id, workspace_id, roles}` tuples into `rbac_store.py`'s `users`/`workspaces`/`memberships`
tables (idempotent `INSERT OR IGNORE`/`UPSERT`) so P5.5's audit log and P5.6's admin UI have one
membership source of truth regardless of which provider is active.

**Acceptance Criteria**:
- [ ] `authenticate(request)` compares the supplied bearer token against **every** configured
      token using `hmac.compare_digest` per candidate — no short-circuit dict/hash lookup on the
      raw token value that could reintroduce a timing side-channel (see Implementation Notes).
- [ ] A request with no `Authorization` header or a non-matching token returns `None` (never
      raises); the caller (middleware) is responsible for turning that into a generic 401.
- [ ] A successful match returns an `AuthIdentity` with `roles` as a `tuple`, sourced from the
      matched config entry.
- [ ] Startup upsert into `rbac_store.py` is idempotent — restarting the app with an unchanged
      token config does not duplicate `memberships` rows.
- [ ] No token value ever appears in a log line, exception message, or stack trace (same
      discipline as `middleware/auth.py`'s existing docstring invariants).

**Implementation Notes**:
- **Security nuance**: the existing single-token middleware safely uses one
  `hmac.compare_digest(supplied, expected)` call. Generalizing to N tokens naively as
  `if supplied in {t.value for t in tokens}` uses Python's hash-based set/dict lookup, which is
  *not* the same constant-time guarantee as `compare_digest` (hash computation and early
  bucket-match can vary with input). Iterate all configured tokens and call
  `hmac.compare_digest(supplied, candidate)` for each, accumulating a boolean rather than
  returning on first match, to keep the comparison shape uniform regardless of position in the
  list.
- Reuse `middleware/auth.py`'s pattern of reading the *value* from `os.environ` at request time
  (not at adapter construction) so env changes take effect without a restart — same rationale as
  the existing docstring.

**Files Involved**:
- `src/research_foundry/api/auth/adapters/__init__.py` - new, package marker
- `src/research_foundry/api/auth/adapters/local_static.py` - new
- `src/research_foundry/services/rbac_store.py` - consumed (upsert on registration)

---

### Task AUTH-104: foundry.yaml + config.py + app.py wiring

**Estimate**: 1 point
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: AUTH-101, AUTH-102, AUTH-103
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

**Description**:
Wire provider selection end-to-end (FR-5):
- `config.py`: add `FoundryConfig.auth_provider() -> str` (reads `auth.provider`, default
  `"none"`, validated against `{"none", "local_static", "clerk", "oidc"}` the same way
  `_validate_auth_mode` validates today's `viewer.auth_mode`); add an accessor for the
  `auth.local_static.tokens` list.
- `app.py`'s `create_app` (today: lines ~104-109 add `TokenAuthMiddleware` when
  `config.viewer_auth_mode() == "token"`): replace with a registry lookup —
  `provider = get_provider(config.auth_provider())`; if `provider is not None` (i.e., not
  `"none"`), add a single generalized auth middleware parameterized by the resolved `AuthProvider`
  instance. Preserve the exact middleware-ordering comment (auth first/innermost, then IP
  allowlist, then CORS) and the `GET /health` exemption.
- `foundry.yaml`: add the `auth:` block (see AUTH-102's example) with a comment block matching the
  care given to the existing `viewer.sensitivity_threshold` comment (lines 22-38) — explain the 4
  provider values and that `local_static` is the air-gapped default.
- Decide (and document inline) the relationship to today's `viewer.auth_mode`/
  `viewer.auth_token_env` fields: recommend treating `auth.provider` as the new canonical selector
  and folding the old single-token behavior into `auth.local_static.tokens` (a one-entry list is a
  valid config), rather than maintaining two parallel selectors long-term.

**Acceptance Criteria**:
- [ ] `auth.provider: none` (or the field entirely absent) results in **zero** added middleware —
      identical to today's `auth_mode="none"` no-op (invariant preserved, testable via middleware
      stack length/type introspection).
- [ ] `auth.provider: local_static` with a valid token → `request.state.identity` is populated with
      the matching `AuthIdentity`; invalid/missing token → generic 401 (no detail leak about which
      provider or which token failed).
- [ ] No router or service file added/touched in this phase contains an `if provider == "clerk"`
      (or similar) branch — selection happens exactly once, at `create_app`.
- [ ] `foundry.yaml`'s new `auth:` block round-trips through `FoundryConfig` without requiring the
      old `viewer.auth_mode`/`viewer.auth_token_env` fields to also be present.

**Implementation Notes**:
- Keep the generalized middleware thin: it should call `provider.authenticate(request)` and set
  `request.state.identity`, delegating all identity-resolution logic to the provider. Do not grow
  provider-specific conditionals inside the middleware itself.
- If `provider.authenticate()` returns `None`, the middleware returns the same generic 401
  `JSONResponse` shape `middleware/auth.py` uses today — no change to the error envelope.

**Files Involved**:
- `src/research_foundry/config.py` - `auth_provider()` + `local_static` token-list accessor
- `src/research_foundry/api/app.py` - `create_app` registry-based middleware resolution
- `src/research_foundry/api/middleware/auth.py` - generalize `TokenAuthMiddleware` (or add a new
  `AuthProviderMiddleware` wrapping any registered provider — final shape decided during
  implementation, but the single-token class should not survive unchanged once `local_static`
  supersedes it)
- `foundry.yaml` - new `auth:` block

---

### Task AUTH-105: oidc/BYO adapter seam (stub)

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: AUTH-101
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

**Description**:
`src/research_foundry/api/auth/adapters/oidc.py`: a Protocol-conformance stub only (FR-4, FU-2).
`OidcAuthProvider` implements the `AuthProvider` Protocol shape (`id = "oidc"`, `available()`
returns `False` unconditionally, `authenticate()` raises `NotImplementedError` with a message
pointing at FU-2), and is **not** registered by default (registering an unavailable/unimplemented
provider that a config could accidentally select is worse than simply not registering it —
`config.auth_provider()` validation must reject `"oidc"` at config-load time with a clear
"not yet implemented" error until FU-2 lands, rather than allowing selection into a broken state).

**Acceptance Criteria**:
- [ ] `OidcAuthProvider` passes `isinstance(x, AuthProvider)` (real Protocol conformance, not a
      placeholder class with a different shape).
- [ ] Setting `auth.provider: oidc` in `foundry.yaml` today produces a clear, actionable
      config-validation error (not a silent no-op, not a runtime crash mid-request).
- [ ] No behavior change to `local_static` or `none` from this stub's presence.

**Implementation Notes**:
- This is intentionally the smallest task in the phase — resist the temptation to sketch JWKS/OIDC
  discovery logic here; that is out of scope until FU-2 is picked up.

**Files Involved**:
- `src/research_foundry/api/auth/adapters/oidc.py` - new, stub only

---

### Task AUTH-900: AC — FE handles missing/absent AuthIdentity

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: AUTH-104
**started**: null
**completed**: null
**verified_by**: [AUTH-106]
**evidence**: []

> **Cross-phase reference**: This exact task ID (`AUTH-900`) is referenced by name from the Phase 8
> (frontend) phase file of this same plan, as the upstream backend contract its FE resilience task
> depends on. Do not renumber or rename this task.

**Description**:
R-P2 requires an implicit AC whenever a phase introduces a new optional backend field — here, the
new field is `AuthIdentity` itself (absent from `request.state` in `auth.provider="none"` mode).
This task is the **backend half** of that contract; the FE half (rendering no role/workspace
affordance) is Phase 8's job and will cite this task as its dependency.

#### AC AUTH-900: Absent AuthIdentity degrades to today's single-operator behavior
- target_surfaces: []
  <!-- Intentionally empty — this phase is backend-only (ui_touched: false). This AC is a
       forward-looking resilience *contract*, not itself UI-touching; Phase 8's frontend
       auth-context task supplies the target_surfaces (AuthContext.tsx, AppShell.tsx) when it
       consumes this contract. -->
- propagation_contract: >
    When `auth.provider="none"` (or no provider is configured), `create_app` adds no auth
    middleware at all (existing invariant, unchanged) — so `request.state` never gains an
    `identity` attribute in this mode. No route or dependency in this phase fabricates a default/
    stub `AuthIdentity` to fill that gap. Any consumer (a future RBAC dependency in P5.2, or the
    frontend in Phase 8) that reads `getattr(request.state, "identity", None)` must treat the
    missing case as "no identity" — the absence itself *is* the signal, not an error state.
- resilience: >
    A request in `auth.provider="none"` mode behaves identically to today's pre-P5 single-operator
    mode: no 401, no role check, no workspace scoping — this phase does not add any of those yet
    (P5.2/P5.3). The only new invariant is that nothing in this phase's code path ever synthesizes
    a fake `AuthIdentity` to "fill in" the gap.
- visual_evidence_required: false
- verified_by:
    - AUTH-106 (this phase — backend contract test)
    - Phase 8 frontend auth-context task (verifies the FE consumption side — exact task ID set by
      the Phase 8 author; that task must cite `AUTH-900` as its dependency)

**Acceptance Criteria**:
- [ ] Integration test: with `auth.provider` unset (or `"none"`), a request handler that does
      `getattr(request.state, "identity", None)` observes `None` — not an `AuthIdentity` with
      empty/default fields.
- [ ] No new code path in AUTH-101 through AUTH-105 constructs an `AuthIdentity()` with placeholder
      values as a fallback.
- [ ] Documented (docstring or comment on `provider.py`) that "absent identity" is the canonical
      no-auth-configured signal, so P5.2's `require_role` dependency (built next phase) has an
      unambiguous contract to code against.

**Implementation Notes**:
- This task is deliberately small in scope — it is an assertion + a short regression test over
  behavior AUTH-101/104 already produce by construction (no middleware added → no attribute set),
  not new production logic. Do not add a `None`-defaulting `AuthIdentity` factory "just in case";
  the absence of the attribute is the contract.

**Files Involved**:
- `tests/test_serve_auth.py` - new test case asserting `request.state` has no `identity` attribute
  when `auth.provider="none"`
- `src/research_foundry/api/auth/provider.py` - docstring note on the absent-identity contract

---

### Task AUTH-106: Tests — provider-parametrized + rebuild-survival

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect, data-layer-expert
**Model**: sonnet
**Effort**: extended
**Dependencies**: AUTH-101, AUTH-102, AUTH-103, AUTH-104, AUTH-105, AUTH-900
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Extend `tests/test_serve_auth.py` (existing file — do not replace) with:
1. A provider-parametrized matrix over `{none, local_static}` (`oidc` excluded — stub only, no
   auth path to exercise yet) covering: valid token → 200 + identity populated; invalid token →
   401 (generic, no detail leak); missing header → 401; `none` provider → no middleware added at
   all (assert on the app's middleware stack, not just behavior, to catch a future accidental
   regression of invariant 6).
2. The `AUTH-900` absent-identity assertion (see above).
3. A durable-store rebuild-survival test: seed `rbac_store.py` with a workspace/user/membership
   row, call `catalog_service.rebuild_schema(paths)` (the existing disposable-cache
   drop-and-recreate function), then re-open `rbac_store.py` and assert the seeded row is still
   present and untouched — the concrete, executable proof of D2/this phase's exit criterion 3.

**Acceptance Criteria**:
- [ ] All existing `test_serve_auth.py` cases still pass unmodified in intent (token-mode behavior
      preserved under the new `local_static` adapter).
- [ ] New provider-parametrized cases pass for both `none` and `local_static`.
- [ ] Rebuild-survival test fails loudly (not silently) if `rbac_store.py` and `catalog_service.py`
      ever end up sharing a connection/file — this is the regression guard for the Gotcha noted in
      AUTH-103.
- [ ] `pytest tests/test_serve_auth.py` green under `./.venv/bin/python -m pytest` (project memory:
      must run under the project venv, not a pyenv shim).

**Implementation Notes**:
- Follow the existing test file's fixture conventions (temp workspace dirs, `FoundryPaths`
  construction) rather than introducing a new fixture pattern.

**Files Involved**:
- `tests/test_serve_auth.py` - extended with the 3 new test groups above

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Provider swap (`none` → `local_static`) works purely via `foundry.yaml`
      config change, no code edit required at the call site.
- [ ] **Testing**: `tests/test_serve_auth.py` green, including the provider-parametrized matrix and
      the rebuild-survival test (AUTH-106).
- [ ] **Security**: constant-time comparison preserved across all configured tokens (AUTH-102); no
      token value in logs/errors; generic 401s; durable store schema is additive-only (no
      `_drop_schema` equivalent in `rbac_store.py`).
- [ ] **Architecture**: `AuthProvider` Protocol + registry structurally mirrors `adapters/base.py`
      (no bespoke shape).
- [ ] **Documentation**: `foundry.yaml`'s new `auth:` block is commented to the same standard as
      the existing `viewer.sensitivity_threshold` block.
- [ ] **Seam verification**: N/A — `integration_owner: null` (both primary agents are
      backend-specialty roles working on disjoint files — `rbac_store.py` for data-layer-expert,
      everything else for backend-architect — with zero `files_affected` overlap between them, so
      R-P3's seam-task trigger does not fire this phase).
- [ ] **Runtime smoke**: N/A — `ui_touched: false`, no `*.tsx` file in this phase's
      `files_affected`.
- [ ] **Reviewer gate**: `task-completion-validator` sign-off (Mode E — reads the diff + this
      phase's ACs, no edit permissions). **No `karen` pass and no human-approval gate at P5.1** —
      see the MUST-STAY callout above for why.

---

## Integration Points

### External Systems

- None in this phase. `clerk`/`oidc` external dependencies (PyJWT, `cryptography`,
  `@clerk/clerk-react`) are P5.4-only; this phase adds zero new third-party dependencies.

### Internal Systems

- **`adapters/base.py`**: pattern source for `AuthProvider`'s Protocol + registry shape (read-only
  reference, not modified).
- **`catalog_service.py`**: pattern source for `rbac_store.py`'s connection/DDL mechanics
  (read-only reference — the durability policy explicitly diverges, see AUTH-103 Gotcha); also the
  target of the rebuild-survival regression test (`rebuild_schema()` is called, not modified).
- **`api/middleware/auth.py`**: generalized in place (AUTH-104) rather than deleted, so any other
  code path that imports `TokenAuthMiddleware` directly is not silently orphaned — confirm no other
  import sites exist before removing the class, or keep it as a thin deprecated alias if any do.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/api/auth/__init__.py` | New package marker | backend-architect |
| `src/research_foundry/api/auth/provider.py` | `AuthIdentity`, `AuthProvider` Protocol, registry | backend-architect |
| `src/research_foundry/api/auth/adapters/__init__.py` | New package marker | backend-architect |
| `src/research_foundry/api/auth/adapters/local_static.py` | Multi-token→role adapter (default) | backend-architect |
| `src/research_foundry/api/auth/adapters/oidc.py` | Protocol-conformance stub (FU-2 seam) | backend-architect |
| `src/research_foundry/services/rbac_store.py` | Durable users/workspaces/memberships/roles store | data-layer-expert |
| `src/research_foundry/paths.py` | Add `rf_state`/`rbac_db` path properties | data-layer-expert |
| `src/research_foundry/api/middleware/auth.py` | Generalize `TokenAuthMiddleware` → provider-backed | backend-architect |
| `src/research_foundry/api/app.py` | `create_app` registry-based middleware resolution | backend-architect |
| `src/research_foundry/config.py` | `auth_provider()` + `local_static` token accessors | backend-architect |
| `foundry.yaml` | New `auth:` block | backend-architect |
| `tests/test_serve_auth.py` | Extended: provider matrix, AUTH-900, rebuild-survival | backend-architect, data-layer-expert |

---

## Testing Strategy

### Unit Tests

- `AuthProvider` registry: register/get/idempotent-replace, `runtime_checkable` conformance.
- `local_static`: per-candidate `hmac.compare_digest` comparison (no short-circuit hash lookup),
  valid/invalid/missing-token cases, config parsing of the `tokens` list.
- `rbac_store.py`: bootstrap creates all 4 tables idempotently; `roles` seed is exactly 5 rows,
  re-seeding is a no-op; no destructive-drop function exists in the module.
- `oidc.py` stub: Protocol conformance, `available() == False`, config-load rejects
  `auth.provider: oidc` with a clear error.

### Integration Tests

- Full `create_app` → request round-trip for `auth.provider ∈ {none, local_static}` (extends
  `tests/test_serve_auth.py`).
- `auth.provider="none"` → assert zero middleware added (introspect the app's middleware stack,
  not just observed request behavior) — direct regression guard for invariant 6.
- AUTH-900: absent-identity assertion in `none` mode.
- Rebuild-survival: seed `rbac_store.py`, call `catalog_service.rebuild_schema()`, assert
  `rbac_store.py` data intact (D2's core, executable proof).

### E2E Tests (if applicable)

- None in this phase — no frontend/UI surface touched (`ui_touched: false`). Existing `w1`/`w3`
  Playwright specs are unaffected; Phase 8/9 own the new `p5-auth-rbac.spec.ts` E2E coverage.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| `rbac_store.py` accidentally inherits `catalog_service.py`'s drop-on-version-mismatch policy, destroying durable identity state on a future schema tweak | High | AUTH-103 explicitly scopes "mirror the mechanics, not the policy"; code review + AUTH-106's rebuild-survival test act as the regression guard; no `_drop_schema`/`rebuild_schema`-shaped function may exist in `rbac_store.py`. |
| Multi-token generalization (AUTH-102) reintroduces a timing side-channel by using hash/dict lookup instead of per-candidate `hmac.compare_digest` | Medium | Explicit AC + implementation note requiring uniform per-candidate constant-time comparison; flagged in task-completion-validator's review checklist for this phase. |
| `auth_mode="none"` no-middleware invariant regresses while refactoring from a single `if auth_mode == "token"` check to registry-based resolution | High | Direct middleware-stack-introspection test (not just behavioral) in AUTH-106; this is the single most security-relevant invariant carried forward from `middleware/auth.py`'s existing docstring contract. |
| Config schema ambiguity between legacy `viewer.auth_mode`/`viewer.auth_token_env` and new `auth.provider`/`auth.local_static.tokens` causes confusion or a silent double-config state | Medium | AUTH-104 explicitly recommends folding old fields into the new schema (a single-entry `tokens` list) rather than maintaining two parallel selectors; documented inline in `foundry.yaml`'s new comment block. |
| Scope creep into RBAC enforcement or workspace-migration territory during "wiring" work (AUTH-104) | High | Explicit escalation rule stated in the MUST-STAY callout above — stop and flag rather than silently expanding into P5.2/P5.3 scope. |

---

## Success Metrics

- **Completion**: All 7 tasks (AUTH-101 through AUTH-106, including AUTH-900) checked off.
- **Quality**: All Quality Gates passed; `task-completion-validator` sign-off obtained.
- **Security**: 0 timing-side-channel regressions in the token-comparison path; 0 fabricated
  `AuthIdentity` fallbacks anywhere in this phase's code.
- **Durability**: `rbac.db` survives a `catalog_service.rebuild_schema()` call with 100% data
  fidelity (AUTH-106 rebuild-survival test).
- **Testing**: `tests/test_serve_auth.py` green under `./.venv/bin/python -m pytest`.

---

## Notes

### Implementation Approach

Work AUTH-101 (Protocol) and AUTH-103 (durable store) in parallel first — they share no files and
only a documented vocabulary (role names, `AuthIdentity` shape) rather than code. AUTH-102
(local_static) converges both once they land, since it both implements the Protocol and upserts
into the store. AUTH-104 (wiring) is the last integration point before AUTH-105 (trivial stub) and
AUTH-900/AUTH-106 (contract test + full test pass) close out the phase.

### Gotchas

- **`rbac_store.py` must not mirror `catalog_service.py`'s destructive rebuild policy** — see
  AUTH-103's Implementation Notes. This is the single highest-value catch for this phase; get it
  wrong and D2 (the whole reason this phase exists) is silently violated.
- **Constant-time comparison across N tokens** — a naive `token in known_tokens` set/dict lookup
  is not equivalent to `hmac.compare_digest`; see AUTH-102.
- **`paths.py` and the two `__init__.py` files are additive** beyond the PRD's originally-enumerated
  `files_affected` list — confirmed necessary via direct code read of the existing `rf_cache`/
  `catalog_db` pattern (2026-07-06); not a scope-creep signal, just a grounding correction.

### Learnings

*(Capture as phase progresses — none yet, phase not started.)*

### Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
