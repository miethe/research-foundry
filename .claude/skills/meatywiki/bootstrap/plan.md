---
name: meatywiki-bootstrap-plan
description: Step-by-step orchestration plan for MeatyWiki bootstrap mode. Detects project state, executes B1-B5 idempotently, diff-confirms all edits outside the vault. B6 covers onboarding an existing repository into the cross-project knowledge hub.
type: progressive-disclosure
skill_name: meatywiki
schema_version: 1
cli_version_range: "compilation-engine-v1 – v1.4 (pre-release)"
---

# Bootstrap Orchestration Plan

This is the executable plan for bootstrap mode. Follow it sequentially. Each step is idempotent: detect existing state, skip if done, otherwise act.

## Step 0 — State Detection (read-only)

Before touching anything, gather state. Run these checks; record results in working memory.

```
Check 1: Is this a git repo?           git rev-parse --show-toplevel
Check 2: Project root path             (use git toplevel; fallback: cwd)
Check 3: Root CLAUDE.md exists?        test -f <root>/CLAUDE.md
Check 4: Sidecar exists?               test -f <root>/.claude/context/meatywiki.md
Check 5: Sidecar referenced in CLAUDE? grep -l '@.claude/context/meatywiki.md' <root>/CLAUDE.md
Check 6: Vault path candidates         look for <root>/{vault,wiki,knowledge,docs/vault}/_meta/
Check 7: User-declared vault path      ask if no candidate found
Check 8: Vault doctor result           meatywiki --vault <path> doctor (capture exit code)
Check 9: wiki-spec.md exists?          test -f <vault>/wiki-spec.md
```

Build a compact state table:

```
- project_root: /abs/path
- root_claude_md_present: true|false
- sidecar_present: true|false
- sidecar_referenced: true|false
- vault_path: /abs/path  (or unknown)
- vault_initialized: true|false (doctor exit 0)
- wiki_spec_present: true|false
```

Present this table to the user before proceeding to B1. If anything is ambiguous (e.g., two candidate vault dirs), ask once with `AskUserQuestion`.

---

## Step B1 — Resolve Vault Path

**Goal:** End with a single absolute path for the vault.

| State | Action |
|---|---|
| Vault detected, doctor ok | Confirm path with user (one line); proceed to B2 (skip init) |
| Vault detected, doctor fails | Ask: repair (run `meatywiki index --reset` + `doctor`) or treat as fresh? |
| No vault, user has preference | Use user-provided path |
| No vault, no preference | Recommend `<project_root>/vault/`; ask to confirm |

Persist the chosen path for downstream steps. Do not create the directory — `meatywiki init` does that.

---

## Step B2 — Initialize Vault

**Skip if** `meatywiki --vault <path> doctor` returned exit 0 in Step 0.

```bash
meatywiki init <vault_path>
```

Verify with:

```bash
meatywiki --vault <vault_path> doctor
```

If init fails, surface the error verbatim and stop. Do not proceed to B3/B4/B5 with a broken vault.

**Optional config tweaks** (only if the user provided preferences; do NOT prompt for these unless they asked):

- Set default LLM providers per stage in `_meta/config.yaml` (classify/extract/compile/query/lint)
- Set `agent_visibility` defaults
- Set ingestion source-type priorities

Defer everything else to standard MeatyWiki configuration flow.

---

## Step B3 — Write CLAUDE.md Sidecar

**Goal:** Drop `<project_root>/.claude/context/meatywiki.md` with content from `sidecar-template.md`.

Substitute these placeholders in the template before writing:

| Placeholder | Source |
|---|---|
| `{{VAULT_PATH}}` | Resolved in B1 (absolute or `<project_root>`-relative) |
| `{{PROJECT_NAME}}` | Inferred from `git remote get-url origin` or project root dir name |
| `{{SKILL_VERSION}}` | From `SKILL.md` frontmatter `skill_version` |
| `{{BOOTSTRAP_DATE}}` | Today's date (ISO 8601) |

**Idempotency:**

1. If sidecar does not exist → write directly (still show preview to user; one-line confirm is fine).
2. If sidecar exists and matches template hash exactly → skip (state already current).
3. If sidecar exists but content differs → show a unified diff; ask: keep existing / overwrite / merge manually. Default: keep existing (safest).

Create the `<project_root>/.claude/context/` directory if missing.

---

## Step B4 — Add CLAUDE.md Pointer

**Goal:** Ensure root `CLAUDE.md` contains a single line referencing the sidecar.

