---
schema_version: '0.1'
type: research_report
report_id: report_20260615_contradiction_detection_across_heterogeneous_sou
title: Contradiction detection across heterogeneous source cards
intent_id: intent_research_20260614_contradiction_detection_across_heterogeneous_sou
evidence_bundle_id: pending
created_at: '2026-06-15T00:01:01-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Claimify is a four-stage LLM claim-extraction pipeline: Sentence Splitting and Context Creation, Selection, Disambiguation, and Decomposition. [claim:clm_001]
A defining feature of Claimify is that it only extracts claims when there is high confidence in the correct interpretation of the source text, otherwise handling the ambiguity rather than forcing extraction. [claim:clm_002]
Claimify identifies referential and structural ambiguity and, if any ambiguity is unresolvable, discards the entire sentence rather than emitting a possibly-wrong claim. [claim:clm_003]
The Selection stage uses an LLM to drop sentences with no verifiable content (e.g., opinion/speculation), retaining only verifiable components before later stages. [claim:clm_004]
The paper introduces a fact-checking-oriented evaluation framework whose two key innovations are a granular assessment of claim coverage and an outcome-based approach to evaluating decontextualization. [claim:clm_005]
The companion human-annotation study labeled 6,490 sentences for verifiable-claim content; the underlying BingCheck dataset is 396 Microsoft Copilot answers. [claim:clm_006]
Discarding is rare in practice: across experiments the largest share labeled "Cannot be disambiguated" was 5.4%, and only 0.8% of disambiguated sentences yielded no claims at Decomposition. [claim:clm_007]
ClaimPKG uses a lightweight, specialized LLM to represent a claim as pseudo-subgraphs that guide a dedicated retrieval module, while a general-purpose LLM then produces the final verdict and justification. [claim:clm_008]
On the FactKG dataset, ClaimPKG achieves state-of-the-art performance, outperforming strong baselines by 9-12 accuracy points across multiple categories. [claim:clm_009]
ClaimPKG demonstrates zero-shot generalizability to unstructured claim-verification datasets such as HoVer and FEVEROUS, combining KG structured knowledge with LLM reasoning across multiple LLM backbones. [claim:clm_010]
The paper motivates ClaimPKG by noting that modern LLMs, despite strong reasoning, struggle with multi-step modular pipelines and reasoning over knowledge graphs without adaptation. [claim:clm_011]
ClaimPKG was accepted to ACL 2025 Findings and submitted to arXiv on 28 May 2025 (arXiv:2505.22552). [claim:clm_012]
Traditional Knowledge Graphs treat facts as static and timeless, ignoring the temporal nature of many truths, which leads to outdated or incorrect inferences. [claim:clm_013]
The paper introduces what the authors describe as the first benchmark designed to evaluate temporal fact validation methods, addressing an underexplored gap distinct from predicting missing temporal facts. [claim:clm_014]
The benchmark is derived from Wikidata and supports systematic, quantitative, and qualitative comparisons across varying assumptions about temporal data and KG structures. [claim:clm_015]
The dataset is derived from the Wikidata dump of May 2023 and transformed into a temporal-validation task. [claim:clm_016]
Negative samples are produced by corrupting only the temporal context of true facts (keeping subject, predicate, and object fixed) so that models are evaluated specifically on temporal reasoning. [claim:clm_017]
The dataset ships in multiple configurations varying temporal scope, including a reduced dense scope (1900-2023) and a full sparser scope (-1000-2023). [claim:clm_018]
The benchmark artifacts are archived on Zenodo (record 15680977) with source code on GitHub (SoulardThibaut/WhenFactExpire); the paper is an ACM Open Access CIKM '25 short paper, pages 6534-6538. [claim:clm_019]
HALO is a low-cost outdated-fact filtering framework that quantifies the temporal validity of historical facts via half-life theory, rather than retraining the underlying model. [claim:clm_020]
HALO models a fact's temporal validity with exponential decay V(ti,tHF)=V0*e^(-lambda*(tc-ti)), where lambda is the decay rate derived from the fact's half-life. [claim:clm_021]
The half-life of a fact is defined as the time at which its validity has decreased to half of its initial value. [claim:clm_022]
HALO classifies facts as active or inactive and computes per-category half-lives, using the average update time interval; active facts that update more frequently have shorter half-lives (non-uniform decay). [claim:clm_023]
The half-life of active facts is derived from the average update time interval across the fact set. [claim:clm_024]
A fact is treated as outdated and filtered once its temporal influence falls below a predefined threshold theta (or it exceeds its expiration date). [claim:clm_025]
Applying HALO filtering raises RE-GCN on ICEWS14 from 37.67 to 41.38 MRR (+3.71) and 27.68 to 30.52 Hits@1 (+2.84). [claim:clm_026]
Applying HALO filtering raises CyGNet on ICEWS14 from 45.45 to 47.88 MRR (+2.43) and 37.46 to 41.24 Hits@1 (+3.78); HALO is evaluated over 5 baselines on ICEWS14, ICEWS18, and ICEWS05-15. [claim:clm_027]
AlignScore reframes factual-consistency evaluation as a general information-alignment function between two arbitrary text pieces, applicable across diverse inconsistency scenarios (contradictions, hallucinations) and input/output granularities. [claim:clm_028]
The alignment function is trained on 4.7M examples drawn from 7 well-established task types: NLI, QA, paraphrasing, fact verification, information retrieval, semantic similarity, and summarization. [claim:clm_029]
AlignScore is evaluated on 22 datasets, 19 of which were never seen during alignment training, demonstrating zero-shot generalization. [claim:clm_030]
The 355M-parameter AlignScore matches or outperforms factual-consistency metrics built on ChatGPT and GPT-4 despite those models being orders of magnitude larger. [claim:clm_031]
AlignScore is implemented by finetuning RoBERTa models at two sizes (125M and 355M), denoted AlignScore-base (RoBERTa-base) and AlignScore-large (RoBERTa-large). [claim:clm_032]
The alignment model has three heads (3-way classification, binary classification, and regression), and for inference the production metric uses the probability of the ALIGNED label from the 3-way classification head, which ablations show outperforms the binary and regression heads. [claim:clm_033]
Evaluation uses the TRUE benchmark (11 datasets across diverse domains) and the SummaC benchmark (6 large summarization datasets), plus additional latest factual-consistency testbeds. [claim:clm_034]
The paper targets the under-explored problem of LLM-based document inconsistency detection by investigating LLMs' evidence-extraction capabilities, not just binary contradiction yes/no. [claim:clm_035]
The two core contributions are new comprehensive evidence-extraction metrics and a redact-and-retry framework with constrained filtering that substantially improves evidence-extraction performance over other prompting methods. [claim:clm_036]
The authors release a new semi-synthetic dataset built for evaluating evidence extraction, alongside strong experimental results. [claim:clm_037]
The inconsistency-detection task is framed as both classifying whether an inconsistency is present and identifying the specific set of inconsistent sentences (evidence localization). [claim:clm_038]
The released semi-synthetic dataset, ContraDocPaired, is constructed from ContraDoc and adds datapoints with an evidence set of size two, addressing ContraDoc's limitation of only containing size-one evidence sets. [claim:clm_039]
Experiments use two LLMs at temperature 0 — GPT-4o (designated strong) and LLaMA3.2-90B (designated weak). [claim:clm_040]
The proposed redact-and-retry with constrained filtering (RnR+CF) is reported as the best-performing method across both datasets, both LLMs, and all metrics. [claim:clm_041]
The survey organizes knowledge conflicts in LLMs into three categories: context-memory, inter-context, and intra-memory conflict. [claim:clm_042]
Context-memory conflict is defined as contextual (input) knowledge conflicting with the parametric knowledge stored in the LLM's parameters. [claim:clm_043]
Inter-context conflict is defined as conflict among different pieces of contextual knowledge, i.e., contradictions among retrieved or source documents. [claim:clm_044]
Intra-memory conflict is defined as conflicting knowledge within the LLM's own parameters, arising from inconsistencies in pre-training data. [claim:clm_045]
The survey reports that LLMs tend to be highly receptive to external evidence even when it conflicts with their parametric memory. [claim:clm_046]
Under inter-context conflict, the survey notes LLMs can favor evidence that aligns with their parametric memory, qualifying the simple over-trust narrative. [claim:clm_047]
An LLM extracts entity nodes, relationship edges, and optional claim/covariate records from each source text chunk to build a graph index. [claim:clm_048]
Claims/covariates are extracted as structured factual statements about entities, such as dates, events, and interactions with other entities. [claim:clm_049]
Leiden community detection partitions the entity graph hierarchically into a nested hierarchy of closely-related-entity communities. [claim:clm_050]
Community summaries are generated bottom-up, with higher-level summaries recursively incorporating lower-level community summaries. [claim:clm_051]
The method was evaluated on global sensemaking over corpora in the ~1 million token range. [claim:clm_052]
On global sensemaking questions, GraphRAG beats naive (vector) RAG on LLM-judged comprehensiveness (72-83%) and diversity (75-82%) win rates. [claim:clm_053]
A gleaning loop re-prompts the LLM with already-extracted entities to recover missed ones, trading extra LLM calls (cost) for higher extraction recall. [claim:clm_054]
GraphRAG is released as an open-source reference implementation. [claim:clm_055]
GraphJudge uses the closed-source GPT-4o-mini in the denoising/extraction (ECTD) module and a fine-tuned open-source LLaMA-2-7B as the graph judge in the KASFT module. [claim:clm_056]
The graph-judgement step is defined as a triple-classification task that predicts a binary correct/incorrect label for each generated triple. [claim:clm_057]
On REBEL-Sub, GraphJudge reaches G-BERTScore-F1 0.5796 versus 0.4289 for GPT-4o-mini; on the domain-specific SCIERC it reaches 0.7283 versus 0.6882 for GPT-4o-mini. [claim:clm_058]
Ablating the graph-judgement module ('w/o GJ') drops REBEL-Sub G-BERTScore-F1 from 0.5796 to 0.4203, confirming the judge is the precision driver. [claim:clm_059]
Trained on GenWiki and tested on REBEL-Sub, GraphJudge scores G-BERTScore-F1 0.5814 versus 0.4163 for GPT-4o, evidence the judge generalizes across datasets. [claim:clm_060]
GraphJudge is cost-effective: it reaches state-of-the-art performance by fine-tuning only a 7B LLM, versus the 70B LLM used by the PiVe verification baseline. [claim:clm_061]
In a SCIERC case study the naive GPT-4o-mini KG contained meaningless triples such as <We, suggest, goal>, which the fine-tuned graph judge filtered out so they did not appear in the GraphJudge KG. [claim:clm_062]
The fine-tuned graph judge reaches over 90% judgement accuracy on REBEL-Sub and GenWiki, whereas un-tuned BERT and GPT-4o perform poorly on the same task. [claim:clm_063]
The study builds a synthetic dataset of 1,867 samples spanning four conflict classes: 37.49% no contradiction, 26.30% self, 19.07% pair, and 17.14% conditional. [claim:clm_064]
On a 140-example human validation study, two expert annotators reached only 74% inter-annotator agreement, indicating contradiction detection is hard even for people. [claim:clm_065]
On conflict detection, Claude-3 Sonnet+CoT scored highest at 0.710 accuracy, Llama3.3-70B basic next at 0.679, and Llama3.1-8B basic lowest at 0.380. [claim:clm_066]
Chain-of-thought prompting is architecture-dependent: it raised Claude-3 Sonnet by 31% (and Haiku 46%) but degraded Llama-70B by 26%. [claim:clm_067]
Difficulty follows a consistent hierarchy: pair contradictions easiest (Llama-70B basic 0.893), conditional moderate, and self-contradictions hardest, with accuracies from 0.006 to 0.456. [claim:clm_068]
Model size has mixed effects: in type detection the smaller Llama-8B outperformed the larger Llama-70B by about 6%, suggesting type detection rests on fundamental understanding rather than raw scale. [claim:clm_069]
Across all models, contradiction detection showed high precision but low recall, meaning models rarely false-flag but miss many real contradictions. [claim:clm_070]
Context validation over retrieved documents remains challenging even for state-of-the-art LLMs, with performance varying significantly across contradiction types. [claim:clm_071]
Unlike prior contradiction-detection work that examines only 1-2 documents, this study evaluates LLMs detecting conflicts across many retrieved documents. [claim:clm_072]
The paper defines three contradiction types - self-contradictory documents, contradicting document pairs, and conditional contradictions across a triplet - and a novel synthetic data generation framework simulating them in retrieved sets. [claim:clm_073]
Chain-of-thought prompting is architecture-dependent: it improved Claude (31% Sonnet, 46% Haiku) but degraded Llama-70B by 26% on conflict detection. [claim:clm_074]
On contradiction-type detection, CoT prompting unexpectedly decreased performance across most models, and the smaller Llama-8B beat the larger 70B by about 6%, suggesting type detection depends on fundamental understanding more than raw scale or reasoning prompts. [claim:clm_075]
All models showed high precision but low recall, meaning they are reliable when they flag a contradiction but miss many actual contradictions - a conservative bias relevant to a pre-generation validation gate. [claim:clm_076]
The work targets context-context conflicts (contradictions among retrieved documents), as opposed to context-memory conflicts between retrieval and parametric knowledge. [claim:clm_077]
MiniCheck builds small fact-checking models that the authors report reach GPT-4-level performance at 400x lower cost, trained on GPT-4-synthesized factual-error data. [claim:clm_078]
The best system, MiniCheck-FT5, has 770M parameters and is reported to outperform all systems of comparable size while reaching GPT-4 accuracy. [claim:clm_079]
For evaluation the authors introduce LLM-AggreFact, a unified benchmark that aggregates 10 existing datasets spanning both closed-book and grounded generation settings, with sentence-level factual errors labeled by human annotators. [claim:clm_080]
The task is framed as binary classification: each (document, claim) pair is scored, and a threshold (default t=0.5) maps the score to label 1 (supported) if above threshold and 0 (not supported) otherwise. [claim:clm_081]
Training data is produced by two synthetic generation methods: C2D (generate documents from human-written claims) and D2C (generate diverse, more realistic documents then derive claims to reduce train/test distribution shift). [claim:clm_082]
With automatic prefix caching (APC) enabled, inference over the 29K-example LLM-AggreFact test set takes about 30 minutes on a single NVIDIA A6000 (48 GB), versus about 55 minutes without caching. [claim:clm_083]
The released package ships multiple checkpoints selectable at scorer init: roberta-large, deberta-v3-large, flan-t5-large, and the state-of-the-art Bespoke-MiniCheck-7B. [claim:clm_084]

