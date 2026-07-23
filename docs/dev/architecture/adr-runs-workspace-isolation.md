---
title: "ADR: Runs/Claims/Evidence Workspace Isolation & Public Visibility"
doc_type: adr
status: accepted
schema_version: 1
created: 2026-07-23
updated: 2026-07-23
feature_slug: public-multiuser-release-activation
resolves: ["DF-004-OQ1", "DF-004-OQ2", "DF-004-OQ3", "DF-004-OQ4"]
related_docs:
  - docs/project_plans/design-specs/runs-evidence-workspace-isolation.md
  - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
  - docs/dev/architecture/adr-rights-entity-model.md
owner: nick
---

# ADR: Runs/Claims/Evidence Workspace Isolation & Public Visibility

## Context

The run/evidence-bundle data model had **no `workspace_id` concept**. Under
`deployment_mode=multi_user`, any authenticated caller in any workspace could
read every run (detail, claim ledger, context, source cards, anchors) and could
trigger a writeback dispatch on any run; agent-job creation trusted a
client-supplied `workspace_id`, making audit attribution spoofable. The DI-1
full-surface audit (rows 9-12) accepted this as deferred residual risk under a
**trusted-cohort** `multi_user` scope only; DF-004 is the tracked remediation
that must land before any adversarial multi-tenant posture.

The DF-004 design-spec flagged the direction as blocked on product decisions.
This ADR records those decisions.

## Decision

1. **Run ownership = launching identity's workspace.** A run belongs to the
   workspace of the identity that launched it. `POST /runs` stamps
   `run.yaml.workspace_id` from `identity.workspace_id` and never from client
   input — the same "identity always overrides client input" contract proven by
   `builder_service.create_draft`. (DF-004-OQ1)

2. **Public visibility, provenance preserved.** Runs carry a `visibility` field:
   `"workspace"` (default) or `"public"`. A `public` run is readable across
   workspaces regardless of enforcement; the owning `workspace_id` is still
   recorded (provenance is never lost). **Public grants READ only** — it does
   not permit a non-owner to trigger a writeback dispatch (a mutating
   cross-tenant action stays owner-scoped). (operator addition)

3. **Enforcement reuses the shared advisory-default flag.** Reads and the
   writeback owner-check delegate to the shared
   `api/auth/scope.py::require_workspace_scope` predicate with
   `resolve_enforcement=lambda: resolve_workspace_isolation_active(paths)` —
   identical to `catalog_service`/`audit_service`/`builder_service`/
   `AgentJobService`. `identity is None` (single-operator-trust / auth
   provider `none`) short-circuits to allow as the first statement, so the LAN
   `single_user` deployment is byte-identical to pre-DF-004. Advisory mode
   logs-and-allows; the operator opts into enforcing for adversarial multi-tenant.
   (DF-004-OQ3)

4. **Cross-workspace denial is an indistinguishable 404, never a 403.** Read
   handlers map a workspace-scoped-away run to the same 404 a missing or
   sensitivity-gated run returns (no-existence-leak). `list_runs` filters
   unreadable runs out of the summary rather than erroring.

5. **Legacy runs backfill to `"default"`.** A run-aware
   `dry_run_runs`/`backfill_runs` + rollback path in
   `workspace_migration_service.py` walks `runs/*/run.yaml`, stamps `"default"`
   on runs lacking a `workspace_id`, records a JSON manifest, and never writes
   `visibility`. Under enforcement a legacy run with a null `workspace_id` is
   denied (null is treated as a mismatch, never a wildcard). Dry-run is
   zero-write. (DF-004-OQ2)

6. **Row 9 fixed atomically.** `create_job` gains an `identity` param and
   stamps `workspace_id` from `identity.workspace_id` (falling back to the body
   value only when `identity is None`); `launch_job` stamps both the persisted
   job and the `agent_job_launched` audit event's `actor_workspace_id` from the
   same effective value; `spawn_job` inherits the corrected job unchanged.
   (DF-004-OQ4)

## Consequences

- Trusted-cohort `multi_user` and LAN `single_user` deployments are unchanged
  until an operator turns enforcement on.
- With enforcement on, runs/claims/evidence and writeback dispatch are
  workspace-scoped, and agent-job attribution can no longer be spoofed.
- **Not yet certified:** a formal DI-1 re-audit + Mode D human sign-off must
  re-verify audit rows 9-12 flip to CONFINED/REMEDIATED before any deployment
  claims adversarial-multi-tenant readiness. This ADR records the engineering
  decision and implementation; it does not itself lift the trusted-cohort scope
  boundary set by the DI-1 audit sign-off.
