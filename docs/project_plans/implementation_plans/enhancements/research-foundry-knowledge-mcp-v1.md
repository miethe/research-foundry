---
title: "Implementation Plan: Research Foundry Knowledge MCP"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-foundry-knowledge-mcp
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/research-foundry-knowledge-mcp.md
scope: "Build a separate read-only local-stdio Knowledge MCP process with exact schema-aligned core search/fetch DTOs and dual encoding, separately named RF paging/filter/receipt tools, governed projections, bounded local URLs, shared CLI/API contracts, and truthful remote-compatibility gates."
effort_estimate: "34 pts bottom-up"
architecture_summary: "KnowledgeAccessContext -> policy-first KnowledgeAccessService -> non-writing adapters -> frozen core/RF DTOs -> thin CLI/GET API -> independent stdio process with its own registry, entry point, settings/credential allowlist, and inventory; local profile is schema-aligned, not hosted-compatible."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/human-briefs/research-foundry-knowledge-mcp.md
  - .codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
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
    - .agents/skills/planning/references/ac-schema.md
    - .agents/skills/planning/references/deferred-items-and-findings.md
    - .claude/specs/changelog-spec.md
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
deferred_items_spec_refs:
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
findings_doc_ref: null
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [implementation, mcp, knowledge-access, read-only, openai-schema-aligned, stdio]
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
  - src/research_foundry/cli/commands/__init__.py
  - src/research_foundry/api/routers/knowledge.py
  - src/research_foundry/api/routers/__init__.py
  - src/research_foundry/api/app.py
  - src/research_foundry/api/openapi.json
  - pyproject.toml
  - tests/unit/test_knowledge_access.py
  - tests/test_knowledge_mcp_process.py
  - tests/test_knowledge_cli.py
  - tests/api/test_knowledge_api.py
  - tests/integration/test_knowledge_parity.py
  - docs/dev/architecture/knowledge-mcp.md
  - docs/user/knowledge-mcp.md
  - README.md
  - CHANGELOG.md
open_questions:
  - id: KMCP-OQ-1
    status: open
    question: "Freeze the explicit non-writing behavior for absent assertion/catalog projections."
  - id: KMCP-OQ-2
    status: open
    question: "Freeze report kind semantics for run-final reports versus report drafts."
  - id: KMCP-OQ-3
    status: open
    question: "Freeze the loopback resource base URL and route versioning contract."
  - id: KMCP-OQ-4
    status: open
    question: "Freeze non-leaking activity-receipt fields and caller persistence ownership."
