---
id: mwb_20260622_dr_gpt_researcher_vs_paperqa2_vs
evidence_bundle_id: bundle_20260614_intent_research_20260613_how_do_gpt
target_page: meatywiki/decisions/gpt_researcher_vs_paperqa2_vs_claude.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260613_how_do_gpt_researcher_paperqa2_and: clm_047 (cheapest
  run), clm_046 (breadth of web sources), clm_051 (hybrid web+MCP retrieval), and clm_048 (Apache-2 self'
key_claims:
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_047
  - clm_046
  - clm_051
  - clm_048
  - clm_025
  - clm_022
  - clm_061
  - clm_033
  - clm_018
  - clm_013
  - clm_015
  - clm_017
  - clm_035
  - clm_inf11
  - clm_inf12
  - clm_inf13
  - clm_inf14
  - clm_037
  - clm_038
  - clm_069
  - clm_024
  - clm_001
  - clm_067
  - clm_071
  - clm_021
  - clm_068
  - clm_012
  - clm_007
  - clm_008
  - clm_010
  - clm_066
  - clm_014
  - clm_052
  - clm_023
  - clm_019
  - clm_030
  - clm_028
  - clm_077
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: GPT Researcher vs PaperQA2 vs Claude Agent SDK as Research Foundry discovery/extraction adapters

## Context

- PaperQA2 is a frontier language model agent optimized for improved factuality that matches or exceeds subject-matter-expert performance on three realistic literature research tasks. [claim:clm_001]
- The human-AI comparison placed no restrictions on the human experts, who retained full access to internet, search tools, and time. [claim:clm_002]
- PaperQA2 writes cited, Wikipedia-style summaries of scientific topics that are significantly more accurate than existing human-written Wikipedia articles. [claim:clm_003]
- The authors introduce LitQA2, a hard scientific-literature-research benchmark that guided PaperQA2's design and led it to exceed human performance. [claim:clm_004]
- Applied to contradiction detection, PaperQA2 identifies 2.34 +/- 1.99 contradictions per paper in a random subset of biology papers, of which 70% are validated by human experts. [claim:clm_005]
- The authors conclude that language model agents are now capable of exceeding domain experts across meaningful scientific-literature tasks. [claim:clm_006]
- GPT Researcher v3.5.0, released May 28 2026, is the latest stable release and is published by maintainer @assafelovic. [claim:clm_007]
- v3.5.0 added an OpenAlex academic retriever and a ModelsLab image-generation provider. [claim:clm_008]
- v3.5.0 raised the max_tokens cap from 32k to 200k to support modern long-output models, and added native Anthropic usage tracking. [claim:clm_009]
- v3.4.4 (April 16 2026) added MiniMax as a native LLM and embedding provider and an Xquik X/Twitter search retriever. [claim:clm_010]
- v3.4.3 (March 13 2026) introduced per-step cost tracking in the research process. [claim:clm_011]
- v3.3.7 was a breaking release that migrated to LangChain v1 and raised the minimum Python version, dropping Python 3.9 support. [claim:clm_012]
- Web search on the Claude API is billed at $10 per 1,000 searches plus standard token costs for search-generated content. [claim:clm_013]
- Each web search counts as one billable use regardless of result count, and searches that error out are not billed. [claim:clm_014]
- The web fetch tool carries no additional charge beyond standard token costs for the fetched content. [claim:clm_015]
- Code execution incurs no additional charge beyond token costs when used alongside the web search or web fetch tools. [claim:clm_016]
- Claude Sonnet 4.6 is $3/MTok input, $15/MTok output, $0.30/MTok cache read; Claude Haiku 4.5 is the cheapest current tier at $1/MTok input, $5/MTok output; Claude Opus 4.8 is $5/MTok input, $25/MTok output. [claim:clm_017]
- Claude Managed Agents session runtime is billed at $0.08 per session-hour, metered only while the session status is 'running'. [claim:clm_018]
- Claude Managed Agents is billed on two dimensions — tokens at standard Model pricing rates and session runtime — with web search inside a session still incurring the standard $10 per 1,000 searches. [claim:clm_019]
- PaperQA2 is a package for high-accuracy retrieval-augmented generation (RAG) over PDFs, text files, Microsoft Office documents, and source code files, with a focus on scientific literature. [claim:clm_020]
- A PaperQA2 answer object exposes formatted_answer, answer (the answer alone), question, and context (summaries of the passages found for the answer). [claim:clm_021]
- PaperQA2 emits in-text citations that reference specific source passages using keys formatted like (pqac-abcd1234). [claim:clm_022]
- PaperQA2 provides a customization interface with default support for all LiteLLM-compatible models. [claim:clm_023]
- By default PaperQA2 uses OpenAI's gpt-4o-2024-11-20 model for the summary_llm, llm, and agent_llm roles. [claim:clm_024]
- PaperQA2 relies on external paper search and metadata services including Semantic Scholar, Crossref, and Unpaywall. [claim:clm_025]
- The Python API entry point imports Settings and ask from paperqa, and an async agent_query() function is also provided for agentic querying. [claim:clm_026]
- AstaBench is a scientific-research agent benchmark suite published as a conference paper at ICLR 2026 and submitted to arXiv on 2025-10-24. [claim:clm_027]
- The headline finding is that despite progress on individual aspects, AI agents remain far from solving science research assistance, based on evaluating 57 agents across 22 agent classes. [claim:clm_028]
- AstaBench comprises 2400+ problems spanning the entire scientific discovery process and multiple domains, with many problems drawn from real user requests to deployed Asta agents. [claim:clm_029]
- The paper explicitly motivates cost-aware evaluation, faulting prior benchmarks for not accounting for confounding variables such as model cost and tool access. [claim:clm_030]
- AstaBench ships a reproducible research environment with production-grade search tools plus nine science-optimized Asta agent classes and numerous baselines for controlled comparison. [claim:clm_031]
- The benchmark targets agents across the discovery pipeline, ranging from general-purpose deep research systems to specialized science agents such as AI Scientist and AIGS. [claim:clm_032]
- PaperQA2's design philosophy explicitly de-prioritizes cost and latency to maximize accuracy as the goal for a best-in-class RAG system. [claim:clm_033]
- PaperQA2 was evaluated on LitQA2, a set of 200 expert-crafted multiple-choice questions. [claim:clm_034]
- The agent-based system delivered significant improvements in both accuracy and answer recall over a non-agentic baseline (agentic vs. non-agentic ablation). [claim:clm_035]
- The citation traversal tool is invoked on only about 46% of questions, indicating selective, query-dependent tool use within the agent loop. [claim:clm_036]
- On average the PaperQA2 agent makes more than 4 tool calls per question. [claim:clm_037]
- The agent averages 1.26 searches per question across benchmark runs. [claim:clm_038]
- FutureHouse is launching Edison Scientific, a commercial spinout to further develop and deploy its AI Scientist for commercial applications. [claim:clm_039]
- A portion of the FutureHouse team is moving to Edison, while FutureHouse continues developing AI Scientists for foundational biology research. [claim:clm_040]
- Sam Rodriques and Andrew White will run both FutureHouse and Edison with stated controls against self-dealing and conflicts of interest. [claim:clm_041]
- Edison commits to a generous free tier while charging power users who need higher rate limits or additional features. [claim:clm_042]
- Since the platform launched in May 2025, FutureHouse has been inundated with rate-limit-increase requests it could not support, motivating the spinout. [claim:clm_043]
- FutureHouse received inbound interest in its agents from VP- or C-level executives at 6 of the top 10 pharma companies. [claim:clm_044]
- FutureHouse argues that productization, payments, go-to-market, and customer support are not the right use of philanthropic funding, justifying the commercial spinout. [claim:clm_045]
- GPT Researcher aggregates more than 20 sources per research run to form objective conclusions. [claim:clm_046]
- Deep Research mode takes about 5 minutes and costs about $0.40 per run using o3-mini at high reasoning effort. [claim:clm_047]
- GPT Researcher is distributed under the Apache 2 license, supporting self-hosted use. [claim:clm_048]
- The Python API instantiates a GPTResearcher with a query, then awaits conduct_research() and write_report() to produce a report. [claim:clm_049]
- GPT Researcher supports MCP integration to connect specialized data sources such as GitHub repos, databases, and custom APIs. [claim:clm_050]
- The retriever is configurable to run a hybrid of web search (Tavily default) and MCP retrievers via the RETRIEVER environment variable. [claim:clm_051]
- The tool is LLM-agnostic and can target custom OpenAI-compatible APIs by setting the OPENAI_BASE_URL environment variable. [claim:clm_052]
- Research can be constrained to a caller-supplied list of URLs via the source_urls parameter of the GPTResearcher class. [claim:clm_053]
- The complement_source_urls flag controls whether GPT Researcher researches beyond the provided URLs; its default value of False restricts research to only the given source_urls. [claim:clm_054]
- An agent prompt instruction can steer both the research direction and report layout by passing the prompt as the query argument together with the custom_report report_type. [claim:clm_055]
- GPT Researcher can research local documents (set DOC_PATH and report_source="local"); supported input formats are PDF, plain text, CSV, Excel, Markdown, PowerPoint, and Word. [claim:clm_056]
- Web sources and local documents can be researched together by setting the report_source argument to "hybrid", with appropriate retrievers and doc path configured. [claim:clm_057]
- GPT Researcher accepts a list of LangChain Document instances (report_source="langchain_documents"), enabling research over documents pulled from a vector store / retriever. [claim:clm_058]
- The same async Python API drives all source modes: instantiate GPTResearcher, then await conduct_research() followed by await write_report(). [claim:clm_059]
- PaperQA2 is presented as the first AI agent to achieve superhuman performance on a variety of scientific literature search tasks, optimized for retrieving and summarizing information over the scientific literature. [claim:clm_060]
- PaperQA2 achieves higher accuracy than PhD- and postdoc-level biology researchers at retrieving information from the scientific literature, as measured using LitQA2, part of the LAB-Bench eval set. [claim:clm_061]
- WikiCrow, an agent built on top of PaperQA2, produces scientific summaries judged more accurate on average than human-written Wikipedia articles by blinded PhD- and postdoc-level researchers. [claim:clm_062]
- An older version (PaperQA) was used to generate Wikipedia-style articles for all 20,000 human genome genes by combining information from 1 million distinct scientific papers, though those earlier articles were on average less accurate than existing Wikipedia articles. [claim:clm_063]
- ContraCrow, an agent built on PaperQA2, evaluates every claim in a paper to find contradicting papers and detected an average of 2.34 contradicted statements per paper in a random subset of biology papers. [claim:clm_064]
- GPT Researcher is installed from PyPi via pip with the command pip install gpt-researcher. [claim:clm_065]
- The pip package prerequisite is that Python 3.10 or newer is installed on the machine. [claim:clm_066]
- The get_research_sources() method retrieves a list of research sources, including their title, content, and images fields. [claim:clm_067]
- The get_research_context() method returns all retrieved information from the research, combining the sources with their corresponding content. [claim:clm_068]
- The get_costs() method returns the number of tokens consumed during the research process. [claim:clm_069]
- The get_research_images() method retrieves a list of images found during the research process. [claim:clm_070]
- The get_source_urls() method returns the list of URLs that were used to gather information for the research. [claim:clm_071]
- FutureHouse launched its platform on May 1, 2025, offering publicly available scientific AI agents free via a web interface and API. [claim:clm_072]
- Crow is a general-purpose literature-search agent that returns concise scholarly answers and is designed for API use. [claim:clm_073]
- Falcon targets deep literature reviews, synthesizing more scientific literature than other agents and drawing on specialized databases like OpenTargets. [claim:clm_074]
- Owl (formerly HasAnyone) is a precedent-search agent specialized to answer whether anyone has done a given task before. [claim:clm_075]
- Phoenix (experimental) is a deployment of ChemCrow, a tool-using agent that helps researchers plan chemistry experiments. [claim:clm_076]
- FutureHouse reports that Crow, Falcon, and Owl were benchmarked and outperform major frontier search models on retrieval precision and accuracy. [claim:clm_077]
- FutureHouse claims its agents were experimentally validated as having better precision than PhD-level researchers in head-to-head literature search tasks. [claim:clm_078]

## Decision

For web/current-events and general-domain briefs on a low budget tier, rf swarm run should select GPT Researcher as the extraction backbone because it is the cheapest modeled run (~$0.40), breadth-first (20+ web sources), and natively hybrid (Tavily + MCP) and self-hostable under Apache-2. [claim:clm_inf11]

## Rationale

- clm_047 (cheapest run), clm_046 (breadth of web sources), clm_051 (hybrid web+MCP retrieval), and clm_048 (Apache-2 self-host) jointly make GPT Researcher the cost-optimal pick for web/general low-budget briefs. [claim:clm_inf11]
- clm_025 (scholarly metadata services), clm_022 (passage-level citations), and clm_061 (expert-matching LitQA2 accuracy) justify PaperQA2 for scientific accuracy-critical briefs, with clm_033 making explicit that the trade is higher cost for that accuracy. [claim:clm_inf12]
- clm_018/clm_013/clm_015 give deterministic session-runtime, per-search, and zero-cost-fetch metering for hard budget ceilings; clm_017's Haiku-vs-Opus spread supports a cheap-extract/expensive-synthesize split, fitting RF's governed cost model. [claim:clm_inf13]
- clm_046 (web breadth) and clm_025/clm_035 (scholarly depth/recall) show the adapters are complementary, not redundant; clm_033 implies a PaperQA2-only attempt at web breadth would be costly, so fan-in is justified only when a brief genuinely spans both evidence types. [claim:clm_inf14]
- This consolidates the per-adapter selection recommendations (clm_inf11 web/cheap, clm_inf12 scientific/accurate, clm_inf13 governed/capped) and the fan-in condition (clm_inf14) into a single keyed routing rule for rf swarm run. [claim:clm_inf16]
- clm_046/clm_047 give GPT Researcher a concrete ~$0.40/>20-source run cost; PaperQA2 sources (clm_037/clm_038) report only per-question tool/search counts and clm_069 notes GPT Researcher's get_costs() returns tokens not dollars; Claude pricing (clm_013/clm_017) is per-search and per-token, so SDK and PaperQA2 costs are derived from components, not stated as a run total. [claim:clm_inf01]
- $0.40 per run (clm_047) divided across 20+ sources (clm_046) gives ~$0.02/source; treated as a coarse upper-bound estimate because the run cost is model-specific (o3-mini, high effort) and the 20-source figure is a floor. [claim:clm_inf02]
- clm_033 states PaperQA2 deliberately ignores cost; clm_037/clm_038 quantify >4 tool calls and 1.26 searches per question; clm_024 fixes a frontier default model (gpt-4o-2024-11-20); each adds token and search billing, so per-claim cost is structurally elevated relative to a single ~$0.40 GPT Researcher run. [claim:clm_inf03]
- clm_013 gives $10/1,000 (=$0.01) per web search and clm_015 makes web fetch free; clm_017 gives the 5x input / 5x output spread between Haiku and Opus, so the SDK per-source cost is search-fee + model-dependent token cost, placing it between the cheap GPT Researcher run and the accuracy-maximized PaperQA2. [claim:clm_inf04]
- clm_022 shows PaperQA2 emits passage-level citation keys; clm_001/clm_061 establish its expert-matching LitQA2 accuracy; clm_067/clm_071 show GPT Researcher exposes only source title/content and URL lists, so PaperQA2 carries finer-grained, benchmark-backed citation provenance. [claim:clm_inf05]
- clm_046 frames GPT Researcher around aggregating 20+ (largely web) sources for breadth; clm_035 shows PaperQA2's agentic loop improves answer recall, and clm_025 ties it to scholarly corpora (Semantic Scholar/Crossref/Unpaywall), so the two maximize different recall axes. [claim:clm_inf06]
- clm_021/clm_022 show PaperQA2 returns passage summaries plus passage-level citation keys directly usable as extraction_card evidence; clm_067/clm_068/clm_071 show GPT Researcher returns source/context/URL bundles without passage-level claim linkage, so RF must reconstruct it, a lossier mapping. [claim:clm_inf07]
- clm_012 documents a breaking LangChain v1 / Python-version migration; clm_007/clm_008/clm_010 show several feature-adding releases per quarter up to v3.5.0; clm_066 confirms the raised Python floor, together implying a high upgrade/stability burden for an RF adapter. [claim:clm_inf08]
- clm_013/clm_014/clm_015/clm_018 give the SDK fully itemized, deterministic billing units including non-billing of errored searches; clm_033 shows PaperQA2 explicitly ignores cost, so the SDK uniquely supports hard, pre-committed budget ceilings at RF's governance gate. [claim:clm_inf09]
- clm_052/clm_051 show GPT Researcher's keys/retrievers are env-configurable; clm_023 shows PaperQA2 uses LiteLLM-compatible (key-bearing) model config; clm_019 shows the Claude SDK uses standard Anthropic billing/keys, so RF's key-profile and secret-scanning gate applies uniformly across all three. [claim:clm_inf10]
- clm_030 shows AstaBench faults prior benchmarks for ignoring cost/tool access and clm_028 shows its sobering cross-agent conclusion, which tempers the vendor self-reported superhuman/precision claims in clm_001 and clm_077, motivating cost-controlled RF validation. [claim:clm_inf15]

## Consequences

- For scientific-literature briefs that demand citation accuracy and passage-level provenance, rf swarm run should select PaperQA2 as the extraction backbone, accepting its higher cost-per-claim, because it targets scholarly corpora (Semantic Scholar/Crossref/Unpaywall), emits passage-level citations, and is benchmarked to match or exceed domain experts on LitQA2. [claim:clm_inf12]
- For high-governance or budget-capped briefs that require deterministic spend and tight RF integration, rf swarm run should select the Claude Agent SDK adapter because its per-search and per-session-hour metering plus free web fetch let RF enforce hard cost ceilings, with Haiku 4.5 for cheap extraction and Opus 4.8 reserved for synthesis. [claim:clm_inf13]
- A multi-adapter fan-in (GPT Researcher for web breadth plus PaperQA2 for scholarly depth) is worth the extra cost only for high-stakes briefs that mix current-web and peer-reviewed evidence, since the two adapters maximize different recall axes and their combined cost still falls below an unbounded accuracy-maximized PaperQA2-only sweep for broad web coverage. [claim:clm_inf14]
- The decision rule reduces to a three-way split keyed on domain and budget: web/general + low budget to GPT Researcher, scientific + accuracy-critical to PaperQA2, and governed/budget-capped or RF-native to the Claude Agent SDK, with multi-adapter fan-in reserved for high-stakes mixed-evidence briefs. [claim:clm_inf16]
- On the published unit-cost figures, GPT Researcher (about $0.40 per full multi-source run with o3-mini) is the only one of the three with a vendor-stated end-to-end run cost, whereas PaperQA2 and the Claude Agent SDK expose only component costs (per-question tool calls/searches and per-search/per-token rates respectively), so a like-for-like cost-per-source-card comparison must be modeled, not read off, for the latter two. [claim:clm_inf01]
- Dividing GPT Researcher's roughly $0.40 run cost by its 20+ aggregated sources yields an order-of-magnitude cost-per-source-card of about $0.02, the lowest modeled per-source extraction cost of the three adapters. [claim:clm_inf02]
- Because PaperQA2's design philosophy explicitly discards cost and latency to maximize accuracy and its agent loop averages more than 4 tool calls and 1.26 searches per question on a default gpt-4o model, its cost-per-claim is structurally higher than GPT Researcher's and the highest of the three adapters. [claim:clm_inf03]
- The Claude Agent SDK's cost-per-source-card is dominated by the $10-per-1,000-searches web-search fee (about $0.01 per search) plus token costs, so its per-source cost lands between GPT Researcher and PaperQA2 and is highly sensitive to the search-to-source ratio and whether Haiku 4.5 ($1/$5 per MTok) or Opus 4.8 ($5/$25 per MTok) does the extraction. [claim:clm_inf04]
- On citation accuracy and source-card provenance fidelity, PaperQA2 is the strongest adapter: it emits passage-level in-text citation keys (pqac-xxxx) tied to specific passages and is benchmarked to match or exceed PhD/postdoc experts on LitQA2, versus GPT Researcher and the bare Claude SDK which return source/URL lists without passage-level citation keys. [claim:clm_inf05]
- On source recall, GPT Researcher optimizes for breadth (20+ aggregated web sources per run) while PaperQA2 optimizes for depth and answer recall within a scientific corpus (significant agentic recall gains over a non-agentic baseline), making them complementary rather than redundant for recall. [claim:clm_inf06]
- PaperQA2's native answer object (formatted_answer, answer, question, context with passage summaries and pqac citation keys) maps onto RF's source_card and extraction_card schemas with the lowest loss of the three adapters because passage-to-citation linkage is preserved, whereas GPT Researcher's get_research_sources()/get_source_urls() requires RF to reconstruct claim-to-passage mappings that the adapter does not emit. [claim:clm_inf07]
- GPT Researcher carries the highest maintenance and breaking-change surface of the three adapters: it shipped a breaking LangChain v1 / Python 3.10+ migration (v3.3.7) and multiple feature-bearing minor releases per quarter through v3.5.0, so its RF adapter needs version pinning and a regression test on every minor bump. [claim:clm_inf08]
- The Claude Agent SDK has the cleanest governance fit under RF's gate because its costs are deterministically metered (per-search $10/1,000 with errored searches not billed, free web fetch, per-token model rates, $0.08/session-hour runtime), letting RF enforce hard budget ceilings that GPT Researcher's modeled run cost and PaperQA2's cost-agnostic loop do not natively provide. [claim:clm_inf09]
- All three adapters can be made governance-compliant on key profiles and secret scanning because each routes through configurable, key-bearing backends (GPT Researcher via OPENAI_BASE_URL/RETRIEVER env vars, PaperQA2 via LiteLLM-compatible model config, the Claude SDK via native Anthropic keys), so RF's secret-scanning gate applies uniformly and no adapter is inherently non-compliant. [claim:clm_inf10]
- RF should treat all benchmark-based recall and accuracy claims for these adapters as cost-unaware vendor self-reports and validate them on a cost-controlled basis, because the only neutral third-party benchmark in the evidence set (AstaBench, ICLR 2026) is explicitly cost-aware and concludes AI agents remain far from solving science research assistance across 57 agents. [claim:clm_inf15]

## Links

- [[claim:clm_047]]
- [[claim:clm_046]]
- [[claim:clm_051]]
- [[claim:clm_048]]
- [[claim:clm_025]]
- [[claim:clm_022]]
- [[claim:clm_061]]
- [[claim:clm_033]]
- [[claim:clm_018]]
- [[claim:clm_013]]
- [[claim:clm_015]]
- [[claim:clm_017]]
- [[claim:clm_035]]
- [[claim:clm_inf11]]
- [[claim:clm_inf12]]
- [[claim:clm_inf13]]
- [[claim:clm_inf14]]
- [[claim:clm_037]]
- [[claim:clm_038]]
- [[claim:clm_069]]
- [[claim:clm_024]]
- [[claim:clm_001]]
- [[claim:clm_067]]
- [[claim:clm_071]]
- [[claim:clm_021]]
- [[claim:clm_068]]
- [[claim:clm_012]]
- [[claim:clm_007]]
- [[claim:clm_008]]
- [[claim:clm_010]]
- [[claim:clm_066]]
- [[claim:clm_014]]
- [[claim:clm_052]]
- [[claim:clm_023]]
- [[claim:clm_019]]
- [[claim:clm_030]]
- [[claim:clm_028]]
- [[claim:clm_077]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
