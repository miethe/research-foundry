---
schema_version: 2
doc_type: design_spec
title: "Public Multi-User Release Activation: Runs/Claims/Evidence Workspace Isolation (DF-004)"
status: draft
maturity: shaping
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
problem_statement: >
  The run/evidence-bundle data model has NO workspace_id concept at all. Under
  deployment_mode=multi_user, any authenticated caller in ANY workspace can list and
  read every run's full detail/claim-ledger/context/source-cards/anchors, and can
  trigger a real writeback dispatch against any run regardless of workspace. A related
  finding lets a caller spoof the workspace_id attributed to an agent-job's audit
  trail. This is the DI-1 full-surface audit's headline residual risk, explicitly
  accepted as deferred (not remediated) by the Mode D human sign-off that authorized
  this feature's trusted-cohort multi_user scope.
open_questions:
  - "Does a run belong to the workspace of the identity that launched it (the natural default), or is run data intentionally cross-workspace-shared (e.g. a shared research corpus by design)? This is a product decision, not an engineering one, and blocks any remediation until answered."
  - "If runs become workspace-scoped, what happens to pre-existing runs created before workspace_id existed on the run schema at all (unlike catalog/report-drafts, which had an explicit WKSP-30x backfill migration) — is a new backfill migration required, and what is the default workspace assignment for legacy runs?"
  - "Does fixing row 9 (POST /agent-jobs trusting client-supplied workspace_id) require touching create_job, spawn_job, AND the audit-event call together, given they are named as a multi-call-site fix in the audit?"
  - "Should GET /runs* read-endpoint scoping use the same indistinguishable-404 pattern already established by catalog_service.get_item and audit_service.get_event, for consistency?"
explored_alternatives:
  - "Do nothing until an adversarial multi-tenant deployment is actually planned — this is the current (accepted) posture; this design-spec exists so that decision is revisited deliberately rather than forgotten."
priority: high
effort_estimate: "TBD at shaping (design direction is well-characterized by the audit's own proposed fixes per surface; sizing needs the workspace-ownership product decision resolved first)"
related_documents:
  - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
  - docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - .claude/findings/public-multiuser-release-activation-findings.md
---

# Runs/Claims/Evidence Workspace Isolation (DF-004)

## Status: Shaping — the single highest-priority follow-up from this feature

This design-spec is the tracked follow-up named explicitly by the DI-1 full-surface
audit's Mode D human sign-off (`docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`,
`signoff.residual_risk_acknowledged`): **it is the item that would lift this feature's
`multi_user` gate from authorizing a trusted-cohort deployment to authorizing a
genuinely adversarial multi-tenant one.** `maturity: shaping`, not `idea`, because the
audit itself already enumerated the exact surfaces and proposed concrete fixes per
row — what remains is a product decision (see the first open question) before any of
those fixes can be written, not open-ended research.

## Problem (audit rows 9-12, verbatim scope)

1. **Rows 10-11 — reads have no workspace check because there is nothing to check
   against.** `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/claims`,
   `GET /runs/{id}/context`, `GET /source-cards/{id}`, `GET /reports/{id}/anchors` (6
   endpoints, `api/routers/runs.py`) never gate on `identity` because the run record
   has no `workspace_id` field. `POST /runs` (launch) resolves `identity` but never
   stamps it onto the run being created — the root cause the read-side gap inherits.
2. **Row 12 — an unscoped cross-tenant WRITE/ACTION, not merely a read gap.**
   `POST /runs/{id}/writeback/approve` (`api/routers/writeback.py`) lets any
   authenticated caller trigger a real writeback dispatch (MeatyWiki/SkillMeat/CCDash)
   against any run in any workspace — reclassified by `karen` (REV-P4-001) from
   could-not-verify to the same NEEDS-REMEDIATION severity as rows 10/11, because a
   real external side effect is a materially worse risk than an information leak.
