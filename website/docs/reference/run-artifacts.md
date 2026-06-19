---
title: Run Artifact Reference
description: Detailed per-file reference for Research Foundry run directories
audience: developers, advanced users
tags: reference, file-structure, schemas
created: 2026-06-19
updated: 2026-06-19
category: reference
status: published
related_documents: [concepts/artifacts.md, concepts/pipeline.md]
---

# Run Artifact Reference

Detailed file-by-file reference for every artifact type in a Research Foundry run directory. Use this alongside [Concepts: Artifacts](../concepts/artifacts.md) for deeper understanding.

## Quick Reference Table

| Artifact | Path Pattern | Format | Immutable | Key Consumer |
|----------|--------------|--------|-----------|--------------|
| Run metadata | `run.yaml` | YAML | Append-only | All stages |
| Research brief | `research_brief.md` | Markdown | Yes | Humans, agents |
| Swarm plan | `swarm_plan.yaml` | YAML | Yes | Orchestration |
| Routing decision | `routing_decision.yaml` | YAML | Yes | Governance |
| Source card | `sources/src_*.md` | Markdown + YAML | Yes | `rf extract` |
| Extraction card | `extractions/ext_*.yaml` | YAML | Yes | `rf claim-map` |
| Claim ledger | `claims/claim_ledger.yaml` | YAML | Append-only | `rf synthesize`, `rf verify` |
| Contradiction log | `claims/contradiction_log.yaml` | YAML | Append-only | `rf verify`, reports |
| Inference log | `claims/inference_log.yaml` | YAML | Append-only | `rf verify`, audit |
| Report (draft) | `reports/report_draft.md` | Markdown | No | `rf verify`, human review |
| Report (final) | `reports/report_final.md` | Markdown | Yes | Bundle, writebacks |
| Verification | `reviews/verification.yaml` | YAML | Yes | Bundle, CCDash |
| Evidence bundle | `evidence_bundle.yaml` | YAML | Yes | Writebacks, archival |
| MeatyWiki writeback | `writebacks/meatywiki_writeback.md` | Markdown | Yes | MeatyWiki API |
| SkillBOM writeback | `writebacks/skillbom_candidate.md` | Markdown | Yes | SkillMeat review |
| CCDash event | `writebacks/ccdash_event.yaml` | YAML | Yes | CCDash telemetry |
| Run trace | `telemetry/run_trace.jsonl` | JSON Lines | Append-only | `rf summarize` |

---

## Core Metadata Files

### `run.yaml`

**Path:** Root of run directory  
**Format:** YAML  
**Produced by:** `rf plan`  
**Status:** Append-only (status updates added, never replaced)  

**Fields:**

```yaml
run_id: string                    # Unique run identifier
status: string                    # created, sources_ingested, extracted, verified, bundled
sensitivity: string               # public, personal, work_internal, work_sensitive, client_internal, client_sensitive
key_profile: string               # personal, work_approved, client_approved, offline_only
created_at: ISO8601 timestamp     # When run was created
completed_at: ISO8601 timestamp   # When run transitioned to bundled
updated_at: ISO8601 timestamp     # Last status update
intent_id: string | null          # Linked research intent ID
model_profiles:
  extraction: string              # Model profile for extraction stage (e.g., rf_extract_cheap)
  synthesis: string               # Model profile for synthesis (e.g., rf_synthesize_deep)
  verification: string            # Model profile for verification (e.g., rf_verify_balanced)
research_brief_path: string       # Path to research_brief.md
swarm_plan_path: string           # Path to swarm_plan.yaml
routing_decision_path: string     # Path to routing_decision.yaml
artifact_counts:
  sources: int                    # Total source cards
  extractions: int                # Total extraction cards
  claims: int                     # Total claims in ledger
  inferences: int                 # Total tracked inferences
  contradictions: int             # Total contradictions detected
tags: string[]                    # Arbitrary tags
```

**Example:**

```yaml
run_id: rf_run_20260614_what_architectures_define_an_agentic_origination
status: bundled
sensitivity: personal
key_profile: personal
created_at: "2026-06-14T10:12:34Z"
completed_at: "2026-06-14T14:55:22Z"
updated_at: "2026-06-14T14:55:22Z"
intent_id: intent_research_20260614_agentic_architectures
model_profiles:
  extraction: rf_extract_cheap
  synthesis: rf_synthesize_deep
  verification: rf_verify_balanced
artifact_counts:
  sources: 12
  extractions: 12
  claims: 87
  inferences: 5
  contradictions: 2
tags: []
```

---

### `research_brief.md`

**Path:** Root of run directory  
**Format:** Markdown with YAML frontmatter  
**Produced by:** `rf plan`  
**Status:** Immutable  

