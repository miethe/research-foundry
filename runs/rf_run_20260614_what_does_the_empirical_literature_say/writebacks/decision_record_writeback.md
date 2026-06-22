---
id: mwb_20260622_dr_claim_ledger_vs_rag_constitutional
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_does_the
target_page: meatywiki/decisions/claim_ledger_vs_rag_constitutional_self.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_does_the_empirical_literature_say: ALCE''s verifier
  is a T5-11B NLI model, urlhealth is a cheap HTTP probe, and RARR runs the expensive edit model only
  on d'
key_claims:
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf17
  include: true
- claim_id: clm_inf18
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
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_054
  - clm_064
  - clm_047
  - clm_005
  - clm_020
  - clm_053
  - clm_007
  - clm_071
  - clm_055
  - clm_062
  - clm_006
  - clm_059
  - clm_058
  - clm_018
  - clm_057
  - clm_060
  - clm_061
  - clm_016
  - clm_044
  - clm_021
  - clm_027
  - clm_066
  - clm_067
  - clm_010
  - clm_032
  - clm_035
  - clm_034
  - clm_038
  - clm_039
  - clm_042
  - clm_070
  - clm_056
  - clm_049
  - clm_048
  - clm_017
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Claim-ledger vs RAG/constitutional/self-consistency mitigation

## Context

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

## Decision

RF's cheap-extract / expensive-synthesize split maps directly onto the empirical verifier economics: claim decomposition and per-claim entailment/NLI checks are the cheap-model tasks (ALCE uses a T5-11B NLI model, SAFE uses search-query reasoning, urlhealth uses an HTTP HEAD probe), while only the synthesis/edit step needs an expensive model, so the verification pass should be routed to small models with the costly model reserved for synthesis and disagreement-triggered edits. [claim:clm_inf10]

## Rationale

- ALCE's verifier is a T5-11B NLI model, urlhealth is a cheap HTTP probe, and RARR runs the expensive edit model only on disagreement, so the verification pass is cheap-model work and the expensive model is reserved for synthesis/edits. [claim:clm_inf10]
- AIS's 'According to P, s' maps onto 'claim supported by source card', and ALCE's recall/precision are statement-level NLI metrics; a source card is the P, so these metrics port directly to RF. [claim:clm_inf15]
- Pre-hoc citations give cheap first-pass provenance but leave ~50% unsupported (ALCE), so a post-hoc atomic verifier gate on material claims combines both families' strengths while bounding cost. [claim:clm_inf16]
- Roig's ~25% median vs 1.19% best (>20x spread) and Vectara's sub-2% leaders show model choice swings fabrication by an order of magnitude, exceeding plausible verifier gains, so model selection is the higher-leverage lever. [claim:clm_inf17]
- Fabrication rises steeply with context length (triples 32K->128K, >10% for all at 200K), so bounding synthesis context and sharding source cards keeps generation in the lower-fabrication regime. [claim:clm_inf18]
- Three independent best-case measurements across grounded summarization, document QA, and cited long-form QA all report non-zero residual unsupported/fabricated rates, so eliminating unsupported claims is empirically unattained across the literature. [claim:clm_inf01]
- Each source defines its rate over a different unit (whole-summary, probe-question, statement-NLI, URL-existence), so the numeric scales are not directly comparable and require normalization to the unit before ranking. [claim:clm_inf02]
- PaperQA2 and Anthropic Citations attach provenance at or before generation; RARR/FacTool/SAFE/ALCE operate after generation by decomposing and verifying; AIS is the human standard used to validate attribution judgments regardless of timing. [claim:clm_inf03]
- RF's claim-ledger is the same atomic-fact-decompose-then-verify loop SAFE and FacTool implement; SAFE's measured 72% human agreement and 20x cost advantage therefore transfer as the architecture's empirical prior. [claim:clm_inf04]
- RAG (PaperQA2) produces citations but no per-statement entailment gate, and ALCE measures ~50% unsupported statements under cited RAG; a verifier that NLI-checks each ledger claim targets exactly that residual, so claim-ledger+verifier reduces material unsupported claims below RAG-alone. [claim:clm_inf05]
- Constitutional Classifiers target permitted/restricted-content policy enforcement, not source attribution; they expose no per-claim support metric, so they operate on an orthogonal axis from the claim-ledger's unsupported-claim reduction. [claim:clm_inf06]
- CoVe verifies against the model's own knowledge (independent self-answering), so a uniformly-held false belief survives; external-evidence verifiers (SAFE/RARR) check against retrieved sources and can flag it, giving them a structural advantage on grounded factuality. [claim:clm_inf07]
- SAFE-style atomic-fact verification gives claim-level provenance, Citations sentence-level, PaperQA2 passage-level; Constitutional Classifiers and CoVe attach no source references, ordering the four on granularity. [claim:clm_inf08]
- The only directly measured verifier-class overheads (Constitutional Classifiers 23.7%; SAFE >20x cheaper than humans) bound the cost of an automated verify pass to a moderate premium rather than an order-of-magnitude increase. [claim:clm_inf09]
- ALCE defines citation recall via NLI entailment and finds ~50% of cited statements not entailed, so the failure (citation present but not supporting) is detected by per-statement NLI entailment failure. [claim:clm_inf11]
- DRBench shows 3-13% fabricated URLs that support metrics miss; urlhealth detects them via HEAD+Wayback and self-correction cuts them 6-79x, defining a separate failure mode and its detection signal. [claim:clm_inf12]
- Vectara's separate Answer Rate column and Constitutional Classifiers' 0.38% refusal-increase metric both track suppression/refusal as a side effect of gating, giving abstention/refusal rate as the detection signal for over-suppression. [claim:clm_inf13]
- SAFE agrees with humans only 72% (disagrees 28%), and NLI verifiers output a hard 0/1, so the verifier itself errs; near-threshold scores are the detection signal warranting escalation. [claim:clm_inf14]

