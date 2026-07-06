---
schema_version: 2
doc_type: phase_plan
title: "Phase 4: Clerk Adapter + OIDC Seam Cross-Check + Minimal FE Login Hook"
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
phase: 4
phase_title: "P5.4 — Clerk Adapter + OIDC Seam Cross-Check + Minimal FE Login Hook"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.1 AuthProvider Protocol + registry merged"
exit_criteria:
  - "Clerk verify unit-tested against JWKS fixture"
  - "local_static path unaffected by Clerk code path"
  - "CLERK-900 seam test passes"
  - "Human gate #3 signed off before any real-secrets activation"
  - "task-completion-validator sign-off"
related_documents:
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
  - "ADR-001 (AuthProvider port, Clerk-first + local/BYO seam — SPIKE public-multiuser-p4p5-foundations)"
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: backend-architect
ui_touched: true
target_surfaces:
  - src/research_foundry/api/auth/adapters/clerk.py
  - frontend/runs-viewer/src/auth/useClerkAuth.ts
seam_tasks:
  - CLERK-900
owner: nick
contributors: [backend-architect, ui-engineer-enhanced]
priority: high
risk_level: high
category: "product-planning"
tags: [implementation, planning, phases, auth, clerk, rbac, security, public-multiuser, phase-5, mode-d]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/auth/adapters/clerk.py
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/config.py
  - foundry.yaml
  - frontend/runs-viewer/src/auth/useClerkAuth.ts
  - tests/unit/test_clerk_adapter.py
  - tests/unit/test_auth_provider_protocol_conformance.py
  - tests/fixtures/auth/clerk_jwks_fixture.json
  - frontend/runs-viewer/src/auth/useClerkAuth.test.ts
---

# Phase 4: Clerk Adapter + OIDC Seam Cross-Check + Minimal FE Login Hook

[← Back to parent plan](../public-multiuser-p5-auth-rbac-v1.md)

