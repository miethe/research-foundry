---
id: mwb_20260622_dr_embedding_model_vector_store_strategy
evidence_bundle_id: bundle_20260615_intent_research_20260614_embedding_model_vector
target_page: meatywiki/decisions/embedding_model_vector_store_strategy_for.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_embedding_model_vector_store_strategy_for: BGE-M3 spec
  (1024d/8192 tokens) covers long notes whereas MiniLM truncates at 256 word pieces; local weights cost
  $0 vs '
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf04
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
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_018
  - clm_021
  - clm_068
  - clm_008
  - clm_067
  - clm_072
  - clm_039
  - clm_040
  - clm_048
  - clm_044
  - clm_042
  - clm_043
  - clm_013
  - clm_064
  - clm_047
  - clm_063
  - clm_023
  - clm_022
  - clm_052
  - clm_051
  - clm_030
  - clm_050
  - clm_037
  - clm_041
  - clm_036
  - clm_045
  - clm_033
  - clm_034
  - clm_054
  - clm_019
  - clm_056
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Embedding model + vector-store strategy for a 1K-100K file-first vault

## Context

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

## Decision

For a single-user file-first Markdown vault, local BGE-M3 (1024-dim dense, 8192-token context) is the recommended default embedding model because its 8192-token context natively covers whole Markdown notes that exceed all-MiniLM-L6-v2's 256-word-piece truncation limit, while embeddings remain free and fully offline. [claim:clm_inf01]

## Rationale

