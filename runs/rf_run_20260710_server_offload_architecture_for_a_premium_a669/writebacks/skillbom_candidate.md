---
id: skillcand_research_swarm_20260711_server_offload_architecture_for_a_knitwit
name: 'Research Swarm — Server Offload Architecture for a KnitWit/LoopNest Premium Tier: Workload Placement,
  Cost Model, Hybrid Architecture, and Privacy/Offline Posture'
proposed_skillbom_id: skill_research_swarm_v0
evidence_bundle_id: bundle_20260711_intent_research_20260710_server_offload_architec
status: candidate
purpose: A 4096-token window (shared by instructions+prompt+output) cannot hold a multi-page PDF pattern
  plus a structured Crochet IR response; exceeding it errors out, so full-document extraction belongs
  on a large-context server model rather than on-device.
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
- interactive_3d_rendering_stitch_counters
- heavy_mesh_generation_and_physics
- knitwit_premium_should_adopt_adobe
- the_architecture_should_split_by
- the_4096_token_extraction_path
- when_a_pattern_is_too
- required_privacy_posture_route_user
- offline_degradation_should_let_cached
- these_placement_findings_most_de
- for_long_context_pdf_url
- per_pattern_extraction_cost_25k
- at_these_token_prices_llm
- caching_by_pattern_hash_cuts
- use_pay_per_use_cloud
- pattern_3d_via_force_directed
performance_evidence:
  ccdash_event_id: exec_20260711_intent_research_20260710_server_offload_architec
  quality_score: pending
  rework_count: 0
  estimated_cost_usd: 0.0
---

# SkillBOM Candidate: Research Swarm — Server Offload Architecture for a KnitWit/LoopNest Premium Tier: Workload Placement, Cost Model, Hybrid Architecture, and Privacy/Offline Posture

## Purpose

A 4096-token window (shared by instructions+prompt+output) cannot hold a multi-page PDF pattern plus a structured Crochet IR response; exceeding it errors out, so full-document extraction belongs on a large-context server model rather than on-device.

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

- CCDash event id: exec_20260711_intent_research_20260710_server_offload_architec
