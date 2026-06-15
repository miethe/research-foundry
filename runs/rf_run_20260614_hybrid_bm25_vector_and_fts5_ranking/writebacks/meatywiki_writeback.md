---
id: mwb_20260615_hybrid_bm25_vector_and_fts5_ranking
evidence_bundle_id: bundle_20260615_intent_research_20260614_hybrid_bm25_vector
target_page: meatywiki/sources/hybrid_bm25_vector_and_fts5_ranking.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_hybrid_bm25_vector_and_fts5_ranking:
  74 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_rib034_00
  - src_20260614_rib034_01
  - src_20260614_rib034_02
  - src_20260614_rib034_03
  - src_20260614_rib034_04
  - src_20260614_rib034_05
  - src_20260614_rib034_06
  - src_20260614_rib034_07
  - src_20260614_rib034_08
  - src_20260614_rib034_09
  - src_20260614_rib034_10
  - src_20260614_rib034_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Hybrid BM25+vector and FTS5 ranking for Markdown KBs

## Summary

Source note distilled from research run rf_run_20260614_hybrid_bm25_vector_and_fts5_ranking: 74 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_rib034_00 — Introducing Contextual Retrieval
- src_20260614_rib034_01 — SQLite FTS5 Extension
- src_20260614_rib034_02 — sqlite-utils Python API — Full-text search
- src_20260614_rib034_03 — From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents
- src_20260614_rib034_04 — Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods
- src_20260614_rib034_05 — Reciprocal rank fusion — Elasticsearch Reference
- src_20260614_rib034_06 — Normalization processor — OpenSearch Documentation
- src_20260614_rib034_07 — Announcing Rerank-v3.5 — Cohere Release Notes
- src_20260614_rib034_08 — BAAI/bge-reranker-v2-m3 — Hugging Face Model Card
- src_20260614_rib034_09 — Shallow Cross-Encoders for Low-Latency Retrieval
- src_20260614_rib034_10 — Evaluating Chunking Strategies for Retrieval (Chroma Technical Report)
- src_20260614_rib034_11 — Is Semantic Chunking Worth the Computational Cost?

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
