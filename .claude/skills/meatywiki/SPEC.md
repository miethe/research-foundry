---
name: meatywiki-spec
description: Skill contract for MeatyWiki — coverage matrix, CLI version compatibility, update/deprecation protocol.
type: spec
skill_name: meatywiki
skill_version: v1.4
cli_version_range: "compilation-engine-v1 – v1.4 (pre-release; spec-driven)"
schema_version: 1
created: 2026-04-14
updated: 2026-06-04
oq_resolutions:
  OQ-1: "defer-scripts (V1 ships 0 shell scripts; wrapping single-command invocations yields <10% token savings vs. direct CLI call)"
  OQ-3: "option-b-per-file (per-file cli_version_range in references/)"
status: draft
engine_prd_ref: "MeatyBrain/App Ideas/Work/Agentic Control Plane/llm_wiki/compilation-engine/PRDs/compilation-engine-v1.md (additional working dir)"
skill_prd_ref: docs/project_plans/PRDs/features/meatywiki-skill-v1.md
context_ref: .claude/progress/meatywiki-compilation-engine/context.md
---

# MeatyWiki Skill Contract (SPEC.md)

## 1. Purpose

This file is the durable contract for the `.claude/skills/meatywiki/` skill. It defines which CLI surface the skill covers, maps each engine PRD acceptance criterion (A1–A15) to the skill file(s) that satisfy it, and provides the protocol for updating or deprecating skill content when the CLI evolves. It is an AI artifact — agent-facing, not human-documentation.

The skill teaches agents to drive the MeatyWiki compilation-engine V1 CLI (`ingest → classify → extract → compile → file-back → lint`) over an Obsidian-compatible markdown vault. It is spec-driven: the CLI does not exist at authorship time; all guidance derives from the engine PRD, canonical spec, and resolved open questions Q1–Q9.

---

## 2. Scope Boundary

### In Scope

- All 14 V1 CLI commands plus 3 new command groups shipped in v1.2: `lens`, `workflow`, `decision` (see §5 File Inventory; detailed in `references/command-reference.md`).
- File-first vault architecture: `raw/`, `wiki/`, `blog/`, `projects/`, `_meta/`, `_prompts/`.
- FTS5 full-text search, semantic search (`--mode semantic`), and hybrid search (`--mode hybrid`) via pgvector.
- 5 mandatory guardrails (FR-S12 + v1.2 additions): writes through `vault/writer.py`; `_meta/` engine-owned; semantic search requires embeddings index + `PORTAL_DATABASE_URL`; `schema_version: "1.0.0"` in all V1 frontmatter; `lens`/`workflow`/`decision` require `PORTAL_DATABASE_URL`.
- ~40 artifact subtypes across 5 workspaces (`wiki/` subdirs).
- SAM and CCDash no-op stub documentation (F1/F2 deferral markers only).
- Lens scoring (fidelity, freshness, clarity) via `lens get|list` (F5 promoted).
- Portal workflow observation and control via `workflow list|show|cancel|retry|bulk-action`.
- Decision table CRUD and artifact evaluation via `decision list|show|create|update|rm|apply`.

### Out of Scope (Deferred Features)

| Deferred | Track | Reason |
|---|---|---|
| SAM `register` command + live integration | F1 | `register` deferred to F1 (Q7 resolved); no-op stub only in V1 |
| CCDash live hook wiring | F2 | CCDash telemetry deferred to F2; no-op stub only in V1 |
| ~~Semantic search (`--semantic` flag, vector embeddings)~~ | ~~F3~~ | **Promoted — shipped in v1.2** via `search --mode semantic|hybrid` |
| Developer-artifact connectors (SkillMeat, GitHub, Claude configs) | F4 | Knowledge-domain connectors only in V1 (Q1 resolved); 9 connector types |
| ~~Workflow OS lens scoring (fidelity, reusability, sensitivity)~~ | ~~F5~~ | **Promoted — shipped in v1.2** via `lens get|list` |
| Portal / web UI integrations | F6 | Portal is a separate system (out of scope for engine V1) |
| Image OCR | Q3 | Images ingested as opaque blobs with optional captions; no OCR library in V1 (Q3 resolved) |
| `agent_visibility` enforcement | Q2 | Advisory metadata only; no enforcement code path in V1 (Q2 resolved) |
| Prompt-template auto-recompile | Q4 | Manual `compile --full --scope` only; no prompt-hash tracking (Q4 resolved) |
| DAG workflows / retry framework | — | Linear pipelines only in V1; no DAGs, no branching, no retry |

---

## 3. CLI Version Compatibility

The skill is authored against `compilation-engine-v1` (pre-release, spec-driven). It is valid for the CLI surface defined in engine PRD FR-1 through FR-22.

**Compatibility definition:**
- The skill is valid for a stated `cli_version_range` declared in this file's frontmatter and in each `references/` file's frontmatter.
- A **minor CLI bump** (new flags, new optional commands): update the affected `references/` file, bump its `cli_version_range`, and update the File Inventory row if line budgets shift.
- A **major CLI bump** (renamed commands, removed flags, breaking behavior change): mandatory full skill review triggered; all `references/` file `cli_version_range` fields must be audited; SPEC.md coverage matrix must be reconciled.
- When the real `compilation-engine-v1` ships, validate every command and flag in `references/command-reference.md` against the actual implementation. Discrepancies are breaking changes for skill purposes even if the CLI semver is still v1.

---

## 4. File Inventory

| File | Purpose | Max Lines | Owner Tag |
|---|---|---|---|
| `SKILL.md` | Entry point. Compile-loop overview, decision tree, top 5 recipes (inline), guardrails section, references/ pointer table. | 500 | ai-artifacts-engineer |
| `SPEC.md` (this file) | Skill contract. Coverage matrix A1–A15, CLI compat, file inventory, update/deprecation protocol, validation approach. | 1000 | ai-artifacts-engineer |
| `references/command-reference.md` | Full command map: 14 V1 commands + `migrate-edges` (v1.1) + `lens`, `workflow`, `decision` (v1.2), per-command flag tables, example invocations (≥2 per command), exit codes, output format. `#migrate-edges`, `#lens`, `#workflow`, `#decision`, and updated `#search`/`#index` sections are required. | 1100 | ai-artifacts-engineer |
| `references/workflow-patterns.md` | Workflow recipes (5 original + Recipe 6: semantic search + Recipe 7: decision table triage + Recipe 8: lens freshness check) with annotated command sequences (setup, command sequence, expected output, troubleshooting tip). | 900 | ai-artifacts-engineer |
| `references/vault-layout.md` | Annotated vault directory tree, per-directory ownership, `_meta/` boundary, Obsidian compatibility notes. | 800 | documentation-writer |
| `references/artifact-taxonomy.md` | ~40 artifact subtypes across 5 workspaces, frontmatter envelope fields, `schema_version: "1.0.0"` requirement. | 800 | ai-artifacts-engineer |
| `references/hook-policy.md` | SAM and CCDash no-op stub behavior, F1/F2 deferral markers, no-op stub interface contract. | 800 | ai-artifacts-engineer |
| `references/troubleshooting.md` | Common failure modes (vault drift, index corruption, LLM timeout, connector errors), remediation steps. | 800 | documentation-writer |
| `bootstrap/README.md` | Bootstrap-mode entry: when to trigger, B1–B5 step summary, guardrails, exit conditions. | 200 | ai-artifacts-engineer |
| `bootstrap/plan.md` | Step-by-step bootstrap orchestration: state detection, B1–B5 with exact commands, failure-mode table, B6 existing-repo onboarding route (detect → patterns → dry-run → sync → state doc → intent doc → optional consolidation check). | 650 | ai-artifacts-engineer |
| `bootstrap/sidecar-template.md` | Canonical template for `<project_root>/.claude/context/meatywiki.md` (sidecar). Contract: §13. | 200 | ai-artifacts-engineer |
| `bootstrap/wiki-spec-template.md` | Canonical template for `<vault>/wiki-spec.md` (project intent stub). Contract: §13. | 200 | ai-artifacts-engineer |
| `bootstrap/troubleshooting.md` | Bootstrap-specific recovery: sidecar drift, CLAUDE.md conflicts, partial-state recovery, re-bootstrap. | 300 | ai-artifacts-engineer |
| `README.md` | User-facing skill overview: bootstrap quickstart + day-to-day usage pointer. Not loaded by agents at runtime. | 200 | documentation-writer |
| `scripts/validate-vault.sh` | **Deferred (OQ-1 resolution)**. Would wrap `meatywiki doctor`; direct invocation is one CLI call. No V1 shell script shipped. | — | — |
| `scripts/dry-run-compile.sh` | **Deferred (OQ-1 resolution)**. Would wrap `meatywiki compile --dry-run`; direct invocation is one CLI call. No V1 shell script shipped. | — | — |