**Pointer line (exact):**

```markdown
@.claude/context/meatywiki.md
```

Place it under a clearly fenced managed block at the **end** of `CLAUDE.md`:

```markdown
<!-- meatywiki:start -->
## MeatyWiki

This project uses MeatyWiki for knowledge compilation. Agent context:

@.claude/context/meatywiki.md
<!-- meatywiki:end -->
```

**Procedure (diff-confirm per user decision):**

1. Read current `CLAUDE.md`.
2. If `<!-- meatywiki:start -->` block exists → diff against the canonical block above; if identical, skip. If different, propose a patch.
3. If no managed block → propose appending the block.
4. Show the unified diff to the user.
5. Apply only on explicit confirm.

If `CLAUDE.md` does not exist at project root:

- Ask the user: create a minimal `CLAUDE.md` with just the MeatyWiki block, or skip B4 entirely?
- If created, the file contains ONLY the managed block plus a one-line project header. Do not invent project context.

---

## Step B5 — Generate `wiki-spec.md` Stub

**Goal:** Write `<vault>/wiki-spec.md` from `wiki-spec-template.md`.

**Skip if** the file already exists. Offer instead:

- Show a diff between template and existing
- Recommend the user fold any missing sections in manually

**Placeholders:**

| Placeholder | Source |
|---|---|
| `{{PROJECT_NAME}}` | Same as B3 |
| `{{VAULT_PATH}}` | Resolved in B1 |
| `{{BOOTSTRAP_DATE}}` | Today |
| `{{INTENT_PROMPT}}` | Ask user one question: "In one paragraph, what is this vault FOR?" — keep their answer verbatim |

The stub leaves Ingest Sources, Lens Priorities, and Deferred Items mostly empty (with examples commented out). The user fills these in over time; bootstrap does not invent them.

---

## Step Exit — Summary & Next Action

Print a single compact summary:

```
MeatyWiki bootstrap complete for {{PROJECT_NAME}}:
  vault:        {{VAULT_PATH}}
  sidecar:      .claude/context/meatywiki.md  ({{written|already-current}})
  CLAUDE.md:    {{block-added|already-current|skipped}}
  wiki-spec:    <vault>/wiki-spec.md  ({{written|already-present|diff-deferred}})

Next:
  - Ingest your first source:   meatywiki --vault {{VAULT_PATH}} ingest <url-or-path>
  - Or compile pending raw/:    meatywiki --vault {{VAULT_PATH}} compile --pending
  - Health check:               meatywiki --vault {{VAULT_PATH}} doctor
```

Do not run those commands automatically. User decides.

---

## Failure Modes

| Symptom | Likely cause | Remediation |
|---|---|---|
| `meatywiki init` exits non-zero | Path not writable, or already a vault with mismatched config | See `troubleshooting.md` § Init Failures |
| Sidecar diff loop (user keeps existing, but template moved on) | Skill version bumped since last bootstrap | See `troubleshooting.md` § Re-bootstrap & Sidecar Drift |
| `CLAUDE.md` has a managed block from a different skill that conflicts | Multiple skills writing to root CLAUDE.md | Append a separate fenced block; do not merge |
| User declines B3 or B4 | Intentional | Note the decline in the summary; bootstrap is incomplete but partial-state is acceptable |
| `wiki-spec.md` exists but is empty | Earlier bootstrap stopped mid-flow | Overwrite-with-template is safe; confirm with user once |

---

## Contract

This plan satisfies SPEC.md §13 (Bootstrap Contract) rows B1–B5. B6 is an additive route; see SPEC.md §13.5 for the update protocol. Any deviation must update SPEC.md per §6 Update / Enhancement Protocol.

---

## Step B6 — Onboard Existing Repository

**Goal:** Register an already-active project repository in the cross-project knowledge hub: detect project boundaries, apply conservative ingest patterns, dry-run and confirm the sync, generate per-project state and intent docs.

**When to use B6 instead of B1–B5:**

B1–B5 bootstrap a fresh project that has no MeatyWiki vault yet. B6 is for repositories that already exist and already contain structured documentation — the vault is already initialized and functional; the new task is wiring the external repo into it as a derived-artifact source.

```
B1–B5 (fresh project)                  B6 (existing repo → hub)
─────────────────────────────────────   ──────────────────────────────────────
User has: a project without a vault    User has: a running vault + target repo
Goal: init vault + write sidecar        Goal: register repo as project source
Vault writes: meatywiki init            Vault writes: none (registry only)
Artifact writes: none at bootstrap      Artifact writes: derived artifacts (sync)
```

