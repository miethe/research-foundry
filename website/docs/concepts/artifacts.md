---
title: Run Artifacts & Directory Anatomy
description: Reference for every file type in a Research Foundry run directory
audience: developers, advanced users
tags: reference, architecture, file-structure
created: 2026-06-19
updated: 2026-06-19
category: concepts
status: published
related_documents: [reference/run-artifacts.md, concepts/pipeline.md]
---

# Run Artifacts & Directory Anatomy

A Research Foundry run directory is an immutable, self-contained evidence snapshot. This page walks the complete structure, showing every file type, its purpose, and what consumes it.

## Run Directory Tree

```
runs/rf_run_20260614_what_architectures_define_an_agentic_origination/
├── run.yaml                          # Run metadata & config
├── research_brief.md                 # Human-readable research brief
├── swarm_plan.yaml                   # Agent routing & execution plan
├── routing_decision.yaml             # Which models/tools run where
├── evidence_bundle.yaml              # FINAL: durable snapshot
│
├── sources/                          # Ingested & normalized source cards
│   ├── src_20260614_rib026_00.md     # Source card (Markdown with YAML frontmatter)
│   ├── src_20260614_rib026_01.md
│   ├── src_20260614_rib026_02.md
│   └── ... (12 sources in this run)
│
├── extractions/                      # Evidence extracted from sources
│   ├── ext_20260614_0eba0c9c_001.yaml
│   ├── ext_20260614_1bd9824e_001.yaml
│   └── ... (12 extraction cards)
│
├── claims/                           # Claim ledger & contradiction tracking
│   ├── claim_ledger.yaml             # Authoritative registry of all claims
│   ├── contradiction_log.yaml        # Disagreements between sources
│   └── inference_log.yaml            # Tracked inferences
│
├── reports/                          # Synthesized research reports
│   ├── report_draft.md               # Initial synthesis
│   └── report_final.md               # Post-review final version
│
├── reviews/                          # Review & verification artifacts
│   └── verification.yaml             # Claim verification results
│
├── writebacks/                       # Rendered outputs for downstream systems
│   ├── meatywiki_writeback.md        # MeatyWiki article + metadata
│   ├── skillbom_candidate.md         # SkillBOM candidate entry
│   └── ccdash_event.yaml             # CCDash event payload
│
└── telemetry/                        # Execution traces & metrics
    └── run_trace.jsonl               # Per-stage timing, costs, token usage
```

## File Reference

### Core Metadata

#### `run.yaml`
**Format:** YAML  
**Contains:** Run ID, status, created/updated timestamps, linked intent ID, sensitivity tier, assigned models/profiles, governance profile  
**Consumed by:** `rf` CLI for all operations; registries for indexing  
**Immutable:** Yes (append only for status updates)

**Example:**
```yaml
run_id: rf_run_20260614_what_architectures_define_an_agentic_origination
status: bundled
sensitivity: personal
key_profile: personal
created_at: "2026-06-14T10:12:34Z"
completed_at: "2026-06-14T14:55:22Z"
intent_id: intent_research_20260614_agentic_architectures
model_profiles:
  extraction: rf_extract_cheap
  synthesis: rf_synthesize_deep
  verification: rf_verify_balanced
```

#### `research_brief.md`
**Format:** Markdown  
**Contains:** Research objective, key questions, scope constraints, success criteria, depth level, audience, cost/token budgets  
**Produced by:** `rf plan`  
**Consumed by:** Swarm agents; human operators for context  

#### `swarm_plan.yaml`
**Format:** YAML  
**Contains:** Agent assignments, tool routing, parallelization strategy, fallback handlers  
**Produced by:** `rf plan`  
**Consumed by:** Orchestration layer; archived for reproducibility  

#### `routing_decision.yaml`
**Format:** YAML  
**Contains:** Model selection rationale, sensitivity-tier routing rules, which tools are enabled  
**Produced by:** Governance engine during plan  
**Consumed by:** Verification, audit trails  

### Sources

#### `sources/src_*.md`
**Format:** Markdown with YAML frontmatter  
**Naming:** `src_YYYYMMDD_<hash>_NN.md`  
**Contains:** 
- Frontmatter: source_id, title, URL/path, source_type (paper, article, official_doc, etc.), ingested_at, sensitivity
- Body: normalized text, extracted quotes, metadata

**Produced by:** `rf ingest`  
**Consumed by:** `rf extract`; linked in claim ledger  

