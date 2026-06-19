---
title: RF Command Reference
description: Complete reference for the `rf` CLI with flags and examples
audience: developers, power users
tags: reference, cli, commands
created: 2026-06-19
updated: 2026-06-19
category: reference
status: published
related_documents: [concepts/pipeline.md, quickstart.md]
---

# RF Command Reference

Complete reference for the `rf` CLI. All examples assume you're in a foundry directory (created via `rf init`).

## Global Flags

```bash
rf [COMMAND] [FLAGS] [ARGS]

  --profile PROFILE            Execution profile: personal, work_approved, client_approved, offline_only
                               (default: personal if .env.personal exists)
  --verbose, -v                Detailed output
  --quiet, -q                  Suppress non-error output
  --help, -h                   Show help
  --version                    Show version
```

---

## Capture

**Capture a raw idea into the inbox.**

```bash
rf capture TEXT [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--from` | string | manual | Source: manual, chat, voice, note, clip, email, meeting |
| `--title` | string | (auto) | Override auto-generated title (first ~8 words of TEXT) |
| `--sensitivity` | string | personal | public, personal, work_internal, work_sensitive, client_internal, client_sensitive |
| `--urgency` | string | medium | low, medium, high |
| `--tags` | string[] | (none) | Comma-separated tags (e.g., `--tags agentic-os,research-foundry`) |
| `--research-potential` | string | unknown | unknown, exploratory, high-impact, foundational |
| `--suggested-project` | string | Research Foundry | Default project name |

### Examples

```bash
# Simple capture
rf capture "How should agentic research handle evidence?"

# Full metadata
rf capture "Research agentic workflows" \
  --from chat \
  --sensitivity personal \
  --urgency high \
  --tags agentic-os \
  --tags research-foundry \
  --research-potential high-impact

# Urgent work research
rf capture "Q3 KnitWit scope assessment" \
  --from meeting \
  --sensitivity work_internal \
  --urgency high \
  --suggested-project KnitWit
```

### Output

Raw idea file: `inbox/raw_ideas/raw_<title_slug>_YYYYMMDD_HHMM.md`

---

## Triage

**Convert raw idea → research intent + I-BOM + IntentTree node.**

```bash
rf triage RAW_IDEA_PATH [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--create-intent` | bool | true | Create research intent |
| `--create-ibom` | bool | true | Create I-BOM (Intent BOM) |
| `--create-tree-node` | bool | true | Create IntentTree node |

### Examples

```bash
# Triage and create all artifacts
rf triage inbox/raw_ideas/raw_*.md

# Triage but skip IntentTree node creation (offline)
rf triage inbox/raw_ideas/raw_*.md --no-create-tree-node

# Triage with explicit profile
rf triage inbox/raw_ideas/raw_*.md --profile work_approved
```

### Output

- Intent: `intents/active/<intent_id>.yaml`
- I-BOM: `iboms/active/<ibom_id>.yaml`
- IntentTree node: `intenttree/nodes/<node_id>.yaml`

---

## Plan

**Plan a research swarm: create research brief, swarm plan, and routing decision.**

```bash
rf plan INTENT_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--depth` | string | medium | shallow, medium, deep |
| `--audience` | string | technical | technical, business, executive |
| `--max-cost` | float | 10.0 | Token budget in USD |
| `--freshness` | string | 180d | How recent sources should be (180d, 90d, 30d, 7d) |

### Examples

```bash
# Standard deep research
rf plan intent_research_20260614_agentic_workflows \
  --depth deep \
  --audience technical

# Quick shallow research with low cost
rf plan intent_research_20260614_agentic_workflows \
  --depth shallow \
  --max-cost 1.0

# Executive summary with low cost
rf plan intent_research_20260614_agentic_workflows \
  --depth medium \
  --audience executive \
  --max-cost 2.0
```

### Output

Run directory: `runs/rf_run_YYYYMMDD_<slug>/` with:
- `run.yaml` (run metadata)
- `research_brief.md` (human-readable brief)
- `swarm_plan.yaml` (agent routing)
- `routing_decision.yaml` (model selection)

---

## Ingest

**Add sources to a run (PDF, URL, document, notebook).**

```bash
rf ingest SOURCE [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--source-type` | string | document | paper, article, official_doc, notebook, report, blog, social_media, video_transcript, conversation |
| `--sensitivity` | string | personal | (see Capture) |
| `--run` | string | (latest) | Run ID (auto-detects if omitted) |
| `--tags` | string[] | (none) | Artifact tags |

### Examples

```bash
# Ingest a local PDF
rf ingest ./research.pdf \
  --source-type paper \
  --sensitivity personal \
  --run rf_run_20260614_agentic_workflows

# Ingest a URL (requires network)
rf ingest "https://docs.example.com/guide.html" \
  --source-type official_doc \
  --sensitivity public

# Ingest a notebook
rf ingest notebook://my_research_notebook \
  --source-type notebook \
  --sensitivity personal

# Ingest with tags
rf ingest ./source.pdf \
  --source-type paper \
  --tags empirical \
  --tags trusted-source
```

