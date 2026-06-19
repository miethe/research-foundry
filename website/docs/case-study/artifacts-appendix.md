# Artifact Appendix: Verbatim Excerpts from RIB-002

All excerpts below come from real committed files in the RIB-002 run directory:
`runs/rf_run_20260614_what_does_the_empirical_literature_say/`

Each excerpt is truncated for readability. Follow the GitHub links to view full files.

---

## Source card: `src_20260614_rib002_00`

*The SAFE (Long-form factuality in large language models) source card, produced by the source-carder agent from the arXiv abstract.*

```yaml
---
schema_version: '0.1'
type: source_card
source_card_id: src_20260614_rib002_00
created_at: '2026-06-14T12:00:00-04:00'
created_by_agent: rf-swarm-carder
sensitivity: personal
source:
  title: "Long-form factuality in large language models"
  source_type: paper
  locator: {url: "https://arxiv.org/abs/2403.18802", file_path: null}
  authors: [Jerry Wei, Chengrun Yang, Xinying Song, Yifeng Lu, Nathan Hu, ...]
  publisher: "arXiv (NeurIPS 2024)"
  published_at: "2024-03"
trust:
  source_rank: primary
  reliability_notes: "Peer-reviewed NeurIPS 2024 paper by Google DeepMind authors;
    abstract claims verified verbatim from arXiv landing page."
  known_limitations:
  - "Body-text section-level locators not independently confirmed (PDF body not
    fully parsed); locators given at abstract granularity."
  - "SAFE's 72% human-agreement figure is on crowdsourced (not expert) annotators."
extracted_points:
- evidence_id: ev_003
  locator: "Abstract"
  summary: "On ~16,000 individual facts SAFE agrees with crowdsourced human annotators
    72% of the time, and on a random subset of 100 disagreement cases SAFE wins 76%."
  quote: "on a set of ~16k individual facts, SAFE agrees with crowdsourced human
    annotators 72% of the time, and on a random subset of 100 disagreement cases,
    SAFE wins 76% of the time."
- evidence_id: ev_004
  locator: "Abstract"
  summary: "SAFE is more than 20 times cheaper than human annotators."
  quote: "At the same time, SAFE is more than 20 times cheaper than human annotators."
---
```

[View full file on GitHub](https://github.com/miethe/research-foundry/blob/main/runs/rf_run_20260614_what_does_the_empirical_literature_say/sources/src_20260614_rib002_00.md)

---

## Claim ledger entry: `clm_064`

*A material supported claim — `clm_064` — linking the SAFE decompose-then-verify pattern to RF's own claim-ledger design. This is one of 75 supported claims in this run.*

```yaml
- claim_id: clm_064
  text: SAFE (Search-Augmented Factuality Evaluator) uses an LLM to break a long-form
    response into individual atomic facts and verify each via a multi-step reasoning
    process that issues Google Search queries, the same decompose-then-verify pattern
    as a claim ledger.
  materiality: material
  claim_type: factual
  status: supported
  confidence: medium
  sources:
  - source_card_id: src_20260614_rib002_00
    evidence_id: ev_001
    relation: supports
    locator: Abstract
  inference_basis:
    from_claims: []
    reasoning_summary: null
  report_locations: []
  reviewer_notes: ''
```

[View full file on GitHub](https://github.com/miethe/research-foundry/blob/main/runs/rf_run_20260614_what_does_the_empirical_literature_say/claims/claim_ledger.yaml)

---

## Verification checks block: `verification.yaml`

*All 13 checks passed, exit code 0. This is the authoritative green state — not the workflow's `bundle_ok` self-report.*

```yaml
run_id: rf_run_20260614_what_does_the_empirical_literature_say
passed: true
exit_code: 0
generated_at: '2026-06-14T17:20:45-04:00'
checks:
- id: report_has_frontmatter
  severity: error
  status: pass
  detail: report has front matter
- id: all_claim_ids_exist
  severity: error
  status: pass
  detail: all cited claim ids resolve to the ledger
- id: claim_ids_unique
  severity: error
  status: pass
  detail: all ledger claim ids are unique
- id: material_claims_have_claim_ids
  severity: error
  status: pass
  detail: every material sentence carries a claim tag or label
- id: supported_claims_have_source_cards
  severity: error
  status: pass
  detail: all supported claims reference at least one existing source card
- id: source_cards_have_locators
  severity: warning
  status: pass
  detail: cited source cards that resolve have locators
- id: inferences_have_basis
  severity: error
  status: pass
  detail: all inference claims declare an inference basis
- id: inference_is_labeled
  severity: error
  status: pass
  detail: inference claims in the report are labeled (or absent)
- id: mixed_is_labeled
  severity: error
  status: pass
  detail: mixed claims in the report are labeled (or absent)
- id: contradicted_is_labeled
  severity: error
  status: pass
  detail: contradicted claims in the report are labeled (or absent)
- id: speculation_is_labeled
  severity: error
  status: pass
  detail: speculation claims in the report are labeled (or absent)
- id: unsupported_claims_block_publish
  severity: error
  status: pass
  detail: no unsupported claims in the ledger
- id: work_sensitive_claims_block_public_report
  severity: error
  status: pass
  detail: report sensitivity is 'personal'; public-leak check not applicable
unsupported: []
```

[View full file on GitHub](https://github.com/miethe/research-foundry/blob/main/runs/rf_run_20260614_what_does_the_empirical_literature_say/reviews/verification.yaml)

---

## SkillBOM candidate writeback

*The SkillBOM candidate emitted by this run — `skillcand_research_swarm_20260614_…` — records the agent postures, tools, output schemas, and known failure modes for reuse consideration.*

```yaml
---
id: skillcand_research_swarm_20260614_claim_ledger_vs_rag_constitutional_self
name: Research Swarm — Claim-ledger vs RAG/constitutional/self-consistency mitigation
proposed_skillbom_id: skill_research_swarm_v0
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_does_the
status: candidate
purpose: 'Reusable research swarm: cheap extraction + deep synthesis with claim
  traceability and governance gating.'
agent_postures:
- researcher
- critic
- synthesizer
tools_used:
- gpt_researcher
- paperqa2
- claude_agent_sdk
- litellm
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
  ccdash_event_id: exec_20260614_intent_research_20260614_what_does_the
  quality_score: pending
  rework_count: 0
---
```

Status is `candidate` — not promoted. Per the RIB-051 governance model, this must pass `candidate → evaluated → human-reviewed → promoted` before reuse.

[View full file on GitHub](https://github.com/miethe/research-foundry/blob/main/runs/rf_run_20260614_what_does_the_empirical_literature_say/writebacks/skillbom_candidate.md)
