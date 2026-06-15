---
schema_version: 0.1
type: research_brief
id: brief_20260614_semantic_entity_consolidation_and_auto_merge
intent_id: intent_research_20260614_semantic_entity_consolidation_and_auto_merge
title: Semantic entity consolidation and auto-merge thresholds in a file-first vault
audience: technical
research_depth: deep
questions:
  primary:
  - id: rq_001
    question: What does the evidence say about Semantic entity consolidation and auto-merge thresholds
      in a file-first vault?
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

# Research Brief: Semantic entity consolidation and auto-merge thresholds in a file-first vault

**Objective.** What entity-resolution algorithms and merge strategies (Fellegi-Sunter, TF-IDF blocking, LLM-assisted dedup) best consolidate semantically equivalent compiled artifacts while producing valid Obsidian-compatible Markdown, and what empirically grounded confidence thresholds and signal mixes (title sim, body cosine, provenance overlap, graph neighborhood) should govern auto-merge vs review-queue vs ignore?

**Depth.** deep  |  **Audience.** technical

## Questions

- (rq_001) What does the evidence say about Semantic entity consolidation and auto-merge thresholds in a file-first vault?
