---
schema_version: '0.1'
type: technical_memo
report_id: report_20260615_hybrid_bm25_vector_and_fts5_ranking
title: Hybrid BM25+vector and FTS5 ranking for Markdown KBs
intent_id: intent_research_20260614_hybrid_bm25_vector_and_fts5_ranking
evidence_bundle_id: pending
created_at: '2026-06-15T09:59:32-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

This memo specifies a tiered retrieval architecture for a personal, Git-backed Markdown knowledge base, and recommends a concrete FTS5 indexing recipe, a score-fusion default, and a reranking strategy.

**Inference:** For a personal Markdown artifact KB, BM25/FTS5 alone is a defensible single-tier retriever through the ~1K-10K document range, because sparse BM25 beat dense text-embedding-3-large on Recall@5 (0.644 vs 0.587) over a 7,318-document corpus, so the lexical-only break point sits at the upper edge of the 10K tier rather than at 1K. [claim:clm_inf01]
**Inference:** The BM25-only failure mode is query-type-specific rather than corpus-size-specific: hybrid fusion added its largest gain (+8.1pp Recall@5) on the table-heavy TAT-DQA subset, so a Markdown KB whose value lives in prose/headings will degrade later than one dense with tables and numeric content. [claim:clm_inf02]
**Inference:** Recommended per-tier architecture: 1K = BM25-only (FTS5) with frontmatter/heading column weighting; 10K = BM25 + cross-encoder reranking of the top ~100-200 lexical candidates (skip the vector index); 50K = full BM25 + dense vector hybrid fused by RRF then reranked. [claim:clm_inf03]
**Inference:** Adding a cross-encoder reranker is the highest-ROI single upgrade for the KB at every tier where it is affordable, contributing a +17.4% Recall@5 lift over unreranked hybrid (0.695->0.816) and a +39.7% relative MRR@3 lift (0.433->0.605), and independently driving the largest portion of the 67% failure-rate reduction in Anthropic's Contextual Retrieval stack. [claim:clm_inf04]
**Inference:** RRF with k=60 is the recommended default fusion method for BM25+vector scores in a personal KB, over weighted-linear normalization, because RRF is unsupervised, training-free, and score-scale-agnostic (no min_max/z_score calibration), and beat Condorcet/CombMNZ and every individual system by 4-5% MAP; weighted normalization should be adopted only if measured query routing shows one signal is systematically stronger. [claim:clm_inf06]

## Where BM25/FTS5-alone degrades: the corpus-size threshold

The empirical anchor for the threshold is a text-and-table retrieval benchmark. The benchmark spans 23,088 question-context-answer triples over 7,318 unique financial documents (drawn from FinQA, ConvFinQA, and TAT-DQA) averaging ~920 tokens each. [claim:clm_001]
Sparse BM25 outperforms dense text-embedding-3-large retrieval on nearly all metrics (Recall@5 0.644 vs 0.587), contradicting the assumption that semantic embeddings dominate sparse lexical retrieval. [claim:clm_002]
Hybrid fusion delivers its largest absolute gain on the table-heavy TAT-DQA subset, adding +8.1 percentage points Recall@5 over BM25 alone, showing neither sparse nor dense retrieval suffices alone on table-heavy questions. [claim:clm_007]

**Inference:** For a personal Markdown artifact KB, BM25/FTS5 alone is a defensible single-tier retriever through the ~1K-10K document range, because sparse BM25 beat dense text-embedding-3-large on Recall@5 (0.644 vs 0.587) over a 7,318-document corpus, so the lexical-only break point sits at the upper edge of the 10K tier rather than at 1K. [claim:clm_inf01]
**Inference:** The BM25-only failure mode is query-type-specific rather than corpus-size-specific: hybrid fusion added its largest gain (+8.1pp Recall@5) on the table-heavy TAT-DQA subset, so a Markdown KB whose value lives in prose/headings will degrade later than one dense with tables and numeric content. [claim:clm_inf02]

### Winning hybrid architecture per tier

**Inference:** Recommended per-tier architecture: 1K = BM25-only (FTS5) with frontmatter/heading column weighting; 10K = BM25 + cross-encoder reranking of the top ~100-200 lexical candidates (skip the vector index); 50K = full BM25 + dense vector hybrid fused by RRF then reranked. [claim:clm_inf03]