**Scripts Policy (OQ-1 resolution, 2026-04-14)**: V1 ships **0 shell scripts**. The two scripts proposed in the plan each wrap a single CLI command with no additional orchestration, yielding <10% token savings per invocation vs. `meatywiki doctor` or `meatywiki compile --dry-run` called directly. Shipping them would add a maintenance surface (shell quoting, PATH assumptions, `meatywiki` executable discovery) without meaningful agent benefit. Agents invoke the CLI commands directly. If a future workflow emerges that genuinely composes 3+ commands with branching logic and is invoked by agents frequently, revisit this decision and author under the skill's standard update protocol (§6).

---

## 5. Coverage Matrix (A1–A15)

Reconciled against engine PRD §18 "Overall Acceptance Criteria" on **2026-04-14** (audit log in §10). Every row cites a skill file that teaches agents how to satisfy the criterion or operate within its boundaries.

| A-ID | Engine-PRD Criterion (verbatim intent) | Skill file(s) that cover it | Status |
|---|---|---|---|
| A1 | **Vault initialization.** `meatywiki init <path>` creates the full vault layout (spec §4.2) with an initial `_meta/config.yaml`; `doctor` returns OK on a fresh vault. | `SKILL.md` §2, `references/command-reference.md#init` / `#doctor`, `references/vault-layout.md` | confirmed |
| A2 | **Frontmatter validation.** Files missing required frontmatter fields are refused by `vault/writer.py` with a Pydantic error; valid writes are atomic (temp + rename) and indexed in the same transaction. | `SKILL.md` §5 guardrail (a), `references/artifact-taxonomy.md` (required fields), `references/troubleshooting.md` (frontmatter validation failure mode) | confirmed |
| A3 | **Index round-trip.** `meatywiki index --reset` rebuilds index from N files so `count(artifacts) == N` with matching `file_hash`; subsequent `doctor` reports zero drift. | `references/command-reference.md#index`, `references/workflow-patterns.md` (index rebuild recipe), `references/troubleshooting.md` (vault drift / index corruption) | confirmed |
| A4 | **URL connector.** `meatywiki ingest <url> --compile` fetches, extracts, classifies as `raw_url/article`, writes `raw_url` artifact in `raw/urls/`, and produces at minimum a `source_summary`. Re-run is a no-op. | `references/command-reference.md#ingest` / `#compile`, `references/workflow-patterns.md` (Recipe 1), `references/artifact-taxonomy.md` (`raw_url` subtype) | confirmed |
| A5 | **PDF connector.** `meatywiki ingest paper.pdf --compile --domain ai` extracts via `pypdf`, classifies as `raw_upload/pdf`, produces `source_summary` + ≥1 `concept`. | `references/command-reference.md#ingest`, `references/workflow-patterns.md` (Recipe 2), `references/artifact-taxonomy.md` (`raw_upload`) | confirmed |
| A6 | **ChatGPT export connector.** `meatywiki ingest chatgpt-export.json --type chatgpt_export --compile` parses multi-turn structure, classifies as `raw_import/chatgpt_export`, produces conversation-aware `source_summary`. | `references/command-reference.md#ingest`, `references/artifact-taxonomy.md` (`raw_import` subtypes) | confirmed |
| A7 | **Entity resolution / dedup.** Three independent sources mentioning the same entity produce **one** `entity` artifact with all three source IDs in `source_refs`; `edges` records three `derived_from` + three `supports` edges. | `references/artifact-taxonomy.md` (entity compounding + edge types), `references/workflow-patterns.md` (compile loop recipe) | confirmed |
| A8 | **Compounding concept page.** Three sources touching the same concept yield a single `concept` artifact with body updated and `source_refs` accumulated; BM25 duplicate check does not flag. | `references/artifact-taxonomy.md` (concept compounding), `references/command-reference.md#lint` | confirmed |
| A9 | **Query with citations.** `meatywiki query "..."` returns answer with `[source: art_XXX]` citation per claim; `--file-back` writes answer as `synthesis` artifact in `wiki/syntheses/` with full `source_refs`. | `SKILL.md` §2/§4 (Recipe 4), `references/command-reference.md#query`, `references/workflow-patterns.md` | confirmed |
| A10 | **Synthesis.** `meatywiki synthesize --scope <scope> --type research_synthesis` produces `synthesis` artifact, detects cross-scope contradictions, emits `contradicts` edges where applicable. | `references/command-reference.md#synthesize`, `references/artifact-taxonomy.md` (synthesis type + `contradicts` edge) | confirmed |
| A11 | **Lint.** `lint --report` outputs JSON with per-check results for 5 deterministic + 2 semantic checks; `lint --checks broken-links --fix` repairs outdated wikilinks whose target file exists. | `references/command-reference.md#lint`, `references/workflow-patterns.md` (Recipe 3), `references/troubleshooting.md` | confirmed |
| A12 | **Multi-model routing.** With `_meta/config.yaml` routing `classify.provider: anthropic` and `compile.provider: openai`, a single run logs LLM calls to both providers attributed to correct stages. | `references/command-reference.md` (init/config section), `references/troubleshooting.md` (LLM timeout, provider switch remediation) | confirmed |
| A13 | **Idempotency.** Re-ingesting an unchanged source is a no-op (0 LLM calls, `cached` outcome); re-ingesting an edited source updates the artifact in-place (`updated` outcome) and marks derived artifacts `needs_recompile: true`; re-compile without `--full` is a no-op. | `SKILL.md` §2 (`--full` vs `--pending`), `references/command-reference.md#ingest` (outcome types: `created`/`cached`/`updated`), `references/command-reference.md#compile`, `references/troubleshooting.md` (idempotency failure mode) | confirmed |
| A14 | **Hooks interface.** `hooks/sam.py` and `hooks/ccdash.py` exist as no-op stubs that log intent on each lifecycle event; disabling hooks has zero effect on pipeline output. | `SKILL.md` §6 (deferred table), `references/hook-policy.md` (full policy + F1/F2 deferral), `references/artifact-taxonomy.md` (namespace reservation) | confirmed |
| A15 | **Service mode (Should).** `meatywiki serve` starts FastAPI exposing `POST /ingest`, `POST /compile`, `POST /query`, `GET /search` with CLI-parity JSON responses. | `references/command-reference.md#serve`, `SKILL.md` §2/§3 (serve command) | confirmed |
| v1.1-ME | **Edge backfill (`migrate-edges`).** `meatywiki migrate-edges --strategy {wikilink\|cooccurrence\|llm\|all} --vault PATH [--dry-run] [--report PATH] [--max-errors N] [--no-confirm]` backfills v1.1 edge types (REFERENCES, RELATES_TO, SUPERSEDES, CONTAINS) onto a vault that predates the linkage stages. `--strategy llm` and `--strategy all` invoke the LLM router (extract-tier model; cost estimate printed before any writes). `--dry-run` previews scope and cost without writing. `--report PATH` writes a JSON (default) or CSV report (extension-selected). `--max-errors N` (default 100; 0 = unlimited) aborts the current strategy phase after N per-artifact errors. `--no-confirm` skips the interactive cost-confirmation prompt. Exit 0 on success; `SystemExit(1)` on `MigrationAbortedError` (threshold exceeded). Existing edges are never overwritten (UNIQUE constraint violations silently skipped — safe to re-run). | `references/command-reference.md#migrate-edges` (to be authored), `references/workflow-patterns.md` (backfill recipe) | confirmed |
| v1.2-SS | **Semantic and hybrid search (`search --mode`).** `meatywiki search "<query>" --mode {semantic\|hybrid} [--type <type>] [--freshness <age>]` enables vector similarity search and FTS5+vector ranked merge. `--semantic` is a shorthand for `--mode semantic`. Requires `meatywiki index --reindex --embeddings` (one LLM embedding call per artifact) and `PORTAL_DATABASE_URL`. Each query invokes the embedding provider once. All existing `search` filters (`--type`, `--freshness`) apply in all modes. | `SKILL.md` §2/§3/§5 guardrail (c), `references/command-reference.md#search` / `#index`, `references/workflow-patterns.md` (Recipe 6) | confirmed |
| v1.2-LS | **Lens scoring (`lens get\|list`).** `meatywiki lens list [--format {json\|yaml\|table}] [--freshness <age>]` lists computed lens scores. `meatywiki lens get <artifact-id> [--format ...]` shows scores for a specific artifact. Scores: fidelity, freshness, clarity. Requires `PORTAL_DATABASE_URL`. Scores are computed by the Portal lens-scoring backend; CLI is read-only. | `SKILL.md` §2/§3/§5 guardrail (e), `references/command-reference.md#lens`, `references/workflow-patterns.md` (Recipe 7/8) | confirmed |
| v1.2-WF | **Workflow observation and control (`workflow list\|show\|cancel\|retry\|bulk-action`).** `meatywiki workflow list` and `workflow show <run-id>` are read-only and do not require the arq worker. `workflow cancel <run-id>`, `workflow retry <run-id>`, and `workflow bulk-action` are mutations that require the arq worker running. Requires `PORTAL_DATABASE_URL`. | `SKILL.md` §2/§3/§5 guardrail (e), `references/command-reference.md#workflow` | confirmed |
| v1.2-DT | **Decision tables (`decision list\|show\|create\|update\|rm\|apply`).** `decision create <spec.yaml>` and `decision update <table-id> <spec.yaml>` accept a YAML rule spec. `decision apply <table-id> <artifact-id>` evaluates the artifact against the rubric and returns a structured result. All subcommands require `PORTAL_DATABASE_URL`. | `SKILL.md` §2/§3/§5 guardrail (e), `references/command-reference.md#decision`, `references/workflow-patterns.md` (Recipe 7) | confirmed |
| v1.3-SD | **Source-directory ingest (`ingest --source-dir`).** `meatywiki ingest --source-dir <path> [--project <id>] [--pattern <glob>] [--dry-run]` ingests plan documents from an external project directory. Sets `is_derived: true` on every artifact created; preserves source path and SHA-256 content hash in envelope fields. `--dry-run` previews matched files and artifact count without writing. `--project <id>` associates artifacts with a named project scope. `--pattern <glob>` filters matched files (default: `**/*.md`). | `references/command-reference.md#ingest`, `references/artifact-taxonomy.md` (`is_derived` field, source-path preservation), `references/workflow-patterns.md` (cross-project recipe), `SPEC.md §16` | confirmed |
| v1.3-SY | **Project sync (`sync`).** `meatywiki sync [--project <id>] [--dry-run] [--report]` re-ingests changed files from configured project directories using SHA-256 hash-based change detection. Only files whose content hash has changed since last ingest are re-processed (no LLM calls for unchanged files). `--project <id>` limits sync to a single project. `--dry-run` reports stale files without re-ingesting. `--report` prints a per-project staleness table (artifact id, source path, last-ingested hash vs. current hash). | `references/command-reference.md#sync`, `references/workflow-patterns.md` (sync recipe), `SPEC.md §16` | confirmed |
| v1.3-AM | **AI memory ingest (`ingest --memory`).** `meatywiki ingest <export-file> --memory [--type {chatgpt_export\|perplexity_export\|gemini_export}]` extracts concept, evidence, and glossary artifacts from AI chat exports (ChatGPT JSON, Perplexity JSON, Gemini JSON). Tags all outputs with `source_type: ai_memory`. Deduplicates on repeated ingest: re-running against an unchanged export is a no-op; re-running against an updated export merges new turns into existing artifacts (`updated` outcome). Connector dispatch order preserved: `import_chatgpt` / `import_perplexity` / `import_gemini` run before `UploadFileConnector` catch-all. | `references/command-reference.md#ingest`, `references/artifact-taxonomy.md` (`ai_memory` source_type, raw_import subtypes), `references/workflow-patterns.md` (AI memory ingest recipe) | confirmed |
| v1.3-CP | **Cross-project query (`query --cross-project`).** `meatywiki query "<text>" --cross-project [other query flags]` removes the per-project FTS5 filter and searches all indexed artifacts regardless of project scope. Each result in the response is annotated with `project_id` and `is_derived` status so callers can distinguish local vs. derived artifacts. All existing `query` flags (`--file-back`, `--scope`, `--mode`) remain composable. | `SKILL.md` §2/§3, `references/command-reference.md#query`, `references/workflow-patterns.md` (cross-project recipe), `SPEC.md §16` | confirmed |
| v1.3-PD | **Auto-detect project boundaries (`projects detect`).** `meatywiki projects detect [ROOT_DIR] [--depth N] [--apply]` scans a directory tree up to DEPTH levels for project boundary markers (CLAUDE.md, pyproject.toml). Dry-run by default: prints a YAML block of proposed `project_directories` entries to stdout. `--apply` merges detected entries into `_meta/config.yaml`, skipping paths already present. | `references/command-reference.md#projects`, `references/workflow-patterns.md` (projects detection recipe), `SPEC.md §16` | confirmed |
| v1.3-WD | **Real-time project watching (`projects watch`).** `meatywiki projects watch [--debounce N]` monitors all enabled `project_directories` from `_meta/config.yaml` for file-system changes. After a quiet period following the last event, triggers sync for the affected directory only. `.git/` paths are always ignored; vault root is excluded from events. Complements `sync` with continuous observation vs. batch detection. Note: the top-level `meatywiki watch` command monitors the vault itself for re-indexing only; `projects watch` is the correct command for cross-project sync automation. | `references/command-reference.md#projects`, `references/workflow-patterns.md`, `SPEC.md §16` | confirmed |
| v1.4-CL | **Duplicate artifact consolidation (`consolidate`).** `meatywiki consolidate [--dry-run] [--auto] [--scope TYPE,...] [--since DATETIME] [--min-confidence FLOAT] [--output FILE]` finds duplicate `entity` and `glossary_term` artifacts and optionally auto-merges safe pairs. Default mode is non-mutating (dry-run). `--auto` executes scoped, guarded auto-band merges. `--scope` restricts to `entity`, `glossary_term`, or both. `--min-confidence` (default 0.65) gates which candidates appear in the report. `--output` writes a JSON or Markdown report. LLM cost: classification-tier calls per candidate pair; `--dry-run` incurs zero LLM calls. | `SPEC.md §16`, `references/command-reference.md#consolidate` | confirmed |
| v1.4-CT | **LLM cost telemetry (`cost report`).** `meatywiki cost report [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--format {table\|json}] [--vault-size] [--db FILE]` reads the cost log at `<vault>/_meta/cost_log.db` and renders per-(stage, model) call counts, p50/p95 cost estimates, and a last-30-day total. `--vault-size` adds an Artifacts column. `--db` overrides the default cost log path. Zero LLM calls. | `SPEC.md §16`, `references/command-reference.md#cost` | confirmed |
| v1.4-EV | **Vault embedding generation (`embed-vault`).** `meatywiki embed-vault [--vault PATH] [--batch-size N] [--force]` generates or refreshes artifact embeddings using file-hash idempotency — artifacts whose `file_hash` is unchanged since last embed run are skipped (0 LLM embedding calls). `--force` re-embeds all artifacts regardless of hash. `--batch-size N` controls per-batch size (default 50). Requires `PORTAL_DATABASE_URL` and an embedding-capable provider in `_meta/config.yaml`. Replaces the `index --embeddings` approach for large vault refresh. | `references/command-reference.md#embed-vault`, `references/workflow-patterns.md` | confirmed |
| v1.4-EP | **Edge evidence provenance (`edges --show-evidence`).** `meatywiki edges --show-evidence <artifact-id> [--format {json\|table}]` displays per-edge evidence provenance for a specific artifact: source passages, cosine similarity scores (for embedding-derived edges), and strategy that generated each edge. Enables auditability of the edge graph. | `references/command-reference.md#edges`, `references/artifact-taxonomy.md` (edge types) | confirmed |
| v1.4-MF | **Batch synthesis flags (`migrate-edges` extensions).** `meatywiki migrate-edges --batch-size N` sets the number of artifacts processed per LLM synthesis batch (default 5). `meatywiki migrate-edges --no-prefilter` disables the embedding cosine pre-filter that normally gates which artifact pairs are forwarded to LLM synthesis (use with caution — increases LLM calls). `meatywiki migrate-edges --include-entity-glossary` extends LLM synthesis to include `entity` and `glossary_term` artifact types (default: `concept`, `summary`, `synthesis` only). All three flags are backward-compatible additions to the existing `migrate-edges` contract (v1.1-ME). | `references/command-reference.md#migrate-edges`, `references/workflow-patterns.md` | confirmed |