**Example:**
```markdown
---
source_id: src_20260614_rib026_00
title: "Research Foundry MVP Specification"
source_type: specification
url: "file:///docs/research-foundry-mvp-spec.md"
ingested_at: "2026-06-14T10:30:15Z"
sensitivity: public
---

# Research Foundry MVP Specification

The MVP runs fully offline and deterministic by default. Governance guard, schema 
validation, claim verification, and the full demo loop require no network and no LLM...
```

### Extractions

#### `extractions/ext_*.yaml`
**Format:** YAML  
**Naming:** `ext_YYYYMMDD_<hash>_NNN.yaml`  
**Contains:** 
- Extraction metadata: extraction_id, source_id, model_profile, extracted_at
- Key claims (statements extracted by cheap model)
- Supporting facts, evidence snippets
- Confidence scores

**Produced by:** `rf extract` (cheap model profile)  
**Consumed by:** `rf claim-map`; linked in claim ledger  

**Example:**
```yaml
extraction_id: ext_20260614_0eba0c9c_001
source_id: src_20260614_rib026_00
model_profile: rf_extract_cheap
extracted_at: "2026-06-14T11:05:22Z"
claims:
  - statement: "The system runs fully offline by default"
    confidence: high
    evidence: "MVP runs this loop fully offline and deterministically by default"
    tags: [core-principle, determinism]
    
  - statement: "Governance is enforced at runtime before execution"
    confidence: high
    evidence: "Governance is a runtime gate, not a memo"
    tags: [governance, architecture]
```

### Claims & Ledger

#### `claims/claim_ledger.yaml`
**Format:** YAML  
**Contains:** Master registry of all claims, each with:
- Claim ID (clm_NNN)
- Statement text
- Status (supported, inference, speculation, contradicted, mixed, unresolved)
- Source IDs (which sources support this claim)
- Confidence (high/medium/low)
- Tags, creation timestamp, extracted_from extraction_id

**Produced by:** `rf claim-map`  
**Consumed by:** `rf synthesize` (reference only); `rf verify` (verification); reports (inline citation)  
**Immutable:** Per-claim; appends only  

**Example:**
```yaml
claims:
  clm_001:
    id: clm_001
    statement: "Research Foundry uses Markdown/YAML as source of truth"
    status: supported
    source_ids: [src_20260614_rib026_00]
    confidence: high
    tags: [architecture, principle]
    created_at: "2026-06-14T11:15:33Z"

  clm_042:
    id: clm_042
    statement: "Cost will become a bottleneck above 50,000 claims"
    status: inference
    supporting_claim_ids: [clm_087, clm_091]
    reasoning: "Cost doubles per 10K claims + linear scaling → inference"
    confidence: medium
    tags: [cost, scalability, limitation]
```

#### `claims/contradiction_log.yaml`
**Format:** YAML  
**Contains:** Conflicts detected during extraction or synthesis
- Conflicting claim IDs
- Supporting sources for each side
- Resolution status (unresolved, reconciled, or accepted-mixed)

**Produced by:** `rf extract` or human review  
**Consumed by:** `rf verify`, reports (as "mixed evidence" label)  

#### `claims/inference_log.yaml`
**Format:** YAML  
**Contains:** Explicitly tracked inferences
- Inference statement
- Supporting claim IDs
- Reasoning
- Confidence, timestamp

**Produced by:** Synthesis phase when model generates unsourced claims  
**Consumed by:** `rf verify`, audit trails  

### Reports

#### `reports/report_draft.md`
**Format:** Markdown  
**Contains:** Initial research report; inline claim-status tags (e.g., `[claim:clm_001]`, `(inference)`, `(speculation)`)  
**Produced by:** `rf synthesize`  
**Consumed by:** `rf verify`, human review, `rf bundle`  

#### `reports/report_final.md`
**Format:** Markdown  
**Contains:** Post-review final version; approved for publication  
**Produced by:** Human review + approval workflow  
**Consumed by:** `rf bundle`, writebacks  

### Reviews & Verification

#### `reviews/verification.yaml`
**Format:** YAML  
**Contains:**
- Verification timestamp and results
- Per-claim verification: status, supporting sources, label (if inference/speculation)
- Overall pass/fail, exit code
- Any policy violations or warnings

**Produced by:** `rf verify`  
**Consumed by:** Bundle, CCDash telemetry, human review  

