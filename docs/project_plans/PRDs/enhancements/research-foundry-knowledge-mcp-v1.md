---
title: "PRD: Research Foundry Knowledge MCP"
schema_version: 2
doc_type: prd
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-foundry-knowledge-mcp
feature_version: v1
tier: 3
effort_estimate: "34 pts bottom-up; see human brief H1-H6"
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
human_brief_ref: docs/project_plans/human-briefs/research-foundry-knowledge-mcp.md
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - .codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md
  - docs/dev/architecture/search-router/architecture.md
  - docs/dev/architecture/search-router/security.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
references:
  user_docs: []
  context: []
  specs:
    - schemas/source_card.schema.yaml
    - schemas/source_assertion.schema.yaml
    - schemas/source_edition.schema.yaml
    - schemas/report_draft.schema.yaml
    - schemas/evidence_bundle.schema.yaml
    - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
    - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
    - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
    - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
  related_prds:
    - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
    - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
    - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
    - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
owner: nick
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [prd, mcp, knowledge-access, read-only, openai-schema-aligned, local-stdio]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/knowledge_search_request.schema.yaml
  - schemas/knowledge_search_response.schema.yaml
  - schemas/knowledge_document.schema.yaml
  - schemas/knowledge_activity_receipt.schema.yaml
  - src/research_foundry/services/knowledge_access.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/assertion_catalog.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/knowledge_mcp/process.py
  - src/research_foundry/knowledge_mcp/registry.py
  - src/research_foundry/knowledge_mcp/settings.py
  - src/research_foundry/cli/commands/knowledge.py
  - src/research_foundry/api/routers/knowledge.py
  - src/research_foundry/api/app.py
  - src/research_foundry/api/openapi.json
  - pyproject.toml
open_questions:
  - id: KMCP-OQ-1
    question: "Which existing read projections need an explicit non-rebuilding mode before the MCP can prove zero filesystem mutation?"
    owner: backend-architect
    status: open
  - id: KMCP-OQ-2
    question: "Which report representation is the v1 fetch authority: run-final report, report draft, or both as distinct kinds?"
    owner: lead-pm
    status: open
  - id: KMCP-OQ-3
    question: "What local loopback base URL is canonical when the stdio server is running without the HTTP server?"
    owner: api-designer
    status: open
  - id: KMCP-OQ-4
    question: "Which fields belong in the caller-carried knowledge activity receipt without leaking denied result membership?"
    owner: backend-architect
    status: open
decisions:
  - decision: "Ship a separate read-only knowledge server; do not register Search Router cost-bearing or file-writing tools."
    rationale: "The current Search Router MCP calls run_search/extract_urls, can reach paid providers, and persists run/source artifacts."
    status: accepted
  - decision: "All CLI, API, and MCP reads delegate to one governed knowledge service."
    rationale: "Thin transports prevent policy, redaction, cursor, URL, and payload-limit drift."
    status: accepted
  - decision: "The v1 transport is local stdio; remote Streamable HTTP and OAuth are deferred."
    rationale: "Remote identity, workspace isolation, rate limits, and canonical HTTPS resource URLs require a separate threat model and promotion gate."
    status: accepted
  - decision: "Call local v1 OpenAI search/fetch schema-aligned, not OpenAI- or ChatGPT-compatible."
    rationale: "A local stdio process and loopback resource URLs are not reachable from a hosted OpenAI/ChatGPT client; true compatibility requires the separately gated canonical HTTPS remote profile."
    status: accepted
  - decision: "Freeze core `search(query)` and `fetch(id)` with no pagination, filters, or receipts; expose those extensions only through separately named `rf_*` tools."
    rationale: "Adding RF-specific arguments or receipt metadata to the compatibility core makes the alleged contract ambiguous and brittle."
    status: accepted
  - decision: "Return every core DTO twice: the object in `structuredContent` and canonical JSON for the same object in one text `content` block."
    rationale: "Clients that understand structured output and clients that only read text receive the identical frozen DTO."
    status: accepted
  - decision: "Run Knowledge MCP as an independent process with its own registry, entry point, settings/credential allowlist, and inventory; share governed read services only."
    rationale: "Module-level separation is insufficient to prevent Search Router provider credentials or cost/mutation tools from entering the process boundary."
    status: accepted
  - decision: "Knowledge reads return a caller-carried activity receipt but perform no persistence."
    rationale: "Provenance remains observable without hiding a filesystem write inside a read-only tool; persistence belongs to the invoking governed workflow."
    status: accepted
