---
schema_version: '0.1'
type: research_report
report_id: report_20260613_as_of_mid_2026_what_are
title: As of mid-2026, what are the capabilities, APIs,
intent_id: intent_research_20260613_as_of_mid_2026_what_are
evidence_bundle_id: pending
created_at: '2026-06-13T23:00:52-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

GPT Researcher's FAST_LLM tier handles fast operations such as summaries and defaults to openai:gpt-4o-mini. [claim:clm_001]
The SMART_LLM tier handles report generation and reasoning and defaults to openai:gpt-5. [claim:clm_002]
The STRATEGIC_LLM tier handles research planning and strategy and defaults to openai:gpt-5-mini. [claim:clm_003]
GPT Researcher's default integration suite uses OpenAI for LLM calls and the Tavily API for real-time web retrieval. [claim:clm_004]
The RETRIEVER setting selects the web search engine; it defaults to tavily with options duckduckgo, bing, google, searchapi, serper, and searx. [claim:clm_005]
The embedding model defaults to openai:text-embedding-3-small with options including ollama, huggingface, azure_openai, and custom. [claim:clm_006]
REPORT_FORMAT controls report citation style, defaulting to APA with options such as MLA, CMS, Harvard, and IEEE. [claim:clm_007]
Configuration is overridden by adding env variables to a .env file or exporting them manually in the local project directory. [claim:clm_008]
The sonar-deep-research model is a research model that conducts exhaustive multi-source searches and synthesizes expert-level insights into detailed reports. [claim:clm_009]
Sonar Deep Research has a 128K-token context length. [claim:clm_010]
Pricing is $2 per 1M input tokens, $8 per 1M output tokens, $2 per 1M citation tokens, $3 per 1M reasoning tokens, and $5 per 1K search-query requests. [claim:clm_011]
Each object in the response's search_results array exposes title, url, date, last_updated, and snippet fields. [claim:clm_012]
The usage object reports prompt_tokens, completion_tokens, total_tokens, citation_tokens, num_search_queries, and reasoning_tokens plus a per-component cost breakdown. [claim:clm_013]
A sample comprehensive query consumed 11,395 completion tokens, 21 search queries, and 193,947 reasoning tokens for a reported total cost of $0.816. [claim:clm_014]
GPT Researcher is an autonomous agent built for comprehensive online research across a variety of tasks. [claim:clm_015]
An average GPT Researcher run takes roughly 3 minutes and costs about $0.10. [claim:clm_016]
GPT Researcher uses a planner agent that generates research questions and execution agents that gather the most relevant information for each question. [claim:clm_017]
GPT Researcher aggregates over 20 web sources per research run to form objective, factual conclusions. [claim:clm_018]
GPT Researcher can produce long, detailed research reports exceeding 2,000 words. [claim:clm_019]
GPT Researcher can generate multiple report types: research, outlines, resources, and lessons reports. [claim:clm_020]
GPT Researcher can export research reports to PDF, Word, and additional formats. [claim:clm_021]
Each GPT Researcher deep research run takes about 5 minutes and costs about $0.40, using o3-mini at 'high' reasoning effort. [claim:clm_022]
Deep Research is invoked by passing report_type="deep" to the GPTResearcher constructor. [claim:clm_023]
deep_research_breadth sets the number of parallel research paths at each level and defaults to 4. [claim:clm_024]
deep_research_depth sets how many levels deep to explore and defaults to 2. [claim:clm_025]
deep_research_concurrency sets the maximum number of concurrent research operations and defaults to 4. [claim:clm_026]
Deep Research uses a tree-like exploration pattern where breadth fans out multiple search queries per level and depth recursively dives deeper following leads. [claim:clm_027]
Concurrent processing uses async/await patterns to run multiple research paths simultaneously. [claim:clm_028]
The recommended total_words setting for a generated deep report is 2000 words. [claim:clm_029]
GPT Researcher is positioned as the first open deep research agent designed for both web and local research on any given task, released under the Apache 2 license. [claim:clm_030]
GPT Researcher is shared under the Apache 2.0 license for academic purposes. [claim:clm_031]
The core Python API instantiates GPTResearcher(query=...), then awaits conduct_research() and write_report() to produce a report. [claim:clm_032]
GPT Researcher includes a Deep Research mode described as an advanced recursive research workflow that explores topics with agentic depth and breadth. [claim:clm_033]
GPT Researcher is LLM-agnostic and supports custom OpenAI-compatible APIs (local models or other providers) via the OPENAI_BASE_URL environment variable. [claim:clm_034]
GPT Researcher supports MCP integration to connect with specialized data sources such as GitHub repositories, databases, and custom APIs. [claim:clm_035]
Reports generated by GPT Researcher can be exported to PDF, Word, and other formats. [claim:clm_036]
Perplexity defines six usage tiers gated by cumulative lifetime spend: Tier 0 at $0, Tier 1 at $50+, Tier 2 at $250+, Tier 3 at $500+, Tier 4 at $1,000+, and Tier 5 at $5,000+. [claim:clm_037]
Tier placement is determined by cumulative purchases over the account lifetime rather than current account balance. [claim:clm_038]
The sonar-deep-research model's per-minute request limit scales by tier from 5 RPM at Tier 0 up through 10, 20, 40, 60, and 100 RPM at Tier 5. [claim:clm_039]
The sonar, sonar-pro, and sonar-reasoning-pro models share an RPM ceiling that rises by tier: 50, 150, 500, 1,000, then 4,000 RPM at both Tier 4 and Tier 5. [claim:clm_040]
Async polling retrieval endpoints carry high, tier-independent limits, with GET /v1/async/sonar at 3,000 RPM and GET /v1/async/sonar/{request_id} at 6,000 RPM across all tiers. [claim:clm_041]
GPT Researcher is distributed under the Apache License, Version 2.0 (January 2004). [claim:clm_042]
Apache 2.0 grants a perpetual, worldwide, royalty-free, irrevocable copyright license to reproduce, prepare derivative works of, and distribute the work in source or object form. [claim:clm_043]
Redistribution requires giving recipients a copy of the license and marking any modified files with prominent notices stating they were changed. [claim:clm_044]
The work is provided 'AS IS' without warranties or conditions of any kind, express or implied, including merchantability or fitness for a particular purpose. [claim:clm_045]
Base Sonar charges $1 per 1M input tokens and $1 per 1M output tokens, the cheapest Sonar model on a per-token basis. [claim:clm_046]
Sonar Pro costs $3 per 1M input tokens and $15 per 1M output tokens; Sonar Reasoning Pro costs $2 input and $8 output per 1M tokens. [claim:clm_047]
Sonar Deep Research has $2/1M input and $8/1M output, plus additional charges of $2/1M citation tokens, $3/1M reasoning tokens, and $5/1K search queries. [claim:clm_048]
Per-request fees per 1000 requests for base Sonar are $5 (low), $8 (medium), and $12 (high) search context size. [claim:clm_049]
Per 1000 requests, Sonar Pro and Sonar Reasoning Pro both charge $6 (low), $10 (medium), and $14 (high) for search context. [claim:clm_050]
Total Sonar query cost equals token costs plus a request fee that varies by search context size and applies only to Sonar, Sonar Pro, and Sonar Reasoning Pro models. [claim:clm_051]
v3.5.0, released May 28, 2026, is the latest stable GPT Researcher release, framed as a stack-wide update with critical bug fixes, performance improvements, and new models and retrievers. [claim:clm_052]
v3.4.4 (April 2026) added MiniMax as a native LLM and embedding provider, added an X/Twitter (Xquik) search retriever, and fixed the PubMed Central retriever returning no results. [claim:clm_053]
v3.4.3 (March 2026) added per-step cost tracking in the research process plus a scrape-count option and other enhancements to the FastAPI frontend. [claim:clm_054]
v3.4.0 (January 2026) introduced inline AI image generation that embeds Gemini-generated illustrations directly into reports, and added native LangSmith tracing/observability. [claim:clm_055]
v3.4.0 also shipped a comprehensive .claude/skills/ directory so Claude Code can understand, use, and extend GPT Researcher. [claim:clm_056]
v3.3.7 (Nov 2025) was a breaking release: the LangChain v1 migration dropped Python 3.9 (now requiring Python 3.10+) and cut requirements.txt from 134 to 63 lines. [claim:clm_057]