**Parent Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md`
**Duration**: ~2–3 days
**Effort**: 5 story points
**Dependencies**: P5.1 (AuthProvider Protocol + registry) merged. Runs in parallel with P5.5 (audit)
and P5.7 (deferred sensitivity) per the decisions block's dependency map — none of the three share
files.
**Team Members**: backend-architect (primary, integration owner), ui-engineer-enhanced (secondary,
minimal FE hook)

**Column conventions**: `Estimate` = story points. `Model`: `sonnet` (this phase is MUST-stay Claude
throughout — see Mode & Agent Routing below). `Effort`: `adaptive|extended` per
`.claude/skills/planning/references/multi-model-guidance.md`. `Provider`: `claude` for every task in
this phase — no exceptions.

---

## Phase Overview

This phase ships the **opt-in, dark-by-default** `ClerkAuthProvider` adapter: a pure-Python JWKS
verification path (PyJWT + `cryptography`, no Node SDK, no self-hosted Clerk instance — SPIKE F1/F5)
that maps Clerk Organizations roles 1:1 onto RF's 5 roles, plus a config-flag gate that keeps the
provider inert until an operator both procures a Clerk plan (FU-3, an operator action, not an
engineering task) and flips `auth.provider: clerk` in `foundry.yaml`. It also confirms the `oidc`
seam Protocol stub (landed in P5.1) is satisfied identically by `clerk`, and ships the minimal
frontend contract hook (`useClerkAuth.ts`) that Phase 8 (P5.8) will wrap inside the full
`AuthContext.tsx` abstraction — this phase does **not** build that abstraction.

### Goals

- Ship `ClerkAuthProvider.authenticate()`: JWT → JWKS-verified `AuthIdentity`, networkless after
  first JWKS fetch (FR-3, SPIKE F1).
- Map Clerk Organizations roles 1:1 onto RF's 5 roles (owner/admin/researcher/reviewer/viewer)
  (FR-3, SPIKE F3 — custom roles require a paid Clerk plan in production; this phase's role-mapping
  logic is provider-agnostic of that constraint and is fully testable against a dev/free-tier or
  fixture JWKS).
- Wire the config flag so `clerk` stays dark-by-default: no behavior change to `local_static` or
  `auth_mode=none` unless an operator explicitly sets `auth.provider: clerk` (FR-3 Note; SPIKE
  verdict "never default or sole").
- Confirm `clerk` and the existing `oidc` seam stub (P5.1) both satisfy the same `AuthProvider`
  Protocol (FR-4) — cross-check only, no new `oidc` implementation work.
- Ship `useClerkAuth.ts`: the minimal hook proving the Clerk login round-trip (browser session token
  → backend JWKS verify → `AuthIdentity`) that P5.8 will consume, not the full auth-context UI.
- Land the mandatory seam task `CLERK-900` proving the FE↔BE contract works end-to-end against a
  JWKS test fixture.

### Architecture Focus

- **Layer**: API (auth adapter) + minimal Frontend (contract hook). No Repository/Service layer
  changes beyond what P5.1 already established for the `AuthProvider` registry.
- **Patterns**: Mirrors `adapters/base.py`'s Protocol + registry idiom (ADR-001) — `clerk.py`
  registers itself exactly like `local_static.py` does; RBAC/route code never branches on provider
  identity.
- **Standards**: Manual JWT verification per Clerk's documented pattern
  (`clerk.com/docs/guides/sessions/manual-jwt-verification`): resolve token → fetch/cached JWKS →
  verify RS256 signature + `exp`/`nbf`/`azp` → construct `AuthIdentity`.

---

## Mode & Agent Routing (read before assigning agents)

**THIS PHASE IS MUST-STAY — NO ICA / CODEX OFFLOAD.** Per the decisions block §2 (Agent Routing)
and §6 (Model Routing), P5.1–P5.4 are the auth-core + RBAC + migration + Clerk verify surface and
stay on the Claude subscription for every implementation task. Do not route any task in this phase
to ICA Sonnet 4.6 or Codex gpt-5.5, including "bounded"-looking sub-tasks (role-mapping table,
config-flag wiring) — the whole phase sits on the Clerk verify path, which is Mode D.

- **Primary**: `backend-architect` (also `integration_owner` for the R-P3 seam obligation below).
- **Secondary**: `ui-engineer-enhanced` (FE hook only — does not touch `AuthContext.tsx`, which is
  out of scope; that file belongs to P5.8).
- **Model**: `sonnet`, effort `extended` for the JWKS-verify core (CLK-4.1) and the seam task
  (CLERK-900); `adaptive` for the remaining tasks (see Task Table).

**Mode D scope, precisely**: per `.claude/rules/delegation-modes.md`, Mode D blocks *production
activation* pending human sign-off — it does not block writing and unit-testing the adapter code
against a dev/test JWKS fixture. Concretely:
- Writing `clerk.py`, its unit tests, the role-mapping table, the config-flag wiring, and
  `useClerkAuth.ts` against a **JWKS test fixture** proceeds under normal `acceptEdits`-equivalent
  execution — no per-task pause required.
- **Wiring the adapter to real Clerk secrets or a production JWKS endpoint** is the specific action
  gated by **Human Gate #3** below and is out of scope for this phase's execution (the flag stays
  off; no real secret ever needs to exist for this phase to reach exit criteria).
- If an executing agent finds itself about to configure a *real* Clerk instance, real secret key, or
  production JWKS URL, it must stop and escalate per the delegation-modes cross-mode-escalation rule
  — that is Human Gate #3's trigger, not this phase's normal build path.

---

## Structured Acceptance Criteria (R-P1–R-P4)

#### AC P5.4-A: FE Clerk login round-trips against backend JWKS verify (seam contract — CLERK-900)
- target_surfaces:
    - src/research_foundry/api/auth/adapters/clerk.py
    - src/research_foundry/api/auth/provider.py
    - frontend/runs-viewer/src/auth/useClerkAuth.ts
- propagation_contract: >
    `useClerkAuth()` obtains the current Clerk session JWT client-side (via `@clerk/clerk-react`'s
    `useAuth().getToken()`), attaches it as `Authorization: Bearer <token>` on a request to the
    backend's identity-resolution path (same header contract `local_static` already uses, extended
    per-provider per the existing `p5-auth-header.test.ts` pattern), and
    `ClerkAuthProvider.authenticate()` verifies the JWT against the cached JWKS, returning an
    `AuthIdentity`. CLERK-900 asserts this full round-trip against a **JWKS test fixture** — never
    Clerk's live hosted API.
- resilience: >
    If Clerk-side token retrieval fails (unauthenticated, network error) or backend verification
    fails (bad signature, expired token, JWKS fetch/parse failure), `useClerkAuth()` returns an
    explicit error state — never a silently-empty identity that could be mistaken for
    `auth_mode=none`, and never a fabricated least-privilege identity constructed client-side.
- visual_evidence_required: false
  # This phase proves the wire contract only. The actual login *screen* consuming this hook ships
  # in Phase 8 (AuthContext.tsx) — screenshot evidence belongs there, not here (see Quality Gates).
- verified_by:
    - CLERK-900

#### AC P5.4-B (R-P2 implicit — new field `AuthIdentity` via Clerk): FE handles a missing/malformed Clerk-resolved identity
- target_surfaces:
    - frontend/runs-viewer/src/auth/useClerkAuth.ts
- propagation_contract: >
    `useClerkAuth()` is the sole point where a Clerk-path `AuthIdentity` (or its absence) enters the
    frontend. No other surface reads Clerk state directly in this phase.
- resilience: >
    A missing, null, or malformed `AuthIdentity` response (backend verify failure) surfaces as an
    explicit `{identity: null, error: <ClientError>}` state — the hook never assumes a default role,
    never silently degrades to "logged in as viewer," and never throws unhandled. Mirrors PRD §11
    AC-5's "FE handles missing `roles`" resilience clause, applied specifically to the Clerk path.
- visual_evidence_required: false
- verified_by:
    - useClerkAuth.test.ts (unit)
    - CLERK-900

#### AC P5.4-C: `clerk` and `oidc` both satisfy the `AuthProvider` Protocol identically
- target_surfaces:
    - src/research_foundry/api/auth/adapters/clerk.py
    - src/research_foundry/api/auth/provider.py
- propagation_contract: >
    A parametrized conformance test instantiates every registered adapter (`local_static`, `clerk`,
    `oidc` stub) and asserts each satisfies the `AuthProvider` Protocol's `authenticate()` signature
    and return contract (`AuthIdentity | None`) without adapter-specific branches in the test itself.
- resilience: >
    If a future adapter is registered without satisfying the Protocol, the conformance test fails
    loudly at test-collection time (`isinstance`/`typing.runtime_checkable` assertion), not silently
    at request time.
- visual_evidence_required: false
- verified_by:
    - test_auth_provider_protocol_conformance.py

---

## Task Breakdown

### Epic: Clerk Adapter + Seam

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Provider | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|----------|--------------|
| CLK-4.1 | `ClerkAuthProvider` JWKS verify | Pure-Python JWKS fetch/cache/verify (PyJWT + `cryptography`); RS256 + `exp`/`nbf`/`azp` checks; JWKS cached after first fetch (networkless thereafter, NFR budget). | JWT signed against a JWKS test fixture verifies to an `AuthIdentity`; second request in the same process makes 0 additional JWKS fetch calls (mock-asserted). | 2 pts | backend-architect | sonnet | extended | claude | None (P5.1 registry only) |
| CLK-4.2 | Clerk Organizations role mapping | Map Clerk Organizations' role slugs 1:1 onto RF's 5 roles (owner/admin/researcher/reviewer/viewer); unmapped/unknown Clerk role → least-privilege (`viewer`), never an error or elevated default. | Unit test enumerates all 5 mapped roles + one unknown-role case asserting `viewer` fallback. | 0.5 pt | backend-architect | sonnet | adaptive | claude | CLK-4.1 |
| CLK-4.3 | Config-flag dark-by-default wiring | `foundry.yaml: auth.provider: clerk` opt-in; `available()` capability check (mirrors `adapters/base.py`'s `available()`-style pattern per SPIKE) requires confirmed outbound internet + a public domain before the provider activates — never defaults, never silently activates. | With no explicit config change, `local_static`/`none` behavior is byte-for-byte unchanged; `available()` returns `False` in the absence of the outbound-internet/public-domain preconditions. | 0.5 pt | backend-architect | sonnet | adaptive | claude | CLK-4.1, CLK-4.2 |
| CLK-4.4 | OIDC seam Protocol conformance cross-check | Parametrized test instantiating `local_static`, `clerk`, and the P5.1 `oidc` stub against the shared `AuthProvider` Protocol — verification only, **no new `oidc` implementation**. | AC P5.4-C passes for all 3 registered adapters. | 0.25 pt | backend-architect | sonnet | adaptive | claude | CLK-4.1 |
| CLK-4.5 | Minimal FE Clerk login hook (`useClerkAuth.ts`) | Thin hook wrapping `@clerk/clerk-react`'s `useAuth().getToken()` + a call to the backend identity-resolution path; returns `{identity, loading, error}`. Does **not** build `AuthContext.tsx`, `ClerkProvider` app-shell wiring, or role-gated affordances — that is P5.8's scope. | Hook resolves a valid fixture-signed token to a populated `identity`; a bad/expired token resolves to a populated `error` with `identity: null`. | 1.25 pt | ui-engineer-enhanced | sonnet | adaptive | claude | CLK-4.1 |
| CLERK-900 | **Seam verification**: FE Clerk login flow round-trips against backend JWKS verify (contract test) | End-to-end contract test: `useClerkAuth()` (or its testable core) → backend `/`-scoped identity endpoint → `ClerkAuthProvider.authenticate()` → JWKS test fixture → `AuthIdentity` returned to the FE caller. Gated on CLK-4.1 and CLK-4.5 both being complete. | AC P5.4-A passes; `verified_by` on both AC P5.4-A and AC P5.4-B references this task ID. | 0.5 pt | backend-architect (owner), ui-engineer-enhanced | sonnet | extended | claude | CLK-4.1, CLK-4.5 |

**Total**: 5 pts (2 + 0.5 + 0.5 + 0.25 + 1.25 + 0.5).

---

## Detailed Task Specifications

### Task CLK-4.1: `ClerkAuthProvider` JWKS verify

**Estimate**: 2 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: None (requires P5.1's `AuthProvider` Protocol + registry merged — this phase's
entry criteria)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Implement `ClerkAuthProvider` at `src/research_foundry/api/auth/adapters/clerk.py`, registering
against the P5.1 `AuthProvider` registry exactly like `local_static.py` does. `authenticate(request)`
extracts the bearer token (Authorization header or `__session` cookie, per Clerk's documented
convention), resolves/caches the JWKS from the configured Clerk Frontend API
(`<frontend-api>/.well-known/jwks.json`) using PyJWT + `cryptography`, verifies RS256 signature plus
`exp`/`nbf`/`azp` claims, and constructs an `AuthIdentity{user_id, workspace_id, roles}` — with
`roles` populated by CLK-4.2's mapping (kept as a separate task for independent testability, called
from here).

**Acceptance Criteria**:
- [ ] A JWT signed against a JWKS **test fixture** (not Clerk's live API) verifies successfully to a
      populated `AuthIdentity`.
- [ ] An expired token, a token with a bad signature, and a token missing `azp` each fail closed
      (return `None`, never raise past the adapter boundary, never leak which check failed in the
      response).
- [ ] JWKS is fetched at most once per process lifetime under normal operation; a second
      `authenticate()` call in the same test makes 0 additional JWKS fetch calls (mock/spy-asserted)
      — satisfies the NFR budget ("networkless per-request after first fetch").
- [ ] No raw JWKS material, signing keys, or token contents are logged (mirrors the existing
      `hmac.compare_digest`/no-log-the-value discipline in `middleware/auth.py`).

**Implementation Notes**:
- Follow Clerk's documented manual-verification pattern exactly (SPIKE F1):
  `clerk.com/docs/guides/sessions/manual-jwt-verification`.
- Use PyJWT + `cryptography` — no `@clerk/clerk-sdk-python`-style Node-adjacent dependency, no
  self-hosted Clerk instance assumption anywhere in this file (SPIKE F5).
- Cache the JWKS key set in-process (e.g., a module-level or instance-level cache with a TTL/ETag
  refresh path) — the "networkless after first fetch" requirement is a hard NFR, not a nice-to-have.
- Test fixture: `tests/fixtures/auth/clerk_jwks_fixture.json` — a locally-generated RSA keypair's
  public JWK plus one or more test JWTs signed with the matching private key. Never depend on
  reaching Clerk's real hosted API in tests.

**Files Involved**:
- `src/research_foundry/api/auth/adapters/clerk.py` — new adapter implementation.
- `src/research_foundry/api/auth/provider.py` — read-only reference for the Protocol/registry shape
  (no changes expected; P5.1 already defines this).
- `tests/fixtures/auth/clerk_jwks_fixture.json` — new JWKS + signed-JWT test fixture.
- `tests/unit/test_clerk_adapter.py` — new unit tests.

---

### Task CLK-4.2: Clerk Organizations role mapping

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: CLK-4.1
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Map Clerk Organizations role slugs onto RF's 5 roles (owner, admin, researcher, reviewer, viewer),
1:1 per FR-3. Clerk supports up to 10 custom roles per instance (SPIKE F3), so RF's 5 fit
comfortably — but custom roles require a paid Clerk plan in *production* (free in dev only). This
task's mapping logic is agnostic to that billing constraint (it maps whatever role slug the verified
token carries); the billing constraint is an operator-facing note (FU-3), not a code branch.

**Acceptance Criteria**:
- [ ] All 5 RF roles have an explicit, tested mapping from a corresponding Clerk Organizations role
      slug.
- [ ] An unrecognized/unmapped Clerk role slug maps to `viewer` (least-privilege) — never to an
      error, never to an elevated default, and never silently to `owner`/`admin`.
- [ ] Mapping table is data (a dict/enum), not a chain of adapter-specific `if` branches in route or
      RBAC code — RBAC code continues to reason only in terms of RF's 5 roles, never Clerk's slugs.

**Implementation Notes**:
- Keep the mapping table colocated with `clerk.py` (or a small `clerk_roles.py` if it grows) —
  this is Clerk-adapter-internal detail, not something `provider.py` or route code should know about.
- Document the paid-plan constraint (FU-3) as a code comment pointing to the PRD note, not as a
  runtime check — RF cannot verify Clerk's own billing plan from the adapter.

**Files Involved**:
- `src/research_foundry/api/auth/adapters/clerk.py` — role-mapping table + resolution function.
- `tests/unit/test_clerk_adapter.py` — role-mapping unit tests (extends CLK-4.1's test file).

---

### Task CLK-4.3: Config-flag dark-by-default wiring

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: CLK-4.1, CLK-4.2
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Wire `auth.provider: clerk` as an explicit opt-in value in `foundry.yaml`'s `auth.provider` enum
(`none|local_static|clerk|oidc`, per FR-5), resolved through the same `create_app` registry lookup
P5.1 established. Add an `available()`-style capability check (mirroring the existing
`adapters/base.py` idiom referenced in the PRD's Architectural Context) that requires confirmed
outbound internet reachability **and** a configured public domain before the `clerk` provider is
permitted to activate — this is the code-level backstop for the SPIKE's "never default or sole"
verdict and directly mitigates the PRD risk row: *"Clerk's 'no self-hosted' constraint (F5) surprises
an operator who enables it on an air-gapped node."*

**Acceptance Criteria**:
- [ ] With no `auth.provider` change from its current default, `local_static`/`none` request
      handling is byte-for-byte unchanged (regression-asserted against the existing
      `p5-auth-header.test.ts`/provider-parametrized auth test suite from P5.1).
- [ ] `available()` returns `False` (and `create_app` refuses to activate `clerk`, failing loudly at
      startup with an actionable message) when outbound internet or a public domain is not
      configured/reachable.
- [ ] Enabling `clerk` requires an explicit, non-default `foundry.yaml` change — there is no
      environment-detection auto-enable path.

**Implementation Notes**:
- This is the primary code-level mitigation for the PRD's Clerk-surprise risk row — treat the
  `available()` check as load-bearing, not cosmetic.
- Reachability check should be a cheap, explicit precondition check (e.g., a config-declared flag
  the operator sets alongside enabling `clerk`, possibly backed by a lightweight connectivity probe)
  — do not implement a heavyweight network diagnostic subsystem; YAGNI applies.

**Files Involved**:
- `foundry.yaml` — document the `auth.provider: clerk` opt-in and its preconditions.
- `src/research_foundry/config.py` — config schema/validation for the `clerk` provider option and
  its `available()` preconditions.
- `src/research_foundry/api/auth/adapters/clerk.py` — `available()` implementation.
- `tests/unit/test_clerk_adapter.py` — dark-by-default + `available()` gate tests.

---

### Task CLK-4.4: OIDC seam Protocol conformance cross-check

**Estimate**: 0.25 points
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: CLK-4.1
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
FR-4 requires the `oidc`/BYO adapter seam (a Protocol conformance point already stubbed in P5.1) to
land even if its concrete implementation defers (FU-2). This task does **not** implement `oidc` — it
adds a parametrized conformance test proving `clerk` (this phase's new adapter) satisfies the exact
same `AuthProvider` Protocol as `local_static` and the existing `oidc` stub, with zero adapter-specific
branching in the test itself.

**Acceptance Criteria**:
- [ ] AC P5.4-C passes: `local_static`, `clerk`, and the `oidc` stub all satisfy `AuthProvider`'s
      `authenticate(request) -> AuthIdentity | None` signature and registry contract
      (`register()`/`get_provider(name)`).
- [ ] The test fails loudly (at collection or assertion time) if a future adapter is registered
      without satisfying the Protocol — not silently at request time.
- [ ] No `oidc.py` implementation changes are made in this task — cross-check only.

**Implementation Notes**:
- If `typing.Protocol` with `@runtime_checkable` is used in `provider.py` (P5.1), this test can use
  `isinstance()` directly; otherwise, assert via `hasattr`/signature introspection consistently with
  whatever pattern P5.1 established for `adapters/base.py`.

**Files Involved**:
- `tests/unit/test_auth_provider_protocol_conformance.py` — new parametrized conformance test.
- `src/research_foundry/api/auth/provider.py` — read-only reference.

---

### Task CLK-4.5: Minimal FE Clerk login hook (`useClerkAuth.ts`)

**Estimate**: 1.25 points
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: CLK-4.1
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Ship `frontend/runs-viewer/src/auth/useClerkAuth.ts`: a narrow, testable hook that (a) uses
`@clerk/clerk-react`'s `useAuth().getToken()` to obtain the current Clerk session JWT client-side,
and (b) resolves it against the backend's identity path (extending the existing
`p5-auth-header.test.ts` header contract, per-provider), returning `{identity, loading, error}`.
This is **explicitly not** `AuthContext.tsx` — no `ClerkProvider` app-shell mounting, no
`SignIn`/`UserButton` rendering, no role-gated affordance logic. Those are P5.8's scope; this hook is
the contract surface P5.8 will import and wrap.

**Acceptance Criteria**:
- [ ] A fixture-signed valid token resolves `identity` to the expected `AuthIdentity` shape
      (`user_id`, `workspace_id`, `roles`), with `loading` transitioning `true → false` and `error`
      staying `null`.
- [ ] A bad/expired token resolves `identity: null`, `error` populated with an explicit,
      non-generic-to-the-point-of-uselessness message (still respecting the "no raw
      credentials/secrets in browser payloads or logs" NFR — the error describes the failure class,
      never echoes the token or JWKS material).
- [ ] `@clerk/clerk-react` is loaded only when `provider=clerk` is the resolved auth mode (opt-in
      devDependency per PRD §8 External Dependencies) — no bundle-size or runtime cost when
      `local_static`/`none` is active.
- [ ] AC P5.4-B (FE handles missing/malformed identity, R-P2) passes.

**Implementation Notes**:
- Keep this hook's public surface small and stable — P5.8 will wrap it, not reimplement it. Resist
  scope creep toward building the login screen or app-shell wiring here (PRD risk row: "Frontend
  auth-context abstraction ... grows unbounded complexity" — mitigation is exactly this kind of
  narrow, single-purpose seam).
- Reuse `client.ts`'s existing request/error-handling conventions where practical (do not fork a new
  fetch pattern), but do not modify `client.ts` itself in this phase unless strictly necessary for
  the hook to function — flag any such need explicitly in the PR/Completion Report rather than
  silently expanding scope, since `client.ts` is also a P5.8-adjacent surface.

**Files Involved**:
- `frontend/runs-viewer/src/auth/useClerkAuth.ts` — new hook.
- `frontend/runs-viewer/src/auth/useClerkAuth.test.ts` — new unit tests (fixture-token based, no
  live Clerk dependency).

---

### Task CLERK-900: Seam verification — FE Clerk login flow round-trips against backend JWKS verify (contract test)

**Estimate**: 0.5 points
**Assigned Subagent(s)**: backend-architect (owner), ui-engineer-enhanced
**Model**: sonnet
**Effort**: extended
**Dependencies**: CLK-4.1, CLK-4.5
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
This is the **mandatory seam task** (R-P3) covering the cross-owner propagation contract between
backend-architect's `ClerkAuthProvider` (CLK-4.1) and ui-engineer-enhanced's `useClerkAuth.ts`
(CLK-4.5). It proves the full round-trip: hook obtains a fixture-signed session token → backend
verifies against the JWKS test fixture → `AuthIdentity` flows back to the FE caller in the expected
shape. `backend-architect` is the `integration_owner` accountable for this task per the phase
frontmatter.

**Acceptance Criteria**:
- [ ] AC P5.4-A passes end-to-end against a **JWKS test fixture** (never Clerk's live hosted API).
- [ ] A negative case (expired/bad-signature token) is asserted to fail the round-trip cleanly on
      both sides (backend returns no identity; FE hook surfaces `error`, not a silent pass-through).
- [ ] Both AC P5.4-A's and AC P5.4-B's `verified_by` lists correctly reference this task ID after it
      passes.

**Implementation Notes**:
- This test may live as a backend integration test that imports/exercises the FE hook's testable
  core logic (e.g., via a lightweight test harness) or as a coordinated pair of tests (one backend,
  one frontend) that share the same JWKS fixture and assert complementary halves of the contract —
  either shape is acceptable as long as the full round-trip is demonstrably exercised, not just each
  side's unit behavior in isolation (CLK-4.1's and CLK-4.5's unit tests already cover those).
- Do not gate this task on real Clerk secrets or network reachability — the entire point is that the
  contract is provable against a fixture before any real-secrets activation (Human Gate #3).

**Files Involved**:
- Seam/contract test file(s) — location decided by the executing pair (e.g.,
  `tests/integration/test_clerk_login_seam.py` and/or an extension of
  `frontend/runs-viewer/src/auth/useClerkAuth.test.ts`); record the actual path(s) chosen in
  `evidence` on completion.

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: `ClerkAuthProvider.authenticate()` verifies a fixture-signed JWT to an
      `AuthIdentity`; `local_static`/`none` behavior is unchanged.
- [ ] **Testing**: CLK-4.1–CLK-4.5 unit tests and the CLERK-900 seam test all pass; the
      P5.1 provider-parametrized auth suite still passes unmodified.
- [ ] **Performance**: JWKS verification is networkless after the first fetch (NFR budget,
      CLK-4.1's cache-hit assertion).
- [ ] **Security**: No raw JWKS material, tokens, or Clerk secrets appear in logs, test output, or
      browser payloads; `available()` gate prevents accidental activation on an air-gapped node.
- [ ] **Documentation**: Role-mapping table and the `available()` precondition are documented inline
      (code comments) referencing FU-3/SPIKE F3/F5; full operator-facing docs land in P5.9.
- [ ] **Code Quality**: `flake8`/`mypy` clean on new/changed Python files; `npx tsc --noEmit` clean
      on the new hook + test file.
- [ ] **Architecture**: `clerk.py` mirrors `adapters/base.py`'s Protocol + registry idiom; no
      route/RBAC code branches on provider identity.
- [ ] **Seam verification** (R-P3, `integration_owner: backend-architect`): `CLERK-900` is completed
      and both AC P5.4-A and AC P5.4-B `verified_by` reference it.
- [ ] **Runtime smoke** (R-P4, `ui_touched: true`): **partial by design** — `CLERK-900` is the
      contract-level smoke test for this phase (headless, fixture-based); a browser
      screenshot is **not** required here because no login *screen* exists yet (P5.8 builds it).
      Record `runtime_smoke: skipped` in the Completion Report with reason "full-UI screenshot
      evidence deferred to P5.8 (AuthContext.tsx / login screen build); this phase's smoke
      equivalent is the CLERK-900 contract test."

---

## Integration Points

### External Systems

- **Clerk hosted Frontend API** (`<frontend-api>/.well-known/jwks.json`): consumed only for JWKS
  material once `clerk` is activated; this phase's tests never reach the live endpoint (JWKS test
  fixture only). No self-hosted Clerk instance exists or is assumed (SPIKE F5).

### Internal Systems

- **P5.1 `AuthProvider` registry** (`api/auth/provider.py`): `clerk.py` registers against this
  exactly as `local_static.py` does — no registry changes expected in this phase.
- **P5.2 RBAC enforcement** (future phase): consumes `AuthIdentity.roles` produced by CLK-4.2's
  mapping — this phase does not implement RBAC checks, only produces a correctly-shaped identity.
- **P5.8 Frontend auth-context** (future phase): imports and wraps `useClerkAuth.ts` inside the full
  `AuthContext.tsx` 3-mode abstraction (Clerk / local / none) — this phase's hook is a dependency for
  that phase, not a substitute for it.
- **P5.9 Regression + E2E** (future phase): the CLERK-900 contract test and CLK-4.1–4.5 unit tests
  feed into the provider-parametrized regression suite assembled there.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/api/auth/adapters/clerk.py` | New: JWKS verify, role mapping, `available()` gate | backend-architect |
