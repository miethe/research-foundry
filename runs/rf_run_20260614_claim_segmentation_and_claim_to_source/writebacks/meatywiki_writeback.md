---
id: mwb_20260614_claim_segmentation_and_claim_to_source
evidence_bundle_id: bundle_20260614_intent_research_20260614_claim_segmentation_and
target_page: meatywiki/sources/claim_segmentation_and_claim_to_source.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_claim_segmentation_and_claim_to_source:
  79 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_078
  include: true
- claim_id: clm_079
  include: true
links:
  source_cards:
  - src_20260614_rib001_00
  - src_20260614_rib001_01
  - src_20260614_rib001_02
  - src_20260614_rib001_03
  - src_20260614_rib001_04
  - src_20260614_rib001_05
  - src_20260614_rib001_06
  - src_20260614_rib001_07
  - src_20260614_rib001_08
  - src_20260614_rib001_09
  - src_20260614_rib001_10
  - src_20260614_rib001_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Claim segmentation and claim-to-source alignment for RF verification

## Summary

Source note distilled from research run rf_run_20260614_claim_segmentation_and_claim_to_source: 79 supported claim(s) across 12 source card(s).

## Key claims

- Factuality metrics like FActScore are sensitive to the decomposition step, so an error attributed to the generating model can actually originate in the metric's decomposition. [claim:clm_001]
- FActScore can change for the same underlying generated text depending on the characteristics (e.g., atomicity) of the decomposition method used. [claim:clm_002]
- Decomposition quality requires subclaims to be coherent/faithful to the original claim (supported or entailed by it). [claim:clm_003]
- For localizing discrepancies against a trusted reference, subclaims should cover all parts of the claim and be as atomic as possible (coverage + atomicity). [claim:clm_004]
- DecompScore is defined as the average number of supported subclaims per passage produced by a decomposition method, validated against the original passage rather than external knowledge. [claim:clm_005]
- Atomic-fact yield per biography varies widely by decomposition method: Russellian/Neo-Davidsonian 42.3, FActScore/Chen et al. ~32, PredPatt 29.2, CoNLL-U 27.1, WiCE 20.0, showing the splitter materially changes claim yield on identical text. [claim:clm_006]
- Attributed QA (AQA) is framed as a key first step toward attributed LLMs, with the dataset comprising human-rated system outputs for the task. [claim:clm_007]
- In the AQA task the input is a question and the output is an (answer, attribution) pair where the answer is a string. [claim:clm_008]
- Attribution is defined as a pointer into a fixed underlying corpus, making claim-to-source linking the core mechanism. [claim:clm_009]
- The attribution must supply supporting evidence for the answer and satisfy the AIS (Attributable to Identified Sources) conditions. [claim:clm_010]
- The release contains 83,030 instances (3,610 examples x 23 systems) over a fixed Wikipedia snapshot taken on 2021-10-13. [claim:clm_011]
- The accompanying paper treats human attribution annotations as the gold standard and shows that a correlated automatic metric (AutoAIS) is suitable for development, validating automatic AIS scoring against gold labels. [claim:clm_012]
- Decomposition and decontextualization have conflicting purposes that create a tension a verification system must resolve: decomposition isolates atomic facts while decontextualization re-inserts relevant context. [claim:clm_013]
- A decontextualized subclaim becomes less atomic and creates a verification ambiguity over which of the multiple embedded atomic facts should actually be checked. [claim:clm_014]
- The original FActScore (decompose-then-verify) method yields an average factuality score of 33.00% on the benchmark, serving as the baseline. [claim:clm_015]
- DnDScore is highest under the Decontextualization-then-Decomposition configuration (decontextualized claim used as context), reaching 61.51%. [claim:clm_016]
- The Decontextualization-then-Decomposition pipeline generates the highest number of subclaims yet lands near the same FActScore as Decomposition-then-Decontextualization, at 44.60%. [claim:clm_017]
- Among judgments that switched from false to true after decontextualizing subclaims, 48.52% involved a pronoun replacement, indicating entity disambiguation is a primary driver of corrected verifications. [claim:clm_018]
- VeriFastScore fine-tunes Llama-3.1-8B to extract and verify all verifiable claims in a text simultaneously, using evidence from Google Search. [claim:clm_019]
- VeriFastScore correlates strongly with the original VeriScore pipeline (r=0.80 example level, r=0.94 system level) while achieving a 6.6x overall speedup (9.9x excluding evidence retrieval). [claim:clm_020]
- Retrieving evidence at a coarser granularity cuts API costs by 39% and reduces retrieval time by almost half. [claim:clm_021]
- Decompose-then-verify factuality metrics like FactScore and VeriScore can take upwards of 100 seconds per response due to numerous LLM calls, limiting large-scale use. [claim:clm_022]
- The combined extract-and-verify task is hard for few-shot prompting because the model must process ~4K tokens of evidence and concurrently decompose, judge verifiability, and verify against noisy evidence. [claim:clm_023]
- Training data was a synthetic dataset built by running responses through the VeriScore pipeline to decompose them into verifiable claims and assign verification labels. [claim:clm_024]
- Fact-checking LLM text commonly proceeds by claim extraction, breaking text into simple factual statements that can be verified independently. [claim:clm_025]
- Claimify's Selection stage uses an LLM to drop sentences without verifiable content, labeling them 'No verifiable claims' and excluding them from later stages. [claim:clm_026]
- In Disambiguation, if context cannot resolve all ambiguity the sentence is labeled 'Cannot be disambiguated' rather than forced into a claim. [claim:clm_027]
- The Decomposition stage has an LLM create standalone claims that preserve critical context from the disambiguated sentences. [claim:clm_028]
- Claimify is described as the first claim extraction system that detects multiple possible interpretations and extracts claims only when confident in the correct one. [claim:clm_029]
- A core Claimify principle is that each extracted claim must be fully supported (entailed) by the source text. [claim:clm_030]
- Evaluation found that 99% of claims extracted by Claimify are entailed by their source sentence, indicating high decontextualization fidelity. [claim:clm_031]
- The work was accepted to ACL 2025 in a paper titled 'Towards Effective Extraction and Evaluation of Factual Claims', which also shows Claimify outperforms existing LLM-based methods. [claim:clm_032]
- CAQA defines a four-level attribution complexity taxonomy where Union, Intersection, and Concatenation are the multi-hop/aggregated cases requiring facts from multiple citations. [claim:clm_033]
- CAQA defines four attribution categories beyond binary support, including an explicit Partially Supportive label where the evidence lacks some required facts. [claim:clm_034]
- GPT-4 zero-shot F1 degrades on the aggregated multi-hop cases, dropping to 0.451 on Concatenation and 0.514 on Intersection. [claim:clm_035]
- All evaluators consistently underperform on the nuanced negative categories, with Partially Supportive being the hardest verdict to detect automatically. [claim:clm_036]
- Evaluators rely on keyword co-occurrence rather than semantic reasoning and systematically misclassify partially-supported claims as supportive. [claim:clm_037]
- The KG-generated CAQA benchmark contains 161,174 samples, and fine-tuned detectors exceed 90% F1, indicating the zero-shot failure is an evaluator-capability gap rather than an unverifiable task. [claim:clm_038]
- RAGTruth defines Evident Conflict as RAG output that directly contradicts the retrieved source content, which is easily verifiable. [claim:clm_039]
- Subtle Conflict is a divergence from the source that alters the intended contextual meaning rather than a blatant contradiction. [claim:clm_040]
- RAGTruth distinguishes evident baseless information (unsubstantiated content) from subtle baseless information defined as inferred details, insights, or sentiments beyond the source. [claim:clm_041]
- The corpus comprises roughly 18,000 naturally generated RAG responses from diverse LLMs, manually annotated at both case and word levels. [claim:clm_042]
- The 2,965 annotated instances split into 989 question answering, 1,033 data-to-text writing, and 943 news summarization cases (17,790 total responses). [claim:clm_043]
- Detecting evident hallucinations is markedly more effective than detecting subtle hallucinations, implying subtle-conflict and subtle-baseless cases are the hardest to auto-verify. [claim:clm_044]
- Span-level hallucination detection is hard: GPT-4-turbo reaches only 18.4% precision while a fine-tuned Llama-2-13B reaches 52.7% F1, motivating routing low-confidence span verdicts to review. [claim:clm_045]
- Decompose-Then-Verify factual-precision metrics such as FActScore can be manipulated to inflate scores by adding obvious or repetitive subclaims. [claim:clm_046]
- Core is a customizable plug-and-play subclaim selection component that filters subclaims by their uniqueness and informativeness. [claim:clm_047]
- Core formalizes subclaim selection as a constrained optimization problem rather than an ad-hoc filter. [claim:clm_048]
- Factual-precision metrics augmented by Core are substantially more robust across a wide range of knowledge domains. [claim:clm_049]
- Core is designed as a drop-in replacement for the decomposition component of existing factual-precision evaluation pipelines. [claim:clm_050]
- The authors release a modular evaluation framework supporting Core plus swappable decomposition strategies, and an expanded FActScore biography dataset. [claim:clm_051]
- The paper introduces 'atomicity' as a novel metric quantifying the information density of a decomposed claim. [claim:clm_052]
- Existing decomposition policies, typically hand-crafted demonstrations, misalign with downstream verifiers in atomicity, yielding suboptimal verification. [claim:clm_053]
- The authors frame finding the optimal decomposition policy for optimal verification as a strongly NP-hard bilevel optimization problem. [claim:clm_054]
- 'Dynamic decomposition' is a reinforcement learning framework that uses verifier feedback to learn a policy for decomposing claims to verifier-preferred atomicity. [claim:clm_055]
- Dynamic decomposition improves verification confidence by 0.07 and accuracy by 0.12 (0-1 scale) on average across varying verifiers, datasets, and input atomicities. [claim:clm_056]
- The official implementation is released publicly as the ACL 2025 paper's experiment repository. [claim:clm_057]
- The work is published in the ACL 2025 Long Papers proceedings, pages 5095-5114, with DOI 10.18653/v1/2025.acl-long.254. [claim:clm_058]
- CiteME's alignment unit is claim-to-single-source: it is the first manually curated citation-attribution benchmark whose text excerpts each unambiguously reference a single specific paper. [claim:clm_059]
- Unaided frontier LMs reach only 4.2-18.5% accuracy on CiteME versus 69.7% for human experts, and CiteAgent (a GPT-4o autonomous agent that can search and read papers) closes much of the gap at 35.3%. [claim:clm_060]
- Prior state-of-the-art retrieval systems SPECTER2 and SPECTER score 0% on CiteME, and even CiteAgent's best 35.3% leaves a 34.4% gap below the 69.7% human accuracy. [claim:clm_061]
- CiteME is adversarially filtered: instances GPT-4o could answer from memory (no internet/tools, 5 runs) were removed, dropping 124 samples to leave 130 total. [claim:clm_062]
- Human accuracy of 69.7% was measured on 100 samples by 20 experts not involved in construction, each given a 2-minute cap and averaging 38.2 seconds per item, so it likely understates maximum human performance. [claim:clm_063]
- Excerpts were curated by 4 ML graduate students to reference a single paper with enough context to find it, and 'trivial' excerpts containing author names or title acronyms (which merely test memorization/retrieval) were excluded. [claim:clm_064]
- A later evaluation reports GPT-o1 scoring 61.3% on CiteME, but the authors estimate it had memorized roughly 38.7% of the dataset, inflating its apparent attribution skill. [claim:clm_065]
- VeriScore extracts only verifiable claims, unlike FActScore and SAFE which decompose every sentence including unverifiable content; FActScore and SAFE assume all claims are verifiable and extract examples and hypotheticals, unfairly penalizing models. [claim:clm_066]
- Verifiable-claim density per sentence varies ~77x by genre: WritingPrompts fiction outputs average 0.03 verifiable claims/sentence versus FreshBooks nonfiction at 2.31, so low verifiable density signals opinion/creative rather than factual material. [claim:clm_067]
- In the human verification study, only 55% of VeriScore-extracted claims were judged supported against retrieved evidence, leaving a large residual unsupported/inconclusive band. [claim:clm_068]
- Human raters preferred VeriScore's one-step extraction over SAFE's two-step extract-and-revise pipeline 93% of the time; SAFE was preferred only 26 of 360 times, 19 of those marginally, and VeriScore drops SAFE's expensive revision step. [claim:clm_069]
- Open-domain claim verification fails on complex, non-entity-centric claims: verifying support requires extensive reasoning over the connection between claim parts rather than exact or related term matching against search snippets. [claim:clm_070]
- VeriScore cannot reliably decide whether an unsupported complex claim is a hallucination because that judgment exceeds what reasoning over search snippets can achieve, indicating such claims should route to review or an inference label. [claim:clm_071]
- LongCite defines the citation unit as fine-grained sentence-level, where each cited snippet references a specific sentence or a span of sentences in the source document. [claim:clm_072]
- On LongBench-Cite, LongCite-8B achieves citation F1 72.0 (recall 62.0, precision 79.7) and LongCite-9B achieves F1 69.2 (recall 57.6, precision 78.1). [claim:clm_073]
- The trained LongCite models surpass proprietary baselines on citation quality: GPT-4o scores F1 65.6 (recall 46.7, precision 53.5) and Claude-3-Sonnet scores F1 67.2 (recall 52.0, precision 67.8). [claim:clm_074]
- Citation recall scores each cited statement 1 / 0.5 / 0 for full / partial / no support of the statement by its concatenated cited snippets, judged by GPT-4o. [claim:clm_075]
- A cited snippet is marked relevant for precision if it at least partially entails a key point of the statement it supports. [claim:clm_076]
- The GPT-4o-as-judge evaluator aligns with human annotators at Cohen's kappa 0.593 for recall and 0.655 for precision. [claim:clm_077]
- The Coarse-to-Fine (CoF) pipeline uses off-the-shelf LLMs to auto-generate the LongCite-45k SFT dataset (44,600 instances) via a four-stage query/answer, coarse chunk-citation, fine sentence-citation, and filtering process. [claim:clm_078]
- Citation F1 is the harmonic mean of citation precision (P) and citation recall (R), computed as F1 = 2*P*R / (P+R). [claim:clm_079]

## Sources

- src_20260614_rib001_00 — Claimify: Extracting high-quality claims from language model outputs
- src_20260614_rib001_01 — DnDScore: Decontextualization and Decomposition for Factuality Verification in Long-Form Text Generation
- src_20260614_rib001_02 — Core: Robust Factual Precision with Informative Sub-Claim Identification
- src_20260614_rib001_03 — A Closer Look at Claim Decomposition
- src_20260614_rib001_04 — Optimizing Decomposition for Optimal Claim Verification
- src_20260614_rib001_05 — VeriFastScore: Speeding up long-form factuality evaluation
- src_20260614_rib001_06 — LongCite: Enabling LLMs to Generate Fine-grained Citations in Long-context QA
- src_20260614_rib001_07 — CiteME: Can Language Models Accurately Cite Scientific Claims?
- src_20260614_rib001_08 — google-research-datasets/Attributed-QA (Attributed Question Answering dataset)
- src_20260614_rib001_09 — RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models
- src_20260614_rib001_10 — Can LLMs Evaluate Complex Attribution in QA? Automatic Benchmarking using Knowledge Graphs
- src_20260614_rib001_11 — VeriScore: Evaluating the factuality of verifiable claims in long-form text generation

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
