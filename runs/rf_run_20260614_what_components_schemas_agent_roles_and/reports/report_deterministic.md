---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_components_schemas_agent_roles_and
title: What components, schemas, agent roles, and execution loop
intent_id: intent_research_20260614_what_components_schemas_agent_roles_and
evidence_bundle_id: pending
created_at: '2026-06-14T15:26:48-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

PaperQA2 matches or exceeds subject-matter-expert performance on three realistic literature research tasks even when humans have unrestricted access to the internet, search tools, and time. [claim:clm_001]
PaperQA2 produces cited, Wikipedia-style topic summaries that are significantly more accurate than existing human-written Wikipedia articles. [claim:clm_002]
The paper introduces LitQA2, a hard scientific-literature-research benchmark that guided PaperQA2's design and drove it to exceed human performance. [claim:clm_003]
Applied to contradiction detection, PaperQA2 identifies an average of 2.34 +/- 1.99 contradictions per paper in a random subset of biology papers, ~70% of which are validated by human experts. [claim:clm_004]
The authors used a rigorous human-AI comparison methodology spanning information retrieval, summarization, and contradiction detection to evaluate the agent on real-world literature search tasks. [claim:clm_005]
The paper was first submitted 10 September 2024 with a v2 revision submitted 26 September 2024 to arXiv under cs.CL. [claim:clm_006]
FActScore breaks a generation into a series of atomic facts and computes the percentage of those atomic facts that are supported by a reliable knowledge source. [claim:clm_007]
An atomic fact is defined as a short sentence conveying a single piece of information, which is the unit of per-claim labeling. [claim:clm_008]
Binary factuality judgments are inadequate for long-form text because generations mix supported and unsupported information, motivating per-claim rather than per-document scoring. [claim:clm_009]
Support is judged relative to a given knowledge source rather than against global truth, mirroring RF's source-card-relative verification model. [claim:clm_010]
An automated estimator using retrieval plus a strong language model approximates the human FActScore with an error rate below 2%. [claim:clm_011]
On biography generation, ChatGPT achieved only 58% FActScore, and GPT-4/ChatGPT were found more factual than public models such as Vicuna and Alpaca. [claim:clm_012]
The automated metric evaluated 6,500 generations from 13 recent LMs, a study that would have cost about $26K under human evaluation. [claim:clm_013]
PaperQA2's agentic workflow is organized as three tools — Paper Search, Gather Evidence, and Generate Answer — that a language agent can invoke in any order. [claim:clm_014]
PaperQA2's core retrieval mechanism is reranking and contextual summarization (RCS), combining document metadata-aware embeddings with LLM-based re-ranking and contextual summarization. [claim:clm_015]
In the Gather Evidence phase, PaperQA2 creates a scored summary of each retrieved chunk in the context of the query, then uses an LLM to re-score and select the most relevant summaries. [claim:clm_016]
PaperQA2 in-text citations reference contexts using a key pattern of the form (pqac-abcd1234). [claim:clm_017]
The PaperQA2 answer object exposes the attributes formatted_answer, answer, question, and context (the summaries of passages found for the answer). [claim:clm_018]
PaperQA2 defaults to OpenAI's gpt-4o-2024-11-20 model across the summary_llm, llm, and agent_llm roles. [claim:clm_019]
PaperQA2's LLM interface is built on the lmi package, which uses litellm to support many LLM providers. [claim:clm_020]
PaperQA2 integrates external metadata providers Semantic Scholar, Crossref, and Unpaywall, combining data from these sources (e.g., Unpaywall open-access links, Crossref bibtex, Semantic Scholar citations). [claim:clm_021]
The spec mandates four-way claim labeling discipline: a research report may contain only supported claims mapped to source cards, labeled inference, labeled speculation, or explicitly unresolved claims. [claim:clm_022]
The spec treats agent runs as rerunnable and disposable while the durable asset is the evidence bundle: source cards, extracted claims, claim ledger, report, reviews, and telemetry. [claim:clm_023]
The spec splits model usage by cost: extraction, source-card creation, dedup, tagging, and formatting run on cheap/free models while synthesis, contradiction analysis, and final report construction use higher-reasoning models. [claim:clm_024]
The spec requires governance to be enforced as a runtime gate: work-provided keys, sensitive source material, model routing, and writeback targets are checked before execution. [claim:clm_025]
The spec maps external tools to MVP roles: GPT Researcher for web/local/hybrid cited reports, PaperQA2 for agentic RAG over papers with in-text citations, LiteLLM for cost-based routing with provider/model/tag budgets, and an Agent Council pattern for an Approve/Concern/Block voting review stage. [claim:clm_026]
The spec prioritizes the initial MVP CLI surface as rf init, rf capture, rf plan, rf verify, and rf writeback to be implemented first. [claim:clm_027]
FutureHouse describes PaperQA2 as the first AI agent to reach superhuman performance across a range of scientific literature search tasks. [claim:clm_028]
PaperQA2 is reported to exceed PhD- and postdoc-level biology researchers at literature retrieval as measured on the LitQA2 benchmark, which is part of the LAB-Bench eval set released by FutureHouse in summer 2024. [claim:clm_029]
Using the ContraCrow agent, FutureHouse reports an average of 2.34 contradicted statements per paper across a random subset of biology papers. [claim:clm_030]
The PaperQA2 system spans three agent applications: question answering (PaperQA2), Wikipedia-style summarization (WikiCrow), and cross-literature contradiction identification (ContraCrow). [claim:clm_031]
The announcement was published September 11, 2024, accompanied by a research paper and an open-source code release (Future-House/paper-qa). [claim:clm_032]
The report frontmatter encodes the RF claim policy that every material claim must map to the claim ledger or be labeled inference/speculation, and records verification_status as pending. [claim:clm_033]
Each Findings sentence terminates in a machine-parseable claim id (e.g. [claim:clm_001] through [claim:clm_005]) that ties the prose assertion to a specific ledger entry. [claim:clm_034]
The report separates Findings, Inferences, Speculation, and Open questions into distinct sections; for this run the Inferences and Speculation sections were explicitly recorded as empty. [claim:clm_035]
The Sources block lists source-card ids so each claim traces to a specific card, e.g. src_20260613_ccdash_36212ddb and src_20260613_paperqa2_5f264205. [claim:clm_036]
The artifact is schema_version 0.1, type research_report, created 2026-06-13T02:11:45-04:00, demonstrating RF's MVP claim-ledger gate is implemented and producing real artifacts. [claim:clm_037]
STORM is an LLM system that writes Wikipedia-like articles from scratch and splits long-form generation into a pre-writing (Internet research + outline) stage and a writing (full article + citations) stage. [claim:clm_038]
The STORM engine is composed of four modules: Knowledge Curation, Outline Generation, Article Generation, and Article Polishing. [claim:clm_039]
STORM's pre-writing discovers perspectives by surveying existing articles on similar topics and simulates a conversation between a Wikipedia writer and a topic expert grounded in Internet sources to drive follow-up questions. [claim:clm_040]
Co-STORM adds a collaborative discourse protocol with three roles — Co-STORM LLM experts, a Moderator that surfaces information not yet used, and the Human user — to manage turns in the conversation. [claim:clm_041]
Co-STORM maintains a dynamically updated mind map that organizes collected information into a hierarchical concept structure to build a shared conceptual space between the human user and the system. [claim:clm_042]
Both STORM and Co-STORM are implemented modularly using DSPy, and the system supports many retrievers including YouRM, BingSearch, VectorRM, SerperRM, BraveRM, SearXNG, DuckDuckGoSearchRM, TavilySearchRM, GoogleSearch, and AzureAISearch. [claim:clm_043]
LiteLLM integration for language and embedding models was added to knowledge-storm v1.1.0 (latest release dated Jan 23, 2025), and Co-STORM was released and integrated into the package in v1.0.0 (Sept 2024). [claim:clm_044]
GPT Researcher's core architecture uses planner agents that generate research questions, execution agents that gather information, and a publisher that aggregates findings into a comprehensive report. [claim:clm_045]
The pipeline runs as discrete steps: create a task-specific agent, generate objective questions, crawl for information per question, summarize and source-track each resource, then filter and aggregate into a final report. [claim:clm_046]
The multi-agent assistant is built with LangGraph and AG2 and is explicitly inspired by the STORM paper, coordinating a team of agents from planning to publication. [claim:clm_047]
GPT Researcher aggregates over 20 sources and generates detailed reports exceeding 2,000 words, with an average multi-agent run producing a 5-6 page report in PDF, Docx, and Markdown. [claim:clm_048]
Deep Research mode uses recursive tree-like exploration with configurable depth and breadth, taking ~5 minutes and costing ~$0.4 per run with o3-mini at high reasoning effort; the retriever supports hybrid web (Tavily) plus MCP sources. [claim:clm_049]
GPT Researcher is distributed under the Apache 2 license, is LLM-agnostic via custom OpenAI-compatible APIs (OPENAI_BASE_URL), and integrates LangSmith for tracing and observability. [claim:clm_050]
Anthropic's Research system uses an orchestrator-worker multi-agent architecture where a lead agent coordinates and delegates to specialized subagents that run in parallel. [claim:clm_051]
A multi-agent system using Claude Opus 4 as the lead and Claude Sonnet 4 subagents beat single-agent Claude Opus 4 by 90.2% on Anthropic's internal research eval. [claim:clm_052]
Token usage alone explained 80% of the performance variance on the BrowseComp evaluation, with tool-call count and model choice as the other factors (three factors explaining 95% total). [claim:clm_053]
Agents typically consume about 4x more tokens than chat interactions, and multi-agent systems use about 15x more tokens than chats. [claim:clm_054]
The LeadResearcher saves its plan to Memory to persist context because exceeding the 200,000-token context window causes truncation and loss of the plan. [claim:clm_055]
After research completes, the system passes all findings to a dedicated CitationAgent that processes the documents and report to identify specific citation locations. [claim:clm_056]
Anthropic introduced two-level parallelism: the lead agent spins up 3-5 subagents in parallel and each subagent uses 3+ tools in parallel, cutting research time by up to 90% on complex queries. [claim:clm_057]
STORM (Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking) is a writing system that targets generating grounded, organized long-form articles from scratch with breadth and depth comparable to Wikipedia pages. [claim:clm_058]
STORM models the pre-writing stage as three components: discovering diverse perspectives, simulating perspective-driven conversations with a topic expert grounded on trusted Internet sources, and curating the collected information into an outline. [claim:clm_059]
For evaluation the authors curate FreshWiki, a dataset of recent high-quality Wikipedia articles, and formulate outline assessments to evaluate the pre-writing stage. [claim:clm_060]
Compared with an outline-driven retrieval-augmented baseline, more of STORM's articles are deemed organized (a 25% absolute increase) and broad in coverage (by 10%). [claim:clm_061]
Expert feedback from experienced Wikipedia editors surfaced new challenges for generating grounded long articles, including source bias transfer and over-association of unrelated facts. [claim:clm_062]
The paper was accepted to the NAACL 2024 Main Conference and first submitted to arXiv on 22 February 2024 (v1), with a v2 revision on 8 April 2024. [claim:clm_063]
ALCE is the first benchmark for Automatic LLMs' Citation Evaluation, requiring end-to-end systems that retrieve supporting evidence and generate answers with citations. [claim:clm_064]
ALCE develops automatic metrics along three dimensions (fluency, correctness, and citation quality) that the authors show correlate strongly with human judgements. [claim:clm_065]
Citation quality is measured via two metrics: citation recall (whether the output is entirely supported by cited passages) and citation precision (whether any cited passages are irrelevant). [claim:clm_066]
A key empirical finding is that on the ELI5 dataset even the best models lack complete citation support 50% of the time, indicating considerable room for improvement. [claim:clm_067]
ALCE uses three datasets spanning a wide range of question types and corpora ranging from Wikipedia to web-scale collections; ASQA and QAMPARI use the 21M-passage Wikipedia corpus. [claim:clm_068]
The paper motivates ALCE by noting that prior work relied on commercial search engines and human evaluation, making it hard to reproduce and compare modeling approaches; ALCE is presented as a reproducible benchmark. [claim:clm_069]
Deep research is powered by a version of the upcoming OpenAI o3 model optimized for web browsing and data analysis, using reasoning to search, interpret, and analyze text, images, and PDFs on the internet. [claim:clm_070]
Deep research finds, analyzes, and synthesizes hundreds of online sources into a comprehensive report at the level of a research analyst from a single prompt. [claim:clm_071]
Deep research was trained end-to-end with reinforcement learning on hard browsing and reasoning tasks, and can cite specific sentences or passages from its sources. [claim:clm_072]
On Humanity's Last Exam (over 3,000 questions across more than 100 subjects), the model powering deep research scores a new high of 26.6% accuracy. [claim:clm_073]
On the GAIA benchmark, deep research reaches a new state of the art with 67.36 avg (pass@1) and 72.57 avg (cons@64), with Level 1 scores of 74.29 (pass@1) and 78.66 (cons@64), topping the external leaderboard. [claim:clm_074]
Deep research may take 5 to 30 minutes to complete a task and notifies the user once the research is complete. [claim:clm_075]
Per the February 10, 2026 update, deep research can connect to any MCP or app and restrict web searches to trusted sites for authenticated, industry-standard sources, with real-time progress tracking and follow-up refinement. [claim:clm_076]
Deep research launched first for Pro users (up to 100 queries/month) on February 2, 2025, and a February 25, 2025 update made it available to all Plus users. [claim:clm_077]

