---
title: "Design Spec: Hard Distributed Lock for Concurrent Approve+Dispatch"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-18
updated: 2026-07-18
feature_slug: runs-writeback-approve-dispatch
deferred_from: runs-writeback-approve-dispatch-v1
deferred_item_id: DI-WBAD-3
category: dependency-blocked
owner: nick
prd_ref: docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md
related_docs:
  - docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md
  - src/research_foundry/services/writeback.py
---

# Design Spec: Hard Distributed Lock for Concurrent Approve+Dispatch

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-writeback-approve-dispatch-v1` |
| **Reason** | Hard distributed lock for concurrent approve+dispatch is deferred in favor of D2's lightweight advisory lock — today's deployment is single-operator LAN. |
| **Promotion trigger** | Multi-tenant OIDC ships and real concurrent-operator collisions are observed (not merely theoretically possible). |
| **Target spec path** | `docs/project_plans/design-specs/writeback-dispatch-distributed-lock.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **Distributed lock mechanism** — a hard mutual-exclusion primitive (e.g.,
  a database-backed lock row, an external lock service, or a lease-based
  protocol) that prevents two concurrent approve+dispatch invocations against
  the same run from both proceeding, replacing the current advisory
  `.dispatch.lock` file.
- **Lock scope** — per-run vs. per-target vs. global; whether the lock needs
  to span multiple API processes/replicas (a true distributed concern) rather
  than a single-process advisory file.
- **Failure/expiry semantics** — lease timeout, stale-lock detection and
  recovery (e.g., a crashed process holding the lock indefinitely), and how
  this differs from the current advisory lock's simpler failure modes.
- **Multi-tenant interaction** — how the lock interacts with RBAC/workspace
  isolation once multi-tenant OIDC ships (per the promotion trigger), since
  concurrent-operator collisions only become a real (not theoretical) risk
  once multiple authenticated operators can act on the same workspace
  simultaneously.
- **Observability** — surfacing lock-contention events in the audit log so
  operators can see when a dispatch was blocked by a concurrent in-flight
  dispatch.

### v1 Constraint

In v1, concurrency protection is a lightweight advisory `.dispatch.lock` file
(per Phase 2's D2 design decision), sufficient for today's single-operator LAN
deployment. This is intentional — building a hard distributed lock ahead of
actual multi-tenant concurrent access would be premature engineering per the
project's YAGNI principle.

---

## Notes for Promotion

- Do not promote this spec until multi-tenant OIDC has actually shipped and
  concurrent-operator collisions have been *observed*, not merely deemed
  possible — the promotion trigger is intentionally evidence-gated.
- Coordinate with whatever RBAC/workspace-isolation mechanism ships alongside
  multi-tenant OIDC (see WKSP-304 enforcement work) — the lock design should
  likely be scoped per-workspace, not merely per-run.
- Evaluate whether the advisory lock's failure mode (a stale lock file left
  behind by a crashed process) has caused real operational pain before
  deciding between a database-backed lock, a lease protocol, or another
  mechanism.