**Frontmatter Fields:**

```yaml
run_id: string
intent_id: string
created_at: ISO8601 timestamp
research_objective: string
key_research_questions: string[] # Primary, secondary
success_criteria: string[]        # How we know this is complete
depth: string                     # shallow, medium, deep
audience: string                  # technical, business, executive
scope_constraints: string[]       # What's in/out of scope
cost_budget_usd: float
token_budget: int
freshness_requirement: string     # e.g., "180d", "7d", "none"
```

**Body:** Human-readable narrative brief describing the research objective, approach, timeline.

---

### `swarm_plan.yaml`

**Path:** Root of run directory  
**Format:** YAML  
**Produced by:** `rf plan`  
**Status:** Immutable  

**Fields:**

```yaml
run_id: string
agent_assignments:
  - agent_id: string              # e.g., "extractor_1"
    role: string                  # extraction, synthesis, verification
    model_profile: string
    sources: string[]             # Source IDs assigned to this agent
    parallelization: int          # Batch size
    
tool_routing:
  - tool_name: string             # e.g., "search", "summarization"
    enabled: bool
    fallback_mode: string         # deterministic, skip, error
    
cost_estimate_usd: float
estimated_duration_minutes: int
```

---

### `routing_decision.yaml`

**Path:** Root of run directory  
**Format:** YAML  
**Produced by:** Governance engine (during `rf plan`)  
**Status:** Immutable  

**Fields:**

```yaml
run_id: string
profile: string                   # Key profile used
policy_version: string            # Governance policy version
decisions:
  extraction_model_allowed: bool
  synthesis_model_allowed: bool
  external_search_allowed: bool
  writeback_targets_allowed: string[]  # Which targets permitted
  requires_review: bool           # If work_sensitive or client_sensitive
  
rationale: string                 # Why these decisions were made
timestamp: ISO8601
```

---

## Source Cards

### `sources/src_YYYYMMDD_<hash>_NN.md`

**Path:** `sources/` directory  
**Format:** Markdown with YAML frontmatter  
**Produced by:** `rf ingest`  
**Status:** Immutable  
**Consumed by:** `rf extract`  

**Frontmatter Fields:**

```yaml
source_id: string                 # Unique ID (e.g., src_20260614_rib026_00)
title: string                     # Human-readable title
source_type: string               # paper, article, official_doc, notebook, report, blog, video_transcript, conversation
url: string | null                # URL if from web, file:// if local
ingested_at: ISO8601 timestamp
sensitivity: string               # public, personal, work_internal, etc.
tags: string[]
author: string | null
published_date: date | null
confidence: string                # high, medium, low (confidence in source quality)
```

**Body:** Normalized source text, extracted quotes, key metadata. May include section headers, bullet points, formatted for readability.

**Example:**

```markdown
---
source_id: src_20260614_rib026_00
title: "Research Foundry MVP Specification"
source_type: specification
url: "file:///docs/research-foundry-mvp-spec.md"
ingested_at: "2026-06-14T10:30:15Z"
sensitivity: public
tags: [specification, architecture]
confidence: high
---

# Research Foundry MVP Specification

The system is Markdown/YAML-first and runs fully offline by default...
```

---

## Extraction Cards

### `extractions/ext_YYYYMMDD_<hash>_NNN.yaml`

**Path:** `extractions/` directory  
**Format:** YAML  
**Produced by:** `rf extract` (cheap model)  
**Status:** Immutable  
**Consumed by:** `rf claim-map`  

**Fields:**

```yaml
extraction_id: string             # Unique ID
source_id: string                 # Which source this came from
model_profile: string             # Which model ran extraction
extracted_at: ISO8601 timestamp
claims:
  - statement: string             # Extracted claim
    confidence: string            # high, medium, low
    evidence: string              # Supporting quote from source
    tags: string[]                # Claim tags
    
supporting_facts:
  - fact: string
    evidence: string
    
contradictions:
  - contradiction_statement: string
    evidence: string
    
summary: string                   # Human-readable summary of extraction
```

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
    tags: [architecture, determinism, core-principle]
```

---

## Claim Ledger & Logs

### `claims/claim_ledger.yaml`

**Path:** `claims/` directory  
**Format:** YAML  
**Produced by:** `rf claim-map`  
**Status:** Append-only  
**Consumed by:** `rf synthesize`, `rf verify`, reports  

**Fields:**

```yaml
claims:
  clm_NNN:                        # Claim ID (clm_001, clm_002, etc.)
    id: string
    statement: string             # The claim itself
    status: string                # supported, inference, speculation, contradicted, mixed, unresolved
    source_ids: string[]          # If supported: which sources
    supporting_claim_ids: string[] # If inference: which claims support this
    confidence: string            # high, medium, low
    reasoning: string | null      # For inferences: why this conclusion
    tags: string[]
    created_at: ISO8601 timestamp
    extracted_from: string        # extraction_id that produced it
    related_claims: string[]      # Cross-references
