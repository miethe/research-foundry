---
id: skillcand_research_swarm_20260615_semantic_entity_consolidation_and_auto_merge
name: Research Swarm — Semantic entity consolidation and auto-merge thresholds in a file-first vault
proposed_skillbom_id: skill_research_swarm_v0
evidence_bundle_id: bundle_20260615_intent_research_20260614_semantic_entity_consoli
status: candidate
purpose: 'Reusable research swarm: cheap extraction + deep synthesis with claim traceability and governance
  gating.'
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
performance_evidence:
  ccdash_event_id: exec_20260615_intent_research_20260614_semantic_entity_consoli
  quality_score: pending
  rework_count: 0
  estimated_cost_usd: 0.0
---

# SkillBOM Candidate: Research Swarm — Semantic entity consolidation and auto-merge thresholds in a file-first vault

## Purpose

Reusable research swarm: cheap extraction + deep synthesis with claim traceability and governance gating.

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

- CCDash event id: exec_20260615_intent_research_20260614_semantic_entity_consoli