**Cross-cutting invariants** (not numbered criteria but enforced by guardrails; the skill must teach these):

| Invariant | Source | Skill file(s) |
|---|---|---|
| ~~FTS5-only search (`--semantic` deferred F3)~~ | ~~PRD FR-22 (Q5 resolved)~~ | **Superseded by v1.2-SS** — semantic/hybrid search now available |
| Semantic search requires embeddings index + `PORTAL_DATABASE_URL` | v1.2-SS | `SKILL.md` §5 guardrail (c), `references/command-reference.md#search` / `#index` |
| `lens`, `workflow`, `decision` require `PORTAL_DATABASE_URL`; mutations need arq worker | v1.2-LS/WF/DT | `SKILL.md` §5 guardrail (e), `references/command-reference.md#lens` / `#workflow` / `#decision` |
| `schema_version: "1.0.0"` mandatory in all V1 frontmatter | PRD §6, context.md migration plan | `SKILL.md` §5 guardrail (d), `references/artifact-taxonomy.md` §Frontmatter Envelope |
| `agent_visibility` advisory (no enforcement) | Context Q2 | `references/artifact-taxonomy.md` (envelope), `references/hook-policy.md` |
| Image OCR not in V1 (opaque blobs + optional caption) | Context Q3 | `references/artifact-taxonomy.md` (`raw_upload/image`) |
| `_meta/` engine-owned | Spec §4.1 | `SKILL.md` §5 guardrail (b), `references/vault-layout.md` |
| 9 V1 knowledge-domain connectors only (dev-artifact connectors `[deferred: F4]`) | PRD Q1, §8 | `references/hook-policy.md`, `references/artifact-taxonomy.md` |

