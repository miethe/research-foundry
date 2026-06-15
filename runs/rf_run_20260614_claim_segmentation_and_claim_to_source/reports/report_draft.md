---
schema_version: '0.1'
type: research_report
report_id: report_20260614_claim_segmentation_and_claim_to_source
title: Claim segmentation and claim-to-source alignment for RF verification
intent_id: intent_research_20260614_claim_segmentation_and_claim_to_source
evidence_bundle_id: pending
created_at: '2026-06-14T21:02:34-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Claim segmentation and claim-to-source alignment for RF verification

## Executive summary

Factuality metrics like FActScore are sensitive to the decomposition step, so an error attributed to the generating model can actually originate in the metric's decomposition. [claim:clm_001] FActScore can change for the same underlying generated text depending on the characteristics (e.g., atomicity) of the decomposition method used. [claim:clm_002] Atomic-fact yield per biography varies widely by decomposition method: Russellian/Neo-Davidsonian 42.3, FActScore/Chen et al. ~32, PredPatt 29.2, CoNLL-U 27.1, WiCE 20.0, showing the splitter materially changes claim yield on identical text. [claim:clm_006]

**Inference:** Claim segmentation in RF must fix and version a single decomposition method, because identical text yields between 20.0 (WiCE) and 42.3 (Russellian/Neo-Davidsonian) atomic facts depending on the splitter, and FActScore itself shifts with atomicity, so any unversioned splitter change would silently break re-runnable alignment and verification audits. [claim:clm_inf03]

On the alignment side, automated claim-to-source alignment precision currently tops out around 80%. **Inference:** Automated claim-to-source alignment precision currently tops out around 80% (LongCite-8B precision 79.7 on sentence-level citation), so RF should treat ~80% precision as the practical ceiling before human review and not assume near-perfect attribution from any single automated aligner. [claim:clm_inf06] **Inference:** Citation-attribution remains genuinely below human level for hard cases, so RF must keep a human-review tier indefinitely: the best autonomous agent (CiteAgent on GPT-4o) reaches only 35.3% on adversarially filtered CiteME versus 69.7% for time-capped human experts, a 34.4-point gap, and reported higher scores (GPT-o1 61.3%) are inflated by ~38.7% dataset memorization. [claim:clm_inf15]

## Segmentation techniques and decomposition fidelity

Fact-checking LLM text commonly proceeds by claim extraction, breaking text into simple factual statements that can be verified independently. [claim:clm_025] Decomposition quality requires subclaims to be coherent/faithful to the original claim (supported or entailed by it). [claim:clm_003] For localizing discrepancies against a trusted reference, subclaims should cover all parts of the claim and be as atomic as possible (coverage + atomicity). [claim:clm_004] DecompScore is defined as the average number of supported subclaims per passage produced by a decomposition method, validated against the original passage rather than external knowledge. [claim:clm_005]

Claimify is the most decontextualization-faithful staged extractor in the survey. Claimify's Selection stage uses an LLM to drop sentences without verifiable content, labeling them 'No verifiable claims' and excluding them from later stages. [claim:clm_026] In Disambiguation, if context cannot resolve all ambiguity the sentence is labeled 'Cannot be disambiguated' rather than forced into a claim. [claim:clm_027] The Decomposition stage has an LLM create standalone claims that preserve critical context from the disambiguated sentences. [claim:clm_028] Claimify is described as the first claim extraction system that detects multiple possible interpretations and extracts claims only when confident in the correct one. [claim:clm_029] A core Claimify principle is that each extracted claim must be fully supported (entailed) by the source text. [claim:clm_030] Evaluation found that 99% of claims extracted by Claimify are entailed by their source sentence, indicating high decontextualization fidelity. [claim:clm_031] The work was accepted to ACL 2025 in a paper titled 'Towards Effective Extraction and Evaluation of Factual Claims', which also shows Claimify outperforms existing LLM-based methods. [claim:clm_032]

