---
id: mwb_20260622_dr_hybrid_bm25_vector_and_fts5
evidence_bundle_id: bundle_20260615_intent_research_20260614_hybrid_bm25_vector
target_page: meatywiki/decisions/hybrid_bm25_vector_and_fts5_ranking.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_hybrid_bm25_vector_and_fts5_ranking: BM25 alone suffices
  at small scale; reranking is the largest single lift and needs no vector index, making it the cheape'
key_claims:
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf14
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_002
  - clm_003
  - clm_004
  - clm_007
  - clm_024
  - clm_008
  - clm_009
  - clm_012
  - clm_013
  - clm_039
  - clm_055
  - clm_010
  - clm_011
  - clm_014
  - clm_015
  - clm_016
  - clm_020
  - clm_064
  - clm_065
  - clm_068
  - clm_066
  - clm_067
  - clm_030
  - clm_032
  - clm_034
  - clm_059
  - clm_069
  - clm_071
  - clm_072
  - clm_074
  - clm_001
  - clm_022
  - clm_023
  - clm_040
  - clm_046
  - clm_047
  - clm_049
  - clm_052
  - clm_041
  - clm_042
  - clm_043
  - clm_045
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Hybrid BM25+vector and FTS5 ranking for Markdown KBs

## Context

- The benchmark spans 23,088 question-context-answer triples over 7,318 unique financial documents (drawn from FinQA, ConvFinQA, and TAT-DQA) averaging ~920 tokens each. [claim:clm_001]
- Sparse BM25 outperforms dense text-embedding-3-large retrieval on nearly all metrics (Recall@5 0.644 vs 0.587), contradicting the assumption that semantic embeddings dominate sparse lexical retrieval. [claim:clm_002]
- Adding a Cohere reranker to the hybrid BM25+dense RRF pipeline lifts Recall@5 from 0.695 to 0.816, a +17.4% improvement over unreranked hybrid retrieval. [claim:clm_003]
- Cross-encoder reranking is the single largest quality lift in the pipeline, raising MRR@3 from 0.433 to 0.605 (+39.7% relative). [claim:clm_004]
- Contextual Retrieval (document enrichment) yields modest gains, improving dense retrieval by +2.8pp and hybrid retrieval by +2.2pp Recall@5. [claim:clm_005]
- HyDE-style query expansion hurts retrieval on this corpus, underperforming even vanilla dense retrieval (Recall@5 0.544 vs 0.587) because generated hypothetical documents hallucinate plausible-but-wrong financial figures. [claim:clm_006]
- Hybrid fusion delivers its largest absolute gain on the table-heavy TAT-DQA subset, adding +8.1 percentage points Recall@5 over BM25 alone, showing neither sparse nor dense retrieval suffices alone on table-heavy questions. [claim:clm_007]
- RRF scores each document by summing reciprocal ranks across the input rankings: RRFscore(d) = sum over r in R of 1/(k + r(d)), where each ranking r is a permutation on 1..|D|. [claim:clm_008]
- The constant k is fixed at 60, chosen during a pilot investigation and never re-tuned during validation; the formula keeps lower-ranked documents from vanishing and dampens outlier systems. [claim:clm_009]
- A pilot experiment over TREC topics found k=60 was near-optimal but that the exact choice was not critical, with MAP varying only slightly across k from 0 to 500. [claim:clm_010]
- RRF consistently yields better results than any individual IR system and better results than the standard fusion method Condorcet Fuse, demonstrated by combining TREC runs and by building a LETOR 3 meta-learner. [claim:clm_011]
- Across pilot and TREC experiments, RRF outperforms Condorcet Fuse, CombMNZ, and the best individual system by roughly 4% to 5% on average in MAP. [claim:clm_012]
- RRF is an unsupervised, training-free fusion method that combines ranks without regard to the arbitrary scores of particular ranking methods and needs no special voting algorithm or global information. [claim:clm_013]
- Applying RRF to the LETOR 3 baseline rank-learning methods produces a meta-learner that, to the authors' knowledge, no reported result matches or exceeds, making it the best known method on that dataset. [claim:clm_014]
- enable_fts() takes a list of named columns and indexes each as a separately searchable FTS field, which is the basis for indexing frontmatter fields and headings as distinct columns. [claim:clm_015]
- Passing tokenize='porter' to enable_fts enables Porter stemming so that English words like 'running' match stemmed alternatives such as 'run'. [claim:clm_016]
- enable_fts() defaults to FTS5, with an explicit fts_version='FTS4' opt-out for using the older FTS4 engine. [claim:clm_017]
- table.search(q) returns rows ordered by relevance (most relevant first) automatically, without requiring an explicit sort. [claim:clm_018]
- Setting include_rank=True adds a 'rank' column carrying the BM25 ranking score, available for FTS5 tables only. [claim:clm_019]
- search() exposes ordering only via an order_by column argument that defaults to the relevance score; it offers no per-column bm25() weight parameter, so custom field weighting must be applied through raw FTS5 rank config / ORDER BY bm25(...). [claim:clm_020]
- The evaluation metric is 1 minus recall@20, defined as the percentage of relevant documents that fail to be retrieved within the top 20 chunks. [claim:clm_021]
- Contextual Embeddings alone cut the top-20-chunk retrieval failure rate from a 5.7% baseline to 3.7%, a 35% reduction. [claim:clm_022]
- Combining Contextual Embeddings with Contextual BM25 cut the failure rate from 5.7% to 2.9%, a 49% reduction. [claim:clm_023]
- Adding a reranking step on top of Contextual Embeddings and Contextual BM25 cut the failure rate from 5.7% to 1.9%, a 67% total reduction. [claim:clm_024]
- Contextual Retrieval prepends a short LLM-generated context to each chunk before indexing, e.g. identifying the source filing and prior-quarter revenue. [claim:clm_025]
- The method was evaluated across multiple knowledge domains including codebases, fiction, ArXiv papers, and science papers. [claim:clm_026]
- The choice of chunking strategy materially affects retrieval performance, with the best strategies outperforming others by up to 9% in recall on a fixed retriever. [claim:clm_027]
- The report evaluates chunkers with token-level Recall, Precision, Precision-Omega (precision when all chunks containing excerpt tokens are retrieved), and IoU. [claim:clm_028]
- Precision-Omega is defined as the precision achieved under the assumption that every chunk containing excerpt tokens was successfully retrieved (a max-precision-under-perfect-recall ceiling). [claim:clm_029]
- The LLMSemanticChunker (GPT-4o) achieved the highest recall at 91.9%, but with very low precision (3.9%) reflecting low retrieval efficiency. [claim:clm_030]
- The ClusterSemanticChunker is an embedding-aware splitter that uses dynamic programming to maximize pairwise cosine similarity within each chunk up to a user-specified maximum length. [claim:clm_031]
- The ClusterSemanticChunker at 400 tokens reached 91.3% recall with 4.5% precision, nearly matching the top recall while remaining an embedding-model-aware splitter. [claim:clm_032]
- The authors conclude the embedding-model-aware ClusterSemanticChunker produced consistently strong results across the evaluation. [claim:clm_033]
- Recall plateaus and then degrades as chunk size changes: overly large chunks dilute relevant information while overly small chunks fail to capture necessary context, framing the recall-vs-completeness tradeoff. [claim:clm_034]
- The normalization-processor is a search-phase-results processor that runs between the query and fetch phases, intercepting query-phase results to normalize and combine document scores from different query clauses before fetch. [claim:clm_035]
- Supported score-normalization techniques are min_max, l2, and z_score, with min_max as the default. [claim:clm_036]
- Supported score-combination techniques are arithmetic_mean, geometric_mean, and harmonic_mean (default arithmetic_mean); z_score supports only arithmetic_mean. [claim:clm_037]
- Per-subquery weights are configurable in the [0.0, 1.0] range, must equal the number of queries and sum to 1.0; if omitted, all queries are weighted equally. [claim:clm_038]
- BM25 and k-NN/neural searches use different relevance-score scales, so scores are normalized onto a common scale before combination, a benefit supported by experimental data. [claim:clm_039]
- The processor only transforms results returned per subquery (it does no extra sampling); using nDCG@10, a returned size of 100-200 worked best for datasets up to 10M documents, and larger sizes raised latency without improving relevance. [claim:clm_040]
- Under a 25ms/query latency limit on TREC DL 2019, TinyBERT-gBCE reaches NDCG@10 of 0.652 versus MonoBERT-Large's 0.431, a +51% gain. [claim:clm_041]
- Shallow (few-layer) transformer cross-encoders outperform full-scale models under low-latency constraints because they can score the relevance of more documents within the same time budget. [claim:clm_042]
- Shallow cross-encoders remain effective on CPU: NDCG@10 drops only 3% versus GPU inference at a 50ms latency budget, making them practical without specialized hardware. [claim:clm_043]
- Shallow cross-encoders benefit from the generalized Binary Cross-Entropy (gBCE) training scheme previously shown successful for recommendation tasks. [claim:clm_044]
- Large-model cross-encoders (e.g., BERT or T5) are computationally expensive and can only score a small number of documents within a reasonably small latency window. [claim:clm_045]
- The study concludes that the computational costs of semantic chunking are not justified by consistent performance gains over fixed-size chunking in RAG. [claim:clm_046]
- On non-stitched document-retrieval datasets, fixed-size chunking led on F1@5, scoring 90.59% on HotpotQA and 93.58% on MSMARCO. [claim:clm_047]
- Breakpoint-based semantic chunking outperformed fixed-size only on artificially stitched high-topic-diversity data, reaching 81.89% F1@5 on Miracl versus 69.45% for fixed-size. [claim:clm_048]
- The authors caution that real-world document topics are likely less diverse than their stitched data, so semantic chunkers may have no edge over fixed-size chunking in practice. [claim:clm_049]
- Evidence-retrieval F1@5 differences across chunkers were minimal (e.g., ExpertQA: fixed-size 47.11% vs clustering 46.87%), with no clear advantage for any strategy. [claim:clm_050]
- In retrieval-based answer generation, BERTScore differences between chunking methods were negligible and inconclusive. [claim:clm_051]
- The paper recommends fixed-size chunking as a more efficient and reliable default for practical RAG applications. [claim:clm_052]
- The study compares three chunkers (fixed-size, breakpoint-based semantic, clustering-based semantic) across document retrieval, evidence retrieval, and answer generation using BEIR and RAGBench datasets. [claim:clm_053]
- RRF is a method for combining multiple result sets that carry different relevance indicators into a single ranked result set. [claim:clm_054]
- RRF requires no tuning, and the individual relevance indicators being combined do not need to be related to (or on the same scale as) one another to produce high-quality results. [claim:clm_055]
- RRF scores a document d by summing 1.0 / (k + rank(result(q), d)) across each query q in which d appears, where rank starts from 1. [claim:clm_056]
- In the RRF formula, k is the ranking constant and rank(result(q), d) is document d's rank within result(q), starting from 1. [claim:clm_057]
- Elasticsearch's rank_constant (k) controls how much influence per-query result sets have on the final ranking; a higher value gives lower-ranked documents more influence, the value must be >= 1, and it defaults to 60. [claim:clm_058]
- Cohere's rerank-v3.5 has a 4096-token context length and is positioned for multilingual retrieval and reasoning tasks. [claim:clm_059]
- Cohere claims rerank-v3.5 achieves state-of-the-art performance on BEIR and across multiple application domains. [claim:clm_060]
- With rerank-v3.5 the Rerank API makes the model parameter required. [claim:clm_061]
- The max_chunks_per_doc parameter is replaced by max_tokens_per_doc, which caps per-document tokens before truncation, defaulting to 4096. [claim:clm_062]
- Support for passing a list of objects for the documents parameter has been removed in the new Rerank API. [claim:clm_063]
- The bm25() auxiliary function returns a real value where a numerically smaller value indicates a better match, so results are ordered best-first via ORDER BY bm25(ft). [claim:clm_064]
- Per-column weights are passed as trailing arguments to bm25() in left-to-right column order, and any column without a supplied weight defaults to 1.0. [claim:clm_065]
- Every FTS5 table exposes a hidden 'rank' column that by default returns the same value as bm25() called with no trailing arguments. [claim:clm_066]
- ORDER BY rank is logically equivalent to ORDER BY bm25(ft) but can be faster, particularly when the query abandons early or uses a LIMIT clause. [claim:clm_067]
- The default ranking for the rank column can be persisted by setting the 'rank' configuration option to a bm25 expression with column weights. [claim:clm_068]
- bge-reranker-v2-m3 is a lightweight reranker built on bge-m3 with strong multilingual capability, easy deployment, and fast inference. [claim:clm_069]
- Unlike an embedding model, the reranker takes a query and a document as input and directly outputs a similarity score rather than an embedding. [claim:clm_070]
- The raw reranker score can be mapped to a float in [0,1] using a sigmoid function. [claim:clm_071]
- The model card lists bge-reranker-v2-m3 as based on bge-m3 with a size of 0.6B parameters. [claim:clm_072]
- The authors recommend bge-reranker-v2-m3 for multilingual reranking scenarios. [claim:clm_073]
- Setting use_fp16=True speeds up inference at the cost of a slight performance degradation. [claim:clm_074]

