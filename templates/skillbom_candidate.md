---
id: {{id}}
name: {{name}}
proposed_skillbom_id: {{proposed_skillbom_id}}
evidence_bundle_id: {{evidence_bundle_id}}
status: {{status}}
purpose: {{purpose}}
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
  ccdash_event_id: {{ccdash_event_id}}
  quality_score: pending
  rework_count: {{rework_count}}
  estimated_cost_usd: {{estimated_cost_usd}}
---
# SkillBOM Candidate: {{name}}

## Purpose

{{purpose}}

## Agent postures

- researcher
- critic
- synthesizer

## Tools

- gpt_researcher
- paperqa2
- claude_agent_sdk
- litellm

## Prompts

- System: skillmeat/prompts/research_swarm_system.md
- Task: skillmeat/prompts/research_swarm_task.md

## Output schemas

- source_card.schema.yaml
- claim_ledger.schema.yaml
- evidence_bundle.schema.yaml

## Validation

- claim_verifier_passed
- governance_guard_passed
- report_reviewed

## Known failure modes

- source_overcollection
- unsupported_synthesis
- citation_mismatch
- stale_sources
- work_personal_boundary_leak

## Performance evidence

- CCDash event id: {{ccdash_event_id}}
- Quality score: pending
- Rework count: {{rework_count}}
- Estimated cost (USD): {{estimated_cost_usd}}
