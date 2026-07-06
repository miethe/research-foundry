---
title: "Phase 8: Frontend Auth-Context + Admin UI + Role-Gated Affordances"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: "public-multiuser-p5-auth-rbac"
feature_version: "v1"
phase: 8
phase_title: "Frontend Auth-Context + Admin UI + Role-Gated Affordances"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.1 AuthProvider contract frozen"
  - "P5.4 Clerk login hook available"
exit_criteria:
  - "Login works per provider"
  - "UI hides unauthorized affordances (defense-in-depth only)"
  - "FEAUTH-900 seam verification passes"
  - "FEAUTH-901 runtime smoke passes"
  - "task-completion-validator sign-off"
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-1-auth-provider-port.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-2-rbac-enforcement.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-4-clerk-adapter.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-5-audit-log.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-6-rate-limits-admin-sharing.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-9-regression-e2e-docs.md
  - .claude/skills/planning/references/ac-schema.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
  - "ADR-001 (auth-provider port — Frontend subsection, SPIKE public-multiuser-p4p5-foundations)"
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: ui-engineer-enhanced
ui_touched: true
target_surfaces:
  - frontend/runs-viewer/src/auth/AuthContext.tsx
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/api/client.ts
seam_tasks:
  - FEAUTH-900
owner: nick
contributors: [ui-engineer-enhanced, ICA-Sonnet-4.6, task-completion-validator]
priority: high
risk_level: medium
category: "product-planning"
tags: [phase-plan, implementation, auth, rbac, frontend, public-multiuser, phase-5]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - frontend/runs-viewer/src/auth/AuthContext.tsx
  - frontend/runs-viewer/src/auth/LocalLoginForm.tsx
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/test/p5-auth-header.test.ts
  - frontend/runs-viewer/src/screens/SettingsScreen.tsx
  - frontend/runs-viewer/src/components/AdminSettings/WorkspaceMembersPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/RateLimitConfigPanel.tsx
  - frontend/runs-viewer/src/components/AdminSettings/AuthProviderStatusPanel.tsx
  - frontend/runs-viewer/src/test/p5-admin-settings.test.tsx
---

# Phase 8: Frontend Auth-Context + Admin UI + Role-Gated Affordances

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~2-3 days
**Effort**: 5 story points
**Dependencies**: P5.1 (AuthProvider contract frozen), P5.4 (Clerk login hook available)
**Team Members**: `ui-engineer-enhanced` (primary), ICA Sonnet 4.6 (bounded subcomponent offload, gated), `task-completion-validator` (mandatory gate)

---

## Phase Overview

This phase builds the frontend half of ADR-001's auth-provider abstraction: a 3-mode
`AuthContext` (Clerk / local_static / none) that wraps the app shell, role-gated navigation and
settings affordances in `AppShell.tsx`, identity/token threading in `client.ts`, and an admin
settings UI that consumes Phase 6's backend admin API. **Server-side enforcement (P5.2's
`require_role` dependency, P5.3's workspace-scoped repository queries) remains the actual
authorization boundary — everything built here is defense-in-depth UI polish, never a
substitute for the server check** (PRD FR-6, Mode-D gate 6, SPIKE ADR-001 Frontend subsection).

