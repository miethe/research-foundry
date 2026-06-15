---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_does_the_empirical_literature_say
title: Claim-ledger vs RAG/constitutional/self-consistency mitigation
intent_id: intent_research_20260614_what_does_the_empirical_literature_say
evidence_bundle_id: pending
created_at: '2026-06-14T14:21:17-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

**Inference:** Empirical 2023-2026 measurements converge on the conclusion that no current LLM eliminates unsupported claims in grounded synthesis: even best-case grounded summarization hallucinates at 1.8% (Vectara, Antgroup Finix S1 32B), best-case document-QA fabricates at 1.19% (GLM 4.5 at 32K), and the best citation systems leave ~50% of ELI5 answers not fully supported, so a residual unsupported-claim rate must be assumed and managed rather than designed away. [claim:clm_inf01]
**Inference:** A claim-ledger + verifier architecture is functionally the decompose-then-verify pattern that SAFE and FacTool already validate (break a long-form response into atomic facts, then check each against retrieved evidence), so RF's design inherits SAFE's demonstrated 72% agreement with human annotators and >20x cost advantage over human evaluation as its expected-performance prior rather than being an unproven novelty. [claim:clm_inf04]
**Inference:** On material-unsupported-claim reduction, an explicit claim-ledger + verifier dominates RAG-alone because RAG supplies grounding but does not enforce per-claim support: PaperQA2's RAG pipeline still emits citation keys without a per-statement entailment gate, and ALCE shows RAG-style cited generations leave ~50% of ELI5 statements unsupported, a gap that the claim-ledger's mandatory verify step is specifically designed to close. [claim:clm_inf05]
**Inference:** Constitutional AI / Constitutional Classifiers address a different failure axis than a claim-ledger and should be treated as complementary, not competing: they gate policy-violating content (universal jailbreaks, harmful categories) with a 23.7% inference overhead, but provide no claim-to-source traceability and no unsupported-claim metric, so they cannot reduce material unsupported claims in synthesis on their own. [claim:clm_inf06]

## Comparison matrix

### Material-unsupported-claim reduction

| Approach | Mechanism | Reduction assessment | Evidence |
|----------|-----------|----------------------|----------|
| Claim-ledger + verifier | Decompose into atomic claims, verify each against retrieved evidence | Strongest; closes the per-claim support gap RAG leaves open [claim:clm_inf05] | [claim:clm_inf05] |
| Claim-ledger + verifier | Same decompose-then-verify loop as SAFE/FacTool | Inherits SAFE's 72% human agreement as performance prior [claim:clm_inf04] | [claim:clm_inf04] |
| RAG (PaperQA2, Citations) | Ground generation in retrieved passages | Leaves ~50% of ELI5 statements unsupported without a per-claim gate [claim:clm_inf05] | [claim:clm_inf05] |
| Constitutional AI | Gate policy-violating content via constitution-trained classifiers | No unsupported-claim metric; orthogonal axis [claim:clm_inf06] | [claim:clm_inf06] |
| Self-consistency (CoVe) | Model deliberates on its own draft, no external evidence | Capped at what the model already knows; misses confidently-wrong claims [claim:clm_inf07] | [claim:clm_inf07] |

### Cost / latency

| Approach | Overhead assessment | Evidence |
|----------|---------------------|----------|
| Claim-ledger + verifier | Bounded single-digit-to-~25% compute premium, dominated by retrieval [claim:clm_inf09] | [claim:clm_inf09] |
| Claim-ledger + verifier | SAFE's decompose-search-verify loop is >20x cheaper than human annotation [claim:clm_067] | [claim:clm_067] |
| Constitutional AI | 23.7% inference overhead measured for the content gate [claim:clm_034] | [claim:clm_034] |
| Self-consistency (CoVe) | Adds a verification-question round but uses no external retrieval [claim:clm_038] | [claim:clm_038] |

### Traceability granularity

| Approach | Granularity | Evidence |
|----------|-------------|----------|
| Claim-ledger + verifier | Atomic-claim level (SAFE/FacTool style), finest provenance [claim:clm_inf08] | [claim:clm_inf08] |
| RAG (Anthropic Citations) | Sentence level [claim:clm_070] | [claim:clm_070] |
| RAG (PaperQA2) | Passage-level citation keys like (pqac-abcd1234) [claim:clm_007] | [claim:clm_007] |
| Constitutional AI | No claim-to-source traceability [claim:clm_inf08] | [claim:clm_inf08] |
| Self-consistency (CoVe) | No source references attached [claim:clm_inf08] | [claim:clm_inf08] |