```

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
    extracted_from: ext_20260614_0eba0c9c_001

  clm_042:
    id: clm_042
    statement: "Cost will scale linearly with claim count"
    status: inference
    supporting_claim_ids: [clm_087, clm_091]
    reasoning: "Multiple sources document per-claim cost; linear scaling observed"
    confidence: medium
    tags: [cost, scalability]
    created_at: "2026-06-14T12:10:44Z"
```

---

### `claims/contradiction_log.yaml`

**Path:** `claims/` directory  
**Format:** YAML  
**Produced by:** During extract or manual review  
**Status:** Append-only  
**Consumed by:** `rf verify`, reports  

**Fields:**

```yaml
contradictions:
  - contradiction_id: string      # contra_001, etc.
    created_at: ISO8601 timestamp
    conflicting_claim_ids: string[]  # Which claims contradict each other
    conflicting_sources: string[]   # Which sources disagree
    nature: string                # direct (A contradicts B), partial, context-dependent
    resolution: string            # How we've decided to handle it
    resolution_status: string     # unresolved, reconciled, accepted-mixed
```

**Example:**

```yaml
contradictions:
  - contradiction_id: contra_001
    created_at: "2026-06-14T11:22:00Z"
    conflicting_claim_ids: [clm_010, clm_011]
    conflicting_sources: [src_20260614_rib026_02, src_20260614_rib026_03]
    nature: "direct"
    resolution: "Source A documents an older design; source B is current spec. Accepted as historical vs. current."
    resolution_status: "reconciled"
```

---

### `claims/inference_log.yaml`

**Path:** `claims/` directory  
**Format:** YAML  
**Produced by:** During synthesis or manual review  
**Status:** Append-only  
**Consumed by:** `rf verify`, audit trails  

**Fields:**

```yaml
inferences:
  - inference_id: string
    created_at: ISO8601 timestamp
    statement: string             # The inference
    supporting_claim_ids: string[]  # Claims that led to this inference
    reasoning: string
    confidence: string            # high, medium, low
    tags: string[]
```

---

## Reports

### `reports/report_draft.md`

**Path:** `reports/` directory  
**Format:** Markdown with inline claim tags  
**Produced by:** `rf synthesize`  
**Status:** Mutable (human review, updates before finalization)  
**Consumed by:** `rf verify`, human review  

**Inline claim tags:**

```markdown
Supported claims (explicit reference optional):
  Research Foundry uses Markdown/YAML [claim:clm_001].

Inference (must label):
  **Inference:** Cost will scale linearly [claim:clm_042, inference].
  
Speculation (must label):
  **Speculation:** By 2027, all teams will use evidence-backed research.

Mixed evidence (must label):
  **Mixed evidence:** Adoption timelines vary [claim:clm_087, clm_091, mixed].

Unresolved (must label):
  **Unresolved / Pending Research:** The exact cost trajectory remains unknown.
```

---

### `reports/report_final.md`

**Path:** `reports/` directory  
**Format:** Markdown (post-review final)  
**Produced by:** Human approval of report_draft  
**Status:** Immutable  
**Consumed by:** Bundle, writebacks  

Same structure as report_draft, but frozen after verification passes and human review approves.

---

## Reviews & Verification

### `reviews/verification.yaml`

**Path:** `reviews/` directory  
**Format:** YAML  
**Produced by:** `rf verify`  
**Status:** Immutable  
**Consumed by:** Bundle, CCDash, audit  

**Fields:**

```yaml
verification_id: string           # ver_YYYYMMDD_NNN
run_id: string
verified_at: ISO8601 timestamp
report_file: string               # Path to report verified
status: string                    # pass, fail, warning
exit_code: int                    # 0 (pass), 4 (unsupported), etc.

results:
  total_material_claims: int
  supported_claims: int
  inference_claims: int
  speculation_claims: int
  contradicted_claims: int
  mixed_claims: int
  unresolved_claims: int
  unsupported_claims: int        # Count causing failures
  
summary: string
notes: string
policy_checks:
  - check_name: string
    status: bool
    message: string
```

**Example:**

```yaml
verification_id: ver_20260614_001
run_id: rf_run_20260614_what_architectures_define_an_agentic_origination
verified_at: "2026-06-14T13:22:10Z"
report_file: reports/report_draft.md
status: pass
exit_code: 0
results:
  total_material_claims: 42
  supported_claims: 35
  inference_claims: 5
  speculation_claims: 2
  unsupported_claims: 0
summary: "All material claims verified or properly labeled."
```

