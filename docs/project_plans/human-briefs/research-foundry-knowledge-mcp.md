---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-research-foundry-knowledge-mcp
title: "Research Foundry Knowledge MCP — Human Brief"
status: draft
category: human-briefs
feature_slug: research-foundry-knowledge-mcp
feature_family: research-interchange-provenance-access
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.72
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags: [human-brief, mcp, knowledge-access, read-only, local-stdio, openai-schema-aligned]
---

# Research Foundry Knowledge MCP — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md`
- **Unified plan**: `docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md`
- **Decisions block**: `.codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md`
- **Epic**: `docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md`
- **Initiative meta-plan**: `.codex/plans/research-interchange-provenance-access-initiative-v1.md`
- **Reusable Assertion Ledger**: `docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md`
- **Provenance continuity**: `docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md`
- **Catalog-assisted planning**: `docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md`
- **External report import**: `docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md`
- **SPIKEs**: None before planning. Escalate if P1 cannot freeze a non-writing projection mode or route-backed local URL contract.

## 2. Product Boundary

This is a separate knowledge surface, not a rename or extension of the existing Search
Router MCP. Search Router tools can reach network/cost-bearing providers and persist runs
or source cards. The new server exposes only governed reads over existing sources,
assertions, reports, and runs.

The schema-aligned core is exact `search(query)` and `fetch(id)`, with no
filters, pagination, or receipts and with identical `structuredContent` plus
canonical-JSON text encoding. Those extensions and typed helpers use separate
`rf_search`, `rf_fetch`, `rf_source_get`, `rf_assertion_get`, `rf_report_get`,
and `rf_run_get` names. Every result is bounded, untrusted data addressed by an
opaque ID and local HTTP GET route rather than a filesystem path.

Local stdio ships first in an independent process/registry/entrypoint/settings
and credential namespace. It is schema-aligned only, not OpenAI/ChatGPT-compatible.
Remote Streamable HTTP, OAuth, multi-tenant rate limits,
remote cache isolation, and canonical public HTTPS URLs remain behind design and security
gates. The stdio server may return loopback route URLs; it must not claim those are
portable or remotely canonical. A compatibility claim requires a reachable
canonical HTTPS remote profile promoted through the three linked shaping specs.

## 3. Estimation Sanity Check

**Earlier bottom-up estimate**: 26 pts
**Bottom-up total**: 34 pts
**Locked planning estimate**: 34 pts; no bundle discount and no claim of empirical actual velocity.

### H1 — Noun Count

The feature introduces six contract/runtime nouns: `KnowledgeAccessContext`,
frozen core `SearchDTO`, frozen core `FetchDTO`, RF-extended
`KnowledgeResult`/`KnowledgeDocument`, opaque knowledge ID/cursor, and a
caller-carried RF activity receipt. It also creates a distinct process/registry
boundary, but no authoritative database or user-managed CRUD entity.

### H2 — Dual-Implementation Multiplier

There is one knowledge service, four governed domain adapters, and three thin transports:
CLI, HTTP GET API, and local stdio MCP. The transports do not earn separate business
logic estimates, but parity is real integration work: schema translation, identity
threading, error mapping, optional MCP SDK loading, URL generation, and OpenAPI snapshots
must agree. P5 and the P6 parity matrix price that multiplier explicitly.

### H3 — Algorithmic Service Flag

P3 is the algorithmic center at 6 points. It applies policy before matching or derived
metadata, merges eligible domain projections, computes stable ranks/cursors, enforces
byte/page/link/depth limits, maps opaque IDs to fetch authorities, projects URLs, and
emits a non-leaking receipt. Required fixtures include:

- exact eligible source/assertion/report/run results;
- no identity, wrong workspace, sensitivity denial, rights denial, and invalid lifecycle;
- equal-rank deterministic ordering and cursor boundaries;
- missing or stale projections without rebuild;
- oversized text, nested payloads, raw paths, and excessive links;
- deleted/unknown/wrong-kind IDs and replay stability;
- mixed-domain queries where a hidden record changes neither count nor order;
- origin URL versus RF resource URL projection.

If these outcomes cannot be expressed deterministically in P1, stop and create a SPIKE.

### H4 — Bundle vs Sum

