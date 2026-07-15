---
title: Reusable Assertion Ledger Shared-Index Isolation Spec
doc_type: design_spec
schema_version: 2
status: deferred
maturity: shaping
created: 2026-07-15
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
deferred_from: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md
---

# Reusable Assertion Ledger Shared-Index Isolation Spec

## Decision

Shared indexes are deferred. P8 ships no shared corpus, cross-workspace query,
index build, ranking behavior, migration, or public API surface. The current
ledger remains private-workspace scoped and assertion-only by default.

## Required design before any implementation

Any later shared-index proposal must define tenant-bound identity, query-time
authorization before ranking/faceting/counting, index partitioning and deletion
semantics, encrypted retention and key ownership, immutable provenance links,
and a reconstruction path proving that a returned assertion was visible to the
caller at the recorded time.

## Deal killers

- Any cross-workspace result, count, facet, timing signal, cache entry, or
  autocomplete suggestion reachable without an explicit authorization proof.
- A global identity or deduplication mechanism that can merge private source
  evidence across tenants or reveal equality by error, timing, or ranking.
- An index that cannot synchronously block invalidated/retracted assertions
  before presenting current reuse candidates.
- A migration that cannot be paused, resumed idempotently, fully disabled, and
  audited without exposing passage text or source locators.

## Future SPIKE gates

1. Threat-model partition, cache, backup, and observability boundaries with
   adversarial cross-tenant probes.
2. Produce a measured isolation/reconstruction prototype using synthetic data
   only, including denied, stale, invalidated, and legacy-missing cases.
3. Obtain privacy, security, operator, and workspace-owner sign-off on
   retention, deletion, key custody, and incident response before implementation.
4. Require independent review of migration/rollback and no-leak telemetry
   evidence on the exact candidate tree.