---

## Evidence Bundle

### `evidence_bundle.yaml`

**Path:** Root of run directory  
**Format:** YAML (large; embedded artifacts)  
**Produced by:** `rf bundle`  
**Status:** Immutable  
**Consumed by:** Writebacks, archival, reproducibility  

**Structure:**

```yaml
bundle_id: string                 # bundle_YYYYMMDD_NNN
run_id: string
created_at: ISO8601 timestamp
verified: bool                    # Whether verification passed before bundling
verification_id: string | null

manifest:
  sources: int
  extractions: int
  claims: int
  inferences: int
  contradictions: int
  reports: int
  writebacks_rendered: bool

lineage:
  intent_id: string
  sensitivity: string
  key_profile: string
  created_at: ISO8601 timestamp

# Full embedded artifacts below (immutable snapshot):
sources:
  - [full source card YAML]
  
extractions:
  - [full extraction card YAML]
  
claims:
  [full claim_ledger.yaml content]
  
contradictions:
  [full contradiction_log.yaml content]
  
report: string                    # Full report Markdown

reviews:
  - [full verification.yaml]

telemetry:
  - [run_trace.jsonl lines]
```

This is a complete, self-contained archive. To reproduce or audit a run later, load the evidence bundle.

---

## Writebacks

### `writebacks/meatywiki_writeback.md`

**Path:** `writebacks/` directory  
**Format:** Markdown with YAML frontmatter  
**Produced by:** `rf writeback --targets meatywiki`  
**Status:** Immutable  

**Frontmatter:**

```yaml
target: meatywiki
run_id: string
created_at: ISO8601 timestamp
title: string
meatywiki_node_id: string | null  # IntentTree node ID if linked
tags: string[]
source_claims: string[]           # Claim IDs referenced
```

**Body:** Article ready to push to MeatyWiki, formatted as Markdown.

---

### `writebacks/skillbom_candidate.md`

**Path:** `writebacks/` directory  
**Format:** Markdown with YAML frontmatter  
**Produced by:** `rf writeback --targets skillmeat`  
**Status:** Immutable  

**Frontmatter:**

```yaml
target: skillmeat
run_id: string
created_at: ISO8601 timestamp
skill_name: string
prerequisites: string[]
learning_outcomes: string[]
confidence: string              # high, medium, low (confidence this is viable skill)
```

**Body:** Skill entry structured for SkillMeat catalog.

---

### `writebacks/ccdash_event.yaml`

**Path:** `writebacks/` directory  
**Format:** YAML  
**Produced by:** `rf writeback --targets ccdash`  
**Status:** Immutable  

**Fields:**

```yaml
event_id: string
run_id: string
timestamp: ISO8601 timestamp
event_type: string               # research_completed, verification_passed, etc.
payload:
  run_status: string
  claims_count: int
  verification_passed: bool
  token_cost: float
  duration_minutes: float
  key_findings: string[]
```

---

## Telemetry

### `telemetry/run_trace.jsonl`

**Path:** `telemetry/` directory  
**Format:** JSON Lines (one JSON object per line)  
**Produced by:** Every stage (best-effort, never fail stage on telemetry error)  
**Status:** Append-only  
**Consumed by:** `rf summarize`, observability systems  

**Line structure:**

```json
{
  "stage": "capture|triage|plan|ingest|extract|claim_map|synthesize|verify|bundle|writeback|summarize",
  "ts": "ISO8601 timestamp",
  "duration_ms": 150,
  "tokens_used": 0,
  "tokens_limit": 100000,
  "cost_usd": 0.0,
  "profile": "personal|work_approved|client_approved|offline_only",
  "model": "model_name|null",
  "status": "ok|warning|error",
  "error_message": "null|string if error"
}
```

**Example lines:**

```jsonl
{"stage":"capture","ts":"2026-06-14T10:12:34Z","duration_ms":120,"tokens_used":0,"profile":"personal","status":"ok"}
{"stage":"extract","ts":"2026-06-14T11:05:22Z","duration_ms":3200,"tokens_used":12000,"cost_usd":0.005,"profile":"personal","model":"claude-3-5-sonnet","status":"ok"}
{"stage":"verify","ts":"2026-06-14T13:22:10Z","duration_ms":450,"tokens_used":0,"profile":"personal","status":"ok"}
```

---

## See Also

- [Concepts: Artifacts](../concepts/artifacts.md) — high-level anatomy and purpose
- [Reference: CLI](cli.md) — commands that produce these artifacts
- [Concepts: Pipeline](../concepts/pipeline.md) — which artifacts each stage creates