VeriScore is the verifiability-filtering extractor. VeriScore extracts only verifiable claims, unlike FActScore and SAFE which decompose every sentence including unverifiable content; FActScore and SAFE assume all claims are verifiable and extract examples and hypotheticals, unfairly penalizing models. [claim:clm_066] Verifiable-claim density per sentence varies ~77x by genre: WritingPrompts fiction outputs average 0.03 verifiable claims/sentence versus FreshBooks nonfiction at 2.31, so low verifiable density signals opinion/creative rather than factual material. [claim:clm_067] Human raters preferred VeriScore's one-step extraction over SAFE's two-step extract-and-revise pipeline 93% of the time; SAFE was preferred only 26 of 360 times, 19 of those marginally, and VeriScore drops SAFE's expensive revision step. [claim:clm_069] In the human verification study, only 55% of VeriScore-extracted claims were judged supported against retrieved evidence, leaving a large residual unsupported/inconclusive band. [claim:clm_068]

Core is the subclaim-selection technique that hardens metrics against gaming. Decompose-Then-Verify factual-precision metrics such as FActScore can be manipulated to inflate scores by adding obvious or repetitive subclaims. [claim:clm_046] Core is a customizable plug-and-play subclaim selection component that filters subclaims by their uniqueness and informativeness. [claim:clm_047] Core formalizes subclaim selection as a constrained optimization problem rather than an ad-hoc filter. [claim:clm_048] Factual-precision metrics augmented by Core are substantially more robust across a wide range of knowledge domains. [claim:clm_049] Core is designed as a drop-in replacement for the decomposition component of existing factual-precision evaluation pipelines. [claim:clm_050] The authors release a modular evaluation framework supporting Core plus swappable decomposition strategies, and an expanded FActScore biography dataset. [claim:clm_051]

Dynamic decomposition treats atomicity as a learnable target. The paper introduces 'atomicity' as a novel metric quantifying the information density of a decomposed claim. [claim:clm_052] Existing decomposition policies, typically hand-crafted demonstrations, misalign with downstream verifiers in atomicity, yielding suboptimal verification. [claim:clm_053] The authors frame finding the optimal decomposition policy for optimal verification as a strongly NP-hard bilevel optimization problem. [claim:clm_054] 'Dynamic decomposition' is a reinforcement learning framework that uses verifier feedback to learn a policy for decomposing claims to verifier-preferred atomicity. [claim:clm_055] Dynamic decomposition improves verification confidence by 0.07 and accuracy by 0.12 (0-1 scale) on average across varying verifiers, datasets, and input atomicities. [claim:clm_056] The official implementation is released publicly as the ACL 2025 paper's experiment repository. [claim:clm_057] The work is published in the ACL 2025 Long Papers proceedings, pages 5095-5114, with DOI 10.18653/v1/2025.acl-long.254. [claim:clm_058]

### Segmentation technique comparison

| Technique | Distinguishing mechanism | Measured fidelity / yield signal | Evidence |
|-----------|--------------------------|----------------------------------|----------|
| Claimify (staged) | Selection + Disambiguation + Decomposition with explicit abstention | 99% of extracted claims entailed by source sentence | [claim:clm_031] |
| VeriScore (verifiability filter) | Extracts only verifiable claims; drops unverifiable content | 55% of extracted claims judged supported vs retrieved evidence | [claim:clm_068] |
| VeriScore (density signal) | Per-sentence verifiable-claim density as a routing signal | 0.03 (fiction) vs 2.31 (nonfiction) claims/sentence, ~77x range | [claim:clm_067] |
| Core (subclaim selection) | Uniqueness/informativeness filter as constrained optimization | More robust across knowledge domains vs ungated decompose-then-verify | [claim:clm_049] |
| Dynamic decomposition (RL) | Learns verifier-preferred atomicity from verifier feedback | +0.07 confidence, +0.12 accuracy (0-1) across verifiers/datasets | [claim:clm_056] |
| Splitter family (yield) | Russellian / FActScore / PredPatt / CoNLL-U / WiCE on identical text | 42.3 / ~32 / 29.2 / 27.1 / 20.0 atomic facts per biography | [claim:clm_006] |

