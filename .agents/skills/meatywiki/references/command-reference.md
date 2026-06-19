---
name: meatywiki-command-reference
description: Complete CLI reference for MeatyWiki commands — flags, examples, exit codes. Covers 14 V1 commands, migrate-edges (v1.1), and lens/workflow/decision/semantic-search (v1.2).
type: reference
skill_name: meatywiki
cli_version_range: "compilation-engine-v1 – v1.2 (pre-release)"
schema_version: 1
created: 2026-04-14
updated: 2026-05-07
---

# MeatyWiki CLI Command Reference

All commands in decision-tree order. Load this file when SKILL.md's command map isn't enough. `register` is in the Deferred Commands footer only.

---

## init

**Purpose.** Initialize a new vault directory structure at the target path.

**Usage.**
```bash
meatywiki init <vault-path>
```

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Create a new vault in ~/my-wiki
meatywiki init ~/my-wiki

# Create a vault in the current directory
meatywiki init .
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Vault initialized successfully |
| 1 | Target path already contains a vault or permission error |

**Output.** Human-readable confirmation listing created directories (`raw/`, `wiki/`, `blog/`, `projects/`, `_meta/`, `_prompts/`) and path of generated `_meta/config.yaml`.

**Related.** See `vault-layout.md` for full directory ownership rules and `_meta/` boundary.

---

## ingest

**Purpose.** Ingest a source into `raw/` and trigger auto-classification.

**Usage.**
```bash
meatywiki ingest <source>
```

Where `<source>` is one of the 9 V1 knowledge-domain connector types: local notes (`.md`), URLs, PDFs, transcripts (`.txt`/`.vtt`), AI-tool exports (chat exports, tool outputs), and related variants. Developer-artifact connectors (SkillMeat, GitHub, Claude configs) are `[deferred: F4]`.

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Ingest a URL; engine fetches, extracts text, writes to raw/
meatywiki ingest https://example.com/article

# Ingest a local PDF
meatywiki ingest ~/downloads/paper.pdf

# Ingest a local markdown note
meatywiki ingest ~/notes/meeting-2026-04-14.md

# Ingest a transcript file
meatywiki ingest ~/recordings/interview.vtt
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Source ingested and written to raw/ |
| 1 | Unreachable URL, unreadable file, or unsupported source type |

**Output.** Human-readable: path of artifact, inferred `artifact_type`, `lifecycle_stage: raw`, and **outcome**:

| Outcome | Meaning |
|---------|---------|
| `created` | New source (no prior `original_path` match); fresh artifact written to `raw/` with new ULID. |
| `cached` | Source file unchanged (hash matches prior `compile_state` record); no write, no-op. |
| `updated` | Source file modified (same `original_path`, different hash); existing artifact updated in-place with same ULID; derived artifacts marked `needs_recompile: true` for lazy re-compilation on next `compile` run. |

Images ingested as opaque blobs with optional captions; no OCR in V1.

**Related.** Run `compile --pending` after ingest to process raw/ through the compile pipeline. When re-ingesting an edited source, `updated` outcome signals that the next `compile` run will re-derive all downstream artifacts without manual intervention. See `artifact-taxonomy.md` for artifact type reference and `needs_recompile` field semantics.

---

## compile

**Purpose.** Process `raw/` artifacts through classify → extract → compile → write `wiki/`.

**Usage.**
```bash
meatywiki compile [--pending] [--scope <domain>] [--dry-run] [--full]
```

**Required flags.** None. (Running `meatywiki compile` with no flags compiles all pending sources; use a flag to narrow scope.)

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--pending` | off | Compile only artifacts in `raw/` with `lifecycle_stage: raw` (not yet classified) |
| `--scope <domain>` | all domains | Limit compile to a named domain (e.g., `ml`, `distributed-systems`); repeatable |
| `--dry-run` | off | Run all pipeline stages but write no files; print what would change |
| `--full` | off | Force recompile of all sources regardless of `lifecycle_stage`; ignores compile_state.json |

**Examples.**
```bash
# Compile only newly ingested (pending) sources
meatywiki compile --pending

