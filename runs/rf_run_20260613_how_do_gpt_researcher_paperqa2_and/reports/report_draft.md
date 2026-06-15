---
schema_version: '0.1'
type: research_report
report_id: report_20260613_how_do_gpt_researcher_paperqa2_and
title: GPT Researcher vs PaperQA2 vs Claude Agent SDK as Research Foundry discovery/extraction adapters
intent_id: intent_research_20260613_how_do_gpt_researcher_paperqa2_and
evidence_bundle_id: pending
created_at: '2026-06-13T23:57:31-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

This memo evaluates three candidate discovery/extraction adapters for Research Foundry (RF): GPT Researcher, PaperQA2, and the Claude Agent SDK.

GPT Researcher aggregates more than 20 sources per research run to form objective conclusions. [claim:clm_046]
GPT Researcher's Deep Research mode takes about 5 minutes and costs about $0.40 per run using o3-mini at high reasoning effort. [claim:clm_047]
**Inference:** On the published unit-cost figures, GPT Researcher (about $0.40 per full multi-source run with o3-mini) is the only one of the three with a vendor-stated end-to-end run cost, whereas PaperQA2 and the Claude Agent SDK expose only component costs (per-question tool calls/searches and per-search/per-token rates respectively), so a like-for-like cost-per-source-card comparison must be modeled, not read off, for the latter two. [claim:clm_inf01]
PaperQA2 is a frontier language model agent optimized for improved factuality that matches or exceeds subject-matter-expert performance on three realistic literature research tasks. [claim:clm_001]
**Inference:** On citation accuracy and source-card provenance fidelity, PaperQA2 is the strongest adapter: it emits passage-level in-text citation keys (pqac-xxxx) tied to specific passages and is benchmarked to match or exceed PhD/postdoc experts on LitQA2, versus GPT Researcher and the bare Claude SDK which return source/URL lists without passage-level citation keys. [claim:clm_inf05]
**Inference:** The Claude Agent SDK has the cleanest governance fit under RF's gate because its costs are deterministically metered (per-search $10/1,000 with errored searches not billed, free web fetch, per-token model rates, $0.08/session-hour runtime), letting RF enforce hard budget ceilings that GPT Researcher's modeled run cost and PaperQA2's cost-agnostic loop do not natively provide. [claim:clm_inf09]
**Inference:** The decision rule reduces to a three-way split keyed on domain and budget: web/general + low budget to GPT Researcher, scientific + accuracy-critical to PaperQA2, and governed/budget-capped or RF-native to the Claude Agent SDK, with multi-adapter fan-in reserved for high-stakes mixed-evidence briefs. [claim:clm_inf16]

## Adapter comparison matrix

The table below scores each adapter against the dimensions RF weighs when selecting an extraction backbone.

