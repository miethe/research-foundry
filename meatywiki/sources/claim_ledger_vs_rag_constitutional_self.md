---
id: mwb_20260614_claim_ledger_vs_rag_constitutional_self
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_does_the
target_page: meatywiki/sources/claim_ledger_vs_rag_constitutional_self.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_does_the_empirical_literature_say:
  75 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_rib002_00
  - src_20260614_rib002_01
  - src_20260614_rib002_02
  - src_20260614_rib002_03
  - src_20260614_rib002_04
  - src_20260614_rib002_05
  - src_20260614_rib002_06
  - src_20260614_rib002_07
  - src_20260614_rib002_08
  - src_20260614_rib002_09
  - src_20260614_rib002_10
  - src_20260614_rib002_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Claim-ledger vs RAG/constitutional/self-consistency mitigation

## Summary

Source note distilled from research run rf_run_20260614_what_does_the_empirical_literature_say: 75 supported claim(s) across 12 source card(s).

## Key claims

- RARR (Retrofit Attribution using Research and Revision) automatically finds attribution for the output of any text generation model and post-edits that output to fix unsupported content while preserving the original as much as possible. [claim:clm_001]
- Applied to several state-of-the-art LMs across diverse generation tasks, RARR significantly improves attribution while preserving the original output far more than prior edit models. [claim:clm_002]
- The Research stage begins with comprehensive question generation (CQGen), producing a sequence of questions covering all aspects of the passage to be verified. [claim:clm_003]
- For each generated query, RARR uses standard web search (Google Search) to retrieve K=5 web pages ranked by relevance as candidate evidence. [claim:clm_004]
- An agreement model decides whether the (partially edited) passage and the retrieved evidence imply the same answer to a query; the edit model is invoked only on disagreement and minimally alters the passage to agree with the evidence. [claim:clm_005]
- RARR is model-agnostic and post-hoc: it retrofits attribution after generation without modifying the underlying LM, requiring only a handful of training examples, a large language model, and standard web search. [claim:clm_006]
- PaperQA2 emits passage-level in-text citation keys formatted like (pqac-abcd1234), each tied to a specific retrieved passage. [claim:clm_007]
- The answer object exposes a formatted_answer with integrated citations alongside a context attribute holding passage summaries. [claim:clm_008]
- Phase 1 (Paper Search) retrieves candidate papers via an LLM-generated keyword query, then chunks, embeds, and adds them to state. [claim:clm_009]
- Phase 2 (Gather Evidence) embedding-ranks chunks, builds scored contextual summaries, then uses an LLM to re-score and select the most relevant summaries. [claim:clm_010]
- PaperQA2 is documented as achieving superhuman performance on scientific-literature tasks including question answering, summarization, and contradiction detection. [claim:clm_011]
- PaperQA2 is Apache-2.0 licensed and self-hostable, with local model backends such as ollama and llamafile supported. [claim:clm_012]
- The leaderboard is scored using HHEM-2.3, Vectara's commercial hallucination evaluation model, with an open-source variant HHEM-2.1-Open available on Hugging Face and Kaggle. [claim:clm_013]
- The leaderboard is computed over a dataset of more than 7,700 articles and was last updated on May 11, 2026. [claim:clm_014]
- The leaderboard measures intrinsic hallucination in document summarization: each LLM is given documents and asked to summarize them, reflecting RAG-style grounded synthesis rather than single-turn QA. [claim:clm_015]
- The primary metric is the factual consistency rate (the rate of summaries with no hallucinations), the inverse of the hallucination rate. [claim:clm_016]
- Answer Rate is reported as a separate column capturing how often a model refuses to respond to the summarization prompt versus producing a summary. [claim:clm_017]
- As of the May 2026 snapshot, the lowest hallucination rates were Antgroup Finix S1 32B at 1.8%, OpenAI GPT-5.4-nano (2026-03-17) at 3.1%, and Google Gemini 2.5 Flash Lite at 3.3%. [claim:clm_018]
- As of the May 2026 snapshot, among the highest hallucination rates were Mistral Ministral 3-3B (2512) at 24.2%, Microsoft Phi-4-Mini-Instruct at 23.5%, and OpenAI o3-Pro at 23.3%. [claim:clm_019]
- AIS formally defines a pair (s,t) as attributable to sources P iff a generic hearer would, with a chosen confidence, affirm 'According to P, s', interpreting s relative to time t. [claim:clm_020]
- The paper introduces AIS (Attributable to Identified Sources) as an evaluation framework for assessing whether NLG output about the external world is supported by underlying sources, paired with a two-stage annotation pipeline. [claim:clm_021]
- AIS uses a two-stage human-annotation task: first annotators judge interpretability of the output without seeing the source, then judge whether the source P supports the output's information. [claim:clm_022]
- In the second stage, after a positive interpretability judgment, annotators are shown the source P and asked whether all information in the output can be supported by P. [claim:clm_023]
- AIS was empirically validated via human evaluation across three task types: two conversational QA datasets, a summarization dataset, and a table-to-text dataset. [claim:clm_024]
- AIS handles context-dependence by treating each sentence interpretation as an explicature - a paraphrase of the output that is interpretable in a linguistically empty context - before attribution is judged. [claim:clm_025]
- FacTool is a task- and domain-agnostic framework for detecting factual errors in texts generated by large language models such as ChatGPT. [claim:clm_026]
- A core motivation is that LLM-generated texts are lengthy and lack a clearly defined granularity for individual facts, which necessitates claim decomposition before verification. [claim:clm_027]
- FacTool is evaluated across four distinct tasks: knowledge-based QA, code generation, mathematical reasoning, and scientific literature review. [claim:clm_028]
- The framework targets the problem that explicit evidence is scarce during the fact-checking process, motivating a tool-augmented evidence-collection approach. [claim:clm_029]
- FacTool is released as open-source code on GitHub (GAIR-NLP/factool) together with a ChatGPT plugin interface. [claim:clm_030]
- The paper frames generative models as expanding the range of tasks now at increasing risk of containing factual errors. [claim:clm_031]
- Constitutional Classifiers are safeguards trained on synthetic data generated by prompting LLMs with a natural-language constitution that specifies permitted and restricted content categories. [claim:clm_032]
- Across over 3,000 estimated hours of red teaming, no red teamer found a universal jailbreak that extracted detailed harmful information from a classifier-guarded LLM comparable to an unguarded model across most target queries. [claim:clm_033]
- The classifiers caused only an absolute 0.38% increase in production-traffic refusals while imposing a 23.7% inference overhead. [claim:clm_034]
- The defense targets universal jailbreaks — prompting strategies that systematically bypass safeguards to enable harmful multi-interaction processes such as manufacturing illegal substances at scale. [claim:clm_035]
- On automated evaluations, enhanced classifiers demonstrated robust defense against held-out, domain-specific jailbreaks. [claim:clm_036]
- The paper was submitted January 31, 2025 by Mrinank Sharma, Meg Tong, Jesse Mu and colleagues at Anthropic (including Jan Leike, Jared Kaplan, and Ethan Perez). [claim:clm_037]
- Chain-of-Verification (CoVe) is a four-step method: draft an initial response, plan verification questions to fact-check the draft, answer them independently, and generate a final verified response. [claim:clm_038]
- Answering verification questions independently is the mechanism intended to prevent the model from being biased by, and thus repeating, its own initial responses. [claim:clm_039]
- CoVe decreases hallucinations across a variety of tasks, including Wikidata list-based questions, closed-book MultiSpanQA, and longform text generation. [claim:clm_040]
- The paper frames hallucination as the generation of plausible yet incorrect factual information, characterizing it as an unsolved problem in large language models. [claim:clm_041]
- CoVe's premise is that language models can deliberate on their own responses to correct their mistakes. [claim:clm_042]
- The paper is authored by Shehzaad Dhuliawala and colleagues (Meta AI / ETH Zurich) and was submitted to arXiv in September 2023, later appearing in Findings of ACL 2024 (pp. 3563-3578). [claim:clm_043]
- Across evaluated commercial LLMs and deep research agents, 3-13% of cited URLs are hallucinated (no Wayback record, likely never existed) and 5-18% are non-resolving overall. [claim:clm_044]
- Per-model fabricated-citation rates on DRBench: gemini-2.5-pro-deepresearch 13.3%, gpt-4.1 5.4%, openai-deepresearch 3.5%, and claude-3-5-sonnet-with-search 3.0%. [claim:clm_045]
- Deep research agents cite far more URLs per query (113.1 for Gemini, 41.2 for OpenAI vs 3.0-24.3 for search-augmented models), yet citation volume alone does not determine reliability. [claim:clm_046]
- The urlhealth tool issues an HTTP HEAD request (falling back to GET) and classifies each cited URL as LIVE, DEAD, LIKELY_HALLUCINATED, or UNKNOWN, using Wayback Machine snapshots to distinguish stale from fabricated URLs. [claim:clm_047]
- Agentic self-correction with urlhealth significantly reduced non-resolving citation rates for all three models (p<1e-35): GPT-5.1 16.0% to 0.6% (26x), Gemini 6.1% to 0.1% (79x), Claude 4.9% to 0.8% (6.4x). [claim:clm_048]
- The paper warns that existing benchmarks measure citation support but not citation existence, so with 3-13% fabricated URLs, naive support metrics systematically overestimate report reliability. [claim:clm_049]
- ALCE is the first benchmark for automatic evaluation of LLM-generated citations, requiring end-to-end systems that retrieve supporting evidence and generate answers with inline citations. [claim:clm_050]
- ALCE evaluates generations along three automatic dimensions—fluency, correctness, and citation quality—shown to correlate strongly with human judgements. [claim:clm_051]
- ALCE compiles three datasets covering different question types and corpora: ASQA (Stelmakh et al., 2022), QAMPARI (Rubin et al., 2022), and ELI5 (Fan et al., 2019). [claim:clm_052]
- Citation quality is measured with two metrics: citation recall (whether output is entirely supported by cited passages) and citation precision (whether any cited passages are irrelevant). [claim:clm_053]
- An NLI model (TRUE, a T5-11B fine-tuned on NLI datasets) checks whether the concatenated cited passages entail each generated statement, scoring each statement 0 or 1. [claim:clm_054]
- Even the best models leave generations not fully supported by cited passages roughly 50% of the time on ELI5; abstract states the best models lack complete citation support 50% of the time. [claim:clm_055]
- Citation recall for a statement is 1 only if at least one citation exists and the NLI model judges that the concatenation of all cited passages entails (fully supports) the statement. [claim:clm_056]
- Even the best-performing model fabricates answers 1.19% of the time at 32K context, with top-tier models in the 5-7% range, and fabrication rises steeply with context length. [claim:clm_057]
- The single best model on this benchmark, GLM 4.5, still fabricates answers 1.19% of the time at 32K context. [claim:clm_058]
- The median model fabricates answers at roughly 25%, far above the best-case rate, indicating model selection dominates fabrication risk. [claim:clm_059]
- At 128K context, only 5 of 26 tested models keep their fabrication rate under 10%. [claim:clm_060]
- At 200K context no model stays below 10% fabrication; even the best performer, Qwen3 Next 80B-A3B, fabricates answers to 10.25% of questions. [claim:clm_061]
- Fabrication is measured with probe questions that ask about content deliberately absent from the documents, so any specific answer is definitively a fabrication. [claim:clm_062]
- Temperature effects are nuanced: T=0.0 gives best overall accuracy in ~60% of cases, but higher temperatures reduce fabrication for most models and sharply cut coherence loss (infinite loops), which can reach 48x higher rates at T=0.0 than T=1.0. [claim:clm_063]
- SAFE (Search-Augmented Factuality Evaluator) uses an LLM to break a long-form response into individual atomic facts and verify each via a multi-step reasoning process that issues Google Search queries, the same decompose-then-verify pattern as a claim ledger. [claim:clm_064]
- The paper extends F1 as an aggregated long-form-factuality metric by balancing precision (percentage of supported facts) against recall, where recall is measured relative to a hyperparameter representing the user's preferred response length. [claim:clm_065]
- On ~16,000 individual facts SAFE agrees with crowdsourced human annotators 72% of the time, and on a random subset of 100 disagreement cases SAFE wins 76% of the time. [claim:clm_066]
- SAFE is more than 20 times cheaper than human annotators for evaluating long-form factuality. [claim:clm_067]
- LongFact is a benchmark of thousands of fact-seeking questions spanning 38 topics, generated using GPT-4. [claim:clm_068]
- Thirteen language models across four families (Gemini, GPT, Claude, and PaLM-2) were benchmarked on LongFact, and larger models generally achieved better long-form factuality. [claim:clm_069]
- Citations grounds Claude's answers in user-provided source documents, returning references to the exact sentences and passages used to generate each response (sentence-level granularity). [claim:clm_070]
- When enabled, the API chunks user-provided source documents into sentences upfront and passes those chunks plus context to the model with the query, so citations are produced at generation time rather than retrofit. [claim:clm_071]
- Anthropic's internal evaluations report that built-in Citations increases recall accuracy by up to 15% compared with most custom citation implementations. [claim:clm_072]
- Customer Endex reported that adopting Citations reduced source hallucinations and formatting issues from 10% to 0% and increased references per response by 20%. [claim:clm_073]
- Citations is generally available (June 23, 2025) for Claude 3.5 Sonnet and Claude 3.5 Haiku on the Anthropic API and Google Cloud Vertex AI, with Amazon Bedrock support added June 30, 2025. [claim:clm_074]
- Users are not charged for the output tokens that return the quoted source text itself. [claim:clm_075]

