---
id: mwb_20260613_agentic_web_scientific_research_tools_a
evidence_bundle_id: bundle_20260613_intent_research_20260613_as_of_mid
target_page: meatywiki/sources/agentic_web_scientific_research_tools_a.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260613_as_of_mid_2026_what_are: 57 supported
  claim(s) across 9 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
links:
  source_cards:
  - src_20260613_rib009_00
  - src_20260613_rib009_01
  - src_20260613_rib009_02
  - src_20260613_rib009_03
  - src_20260613_rib009_04
  - src_20260613_rib009_05
  - src_20260613_rib009_06
  - src_20260613_rib009_07
  - src_20260613_rib009_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Agentic web/scientific research tools: a mid-2026 capability landscape for Research Foundry discovery adapters

## Summary

Source note distilled from research run rf_run_20260613_as_of_mid_2026_what_are: 57 supported claim(s) across 9 source card(s).

## Key claims

- GPT Researcher's FAST_LLM tier handles fast operations such as summaries and defaults to openai:gpt-4o-mini. [claim:clm_001]
- The SMART_LLM tier handles report generation and reasoning and defaults to openai:gpt-5. [claim:clm_002]
- The STRATEGIC_LLM tier handles research planning and strategy and defaults to openai:gpt-5-mini. [claim:clm_003]
- GPT Researcher's default integration suite uses OpenAI for LLM calls and the Tavily API for real-time web retrieval. [claim:clm_004]
- The RETRIEVER setting selects the web search engine; it defaults to tavily with options duckduckgo, bing, google, searchapi, serper, and searx. [claim:clm_005]
- The embedding model defaults to openai:text-embedding-3-small with options including ollama, huggingface, azure_openai, and custom. [claim:clm_006]
- REPORT_FORMAT controls report citation style, defaulting to APA with options such as MLA, CMS, Harvard, and IEEE. [claim:clm_007]
- Configuration is overridden by adding env variables to a .env file or exporting them manually in the local project directory. [claim:clm_008]
- The sonar-deep-research model is a research model that conducts exhaustive multi-source searches and synthesizes expert-level insights into detailed reports. [claim:clm_009]
- Sonar Deep Research has a 128K-token context length. [claim:clm_010]
- Pricing is $2 per 1M input tokens, $8 per 1M output tokens, $2 per 1M citation tokens, $3 per 1M reasoning tokens, and $5 per 1K search-query requests. [claim:clm_011]
- Each object in the response's search_results array exposes title, url, date, last_updated, and snippet fields. [claim:clm_012]
- The usage object reports prompt_tokens, completion_tokens, total_tokens, citation_tokens, num_search_queries, and reasoning_tokens plus a per-component cost breakdown. [claim:clm_013]
- A sample comprehensive query consumed 11,395 completion tokens, 21 search queries, and 193,947 reasoning tokens for a reported total cost of $0.816. [claim:clm_014]
- GPT Researcher is an autonomous agent built for comprehensive online research across a variety of tasks. [claim:clm_015]
- An average GPT Researcher run takes roughly 3 minutes and costs about $0.10. [claim:clm_016]
- GPT Researcher uses a planner agent that generates research questions and execution agents that gather the most relevant information for each question. [claim:clm_017]
- GPT Researcher aggregates over 20 web sources per research run to form objective, factual conclusions. [claim:clm_018]
- GPT Researcher can produce long, detailed research reports exceeding 2,000 words. [claim:clm_019]
- GPT Researcher can generate multiple report types: research, outlines, resources, and lessons reports. [claim:clm_020]
- GPT Researcher can export research reports to PDF, Word, and additional formats. [claim:clm_021]
- Each GPT Researcher deep research run takes about 5 minutes and costs about $0.40, using o3-mini at 'high' reasoning effort. [claim:clm_022]
- Deep Research is invoked by passing report_type="deep" to the GPTResearcher constructor. [claim:clm_023]
- deep_research_breadth sets the number of parallel research paths at each level and defaults to 4. [claim:clm_024]
- deep_research_depth sets how many levels deep to explore and defaults to 2. [claim:clm_025]
- deep_research_concurrency sets the maximum number of concurrent research operations and defaults to 4. [claim:clm_026]
- Deep Research uses a tree-like exploration pattern where breadth fans out multiple search queries per level and depth recursively dives deeper following leads. [claim:clm_027]
- Concurrent processing uses async/await patterns to run multiple research paths simultaneously. [claim:clm_028]
- The recommended total_words setting for a generated deep report is 2000 words. [claim:clm_029]
- GPT Researcher is positioned as the first open deep research agent designed for both web and local research on any given task, released under the Apache 2 license. [claim:clm_030]
- GPT Researcher is shared under the Apache 2.0 license for academic purposes. [claim:clm_031]
- The core Python API instantiates GPTResearcher(query=...), then awaits conduct_research() and write_report() to produce a report. [claim:clm_032]
- GPT Researcher includes a Deep Research mode described as an advanced recursive research workflow that explores topics with agentic depth and breadth. [claim:clm_033]
- GPT Researcher is LLM-agnostic and supports custom OpenAI-compatible APIs (local models or other providers) via the OPENAI_BASE_URL environment variable. [claim:clm_034]
- GPT Researcher supports MCP integration to connect with specialized data sources such as GitHub repositories, databases, and custom APIs. [claim:clm_035]
- Reports generated by GPT Researcher can be exported to PDF, Word, and other formats. [claim:clm_036]
- Perplexity defines six usage tiers gated by cumulative lifetime spend: Tier 0 at $0, Tier 1 at $50+, Tier 2 at $250+, Tier 3 at $500+, Tier 4 at $1,000+, and Tier 5 at $5,000+. [claim:clm_037]
- Tier placement is determined by cumulative purchases over the account lifetime rather than current account balance. [claim:clm_038]
- The sonar-deep-research model's per-minute request limit scales by tier from 5 RPM at Tier 0 up through 10, 20, 40, 60, and 100 RPM at Tier 5. [claim:clm_039]
- The sonar, sonar-pro, and sonar-reasoning-pro models share an RPM ceiling that rises by tier: 50, 150, 500, 1,000, then 4,000 RPM at both Tier 4 and Tier 5. [claim:clm_040]
- Async polling retrieval endpoints carry high, tier-independent limits, with GET /v1/async/sonar at 3,000 RPM and GET /v1/async/sonar/{request_id} at 6,000 RPM across all tiers. [claim:clm_041]
- GPT Researcher is distributed under the Apache License, Version 2.0 (January 2004). [claim:clm_042]
- Apache 2.0 grants a perpetual, worldwide, royalty-free, irrevocable copyright license to reproduce, prepare derivative works of, and distribute the work in source or object form. [claim:clm_043]
- Redistribution requires giving recipients a copy of the license and marking any modified files with prominent notices stating they were changed. [claim:clm_044]
- The work is provided 'AS IS' without warranties or conditions of any kind, express or implied, including merchantability or fitness for a particular purpose. [claim:clm_045]
- Base Sonar charges $1 per 1M input tokens and $1 per 1M output tokens, the cheapest Sonar model on a per-token basis. [claim:clm_046]
- Sonar Pro costs $3 per 1M input tokens and $15 per 1M output tokens; Sonar Reasoning Pro costs $2 input and $8 output per 1M tokens. [claim:clm_047]
- Sonar Deep Research has $2/1M input and $8/1M output, plus additional charges of $2/1M citation tokens, $3/1M reasoning tokens, and $5/1K search queries. [claim:clm_048]
- Per-request fees per 1000 requests for base Sonar are $5 (low), $8 (medium), and $12 (high) search context size. [claim:clm_049]
- Per 1000 requests, Sonar Pro and Sonar Reasoning Pro both charge $6 (low), $10 (medium), and $14 (high) for search context. [claim:clm_050]
- Total Sonar query cost equals token costs plus a request fee that varies by search context size and applies only to Sonar, Sonar Pro, and Sonar Reasoning Pro models. [claim:clm_051]
- v3.5.0, released May 28, 2026, is the latest stable GPT Researcher release, framed as a stack-wide update with critical bug fixes, performance improvements, and new models and retrievers. [claim:clm_052]
- v3.4.4 (April 2026) added MiniMax as a native LLM and embedding provider, added an X/Twitter (Xquik) search retriever, and fixed the PubMed Central retriever returning no results. [claim:clm_053]
- v3.4.3 (March 2026) added per-step cost tracking in the research process plus a scrape-count option and other enhancements to the FastAPI frontend. [claim:clm_054]
- v3.4.0 (January 2026) introduced inline AI image generation that embeds Gemini-generated illustrations directly into reports, and added native LangSmith tracing/observability. [claim:clm_055]
- v3.4.0 also shipped a comprehensive .claude/skills/ directory so Claude Code can understand, use, and extend GPT Researcher. [claim:clm_056]
- v3.3.7 (Nov 2025) was a breaking release: the LangChain v1 migration dropped Python 3.9 (now requiring Python 3.10+) and cut requirements.txt from 134 to 63 lines. [claim:clm_057]

## Sources

- src_20260613_rib009_00 — assafelovic/gpt-researcher: An autonomous agent that conducts deep research on any data using any LLM providers
- src_20260613_rib009_01 — Releases - assafelovic/gpt-researcher
- src_20260613_rib009_02 — Deep Research - GPT Researcher Documentation
- src_20260613_rib009_03 — Configuration - GPT Researcher Documentation
- src_20260613_rib009_04 — Introduction - GPT Researcher Documentation
- src_20260613_rib009_05 — GPT Researcher LICENSE (Apache 2.0)
- src_20260613_rib009_06 — Sonar Deep Research — Perplexity API Docs
- src_20260613_rib009_07 — Pricing — Perplexity API Docs
- src_20260613_rib009_08 — Rate Limits and Usage Tiers — Perplexity API Docs

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