# Preview compile without writing (safe pre-flight)
meatywiki compile --pending --dry-run

# Recompile only the ml domain
meatywiki compile --scope ml

# Force full recompile of everything
meatywiki compile --full

# Force full recompile scoped to one domain
meatywiki compile --full --scope distributed-systems
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Compile completed; all staged artifacts written |
| 1 | Pipeline stage failure (LLM error, schema validation failure, write error) |
| 2 | No pending sources found (when `--pending` passed and raw/ is empty) |

**Output.** Human-readable progress per artifact: `[compile] <artifact-id> → wiki/<subdir>/<slug>.md`. `--dry-run` prefixes all lines with `[dry-run]` and writes nothing. Final summary: N compiled, N skipped, N failed.

**Related.** See `workflow-patterns.md` recipe 3 for the full compile loop. Prompt-template auto-recompile is `[deferred: Q4]`; use `--full --scope` manually.

---

## query

**Purpose.** Execute an FTS5-backed natural-language query over compiled wiki artifacts.

**Usage.**
```bash
meatywiki query "<question>" [--file-back] [--scope <domain>]
```

**Required flags.** None. (The query string is a positional argument.)

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--file-back` | off | Write query answer as a new artifact to `wiki/summaries/` with `schema_version: "1.0.0"` frontmatter |
| `--scope <domain>` | all domains | Restrict FTS5 search to artifacts in a named domain |

**Examples.**
```bash
# Query the wiki for an answer
meatywiki query "What are the key patterns in distributed tracing?"

# Query and write the answer back to the vault
meatywiki query "Summarize the consensus algorithms covered in the wiki" --file-back

# Scope a query to a specific domain
meatywiki query "How does attention work?" --scope ml
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Query completed; results printed (or filed) |
| 1 | FTS5 index error or LLM failure |
| 2 | No results found |

**Output.** Human-readable answer synthesized from matched wiki artifacts, followed by a list of source artifact IDs. With `--file-back`: additionally prints path of created `wiki/summaries/` artifact.

**Related.** For keyword search over raw text, use `search`. See `workflow-patterns.md` recipe 4 for the query + file-back pattern.

---

## synthesize

**Purpose.** Perform cross-source synthesis and write a new wiki artifact from multiple sources.

**Usage.**
```bash
meatywiki synthesize "<topic>" [<source-id> ...]
```

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Synthesize a topic from the full wiki
meatywiki synthesize "Consensus algorithms in distributed systems"

# Synthesize from specific source artifact IDs
meatywiki synthesize "RAFT vs Paxos tradeoffs" art-01HXYZ art-01HABC

# Synthesize a topic scoped by title keyword
meatywiki synthesize "transformer attention mechanisms"
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Synthesis artifact written to wiki/ |
| 1 | LLM failure or no relevant sources found |

**Output.** Human-readable: path of created `wiki/syntheses/` artifact, source artifact IDs used, token cost summary.

**Related.** `synthesize` writes to `wiki/syntheses/`; for a simple query-and-file, use `query --file-back`. See `artifact-taxonomy.md` for the 5 synthesis output subtypes.

---

## lint

**Purpose.** Run deterministic and semantic checks on vault artifacts; optionally auto-fix.

**Usage.**
```bash
meatywiki lint [--fix] [--report] [--checks <names>]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--fix` | off | Auto-apply safe fixes (missing `schema_version`, malformed frontmatter, broken wikilinks) |
| `--report` | off | Write a structured lint report to `_meta/lint-report.json` instead of (or in addition to) stdout |
| `--checks <names>` | all checks | Comma-separated subset of check names (e.g., `frontmatter,links,lifecycle`) |

