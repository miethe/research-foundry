---
name: project-scaffolder
description: "Use this skill when scaffolding a new project or feature from context (PRD, implementation plan, project directory, or free-text description). Transforms context into a deployed Bundle of artifacts via structured Intent extraction and ranked artifact search. Invoked by /scaffold:project and /scaffold:feature commands. Trigger phrases: 'scaffold my project', 'set up my Codex environment', 'create a starter bundle', 'scaffold from my PRD', 'build my artifact bundle', 'feature scaffold', 'scaffold feature'. Requires a seeded local collection (≥20 artifacts) and a running SkillMeat API."
---

# Project Scaffolder Skill

Transforms project context (PRDs, directories, or free text) into a deployed Bundle of Codex artifacts via a five-step pipeline: analyze → curate → preview → confirm → deploy. **Note**: This is an agent-side skill, invoked user-initiated from Codex via `/scaffold:project` or `/scaffold:feature` commands. It builds on top of **Project Starters** (baseline artifacts auto-deployed by `skillmeat scaffold --full` or the New Project dialog). See "Integration with CLI/Web Scaffolding" below.

## Quick Start

| Mode | Command | Use When |
|------|---------|----------|
| [Project mode](./modes/project-mode.md) | `/scaffold:project` | After project init + starters deployment; adds domain-specific artifacts from PRD |
| [Feature mode](./modes/feature-mode.md) | `/scaffold:feature` | Adding a feature to an existing project; avoids re-adding deployed artifacts |

## Workflow Pipeline

```
/scaffold:project  OR  /scaffold:feature
         │
         ▼
1. ANALYZE — project-analyzer (Sonnet 4.6)
   • Reads context (PRD path / directory / free text, up to 10K tokens)
   • Emits Intent Set YAML (capabilities, stacks, confidence scores)
         │
         ▼ (if aggregate_confidence < 0.65 OR ≥2 high-priority intents < 0.5 confidence)
2. INTERVIEW — Opus asks ≤3 targeted questions
   • Questions target lowest-confidence high-priority intents
   • Answers fed back to analyzer for a refined Intent Set
         │
         ▼
3. CURATE — artifact-curator (Sonnet 4.6) [Phase 2]
   • Three-leg search: local match, local metadata, marketplace
   • Deterministic ranking: 0.5×semantic + 0.3×metadata + 0.2×marketplace
   • De-duplicates by artifact_uuid; caps at 5 candidates/intent
   • Removes candidates with final_score < 0.3
         │
         ▼
4. PREVIEW — shown to user
   • Table: type | name | source | confidence | intent
   • User can confirm all / remove items / abort
         │
         ▼
5. DEPLOY — on confirmation
   • POST /api/v1/bundles → create Bundle
   • POST /api/v1/bundles/{id}/members → add artifacts (alphabetical: type asc, name asc)
   • skillmeat scaffold --bundle <id> --project <path>  [if deploy target specified]
   • Intent Set YAML persisted alongside Bundle manifest
```

## Subagent Definitions

### project-analyzer

- **Definition**: `.Codex/agents/scaffolder/project-analyzer.md`
- **Model**: Sonnet 4.6, permissionMode: plan
- **Input**: PRD file path, implementation plan path, project directory path, or free-text description
- **Processing**: Reads context (truncates at 10K tokens with warning); extracts tech stack, frameworks, architectural patterns, domain concepts, required capabilities
- **Output**: Intent Set YAML with confidence scores per intent and aggregate score
- **Invoked**: Once per scaffold run, before curator

### artifact-curator

- **Definition**: `.Codex/agents/scaffolder/artifact-curator.md`
- **Model**: Sonnet 4.6, permissionMode: plan
- **Input**: Intent Set YAML (from analyzer)
- **Processing**: Three-leg search (local match, metadata, marketplace); merge + rank; de-duplicate; filter
- **Output**: Ranked artifact candidate list with confidence and source intent traceability
- **Invoked**: After analyzer (and interview, if triggered); Phase 2 full implementation

## Intent Schema

Full YAML schema: `./schemas/intent-schema.yaml`
Example (12 intents): `./schemas/example-intents.yaml`
Python dataclasses: `skillmeat/core/scaffolder/intent_schema.py`

### Quick Reference