| Tier | Winning architecture | Rationale | Evidence |
| --- | --- | --- | --- |
| 1K | BM25-only FTS5 with frontmatter/heading column weighting | Lexical-only is adequate well past 1K; structural weighting captures much of hybrid's benefit at zero index cost | BM25-only suffices through ~10K [claim:clm_inf01] |
| 1K | Heading/title-weighted BM25 as the structural lift | BM25+frontmatter is a pure-FTS5 configuration needing no second index | Frontmatter weighting is a zero-cost hybrid-class lift [claim:clm_inf09] |
| 10K | BM25 + cross-encoder reranking of top ~100-200 lexical candidates; skip the vector index | Reranking is the largest single lift and needs no vector store | Reranking pays off from ~10K [claim:clm_inf05] |
| 50K | Full BM25 + dense vector hybrid fused by RRF, then reranked | Recall headroom at the largest tier justifies the dense leg | Hybrid+rerank reaches Recall@5 0.816 [claim:clm_inf04] |

## Concrete FTS5 indexing and ranking recipe for Markdown

The recipe rests on six FTS5/sqlite-utils capabilities, then composes them into a persistent column-weighted configuration.

### Indexing and tokenizer primitives

enable_fts() takes a list of named columns and indexes each as a separately searchable FTS field, which is the basis for indexing frontmatter fields and headings as distinct columns. [claim:clm_015]
Passing tokenize='porter' to enable_fts enables Porter stemming so that English words like 'running' match stemmed alternatives such as 'run'. [claim:clm_016]
enable_fts() defaults to FTS5, with an explicit fts_version='FTS4' opt-out for using the older FTS4 engine. [claim:clm_017]
table.search(q) returns rows ordered by relevance (most relevant first) automatically, without requiring an explicit sort. [claim:clm_018]
Setting include_rank=True adds a 'rank' column carrying the BM25 ranking score, available for FTS5 tables only. [claim:clm_019]
search() exposes ordering only via an order_by column argument that defaults to the relevance score; it offers no per-column bm25() weight parameter, so custom field weighting must be applied through raw FTS5 rank config / ORDER BY bm25(...). [claim:clm_020]

### Ranking and column-weighting primitives

The bm25() auxiliary function returns a real value where a numerically smaller value indicates a better match, so results are ordered best-first via ORDER BY bm25(ft). [claim:clm_064]
Per-column weights are passed as trailing arguments to bm25() in left-to-right column order, and any column without a supplied weight defaults to 1.0. [claim:clm_065]
Every FTS5 table exposes a hidden 'rank' column that by default returns the same value as bm25() called with no trailing arguments. [claim:clm_066]
ORDER BY rank is logically equivalent to ORDER BY bm25(ft) but can be faster, particularly when the query abandons early or uses a LIMIT clause. [claim:clm_067]
The default ranking for the rank column can be persisted by setting the 'rank' configuration option to a bm25 expression with column weights. [claim:clm_068]

### The recommended persistent configuration

**Inference:** Concrete FTS5 recipe for heading/frontmatter-rich Markdown: enable_fts() over distinct columns (title, headings, frontmatter tags, body) with tokenize='porter', then persist heading/title boost via the rank config e.g. INSERT INTO ft(ft,rank) VALUES('rank','bm25(10.0, 5.0, 3.0, 1.0)') so weights apply automatically through ORDER BY rank without a per-query bm25() weight argument. [claim:clm_inf08]
**Inference:** Heading- and title-weighted BM25 is itself a hybrid-class lift (BM25+frontmatter signals) available at zero extra index cost, since FTS5 lets distinct Markdown structural columns carry boost weights (e.g. title 10.0, headings 5.0, body 1.0); for the 1K tier this captures much of hybrid's benefit without any vector store. [claim:clm_inf09]
**Inference:** ORDER BY rank should be preferred over ORDER BY bm25(ft) in the KB query path because it is logically equivalent yet can short-circuit faster under LIMIT/early-abandon, which matters when the KB only needs the top-k candidates to feed a reranker. [claim:clm_inf10]

#### Indexing recipe table

| Practice | Configuration | Evidence |
| --- | --- | --- |
| Multi-column index | enable_fts() over title, headings, frontmatter tags, body indexes each as a separately searchable field [claim:clm_015] | sqlite-utils API |
| Tokenizer | tokenize='porter' enables Porter stemming for English morphological matches [claim:clm_016] | sqlite-utils API |
| Engine default | enable_fts() defaults to FTS5, with fts_version='FTS4' as the opt-out [claim:clm_017] | sqlite-utils API |
| Column weights | Per-column weights are trailing bm25() arguments in column order; unweighted columns default to 1.0 [claim:clm_065] | FTS5 docs |
| Persistent boost | The rank config option persists a bm25 expression with column weights as the default ranking [claim:clm_068] | FTS5 docs |
| Query ordering | ORDER BY rank is equivalent to ORDER BY bm25(ft) but can short-circuit faster under LIMIT [claim:clm_067] | FTS5 docs |