## Inferences

**Inference:** GPT Researcher and Perplexity Sonar Deep Research are the only two of the four target tools with first-party evidence in this run, so Gemini Deep Research and PaperQA2 cannot yet be scored against RF's adapter contract and must be treated as evidence gaps pending dedicated source cards. [claim:clm_inf01]
**Inference:** Both evidenced tools expose programmatic, headless interfaces (GPT Researcher via the GPTResearcher Python class with conduct_research()/write_report(); Perplexity via an HTTP chat-completions endpoint plus async submit/poll endpoints), so neither is UI-only and both clear RF's baseline requirement of API-driven, headless invocation. [claim:clm_inf02]
**Inference:** Perplexity Sonar Deep Research normalizes into RF's source_card and extraction_card schemas more directly than GPT Researcher because its response already returns a structured search_results array (title, url, date, last_updated, snippet) plus a typed usage/cost object, whereas GPT Researcher emits a prose report (PDF/Word/Markdown) whose citations must be parsed out post hoc. [claim:clm_inf03]
**Inference:** GPT Researcher carries the most permissive governance posture of the evidenced tools: its Apache 2.0 license grants perpetual, royalty-free, irrevocable rights with no terms-of-service restriction on automated/programmatic use of the code itself, so the only governance constraints come from whichever LLM and retriever providers (default OpenAI plus Tavily) are wired in behind it. [claim:clm_inf04]
**Inference:** Because GPT Researcher is self-hostable and LLM-agnostic via OPENAI_BASE_URL, RF can route it through self-hosted or in-region OpenAI-compatible endpoints to satisfy data-residency and key-handling requirements, an option Perplexity's hosted-only Sonar API does not offer since every Sonar Deep Research call must traverse Perplexity's servers under their tier-gated account. [claim:clm_inf05]
**Inference:** On a per-deep-run basis the two evidenced tools are within roughly 2x of each other: GPT Researcher deep mode is vendor-stated at about $0.40 per run, while a worked Perplexity Sonar Deep Research example cost $0.816, so cost is not a decisive differentiator and adapter selection should turn on output structure and governance rather than price. [claim:clm_inf06]
**Inference:** Perplexity Sonar Deep Research's per-run cost is dominated and made volatile by reasoning tokens, not input/output tokens: in the worked example 193,947 reasoning tokens billed at $3/1M contributed $0.582 of the $0.816 total (about 71%), so RF must budget for reasoning-token blow-ups and cap query complexity rather than rely on the $2/$8 input-output headline rates. [claim:clm_inf07]
**Inference:** Perplexity's tier system gates real-mode throughput on cumulative lifetime spend rather than balance, so a new RF account starts at Tier 0 with only 5 RPM for sonar-deep-research and must accumulate $1,000+ in spend to reach Tier 4-level limits; RF should therefore route bulk or parallel Sonar Deep Research jobs through the tier-independent async submit/poll endpoints (3,000/6,000 RPM) to avoid early throttling. [claim:clm_inf08]
**Inference:** GPT Researcher carries the highest API-stability risk of the evidenced tools because it ships multiple minor releases per quarter and has already executed a breaking change (v3.3.7 dropping Python 3.9 via LangChain v1), so RF must pin a known-good version (latest stable v3.5.0, May 2026) and gate upgrades behind adapter regression tests rather than tracking head. [claim:clm_inf09]
**Inference:** Implement GPT Researcher as the first real-mode RF adapter and Perplexity Sonar Deep Research as the second: GPT Researcher wins on governance (Apache 2.0, self-hostable, no automated-use ToS), cost-floor ($0.10 standard / $0.40 deep), and a native Python API, while Perplexity ranks second for its cleaner structured-JSON output but loses on hosted-only data residency and tier-gated throughput; Gemini Deep Research and PaperQA2 are deferred until source cards exist. [claim:clm_inf10]
**Inference:** GPT Researcher's three-tier model scheme (FAST_LLM gpt-4o-mini, STRATEGIC_LLM gpt-5-mini, SMART_LLM gpt-5) directly realizes RF's cheap-extract / expensive-synthesize cost discipline, letting the RF adapter cap spend by overriding only the strategic and smart tiers while leaving cheap summary work on gpt-4o-mini. [claim:clm_inf11]

## Speculation

**Speculation:** If Gemini Deep Research and PaperQA2 follow the patterns of their peers, Gemini Deep Research will likely arrive as a hosted, account-gated API resembling Perplexity's governance profile while PaperQA2 (an open-source scientific-QA library) will likely resemble GPT Researcher's self-hostable, structured-output profile and may rank second behind GPT Researcher once evidenced, but this is unverified and contingent on dedicated source cards. [claim:clm_spec01]

## Open questions

- None recorded.

## Sources

- src_20260613_rib009_03: Configuration - GPT Researcher Documentation
- src_20260613_rib009_06: Sonar Deep Research — Perplexity API Docs
- src_20260613_rib009_04: Introduction - GPT Researcher Documentation
- src_20260613_rib009_02: Deep Research - GPT Researcher Documentation
- src_20260613_rib009_00: assafelovic/gpt-researcher: An autonomous agent that conducts deep research on any data using any LLM providers
- src_20260613_rib009_08: Rate Limits and Usage Tiers — Perplexity API Docs
- src_20260613_rib009_05: GPT Researcher LICENSE (Apache 2.0)
- src_20260613_rib009_07: Pricing — Perplexity API Docs
- src_20260613_rib009_01: Releases - assafelovic/gpt-researcher
