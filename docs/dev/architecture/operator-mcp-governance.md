---
title: "Research Foundry Operator MCP Governance"
description: "Architecture and trust boundaries for the local stdio-only governed operation MCP."
audience: [developers, ai-agents]
tags: [mcp, operator, governance, authorization, receipts, stdio]
created: 2026-07-31
updated: 2026-07-31
category: architecture
doc_type: architecture
schema_version: 1
status: active
feature_slug: research-foundry-operator-mcp
owner: nick
related_documents:
  - docs/user/research-foundry-operator-mcp.md
  - docs/user/knowledge-mcp.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/design-specs/operator-mcp-remote-transport-shaping.md
  - docs/project_plans/design-specs/operator-mcp-live-writeback-shaping.md
---

# Research Foundry Operator MCP Governance

> Runtime authority: `src/research_foundry/operator_mcp/server.py`,
> `src/research_foundry/services/operator_mcp_policy.py`, and the four
> `schemas/operator_mcp_*.schema.yaml` contracts. This document describes the local surface; it
> does not redefine the authority contracts owned by Knowledge MCP, RPC, ERI, CARP, RAL/activation,
> RFUP, or the Search Router.

The Operator MCP is a thin, local stdio adapter over a closed set of canonical services. Its trust
sequence is: resolve local identity/workspace/sensitivity, evaluate policy, bind/consume a
confirmation where required, create/replay a durable operation, use an AgentJob-backed attempt,
then emit receipts. It must never become a generic command runner, provider router, or second
evidence authority.

```text
stdio client
  -> closed 14-tool server registry
  -> local PolicyContext (identity, workspace, sensitivity)
  -> preflight / confirmation binding
  -> durable operation + AgentJob attempt
  -> named canonical adapter/service
  -> operation/action/effect/checkpoint/terminal receipts
```

## Identity, workspace, and sensitivity

Identity is resolved from the configured local operator, not accepted as a tool argument. The
workspace is mandatory. Where a target has a canonical owner record on disk, its owning workspace
is resolved server-side and compared with the actor workspace. Staging-only targets that do not
yet exist locally are the exception: `external_report.import`'s `import_packet` target binds the
caller-declared workspace, which RBAC then validates against the configured local operator (only
an optional `target_run_id` is resolved from canonical state). A missing target, wrong-workspace target, or target above the caller's
sensitivity ceiling must be indistinguishable as a safe `not_found` denial; `identity_denied` is
reserved for a wholly unresolved identity.

The sensitivity ceiling is likewise resolved locally. Missing, malformed, or unknown configuration
fails closed to the strictest ceiling. The policy surface is closed: operation kinds and target
kinds are bounded contracts, while per-operation payload shape is owned by the named adapter.

## Confirmation and durable operation binding

`operation.preflight` is the one server-implemented meta tool. It evaluates policy and mints a
confirmation only for an allowed confirmation-requiring kind. The confirmation binds the canonical
input digest, identity/workspace context, effective sensitivity, operation kind, targets, policy
snapshot, idempotency key, and expiry. Consuming it for changed payload, targets, policy, actor,
or sensitivity fails closed.

Preflight is not execution: it creates no operation manifest, receipt, adapter action, or canonical
domain effect. A successful confirmation-required preflight has one deliberately bounded durable
effect: its confirmation record. `job.status` requires no confirmation and mints none.

The operation envelope has a client-chosen idempotency key. Exact retries converge on the original
durable operation; reuse with changed bound inputs is an `idempotency_conflict`. Cancellation and
resume operate through the durable AgentJob lifecycle rather than a separate MCP-only job model.

## Receipts, audit, and bounded errors

The receipt schema is a closed discriminated union of five kinds:

- `operation_receipt` records acceptance or denial of an operation.
- `action_receipt` and `effect_receipt` record immutable work and its canonical effects.
- `checkpoint` is the one mutable, atomically replaceable recovery record.
- `terminal_receipt` closes the operation and includes audit-delivery disposition.

Receipts are primary operation evidence. Audit is supplemental: `delivered`, `degraded`, or
`unavailable` is recorded in the terminal receipt and does not erase effect truth.

Transport and policy denials use the versioned `operator_mcp_error` envelope. Its closed reason-code
vocabulary and bounded/redacted fields prevent raw exception, secret, or filesystem-path disclosure.
The server maps unknown tool names, oversized argument payloads, and unexpected dispatch failures
through this shape; adapters return the same shaped errors.

## Transport, limits, and threat boundary

The process is **stdio-only**. Normal instance activation paths for SSE and Streamable HTTP are
explicitly refused. This protects the supported MCP transport surface, but does not claim to confine
arbitrary Python code that already executes inside the process and can call an unbound base-class
method or create its own listener.

The server bounds raw argument size and nesting depth before dispatch. Operation envelopes bound
target count and input-payload properties; schema fields are length-limited. These are defense in
depth alongside the canonical policy and adapter checks, not replacements for them.

Remote transport is **deferred**. Live writeback is **deferred**. The present `writeback.preview`
tool is preview-only and cannot execute a live writeback within the M2 stdio-surface scope. Owner
qualification remains `not_executed_owner_data_absent`; no private-owner or production canary has
been executed from repository fixtures.

## Related authority boundaries

- [Knowledge MCP](knowledge-mcp.md) remains the separate governed read surface.
- [RPC](../guides/research-provenance-continuity.md),
  [ERI](../../user/external-research-interchange.md),
  [CARP](../guides/catalog-assisted-research-planning.md),
  [RAL](../../user/assertion-ledger.md) and
  [activation](../../project_plans/PRDs/features/assertion-ledger-activation-v1.md),
  [RFUP](../../project_plans/human-briefs/rfup-external-routing.md), and the
  [Search Router](../../project_plans/design-specs/research_foundry_search_router_spec.md) retain
  their own authority contracts. The Operator MCP calls their canonical owners; it does not restate
  or replace them.