| Dimension | GPT Researcher | PaperQA2 | Claude Agent SDK | Evidence |
|---|---|---|---|---|
| Source recall (breadth) | Aggregates more than 20 sources per research run to form objective conclusions. | — | — | [claim:clm_046] |
| Source recall (depth) | — | Delivered significant improvements in both accuracy and answer recall over a non-agentic baseline. | — | [claim:clm_035] |
| Recall axes (complementarity) | GPT Researcher optimizes for breadth (20+ aggregated web sources per run) while PaperQA2 optimizes for depth and answer recall within a scientific corpus, making them complementary rather than redundant for recall. | (same row) | — | **Inference:** [claim:clm_inf06] |
| Citation accuracy | Returns source/URL lists without passage-level citation keys. | Emits passage-level citation keys (pqac-xxxx) and is benchmarked to match or exceed PhD/postdoc experts on LitQA2; strongest adapter on citation accuracy and provenance fidelity. | Returns source/URL lists without passage-level citation keys. | **Inference:** [claim:clm_inf05] |
| Cost-per-source-card | Roughly $0.40 run cost divided across 20+ sources yields an order-of-magnitude cost-per-source-card of about $0.02, the lowest modeled per-source extraction cost of the three adapters. | (highest; cost-agnostic loop) | Dominated by the $10-per-1,000-searches web-search fee (about $0.01 per search) plus token costs, landing between GPT Researcher and PaperQA2 and highly sensitive to the search-to-source ratio and to Haiku 4.5 vs Opus 4.8. | **Inference:** [claim:clm_inf02] |
| Cost-per-source-card (SDK detail) | — | — | Search fee about $0.01 per search plus token costs, sensitive to whether Haiku 4.5 ($1/$5 per MTok) or Opus 4.8 ($5/$25 per MTok) does the extraction. | **Inference:** [claim:clm_inf04] |
| Cost-per-claim | Single ~$0.40 run baseline (lowest). | Structurally higher than GPT Researcher's and the highest of the three adapters, because its loop averages more than 4 tool calls and 1.26 searches per question on a default gpt-4o model with cost deliberately discarded. | (between the two) | **Inference:** [claim:clm_inf03] |
| Governance fit | Modeled run cost does not natively provide a hard budget ceiling. | Cost-agnostic loop does not natively provide a hard budget ceiling. | Cleanest governance fit: deterministically metered costs let RF enforce hard budget ceilings. | **Inference:** [claim:clm_inf09] |
| Key-profile / secret-scanning compliance | Routes through OPENAI_BASE_URL/RETRIEVER env vars; compliant. | Routes through LiteLLM-compatible model config; compliant. | Routes through native Anthropic keys; compliant. No adapter is inherently non-compliant. | **Inference:** [claim:clm_inf10] |
| RF schema-mapping loss | get_research_sources()/get_source_urls() requires RF to reconstruct claim-to-passage mappings the adapter does not emit (lossier). | Native answer object maps onto RF's source_card and extraction_card schemas with the lowest loss because passage-to-citation linkage is preserved. | (source/URL lists; no passage keys) | **Inference:** [claim:clm_inf07] |
| Maintenance / breaking-change surface | Highest of the three: shipped a breaking LangChain v1 / Python 3.10+ migration (v3.3.7) and multiple feature-bearing minor releases per quarter through v3.5.0, needing version pinning and a regression test on every minor bump. | — | — | **Inference:** [claim:clm_inf08] |

## Supporting unit-cost evidence

| Cost input | Value | Evidence |
|---|---|---|
| GPT Researcher Deep Research run | About 5 minutes and about $0.40 per run using o3-mini at high reasoning effort. | [claim:clm_047] |
| GPT Researcher sources per run | More than 20 sources aggregated per research run. | [claim:clm_046] |
| Claude API web search | Billed at $10 per 1,000 searches plus standard token costs for search-generated content. | [claim:clm_013] |
| Claude API web search billing unit | Each web search counts as one billable use regardless of result count, and searches that error out are not billed. | [claim:clm_014] |
| Claude API web fetch | Carries no additional charge beyond standard token costs for the fetched content. | [claim:clm_015] |
| Claude model pricing | Sonnet 4.6 is $3/MTok input, $15/MTok output, $0.30/MTok cache read; Haiku 4.5 is the cheapest tier at $1/MTok input, $5/MTok output; Opus 4.8 is $5/MTok input, $25/MTok output. | [claim:clm_017] |
| Claude Managed Agents runtime | Session runtime is billed at $0.08 per session-hour, metered only while the session status is 'running'. | [claim:clm_018] |
| Claude Managed Agents billing dimensions | Billed on tokens at standard Model pricing rates and session runtime, with web search inside a session still incurring the standard $10 per 1,000 searches. | [claim:clm_019] |
| PaperQA2 tool calls per question | On average the PaperQA2 agent makes more than 4 tool calls per question. | [claim:clm_037] |
| PaperQA2 searches per question | The agent averages 1.26 searches per question across benchmark runs. | [claim:clm_038] |
| PaperQA2 default model | By default PaperQA2 uses OpenAI's gpt-4o-2024-11-20 model for the summary_llm, llm, and agent_llm roles. | [claim:clm_024] |
| PaperQA2 cost posture | PaperQA2's design philosophy explicitly de-prioritizes cost and latency to maximize accuracy as the goal for a best-in-class RAG system. | [claim:clm_033] |

## Capability and provenance derivation

This section derives the recall, citation, and provenance findings from the underlying capability evidence.

