---
schema_version: 0.1
id: impl-plan-2026-06-21-search-router
type: implementation_plan
title: Research Foundry Search Router — MVP Implementation Plan
project: Research Foundry
status: in_progress
owner: Nick Miethe
created_at: 2026-06-21
source_spec: docs/project_plans/design-specs/research_foundry_search_router_spec.md
---

# Research Foundry Search Router — MVP Implementation Plan

Derived from the ADR/spec (`research_foundry_search_router_spec.md`). This plan scopes the spec to
an MVP that fits Research Foundry's actual architecture and philosophy, and serves as the delegation
brief for the build waves.

## 0. Scope decisions (resolved from RF philosophy + codebase)

RF is a **Markdown/YAML-first, file-backed control plane** (deps: `typer, rich, pyyaml, jsonschema`)
where external tools are **optional, lazy-imported, and degrade to offline behavior**. The spec's
heavy infra (Postgres/MinIO/Redis/OpenSearch/qdrant) contradicts this and is explicitly flagged as
"excessive architecture before utility." Resolutions:

| Open question | Decision |
|---|---|
| Standalone repo vs integrated | **Integrated** into `research_foundry` package + `rf` CLI (merge to main). |
| Python-only vs TS MCP (OQ-1) | **Python-only.** MCP is a thin optional wrapper. |
| Storage backbone (OQ-2) | **File-backed** under `runs/<run_id>/` (existing convention). Postgres/MinIO/etc. **deferred**. |
| Schema/model style | **dataclasses + YAML JSON-Schema** (`schemas/*.schema.yaml`). **No Pydantic.** |
| HTTP client | `httpx` as an **optional** `search` extra; **lazy import**; **offline-degrade** when absent/no key. |
| MVP depth | Spec **Phase 0–1 + thin Phase 2**: schemas, 5 adapters, routing, orchestrator, `rf search`/`rf extract` CLI, optional MCP. |

**Reuse, don't rebuild** — these already exist and the router calls them:
- `services/source_cards.py` → `ingest_source(...)`, `create_source_card(...)`, `list_source_cards(...)`, `_fetch_url(...)` (degraded fetch).
- `services/extraction.py` → extraction cards.
- `services/telemetry.py` → `emit_ccdash_event(run_id)` (CCDash writeback already done).
- `services/writeback.py` → MeatyWiki / SkillBOM / IntentTree / ARC writebacks (already done).
- `schemas.py` (`SchemaRegistry`, validate against `schemas/<name>.schema.yaml`), `config.py` (`FoundryConfig`), `paths.py` (`FoundryPaths`/`RunPaths`), `frontmatter.py`, `yamlio.py`, `ids.py`, `errors.py`.
- Existing schemas to reuse: `source_card`, `ccdash_event`, `routing_decision`, `claim_ledger`, `source_candidates` shape.

**Genuinely new** = providers (brave/exa/jina/firecrawl/github), routing layer (modes/policy/budgets/dedupe/ranking),
the orchestrator, two new schemas (`search_request`, `search_run`), optional `tool_profile` schema, CLI groups,
optional MCP server.

**Deferred (documented stubs / next steps):** Postgres/MinIO/Redis/OpenSearch/qdrant; Serper/Tavily/Perplexity/Gemini/OpenAI-synthesis adapters; academic adapters (OpenAlex/Semantic Scholar/PubMed/arXiv); `crawl.site` bounded crawl; `monitoring_delta`; automatic provider scoring; recurring skill-scout.

## 1. Module layout (new)

```
src/research_foundry/services/search_router/
  __init__.py            # public API: run_search(request)->SearchRun, extract_urls(...)
  router.py              # orchestrator: request -> mode -> provider chain -> normalize -> dedupe -> rank -> extract -> source cards -> telemetry -> search_run.yaml
  modes.py              # SearchMode definitions (spec §7): name, purpose, default provider chain, default budget, outputs
  policy.py             # routing rules (spec §12): pick mode + provider chain + budget from request/constraints
  budgets.py            # Budget dataclass + BudgetTracker (enforce max_external_queries/urls/cost/latency)
  dedupe.py             # canonicalize_url(), dedupe_hits() (by canonical url + title + content hash)
  ranking.py            # authority_score() (spec §15.3) + rank_hits()
  cli.py                # Typer: `rf search` group + `rf extract` group; register(app)
  mcp_server.py         # OPTIONAL thin MCP wrapper (lazy 'mcp' import; degrade if absent)
  providers/
    __init__.py
    base.py             # SearchProvider Protocol, SearchHit/ExtractedDoc/ProviderResult dataclasses, env-key + module + offline helpers, registry
    registry.py         # register/get/all providers
    brave.py            # discovery
    exa.py              # semantic discovery
    jina.py             # known-url extraction
    firecrawl.py        # robust extraction (+ search)
    github.py           # repo/skill discovery
schemas/
  search_request.schema.yaml   # NEW (spec §11.1)
  search_run.schema.yaml       # NEW (spec §11.2)
  tool_profile.schema.yaml     # NEW (spec §11.5, optional)
tests/search_router/...        # unit + integration (offline, mocked providers)
docs/dev/architecture/search-router/   # architecture.md, provider_profiles.md, deployment.md, security.md, web-search-policy.md
```

## 2. Core contracts (delegation-precise)

### 2.1 Provider base (`providers/base.py`)
Mirror `adapters/base.py` (`module_available()`, `requires`, registry). Dataclasses:

```python
@dataclass
class SearchHit:
    title: str; url: str; snippet: str = ""
    provider: str = ""; rank: int = 0; score: float | None = None
    source_type: str | None = None; published_at: str | None = None
    raw: dict = field(default_factory=dict)

@dataclass
class ExtractedDoc:
    url: str; markdown: str; title: str | None = None
    content_length_chars: int = 0; text_hash: str = ""        # sha256:...
    fetched_at: str = ""; extractor: str = ""; degraded: bool = False
    risk_flags: list[str] = field(default_factory=list); raw: dict = field(default_factory=dict)

@dataclass
class ProviderResult:
    provider: str; role: str               # discovery|extraction|crawl
    status: str                            # success|partial|failed|skipped|degraded
    hits: list[SearchHit] = field(default_factory=list)
    docs: list[ExtractedDoc] = field(default_factory=list)
    queries_executed: int = 0; estimated_cost_usd: float = 0.0
    latency_ms: int = 0; error: str | None = None
```

```python
@runtime_checkable
class SearchProvider(Protocol):
    id: str                                # e.g. "brave"
    roles: tuple[str, ...]                 # ("discovery",) / ("extraction",) / ("discovery","extraction")
    requires: tuple[str, ...]              # ("httpx",)
    env_keys: tuple[str, ...]              # ("RF_BRAVE_API_KEY","BRAVE_API_KEY")
    def available(self) -> bool: ...       # module importable AND an env key present
    def search(self, query: str, *, max_results: int, constraints: dict) -> ProviderResult: ...
    def extract(self, urls: list[str]) -> ProviderResult: ...   # extraction providers only
```

**Offline-degrade contract (mandatory, mirrors RF philosophy):** when `httpx` is missing or no env
key is set, `available()` returns False; the router skips the provider (status `skipped`) or, when
forced, providers return `status="degraded"` with empty hits/docs and `degraded=True` — never raise
for missing creds/network. Tests run fully offline by injecting fake providers / monkeypatching the
HTTP call. API keys come from **env only** (never config files, never exposed to agents).

### 2.2 Modes & default chains (spec §7/§12)
`source_discovery`: [brave, exa] · `semantic_discovery`: [exa, github, brave] · `known_url_extract`: [jina, firecrawl] · `quick_lookup`: [brave] · `github_discovery`: [github, exa, brave] · `official_source_check`: [brave, exa] (prefer official domains) · `cache_first`: [] (local source cards only). Each mode carries default budget caps from §7.

### 2.3 SearchRun on disk
A run dir `runs/<run_id>/` (run_id via `ids.py`, e.g. `rf_run_*`) containing: `search_run.yaml`
(validated against `search_run` schema), `source_candidates.yaml` (normalized ranked hits),
`routing_decision.yaml` (mode + provider chain), `sources/` (source cards via existing
`source_cards.create_source_card`/`ingest_source`). Telemetry via `telemetry.emit_ccdash_event`.

## 3. Execution waves

- **Wave 1 — Foundation (sequential, in-session/strong agent):** schemas (`search_request`,
  `search_run`, `tool_profile`); `providers/base.py` + `registry.py`; `modes.py`, `budgets.py`,
  `dedupe.py`, `ranking.py`; `__init__.py` public API stubs. Unit tests for dedupe/ranking/budgets/modes.
- **Wave 2 — Providers (parallel fan-out, ICA where feasible):** `brave.py`, `exa.py`, `jina.py`,
  `firecrawl.py`, `github.py`, each implementing the Wave-1 Protocol, offline-degrading, with a
  unit test using a mocked HTTP transport + an offline-degrade test.
- **Wave 3 — Orchestrator + CLI:** `policy.py`, `router.py` (full run lifecycle, reusing
  source_cards + telemetry), `cli.py` (`rf search` / `rf extract`), wire into `cli.py _wire()`.
- **Wave 4 — Tests + docs + optional MCP + validation:** integration test (brave→jina→source card,
  fully mocked), CLI smoke tests, docs set + Claude Code web-search policy, optional `mcp_server.py`.
  Reviewer gate; fix; commit; squash-merge to main.

## 4. Acceptance criteria (MVP)

- `rf search "<q>" --mode source_discovery` produces a reproducible run dir with `search_run.yaml`,
  ranked `source_candidates.yaml`, and ≥1 source card — **fully offline** (mocked providers in tests).
- `rf extract <url>` creates a source card with url, source_type, freshness, content hash, summary,
  risk flags, provider provenance (reusing `source_cards`).
- Budget caps enforced; duplicate URLs deduped; per-run cost estimated; CCDash event emitted.
- All new code: `ruff` clean, `mypy` clean, `pytest` green under `uv run`. No new hard dependency
  (httpx is an optional `search` extra; package imports without it).
- Providers never raise on missing creds/network — they degrade.

## 5. Validation commands

```bash
uv run ruff check src/research_foundry/services/search_router tests/search_router
uv run mypy src/research_foundry/services/search_router
uv run pytest tests/search_router -q
```

## 6. Deferred / next steps (write into docs)

Postgres/object-store/vector backends; Serper/Tavily/synthesis + academic adapters; bounded
`crawl.site`; `monitoring_delta` recurring scout; automatic provider scoring from CCDash telemetry;
full MCP harness integration + per-agent tokens; live-provider validation (no API keys in this build).
