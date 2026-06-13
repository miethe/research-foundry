---
id: {{id}}
intent_id: {{intent_id}}
title: {{title}}
audience: {{audience}}
research_depth: {{research_depth}}
questions:
  primary:
    - id: rq_001
      question: {{primary_question_1}}
  secondary:
    - id: rq_002
      question: {{secondary_question_1}}
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
# Research Brief: {{title}}

## Primary questions

- [rq_001] {{primary_question_1}}

## Secondary questions

- [rq_002] {{secondary_question_1}}

## Source strategy

Include source types: official_docs, peer_reviewed_papers, standards, reputable_news, vendor_docs, repo_readmes, personal_notes.
Exclude source types: unsourced_social_posts, SEO_content_farms.
Freshness required: true (max_age_days: 180; exceptions: foundational_theory, historical_background).

## Output requirements

- Format: markdown
- Include claim ledger: true
- Include source cards: true
- Include inference log: true
- Include open questions: true