ASCII flowchart — entry decision:

```
  User wants to onboard a repo?
          │
          ├─ No vault yet ──────────────────────→ B1 (Resolve Vault Path)
          │                                           │
          │                                       B2 (Init Vault)
          │                                           │
          │                                       B3 (Write Sidecar)
          │                                           │
          │                                       B4 (Add CLAUDE.md Pointer)
          │                                           │
          │                                       B5 (Generate wiki-spec.md)
          │
          └─ Vault initialized, target repo       → B6 (Onboard Existing Repo)
             exists, not yet registered as           │
             a project directory                 B6-1 (Detect + Register)
                                                     │
                                                 B6-2 (Configure Patterns)
                                                     │
                                                 B6-3 (Dry-run Ingest)
                                                     │
                                                 B6-4 (Apply Sync)
                                                     │
                                                 B6-5 (State Doc)
                                                     │
                                                 B6-6 (Intent Doc)
                                                     │
                                                 B6-7 (Optional: Consolidation Check)
                                                     │
                                                 B6 Exit Summary
```

---

### B6-1 — Detect and Register the Target Repository

Run `projects detect` to find the target repo (and any adjacent repos) and register the target as a named project source.

**Gather state first (read-only):**

```
Check 1: Target repo root          git -C <target_repo_path> rev-parse --show-toplevel
Check 2: Already registered?       grep -r '<target_repo_path>' <vault>/_meta/config.yaml
Check 3: Detect boundaries nearby  meatywiki projects detect <parent_dir> --depth 2
```

If Check 2 finds the path already present, skip to B6-3. Skip does not mean proceed blindly — confirm with the user that the existing registration is current and correct.

**Register with detect --apply:**

```bash
meatywiki projects detect <parent_dir_of_target_repo> --depth 2
```

Review the YAML output. Confirm the target repo appears with the expected slug. Then apply:

```bash
meatywiki projects detect <parent_dir_of_target_repo> --depth 2 --apply
```

`--apply` merges detected entries into `_meta/config.yaml`. Paths already present are silently skipped — it is safe to re-run.

**Flags verified against `meatywiki projects detect --help` (2026-06-04):**

| Flag | Behavior |
|---|---|
| `ROOT_DIR` (positional) | Root to scan; defaults to cwd |
| `--depth INTEGER` | Max depth; default 3 |
| `--apply` | Merge into `_meta/config.yaml`; dry-run without it |

Cost: zero LLM calls. File-system scan only.

---

### B6-2 — Configure Conservative Ingest Patterns

**Why conservative patterns?** The default `--pattern '**/*.md'` over a real project repo can match hundreds or thousands of files — generated docs, test fixtures, node_modules sneaking through, locale files — creating artifact sprawl and large LLM bills. The patterns below cover the high-value signal without sprawl.

After detecting the project, edit `_meta/config.yaml` to set patterns for the new project entry. The `--apply` step from B6-1 adds the entry with default patterns; edit the entry manually to tighten it.

**Recommended conservative patterns (for most repos):**

```yaml
project_directories:
  - project_id: <slug>           # e.g., "meatywiki" or "my-api-service"
    path: /abs/path/to/repo
    enabled: true
    patterns:
      - "docs/project_plans/**/*.md"   # structured planning docs
      - "README.md"                    # root readme only (not **/README.md)
      - "CLAUDE.md"                    # agent context file
    exclude_patterns: []               # see .meatywikiignore template below
```

**Why these three patterns:**

| Pattern | Rationale |
|---|---|
| `docs/project_plans/**/*.md` | Contains PRDs, implementation plans, and design specs — highest-value structured knowledge |
| `README.md` | Root-level project overview; anchors classification context |
| `CLAUDE.md` | Agent context; provides repo-level conventions that inform downstream synthesis |

**Patterns NOT recommended by default (add only if justified):**

| Pattern | Risk |
|---|---|
| `**/*.md` | Matches generated docs, test fixtures, changelogs, locale strings → artifact sprawl |
| `src/**/*.md` | Matches inline code docs that rarely produce useful knowledge artifacts |
| `**/*.yaml` | Often config files, not knowledge; requires domain-specific judgment |

**`.meatywikiignore` template**

For fine-grained exclusion at the filesystem level, place `.meatywikiignore` at the repo root. The ingest pipeline checks this file before matching patterns. Template:

