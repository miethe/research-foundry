---
title: "Phase 3: Admin API"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P3
phase_title: "Admin API"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
entry_criteria:
  - "P2 sealed (karen milestone REV-P2-002 passed) — token_service.py exists and is reviewed."
exit_criteria:
  - "require_role route sweep green."
  - "No raw secret in any response except one-time issuance."
  - "task-completion-validator pass."
---

# Phase 3: Admin API

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 8 pts
**Dependencies**: P2 (full phase, `batch_3`)
**Assigned Subagent(s)**: `python-backend-engineer` (primary); `api-librarian`/`senior-code-reviewer` (error-envelope + no-secret-leak review)
**Model**: sonnet | **Effort**: adaptive
**Mode**: C — Autonomous Feature Sprint (CRUD-shaped routes over an already-reviewed service layer)

## Overview

Additive routes on `api/routers/admin.py` exposing `token_service.py`'s issue/list/revoke/rotate operations for both principal types, plus a deployment-mode-status read endpoint and audit-log wiring on every mutation. This phase never touches the composite auth chain or the token store schema — it is a thin, RBAC-gated CRUD surface over the already-reviewed P2 service layer.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-301 | Admin API — service accounts | `POST/GET /api/admin/service-accounts`, `DELETE /api/admin/service-accounts/{id}`, `POST /api/admin/service-accounts/{id}/tokens` (rotate). All mutation routes gated with `require_role`. | FR-15 (service-account subset) satisfied; rotate invalidates the prior token immediately. | 3 pts | python-backend-engineer | sonnet | adaptive | P2 sealed |
| ACT-302 | Admin API — PATs | `POST/GET /api/admin/pats`, `DELETE /api/admin/pats/{id}`. Self-issue/list/revoke scoped to the caller's own PATs unless caller is owner/admin. | FR-15 (PAT subset) satisfied; non-owner/admin caller cannot list/revoke another user's PAT (403, not 404-leak). | 3 pts | python-backend-engineer | sonnet | adaptive | P2 sealed |
| ACT-303 | Admin API — deployment-mode-status + audit wiring | `GET /api/admin/deployment-mode-status` (surfaces resolved `deployment_mode` and per-knob preset/override status); wire `audit_event` logging for every mutation route in ACT-301/ACT-302 (issuance, revocation, rotation, role change). | FR-15 (status), FR-17 satisfied; every mutation produces exactly one `audit_event` row with actor + target + outcome. | 2 pts | python-backend-engineer | sonnet | adaptive | ACT-301, ACT-302 |
| REV-P3-001 | Reviewer gate: error-envelope + no-secret-leak review | Mode E review confirming every route uses the `ErrorResponse` envelope and no response (other than the one-time issuance response) contains a raw secret. | Reviewer confirms `require_role` sweep green across all new routes and no plaintext secret leak. | gate | senior-code-reviewer | sonnet | adaptive | ACT-301, ACT-302, ACT-303 |
| REV-P3-002 | Reviewer gate: task-completion-validator | Standard phase-completion review. | Validator confirms FR-15, FR-17 satisfied. | gate | task-completion-validator | sonnet | adaptive | REV-P3-001 |

**Phase point subtotal**: 8 pts (reviewer-gate rows excluded).

## Structured Acceptance Criteria

#### R-P1 guard: `require_role` route sweep (expansion of the P3 exit gate's "sweep" language)
- target_surfaces:
    - src/research_foundry/api/routers/admin.py
- propagation_contract: >
    Every mutation route added in ACT-301/ACT-302/ACT-303 (`POST`, `DELETE`, rotate `POST`) carries
    an explicit `require_role` dependency; `GET` list routes are scoped per FR-15 (self-vs-admin for
    PATs; workspace-scoped for service accounts).
- resilience: >
    A caller lacking the required role receives a 403 via the standard RBAC dependency path — never
    a silent 200 with an empty/filtered list that could be mistaken for "no data" vs. "no permission."
- visual_evidence_required: false
- verified_by:
    - REV-P3-001
    - ACT-601 (Phase 6)

## Quality Gates

- [ ] `require_role` sweep green across every new mutation route.
- [ ] No raw secret in any admin API response except the one-time issuance response.
- [ ] `audit_event` row produced for every issuance/revocation/rotation/role-change action.
- [ ] PAT self-vs-admin scoping confirmed (non-owner cannot enumerate other users' PATs).
- [ ] `senior-code-reviewer` pass (REV-P3-001).
- [ ] `task-completion-validator` pass (REV-P3-002).

## Key Files & Integration Points

- `src/research_foundry/api/routers/admin.py` (439 lines) — all new routes land here, additive to existing workspace-member/role-update/auth-provider-status/rate-limit routes.
- `src/research_foundry/services/token_service.py` (from P2) — routes call this service directly; no new business logic in the router layer.
- `src/research_foundry/services/audit_service.py` (555 lines) — existing `audit_event` write path, reused unchanged.

## Integration Owner

Single specialty phase (python-backend-engineer, with senior-code-reviewer as reviewer, not co-implementer) — no `integration_owner`/seam task required per R-P3.

---

[← Phase 2](./phase-2-principal-store-auth-resolution.md) | [← Back to main plan](../public-multiuser-release-activation-v1.md) | [Next: Phase 4 →](./phase-4-di1-audit-enforcement.md)
