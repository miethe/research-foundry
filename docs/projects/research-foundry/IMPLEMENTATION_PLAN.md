---
schema_version: 0.1
id: plan_research_foundry_mvp_2026_06_13
type: implementation_plan
title: "Research Foundry MVP — Implementation Plan"
project: "Research Foundry"
owner: "Nick Miethe"
created_at: "2026-06-13"
status: in_progress
source_spec: docs/projects/research-foundry/research-foundry-mvp-spec.md
---

# Research Foundry MVP — Implementation Plan

This plan operationalizes `research-foundry-mvp-spec.md` into a buildable,
testable MVP. It is executed via **Claude Code workflows** (parallel subagent
teams) coordinated by an orchestrator that owns the integration seams.

## 1. Guiding decisions (the build contract)

| Decision | Choice | Rationale |
|---|---|---|
| Language / runtime | Python ≥ 3.11 | Spec uses Python pseudocode + `python -m research_foundry...` hooks |
| Packaging | `uv` + `pyproject.toml`, src-layout | User standard; reproducible; `rf` console script |
| CLI framework | **Typer** + **Rich** | Clean nested command groups (`rf swarm run`, `rf skillbom promote`), typed, good `--help`, Rich tables for `status`/`doctor`/`cost` |
| Schema source of truth | **JSON Schema (Draft 2020-12) authored in YAML** under `schemas/`, validated with `jsonschema` | Honors "Markdown/YAML is the source of truth"; `rf schema validate` is trivial |
| Serialization | PyYAML (safe load/dump, ordered) + tiny homegrown frontmatter splitter | No heavy deps |
| External tools | gpt-researcher, paper-qa, claude-agent-sdk, litellm = **optional extras**, lazily imported, graceful degrade | MVP must install + run + test with **no API keys / no heavy ML deps** |
| Default execution mode | **Deterministic / offline** end-to-end; LLM is opt-in (`--llm`, profiles) | The differentiated value (claim verifier + governance) is 100% deterministic & testable; LLM calls are seams |

### Core principle (from spec §18)
> Implement the **claim verifier before fancy swarm orchestration.** The
> Foundry's value is that it can *prove* which claims came from where, what was
> inferred, what is speculative, and what should be reused.

So `verification.py` + `governance.py` are the crown jewels: real, exhaustive,
fully unit-tested. Adapters to GPT Researcher / PaperQA2 / Claude Agent SDK are
thin seams that normalize into the same YAML substrate.

## 2. Module contract (`src/research_foundry/`)

```
__init__.py        # __version__
__main__.py        # python -m research_foundry → cli.app()
errors.py          # ExitCode(IntEnum) {OK=0, SCHEMA=2, GOVERNANCE=3, UNSUPPORTED=4,
                   #   BUDGET=5, ADAPTER=6, HUMAN_REVIEW=7}; RFError hierarchy
ids.py             # slugify(), now()/today() clock, make_id(prefix, slug), short_hash()
yamlio.py          # load_yaml / dump_yaml (ordered, block scalars, deterministic)
frontmatter.py     # split_frontmatter(text) -> (meta, body); join_frontmatter(meta, body)
paths.py           # FoundryPaths: root, runs/<id>/..., inbox, intents, registries, mirrors
config.py          # load foundry.yaml + config/*.yaml; KeyProfile/env resolution
schemas.py         # SchemaRegistry: load schemas/*.schema.yaml; validate(obj, name) -> [errors]
registry.py        # registries/*.yaml read + upsert (source_index, run_index, claim_index…)
models.py          # thin dataclasses/TypedDicts for the central artifacts (optional helpers)
services/
  capture.py       # rf capture + rf triage  (raw_idea → intent + ibom + tree node)
  planning.py      # rf plan  (intent+ibom → research_brief + swarm_plan + routing_decision)
  source_cards.py  # rf ingest / source-card create  (locator → source_card.md)
  extraction.py    # rf extract  (source cards → extraction_card.yaml)
  claim_mapping.py # rf claim-map  (extractions → claim_ledger.yaml)
  synthesis.py     # rf synthesize  (claim ledger → report; ONLY existing claim IDs + labels)
  verification.py  # rf verify  (THE verifier; §12 checks; exit codes)
  governance.py    # rf guard  (key profiles §7.1, policy rules §7.2, secret scan)
  writeback.py     # rf bundle + rf writeback  (meatywiki + skillbom + ccdash artifacts)
  telemetry.py     # ccdash event emit + rf ccdash summarize
adapters/
  base.py          # Adapter protocol, AdapterResult, registry, lazy-import guard
  claude_agent_sdk.py / gpt_researcher.py / paperqa2.py / opencode.py / litellm_router.py
validators/
  guard_pretool.py # PreToolUse hook entrypoint (governance preflight)
  scan_artifact.py # PostToolUse hook entrypoint (secret scan + claim-label lint)
  schema_cli.py    # backs `rf schema validate`
```

## 3. Execution waves (workflow orchestration)

- **Wave 0 — Foundation (orchestrator, direct):** pyproject.toml + all util/contract
  modules (`errors, ids, yamlio, frontmatter, paths, config, schemas, registry`,
  `adapters/base`, package `__init__`/`__main__`). Establishes imports every
  service depends on. Commit.
- **Wave 1 — Content (Workflow, parallel):**
  - 16 `schemas/*.schema.yaml` (JSON Schema from §6)
  - `config/*.yaml` + `foundry.yaml` + `.env.example` (§6.1, §7, §8)
  - `templates/*` (§6.8, §6.12, §6.13…)
  - `.claude/agents/rf_*.md` (6 subagents §9) + `.claude/skills/research-foundry/SKILL.md`
    + `.claude/settings.json` hooks (§7.3)
  - README.md. Commit.
- **Wave 2 — Services (Workflow, parallel; disjoint file ownership):** the 10
  service modules + the validators + the 5 adapters, **each with its unit tests**.
  Commit.
- **Wave 3 — CLI + integration (orchestrator):** `cli.py` wiring; `uv sync`;
  `uv run rf --help`; run the demo loop end-to-end; fix. Commit.
- **Wave 4 — Adversarial verification (Workflow):** pytest + acceptance criteria
  (§15): verify FAILS on unsupported claims; guard BLOCKS work/personal mixing;
  every material claim maps or is labeled; bundle references all artifacts; one
  CCDash event + one writeback per run.
- **Wave 5 — Polish (orchestrator):** root-doc identity substitution, demo
  evidence bundle for the §19 topic, final commit.

## 4. Build order (spec §18) → maps to waves
schemas+folders (W0/W1) → CLI skeleton (W0/W3) → governance guard (W2) →
capture/triage (W2) → source cards (W2) → claim ledger (W2) → verifier (W2) →
report generator (W2) → writebacks (W2) → adapters (W2) → council (W2) →
telemetry summaries (W2).

## 5. Acceptance (spec §15) — done = all green
- `rf capture` + `rf triage` produce valid YAML (3 linked artifacts).
- `rf plan` creates brief + routing decision + swarm plan.
- ≥ 5 source cards from mixed types; extraction cards map back.
- 100% of material claims mapped or labeled inference/speculation.
- `rf verify` exits 0 before publish; **exits 4 on an unsupported material claim.**
- `evidence_bundle.yaml` references all run artifacts.
- ≥ 1 MeatyWiki writeback candidate + ≥ 1 SkillBOM candidate.
- 1 CCDash event per run; includes cost/claims/tools/postures/reuse.
- `rf guard` **blocks** work/personal key mixing.
- Demo run for §19 topic produces a zero-unsupported-claim report.