**Examples.**
```bash
# Run all lint checks; print findings to stdout
meatywiki lint

# Auto-fix all safe issues
meatywiki lint --fix

# Generate a lint report file
meatywiki lint --report

# Run only frontmatter and lifecycle checks
meatywiki lint --checks frontmatter,lifecycle

# Fix issues and write a report
meatywiki lint --fix --report
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | No issues found (or all issues fixed with `--fix`) |
| 1 | Issues found that could not be auto-fixed (or `--fix` not passed) |
| 2 | Internal lint engine error |

**Output.** Per-artifact findings table: artifact path, check name, severity, description. With `--fix`: lines marked `[fixed]` or `[manual-required]`. With `--report`: confirmation of report path.

**Related.** Run after every `compile` in the standard loop. See `workflow-patterns.md` recipe 3. For vault health beyond lint, use `doctor`.

---

## search

**Purpose.** Search vault artifacts: FTS5 keyword, vector similarity, or hybrid ranked merge.

**Usage.**
```bash
meatywiki search "<query>" [--mode {fts|semantic|hybrid}] [--semantic] [--type <artifact-type>] [--freshness <age>]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--mode {fts\|semantic\|hybrid}` | `fts` | `fts`: FTS5 keyword only. `semantic`: vector similarity via pgvector. `hybrid`: FTS5 + vector ranked merge. |
| `--semantic` | off | Shorthand for `--mode semantic`. |
| `--type <artifact-type>` | all types | Filter results to a specific artifact subtype (e.g., `concept`, `entity`, `summary`). Applies in all modes. |
| `--freshness <age>` | all ages | Filter to artifacts updated within a time window (e.g., `7d`, `30d`, `1y`). Applies in all modes. |

**Semantic search prerequisites.** Run `meatywiki index --reindex --embeddings` first and set `PORTAL_DATABASE_URL`. Each query calls the embedding provider once.

**Examples.**
```bash
# FTS5 keyword search (default)
meatywiki search "transformer attention"

# Vector similarity search
meatywiki search "attention mechanisms in transformers" --mode semantic

# Shorthand for semantic
meatywiki search "distributed tracing" --semantic

# Hybrid: FTS5 + vector, ranked merge
meatywiki search "consensus algorithms" --mode hybrid --type concept

# Filter by type and freshness (all modes)
meatywiki search "LLM evaluation" --freshness 30d --type summary
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Search completed; results printed |
| 1 | Index error (FTS5 or embeddings) |
| 2 | No results found |

**Output.** Ranked results table: artifact path, type, last-updated, match snippet (FTS5) or similarity score (semantic). Hybrid mode shows merged rank.

**Related.** For natural-language questions with synthesized answers, use `query`. For type enumeration, see `artifact-taxonomy.md`. Run `index --reindex --embeddings` before first semantic search.

---

## graph

**Purpose.** Traverse and render artifact relationship edges from the compiled graph index.

**Usage.**
```bash
meatywiki graph [<artifact-id>] [--depth <n>] [--format <fmt>]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--depth <n>` | 2 | Number of relationship hops to traverse from the root artifact |
| `--format <fmt>` | `text` | Output format: `text`, `json`, `dot` (Graphviz) |

**Examples.**
```bash
# Show the relationship graph for a specific artifact (depth 2)
meatywiki graph art-01HXYZ

# Traverse up to 3 hops deep
meatywiki graph art-01HXYZ --depth 3

# Export the full graph in Graphviz DOT format
meatywiki graph --format dot

# Export artifact subgraph as JSON
meatywiki graph art-01HABC --format json --depth 1
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Graph traversal complete; output printed or written |
| 1 | Artifact ID not found or index error |

**Output.** `text`: indented tree of artifact IDs with edge labels (e.g., `supports`, `contradicts`, `derived-from`). `json`: structured edge list. `dot`: Graphviz DOT source.

**Related.** See `artifact-taxonomy.md` for edge type definitions. If graph appears stale after manual vault edits, run `index --reset` first.

---

## index

**Purpose.** Manage the derived SQLite + FTS5 index and optional embeddings index.

**Usage.**
```bash
meatywiki index [--reset] [--reindex] [--embeddings]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--reset` | off | Drop and rebuild `_meta/meatywiki.db` from vault files; safe to run at any time |
| `--reindex` | off | Rebuild the index incrementally (use with `--embeddings` to rebuild embeddings only) |
| `--embeddings` | off | Generate and store vector embeddings for all indexed artifacts; used with `--reindex`. Calls the embedding provider once per artifact. Requires `PORTAL_DATABASE_URL`. |

**Examples.**
```bash
# Rebuild FTS5 index after manual vault edits or corruption
meatywiki index --reset

