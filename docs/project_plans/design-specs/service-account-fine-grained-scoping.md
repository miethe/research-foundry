---
schema_version: 2
doc_type: design_spec
title: "Public Multi-User Release Activation: Service-Account Fine-Grained Scoping (DF-003)"
status: draft
maturity: shaping
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
problem_statement: >
  Service accounts and PATs are issued exactly one role from the existing 5-role model
  (owner/admin/contributor/analyst/viewer) — there is no way to grant a machine caller a
  narrower permission set than the role model affords (e.g. "may call rf search and
  rf catalog search, but not rf writeback approve", or "read-only on one workspace's
  catalog only, nothing else contributor grants").
open_questions:
  - "Allowlist shape: tool/endpoint-name allowlist, resource-type allowlist, or a data-domain (project/tag) allowlist — or some combination?"
  - "Scope granularity: per-service-account (one allowlist for the account, all its tokens inherit it) or per-token (each rotation can narrow further)?"
  - "Enforcement point: does the composite auth chain's identity-resolution step need to carry scope alongside role, or is scope checked at each router/service call site independently (mirroring how role is checked today via require_role)?"
  - "UI: does the admin Service Accounts panel need a scope-editing affordance at creation time, or only at the API layer initially (UI follow-up deferred separately)?"
explored_alternatives:
  - "Invent a new fine-grained permission matrix distinct from the 5-role model — rejected direction; the PRD's own OQ Q2 deferral explicitly frames this as narrowing an EXISTING role, not replacing the role model."
priority: medium
effort_estimate: "TBD at shaping (design direction known; sizing needs the allowlist-shape open question resolved first)"
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - docs/dev/architecture/auth-rbac-operator-guide.md
---

# Service-Account Fine-Grained Scoping (DF-003)

## Status: Shaping (Direction Known, Not Yet Ready)

**Direction is reasonably clear**: per this feature's Deferred Items table, DF-003
extends the **existing** 5-role model with an optional, narrower allowlist — it does
**not** invent a new permission matrix. This is why `maturity: shaping` (not `idea`):
the shape of the solution is known even though the concrete schema/enforcement
mechanics are not yet locked.

## Current State (as of public-multiuser-release-activation)

- Every service account and PAT gets **exactly one** role from
  `token_service.VALID_ROLES` at issuance (`POST /admin/service-accounts` body:
  `{"name", "role", "description"?}`; `POST /admin/pats` body:
  `{"role", "expires_at"?, "user_id"?}`).
- That role is re-checked at **every resolution**, not just issuance (FR-9
  role-ceiling), via the same composite-auth-chain path used for human identities —
  scoping mechanics added by this feature reuse the existing role-check idiom rather
  than introducing a parallel one.
- No allowlist/scope concept exists on `service_accounts` or `access_tokens` today —
  a service account with `role=contributor` can do everything a human contributor
  can, workspace-wide.

## Why Deferred (Not Attempted Now)

Per the PRD's own Open Questions (Q2, deferred) and this feature's Deferred Items
table: fine-grained per-service-account tool/data-scope allowlists were explicitly
scoped out to keep this feature's already-large surface (two principal types ×
issue/list/revoke/rotate × admin API × admin UI) from doubling again. Building it now,
before any concrete consumer names the specific narrower scope they need, risks
guessing the wrong allowlist shape (tool-name vs. resource-type vs. data-domain) and
having to redo it.

## Trigger for Promotion (to `ready`)

> A future feature needs narrower machine-scoping than "researcher" or "viewer"
> affords (per the parent plan's Deferred Items table).

Concretely: the first real consumer request that says "this service account should be
able to do X but explicitly not Y, where X and Y are both covered by the same role
today" is the signal to lock the allowlist shape and move to `ready`.

## Design Envelope (Sketch)

- **Extend, don't replace**: add an optional scope column (working name:
  `scope_allowlist`, JSON-encoded) to `service_accounts` (and optionally
  `access_tokens`, if per-token narrowing is chosen over per-account) — nullable, so
  every existing account defaults to "full role permissions" (no allowlist = role's
  full capability set, preserving backward compatibility with every account issued
  before this lands).
- **Enforcement mirrors the existing role-check idiom**: the composite auth chain
  already resolves an `AuthIdentity`-shaped object with `roles` — a scope allowlist
  would thread alongside it (e.g. `AuthIdentity.scopes: list[str] | None`) and be
  checked at the same call sites `require_role(...)` already gates, not a new
  independent enforcement layer.
- **Admin API**: `POST /admin/service-accounts` body would gain an optional
  `scope_allowlist` field; `GET` responses would surface it (never a secret, so no
  special handling needed there).
- **Admin UI**: the existing `ServiceAccountsPanel.tsx` creation form would need a
  scope-editing affordance — likely a later, separately-scoped UI task once the
  backend allowlist shape is locked.

## Acceptance Criteria for Promotion to Ready

- [ ] A concrete consumer request names the specific capability gap (not hypothetical).
- [ ] Allowlist shape (tool/endpoint vs. resource-type vs. data-domain) is locked.
- [ ] Enforcement point is confirmed to reuse the existing `require_role`-adjacent
      check idiom (no new parallel enforcement layer introduced).

## Deferred to Future Phase

- Concrete schema migration, admin API/UI wiring, and the composite-auth-chain scope
  threading are all out of scope until promotion to `ready`.