**Inference:** Of the surveyed segmenters, Claimify is the best fit for RF's pre-verification stage because its staged Selection-Disambiguation-Decomposition design achieves 99% source-sentence entailment and explicitly abstains on irreducibly ambiguous sentences, directly satisfying RF's invariant that every extracted claim be entailed or labeled rather than forced. [claim:clm_inf01]

**Inference:** RF should adopt VeriScore-style verifiable-claim filtering as the first segmentation step, using per-sentence verifiable-claim density (e.g., the ~0.03 vs 2.31 fiction-vs-nonfiction split) as a cheap routing signal to send low-density passages to an 'unverifiable/opinion' bucket rather than into the claim ledger. [claim:clm_inf02]

## Claim-to-source alignment techniques and measured precision/recall

Attribution is defined as a pointer into a fixed underlying corpus, making claim-to-source linking the core mechanism. [claim:clm_009] The attribution must supply supporting evidence for the answer and satisfy the AIS (Attributable to Identified Sources) conditions. [claim:clm_010] In the AQA task the input is a question and the output is an (answer, attribution) pair where the answer is a string. [claim:clm_008] Attributed QA (AQA) is framed as a key first step toward attributed LLMs, with the dataset comprising human-rated system outputs for the task. [claim:clm_007] The release contains 83,030 instances (3,610 examples x 23 systems) over a fixed Wikipedia snapshot taken on 2021-10-13. [claim:clm_011] The accompanying paper treats human attribution annotations as the gold standard and shows that a correlated automatic metric (AutoAIS) is suitable for development, validating automatic AIS scoring against gold labels. [claim:clm_012]

LongCite supplies the strongest measured sentence-level aligner. LongCite defines the citation unit as fine-grained sentence-level, where each cited snippet references a specific sentence or a span of sentences in the source document. [claim:clm_072] On LongBench-Cite, LongCite-8B achieves citation F1 72.0 (recall 62.0, precision 79.7) and LongCite-9B achieves F1 69.2 (recall 57.6, precision 78.1). [claim:clm_073] The trained LongCite models surpass proprietary baselines on citation quality: GPT-4o scores F1 65.6 (recall 46.7, precision 53.5) and Claude-3-Sonnet scores F1 67.2 (recall 52.0, precision 67.8). [claim:clm_074] Citation recall scores each cited statement 1 / 0.5 / 0 for full / partial / no support of the statement by its concatenated cited snippets, judged by GPT-4o. [claim:clm_075] A cited snippet is marked relevant for precision if it at least partially entails a key point of the statement it supports. [claim:clm_076] Citation F1 is the harmonic mean of citation precision (P) and citation recall (R), computed as F1 = 2*P*R / (P+R). [claim:clm_079] The GPT-4o-as-judge evaluator aligns with human annotators at Cohen's kappa 0.593 for recall and 0.655 for precision. [claim:clm_077] The Coarse-to-Fine (CoF) pipeline uses off-the-shelf LLMs to auto-generate the LongCite-45k SFT dataset (44,600 instances) via a four-stage query/answer, coarse chunk-citation, fine sentence-citation, and filtering process. [claim:clm_078]

CiteME measures the hard single-source attribution ceiling against humans. CiteME's alignment unit is claim-to-single-source: it is the first manually curated citation-attribution benchmark whose text excerpts each unambiguously reference a single specific paper. [claim:clm_059] Unaided frontier LMs reach only 4.2-18.5% accuracy on CiteME versus 69.7% for human experts, and CiteAgent (a GPT-4o autonomous agent that can search and read papers) closes much of the gap at 35.3%. [claim:clm_060] Prior state-of-the-art retrieval systems SPECTER2 and SPECTER score 0% on CiteME, and even CiteAgent's best 35.3% leaves a 34.4% gap below the 69.7% human accuracy. [claim:clm_061] CiteME is adversarially filtered: instances GPT-4o could answer from memory (no internet/tools, 5 runs) were removed, dropping 124 samples to leave 130 total. [claim:clm_062] Excerpts were curated by 4 ML graduate students to reference a single paper with enough context to find it, and 'trivial' excerpts containing author names or title acronyms (which merely test memorization/retrieval) were excluded. [claim:clm_064] Human accuracy of 69.7% was measured on 100 samples by 20 experts not involved in construction, each given a 2-minute cap and averaging 38.2 seconds per item, so it likely understates maximum human performance. [claim:clm_063] A later evaluation reports GPT-o1 scoring 61.3% on CiteME, but the authors estimate it had memorized roughly 38.7% of the dataset, inflating its apparent attribution skill. [claim:clm_065]