---

## 6. Update / Enhancement Protocol

When the CLI changes (new flag, renamed command, removed behavior, or the real CLI ships and diverges from the spec), follow these steps:

1. **Identify the changed surface.** Diff the CLI release notes or `compilation-engine-v1.md` changes against the current `references/command-reference.md`. Note the command name, flag name, and change type (added / changed / removed).

2. **Locate affected skill files.** Cross-reference the change against:
   - The File Inventory table (§4) to identify which `references/` file owns the command or domain.
   - The Coverage Matrix (§5) to identify which A-ID rows cite that file — those rows may need wording updates.

3. **Update the reference file.** Edit the affected `references/` file. For added flags: add a row to the flag table and ≥1 example invocation. For changed behavior: update the example and expected output. For removed commands/flags: apply the Deprecation Policy (§7) — do not delete immediately.

4. **Bump `cli_version_range` frontmatter.** Update the `cli_version_range` field in the modified `references/` file's YAML frontmatter to reflect the new valid range (e.g., `"compilation-engine-v1.0.0 – v1.2.0"`).

5. **Update SPEC.md.** If a file's line count changed materially (>10%), update the File Inventory row's Max Lines field. If a Coverage Matrix row's skill-file mapping changed, update the row. Bump `updated` date in this file's frontmatter.

6. **Run skill-builder validation.** Confirm SKILL.md is still <500 lines, all `references/` files are <800 lines, frontmatter schema is valid, and structural checks pass.

7. **If it is a major CLI version bump:** trigger a full skill review — audit every row of the Coverage Matrix, re-verify all 14 command entries in `command-reference.md`, and update `cli_version_range` in SPEC.md frontmatter and all `references/` file frontmatters.

---

## 7. Deprecation Policy

**Removed command or flag:**
1. Mark the affected content `[deprecated: engine v{X.Y}]` inline (e.g., in the flag table row or command section header).
2. Keep the deprecated content through one minor CLI version bump so agents on older CLI versions can still find it.
3. At the next minor CLI version bump, delete the deprecated content and remove the `[deprecated]` marker.

**Deferred features (F1–F6):**
- Content for deferred features must carry `[deferred: F{N}]` label in all skill files.
- Deferred content contains no instructional guidance — only a statement that the feature is deferred and which F-track it belongs to.
- When a deferred feature is promoted (e.g., F1 ships SAM integration): remove the `[deferred: F1]` label, add full documentation in the appropriate `references/` file, update the Coverage Matrix row, and follow the Update Protocol above.
- Deferred labels are never removed without a corresponding promotion of the feature into scope.

**Entire skill deprecation:**
- If the MeatyWiki CLI is replaced or substantially rewritten (major version), the skill directory is archived at `.claude/skills/meatywiki-v1-archived/` and a new skill is created for the new version. The archived skill carries `status: deprecated` in its frontmatter.

---

## 8. Validation Approach

Validation is performed at Phase 4 of the implementation plan and again on any CLI version bump.

**(a) Skill-builder structural checks**
- `SKILL.md` present at `.claude/skills/meatywiki/SKILL.md`.
- `SKILL.md` < 500 lines (`wc -l`).
- `SKILL.md` frontmatter schema valid: `name`, `description` fields present and non-empty.
- `references/` directory exists; all six reference files present.
- Each `references/` file < 800 lines.
- Script files (if present) follow naming convention and are executable.

**(b) Coverage matrix audit**
- All 15 rows (A1–A15) cite ≥1 skill file.
- No row cites a file not in the File Inventory (§4).
- All rows have `status: draft` (until engine PRD surfaces and wording is confirmed) or `status: confirmed` (post-reconciliation).

**(c) Command-flag audit**
- Cross-reference every command entry in `references/command-reference.md` against PRD FR-1 (command list) and FR-2 through FR-22 (per-command behavior).
- Currently: cross-reference against skill PRD §13 (V1 CLI command surface reference table) since engine PRD is not present in this repo.
- Confirm all 14 V1 commands are present; confirm documented flags match skill PRD §13 flag listings (`compile --pending/--scope/--dry-run/--full`, `query --file-back/--scope`, `lint --fix/--report/--checks`, `search --type/--freshness/--mode/--semantic`, `graph --depth/--format`, `index --reset/--reindex/--embeddings`, `watch --auto-compile`).
- **v1.1 addition — `migrate-edges`**: Confirm `#migrate-edges` section exists in `command-reference.md` with all six flags documented: `--strategy {wikilink|cooccurrence|llm|all}` (required), `--vault PATH` (optional, overrides env/cwd), `--dry-run` (flag), `--report PATH` (optional, extension-selects JSON/CSV), `--max-errors N` (int, default 100; 0 = unlimited), `--no-confirm` (flag). Confirm two exit codes documented: 0 (success) and `SystemExit(1)` (`MigrationAbortedError` / threshold exceeded). Confirm LLM cost implications noted for `llm` and `all` strategies.
- **v1.2 additions**: Confirm `#lens`, `#workflow`, `#decision` sections exist in `command-reference.md`. Confirm `#search` documents `--mode {semantic|hybrid}` and `--semantic` shorthand. Confirm `#index` documents `--reindex` and `--embeddings`. Confirm `PORTAL_DATABASE_URL` requirement is noted for all four new surfaces.

**(d) Deferred-feature audit**
- Search all skill files for references to: `register`, SkillMeat connector, GitHub connector, Claude config connector, Portal web UI, OCR.
- Confirm each occurrence carries `[deferred: F{N}]` label and contains no instructional guidance.
- Search for `F1`, `F2`, `F4`, `F6` labels; confirm each is paired with `[deferred: F{N}]` syntax.
- Confirm `--semantic`, lens scoring, and workflow observation are documented as **active** (not deferred). F3 and F5 are promoted; any `[deferred: F3]` or `[deferred: F5]` remaining in skill files is a bug.

**(e) Guardrail completeness check**
- Confirm SKILL.md guardrails section explicitly states all 5 required guards:
  - (a) All writes go through `vault/writer.py`
  - (b) `_meta/` is engine-owned; do not manually edit `meatywiki.db`, `compile_state.json`, `config.yaml`
  - (c) Semantic search (`--mode semantic|hybrid`) requires embeddings index + `PORTAL_DATABASE_URL`; fall back to FTS5 when not indexed
  - (d) `schema_version: "1.0.0"` must appear in all V1 artifact frontmatter
  - (e) `lens`, `workflow`, `decision` require `PORTAL_DATABASE_URL`; mutations need arq worker

---

## 9. Version Management

**Chosen strategy: option (b) — per-file `cli_version_range` in each `references/` file.**

Each `references/` file carries its own `cli_version_range` field in its YAML frontmatter, scoped to the commands and behaviors it documents. The `cli_version_range` in this file's frontmatter is a roll-up representing the minimum compatible engine version across all `references/` files — it tightens only when every references file has migrated. This enables targeted updates: when a single command ships a breaking change, only the affected file's range and frontmatter need updating, without forcing a whole-skill version bump.

**Per-file frontmatter contract:**

- Each `references/*.md` file MUST declare `cli_version_range: "<spec>"` in its frontmatter, where `<spec>` uses the form `">=<MAJOR.MINOR.PATCH>,<<MAJOR.MINOR.PATCH>"` (PEP 440 / semver range syntax).
- During V1 pre-release authorship, all files declare `cli_version_range: "compilation-engine-v1 (pre-release)"` as a literal string; semver ranges are adopted once the engine ships a tagged release.
- `SPEC.md` frontmatter `cli_version_range` is the intersection (tightest compatible) of all references/ files; bump it only when every references file has migrated.