success_metrics:
  - "OpenAI-schema-aligned search(query) and fetch(id) return frozen bounded DTOs over local stdio with identical structuredContent and JSON text content."
  - "Source, assertion, report, and run reads apply workspace, sensitivity, rights, and lifecycle policy before text, counts, URLs, cursors, or existence signals are produced."
  - "CLI, HTTP, and MCP wrappers return contract-equivalent results from the same service fixtures."
  - "A negative tool and filesystem audit proves no network search, job launch, import, approval, bundle, writeback, cache rebuild, database creation, or other mutation."
  - "Process/inventory tests prove the Knowledge MCP registry, entry point, configuration, and credential namespace are independent from Search Router and Operator MCP; only governed read services cross the boundary."
  - "Remote compatibility remains false until the remote transport, canonical resource URL, and cache-isolation shaping specs are promoted and a reachable canonical HTTPS profile is qualified."
---

# Feature Brief & Metadata

**Feature Name:** Research Foundry Knowledge MCP
**Filepath Name:** `research-foundry-knowledge-mcp-v1`
**Date:** 2026-07-18
**Author:** Codex planning worker under delegated orchestration
**Tier / Estimate:** Tier 3 / 34 points bottom-up

## 1. Executive Summary

Research Foundry already has valuable read surfaces: a workspace- and rights-governed
assertion catalog, a sensitivity-gated general catalog, run exports, report drafts, and
source-card projections. Agents cannot consume those surfaces through one stable,
read-only knowledge contract. The only current MCP server is the Search Router wrapper;
its tools call `run_search()` or `extract_urls()`, may reach paid/network providers, and
write runs and source cards. It is therefore an acquisition/operator surface, not the
knowledge surface defined here.

This feature adds a separate `research-foundry-knowledge` service and an
independent local-stdio MCP process. The core tools are schema-aligned
`search(query)` and `fetch(id)` with exact input/output DTOs and dual
`structuredContent` plus canonical-JSON text encoding. Pagination, filters,
receipts, and typed reads exist only under separately named `rf_*` tools. Every
result uses a stable opaque knowledge ID and a local route-backed URL; no
filesystem path is returned as a resource identifier.

All transports delegate to one service. Policy projects workspace, sensitivity, rights,
lifecycle/freshness, and allowed use before matching, counts, snippets, cursors, URLs, or
existence signals. Local stdio ships first. Remote Streamable HTTP, OAuth, multi-tenant
rate limits, and canonical public HTTPS resource URLs remain deferred behind design and
security gates. Local stdio v1 is not OpenAI/ChatGPT-compatible because hosted
clients cannot reach its loopback resources. True compatibility requires a
reachable canonical HTTPS remote profile promoted through the three linked
shaping specs.

## 2. Context & Current State

### 2.1 Existing building blocks

- `AssertionCatalog.search()` and `.packet()` implement private lexical retrieval with
  workspace, rights, lifecycle, cursor, and no-candidate-derived-denial behavior.
- `catalog_service.search()` and `.get_item()` project source, claim, inference, report,
  and related catalog items with sensitivity and enforcing-workspace filters.
- `export_service.list_runs()` and `.export_run()` provide the shared run read model and
  sensitivity gate used by the HTTP run routes.
- `builder_service.list_drafts()` and `.load_draft()` provide workspace-aware report
  draft reads; API routes add sensitivity/no-existence-leak checks.
- `/api/catalog`, `/api/assertions`, `/api/reports`, and `/api/runs` expose substantial
  read contracts, but they are separate DTOs and do not provide OpenAI search/fetch.
- `services/search_router/mcp_server.py` is a useful thin-adapter and optional-SDK pattern,
  but its registered tools are not read-only.