**Inference:** On traceability granularity the four approaches rank claim-ledger+verifier (atomic-claim, SAFE/FacTool-style) >= Anthropic Citations (sentence) >= PaperQA2 RAG (passage) >> constitutional AI and self-consistency (no traceability at all), so finer-grained provenance is achieved precisely by the decompose-then-verify family and is absent from policy-gating and self-deliberation methods. [claim:clm_inf08]
**Inference:** Self-consistency / self-verification methods such as Chain-of-Verification reduce hallucination using only the model's own deliberation and no external evidence, which structurally caps their unsupported-claim reduction at what the model already knows; a claim-ledger + verifier that retrieves external evidence (the RARR/SAFE/FacTool pattern) can catch confidently-wrong claims that CoVe's independent self-answering cannot, making external-evidence verification strictly stronger for material-claim grounding. [claim:clm_inf07]
**Inference:** The measured cost/latency overhead of a verifier pass is moderate and dominated by retrieval, not synthesis: Constitutional Classifiers' content gate costs 23.7% inference overhead, and SAFE's full decompose-search-verify loop is still >20x cheaper than human annotation, so a per-claim verifier adds a bounded single-digit-to-~25% compute premium rather than a multiplicative blowup, making it economically viable as a standing gate. [claim:clm_inf09]

## Measured hallucination and unsupported-claim rates

### Reported rates by source

| Source / benchmark | Reported rate | Measurement unit | Evidence |
|--------------------|---------------|------------------|----------|
| Vectara (HHEM-2.3) best case | Antgroup Finix S1 32B 1.8%, GPT-5.4-nano 3.1%, Gemini 2.5 Flash Lite 3.3% [claim:clm_018] | Share of whole summaries containing any hallucination | [claim:clm_018] |
| Vectara (HHEM-2.3) worst case | Mistral Ministral 3-3B 24.2%, Phi-4-Mini 23.5%, o3-Pro 23.3% [claim:clm_019] | Share of whole summaries containing any hallucination | [claim:clm_019] |
| Roig document-QA best case | GLM 4.5 fabricates 1.19% at 32K, top-tier 5-7% [claim:clm_057] | Share of probe questions about deliberately-absent content | [claim:clm_057] |
| Roig document-QA median | Median model fabricates ~25% [claim:clm_059] | Share of probe questions about deliberately-absent content | [claim:clm_059] |
| Roig at 128K context | Only 5 of 26 models stay under 10% fabrication [claim:clm_060] | Share of probe questions about deliberately-absent content | [claim:clm_060] |
| Roig at 200K context | No model under 10%; best Qwen3 Next 80B-A3B at 10.25% [claim:clm_061] | Share of probe questions about deliberately-absent content | [claim:clm_061] |
| ALCE citation support | Best models leave ~50% of ELI5 generations not fully supported [claim:clm_055] | Statement-level NLI-entailment failure vs cited passages | [claim:clm_055] |
| DRBench fabricated URLs | 3-13% of cited URLs hallucinated, 5-18% non-resolving overall [claim:clm_044] | Cited-URL existence (Wayback record) | [claim:clm_044] |
| DRBench per-model fabrication | gemini-2.5-pro-deepresearch 13.3%, gpt-4.1 5.4%, openai-deepresearch 3.5%, claude-3-5-sonnet-with-search 3.0% [claim:clm_045] | Cited-URL existence | [claim:clm_045] |
| urlhealth self-correction | GPT-5.1 16.0% to 0.6% (26x), Gemini 6.1% to 0.1% (79x), Claude 4.9% to 0.8% (6.4x), p<1e-35 [claim:clm_048] | Non-resolving citation rate before/after agentic correction | [claim:clm_048] |
| SAFE vs human annotators | 72% agreement on ~16,000 facts; 76% win rate on 100 disagreements [claim:clm_066] | Atomic-fact support agreement | [claim:clm_066] |
| Anthropic Citations | Up to 15% recall-accuracy increase vs custom implementations [claim:clm_072] | Internal recall-accuracy evaluation | [claim:clm_072] |
| Anthropic Citations (Endex) | Source hallucinations 10% to 0%, references per response +20% [claim:clm_073] | Customer-reported hallucination/formatting rate | [claim:clm_073] |
| Constitutional Classifiers | 0.38% absolute refusal increase, 23.7% inference overhead [claim:clm_034] | Production-traffic refusal delta and inference cost | [claim:clm_034] |