## Inferences

**Inference:** For RF's contradiction_log over heterogeneous source cards, the three viable detection families rank inter-context LLM claim-pair judging (Gokul et al.) first for genuine cross-document contradictions, fine-tuned alignment/entailment scorers (AlignScore-large 355M, MiniCheck-FT5 770M) second as a cheap support/refute gate, and KG-consistency checks (ClaimPKG, GraphJudge) third because they require an entity-linked graph that RF source cards do not yet provide. [claim:clm_inf01]
**Inference:** No single source reports both high precision and high recall for genuine factual contradiction detection: the only RF-relevant measured detection accuracy (Claude-3 Sonnet+CoT 0.710, Llama3.3-70B 0.679 on Gokul et al.) is paired with the explicit finding that all models are high-precision/low-recall, so RF should treat any LLM contradiction flag as a high-confidence positive but never treat a no-flag result as evidence of consistency. [claim:clm_inf02]
**Inference:** The cheap-extract / expensive-arbitrate split should place a fine-tuned 355M-770M alignment scorer (AlignScore-large or MiniCheck-FT5) as the cheap first-pass candidate-gate and reserve a frontier general-purpose LLM (GPT-4o or Claude-3 Sonnet) only for arbitrating candidate pairs the cheap scorer flags as non-aligned, mirroring ClaimPKG's lightweight-specialized-then-general split and GraphJudge's cheap-judge-after-strong-generator architecture. [claim:clm_inf03]
**Inference:** A concrete RF break-even rule is: run the 355M/770M cheap scorer on every candidate source-card pair (a 29K-pair sweep is ~30 min on one A6000 with prefix caching per MiniCheck), then escalate to an expensive LLM arbiter only for pairs scoring below the alignment threshold (default t=0.5), which keeps frontier-LLM spend proportional to the suspected-contradiction rate rather than to the full O(n^2) pair count. [claim:clm_inf04]
**Inference:** Naive all-pairs contradiction checking is O(n^2) in source cards and becomes the dominant cost as the card set grows; RF should gate candidate pairs with embedding-similarity blocking and entity-resolution before any LLM call, reusing the same candidate-retrieval idea that ClaimPKG uses to retrieve only relevant KG subgraphs rather than scanning the whole graph. [claim:clm_inf05]
**Inference:** Source heterogeneity (web vs PDF vs papers vs personal notes) must be normalized into atomic, decontextualized, verifiable claims before any pairwise comparison, because contradiction and alignment scorers operate on claim/sentence pairs, not raw documents; Claimify's four-stage Selection-Disambiguation-Decomposition pipeline is the recommended normalizer and its conservative ambiguity-discarding lowers false contradictions at the cost of some coverage. [claim:clm_inf06]
**Inference:** Claimify's reported discard rates (<=5.4% 'Cannot be disambiguated', 0.8% yielding no claims) indicate the normalization step is cheap in lost coverage, so RF can adopt high-confidence-only claim extraction as the default front end without materially shrinking the contradiction-comparison corpus. [claim:clm_inf07]
**Inference:** A genuine factual contradiction must be distinguished from differing temporal context: the same subject-predicate-object asserted at two different valid-times is not a contradiction but a temporal succession, exactly the corruption-of-temporal-context-only design used by the When-Facts-Expire benchmark, so RF's comparison must condition on a valid_time/as_of field before declaring conflict. [claim:clm_inf08]
**Inference:** Stale-claim flagging in RF's source-card KG is best handled by HALO-style half-life decay rather than LLM re-judging: a per-claim validity V=V0*e^(-lambda*(tc-ti)) with category-specific half-lives lets RF down-weight or expire a claim once V falls below a threshold theta at near-zero marginal cost, and HALO's measured +2.4-3.7 MRR gains show staleness filtering improves downstream reasoning. [claim:clm_inf09]
**Inference:** Conflicting-claim flagging and stale-claim flagging are separable subsystems in RF: contradiction detection (NLI/LLM-judge) answers 'do two current claims disagree' while temporal validity (HALO half-life, When-Facts-Expire validation) answers 'is this claim still in force', and conflating them causes the false-contradiction failure mode that motivated the temporal-KG benchmarks. [claim:clm_inf10]
**Inference:** Orphaned-claim flagging maps onto GraphJudge's triple-classification: a claim node with no supporting source card or no resolvable entity edge is the analogue of GraphJudge's 'incorrect' triple (e.g., the filtered <We, suggest, goal>), so RF can flag orphans with a binary correct/incorrect judge, and GraphJudge's evidence that a fine-tuned 7B judge reaches >90% accuracy while un-tuned GPT-4o fails suggests RF needs a tuned judge, not a zero-shot frontier model, for this step. [claim:clm_inf11]
**Inference:** The reliable-enough-to-auto-resolve versus surface-for-human boundary should be drawn at the precision/recall asymmetry: an LLM-judge contradiction flag (high precision) plus an agreeing cheap alignment scorer can auto-populate the contradiction_log entry, but self-contradiction and conditional-contradiction classes (Llama-70B 0.006-0.456 accuracy) and any single-signal flag must be routed to human adjudication. [claim:clm_inf12]
**Inference:** Prompting strategy in RF's arbitration step must be model-conditioned: chain-of-thought raised Claude-3 Sonnet detection by 31% (Haiku 46%) but degraded Llama-70B by 26%, so RF should enable CoT for Claude-family arbiters and disable it for Llama-family arbiters rather than applying a uniform prompt template. [claim:clm_inf13]
**Inference:** RF's contradiction_log should be evidence-localized, not binary: following the document-inconsistency-detection finding that pinpointing the inconsistent sentence set (RnR+CF best across both LLMs) beats yes/no detection, each contradiction_log entry should store the specific conflicting claim ids and their source-card evidence ids rather than only a conflict boolean. [claim:clm_inf14]
**Inference:** A traceable contradiction_log schema for RF is: contradiction_id; claim_a_id and claim_b_id (RF claim ids); source_card_a and source_card_b with evidence_ids; conflict_type {pair|self|conditional} (Gokul taxonomy); distinction_axis {factual|scope|temporal|measurement_basis}; valid_time_a / valid_time_b and as_of (temporal guard); detector {nli_score|llm_judge|kg_judge} with detector_score and threshold; resolution_status {auto_resolved|needs_human|resolved}; and adjudicator_note - every field tracing to a cited mechanism. [claim:clm_inf15]
**Inference:** The distinction between genuine contradiction and scope/measurement-basis difference is encodable as explicit qualifier fields on each claim (e.g., scope_qualifier, measurement_basis, unit/dataset, population) so that two claims are only compared as potential contradictions when their qualifier tuples match; this operationalizes the survey's observation that inter-context conflict is real only among comparable contextual statements. [claim:clm_inf16]

