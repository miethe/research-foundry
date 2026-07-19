---
title: "Design Spec: Automated Rollback/Undo of a Completed Writeback Dispatch"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-18
updated: 2026-07-18
feature_slug: runs-writeback-approve-dispatch
deferred_from: runs-writeback-approve-dispatch-v1
deferred_item_id: DI-WBAD-2
category: backlog
owner: nick
prd_ref: docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md
related_docs:
  - docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md
  - src/research_foundry/services/writeback.py
---

# Design Spec: Automated Rollback/Undo of a Completed Writeback Dispatch

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-writeback-approve-dispatch-v1` |
| **Reason** | Automated rollback/undo of a completed dispatch is out of scope (PRD Risk R3) — the existing overwrite-idempotent re-render already gives a manual remediation path. |
| **Promotion trigger** | Manual remediation proves insufficient at higher dispatch volume, or a target becomes a live push where overwrite-idempotency no longer holds. |
| **Target spec path** | `docs/project_plans/design-specs/writeback-dispatch-rollback.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **Automated rollback mechanism** — a dedicated "undo last dispatch" action
  (API endpoint + runs-viewer UI control) that reverses the effects of a
  completed approve+dispatch invocation without requiring the operator to
  manually re-invoke and overwrite.
- **Rollback scope and boundary** — what "undo" means per target: for
  local-file targets (MeatyWiki, SkillMeat, CCDash) this likely means
  restoring the prior file content/version; for any future live-push target
  (see DI-WBAD-1) rollback semantics would need to be defined separately
  (compensating action vs. no-op vs. unsupported).
- **Versioning/snapshot requirement** — whether rollback requires persisting a
  pre-dispatch snapshot of each target's content, and where that snapshot
  would live (audit log payload vs. separate history store).
- **Audit-trail implications** — a rollback action would itself need an
  audit row (5th outcome class beyond the current 4), including which prior
  dispatch it reverses.
- **Interaction with re-approval** — whether a rolled-back run reverts to
  `not-yet-approved` state or remains approved but un-dispatched.

### v1 Constraint

In v1, there is no automated rollback/undo. The only recovery mechanism this
feature ships with is the manual remediation path: correct the run's content,
re-invoke approve+dispatch (overwrite takes effect immediately), and manually
delete/replace a stale mirror file only if a target system's out-of-band
consumer already ingested the bad version before the overwrite landed. This
manual path is documented as part of Phase 4's docs update (DOC-003) in the
parent implementation plan.

---

## Notes for Promotion

- Before scoping this, confirm the manual remediation path has actually
  proven insufficient in practice (per the promotion trigger) rather than
  building rollback speculatively.
- Any rollback design must account for the per-target isolation model
  (PRD Risk R7) — a partial dispatch (some targets succeeded, some failed)
  complicates what "rollback" means for a single invocation.
- Consider whether a lighter-weight interim mitigation (e.g., a
  confirmation/preview step before dispatch) would reduce the need for
  rollback entirely, before committing to full undo semantics.