CAQA measures attribution complexity. CAQA defines a four-level attribution complexity taxonomy where Union, Intersection, and Concatenation are the multi-hop/aggregated cases requiring facts from multiple citations. [claim:clm_033] CAQA defines four attribution categories beyond binary support, including an explicit Partially Supportive label where the evidence lacks some required facts. [claim:clm_034] GPT-4 zero-shot F1 degrades on the aggregated multi-hop cases, dropping to 0.451 on Concatenation and 0.514 on Intersection. [claim:clm_035] All evaluators consistently underperform on the nuanced negative categories, with Partially Supportive being the hardest verdict to detect automatically. [claim:clm_036] Evaluators rely on keyword co-occurrence rather than semantic reasoning and systematically misclassify partially-supported claims as supportive. [claim:clm_037] The KG-generated CAQA benchmark contains 161,174 samples, and fine-tuned detectors exceed 90% F1, indicating the zero-shot failure is an evaluator-capability gap rather than an unverifiable task. [claim:clm_038]

### Alignment technique precision/recall matrix

| Aligner / setting | Alignment unit | Precision | Recall | F1 / accuracy | Evidence |
|-------------------|----------------|-----------|--------|---------------|----------|
| LongCite-8B (trained) | Sentence-level citation | 79.7 | 62.0 | F1 72.0 | [claim:clm_073] |
| LongCite-9B (trained) | Sentence-level citation | 78.1 | 57.6 | F1 69.2 | [claim:clm_073] |
| GPT-4o (zero-shot baseline) | Sentence-level citation | 53.5 | 46.7 | F1 65.6 | [claim:clm_074] |
| Claude-3-Sonnet (baseline) | Sentence-level citation | 67.8 | 52.0 | F1 67.2 | [claim:clm_074] |
| GPT-4 zero-shot (Concatenation) | Multi-hop attribution | n/a | n/a | F1 0.451 | [claim:clm_035] |
| GPT-4 zero-shot (Intersection) | Multi-hop attribution | n/a | n/a | F1 0.514 | [claim:clm_035] |
| Fine-tuned detector (CAQA) | Attribution category | n/a | n/a | >90% F1 | [claim:clm_038] |
| CiteAgent (GPT-4o) | Claim-to-single-source | n/a | n/a | 35.3% accuracy | [claim:clm_060] |
| Human experts (CiteME) | Claim-to-single-source | n/a | n/a | 69.7% accuracy | [claim:clm_060] |
| SPECTER2 / SPECTER (CiteME) | Claim-to-single-source | n/a | n/a | 0% accuracy | [claim:clm_061] |

**Inference:** For the alignment step RF should prefer a fine-tuned sentence-level citation model over a zero-shot frontier prompt, since LongCite-8B reaches citation F1 72.0 (P 79.7 / R 62.0) versus GPT-4o's F1 65.6 (P 53.5) and Claude-3-Sonnet's F1 67.2 on the same LongBench-Cite protocol, a ~5-6 point F1 and ~12-26 point precision advantage. [claim:clm_inf05]

## Analysis: ordering, cost, and the gaming hazard