| `src/research_foundry/config.py` | `auth.provider: clerk` schema + preconditions | backend-architect |
| `foundry.yaml` | Document opt-in `clerk` provider config | backend-architect |
| `frontend/runs-viewer/src/auth/useClerkAuth.ts` | New: minimal FE login contract hook | ui-engineer-enhanced |
| `tests/fixtures/auth/clerk_jwks_fixture.json` | New: JWKS + signed-JWT test fixture | backend-architect |
| `tests/unit/test_clerk_adapter.py` | New: adapter unit tests | backend-architect |
| `tests/unit/test_auth_provider_protocol_conformance.py` | New: cross-adapter Protocol conformance | backend-architect |
| `frontend/runs-viewer/src/auth/useClerkAuth.test.ts` | New: hook unit tests | ui-engineer-enhanced |

---

## Testing Strategy

### Unit Tests

- `ClerkAuthProvider.authenticate()` against valid/expired/bad-signature/missing-claim JWTs (JWKS
  test fixture only).
- JWKS cache-hit assertion (0 additional fetches on second call in-process).
- Role-mapping table: all 5 RF roles + one unknown-role → `viewer` fallback case.
- `available()` gate: preconditions absent → `False`; preconditions present → `True`.
- `useClerkAuth.ts`: valid token → populated identity; bad token → populated error, null identity.

