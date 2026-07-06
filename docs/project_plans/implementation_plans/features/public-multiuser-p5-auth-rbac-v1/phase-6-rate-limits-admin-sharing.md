---
title: "Phase 6: Rate Limits + Admin Settings + Sharing/Publish-Preview Gates"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
phase: 6
phase_title: "Rate Limits + Admin Settings + Sharing/Publish-Preview Gates"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.3 workspace isolation enforced (migration complete + Human gate #1 passed)"
exit_criteria:
  - "Rate limit enforced and tested"
  - "Share link respects sensitivity threshold"
  - "publish-preview returns 422 on any sensitivity violation regardless of role"
  - "karen public-exposure-milestone sign-off"
  - "task-completion-validator sign-off"
related_documents:
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-2-rbac-enforcement.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-8-auth-context-ui.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: python-backend-engineer
ui_touched: true
target_surfaces:
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/api/middleware/rate_limit.py
  - src/research_foundry/api/routers/admin.py
  - src/research_foundry/services/rbac_store.py
  - foundry.yaml
  - frontend/runs-viewer/src/pages/SettingsPage.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/app/AppShell.tsx
seam_tasks:
  - GATE-900
  - GATE-901
owner: python-backend-engineer
contributors: [python-backend-engineer, ui-engineer]
priority: high
risk_level: high
category: "product-planning"
tags: [phase-plan, implementation, auth, rbac, rate-limiting, admin-settings, sharing, public-exposure]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/api/middleware/rate_limit.py
  - src/research_foundry/api/routers/admin.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/config.py
  - foundry.yaml
  - frontend/runs-viewer/src/pages/SettingsPage.tsx
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/test/p5-auth-header.test.ts
---

# Phase 6: Rate Limits + Admin Settings + Sharing/Publish-Preview Gates

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~2-3 days (5 points @ sonnet/adaptive, one primary + one secondary agent, no offload)
**Effort**: 5 story points
**Dependencies**: P5.3 complete (workspace isolation migration enforced + Human gate #1 passed)
**Team Members**: `python-backend-engineer` (primary — rate limiting, admin API, sharing gate), `ui-engineer` (secondary — `/settings` UI extension, frontend resilience gates)

---

## Phase Overview

This is the **public-exposure gates** phase of the P5 Auth/RBAC feature — the last backend-hardening
phase before public/LAN-shared traffic is safe to accept. It has three distinct, non-overlapping
sub-areas — treat them as separate task groups, not a blended backend sprint:

1. **Rate limiting** — a per-identity + per-route sliding-window limiter (LOCKED decision D6/FR-9;
   explicitly **not** a global budget), config-driven in `foundry.yaml`, returning `429` +
   `Retry-After` on exceed.
2. **Admin settings** — workspace/member/role management, auth-provider status, and rate-limit
   config, exposed via a backend API and a **minimal** extension of the existing `/settings` route
   (do not fork a new top-level route — Phase 8 builds the fuller admin UI on top of this).
3. **Sharing / publish-preview gates** — read-only, sensitivity-scoped share links (LOCKED decision
   D5; general public URLs are explicitly **deferred/out-of-scope** — do not build them), and an
   extension of the existing P2/P3 `verify_draft`/D13 fail-closed checks in
   `reports.py::publish_preview` so sensitivity fail-closed holds **independent of role** — this is
   the PRD's AC-2, reproduced verbatim in Task P5.6-T4 below.

Two mandatory resilience gates (R-P2) close the loop between this phase's new backend fields and
the frontend that consumes them, and simultaneously serve as this phase's cross-owner seam
verification (R-P3): **GATE-900** (rate-limit state) and **GATE-901** (admin-settings fields). Their
task IDs are locked — **Phase 8 (frontend auth-context UI) references them verbatim.**

### Goals

- Ship an enforceable, config-driven rate limiter that cannot be bypassed by omitting a route.
- Give an operator/admin a real (if minimal) settings surface to manage members, roles, provider
  status, and rate-limit budget without touching `foundry.yaml` by hand.
- Close the sharing/publish gap: a report can be shared read-only, sensitivity-scoped, and no role
  — including `owner` — can bypass a sensitivity failure.
- Guarantee the frontend degrades safely (never crashes, never shows a false-positive "rate
  limited" or a broken admin panel) when either new backend field is absent.

### Architecture Focus

This phase implements the **API + Service** layer (rate limiter, admin API, sharing gate) and a
**minimal UI** layer (settings extension), following Research Foundry's layered architecture:
- **Layer**: Service → API (rate limiter, admin router, sharing gate) → UI (settings extension).
- **Patterns**: reuse P5.2's `require_role(...)` dependency for every admin mutation route (no
  bespoke auth check); reuse P2/P3's `verify_draft`/D13 fail-closed pattern for the sharing gate
  (extend, don't reimplement); reuse P5.1's `AuthIdentity`/durable RBAC store (`rbac_store.py`) for
  admin member/role reads-writes — never the disposable `catalog.db` (D2 lesson from P2/P3).
- **Standards**: fail-closed by default (ambiguous state → deny/block, never permissive); no
  UI-only gating — the `/settings` extension is a convenience surface, the server remains the
  authority.

---

## Reviewer Gates (both mandatory — do not skip either)

| Gate | Trigger | Notes |
|------|---------|-------|
| `task-completion-validator` | End of phase, before `karen` | Standard per-phase gate (every P5 phase requires this). |
| `karen` | End of phase, **public-exposure milestone** | One of only 3 `karen` checkpoints in the whole P5 plan (alongside P5.3 isolation and P5.9 end-of-feature). Validates that the rate limiter is not bypassable, the sharing gate is role-independent, and the admin UI does not leak anything server-side RBAC should be blocking. |

Do not advance to `karen` until `task-completion-validator` has passed. Do not merge this phase
until both have signed off.

---

## Task Breakdown

### Epic: Rate Limiting

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-----------------------|-------|--------|--------------|
| P5.6-T1 | Rate-limit middleware | Per-identity + per-route sliding-window limiter, config-driven budget | See Task P5.6-T1 below | 1.5 pts | python-backend-engineer | sonnet | adaptive | None (consumes P5.1 `AuthIdentity`) |

### Epic: Admin Settings

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-----------------------|-------|--------|--------------|
| P5.6-T2 | Admin settings backend API | Workspace/member/role management + auth-provider status + rate-limit config endpoints | See Task P5.6-T2 below | 1.5 pts | python-backend-engineer | sonnet | adaptive | P5.6-T1 (rate-limit config shape) |
| P5.6-T3 | Admin settings UI extension | Minimal extension of existing `/settings` route consuming P5.6-T2's API | See Task P5.6-T3 below | 0.5 pts | ui-engineer | sonnet | adaptive | P5.6-T2 |

### Epic: Sharing & Publish-Preview Gates

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-----------------------|-------|--------|--------------|
| P5.6-T4 | Sharing/publish-preview gate extension | Read-only sensitivity-scoped share links; role-independent fail-closed `publish_preview` (PRD AC-2) | See Task P5.6-T4 below (AC-2, verbatim) | 1.0 pt | python-backend-engineer | sonnet | adaptive | Entry criteria (P5.3) only — otherwise independent |

### Epic: Cross-Cutting Resilience Gates (R-P2 — mandatory)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-----------------------|-------|--------|--------------|
| GATE-900 | AC: FE handles missing rate-limit-state field | Absent field ⇒ FE assumes no active limit, renders nothing | See Task GATE-900 below | 0.25 pts | ui-engineer | sonnet | adaptive | P5.6-T1 |
| GATE-901 | AC: FE handles missing admin-settings fields | Absent field(s) ⇒ FE disables the affected admin-panel section, does not crash | See Task GATE-901 below | 0.25 pts | ui-engineer | sonnet | adaptive | P5.6-T2, P5.6-T3 |

**Points Summary**: 1.5 + 1.5 + 0.5 + 1.0 + 0.25 + 0.25 = **5.0 pts** ✓

**Model Selection Guidance**: `sonnet` / `adaptive` across all tasks in this phase — no ICA/Codex
offload (explicit decision-block routing for P5.6; this phase gates public exposure and stays on
the primary Claude subscription end to end).

---

## Detailed Task Specifications

### Task P5.6-T1: Rate-limit middleware

**Estimate**: 1.5 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: None (consumes `AuthIdentity` from P5.1; does not depend on P5.2/P5.3 role logic)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Implement a per-identity + per-route sliding-window rate limiter (LOCKED decision D6/FR-9 — **not**
a global budget). Budget is config-driven in `foundry.yaml` (e.g., requests-per-window and
window-seconds, under a new `auth.rate_limit` block). On exceed, the request is rejected with HTTP
`429` and a `Retry-After` header giving seconds until the caller's window resets. The counter is
in-process/local (NFR: no synchronous network round-trip added per request — see PRD §6.2
Performance).

**Acceptance Criteria**:
- [ ] Limiter keys on `(AuthIdentity.user_id, route)` — never a single global counter (D6/FR-9).
- [ ] Budget (requests-per-window, window-seconds) is configurable via `foundry.yaml` with a
      documented default that does not break existing single-operator (`auth_mode=none`) usage.
- [ ] Exceeding the budget returns `429` with a `Retry-After` header (seconds remaining in window).
- [ ] Counter is in-process/local — no added synchronous network round-trip (NFR §6.2).
- [ ] `auth_mode=none` (legacy single-operator) either exempts the limiter or applies a generous
      default that does not regress existing air-gapped deployments.

**Implementation Notes**:
- Mirror the middleware-registration idiom already used by `TokenAuthMiddleware`
  (`api/middleware/auth.py`) — resolve/attach at `create_app` time, gated by a `foundry.yaml` flag
  (`auth.rate_limit.enabled`, default `true` once shipped per PRD §8 Feature Flags).
- Sliding window (not fixed window) avoids the boundary-burst problem of naive fixed-window
  counters; a simple in-memory ring-buffer or token-bucket-per-key implementation is sufficient —
  do not introduce a new external dependency (e.g., Redis) for this.
- This task defines the exact shape of the "rate-limit-state" field/header that GATE-900 depends
  on (e.g., `X-RateLimit-Remaining`/`X-RateLimit-Reset` headers, or a JSON field on relevant
  responses) — document the chosen shape in the task's evidence/commit so GATE-900 can consume it.

**Files Involved**:
- `src/research_foundry/api/middleware/rate_limit.py` — new limiter implementation.
- `src/research_foundry/config.py` — `auth.rate_limit` config schema.
- `foundry.yaml` — new `auth.rate_limit` block; document with the same care as the existing
  `viewer.sensitivity_threshold` comment block (PRD Documentation Acceptance).
- `src/research_foundry/api/app.py` — wire the limiter at app-creation time.

---

### Task P5.6-T2: Admin settings backend API

**Estimate**: 1.5 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: P5.6-T1 (rate-limit config shape must exist to expose/edit it here)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Add the admin settings API surface (FR-10): workspace/member/role management, auth-provider status,
and rate-limit configuration — all gated by P5.2's `require_role(...)` dependency (owner/admin
only; no bespoke auth check invented here). Reads and writes the durable RBAC store
(`rbac_store.py`, from P5.1) for member/role state — never `catalog.db`.

**Acceptance Criteria**:
- [ ] `GET /api/admin/workspace` returns members + roles for the caller's workspace; owner/admin
      only (`require_role`), 403/404 for anyone else consistent with the existing no-existence-leak
      convention.
- [ ] `PATCH /api/admin/members/{user_id}/role` updates a member's role; owner/admin only.
- [ ] `GET /api/admin/auth-provider-status` returns the active provider + availability; **never**
      returns raw credentials, JWKS secrets, or Clerk secret keys in the payload (NFR §6.2
      Security).
- [ ] `GET`/`PATCH /api/admin/rate-limit-config` reads/updates the P5.6-T1 rate-limit budget;
      owner/admin only.
- [ ] Every admin mutation route depends on P5.2's `require_role(...)` — no route invents its own
      authorization check.

**Implementation Notes**:
- This is the API contract GATE-901 depends on — document the exact response shape (which fields
  can legitimately be absent, e.g., a viewer-role caller getting a trimmed payload) so the FE
  resilience task has a concrete contract to test against.
- If P5.5 (audit log) has landed by the time this task executes, admin mutations SHOULD emit an
  `audit_event` row (role changes are exactly the kind of governed mutation P5.5 exists to capture)
  — this is a nice-to-have composition, not a hard dependency; do not block this task on P5.5.

**Files Involved**:
- `src/research_foundry/api/routers/admin.py` — new router.
- `src/research_foundry/services/rbac_store.py` — read/write member-role state (from P5.1).
- `src/research_foundry/config.py` — surface rate-limit config for read/update.

---

### Task P5.6-T3: Admin settings UI extension

**Estimate**: 0.5 points
**Assigned Subagent(s)**: ui-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: P5.6-T2
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Extend the **existing** `/settings` route with a minimal admin panel section: member/role list +
role-change control, auth-provider status (read-only), and rate-limit config display/edit —
owner/admin-gated on the client (server remains the authority). **Do not fork a new top-level
route.** This is intentionally minimal: Phase 8 (P5.8) builds the fuller admin UI + role-gated
affordances across the app shell; this task only wires enough of the `/settings` extension to
consume P5.6-T2's API and satisfy GATE-901.

**Acceptance Criteria**:
- [ ] Locate the existing `/settings` route/page component via `codebase-explorer` first (exact
      path not pre-verified in this plan — likely `frontend/runs-viewer/src/pages/SettingsPage.tsx`
      or similar); extend it, do not create a new route.
- [ ] Renders member/role list + auth-provider status + rate-limit config when the admin-settings
      API fields are present.
- [ ] Section is role-gated client-side (rendered/enabled only for owner/admin identity) — this is
      a UX convenience, not a security control; the server (P5.6-T2's `require_role`) remains
      authoritative.
- [ ] Structure composes cleanly with Phase 8's fuller admin UI build — no throwaway scaffolding
      that Phase 8 has to rip out.

**Implementation Notes**:
- Use `frontend/runs-viewer/src/api/client.ts` for the new admin API calls, following the existing
  `loopbackGet()` contract pattern already used for auth headers (`p5-auth-header.test.ts`).
- Keep this genuinely minimal — a full admin dashboard is explicitly Phase 8's job.

**Files Involved**:
- `frontend/runs-viewer/src/pages/SettingsPage.tsx` — path to confirm via `codebase-explorer`;
  extend the existing `/settings` route's page component.
- `frontend/runs-viewer/src/api/client.ts` — new admin API client calls.

---

### Task P5.6-T4: Sharing/publish-preview gate extension (PRD AC-2)

**Estimate**: 1.0 point
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: Entry criteria only (P5.3 workspace isolation) — otherwise independent of the
other tasks in this phase.
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Ship the v1 public-sharing primitive (LOCKED decision D5): **read-only, sensitivity-scoped share
links only** — general public URLs are explicitly deferred/out-of-scope; do not build them. Extend
P2/P3's existing `verify_draft`/D13 fail-closed checks in `reports.py::publish_preview` (reuse, do
not reimplement) so that sensitivity fail-closed holds **independent of the caller's role** — an
`owner` cannot bypass a sensitivity failure by role alone. This is the PRD's AC-2, reproduced
verbatim below per the AC schema.

**Acceptance Criteria** (structured, per `.claude/skills/planning/references/ac-schema.md` — reused
verbatim from PRD §11 AC-2):

#### AC-2: Public report export fails closed on sensitivity violations
- target_surfaces:
    - src/research_foundry/api/routers/reports.py
    - src/research_foundry/services/builder_service.py
    - src/research_foundry/services/verification.py
    - src/research_foundry/services/export_service.py
- propagation_contract: >
    The sharing/publish flow reuses the D13 `verify_draft` fail-closed checks (`publish_preview`)
    plus the new global-source-index check (FR-14); any error-severity failure blocks publication
    (HTTP 422) independent of the caller's role — an owner cannot bypass a sensitivity failure by
    role alone.
- resilience: >
    If the sensitivity label or global source index is unavailable/unresolvable, the check fails
    closed (blocks publish) rather than defaulting to permissive.
- visual_evidence_required: false
- verified_by:
    - publish-preview-fail-closed-regression
    - blank-origin-draft-sensitivity-regression

> **Scope note on `verified_by`**: `publish-preview-fail-closed-regression` is this task's own
> regression test (owned here, P5.6). `blank-origin-draft-sensitivity-regression` is the global
> source index closure and belongs to **P5.7** (FR-14) — this task composes with it (the
> `publish_preview` check calls into the global source index once P5.7 lands) but does **not**
> re-implement FR-14. Do not duplicate P5.7's work in this task.

**Additional acceptance criteria (this task's own scope, beyond the reused AC-2 block)**:
- [ ] A new read-only, sensitivity-scoped share-link mechanism exists (e.g., a scoped share token
      resolvable to a report at the caller's threshold) — **no general public URL surface** (D5).
- [ ] The share-link record lives in a **durable** store (e.g., the P5.1 `.rf_state/rbac.db` or a
      dedicated durable shares table) — **never** the disposable `catalog.db` (D2 lesson from
      P2/P3: `catalog.db` drops+rebuilds on `user_version` mismatch and would silently invalidate
      live share links).
- [ ] `publish_preview` returns `422` on any error-severity sensitivity failure, tested explicitly
      with an `owner`-role caller to prove role cannot override the block.
- [ ] Share-link resolution (read time) re-applies the same sensitivity threshold check as export —
      it does not trust a check performed only at link-creation time.

**Implementation Notes**:
- Reuse existing D13 checks in `reports.py::publish_preview` — this is an extension task, not a
  rewrite. Do not touch the underlying `verify_draft` failure-severity logic beyond what's needed
  to plug in the share-link path.
- Keep the share-link mechanism deliberately small (v1 scope, D5) — a token/slug plus a durable
  lookup row is sufficient; do not build account-less public URL infrastructure.

**Files Involved**:
- `src/research_foundry/api/routers/reports.py` — sharing endpoint(s) + `publish_preview` role-
  independence hardening.
- `src/research_foundry/services/builder_service.py` — share-link creation/lookup plumbing.
- `src/research_foundry/services/verification.py` — `verify_draft` composition point.
- `src/research_foundry/services/export_service.py` — sensitivity-threshold reuse at share-link
  read time.

---

### Task GATE-900: AC — FE handles missing rate-limit-state field

**Estimate**: 0.25 points
**Assigned Subagent(s)**: ui-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: P5.6-T1
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Mandatory R-P2 resilience task: P5.6-T1 introduces a new backend field/header (rate-limit state —
remaining/limit/reset). This field may legitimately be absent (limiter disabled, older proxy strips
headers, `auth_mode=none`). The frontend must treat absence as **"no active limit"** and render
nothing — never surface a false "you are rate limited" banner. This task doubles as this phase's
R-P3 seam-verification task (backend-produced field → frontend-consumed contract).

**Acceptance Criteria** (structured, per ac-schema.md):

#### AC GATE-900: FE handles missing rate-limit-state field
- target_surfaces:
    - frontend/runs-viewer/src/api/client.ts
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: >
    P5.6-T1's rate-limit middleware attaches rate-limit state (remaining/limit/reset) via response
    header or field on rate-limited routes; `client.ts` parses it opportunistically and exposes it
    to `AppShell`'s rate-limit-status indicator.
- resilience: >
    When the field/header is absent, `client.ts` treats it as `null`/undefined and `AppShell`
    renders no rate-limit UI at all — no banner, no false "you are being rate limited" state.
    Absence means "no active limit," never an error or a degraded-but-visible state.
- visual_evidence_required: false
- verified_by:
    - GATE-900

**Acceptance Criteria (checklist)**:
- [ ] Absent rate-limit-state field ⇒ `AppShell` renders no rate-limit affordance at all (not a
      disabled/greyed one — genuinely absent).
- [ ] Present-and-under-budget state ⇒ no banner (only near-limit/exceeded states render anything).
- [ ] Present-and-exceeded state (429 response) ⇒ surfaces the `Retry-After` value to the caller.
- [ ] Unit test added/extended in `p5-auth-header.test.ts` covering the missing-field case.

**Implementation Notes**:
- This task's evidence (screenshot) satisfies this phase's R-P4 "runtime smoke" quality gate — see
  Quality Gates below.

**Files Involved**:
- `frontend/runs-viewer/src/api/client.ts` — parse rate-limit-state field/header, tolerate absence.
- `frontend/runs-viewer/src/app/AppShell.tsx` — conditional rate-limit-status indicator.
- `frontend/runs-viewer/src/test/p5-auth-header.test.ts` — extend with the missing-field case.

---

### Task GATE-901: AC — FE handles missing admin-settings fields

**Estimate**: 0.25 points
**Assigned Subagent(s)**: ui-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: P5.6-T2, P5.6-T3
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Mandatory R-P2 resilience task: P5.6-T2 introduces new admin-settings API fields (member/role list,
auth-provider status, rate-limit config). Any of these may be absent (partial response, a
permission-trimmed payload for a non-owner caller, an older backend). The frontend must **disable
the affected admin-panel section independently** rather than crash or render a broken/partial
control. This is this phase's second R-P3 seam-verification task.

**Acceptance Criteria** (structured, per ac-schema.md):

#### AC GATE-901: FE handles missing admin-settings fields
- target_surfaces:
    - frontend/runs-viewer/src/pages/SettingsPage.tsx
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: >
    P5.6-T2's admin settings API returns member/role list, auth-provider status, and rate-limit
    config fields; the P5.6-T3 `/settings` UI extension reads them via `client.ts` and renders the
    admin panel section conditionally.
- resilience: >
    If any admin-settings field is missing/null (partial API response, permission-trimmed payload,
    or an older backend), the FE disables **only the affected subsection** (member list, provider
    status, or rate-limit config) rather than crashing or rendering a broken/partial control. Each
    subsection degrades independently — one missing field does not take down the whole panel.
- visual_evidence_required: false
- verified_by:
    - GATE-901

**Acceptance Criteria (checklist)**:
- [ ] Missing member/role list ⇒ that subsection disables with a clear "unavailable" state; other
      subsections render normally.
- [ ] Missing auth-provider status ⇒ that subsection disables independently.
- [ ] Missing rate-limit config ⇒ that subsection disables independently.
- [ ] No subsection's absence throws an unhandled error or blanks the entire `/settings` page.
- [ ] Unit test added/extended in `p5-auth-header.test.ts` (or a new admin-settings-specific test)
      covering each missing-field case independently.

**Implementation Notes**:
- This task's evidence (screenshot) also satisfies this phase's R-P4 "runtime smoke" quality gate
  — see Quality Gates below.

**Files Involved**:
- `frontend/runs-viewer/src/pages/SettingsPage.tsx` — per-subsection resilience.
- `frontend/runs-viewer/src/api/client.ts` — tolerate partial admin-settings payloads.

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: rate limiter enforces per-identity+per-route budgets; admin API + UI
      extension work end-to-end; sharing/publish-preview gate blocks on any sensitivity violation
      regardless of role.
- [ ] **Testing**: unit tests for the sliding-window limiter, admin API role gating, and
      `publish_preview` role-independence; integration test for the full sharing flow.
- [ ] **Performance**: rate-limit check adds no synchronous network round-trip (NFR §6.2).
- [ ] **Security**: auth-provider-status endpoint never returns raw credentials/secrets; share
      links are read-only and sensitivity-scoped (no general public URL surface, D5).
- [ ] **Documentation**: `foundry.yaml`'s new `auth.rate_limit` block documented with the same care
      as `viewer.sensitivity_threshold`.
- [ ] **Code Quality**: linting/type-checks pass for all new backend and frontend files.
- [ ] **Architecture**: reuses P5.1 `AuthIdentity`/`rbac_store.py`, P5.2 `require_role(...)`, and
      P2/P3 `verify_draft`/D13 — no bespoke parallel auth or sensitivity-check mechanism invented.
- [ ] **Seam verification** (`integration_owner: python-backend-engineer`): GATE-900 and GATE-901
      (`seam_tasks`) are completed and their `verified_by` references are populated (R-P3).
- [ ] **Runtime smoke** (`ui_touched: true`): screenshot evidence in
      `.claude/evidence/phase-6/` for both GATE-900 (rate-limit-state absence) and GATE-901
      (admin-settings field absence) — a clean unit-test pass alone is not a substitute (R-P4).

---

## Integration Points

### External Systems

- **None new** — this phase does not introduce a new external dependency (no Redis, no external
  rate-limit service). The rate limiter is in-process by design (NFR §6.2).

### Internal Systems

- **P5.1 (`AuthProvider` / `rbac_store.py`)**: rate limiter keys on `AuthIdentity.user_id`; admin
  API reads/writes member/role state in the same durable store.
- **P5.2 (`require_role(...)`)**: every admin mutation route in P5.6-T2 depends on this — no new
  authorization mechanism is introduced.
- **P5.3 (workspace isolation)**: entry criterion — admin workspace/member listing must already be
  workspace-scoped by the time this phase executes.
- **P2/P3 (`verify_draft` / D13 fail-closed checks)**: P5.6-T4 extends this existing mechanism; it
  is not reimplemented.
- **P5.5 (audit log, parallel)**: admin mutations SHOULD emit an audit row once P5.5 lands — a
  soft/opportunistic composition, not a hard dependency for this phase.
- **P5.7 (global source index, parallel)**: `blank-origin-draft-sensitivity-regression` (part of
  AC-2's `verified_by`) is P5.7's deliverable — this phase composes with it, does not implement it.
- **P5.8 (frontend auth-context UI, downstream)**: consumes this phase's rate-limit-state and
  admin-settings API contracts; GATE-900/GATE-901 task IDs are referenced verbatim by Phase 8 — do
  not renumber them.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/api/middleware/rate_limit.py` | New sliding-window rate limiter | python-backend-engineer |
| `src/research_foundry/api/routers/admin.py` | New admin settings API router | python-backend-engineer |
| `src/research_foundry/api/routers/reports.py` | Sharing endpoint + `publish_preview` role-independence hardening | python-backend-engineer |
| `src/research_foundry/services/rbac_store.py` | Admin API reads/writes member/role state | python-backend-engineer |
| `src/research_foundry/services/builder_service.py` | Share-link creation/lookup plumbing | python-backend-engineer |
| `src/research_foundry/services/verification.py` | `verify_draft` composition for sharing gate | python-backend-engineer |
| `src/research_foundry/services/export_service.py` | Sensitivity-threshold reuse at share-link read time | python-backend-engineer |
| `src/research_foundry/config.py` | Rate-limit + admin config schema | python-backend-engineer |
| `foundry.yaml` | New `auth.rate_limit` config block | python-backend-engineer |
| `frontend/runs-viewer/src/pages/SettingsPage.tsx` | Minimal admin panel extension to existing `/settings` | ui-engineer |
| `frontend/runs-viewer/src/api/client.ts` | Admin API calls + rate-limit-state parsing | ui-engineer |
| `frontend/runs-viewer/src/app/AppShell.tsx` | Rate-limit-status indicator (GATE-900) | ui-engineer |

---

## Testing Strategy

### Unit Tests

- Sliding-window limiter: budget enforcement, window reset, `Retry-After` calculation, per-(user,
  route) key isolation (one user's burst does not throttle another).
- Admin API: role gating on every route (owner/admin allowed, other roles 403), no-secrets-in-
  payload assertion on auth-provider-status.
- `publish_preview`: role-independence — parametrize the fail-closed test across all 5 roles,
  including `owner`, and assert `422` fires identically regardless of role.
- Frontend: `p5-auth-header.test.ts` extended for GATE-900 (missing rate-limit-state) and GATE-901
  (missing admin-settings fields, each subsection independently).

### Integration Tests

- Full sharing flow: create a share link, resolve it at read time, confirm the sensitivity
  threshold check re-applies (not just at creation time).
- End-to-end rate-limit exceed scenario against a live route: confirm `429` + `Retry-After`.
- Admin settings round-trip: `PATCH` a member's role via the API, confirm it persists in
  `rbac_store.py` and is reflected on next `GET`.

### E2E Tests (if applicable)

- Not owned by this phase — P5.9 (`p5-auth-rbac.spec.ts`) is the canonical E2E owner and will
  incorporate scenarios exercised here (sharing link, admin settings, rate-limit-state UI). This
  phase's unit/integration tests plus the GATE-900/901 runtime-smoke screenshots are the
  phase-local verification; do not duplicate full E2E here.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Rate limiting causes false-positive lockouts or a performance regression for legitimate burst usage | Medium | Config-driven sane defaults; per-identity+per-route granularity (not global) so one user cannot starve another; in-process counter (no network round-trip). |
| Admin settings UI balloons into duplicate work with Phase 8's fuller admin build | Medium | Explicit "minimal" scope boundary in Task P5.6-T3; single shared `/settings` route; composability called out as an acceptance criterion. |
| Sharing gate has a role-bypass regression (an owner circumvents a sensitivity failure) | High | AC-2's fail-closed test is parametrized explicitly across all 5 roles including `owner`; `karen` public-exposure milestone specifically reviews this. |
| Share-link record lands in the disposable `catalog.db` by mistake, silently invalidating live links on a cache rebuild | High | Explicit acceptance criterion in Task P5.6-T4 requiring a durable store (D2 lesson called out inline). |
| `karen` public-exposure milestone surfaces a gap late in the phase | Medium | `task-completion-validator` runs first and must pass before `karen` is invoked; do not treat validator silence as a pass (see project memory on silent-reviewer gotcha). |

---

## Success Metrics

- **Completion**: all 6 tasks (P5.6-T1 through T4, GATE-900, GATE-901) checked off, summing to 5.0
  points.
- **Quality**: both reviewer gates (`task-completion-validator` + `karen` public-exposure
  milestone) passed.
- **Performance**: rate-limit check adds 0 synchronous network round-trips; no measurable p95
  latency regression on rate-limited routes beyond the in-process check itself.
- **Testing**: role-parametrized `publish_preview` fail-closed test green across all 5 roles;
  GATE-900/GATE-901 missing-field unit tests green; runtime-smoke screenshots captured for both.

---

## Notes

### Implementation Approach

Execute the three epics largely in parallel within the phase (Rate Limiting and Sharing/Publish
Gates share no files and no owner dependency), then close with the two cross-cutting resilience
gates once their respective backend contracts (P5.6-T1, P5.6-T2/T3) are frozen. Admin Settings is
internally sequential (backend API before UI extension).

### Gotchas

- **Task IDs `GATE-900` and `GATE-901` are locked** — Phase 8 (frontend auth-context UI) references
  them verbatim. Do not renumber or rename them during execution.
- **D5 boundary**: sharing v1 is read-only, sensitivity-scoped links only. Do not build a general
  public URL surface here even if it looks like a small extension — that is explicitly deferred.
- **D2 lesson (from P2/P3)**: any new durable state this phase introduces (share-link records) must
  not land in `catalog.db` — it is disposable and drops+rebuilds on `user_version` mismatch.
- **No UI-only gating**: the `/settings` extension's role-gating is a UX convenience; P5.6-T2's
  `require_role(...)` on the backend is the actual control. Do not treat client-side hiding as
  sufficient (Mode-D gate 6 precedent from P5.2).

### Learnings

_Capture as phase progresses._

### Findings Captured This Phase

- [x] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