### 2.2 Read-only landmines

The new server cannot merely call every current read method:

- `AssertionCatalog` may lazily rebuild a missing projection, which writes `.rf_cache`.
- General catalog connection/setup may create or migrate `catalog.db` unless an explicit
  read-only/query-only path is used.
- Search Router calls create canonical runs/source cards and may spend provider budget.
- Raw run/report/catalog payloads can contain filesystem paths, overlarge text, hidden
  cross-resource edges, or fields whose policy was designed for a different caller.
- `identity=None` currently means single-operator trust in several services; the MCP must
  make that trust mode explicit and must require workspace identity when isolation is on.

### 2.3 Non-duplication map

| Existing owner | Remains authoritative for | Knowledge MCP owns |
|---|---|---|
| Reusable Assertion Ledger | Assertion/edition/passage identity, rights, lifecycle, evidence packets | Bounded read projection only |
| Research Provenance Continuity | Origin/run/activity envelope and durable lineage | Caller-carried read receipt using that envelope |
| Catalog-Assisted Research Planning | Pre-discovery selection, coverage/residual decisions | Read access to eligible catalog products |
| External Research Interchange | Candidate quarantine, source/passage resolution, verified promotion | No direct exposure of unverified vendor prose as evidence |
| Search Router | Acquisition modes, providers, budgets, run/source-card writes | No provider call; separate tool registry |
| Existing API/service layers | Canonical file/DB reads and policy decisions | Normalized search/fetch DTO and transport parity |

## 3. Problem Statement

> Agents need stable local access to Research Foundry knowledge, but today they must know
> several API/file-specific shapes or call an MCP server whose tools may spend money and
> mutate the workspace. A combined surface would blur retrieval with acquisition and could
> leak sensitive, rights-denied, stale, cross-workspace, or filesystem-only information.

The absence of a shared service also invites separate CLI/API/MCP implementations with
different authorization order, payload limits, IDs, and URL semantics. Remote transport
would amplify those gaps before OAuth, workspace identity, and HTTPS resource identity
are settled.

## 4. Goals and Success Metrics

### Goals

1. Provide exact OpenAI-schema-aligned `search(query)` and `fetch(id)` DTOs over governed RF knowledge, without claiming hosted compatibility.
2. Provide pagination, filters, receipts, and typed source/assertion/report/run reads only through separately named `rf_*` tools.
3. Apply one policy and projection contract across service, CLI, API, and MCP.
4. Prove the local stdio tool inventory and execution are read-only and cost-free.
5. Return bounded text, stable cursors, opaque IDs, and URL-backed references without raw
   filesystem paths.
6. Preserve provenance through a non-persisting activity receipt the caller can attach to
   the canonical run/activity envelope.
7. Enforce an independent process/registry/entrypoint/settings/credential/inventory boundary that shares only governed read services.
8. Keep true OpenAI/ChatGPT compatibility gated on reachable canonical HTTPS remote transport and cache isolation.

### Success metrics

| Measure | Baseline | Target | Evidence |
|---|---:|---:|---|
| Shared knowledge service | 0 | 1 contract used by all transports | Parity fixtures |
| Schema-aligned core tools | 0 | exact `search(query)` and `fetch(id)` plus dual encoding | MCP inventory/schema snapshot |
| Governed typed reads | Fragmented | source/assertion/report/run | Positive and denial matrix |
| Payload bound | Surface-specific | Search text ≤2 KiB/result; fetch page ≤32 KiB; ≤25 results | Boundary tests |
| Filesystem paths in output | Possible in raw exports | 0 | Recursive payload audit |
| Mutating/cost-bearing tools | 5 in Search Router MCP | 0 in knowledge MCP | Inventory + provider/write spies |
| Cross-transport contract drift | Unmeasured | Canonical JSON-equivalent normalized payloads | CLI/API/MCP parity test |
| Process boundary | Search Router registry/process carries cost-bearing capabilities | Dedicated process/registry/entrypoint/settings/credential allowlist/inventory | Import graph, environment, and inventory snapshot |
| Hosted compatibility | None | Explicitly false for local v1; separately qualified reachable HTTPS profile required | Remote-profile promotion evidence |