### Integration Tests

- `CLERK-900`: full FE-hook-to-backend-verify round-trip against the shared JWKS fixture, including
  the negative (bad/expired token) case.
- Regression check: existing P5.1 provider-parametrized `p5-auth-header.test.ts`/auth suite still
  passes unmodified with `clerk` registered but inactive (config flag off).

### E2E Tests (if applicable)

- **Out of scope for this phase.** Full E2E login/role-bounded-action coverage (`p5-auth-rbac.spec.ts`)
  is P5.9's job, once P5.8's full `AuthContext.tsx` exists to drive an actual login screen.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Clerk's "no self-hosted" constraint (F5) surprises an operator who enables it on an air-gapped node (PRD risk row) | Medium | `available()` check (CLK-4.3) requires confirmed outbound internet + public domain before activation; documented prominently; never default. |
| Human Gate #3 is skipped/forgotten and real secrets get wired before sign-off | High | Gate is explicit in this phase's exit criteria and in the parent plan; no task in this phase touches real secrets, so there is nothing to "accidentally" activate without a deliberate, separate, gated action. |
| Frontend auth-context scope creep (PRD risk row: "grows unbounded complexity") | Medium | `useClerkAuth.ts` is deliberately scoped to the contract only (CLK-4.5 Implementation Notes); `AuthContext.tsx` app-shell wiring is explicitly deferred to P5.8, not built here even partially. |
| JWKS caching goes stale (key rotation) and verification silently fails for legitimate tokens | Low | Out of scope for this phase's fixture-based tests (fixture keys don't rotate); flag as a P5.9/operator-docs follow-up if the cache doesn't already implement a refresh path — do not gold-plate here (YAGNI). |
| Role-mapping drift between Clerk's paid-plan custom roles (production) and free-tier/dev roles used in testing | Low | Mapping logic is data-driven and provider-agnostic of Clerk's billing tier (CLK-4.2); the billing constraint (FU-3) is an operator note, not a code branch, so there is no dev/prod code divergence to drift. |

