---
schema_version: 0.1
type: research_brief
id: brief_20260614_hybrid_bm25_vector_and_fts5_ranking
intent_id: intent_research_20260614_hybrid_bm25_vector_and_fts5_ranking
title: Hybrid BM25+vector and FTS5 ranking for Markdown KBs
audience: technical
research_depth: deep
questions:
  primary:
  - id: rq_001
    question: What does the evidence say about Hybrid BM25+vector and FTS5 ranking for Markdown KBs?
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

# Research Brief: Hybrid BM25+vector and FTS5 ranking for Markdown KBs

**Objective.** At what corpus size does BM25/FTS5 alone become insufficient for a Markdown artifact KB, which hybrid architectures (BM25+vector, BM25+frontmatter, semantic chunking, BM25+reranking) deliver the best recall/precision at each scale tier from 1K to 50K documents, and what FTS5 indexing practices (heading-boost, frontmatter indexing, BM25 ranking customization) are best?

**Depth.** deep  |  **Audience.** technical

## Questions

- (rq_001) What does the evidence say about Hybrid BM25+vector and FTS5 ranking for Markdown KBs?