## 5. Personas and Journeys

### Research agent

Searches local RF knowledge before external discovery, fetches one governed document, and
receives exact provenance IDs plus a source URL without learning internal paths.

### Reviewer

Fetches an assertion packet or report/run summary and sees lifecycle, rights, sensitivity,
workspace-safe lineage, and truncation state needed to judge reuse.

### Local operator

Registers `rf-knowledge-mcp` over stdio with an explicit local trust/workspace policy and
can prove that no tool launches providers, modifies files, creates databases, or writes
back externally.

### High-level flow

```text
CLI / GET API / local stdio MCP
  -> KnowledgeAccessContext (identity/trust mode + sensitivity ceiling + limits)
  -> KnowledgeAccessService
  -> policy-first kind adapters
  -> allowlisted source/assertion/report/run projection
  -> stable opaque id + loopback-backed URL + bounded untrusted text
  -> caller-carried activity receipt (not persisted here)
```

## 6. Requirements

### 6.1 Functional requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| KMCP-FR-1 | Ship Knowledge MCP as a separate OS process with its own registry module, `rf-knowledge-mcp` entry point, settings and credential allowlist, dependency/import boundary, and exact inventory; do not import/register Search Router or Operator registries. | Must | Governed read services are the only shared runtime layer; `rf-mcp` remains unchanged. |
| KMCP-FR-2 | Expose core `search` with input exactly `{query: string}` (`query` required, `additionalProperties: false`) and output exactly `SearchDTO = {results: [{id,title,url}]}`. | Must | No text/snippet, cursor, limit, filter, kind, receipt, metadata, or extension field in the core input/output. |
| KMCP-FR-3 | Expose core `fetch` with input exactly `{id: string}` (`id` required, `additionalProperties: false`) and output `FetchDTO = {id,title,text,url,metadata?}`, where optional `metadata` is the documented generic key/value map (`Record<string, unknown>`), not a closed object. | Must | Root fields are closed; no cursor, page, receipt, or required RF-specific metadata. `kind` and `truncated` are optional metadata keys, never required or exhaustive. |
| KMCP-FR-4 | Encode each core DTO identically in MCP result `structuredContent` and in exactly one `content` text block containing deterministic canonical JSON of that same object. | Must | Decode(text) must deep-equal `structuredContent`; no prose wrapper. |
| KMCP-FR-5 | Expose search snippets, pagination, filters, typed RF metadata, caller-carried receipts, and typed source/assertion/report/run reads only through separately named `rf_search`, `rf_fetch`, `rf_source_get`, `rf_assertion_get`, `rf_report_get`, and `rf_run_get`. | Must | No alternate policy path and no alias under core names. |
| KMCP-FR-6 | Define `KnowledgeAccessContext`, stable opaque IDs, search page, document, denial, cursor, local URL, and activity-receipt contracts. | Must | Additive versioned schemas. |
| KMCP-FR-7 | Apply workspace, sensitivity, rights/allowed-use, lifecycle/freshness/evaluation, and capability projection before matching or emitting any result-derived field. | Must | Policy order is invariant. |
| KMCP-FR-8 | Add explicit non-writing/query-only modes to reused projections; missing caches/indexes return typed unavailable, never rebuild. | Must | Read-only means zero workspace mutation. |
| KMCP-FR-9 | Build local result URLs from an allowlisted route map and configured loopback base; label them local/non-canonical and keep origin URL separate. | Must | No `file://`, absolute path, or compatibility claim. |
| KMCP-FR-10 | Bound core and RF-extended query/result/page/text/link/depth/serialization sizes; core uses fixed server caps while RF tools expose validated pagination/filters. | Must | Stable RF-tool truncation/next-cursor fields only. |
| KMCP-FR-11 | Mark returned source/report text as untrusted data and strip prompt/control framing. | Must | Content never enters tool descriptions/instructions. |
| KMCP-FR-12 | Return a deterministic, non-persisted activity receipt only from `rf_*` tools, with request/context hash, visible returned refs, denial/truncation state, and optional parent run ref. | Should | Core DTOs remain receipt-free; no hidden telemetry write. |
| KMCP-FR-13 | Add thin CLI and GET-only API wrappers with contract-equivalent service/RF-extended outputs and generated OpenAPI. | Must | One shared service. |
| KMCP-FR-14 | Lazy-import the optional MCP SDK so non-MCP RF imports and CLI remain offline-safe. | Must | Mirror existing pattern. |
| KMCP-FR-15 | Fail closed on missing required workspace context, invalid cursor, over-broad ceiling, missing projection, unknown/hidden ID, or route/base-URL mismatch. | Must | Hidden and absent IDs indistinguishable. |
| KMCP-FR-16 | Keep Streamable HTTP, OAuth, non-loopback hosting, canonical HTTPS URLs, remote caching/rate limits, and OpenAI/ChatGPT compatibility claims absent from local v1. | Must | True compatibility requires promotion and live qualification of the linked remote profile. |