---

## Human Gate #3

**Mandatory. This blocks phase exit for any production/live-Clerk activation.**

Before the `ClerkAuthProvider` adapter is wired to **real Clerk secrets or a production JWKS
endpoint** in any deployment (dev, staging, or production), an explicit human sign-off is required
covering:

1. **Where Clerk secrets are stored** (env var, secret manager, or otherwise) — never committed,
   never logged, never placed in a browser payload.
2. **How the JWKS is fetched and cached** — confirm the caching strategy (CLK-4.1) is understood and
   accepted by the operator, including refresh/rotation behavior if implemented.
3. **What is logged** — confirm no token contents, JWKS material, or Clerk secret keys appear in
   application logs, telemetry spans, or audit records (composes with the NFR's no-log-the-value
   discipline).

**This gate does NOT block**: building and unit-testing the adapter against a **dev/test JWKS
fixture** (as this phase does). The gate fires specifically at the transition from
fixture-based development to any real-secrets/real-JWKS activation — including a developer's own
personal Clerk dev instance used for manual smoke-testing, not just a production rollout.

Record the sign-off (who approved, date, and the three points above) in the Completion Report before
setting this phase's `status: completed`, and again — referencing this same gate — before
`auth.provider: clerk` is ever flipped on in a real deployment's `foundry.yaml`.