```
# .meatywikiignore — paths excluded from meatywiki ingest/sync
# One glob pattern per line. Lines starting with # are comments.
# All paths are relative to the repo root.

# Version control
.git/

# Dependency directories
node_modules/
vendor/
.venv/
venv/
__pycache__/

# Build and dist outputs
dist/
build/
target/
out/
.next/

# Generated and cache files
.cache/
.tmp/
*.log
*.log.*

# Local environment secrets
.env.local
.env.*.local

# OS artifacts
.DS_Store
Thumbs.db
```

Note: `.meatywikiignore` support is a best-effort exclusion layer on top of the `patterns` configuration in `_meta/config.yaml`. It does not replace `exclude_patterns` in config — both apply.

---

### B6-3 — Dry-Run Ingest Preview

Before writing any artifacts, preview what would be ingested. This step is **mandatory** — do not proceed to B6-4 without user review of the dry-run output.

```bash
meatywiki ingest --source-dir <target_repo_path> \
  --pattern 'docs/project_plans/**/*.md' \
  --pattern 'README.md' \
  --pattern 'CLAUDE.md' \
  --project <slug> \
  --dry-run
```

The dry-run output shows:
- Matched file count and paths
- Estimated artifact count
- Files that would be skipped (already ingested with matching hash)

**Decision gate:** Present the file count and estimated LLM cost to the user. A typical conservative pattern set on a moderately sized repo produces 20–80 files. If the count is unexpectedly large (>200), narrow the patterns before proceeding. Do not proceed to B6-4 until the user has reviewed and confirmed the dry-run output.

**Flags verified against `meatywiki ingest --help` (2026-06-04):**

| Flag | Behavior |
|---|---|
| `--source-dir DIRECTORY` | Scan this directory (positional SOURCE is ignored when set) |
| `--pattern TEXT` | Glob pattern; can be repeated |
| `--project TEXT` | Associate artifacts with this project slug; can be repeated |
| `--dry-run` | Validate without writing files |

Cost: zero LLM calls in dry-run mode.

---

### B6-4 — Apply Sync (First Ingest)

After user confirms the dry-run, run the initial ingest. This replaces manual `ingest --source-dir` after initial setup with the hub's `sync` command — use whichever matches the state:

**Option A — First-time ingest (project not yet indexed):**

```bash
meatywiki ingest --source-dir <target_repo_path> \
  --pattern 'docs/project_plans/**/*.md' \
  --pattern 'README.md' \
  --pattern 'CLAUDE.md' \
  --project <slug>
```

**Option B — Project already registered, sync changed files only:**

```bash
meatywiki sync --project <slug> --dry-run
```

Review the staleness table. Then apply:

```bash
meatywiki sync --project <slug>
```

`sync` uses SHA-256 content-hash detection — unchanged files incur zero LLM calls. Only new or modified files are re-ingested.

**Flags verified against `meatywiki sync --help` (2026-06-04):**

| Flag | Behavior |
|---|---|
| `--project TEXT` | Sync only this project_id; omit to sync all |
| `--dry-run` | Print planned actions without writing |
| `--report` | Emit staleness table without re-ingesting |

Cost: LLM classification + extraction calls for each new or changed file. Files with unchanged content hash cost zero LLM calls.

---

### B6-5 — Generate Per-Project State Doc

After sync, generate a state snapshot that captures what knowledge the hub now holds for this project. This is a **manual curation step** — there is no dedicated `meatywiki state` command. The recommended approach uses `query --file-back` to produce a synthesis artifact that serves as the state doc.

```bash
meatywiki query "What does the hub know about the <slug> project? Summarize key architectural decisions, active feature tracks, and open questions." \
  --project <slug> \
  --file-back
```

This writes a `research_synthesis` artifact to `wiki/syntheses/` with the auto-generated filename.

**Manual STATE.md curation (recommended):**

After `--file-back` writes the synthesis, rename or copy the output to a predictable path within the vault:

```
<vault>/wiki/syntheses/<slug>-state.md
```

Update the frontmatter `title` field to `<ProjectName> State — <YYYY-MM-DD>`. This file is the per-project state doc and should be refreshed periodically (via the same query) as new knowledge is ingested.

**Note:** The `query --project <slug> --file-back` flag is verified shipped (see `meatywiki query --help`). The STATE.md file naming and placement are a manual convention, not an automated CLI feature. This is a deferred feature (see B6 Deferred Items below).

---

### B6-6 — Create Per-Project Intent Doc (wiki-spec.md)

