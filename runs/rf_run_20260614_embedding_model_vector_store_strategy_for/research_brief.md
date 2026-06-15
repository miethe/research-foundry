---
schema_version: 0.1
type: research_brief
id: brief_20260614_embedding_model_vector_store_strategy_for
intent_id: intent_research_20260614_embedding_model_vector_store_strategy_for
title: Embedding model + vector-store strategy for a 1K-100K file-first vault
audience: technical
research_depth: deep
questions:
  primary:
  - id: rq_001
    question: What does the evidence say about Embedding model + vector-store strategy for a 1K-100K file-first
      vault?
  secondary: []
source_strategy:
  include_source_types:
  - official_docs
  - peer_reviewed_papers
  - standards
  - reputable_news
  - vendor_docs
  - repo_readmes
  - personal_notes
  exclude_source_types:
  - unsourced_social_posts
  - SEO_content_farms
  freshness:
    required: true
    max_age_days: 180
    exceptions:
    - foundational_theory
    - historical_background
output_requirements:
  format: markdown
  include_claim_ledger: true
  include_source_cards: true
  include_inference_log: true
  include_open_questions: true
---

# Research Brief: Embedding model + vector-store strategy for a 1K-100K file-first vault

**Objective.** Which combination of embedding model (local bge-m3/MiniLM/nomic vs API text-embedding-3-small) and vector backend (sqlite-vec, pgvector IVFFlat/HNSW, FAISS, Chroma, LanceDB, Qdrant) achieves the best precision/recall, cost, and query latency for a single-user file-first Markdown vault in the 1K-100K artifact range, considering privacy and Git/Obsidian compatibility?

**Depth.** deep  |  **Audience.** technical

## Questions

- (rq_001) What does the evidence say about Embedding model + vector-store strategy for a 1K-100K file-first vault?
