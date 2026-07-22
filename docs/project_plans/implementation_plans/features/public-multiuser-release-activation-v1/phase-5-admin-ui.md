---
title: "Phase 5: Admin UI"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P5
phase_title: "Admin UI"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
entry_criteria:
  - "P3 sealed — admin API routes exist and are reviewed; UI must not ship ahead of backend (Risk: decisions-block §3)."
exit_criteria:
  - "AC-1 (one-time-secret UX + principal-type surfacing) green."
  - "a11y smoke (WCAG 2.1 AA) passed."
  - "task-completion-validator pass."
---

# Phase 5: Admin UI

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 6 pts
**Dependencies**: P3 (full phase) — deliberately sequenced last among backend-adjacent phases
**Assigned Subagent(s)**: `ui-engineer-enhanced` (primary); `a11y-sheriff` (jest-axe on new panels)
**Model**: sonnet | **Effort**: adaptive
**Mode**: C — Autonomous Feature Sprint (additive panels over an existing, reviewed admin surface)

## Overview

Two new admin panels and an `AuthContext.tsx` extension, additive to the existing `AdminSettings/RoleAssignmentPanel.tsx` surface — no new route tree. The one-time-secret display UX is the highest-risk UI element in this phase: the plaintext secret must never persist beyond local component state.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-501 | Admin UI — service accounts panel | `ServiceAccountsPanel.tsx`: issue (name + role) / list / revoke / rotate, one-time-secret display with copy-and-dismiss UX. Consumes `GET/POST/DELETE /api/admin/service-accounts` and `POST .../{id}/tokens`. | FR-16 (service-account subset) satisfied; secret held only in local component state, cleared on dismiss/navigation, never persisted to a store or URL. | 2.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3 sealed |
| ACT-502 | Admin UI — PATs panel + auth-context | `PersonalAccessTokensPanel.tsx`: self-issue (role ≤ own role) / list / revoke. `AuthContext.tsx` extended to expose `principalType: "human" \| "service" \| "user_pat"` to consuming components. | FR-16 (PAT subset) satisfied; `principalType` correctly derived from resolved identity (token-store row or Clerk session). | 2.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3 sealed |
| ACT-503 | R-P4 runtime smoke + a11y pass | Runtime-smoke task (mandatory per R-P4, this phase touches `.tsx` files): exercise every `target_surfaces` entry in AC-1 — issue/list/revoke/rotate round-trip against a live API, plus WCAG 2.1 AA automated pass (`jest-axe`) matching the existing `RoleAssignmentPanel`/`AuthProviderStatusPanel` baseline. | AC-1 fully green across all 4 target surfaces; a11y tests pass with zero new violations. | 1 pt | ui-engineer-enhanced + a11y-sheriff | sonnet | adaptive | ACT-501, ACT-502 |
| REV-P5-001 | Reviewer gate: task-completion-validator | Standard phase-completion review. | Validator confirms FR-16 satisfied, AC-1 green. | gate | task-completion-validator | sonnet | adaptive | ACT-503 |

**Phase point subtotal**: 6 pts (reviewer-gate row excluded).

## Structured Acceptance Criteria

#### AC-1: Admin UI reflects principal type and secret lifecycle correctly across the identity-admin surface
*(Reproduced from PRD §11; this is P5's primary exit-gate AC.)*
- target_surfaces:
    - frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx
    - frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx
    - frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx
    - frontend/runs-viewer/src/auth/AuthContext.tsx
- propagation_contract: >
    `AuthContext.tsx` exposes `principalType` derived from the resolved identity's token-store row
    (service/user_pat) or Clerk session (human); `ServiceAccountsPanel`/`PersonalAccessTokensPanel`
    consume `GET /api/admin/service-accounts` and `GET /api/admin/pats` for list state, and the
    one-time plaintext secret is held only in local component state (never persisted to a store or
    URL) after a `POST` issue call, cleared on dismiss/navigation.
- resilience: >
    If `principalType` is absent from the resolved identity payload (e.g., older cached session),
    panels render the human-session default (no principal-type badge) rather than erroring;
    revoke/rotate buttons disable with a tooltip if the admin API call for status is unavailable.
- visual_evidence_required: false
- verified_by:
    - ACT-503
    - ACT-602 (Phase 6, E2E issue-revoke round trip)

## Quality Gates

- [ ] `ServiceAccountsPanel.tsx`: issue/list/revoke/rotate all functional against the live admin API.
- [ ] `PersonalAccessTokensPanel.tsx`: self-issue (role ≤ own role)/list/revoke functional.
- [ ] `AuthContext.tsx` correctly surfaces `principalType` for all three identity shapes.
- [ ] One-time secret never persists beyond local component state (verified in ACT-503).
- [ ] WCAG 2.1 AA compliance (`jest-axe`) — zero new violations vs. existing `AdminSettings` baseline.
- [ ] `task-completion-validator` pass (REV-P5-001).

## Key Files & Integration Points

- `frontend/runs-viewer/src/components/AdminSettings/ServiceAccountsPanel.tsx` (new)
- `frontend/runs-viewer/src/components/AdminSettings/PersonalAccessTokensPanel.tsx` (new)
- `frontend/runs-viewer/src/components/AdminSettings/RoleAssignmentPanel.tsx` (151 lines, existing baseline pattern — reuse layout/a11y conventions)
- `frontend/runs-viewer/src/auth/AuthContext.tsx` (373 lines) — `principalType` extension.

## Integration Owner

Single specialty phase (ui-engineer-enhanced, with a11y-sheriff as reviewer sharing ACT-503) — no separate `integration_owner` declaration required beyond the ACT-503 combined task, which already functions as the seam between implementation and accessibility review.

---

[← Phase 4](./phase-4-di1-audit-enforcement.md) | [← Back to main plan](../public-multiuser-release-activation-v1.md) | [Next: Phase 6 →](./phase-6-testing-docs.md)