## Inferences

**Inference:** Across all five comparable systems (GPT Researcher, PaperQA2, STORM/Co-STORM, Anthropic Research, OpenAI Deep Research), a planner/decomposer role, one or more retrieval-execution roles, and a synthesis/aggregation role are universal, so RF's researcher and synthesizer roles are MUST-have while a standalone red-team role appears in none of them and is therefore CAN-defer for MVP. [claim:clm_inf01]
**Inference:** A dedicated post-research citation/attribution step is a MUST-have rather than a nice-to-have, because Anthropic runs a separate CitationAgent after the research loop and PaperQA2 embeds citation keys (pqac-abcd1234) into every answer, converging on the same pattern RF encodes as its claim ledger plus [claim:clm_NNN] markers. [claim:clm_inf02]
**Inference:** RF's cheap-extract/expensive-synthesize split is validated by prior art rather than novel: it generalizes Anthropic's Opus-4-lead / Sonnet-4-subagent tiering and PaperQA2's single-tier gpt-4o-2024-11-20 default, and the Anthropic finding that an Opus+Sonnet split beat single-agent Opus by 90.2% is direct evidence that role-based model tiering improves quality per dollar. [claim:clm_inf03]
**Inference:** The single largest cost driver for any RF deep run is token volume, not model selection or orchestration overhead, because Anthropic found token usage alone explained 80% of BrowseComp performance variance and that multi-agent systems consume ~15x the tokens of a chat, implying RF's per-run budget gates (LiteLLM provider/model/tag budgets) are the correct primary cost-control lever. [claim:clm_inf04]
**Inference:** RF's choice to make the claim ledger the authority (every material claim maps to a source card or is labeled inference/speculation) is the strongest traceability discipline among the surveyed systems: GPT Researcher only source-tracks summaries, STORM cites at the article level, and even Anthropic and PaperQA2 attach citations to passages but do not enforce a four-way support/inference/speculation/unresolved partition. [claim:clm_inf05]
**Inference:** An evidence/source-card schema, a claim-ledger schema, and a report schema are the three MUST-have RF schemas, because every surveyed system materializes evidence units (chunks/contexts/sources), an attribution mapping (citation keys or a citation pass), and a final report, whereas RF's writeback targets (MeatyWiki/SkillMeat/CCDash) have no analog in any comparable system and are therefore safely CAN-defer post-MVP. [claim:clm_inf06]
**Inference:** RF's biggest unjustified gap relative to prior art is the absence of an explicit context-persistence/memory mechanism in the MVP: Anthropic's LeadResearcher must save its plan to Memory because exceeding the 200,000-token window truncates and loses it, so a deep RF swarm that decomposes a query across many source cards will hit the same truncation failure mode unless a plan/state persistence step is treated as MUST-have. [claim:clm_inf07]
**Inference:** Parallel fan-out of subagents should be deferred past RF's first MVP even though it is the highest-leverage performance feature, because Anthropic's two-level parallelism cut research time up to 90% but multi-agent runs cost ~15x chat tokens, so a sequential or low-fan-out loop is the right MVP default and parallelism is a CAN-defer optimization gated behind budget enforcement. [claim:clm_inf08]
**Inference:** RF's verification gate should adopt FActScore-style atomic-fact decomposition and ALCE-style citation precision/recall as its concrete claim-verification metrics, because both define support relative to a given knowledge source (not global truth), which is exactly RF's source-card-relative model, and ALCE shows even the best models lack complete citation support 50% of the time on ELI5 — quantifying the failure RF's ledger is designed to catch. [claim:clm_inf09]
**Inference:** RF should reuse PaperQA2 and GPT Researcher as execution components rather than reimplement their loops, because PaperQA2 already provides agentic RAG with in-text citations over papers and GPT Researcher already provides cited web/hybrid reports, both are LiteLLM/OpenAI-compatible and Apache-2-or-open, matching RF's LiteLLM routing principle exactly. [claim:clm_inf10]
**Inference:** The MUST-have RF execution loop is capture-sources -> extract-claims-into-cards -> map-claims-to-ledger -> synthesize-report -> verify-gate, which is the common denominator of GPT Researcher's plan/crawl/summarize/aggregate and PaperQA2's search/gather/generate; the rf init and rf writeback commands are loop-adjacent and CAN-defer relative to capture/plan/verify. [claim:clm_inf11]
**Inference:** RF's Agent Council (Approve/Concern/Block voting) review stage is a justified divergence from prior art that none of the five systems implements, and it is best positioned as the human-in-the-loop analog of Co-STORM's Moderator role and Anthropic's CitationAgent check — making it MUST-have for governed/work output but CAN-defer for low-stakes personal runs. [claim:clm_inf12]
**Inference:** A functional RF swarm can be demonstrated with four concrete metrics — claim coverage (percent of material report sentences terminating in a claim id, target 100%), source-card support rate (percent of supported claims with at least one resolving source card), citation precision/recall on a held-out sample, and cost-per-run under the LiteLLM budget — and the existing 0.1 artifact already proves claim coverage and support-rate are mechanically enforceable. [claim:clm_inf13]
**Inference:** On a quality-per-dollar ranking for RF's likely workloads, PaperQA2 is the best fit for scientific-paper questions (superhuman LitQA2 retrieval, native citation keys), GPT Researcher is the best fit for open-web/hybrid reports at ~$0.4/run, and an Anthropic-style Opus+Sonnet orchestration is the best fit only for high-stakes synthesis where the ~15x token premium is justified by the 90.2% quality lift. [claim:clm_inf14]

