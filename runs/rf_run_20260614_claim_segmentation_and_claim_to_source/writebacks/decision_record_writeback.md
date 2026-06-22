---
id: mwb_20260622_dr_claim_segmentation_and_claim_to
evidence_bundle_id: bundle_20260614_intent_research_20260614_claim_segmentation_and
target_page: meatywiki/decisions/claim_segmentation_and_claim_to_source.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_claim_segmentation_and_claim_to_source: Claimify''s
  three stages drop unverifiable sentences (clm_026), abstain when ambiguity is unresolved (clm_027/clm_029),
  p'
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_026
  - clm_027
  - clm_028
  - clm_029
  - clm_030
  - clm_031
  - clm_032
  - clm_066
  - clm_067
  - clm_001
  - clm_005
  - clm_052
  - clm_053
  - clm_034
  - clm_036
  - clm_037
  - clm_075
  - clm_022
  - clm_023
  - clm_019
  - clm_025
  - clm_046
  - clm_047
  - clm_048
  - clm_049
  - clm_050
  - clm_013
  - clm_015
  - clm_016
  - clm_018
  - clm_072
  - clm_009
  - clm_010
  - clm_012
  - clm_077
  - clm_038
  - clm_002
  - clm_006
  - clm_073
  - clm_074
  - clm_033
  - clm_035
  - clm_070
  - clm_040
  - clm_041
  - clm_044
  - clm_045
  - clm_020
  - clm_021
  - clm_024
  - clm_060
  - clm_061
  - clm_062
  - clm_065
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Claim segmentation and claim-to-source alignment for RF verification

## Context

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

## Decision

Of the surveyed segmenters, Claimify is the best fit for RF's pre-verification stage because its staged Selection-Disambiguation-Decomposition design achieves 99% source-sentence entailment and explicitly abstains on irreducibly ambiguous sentences, directly satisfying RF's invariant that every extracted claim be entailed or labeled rather than forced. [claim:clm_inf01]

## Rationale

- Claimify's three stages drop unverifiable sentences (clm_026), abstain when ambiguity is unresolved (clm_027/clm_029), preserve context (clm_028), and require entailment (clm_030), with 99% measured entailment (clm_031) and ACL-2025 superiority over prior methods (clm_032); this is the only surveyed method that both abstains and is measured for decontextualization fidelity, matching RF's entail-or-label gate. [claim:clm_inf01]
- VeriScore extracts only verifiable claims and was preferred over decompose-everything methods (clm_066); verifiable-claim density varies ~77x by genre (clm_067), giving a measurable cheap signal that mirrors Claimify's Selection drop (clm_026), so density can gate which segments even enter alignment. [claim:clm_inf02]
- Error can originate in decomposition (clm_001), DecompScore is method-relative (clm_005), atomicity is a defined information-density metric (clm_052), and policies misalign with verifiers on atomicity (clm_053); auditing which source of error applies requires storing method id/version + atomicity per claim. [claim:clm_inf04]
- CAQA defines Partially Supportive (clm_034) as the hardest verdict (clm_036) where evaluators use keyword co-occurrence and over-call support (clm_037); LongCite already operationalizes partial as a 0.5 score (clm_075), giving RF a concrete signal to route to 'mixed' instead of trusting an over-optimistic 'supported'. [claim:clm_inf08]
- Decompose-then-verify takes 100+s per response (clm_022) and the joint task is too hard for few-shot prompting (clm_023), yet a fine-tuned 8B model handles extract+verify together (clm_019); since plain extraction is a comparatively simple operation (clm_025), the cheap/deep split should fall between segmentation and the joint align/verdict step. [claim:clm_inf10]
- Decompose-then-verify metrics inflate under repetitive subclaims (clm_046); Core filters subclaims by uniqueness/informativeness (clm_047) as a constrained optimization (clm_048), making metrics robust across domains (clm_049) and droppable in place (clm_050), so calibration must include a Core-style pre-filter or thresholds are not comparable across models. [claim:clm_inf12]
- Decomposition and decontextualization conflict (clm_013); ordering matters empirically, with Decontextualization-then-Decomposition at 61.51% vs 33.00% baseline (clm_015/clm_016) and pronoun/entity disambiguation driving corrected verdicts (clm_018); aligning at the sentence level (clm_072) yields the concrete segment->decontextualize->align->verdict order. [claim:clm_inf13]
- Attribution is a pointer into a fixed corpus satisfying AIS (clm_009/clm_010), partial support is a defined category (clm_034) operationalized as a 0.5 score (clm_075), and method-relative scoring (clm_005) requires storing the method; together these dictate the minimal field set including locator/span and a partial-support score. [claim:clm_inf14]
- AQA validates AutoAIS against human-gold annotations (clm_012), LongCite's GPT-4o judge only reaches kappa 0.593-0.655 with humans (clm_077), and CAQA fine-tuning past 90% F1 shows the gap is calibratable (clm_038); RF should therefore gold-calibrate its scorer and use an abstain/agreement band rather than trusting a single judge. [claim:clm_inf16]
- Splitter choice changes yield from 20.0 to 42.3 facts on the same text (clm_006), the metric is sensitive to the decomposition step (clm_001), and the score moves with atomicity for fixed text (clm_002); therefore a fixed, versioned splitter is required for reproducible claim counts and verdicts. [claim:clm_inf03]
- On the identical sentence-level citation protocol (clm_072), trained LongCite-8B F1 72.0/P 79.7 (clm_073) exceeds GPT-4o F1 65.6/P 53.5 and Claude-3-Sonnet F1 67.2 (clm_074); the precision gap is most material for a hard verification gate that should minimize false 'supported' verdicts. [claim:clm_inf05]
- The best trained sentence-level citer reaches precision 79.7 (clm_073), above proprietary baselines (clm_074), and the GPT-4o judge measuring this only agrees with humans at kappa 0.593-0.655 (clm_077); combined, this caps trustworthy automated alignment precision near 80% and implies a mandatory human band above that. [claim:clm_inf06]
- CAQA marks Union/Intersection/Concatenation as the multi-hop cases (clm_033) where GPT-4 F1 drops to 0.451/0.514 (clm_035), and VeriScore independently fails on complex claims needing reasoning across claim parts (clm_070); two sources converging identifies aggregation/multi-hop as the primary failure class to route to review. [claim:clm_inf07]
- RAGTruth's subtle conflict (clm_040) and subtle baseless inferred-content (clm_041) are detected far worse than evident ones (clm_044), and span-level precision is 18.4%/52.7% F1 (clm_045); subtle inferred content is exactly what RF should label inference, and weak span detection mandates a review default. [claim:clm_inf09]
- VeriFastScore is a fine-tuned 8B model (clm_019) trained on synthetic VeriScore-pipeline labels (clm_024) that matches the pipeline at r=0.94/r=0.80 with 6.6x speedup (clm_020) plus 39% cost / ~half retrieval time via coarse retrieval (clm_021); this is a concrete distill-then-serve recipe for RF's verifier tier. [claim:clm_inf11]
- On adversarially filtered CiteME (clm_062) the best agent hits 35.3% vs 69.7% human (clm_060) leaving a 34.4-point gap (clm_061), and apparently strong scores are memorization artifacts (clm_065); on truly novel claims automated attribution is far from human, so a human tier is non-optional. [claim:clm_inf15]

