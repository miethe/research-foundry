---
id: mwb_20260614_minimum_viable_architecture_for_an_evidence
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_components_schemas
target_page: meatywiki/sources/minimum_viable_architecture_for_an_evidence.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_components_schemas_agent_roles_and:
  77 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
links:
  source_cards:
  - src_20260614_rib025_00
  - src_20260614_rib025_01
  - src_20260614_rib025_02
  - src_20260614_rib025_03
  - src_20260614_rib025_04
  - src_20260614_rib025_05
  - src_20260614_rib025_06
  - src_20260614_rib025_07
  - src_20260614_rib025_08
  - src_20260614_rib025_09
  - src_20260614_rib025_10
  - src_20260614_rib025_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Minimum Viable Architecture for an Evidence-Backed Research Swarm

## Summary

Source note distilled from research run rf_run_20260614_what_components_schemas_agent_roles_and: 77 supported claim(s) across 12 source card(s).

## Key claims

- PaperQA2 matches or exceeds subject-matter-expert performance on three realistic literature research tasks even when humans have unrestricted access to the internet, search tools, and time. [claim:clm_001]
- PaperQA2 produces cited, Wikipedia-style topic summaries that are significantly more accurate than existing human-written Wikipedia articles. [claim:clm_002]
- The paper introduces LitQA2, a hard scientific-literature-research benchmark that guided PaperQA2's design and drove it to exceed human performance. [claim:clm_003]
- Applied to contradiction detection, PaperQA2 identifies an average of 2.34 +/- 1.99 contradictions per paper in a random subset of biology papers, ~70% of which are validated by human experts. [claim:clm_004]
- The authors used a rigorous human-AI comparison methodology spanning information retrieval, summarization, and contradiction detection to evaluate the agent on real-world literature search tasks. [claim:clm_005]
- The paper was first submitted 10 September 2024 with a v2 revision submitted 26 September 2024 to arXiv under cs.CL. [claim:clm_006]
- FActScore breaks a generation into a series of atomic facts and computes the percentage of those atomic facts that are supported by a reliable knowledge source. [claim:clm_007]
- An atomic fact is defined as a short sentence conveying a single piece of information, which is the unit of per-claim labeling. [claim:clm_008]
- Binary factuality judgments are inadequate for long-form text because generations mix supported and unsupported information, motivating per-claim rather than per-document scoring. [claim:clm_009]
- Support is judged relative to a given knowledge source rather than against global truth, mirroring RF's source-card-relative verification model. [claim:clm_010]
- An automated estimator using retrieval plus a strong language model approximates the human FActScore with an error rate below 2%. [claim:clm_011]
- On biography generation, ChatGPT achieved only 58% FActScore, and GPT-4/ChatGPT were found more factual than public models such as Vicuna and Alpaca. [claim:clm_012]
- The automated metric evaluated 6,500 generations from 13 recent LMs, a study that would have cost about $26K under human evaluation. [claim:clm_013]
- PaperQA2's agentic workflow is organized as three tools — Paper Search, Gather Evidence, and Generate Answer — that a language agent can invoke in any order. [claim:clm_014]
- PaperQA2's core retrieval mechanism is reranking and contextual summarization (RCS), combining document metadata-aware embeddings with LLM-based re-ranking and contextual summarization. [claim:clm_015]
- In the Gather Evidence phase, PaperQA2 creates a scored summary of each retrieved chunk in the context of the query, then uses an LLM to re-score and select the most relevant summaries. [claim:clm_016]
- PaperQA2 in-text citations reference contexts using a key pattern of the form (pqac-abcd1234). [claim:clm_017]
- The PaperQA2 answer object exposes the attributes formatted_answer, answer, question, and context (the summaries of passages found for the answer). [claim:clm_018]
- PaperQA2 defaults to OpenAI's gpt-4o-2024-11-20 model across the summary_llm, llm, and agent_llm roles. [claim:clm_019]
- PaperQA2's LLM interface is built on the lmi package, which uses litellm to support many LLM providers. [claim:clm_020]
- PaperQA2 integrates external metadata providers Semantic Scholar, Crossref, and Unpaywall, combining data from these sources (e.g., Unpaywall open-access links, Crossref bibtex, Semantic Scholar citations). [claim:clm_021]
- The spec mandates four-way claim labeling discipline: a research report may contain only supported claims mapped to source cards, labeled inference, labeled speculation, or explicitly unresolved claims. [claim:clm_022]
- The spec treats agent runs as rerunnable and disposable while the durable asset is the evidence bundle: source cards, extracted claims, claim ledger, report, reviews, and telemetry. [claim:clm_023]
- The spec splits model usage by cost: extraction, source-card creation, dedup, tagging, and formatting run on cheap/free models while synthesis, contradiction analysis, and final report construction use higher-reasoning models. [claim:clm_024]
- The spec requires governance to be enforced as a runtime gate: work-provided keys, sensitive source material, model routing, and writeback targets are checked before execution. [claim:clm_025]
- The spec maps external tools to MVP roles: GPT Researcher for web/local/hybrid cited reports, PaperQA2 for agentic RAG over papers with in-text citations, LiteLLM for cost-based routing with provider/model/tag budgets, and an Agent Council pattern for an Approve/Concern/Block voting review stage. [claim:clm_026]
- The spec prioritizes the initial MVP CLI surface as rf init, rf capture, rf plan, rf verify, and rf writeback to be implemented first. [claim:clm_027]
- FutureHouse describes PaperQA2 as the first AI agent to reach superhuman performance across a range of scientific literature search tasks. [claim:clm_028]
- PaperQA2 is reported to exceed PhD- and postdoc-level biology researchers at literature retrieval as measured on the LitQA2 benchmark, which is part of the LAB-Bench eval set released by FutureHouse in summer 2024. [claim:clm_029]
- Using the ContraCrow agent, FutureHouse reports an average of 2.34 contradicted statements per paper across a random subset of biology papers. [claim:clm_030]
- The PaperQA2 system spans three agent applications: question answering (PaperQA2), Wikipedia-style summarization (WikiCrow), and cross-literature contradiction identification (ContraCrow). [claim:clm_031]
- The announcement was published September 11, 2024, accompanied by a research paper and an open-source code release (Future-House/paper-qa). [claim:clm_032]
- The report frontmatter encodes the RF claim policy that every material claim must map to the claim ledger or be labeled inference/speculation, and records verification_status as pending. [claim:clm_033]
- Each Findings sentence terminates in a machine-parseable claim id (e.g. [claim:clm_001] through [claim:clm_005]) that ties the prose assertion to a specific ledger entry. [claim:clm_034]
- The report separates Findings, Inferences, Speculation, and Open questions into distinct sections; for this run the Inferences and Speculation sections were explicitly recorded as empty. [claim:clm_035]
- The Sources block lists source-card ids so each claim traces to a specific card, e.g. src_20260613_ccdash_36212ddb and src_20260613_paperqa2_5f264205. [claim:clm_036]
- The artifact is schema_version 0.1, type research_report, created 2026-06-13T02:11:45-04:00, demonstrating RF's MVP claim-ledger gate is implemented and producing real artifacts. [claim:clm_037]
- STORM is an LLM system that writes Wikipedia-like articles from scratch and splits long-form generation into a pre-writing (Internet research + outline) stage and a writing (full article + citations) stage. [claim:clm_038]
- The STORM engine is composed of four modules: Knowledge Curation, Outline Generation, Article Generation, and Article Polishing. [claim:clm_039]
- STORM's pre-writing discovers perspectives by surveying existing articles on similar topics and simulates a conversation between a Wikipedia writer and a topic expert grounded in Internet sources to drive follow-up questions. [claim:clm_040]
- Co-STORM adds a collaborative discourse protocol with three roles — Co-STORM LLM experts, a Moderator that surfaces information not yet used, and the Human user — to manage turns in the conversation. [claim:clm_041]
- Co-STORM maintains a dynamically updated mind map that organizes collected information into a hierarchical concept structure to build a shared conceptual space between the human user and the system. [claim:clm_042]
- Both STORM and Co-STORM are implemented modularly using DSPy, and the system supports many retrievers including YouRM, BingSearch, VectorRM, SerperRM, BraveRM, SearXNG, DuckDuckGoSearchRM, TavilySearchRM, GoogleSearch, and AzureAISearch. [claim:clm_043]
- LiteLLM integration for language and embedding models was added to knowledge-storm v1.1.0 (latest release dated Jan 23, 2025), and Co-STORM was released and integrated into the package in v1.0.0 (Sept 2024). [claim:clm_044]
- GPT Researcher's core architecture uses planner agents that generate research questions, execution agents that gather information, and a publisher that aggregates findings into a comprehensive report. [claim:clm_045]
- The pipeline runs as discrete steps: create a task-specific agent, generate objective questions, crawl for information per question, summarize and source-track each resource, then filter and aggregate into a final report. [claim:clm_046]
- The multi-agent assistant is built with LangGraph and AG2 and is explicitly inspired by the STORM paper, coordinating a team of agents from planning to publication. [claim:clm_047]
- GPT Researcher aggregates over 20 sources and generates detailed reports exceeding 2,000 words, with an average multi-agent run producing a 5-6 page report in PDF, Docx, and Markdown. [claim:clm_048]
- Deep Research mode uses recursive tree-like exploration with configurable depth and breadth, taking ~5 minutes and costing ~$0.4 per run with o3-mini at high reasoning effort; the retriever supports hybrid web (Tavily) plus MCP sources. [claim:clm_049]
- GPT Researcher is distributed under the Apache 2 license, is LLM-agnostic via custom OpenAI-compatible APIs (OPENAI_BASE_URL), and integrates LangSmith for tracing and observability. [claim:clm_050]
- Anthropic's Research system uses an orchestrator-worker multi-agent architecture where a lead agent coordinates and delegates to specialized subagents that run in parallel. [claim:clm_051]
- A multi-agent system using Claude Opus 4 as the lead and Claude Sonnet 4 subagents beat single-agent Claude Opus 4 by 90.2% on Anthropic's internal research eval. [claim:clm_052]
- Token usage alone explained 80% of the performance variance on the BrowseComp evaluation, with tool-call count and model choice as the other factors (three factors explaining 95% total). [claim:clm_053]
- Agents typically consume about 4x more tokens than chat interactions, and multi-agent systems use about 15x more tokens than chats. [claim:clm_054]
- The LeadResearcher saves its plan to Memory to persist context because exceeding the 200,000-token context window causes truncation and loss of the plan. [claim:clm_055]
- After research completes, the system passes all findings to a dedicated CitationAgent that processes the documents and report to identify specific citation locations. [claim:clm_056]
- Anthropic introduced two-level parallelism: the lead agent spins up 3-5 subagents in parallel and each subagent uses 3+ tools in parallel, cutting research time by up to 90% on complex queries. [claim:clm_057]
- STORM (Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking) is a writing system that targets generating grounded, organized long-form articles from scratch with breadth and depth comparable to Wikipedia pages. [claim:clm_058]
- STORM models the pre-writing stage as three components: discovering diverse perspectives, simulating perspective-driven conversations with a topic expert grounded on trusted Internet sources, and curating the collected information into an outline. [claim:clm_059]
- For evaluation the authors curate FreshWiki, a dataset of recent high-quality Wikipedia articles, and formulate outline assessments to evaluate the pre-writing stage. [claim:clm_060]
- Compared with an outline-driven retrieval-augmented baseline, more of STORM's articles are deemed organized (a 25% absolute increase) and broad in coverage (by 10%). [claim:clm_061]
- Expert feedback from experienced Wikipedia editors surfaced new challenges for generating grounded long articles, including source bias transfer and over-association of unrelated facts. [claim:clm_062]
- The paper was accepted to the NAACL 2024 Main Conference and first submitted to arXiv on 22 February 2024 (v1), with a v2 revision on 8 April 2024. [claim:clm_063]
- ALCE is the first benchmark for Automatic LLMs' Citation Evaluation, requiring end-to-end systems that retrieve supporting evidence and generate answers with citations. [claim:clm_064]
- ALCE develops automatic metrics along three dimensions (fluency, correctness, and citation quality) that the authors show correlate strongly with human judgements. [claim:clm_065]
- Citation quality is measured via two metrics: citation recall (whether the output is entirely supported by cited passages) and citation precision (whether any cited passages are irrelevant). [claim:clm_066]
- A key empirical finding is that on the ELI5 dataset even the best models lack complete citation support 50% of the time, indicating considerable room for improvement. [claim:clm_067]
- ALCE uses three datasets spanning a wide range of question types and corpora ranging from Wikipedia to web-scale collections; ASQA and QAMPARI use the 21M-passage Wikipedia corpus. [claim:clm_068]
- The paper motivates ALCE by noting that prior work relied on commercial search engines and human evaluation, making it hard to reproduce and compare modeling approaches; ALCE is presented as a reproducible benchmark. [claim:clm_069]
- Deep research is powered by a version of the upcoming OpenAI o3 model optimized for web browsing and data analysis, using reasoning to search, interpret, and analyze text, images, and PDFs on the internet. [claim:clm_070]
- Deep research finds, analyzes, and synthesizes hundreds of online sources into a comprehensive report at the level of a research analyst from a single prompt. [claim:clm_071]
- Deep research was trained end-to-end with reinforcement learning on hard browsing and reasoning tasks, and can cite specific sentences or passages from its sources. [claim:clm_072]
- On Humanity's Last Exam (over 3,000 questions across more than 100 subjects), the model powering deep research scores a new high of 26.6% accuracy. [claim:clm_073]
- On the GAIA benchmark, deep research reaches a new state of the art with 67.36 avg (pass@1) and 72.57 avg (cons@64), with Level 1 scores of 74.29 (pass@1) and 78.66 (cons@64), topping the external leaderboard. [claim:clm_074]
- Deep research may take 5 to 30 minutes to complete a task and notifies the user once the research is complete. [claim:clm_075]
- Per the February 10, 2026 update, deep research can connect to any MCP or app and restrict web searches to trusted sites for authenticated, industry-standard sources, with real-time progress tracking and follow-up refinement. [claim:clm_076]
- Deep research launched first for Pro users (up to 100 queries/month) on February 2, 2025, and a February 25, 2025 update made it available to all Plus users. [claim:clm_077]

## Sources

- src_20260614_rib025_00 — assafelovic/gpt-researcher: An autonomous agent that conducts deep research on any data using any LLM providers (GitHub README)
- src_20260614_rib025_01 — Language agents achieve superhuman synthesis of scientific knowledge
- src_20260614_rib025_02 — Future-House/paper-qa (PaperQA2): High accuracy RAG for answering questions from scientific documents with citations (GitHub README)
- src_20260614_rib025_03 — stanford-oval/storm: An LLM-powered knowledge curation system that researches a topic and generates a full-length report with citations (GitHub README)
- src_20260614_rib025_04 — Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models
- src_20260614_rib025_05 — How we built our multi-agent research system
- src_20260614_rib025_06 — Introducing deep research (OpenAI)
- src_20260614_rib025_07 — PaperQA2: Superhuman scientific literature search (FutureHouse research announcement)
- src_20260614_rib025_08 — Nick's Research Foundry MVP Spec
- src_20260614_rib025_09 — RF run report_draft.md (run rf_run_20260613_what_is_the_minimum_viable_architecture)
- src_20260614_rib025_10 — Enabling Large Language Models to Generate Text with Citations
- src_20260614_rib025_11 — FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
