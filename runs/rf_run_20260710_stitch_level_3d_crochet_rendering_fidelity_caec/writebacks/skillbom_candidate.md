---
id: skillcand_research_swarm_20260711_stitch_level_3d_crochet_rendering_fidelity
name: 'Research Swarm — Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest: Reconstruction
  Techniques, Shaping Algorithms, Progressive Guides, and On-Device vs Server Placement'
proposed_skillbom_id: skill_research_swarm_v0
evidence_bundle_id: bundle_20260711_intent_research_20260710_stitch_level_3d
status: candidate
purpose: Greer-Mould and CrochetPARADE forward-simulate a written pattern to 3D (matching IR-in), while
  AmiGo/Remesher require a closed mesh + seed; therefore the pattern-input engines are the only ones that
  fit the L1 playback pipeline.
agent_postures:
- researcher
- critic
- synthesizer
tools_used:
- gpt_researcher
- paperqa2
- claude_agent_sdk
- litellm
prompts:
  system: skillmeat/prompts/research_swarm_system.md
  task: skillmeat/prompts/research_swarm_task.md
context_packs:
- research_foundry_core
output_schemas:
- source_card.schema.yaml
- claim_ledger.schema.yaml
- evidence_bundle.schema.yaml
validation:
- claim_verifier_passed
- governance_guard_passed
- report_reviewed
known_failure_modes:
- source_overcollection
- unsupported_synthesis
- citation_mismatch
- stale_sources
- work_personal_boundary_leak
- recommended_forward_shaping_pipeline_for
- amigo_s_constrained_optimization_embedding
- model_at_round_n_and
- ghost_next_row_overlay_and
- true_per_stitch_v_stitch
- the_on_device_server_boundary
- forking_crochetparade_s_code_is
- the_crochet_ir_v0_1
- purely_geometric_constraint_embedding_amigo
- ranked_by_visual_fidelity_per
- the_literature_splits_into_a
- a_round_by_round_inc
- the_dominant_shape_fidelity_failure
- crochetparade_is_the_decisive_precedent
- rendering_is_not_the_mobile
- on_the_academic_feasibility_vs
- there_is_a_direct_capability
performance_evidence:
  ccdash_event_id: exec_20260711_intent_research_20260710_stitch_level_3d
  quality_score: pending
  rework_count: 0
  estimated_cost_usd: 0.0
---

# SkillBOM Candidate: Research Swarm — Stitch-Level 3D Crochet Rendering Fidelity for KnitWit/LoopNest: Reconstruction Techniques, Shaping Algorithms, Progressive Guides, and On-Device vs Server Placement

## Purpose

Greer-Mould and CrochetPARADE forward-simulate a written pattern to 3D (matching IR-in), while AmiGo/Remesher require a closed mesh + seed; therefore the pattern-input engines are the only ones that fit the L1 playback pipeline.

## Agent postures

- researcher
- critic
- synthesizer

## Tools

- gpt_researcher
- paperqa2
- claude_agent_sdk
- litellm

## Output schemas

- source_card.schema.yaml
- claim_ledger.schema.yaml
- evidence_bundle.schema.yaml

## Performance evidence

- CCDash event id: exec_20260711_intent_research_20260710_stitch_level_3d