**Example:**
```yaml
verification_id: ver_20260614_001
run_id: rf_run_20260614_what_architectures_define_an_agentic_origination
verified_at: "2026-06-14T13:22:10Z"
report_file: reports/report_draft.md
status: pass
exit_code: 0
verified_claims: 42
unsupported_claims: 0
inferences_labeled: 5
speculations_labeled: 2
contradictions_labeled: 0
notes: "All material claims traced to sources or properly labeled."
```

### Evidence Bundle

#### `evidence_bundle.yaml`
**Format:** YAML  
**Contains:** Immutable snapshot of sources, extractions, claim ledger, verified report, reviews, and metadata  
**Produced by:** `rf bundle` (snapshot of entire run)  
**Consumed by:** Writebacks, archival, downstream systems (never re-run)  
**Immutable:** Yes; this is the durable artifact  

**Structure:**
```yaml
bundle_id: bundle_20260614_001
run_id: rf_run_20260614_what_architectures_define_an_agentic_origination
created_at: "2026-06-14T14:00:00Z"
verified: true
verification_id: ver_20260614_001

manifest:
  sources: 12
  extractions: 12
  claims: 87
  reports: 1

lineage:
  intent_id: intent_research_20260614_agentic_architectures
  sensitivity: personal
  key_profile: personal

sources: [<full embedded source cards>]
claim_ledger: [<full embedded claims>]
report: [<full verified report>]
reviews: [<verification.yaml>]
telemetry: [<run_trace.jsonl lines>]
```

### Writebacks

#### `writebacks/meatywiki_writeback.md`
**Format:** Markdown  
**Contains:** Article ready to publish to MeatyWiki; includes frontmatter with target node, tags, source links  
**Produced by:** `rf writeback --targets meatywiki`  
**Consumed by:** MeatyWiki intake API or file push  

#### `writebacks/skillbom_candidate.md`
**Format:** Markdown  
**Contains:** SkillBOM entry candidate; structured as skill, prerequisites, outcome, examples  
**Produced by:** `rf writeback --targets skillmeat`  
**Consumed by:** SkillMeat catalog; human review  

#### `writebacks/ccdash_event.yaml`
**Format:** YAML  
**Contains:** CCDash event payload; metrics like token cost, verification status, runtime  
**Produced by:** `rf writeback --targets ccdash`  
**Consumed by:** CCDash telemetry ingestion  

### Telemetry

#### `telemetry/run_trace.jsonl`
**Format:** JSON Lines (one JSON object per line)  
**Contains:** Per-stage execution trace: stage name, timestamp, duration, token counts, tool calls, model profile, cost estimate  
**Produced by:** Every stage (best-effort)  
**Consumed by:** `rf summarize`, observability, cost tracking  

**Example lines:**
```jsonl
{"stage":"capture","ts":"2026-06-14T10:12:34Z","duration_ms":120,"tokens_used":0,"profile":"personal","status":"ok"}
{"stage":"triage","ts":"2026-06-14T10:15:10Z","duration_ms":450,"tokens_used":0,"profile":"personal","status":"ok"}
{"stage":"plan","ts":"2026-06-14T10:18:00Z","duration_ms":1800,"tokens_used":2500,"profile":"personal","model":"gpt-3.5","cost_usd":0.001,"status":"ok"}
{"stage":"extract","ts":"2026-06-14T11:05:22Z","duration_ms":3200,"tokens_used":12000,"profile":"personal","model":"gpt-3.5","cost_usd":0.005,"status":"ok"}
```

## Run Naming Convention

All run directories follow: `rf_run_YYYYMMDD_<slug>`

- **YYYYMMDD:** Date created (ISO format)
- **slug:** URL-safe, first ~50 chars of research intent title

Example: `rf_run_20260614_what_architectures_define_an_agentic_origination`

## Immutability & Reproducibility

- **`sources/`** and **`extractions/`** are append-only (new sources/extractions added, never replaced)
- **`claims/`** ledger is append-only per claim (new claims added, existing IDs never change)
- **`reports/`** can have multiple versions (draft → final), but verified reports are frozen
- **`evidence_bundle.yaml`** is immutable snapshot; re-bundling produces a new bundle with new ID
- **`run.yaml`** status is append-only (created → sources_ingested → extracted → verified → bundled)

This ensures reproducibility: given an evidence bundle and run ID, you can always reconstruct or audit the research.

## See Also

- [Reference: Run Artifacts](../reference/run-artifacts.md) — detailed per-file reference
- [Concepts: Pipeline](pipeline.md) — where each artifact type is created
- [Concepts: Governance](governance.md) — sensitivity tiers and governance in artifacts