Each project registered in the hub should have a `wiki-spec.md` intent document inside the vault. This is separate from the project's own root `wiki-spec.md` (if it has one) — it declares the vault's intent for knowledge about this project.

**Skip if** `<vault>/wiki/<slug>/wiki-spec.md` or a project-scoped wiki-spec equivalent already exists. Offer a diff-update path instead.

**Location convention:**

```
<vault>/projects/<slug>/wiki-spec.md
```

**Minimal starter content:**

```markdown
---
title: "<ProjectName> — Knowledge Spec"
project: <slug>
created: <YYYY-MM-DD>
schema_version: "1.0.0"
---

# <ProjectName> Knowledge Spec

## Intent

One paragraph: what knowledge from this project does the vault compile and for what purpose?

## Ingest Sources

- `docs/project_plans/**/*.md` — PRDs, implementation plans, design specs
- `README.md` — root project overview
- `CLAUDE.md` — agent conventions

## Lens Priorities

- (fill in as vault use patterns emerge)

## Deferred / Out of Scope

- Source code files (not knowledge artifacts)
- Generated documentation (markdown output of build tools)
```

This stub leaves the intent paragraph intentionally blank for the user to fill in. Ask the user one question: "In one sentence, what is the vault's purpose for knowledge about this project?" — keep their answer verbatim as the intent paragraph.

---

### B6-7 — Optional: Consolidation Check

After the initial ingest, run a consolidation dry-run to surface any duplicate entity or glossary artifacts that arose from ingesting related documents from the new project.

This step is **optional**. Recommend it only if the dry-run output from B6-3 showed >50 files, or if the project domain overlaps substantially with existing vault content (e.g., both projects share domain vocabulary like "artifact", "workflow", "portal").

```bash
meatywiki consolidate --dry-run --scope entity,glossary_term --min-confidence 0.75
```

Review the report. If it identifies high-confidence duplicate pairs, apply selectively:

```bash
meatywiki consolidate --auto --scope entity --min-confidence 0.85
```

Do not apply consolidation automatically during B6. Always require user review of the dry-run report first.

**Flags verified against `meatywiki consolidate --help` (2026-06-04):**

| Flag | Behavior |
|---|---|
| `--dry-run` | Default mode; shows candidates without executing merges |
| `--auto` | Execute guarded auto-band merges (use after reviewing dry-run) |
| `--scope TYPE[,TYPE...]` | Restrict to `entity`, `glossary_term`, or both |
| `--min-confidence FLOAT` | Default 0.65; raise to 0.85+ for conservative apply |

Cost: LLM classification-tier calls per candidate pair during scoring. `--dry-run` incurs zero LLM calls.

---

### B6 Exit — Summary & Next Actions

Print a compact summary after all B6 steps complete:

```
MeatyWiki B6 onboarding complete for {{PROJECT_NAME}}:
  project_id:   <slug>
  source_dir:   <target_repo_path>
  patterns:     docs/project_plans/**/*.md, README.md, CLAUDE.md
  artifacts:    N new / M updated / K skipped
  state doc:    <vault>/wiki/syntheses/<slug>-state.md  ({{written|skipped}})
  intent doc:   <vault>/projects/<slug>/wiki-spec.md  ({{written|skipped}})
  consolidate:  {{ran dry-run: P pairs / skipped}}

Next:
  - Refresh state doc periodically:
      meatywiki query "..." --project <slug> --file-back
  - Sync when source files change:
      meatywiki sync --project <slug>
  - Enable real-time sync (optional, long-running):
      meatywiki projects watch
  - Cross-project knowledge query:
      meatywiki query "..." --cross-project
  - More: docs/guides/cross-project-knowledge-hub.md
```

Do not run those commands automatically. User decides.

---

### B6 Deferred Items

The following steps in the B6 flow have no shipped CLI command. They are documented as manual steps in this plan and are candidates for future automation:

| Item | Deferred Feature | Notes |
|---|---|---|
| `meatywiki state --project <slug>` | No `state` command exists | Use `query --project <slug> --file-back` + manual rename as a proxy |
| Auto-naming STATE.md with predictable slug path | No `--output` flag on `query` | Output lands in `wiki/syntheses/` with auto-generated filename; rename manually |
| Per-project wiki-spec.md scaffolding from CLI | No `meatywiki init-project` command | Use the inline template in B6-6 as a starting point; fill in manually |
| `.meatywikiignore` enforcement | Best-effort exclusion only | Platform support varies; verify with a `--dry-run` after placing the file |