# Check index status without rebuilding
meatywiki index

# Build embeddings index for semantic search (one-time / after bulk ingest)
meatywiki index --reindex --embeddings

# Rebuild embeddings only (not full FTS5 reset)
meatywiki index --reindex --embeddings
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Index rebuilt or status reported successfully |
| 1 | Index rebuild failed (disk error, schema mismatch, embedding provider error) |

**Output.** With `--reset`: `[index] reindexing <artifact-path>` per file then summary (N artifacts indexed, N edges built, elapsed time). With `--embeddings`: additional `[embed] <artifact-id>` lines and cost estimate. Without flags: index freshness status (last rebuild timestamp, artifact count, index size, embeddings coverage).

**Related.** Run `index --reset` after direct vault edits or failed compile. Run `index --reindex --embeddings` before first `search --mode semantic`. See `workflow-patterns.md` recipe 5 and recipe 6.

---

## stats

**Purpose.** Print vault counts broken down by artifact type, lifecycle stage, and freshness.

**Usage.**
```bash
meatywiki stats
```

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Print summary stats for the entire vault
meatywiki stats

# Typical post-compile check: stats after compiling
meatywiki compile --pending && meatywiki stats
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Stats printed |
| 1 | Index unavailable or vault not initialized |

**Output.** Human-readable table: artifact count by type, count by lifecycle stage (`raw`, `classified`, `compiled`, `reviewed`, `published`), count of artifacts updated in last 7d/30d/90d. No arguments or flags change the output format in V1.

**Related.** Run after every compile or index rebuild as a sanity check. For health beyond counts, use `doctor`.

---

## doctor

**Purpose.** Run a health check covering vault structure, index freshness, config validity, and drift detection.

**Usage.**
```bash
meatywiki doctor
```

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Run the full health check
meatywiki doctor

# Typical remediation sequence after detecting drift
meatywiki doctor
meatywiki index --reset
meatywiki doctor
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | All checks pass; vault healthy |
| 1 | One or more checks failed (drift detected, index stale, config invalid) |
| 2 | Vault not initialized or unreadable |

**Output.** Per-check result table: check name, status (`OK` / `WARN` / `FAIL`), description, remediation hint. Checks include: vault directory structure, `_meta/config.yaml` validity, index freshness (age since last rebuild), artifact count consistency (vault files vs. index rows), broken wikilinks count.

**Related.** Run after `index --reset` to confirm remediation. See `troubleshooting.md` for remediation steps keyed to specific `FAIL` check names.

---

## watch

**Purpose.** Watch `raw/` for new files and auto-ingest on file drop.

**Usage.**
```bash
meatywiki watch [--auto-compile]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--auto-compile` | off | After each auto-ingest, immediately run `compile --pending` for the new artifact |

**Examples.**
```bash
# Watch raw/ for new files and ingest them as they appear
meatywiki watch

# Watch and auto-compile each new file immediately after ingest
meatywiki watch --auto-compile

# Typical background usage (shell backgrounding is outside the CLI)
meatywiki watch --auto-compile
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Watcher stopped cleanly (SIGINT/SIGTERM) |
| 1 | Watcher startup failure (vault not initialized, watchdog error) |

**Output.** Streaming: `[watch] detected <filename>`, `[ingest] <artifact-id>`, and (with `--auto-compile`) `[compile] <artifact-id> → wiki/...`. Process runs until interrupted.

**Related.** `watch` is a "Should" priority in V1 (requires `watchdog` dependency). See `ingest` for the single-file equivalent. Use `compile --pending` for a batch compile after a watch session.

---

## promote

**Purpose.** Apply lifecycle promotion rules to advance artifact stages (`raw → classified → compiled → reviewed → published`).

**Usage.**
```bash
meatywiki promote [<artifact-id> ...] [--force]
```

**Required flags.** None.

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--force` | off | Bypass default promotion rules; promote regardless of `verification_status` or `lifecycle_stage` constraints |