## Decision

Recommended per-tier architecture: 1K = BM25-only (FTS5) with frontmatter/heading column weighting; 10K = BM25 + cross-encoder reranking of the top ~100-200 lexical candidates (skip the vector index); 50K = full BM25 + dense vector hybrid fused by RRF then reranked. [claim:clm_inf03]

## Rationale

- BM25 alone suffices at small scale; reranking is the largest single lift and needs no vector index, making it the cheapest first upgrade at 10K; the full hybrid+rerank stack (Recall@5 0.816) is reserved for the largest tier where recall headroom justifies the vector-index cost. [claim:clm_inf03]
- RRF needs no per-deployment tuning and ignores incommensurate score scales (BM25 vs cosine), which weighted-linear fusion must reconcile via normalization; RRF's documented 4-5% MAP edge and zero-tuning property make it the safer default for a low-maintenance personal KB. [claim:clm_inf06]
- RRF is reported as the best-known method on LETOR-3 and its single constant is non-critical; a personal KB lacks the labeled relevance judgments needed to train a learned fuser, so the unsupervised method dominates on cost-adjusted terms. [claim:clm_inf07]
- Multi-column enable_fts plus Porter stemming is documented; since neither sqlite-utils search() nor the bm25() ad-hoc call is convenient for persistent weighting, the FTS5 'rank' configuration option is the canonical way to bake in title/heading boosts so every query inherits them via ORDER BY rank. [claim:clm_inf08]
- The hidden rank column equals weightless bm25() and FTS5 documents ORDER BY rank as the faster equivalent under LIMIT; top-k retrieval for reranking is exactly the LIMIT-bounded case where the speedup applies. [claim:clm_inf10]
- High-recall LLM chunking carries punishing precision/efficiency costs; embedding-aware or fixed-window chunking achieves comparable recall cheaply, and the recall-vs-chunk-size tradeoff means chunk length should be tuned rather than maximized. [claim:clm_inf12]
- bge-reranker-v2-m3 is a lightweight locally deployable cross-encoder, ideal for a sensitivity=personal KB; Cohere rerank-v3.5 is a hosted alternative whose SOTA claims are vendor-asserted, so it is a quality/convenience upgrade rather than the privacy-preserving default. [claim:clm_inf13]
- T2-RAGBench's 7,318-doc corpus is squarely between the 1K and 10K tiers, and BM25 won outright there, so lexical-only retrieval is adequate through ~10K; degradation is query-type-driven (tables), not raw-count-driven, within this range. [claim:clm_inf01]
- BM25 led overall but the hybrid uplift concentrated on table-heavy questions, indicating lexical insufficiency is triggered by content type (tables/numbers) more than by sheer document count. [claim:clm_inf02]
- Two independent benchmarks (T2-RAGBench and Anthropic Contextual Retrieval) both isolate reranking as the largest marginal quality contributor; the failure rate falls 2.9%->1.9% (a further 1pp / ~34% relative) purely from adding reranking on top of an already-hybrid pipeline. [claim:clm_inf04]
- Reranking's lift is corpus-independent per-query work over a fixed candidate set (OpenSearch finds 100-200 candidates optimal up to 10M docs), so its marginal value rises with corpus size as BM25 precision@k erodes, while at tiny corpora the lexical top-k is already mostly relevant. [claim:clm_inf05]
- Per-column weighting indexes and boosts structural metadata within the lexical engine alone, so BM25+frontmatter is a pure-FTS5 configuration with no second index, making it the lowest-cost relevance gain for small structured corpora. [claim:clm_inf09]
- Vectara/UW-Madison found fixed-size matches or beats semantic chunking on realistic single-topic documents and recommends it as default; Markdown artifacts are typically single-topic, so semantic chunking's edge (only on stitched multi-topic data) does not apply. [claim:clm_inf11]
- Under tight latency, shallow models score more candidates per budget and thus win; CPU viability (only 3% drop) matches the no-specialized-hardware profile of a personal KB. [claim:clm_inf14]

