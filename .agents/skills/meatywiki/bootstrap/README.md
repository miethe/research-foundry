---
name: meatywiki-bootstrap
description: Bootstrap mode for the meatywiki skill — wires MeatyWiki into a fresh project (B1-B5: vault init, CLAUDE.md sidecar pointer, wiki-spec stub) or onboards an existing repository into the cross-project knowledge hub (B6: detect, patterns, sync, state doc, intent doc).
type: progressive-disclosure
skill_name: meatywiki
schema_version: 1
cli_version_range: "compilation-engine-v1 – v1.4 (pre-release)"
---

# MeatyWiki Bootstrap Mode

Bootstrap mode is a one-shot orchestration that prepares a project to use MeatyWiki from agentic workflows. It is **separate** from day-to-day CLI usage; once bootstrap completes, agents drive `meatywiki` commands normally per `SKILL.md`.

## When to Use

**B1–B5 (fresh project):** Trigger when **any** of these is true and the user has indicated MeatyWiki should be part of the project's agentic workflow:

- The project has no `<vault>/_meta/meatywiki.db` (no MeatyWiki vault yet)
- The project's root `CLAUDE.md` (or `AGENTS.md`) contains no MeatyWiki context pointer
- The project has a vault but no project-level `wiki-spec.md` declaring intent (scope, ingest sources, lens priorities)

Explicit trigger phrases the user may type:

- "bootstrap meatywiki here" / "set up meatywiki for this project"
- "wire meatywiki into this repo" / "add meatywiki context to CLAUDE.md"
- "initialize a meatywiki vault for this project"

**B6 (existing repo onboarding):** Trigger when the vault is already initialized and the user wants to register an external project repo as a derived-artifact source:

- "add this repo to meatywiki" / "onboard `<repo>` into the knowledge hub"
- "wire `<repo>` into my vault" / "sync `<repo>` docs into meatywiki"
- "start tracking `<repo>` as a project source"

## When NOT to Use

- The project already has a `_meta/meatywiki.db` AND a `<vault>/wiki-spec.md` AND a `@.claude/context/meatywiki.md` reference in root `CLAUDE.md` AND is already registered in `_meta/config.yaml`. Bootstrap is idempotent but adds no value — go straight to normal compile loop.
- The user wants to ingest a single source — that's `meatywiki ingest`, not bootstrap.
- The user is working in this monorepo (`meatywiki` itself). Bootstrap is for **target** projects that use MeatyWiki as a knowledge layer.

## What Bootstrap Does

**B1–B5** bootstrap a fresh project (five idempotent steps). **B6** onboards an existing repo into the cross-project hub (seven steps, vault already initialized). Each step detects existing state and skips if already done.

**B1–B5 steps (fresh project):**

| Step | Action | Idempotency check |
|---|---|---|
| B1 | Detect or elicit vault path | If `<vault>/_meta/` exists, reuse; otherwise prompt |
| B2 | Run `meatywiki init <path>` + write `_meta/config.yaml` defaults | Skip if `_meta/meatywiki.db` already present and valid (`meatywiki doctor` returns ok) |
| B3 | Drop `.claude/context/meatywiki.md` sidecar in the **project root** (not the vault) | Diff against template; only overwrite with explicit consent |
| B4 | Propose one-line `@.claude/context/meatywiki.md` pointer in root `CLAUDE.md`; apply on confirm | Skip if pointer already present |
| B5 | Generate `<vault>/wiki-spec.md` stub from template + project context | Skip if file exists; offer to diff-update |

Steps B3 and B4 are the **only** edits to project files outside the vault. Step B3 writes a sidecar (full content); step B4 adds one line to root `CLAUDE.md`. Both are diff-confirmed.

**B6 steps (existing repo onboarding):**

| Step | Action | Gate |
|---|---|---|
| B6-1 | `meatywiki projects detect <parent_dir> --depth 2 --apply` — register repo in `_meta/config.yaml` | Skip if path already in config |
| B6-2 | Configure conservative patterns in config: `docs/project_plans/**/*.md`, `README.md`, `CLAUDE.md`; optionally add `.meatywikiignore` | Manual config edit |
| B6-3 | `meatywiki ingest --source-dir <path> --pattern ... --project <slug> --dry-run` — preview matched files and cost | **Mandatory; user must review before B6-4** |
| B6-4 | `meatywiki sync --project <slug>` (or `ingest --source-dir` for first-time) — write derived artifacts | User confirms dry-run output |
| B6-5 | `meatywiki query "..." --project <slug> --file-back` + manual rename → per-project state doc | Manual curation |
| B6-6 | Write per-project `wiki-spec.md` intent stub using inline template | Manual curation; skip if exists |
| B6-7 | (Optional) `meatywiki consolidate --dry-run` — surface duplicates if domain overlap detected | User reviews report before any apply |

## Guardrails

- **Diff-confirm every edit outside the vault.** Show the user the proposed patch to `CLAUDE.md` and the sidecar contents before writing. Never blast-update.
- **Never overwrite a non-empty `wiki-spec.md`.** Offer a diff-patch path instead.
- **Vault writes go through the engine.** Bootstrap calls `meatywiki init` — it does not directly create files under `wiki/`, `raw/`, or `_meta/`.
- **Project root scope.** Bootstrap may write `.claude/context/meatywiki.md` and update `CLAUDE.md` in the **project root only**. It does not touch parent directories, sibling repos, or global Claude config.
- **No global skill install.** The skill being globally installed IS the wiring — bootstrap does NOT create per-project `.claude/skills/meatywiki/` shims.

## Files in This Directory

| File | Purpose | When to load |
|---|---|---|
| `README.md` (this) | Entry point, decision tree, guardrails | Always first when bootstrap is triggered |
| `plan.md` | Step-by-step orchestration: state detection → B1–B5 sequence with exact commands | When executing bootstrap |
| `sidecar-template.md` | Exact content for `.claude/context/meatywiki.md` (the CLAUDE.md sidecar) | Step B3 |
| `wiki-spec-template.md` | Exact content for `<vault>/wiki-spec.md` (project intent stub) | Step B5 |
| `troubleshooting.md` | Partial-state recovery, re-bootstrap, drift between sidecar and skill version | When B-step fails or state is ambiguous |

## Exit Conditions

Bootstrap reports completion when **all** are true:

1. `meatywiki doctor` returns ok against the vault
2. `.claude/context/meatywiki.md` exists in project root and matches current sidecar-template (modulo project-specific fills)
3. Root `CLAUDE.md` contains the `@.claude/context/meatywiki.md` reference line
4. `<vault>/wiki-spec.md` exists with the user's project intent filled in (not just the template placeholders)

Report back a one-paragraph summary listing: vault path, files written/modified (with diffs collapsed), and the next agent command the user should run (typically `meatywiki ingest <first-source>` or `meatywiki stats`).

---

See `SPEC.md` §13 (Bootstrap Contract) for the durable contract (§13.2 now covers B1–B6); this README is the operational entry point.