**Examples.**
```bash
# Promote all artifacts that meet default promotion rules
meatywiki promote

# Promote a specific artifact
meatywiki promote art-01HXYZ

# Force-promote an artifact past a rule block
meatywiki promote art-01HXYZ --force

# Promote multiple specific artifacts
meatywiki promote art-01HXYZ art-01HABC
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Promotion applied; artifacts advanced |
| 1 | No artifacts eligible for promotion (without `--force`) or write error |
| 2 | Artifact ID not found |

**Output.** Per-artifact result: `[promote] <artifact-id>: <old-stage> → <new-stage>` or `[skip] <artifact-id>: <reason>`. With `--force`: skipped rules listed inline.

**Related.** Default promotion rules: artifacts in `lifecycle_stage: compiled` require `verification_status: human_review_complete` before advancing to `reviewed`. See `artifact-taxonomy.md` for full lifecycle rules. See `troubleshooting.md` for stuck-promotion remediation.

---

## serve

**Purpose.** Start the FastAPI thin CLI-parity wrapper service.

**Usage.**
```bash
meatywiki serve
```

**Required flags.** None.

**Optional flags.** None documented in V1.

**Examples.**
```bash
# Start the API service on the default host/port
meatywiki serve

# Typical usage: start service, then interact via HTTP
meatywiki serve
# In another shell: curl http://localhost:8000/stats
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Service stopped cleanly |
| 1 | Startup failure (port conflict, vault not initialized, FastAPI/uvicorn error) |

**Output.** Uvicorn startup logs followed by per-request access log lines. The service exposes CLI-parity endpoints (one endpoint per CLI command); no additional API surface beyond the 14 commands in V1.

**Related.** `serve` is a "Should" priority in V1; requires `fastapi` and `uvicorn` dependencies. For direct CLI use, no service is needed.

---

## lens

**Purpose.** Query computed lens scores (fidelity, freshness, clarity) for vault artifacts from the Portal lens-scoring backend. Read-only; scores are computed by the Portal service.

**Requires.** `PORTAL_DATABASE_URL`.

### lens list

**Usage.**
```bash
meatywiki lens list [--format {json|yaml|table}] [--freshness <age>]
```

**Optional flags.**
| Flag | Default | Notes |
|---|---|---|
| `--format {json\|yaml\|table}` | `table` | Output format |
| `--freshness <age>` | all | Filter to artifacts whose freshness score was computed within the given window (e.g., `7d`, `30d`) |

**Examples.**
```bash
# List all lens scores in table format
meatywiki lens list

# Show stale artifacts (freshness score computed in last 30 days)
meatywiki lens list --freshness 30d

# Machine-readable output
meatywiki lens list --format json
```

### lens get

**Usage.**
```bash
meatywiki lens get <artifact-id> [--format {json|yaml|table}]
```

**Examples.**
```bash
# Get lens scores for a specific artifact
meatywiki lens get art-01HXYZ

# JSON output for scripting
meatywiki lens get art-01HXYZ --format json
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Scores retrieved and printed |
| 1 | `PORTAL_DATABASE_URL` not set or DB error |
| 2 | Artifact ID not found or scores not yet computed |

**Output.** Table: artifact ID, fidelity score, freshness score, clarity score, computed-at timestamp. JSON/YAML are structured equivalents.

**Related.** Lens scores are computed by the Portal lens-scoring backend. Run Portal service and reconciler to populate scores. Use `--freshness` to triage stale artifacts before decision table evaluation.

---

## workflow

**Purpose.** Observe and control Portal workflow runs from the CLI. Read-only subcommands (`list`, `show`) do not require the arq worker. Mutation subcommands (`cancel`, `retry`, `bulk-action`) require the arq worker running.

**Requires.** `PORTAL_DATABASE_URL`. Mutations additionally require arq worker.

### workflow list

**Usage.**
```bash
meatywiki workflow list [--status <status>] [--format {json|yaml|table}]
```

**Examples.**
```bash
# List all workflow runs
meatywiki workflow list