### Measurement methodology by framework

The leaderboard is scored using HHEM-2.3, Vectara's commercial hallucination evaluation model, with an open-source variant HHEM-2.1-Open available on Hugging Face and Kaggle. [claim:clm_013]
The leaderboard is computed over a dataset of more than 7,700 articles and was last updated on May 11, 2026. [claim:clm_014]
The leaderboard measures intrinsic hallucination in document summarization: each LLM is given documents and asked to summarize them, reflecting RAG-style grounded synthesis rather than single-turn QA. [claim:clm_015]
The primary metric is the factual consistency rate (the rate of summaries with no hallucinations), the inverse of the hallucination rate. [claim:clm_016]
Answer Rate is reported as a separate column capturing how often a model refuses to respond to the summarization prompt versus producing a summary. [claim:clm_017]
Fabrication in the Roig study is measured with probe questions that ask about content deliberately absent from the documents, so any specific answer is definitively a fabrication. [claim:clm_062]
The single best model on the Roig benchmark, GLM 4.5, still fabricates answers 1.19% of the time at 32K context. [claim:clm_058]
Temperature effects are nuanced: T=0.0 gives best overall accuracy in ~60% of cases, but higher temperatures reduce fabrication for most models and sharply cut coherence loss (infinite loops), which can reach 48x higher rates at T=0.0 than T=1.0. [claim:clm_063]
ALCE is the first benchmark for automatic evaluation of LLM-generated citations, requiring end-to-end systems that retrieve supporting evidence and generate answers with inline citations. [claim:clm_050]
ALCE evaluates generations along three automatic dimensions—fluency, correctness, and citation quality—shown to correlate strongly with human judgements. [claim:clm_051]
ALCE compiles three datasets covering different question types and corpora: ASQA (Stelmakh et al., 2022), QAMPARI (Rubin et al., 2022), and ELI5 (Fan et al., 2019). [claim:clm_052]
Citation quality in ALCE is measured with two metrics: citation recall (whether output is entirely supported by cited passages) and citation precision (whether any cited passages are irrelevant). [claim:clm_053]
An NLI model (TRUE, a T5-11B fine-tuned on NLI datasets) checks whether the concatenated cited passages entail each generated statement, scoring each statement 0 or 1. [claim:clm_054]
Citation recall for a statement is 1 only if at least one citation exists and the NLI model judges that the concatenation of all cited passages entails (fully supports) the statement. [claim:clm_056]
SAFE (Search-Augmented Factuality Evaluator) uses an LLM to break a long-form response into individual atomic facts and verify each via a multi-step reasoning process that issues Google Search queries, the same decompose-then-verify pattern as a claim ledger. [claim:clm_064]
The SAFE paper extends F1 as an aggregated long-form-factuality metric by balancing precision (percentage of supported facts) against recall, where recall is measured relative to a hyperparameter representing the user's preferred response length. [claim:clm_065]
SAFE is more than 20 times cheaper than human annotators for evaluating long-form factuality. [claim:clm_067]
LongFact is a benchmark of thousands of fact-seeking questions spanning 38 topics, generated using GPT-4. [claim:clm_068]
Thirteen language models across four families (Gemini, GPT, Claude, and PaLM-2) were benchmarked on LongFact, and larger models generally achieved better long-form factuality. [claim:clm_069]
The DRBench urlhealth tool issues an HTTP HEAD request (falling back to GET) and classifies each cited URL as LIVE, DEAD, LIKELY_HALLUCINATED, or UNKNOWN, using Wayback Machine snapshots to distinguish stale from fabricated URLs. [claim:clm_047]
Deep research agents cite far more URLs per query (113.1 for Gemini, 41.2 for OpenAI vs 3.0-24.3 for search-augmented models), yet citation volume alone does not determine reliability. [claim:clm_046]
The DRBench paper warns that existing benchmarks measure citation support but not citation existence, so with 3-13% fabricated URLs, naive support metrics systematically overestimate report reliability. [claim:clm_049]
Across over 3,000 estimated hours of red teaming, no red teamer found a universal jailbreak that extracted detailed harmful information from a classifier-guarded LLM comparable to an unguarded model across most target queries. [claim:clm_033]
The Constitutional Classifiers defense targets universal jailbreaks — prompting strategies that systematically bypass safeguards to enable harmful multi-interaction processes such as manufacturing illegal substances at scale. [claim:clm_035]
On automated evaluations, enhanced classifiers demonstrated robust defense against held-out, domain-specific jailbreaks. [claim:clm_036]
Constitutional Classifiers are safeguards trained on synthetic data generated by prompting LLMs with a natural-language constitution that specifies permitted and restricted content categories. [claim:clm_032]
The Constitutional Classifiers paper was submitted January 31, 2025 by Mrinank Sharma, Meg Tong, Jesse Mu and colleagues at Anthropic (including Jan Leike, Jared Kaplan, and Ethan Perez). [claim:clm_037]

