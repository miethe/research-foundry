---
title: Research Foundry Knowledge MCP Remote Transport
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
  Exposing the local read service over a network adds identity, tenant,
  authorization, session, revocation, rate-limit, origin, TLS, observability,
  and incident-response boundaries that local stdio does not solve.
open_questions:
  - "Which hosted clients and MCP protocol versions form the qualification matrix?"
  - "Which identity provider, grant, audience, and scope vocabulary are approved?"
  - "Is workspace selection token-bound, route-bound, or both, and how is ambiguity denied?"
  - "What session and rate-limit partition prevents cross-workspace timing signals?"
  - "Which privacy-safe audit fields are mandatory for incident response?"
explored_alternatives:
  - "Promote local stdio as hosted-compatible: rejected because hosted clients cannot reach loopback resources."
  - "Reuse local trust, ambient filesystem identity, or provider/operator credentials remotely: rejected because it weakens workspace and capability isolation."
  - "Share the Search Router or Operator process/registry: rejected because the Knowledge MCP must retain a read-only credential and dependency boundary."
  - "Defer remote transport behind a separately qualified canonical HTTPS profile: retained shaping baseline."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
---

# Research Foundry Knowledge MCP Remote Transport

## Decision

Remote Knowledge MCP transport is deferred. Local v1 is an independent stdio
process and is only schema-aligned with the frozen core `search(query)` and
`fetch(id)` DTOs. It is not OpenAI/ChatGPT-compatible because a hosted client
cannot reach loopback resources. A compatibility claim requires a separately
qualified, reachable canonical HTTPS remote profile.

## Problem Statement

Exposing the local read service over a network adds identity, tenant,
authorization, session, revocation, rate-limit, origin, TLS, observability, and
incident-response boundaries that stdio does not solve. Reusing local trust or
provider/operator credentials would weaken workspace isolation and could place
cost-bearing or mutating capabilities in the read-only process.

## Required Remote Profile

The promoted profile must define:

- one canonical HTTPS MCP endpoint with owned DNS, valid TLS, explicit protocol
  version, bounded request/response sizes, timeouts, and connection limits;
- supported Streamable HTTP lifecycle, session creation/expiry/revocation,
  retry/idempotency rules, and safe behavior after process loss;
- OAuth/OIDC authorization-code or other approved user/agent flow with audience,
  issuer, scopes, token lifetime, refresh/revocation, and key-rotation rules;
- deterministic binding from authenticated principal to authorized workspace,
  sensitivity ceiling, allowed use/kinds, and capability set before lookup;
- no fallback to local trust, anonymous workspace inference, shared provider
  credentials, Search Router/Operator registries, or ambient filesystem identity;
- request, tenant, and tool rate limits that cannot reveal hidden membership;
- TLS/origin/host validation, DNS-rebinding defenses, request-smuggling and
  cross-origin protections appropriate to the selected MCP transport;
- bounded privacy-safe audit/metrics that do not persist returned text, denied
  IDs, bearer tokens, raw queries, or cross-tenant counts; and
- deployment, health, rollback, revocation, incident-response, and owner-held
  canary procedures with repository readiness kept separate from qualification.

## Core Contract Preservation

Remote transport may not change the core tool contract:

- `search` input is exactly `{query: string}` and output is exactly the frozen
  `SearchDTO`;
- `fetch` input is exactly `{id: string}` and output is exactly the frozen
  `FetchDTO`;
- each DTO appears identically in `structuredContent` and one text `content`
  block containing deterministic canonical JSON; and
- filters, paging, receipts, and typed reads remain separately named `rf_*`
  tools.

## Open Questions

1. Which hosted clients and MCP protocol versions form the qualification matrix?
2. Which identity provider, grant, audience, and scope vocabulary are approved?
3. Is workspace selection token-bound, route-bound, or both, and how is ambiguity denied?
4. What session and rate-limit partition prevents cross-workspace timing signals?
5. Which privacy-safe audit fields are mandatory for incident response?

## Promotion Gates

1. Approve a remote threat model covering authentication bypass, tenant confusion,
   DNS rebinding, origin abuse, replay, session fixation, token theft, rate-limit
   side channels, dependency compromise, and denial-of-service.
2. Approve canonical URL and remote-cache-isolation specs; transport cannot promote alone.
3. Prove process/import/settings/credential separation from Search Router and Operator MCP.
4. Pass two-workspace, hidden=missing, token expiry/revocation, wrong audience,
   wrong workspace, protocol error, retry, overload, and process-loss fixtures.
5. Deploy to an owner-controlled canonical HTTPS endpoint and prove live
   `search`/`fetch` DTO and dual-encoding conformance from each named hosted client.
6. Obtain security, privacy, operations, and workspace-owner approval on the exact profile.

## Non-Goals

- Shipping remote transport in local v1.
- Adding acquisition, provider, import, job, approval, mutation, or writeback tools.
- Sharing provider/operator secrets, registries, or process configuration.
- Claiming compatibility from schemas, localhost tests, or repository fixtures alone.
