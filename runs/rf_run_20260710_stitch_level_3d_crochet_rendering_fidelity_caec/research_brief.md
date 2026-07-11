---
schema_version: 0.1
type: research_brief
id: brief_20260710_stitch_level_3d_crochet_rendering_fidelity
intent_id: intent_research_20260710_stitch_level_3d_crochet_rendering_fidelity_6718
title: Stitch-level 3D crochet rendering fidelity for the KnitWit/LoopNest
audience: technical
research_depth: deep
questions:
  primary:
  - id: rq_001
    question: What does the evidence say about Stitch-level 3D crochet rendering fidelity for the KnitWit/LoopNest?
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

# Research Brief: Stitch-level 3D crochet rendering fidelity for the KnitWit/LoopNest

**Objective.** Stitch-level 3D crochet rendering fidelity for the KnitWit/LoopNest iOS app: our forward engine converts NativePattern (amigurumi crochet patterns) into a stitch graph, embeds it in 3D, and renders via Metal — but generated shapes only loosely resemble the expected objects. Research: (1) state of the art for pattern->3D shape reconstruction of crochet/knit (stitch meshes, yarn-level geometry, mass-spring/physics relaxation, curvature-driven embedding, CrochetPARADE, knitting/crochet compilers, academic + hobbyist tools); (2) practical algorithms to make increases/decreases produce correct global shape (spheres, cones, tubes, appendages) from round-by-round stitch counts; (3) rendering stitch guides: per-stitch visual guides, V-stitch geometry, step-by-step progressive 3D construction (show model at round N) with highlighting of the current stitch/round; (4) feasibility on-device (Metal, iPhone) vs precomputed/server-side; cite concrete papers, repos, and implementable techniques.

**Depth.** deep  |  **Audience.** technical

## Questions

- (rq_001) What does the evidence say about Stitch-level 3D crochet rendering fidelity for the KnitWit/LoopNest?