## Consequences

- RF should adopt VeriScore-style verifiable-claim filtering as the first segmentation step, using per-sentence verifiable-claim density (e.g., the ~0.03 vs 2.31 fiction-vs-nonfiction split) as a cheap routing signal to send low-density passages to an 'unverifiable/opinion' bucket rather than into the claim ledger. [claim:clm_inf02]
- The claim ledger must record the decomposition method id/version and a per-claim atomicity value alongside source_card_id and locator, since decomposition policies misalign with verifiers in atomicity and DecompScore is defined as supported-subclaims-per-passage for a specific method, so without these fields a verdict cannot be reproduced or attributed to the splitter versus the model. [claim:clm_inf04]
- RF's 'mixed' status should map to the Partially-Supportive failure class, which is the single hardest verdict for automated evaluators (highest zero-shot F1 only ~0.456 in CAQA) because they fall back on keyword co-occurrence and misclassify partial support as full support, so any claim scored partial must be forced to 'mixed' or human review rather than 'supported'. [claim:clm_inf08]
- RF should run cheap-tier segmentation but escalate the combined align-and-verdict step to a deeper tier or a purpose-fine-tuned model, because few-shot extraction-plus-verification over ~4K evidence tokens is too complex for prompting alone, while decompose-then-verify on a frontier model costs 100+ seconds per response. [claim:clm_inf10]
- RF's alignment thresholds should be set per chosen synthesis model's residual hallucination rate rather than as a fixed cutoff, because the same automated alignment metric can be gamed by padding obvious or repetitive subclaims, so a Core-style uniqueness/informativeness filter must run before any supports/mixed/review threshold is applied. [claim:clm_inf12]
- The recommended RF pipeline order is Select-and-decontextualize (cheap, Claimify/VeriScore-style) -> Core-style subclaim selection -> sentence-level alignment to source_card_id+locator (LongCite-style) -> partial-aware verdict, with decontextualization placed before final decomposition since DnDScore peaks at 61.51% under Decontextualization-then-Decomposition versus a 33.00% decompose-then-verify baseline. [claim:clm_inf13]
- RF's minimal re-runnable claim-ledger schema needs at least: claim_id, claim_type, materiality, status (supported/mixed/inference/speculation/unsupported), decomposition_method+version, atomicity, and per-source {source_card_id, locator/span, relation, partial-or-full support score}, because attribution is fundamentally a pointer-into-a-fixed-corpus and partial support must be a first-class score, not a boolean. [claim:clm_inf14]
- Because the LLM-as-judge that scores alignment agrees with humans only at Cohen's kappa 0.593-0.655, RF should require two-tier verdict agreement (or a calibrated abstain band) and validate its automatic AIS scorer against a small gold human-annotated set, following the AQA precedent that treats human annotations as gold and only then accepts a correlated automatic metric. [claim:clm_inf16]
- Claim segmentation in RF must fix and version a single decomposition method, because identical text yields between 20.0 (WiCE) and 42.3 (Russellian/Neo-Davidsonian) atomic facts depending on the splitter, and FActScore itself shifts with atomicity, so any unversioned splitter change would silently break re-runnable alignment and verification audits. [claim:clm_inf03]
- For the alignment step RF should prefer a fine-tuned sentence-level citation model over a zero-shot frontier prompt, since LongCite-8B reaches citation F1 72.0 (P 79.7 / R 62.0) versus GPT-4o's F1 65.6 (P 53.5) and Claude-3-Sonnet's F1 67.2 on the same LongBench-Cite protocol, a ~5-6 point F1 and ~12-26 point precision advantage. [claim:clm_inf05]
- Automated claim-to-source alignment precision currently tops out around 80% (LongCite-8B precision 79.7 on sentence-level citation), so RF should treat ~80% precision as the practical ceiling before human review and not assume near-perfect attribution from any single automated aligner. [claim:clm_inf06]
- Multi-hop and aggregated quantitative claims are the dominant systematic failure mode for automated aligners and must be flagged for human review: GPT-4 zero-shot attribution F1 falls to 0.451 on Concatenation and 0.514 on Intersection, far below single-source cases, mirroring VeriScore's failure on complex non-entity-centric claims. [claim:clm_inf07]
- Subtle hallucinations (Subtle Conflict and Subtle Baseless Information) and span-level localization, not evident contradictions, are where RF's gate will leak: span-level detection precision is only 18.4% for GPT-4-turbo and 52.7% F1 for a fine-tuned Llama-2-13B, so low-confidence span verdicts and subtle divergences must default to human review or an inference/speculation label. [claim:clm_inf09]
- Distilling RF's deep-tier verifier into a fine-tuned small model is the most cost-effective scaling path: VeriFastScore (fine-tuned Llama-3.1-8B) reproduces the slow VeriScore pipeline at r=0.94 system-level and r=0.80 example-level with a 6.6x speedup, and coarser-granularity retrieval adds a 39% API-cost cut and ~2x retrieval speedup. [claim:clm_inf11]
- Citation-attribution remains genuinely below human level for hard cases, so RF must keep a human-review tier indefinitely: the best autonomous agent (CiteAgent on GPT-4o) reaches only 35.3% on adversarially filtered CiteME versus 69.7% for time-capped human experts, a 34.4-point gap, and reported higher scores (GPT-o1 61.3%) are inflated by ~38.7% dataset memorization. [claim:clm_inf15]