## Speculation

**Speculation:** As MCP-connected deep-research products (OpenAI deep research connecting to any MCP/app, GPT Researcher's hybrid Tavily+MCP retriever) become the default, RF's durable evidence-bundle and claim-ledger will likely shift from being the system that generates research to being the governance/audit layer that wraps externally-run MCP research swarms. [claim:clm_spec01]
**Speculation:** RF's claim ledger will plausibly need a contradiction-tracking field promoted to MUST-have sooner than its spec assumes, because PaperQA2/ContraCrow find an average of 2.34 contradictions per biology paper and STORM editors flagged over-association of unrelated facts, suggesting cross-source contradiction is common enough that an MVP without it will surface unflagged conflicts. [claim:clm_spec02]
**Speculation:** If RF enforces atomic-fact-level verification on every material claim, its dominant MVP cost will migrate from synthesis to verification, because FActScore's automated estimator approximates human scoring at <2% error but still required scoring 6,500 generations (a study that would have cost ~$26K under human evaluation), implying per-claim verification at scale is the line item most likely to break a naive per-run budget. [claim:clm_spec03]

## Open questions

- None recorded.

## Sources

- src_20260614_rib025_01: Language agents achieve superhuman synthesis of scientific knowledge
- src_20260614_rib025_11: FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation
- src_20260614_rib025_02: Future-House/paper-qa (PaperQA2): High accuracy RAG for answering questions from scientific documents with citations (GitHub README)
- src_20260614_rib025_08: Nick's Research Foundry MVP Spec
- src_20260614_rib025_07: PaperQA2: Superhuman scientific literature search (FutureHouse research announcement)
- src_20260614_rib025_09: RF run report_draft.md (run rf_run_20260613_what_is_the_minimum_viable_architecture)
- src_20260614_rib025_03: stanford-oval/storm: An LLM-powered knowledge curation system that researches a topic and generates a full-length report with citations (GitHub README)
- src_20260614_rib025_00: assafelovic/gpt-researcher: An autonomous agent that conducts deep research on any data using any LLM providers (GitHub README)
- src_20260614_rib025_05: How we built our multi-agent research system
- src_20260614_rib025_04: Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models
- src_20260614_rib025_10: Enabling Large Language Models to Generate Text with Citations
- src_20260614_rib025_06: Introducing deep research (OpenAI)