PaperQA2 is a package for high-accuracy retrieval-augmented generation (RAG) over PDFs, text files, Microsoft Office documents, and source code files, with a focus on scientific literature. [claim:clm_020]
PaperQA2 achieves higher accuracy than PhD- and postdoc-level biology researchers at retrieving information from the scientific literature, as measured using LitQA2, part of the LAB-Bench eval set. [claim:clm_061]
PaperQA2 was evaluated on LitQA2, a set of 200 expert-crafted multiple-choice questions. [claim:clm_034]
The authors introduce LitQA2, a hard scientific-literature-research benchmark that guided PaperQA2's design and led it to exceed human performance. [claim:clm_004]
PaperQA2 emits in-text citations that reference specific source passages using keys formatted like (pqac-abcd1234). [claim:clm_022]
A PaperQA2 answer object exposes formatted_answer, answer (the answer alone), question, and context (summaries of the passages found for the answer). [claim:clm_021]
PaperQA2 relies on external paper search and metadata services including Semantic Scholar, Crossref, and Unpaywall. [claim:clm_025]
The citation traversal tool is invoked on only about 46% of questions, indicating selective, query-dependent tool use within the agent loop. [claim:clm_036]
**Inference:** PaperQA2's native answer object (formatted_answer, answer, question, context with passage summaries and pqac citation keys) maps onto RF's source_card and extraction_card schemas with the lowest loss of the three adapters because passage-to-citation linkage is preserved, whereas GPT Researcher's get_research_sources()/get_source_urls() requires RF to reconstruct claim-to-passage mappings that the adapter does not emit. [claim:clm_inf07]

GPT Researcher's get_research_sources() method retrieves a list of research sources, including their title, content, and images fields. [claim:clm_067]
GPT Researcher's get_source_urls() method returns the list of URLs that were used to gather information for the research. [claim:clm_071]
GPT Researcher's get_costs() method returns the number of tokens consumed during the research process. [claim:clm_069]
GPT Researcher is LLM-agnostic and can target custom OpenAI-compatible APIs by setting the OPENAI_BASE_URL environment variable. [claim:clm_052]
The retriever is configurable to run a hybrid of web search (Tavily default) and MCP retrievers via the RETRIEVER environment variable. [claim:clm_051]
GPT Researcher is distributed under the Apache 2 license, supporting self-hosted use. [claim:clm_048]
GPT Researcher v3.5.0 added an OpenAlex academic retriever and a ModelsLab image-generation provider. [claim:clm_008]
v3.3.7 was a breaking release that migrated to LangChain v1 and raised the minimum Python version, dropping Python 3.9 support. [claim:clm_012]

PaperQA2 provides a customization interface with default support for all LiteLLM-compatible models. [claim:clm_023]
Claude Managed Agents is billed on two dimensions — tokens at standard Model pricing rates and session runtime — with web search inside a session still incurring the standard $10 per 1,000 searches. [claim:clm_019]
**Inference:** All three adapters can be made governance-compliant on key profiles and secret scanning because each routes through configurable, key-bearing backends (GPT Researcher via OPENAI_BASE_URL/RETRIEVER env vars, PaperQA2 via LiteLLM-compatible model config, the Claude SDK via native Anthropic keys), so RF's secret-scanning gate applies uniformly and no adapter is inherently non-compliant. [claim:clm_inf10]

## Benchmark-validity caveat

AstaBench is a scientific-research agent benchmark suite published as a conference paper at ICLR 2026 and submitted to arXiv on 2025-10-24. [claim:clm_027]
The AstaBench headline finding is that despite progress on individual aspects, AI agents remain far from solving science research assistance, based on evaluating 57 agents across 22 agent classes. [claim:clm_028]
The AstaBench paper explicitly motivates cost-aware evaluation, faulting prior benchmarks for not accounting for confounding variables such as model cost and tool access. [claim:clm_030]
FutureHouse reports that Crow, Falcon, and Owl were benchmarked and outperform major frontier search models on retrieval precision and accuracy. [claim:clm_077]
**Inference:** RF should treat all benchmark-based recall and accuracy claims for these adapters as cost-unaware vendor self-reports and validate them on a cost-controlled basis, because the only neutral third-party benchmark in the evidence set (AstaBench, ICLR 2026) is explicitly cost-aware and concludes AI agents remain far from solving science research assistance across 57 agents. [claim:clm_inf15]

## Recommendations and decision rules

