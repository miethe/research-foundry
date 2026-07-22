---
schema_version: 2
doc_type: design_spec
title: "Public Multi-User Release Activation: rbac.db Postgres Migration (DF-002)"
status: draft
maturity: idea
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
problem_statement: >
  RBAC, workspace membership, service accounts, and access tokens all live in a single
  SQLite file (`rbac.db`). SQLite serializes writers; there is no measured evidence yet
  that this is a real bottleneck, but it is a known future-scale ceiling this feature's
  decisions-block explicitly named and deferred rather than solved speculatively.
open_questions:
  - "What is the actual write-concurrency profile once real multi_user traffic exists (token issuance/revocation rate, membership-change rate)?"
  - "Is a Postgres migration the right target, or does SQLite WAL mode / a connection-pool wrapper buy enough headroom first?"
  - "Does a migration need to be online/zero-downtime, or can it be a scheduled cutover (single-operator-owned deployments can tolerate a maintenance window)?"
  - "Do service_accounts/access_tokens migrate independently of the RBAC/workspace tables, or must they move together (shared FK/discriminator integrity, per this feature's OQ-2 resolution)?"
explored_alternatives:
  - "SQLite WAL mode as an intermediate step (deferred consideration, not evaluated)."
priority: low
effort_estimate: "TBD (unknown scope; gated on demonstrated need)"
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
---

# rbac.db Postgres Migration (DF-002)

## Status: Idea (Not Active)

This design specification is a placeholder for a **future-scale item**, not a scoped
piece of work: migrating Research Foundry's non-human-principal and RBAC token store
(`rbac.db`, extended by this feature with `service_accounts`/`access_tokens` tables)
from SQLite to Postgres. Per this feature's decisions-block: **"Token store extends
the existing SQLite `rbac.db` (no Postgres, no new datastore)"** — rationale: "avoids
a second source of truth for identity data; Postgres migration is an explicit future
scale item."

## Current State (as of public-multiuser-release-activation)

- `rbac.db` (SQLite) holds `workspaces`, `team_members`, `service_accounts`, and
  `access_tokens` — schema versioned v2→v3 by this feature's ACT-201, idempotent
  `CREATE TABLE IF NOT EXISTS`.
- Research Foundry has **no dual-implementation (local+enterprise) repository split**
  anywhere in this codebase (confirmed at this feature's estimation-sanity-check, H2:
  "N/A — not applied") — a Postgres migration here would be the *first* instance of a
  non-SQLite datastore in the project, not a variant of an existing pattern.
- No ORM: services own their SQL directly (`SERVICE_CONTRACT.md` §0 convention). A
  Postgres migration inherits this constraint — no ORM introduction implied.

## Why Deferred (Not Attempted Now)

1. **No measured problem yet.** `multi_user` deployments (and therefore real
   concurrent-write load on `rbac.db`) do not exist in production at this feature's
   completion — there is nothing to benchmark against.
2. **Scope uncertainty.** Whether the right next step is Postgres, SQLite WAL mode,
   or a connection-pool wrapper is unknown without a measured bottleneck to target.
3. **Avoids speculative complexity.** Introducing a second datastore technology
   before any consumer needs it would violate this project's YAGNI principle
   (`CLAUDE.md` Prime Directives).

## Trigger for Promotion

> Token-store row volume or concurrent-write contention on SQLite becomes a
> **measured** problem (per the parent plan's Deferred Items table).

Concretely: this feature's own Post-Implementation follow-up already names the
leading signal to watch — `audit_event` row volume post-launch under real
`multi_user` usage (issuance/revocation/rotation traffic). A sustained lock-contention
signal there (or in `rbac.db` itself, e.g. `SQLITE_BUSY` errors, `verify_token`
latency degradation under load — see the P2 `karen` Low finding tracked in this
feature's findings doc) is the promotion trigger, not a calendar date.

## Design Envelope (Sketch, Unvalidated)

- **Scope decision needed at shaping time**: does the whole `rbac.db` schema move
  together, or only the higher-write-volume `access_tokens` table (tokens rotate;
  `workspaces`/`team_members` are comparatively static)?
- **Migration shape**: dual-write/backfill/cutover pattern, mirroring this project's
  existing `workspace_migration_service.py` (dry-run → backfill → rollback) idiom
  rather than inventing a new migration discipline.
- **Connection management**: Postgres requires explicit connection pooling (SQLite's
  per-request `bootstrap()`/`conn.close()` pattern does not translate directly) —
  a pooling strategy is in-scope for the shaping pass, not this stub.

## Acceptance Criteria for Promotion to Shaping

- [ ] A measured contention/volume signal exists (not a hypothetical).
- [ ] Scope is locked: full-schema migration vs. `access_tokens`-only.
- [ ] A migration pattern (dry-run/backfill/cutover vs. dual-write) is chosen and
      justified against `workspace_migration_service.py`'s existing precedent.

## Deferred to Future Phase

- Connection pooling implementation, dual-write correctness testing, and any
  Postgres-specific RBAC query rewrites are all out of scope until promotion.