### 6.2 Tool inventory

| Tool | Required inputs | Purpose | Explicit exclusions |
|---|---|---|---|
| `search` | exactly `query` | Schema-aligned fixed-cap core `SearchDTO` | No filters, pagination, receipts, metadata, provider search, or rebuild |
| `fetch` | exactly `id` | Schema-aligned fixed-cap core `FetchDTO` | No cursor/page/receipt, raw path, or unbounded body |
| `rf_search` | `query`; optional validated kinds/filters/limit/cursor/receipt context | RF-extended governed search page | Not an alias for core `search` |
| `rf_fetch` | `id`; optional validated cursor/receipt context | RF-extended paged document | Not an alias for core `fetch` |
| `rf_source_get` | `source_id` | Governed source projection | No ingest/extract/refresh |
| `rf_assertion_get` | `assertion_id` | Eligible evidence packet/lineage projection | No lifecycle/evaluation mutation |
| `rf_report_get` | `report_id` | Governed report/run-report projection | No edit/verify/publish |
| `rf_run_get` | `run_id` | Governed run summary/detail projection | No launch/resume/bundle/writeback |

There are no tools named or aliased for `run_search`, `extract_url`, crawl, import,
rebuild, create, delete, approve, verify, bundle, launch, generate, job, or writeback.

### 6.3 Exact schema-aligned core DTO and MCP encoding

```json
{
  "results": [
    {
      "id": "rfk:v1:assertion:opaque-id",
      "title": "Bounded title",
      "url": "http://127.0.0.1:7432/api/knowledge/fetch/rfk%3Av1%3A..."
    }
  ]
}
```

The core `search` input contains only `query`; the output contains only
`results`, and each result contains exactly `id`, `title`, and `url`; snippets
appear only in `rf_search`. The core `fetch` input contains only `id`; its
output requires exactly `id`, `title`, `text`, and `url` and may include
`metadata` as the documented generic string-keyed map of JSON values
(`Record<string, unknown>`). The fetch root rejects other fields, but the
optional metadata map is intentionally open: `kind` and `truncated` may be
keys inside it but are neither required nor exhaustive. Both input schemas set
`additionalProperties: false`.

For either core call, the MCP result is encoded as:

```json
{
  "structuredContent": {"...": "the exact core DTO"},
  "content": [
    {"type": "text", "text": "<deterministic canonical JSON of the exact same DTO>"}
  ]
}
```

There is exactly one text block and no prose wrapper. Parsing its JSON must
deep-equal `structuredContent`. Search snippets, pagination, filters, typed RF
metadata, and activity receipts appear only in the separately named `rf_*`
contracts; the optional core fetch metadata remains a generic map.

The local URL is an HTTP read-contract reference, not the authority ID or a
canonical remotely reachable citation. Local v1 is schema-aligned only, not
OpenAI/ChatGPT-compatible. A public source locator may appear only in governed
RF-extended metadata. True compatibility requires a reachable canonical HTTPS
remote profile promoted through the remote transport, canonical URL, and cache
isolation specs.