**Inference:** Reported unsupported-claim rates are not comparable across studies because each defines a different unit and metric: Vectara measures the share of whole summaries containing any hallucination (HHEM-2.3, 1.8-24.2%), Roig measures the share of probe questions answered about deliberately-absent content (RIKER, 1.19-25%+), ALCE measures statement-level NLI-entailment failure against cited passages (~50% on ELI5), and DRBench measures fabricated-URL existence (3-13%), so headline percentages must be read against their measurement unit before any cross-framework ranking. [claim:clm_inf02]

## Mechanism survey

This section documents how each attribution and verification mechanism in the literature operates, grouping them by attribution timing.

### Post-hoc / retrofit verification

RARR (Retrofit Attribution using Research and Revision) automatically finds attribution for the output of any text generation model and post-edits that output to fix unsupported content while preserving the original as much as possible. [claim:clm_001]
Applied to several state-of-the-art LMs across diverse generation tasks, RARR significantly improves attribution while preserving the original output far more than prior edit models. [claim:clm_002]
The RARR Research stage begins with comprehensive question generation (CQGen), producing a sequence of questions covering all aspects of the passage to be verified. [claim:clm_003]
For each generated query, RARR uses standard web search (Google Search) to retrieve K=5 web pages ranked by relevance as candidate evidence. [claim:clm_004]
An agreement model decides whether the (partially edited) passage and the retrieved evidence imply the same answer to a query; the edit model is invoked only on disagreement and minimally alters the passage to agree with the evidence. [claim:clm_005]
RARR is model-agnostic and post-hoc: it retrofits attribution after generation without modifying the underlying LM, requiring only a handful of training examples, a large language model, and standard web search. [claim:clm_006]
FacTool is a task- and domain-agnostic framework for detecting factual errors in texts generated by large language models such as ChatGPT. [claim:clm_026]
A core FacTool motivation is that LLM-generated texts are lengthy and lack a clearly defined granularity for individual facts, which necessitates claim decomposition before verification. [claim:clm_027]
FacTool is evaluated across four distinct tasks: knowledge-based QA, code generation, mathematical reasoning, and scientific literature review. [claim:clm_028]
The FacTool framework targets the problem that explicit evidence is scarce during the fact-checking process, motivating a tool-augmented evidence-collection approach. [claim:clm_029]
FacTool is released as open-source code on GitHub (GAIR-NLP/factool) together with a ChatGPT plugin interface. [claim:clm_030]
The FacTool paper frames generative models as expanding the range of tasks now at increasing risk of containing factual errors. [claim:clm_031]

### Pre-hoc / generation-time grounding