### Output

Source card: `runs/rf_run_*/sources/src_<hash>_NN.md`

---

## Extract

**Extract evidence from sources using cheap model profile.**

```bash
rf extract RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--model-profile` | string | rf_extract_cheap | Model profile name |
| `--sources` | string[] | (all) | Filter by source IDs (optional) |

### Examples

```bash
# Standard extraction (cheap model)
rf extract rf_run_20260614_agentic_workflows

# Extract with custom profile
rf extract rf_run_20260614_agentic_workflows \
  --model-profile rf_extract_medium

# Extract from specific sources only
rf extract rf_run_20260614_agentic_workflows \
  --sources src_20260614_rib026_00 \
  --sources src_20260614_rib026_01
```

### Output

Extraction cards: `runs/rf_run_*/extractions/ext_*.yaml`

---

## Claim-Map

**Build the authoritative claim ledger from extractions.**

```bash
rf claim-map RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--from` | string | extractions | Source type: extractions, previous_ledger, inference_log |
| `--dedup` | bool | true | Deduplicate similar claims |
| `--threshold` | float | 0.85 | Similarity threshold for deduplication (0–1) |
| `--out` | string | claims/claim_ledger.yaml | Output ledger path |

### Examples

```bash
# Build ledger from extractions
rf claim-map rf_run_20260614_agentic_workflows

# Build ledger with custom dedup threshold
rf claim-map rf_run_20260614_agentic_workflows --threshold 0.90

# Update existing ledger
rf claim-map rf_run_20260614_agentic_workflows --from previous_ledger
```

### Output

Claim ledger: `runs/rf_run_*/claims/claim_ledger.yaml`

---

## Synthesize

**Synthesize a research report using deep model profile (may only cite claim IDs).**

```bash
rf synthesize RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--model-profile` | string | rf_synthesize_deep | Model profile name |
| `--report` | string | reports/report_draft.md | Output report path |
| `--tone` | string | professional | professional, executive, technical, accessible |
| `--audience` | string | technical | (from plan, or override) |
| `--max-length` | int | 0 (unlimited) | Max words in report |

### Examples

```bash
# Standard synthesis
rf synthesize rf_run_20260614_agentic_workflows

# Executive summary
rf synthesize rf_run_20260614_agentic_workflows \
  --tone executive \
  --audience executive \
  --max-length 2000

# Technical deep dive
rf synthesize rf_run_20260614_agentic_workflows \
  --tone technical \
  --model-profile rf_synthesize_deep
```

### Output

Report: `runs/rf_run_*/reports/report_draft.md` (with inline claim status tags)

---

## Verify

**Verify all material claims are supported, labeled, or unresolved.**

```bash
rf verify RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fail-on-unsupported` | bool | false | Exit 4 if unsupported claims found |
| `--report` | string | (auto-detect) | Explicit report path |
| `--claim-ledger` | string | (auto-detect) | Explicit ledger path |
| `--strict` | bool | false | Also fail on warnings (inference/speculation count) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All claims verified; pass |
| 2 | Schema validation failed |
| 3 | Governance policy blocked |
| 4 | Unsupported material claim detected |
| 5 | Budget exceeded |
| 6 | Adapter/tool failure |
| 7 | Human review required |

### Examples

```bash
# Verify and fail on unsupported claims
rf verify rf_run_20260614_agentic_workflows --fail-on-unsupported

# Verify with explicit paths
rf verify rf_run_20260614_agentic_workflows \
  --report reports/report_final.md \
  --claim-ledger claims/claim_ledger.yaml \
  --fail-on-unsupported

# Strict verification (also warn on high inference count)
rf verify rf_run_20260614_agentic_workflows --strict
```

### Output

Verification report: `runs/rf_run_*/reviews/verification.yaml`

---

## Bundle

**Create immutable evidence bundle snapshot.**

```bash
rf bundle RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--verify` | bool | false | Run verification before bundling |
| `--out` | string | evidence_bundle.yaml | Output bundle path |

### Examples

```bash
# Create bundle
rf bundle rf_run_20260614_agentic_workflows

# Create bundle with verification
rf bundle rf_run_20260614_agentic_workflows --verify

# Custom output path
rf bundle rf_run_20260614_agentic_workflows \
  --verify \
  --out bundles/bundle_final_approved.yaml
```

### Output

Bundle: `runs/rf_run_*/evidence_bundle.yaml` (immutable snapshot)

---

## Writeback

**Render and push outputs to MeatyWiki, SkillMeat, CCDash, NotebookLM, etc.**

