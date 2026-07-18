---
title: Research Foundry Knowledge MCP Remote Cache Isolation
doc_type: design_spec
schema_version: 2
status: deferred
maturity: shaping
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-foundry-knowledge-mcp
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
deferred_from: docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
problem_statement: >-
  Remote knowledge outputs depend on identity, workspace, policy, lifecycle,
  query or resource identity, schema version, and projection generation, so an
  incomplete cache partition can return another tenant's data or leak membership.
open_questions:
  - "Which cache product, topology, capacity, cost, and operational owner are acceptable?"
  - "What complete partition key and authorization snapshot version bind every cached value?"
  - "What invalidation and deletion SLA covers replicas, queues, backups, logs, and disaster-recovery copies?"
  - "How will hidden/absent and hit/miss timing, size, and metrics equivalence be qualified?"
  - "Which encryption, key-custody, retention, and incident-response controls are required?"
explored_alternatives:
  - "Add no new cache in local v1: retained current boundary."
  - "Share cache partitions across workspaces: rejected because hit rate cannot override tenant isolation."
  - "Treat a cache hit as authorization: rejected because policy must be re-evaluated before serving."
  - "Enable negative caching by default: rejected unless hidden/absent equivalence and invalidation are proven."
  - "Reuse shared vector or graph indexes as the cache: deferred to the separate shared-index design scope."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
---

# Research Foundry Knowledge MCP Remote Cache Isolation

## Decision

Remote and multi-tenant caching is deferred. Local v1 performs governed reads
without introducing a new shared cache. A remote profile may not add result,
document, authorization, cursor, denial, or negative caching until partition,
invalidation, timing, deletion, backup, and key boundaries are proven.

## Problem Statement

Knowledge search and fetch outputs depend on principal, workspace, sensitivity
ceiling, rights/allowed use, lifecycle/evaluation/freshness state, capability,
query/ID, service/schema version, and projection generation. A cache key that
omits any governing input can return another tenant's data or reveal membership
through hit/miss timing, counts, cursors, or error differences.

## Required Isolation Model

Any proposed cache must define a complete partition key containing, or a proof
equivalent to:

- authenticated principal/authorization snapshot and workspace ID;
- sensitivity ceiling, allowed-use/rights/capability and policy version;
- resource kind, opaque ID or normalized query, validated filters, fixed/explicit limits;
- lifecycle/evaluation/freshness generation and underlying projection generation;
- core versus RF-extended DTO/schema/tool version; and
- canonical host/route version where cached URLs are emitted.

Cache values must be encrypted with approved key ownership, size/TTL bounded,
and free of tokens, credentials, raw audit context, denied IDs, hidden counts,
and private filesystem paths. Authorization is re-evaluated before serving a
value; a cache hit is never authorization.

## Invalidation and Deletion

The design must define synchronous or bounded invalidation for rights changes,
workspace membership loss, sensitivity promotion, assertion invalidation or
retraction, report revision, source deletion, policy/schema/ID version change,
key rotation, and incident response. It must cover replicas, queues, backups,
logs, metrics, and disaster-recovery copies with an auditable deletion SLA.

Negative caching is disabled by default. If proposed, it must prove hidden and
absent resources have indistinguishable value, TTL, key shape, size, timing,
metrics, and invalidation behavior.

## Adversarial Evaluation Matrix

- Two workspaces issue identical queries and opaque-looking IDs.
- A user's workspace or rights are revoked between fill and read.
- Sensitivity, lifecycle, evaluation, or source edition changes after fill.
- Hidden records are added/removed without changing an authorized caller's output or timing class.
- Cursor, filter, fixed core cap, and RF extended limit boundaries collide.
- Cache key/version truncation, hash collision, eviction pressure, replica lag,
  backup restore, key rotation, and partial invalidation occur.
- Metrics/logs/alerts are inspected for tenant IDs, queries, result IDs, counts,
  content, denial membership, and timing side channels.

## Promotion Gates

1. Approve a cache-specific threat model and data classification.
2. Prove key completeness and tenant partitioning with synthetic two-workspace tests.
3. Prove rights/lifecycle/deletion invalidation across replicas and backups.
4. Demonstrate hidden/absent and hit/miss timing/size/metric equivalence within approved bounds.
5. Approve encryption, key custody, retention, deletion, backup, observability,
   incident response, capacity, and cost owners.
6. Approve remote transport and canonical URL specs; cache cannot promote alone.

## Non-Goals

- Adding a cache to local v1.
- Treating a cache as authorization, provenance authority, or canonical storage.
- Sharing cache partitions across workspaces to improve hit rate.
- Adding shared/vector/graph indexes; the separate shared-index spec owns that scope.