PaperQA2 emits passage-level in-text citation keys formatted like (pqac-abcd1234), each tied to a specific retrieved passage. [claim:clm_007]
The PaperQA2 answer object exposes a formatted_answer with integrated citations alongside a context attribute holding passage summaries. [claim:clm_008]
PaperQA2 Phase 1 (Paper Search) retrieves candidate papers via an LLM-generated keyword query, then chunks, embeds, and adds them to state. [claim:clm_009]
PaperQA2 Phase 2 (Gather Evidence) embedding-ranks chunks, builds scored contextual summaries, then uses an LLM to re-score and select the most relevant summaries. [claim:clm_010]
PaperQA2 is documented as achieving superhuman performance on scientific-literature tasks including question answering, summarization, and contradiction detection. [claim:clm_011]
PaperQA2 is Apache-2.0 licensed and self-hostable, with local model backends such as ollama and llamafile supported. [claim:clm_012]
Anthropic Citations grounds Claude's answers in user-provided source documents, returning references to the exact sentences and passages used to generate each response (sentence-level granularity). [claim:clm_070]
When enabled, the API chunks user-provided source documents into sentences upfront and passes those chunks plus context to the model with the query, so citations are produced at generation time rather than retrofit. [claim:clm_071]
Anthropic's internal evaluations report that built-in Citations increases recall accuracy by up to 15% compared with most custom citation implementations. [claim:clm_072]
Customer Endex reported that adopting Citations reduced source hallucinations and formatting issues from 10% to 0% and increased references per response by 20%. [claim:clm_073]
Citations is generally available (June 23, 2025) for Claude 3.5 Sonnet and Claude 3.5 Haiku on the Anthropic API and Google Cloud Vertex AI, with Amazon Bedrock support added June 30, 2025. [claim:clm_074]
Users are not charged for the output tokens that return the quoted source text itself. [claim:clm_075]

### Self-deliberation verification

Chain-of-Verification (CoVe) is a four-step method: draft an initial response, plan verification questions to fact-check the draft, answer them independently, and generate a final verified response. [claim:clm_038]
Answering verification questions independently is the mechanism intended to prevent the model from being biased by, and thus repeating, its own initial responses. [claim:clm_039]
CoVe decreases hallucinations across a variety of tasks, including Wikidata list-based questions, closed-book MultiSpanQA, and longform text generation. [claim:clm_040]
The CoVe paper frames hallucination as the generation of plausible yet incorrect factual information, characterizing it as an unsolved problem in large language models. [claim:clm_041]
CoVe's premise is that language models can deliberate on their own responses to correct their mistakes. [claim:clm_042]
The CoVe paper is authored by Shehzaad Dhuliawala and colleagues (Meta AI / ETH Zurich) and was submitted to arXiv in September 2023, later appearing in Findings of ACL 2024 (pp. 3563-3578). [claim:clm_043]

### The human gold standard

The AIS paper introduces AIS (Attributable to Identified Sources) as an evaluation framework for assessing whether NLG output about the external world is supported by underlying sources, paired with a two-stage annotation pipeline. [claim:clm_021]
AIS formally defines a pair (s,t) as attributable to sources P iff a generic hearer would, with a chosen confidence, affirm 'According to P, s', interpreting s relative to time t. [claim:clm_020]
AIS uses a two-stage human-annotation task: first annotators judge interpretability of the output without seeing the source, then judge whether the source P supports the output's information. [claim:clm_022]
In the second AIS stage, after a positive interpretability judgment, annotators are shown the source P and asked whether all information in the output can be supported by P. [claim:clm_023]
AIS was empirically validated via human evaluation across three task types: two conversational QA datasets, a summarization dataset, and a table-to-text dataset. [claim:clm_024]
AIS handles context-dependence by treating each sentence interpretation as an explicature - a paraphrase of the output that is interpretable in a linguistically empty context - before attribution is judged. [claim:clm_025]

**Inference:** The existing frameworks split cleanly into two attribution timings: pre-hoc / generation-time systems that constrain output to retrieved context (PaperQA2 passage-level keys, Anthropic Citations sentence-level chunks) and post-hoc / retrofit systems that decompose then verify after generation (RARR claim-level edits, FacTool and SAFE atomic-fact verification, ALCE NLI scoring), with AIS sitting orthogonally as the human gold standard both timings are validated against. [claim:clm_inf03]

## Analysis and derivation