## Consequences

- RRF with k=60 is the recommended default fusion method for BM25+vector scores in a personal KB, over weighted-linear normalization, because RRF is unsupervised, training-free, and score-scale-agnostic (no min_max/z_score calibration), and beat Condorcet/CombMNZ and every individual system by 4-5% MAP; weighted normalization should be adopted only if measured query routing shows one signal is systematically stronger. [claim:clm_inf06]
- A learned fusion model is not justified for a personal KB at any tier from 1K to 50K: RRF already produces the best-known LETOR-3 meta-learner result and the k=60 choice is near-optimal-but-not-critical, so the training data, labeling, and maintenance burden of a learned fuser would buy negligible precision over zero-tuning RRF. [claim:clm_inf07]
- Concrete FTS5 recipe for heading/frontmatter-rich Markdown: enable_fts() over distinct columns (title, headings, frontmatter tags, body) with tokenize='porter', then persist heading/title boost via the rank config e.g. INSERT INTO ft(ft,rank) VALUES('rank','bm25(10.0, 5.0, 3.0, 1.0)') so weights apply automatically through ORDER BY rank without a per-query bm25() weight argument. [claim:clm_inf08]
- ORDER BY rank should be preferred over ORDER BY bm25(ft) in the KB query path because it is logically equivalent yet can short-circuit faster under LIMIT/early-abandon, which matters when the KB only needs the top-k candidates to feed a reranker. [claim:clm_inf10]
- When the KB does chunk (at 50K with a vector index), heading-delimited or fixed-window chunking sized to the embedding model is preferable to LLM-driven semantic chunking, because the LLMSemanticChunker reached 91.9% recall at only 3.9% precision while the embedding-aware ClusterSemanticChunker matched recall (91.3%) far more efficiently and chunk size must be tuned to avoid the recall plateau-then-degrade effect. [claim:clm_inf12]
- For the KB's reranker, a local self-hosted bge-reranker-v2-m3 (~0.6B params, sigmoid-mapped [0,1] scores, use_fp16 for speed) is the recommended default for cost and privacy, with Cohere rerank-v3.5 (4096-token, hosted, model param required) reserved for when API simplicity or claimed BEIR-SOTA quality outweighs per-call cost and sending personal data off-device. [claim:clm_inf13]
- For a personal Markdown artifact KB, BM25/FTS5 alone is a defensible single-tier retriever through the ~1K-10K document range, because sparse BM25 beat dense text-embedding-3-large on Recall@5 (0.644 vs 0.587) over a 7,318-document corpus, so the lexical-only break point sits at the upper edge of the 10K tier rather than at 1K. [claim:clm_inf01]
- The BM25-only failure mode is query-type-specific rather than corpus-size-specific: hybrid fusion added its largest gain (+8.1pp Recall@5) on the table-heavy TAT-DQA subset, so a Markdown KB whose value lives in prose/headings will degrade later than one dense with tables and numeric content. [claim:clm_inf02]
- Adding a cross-encoder reranker is the highest-ROI single upgrade for the KB at every tier where it is affordable, contributing a +17.4% Recall@5 lift over unreranked hybrid (0.695->0.816) and a +39.7% relative MRR@3 lift (0.433->0.605), and independently driving the largest portion of the 67% failure-rate reduction in Anthropic's Contextual Retrieval stack. [claim:clm_inf04]
- The reranking stage pays off starting at the ~10K tier and earlier for table/numeric-heavy KBs, because its quality lift is the largest in the pipeline while its only cost is scoring the top ~100-200 candidates a stage the KB already retrieves; below ~1K, BM25 precision@k is high enough that the latency/cost is unlikely to repay itself. [claim:clm_inf05]
- Heading- and title-weighted BM25 is itself a hybrid-class lift (BM25+frontmatter signals) available at zero extra index cost, since FTS5 lets distinct Markdown structural columns carry boost weights (e.g. title 10.0, headings 5.0, body 1.0); for the 1K tier this captures much of hybrid's benefit without any vector store. [claim:clm_inf09]
- Whole-document or heading-section indexing should be the default for the Markdown KB rather than expensive semantic chunking: fixed-size chunking led non-stitched document retrieval (F1@5 90.59% HotpotQA, 93.58% MSMARCO) and semantic chunking only won on artificially topic-stitched data, so its compute cost is not justified for naturally coherent Markdown artifacts. [claim:clm_inf11]
- Reranker depth should be chosen against a per-query latency budget, not maximized: shallow cross-encoders (TinyBERT-gBCE) beat full-scale MonoBERT-Large by +51% NDCG@10 under a 25ms/query limit and run on CPU with only ~3% loss, so a personal KB without a GPU should favor a shallow reranker over a large one. [claim:clm_inf14]