```bash
rf writeback RUN_ID [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--targets` | string[] | all | Comma-separated: meatywiki, skillmeat, ccdash, intenttree, arc, notebooklm |
| `--require-review` | bool | false | Hold before publishing; operator must approve |
| `--confirm-approved` | bool | false | Confirm approval and proceed (after review) |
| `--profile` | string | personal | (global flag) |

### Examples

```bash
# Write back to all targets
rf writeback rf_run_20260614_agentic_workflows \
  --targets meatywiki,skillmeat,ccdash

# Require review before writeback
rf writeback rf_run_20260614_agentic_workflows \
  --targets meatywiki \
  --require-review

# Confirm approved and proceed
rf writeback rf_run_20260614_agentic_workflows \
  --targets meatywiki \
  --confirm-approved

# Work-sensitive writeback
rf writeback rf_run_20260614_agentic_workflows \
  --profile work_approved \
  --targets meatywiki,skillmeat \
  --require-review
```

### Output

Writebacks: `runs/rf_run_*/writebacks/`:
- `meatywiki_writeback.md`
- `skillbom_candidate.md`
- `ccdash_event.yaml`
- `intenttree_status.yaml`
- `notebooklm_upload_candidate.md`

---

## Summarize

**Aggregate telemetry and outcomes across runs.**

```bash
rf summarize [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period` | string | daily | daily, weekly, monthly, all |
| `--output` | string | (print) | Output file (YAML or JSON) |
| `--filter` | string | (none) | Filter by profile, sensitivity, or intent_id |

### Examples

```bash
# Daily summary
rf summarize --period daily

# Weekly summary to file
rf summarize --period weekly --output telemetry/week_summary.yaml

# All-time summary
rf summarize --period all

# Filter by profile
rf summarize --period daily --filter "profile:work_approved"
```

### Output

Summary report (stdout or file): token costs, claim stats, verification outcomes, run count.

---

## Guard

**Manage governance profiles and security checks.**

```bash
rf guard [SUBCOMMAND] [FLAGS]
```

### Subcommands

#### `check`
Check governance profile status:

```bash
rf guard check --profile personal
rf guard check --profile work_approved
```

#### `reload`
Reload governance policies from config:

```bash
rf guard reload
```

#### `redact`
Redact secrets and PII from a run:

```bash
rf guard redact runs/rf_run_*/ --target public
```

### Examples

```bash
rf guard check --profile personal
rf guard reload
rf guard redact runs/rf_run_20260614_*/ --target public
```

---

## Doctor

**Diagnose system health and configuration.**

```bash
rf doctor [FLAGS]
```

Shows:
- Profile status (keys, providers, writebacks)
- External service reachability (IntentTree, ARC, MeatyWiki, SkillMeat, NotebookLM)
- Python version, package version, venv status
- Schema validation, storage usage

### Examples

```bash
rf doctor
rf doctor --verbose
```

---

## Status

**Show run status or push updates to external systems.**

```bash
rf status [SUBCOMMAND] [FLAGS]
```

### Subcommands

#### `show`
Show run status:

```bash
rf status show rf_run_20260614_agentic_workflows
```

#### `push`
Push status update to IntentTree or ARC:

```bash
rf status push \
  --run rf_run_20260614_agentic_workflows \
  --to intenttree \
  --stage sources_ingested

rf status push \
  --run rf_run_20260614_agentic_workflows \
  --to arc \
  --stage verify_passed
```

---

## Cost

**Show token and financial cost for one or more runs.**

```bash
rf cost [RUN_ID] [FLAGS]
```

### Examples

```bash
rf cost rf_run_20260614_agentic_workflows
rf cost runs/rf_run_*/
rf cost --period daily
```

---

## Index

**Manage artifact registries (indexes over sources, claims, reports, runs).**

```bash
rf index [SUBCOMMAND]
```

### Subcommands

#### `rebuild`
Rebuild all indexes:

```bash
rf index rebuild
```

#### `search`
Search across indexed artifacts:

```bash
rf index search "agentic research" --type intent
rf index search "agentic research" --type claim
rf index search "agentic research" --type report
```

---

## NotebookLM (NLM)

**Manage NotebookLM integration (optional; requires live NLM session).**

```bash
rf notebooklm [SUBCOMMAND] [FLAGS]
```

### Subcommands

#### `resolve`
Resolve or create the run ↔ notebook mapping:

```bash
rf notebooklm resolve --run rf_run_20260614_agentic_workflows --project my-project --create
```

#### `status`
Show notebook status:

```bash
rf notebooklm status --run rf_run_20260614_agentic_workflows
```

#### `sync`
Sync notebook sources with RF:

```bash
rf notebooklm sync --run rf_run_20260614_agentic_workflows --project my-project
```

---

## See Also

- [Quickstart](../quickstart.md)
- [Pipeline](../concepts/pipeline.md)
- [Run Artifacts](../concepts/artifacts.md)