**Inference:** RF's cheap-extract / expensive-synthesize split maps directly onto the empirical verifier economics: claim decomposition and per-claim entailment/NLI checks are the cheap-model tasks (ALCE uses a T5-11B NLI model, SAFE uses search-query reasoning, urlhealth uses an HTTP HEAD probe), while only the synthesis/edit step needs an expensive model, so the verification pass should be routed to small models with the costly model reserved for synthesis and disagreement-triggered edits. [claim:clm_inf10]
**Inference:** Existing claim-attribution evaluation methodology transfers cleanly to RF's source-card model: AIS provides the human gold-standard definition (a generic hearer affirms 'According to P, s'), ALCE provides the automatic statement-level NLI metrics (citation recall/precision), and a source card is operationally the 'P' in the AIS definition, so RF can adopt citation-recall (claim fully entailed by its source cards) and citation-precision (no irrelevant source cards) as its native verification metrics with minimal adaptation. [claim:clm_inf15]
**Inference:** Model selection dominates verifier design for fabrication risk: Roig shows the median model fabricates ~25% versus the best model's 1.19% at 32K, a >20x spread, so choosing a low-hallucination synthesis model (e.g., a sub-2% Vectara-leaderboard model) is a higher-leverage first move than verifier tuning, and the verifier should be calibrated for the chosen model's residual rate rather than a generic one. [claim:clm_inf17]
**Inference:** Context-length is an operational guardrail for a claim-ledger: Roig shows fabrication nearly triples from 32K to 128K and exceeds 10% for every model at 200K, so RF should cap per-synthesis evidence-context size and shard large source-card sets into multiple bounded synthesis passes rather than stuffing all cards into one long context, since the verifier's workload grows precisely where fabrication is worst. [claim:clm_inf18]

## Documented failure modes

| Failure mode | Detection signal | Evidence |
|--------------|------------------|----------|
| Citation-without-support | Per-statement NLI entailment failure vs concatenated cited passages [claim:clm_inf11] | [claim:clm_inf11] |
| Fabricated-citation / non-existent-source | URL existence verification (HTTP HEAD + Wayback snapshot) [claim:clm_inf12] | [claim:clm_inf12] |
| Over-suppression / over-refusal | Rise in refusal / answer-rate column relative to baseline [claim:clm_inf13] | [claim:clm_inf13] |
| Verifier hallucination | Near-threshold entailment scores from a fallible verifier [claim:clm_inf14] | [claim:clm_inf14] |

**Inference:** Citation-without-support is the most prevalent documented verifier/attribution failure mode, with the detection signal being per-statement NLI entailment failure against the concatenated cited passages: ALCE measures it at ~50% of ELI5 statements even for ChatGPT/GPT-4, so a claim-ledger must run an entailment check per claim rather than trusting that a present citation implies support. [claim:clm_inf11]
**Inference:** Fabricated-citation / non-existent-source is a second distinct failure mode invisible to support metrics, with the detection signal being URL existence verification (HTTP HEAD plus Wayback Machine snapshot lookup): DRBench finds 3-13% of cited URLs never existed, support-only benchmarks cannot catch this, and urlhealth-style agentic self-correction drove non-resolving rates from 4.9-16.0% to under 1% (6-79x). [claim:clm_inf12]
**Inference:** Over-suppression / over-refusal is a third failure mode of any verify-gate, and its detection signal is a rise in the refusal/answer-rate column relative to baseline: Vectara reports Answer Rate separately precisely because aggressive grounding can suppress legitimate output, and Constitutional Classifiers quantify the cost as a 0.38% absolute refusal increase, so a claim-ledger must monitor a no-claim-emitted / abstention rate to detect a verifier that is rejecting supportable claims. [claim:clm_inf13]
**Inference:** Verifier hallucination (the verifier itself misjudging support) is a fourth failure mode, evidenced by SAFE disagreeing with human annotators 28% of the time, so a claim-ledger should treat verifier verdicts as fallible and route low-confidence or near-threshold entailment scores to escalation or human review rather than auto-accepting them. [claim:clm_inf14]

## Recommendations and decision rules