---

## Success Metrics

- **Completion**: All 6 tasks (CLK-4.1–4.5, CLERK-900) checked off.
- **Quality**: All Quality Gates passed, including the seam and (partial-by-design) runtime-smoke
  gates.
- **Performance**: JWKS verify networkless after first fetch, confirmed by test.
- **Testing**: Unit + seam contract tests green; existing P5.1 auth suite unregressed.

---

## Notes

### Implementation Approach

Build backend-first (CLK-4.1 → CLK-4.2 → CLK-4.3 → CLK-4.4 in sequence, since each depends on the
adapter existing), with CLK-4.5 (FE hook) startable in parallel once CLK-4.1's `AuthIdentity` shape
is stable — the two owners should agree on the exact response shape early to avoid CLERK-900
becoming a late-discovered mismatch. CLERK-900 is the final task and is explicitly gated on both
CLK-4.1 and CLK-4.5.

### Gotchas

- **SPIKE F5**: Clerk requires a domain you own + public DNS — do not assume any dev-mode
  workaround makes this air-gapped-friendly. The `available()` gate exists precisely because this is
  easy to get wrong.
- **SPIKE F3**: Clerk's custom-roles-require-paid-plan constraint is a *production* billing
  constraint, not a code-testable condition — do not try to detect Clerk's billing plan from the
  adapter; document it, don't gate on it in code.
- **FR-3 Note**: dark-by-default is a hard requirement — any test or dev config that accidentally
  defaults `auth.provider` to `clerk` is a regression against this phase's exit criteria.
- Do not let CLK-4.5 or CLERK-900 scope-creep into building `AuthContext.tsx` — that temptation is
  real once the hook works end-to-end, but it is explicitly P5.8's deliverable.

### Learnings

_Capture as this phase progresses._

### Findings Captured This Phase

- [x] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