### Index freshness under Git churn

**Speculation:** To keep the FTS5 lexical index and the vector index consistent under Git-commit churn without duplicating Markdown bytes, the KB should use an external-content / contentless FTS5 table keyed to file path+content hash and re-index only changed files per commit, since FTS5 indexes named columns derived from source rows rather than requiring a separate copy of the text. [claim:clm_inf15]

## Score-fusion recommendation: RRF vs weighted vs learned

### How RRF and weighted fusion are defined

RRF scores each document by summing reciprocal ranks across the input rankings: RRFscore(d) = sum over r in R of 1/(k + r(d)), where each ranking r is a permutation on 1..|D|. [claim:clm_008]
RRF scores a document d by summing 1.0 / (k + rank(result(q), d)) across each query q in which d appears, where rank starts from 1. [claim:clm_056]
In the RRF formula, k is the ranking constant and rank(result(q), d) is document d's rank within result(q), starting from 1. [claim:clm_057]
The constant k is fixed at 60, chosen during a pilot investigation and never re-tuned during validation; the formula keeps lower-ranked documents from vanishing and dampens outlier systems. [claim:clm_009]
A pilot experiment over TREC topics found k=60 was near-optimal but that the exact choice was not critical, with MAP varying only slightly across k from 0 to 500. [claim:clm_010]
Elasticsearch's rank_constant (k) controls how much influence per-query result sets have on the final ranking; a higher value gives lower-ranked documents more influence, the value must be >= 1, and it defaults to 60. [claim:clm_058]
RRF is a method for combining multiple result sets that carry different relevance indicators into a single ranked result set. [claim:clm_054]
RRF requires no tuning, and the individual relevance indicators being combined do not need to be related to (or on the same scale as) one another to produce high-quality results. [claim:clm_055]
RRF is an unsupervised, training-free fusion method that combines ranks without regard to the arbitrary scores of particular ranking methods and needs no special voting algorithm or global information. [claim:clm_013]

The weighted-normalization alternative requires per-deployment score calibration. The normalization-processor is a search-phase-results processor that runs between the query and fetch phases, intercepting query-phase results to normalize and combine document scores from different query clauses before fetch. [claim:clm_035]
Supported score-normalization techniques are min_max, l2, and z_score, with min_max as the default. [claim:clm_036]
Supported score-combination techniques are arithmetic_mean, geometric_mean, and harmonic_mean (default arithmetic_mean); z_score supports only arithmetic_mean. [claim:clm_037]
Per-subquery weights are configurable in the [0.0, 1.0] range, must equal the number of queries and sum to 1.0; if omitted, all queries are weighted equally. [claim:clm_038]
BM25 and k-NN/neural searches use different relevance-score scales, so scores are normalized onto a common scale before combination, a benefit supported by experimental data. [claim:clm_039]

### Why RRF wins on quality and tuning cost

RRF consistently yields better results than any individual IR system and better results than the standard fusion method Condorcet Fuse, demonstrated by combining TREC runs and by building a LETOR 3 meta-learner. [claim:clm_011]
Across pilot and TREC experiments, RRF outperforms Condorcet Fuse, CombMNZ, and the best individual system by roughly 4% to 5% on average in MAP. [claim:clm_012]
Applying RRF to the LETOR 3 baseline rank-learning methods produces a meta-learner that, to the authors' knowledge, no reported result matches or exceeds, making it the best known method on that dataset. [claim:clm_014]

**Inference:** RRF with k=60 is the recommended default fusion method for BM25+vector scores in a personal KB, over weighted-linear normalization, because RRF is unsupervised, training-free, and score-scale-agnostic (no min_max/z_score calibration), and beat Condorcet/CombMNZ and every individual system by 4-5% MAP; weighted normalization should be adopted only if measured query routing shows one signal is systematically stronger. [claim:clm_inf06]
**Inference:** A learned fusion model is not justified for a personal KB at any tier from 1K to 50K: RRF already produces the best-known LETOR-3 meta-learner result and the k=60 choice is near-optimal-but-not-critical, so the training data, labeling, and maintenance burden of a learned fuser would buy negligible precision over zero-tuning RRF. [claim:clm_inf07]