**Inference:** Decision rule for RF: default to a pre-hoc grounded-generation layer (sentence/passage citations, PaperQA2/Anthropic-Citations style) for first-pass provenance, then run a post-hoc atomic-claim verifier (SAFE/RARR/FacTool style) as a mandatory gate on material claims only, because pre-hoc alone leaves ~50% unsupported (ALCE) and post-hoc-on-everything is unnecessarily expensive given fabrication concentrates in material specific answers (Roig probe design). [claim:clm_inf16]
**Inference:** Model selection dominates verifier design for fabrication risk: Roig shows the median model fabricates ~25% versus the best model's 1.19% at 32K, a >20x spread, so choosing a low-hallucination synthesis model (e.g., a sub-2% Vectara-leaderboard model) is a higher-leverage first move than verifier tuning, and the verifier should be calibrated for the chosen model's residual rate rather than a generic one. [claim:clm_inf17]
**Inference:** RF's cheap-extract / expensive-synthesize split maps directly onto the empirical verifier economics: claim decomposition and per-claim entailment/NLI checks are the cheap-model tasks (ALCE uses a T5-11B NLI model, SAFE uses search-query reasoning, urlhealth uses an HTTP HEAD probe), while only the synthesis/edit step needs an expensive model, so the verification pass should be routed to small models with the costly model reserved for synthesis and disagreement-triggered edits. [claim:clm_inf10]
**Inference:** Context-length is an operational guardrail for a claim-ledger: Roig shows fabrication nearly triples from 32K to 128K and exceeds 10% for every model at 200K, so RF should cap per-synthesis evidence-context size and shard large source-card sets into multiple bounded synthesis passes rather than stuffing all cards into one long context, since the verifier's workload grows precisely where fabrication is worst. [claim:clm_inf18]
**Inference:** Existing claim-attribution evaluation methodology transfers cleanly to RF's source-card model: AIS provides the human gold-standard definition (a generic hearer affirms 'According to P, s'), ALCE provides the automatic statement-level NLI metrics (citation recall/precision), and a source card is operationally the 'P' in the AIS definition, so RF can adopt citation-recall (claim fully entailed by its source cards) and citation-precision (no irrelevant source cards) as its native verification metrics with minimal adaptation. [claim:clm_inf15]
**Speculation:** As frontier deep-research agents continue to cite ever-larger URL sets (113 URLs/query for Gemini deep research today), existence-verification (urlhealth-style) rather than support-verification will become the binding bottleneck for report trust, so RF should prioritize cheap, mandatory URL/source-existence checks now in anticipation that fabricated-source rates, not unsupported-claim rates, will dominate reliability complaints. [claim:clm_spec01]
**Speculation:** If a claim-ledger + verifier reaches SAFE-level human agreement (~72-76%) on RF source cards, the residual disagreement band implies a self-correction ceiling around the DRBench result (non-resolving citations driven to <1% but not 0%), so RF should plan for an irreducible low-single-digit material-unsupported-claim rate and surface it as a calibrated confidence label rather than promising zero unsupported claims. [claim:clm_spec02]

## Open questions

- What is the measured citation-recall and citation-precision of a claim-ledger + verifier on real RF source cards, rather than the SAFE/ALCE proxies used as priors?
- Does the cheap-model verifier (T5-11B-class NLI) preserve SAFE-level agreement when the unit of verification is an RF source card rather than a web search result?
- Where should the escalation threshold for verifier hallucination sit so that near-threshold entailment scores are routed to human review without inflating the over-refusal rate?
- How far below the 32K context regime must per-synthesis evidence-context be capped to keep fabrication near the best-case 1.19% rather than the median 25%?

## Sources

- src_20260614_rib002_04: RARR: Researching and Revising What Language Models Say, Using Language Models
- src_20260614_rib002_09: Future-House/paper-qa (PaperQA2): high-accuracy RAG over scientific literature
- src_20260614_rib002_01: Vectara Hallucination Leaderboard (HHEM-2.3)
- src_20260614_rib002_07: Measuring Attribution in Natural Language Generation Models
- src_20260614_rib002_06: FacTool: Factuality Detection in Generative AI -- A Tool Augmented Framework for Multi-Task and Multi-Domain Scenarios
- src_20260614_rib002_11: Constitutional Classifiers: Defending against Universal Jailbreaks across Thousands of Hours of Red Teaming
- src_20260614_rib002_10: Chain-of-Verification Reduces Hallucination in Large Language Models
- src_20260614_rib002_02: Detecting and Correcting Reference Hallucinations in Commercial LLMs and Deep Research Agents
- src_20260614_rib002_05: Enabling Large Language Models to Generate Text with Citations (ALCE benchmark)
- src_20260614_rib002_03: How Much Do LLMs Hallucinate in Document Q&A Scenarios? A 172-Billion-Token Study Across Temperatures, Context Lengths, and Hardware Platforms
- src_20260614_rib002_00: Long-form factuality in large language models
- src_20260614_rib002_08: Introducing Citations on the Anthropic API