Decomposition and decontextualization have conflicting purposes that create a tension a verification system must resolve: decomposition isolates atomic facts while decontextualization re-inserts relevant context. [claim:clm_013] A decontextualized subclaim becomes less atomic and creates a verification ambiguity over which of the multiple embedded atomic facts should actually be checked. [claim:clm_014] The original FActScore (decompose-then-verify) method yields an average factuality score of 33.00% on the benchmark, serving as the baseline. [claim:clm_015] DnDScore is highest under the Decontextualization-then-Decomposition configuration (decontextualized claim used as context), reaching 61.51%. [claim:clm_016] The Decontextualization-then-Decomposition pipeline generates the highest number of subclaims yet lands near the same FActScore as Decomposition-then-Decontextualization, at 44.60%. [claim:clm_017] Among judgments that switched from false to true after decontextualizing subclaims, 48.52% involved a pronoun replacement, indicating entity disambiguation is a primary driver of corrected verifications. [claim:clm_018]

The cost analysis favors a cheap-segment / deep-verify split. Decompose-then-verify factuality metrics like FactScore and VeriScore can take upwards of 100 seconds per response due to numerous LLM calls, limiting large-scale use. [claim:clm_022] The combined extract-and-verify task is hard for few-shot prompting because the model must process ~4K tokens of evidence and concurrently decompose, judge verifiability, and verify against noisy evidence. [claim:clm_023] VeriFastScore fine-tunes Llama-3.1-8B to extract and verify all verifiable claims in a text simultaneously, using evidence from Google Search. [claim:clm_019] Training data was a synthetic dataset built by running responses through the VeriScore pipeline to decompose them into verifiable claims and assign verification labels. [claim:clm_024] VeriFastScore correlates strongly with the original VeriScore pipeline (r=0.80 example level, r=0.94 system level) while achieving a 6.6x overall speedup (9.9x excluding evidence retrieval). [claim:clm_020] Retrieving evidence at a coarser granularity cuts API costs by 39% and reduces retrieval time by almost half. [claim:clm_021]

**Inference:** RF should run cheap-tier segmentation but escalate the combined align-and-verdict step to a deeper tier or a purpose-fine-tuned model, because few-shot extraction-plus-verification over ~4K evidence tokens is too complex for prompting alone, while decompose-then-verify on a frontier model costs 100+ seconds per response. [claim:clm_inf10]

**Inference:** Distilling RF's deep-tier verifier into a fine-tuned small model is the most cost-effective scaling path: VeriFastScore (fine-tuned Llama-3.1-8B) reproduces the slow VeriScore pipeline at r=0.94 system-level and r=0.80 example-level with a 6.6x speedup, and coarser-granularity retrieval adds a 39% API-cost cut and ~2x retrieval speedup. [claim:clm_inf11]

**Inference:** RF's alignment thresholds should be set per chosen synthesis model's residual hallucination rate rather than as a fixed cutoff, because the same automated alignment metric can be gamed by padding obvious or repetitive subclaims, so a Core-style uniqueness/informativeness filter must run before any supports/mixed/review threshold is applied. [claim:clm_inf12]

**Inference:** The recommended RF pipeline order is Select-and-decontextualize (cheap, Claimify/VeriScore-style) -> Core-style subclaim selection -> sentence-level alignment to source_card_id+locator (LongCite-style) -> partial-aware verdict, with decontextualization placed before final decomposition since DnDScore peaks at 61.51% under Decontextualization-then-Decomposition versus a 33.00% decompose-then-verify baseline. [claim:clm_inf13]

## Recommendations and decision rules

**Inference:** The claim ledger must record the decomposition method id/version and a per-claim atomicity value alongside source_card_id and locator, since decomposition policies misalign with verifiers in atomicity and DecompScore is defined as supported-subclaims-per-passage for a specific method, so without these fields a verdict cannot be reproduced or attributed to the splitter versus the model. [claim:clm_inf04]

**Inference:** RF's minimal re-runnable claim-ledger schema needs at least: claim_id, claim_type, materiality, status (supported/mixed/inference/speculation/unsupported), decomposition_method+version, atomicity, and per-source {source_card_id, locator/span, relation, partial-or-full support score}, because attribution is fundamentally a pointer-into-a-fixed-corpus and partial support must be a first-class score, not a boolean. [claim:clm_inf14]