```yaml
scaffold_run_id: "scaf_20260407_abc123"      # unique per run
generated_at: "2026-04-07T14:32:00Z"         # ISO 8601
scope_variant: "whole-project"               # whole-project | feature | artifact-type-scoped
source_summary: "FastAPI + React + PostgreSQL PRD"
intents:
  - id: "int_001"
    capability: "python-backend"             # see CAPABILITY_ENUM in intent_schema.py
    stack: "fastapi"                         # optional
    confidence: 0.95                         # 0.0–1.0
    source: "PRD §2 — Tech Stack"
    priority: high                           # high | medium | low
aggregate_confidence: 0.75                   # weighted mean by priority
interview_triggered: false
```

### Aggregate Confidence Formula

```
weights: high=1.0, medium=0.6, low=0.3
aggregate = sum(confidence[i] × weight[priority[i]]) / sum(weight[priority[i]])
```

### Interview Trigger

Triggers when:
- `aggregate_confidence < 0.65`, OR
- `count(intents where confidence < 0.5 AND priority == high) >= 2`

Generates ≤3 targeted questions (one per lowest-confidence high-priority intent).
Pure Python logic: `skillmeat/core/scaffolder/interview.py`

## API Integration

The skill uses only existing stable endpoints:

| Leg | Endpoint | Purpose |
|-----|----------|---------|
| Semantic search | `GET /api/v1/match?q=<capability stack>&limit=10` | TF-IDF ranked matches |
| Metadata search | `GET /api/v1/artifacts?tags=<capability>&type=<types>&limit=50` | Tag + type filter |
| Marketplace | `GET /api/v1/marketplace/listings?q=<query>&limit=10` | Optional (feature flag) |
| Bundle create | `POST /api/v1/bundles` | Creates Bundle with scaffold metadata |
| Bundle members | `POST /api/v1/bundles/{id}/members` | Adds ranked artifacts |

Feature flag: `SCAFFOLD_MARKETPLACE_ENABLED` (default: `true`)

## Scope Variants

| Variant | Command | Behavior |
|---------|---------|----------|
| `whole-project` | `/scaffold:project` | Full artifact scan; no exclusion of existing artifacts |
| `feature` | `/scaffold:feature` | Reads deployed `.Codex/` inventory; excludes already-present artifacts |
| `artifact-type-scoped` | Either + `--types` | Restricts curator search to specified artifact types |

## Dry-Run Mode

Pass `--dry-run` to suppress Bundle creation and file writes. Preview is shown; no API writes occur. Useful for evaluating recommendations before committing.

## Prerequisites

- SkillMeat API running (`skillmeat web dev`)
- Collection seeded with ≥20 artifacts for non-trivial results
- For marketplace: `SCAFFOLD_MARKETPLACE_ENABLED=true` (default)

## Integration with CLI/Web Scaffolding (v1)

**Relationship Summary:**

The Project Scaffolding Workflow (v1) has two distinct phases:

1. **Phase 1: Baseline Setup (CLI/Web)** — `skillmeat scaffold --full` or New Project dialog
   - Runs `skillmeat init` (interactive prompts for name, description, platforms, spec detection)
   - Deploys **Project Starters** — org-curated bundles tagged `kind=project_starter` (e.g., planning skills, debug context, devops agents)
   - Every new project gets the enabled starters by default
   - **Emits a hint** pointing to `/scaffold:project` but does NOT auto-invoke it (user-initiated in v1)

2. **Phase 2: PRD-Driven Curation (Agent Skill)** — `/scaffold:project` (this skill)
   - User manually invokes from Codex after project init + starters deployment
   - Analyzes project context (PRD, spec, or directory) → identifies missing domain-specific artifacts
   - Recommends and deploys additional artifacts on **top of** the Project Starters baseline
   - Example: A "FastAPI + React SaaS" project gets Starters (planning, debug), then /scaffold:project adds async-task-queue agents, testing utilities, etc.

**Scope in v1**: Agent dispatch is user-initiated. Auto-invocation of `/scaffold:project` from CLI/web is a v2+ concern (currently in the deferred items list).

**Key Point**: Project Starters form the **baseline**; `/scaffold:project` **extends** it with domain-specific recommendations.

## Mode Guides

- [Project Mode](./modes/project-mode.md) — full detail for `/scaffold:project`
- [Feature Mode](./modes/feature-mode.md) — full detail for `/scaffold:feature`
