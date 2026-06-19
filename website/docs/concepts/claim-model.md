---
title: The Claim-Status Model
description: How claims are tagged, audited, and verified
audience: developers, researchers, policy makers
tags: governance, verification, audit
created: 2026-06-19
updated: 2026-06-19
category: concepts
status: published
related_documents: [concepts/pipeline.md, reference/cli.md]
---

# The Claim-Status Model

A **material claim** is any statement a reader could reasonably rely on as fact: factual assertions, quantitative data, comparative statements, causal relationships, attributions, recommendations, or predictions. Every material claim in a report must carry a well-defined status and (when uncertain) a human-readable label.

## Claim Statuses

| Status | Meaning | Report Label Required | Verification Impact | Example |
|--------|---------|----------------------|---------------------|---------|
| `supported` | Directly supported by one or more source cards | No | Pass | "Research Foundry uses Markdown/YAML as source of truth" — traced to README |
| `mixed` | Sources disagree or support only part of the claim | Yes (`Mixed evidence:`) | Pass | "Model A is faster" when sources show it's faster on task X but slower on task Y |
| `contradicted` | Evidence directly contradicts the claim | Yes (`Contradicted / do not use as finding:`) | Pass | "The system requires a database" — contradicted by spec (file-backed only) |
| `inference` | Reasonable synthesis from supported claims; not directly stated by sources | Yes (`Inference:`) | Pass | "High token costs will limit adoption" — inferred from supported claims about cost structure |
| `speculation` | Forward-looking or insufficiently evidenced idea; acknowledged uncertainty | Yes (`Speculation:`) | Pass | "By 2027, most research teams will use evidence-backed systems" — plausible but unverified |
| `unresolved` | Acknowledged gap; explicitly flagged as needing resolution | Yes (`Unresolved / pending research:`) | Pass | "Long-term cost trajectory is unknown; requires Q3 2026 analysis" |
| `unsupported` | Material claim lacks a source, label, or proper status marker | Yes (if present) | **Fail** (exit 4) | "The system scales to 100k claims" — no source, no label |

## Tagging Discipline

Every material claim must carry one of these statuses via an inline tag. In Markdown reports, use one of these patterns:

### Supported Claims
No tag required (default). But you may include a reference for clarity:

```markdown
Research Foundry runs fully offline by default [claim:clm_001].
```

### Labeled Claims
Use a block prefix or inline tag:

```markdown
**Inference:** Given that source A shows cost doubles per 10K claims and source B 
documents linear scaling, inference suggests cost will become a bottleneck above 50K claims 
[claim:clm_042, inference].
```

Or inline for brevity:

```markdown
Token costs will likely increase by 15% per year (inference, based on clm_087 + clm_091).
```

### Explicitly Unresolved
```markdown
**Unresolved / Pending Research:** The exact cost of IntentTree integration under load 
remains unknown. This requires live testing with 500+ concurrent source nodes.
```

## Verification Process

`rf verify` scans the report and applies the claim policy:

1. **Locate every material claim** in the report (heuristic: imperative sentences, quantitative statements, causal claims, recommendations).
2. **Extract claim status tags** (`[claim:clm_NNN, status]` or report labels).
3. **For supported claims**: check that the claim ID exists in `claims/claim_ledger.yaml`.
4. **For labeled claims**: confirm the label matches a permitted status (inference, speculation, contradicted, unresolved).
5. **For untagged material claims**: flag as `unsupported` (potential error).
6. **Exit codes**:

| Exit Code | Meaning |
|-----------|---------|
| 0 | All claims verified; report passes |
| 2 | Schema validation failed |
| 3 | Governance policy blocked (e.g., work-sensitive material leaked to personal writeback) |
| 4 | Unsupported material claim detected |
| 5 | Cost/token budget exceeded |
| 6 | Adapter or tool failure during verification |
| 7 | Human review required |

## Claim Ledger Structure

The claim ledger (`claims/claim_ledger.yaml`) is the authoritative registry:

```yaml
claims:
  clm_001:
    id: clm_001
    status: supported
    statement: "Research Foundry uses Markdown/YAML as source of truth."
    source_ids:
      - src_20260614_rib026_00
      - src_20260614_rib026_01
    confidence: high
    created_at: "2026-06-14T10:23:45Z"
    tags: [architecture, core-principle]
    extracted_from: ext_20260614_0eba0c9c_001

  clm_002:
    id: clm_002
    status: inference
    statement: "High token costs will limit adoption for cost-sensitive teams."
    source_ids:
      - clm_087  # cost structure
      - clm_091  # scaling behavior
    confidence: medium
    reasoning: "Inferred from two supported claims about cost and scaling."
    created_at: "2026-06-14T11:15:32Z"
    tags: [implications, risk]
```

## Contradiction Log

When sources disagree, the system records contradictions:

```yaml
contradictions:
  - contradiction_id: contra_001
    conflicting_claims:
      - clm_010: "System requires a database"
      - clm_011: "System is file-backed only"
    sources:
      - src_A (claims clm_010)
      - src_B (claims clm_011)
    resolution: "Reconciled via spec review: system is file-backed by design, contradicting an older design doc."
    status: resolved
```

## Inference Log

Tracked separately for transparency:

```yaml
inferences:
  - inference_id: inf_001
    statement: "Adoption will accelerate as teams integrate with IntentTree."
    supporting_claims:
      - clm_087  # integration points exist
      - clm_112  # teams use IntentTree
    reasoning: "Two supported claims suggest conditions for adoption acceleration."
    created_at: "2026-06-14T12:00:00Z"
```

## Policy Enforcement

Claims must pass governance before synthesis:

- **Personal runs** may only contain personal sensitivity claims (public, personal).
- **Work runs** require explicit approval for work-sensitive claims.
- **Client runs** require human review and cannot cross-cite work-sensitive data.

Check your profile:

```bash
rf guard check --profile personal
rf doctor
```

## Example: Verification Flow

Given this report excerpt:

```markdown
# Research Findings

Research Foundry uses Markdown/YAML as source of truth. The system can handle 
10,000+ claims in a single run. (Inference: cost scaling suggests a practical 
ceiling around 50,000 claims for most teams.)

By 2027, evidence-backed research will be standard. (Speculation)

The system requires a database. (Unsupported)
```

Verification would:

1. ✓ `Markdown/YAML...` — claims `clm_001` exists in ledger → **pass**
2. ✓ `10,000+ claims` — claims `clm_015` supported by multiple sources → **pass**
3. ✓ `Inference: cost scaling...` — labeled inference with supporting claim IDs → **pass**
4. ✓ `By 2027, standard` — labeled speculation → **pass**
5. ✗ `requires a database` — material claim, no tag, no ledger entry → **fail** (exit 4)

Run `rf verify --fail-on-unsupported` to catch this before publish.

## See Also

- [Pipeline](pipeline.md) — where claim-mapping fits in the workflow
- [Reference: CLI](../reference/cli.md) — `rf verify` flags and options
