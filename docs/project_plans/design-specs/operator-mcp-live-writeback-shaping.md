---
schema_version: 2
doc_type: design-spec
title: "Operator MCP Live Writeback"
status: deferred
maturity: shaping
created: 2026-07-31
updated: 2026-07-31
feature_slug: research-foundry-operator-mcp
deferred_from: "research-foundry-operator-mcp-v1 M3"
deferred_item_id: OPM-DF-LIVE-WRITEBACK
category: backlog
owner: nick
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
related_documents:
  - docs/user/research-foundry-operator-mcp.md
  - docs/dev/architecture/operator-mcp-governance.md
  - docs/project_plans/design-specs/writeback-dispatch-rollback.md
---

# Operator MCP Live Writeback

## What is deferred

`writeback.preview` is the only Operator MCP writeback tool in this surface. It is preview-only:
it cannot execute network, client, mirror, or live external writeback effects within the M2
stdio-surface scope. Live writeback is **deferred**.

## Why it is deferred

Executing a writeback would add an external side effect with target credentials, destination
authorization, irreversible or compensating-effect semantics, approval provenance, and operator
accountability. A preview proves none of those. Repository fixtures also do not qualify a private
owner target: owner qualification is `not_executed_owner_data_absent`.

## Promotion gates

Before any live-writeback implementation is scoped, require:

1. A named target and its authoritative destination contract, permissions model, and credential
   owner/rotation process.
2. An explicit confirmation and approval model that binds target, payload, policy snapshot, actor,
   and idempotency semantics to the live effect.
3. Durable effect/receipt and audit requirements, including partial-failure handling, retry safety,
   reconciliation, and the rollback/undo decision.
4. A target-specific secret, privacy, rights, and sensitivity review; do not forward private source
   material merely because it was admissible for a local preview.
5. An authorized owner-held canary, with separately recorded evidence, rollback readiness, and an
   explicit release decision.

## Non-goals

This spec does not authorize a live target, credential, deployment, or canary. It does not convert
a preview receipt into a live-effect receipt, and it does not alter the existing writeback-owner
contracts.
