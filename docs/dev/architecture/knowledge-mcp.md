---
title: "Research Foundry Knowledge MCP — Architecture"
description: "Architecture of the governed, read-only Knowledge access surface: KnowledgeAccessContext, KnowledgeAccessService, the four KindProjectors, the frozen core/RF DTO split with dual encoding, and the independent rf-knowledge-mcp stdio process."
audience: [developers, ai-agents]
tags: [mcp, knowledge-access, read-only, architecture, stdio]
created: 2026-07-27
updated: 2026-07-27
category: architecture
doc_type: architecture
schema_version: 1
status: active
feature_slug: research-foundry-knowledge-mcp
owner: nick
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - .codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md
  - docs/user/knowledge-mcp.md
  - docs/dev/architecture/search-router/architecture.md
  - docs/dev/architecture/search-router/security.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
  - .claude/findings/research-foundry-knowledge-mcp-findings.md
---

# Research Foundry Knowledge MCP — Architecture

> Source of truth for behavior: `src/research_foundry/services/knowledge_access.py`
> (the governed service), `src/research_foundry/knowledge_mcp/` (the independent stdio
> process), `src/research_foundry/cli/commands/knowledge.py` (`rf knowledge ...`), and
> `src/research_foundry/api/routers/knowledge.py` (`GET /api/knowledge/...`). This document
> describes what exists today; deferred behavior is called out explicitly in
> [Local, not remote](#6-local-not-remote-v1-boundary) below.

The **RF Knowledge MCP** gives local agents bounded, URL-backed, policy-projected reads over
four existing RF domains — sources, assertions, reports, and runs — through one shared,
read-only service, and exposes it identically over four transports: an MCP stdio process, the
`rf` CLI, a GET-only HTTP API, and (internally) the service's own Python API. It never
writes, rebuilds, or mutates anything; it never creates a second catalog; and it never
duplicates policy logic per transport.

## 1. Layered architecture

```text
KnowledgeAccessContext           (identity, sensitivity ceiling, tool — resolved by the
      |                           calling transport, never accepted as a request field)
      v
KnowledgeAccessService           (policy-first: search_core/fetch_core frozen tools,
      |                           search_extended/fetch_extended RF tools, the shared
      |                           _search/_fetch composer)
      v
KindProjector registry           (4 non-writing projectors, one per governed read authority)
  SourceKindProjector       -> catalog_service   (query-only connection)
  AssertionKindProjector    -> assertion_catalog  (non-rebuilding search_read_only/packet_read_only)
  ReportKindProjector  x2   -> builder_service    (load_draft/list_drafts/export_markdown; one
                                                    instance per target_kind: report_draft, report_final)
  RunKindProjector          -> export_service     (list_runs/export_run)
      |
      v
Frozen core / RF DTOs + dual encoding
  KnowledgeSearchResponse / KnowledgeSearchResultItem   (core SearchDTO)
  RfKnowledgeSearchOutcome / RfKnowledgeSearchResultItem (RF-extended)
  KnowledgeDocument                                      (core FetchDTO)
  RfKnowledgeDocument                                    (RF-extended, + typed getters)
      |
      v
Four transports, same DTOs, no per-transport policy logic
  rf-knowledge-mcp (stdio MCP process; own registry.py/settings.py/process.py)
  rf knowledge ...  (CLI; cli/commands/knowledge.py)
  GET /api/knowledge/...  (api/routers/knowledge.py)
```

Every layer below `KnowledgeAccessContext` is shared code. A transport (MCP tool, CLI
subcommand, or HTTP route) resolves a context, calls one `KnowledgeAccessService` method, and
renders the returned DTO's `.to_dict()` — nothing else. This is invariant 4 below.

### 1.1 `KnowledgeAccessContext` (policy input, resolved by the transport)

`research_foundry.services.knowledge_access.KnowledgeAccessContext` is a frozen dataclass
carrying exactly:

- `identity: AuthIdentity | None` — **local trust** (`None`) for the stdio MCP process and the
  `rf knowledge` CLI (no separate remote auth in v1, same as every existing `rf` read command);
  **enforced identity** (`request.state.identity`, possibly `None` when no auth provider is
  configured) for the GET-only HTTP API — the same WKSP-304 row-level isolation pattern every
  other RF read router already uses.
- `sensitivity_ceiling: str` — one of `public` / `personal` / `work_sensitive` /
  `client_sensitive` (`export_service.SENSITIVITY_ORDER`), resolved by
  `resolve_context()` from an explicit transport override, else the workspace's configured
  ceiling. A request can never widen this by adding a field to its own body.
- `tool: str` — one of the eight frozen tool names (below); every activity receipt's `tool`
  field is this same string, never a transport-invented label.

`resolve_context()` is the **only** place identity, sensitivity, and tool eligibility are
resolved. No `KnowledgeAccessService` method accepts a raw identity/workspace argument instead.

### 1.2 `KnowledgeAccessService` (policy-first, zero writes)

`KnowledgeAccessService` exposes two tool pairs, both delegating to the same private
`_search`/`_fetch` composer:

- **Frozen core** — `search_core(context, query=...)` -> `KnowledgeSearchResponse`;
  `fetch_core(context, knowledge_id=...)` -> `KnowledgeDocument`. Exactly the P1-frozen
  `search(query)` / `fetch(id)` contract; never accepts filters, kinds, paging, or a receipt
  flag.
- **RF-extended** — `search_extended(context, query=..., kinds=, limit=, cursor=,
  parent_run_ref=, include_receipt=)` -> `RfKnowledgeSearchOutcome`; `fetch_extended(...)` ->
  `RfKnowledgeDocument`. `include_receipt` defaults to `False` so every P2/P3 caller that
  compares against a receipt-less literal keeps passing; the four typed getters and the
  `rf_search`/`rf_fetch` tools always pass `include_receipt=True`.

The shared `_search`/`_fetch` composer: validates the query/limit/id shape; resolves
`eligible_kinds()` (a `kinds` filter can only **narrow**, never widen, the five-kind
vocabulary); asks each registered `KindProjector` for its page; merges candidates with a
deterministic `(kind, opaque_id)` sort key (`deterministic_id_sort_key`) so repeated calls
against the same snapshot replay byte-identically; and bounds the result to the resolved
limit. A kind with **no registered projector** contributes zero results and denies safely
(`KnowledgeDenied("projection_unavailable")`) — indistinguishable in shape from a real policy
denial (KMCP-OQ-1). The service never opens a database connection, writes a file, or calls a
rebuild/import/migration function itself (invariant 2); every read authority it calls is
already an existing, authoritative RF service.

### 1.3 The four `KindProjector` implementations

`KindProjector` is a `Protocol` with `search(...)` and `fetch(...)`; a concrete projector
resolves ONE governed read authority into allowlisted `RfKnowledgeSearchResultItem` /
`RfKnowledgeDocument` values, after policy has already filtered the underlying records. Every
projector folds the sensitivity ceiling — and, when WKSP-304 isolation is active, the
workspace scope — directly into the read itself, before deriving a title/snippet/URL/
provenance field; every projector must raise `KnowledgeDenied` for anything unknown, hidden,
cross-workspace, or rights-denied, never return a partial document.

| Kind | Projector | Read authority (never a mutator) | Allowlisted fields (`rf_metadata`) | Path stripping |
|---|---|---|---|---|
| `source` | `SourceKindProjector` | `catalog_service.query_only_connection` / `is_catalog_available` | `source_type`, `trust`, bounded `evidence_points` (claim_id/relation/quote/summary, threshold-filtered), `provenance` (catalog_item_id/run_id/source_card_id) | source-card `url` only becomes `original_source_url` when it is already `http(s)` |
| `assertion` | `AssertionKindProjector` | `AssertionCatalog.search_read_only` / `.packet_read_only` (non-rebuilding) | `assertion_version`, `lifecycle_state`, `qualifiers`, `source_edition` (id/media_type/access_scope/captured_at), `passage_id`, bounded `evaluations`, `rights_decision`, `provenance` (incl. bounded `run_uses`) | edition `retrieval_locator.file_path` never surfaced; only its sibling `.url` (if `http(s)`) |
| `report_draft` / `report_final` | `ReportKindProjector` (one instance per `target_kind`) | `builder_service.list_drafts` / `.load_draft` / `.export_markdown` (read-only; never `create_draft*`/`add_block`/`delete_draft`) | `status`, `audience`, `origin`, `block_count`, `claim_link_count`, `source_link_count`, `provenance` (report_draft_id/source_run_id) | `export_markdown` never emits a raw path |
| `run` | `RunKindProjector` | `export_service.list_runs` / `.export_run` (the existing DF-004 run read model) | `status_derived`, `sensitivity`, `claim_counts`, `verification_passed`, `governance_verdict`, `category`, bounded `tags`, `provenance` (run_id/intent_id) | `export_run` never emits an artifact path |

`report_draft` and `report_final` are the **same** underlying Report Builder draft entity,
distinguished only by its current lifecycle `status` at read time
(`_report_kind_for_status`: `published`/`archived` resolve to `report_final`; every other
status resolves to `report_draft`) — never stored twice, never merged into one ambiguous
`"report"` kind (KMCP-OQ-2). Fetching a draft by the wrong-kind id denies with the same
generic shape as a missing id.

`_paginate_document_text` (byte-offset cursor pagination) and `_build_receipt` (the caller-carried
activity receipt) are shared across all four projectors' `fetch` paths, so cursor semantics and
receipt shape are identical regardless of kind.

## 2. Frozen core / RF DTO split + dual encoding

Every DTO mirrors the frozen P1 schemas byte-for-byte (`schemas/knowledge_search_request.schema.yaml`,
`schemas/knowledge_search_response.schema.yaml`, `schemas/knowledge_document.schema.yaml`,
`schemas/knowledge_activity_receipt.schema.yaml`):

- **Core `SearchDTO`** (`KnowledgeSearchResponse` / `KnowledgeSearchResultItem`) — closed root,
  exactly `{"results": [...]}`; each item is exactly `{id, title, url}`. No snippet, kind, rank,
  score, or receipt field. At most 10 results.
- **RF `rf_search` outcome** (`RfKnowledgeSearchOutcome` / `RfKnowledgeSearchResultItem`) —
  separately named; adds `kind`, `snippet`, `rank`, `score`, the constant
  `content_is_untrusted: true`, `next_cursor`, `truncated`, and an optional `receipt`. At most
  50 results per page.
- **Core `FetchDTO`** (`KnowledgeDocument`) — closed root, exactly `id`/`title`/`text`/`url`
  required plus an open, optional `metadata` map (the one deliberate place the core schema
  accepts arbitrary keys).
- **RF-extended document** (`RfKnowledgeDocument`) — returned by `rf_fetch` and all four typed
  getters; adds `kind`, `original_source_url`, `truncated`, `next_cursor`, a typed
  `rf_metadata` bag, `content_is_untrusted: true`, and an optional `receipt`.

**Dual encoding (KMCP-1.3).** Every MCP tool result places the identical DTO dict in both
`structuredContent` and exactly one `content` block of
`{"type": "text", "text": "<canonical-json>"}`, using this repo's existing canonical-JSON
convention (`json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)` — the
same algorithm as `assertion_identity.canonical_source_assertion_json`). `registry.py`
constructs this by hand (`mcp.types.CallToolResult`, `structured_output=False`) rather than
relying on FastMCP's own signature-derived JSON, which uses a different (indented,
insertion-ordered) convention.

