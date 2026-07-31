---
schema_version: 2
doc_type: design-spec
title: "Operator MCP Remote Transport"
status: deferred
maturity: shaping
created: 2026-07-31
updated: 2026-07-31
feature_slug: research-foundry-operator-mcp
deferred_from: "research-foundry-operator-mcp-v1 M3"
deferred_item_id: OPM-DF-REMOTE-TRANSPORT
category: backlog
owner: nick
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
related_documents:
  - docs/user/research-foundry-operator-mcp.md
  - docs/dev/architecture/operator-mcp-governance.md
  - docs/user/knowledge-mcp.md
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
---

# Operator MCP Remote Transport

## What is deferred

The shipped Operator MCP is a local stdio-only process. Adding a remotely reachable transport
(including SSE, Streamable HTTP, HTTPS gateway, tunnel, or hosted connector registration) is
**deferred**. The current stdio guard is not an approval or partial implementation of any remote
transport.

## Why it is deferred

Remote reachability changes the trust boundary materially: the configured local operator identity
cannot be reused as remote caller identity, and confirmation binding, workspace isolation,
sensitivity ceilings, rate limits, token confidentiality, audit attribution, and deployment
ownership all require a remote-specific design and evidence. None is established by local fixtures.
Owner qualification is `not_executed_owner_data_absent`.

## Promotion gates

Do not promote this shaping note to an implementation plan until all of the following are named and
approved:

1. A remote caller-authentication and workspace-identity contract, including revocation and service
   identity handling.
2. A transport-specific authorization, confirmation-token storage/handling, and replay-defense
   design that preserves the local no-existence-leak behavior.
3. Network exposure, TLS, secret ownership/rotation, rate limiting, logging/redaction, incident
   response, and rollback ownership.
4. A public-safe integration test matrix plus an authorized owner-held canary. The latter remains
   separate evidence and may not be inferred from a passing repository test.
5. A decision on whether remote clients are a direct Operator MCP surface or must pass through a
   separately governed gateway.

## Non-goals

This document does not select a protocol, authorize a tunnel, define a hosted connector, or change
the local stdio guard. It does not make the local Operator MCP remotely compatible by implication.