**Breaking vs. additive vs. patch changes:**

| Change type | Examples | Version impact |
|---|---|---|
| Breaking | Command renamed/removed; flag renamed/removed; default behavior changed; guardrail rule inverted | Bump engine MAJOR → re-run skill audit; update affected references file + its `cli_version_range`; possibly bump `SKILL.md` `skill_version` major |
| Additive | New flag with backward-compatible default; new command added; new artifact subtype; new recipe pattern | Bump engine MINOR → extend affected references file's upper bound in `cli_version_range`; `skill_version` MINOR bump |
| Patch | Clarified docs, error-message wording, non-semantic output format tweak | Bump engine PATCH → usually no skill change required; document in skill commit only |

**When to bump (procedure):**

1. Engine releases new version → grep `.claude/skills/meatywiki/` for affected command/flag mentions.
2. For each hit, update the references file's `cli_version_range` to include the new version (extending upper bound for additive; raising lower bound for breaking).
3. Recompute `SPEC.md` frontmatter `cli_version_range` as the intersection; update if it tightened.
4. If any breaking changes, bump `SKILL.md` frontmatter `skill_version` (MAJOR for breaking, MINOR for additive); re-run skill-builder validation.

**Note on option (c) CHANGELOG rejection:** This strategy deliberately omits a `CHANGELOG.md` (option c). The per-file `cli_version_range` fields combined with git history provide the necessary audit trail without adding a separate sync surface. If a future skill version identifies a concrete need, a CHANGELOG can be added without invalidating this strategy.

---

## 10. Phase 4 Audit Log

**Audit date:** 2026-04-14
**Auditor:** /dev:execute-phase orchestrator (Opus 4.6)
**Engine PRD:** `/Users/miethe/Documents/Other/PKM/MeatyBrain/App Ideas/Work/Agentic Control Plane/llm_wiki/compilation-engine/PRDs/compilation-engine-v1.md` (795 lines; per-capability A1–A15 in §18)

### (a) Coverage matrix reconciliation

Reconciled §5 of this SPEC.md against engine PRD §18 on 2026-04-14. The pre-audit matrix contained *inferred* criteria (the PRD was not previously accessible to the skill). All 15 rows were rewritten against the verbatim per-capability acceptance criteria:

- **15/15 A-IDs** present with specific skill-file citations.
- **0/15** remain in `draft` status; all rows marked `confirmed`.
- Cross-cutting invariants (FTS5-only, `schema_version: "1.0.0"`, agent_visibility advisory, `_meta/` engine-owned, image-as-opaque-blob, 9 V1 connectors) added as a separate table; each cites the guardrail it enforces and the skill file(s) that teach it.

### (b) Command-flag audit (PRD FR-1 vs. `command-reference.md`)

PRD FR-1 command list: `init`, `ingest`, `compile`, `query`, `synthesize`, `lint`, `search`, `graph`, `index`, `stats`, `doctor`, `watch`, `promote` (Must) + `serve` (Should via FR-21). `register` is `[deferred: F1]` per Q7 and is not present.

- **14/14 V1 commands documented** in `references/command-reference.md` and surfaced in `SKILL.md` §3 Command Map.
- **0 invented commands** (scanned for any command word not in FR-1/FR-21).
- **0 invented flags** (cross-checked `--pending`, `--scope`, `--dry-run`, `--full`, `--file-back`, `--fix`, `--report`, `--checks`, `--type`, `--freshness`, `--depth`, `--format`, `--reset`, `--auto-compile`, `--force`, `--compile`, `--domain`, `--semantic` (absent as expected — F3)).
- `register` explicitly marked `[deferred: F1]` in `SKILL.md` §2 decision tree and §6 deferred table.

### (c) Deferred-feature audit (Phase 4, 2026-04-14)

Note: F3 and F5 have since been promoted in v1.2. See §12 v1.2 audit log.

| Mention | Location | Label (at audit time) |
|---|---|---|
| `register` command | `SKILL.md` §2 | `[deferred: F1]` |
| SAM hook live integration | `references/hook-policy.md` §4 | `[deferred: F1]` |
| CCDash hook live integration | `references/hook-policy.md` §5 | `[deferred: F2]` |
| `--semantic` flag / vector query | `SKILL.md` §5(c), `references/command-reference.md` (query/search) | `[deferred: F3]` → **promoted v1.2** |
| SkillMeat / GitHub / Claude-config connectors | `references/hook-policy.md` §2/§7 | `[deferred: F4]` |
| Workflow OS lens scoring | `SKILL.md` §6 | `[deferred: F5]` → **promoted v1.2** |
| Portal / web UI | `SKILL.md` §6, `SPEC.md` §2 | `[deferred: F6]` |
| Image OCR | `SKILL.md` §6, `references/artifact-taxonomy.md` (`raw_upload/image`) | non-F (Q3 resolved) |
| `agent_visibility` enforcement | `references/artifact-taxonomy.md`, `references/hook-policy.md` | non-F (Q2 resolved) |

### (d) Structural checks (skill-builder parity)

- `SKILL.md`: 162 lines (<500 ✓); frontmatter: `name`, `description`, `schema_version`, `skill_version`, `cli_version_range`, `spec_ref` present.
- All 6 references/ files < 800 lines (max: `command-reference.md` = 592).
- All 6 references/ files declare the required per-file frontmatter (`name`, `description`, `type`, `skill_name`, `cli_version_range`, `schema_version`).
- `scripts/` contains only `.gitkeep` (0 scripts shipped; OQ-1 resolution confirmed).
- 4/4 guardrails (a)–(d) present in `SKILL.md` §5.

### (e) OQ resolutions

| OQ | Status | Resolution |
|---|---|---|
| OQ-1 (scripts) | resolved 2026-04-14 | Defer — ship 0 scripts in V1 (see §4 Scripts Policy) |
| OQ-2 (test fixtures) | deferred | F2 skill version (no agent test-vault use case in V1) |
| OQ-3 (versioning) | resolved 2026-04-14 | Option (b): per-file `cli_version_range` (see §9) |

### (f) Residual risks / notes for future audit

- **Draft SPEC status.** The `status: draft` frontmatter remains until the engine CLI ships and commands/flags are validated against the real implementation. Promote to `status: stable` at that time.
- **Line count drift.** `command-reference.md` at 592 lines is the closest to the 800-line ceiling (now bumped to 900 to accommodate `migrate-edges`); monitor on any CLI v1.x flag expansion.
- **Minor inconsistency fixed.** Three references (command-reference, vault-layout, workflow-patterns) used `parent_skill` where the Phase-3 references used `skill_name`. Normalized to `skill_name` on 2026-04-14 for consistency with SPEC.md §9 contract.

---

## 11. v1.1 Audit Log (migrate-edges CLI contract)

**Audit date:** 2026-04-28
**Auditor:** ai-artifacts-engineer (P6-06)
**Engine version:** compilation-engine-v1.1 (entity-linkage; branch `feat/compilation-engine-v1.1`)

### Decision: full contract section (not N/A)

`migrate-edges` is a new top-level CLI command added in v1.1, not a wrapper around an existing command. It exposes a distinct flag surface, output format, and exit-code contract. The SPEC documents commands by name in the Coverage Matrix (§5) and points to `references/command-reference.md` for per-command flag tables. A new Coverage Matrix row (`v1.1-ME`) has been added and the File Inventory row for `command-reference.md` updated to require a `#migrate-edges` section (§4). This is an **additive CLI bump** per the version management table (§9): new command, backward-compatible defaults.

### Verified flag surface (from `src/meatywiki/cli.py` lines 1053–1309)

| Flag | Type | Default | Required | Notes |
|---|---|---|---|---|
| `--strategy` | Choice: `wikilink\|cooccurrence\|llm\|all` | — | yes | Selects edge-backfill stage(s) |
| `--vault` / `vault_flag` | Path (dir, need-not-exist) | None (resolves via env/cwd) | no | Overrides env `MEATYWIKI_VAULT_ROOT` and cwd resolution |
| `--dry-run` | Flag (bool) | False | no | Prints report + cost estimate; no DB writes |
| `--report` / `report_path` | Path (file) | None | no | Extension selects format: `.json` (default) or `.csv` |
| `--max-errors` / `max_errors` | int | 100 (shown in help) | no | Abort after N per-artifact errors; 0 = unlimited |
| `--no-confirm` / `no_confirm` | Flag (bool) | False | no | Skips interactive LLM cost-confirmation prompt |