- BGE-M3 spec (1024d/8192 tokens) covers long notes whereas MiniLM truncates at 256 word pieces; local weights cost $0 vs OpenAI's $0.02/1M tokens, so a local long-context model dominates for privacy-first vaults. [claim:clm_inf01]
- MiniLM's 384 dimensions and 22.7M params make it the lightest option and produce the smallest vectors, but the 256-word-piece truncation and modest ArguAna score (50.17) cap retrieval quality on longer Markdown, so it fits only short-note vaults. [claim:clm_inf02]
- sqlite-vec stores float/int8/binary vectors in vec0 virtual tables inside a single dependency-free SQLite file, so backup/restore is a file copy and the index regenerates from Markdown; pgvector by contrast requires a running Postgres server, raising operational complexity for a single user. [claim:clm_inf04]
- pgvector states HNSW beats IVFFlat on speed-recall at the cost of slower builds and more memory; for a solo vault where index rebuilds are infrequent and query quality matters most, the HNSW tradeoff is favorable with documented defaults m=16/ef_construction=64/ef_search=40. [claim:clm_inf07]
- Combines sqlite-vec's brute-force-only nature plus its int8/binary support at small/mid scale with pgvector HNSW's superior speed-recall at large scale; the single-file property keeps the operator on sqlite-vec while latency is acceptable, deferring the Postgres-server step to the top tier. [claim:clm_inf08]
- pgvector 0.7.0 adds 4-byte->2-byte and binary quantization plus halfvec/bit indexing up to 4,000/64,000 dims, and sqlite-vec natively stores int8 and binary vectors; quantization cuts bytes-per-vector ~2x (halfvec) to ~32x (binary), the standard memory/recall tradeoff at scale. [claim:clm_inf10]
- Cross-encoders are documented as more accurate than bi-encoders but run a forward pass per candidate; at small vault sizes brute-force dense retrieval already returns the right documents, so reranking is best reserved for larger tiers or ambiguous queries (low confidence on the exact threshold). [claim:clm_inf12]
- BGE-M3 and nomic both handle up to 8192 tokens, so a Markdown heading section almost always fits in one chunk, maximizing context per embedding; MiniLM's 256-word-piece truncation would split the same section, degrading coherence, so chunking is model-context-dependent. [claim:clm_inf13]
- Synthesizes the model verdict (BGE-M3 long-context, hybrid-capable), the dimensionality sweet spot (~512d at ~0.32 MTEB loss by analogy to nomic's curve), the file-first default backend (sqlite-vec single file), and the documented upgrade path (pgvector HNSW better speed-recall) into one end-to-end default. [claim:clm_inf16]
- text-embedding-3-small posts 62.3 MTEB; nomic-embed-text-v1.5 at 768d posts a 62.28 MTEB average, essentially a tie, and BGE-M3 is a strong multilingual peer. The quality delta is within benchmark noise while local models keep all data on-disk at $0/token, so privacy outweighs the marginal quality difference. [claim:clm_inf03]
- sqlite-vec v0.1.0/stable is brute-force only and degrades on large datasets; ANN (DiskANN/IVF) only appears in the v0.1.10-alpha line which remains under active development, so production-grade ANN for 100K vectors is not yet on the stable channel. [claim:clm_inf05]
- sqlite-vec cites >1M vectors as where brute force slows, but interactive single-user latency degrades earlier as scan cost grows linearly; pgvector's IVFFlat list guidance (rows/1000 up to 1M) and HNSW's documented better speed-recall imply ANN payoff begins in the tens-of-thousands range for sub-second queries. Exact crossover is hardware-dependent (low confidence). [claim:clm_inf06]
- nomic's published curve shows 768->256 costs ~1.24 MTEB points and 768->512 only ~0.32, and OpenAI's dimensions parameter plus its 3-large-at-256-beats-ada-1536 result confirm the same negligible-degradation pattern; truncating to 256-512d roughly halves-to-thirds per-vector storage for minor quality loss. [claim:clm_inf09]
- BGE-M3 produces dense, sparse, and multi-vector outputs from one model and its authors explicitly recommend hybrid retrieval + re-ranking; since the sparse signal is a byproduct of the same encoder pass, the added complexity is marginal and the lexical leg helps exact-keyword recall that dense vectors miss. [claim:clm_inf11]
- sqlite-vec is a dependency-free extension storing everything in one file (copy = backup); pgvector mandates a running Postgres server with its own lifecycle, so install/backup/restore burden is structurally higher and only pays off when query scale or concurrency demands a server. [claim:clm_inf14]
- Both backends store vectors as rows that can be updated/inserted individually, so a Git commit touching N notes triggers only N re-embeds; with local models the marginal embed cost is $0 and with text-embedding-3-small it is $0.02/1M tokens, keeping staleness cheap to repair per commit. [claim:clm_inf15]

## Consequences

- all-MiniLM-L6-v2 (384-dim, 22.7M params, 256-word-piece truncation) is the right embedding model only for vaults of short atomic notes where minimal RAM/CPU and the smallest index footprint matter more than recall on long documents. [claim:clm_inf02]
- sqlite-vec is the recommended default vector backend for a Git/Obsidian-compatible solo homelab because its entire vector store lives inside one dependency-free SQLite file that sits beside the vault, is trivially backed up, and is fully re-buildable from the Markdown sources. [claim:clm_inf04]
- At the 100K-artifact ceiling pgvector with an HNSW index is the recommended backend over IVFFlat, because pgvector documents HNSW as having a better speed-recall tradeoff and a single operator pays its slower build time and higher memory only rarely. [claim:clm_inf07]
- A three-tier scaling ladder is recommended: brute-force sqlite-vec at 1K, sqlite-vec with int8/binary quantized vectors (or alpha DiskANN) at 10K, and pgvector HNSW (or stabilized DiskANN) at 100K, with migration triggered by interactive query latency rather than a fixed artifact count alone. [claim:clm_inf08]
- Binary/int8 quantization is the recommended lever for hitting the 100K ceiling cheaply: pgvector's binary_quantize and halfvec expression indexes and sqlite-vec's native int8/binary vec0 types both shrink index size several-fold, trading a tolerable recall drop for memory and latency headroom. [claim:clm_inf10]
- Cross-encoder re-ranking should be applied only as an optional top-k refinement on a solo vault, because while it raises accuracy over bi-encoder retrieval it adds per-query compute that is hard to justify below roughly 10K artifacts where brute-force dense recall is already high. [claim:clm_inf12]
- Heading-section chunking is the recommended Markdown chunking strategy for BGE-M3 and nomic-embed, because their 8192-token context comfortably holds a full heading section, preserving semantic coherence without the truncation that fixed small windows or MiniLM's 256-word-piece limit would force. [claim:clm_inf13]
- The recommended default stack for a privacy-first, Git/Obsidian-compatible solo vault in the 1K-100K range is BGE-M3 embeddings truncated to 512 dimensions stored in sqlite-vec, migrating only the dense index to pgvector HNSW if interactive query latency degrades near the 100K ceiling. [claim:clm_inf16]
- Choosing fully local embeddings (BGE-M3 or nomic-embed-text-v1.5) over OpenAI text-embedding-3-small costs roughly 0-2 aggregate MTEB points of retrieval quality, a gap small enough that the privacy and offline benefits dominate for a personal vault. [claim:clm_inf03]
- Stable sqlite-vec (v0.1.9 and earlier) is brute-force KNN only, so its query latency scales linearly with vault size and it is best suited to the 1K-10K artifact tier; the v0.1.10-alpha DiskANN/IVF work is the path to the 100K tier but is pre-stable as of mid-2026. [claim:clm_inf05]
- The practical migration threshold from brute-force sqlite-vec to an ANN-indexed backend sits well below sqlite-vec's own >1M-vector slowdown marker, in the low tens of thousands of chunks, once linear-scan query latency becomes interactively noticeable for a single user. [claim:clm_inf06]
- Both candidate local models and the OpenAI API support Matryoshka-style dimension reduction, so a vault can cut index size by truncating to 256 dimensions while sacrificing only about 1.2 MTEB points (nomic 62.28 to 61.04), making 256-512d the recommended storage sweet spot at the 100K ceiling. [claim:clm_inf09]
- A hybrid dense+sparse retrieval setup is justified even on a small personal vault when using BGE-M3, because the single model already emits both dense and sparse (lexical) representations, so hybrid adds keyword-recall robustness with little extra model or infrastructure cost. [claim:clm_inf11]
- Operational complexity favors sqlite-vec decisively for a homelab: restore-from-files is a single SQLite file copy with zero running services, whereas pgvector requires provisioning, securing, backing up, and version-managing a Postgres 13+ server, a recurring cost only the 100K tier justifies. [claim:clm_inf14]
- Because the vault is re-buildable from Markdown, incremental re-embedding cost under frequent Git edits is bounded by changed-file count rather than vault size, and both sqlite-vec (vec0 row upserts) and pgvector (row UPDATE/INSERT) support cheap per-note upserts that avoid full re-indexing. [claim:clm_inf15]

## Links

- [[claim:clm_018]]
- [[claim:clm_021]]
- [[claim:clm_068]]
- [[claim:clm_008]]
- [[claim:clm_067]]
- [[claim:clm_072]]
- [[claim:clm_039]]
- [[claim:clm_040]]
- [[claim:clm_048]]
- [[claim:clm_044]]
- [[claim:clm_042]]
- [[claim:clm_043]]
- [[claim:clm_013]]
- [[claim:clm_064]]
- [[claim:clm_047]]
- [[claim:clm_063]]
- [[claim:clm_023]]
- [[claim:clm_022]]
- [[claim:clm_052]]
- [[claim:clm_051]]
- [[claim:clm_030]]
- [[claim:clm_050]]
- [[claim:clm_037]]
- [[claim:clm_041]]
- [[claim:clm_036]]
- [[claim:clm_045]]
- [[claim:clm_033]]
- [[claim:clm_034]]
- [[claim:clm_054]]
- [[claim:clm_019]]
- [[claim:clm_056]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
