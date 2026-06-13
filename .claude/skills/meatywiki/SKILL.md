---
name: meatywiki
description: Drive the MeatyWiki CLI end-to-end — knowledge-compilation loop (ingest → classify → extract → compile → file-back → lint) over a file-first Obsidian-compatible markdown vault. Use when running any MeatyWiki CLI task, compiling inbox sources, querying/searching the wiki (including semantic/vector search), checking lens scores, managing workflow runs, evaluating decisions, OR bootstrapping MeatyWiki into a fresh project (vault init + CLAUDE.md sidecar + wiki-spec stub). Triggers: "meatywiki", "compile loop", "ingest into wiki", "vault", "knowledge compilation", "semantic search", "lens score", "fidelity", "freshness", "workflow run", "decision table", "bootstrap meatywiki", "set up meatywiki", "wire meatywiki into this project". Do NOT use for: non-MeatyWiki knowledge systems, Portal UI, SAM/CCDash (those are separate skills/projects).
schema_version: 1
skill_version: 0.3.0
cli_version_range: "compilation-engine-v1 – v1.2 (pre-release)"
spec_ref: SPEC.md
---

# MeatyWiki Skill

## 1. Compile Loop Overview

MeatyWiki implements Karpathy's knowledge-compilation loop over a markdown vault. Sources enter via `ingest` (raw/), flow through classify → extract → compile into structured wiki/ artifacts, and are validated by `lint`. Files are canonical; SQLite + FTS5 (`_meta/meatywiki.db`) is a derived, rebuildable index. Seven engine layers (CLI → Vault → Schema → Index → LLM → Workflows → Hooks) execute as linear pipelines — no DAGs, no retry framework.

---

## 1.5 Bootstrap Mode (one-shot project setup)

**When the user says "bootstrap meatywiki here" / "set up meatywiki for this project" / "wire meatywiki into this repo"**, or when MeatyWiki should be added to a project that has no vault yet, load `bootstrap/README.md` and follow it. Bootstrap is a one-shot orchestration that:

1. Runs `meatywiki init` for the project's vault
2. Writes a `.claude/context/meatywiki.md` sidecar in the project root
3. Proposes a diff-confirmed managed block in root `CLAUDE.md` referencing the sidecar
4. Generates a `<vault>/wiki-spec.md` stub capturing project intent

All steps are idempotent and diff-confirmed. Bootstrap is **separate** from day-to-day CLI usage documented below; once it completes, agents drive `meatywiki` commands normally per the rest of this file.

Entry point: `bootstrap/README.md`. Contract: `SPEC.md` §13. Do NOT inline bootstrap steps here — they are a progressive-disclosure surface.

---

## 2. Decision Tree

```
TASK                                      COMMAND
─────────────────────────────────────────────────────────────────
First-time vault setup                 →  init
Add a source (URL/PDF/note/transcript) →  ingest
Process inbox (raw/ → wiki/)           →  compile --pending
Recompile specific domain              →  compile --scope <domain>
Preview compile without writing        →  compile --dry-run
Force full recompile of all sources    →  compile --full
Look up information in the wiki        →  query
Write query answer back to vault       →  query --file-back
Scope a query to a domain              →  query --scope <domain>
Cross-source synthesis / summary       →  synthesize
Fix frontmatter / schema drift         →  lint --fix
Generate a lint report                 →  lint --report
Run specific lint checks               →  lint --checks <names>
Full-text keyword search               →  search
Filter search by artifact type         →  search --type <type>
Filter search by freshness             →  search --freshness <age>
Vector similarity search               →  search --mode semantic
Hybrid FTS5 + vector search            →  search --mode hybrid
Traverse artifact relationships        →  graph
Set relationship traversal depth       →  graph --depth <n>
Export graph in specific format        →  graph --format <fmt>
Rebuild the derived SQLite index       →  index --reset
Index embeddings for semantic search   →  index --reindex --embeddings
Count artifacts / freshness stats      →  stats
Report classification friction metrics →  stats --friction
Review low-confidence pending artifacts →  review --low-confidence
Override artifact classification       →  reclassify <artifact-id> --type <type>
Health check: vault + index + config   →  doctor
Auto-ingest on file drop               →  watch
Auto-compile on file drop              →  watch --auto-compile
Lifecycle promotion (draft→compiled…)  →  promote
Force promotion past rules             →  promote --force
Start FastAPI thin wrapper             →  serve
List computed lens scores              →  lens list
Get lens scores for an artifact        →  lens get <artifact-id>
List Portal workflow runs              →  workflow list
Show a workflow run                    →  workflow show <run-id>
Cancel a workflow run                  →  workflow cancel <run-id>
Retry a failed workflow run            →  workflow retry <run-id>
Bulk-action workflow runs              →  workflow bulk-action
List decision tables                   →  decision list
Show a decision table                  →  decision show <table-id>
Create a decision table (YAML spec)    →  decision create <spec.yaml>
Update a decision table                →  decision update <table-id> <spec.yaml>
Delete a decision table                →  decision rm <table-id>
Evaluate artifact against rubric       →  decision apply <table-id> <artifact-id>

(Register artifact with SAM           →  [deferred: F1])
```

---

## 3. Command Map

| Command | Purpose | Key flags | Reference |
|---|---|---|---|
| `init` | Initialize a new vault at the target path | — | `references/command-reference.md#init` |
| `ingest` | Ingest a source into raw/ and classify | — | `references/command-reference.md#ingest` |
| `compile` | Process raw/ artifacts through extract → compile → write wiki/ | `--pending`, `--scope`, `--dry-run`, `--full` | `references/command-reference.md#compile` |
| `query` | FTS5-backed natural-language query over the wiki | `--file-back`, `--scope` | `references/command-reference.md#query` |
| `synthesize` | Cross-source synthesis into a new wiki/ artifact | — | `references/command-reference.md#synthesize` |
| `lint` | Deterministic + semantic checks on vault artifacts | `--fix`, `--report`, `--checks` | `references/command-reference.md#lint` |
| `search` | Full-text and semantic/hybrid search | `--type`, `--freshness`, `--mode`, `--semantic` | `references/command-reference.md#search` |
| `graph` | Traverse and render artifact relationships | `--depth`, `--format` | `references/command-reference.md#graph` |
| `index` | Manage the derived SQLite + FTS5 + embeddings index | `--reset`, `--reindex`, `--embeddings` | `references/command-reference.md#index` |
| `stats` | Vault counts by type, lifecycle, freshness | `--friction` | `references/command-reference.md#stats` |
| `review` | Review low-confidence or flagged artifacts pending classification | `--low-confidence` | `references/command-reference.md#review` |
| `reclassify` | Override artifact classification and record the override | `--type` | `references/command-reference.md#reclassify` |
| `doctor` | Health check: structure, index freshness, config, drift | — | `references/command-reference.md#doctor` |
| `watch` | Auto-ingest on file drop in raw/ | `--auto-compile` | `references/command-reference.md#watch` |
| `promote` | Lifecycle promotion with default rules | `--force` | `references/command-reference.md#promote` |
| `serve` | Start the FastAPI thin CLI-parity wrapper | — | `references/command-reference.md#serve` |
| `lens` | Query computed lens scores (fidelity, freshness, clarity) | `--format`, `--freshness` | `references/command-reference.md#lens` |
| `workflow` | Observe and control Portal workflow runs | — | `references/command-reference.md#workflow` |
| `decision` | Manage decision tables and evaluate artifacts against rubrics | — | `references/command-reference.md#decision` |

---

## 4. Top 7 Workflow Recipes

### Recipe 1 — Ingest a URL and auto-classify into the wiki

```bash
meatywiki ingest https://example.com/article
meatywiki compile --pending
meatywiki stats
```

### Recipe 2 — Ingest a PDF with manual classification override

```bash
meatywiki ingest ~/downloads/paper.pdf
# Review raw/ artifact; edit frontmatter artifact_type if auto-classify is wrong
meatywiki compile --pending
```

### Recipe 3 — Full compile loop end-to-end

```bash
meatywiki ingest <source>
meatywiki compile --pending
meatywiki lint --fix
meatywiki stats
```

### Recipe 4 — Query the wiki and write the answer back to a vault file

```bash
meatywiki query "What are the key patterns in distributed tracing?" --file-back
# Engine writes answer to wiki/summaries/ with schema_version: "1.0.0" frontmatter
```

### Recipe 5 — Rebuild the derived index after manual vault edits

```bash
meatywiki index --reset
meatywiki stats
meatywiki doctor
```

### Recipe 6 — Semantic search workflow

```bash
# One-time: build embeddings index (calls embedding provider once per artifact)
meatywiki index --reindex --embeddings

# Vector similarity search
meatywiki search "attention mechanisms in transformers" --mode semantic

# Hybrid: FTS5 + vector, ranked merge
meatywiki search "distributed tracing patterns" --mode hybrid --type concept
```

### Recipe 7 — Decision table triage workflow

```bash
# Check lens freshness to identify stale artifacts before triage
meatywiki lens list --freshness 30d --format table

# Create a decision table from a YAML rubric spec
meatywiki decision create triage-rubric.yaml

# Evaluate an artifact against the rubric
meatywiki decision apply <table-id> <artifact-id>
```

---

## 5. Guardrails

- **(a) All writes go through the engine.** Agents MUST invoke `meatywiki` commands rather than editing `wiki/`, `raw/`, or `_meta/` files directly; all writes pass through `vault/writer.py` which indexes in the same transaction. Direct file edits will cause vault/index drift.
- **(b) `_meta/` is engine-owned.** Never edit `_meta/meatywiki.db`, `_meta/compile_state.json`, or `_meta/config.yaml` programmatically except via CLI commands or `meatywiki config` operations. `_meta/` is gitignored.
- **(c) Semantic search requires embeddings index.** `search --mode semantic` and `--mode hybrid` require `meatywiki index --reindex --embeddings` to have been run and `PORTAL_DATABASE_URL` set. Each query calls the embedding provider once. Fall back to plain `search` (FTS5 only) when embeddings are not indexed.
- **(d) All V1 frontmatter must include `schema_version: "1.0.0"`.** Artifacts without this field will fail lint and will not round-trip through the index.
- **(e) `lens`, `workflow`, and `decision` commands require `PORTAL_DATABASE_URL`.** Read-only `workflow list|show` work without the arq worker running. Mutation commands (`workflow cancel|retry|bulk-action`) need the arq worker running.

---

## 6. Deferred Features (do NOT invoke)

| Feature | Track | What the skill says |
|---|---|---|
| SAM `register` + live hook | F1 | no-op stub only |
| CCDash live hook | F2 | no-op stub only |
| Dev-artifact connectors (SkillMeat/GitHub/Claude config) | F4 | knowledge-domain connectors only |
| Portal / web UI | F6 | not in engine V1 |
| Image OCR | — | images as opaque blobs + captions |
| `agent_visibility` enforcement | — | advisory metadata only |
| Prompt-template auto-recompile | — | manual `compile --full --scope` only |
| DAG workflows / retry | — | linear pipelines only |

**Promoted (no longer deferred):** F3 (semantic/hybrid search via `search --mode`) and F5 (lens scoring via `lens get|list`) shipped in v1.2.

---

## 7. References Pointer Table

| File | Load when | Max lines |
|---|---|---|
| `references/command-reference.md` | Need full flag/exit-code/example detail for a command | 900 |
| `references/workflow-patterns.md` | Need expanded recipe with setup/output/troubleshooting | 800 |
| `references/vault-layout.md` | Need to understand directory ownership or Obsidian compat | 800 |
| `references/artifact-taxonomy.md` | Need to construct or validate a specific artifact subtype | 800 |
| `references/hook-policy.md` | Working near SAM/CCDash stubs or F1/F2 boundary | 800 |
| `references/troubleshooting.md` | Compile failure, vault drift, index corruption, LLM timeout | 800 |
| `bootstrap/README.md` | Bootstrap mode entry: when to trigger, what it does, exit conditions | 200 |
| `bootstrap/plan.md` | Bootstrap orchestration: state detection → B1–B5 with exact commands | 300 |
| `bootstrap/sidecar-template.md` | Canonical content for `.claude/context/meatywiki.md` sidecar (B3) | 200 |
| `bootstrap/wiki-spec-template.md` | Canonical content for `<vault>/wiki-spec.md` intent stub (B5) | 200 |
| `bootstrap/troubleshooting.md` | Sidecar drift, partial-state recovery, re-bootstrap across skill versions | 300 |

---

## 8. Contract Pointer

See `SPEC.md` for the coverage matrix, CLI version compatibility, and update protocol.