### 6.4 Non-functional requirements

- Same inputs, projection snapshot, context, and limits produce stable ordering, IDs,
  cursors, receipts, and serialized fields.
- Denied and missing resources reveal no title, count, kind, URL, timing detail, or edge.
- Service outputs are allowlist-built; recursive redaction is defense in depth only.
- SQLite access uses read-only/query-only mode and never creates WAL/journal/schema files.
- A full local-stdio fixture call leaves the workspace file manifest and content hashes
  unchanged.
- Search and fetch remain available without the MCP extra through service/CLI/API tests.
- Remote configuration is rejected in v1 rather than silently using stdio policy remotely.

## 7. Scope

### In scope

- Shared read service and versioned DTO schemas.
- Exact schema-aligned core `search`/`fetch` plus six separately named `rf_*` extended/typed read tools.
- Existing local catalog/assertion/report/run projections in explicit read-only mode.
- Policy-first projection, opaque IDs, local URLs, cursors, limits, and untrusted-data flags.
- Independent local stdio process/registry/entry point/settings/credential allowlist/inventory, CLI commands, GET-only API routes, OpenAPI regeneration.
- Caller-carried provenance receipt, parity/negative/security tests, docs and changelog.

### Out of scope

- External discovery, extraction, crawl, provider health, or Search Router changes beyond
  preventing accidental registry reuse.
- Any filesystem/database mutation, cache rebuild, import, index, report edit, lifecycle
  change, verification, bundle, approval, job, writeback, or external integration call.
- Operator MCP tools or shared knowledge/operator credentials/registries.
- Streamable HTTP MCP, SSE, OAuth/OIDC, remote deployment, public multi-tenant hosting,
  canonical public HTTPS namespace, remote rate limits, or cross-workspace federation.
- Vector/embedding/graph retrieval, LLM query rewriting, synthesis, or answer generation.
- Returning quarantined external synthesis as evidence; interchange promotion remains
  owned by the external-import contract.

## 8. Dependencies and Assumptions

### Hard dependencies

- RAL catalog/packet rights, lifecycle, workspace, and denial contracts.
- Research Provenance Continuity P1 receipt/run-envelope vocabulary.
- Catalog-Assisted Research Planning governed retrieval response contracts and DG-3
  safety evidence before catalog tools close.
- Existing catalog, assertion, report, run, auth identity, workspace isolation, and
  sensitivity service seams.
- Optional official Python MCP SDK via the existing `mcp` extra.
- Research Provenance Continuity `RPC-1.G` exact-tree contract approval.

### Adjacent dependencies

- External Research Interchange owns quarantined imported material. Knowledge reads may
  expose it only after its state is allowed by the shared projection; they do not promote it.
- Operator MCP depends on this package's stable read identifiers but uses a separate
  server, registry, policy, and implementation plan.

### Sequence

```text
RAL + provenance contracts + catalog safety
  -> KMCP contract/policy freeze
  -> non-writing shared read service
  -> domain projections/URLs/bounds
  -> local stdio MCP
  -> CLI/API parity
  -> adversarial qualification/docs
```

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| “Read” lazily writes cache or DB state | Critical | Explicit query-only modes; missing projection unavailable; before/after manifest/hash test |
| Knowledge server exposes Search Router tools | Critical | Separate module/entry point/registry; exact inventory snapshot; provider spies |
| Cross-workspace or rights leak via count/snippet/cursor/URL | Critical | Policy before derivation; hidden=missing; two-workspace fixed-envelope tests |
| Raw run/report paths leak | High | Allowlist projection and recursive path/URI audit |
| Core schema drifts by transport | High | Exact frozen DTOs; dual-encoding equality; golden service/CLI/API/MCP normalized payloads |
| Local schema alignment is overstated as hosted compatibility | High | Local/loopback profile explicitly non-compatible; require promoted reachable HTTPS remote profile before OpenAI/ChatGPT claim |
| Provider credentials or tools enter the knowledge process | Critical | Separate process, import boundary, registry, entry point, settings/credential allowlist, environment/inventory snapshot |
| Oversized report/source exhausts context | High | Per-field and total byte limits; stable paging/truncation |
| Local HTTP URL is mistaken for global canonical URL | Medium | Label `local_resource_url`; reject non-loopback; defer HTTPS namespace |
| Activity receipt becomes a covert write | High | Return receipt only; persistence absent from knowledge package |
| Stale/retracted assertion presented as current | High | Lifecycle/freshness/evaluation projection before search/fetch |
| Fetched text prompts the agent | High | `content_is_untrusted`; text only in result data; injection fixtures |