**Inference:** For web/current-events and general-domain briefs on a low budget tier, rf swarm run should select GPT Researcher as the extraction backbone because it is the cheapest modeled run (~$0.40), breadth-first (20+ web sources), and natively hybrid (Tavily + MCP) and self-hostable under Apache-2. [claim:clm_inf11]
**Inference:** For scientific-literature briefs that demand citation accuracy and passage-level provenance, rf swarm run should select PaperQA2 as the extraction backbone, accepting its higher cost-per-claim, because it targets scholarly corpora (Semantic Scholar/Crossref/Unpaywall), emits passage-level citations, and is benchmarked to match or exceed domain experts on LitQA2. [claim:clm_inf12]
**Inference:** For high-governance or budget-capped briefs that require deterministic spend and tight RF integration, rf swarm run should select the Claude Agent SDK adapter because its per-search and per-session-hour metering plus free web fetch let RF enforce hard cost ceilings, with Haiku 4.5 for cheap extraction and Opus 4.8 reserved for synthesis. [claim:clm_inf13]
**Inference:** A multi-adapter fan-in (GPT Researcher for web breadth plus PaperQA2 for scholarly depth) is worth the extra cost only for high-stakes briefs that mix current-web and peer-reviewed evidence, since the two adapters maximize different recall axes and their combined cost still falls below an unbounded accuracy-maximized PaperQA2-only sweep for broad web coverage. [claim:clm_inf14]
**Inference:** The decision rule reduces to a three-way split keyed on domain and budget: web/general + low budget to GPT Researcher, scientific + accuracy-critical to PaperQA2, and governed/budget-capped or RF-native to the Claude Agent SDK, with multi-adapter fan-in reserved for high-stakes mixed-evidence briefs. [claim:clm_inf16]

The condensed routing rule:

| Query type | Budget tier | Selected adapter | Evidence |
|---|---|---|---|
| Web / current-events / general domain | Low | GPT Researcher | **Inference:** [claim:clm_inf11] |
| Scientific literature, accuracy/provenance-critical | Higher (accepts elevated cost-per-claim) | PaperQA2 | **Inference:** [claim:clm_inf12] |
| High-governance or budget-capped, RF-native | Capped / deterministic | Claude Agent SDK | **Inference:** [claim:clm_inf13] |
| Mixed current-web + peer-reviewed, high-stakes | High | GPT Researcher + PaperQA2 fan-in | **Inference:** [claim:clm_inf14] |

### Adapter-stability hedge

Because GPT Researcher already added an OpenAlex academic retriever in v3.5.0, it is likely to encroach on PaperQA2's scientific-literature niche within the next few release cycles, narrowing PaperQA2's domain advantage to citation-accuracy-critical work. **Speculation:** [claim:clm_spec01]
FutureHouse's commercial spinout to Edison Scientific and its history of unmet rate-limit demand signal a likely future tightening or paywalling of PaperQA2-adjacent hosted access, so RF should prefer the self-hosted open-source PaperQA2 package over any hosted FutureHouse API to insulate the adapter from pricing and rate-limit volatility. **Speculation:** [claim:clm_spec02]

## Open questions

- Should RF treat GPT Researcher's get_costs() (tokens, not dollars) as sufficient for the governance gate, or normalize it to a dollar estimate at ingestion?
- At what search-to-source ratio does the Claude Agent SDK's modeled cost-per-source-card cross GPT Researcher's or PaperQA2's?
- Does the OpenAlex retriever added in GPT Researcher v3.5.0 close enough of PaperQA2's scholarly-corpus gap to change the scientific-brief routing rule?

## Sources

- src_20260613_rib010_04: Language agents achieve superhuman synthesis of scientific knowledge
- src_20260613_rib010_01: Releases - assafelovic/gpt-researcher
- src_20260613_rib010_06: Pricing - Claude API Docs
- src_20260613_rib010_03: Future-House/paper-qa (PaperQA2): high-accuracy RAG over scientific literature
- src_20260613_rib010_10: AstaBench: Rigorous Benchmarking of AI Agents with a Scientific Research Suite
- src_20260613_rib010_09: Engineering Blog: Journey to superhuman performance on scientific tasks
- src_20260613_rib010_11: Announcing Edison Scientific
- src_20260613_rib010_00: assafelovic/gpt-researcher: An autonomous agent that conducts deep research on any data using any LLM providers
- src_20260613_rib010_07: Tailored Research - GPT Researcher Documentation
- src_20260613_rib010_05: PaperQA2: Superhuman scientific literature search
- src_20260613_rib010_02: PIP Package - GPT Researcher Documentation
- src_20260613_rib010_08: Launching the FutureHouse Platform: AI Agents for Scientific Discovery