**Opaque IDs and local URLs (invariant 6).** Every id is `rfk:v1:<kind>:<opaque>`
(`parse_knowledge_id`); every `url` is a route-backed, loopback-only, non-canonical resource
URL of the exact form `http(s)://(127.0.0.1|localhost|[::1])[:port]/api/knowledge/v1/fetch/<percent-encoded-id>`
(`build_local_resource_url`) — never a filesystem path, never a raw database row id. A
`search`/`rf_search` result's `url` is the SAME url `fetch`/`rf_fetch` resolves for that id
(self-referential fetch route, KMCP-OQ-3).

**Caller-carried activity receipt (KMCP-OQ-4).** RF-extended tools optionally attach a
`knowledge_activity_receipt`-shaped dict: `schema_version`, `type`, `tool`, `generated_at`,
`persisted: false` (hard-pinned — the service never writes this receipt anywhere), a one-way
SHA-256 `request_context_hash` over the normalized request+policy context, `policy_version`
(`KNOWLEDGE_POLICY_VERSION = "kmcp-v1"`), `returned_ids` (exact echo, never a superset),
`bounds` (results/text counts and truncation, scoped to what was returned), and an optional
`correlation_ref` echoing the caller's `parent_run_ref`. It never carries a total-candidate,
denied, or hidden count — "no denied membership" is enforced by field absence, not a flag.