| Capability area | Independent estimate | Notes |
|---|---:|---|
| P1 contract and boundary freeze | 7 pts | Exact core/RF DTOs, dual encoding, IDs/URLs, policy, process/credentials, remote truth |
| P2 non-writing knowledge core | 5 pts | Query-only DB/cache modes and negative audit |
| P3 governed domain projections | 6 pts | H3 policy, merge, rank, cursor, fetch, limits |
| P4 independent local stdio MCP | 7 pts | Separate process/registry/entrypoint/settings/credentials, eight tools, exact dual encoding |
| P5 CLI and API parity | 4 pts | Thin adapters, local/non-canonical URLs, OpenAPI and truth labels |
| P6 hardening, docs, closeout | 5 pts | Adversarial process/parity matrix, docs/spec reconciliation, review |
| **Sum** | **34 pts** | **Locked bottom-up total** |

### H5 — Anchor Reference

The current Search Router MCP is a small, useful thin-adapter and optional-SDK anchor,
but it is not a safety anchor because its tools can call providers and write artifacts.
The 28-point catalog-assisted planning package is a nearby multi-service, multi-transport,
policy-heavy anchor. The epic's 21-point number was preliminary before live inspection
found lazy assertion-cache rebuild, catalog DB/WAL creation risk, raw path projection,
URL semantics, and the full parity matrix.

The 34-point estimate exceeds the catalog-planning package because it now owns
an exact compatibility-shaped wire contract, dual encoding, a hard OS-process
and credential boundary, eight-tool inventory, zero-write proof, and remote
compatibility truth gates. It still does not schedule providers or persist an
evidence plan. The repository contains planned-point analogs and landed surfaces, but no
authoritative actual-point ledger was found; H5 is comparison, not measured velocity.

### H6 — Hidden Plumbing Budget

P1-P5 total 29 points. P6 adds 5 points, or 17.2%, for cross-process
inventory/environment audits, core dual-encoding fixtures, explicit query-only
DB/cache behavior, optional SDK loading, route/OpenAPI parity, docs/spec
reconciliation, and exact-tree evidence. This is inside the 15-20% guide.

**Reconciliation**: Existing read services avoid a new store, but they do not by
themselves prove non-mutation, consistent redaction, bounded output, stable IDs, usable
URLs, process isolation, exact core/RF schemas, or CLI/API/MCP parity. The
reviewer-expanded 34-point sum replaces the earlier estimate.

## 4. Wave and Orchestration Notes

**Critical path**: Provenance Continuity `RPC-1.G` and governed catalog contracts → KMCP P1 →
P2 → P3 → P4 → P5 → P6.

**Serialization barriers**: One writer owns the four knowledge schemas and core service.
Catalog/assertion non-writing changes land before domain adapters. The MCP process,
registry, settings/credential allowlist, and `pyproject.toml` entry point land together. Generate OpenAPI once after the P5 contract
freezes. Every material fix invalidates the earlier exact-tree approval.

**Parallel opportunities**: Read-only threat review and fixture design may run beside P1
contract work. Domain fixture preparation may run beside P2 only with non-overlapping
files. Documentation can draft during P5 and reconcile to the exact P6 candidate.

**Cross-feature coupling**: RAL remains the assertion authority; Provenance Continuity
owns durable origin/activity lineage; catalog planning owns pre-discovery selection;
external interchange owns quarantine and verified promotion. The future operator MCP may
consume stable IDs but is not part of or a dependency for this read-only server.

## 5. Open Questions Ledger

| ID | Decision needed | Status | Safe default if unresolved |
|---|---|---|---|
| KMCP-OQ-1 | Which projections need explicit non-rebuilding/query-only modes? | open | Absent projection returns typed unavailable; never build, migrate, or create. |
| KMCP-OQ-2 | Are run-final reports and report drafts both v1 fetch kinds? | open | Distinct explicit kinds; never silently prefer one. |
| KMCP-OQ-3 | What URL is returned when stdio runs without the API process? | open | Stable loopback route template marked local/non-canonical; fetch content remains in-band; no hosted compatibility claim. |
| KMCP-OQ-4 | Which receipt fields are safe without persistence or membership leakage? | open | Request/context hash, visible returned refs, bounds/truncation, policy version; caller owns persistence. |

## 6. Deferred Items Rationale

