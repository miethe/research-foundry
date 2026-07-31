---
title: Research Foundry Operator MCP
description: "How to run the local rf-operator-mcp stdio process, use its governed operation tools, and interpret confirmations, receipts, and bounded errors."
audience: [users, developers]
tags: [mcp, operator, governance, stdio, confirmations, receipts]
created: 2026-07-31
updated: 2026-07-31
category: user-documentation
doc_type: user_guide
schema_version: 1
status: active
feature_slug: research-foundry-operator-mcp
related_documents:
  - docs/dev/architecture/operator-mcp-governance.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
  - docs/user/knowledge-mcp.md
  - docs/project_plans/design-specs/operator-mcp-remote-transport-shaping.md
  - docs/project_plans/design-specs/operator-mcp-live-writeback-shaping.md
---

# Research Foundry Operator MCP

`rf-operator-mcp` is the local, governed operation surface for Research Foundry. It is distinct
from the read-only [Knowledge MCP](knowledge-mcp.md): this process preflights and coordinates a
closed set of operations under local identity, workspace, sensitivity, confirmation, and durable
receipt rules.

> **v1 boundary:** this is a **local stdio-only** process. Remote transport is **deferred**. Live
> writeback is **deferred**; the only writeback tool is a preview surface. Owner qualification is
> `not_executed_owner_data_absent`: repository fixtures are not evidence of an authorized private
> or production-owner run.

## Install and run

Install the optional MCP dependency, then launch the packaged process:

```bash
uv sync --extra mcp
rf-operator-mcp
```

For an MCP-aware client, register it as a stdio command:

```json
{
  "mcpServers": {
    "rf-operator-mcp": {
      "type": "stdio",
      "command": "rf-operator-mcp"
    }
  }
}
```

The server refuses SSE and Streamable HTTP activation through its normal instance methods. This is
a transport guard, not a sandbox against arbitrary code already running in the same Python process.

## Closed tool inventory

The server registry derives this exact 14-name inventory from the policy contract; it has no
wildcard or arbitrary-dispatch tool.

| Tool | Role |
|---|---|
| `operation.preflight` | Evaluate a requested operation and, when required and allowed, mint a bound confirmation. |
| `run.plan` | Plan a research run. |
| `swarm.start` | Start a governed swarm. |
| `job.status` | Read a job's bounded lifecycle status. |
| `job.cancel` | Request cancellation at a supported safe point. |
| `job.resume` | Resume a recoverable operation. |
| `external_report.import` | Hand an external-report packet to the ERI-owned import flow. |
| `source.ingest` | Hand source ingestion to its canonical service. |
| `run.extract` | Run bounded extraction for a run. |
| `run.claim_map` | Build or update the run's claim map. |
| `run.synthesize` | Synthesize a report from governed evidence. |
| `run.verify` | Verify the run's report/claim evidence. |
| `run.bundle` | Build an evidence bundle after required prerequisites pass. |
| `writeback.preview` | Produce a governed preview only; it does not execute a live writeback. |

These tools coordinate existing authorities; they do not replace them. Their contracts remain in
[Knowledge MCP](knowledge-mcp.md), [RPC](../dev/guides/research-provenance-continuity.md),
[ERI](external-research-interchange.md),
[CARP](../dev/guides/catalog-assisted-research-planning.md),
[RAL](assertion-ledger.md) and
[activation](../project_plans/PRDs/features/assertion-ledger-activation-v1.md),
[RFUP](../project_plans/human-briefs/rfup-external-routing.md), and the
[Search Router](../project_plans/design-specs/research_foundry_search_router_spec.md).

## Preflight and confirmation

Call `operation.preflight` before an operation that requires confirmation. The server resolves the
operator identity and sensitivity ceiling from local configuration; clients do not supply either.
It checks policy and, on an allow decision, returns a confirmation for the same canonical operation
inputs, targets, policy snapshot, and expiry. Keep the opaque token private and present it only for
that exact operation.

`job.status` is the bounded lifecycle read exception: it can return an allowed result without a
confirmation. A denied preflight does not create an operation, receipt, or adapter effect. An
allowed confirmation-requiring preflight persists one confirmation record; it does not execute the
requested operation.

## Receipts and errors

Operation progress is represented by a versioned, discriminated receipt envelope. Its five kinds
are `operation_receipt`, `action_receipt`, `effect_receipt`, `checkpoint`, and
`terminal_receipt`. Receipts describe durable operation truth; audit delivery is supplemental and
its delivered/degraded/unavailable disposition is recorded rather than silently erasing that truth.

Errors are bounded, redacted envelopes with a closed `reason_code`. Do not parse error text for
authorization or existence information. In particular, a missing target, another workspace's
target, and a target above the allowed sensitivity use the same safe `not_found` shape.

## Troubleshooting and limits

- If startup reports that MCP is unavailable, install the `mcp` extra shown above. The base package
  intentionally remains usable without it.
- Use a configured local operator identity and a valid configured sensitivity ceiling. Missing or
  invalid resolution fails closed rather than granting broader access.
- Reuse the same idempotency key only for a retry of the same bound operation. Changed inputs with
  the same key are rejected.
- Treat a cancellation as a request to stop at a supported safe point; use `job.status` and, when
  applicable, `job.resume` to observe recovery.
- Do not attempt remote mounting or live writeback. Those capabilities are deferred, not hidden
  flags or implied by a successful preview.