## 3. The exact eight tools

The registry (`research_foundry.knowledge_mcp.registry`) — and the CLI/API transports that
mirror it — expose **exactly** these eight tools, reused (not redefined) from
`knowledge_access.TOOL_NAMES`:

| # | Tool | CLI (`rf knowledge ...`) | API route | Shape |
|---|---|---|---|---|
| 1 | `search` | — (core; no CLI parity) | `GET /api/knowledge/v1/search?query=` | Frozen core `SearchDTO` |
| 2 | `fetch` | — (core; no CLI parity) | `GET /api/knowledge/v1/fetch/{id}` | Frozen core `FetchDTO` |
| 3 | `rf_search` | `search QUERY [--kind --limit --cursor --parent-run-ref --sensitivity-threshold]` | `GET /api/knowledge/search` | RF-extended search outcome |
| 4 | `rf_fetch` | `fetch ID [--cursor --parent-run-ref --sensitivity-threshold]` | `GET /api/knowledge/fetch/{id}` | RF-extended document |
| 5 | `rf_source_get` | `source-get ID [...]` | `GET /api/knowledge/source/{id}` | RF-extended document, kind-scoped to `source` |
| 6 | `rf_assertion_get` | `assertion-get ID [...]` | `GET /api/knowledge/assertion/{id}` | RF-extended document, kind-scoped to `assertion`; always denies in v1 (see [§5](#5-known-limitations)) |
| 7 | `rf_report_get` | `report-get ID [...]` | `GET /api/knowledge/report/{id}` | RF-extended document, kind-scoped to `report_draft` OR `report_final` |
| 8 | `rf_run_get` | `run-get ID [...]` | `GET /api/knowledge/run/{id}` | RF-extended document, kind-scoped to `run` |

No acquisition, extraction, job, import, approval, bundle, provider, cache-build,
telemetry-write, audit-write, persistence, or writeback tool name may ever appear in this
registry. There is no POST/PUT/PATCH/DELETE route anywhere in `api/routers/knowledge.py`.

Every typed getter (`rf_source_get`/`rf_assertion_get`/`rf_report_get`/`rf_run_get`) checks the
id's kind segment via `parse_knowledge_id` **before** it ever reaches the governed read
authority; a wrong-kind id denies with the exact same generic message as a missing id — never a
distinguishing "wrong kind" signal.

**Safe denial, everywhere.** `search`/`rf_search` never raise for a policy denial or a
malformed query — they collapse to the same empty `results: []` shape a zero-match query would
produce. `fetch`/`rf_fetch` and all four typed getters map **every** `KnowledgeAccessError`
(malformed id, missing, hidden, cross-workspace, rights-denied, stale/unavailable projection,
wrong-kind) to the same generic, detail-free denial (`"Unable to fetch the requested knowledge
id."` — an MCP tool error, a CLI exit-1 stderr line, or an HTTP 404, depending on transport) —
the exception's own internal `reason` is never rendered.

## 4. The independent `rf-knowledge-mcp` process

`research_foundry.knowledge_mcp` is a separate package (`process.py`, `registry.py`,
`settings.py`) with its own packaged entry point (`rf-knowledge-mcp`, `pyproject.toml`
`[project.scripts]`), distinct from the Search Router's `rf-mcp`
(`research_foundry.services.search_router.mcp_launcher`) and from any Operator/Hermes process.
It never imports `research_foundry.services.search_router.*`, and the Search Router never
imports this package.

- **`process.py` (`main()`)** — resolves this process's own `KnowledgeMcpSettings`, sets the
  log level, calls `registry.build_server(settings)`, and runs it — stdio only.
- **`registry.py` (`build_server`)** — the **sole** place any `rf-knowledge-mcp` tool name is
  registered. Bootstraps the four concrete `KindProjector`s against this process's resolved
  `FoundryPaths`, constructs a genuine `FastMCP` **subclass** (`_StdioOnlyFastMCP`, not a
  wrapper) whose `sse_app`/`streamable_http_app`/`run_sse_async`/`run_streamable_http_async`
  all raise `UnsupportedTransportError`, and whose `run()` refuses any `transport` other than
  `None`/`"stdio"`. Lazily imports the `mcp` SDK, raising a clear `RuntimeError` naming the
  `mcp` extra if it is missing.
- **`settings.py` (`resolve_settings`)** — reads **only** the Foundry workspace root
  (`RESEARCH_FOUNDRY_HOME`, same `FoundryPaths.discover()` mechanism every RF transport
  already uses), an optional `foundry.knowledge_mcp.sensitivity_threshold_max` config ceiling
  (a namespace deliberately separate from the Search Router's own `foundry.mcp.*`), and a
  dedicated `RF_KNOWLEDGE_MCP_LOG_LEVEL` env var. `ALLOWED_ENV_VARS` is the exact, exhaustive
  set. It never reads a Search Router provider credential, an Operator/Hermes token
  (`RF_TOKEN_AGENT` included), a writeback credential (MeatyWiki/SkillMeat/CCDash), or a
  catalog-build/migration flag.

**Local trust caveat.** This process always resolves `identity=None` ("local trust" — the
calling OS process's own identity; no separate remote auth in v1). Every assertion read
unconditionally requires a non-`None` identity with a workspace id (an assertion-catalog
invariant, not gated by the WKSP-304 flag) — so `rf_assertion_get` denies generically for
**every** id through this stdio process today, and `search`/`rf_search` never return an
`assertion`-kind result through it either. This is expected v1 behavior, not a bug (see
[§5](#5-known-limitations)).

## 5. Known limitations

- **`rf_assertion_get` always denies via the stdio MCP process and the `rf` CLI** (local trust,
  `identity=None`) — see §4 above. It can succeed only through the GET-only HTTP API when a
  real, workspace-bearing identity is resolved from configured auth middleware.
- **`rf-knowledge-mcp` needs the `serve` extra, not only `mcp`.** `KnowledgeAccessService`
  transitively imports `research_foundry.api.auth.scope.resolve_workspace_isolation_active`
  (real, load-bearing WKSP-304 logic), and `research_foundry.api.__init__` unconditionally
  imports `fastapi`/`uvicorn` so that importing the always-installed `research_foundry.api`
  package fails loudly if the `serve` extra is missing. An operator who installs only
  `pip install 'research-foundry[mcp]'` (no `serve`) will see a raw `ModuleNotFoundError:
  fastapi` on process start, not the module's own hand-written missing-SDK message. This is a
  real, pre-existing gap, not a regression — see
  [`.claude/findings/research-foundry-knowledge-mcp-findings.md`](../../../.claude/findings/research-foundry-knowledge-mcp-findings.md)
  (KMCP-F1) for the full root-cause writeup and promotion trigger. It does **not** weaken
  invariant 1 (the process's registry/settings/credential allowlist still admit no Search
  Router/Operator/provider dependency) — it is an installability gap, not a boundary leak.

## 6. Local, not remote (v1 boundary)

The v1 local stdio Knowledge MCP is **schema-aligned only**: it implements the exact frozen
`search(query)`/`fetch(id)` shapes a hosted MCP client (e.g. an OpenAI/ChatGPT-style connector)
would expect, but it makes **no** hosted-client compatibility claim, anywhere. A hosted client
cannot reach `local_resource_url`'s loopback-only address, and this process registers stdio
only — Streamable HTTP, SSE, OAuth, and any non-loopback listener are refused at the code level
(`_StdioOnlyFastMCP`), not only by convention.

Four shaping specs (`status: deferred`, `maturity: shaping`) record what a remote profile would
require, and all four must be independently promoted — plus a reachable canonical HTTPS
endpoint qualified and a named security/privacy sign-off recorded — before any compatibility
claim, local or remote, may be made:

- [`research-foundry-knowledge-mcp-remote-transport.md`](../../project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md) — remote MCP transport (Streamable HTTP, session/OAuth, rate limits, incident response).
- [`research-foundry-knowledge-mcp-canonical-resource-urls.md`](../../project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md) — a remotely reachable, owned-HTTPS canonical resource-URL namespace.
- [`research-foundry-knowledge-mcp-remote-cache-isolation.md`](../../project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md) — any remote/multi-tenant cache placed in front of Knowledge reads.
- [`reusable-assertion-ledger-shared-indexes.md`](../../project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md) — any shared/cross-workspace assertion index Knowledge search could draw on remotely.

See [`docs/user/knowledge-mcp.md`](../../user/knowledge-mcp.md) for the operator-facing version
of this same boundary, and the [Reviewer and Closeout Contract in the implementation
plan](../../project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md#reviewer-and-closeout-contract)
for how this was verified.

## 7. Invariants

1. **Separate process and registry.** `rf-knowledge-mcp` has its own entry point,
   settings/credential allowlist, dependency boundary, and inventory; it never
   imports/registers/calls a Search Router or Operator tool.
2. **Read means no writes.** No cache/index rebuild, database creation/WAL, run/source
   creation, audit artifact, telemetry artifact, or writeback.
3. **Policy before derivation.** Hidden records cannot affect counts, snippets, ranks,
   cursors, URLs, links, receipts, or timing detail.
4. **One service contract.** Transports (CLI/API/MCP) contain parsing/rendering only; all
   policy and business logic lives in `KnowledgeAccessService`.
5. **Frozen core.** `search` accepts only `query` and `fetch` only `id`; fixed DTOs are
   emitted identically in `structuredContent` and one canonical-JSON text block. RF
   paging/filter/receipt extensions use separate names and never merge onto the core root.
6. **Stable references.** Opaque IDs are authority-neutral; local URLs use allowlisted GET
   routes, never expose a filesystem path, and are explicitly non-canonical.
7. **Bounded, untrusted data.** Content is byte/page limited and marked untrusted
   (`content_is_untrusted: true`).
8. **Remote truth.** No Streamable HTTP, SSE, OAuth, non-loopback listener, canonical HTTPS
   URL, or OpenAI/ChatGPT compatibility claim in v1.

## Related documents

- PRD: [`research-foundry-knowledge-mcp-v1.md`](../../project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md)
- Implementation plan: [`research-foundry-knowledge-mcp-v1.md`](../../project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md)
- Decisions block: [`decisions-block.md`](../../../.codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md)
- User-facing guide: [`docs/user/knowledge-mcp.md`](../../user/knowledge-mcp.md)
- Findings: [`research-foundry-knowledge-mcp-findings.md`](../../../.claude/findings/research-foundry-knowledge-mcp-findings.md) (KMCP-F1)