## 10. Acceptance Criteria

#### AC KMCP-1: Tool inventory is read-only and cost-free
- target_surfaces:
    - src/research_foundry/knowledge_mcp/process.py
    - src/research_foundry/knowledge_mcp/registry.py
    - src/research_foundry/knowledge_mcp/settings.py
    - src/research_foundry/services/knowledge_access.py
    - pyproject.toml
- propagation_contract: The dedicated OS process owns exactly search, fetch, rf_search, rf_fetch, rf_source_get, rf_assertion_get, rf_report_get, and rf_run_get in its own registry/entrypoint/settings/credential allowlist and delegates only to governed read services.
- resilience: Missing SDK fails clearly; Search Router/Operator registries, provider credentials, provider clients, mutators, and cost-bearing tools are absent from the process import graph, environment view, and inventory.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.2
    - KMCP-6.3

#### AC KMCP-2: Schema-aligned core DTOs and dual encoding are exact
- target_surfaces:
    - schemas/knowledge_search_request.schema.yaml
    - schemas/knowledge_search_response.schema.yaml
    - schemas/knowledge_document.schema.yaml
    - src/research_foundry/services/knowledge_access.py
    - src/research_foundry/knowledge_mcp/registry.py
- propagation_contract: Core search accepts exactly query and returns SearchDTO with result items exactly id/title/url; core fetch accepts exactly id and returns required id/title/text/url plus optional generic key/value metadata; each MCP result places the DTO in structuredContent and canonical JSON of the identical DTO in one text content block.
- resilience: Additional core arguments and non-contract root/result fields fail schema validation while arbitrary keys remain valid inside optional fetch metadata; parsing content[0].text deep-equals structuredContent; snippets, pagination, filters, receipts, and typed RF metadata exist only in rf_search/rf_fetch.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.4

#### AC KMCP-3: Governance precedes every derived field
- target_surfaces:
    - src/research_foundry/services/knowledge_access.py
    - src/research_foundry/services/catalog_service.py
    - src/research_foundry/services/assertion_catalog.py
    - src/research_foundry/services/export_service.py
    - src/research_foundry/services/builder_service.py
- propagation_contract: Workspace, sensitivity, rights, lifecycle/freshness/evaluation, and capability decisions filter records before matching, sorting, counts, snippets, cursors, links, URLs, or receipts are derived.
- resilience: Missing identity under enforced isolation and every denied policy case return the same bounded no-existence-leak result.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.5

#### AC KMCP-4: Source, assertion, report, and run reads expose no paths or unbounded payloads
- target_surfaces:
    - src/research_foundry/services/knowledge_access.py
    - schemas/knowledge_document.schema.yaml
- propagation_contract: Each kind adapter allowlists fields into one KnowledgeDocument, generates an opaque ID and route-backed local URL, and applies common byte/link/depth limits.
- resilience: Missing optional metadata is omitted rather than synthesized; path-like values and unsupported nested fields are omitted rather than passed through.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.6

#### AC KMCP-5: Service, CLI, API, and MCP stay contract-equivalent
- target_surfaces:
    - src/research_foundry/services/knowledge_access.py
    - src/research_foundry/cli/commands/knowledge.py
    - src/research_foundry/api/routers/knowledge.py
    - src/research_foundry/knowledge_mcp/registry.py
    - src/research_foundry/api/openapi.json
- propagation_contract: Each transport maps caller context into shared service DTOs; the core remains frozen while RF extensions carry filters/paging/receipts without transport-local filtering, ranking, redaction, or URL construction.
- resilience: RF extension evolution cannot add fields to core inputs/DTOs; all transports preserve safe denial and dual-encoding equality.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.7