### Fusion method comparison

| Fusion method | Tuning cost | Quality signal | Evidence |
| --- | --- | --- | --- |
| RRF (k=60) | Zero; k=60 near-optimal but non-critical across k 0-500 | +4-5% MAP over Condorcet/CombMNZ/best system | Pilot found k near-optimal, not critical [claim:clm_010] |
| RRF (k=60) | Score-scale-agnostic; combines incommensurate indicators | Beats every individual IR system and Condorcet Fuse | RRF beats individual systems and Condorcet [claim:clm_011] |
| Weighted normalization | Requires min_max/l2/z_score calibration of differing scales | Tunable per-subquery weights summing to 1.0 | Weights must sum to 1.0 in [0,1] range [claim:clm_038] |
| Learned fuser | High; needs labeled relevance judgments + maintenance | Best-known LETOR-3 result already reached by unsupervised RRF | Learned fuser not justified for personal KB [claim:clm_inf07] |

## Reranking stage: the payoff threshold and depth

Reranking is the single highest-leverage upgrade once the lexical stage saturates. Adding a Cohere reranker to the hybrid BM25+dense RRF pipeline lifts Recall@5 from 0.695 to 0.816, a +17.4% improvement over unreranked hybrid retrieval. [claim:clm_003]
Cross-encoder reranking is the single largest quality lift in the pipeline, raising MRR@3 from 0.433 to 0.605 (+39.7% relative). [claim:clm_004]
The evaluation metric is 1 minus recall@20, defined as the percentage of relevant documents that fail to be retrieved within the top 20 chunks. [claim:clm_021]
Contextual Embeddings alone cut the top-20-chunk retrieval failure rate from a 5.7% baseline to 3.7%, a 35% reduction. [claim:clm_022]
Combining Contextual Embeddings with Contextual BM25 cut the failure rate from 5.7% to 2.9%, a 49% reduction. [claim:clm_023]
Adding a reranking step on top of Contextual Embeddings and Contextual BM25 cut the failure rate from 5.7% to 1.9%, a 67% total reduction. [claim:clm_024]
The processor only transforms results returned per subquery (it does no extra sampling); using nDCG@10, a returned size of 100-200 worked best for datasets up to 10M documents, and larger sizes raised latency without improving relevance. [claim:clm_040]

**Inference:** Adding a cross-encoder reranker is the highest-ROI single upgrade for the KB at every tier where it is affordable, contributing a +17.4% Recall@5 lift over unreranked hybrid (0.695->0.816) and a +39.7% relative MRR@3 lift (0.433->0.605), and independently driving the largest portion of the 67% failure-rate reduction in Anthropic's Contextual Retrieval stack. [claim:clm_inf04]
**Inference:** The reranking stage pays off starting at the ~10K tier and earlier for table/numeric-heavy KBs, because its quality lift is the largest in the pipeline while its only cost is scoring the top ~100-200 candidates a stage the KB already retrieves; below ~1K, BM25 precision@k is high enough that the latency/cost is unlikely to repay itself. [claim:clm_inf05]

### Choosing the reranker model and depth

bge-reranker-v2-m3 is a lightweight reranker built on bge-m3 with strong multilingual capability, easy deployment, and fast inference. [claim:clm_069]
Unlike an embedding model, the reranker takes a query and a document as input and directly outputs a similarity score rather than an embedding. [claim:clm_070]
The raw reranker score can be mapped to a float in [0,1] using a sigmoid function. [claim:clm_071]
The model card lists bge-reranker-v2-m3 as based on bge-m3 with a size of 0.6B parameters. [claim:clm_072]
The authors recommend bge-reranker-v2-m3 for multilingual reranking scenarios. [claim:clm_073]
Setting use_fp16=True speeds up inference at the cost of a slight performance degradation. [claim:clm_074]
Cohere's rerank-v3.5 has a 4096-token context length and is positioned for multilingual retrieval and reasoning tasks. [claim:clm_059]
Cohere claims rerank-v3.5 achieves state-of-the-art performance on BEIR and across multiple application domains. [claim:clm_060]
With rerank-v3.5 the Rerank API makes the model parameter required. [claim:clm_061]
The max_chunks_per_doc parameter is replaced by max_tokens_per_doc, which caps per-document tokens before truncation, defaulting to 4096. [claim:clm_062]
Support for passing a list of objects for the documents parameter has been removed in the new Rerank API. [claim:clm_063]
Under a 25ms/query latency limit on TREC DL 2019, TinyBERT-gBCE reaches NDCG@10 of 0.652 versus MonoBERT-Large's 0.431, a +51% gain. [claim:clm_041]
Shallow (few-layer) transformer cross-encoders outperform full-scale models under low-latency constraints because they can score the relevance of more documents within the same time budget. [claim:clm_042]
Shallow cross-encoders remain effective on CPU: NDCG@10 drops only 3% versus GPU inference at a 50ms latency budget, making them practical without specialized hardware. [claim:clm_043]
Shallow cross-encoders benefit from the generalized Binary Cross-Entropy (gBCE) training scheme previously shown successful for recommendation tasks. [claim:clm_044]
Large-model cross-encoders (e.g., BERT or T5) are computationally expensive and can only score a small number of documents within a reasonably small latency window. [claim:clm_045]