**Inference:** Because the LLM-as-judge that scores alignment agrees with humans only at Cohen's kappa 0.593-0.655, RF should require two-tier verdict agreement (or a calibrated abstain band) and validate its automatic AIS scorer against a small gold human-annotated set, following the AQA precedent that treats human annotations as gold and only then accepts a correlated automatic metric. [claim:clm_inf16]

### Claim-ledger field set mapped to source cards

| Ledger field | Rationale | Evidence |
|--------------|-----------|----------|
| decomposition_method + version | Splitter changes yield silently on identical text | [claim:clm_006] |
| per-claim atomicity value | DecompScore is method-relative, defined per decomposition method | [claim:clm_005] |
| per-source source_card_id + locator/span | Attribution is a pointer into a fixed corpus satisfying AIS | [claim:clm_009] |
| partial-or-full support score (not boolean) | Partial support is operationalized as a 0.5 recall score | [claim:clm_075] |
| status incl. mixed for partial support | Partially Supportive is an explicit category beyond binary support | [claim:clm_034] |
| gold-calibrated AIS scorer + abstain band | LLM judge agrees with humans only at kappa 0.593 / 0.655 | [claim:clm_077] |

### Decision rules for verdict routing

| Condition | Routing rule | Evidence |
|-----------|--------------|----------|
| Low per-sentence verifiable-claim density | Genre density varies ~77x (0.03 vs 2.31), signalling opinion/creative material | [claim:clm_067] |
| Aligner precision near its ~80% ceiling | Best trained sentence-level citer reaches precision 79.7 | [claim:clm_073] |
| Multi-hop / aggregated quantitative claim | GPT-4 F1 falls to 0.451 / 0.514 on aggregated cases | [claim:clm_035] |
| Partial-support score detected | Partially Supportive is the hardest verdict to detect automatically | [claim:clm_036] |
| Subtle conflict / subtle baseless / low-confidence span | Span detection precision is only 18.4% / 52.7% F1 | [claim:clm_045] |
| Novel hard single-source attribution | Best agent reaches 35.3% vs 69.7% human on filtered CiteME | [claim:clm_060] |

## Failure modes that must route to human review, inference, or 'mixed'

RAGTruth defines Evident Conflict as RAG output that directly contradicts the retrieved source content, which is easily verifiable. [claim:clm_039] Subtle Conflict is a divergence from the source that alters the intended contextual meaning rather than a blatant contradiction. [claim:clm_040] RAGTruth distinguishes evident baseless information (unsubstantiated content) from subtle baseless information defined as inferred details, insights, or sentiments beyond the source. [claim:clm_041] The corpus comprises roughly 18,000 naturally generated RAG responses from diverse LLMs, manually annotated at both case and word levels. [claim:clm_042] The 2,965 annotated instances split into 989 question answering, 1,033 data-to-text writing, and 943 news summarization cases (17,790 total responses). [claim:clm_043] Detecting evident hallucinations is markedly more effective than detecting subtle hallucinations, implying subtle-conflict and subtle-baseless cases are the hardest to auto-verify. [claim:clm_044] Span-level hallucination detection is hard: GPT-4-turbo reaches only 18.4% precision while a fine-tuned Llama-2-13B reaches 52.7% F1, motivating routing low-confidence span verdicts to review. [claim:clm_045]

Open-domain claim verification fails on complex, non-entity-centric claims: verifying support requires extensive reasoning over the connection between claim parts rather than exact or related term matching against search snippets. [claim:clm_070] VeriScore cannot reliably decide whether an unsupported complex claim is a hallucination because that judgment exceeds what reasoning over search snippets can achieve, indicating such claims should route to review or an inference label. [claim:clm_071]

### Failure-mode routing matrix