- **Streamable HTTP and OAuth**: requires identity/session, revocation, rate-limit, and transport threat-model approval.
- **Canonical public HTTPS resource URLs**: requires host ownership, version/redirect/migration policy, and live reachability proof.
- **Remote cache**: requires tenant partition, timing, invalidation, backup, and deletion design.
- **Shared/vector/graph retrieval**: requires separate quality evidence and private-index isolation approval.
- **Operator MCP mutation tools**: require an independent policy posture; they must never be added to this registry.

The three Knowledge MCP shaping specs and the existing shared-index shaping spec
are registered now. P6 reconciles them to the exact implementation; registration
does not turn deferred scope into implementation.

## 7. Risk Narrative

- **A read that writes is the primary integrity risk**: lazy projection rebuild, DB setup,
  WAL files, audit/telemetry, or implicit persistence would falsify the server boundary.
- **Policy ordering is the primary privacy risk**: hidden records must not affect text,
  counts, ranks, cursors, URLs, receipts, existence errors, or detailed timing.
- **Raw payload reuse is unsafe**: run/report exports may contain paths or oversized and
  policy-inappropriate fields; adapters require allowlisted projections.
- **URL overclaim is a trust risk**: a loopback template is useful locally but is not a
  canonical HTTPS citation or proof that an API process is live.
- **Tool-registry drift is a cost risk**: importing Search Router registration code could
  make provider or mutating tools reachable even when the core service is read-only.
- **Process and credential bleed is stronger than registry drift**: the Knowledge process must not import provider/operator registries, dependencies, or credential keys; only governed read services cross the boundary.
- **Compatibility overclaim is a product risk**: a correct local DTO does not make loopback resources reachable from OpenAI/ChatGPT. The remote profile remains unqualified until canonical HTTPS is live and gated.

## 8. What to Watch For

- `AssertionCatalog._records()` may rebuild `.rf_cache`; the knowledge caller needs an
  explicit no-rebuild path, not a filesystem snapshot as the only guard.
- Catalog connection/setup can create or migrate a database and WAL; use an explicit
  query-only URI/connection with typed unavailable behavior.
- Existing `/api/catalog`, `/api/assertions`, `/api/reports`, and `/api/runs` are useful
  authorities but do not share the frozen schema-aligned core/RF DTO split.
- `identity=None` means local trust in some services. The access context must distinguish
  explicit local trust from enforced workspace identity.
- Preserve the existing `rf-mcp` entry point. Add `rf-knowledge-mcp` as a separate OS process, registry, settings/credential allowlist, and inventory.
- URL and ID stability must be tested independently of absolute fixture paths.

## 9. Expected Success Behaviors

- [ ] Core `search(query)` and `fetch(id)` reject every extra argument, return the exact frozen DTOs under fixed caps, and encode the same object in `structuredContent` and one canonical-JSON text block.
- [ ] Paging, filters, receipts, and typed reads appear only under the six separately named `rf_*` tools.
- [ ] Source, assertion, report, and run helpers apply the same access context and denial contract as search/fetch.
- [ ] Missing projections and databases return typed unavailable without creating cache, schema, DB, WAL, run, source, receipt, audit, or telemetry files.
- [ ] Provider and write spies record zero calls for every registered knowledge tool.
- [ ] MCP inventory contains exactly eight allowed read tools; process imports, environment/settings, and credentials contain no Search Router/Operator registry, provider client, or mutation capability.
- [ ] CLI, API, and MCP normalized fixture responses are contract-equivalent, including truncation and errors.
- [ ] Local v1 is labeled schema-aligned and local/non-canonical everywhere; OpenAI/ChatGPT compatibility stays false until a reachable canonical HTTPS remote profile passes all three shaping-spec gates.
- [ ] Remote transport, OAuth, public canonical URL, remote cache, and operator tools are absent from the shipped v1 surface.
- [ ] Closeout distinguishes repository readiness from remote deployment, owner/private execution, and release.

## 10. Running Log

- [2026-07-18] Reviewer expansion froze exact core DTOs and dual encoding, moved filters/paging/receipts to `rf_*` tools, required an independent process/credential boundary, and corrected local compatibility truth. H1-H6 were re-derived and the package locked at 34 points. No empirical actual-points, remote readiness, or owner/private qualification claim is made.