**Exit codes (verified):**
- `0` — successful migration (or dry-run preview)
- `SystemExit(1)` — `MigrationAbortedError` raised (threshold exceeded); partial report still emitted
- Click `ClickException` (non-zero, Click-managed) — `ValueError` or unhandled `Exception`

**LLM cost behavior (verified):**
- Triggered when `strategy in {"llm", "all"}`
- `estimate_llm_cost()` called before any writes; cost range printed to stderr
- Interactive `click.confirm()` prompt unless `--dry-run` or `--no-confirm`
- Model tier used: `ModelPurpose.EXTRACT` (Sonnet-tier per router config)

**Output (verified):**
- Always emits JSON report to stdout via `format_report(report, fmt="json")`
- If `--report PATH` provided: also writes JSON or CSV to file (format inferred from extension via `_infer_fmt()`)
- Dry-run: emits `[DRY RUN] migrate-edges --strategy ...` prefix line, then report

**Edge types backfilled (verified, from docstring):**
`REFERENCES`, `RELATES_TO`, `SUPERSEDES`, `CONTAINS` — existing edges never overwritten (UNIQUE constraint violations silently skipped; safe to re-run).

### Spec drift observed

**None.** The task prompt listed `--vault PATH` as a required positional-style argument; the actual implementation makes it optional (`default=None`), falling back to env/cwd vault resolution (consistent with all other commands). The contract row in §5 and the flag table above reflect the actual implementation.

### Files requiring follow-up

- `references/command-reference.md` — **needs a `#migrate-edges` section** authored (per §4 File Inventory update). This is out of scope for P6-06 (SPEC-only task) but is a known gap; the §8(c) audit check will catch it at the next validation pass.
- `references/workflow-patterns.md` — may benefit from a backfill recipe (Recipe 6: edge backfill); not required for P6-06.

### cli_version_range update

`SPEC.md` frontmatter `cli_version_range` extended from `"compilation-engine-v1 (pre-release; spec-driven)"` to `"compilation-engine-v1 – v1.1 (pre-release; spec-driven)"` — additive bump per §9 procedure.

---

## 12. v1.2 Audit Log (F3/F5 promotions + new command groups)

**Audit date:** 2026-05-07
**Auditor:** ai-artifacts-engineer
**Engine version:** compilation-engine-v1.2 (branch `harden/intent-alignment-analysis`)

### Decision: additive CLI bump

Four new CLI surfaces shipped in v1.2 (`search --mode`, `index --embeddings`, `lens`, `workflow`, `decision`). This is an **additive CLI bump** per §9: new commands and flags with backward-compatible defaults. F3 (semantic search) and F5 (lens scoring) are promoted from deferred to active.

### Changes applied

| File | Change |
|---|---|
| `SKILL.md` | Frontmatter: bumped `skill_version` 0.1.0-draft → 0.2.0, `cli_version_range` extended to v1.2, `description` adds new trigger keywords. Decision tree: added `search --mode`, `index --reindex --embeddings`, `lens`, `workflow`, `decision` rows. Command map: updated `search`, `index` entries; added `lens`, `workflow`, `decision`. Recipes: 5 → 7 (added semantic search + decision triage). Guardrail (c): replaced FTS5-only restriction with embeddings prereq. New guardrail (e): `lens`/`workflow`/`decision` require `PORTAL_DATABASE_URL`. Deferred table: removed F3/F5 rows; added promoted note. |
| `SPEC.md` | Scope boundary: updated In Scope, struck-through F3/F5 deferred rows with promoted note. File Inventory: `command-reference.md` max lines → 1100; `workflow-patterns.md` max lines → 900 + updated description. Coverage matrix: added v1.2-SS, v1.2-LS, v1.2-WF, v1.2-DT rows. Cross-cutting invariants: replaced FTS5-only row with semantic prereq + new guardrail (e) rows. §8(c)/(d)/(e): updated audit checks. Frontmatter `cli_version_range` → v1.2, `updated` → 2026-05-07. |
| `references/command-reference.md` | `search`: added `--mode` and `--semantic` flags; removed `[deferred: F3]` marker. `index`: added `--reindex` and `--embeddings` flags. Added `#lens`, `#workflow`, `#decision` sections. Removed deferred-commands references to F3/F5. |
| `references/workflow-patterns.md` | Added Recipe 6 (semantic search), Recipe 7 (decision table triage), Recipe 8 (lens freshness check). Updated Recipe 4 to remove FTS5-only restriction note. |

### Spec drift observed

None. All four new command groups confirmed in shipped CLI per git log (commits `8703760`, `2eb6983`, `b5d0851`, and the workflow/decision commits on branch `harden/intent-alignment-analysis`).

### cli_version_range update

`SPEC.md` frontmatter `cli_version_range` extended to `"compilation-engine-v1 – v1.2 (pre-release; spec-driven)"` — additive bump per §9 procedure. `SKILL.md` `skill_version` bumped to `0.2.0` (additive per §9 version management table).

---

## 13. Bootstrap Contract

**Added:** 2026-05-15 (skill v0.3.0)
**Scope:** Bootstrap mode — one-shot orchestration that wires MeatyWiki into a target project.

### 13.1 Posture

The MeatyWiki skill has two postures:

- **Driver posture** (default, §1–§12 of SKILL.md): agents invoke `meatywiki` CLI commands against an already-bootstrapped project.
- **Bootstrap posture** (§1.5 of SKILL.md, `bootstrap/`): one-shot setup of a fresh project. Mutates files outside the vault (`.claude/context/meatywiki.md`, root `CLAUDE.md`, `<vault>/wiki-spec.md`).

Bootstrap files MUST live under `bootstrap/` (progressive disclosure). SKILL.md MUST carry only a minimal §1.5 pointer; it MUST NOT inline bootstrap steps.

### 13.2 Bootstrap Coverage Matrix (B1–B6)

| B-ID | Bootstrap step | Skill file(s) | Mutates outside vault? | Diff-confirm? |
|---|---|---|---|---|
| B1 | Resolve vault path (detect existing or elicit) | `bootstrap/plan.md` §B1 | No | n/a |
| B2 | `meatywiki init` + initial `_meta/config.yaml` | `bootstrap/plan.md` §B2 | No (vault is engine territory) | No (engine call) |
| B3 | Write `<project_root>/.claude/context/meatywiki.md` sidecar | `bootstrap/plan.md` §B3, `bootstrap/sidecar-template.md` | **Yes** | **Yes** (on conflict; first-write may use one-line confirm) |
| B4 | Append managed `<!-- meatywiki:start --> ... <!-- meatywiki:end -->` block to root `CLAUDE.md` with `@.claude/context/meatywiki.md` pointer | `bootstrap/plan.md` §B4 | **Yes** | **Yes (always)** |
| B5 | Write `<vault>/wiki-spec.md` from template | `bootstrap/plan.md` §B5, `bootstrap/wiki-spec-template.md` | No (vault file) | Only on conflict |
| B6 | Onboard existing repo: detect + register → conservative patterns → dry-run → sync → state doc → intent doc → optional consolidation check | `bootstrap/plan.md` §B6-1..B6-7 | No (writes derived artifacts into vault via engine; edits `_meta/config.yaml` via `projects detect --apply`) | Dry-run confirmation at B6-3; consolidation review at B6-7 |

### 13.3 Invariants (bootstrap-specific)

| Invariant | Enforced by |
|---|---|
| Bootstrap NEVER creates per-project `.claude/skills/meatywiki/` shims | `bootstrap/README.md` § Guardrails; skill is globally installed by design |
| Bootstrap NEVER writes outside `<project_root>` (no parent dirs, no sibling repos, no global Claude config) | `bootstrap/README.md` § Guardrails |
| Bootstrap NEVER overwrites a non-empty `wiki-spec.md` without explicit consent (option 2 in `troubleshooting.md` § wiki-spec.md Conflicts) | `bootstrap/plan.md` §B5, `bootstrap/troubleshooting.md` |
| Bootstrap NEVER overwrites existing managed-block content in `CLAUDE.md` without a unified diff and explicit consent | `bootstrap/plan.md` §B4 |
| Each step is idempotent (state detection skips completed steps) | `bootstrap/plan.md` § Step 0, every B-step's "Skip if" rule |
| Sidecar carries `meatywiki_skill_version` pin for drift detection | `bootstrap/sidecar-template.md` frontmatter |
| Sidecar content above the "Edit by hand only" HR is managed; content below is user-owned and preserved on re-bootstrap | `bootstrap/sidecar-template.md` footer; `bootstrap/troubleshooting.md` § Sidecar Drift |

### 13.4 Managed-Block Format

The canonical `CLAUDE.md` block (B4) is:

```markdown
<!-- meatywiki:start -->
## MeatyWiki

This project uses MeatyWiki for knowledge compilation. Agent context:

@.claude/context/meatywiki.md
<!-- meatywiki:end -->
```

Markers MUST be `<!-- meatywiki:start -->` and `<!-- meatywiki:end -->` (lowercase, exact). Other skills following this pattern (e.g., `notebooklm-cli`, `demo-forge`) MUST use their own marker namespace and a separate block. Blocks are independent; bootstrap MUST NOT merge them.

### 13.5 Update Protocol for Bootstrap Surface

When the bootstrap contract changes (new step, changed sidecar template, changed CLAUDE.md block format):

1. **Additive** (new optional B-step, new template section): bump `SKILL.md` `skill_version` MINOR. Append a row to §13.2. Update affected `bootstrap/` files. No forced re-bootstrap.
2. **Breaking** (renamed step, removed template section, changed marker format): bump `SKILL.md` `skill_version` MAJOR. Document the migration in `bootstrap/troubleshooting.md` § Re-Bootstrap. Projects with sidecar `meatywiki_skill_version` below the breaking version SHOULD re-run bootstrap.
3. **Patch** (wording, examples): no version bump required.

The sidecar's `meatywiki_skill_version` frontmatter field is the migration anchor. Bootstrap reads it during state detection and triggers the appropriate flow (no-op / additive update / drift dialog).

### 13.6 Cross-Skill Pattern Note

This bootstrap pattern (minimal SKILL.md §1.5 + `bootstrap/` progressive disclosure + sidecar + managed CLAUDE.md block + project-spec stub) is reusable for other CLI-driver skills that benefit from one-shot project wiring (e.g., `notebooklm-cli`, `demo-forge`). Adopters MUST use their own marker namespace per §13.4 and their own sidecar path (`.claude/context/<skill-name>.md`). The MeatyWiki bootstrap files are **not** a shared library — they are skill-specific. Pattern replication is documentation, not code reuse.

---

## 14. v1.3 Audit Log (Cross-Project Knowledge Hub)

**Audit date:** 2026-05-24
**Auditor:** ai-artifacts-engineer
**Engine version:** compilation-engine-v1.3 (Agent Skills; shipped 2026-05-09)
**Feature track:** cross-project-knowledge-hub (phases 1–5 shipped 2026-05-09; phases 6–7 in progress)

### Decision: additive CLI bump

Six new CLI surfaces shipped in v1.3 as part of the Cross-Project Knowledge Hub v1 and v2 features: `ingest --source-dir`, `sync`, `ingest --memory`, `query --cross-project`, `projects detect [--apply]`, and `watch`. This is an **additive CLI bump** per §9: new commands and flags with backward-compatible defaults. No existing command behavior is changed.

### Changes applied

| File | Change |
|---|---|
| `SPEC.md` | Frontmatter: bumped `cli_version_range` to v1.3, `updated` to 2026-05-25. Coverage matrix: added v1.3-SD, v1.3-SY, v1.3-AM, v1.3-CP, v1.3-PD, v1.3-WD rows. Appended §14 audit log. **Updated 2026-06-04 (P4-01):** `cli_version_range` bumped to v1.4, `skill_version` added as v1.4, `updated` date 2026-06-04. Coverage matrix v1.3-PD and v1.3-WD rows corrected to match actual shipped CLI flags (see §14 spec drift note). New coverage matrix rows added: v1.4-CL (`consolidate`), v1.4-CT (`cost report`). New §16 "Command Reference: Adoption Readiness Commands" added with full flag tables, examples, and cost estimates for 7 commands. |
| `references/command-reference.md` | **Pending:** `#ingest` section needs `--source-dir` and `--memory` flag subsections. `#sync` section needs to be authored. `#query` section needs `--cross-project` flag documented. **v2 additions:** `#projects` section with `detect` and `detect --apply` subcommands. `#watch` command section (already in V1 scope; clarify real-time daemon behavior). `#consolidate` section needs to be authored. `#cost` section needs to be authored. |
| `references/workflow-patterns.md` | **Pending:** cross-project ingest recipe, AI memory ingest recipe, projects detection recipe, and file-watching recipe should be added. |

### New command surfaces summary

| ID | Command surface | Key behavior |
|---|---|---|
| v1.3-SD | `ingest --source-dir <path>` | Batch ingest from external project dir; `is_derived: true`; SHA-256 hash preserved; `--project`, `--pattern`, `--dry-run` |
| v1.3-SY | `sync` | Hash-based change detection re-ingest; `--project`, `--dry-run`, `--report` staleness view |
| v1.3-AM | `ingest --memory` | AI chat export extraction (ChatGPT/Perplexity/Gemini); `source_type: ai_memory`; dedup on re-ingest |
| v1.3-CP | `query --cross-project` | Cross-project FTS5 search; results annotated with `project_id` + `is_derived`; composable with all existing query flags |
| v1.3-PD | `projects detect [--apply]` | Scan vault for project boundaries; report detected structure; `--apply` writes to config |
| v1.3-WD | `projects watch [--debounce N]` | Long-running daemon for real-time project directory monitoring; triggers sync per changed project; `.git/` always ignored. Note: top-level `watch` is vault-only re-index; `projects watch` is cross-project sync automation. |

### Spec drift observed

**Corrected 2026-06-04 (P4-01):** The original v1.3-WD summary row and coverage matrix description incorrectly described this as "`watch`" with "`--auto-compile`". The actual shipped command is `meatywiki projects watch` (a subcommand of the `projects` group). The top-level `meatywiki watch` monitors the vault for re-indexing only (no sync). `--auto-compile` does not exist on either command. The coverage matrix row and §16 command reference have been corrected to match the shipped CLI. Coverage matrix rows are otherwise derived from the cross-project-knowledge-hub PRD and phase 1–5 shipped implementation. `command-reference.md` and `workflow-patterns.md` still require follow-up edits — these are known gaps, not spec drift.

### cli_version_range update

`SPEC.md` frontmatter `cli_version_range` extended to `"compilation-engine-v1 – v1.3 (pre-release; spec-driven)"` — additive bump per §9 procedure.

---

## 15. v1.4 Audit Log (Edge Density Remediation v2)

**Audit date:** 2026-05-27
**Auditor:** ai-artifacts-engineer (DOC-008, Phase 7)
**Engine version:** compilation-engine-v1.4 (Edge Density v2: embedding pre-filter + batch synthesis)

### Decision: additive CLI bump

Three new or extended CLI surfaces shipped in v1.4 as part of the Edge Density Remediation v2 feature track: `embed-vault` (new top-level command with file-hash idempotency), `edges --show-evidence` (new flag on the existing `edges` command group), and three new flags on `migrate-edges` (`--batch-size`, `--no-prefilter`, `--include-entity-glossary`). This is an **additive CLI bump** per §9: new commands and flags with backward-compatible defaults. No existing command behavior is changed.

### Changes applied

| File | Change |
|---|---|
| `SPEC.md` | Frontmatter: bumped `cli_version_range` to v1.4, `updated` to 2026-05-27. Coverage matrix: added v1.4-EV, v1.4-EP, v1.4-MF rows. Appended §15 audit log. |
| `references/command-reference.md` | **Pending:** `#embed-vault` section needs to be authored. `#edges` section needs `--show-evidence` flag subsection. `#migrate-edges` flag table needs `--batch-size`, `--no-prefilter`, `--include-entity-glossary` rows. |
| `references/workflow-patterns.md` | **Pending:** embedding refresh recipe (embed-vault idempotency workflow) and edge evidence audit recipe should be added. |

### New command surfaces summary

| ID | Command surface | Key behavior |
|---|---|---|
| v1.4-EV | `embed-vault` | File-hash idempotent embedding generation/refresh; `--batch-size`, `--force`; requires `PORTAL_DATABASE_URL` |
| v1.4-EP | `edges --show-evidence <artifact-id>` | Per-edge provenance display: source passages, cosine scores, generating strategy; `--format json\|table` |
| v1.4-MF | `migrate-edges --batch-size N` / `--no-prefilter` / `--include-entity-glossary` | Batch synthesis tuning and scope expansion; backward-compatible extensions to v1.1-ME contract |

### Spec drift observed

None. Coverage matrix rows derived from Edge Density Remediation v2 PRD (phases 3–5). `command-reference.md` and `workflow-patterns.md` require follow-up edits (noted as "to be extended/authored" in the coverage matrix rows) — known gaps, not spec drift.

### cli_version_range update

`SPEC.md` frontmatter `cli_version_range` extended to `"compilation-engine-v1 – v1.4 (pre-release; spec-driven)"` — additive bump per §9 procedure.

---

## 16. Command Reference: Adoption Readiness Commands