## Links

- [[claim:clm_002]]
- [[claim:clm_003]]
- [[claim:clm_004]]
- [[claim:clm_007]]
- [[claim:clm_024]]
- [[claim:clm_008]]
- [[claim:clm_009]]
- [[claim:clm_012]]
- [[claim:clm_013]]
- [[claim:clm_039]]
- [[claim:clm_055]]
- [[claim:clm_010]]
- [[claim:clm_011]]
- [[claim:clm_014]]
- [[claim:clm_015]]
- [[claim:clm_016]]
- [[claim:clm_020]]
- [[claim:clm_064]]
- [[claim:clm_065]]
- [[claim:clm_068]]
- [[claim:clm_066]]
- [[claim:clm_067]]
- [[claim:clm_030]]
- [[claim:clm_032]]
- [[claim:clm_034]]
- [[claim:clm_059]]
- [[claim:clm_069]]
- [[claim:clm_071]]
- [[claim:clm_072]]
- [[claim:clm_074]]
- [[claim:clm_001]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_040]]
- [[claim:clm_046]]
- [[claim:clm_047]]
- [[claim:clm_049]]
- [[claim:clm_052]]
- [[claim:clm_041]]
- [[claim:clm_042]]
- [[claim:clm_043]]
- [[claim:clm_045]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