| Failure class | Why automated alignment leaks | Required routing | Evidence |
|---------------|-------------------------------|------------------|----------|
| Multi-hop / aggregated claims | GPT-4 F1 0.451 (Concatenation), 0.514 (Intersection) | Human review | [claim:clm_035] |
| Partially-supportive | Hardest verdict; evaluators over-call support via keyword co-occurrence | 'mixed' or human review | [claim:clm_037] |
| Subtle conflict / subtle baseless / span | Span precision 18.4% (GPT-4-turbo), 52.7% F1 (Llama-2-13B) | Human review or inference/speculation | [claim:clm_045] |
| Hard novel single-source attribution | Reported high scores inflated by ~38.7% dataset memorization | Indefinite human-review tier | [claim:clm_065] |

**Inference:** Multi-hop and aggregated quantitative claims are the dominant systematic failure mode for automated aligners and must be flagged for human review: GPT-4 zero-shot attribution F1 falls to 0.451 on Concatenation and 0.514 on Intersection, far below single-source cases, mirroring VeriScore's failure on complex non-entity-centric claims. [claim:clm_inf07]

**Inference:** RF's 'mixed' status should map to the Partially-Supportive failure class, which is the single hardest verdict for automated evaluators (highest zero-shot F1 only ~0.456 in CAQA) because they fall back on keyword co-occurrence and misclassify partial support as full support, so any claim scored partial must be forced to 'mixed' or human review rather than 'supported'. [claim:clm_inf08]

**Inference:** Subtle hallucinations (Subtle Conflict and Subtle Baseless Information) and span-level localization, not evident contradictions, are where RF's gate will leak: span-level detection precision is only 18.4% for GPT-4-turbo and 52.7% F1 for a fine-tuned Llama-2-13B, so low-confidence span verdicts and subtle divergences must default to human review or an inference/speculation label. [claim:clm_inf09]

## Forward outlook

**Speculation:** An RF verifier built as a fine-tuned small model (VeriFastScore-style) calibrated against a CAQA-style fine-tuned detector could plausibly push automated supports-precision toward the 90%+ F1 seen for fine-tuned CAQA evaluators, shrinking the human-review band to the partial-support and multi-hop classes only, but this is unvalidated for RF's domain and synthesis model. [claim:clm_spec01]

## Open questions

- What is RF's measured residual hallucination rate per synthesis model, so alignment thresholds can be calibrated rather than fixed?
- Does a Claimify-plus-Core segmentation stack reproduce its reported 99% entailment and domain robustness on RF's own report corpus?
- Can a distilled VeriFastScore-style verifier reach a usable precision/recall on RF source cards (not just Wikipedia/biography benchmarks)?
- What inter-annotator agreement does RF's own gold human-annotation set achieve, and is it high enough to validate the automatic AIS scorer against?
- Where should the cheap-tier/deep-tier boundary sit for RF's typical evidence length relative to the ~4K-token combined-task threshold?

## Sources

- src_20260614_rib001_03: A Closer Look at Claim Decomposition
- src_20260614_rib001_08: google-research-datasets/Attributed-QA (Attributed Question Answering dataset)
- src_20260614_rib001_01: DnDScore: Decontextualization and Decomposition for Factuality Verification in Long-Form Text Generation
- src_20260614_rib001_05: VeriFastScore: Speeding up long-form factuality evaluation
- src_20260614_rib001_00: Claimify: Extracting high-quality claims from language model outputs
- src_20260614_rib001_10: Can LLMs Evaluate Complex Attribution in QA? Automatic Benchmarking using Knowledge Graphs
- src_20260614_rib001_09: RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models
- src_20260614_rib001_02: Core: Robust Factual Precision with Informative Sub-Claim Identification
- src_20260614_rib001_04: Optimizing Decomposition for Optimal Claim Verification
- src_20260614_rib001_07: CiteME: Can Language Models Accurately Cite Scientific Claims?
- src_20260614_rib001_11: VeriScore: Evaluating the factuality of verifiable claims in long-form text generation
- src_20260614_rib001_06: LongCite: Enabling LLMs to Generate Fine-grained Citations in Long-context QA
