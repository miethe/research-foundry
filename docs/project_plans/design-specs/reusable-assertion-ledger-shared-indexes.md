---
title: Reusable Assertion Ledger Shared-Index Isolation Spec
doc_type: design_spec
schema_version: 2
status: deferred
maturity: shaping
created: 2026-07-15
updated: 2026-07-27
feature_slug: reusable-assertion-ledger
deferred_from: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
---

# Reusable Assertion Ledger Shared-Index Isolation Spec

## Decision

Shared indexes are deferred. P8 ships no shared corpus, cross-workspace query,
index build, ranking behavior, migration, or public API surface. The current
ledger remains private-workspace scoped and assertion-only by default.

## Reconciled Against Local v1 (KMCP P1-P5)

- **Shipped locally:** the Knowledge MCP (`rf-knowledge-mcp`) draws its
  `search`/`rf_search`/`rf_assertion_get` assertion surface exclusively from
  the existing private, per-workspace assertion ledger
  (`AssertionKindProjector`) — never a shared or cross-workspace index. In
  local stdio v1 this process always resolves `identity=None` ("local
  trust"; `settings.py`), while every assertion read unconditionally
  requires a non-`None` identity with a workspace id — an assertion-catalog
  invariant independent of the WKSP-304 isolation flag. Consequently
  `search`/`rf_search` never return an `assertion`-kind result and
  `rf_assertion_get` denies generically for every id through this local
  process (`registry.py`'s "Local-trust caveat" section). Knowledge MCP v1
  therefore exposes strictly LESS assertion surface than the private,
  identity-bearing ledger already offers via existing CLI/API — not a
  shared, wider, or cross-tenant one.
- **Still deferred:** everything this spec's "Required design before any
  implementation" and "Deal killers" sections list — tenant-bound identity,
  query-time authorization before ranking/faceting, shared-index
  partitioning/deletion, and a visibility-reconstruction proof. None of it
  is implicated by Knowledge MCP v1 because it introduces no shared or
  cross-workspace assertion index at all.
- **Promotion gate:** unchanged from "Future SPIKE gates" below — an
  adversarial cross-tenant threat model; a synthetic isolation/
  reconstruction prototype; privacy/security/operator/workspace-owner
  sign-off; and independent migration/rollback plus no-leak telemetry
  review — before any shared-index proposal, for Knowledge MCP or otherwise,
  moves past this shaping spec (decisions-block §10's fourth bullet, in
  `research-foundry-knowledge-mcp-v1.md`).

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
