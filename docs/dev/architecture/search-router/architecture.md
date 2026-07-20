---
title: "Search Router — Architecture"
doc_type: architecture
status: accepted
schema_version: 1
created: 2026-06-21
updated: 2026-07-20
feature_slug: search-router
last_verified: 2026-07-20
related_docs:
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/design-specs/research_foundry_search_router_implementation_plan.md
  - docs/dev/architecture/search-router/provider_profiles.md
  - docs/dev/architecture/search-router/deployment.md
  - docs/dev/architecture/search-router/security.md
  - docs/dev/architecture/search-router/web-search-policy.md
owner: nick
---

# Search Router — Architecture

The Research Foundry **Search Router** is a thin, file-backed dispatcher that
turns a `SearchRequest` (query + mode + constraints + budget) into a deterministic
run on disk: candidates, source cards, telemetry, and a routing decision — all
plain YAML/Markdown under `runs/<run_id>/`. It is the substrate for every other
discovery surface in Research Foundry (`rf search`, the optional MCP server, and
eventually the REST API in spec §10.3).

> Source of truth for behavior: `src/research_foundry/services/search_router/`
> (`router.py`, `modes.py`, `policy.py`, `providers/*.py`). Docs describe **what
> exists today**; deferred behavior is called out explicitly.

---

## 1. Modes vs. Providers

Two orthogonal concepts:

- **Mode** — *what the caller is trying to do* (a canonical intent: "quick
  lookup", "source discovery", "github discovery", …). Modes are declared in
  `modes.py` as immutable `SearchMode` records carrying a `purpose`, a default
  `provider_chain`, a `budget` ceiling, and the expected `outputs`. The set is
  closed: only the 12 names enumerated below are valid (`SearchRequest.mode`
  enum, `schemas/search_request.schema.yaml`).
- **Provider** — *how the work gets done* (a registered adapter that implements
  the `SearchProvider` protocol from `providers/base.py`, declaring `roles` such
  as `discovery` or `extraction`). Providers are pluggable and degrade-safe:
  missing keys / missing `httpx` / network failures never raise — they just
  drop out of the chain and the run records the degradation.

`policy.resolve_chain()` filters the mode's default chain to providers that are
actually registered and available, so a mode like `source_discovery` can run
with only Brave installed and silently skip Exa re-ranking when the Exa key is
absent.

### 1.1 Mode → provider-chain table (canonical, from `modes.py`)

| Mode | Purpose | Default chain | Key outputs |
|------|---------|---------------|-------------|
| `cache_first` | Return results from previously stored source cards without any external query. | *(none)* | `source_cards` |
| `known_url_extract` | Extract full markdown from one or more known URLs. | `jina → firecrawl` | `extracted_markdown`, `source_cards` |
| `quick_lookup` | Fast factual lookup; breadth over depth. | `brave` | `source_cards`, `summary` |
| `source_discovery` | Broad sources on a topic; web search + semantic re-rank. | `brave → exa` | `source_cards`, `summary` |
| `semantic_discovery` | Semantic-similarity search across web + repos. | `exa → github → brave` | `source_cards`, `extracted_markdown`, `summary` |
| `official_source_check` | Verify / find authoritative sources for a claim. | `brave → exa` | `source_cards`, `claim_ledger` |
| `github_discovery` | Discover repos, READMEs, code. | `github → exa → brave` | `source_cards`, `summary` |
| `academic_discovery` | OpenAlex / Semantic Scholar / arXiv / PubMed. | *(deferred — no adapters yet)* | `source_cards`, `claim_ledger`, `summary` |
| `docs_crawl` | Crawl a docs site for comprehensive coverage. | `firecrawl` | `extracted_markdown`, `source_cards` |
| `deep_research` | Multi-stage discovery → extraction → synthesis. | *(deferred — orchestrated upstream)* | `source_cards`, `extracted_markdown`, `claim_ledger`, `summary` |
| `monitoring_delta` | Recurring scout for new/changed sources. | *(deferred — scheduled upstream)* | `source_cards` |
| `free_discovery` | Free, keyless discovery + extraction via node-local SearXNG (`aos-web`); zero API cost, breadth over authority. All fetched content is untrusted. | `searxng` | `source_cards`, `summary` |

Empty default chains mean the mode is **declared** in the contract but has no
default provider sequence in the MVP — calls succeed (file-backed, degraded)
and surface zero candidates rather than raising. Adapters can be added without
schema changes.

---

## 2. Run Lifecycle

A `run_search()` invocation walks one path top-to-bottom; each step is local,
synchronous, and recorded on disk.

```text
SearchRequest
   │
   ▼
[ validate ]            schemas/search_request.schema.yaml  (best-effort,
   │                     errors land in search_run.schema_errors)
   ▼
[ select_mode ]         policy.select_mode(request)
   │
   ▼
[ resolve_chain ]       policy.resolve_chain(mode, providers)
   │                    — keeps only available, role-matching adapters
   ▼
[ discovery loop ]      for pid in chain:
   │                       provider.search(query, max_results, constraints)
   │                       BudgetTracker enforces query/cost/latency caps
   │                       failures recorded in provider_chain[], not raised
   ▼
[ dedupe ]              dedupe.dedupe_hits() — URL canonicalization
   │                    (host/scheme/tracking-param normalization)
   ▼
[ rank ]                ranking.rank_hits() — authority score
   │                    (source_type weight + freshness + risk penalties)
   ▼
[ constrain ]           allow/block domain filters from request.constraints
   │
   ▼
[ source cards ]        services.source_cards.create_source_card() per hit;
   │                    optional extraction via jina/firecrawl when available
   │
   ▼
[ telemetry ]           services.telemetry.emit_ccdash_event()  (best-effort)
   │
   ▼
SearchRun on disk: runs/<run_id>/{search_run.yaml,
                                   source_candidates.yaml,
                                   routing_decision.yaml,
                                   sources/...}
```

**Degrade philosophy.** Every external dependency is wrapped: a provider raise
becomes a `provider_chain[].status = failed` entry plus a `schema_errors` line.
A missing schema directory skips validation. A failing extractor leaves the
source card content-empty but the card is still created. The run **always**
produces `search_run.yaml`; the only way it doesn't is if disk write itself
fails. This is the offline-degrade philosophy from spec §5.

---

## 3. File Layout (`runs/<run_id>/`)

| Path | Producer | Purpose |
|------|----------|---------|
| `search_run.yaml` | `router.run_search` | Top-level run record: request, provider chain log, normalized results, source-card refs, metrics, writeback stubs. Validated against `schemas/search_run.schema.yaml`. |
| `source_candidates.yaml` | `router.run_search` | The deduped + ranked + constraint-filtered hit list (provider raw output, post-processing). |
| `routing_decision.yaml` | `policy.build_routing_decision` | Mode chosen + chain used + reasons. Only persisted when it validates against `routing_decision` schema. |
| `sources/<source_card_id>/...` | `services.source_cards.create_source_card` | One source card per discovered hit (existing service — reused as-is). |
| `telemetry/` | `services.telemetry.emit_ccdash_event` | CCDash execution event (existing service — reused as-is). |

The Search Router writes **only** `search_run.yaml`, `source_candidates.yaml`,
and (optionally) `routing_decision.yaml`. Everything else under
`runs/<run_id>/` is produced by existing Research Foundry services that the
router calls into — source cards, telemetry, and (downstream) claim ledgers,
reports, and writebacks. This is intentional: the router doesn't own those
artifacts, it just produces inputs for them.

---

## 4. Reuse of Existing Services

| Capability | Owner module | How the router uses it |
|------------|--------------|------------------------|
| Source card creation | `research_foundry.services.source_cards` | Called per discovered hit with optional extracted markdown. The router never touches the source-card file layout directly. |
| CCDash telemetry | `research_foundry.services.telemetry` | `emit_ccdash_event(run_id)` fired at end of run, best-effort. |
| ID minting | `research_foundry.ids` | `run_id`, `disambiguate_id` — collision-free run ids rooted at the query string. |
| Schema validation | `research_foundry.schemas.SchemaRegistry` | Best-effort `validate(obj, name)` for `search_request`, `search_run`, `routing_decision`. Errors collected, never raised. |
| YAML serialization | `research_foundry.yamlio.dump_yaml` | Atomic-write YAML for all router-owned files. |
| Path discovery | `research_foundry.paths.FoundryPaths` | `run_paths(run_id)` gives the `runs/<run_id>/` view; `schemas` resolves user vs. distribution copy. |

The router is a **composer**, not a new subsystem. Adding a provider does not
require touching source-cards, telemetry, or the runs viewer.

---

## 5. Entry Points

| Surface | Module | Status |
|---------|--------|--------|
| Python API | `research_foundry.services.search_router.run_search`, `extract_urls` | Implemented (Wave 3) |
| CLI | `rf search`, `rf fetch` (`services.search_router.cli`) | Implemented (Wave 3) |
| MCP server | `services.search_router.mcp_server` (optional extra `mcp`) | Implemented (Wave 4 — thin) |
| REST API | spec §10.3 | Deferred |

---

## 6. Out of Scope (Today)

These are **declared** in the spec or contracts but not yet implemented; they
do **not** ship in this wave:

- `academic_discovery` adapters (OpenAlex / Semantic Scholar / arXiv / PubMed).
- `deep_research` orchestration (multi-stage; would compose the existing modes).
- `monitoring_delta` scheduler.
- REST surface from spec §10.3 (FastAPI app).
- The persistent storage tier from spec §14 (Postgres / MinIO / Redis /
  OpenSearch / Qdrant) — MVP is file-backed under `runs/`.
- Claim-ledger building beyond what the existing `source_cards`/`claims`
  services already do.

These are tracked as next-wave work in the implementation plan; the router's
contract is designed so each can be slotted in without breaking changes.