## Sources

- src_20260614_rib002_00 — Long-form factuality in large language models
- src_20260614_rib002_01 — Vectara Hallucination Leaderboard (HHEM-2.3)
- src_20260614_rib002_02 — Detecting and Correcting Reference Hallucinations in Commercial LLMs and Deep Research Agents
- src_20260614_rib002_03 — How Much Do LLMs Hallucinate in Document Q&A Scenarios? A 172-Billion-Token Study Across Temperatures, Context Lengths, and Hardware Platforms
- src_20260614_rib002_04 — RARR: Researching and Revising What Language Models Say, Using Language Models
- src_20260614_rib002_05 — Enabling Large Language Models to Generate Text with Citations (ALCE benchmark)
- src_20260614_rib002_06 — FacTool: Factuality Detection in Generative AI -- A Tool Augmented Framework for Multi-Task and Multi-Domain Scenarios
- src_20260614_rib002_07 — Measuring Attribution in Natural Language Generation Models
- src_20260614_rib002_08 — Introducing Citations on the Anthropic API
- src_20260614_rib002_09 — Future-House/paper-qa (PaperQA2): high-accuracy RAG over scientific literature
- src_20260614_rib002_10 — Chain-of-Verification Reduces Hallucination in Large Language Models
- src_20260614_rib002_11 — Constitutional Classifiers: Defending against Universal Jailbreaks across Thousands of Hours of Red Teaming

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