This phase **consumes backend contracts from three other phases it does not own**: Phase 2
(role/permission fields on `AuthIdentity`), Phase 3 (workspace-scoping enforcement semantics —
what a cross-workspace read looks like from the client's perspective), and Phase 6
(rate-limit-state and admin-settings fields exposed by the new admin API). `FEAUTH-900` below
exists specifically to verify those seams are honored with real resilience, not optimistic UI
state.

### Goals

- Ship `AuthContext.tsx` as the single place that resolves `provider`/`auth_mode` and renders the
  correct login surface (Clerk components, local login form, or nothing).
- Back `AppShell.tsx`'s existing `NAV_ITEMS` disabled-state pattern with real role checks derived
  from the resolved identity, while keeping the server as the actual gate.
- Thread the resolved identity/token through `client.ts`, extending the existing
  `p5-auth-header.test.ts` contract per-provider (not replacing it).
- Ship an admin settings UI (extending `SettingsScreen.tsx`) that surfaces Phase 6's
  workspace/member/role/rate-limit/provider-status admin API.
- Verify — not assume — that the above degrades correctly for every upstream "FE handles missing
  X" contract (`FEAUTH-900`) and works end-to-end for every provider/role/mode combination
  (`FEAUTH-901`).

### Architecture Focus

- **Layer**: UI (frontend auth abstraction + admin settings surface)
- **Patterns**: Provider/adapter idiom mirrored from the backend `AuthProvider` Protocol
  (SPIKE ADR-001 — "mirror the existing adapter idiom, no bespoke shape"); existing
  `NAV_ITEMS`/`NavState` disabled-affordance pattern in `AppShell.tsx`; existing
  `loopbackGet()`/`ClientError` contract in `client.ts`; house `rv-*`/`it-*` CSS convention
  (no Tailwind).
- **Standards**: WCAG 2.1 AA on the local-login form and admin settings UI (PRD NFR
  Accessibility); defense-in-depth-only framing on every role-gated UI element (never the sole
  control).

### Offload Plan (mandatory labeling)

| Scope | Owner | Rationale |
|-------|-------|-----------|
| `AuthContext.tsx` 3-mode core degradation logic | **Claude (sonnet), MUST-stay** | Judgment-heavy: getting the none/local_static/clerk dispatch and the FR-2 resilience behaviors wrong is exactly the class of bug `FEAUTH-900` exists to catch. Not mechanical. |
| All role-gated-affordance wiring in `AppShell.tsx` / `SettingsScreen.tsx` (which real backend field drives which disabled state) | **Claude (sonnet), MUST-stay** | Must reflect REAL backend contracts (roles, workspace scoping, rate-limit/admin fields) — judgment-heavy, not mechanical. |
| Individual `AdminSettings/*Panel.tsx` subcomponent widgets (layout, table rendering, form fields) | **ICA Sonnet 4.6, offloadable** | Bounded, contract-clear once the panel's data shape is fixed by `FEAUTH-004`. |
| `LocalLoginForm.tsx` styling/layout only (not its submit/error-handling logic) | **ICA Sonnet 4.6, offloadable** | Presentational; the auth-flow logic that calls it stays in `AuthContext.tsx`. |
| **Validator gate** | `task-completion-validator` | MUST review any ICA-produced subcomponent before acceptance — no exceptions. |

---

## Acceptance Criteria (Structured, from PRD AC-5 + FR-2 resilience additions)

#### AC-5: Frontend auth-context abstraction degrades correctly per provider/mode
- target_surfaces:
    - frontend/runs-viewer/src/auth/AuthContext.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: >
    `AuthContext` resolves to `ClerkProvider`/`SignIn` (provider=clerk), a local login form
    (provider=local_static), or nothing (auth_mode=none) at app-shell mount; `client.ts`'s
    `loopbackGet()` threads the resolved identity/token per the existing
    `p5-auth-header.test.ts` contract, extended per-provider.
- resilience: >
    Static-export build has no server to authenticate against — `AuthContext` renders no login UI
    and all data fetches degrade to the pre-gated (export-time) read-only public dataset.
- visual_evidence_required: before/after screenshots at desktop >=1440px for each of the 3 provider states (clerk, local_static, none)
- verified_by:
    - FEAUTH-001
    - p5-auth-header-test-extended
    - FEAUTH-900
    - FEAUTH-901

#### AC-5a: FE handles a missing/absent `AuthIdentity` (auth_mode=none)
- target_surfaces:
    - frontend/runs-viewer/src/auth/AuthContext.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: >
    When no `AuthProvider` middleware is configured (`auth_mode=none`), `AuthContext` never
    receives an `AuthIdentity` from the backend and falls back to today's implicit
    single-operator identity.
- resilience: >
    No role/workspace UI affordance is rendered; the app behaves exactly as the current
    single-operator mode — this is a regression gate, not new behavior.
- visual_evidence_required: false (covered by AC-5's "none" screenshot state)
- verified_by:
    - FEAUTH-001
    - FEAUTH-900

#### AC-5b: FE handles a 401/403 from any RBAC-gated route
- target_surfaces:
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: >
    Extends `p5-auth-header.test.ts` (401 case already covered pre-existing in the codebase):
    `loopbackGet()` must surface a **403** the same way — a `ClientError` with `status` set —
    never silently swallowed.
- resilience: >
    Callers (screens/components) must render a visible denial state from the thrown
    `ClientError`, never a blank or silently-failed screen.
- visual_evidence_required: false
- verified_by:
    - FEAUTH-003
    - p5-auth-header-test-extended

#### AC-5c: FE handles a missing `roles` array on an `AuthIdentity` payload
- target_surfaces:
    - frontend/runs-viewer/src/auth/AuthContext.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: >
    If a backend payload lacks a `roles` array (malformed or stale-contract identity),
    `AuthContext` treats the identity as least-privilege (viewer-equivalent).
- resilience: >
    Never treated as an error and never defaults to elevated privilege; `AppShell` hides every
    role-gated affordance above viewer level in this state.
- visual_evidence_required: false
- verified_by:
    - FEAUTH-001
    - FEAUTH-002
    - FEAUTH-900

---

## Task Breakdown

### Epic: Frontend Auth-Context + Admin UI

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|-----------------------|-------|--------|--------------|
| FEAUTH-001 | AuthContext.tsx core 3-mode abstraction | New `AuthContext.tsx`: Clerk / local_static / none dispatch, FR-2 resilience | AC-5, AC-5a, AC-5c | 1.5 pts | ui-engineer-enhanced | sonnet | adaptive | None (consumes P5.1/P5.4 contracts) |
| FEAUTH-002 | AppShell.tsx role-gated affordances | Back `NAV_ITEMS` disabled-state with real role checks; defense-in-depth framing | AC-5c | 1 pt | ui-engineer-enhanced | sonnet | adaptive | FEAUTH-001 |
| FEAUTH-003 | client.ts identity threading + test extension | Thread resolved identity/token through `loopbackGet()`; extend `p5-auth-header.test.ts` per-provider + 403 case | AC-5, AC-5b | 1 pt | ui-engineer-enhanced | sonnet | adaptive | FEAUTH-001 |
| FEAUTH-004 | Admin settings UI (consumes Phase 6 API) | Extend `SettingsScreen.tsx` with role-gated admin section; 4 subcomponent panels | AC-5c | 1 pt | ui-engineer-enhanced / ICA Sonnet 4.6 (subcomponents) | sonnet | adaptive | FEAUTH-002 |
| FEAUTH-900 | Seam verification: role-gated affordances actually reflect server enforcement, not just optimistic UI state | Cross-phase resilience verification against AUTH-900/RBAC-900/WKSP-900/GATE-900/GATE-901/AUDIT-900 | AC-5, AC-5a, AC-5c | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | FEAUTH-001, FEAUTH-002, FEAUTH-003, FEAUTH-004 |
| FEAUTH-901 | Runtime smoke: exercise every target_surfaces entry | Login x2 providers, admin UI, 5 per-role checks, static-export degrade | AC-5 | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | FEAUTH-900 |

**Model Selection Guidance**: Phase-level default is `sonnet` / `adaptive` (decisions block §6). The
`AuthContext.tsx` core dispatch and all role-gating wiring stay on Claude per the Offload Plan
above — do not route those to ICA/Codex regardless of apparent simplicity. Only `AdminSettings/*`
subcomponent widgets and `LocalLoginForm.tsx` styling/layout may go to ICA Sonnet 4.6, gated behind
`task-completion-validator`.

---

## Detailed Task Specifications

### Task FEAUTH-001: AuthContext.tsx core 3-mode abstraction

**Estimate**: 1.5 points
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None within phase; consumes P5.1's `AuthIdentity{user_id, workspace_id, roles}`
contract and P5.4's Clerk login hook.
**started**: null
**completed**: null
**verified_by**: [FEAUTH-900, FEAUTH-901]
**evidence**: []

**Description**:
Create `frontend/runs-viewer/src/auth/AuthContext.tsx` (new file — this directory does not exist
yet). Exposes a React context/provider that resolves the active `provider`/`auth_mode`
(read from viewer config, mirroring how `getViewerSettings()` resolves theme today) and renders:

- **`provider=clerk`**: wraps children in `ClerkProvider`, renders `SignIn` when unauthenticated.
  Consumes Phase 4's minimal Clerk hook rather than reimplementing token/session handling.
- **`provider=local_static`**: renders `LocalLoginForm.tsx` (new, sibling file) when
  unauthenticated; on submit, exchanges credentials via a `client.ts`-mediated call and stores the
  resulting `AuthIdentity`/token in context state.
- **`auth_mode=none`**: pure passthrough — renders children directly with the current implicit
  single-operator identity. No login UI, no role/workspace chrome (AC-5a).

Must implement the FR-2 resilience contracts directly in this file:
- Missing `AuthIdentity` (none mode) → no role/workspace affordance rendered (AC-5a).
- Missing `roles` array on an otherwise-present `AuthIdentity` → treat as least-privilege
  viewer-equivalent, never an error, never elevated privilege (AC-5c).

Static-export mode has no server: `AuthContext` must detect this build target and render no login
UI at all, regardless of configured provider — data fetches degrade to the pre-gated (export-time)
read-only public dataset (AC-5, resilience clause).

**Acceptance Criteria**:
- [ ] Three concrete modes only (Clerk, local_static, none) — no speculative 4th mode (PRD risk
      table: "keep the abstraction to exactly 3 concrete implementations").
- [ ] `auth_mode=none` renders identical to current behavior (regression-safe).
- [ ] Missing `roles` array never escalates privilege (AC-5c).
- [ ] Static-export build renders zero login UI in any provider configuration.
- [ ] Before/after screenshots captured for all 3 provider states at desktop ≥1440px
      (AC-5 visual_evidence_required).

**Implementation Notes**:
- Mirror the backend `AuthProvider` Protocol shape conceptually (resolve-once-at-mount, no
  call-site branching on provider identity elsewhere in the app) per SPIKE ADR-001's "no bespoke
  shape" instruction, even though this is a React context, not a Python Protocol.
- Do not import the Clerk SDK unconditionally — gate the import behind the resolved provider so
  the static-export bundle never pulls in Clerk (bundle-size / offline-first concern).
- Keep this file and its direct dispatch logic on Claude (sonnet) per the Offload Plan; only
  `LocalLoginForm.tsx`'s styling/layout may be ICA-drafted.

**Files Involved**:
- `frontend/runs-viewer/src/auth/AuthContext.tsx` - new file, core 3-mode context/provider
- `frontend/runs-viewer/src/auth/LocalLoginForm.tsx` - new file, local_static login form (logic on Claude, styling may be ICA-drafted)

---

### Task FEAUTH-002: AppShell.tsx role-gated affordances

**Estimate**: 1 point
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: FEAUTH-001
**started**: null
**completed**: null
**verified_by**: [FEAUTH-900, FEAUTH-901]
**evidence**: []

**Description**:
`AppShell.tsx` already has a `NavState = "enabled" | "contextual" | "disabled"` pattern and a
static `NAV_ITEMS` array (one hardcoded `disabled` entry for "Agents", pending Phase 4). This task
backs that same rendering path with **real** role checks derived from `AuthContext`'s resolved
identity: each nav item (and, where applicable, sub-affordances inside `SettingsScreen.tsx`)
declares an allowed-role set; `disabled` becomes `true` when the resolved identity's roles don't
intersect that set, with a role-specific `disabledReason` (e.g. "Requires admin or owner role")
distinct from the existing "Planned — ..." reason used for not-yet-shipped features.

**This is defense-in-depth only.** The comment block directly above the role-check logic must
state explicitly that server-side `require_role` enforcement (P5.2) and workspace-scoped
repository queries (P5.3) are the actual authorization boundary — hiding a nav item here prevents
confusion, not privilege escalation, and must never be treated as sufficient on its own
(PRD FR-6 / Mode-D gate 6).

**Acceptance Criteria**:
- [ ] Every role-gated nav/affordance state is derived from `AuthContext`'s resolved identity, not
      a hardcoded flag (except the pre-existing "Agents: planned" entry, which is unrelated to
      auth and stays as-is).
- [ ] A missing `roles` array renders every role-gated affordance disabled (viewer-equivalent,
      AC-5c) — never enabled-by-default.
- [ ] Explicit code comment states server-side enforcement is the real boundary.
- [ ] No behavior change for `auth_mode=none` (AC-5a regression guard).

**Implementation Notes**:
- Extend the existing `NavCapability` interface with an `allowedRoles?: Role[]` field rather than
  introducing a parallel gating mechanism.
- Reuse the existing `disabled`/`aria-disabled`/`title` wiring — do not fork a second disabled-item
  rendering path.

**Files Involved**:
- `frontend/runs-viewer/src/app/AppShell.tsx` - extend `NavCapability`/`NAV_ITEMS` with role checks

---

### Task FEAUTH-003: client.ts identity threading + test extension

**Estimate**: 1 point
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: FEAUTH-001
**started**: null
**completed**: null
**verified_by**: [FEAUTH-900, FEAUTH-901]
**evidence**: []

**Description**:
`client.ts`'s `loopbackGet()` currently injects a single build-time
`VITE_RUNS_LOOPBACK_API_TOKEN` bearer token (per `p5-auth-header.test.ts`). This task extends it to
thread the identity/token resolved by `AuthContext` per request: the `local_static` multi-token
session value, or Clerk's session token (via the Phase 4 hook's `getToken()`-equivalent), while
preserving every existing invariant already under test (Authorization header present only when a
token exists; never `Bearer ` with an empty value; 401 → `ClientError`).

Extend `frontend/runs-viewer/src/test/p5-auth-header.test.ts` — **extend, not replace or rewrite**
(matches the project's existing convention of extending `w1`/`w3` E2E specs rather than
duplicating them) — with:
- A per-provider case for `local_static` session-token resolution.
- A per-provider case for Clerk token resolution (mocked hook).
- A **new 403 case** (AC-5b): mirrors the existing 401 case but asserts a 403 also surfaces as a
  `ClientError` with `status: 403`, never silently swallowed.

**Acceptance Criteria**:
- [ ] All 3 pre-existing `p5-auth-header.test.ts` cases (token present / absent / empty) still
      pass unmodified.
- [ ] New 403 case passes (AC-5b).
- [ ] New per-provider token-resolution cases pass for both `local_static` and `clerk`.
- [ ] No new Authorization-header leak paths (e.g., token never logged, never appears in error
      messages).

**Implementation Notes**:
- Keep `loopbackGet()`'s existing header-construction shape; add a resolver function that
  `AuthContext` supplies (or that reads from a shared module-level identity store) rather than
  re-deriving auth state independently inside `client.ts`.
- The static-export path (`staticGet()`) is unaffected — it never sends an Authorization header.

**Files Involved**:
- `frontend/runs-viewer/src/api/client.ts` - thread resolved identity/token through `loopbackGet()`
- `frontend/runs-viewer/src/test/p5-auth-header.test.ts` - extend with per-provider + 403 cases

---

### Task FEAUTH-004: Admin settings UI (consumes Phase 6 backend admin API)

**Estimate**: 1 point
**Assigned Subagent(s)**: ui-engineer-enhanced (composition/wiring) / ICA Sonnet 4.6 (subcomponent widgets, gated)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: FEAUTH-002
**started**: null
**completed**: null
**verified_by**: [FEAUTH-900, FEAUTH-901]
**evidence**: []

**Description**:
Extend the existing `frontend/runs-viewer/src/screens/SettingsScreen.tsx` (route already exists at
`/settings` — extend, don't fork a new top-level route, per PRD FR-10) with a role-gated admin
section, visible only when the resolved identity's roles include admin/owner (via FEAUTH-002's
gating pattern). The section houses four new subcomponent panels under
`frontend/runs-viewer/src/components/AdminSettings/`:

- `WorkspaceMembersPanel.tsx` — member list + role assignment, consuming Phase 6's member/role
  admin API.
- `RoleAssignmentPanel.tsx` — capability-matrix display (read) and role-change UI (write, gated by
  the same admin check).
- `RateLimitConfigPanel.tsx` — read-only display of Phase 6's rate-limit configuration/state.
- `AuthProviderStatusPanel.tsx` — shows the active provider and, for Clerk, its `available()`
  status (outbound internet + public domain confirmation).

**Offload note**: the four panel subcomponents (layout, table/list rendering, form field wiring
against an already-fixed data shape) are ICA Sonnet 4.6 candidates once this task's data contracts
are fixed. The role-gating condition that decides whether the admin section renders at all, and the
composition of `SettingsScreen.tsx` itself, stay on Claude (sonnet) per the Offload Plan.
**`task-completion-validator` MUST review any ICA-produced panel before acceptance.**

**Acceptance Criteria**:
- [ ] Admin section renders only for admin/owner roles; hidden (not just visually collapsed) for
      researcher/reviewer/viewer.
- [ ] Each panel degrades explicitly (disabled + message, per FR-2 resilience convention) when its
      backing Phase 6 field is absent/null — never a crash, never silent emptiness.
- [ ] WCAG 2.1 AA on all new form fields (keyboard nav, labels, visible focus) per PRD NFR
      Accessibility.
- [ ] Any ICA-produced subcomponent passes `task-completion-validator` review before merge.

**Implementation Notes**:
- Follow the existing `rv-*`/`it-*` CSS convention (see `frontend/runs-viewer/src/styles/`) — no
  Tailwind, matching every other screen in this codebase.
- Data shapes for the four panels are defined by Phase 6's admin API contract — reference it by
  path/contract, do not invent a shape ahead of that phase landing.

**Files Involved**:
- `frontend/runs-viewer/src/screens/SettingsScreen.tsx` - add role-gated admin section
- `frontend/runs-viewer/src/components/AdminSettings/WorkspaceMembersPanel.tsx` - new (ICA candidate)
- `frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx` - new (ICA candidate)
- `frontend/runs-viewer/src/components/AdminSettings/RateLimitConfigPanel.tsx` - new (ICA candidate)
- `frontend/runs-viewer/src/components/AdminSettings/AuthProviderStatusPanel.tsx` - new (ICA candidate)
- `frontend/runs-viewer/src/test/p5-admin-settings.test.tsx` - new, unit tests for role-gating + panel resilience

---

### Task FEAUTH-900: Seam verification: role-gated affordances actually reflect server enforcement, not just optimistic UI state

**Estimate**: 0.25 points
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: FEAUTH-001, FEAUTH-002, FEAUTH-003, FEAUTH-004
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
This phase consumes backend contracts from three other phases it does not own (R-P3). This task
verifies — against the **actual running implementation** of `AuthContext.tsx`/`AppShell.tsx`/
`client.ts`, not a read of the code that merely "looks right" — that each upstream "FE handles
missing X" seam holds:

- **`AUTH-900` (Phase 1)**: when `AuthProvider.authenticate()` fails or returns no identity, the FE
  must not render a partial/mismatched identity state — confirm the generic-401 path
  (`FEAUTH-003`) and `AuthContext`'s none-mode fallback (`FEAUTH-001`) both fire correctly, not
  just one of the two.
- **`RBAC-900` (Phase 2)**: when a role-gated mutation is attempted and the server returns a real
  403 (`require_role` rejection), verify the actual attempt is blocked and surfaced via
  `FEAUTH-003`'s `ClientError` path — **even if `FEAUTH-002`'s optimistic nav-hiding has a gap**,
  the mutation itself must still be denied and reported, proving the UI hide is decoration, not
  the control.
- **`WKSP-900` (Phase 3)**: a cross-workspace record access must render as the standard
  "not found" UI state (never a distinguishable "exists but forbidden" state) — verify no FE code
  path (error message, console log, network inspector-visible payload) leaks workspace-boundary
  existence, consistent with the no-existence-leak convention threaded through `client.ts`.
- **`GATE-900` and `GATE-901` (Phase 6)**: rate-limit 429/`Retry-After` responses and
  admin-settings/sharing config fields being absent/null must degrade per `FEAUTH-004`'s
  resilience contract (disabled panel + explanatory message) — verify both gate responses
  independently, not just one representative case.
- **`AUDIT-900` (Phase 5, conditional)**: **only if** `FEAUTH-004`'s admin UI surfaces any
  audit-log-derived field, verify it degrades gracefully when the audit service is
  unavailable/empty. If no admin-UI surface exposes an audit-derived field in this phase's scope,
  mark this sub-item explicitly N/A in the Completion Report — do not silently skip it.

**Acceptance Criteria**:
- [ ] Each of the 6 sub-items above (`AUTH-900`, `RBAC-900`, `WKSP-900`, `GATE-900`, `GATE-901`,
      `AUDIT-900`) has a written pass/fail/N/A verdict in the Completion Report, with the specific
      FE behavior observed — not a generic "looks fine."
- [ ] Any failure blocks phase exit; this is a hard gate, not advisory.
- [ ] `AUDIT-900` is explicitly marked N/A (with reason) if not applicable, never silently omitted.

**Implementation Notes**:
- This task is a verification exercise, not new production code — no new files expected, though a
  fix-forward edit to `FEAUTH-001`-`004`'s output is in scope if a seam fails.
- Coordinate with the sibling phase files (Phase 1/2/3/5/6) for the exact upstream task IDs and
  their stated contracts before marking a sub-item pass.

**Files Involved**:
- `frontend/runs-viewer/src/auth/AuthContext.tsx` - verification target, fix-forward if needed
- `frontend/runs-viewer/src/app/AppShell.tsx` - verification target, fix-forward if needed
- `frontend/runs-viewer/src/api/client.ts` - verification target, fix-forward if needed

---

### Task FEAUTH-901: Runtime smoke: exercise every target_surfaces entry

**Estimate**: 0.25 points
**Assigned Subagent(s)**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: FEAUTH-900
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Runtime smoke exercising every `target_surfaces` entry for this phase (R-P4). This is the
**phase-local** smoke check; Phase 9's `p5-auth-rbac.spec.ts` Playwright suite is the full
regression covering the same surfaces in both static-export and live-API modes — this task does
not duplicate that suite, it is the fast local gate that runs before Phase 9 exists/lands.

Exercises, at minimum:
1. Login — `local_static` provider (success + failure case).
2. Login — Clerk provider (`SignIn` renders; redirect/session flow reaches an authenticated
   state).
3. Admin settings UI renders for an admin identity; is hidden for a non-admin identity.
4. Role-gated affordance hiding — **5 separate checks, one per role** (owner, admin, researcher,
   reviewer, viewer) — confirm each role sees exactly its permitted nav/action set. Do not
   collapse this into one generic "role gating works" check.
5. Static-export read-only degrade path — confirm zero login UI renders and all data resolves to
   the pre-gated public dataset.

**Acceptance Criteria**:
- [ ] All 5 checks above pass with captured evidence (screenshot or recorded assertion) in
      `.claude/evidence/phase-8/`.
- [ ] The 5 per-role checks are individually recorded — 5 distinct results, not 1.
- [ ] Note in the Completion Report explicitly cross-referencing Phase 9: "this is the phase-local
      smoke check; full regression coverage is `p5-auth-rbac.spec.ts` (Phase 9)."

**Implementation Notes**:
- Reuse `p5-admin-settings.test.tsx` and the extended `p5-auth-header.test.ts` as the automated
  backbone where possible; supplement with manual/scripted runtime checks for the visual
  before/after screenshots AC-5 requires.
- Do not mark this `runtime_smoke: skipped` — AC-5's `visual_evidence_required` is explicit and
  non-optional for this phase.

**Files Involved**:
- `frontend/runs-viewer/src/auth/AuthContext.tsx` - smoke target
- `frontend/runs-viewer/src/app/AppShell.tsx` - smoke target
- `frontend/runs-viewer/src/api/client.ts` - smoke target
- `frontend/runs-viewer/src/screens/SettingsScreen.tsx` - smoke target (admin UI)

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Login works per provider (Clerk, local_static); `auth_mode=none` is
      unaffected; admin settings UI consumes Phase 6's backend admin API correctly.
- [ ] **Testing**: `p5-auth-header.test.ts` extended and green (all pre-existing + new cases);
      `p5-admin-settings.test.tsx` green.
- [ ] **Performance**: No perceptible auth-check latency added client-side (identity resolution is
      local/cached, not a per-render network round-trip).
- [ ] **Security**: No credential/token value ever logged, rendered in an error message, or
      otherwise exposed in a browser-visible payload.
- [ ] **Documentation**: Inline code comments state server-side enforcement is the real boundary
      wherever a role-gated UI decision is made.
- [ ] **Code Quality**: `npm run build` passes; `npx tsc --noEmit` clean for touched files.
- [ ] **Architecture**: `AuthContext.tsx` stays to exactly 3 concrete modes (no speculative 4th);
      house CSS convention followed throughout.
- [ ] **Seam verification** (`integration_owner: ui-engineer-enhanced`): `FEAUTH-900` completed
      with all 6 sub-items resolved pass/fail/N/A (R-P3).
- [ ] **Runtime smoke** (`ui_touched: true`): `FEAUTH-901` completed with screenshot evidence in
      `.claude/evidence/phase-8/` for all 3 provider states + 5 per-role checks (R-P4) — a clean
      unit-test pass alone is not a substitute.
- [ ] **Reviewer gate**: `task-completion-validator` sign-off, including explicit review of any
      ICA-produced `AdminSettings/*` subcomponent.

---

## Integration Points

### External Systems

- **Clerk** (`@clerk/clerk-react`): `ClerkProvider`, `SignIn` — loaded only when `provider=clerk`
  is resolved, never bundled unconditionally (static-export bundle-size concern).
- **Research Foundry backend admin API** (Phase 6): member/role/rate-limit/provider-status fields
  consumed read-only (and, for role assignment, write) by the `AdminSettings/*` panels.

### Internal Systems

- **`AppShell.tsx` `NAV_ITEMS`**: existing disabled-state rendering path, extended (not forked) to
  drive off real role checks.
- **`client.ts` `loopbackGet()`**: existing auth-header contract, extended per-provider.
- **`SettingsScreen.tsx`**: existing `/settings` route, extended with a role-gated admin section.

---

## Key Files Modified

| File Path | Lines | Purpose | Subagent |
|-----------|-------|---------|----------|
| `frontend/runs-viewer/src/auth/AuthContext.tsx` | new file | 3-mode auth-context core | ui-engineer-enhanced |
| `frontend/runs-viewer/src/auth/LocalLoginForm.tsx` | new file | local_static login form | ui-engineer-enhanced / ICA (styling only) |
| `frontend/runs-viewer/src/app/AppShell.tsx` | ~1-140 | role-gated `NAV_ITEMS` | ui-engineer-enhanced |
| `frontend/runs-viewer/src/api/client.ts` | ~47-140 | identity/token threading | ui-engineer-enhanced |
| `frontend/runs-viewer/src/test/p5-auth-header.test.ts` | full file, extended | per-provider + 403 test cases | ui-engineer-enhanced |
| `frontend/runs-viewer/src/screens/SettingsScreen.tsx` | new section | role-gated admin section | ui-engineer-enhanced |
| `frontend/runs-viewer/src/components/AdminSettings/*.tsx` | new files | admin subcomponent panels | ICA Sonnet 4.6 (gated) |
| `frontend/runs-viewer/src/test/p5-admin-settings.test.tsx` | new file | admin UI unit tests | ui-engineer-enhanced |

---

## Testing Strategy

### Unit Tests

- `AuthContext.tsx`: dispatch logic for all 3 modes; FR-2 resilience (missing identity, missing
  roles array).
- `AppShell.tsx`: role-gated `NAV_ITEMS` computation for each of the 5 roles + the
  missing-roles-array case.
- `client.ts`: extended `p5-auth-header.test.ts` — per-provider token resolution + 403 case.
- `SettingsScreen.tsx` / `AdminSettings/*`: new `p5-admin-settings.test.tsx` — role-gating +
  per-panel resilience when a backing field is absent/null.

### Integration Tests

- `AuthContext` + `AppShell` + `client.ts` wired together against mocked `AuthProvider` states
  (Clerk mocked hook, local_static mocked session, none passthrough) to confirm no cross-module
  drift.

### E2E Tests (if applicable)

- Not owned by this phase — Phase 9's `p5-auth-rbac.spec.ts` provides full E2E coverage (static +
  live modes). `FEAUTH-901`'s runtime smoke is the phase-local pre-check, explicitly
  cross-referenced to Phase 9 in its Completion Report note.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Optimistic UI-only role check drifts from real server enforcement (the exact failure mode PRD risk table warns against) | High | `FEAUTH-900` seam verification explicitly tests the mutation path, not just the nav-hide state; server (P5.2/P5.3) remains the actual boundary regardless of FE state. |
