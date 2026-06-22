---
title: "Search Router — Deployment & Operation"
doc_type: runbook
status: accepted
schema_version: 1
created: 2026-06-21
updated: 2026-06-21
feature_slug: search-router
last_verified: 2026-06-21
related_docs:
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/dev/architecture/search-router/architecture.md
  - docs/dev/architecture/search-router/security.md
owner: nick
---

# Search Router — Deployment & Operation

The Search Router MVP is intentionally **file-backed** and **process-local**:
no database, no object store, no queue. You install the `rf` CLI, set provider
keys in the environment, and runs land under `runs/<run_id>/` in the workspace.

The fuller infrastructure stack in spec §14 (Postgres / MinIO / Redis /
OpenSearch / Qdrant) is **deferred**; everything below is what ships today.

---

## 1. Install

The base `rf` CLI ships with no external HTTP dependency. Provider adapters
need `httpx`, gated behind the optional `search` extra. The thin MCP server
needs the official MCP SDK, gated behind the optional `mcp` extra.

```bash
# Base install (CLI + schemas + orchestrator; offline-only)
uv sync

# Add HTTP-capable provider adapters (brave / exa / jina / firecrawl / github)
uv sync --extra search

# Add the optional thin MCP server (lazy import — module loads without this)
uv sync --extra mcp

# Combined
uv sync --extra search --extra mcp
```

`pip` equivalents work too: `pip install -e ".[search,mcp]"`.

**Note.** With *only* the base install the router still runs: every provider
reports unavailable, every external call short-circuits, and the run produces
an empty candidate list plus a clean `search_run.yaml`. This is the
offline-degrade contract from spec §5.

---

## 2. Environment Variables

Keys are read from the environment at call time — **never** from config files
checked into the repo, **never** passed through to agents. Spec §14.3 (homelab)
endorses Vault / SOPS / 1Password CLI / sealed `.env` on the host.

| Variable | Provider | Required? |
|----------|----------|-----------|
| `RF_BRAVE_API_KEY` (or `BRAVE_API_KEY`) | Brave | Required for `brave` |
| `RF_EXA_API_KEY` (or `EXA_API_KEY`) | Exa | Required for `exa` |
| `RF_FIRECRAWL_API_KEY` (or `FIRECRAWL_API_KEY`) | Firecrawl | Required for `firecrawl` |
| `RF_JINA_API_KEY` (or `JINA_API_KEY`) | Jina Reader | **Optional** — Reader is keyless; key raises rate limit |
| `RF_GITHUB_TOKEN` (or `GITHUB_TOKEN`) | GitHub | **Optional** — unauth public search works at low rates |

If a key is missing, that provider is silently dropped from the chain (with a
`provider_chain[].status = "unavailable"` log entry). The run does not fail.

**Local convention.** Drop a `.env` next to the workspace and source it before
calling `rf` (e.g. `set -a; source .env; set +a`). Do not commit `.env`; a
`.env.example` listing the variable names (no values) is fine.

---

## 3. Running the CLI

The router is exposed as two `rf` subcommands (`services.search_router.cli`):

```bash
# Run a search (mode-driven; defaults to source_discovery)
rf search "agent-native search APIs"
rf search "redis vs kafka for event sourcing" --mode source_discovery --max-results 6
rf search "Brave Search API pricing" --mode quick_lookup --max-cost 0.05

# Known-URL fetch (jina → firecrawl)
rf fetch https://example.com/docs/x https://example.com/blog/y
```

Each invocation writes:

```text
runs/<run_id>/
  search_run.yaml          # full run record (validated against search_run schema)
  source_candidates.yaml   # deduped + ranked hits (post-constraint filter)
  routing_decision.yaml    # only when it validates
  sources/<card_id>/...    # one source card per hit (existing service)
  telemetry/...            # CCDash event (best-effort)
```

Inspect runs with the existing `rf runs` family (see `docs/dev/architecture/
adr-runs-read-path.md`).

---

## 4. Calling the Router from Python

```python
from research_foundry.services.search_router import run_search, extract_urls

run = run_search({
    "query": "best web search APIs for AI agents",
    "mode": "source_discovery",
    "budget": {"max_provider_cost_usd": 0.25, "max_urls_to_extract": 8},
    "output_requirements": {"source_cards": True},
})
print(run["run_id"], len(run["normalized_results"]))

ex = extract_urls(["https://example.com/docs/page"])
print(ex["run_id"], ex["source_cards"], ex["degraded"])
```

Both functions return the run dict and always write `search_run.yaml` (or the
extraction equivalent) to disk before returning. Failures land in
`run["schema_errors"]`, not in raised exceptions.

---

## 5. Running the Optional MCP Server

Install `mcp` extra, then:

```bash
uv run python -m research_foundry.services.search_router.mcp_server
```

The module **imports cleanly without `mcp` installed**; only `build_server()`
and `main()` try to resolve the SDK, and they raise a clear `RuntimeError`
asking you to `uv sync --extra mcp` if it's missing. Tools registered today:

- `search.run` — wraps `run_search(request)`
- `extract.url` — wraps `extract_urls(urls)`
- `search.source_discovery` / `search.semantic_discovery` /
  `search.github_discovery` — thin mode-presets that call `run_search` with
  the corresponding `mode`.

This covers the minimum tool surface from spec §10.2 needed for an agent
harness to drive the router. The full surface (`crawl.site`,
`research.build_source_cards`, `research.verify_claims`,
`research.monitor_query`, …) is deferred.

---

## 6. Deferred Infrastructure (Spec §14)

The following are intentionally **not** part of the MVP and are tracked as
future work. Adding any of them does **not** require breaking changes to the
router contract.

| Component | Spec role | Current substitute |
|-----------|-----------|--------------------|
| Postgres | Runs / sources / claims / provider metrics | YAML files under `runs/<run_id>/` |
| MinIO | Raw HTML / Markdown / PDF / screenshot blobs | Inline content in source cards |
| Redis | Short-lived cache + rate limits | None (no client-side rate limiter today) |
| OpenSearch | Local lexical search | None (re-run search, or use existing `rf find`) |
| Qdrant / pgvector | Local semantic search / dedupe | URL-canonical dedupe + authority ranking only |
| FastAPI REST surface | spec §10.3 (`POST /v1/search`, …) | CLI + MCP only |

When the storage tier lands, the router contract stays the same — files become
a write-through cache or a read-side replica, and the on-disk run layout
remains the canonical artifact.