#### AC KMCP-6: Local stdio ships while remote transport stays absent
- target_surfaces:
    - src/research_foundry/knowledge_mcp/process.py
    - pyproject.toml
    - docs/dev/architecture/knowledge-mcp.md
    - docs/user/knowledge-mcp.md
- propagation_contract: The packaged independent entry point starts FastMCP on stdio with explicitly local/non-canonical loopback URLs; no Streamable HTTP, SSE, OAuth, non-loopback listener, or OpenAI/ChatGPT compatibility claim is registered.
- resilience: Remote/non-loopback configuration fails closed. True compatibility stays blocked until the linked remote transport, canonical URL, and cache-isolation specs are promoted and a reachable canonical HTTPS profile is qualified.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.8

## 11. Implementation Outline

| Phase | Outcome | Dependency | Estimate |
|---|---|---|---:|
| P1 | Freeze exact core/extended DTOs, dual encoding, policy order, IDs/URLs, process/credential boundary, inventory, remote truth, and negative contract | RPC-1.G + catalog contract | 7 pts |
| P2 | Implement explicit non-writing shared knowledge core and projection-read modes | P1 | 5 pts |
| P3 | Add source/assertion/report/run adapters, URL mapping, paging, and receipt | P2 | 6 pts |
| P4 | Add independent optional-SDK stdio process/registry/settings/credential boundary and exact core/RF tool encodings | P3 | 7 pts |
| P5 | Add CLI/API/OpenAPI parity and truthful local-profile labeling | P4 | 4 pts |
| P6 | Run adversarial/parity/mutation/process gates; docs, changelog, shaping-spec links, exact-tree review | P5 | 5 pts |
| **Total** | — | — | **34 pts** |

## 12. Deferred Items

| Item | Why deferred | Promotion trigger |
|---|---|---|
| Streamable HTTP MCP + OAuth | Remote identity/session/threat model unresolved | Promote `research-foundry-knowledge-mcp-remote-transport.md` after auth/rate-limit/revocation/security gates |
| Canonical public HTTPS resource URLs | No accepted public namespace/host ownership | Promote `research-foundry-knowledge-mcp-canonical-resource-urls.md` after host/migration/redirect/reachability gates |
| Remote/multi-tenant caching | Could leak cross-workspace membership | Promote `research-foundry-knowledge-mcp-remote-cache-isolation.md` after partition/eviction/timing/deletion proof |
| Vector/embedding/graph retrieval | RAL v1 is lexical/private and no shared semantic authority is approved | Promote `reusable-assertion-ledger-shared-indexes.md` after separate evaluation/isolation gates |
| Mutation/cost-bearing tools | Different policy and retry/confirmation posture | Research Foundry Operator MCP package |

## 13. Reviewer Gates

- `task-completion-validator` reviews every Tier-3 phase exit against the exact tree.
- `karen` reviews P1 contract/security decisions, P3 integrated projection semantics, and
  the final P6 candidate.
- A material change to tool inventory, exact core DTO/dual encoding, policy order, ID/URL contract, process/credential boundary, or compatibility label
  invalidates prior approvals and requires the same reviewers on the new tree.
- Review evidence must distinguish repository/synthetic qualification from any future
  private or remote owner-held execution.

## 14. Documentation Requirements

- Add `docs/dev/architecture/knowledge-mcp.md` with service/adapter/transport boundaries,
  process/credential boundary, exact core and RF tool schemas, dual encoding, policy order, local/non-canonical URL/ID rules, limits, receipt semantics, and remote deferrals.
- Add `docs/user/knowledge-mcp.md` with install, stdio registration, local trust/workspace
  configuration, examples, denial/truncation behavior, and untrusted-content warning.
- Update README MCP inventory so `rf-mcp` (Search Router) and `rf-knowledge-mcp` are not
  conflated; update CHANGELOG with local-only/read-only truth.
- Regenerate OpenAPI and document the exact focused tests and mutation audit.