| Clerk SDK bundled into the static-export build, bloating an offline-first artifact | Medium | `AuthContext.tsx` gates the Clerk import behind the resolved provider; verified in `FEAUTH-901`'s static-export smoke check. |
| ICA-produced `AdminSettings/*` subcomponents diverge from house `rv-*`/`it-*` CSS convention | Medium | `task-completion-validator` review is mandatory before any ICA output is accepted (Offload Plan). |
| Missing `roles` array silently defaults to elevated privilege instead of least-privilege | High | AC-5c is a first-class structured AC with its own `verified_by` tasks (`FEAUTH-001`, `FEAUTH-002`, `FEAUTH-900`). |
| Admin settings UI shape drifts from Phase 6's actual API contract if built before that phase lands | Medium | `FEAUTH-004` depends on Phase 6's admin API by contract reference; `FEAUTH-900`'s `GATE-900`/`GATE-901` sub-items re-verify the seam once both phases are complete. |

---

## Success Metrics

- **Completion**: All 6 tasks (`FEAUTH-001` through `FEAUTH-004`, `FEAUTH-900`, `FEAUTH-901`)
  checked off.
- **Quality**: All quality gates passed, including seam verification and runtime smoke.
- **Performance**: No added client-side auth-check latency beyond local identity resolution.
- **Testing**: `p5-auth-header.test.ts` (extended) and `p5-admin-settings.test.tsx` green;
  `npm run build` passes; Playwright auth spec (Phase 9) passes once landed.

---

## Notes

### Implementation Approach

Build `AuthContext.tsx` and the role-gating wiring first (Claude, MUST-stay), then extend
`client.ts`'s identity threading, then build the admin settings UI (composition on Claude,
subcomponents optionally on ICA), and close with the seam verification and runtime smoke tasks —
in that order, since `FEAUTH-900`/`FEAUTH-901` require all four preceding tasks complete.

### Gotchas

- **`AppShell.tsx`'s existing "Agents: disabled" entry is unrelated to auth** — it's a
  not-yet-shipped-feature flag (Phase 4), not a role gate. Don't conflate the two `disabled`
  reasons; keep them visually/textually distinct.
- **Static-export mode has no server at all** — do not assume any auth-context code path can make
  a network call in that build target; everything must resolve to the pre-gated export-time
  dataset.
- **Phase 6's admin API contract may not be frozen when `FEAUTH-004` starts** — build against the
  contract reference, not a guessed shape; re-verify in `FEAUTH-900`'s `GATE-900`/`GATE-901`
  sub-items once both phases are complete.

### Learnings

[Capture learnings as phase progresses]

### Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