# Filter to failed runs
meatywiki workflow list --status failed

# JSON output
meatywiki workflow list --format json
```

### workflow show

**Usage.**
```bash
meatywiki workflow show <run-id> [--format {json|yaml|table}]
```

**Examples.**
```bash
meatywiki workflow show wf-01HXYZ
meatywiki workflow show wf-01HXYZ --format json
```

### workflow cancel

**Usage.**
```bash
meatywiki workflow cancel <run-id>
```

**Examples.**
```bash
meatywiki workflow cancel wf-01HXYZ
```

### workflow retry

**Usage.**
```bash
meatywiki workflow retry <run-id>
```

**Examples.**
```bash
meatywiki workflow retry wf-01HFAIL
```

### workflow bulk-action

**Usage.**
```bash
meatywiki workflow bulk-action --action {cancel|retry} [--status <status>] [--confirm]
```

**Examples.**
```bash
# Retry all failed runs (with confirmation prompt)
meatywiki workflow bulk-action --action retry --status failed

# Cancel all pending runs without prompt
meatywiki workflow bulk-action --action cancel --status pending --confirm
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Operation completed |
| 1 | `PORTAL_DATABASE_URL` not set, DB error, or arq worker unavailable (mutations only) |
| 2 | Run ID not found |

**Output.** `list`: table of run ID, workflow type, status, started-at, elapsed. `show`: full run detail. `cancel`/`retry`: confirmation line with new status. `bulk-action`: summary of affected runs.

**Related.** `workflow list --status failed` before `workflow bulk-action --action retry` is the standard triage pattern. Read-only operations are safe without arq worker.

---

## decision

**Purpose.** Manage decision tables (rubric specs) and evaluate artifacts against them.

**Requires.** `PORTAL_DATABASE_URL`.

### decision list

**Usage.**
```bash
meatywiki decision list [--format {json|yaml|table}]
```

**Examples.**
```bash
meatywiki decision list
meatywiki decision list --format json
```

### decision show

**Usage.**
```bash
meatywiki decision show <table-id> [--format {json|yaml|table}]
```

**Examples.**
```bash
meatywiki decision show dt-01HXYZ
```

### decision create

**Usage.**
```bash
meatywiki decision create <spec.yaml>
```

The YAML spec must include a `name`, `description`, and `rules` list. Each rule has a `criterion`, `weight`, and optional `threshold`.

**Examples.**
```bash
meatywiki decision create triage-rubric.yaml
meatywiki decision create ~/rubrics/freshness-gate.yaml
```

### decision update

**Usage.**
```bash
meatywiki decision update <table-id> <spec.yaml>
```

**Examples.**
```bash
meatywiki decision update dt-01HXYZ updated-rubric.yaml
```

### decision rm

**Usage.**
```bash
meatywiki decision rm <table-id> [--confirm]
```

**Examples.**
```bash
meatywiki decision rm dt-01HXYZ --confirm
```

### decision apply

**Purpose.** Evaluate a vault artifact against a decision table rubric and return a structured result.

**Usage.**
```bash
meatywiki decision apply <table-id> <artifact-id> [--format {json|yaml|table}]
```

**Examples.**
```bash
# Evaluate an artifact against a triage rubric
meatywiki decision apply dt-01HXYZ art-01HABC

# JSON output for scripting
meatywiki decision apply dt-01HXYZ art-01HABC --format json
```

**Exit codes.**
| Code | Meaning |
|---|---|
| 0 | Operation completed |
| 1 | `PORTAL_DATABASE_URL` not set or DB error |
| 2 | Table ID or artifact ID not found |

**Output.** `apply`: per-criterion scores, overall result (pass/fail/review), and aggregate score. `list`: table of ID, name, rule count, last-updated. `create`/`update`: confirmation with table ID.

**Related.** Use `lens list --freshness <age>` to identify low-freshness artifacts before applying a decision table. See `workflow-patterns.md` Recipe 7 for the full triage workflow.

---

## Deferred commands

| Command | Track | Status |
|---|---|---|
| `register` | F1 | Not available in V1. SAM registry integration deferred. |