## Consequences

- Existing claim-attribution evaluation methodology transfers cleanly to RF's source-card model: AIS provides the human gold-standard definition (a generic hearer affirms 'According to P, s'), ALCE provides the automatic statement-level NLI metrics (citation recall/precision), and a source card is operationally the 'P' in the AIS definition, so RF can adopt citation-recall (claim fully entailed by its source cards) and citation-precision (no irrelevant source cards) as its native verification metrics with minimal adaptation. [claim:clm_inf15]
- Decision rule for RF: default to a pre-hoc grounded-generation layer (sentence/passage citations, PaperQA2/Anthropic-Citations style) for first-pass provenance, then run a post-hoc atomic-claim verifier (SAFE/RARR/FacTool style) as a mandatory gate on material claims only, because pre-hoc alone leaves ~50% unsupported (ALCE) and post-hoc-on-everything is unnecessarily expensive given fabrication concentrates in material specific answers (Roig probe design). [claim:clm_inf16]
- Model selection dominates verifier design for fabrication risk: Roig shows the median model fabricates ~25% versus the best model's 1.19% at 32K, a >20x spread, so choosing a low-hallucination synthesis model (e.g., a sub-2% Vectara-leaderboard model) is a higher-leverage first move than verifier tuning, and the verifier should be calibrated for the chosen model's residual rate rather than a generic one. [claim:clm_inf17]
- Context-length is an operational guardrail for a claim-ledger: Roig shows fabrication nearly triples from 32K to 128K and exceeds 10% for every model at 200K, so RF should cap per-synthesis evidence-context size and shard large source-card sets into multiple bounded synthesis passes rather than stuffing all cards into one long context, since the verifier's workload grows precisely where fabrication is worst. [claim:clm_inf18]
- Empirical 2023-2026 measurements converge on the conclusion that no current LLM eliminates unsupported claims in grounded synthesis: even best-case grounded summarization hallucinates at 1.8% (Vectara, Antgroup Finix S1 32B), best-case document-QA fabricates at 1.19% (GLM 4.5 at 32K), and the best citation systems leave ~50% of ELI5 answers not fully supported, so a residual unsupported-claim rate must be assumed and managed rather than designed away. [claim:clm_inf01]
- Reported unsupported-claim rates are not comparable across studies because each defines a different unit and metric: Vectara measures the share of whole summaries containing any hallucination (HHEM-2.3, 1.8-24.2%), Roig measures the share of probe questions answered about deliberately-absent content (RIKER, 1.19-25%+), ALCE measures statement-level NLI-entailment failure against cited passages (~50% on ELI5), and DRBench measures fabricated-URL existence (3-13%), so headline percentages must be read against their measurement unit before any cross-framework ranking. [claim:clm_inf02]
- The existing frameworks split cleanly into two attribution timings: pre-hoc / generation-time systems that constrain output to retrieved context (PaperQA2 passage-level keys, Anthropic Citations sentence-level chunks) and post-hoc / retrofit systems that decompose then verify after generation (RARR claim-level edits, FacTool and SAFE atomic-fact verification, ALCE NLI scoring), with AIS sitting orthogonally as the human gold standard both timings are validated against. [claim:clm_inf03]
- A claim-ledger + verifier architecture is functionally the decompose-then-verify pattern that SAFE and FacTool already validate (break a long-form response into atomic facts, then check each against retrieved evidence), so RF's design inherits SAFE's demonstrated 72% agreement with human annotators and >20x cost advantage over human evaluation as its expected-performance prior rather than being an unproven novelty. [claim:clm_inf04]
- On material-unsupported-claim reduction, an explicit claim-ledger + verifier dominates RAG-alone because RAG supplies grounding but does not enforce per-claim support: PaperQA2's RAG pipeline still emits citation keys without a per-statement entailment gate, and ALCE shows RAG-style cited generations leave ~50% of ELI5 statements unsupported, a gap that the claim-ledger's mandatory verify step is specifically designed to close. [claim:clm_inf05]
- Constitutional AI / Constitutional Classifiers address a different failure axis than a claim-ledger and should be treated as complementary, not competing: they gate policy-violating content (universal jailbreaks, harmful categories) with a 23.7% inference overhead, but provide no claim-to-source traceability and no unsupported-claim metric, so they cannot reduce material unsupported claims in synthesis on their own. [claim:clm_inf06]
- Self-consistency / self-verification methods such as Chain-of-Verification reduce hallucination using only the model's own deliberation and no external evidence, which structurally caps their unsupported-claim reduction at what the model already knows; a claim-ledger + verifier that retrieves external evidence (the RARR/SAFE/FacTool pattern) can catch confidently-wrong claims that CoVe's independent self-answering cannot, making external-evidence verification strictly stronger for material-claim grounding. [claim:clm_inf07]
- On traceability granularity the four approaches rank claim-ledger+verifier (atomic-claim, SAFE/FacTool-style) >= Anthropic Citations (sentence) >= PaperQA2 RAG (passage) >> constitutional AI and self-consistency (no traceability at all), so finer-grained provenance is achieved precisely by the decompose-then-verify family and is absent from policy-gating and self-deliberation methods. [claim:clm_inf08]
- The measured cost/latency overhead of a verifier pass is moderate and dominated by retrieval, not synthesis: Constitutional Classifiers' content gate costs 23.7% inference overhead, and SAFE's full decompose-search-verify loop is still >20x cheaper than human annotation, so a per-claim verifier adds a bounded single-digit-to-~25% compute premium rather than a multiplicative blowup, making it economically viable as a standing gate. [claim:clm_inf09]
- Citation-without-support is the most prevalent documented verifier/attribution failure mode, with the detection signal being per-statement NLI entailment failure against the concatenated cited passages: ALCE measures it at ~50% of ELI5 statements even for ChatGPT/GPT-4, so a claim-ledger must run an entailment check per claim rather than trusting that a present citation implies support. [claim:clm_inf11]
- Fabricated-citation / non-existent-source is a second distinct failure mode invisible to support metrics, with the detection signal being URL existence verification (HTTP HEAD plus Wayback Machine snapshot lookup): DRBench finds 3-13% of cited URLs never existed, support-only benchmarks cannot catch this, and urlhealth-style agentic self-correction drove non-resolving rates from 4.9-16.0% to under 1% (6-79x). [claim:clm_inf12]
- Over-suppression / over-refusal is a third failure mode of any verify-gate, and its detection signal is a rise in the refusal/answer-rate column relative to baseline: Vectara reports Answer Rate separately precisely because aggressive grounding can suppress legitimate output, and Constitutional Classifiers quantify the cost as a 0.38% absolute refusal increase, so a claim-ledger must monitor a no-claim-emitted / abstention rate to detect a verifier that is rejecting supportable claims. [claim:clm_inf13]
- Verifier hallucination (the verifier itself misjudging support) is a fourth failure mode, evidenced by SAFE disagreeing with human annotators 28% of the time, so a claim-ledger should treat verifier verdicts as fallible and route low-confidence or near-threshold entailment scores to escalation or human review rather than auto-accepting them. [claim:clm_inf14]

## Links

- [[claim:clm_054]]
- [[claim:clm_064]]
- [[claim:clm_047]]
- [[claim:clm_005]]
- [[claim:clm_020]]
- [[claim:clm_053]]
- [[claim:clm_007]]
- [[claim:clm_071]]
- [[claim:clm_055]]
- [[claim:clm_062]]
- [[claim:clm_006]]
- [[claim:clm_059]]
- [[claim:clm_058]]
- [[claim:clm_018]]
- [[claim:clm_057]]
- [[claim:clm_060]]
- [[claim:clm_061]]
- [[claim:clm_016]]
- [[claim:clm_044]]
- [[claim:clm_021]]
- [[claim:clm_027]]
- [[claim:clm_066]]
- [[claim:clm_067]]
- [[claim:clm_010]]
- [[claim:clm_032]]
- [[claim:clm_035]]
- [[claim:clm_034]]
- [[claim:clm_038]]
- [[claim:clm_039]]
- [[claim:clm_042]]
- [[claim:clm_070]]
- [[claim:clm_056]]
- [[claim:clm_049]]
- [[claim:clm_048]]
- [[claim:clm_017]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