3. **Row 9 — client-supplied `workspace_id` on agent-job creation, with an FR-12
   attribution caveat.** `POST /agent-jobs` (`api/routers/agent_jobs.py`) takes
   `workspace_id=body.workspace_id` verbatim from the request body instead of
   stamping it from `identity.workspace_id` (unlike `builder_service.create_draft`'s
   established pattern). The `agent_job_launched` audit-trail's `actor_workspace_id`
   inherits the same unverified value — this feature's own FR-12 execution-identity
   binding (service-account default for un-actored jobs) protects `created_by` but
   does **not** protect `actor_workspace_id`, so audit-trail attribution remains
   spoofable until this row is fixed.

## Why Deferred (Mode D-accepted, not silently missed)

This was a deliberate, explicit, human-reviewed acceptance — not an oversight. The
audit's own "Recommendation to the human reviewer" section framed it as exactly this
choice: wiring the `multi_user` startup gate (this feature's core deliverable) does
not by itself certify these findings resolved, and the human reviewer's job was to
decide whether that gap should block acceptance or be carried forward as an explicit,
acknowledged trade-off. It was accepted as the latter — see the audit's frontmatter
`signoff:` block for the literal acceptance record and scope boundary.

## Trigger for Promotion (to `ready`)

Per the orchestrator's framing of this deferred item: **before any deployment moves
from trusted-cohort `multi_user` to a genuinely adversarial/untrusted multi-tenant
posture.** Concretely, promotion should happen before (not after) any of the following:
- A `multi_user` deployment is opened to callers who are not mutually trusting.
- Any SLA or compliance commitment is made about per-tenant data isolation for runs.

## Design Envelope (per-surface fix sketch, from the audit's own proposed fixes)

| Surface | Proposed fix direction (from the audit) |
|---|---|
| Run creation (row 11) | Stamp `workspace_id` on the run record from `identity.workspace_id` at `POST /runs` launch time — mirrors `builder_service.create_draft`'s "identity always overrides client input" pattern, already proven at rows 1-3/13 of the audit. |
| Run reads (row 10) | Once runs carry `workspace_id`, thread `identity` into `runs.py`'s 6 read handlers and gate with the same indistinguishable-404 idiom already used by `catalog_service.get_item` and `audit_service.get_event` (a cross-workspace mismatch returns `None`/404, never a distinguishable 403). |
| Writeback dispatch (row 12) | Gate `approve_and_dispatch` on the same workspace check as row 10's reads, before any external dispatch call is made — `identity.user_id` is already correctly threaded for `approved_by` attribution; only the run's own workspace membership is unchecked. |
| Agent-job creation (row 9) | Stamp `workspace_id` from `identity.workspace_id` (not `body.workspace_id`) in `create_job`, and propagate the corrected value through `spawn_job` and the `agent_job_launched` audit-event call together (named as a multi-site fix in the audit — fixing only one call site would leave the others inconsistent). |

**The blocking open question**: none of the above can be written until the
workspace-ownership product decision (open question #1) is answered — every proposed
fix above assumes "a run belongs to the workspace of the identity that launched it,"
which the audit explicitly flags as unconfirmed, not assumed.

## Acceptance Criteria for Promotion to Ready

- [ ] The run-ownership product decision is made and recorded (ADR or plan decision).
- [ ] A backfill/migration strategy for pre-existing runs (created before `workspace_id`
      existed on the run schema) is decided, mirroring `workspace_migration_service.py`'s
      dry-run/backfill/rollback precedent where applicable.
- [ ] Row 9's multi-call-site fix scope (`create_job`, `spawn_job`, the audit-event
      call) is confirmed as a single atomic change, not staged partially.
- [ ] A re-audit re-verifies rows 9-12 flip to CONFINED/REMEDIATED before any claim of
      adversarial multi-tenant readiness is made.

## Deferred to Future Phase

- Concrete schema migration for `runs`/claim-ledger/source-card/evidence-bundle
  records, the read-side identity threading, the writeback-approve gate, and the
  agent-job creation fix are all out of scope until the product decision above is made.
