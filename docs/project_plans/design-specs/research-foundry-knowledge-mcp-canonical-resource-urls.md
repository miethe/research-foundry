---
title: Research Foundry Knowledge MCP Canonical Resource URLs
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
  Hosted clients need reachable resource URLs without allowing the URL namespace
  to leak tenant membership or replace governed identity, authorization,
  versioning, migration, revocation, and deletion semantics.
open_questions:
  - "What changes require a new opaque-ID version rather than a route/API version?"
  - "Which redirects are permanent, how long are they retained, and how are targets allowlisted?"
  - "Can a resource move hosts without revealing that the old ID existed?"
  - "How are tombstone, retention, legal deletion, and lifecycle invalidation represented?"
  - "Which URL remains stable when an edition or report receives a new version?"
  - "How does a client discover a successor without treating mutable content as the same resource?"
explored_alternatives:
  - "Treat loopback routes as canonical: rejected because hosted clients cannot reach them and they are not durable citations."
  - "Expose original public source locators as RF resource URLs: rejected because locators are not RF authority and may leak governed metadata."
  - "Embed workspace names, paths, titles, or sequential database IDs in URLs: rejected for privacy, migration, and authority reasons."
  - "Use an owned HTTPS namespace with versioned opaque knowledge IDs: retained shaping baseline pending host and migration decisions."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
---

# Research Foundry Knowledge MCP Canonical Resource URLs

## Decision

Canonical remotely reachable resource URLs are deferred. Local loopback route
templates are useful transport references but are not durable citations,
canonical identity, or evidence of hosted-client reachability. Opaque knowledge
IDs remain the authority-neutral lookup key in local v1.

## Problem Statement

A remote `search` result must contain a URL that its intended hosted client can
reach, while authorization must still occur before resource-derived output. A
URL namespace also needs host ownership, TLS, versioning, migration, redirect,
revocation, deletion, and cross-workspace no-leak semantics. Treating localhost
or a mutable deployment hostname as canonical would create broken citations and
could leak tenant membership.

## Candidate Canonical Form

The shaping baseline is:

```text
https://<owned-host>/knowledge/v1/resources/<opaque-knowledge-id>
```

The exact host and route remain undecided. The URL:

- contains no workspace name, filesystem path, source locator, title, content
  digest, sensitivity, provider, or sequential database identifier;
- uses the same versioned opaque ID resolved by `fetch(id)` but does not make
  the URL itself canonical evidence authority;
- requires authenticated policy evaluation before content or resource-derived
  metadata, and makes hidden and absent resources indistinguishable;
- never redirects to `file:`, loopback, private/reserved/link-local/metadata,
  unowned, downgraded HTTP, or user-supplied origins;
- returns stable bounded terminal behavior for deleted, tombstoned, invalidated,
  migrated, and unsupported-version resources; and
- separates governed RF resource URL from the original public source locator.

## Version and Migration Rules to Freeze

- What changes require a new opaque-ID version versus a route/API version?
- Which redirects are permanent, how long are they retained, and how are targets allowlisted?
- Can a resource move hosts without revealing that the old ID existed?
- How are tombstone, retention, legal deletion, and lifecycle invalidation represented?
- Which URL remains stable when an edition or report receives a new version?
- How does a client discover a successor without treating mutable content as the same resource?

## Reachability and Security Tests

The promoted design must test owned DNS/TLS, hosted-client reachability,
authorization-before-resolution, wrong workspace, hidden/absent equality,
expired/revoked identity, route-version mismatch, encoded IDs, path traversal,
host-header abuse, open redirect, redirect loop/downgrade/private pivot, and
response cache controls. Tests must cover both IPv4 and IPv6 deployment paths.

## Promotion Gates

1. Approve host ownership, DNS/TLS issuance and rotation, availability target,
   privacy-safe monitoring, and incident-response owner.
2. Approve opaque ID/version/redirect/tombstone/deletion/migration semantics.
3. Approve the remote transport and cache-isolation specs; URLs cannot promote alone.
4. Prove every core search URL resolves from named hosted clients to the same
   governed identity returned by `fetch(id)` without cross-workspace signals.
5. Prove no local/non-canonical URL or original locator is mislabeled canonical.
6. Record exact live reachability evidence before any OpenAI/ChatGPT compatibility claim.

## Non-Goals

- Making loopback URLs canonical.
- Using URLs as authorization, workspace identity, or evidence identity.
- Exposing raw source locators or paths as RF resource URLs.
- Promoting remote transport, public sharing, or cross-workspace federation by implication.