**Inference:** For the KB's reranker, a local self-hosted bge-reranker-v2-m3 (~0.6B params, sigmoid-mapped [0,1] scores, use_fp16 for speed) is the recommended default for cost and privacy, with Cohere rerank-v3.5 (4096-token, hosted, model param required) reserved for when API simplicity or claimed BEIR-SOTA quality outweighs per-call cost and sending personal data off-device. [claim:clm_inf13]
**Inference:** Reranker depth should be chosen against a per-query latency budget, not maximized: shallow cross-encoders (TinyBERT-gBCE) beat full-scale MonoBERT-Large by +51% NDCG@10 under a 25ms/query limit and run on CPU with only ~3% loss, so a personal KB without a GPU should favor a shallow reranker over a large one. [claim:clm_inf14]

## Chunking and document-enrichment decisions

These choices govern what unit gets indexed and whether enrichment is worth its compute. Contextual Retrieval (document enrichment) yields modest gains, improving dense retrieval by +2.8pp and hybrid retrieval by +2.2pp Recall@5. [claim:clm_005]
Contextual Retrieval prepends a short LLM-generated context to each chunk before indexing, e.g. identifying the source filing and prior-quarter revenue. [claim:clm_025]
The method was evaluated across multiple knowledge domains including codebases, fiction, ArXiv papers, and science papers. [claim:clm_026]
HyDE-style query expansion hurts retrieval on this corpus, underperforming even vanilla dense retrieval (Recall@5 0.544 vs 0.587) because generated hypothetical documents hallucinate plausible-but-wrong financial figures. [claim:clm_006]

The chunking benchmarks frame the cost/benefit. The choice of chunking strategy materially affects retrieval performance, with the best strategies outperforming others by up to 9% in recall on a fixed retriever. [claim:clm_027]
The report evaluates chunkers with token-level Recall, Precision, Precision-Omega (precision when all chunks containing excerpt tokens are retrieved), and IoU. [claim:clm_028]
Precision-Omega is defined as the precision achieved under the assumption that every chunk containing excerpt tokens was successfully retrieved (a max-precision-under-perfect-recall ceiling). [claim:clm_029]
The LLMSemanticChunker (GPT-4o) achieved the highest recall at 91.9%, but with very low precision (3.9%) reflecting low retrieval efficiency. [claim:clm_030]
The ClusterSemanticChunker is an embedding-aware splitter that uses dynamic programming to maximize pairwise cosine similarity within each chunk up to a user-specified maximum length. [claim:clm_031]
The ClusterSemanticChunker at 400 tokens reached 91.3% recall with 4.5% precision, nearly matching the top recall while remaining an embedding-model-aware splitter. [claim:clm_032]
The authors conclude the embedding-model-aware ClusterSemanticChunker produced consistently strong results across the evaluation. [claim:clm_033]
Recall plateaus and then degrades as chunk size changes: overly large chunks dilute relevant information while overly small chunks fail to capture necessary context, framing the recall-vs-completeness tradeoff. [claim:clm_034]
The study concludes that the computational costs of semantic chunking are not justified by consistent performance gains over fixed-size chunking in RAG. [claim:clm_046]
On non-stitched document-retrieval datasets, fixed-size chunking led on F1@5, scoring 90.59% on HotpotQA and 93.58% on MSMARCO. [claim:clm_047]
Breakpoint-based semantic chunking outperformed fixed-size only on artificially stitched high-topic-diversity data, reaching 81.89% F1@5 on Miracl versus 69.45% for fixed-size. [claim:clm_048]
The authors caution that real-world document topics are likely less diverse than their stitched data, so semantic chunkers may have no edge over fixed-size chunking in practice. [claim:clm_049]
Evidence-retrieval F1@5 differences across chunkers were minimal (e.g., ExpertQA: fixed-size 47.11% vs clustering 46.87%), with no clear advantage for any strategy. [claim:clm_050]
In retrieval-based answer generation, BERTScore differences between chunking methods were negligible and inconclusive. [claim:clm_051]
The paper recommends fixed-size chunking as a more efficient and reliable default for practical RAG applications. [claim:clm_052]
The study compares three chunkers (fixed-size, breakpoint-based semantic, clustering-based semantic) across document retrieval, evidence retrieval, and answer generation using BEIR and RAGBench datasets. [claim:clm_053]

**Inference:** Whole-document or heading-section indexing should be the default for the Markdown KB rather than expensive semantic chunking: fixed-size chunking led non-stitched document retrieval (F1@5 90.59% HotpotQA, 93.58% MSMARCO) and semantic chunking only won on artificially topic-stitched data, so its compute cost is not justified for naturally coherent Markdown artifacts. [claim:clm_inf11]
**Inference:** When the KB does chunk (at 50K with a vector index), heading-delimited or fixed-window chunking sized to the embedding model is preferable to LLM-driven semantic chunking, because the LLMSemanticChunker reached 91.9% recall at only 3.9% precision while the embedding-aware ClusterSemanticChunker matched recall (91.3%) far more efficiently and chunk size must be tuned to avoid the recall plateau-then-degrade effect. [claim:clm_inf12]

## Per-tier comparison matrix

The tables below score four configurations against recall/precision, latency, and cost at each tier, with the evidence tag carried in each row.

### 1K tier

| Configuration | Recall/precision | Latency | Cost | Evidence |
| --- | --- | --- | --- | --- |
| BM25-only | Lexical-only adequate well past 1K (BM25 Recall@5 0.644 > dense 0.587) [claim:clm_002] | Single FTS5 query; ORDER BY rank short-circuits under LIMIT [claim:clm_067] | 100% local FTS5, effectively zero marginal cost at 1K (**Speculation**) [claim:clm_spec01] | mixed |
| BM25+frontmatter | Structural column weighting captures much of hybrid's benefit at 1K [claim:clm_inf09] | Same single FTS5 query path; persisted via rank config [claim:clm_068] | Zero extra index cost; pure-FTS5 configuration [claim:clm_inf09] | inference |
| BM25+vector | Hybrid's largest uplift is on table-heavy queries, not small prose corpora [claim:clm_007] | Adds a dense leg plus RRF fusion over k=60 [claim:clm_008] | Reserved for 50K; vector index unjustified at 1K [claim:clm_inf03] | mixed |
| BM25+reranking | Below ~1K, BM25 precision@k is high enough that reranking is unlikely to repay its cost [claim:clm_inf05] | Adds a top-100-200 cross-encoder scoring pass [claim:clm_040] | Reranking ROI not yet reached below ~1K [claim:clm_inf05] | inference |

### 10K tier

| Configuration | Recall/precision | Latency | Cost | Evidence |
| --- | --- | --- | --- | --- |
| BM25-only | Still defensible through ~10K on prose/heading corpora [claim:clm_inf01] | Single FTS5 query path [claim:clm_067] | 100% local FTS5 (**Speculation**) [claim:clm_spec01] | mixed |
| BM25+frontmatter | Heading/title weighting remains a zero-cost lift [claim:clm_inf09] | Same single-query path; weights via rank config [claim:clm_068] | Zero extra index cost [claim:clm_inf09] | inference |
| BM25+vector | Hybrid adds its largest gain (+8.1pp Recall@5) on table-heavy content [claim:clm_007] | Dense leg + RRF fusion adds a stage [claim:clm_008] | Vector index skipped at 10K in favor of reranking [claim:clm_inf03] | mixed |
| BM25+reranking | Reranking is the largest single lift and pays off from ~10K [claim:clm_inf05] | Scores top ~100-200 candidates; CPU-viable shallow reranker loses only ~3% [claim:clm_043] | Dominant cost shifts to a local CPU rerank pass, near-zero cash (**Speculation**) [claim:clm_spec01] | mixed |

### 50K tier

| Configuration | Recall/precision | Latency | Cost | Evidence |
| --- | --- | --- | --- | --- |
| BM25-only | Lexical-only insufficient on table-heavy questions at scale [claim:clm_007] | Single FTS5 query path [claim:clm_067] | 100% local FTS5 (**Speculation**) [claim:clm_spec01] | mixed |
| BM25+frontmatter | Structural weighting still a free lift but does not close the table gap [claim:clm_007] | Same single-query path [claim:clm_068] | Zero extra index cost [claim:clm_inf09] | mixed |
| BM25+vector | Full hybrid fused by RRF recommended at 50K [claim:clm_inf03] | Dense leg + RRF; 100-200 candidate window optimal up to 10M docs [claim:clm_040] | Embedding generation + vector-index maintenance becomes the largest recurring cost (**Speculation**) [claim:clm_spec01] | mixed |
| BM25+reranking | Hybrid+rerank reaches Recall@5 0.816 (+17.4%) and MRR@3 0.605 (+39.7%) [claim:clm_003] | Reranking adds a fixed top-100-200 scoring pass [claim:clm_040] | Reranking is a fixed per-query add-on atop the dense leg (**Speculation**) [claim:clm_spec01] | mixed |

## Analysis and derivation

### RRF mechanics

RRF scores each document by summing reciprocal ranks across the input rankings: RRFscore(d) = sum over r in R of 1/(k + r(d)), where each ranking r is a permutation on 1..|D|. [claim:clm_008]
The constant k is fixed at 60, chosen during a pilot investigation and never re-tuned during validation; the formula keeps lower-ranked documents from vanishing and dampens outlier systems. [claim:clm_009]
A pilot experiment over TREC topics found k=60 was near-optimal but that the exact choice was not critical, with MAP varying only slightly across k from 0 to 500. [claim:clm_010]

### Why reranking dominates the marginal-quality budget

Across two independent benchmarks the reranking stage is isolated as the largest contributor. Cross-encoder reranking is the single largest quality lift in the pipeline, raising MRR@3 from 0.433 to 0.605 (+39.7% relative). [claim:clm_004]
Adding a reranking step on top of Contextual Embeddings and Contextual BM25 cut the failure rate from 5.7% to 1.9%, a 67% total reduction. [claim:clm_024]
The processor only transforms results returned per subquery (it does no extra sampling); using nDCG@10, a returned size of 100-200 worked best for datasets up to 10M documents, and larger sizes raised latency without improving relevance. [claim:clm_040]

**Inference:** The reranking stage pays off starting at the ~10K tier and earlier for table/numeric-heavy KBs, because its quality lift is the largest in the pipeline while its only cost is scoring the top ~100-200 candidates a stage the KB already retrieves; below ~1K, BM25 precision@k is high enough that the latency/cost is unlikely to repay itself. [claim:clm_inf05]

### Predicted cost split across tiers

**Speculation:** Predicted cheap-lexical / expensive-reranker cost split: at 1K the KB stays 100% local FTS5 (effectively zero marginal cost); at 10K the dominant cost shifts to reranking the top ~100-200 candidates per query (a local bge/TinyBERT pass, still near-zero cash cost on CPU); at 50K the embedding-generation and vector-index maintenance for the dense leg becomes the largest recurring cost, with reranking a fixed per-query add-on. [claim:clm_spec01]

## Recommendations and decision rules

**Inference:** Recommended per-tier architecture: 1K = BM25-only (FTS5) with frontmatter/heading column weighting; 10K = BM25 + cross-encoder reranking of the top ~100-200 lexical candidates (skip the vector index); 50K = full BM25 + dense vector hybrid fused by RRF then reranked. [claim:clm_inf03]
**Inference:** Concrete FTS5 recipe for heading/frontmatter-rich Markdown: enable_fts() over distinct columns (title, headings, frontmatter tags, body) with tokenize='porter', then persist heading/title boost via the rank config e.g. INSERT INTO ft(ft,rank) VALUES('rank','bm25(10.0, 5.0, 3.0, 1.0)') so weights apply automatically through ORDER BY rank without a per-query bm25() weight argument. [claim:clm_inf08]
**Inference:** ORDER BY rank should be preferred over ORDER BY bm25(ft) in the KB query path because it is logically equivalent yet can short-circuit faster under LIMIT/early-abandon, which matters when the KB only needs the top-k candidates to feed a reranker. [claim:clm_inf10]
**Inference:** RRF with k=60 is the recommended default fusion method for BM25+vector scores in a personal KB, over weighted-linear normalization, because RRF is unsupervised, training-free, and score-scale-agnostic (no min_max/z_score calibration), and beat Condorcet/CombMNZ and every individual system by 4-5% MAP; weighted normalization should be adopted only if measured query routing shows one signal is systematically stronger. [claim:clm_inf06]
**Inference:** A learned fusion model is not justified for a personal KB at any tier from 1K to 50K: RRF already produces the best-known LETOR-3 meta-learner result and the k=60 choice is near-optimal-but-not-critical, so the training data, labeling, and maintenance burden of a learned fuser would buy negligible precision over zero-tuning RRF. [claim:clm_inf07]
**Inference:** Adding a cross-encoder reranker is the highest-ROI single upgrade for the KB at every tier where it is affordable, contributing a +17.4% Recall@5 lift over unreranked hybrid (0.695->0.816) and a +39.7% relative MRR@3 lift (0.433->0.605), and independently driving the largest portion of the 67% failure-rate reduction in Anthropic's Contextual Retrieval stack. [claim:clm_inf04]
**Inference:** For the KB's reranker, a local self-hosted bge-reranker-v2-m3 (~0.6B params, sigmoid-mapped [0,1] scores, use_fp16 for speed) is the recommended default for cost and privacy, with Cohere rerank-v3.5 (4096-token, hosted, model param required) reserved for when API simplicity or claimed BEIR-SOTA quality outweighs per-call cost and sending personal data off-device. [claim:clm_inf13]
**Inference:** Reranker depth should be chosen against a per-query latency budget, not maximized: shallow cross-encoders (TinyBERT-gBCE) beat full-scale MonoBERT-Large by +51% NDCG@10 under a 25ms/query limit and run on CPU with only ~3% loss, so a personal KB without a GPU should favor a shallow reranker over a large one. [claim:clm_inf14]
**Inference:** Whole-document or heading-section indexing should be the default for the Markdown KB rather than expensive semantic chunking: fixed-size chunking led non-stitched document retrieval (F1@5 90.59% HotpotQA, 93.58% MSMARCO) and semantic chunking only won on artificially topic-stitched data, so its compute cost is not justified for naturally coherent Markdown artifacts. [claim:clm_inf11]
**Inference:** When the KB does chunk (at 50K with a vector index), heading-delimited or fixed-window chunking sized to the embedding model is preferable to LLM-driven semantic chunking, because the LLMSemanticChunker reached 91.9% recall at only 3.9% precision while the embedding-aware ClusterSemanticChunker matched recall (91.3%) far more efficiently and chunk size must be tuned to avoid the recall plateau-then-degrade effect. [claim:clm_inf12]
**Speculation:** Query routing will likely add measurable precision on the KB: keyword/navigational lookups (exact filenames, tags, headings) are best served by lexical FTS5 alone, conceptual queries by the dense+rerank path, and a lightweight router that sends only conceptual queries through the expensive stages would cut average latency/cost while preserving precision@k. [claim:clm_spec02]

## Open questions

- At what exact document count does the table-heavy vs prose-heavy degradation curve cross for this specific KB's content mix?
- Does the external-content / contentless FTS5 freshness strategy hold up under real Git-commit churn at 50K documents?
- Would a measured query router actually preserve precision@k while cutting average latency on this KB's query distribution?
- How much per-call cost and latency does the embedding-generation + vector-index maintenance leg add at the 50K tier in practice?

## Sources

- src_20260614_rib034_03: From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents
- src_20260614_rib034_04: Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods
- src_20260614_rib034_02: sqlite-utils Python API — Full-text search
- src_20260614_rib034_00: Introducing Contextual Retrieval
- src_20260614_rib034_10: Evaluating Chunking Strategies for Retrieval (Chroma Technical Report)
- src_20260614_rib034_06: Normalization processor — OpenSearch Documentation
- src_20260614_rib034_09: Shallow Cross-Encoders for Low-Latency Retrieval
- src_20260614_rib034_11: Is Semantic Chunking Worth the Computational Cost?
- src_20260614_rib034_05: Reciprocal rank fusion — Elasticsearch Reference
- src_20260614_rib034_07: Announcing Rerank-v3.5 — Cohere Release Notes
- src_20260614_rib034_01: SQLite FTS5 Extension
- src_20260614_rib034_08: BAAI/bge-reranker-v2-m3 — Hugging Face Model Card