## Links

- [[claim:clm_026]]
- [[claim:clm_027]]
- [[claim:clm_028]]
- [[claim:clm_029]]
- [[claim:clm_030]]
- [[claim:clm_031]]
- [[claim:clm_032]]
- [[claim:clm_066]]
- [[claim:clm_067]]
- [[claim:clm_001]]
- [[claim:clm_005]]
- [[claim:clm_052]]
- [[claim:clm_053]]
- [[claim:clm_034]]
- [[claim:clm_036]]
- [[claim:clm_037]]
- [[claim:clm_075]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_019]]
- [[claim:clm_025]]
- [[claim:clm_046]]
- [[claim:clm_047]]
- [[claim:clm_048]]
- [[claim:clm_049]]
- [[claim:clm_050]]
- [[claim:clm_013]]
- [[claim:clm_015]]
- [[claim:clm_016]]
- [[claim:clm_018]]
- [[claim:clm_072]]
- [[claim:clm_009]]
- [[claim:clm_010]]
- [[claim:clm_012]]
- [[claim:clm_077]]
- [[claim:clm_038]]
- [[claim:clm_002]]
- [[claim:clm_006]]
- [[claim:clm_073]]
- [[claim:clm_074]]
- [[claim:clm_033]]
- [[claim:clm_035]]
- [[claim:clm_070]]
- [[claim:clm_040]]
- [[claim:clm_041]]
- [[claim:clm_044]]
- [[claim:clm_045]]
- [[claim:clm_020]]
- [[claim:clm_021]]
- [[claim:clm_024]]
- [[claim:clm_060]]
- [[claim:clm_061]]
- [[claim:clm_062]]
- [[claim:clm_065]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