wave_plan:
  serialization_barriers:
    - schemas/knowledge_search_request.schema.yaml
    - schemas/knowledge_search_response.schema.yaml
    - schemas/knowledge_document.schema.yaml
    - schemas/knowledge_activity_receipt.schema.yaml
    - src/research_foundry/services/knowledge_access.py
    - src/research_foundry/services/catalog_service.py
    - src/research_foundry/services/assertion_catalog.py
    - src/research_foundry/api/openapi.json
    - pyproject.toml
  phases:
    - id: P1
      depends_on: [RPC-1.G, CARP-2.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/knowledge_search_request.schema.yaml
        - schemas/knowledge_search_response.schema.yaml
        - schemas/knowledge_document.schema.yaml
        - schemas/knowledge_activity_receipt.schema.yaml
    - id: P2
      depends_on: [KMCP-1.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/knowledge_access.py
        - src/research_foundry/services/catalog_service.py
        - src/research_foundry/services/assertion_catalog.py
    - id: P3
      depends_on: [P2]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/knowledge_access.py
        - src/research_foundry/services/export_service.py
        - src/research_foundry/services/builder_service.py
    - id: P4
      depends_on: [P3]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/knowledge_mcp/process.py
        - src/research_foundry/knowledge_mcp/registry.py
        - src/research_foundry/knowledge_mcp/settings.py
        - pyproject.toml
    - id: P5
      depends_on: [P4]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/cli/commands/knowledge.py
        - src/research_foundry/api/routers/knowledge.py
        - src/research_foundry/api/app.py
        - src/research_foundry/api/openapi.json
    - id: P6
      depends_on: [P5]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - tests/unit/test_knowledge_access.py
        - tests/test_knowledge_mcp_process.py
        - tests/test_knowledge_cli.py
        - tests/api/test_knowledge_api.py
        - tests/integration/test_knowledge_parity.py
        - docs/dev/architecture/knowledge-mcp.md
        - docs/user/knowledge-mcp.md
        - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
        - docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md
        - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md
        - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
        - README.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2]
    - [P3]
    - [P4]
    - [P5]
    - [P6]
---

# Implementation Plan: Research Foundry Knowledge MCP

**Plan ID**: `IMPL-2026-07-18-RESEARCH-FOUNDRY-KNOWLEDGE-MCP`
**Date**: 2026-07-18
**Human Brief**: `docs/project_plans/human-briefs/research-foundry-knowledge-mcp.md`
**Decisions Block**: `.codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md`
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 34 points

## Executive Summary

Build a separate read-only knowledge plane over existing RF read authorities. The core
service normalizes sources, assertions, reports, and runs into stable `KnowledgeResult`
and `KnowledgeDocument` DTOs only after workspace, sensitivity, rights, lifecycle, and
capability projection. It owns IDs, route-backed local URLs, pagination, byte limits,
untrusted-content labeling, safe denial, and a non-persisted activity receipt.

The service is the only business-logic surface. Core `search(query)` and
`fetch(id)` have exact fixed DTOs and identical `structuredContent` plus
canonical-JSON text encoding. Pagination, filters, receipts, and typed reads use
separate `rf_*` names. The `rf-knowledge-mcp` entry point starts an independent
stdio process with its own registry, settings/credential allowlist, dependency
boundary, and inventory; existing Search Router and Operator registries cannot
enter that process. Local v1 is schema-aligned only, not OpenAI/ChatGPT-compatible.

## Implementation Strategy

### Architecture sequence

```text
P1 exact core/RF contracts, dual encoding, policy/process/remote truth
  -> P2 non-writing read core
  -> P3 four domain adapters + URLs/bounds/receipt
  -> P4 independent stdio process/registry/settings/inventory
  -> P5 CLI/GET API/OpenAPI parity and local-profile labeling
  -> P6 adversarial gates/docs/exact-tree review
```

### Invariants

1. **Separate process and registry:** knowledge MCP has its own entry point, settings/credential allowlist, dependency boundary, and inventory; it never imports/registers/calls Search Router or Operator tools.
2. **Read means no writes:** no cache/index rebuild, database creation/WAL, run/source
   creation, audit artifact, telemetry artifact, or writeback.
3. **Policy before derivation:** hidden records cannot affect counts, snippets, ranks,
   cursors, URLs, links, receipts, or timing detail.
4. **One service contract:** transports contain parsing/rendering only.
5. **Frozen core:** `search` accepts only query and `fetch` only id; fixed DTOs are emitted identically in structuredContent and one canonical-JSON text block. RF paging/filter/receipt extensions use separate names.
6. **Stable references:** opaque IDs are authority-neutral; local URLs use allowlisted GET routes, never expose paths, and are explicitly non-canonical.
7. **Bounded untrusted data:** content is byte/page limited and marked untrusted.
8. **Remote truth:** no Streamable HTTP, SSE, OAuth, non-loopback listener, canonical HTTPS URL, or OpenAI/ChatGPT compatibility claim in v1.

### Critical path

`RPC-1.G -> CARP-2.G -> P1 -> P2 -> P3 -> P4 -> P5 -> P6`.
External-interchange work may proceed independently, but unverified handoff candidates are
not eligible knowledge evidence. Operator MCP consumes settled IDs later and is not a
dependency for this read-only package.

### Phase summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Effort | Gate |
|---|---|---:|---|---|---|---|
| P1 | Contract and Boundary Freeze | 7 pts | backend-architect, api-designer | sonnet | extended | validator + karen |
| P2 | Non-Writing Knowledge Core | 5 pts | python-backend-engineer, data-layer-expert | sonnet | extended | validator |
| P3 | Governed Domain Projections | 6 pts | python-backend-engineer, backend-architect | sonnet | extended | validator + karen |
| P4 | Independent Local Stdio MCP | 7 pts | python-backend-engineer | sonnet | extended | validator |
| P5 | CLI and API Parity | 4 pts | api-designer, python-backend-engineer | sonnet | adaptive | validator |
| P6 | Hardening, Docs, Closeout | 5 pts | validation/doc agents | sonnet/haiku | extended | validator + karen |
| **Total** | — | **34 pts** | — | — | — | — |

H1-H6 details and the reviewer-driven 26-to-34-point delta are recorded in the Human Brief.

## Deferred Items and Findings Policy

### Deferred items triage

| ID | Category | Reason deferred | Promotion trigger | Target spec/path |
|---|---|---|---|---|
| KMCP-DF-1 | policy | Streamable HTTP and OAuth need remote identity/session/threat design | Auth, rate-limit, revocation, workspace and transport review accepted | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md` |
| KMCP-DF-2 | design | Public HTTPS resource namespace and migrations are unresolved | Canonical URL ADR, host ownership, redirect/version policy, live reachability | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md` |
| KMCP-DF-3 | policy | Remote cache could leak tenant membership/timing | Partition, invalidation, timing, backup and deletion threat model passes | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md` |
| KMCP-DF-4 | design | Shared/vector/graph retrieval is outside RAL private lexical v1 | Separate evidence/quality evaluation and isolation approval | `docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md` |
| KMCP-DF-5 | prereq | Mutation and cost-bearing tools require another policy posture | Operator MCP plan approved and read IDs stable | `docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md` |

The three Knowledge MCP shaping specs and the existing shared-index shaping spec are
linked in `deferred_items_spec_refs`. If execution discovers a load-bearing mismatch,
create `.claude/findings/research-foundry-knowledge-mcp-findings.md` at the first real
finding, link it in frontmatter, and follow the planning skill findings lifecycle.

## Phase Breakdown

### Phase P1: Contract and Boundary Freeze

**Goal:** Freeze exact core/RF DTOs, dual encoding, policy, process/credential boundary, local-profile truth, and remote gates before implementation.
**Depends on:** Research Provenance Continuity `RPC-1.G`; governed catalog `CARP-2.G` response contract.
**Files:** four `knowledge_*` schemas, decisions block.
**Exit:** exact contract reviewed; OQ defaults explicit.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-1.1 | Access and policy contract | Define local trust vs enforced identity, sensitivity ceiling, allowed use/kinds, policy order, fixed core caps, and safe denial. | Missing/cross-workspace/rights-denied examples reveal no derived fields | 1 | backend-architect | sonnet | extended | RPC-1.G, CARP-2.G |
| KMCP-1.2 | Exact core and RF DTOs | Freeze core search input exactly `{query}` and SearchDTO result items exactly id/title/url; freeze core fetch input exactly `{id}` and FetchDTO required id/title/text/url plus optional generic key/value metadata map; close core roots/items while allowing arbitrary metadata keys; keep snippets, filters, paging, receipts, and typed RF metadata in separately named rf_search/rf_fetch DTOs. | Positive/negative examples reject non-contract core fields, accept generic fetch metadata keys, and validate RF extensions | 2 | api-designer | sonnet | extended | KMCP-1.1 |
| KMCP-1.3 | Dual encoding, URL, and receipt contract | Freeze identical structuredContent plus one canonical-JSON text block for core DTOs; local/non-canonical route map; RF-only receipt fields/hashes/non-persistence. | JSON text deep-equals structuredContent; core has no receipt/page/filter; no path/denied ID in URLs | 1.5 | backend-architect, api-designer | sonnet | extended | KMCP-1.2 |
| KMCP-1.4 | Process, credentials, and inventory contract | Freeze separate OS process, registry, entry point, import/dependency boundary, settings and credential allowlist, eight allowed tools, forbidden registry/modules/env keys, and governed-read-only sharing. | Search Router/Operator registries, provider credentials/clients, and mutators cannot enter process or inventory | 1.5 | backend-architect, task-completion-validator | sonnet | extended | KMCP-1.3 |
| KMCP-1.5 | Local/remote compatibility gate | Declare local stdio schema-aligned only; link remote transport, canonical URL, cache-isolation, and shared-index shaping specs; define promotion evidence for reachable canonical HTTPS compatibility. | Docs/schemas contain no local OpenAI/ChatGPT compatibility claim; remote gates are explicit | 1 | api-designer, task-completion-validator | sonnet | extended | KMCP-1.3, KMCP-1.4 |
| KMCP-1.G | Contract gate | Review exact P1 tree and dependency ownership. | task-completion-validator and Karen APPROVE the same exact tree | gate | task-completion-validator, Karen | sonnet/opus | extended | KMCP-1.5 |

### Phase P2: Non-Writing Knowledge Core

**Goal:** Make current read authorities safe for a zero-mutation caller.
**Depends on:** P1 gate.
**Files:** `knowledge_access.py`, catalog/assertion read services, unit tests.
**Exit:** missing projections fail typed/unavailable without writes.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-2.1 | Service skeleton/context | Implement request validation, context resolution, kind registry/allowlist, response objects, safe errors, and deterministic ordering. | No transport/MCP imports; schemas round-trip | 1.5 | python-backend-engineer | sonnet | adaptive | KMCP-1.G |
| KMCP-2.2 | Query-only catalog access | Add explicit read-only/query-only general-catalog connection and absent-index behavior; prohibit schema/WAL/rebuild writes. | Missing DB returns unavailable; existing DB queries with zero changed files | 1.5 | data-layer-expert | sonnet | extended | KMCP-2.1 |
| KMCP-2.3 | Non-rebuilding assertion access | Add explicit non-rebuilding search/packet/lineage path while preserving policy-before-match and current callers. | Missing/stale projection does not rebuild; rights/workspace denial stable | 1 | python-backend-engineer | sonnet | extended | KMCP-2.1 |
| KMCP-2.4 | Core negative matrix | Spy on cache/index/run/source/audit/telemetry/provider/write functions and snapshot fixture tree/DB. | Every core read causes zero writes/provider calls | 1 | python-backend-engineer | sonnet | extended | KMCP-2.2, KMCP-2.3 |
| KMCP-2.G | Core gate | Review exact non-writing service tree. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | KMCP-2.4 |

### Phase P3: Governed Domain Projections

**Goal:** Normalize source, assertion, report, and run reads with shared URLs/bounds.
**Depends on:** P2 gate.
**Files:** knowledge service plus export/builder read seams and tests.
**Exit:** four kind matrices and generic search/fetch pass.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-3.1 | Source projection | Resolve governed source catalog/run data; allowlist title, locator URL, trust, permitted evidence snippets, provenance IDs; strip paths. | Source threshold/rights/path/size matrix passes | 1.5 | python-backend-engineer | sonnet | extended | KMCP-2.G |
| KMCP-3.2 | Assertion projection | Resolve exact assertion packet/lineage; include edition/passage/version/lifecycle/evaluation/rights fields within caps. | Eligible visible; stale/invalid/rights/cross-workspace fail per contract | 1.5 | python-backend-engineer | sonnet | extended | KMCP-2.G |
| KMCP-3.3 | Report and run projection | Distinguish report-final/report-draft kinds; route through builder/export gates; expose bounded summaries/body pages and provenance refs only. | Hidden/missing indistinguishable; no raw artifact paths/secret fields | 1.5 | python-backend-engineer | sonnet | extended | KMCP-2.G |
| KMCP-3.4 | Search/fetch composer | Merge authorized kind pages deterministically; build opaque IDs/local URLs plus RF-only snippets, cursors, fetch pages, and caller-carried receipt. | Search result fetches same resource; core search stays snippet-free; same snapshot replays byte-equivalent | 1.5 | backend-architect, python-backend-engineer | sonnet | extended | KMCP-3.1..3.3 |
| KMCP-3.G | Projection gate | Review policy order, URL/ID semantics, receipts and exact tree. | task-completion-validator and karen APPROVE | gate | task-completion-validator, karen | sonnet/opus | extended | KMCP-3.4 |

### Phase P4: Local Stdio MCP

**Goal:** Expose the settled service through an independent optional-SDK stdio process with frozen core and RF tool encodings.
**Depends on:** P3 gate.
**Files:** `knowledge_mcp/process.py`, `registry.py`, `settings.py`, `pyproject.toml`, MCP tests.
**Exit:** exact eight-tool process works locally; provider/operator registries, credentials, and mutators are absent.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-4.1 | Independent optional-SDK process | Implement process/registry/settings modules, lazy FastMCP import, stdio-only `rf-knowledge-mcp` entry point, read-only settings/credential allowlist, and dependency/import boundary. | Missing extra clear; Search Router/Operator registry and provider config/env keys absent | 2 | python-backend-engineer | sonnet | extended | KMCP-3.G |
| KMCP-4.2 | Exact core tools and dual encoding | Register search/fetch with only required query/id; emit snippet-free id/title/url search items and fetch required id/title/text/url plus optional generic metadata; encode each fixed DTO in structuredContent and exactly one canonical-JSON text block. | Input/output/tool-result snapshots cover absent/present arbitrary metadata; parsed JSON deep-equals structuredContent | 2 | python-backend-engineer | sonnet | extended | KMCP-4.1 |
| KMCP-4.3 | RF-extended tools | Register rf_search/rf_fetch for validated filters/paging/receipts and rf_source_get/rf_assertion_get/rf_report_get/rf_run_get as thin service calls. | Core schemas unchanged; RF outputs equal service fixtures | 1.5 | python-backend-engineer | sonnet | adaptive | KMCP-4.2 |
| KMCP-4.4 | Inventory, environment, and transport lock | Snapshot exact eight names, process imports/dependencies/settings/environment, and assert forbidden tools/credentials/registries plus Streamable HTTP/SSE/OAuth/non-loopback options absent. | Separate-process inventory green; stdio only; local profile labeled schema-aligned | 1.5 | task-completion-validator | sonnet | extended | KMCP-4.3 |
| KMCP-4.G | MCP gate | Review exact tool/entrypoint tree. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | KMCP-4.4 |

### Phase P5: CLI and API Parity

**Goal:** Expose the same service contract through local CLI and GET-only HTTP.
**Depends on:** P4 gate.
**Files:** knowledge CLI/router, app registration, OpenAPI, parity tests.
**Exit:** normalized response parity and route-backed URLs pass.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-5.1 | Knowledge CLI | Add `rf knowledge search/fetch/source-get/assertion-get/report-get/run-get` with JSON default for automation and shared context/limits. | Exit/error and golden JSON tests pass; no transport-local policy | 1 | python-backend-engineer | sonnet | adaptive | KMCP-4.G |
| KMCP-5.2 | GET-only API | Add `/api/knowledge/search`, `/fetch/{id}`, and typed GET routes; thread request identity and server ceiling into shared context. | No POST/PUT/PATCH/DELETE; hidden/missing parity | 1 | api-designer, python-backend-engineer | sonnet | extended | KMCP-4.G |
| KMCP-5.3 | URL/OpenAPI/parity seam | Regenerate OpenAPI/types as applicable; prove result URLs resolve through the same API and normalized service/CLI/API/MCP outputs match. | Contract diff empty after transport metadata normalization | 1 | api-designer | sonnet | extended | KMCP-5.1, KMCP-5.2 |
| KMCP-5.4 | Local-profile truth gate | Label loopback URLs local/non-canonical across CLI/API/docs; reject remote config; assert no OpenAI/ChatGPT compatibility claim without reachable HTTPS remote profile. | Cross-surface truth snapshot and negative config fixtures pass | 1 | api-designer, task-completion-validator | sonnet | extended | KMCP-5.3 |
| KMCP-5.G | Transport gate | Review exact generated/transport tree. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | KMCP-5.4 |

### Phase P6: Hardening, Documentation, and Closeout

**Goal:** Prove every PRD AC on the exact integrated tree and document truthful limits.
**Depends on:** P5 gate.
**Files:** focused/integration tests, user/dev docs, README, CHANGELOG.
**Exit:** AC KMCP-1..6 evidenced; no remote/private readiness inferred; shaping specs remain linked and truthful.

| Task | Name | Description | Acceptance | Points | Assigned | Model | Effort | Depends on |
|---|---|---|---|---:|---|---|---|---|
| KMCP-6.1 | Focused/full regression | Run schema, service, catalog/assertion/export/builder, API, CLI, optional-SDK, and full RF gates. | No legacy Search Router/API/CLI regression | 0.5 | python-backend-engineer | sonnet | adaptive | KMCP-5.G |
| KMCP-6.2 | Process/tool/SDK gate | Verify exact eight tools, required schemas, optional import, separate OS process/registry/entry point/settings/credential allowlist/import graph. | Evidence AC KMCP-1 inventory half | 0.5 | task-completion-validator | sonnet | extended | KMCP-5.G |
| KMCP-6.3 | Zero-mutation/cost gate | Snapshot files/DB and spy on providers/mutators across all tools/transports. | Evidence AC KMCP-1 read-only half | 0.5 | task-completion-validator | sonnet | extended | KMCP-6.2 |
| KMCP-6.4 | Core/RF boundary gate | Test exact query/id-only core schemas, id/title/url search items with no snippet, fetch optional generic metadata acceptance, fixed caps, structuredContent/JSON equality, and rejection of core filters/pages/receipts; test snippets and RF extensions under rf_* names. | Evidence AC KMCP-2 | 0.5 | api-designer | sonnet | extended | KMCP-6.3 |
| KMCP-6.5 | Policy/no-leak gate | Run public/personal/work/client, two-workspace, rights missing/denied, stale/invalidated, capability and hidden-ID matrix. | Evidence AC KMCP-3 | 0.5 | task-completion-validator | sonnet | extended | KMCP-6.3 |
| KMCP-6.6 | Projection/path gate | Exercise four kinds, nested path/file URI removal, untrusted text, depth/link/size caps, URL resolution. | Evidence AC KMCP-4 | 0.5 | python-backend-engineer | sonnet | extended | KMCP-6.4, KMCP-6.5 |
| KMCP-6.7 | Parity gate | Compare normalized shared fixture payload through service, CLI, GET API and MCP. | Evidence AC KMCP-5 | 0.5 | api-designer | sonnet | extended | KMCP-6.6 |
| KMCP-6.8 | Docs/remote-absence gate | Write architecture/user docs, README split, CHANGELOG; validate stdio-only/non-loopback rejection, schema-aligned-only language, and crosslinks. | Evidence AC KMCP-6; docs truthful | 0.5 | documentation-writer, changelog-generator | haiku | adaptive | KMCP-6.7 |
| KMCP-6.9 | Shaping-spec reconciliation | Reconcile remote transport, canonical URL, remote cache isolation, and shared-index specs to actual local boundaries and explicit promotion gates. | Four linked specs remain shaping/deferred and no remote capability is implied | 1 | backend-architect, documentation-writer | sonnet | extended | KMCP-6.8 |
| KMCP-6.G | Final Tier-3 gate | Validate exact final tree and evidence; issue formal verdicts. | task-completion-validator then Karen APPROVE | gate | task-completion-validator, Karen | sonnet/opus | extended | KMCP-6.9 |

## Structured Acceptance Criteria

#### AC KMCP-1: Tool inventory is read-only and cost-free
- target_surfaces:
    - src/research_foundry/knowledge_mcp/process.py
    - src/research_foundry/knowledge_mcp/registry.py
    - src/research_foundry/knowledge_mcp/settings.py
    - src/research_foundry/services/knowledge_access.py
    - pyproject.toml
- propagation_contract: The dedicated OS process owns exactly search, fetch, rf_search, rf_fetch, rf_source_get, rf_assertion_get, rf_report_get, and rf_run_get in its own registry/entrypoint/settings/credential allowlist and delegates only to governed read services.
- resilience: Missing SDK fails clearly; Search Router/Operator registries, provider credentials/clients, mutators, and cost-bearing tools are absent from the process import graph, environment view, and inventory; missing projections cause no writes.
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
- resilience: Missing identity under enforced isolation and every denial case return the same bounded no-existence-leak shape.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.5

#### AC KMCP-4: Four knowledge kinds expose no paths or unbounded payloads
- target_surfaces:
    - src/research_foundry/services/knowledge_access.py
    - schemas/knowledge_document.schema.yaml
- propagation_contract: Source, assertion, report, and run adapters allowlist fields into one KnowledgeDocument, generate opaque IDs and route-backed local URLs, and apply common byte/link/depth limits.
- resilience: Missing optional metadata is omitted rather than synthesized; path-like and unsupported nested values are omitted rather than passed through.
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
- propagation_contract: Each transport maps caller context into shared service DTOs; the core remains frozen while RF extensions carry snippets/filters/paging/receipts without local filtering, ranking, redaction, receipt, or URL logic.
- resilience: RF extension evolution cannot add root/result fields to core DTOs or close the optional generic fetch metadata map; all transports preserve safe denial and dual-encoding equality.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.7

#### AC KMCP-6: Local stdio ships while remote access remains deferred
- target_surfaces:
    - src/research_foundry/knowledge_mcp/process.py
    - pyproject.toml
    - docs/dev/architecture/knowledge-mcp.md
    - docs/user/knowledge-mcp.md
- propagation_contract: The packaged independent entry point starts FastMCP on stdio with explicitly local/non-canonical loopback URLs and registers no Streamable HTTP, SSE, OAuth, non-loopback listener, or OpenAI/ChatGPT compatibility claim.
- resilience: Remote/non-loopback configuration fails closed; compatibility remains blocked until the linked remote transport, canonical URL, and cache-isolation specs are promoted and a reachable canonical HTTPS profile is qualified.
- visual_evidence_required: false
- verified_by:
    - KMCP-6.8

## Risk and Rollback

| Risk | Prevention/detection | Rollback |
|---|---|---|
| Read path mutates cache/DB | Query-only code paths, spies, manifest/hash test | Disable new entry point/routes; shared existing readers unchanged |
| Search Router tools appear | Separate module/entrypoint, exact inventory snapshot | Remove knowledge script registration; `rf-mcp` unchanged |
| Provider credentials or registries enter process | Separate process/import graph/settings allowlist/environment snapshot | Disable entry point; retain shared read service only |
| Policy leak | Projection order, hidden=missing, two-workspace matrix | Disable affected kind adapter; retain safe empty response |
| URL/ID instability | Versioned opaque IDs and route map; replay fixtures | Keep prior ID version decoder; stop emitting new version |
| Oversized/untrusted content | Allowlist, byte/depth/link caps, untrusted marker | Reduce caps/disable kind; no canonical data affected |
| Transport drift | Golden parity suite | Disable wrapper independently; service remains authority |
| Local profile overstated as hosted-compatible | Schema-aligned-only docs/config snapshots and remote-profile gate | Remove compatibility label; local service remains usable |

No rollback deletes or rewrites canonical research evidence. Derived knowledge contracts and
entry points are additive; the safe fallback is to disable the new surface.

## Validation Commands

```bash
.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py \
  -f docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md --strict --verbose

.venv/bin/python .agents/skills/artifact-tracking/scripts/ac-coverage-report.py \
  --plan docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md --dry

.venv/bin/python -m pytest -q \
  tests/unit/test_knowledge_access.py \
  tests/test_knowledge_mcp_process.py \
  tests/test_knowledge_cli.py \
  tests/api/test_knowledge_api.py \
  tests/integration/test_knowledge_parity.py

.venv/bin/python -m pytest -q \
  tests/test_search_router_foundation.py \
  tests/test_search_router_router.py \
  tests/unit/test_assertion_catalog.py \
  tests/unit/test_catalog_service.py \
  tests/api/test_assertions_api.py

.venv/bin/python -m ruff check src/research_foundry tests
.venv/bin/python -m mypy src/research_foundry --ignore-missing-imports
.venv/bin/python -m pytest -q
```

Focused commands are planned evidence, not evidence already executed by this draft.

## Reviewer and Closeout Contract

- Every phase closes with `task-completion-validator` on the exact current tree.
- Karen reviews P1, P3, and P6; changes after a verdict invalidate it.
- P6 runs strict artifact validation, AC dry coverage, reference/link checks, focused and
  full repository gates, then reconciles docs and changelog to actual behavior.
- Completion labels repository qualification separately from owner/private or future
  remote execution. Local stdio proof does not imply remote/OAuth/HTTPS readiness.
- Progress artifacts are created only when execution begins; this planning package creates
  none.
