---
title: "Design Spec: Rights-Owner / Counsel Role & Attestation Workflow"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-21
updated: 2026-07-21
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
feature_slug: rights-entity-model
deferred_from: rights-entity-model-v1
deferred_item_id: DI-RIGHTS-4
category: backlog
owner: rf
related_docs:
  - docs/dev/architecture/adr-rights-entity-model.md
  - docs/project_plans/design-specs/rights-runtime-resolution-api.md
  - docs/project_plans/design-specs/rights-surveillance-loop.md
open_questions:
  - "OQ-RF-6: Is there an RF rights-owner/counsel role to gate CLEARED_*/counsel_approved writes?"
---

# Design Spec: Rights-Owner / Counsel Role & Attestation Workflow

> **Maturity: idea** — This spec names and scopes a real, deferred gap
> (`DI-RIGHTS-4` / `OQ-RF-6`). It does not propose a final design; it records
> the problem, the current fallback, and the trigger condition that would
> promote this into an actual PRD.

---

## Origin

| Field | Value |
|-------|-------|
| **Deferred from** | `rights-entity-model-v1` (Phase 6, task P6-8c) |
| **Deferred item ID** | `DI-RIGHTS-4` |
| **Open question** | `OQ-RF-6` |
| **Category** | backlog |
| **PRD** | `docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md` |
| **Implementation plan** | `docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md` |
| **ADR** | `docs/dev/architecture/adr-rights-entity-model.md` ("Known Gaps" → OQ-RF-6) |

## Problem Statement

The `rights-entity-model-v1` feature enforces that `CLEARED_*` rights-status
values, `counsel_approved`, and `attestation.status: attested` can only ever
be written by a human — but it enforces this **by exclusion**, not by a
positive role. Per the parent plan's Deferred Items table
(`docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md`,
"Deferred Items Triage Table"), `DI-RIGHTS-4` is:

> Formal rights-owner/counsel role and attestation workflow (OQ-RF-6) — no
> such role exists anywhere upstream today.

And the ADR's "Known Gaps → OQ-RF-6" section states the boundary explicitly:

> Invariant 1 above enforces that `CLEARED_*`/`counsel_approved`/
> `attestation.status: attested` are human-only by **exclusion** — no agent
> identity is authorized to write them — not by a positive, named role. There
> is no existing RF counsel/rights-owner role, permission scope, or
> attestation workflow anywhere upstream today. "Human-only" currently means
> "not any known agent identity," which is a correct but coarse authorization
> boundary.

This is a correct, fail-closed boundary for v1 (proven by negative tests over
both write paths in P3 and P5), but it is not a durable authorization model.
There is no first-class rights-owner/counsel identity, no permission scope
tied to that identity, and no attestation workflow (request → review →
sign-off → audit trail) that a human reviewer actually walks through today.
"Human-only" is enforced as "absence of agent authorization," which does not
scale to multi-reviewer, multi-tenant, or audit-driven scenarios.

## Current State (Shipped Fallback)

- `attestation.status` supports `attested`, but nothing in RF's schema or
  runtime models *who* is authorized to set it beyond "not an agent
  identity."
- `CLEARED_*` rights-status values and `counsel_approved` are gated the same
  way — negative tests confirm no agent-writable code path can produce them,
  but no positive role check exists.
- There is no RF permission scope, session identity, or UI surface
  representing "I am acting as rights counsel for this attestation."
- No audit trail links a specific human identity to a specific attestation
  decision beyond whatever generic actor/author metadata RF already captures
  on writes.

This fallback is intentionally coarse. It is a correct stopgap, not a design
for the role this spec is scoped to eventually produce.

## Trigger Condition for Promotion

Per the parent plan's Deferred Items Triage Table, the exact, authoritative
trigger condition for promoting this item out of backlog is:

> A human reviewer workflow needs a first-class role/permission model

This spec should be promoted to a PRD only when a concrete human reviewer
workflow — not a hypothetical one — requires a named rights-owner/counsel
role with its own permission scope, distinct from "any human, gated by agent
exclusion." Until that consumer exists, human-only-by-exclusion remains
sufficient and this spec stays at `maturity: idea`.

## Open Questions (For Future Shaping)

- What identity/permission primitive does RF use for human-only roles
  elsewhere (if any), and can rights-owner/counsel reuse it, or does it need
  a new one?
- Is "rights-owner" a role distinct from "counsel," or one combined role
  with a single permission scope?
- Does the attestation workflow need a request → review → sign-off state
  machine, or is a single sign-off event (as currently modeled) sufficient
  once tied to a named identity?
- Does this role need to be workspace-scoped (per WKSP-304 row-level
  isolation) or global to an RF deployment?
- What audit-trail requirements (if any) does a real rights-owner/counsel
  consumer bring — e.g., is a signed/timestamped attestation record required
  for legal defensibility?

## Explored Alternatives

None yet — this spec is `maturity: idea`, recording the gap named by
`DI-RIGHTS-4`/`OQ-RF-6` rather than proposing a design. Alternatives should be
explored when a real trigger (above) surfaces and this spec is shaped toward
`ready`.

## Non-Goals (For This Spec, As Currently Scoped)

- This spec does not weaken or replace the existing human-only-by-exclusion
  enforcement in `rights-entity-model-v1`. That enforcement (negative tests
  over both write paths, P3 and P5) remains the fail-closed baseline until a
  positive role model is designed, reviewed, and shipped.
- This spec does not propose a general-purpose RBAC system for RF; scope is
  limited to the rights-owner/counsel attestation surface unless a broader
  need is identified during shaping.

## Related Deferred Items

- `DI-RIGHTS-1` (OQ-RF-3, runtime rights-resolution API) —
  `docs/project_plans/design-specs/rights-runtime-resolution-api.md`
- `DI-RIGHTS-3` (OQ-RF-5, rights-terms surveillance execution loop) —
  `docs/project_plans/design-specs/rights-surveillance-loop.md`
