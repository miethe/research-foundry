---
title: "Search Router — Provider Profiles"
doc_type: reference
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

# Search Router — Provider Profiles

This page documents **only the providers that are actually implemented today**
under `src/research_foundry/services/search_router/providers/`. Each adapter
implements the `SearchProvider` protocol from `providers/base.py` and degrades
to "unavailable" (silently dropped from the chain) when its API key or `httpx`
is not installed.

Key conventions used by every adapter:

- **Env key resolution.** Adapters consult `RF_<PROVIDER>_API_KEY` first, then
  the vendor-standard `<PROVIDER>_API_KEY` (via `env_first`). Keys are read at
  call time, never embedded in config files (spec §15, §14.3).
- **Optional `httpx`.** All HTTP work is gated behind the `search` extra
  (`uv sync --extra search`). Without it, adapters report unavailable.
- **No raises from the run loop.** A provider exception becomes a
  `provider_chain[].status = "failed"` entry plus a `schema_errors` line on
  the run — the run still completes.

Pricing notes below are quoted from spec §8 footnotes; verify against the
provider's live pricing page before depending on a cost figure. (`last_verified:
2026-06-21`.)

---

## Brave Search API — `brave`

- **Role:** `discovery` (broad raw web/news/source candidates).
- **Endpoint:** `https://api.search.brave.com/res/v1/web/search`.
- **Env keys:** `RF_BRAVE_API_KEY`, falls back to `BRAVE_API_KEY`.
- **Pricing note (spec §8.1):** "Brave advertises complete search results with
  LLM context at $5 per 1,000 requests and $5 monthly credits." Verify at
  brave.com pricing before treating this as authoritative.
- **Known limits / cautions:**
  - Returns raw web results — extraction is **not** part of the response;
    pair with `jina` or `firecrawl` for source-card content.
  - Per-IP rate limits on free tiers; the run's `BudgetTracker.max_external_queries`
    is the only client-side guard today (no token bucket).
  - No semantic re-ranking — Brave is the breadth provider; chain it with Exa
    when conceptual similarity matters.

## Exa — `exa`

- **Role:** `discovery` (semantic search; "find things like this").
- **Endpoint:** `https://api.exa.ai/search`.
- **Env keys:** `RF_EXA_API_KEY`, falls back to `EXA_API_KEY`.
- **Pricing note (spec §8.1):** "Exa lists Search at $7 per 1k requests and
  Deep Search at $12–15 per 1k requests."
- **Known limits / cautions:**
  - Semantic-first ranking; results may differ substantially from a Google-style
    SERP — favor Exa when the query is a concept, not a string match.
  - Deep Search costs ~2× the standard Search call — the adapter calls the
    standard endpoint; deep-search is not wired up.
  - No first-party crawl — pair with an extraction provider for content.

## Jina Reader — `jina`

- **Role:** `extraction` (URL → Markdown).
- **Endpoint:** `https://r.jina.ai/<url>` (Reader prefix model).
- **Env keys:** `RF_JINA_API_KEY`, falls back to `JINA_API_KEY` —
  **optional**. The Reader endpoint works **keyless**; a key raises the rate
  limit. Adapter reports available even without a key.
- **Pricing note (spec §8.1):** "Jina positions Reader as part of its search
  foundation for web reader/deepsearch workflows." Keyless tier is rate-limited;
  paid tier is per-token (verify on jina.ai).
- **Known limits / cautions:**
  - Plain GET against the Reader prefix — JS-heavy pages may return shallow
    content; fall through to `firecrawl` for those.
  - Reader is single-URL — no crawl, no search.
  - First in the extraction preference order (`router._EXTRACTION_PROVIDER_PREFERENCE
    = ("jina", "firecrawl")`) precisely because it's free-tier-viable.

## Firecrawl — `firecrawl`

- **Roles:** `extraction` *and* `discovery`. Supports both `scrape` (single URL
  → Markdown) and `search` (vendor SERP-like).
- **Endpoints:**
  - Scrape: `https://api.firecrawl.dev/v1/scrape`
  - Search: `https://api.firecrawl.dev/v1/search`
- **Env keys:** `RF_FIRECRAWL_API_KEY`, falls back to `FIRECRAWL_API_KEY`.
- **Pricing note (spec §8.1):** "Firecrawl lists 1,000 free credits/pages per
  month; Scrape, Crawl, Map, and Monitor cost 1 credit per page, while Search
  costs 2 credits per 10 results."
- **Known limits / cautions:**
  - Used as the **fallback** extractor (after Jina) and the only `docs_crawl`
    discovery provider in the default chain.
  - JS rendering is supported but slower — set realistic `max_latency_seconds`.
  - The adapter calls `/v1/scrape` per URL (no batch). Multi-URL extraction
    walks the list serially today.

## GitHub Search — `github`

- **Role:** `discovery` (repos, READMEs, releases).
- **Endpoint:** `https://api.github.com/search/repositories`.
- **Env keys:** `RF_GITHUB_TOKEN`, falls back to `GITHUB_TOKEN`. **Optional**
  — the GitHub search API is public, but unauthenticated calls are rate-limited
  to ~10 req/min/IP. A token raises that to ~30 req/min.
- **Pricing note:** Free for public-repo search at the rates above. No vendor
  paid tier for this endpoint.
- **Known limits / cautions:**
  - Only `repositories` is wired today — no `code` or `issues` search.
  - Returns repo metadata (name, description, stars, URL). README extraction
    is downstream (let `jina`/`firecrawl` hit the repo README URL).
  - Used as first link in `github_discovery` mode (`github → exa → brave`).

---

## Deferred Providers (Next Steps)

The spec (§8 + §9 + §17) calls out providers we **intentionally have not
implemented** in the MVP. They are listed here so the gap is visible and the
implementation order is clear:

| Provider | Role | Why deferred | Where to slot in |
|----------|------|--------------|------------------|
| **Serper** | discovery (Google-style SERP) | Brave already covers broad discovery for our default cost envelope. Add when we need Google-rank fidelity. | `providers/serper.py` + add to `quick_lookup` / `source_discovery` chains. |
| **Tavily** | discovery + extraction (agent-native) | One-API convenience overlaps existing chain; revisit once we benchmark. | `providers/tavily.py`; could replace Brave+Jina in `quick_lookup`. |
| **Perplexity Sonar** | cited-answer engine | Synthesis surface, not a source provider — would live as a separate "summarizer" role, not in the discovery chain. | New `summarizer` role on `SearchProvider`. |
| **Gemini Grounding** | Google-grounded synthesis | Same as Sonar — synthesis, not source acquisition. | New `summarizer` role; also part of multi-model routing layer. |
| **OpenAI web_search** (Responses) | model-mediated discovery + synthesis | Same as Sonar; useful in `deep_research` mode. | New `summarizer` role; gated by `llm` extra. |
| **OpenAlex / Semantic Scholar / arXiv / PubMed** | academic discovery | `academic_discovery` mode currently has empty chain. These are the four adapters that unblock it. | `providers/openalex.py`, etc.; wire into `academic_discovery` chain. |
| **Claude web search** | Claude-native lookup | Same shape as OpenAI/Gemini; lower priority since router is Claude-callable from the CLI/MCP side already. | `summarizer` role. |

> Avoid as new dependencies: **Bing Search APIs** (retired 2025-08-11) and
> **Google Custom Search JSON API** (closed to new customers; existing users
> migrate by 2027-01-01). See spec §8.2.
