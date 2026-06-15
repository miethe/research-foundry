---
schema_version: 0.1
type: research_brief
id: brief_20260614_determinism_ci_cost_control_for_agentic
intent_id: intent_research_20260614_determinism_ci_cost_control_for_agentic
title: Determinism & CI cost-control for agentic eval harnesses
audience: technical
research_depth: deep
questions:
  primary:
  - id: rq_001
    question: What does the evidence say about Determinism & CI cost-control for agentic eval harnesses?
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

# Research Brief: Determinism & CI cost-control for agentic eval harnesses

**Objective.** What determinism strategies (temperature-0+seed, stubbed tool responses, rubric-based LLM-as-judge) and CI cost-control approaches (per-PR vs nightly vs gated runs with cost ceilings) are most effective for evaluating multi-turn agentic workflows where tool-call patterns matter but exact output text does not?

**Depth.** deep  |  **Audience.** technical

## Questions

- (rq_001) What does the evidence say about Determinism & CI cost-control for agentic eval harnesses?