## Speculation

**Speculation:** Because the only measured cross-document contradiction accuracies (0.71 best, self-contradiction as low as 0.006) come from synthetic Claude-3/Llama datasets, RF's contradiction recall on real heterogeneous source cards will likely be materially lower than these benchmarks until a frontier 2026-class arbiter (GPT-4o-class or newer) and an RF-specific evaluation set are validated live. [claim:clm_spec01]
**Speculation:** A pragmatic RF v1 should ship the cheap-gate-only path (AlignScore-large or MiniCheck-FT5 candidate scoring plus HALO staleness decay) and defer KG-judge orphan detection to v2, on the assumption that building an entity-linked source-card graph is higher-effort than thresholded pair scoring and that RF's near-term value is catching the high-precision contradictions the cheap scorer plus a frontier arbiter already surface. [claim:clm_spec02]

## Open questions

- None recorded.

## Sources

- src_20260614_rib003_10: Towards Effective Extraction and Evaluation of Factual Claims (Claimify)
- src_20260614_rib003_02: ClaimPKG: Enhancing Claim Verification via Pseudo-Subgraph Generation with Lightweight Specialized LLM
- src_20260614_rib003_09: When Facts Expire: Benchmarking Temporal Validity in Knowledge Graphs
- src_20260614_rib003_08: HALO: Half Life-Based Outdated Fact Filtering in Temporal Knowledge Graphs
- src_20260614_rib003_01: AlignScore: Evaluating Factual Consistency with a Unified Alignment Function
- src_20260614_rib003_07: Improved Evidence Extraction and Metrics for Document Inconsistency Detection with LLMs
- src_20260614_rib003_05: Knowledge Conflicts for LLMs: A Survey
- src_20260614_rib003_03: From Local to Global: A Graph RAG Approach to Query-Focused Summarization
- src_20260614_rib003_04: Can LLMs be Good Graph Judge for Knowledge Graph Construction?
- src_20260614_rib003_11: Contradiction Detection in RAG Systems: Evaluating LLMs as Context Validators for Improved Information Consistency
- src_20260614_rib003_06: Contradiction Detection in RAG Systems: Evaluating LLMs as Context Validators for Improved Information Consistency
- src_20260614_rib003_00: MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents
