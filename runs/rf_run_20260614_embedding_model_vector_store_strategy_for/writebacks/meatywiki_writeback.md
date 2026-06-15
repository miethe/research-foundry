---
id: mwb_20260615_embedding_model_vector_store_strategy_for
evidence_bundle_id: bundle_20260615_intent_research_20260614_embedding_model_vector
target_page: meatywiki/sources/embedding_model_vector_store_strategy_for.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_embedding_model_vector_store_strategy_for:
  72 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_rib033_00
  - src_20260614_rib033_01
  - src_20260614_rib033_02
  - src_20260614_rib033_03
  - src_20260614_rib033_04
  - src_20260614_rib033_05
  - src_20260614_rib033_06
  - src_20260614_rib033_07
  - src_20260614_rib033_08
  - src_20260614_rib033_09
  - src_20260614_rib033_10
  - src_20260614_rib033_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Embedding model + vector-store strategy for a 1K-100K file-first vault

## Summary

Source note distilled from research run rf_run_20260614_embedding_model_vector_store_strategy_for: 72 supported claim(s) across 12 source card(s).

## Key claims

- MMTEB is a large-scale, community-driven expansion of MTEB covering over 500 quality-controlled evaluation tasks across 250+ languages. [claim:clm_001]
- MMTEB adds novel task categories beyond standard retrieval/classification: instruction following, long-document retrieval, and code retrieval. [claim:clm_002]
- The best-performing publicly available model on MMTEB is multilingual-e5-large-instruct at only 560M parameters, outperforming much larger billion-parameter LLMs (which lead only on certain subsets/categories). [claim:clm_003]
- To reduce compute cost, MMTEB introduces an inter-task-correlation downsampling method that preserves relative model rankings while selecting a diverse task subset. [claim:clm_004]
- Retrieval tasks are optimized by sampling hard negatives to create smaller but effective splits, yielding benchmarks that drastically reduce computational demands. [claim:clm_005]
- The new zero-shot English benchmark preserves a ranking order similar to the full-scale version at a fraction of the computational cost. [claim:clm_006]
- The paper was submitted to arXiv on 19 Feb 2025 (v1) and accepted as a conference paper at ICLR 2025. [claim:clm_007]
- OpenAI's text-embedding-3-small is priced at $0.02 per 1M tokens on the standard API. [claim:clm_008]
- The Batch API rate for text-embedding-3-small is the same $0.02 per 1M tokens as the standard API. [claim:clm_009]
- OpenAI describes text-embedding-3-small as an improved, more performant successor to its ada embedding model. [claim:clm_010]
- By contrast, the larger text-embedding-3-large model is priced at $0.13 per 1M tokens per its companion model page. [claim:clm_011]
- OpenAI lists embeddings use cases including search, clustering, recommendations, anomaly detection, and classification. [claim:clm_012]
- sqlite-vec v0.1.0 supports only brute-force search, which degrades on large datasets exceeding 1M vectors with large dimensions. [claim:clm_013]
- The maintainer's goal is to add an approximate-nearest-neighbors search mode before the v1 release, accepting a trade of accuracy and resource usage for speed. [claim:clm_014]
- Any ANN solution must remain SQLite-native: storing data in shadow tables, fitting within pages, and keeping memory usage low. [claim:clm_015]
- Among candidate ANN algorithms (IVF, HNSW, DiskANN), the maintainer favors DiskANN for its simplicity, specifically LM-DiskANN. [claim:clm_016]
- Open design questions about the ANN index — including storage, declaration syntax, metadata filtering, and query-level KNN/ANN selection — are coordinated in this single GitHub tracking issue. [claim:clm_017]
- BGE-M3 produces dense embeddings of dimension 1024 and supports a maximum input sequence length of 8192 tokens. [claim:clm_018]
- BGE-M3 can simultaneously perform three retrieval functionalities: dense retrieval, multi-vector (ColBERT) retrieval, and sparse (lexical) retrieval. [claim:clm_019]
- BGE-M3 supports more than 100 working languages. [claim:clm_020]
- BGE-M3 can process inputs of varying granularity, from short sentences up to long documents of up to 8192 tokens. [claim:clm_021]
- The model card recommends a RAG retrieval pipeline of hybrid retrieval (dense + sparse) followed by re-ranking for higher accuracy and generalization. [claim:clm_022]
- Re-ranking with a cross-encoder is recommended because cross-encoder re-rankers achieve higher accuracy than bi-encoder embedding models. [claim:clm_023]
- On CPU, for the shortest-text dataset (stsb), ONNX with int8 quantization reaches a 3.08x speedup over the PyTorch fp32 baseline, versus 1.39x for plain ONNX and 1.29x for OpenVINO. [claim:clm_024]
- For Intel CPUs where a 0.4% accuracy loss is acceptable, the documentation recommends the openvino-qint8 backend; non-Intel CPUs are routed to plain onnx. [claim:clm_025]
- On GPU, the flowchart recommends onnx-O4 when text is usually smaller than 500 characters and PyTorch float16 otherwise. [claim:clm_026]
- On GPU for the shortest-text dataset, ONNX-O4 reaches 1.83x speedup while fp16 and bf16 reach only 1.54x and 1.53x, leading to the recommendation of ONNX on GPU for shorter texts. [claim:clm_027]
- The reported speedups are averaged across 4 models, 3 datasets, and many batch sizes, so aggressive averaging hides finer patterns and results must be tested per model and data. [claim:clm_028]
- For longer texts ONNX and OpenVINO can perform slightly worse than PyTorch, and the docs caution that real backend choice should be measured on your specific model and data. [claim:clm_029]
- On the MTEB benchmark, text-embedding-3-large scores 64.6%, text-embedding-3-small scores 62.3%, and text-embedding-ada-002 scores 61.0%. [claim:clm_030]
- All three embedding models (3-small, 3-large, ada-002) accept a maximum of 8192 input tokens. [claim:clm_031]
- Default output dimensionality is 1536 for text-embedding-3-small and 3072 for text-embedding-3-large. [claim:clm_032]
- The dimensions parameter lets developers shorten embeddings (remove numbers from the end of the vector) without losing the embedding's concept-representing properties. [claim:clm_033]
- A text-embedding-3-large embedding shortened to 256 dimensions still outperforms an unshortened text-embedding-ada-002 embedding at 1536 dimensions. [claim:clm_034]
- OpenAI recommends using the dimensions parameter at embedding-creation time as the preferred approach for reducing dimensionality. [claim:clm_035]
- The latest sqlite-vec releases are the v0.1.10-alpha series (alpha.4 dated 2026-05-18), while the last stable line is v0.1.9, released 2026-03-31. [claim:clm_036]
- The v0.1.10 alpha series introduces three new ANN index approaches in sqlite-vec: rescore, IVF (experimental and not enabled), and DiskANN. [claim:clm_037]
- ANN support via DiskANN was announced in v0.1.7 as the project's biggest upcoming update, indicating that prior stable releases were brute-force KNN only. [claim:clm_038]
- sqlite-vec is a loadable SQLite extension written in pure C with no dependencies that runs anywhere SQLite runs, including Linux, macOS, Windows, WASM in the browser, and Raspberry Pis. [claim:clm_039]
- Vectors are stored and queried inside SQLite vec0 virtual tables, supporting float, int8, and binary vector types, so the vector store lives entirely within the SQLite database file. [claim:clm_040]
- The DiskANN/IVF ANN features remain under active development through the v0.1.10 alpha series, with ongoing bug fixes and integration tests across flat and ANN indexes. [claim:clm_041]
- pgvector's HNSW index defaults are m=16 (max connections per layer) and ef_construction=64 (dynamic candidate list size for building the graph). [claim:clm_042]
- The HNSW query-time candidate list size (ef_search) defaults to 40 in pgvector. [claim:clm_043]
- pgvector documents that HNSW offers better speed-recall query performance than IVFFlat but has slower build times and uses more memory. [claim:clm_044]
- For IVFFlat, pgvector recommends sizing lists as rows/1000 for up to 1M rows and sqrt(rows) above 1M rows. [claim:clm_045]
- pgvector recommends starting the IVFFlat probes parameter at sqrt(lists). [claim:clm_046]
- pgvector supports indexing halfvec (2-byte) vectors up to 4,000 dimensions and bit/binary vectors up to 64,000 dimensions. [claim:clm_047]
- pgvector's current release is v0.8.2 and runs as a Postgres extension requiring a running Postgres server (Postgres 13+), not an embeddable single-file store. [claim:clm_048]
- nomic-embed-text-v1.5 uses Matryoshka Representation Learning to let developers trade off embedding size for a negligible reduction in performance. [claim:clm_049]
- Matryoshka training supports embedding dimensions of 768, 512, 256, 128, and 64, with MTEB averages of 62.28, 61.96, 61.04, 59.34, and 56.10 respectively. [claim:clm_050]
- Truncating from 768 to 512 dimensions costs roughly 0.32 MTEB points (62.28 to 61.96) and to 256 dimensions roughly 1.24 points (62.28 to 61.04), confirming the negligible-degradation tradeoff. [claim:clm_051]
- The model natively supports scaling the sequence length past 2048 tokens (up to 8192). [claim:clm_052]
- The model is built starting from a long-context BERT base (nomic-bert-2048), then trained with unsupervised contrastive stages on weakly related text pairs. [claim:clm_053]
- Embeddings are resized to a target Matryoshka dimension by layer-normalizing and slicing to matryoshka_dim, enabling client-side dimension reduction without re-embedding. [claim:clm_054]
- M3-Embedding (BGE-M3) is an embedding model distinguished by three axes of versatility — multi-linguality, multi-functionality, and multi-granularity — providing uniform semantic retrieval support for more than 100 working languages. [claim:clm_055]
- A single M3-Embedding model can simultaneously perform all three common retrieval functionalities — dense retrieval, multi-vector retrieval, and sparse (lexical) retrieval. [claim:clm_056]
- M3-Embedding processes inputs of varying granularity, from short sentences up to long documents of 8,192 tokens, enabling long-document retrieval. [claim:clm_057]
- The model is trained via a novel self-knowledge distillation approach in which relevance scores from the different retrieval functionalities are integrated as a teacher signal to improve training quality. [claim:clm_058]
- Training optimizes the batching strategy to enable a large batch size and high training throughput, improving the discriminativeness of the learned embeddings. [claim:clm_059]
- The paper was first submitted 5 Feb 2024 (v1) by BAAI authors (Chen, Xiao, Zhang, Luo, Lian, Liu); its latest revision v5 is dated 12 Dec 2025, keeping it within an active-maintenance freshness window. [claim:clm_060]
- pgvector 0.7.0, an open-source PostgreSQL vector similarity search extension, was announced on PostgreSQL.org on 2024-04-30 (CHANGELOG dated 2024-04-29). [claim:clm_061]
- pgvector 0.7.0 adds the halfvec type (2-byte floats, indexable up to 4,000 dimensions) and the sparsevec type (indexable up to 1,000 nonzero dimensions). [claim:clm_062]
- pgvector 0.7.0 adds indexing support for binary vectors using the bit type, indexable up to 64,000 dimensions. [claim:clm_063]
- pgvector 0.7.0 supports quantizing vectors via expression indexes, including 4-byte to 2-byte float quantization and binary quantization through the binary_quantize function. [claim:clm_064]
- pgvector 0.7.0 adds hamming_distance and jaccard_distance functions for bit vectors and adds HNSW indexing support for L1 distance operations. [claim:clm_065]
- pgvector 0.7.0 adds SIMD support with CPU dispatching for Linux x86-64 architectures. [claim:clm_066]
- The model maps sentences and paragraphs to a 384-dimensional dense vector space, suitable for clustering and semantic search. [claim:clm_067]
- The model is intended as a sentence and short-paragraph encoder, and by default truncates input longer than 256 word pieces. [claim:clm_068]
- Training uses a contrastive learning objective where the model predicts which randomly sampled sentence was actually paired with a given sentence. [claim:clm_069]
- The model was fine-tuned on a concatenation of multiple datasets totaling over 1 billion sentence pairs (1,170,060,424 training tuples). [claim:clm_070]
- The model is fine-tuned from the pretrained nreimers/MiniLM-L6-H384-uncased base model. [claim:clm_071]
- The model has 22.7M parameters and reports a score of 50.17 on the ArguAna retrieval task. [claim:clm_072]

## Sources

- src_20260614_rib033_00 — BAAI/bge-m3 - Hugging Face model card
- src_20260614_rib033_01 — M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation
- src_20260614_rib033_02 — nomic-ai/nomic-embed-text-v1.5 - Hugging Face model card
- src_20260614_rib033_03 — sentence-transformers/all-MiniLM-L6-v2 - Hugging Face model card
- src_20260614_rib033_04 — Vector embeddings | OpenAI API (text-embedding-3 model specs)
- src_20260614_rib033_05 — OpenAI text-embedding-3-small model page (pricing)
- src_20260614_rib033_06 — MMTEB: Massive Multilingual Text Embedding Benchmark
- src_20260614_rib033_07 — Speeding up Inference - Sentence Transformers documentation
- src_20260614_rib033_08 — Releases · asg017/sqlite-vec
- src_20260614_rib033_09 — Tracking issue: ANN (Approximate Nearest Neighbors) Index · Issue #25 · asg017/sqlite-vec
- src_20260614_rib033_10 — pgvector/pgvector: Open-source vector similarity search for Postgres
- src_20260614_rib033_11 — pgvector 0.7.0 Released!

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