**Added:** 2026-06-04 (skill v1.4, P4-01)
**Scope:** Detailed reference for the seven CLI commands shipped as part of the Cross-Project Knowledge Hub v2 and Audit Wave 3 tracks. All commands verified against `uv run meatywiki <cmd> --help` on 2026-06-04.

**Checklist items completed by this section:** 14 (v1.4-CL `consolidate`), 15 (v1.4-CT `cost report`).

---

### consolidate

**Purpose:** Find duplicate `entity` and `glossary_term` artifacts and optionally auto-merge safe pairs. Default mode is non-mutating (dry-run required). Designed for post-ingest hygiene when multiple ingestion runs produce near-duplicate concept entries.

**Flags:**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--dry-run` / `--no-dry-run` | bool | `--dry-run` | Default mode. Shows candidates and scores without executing merges. |
| `--auto` | flag | off | Execute scoped, guarded auto-band merges. Use only after reviewing dry-run output. |
| `--scope TYPE[,TYPE...]` | str | all | Restrict to `entity`, `glossary_term`, or both (comma-separated). |
| `--since DATETIME` | ISO-8601 | — | Seed candidates from artifacts created/updated after this timestamp only. |
| `--min-confidence FLOAT` | 0.0–1.0 | 0.65 | Minimum scored confidence to include in the report. |
| `--output FILE` | path | — | Write report to file. `.json` → JSON; `.md`/`.markdown` → Markdown. |

**Example — dry-run (safe, no writes):**
```bash
meatywiki consolidate --scope entity --min-confidence 0.75 --output /tmp/dedup-report.md
```

**Example — apply auto-merge for high-confidence pairs:**
```bash
meatywiki consolidate --auto --scope entity,glossary_term --min-confidence 0.85
```

**Cost estimate:** LLM classification-tier calls per candidate pair during scoring. `--dry-run` (default) incurs zero LLM calls. `--auto` triggers merge writes but no additional LLM calls beyond scoring.

---

### cost report

**Purpose:** Read the engine cost log at `<vault>/_meta/cost_log.db` and render per-(stage, model) call counts, p50/p95 cost estimates, and a last-30-day total. Zero LLM calls — pure telemetry read. Useful for identifying expensive pipeline stages and tracking spend trends.

**Flags:**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--since YYYY-MM-DD` | date | — | Filter records on/after this date (inclusive). |
| `--until YYYY-MM-DD` | date | — | Filter records up to and including this date. |
| `--format {table\|json}` | choice | `table` | Human-readable table or machine-readable JSON. |
| `--vault-size` | flag | off | Add an Artifacts column showing last recorded `vault_artifact_count` per group. |
| `--db FILE` | path | `<vault>/_meta/cost_log.db` | Override the cost log DB path. |

**Example — last-30-day summary:**
```bash
meatywiki cost report
```

**Example — monthly spend with artifact count:**
```bash
meatywiki cost report --since 2026-05-01 --until 2026-05-31 --vault-size --format json
```

**Cost estimate:** Zero LLM calls. Reads `_meta/cost_log.db` only.

---

### sync

**Purpose:** Re-ingest changed files from all (or one) configured external project directories. Uses SHA-256 content-hash comparison against the stored `source_content_hash` to detect changes — only changed files are re-processed (no LLM calls for unchanged files). Configured project directories live in `_meta/config.yaml` under `project_directories`.

**Flags:**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--project TEXT` | str | — | Sync only the project whose `project_id` matches this value. Omitting syncs all enabled project directories. |
| `--dry-run` | flag | off | Print planned actions (new/updated/skipped per file) without writing anything. |
| `--report` | flag | off | Emit a staleness table (sources with changed hashes) without re-ingesting. |

**Exit codes:** `0` on success (even if files were updated); `1` if any file raises an error during ingest.

**Example — preview all changes across all projects:**
```bash
meatywiki sync --dry-run
```

**Example — apply sync for one project:**
```bash
meatywiki sync --project meatywiki
```

**Example — print staleness table without writing:**
```bash
meatywiki sync --report
```

**Cost estimate:** LLM classification + extraction calls only for files whose content hash has changed. Re-syncing an unchanged directory costs zero LLM calls.

---

### ingest --source-dir

**Purpose:** Scan an external project directory and ingest all matched files as derived artifacts. Sets `is_derived: true` on every artifact created and preserves the source path and SHA-256 content hash in envelope fields. Use `--dry-run` to preview before writing.

**Relevant flags (on `meatywiki ingest`):**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--source-dir DIRECTORY` | path | — | **Required for this mode.** Scan this directory. When provided, the positional `SOURCE` argument is ignored. |
| `--pattern TEXT` | glob | `**/*.md` | File glob pattern. Can be repeated for multiple patterns. |
| `--project TEXT` | str | — | Associate ingested artifacts with this project slug. Can be repeated. |
| `--dry-run` | flag | off | Validate without writing files. |
| `--domain TEXT` | str | — | Domain tags. Can be repeated. |

**Example — dry-run to preview what would be ingested:**
```bash
meatywiki ingest --source-dir ~/dev/myproject/docs --pattern '**/*.md' --project myproject --dry-run
```

**Example — ingest with custom pattern, associate with project:**
```bash
meatywiki ingest --source-dir ~/dev/myproject/docs \
  --pattern 'project_plans/**/*.md' \
  --project myproject \
  --domain planning
```

**Cost estimate:** LLM classification + extraction calls per matched file (not per directory). Use `--dry-run` first to confirm matched file count before incurring LLM costs.

---

### query --cross-project

**Purpose:** Search across all indexed artifacts regardless of project scope. When `--cross-project` is set, any `--project` filter is ignored. Each result is annotated with its originating `project_id` and a `[derived]` marker for artifacts synced from external repositories. All other `query` flags remain composable.

**Relevant flags (on `meatywiki query`):**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--cross-project` | flag | off | Remove per-project FTS5 filter; search all projects. Overrides `--project` when both are given. |
| `--scope TEXT` | str | — | Limit to a domain scope (still applied across all projects). |
| `--limit-context INTEGER` | int | 10 | Max artifacts in LLM context. |
| `--file-back` | flag | off | Write answer as a `research_synthesis` artifact under `wiki/syntheses/`. |
| `--format {text\|json}` | choice | `text` | Output format. |

**Example — cross-project synthesis query:**
```bash
meatywiki query "What architectural patterns are used across our projects?" --cross-project --file-back
```

**Example — scoped cross-project query with JSON output:**
```bash
meatywiki query "Portal authentication decisions" --cross-project --scope portal --format json
```

**Cost estimate:** One LLM synthesis call (compile/query-tier model) plus one embedding call if semantic mode is active. `--file-back` adds one write (no additional LLM call).

---

### projects detect

**Purpose:** Scan a directory tree for project boundary markers (CLAUDE.md, pyproject.toml) and propose `project_directories` entries for `_meta/config.yaml`. Dry-run by default — prints a YAML block to stdout without writing. `--apply` merges detected entries into the config, skipping paths already present.

**Flags:**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `ROOT_DIR` | positional | cwd | Root directory to scan. |
| `--apply` | flag | off | Merge detected entries into `_meta/config.yaml`. Skips paths already present. |
| `--depth INTEGER` | int | 3 | Maximum directory depth to scan below ROOT_DIR. |

**Example — preview detected projects under ~/dev:**
```bash
meatywiki projects detect ~/dev --depth 2
```

**Example — apply detection results to config:**
```bash
meatywiki projects detect ~/dev --depth 2 --apply
```

**Cost estimate:** Zero LLM calls. File-system scan only.

---

### projects watch

**Purpose:** Long-running daemon that monitors all enabled `project_directories` from `_meta/config.yaml` for file-system changes. After a quiet period (debounce) following the last event in a project directory, the sync pipeline is invoked for that directory only. `.git/` paths are always ignored; vault root is excluded. Exits on SIGINT/SIGTERM.

**Distinction from `meatywiki watch`:** The top-level `meatywiki watch` command monitors the vault itself for re-indexing (`.md` changes → incremental index update). `projects watch` monitors external project directories and triggers the full sync pipeline. These are separate commands with separate scopes.

**Flags:**

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--debounce FLOAT` | seconds | `features.watch.debounce_seconds` from config (3.0) | Quiet period after last event before sync is triggered. |

**Example — start project watcher:**
```bash
meatywiki projects watch
```

**Example — tighter debounce for interactive use:**
```bash
meatywiki projects watch --debounce 1.5
```

**Cost estimate:** Zero LLM calls in watch mode itself. Sync triggered by file changes incurs the same cost as `meatywiki sync` for changed files only (classification + extraction per changed file).
