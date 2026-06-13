---
schema_version: 2
doc_type: bundle_spec
bundle_name: skillmeat-instance-starter
bundle_version: 1.0.0
bundle_kind: project_starter
status: stable
created: 2026-05-25
updated: 2026-05-25
owner: nick
source_docs:
  - docs/user/guides/project-scaffolding.md
  - scripts/starter-bundle-manifest.yaml
  - scripts/bundle/README.md
related_skills:
  - dev-execution
  - artifact-tracking
  - planning
  - debugging
  - symbols
affects_commands:
  - skillmeat scaffold --full
  - skillmeat scaffold --standard
  - skillmeat template create
  - skillmeat template list
aligned_app_version: "0.50.1"
---

# SkillMeat Instance Starter Bundle — Specification

## 1. Purpose & Scope

The Instance Starter Bundle is a deployable SkillMeat artifact (`type: bundle`, `kind: project_starter`) that packages the complete SkillMeat AI-assisted development methodology into a single distributable unit. Its purpose is to bootstrap new Claude Code projects with a standardized, pre-configured agent environment — rules, skills, agents, commands, configuration, specs, and context playbooks — in a single scaffold operation.

**In scope:**
- Exporting portable methodology artifacts from the SkillMeat `.claude/` tree
- Three-tier categorization (core / recommended / excluded) for flexible deployment
- Variable substitution for two parameterized template files at build time
- Security pre-flight validation before bundle assembly
- Bundle manifest generation (`bundle-manifest.toml`) for downstream registration
- Build script (`build-starter-bundle.py`) and manifest (`starter-bundle-manifest.yaml`)
- Integration with `skillmeat scaffold`, `skillmeat template`, and the web UI new-project dialog

**Out of scope:**
- SkillMeat product-specific content (collection management, marketplace, web UI internals)
- Ephemeral project artifacts (progress files, worknotes, capsules, worktrees)
- Historical or session-specific content (plans, analyses, evidence, explorations)
- Runtime symbol graph data (`ai/symbols-*.json`) — these are project-specific and must be regenerated after deployment
- Hooks that require path parameterization (deployed as recommended tier but require manual substitution)

---

## 2. Capability Matrix

| Intent | Workflow / Section | Canonical Doc |
|--------|-------------------|---------------|
| Bootstrap a new project with methodology artifacts | `skillmeat scaffold --full` → auto-deploys all enabled starters | `docs/user/guides/project-scaffolding.md` §"CLI Flow" |
| Build a custom bundle from the manifest | `python scripts/build-starter-bundle.py --project-name ...` | `docs/user/guides/project-scaffolding.md` §"Instance Starter Bundle" |
| Preview bundle contents without writing files | `--dry-run` flag on build script | `scripts/bundle/README.md` §"Quick Start" |
| Understand what each tier includes | `scripts/starter-bundle-manifest.yaml` tier sections | `scripts/bundle/README.md` §"What's Included" |
| Parameterize CLAUDE.md and intent.md for a project | Template substitution at build time via `--project-name`, `--project-description`, `--author`, `--architecture-description`, `--date` | `scripts/bundle/README.md` §"Variable Substitution" |
| Register a built bundle as a project starter | `skillmeat template create --kind project-starter` | `docs/user/guides/project-scaffolding.md` §"Creating Your Own Starter Bundle" |
| Update the bundle manifest (add/remove artifacts) | Edit `scripts/starter-bundle-manifest.yaml`, rebuild | `docs/user/guides/project-scaffolding.md` §"Updating Your Instance Starter Bundle" |
| Validate bundle security before shipping | Automatic pre-flight scan in `build_bundle()` rejects sensitive files | `scripts/bundle/README.md` §"Security" |
| Deploy starters to an already-initialized project | `skillmeat scaffold --standard` | `docs/user/guides/project-scaffolding.md` §"Standard Deploy Only" |
| Run scaffold in CI/non-TTY environments | `skillmeat scaffold --full --no-input` | `docs/user/guides/project-scaffolding.md` §"Non-Interactive / CI Mode" |
| List registered project starters | `skillmeat template list --kind project-starter` | `docs/user/guides/project-scaffolding.md` §"Listing Project Starters" |

---

## 3. Structure Overview

### Three-Tier System

```
scripts/starter-bundle-manifest.yaml
├── bundle_metadata       # name, version, description, bundle_kind
├── parameterized_templates  # CLAUDE.md and intents/intent.md
├── core/                 # Always deployed — methodology essentials
├── recommended/          # Deployed by default — domain supplements
└── excluded/             # Never packaged — product-specific or ephemeral
```

### Core Tier Content (approximate counts)

| Category | Entries | Approx. Files | Approx. Size |
|----------|---------|---------------|--------------|
| Rules | 5 files | 5 | ~20 KB |
| Skills | 9 directories | ~186 | ~2,356 KB |
| Agents | ~15 entries | ~36 files | ~284 KB |
| Commands | ~9 directories + files | ~49 | ~457 KB |
| Config | 4 files | 4 | ~16 KB |
| Templates | 1 directory | 5 | ~88 KB |
| Specs | ~9 entries | ~14 | ~144 KB |
| Key Context | 5 files | 5 | ~64 KB |
| Scripts | 10 files | 10 | ~64 KB |
| Hooks | 6 files | 6 | ~24 KB |
| Prompts | 1 file | 1 | ~4 KB |
| Examples | 1 directory | ~7 | ~33 KB |
| **Total Core** | | **~342** | **~3,554 KB** |

### Recommended Tier Content (approximate counts)

| Category | Entries | Approx. Files | Approx. Size |
|----------|---------|---------------|--------------|
| Skills | ~29 directories | ~varies | ~1,600 KB |
| Agents | ~11 files | ~11 | ~48 KB |
| Commands | ~6 files | ~6 | ~24 KB |
| Key Context | 6 files | 6 | ~120 KB |
| Specs | 2 files | 2 | ~16 KB |
| Hooks | 4 files | 4 | ~16 KB |
| Prompts | 1 file | 1 | ~4 KB |
| Docs | 1 file | 1 | ~4 KB |
| **Total Rec** | | **~93** | **~1,832 KB** |

**Combined (core + recommended)**: ~435 files, ~5.4 MB

> Note: The `symbols/` skill contains pre-generated symbol graph JSON files that are project-specific. The skill scripts are portable; only the `*.json` data files need regeneration after deployment via `/analyze:symbols:symbols-update`.

### Build Output Structure

```
dist/starter-bundle/
├── bundle-manifest.toml  # Generated: name, version, file_count, total_size_bytes
├── README.md             # This bundle's README (copied from scripts/bundle/README.md)
├── SPEC.md               # This spec (copied from scripts/bundle/SPEC.md)
├── CLAUDE.md             # Parameterized project entry point
├── intents/
│   └── intent.md         # Parameterized project intent file
└── .claude/
    ├── rules/            # Methodology invariants
    ├── skills/           # Skill frameworks
    ├── agents/           # Agent definitions
    ├── commands/         # Slash commands
    ├── config/           # Multi-model routing, subagent config
    ├── templates/        # PM planning templates
    ├── specs/            # Methodology specifications
    ├── context/          # Key-context playbooks
    ├── scripts/          # Utility scripts
    ├── hooks/            # Pre/post-tool hooks
    ├── prompts/          # Reusable prompt stubs
    └── examples/         # Progress and worknotes templates
```

---

## 4. Integration Points

### Deployment Paths

| Integration | Invocation | Notes |
|-------------|------------|-------|
| `skillmeat scaffold --full` | Auto-deploys all enabled starters via `/api/v1/scaffold-templates?kind=project_starter` | Interactive init + starter deployment in one command |
| `skillmeat scaffold --standard` | Deploys starters to an already-initialized project | Skips interactive init prompts |
| Web UI — New Project dialog | "Project Starters" multi-select step | Starters fetched at dialog load time from API |
| Build script (manual) | `python scripts/build-starter-bundle.py [OPTIONS]` | Generates `dist/starter-bundle/`; requires manual `skillmeat template create` afterward |
| `skillmeat template create` | Registers built bundle as a project starter | Uses `--kind project-starter --source dist/starter-bundle/` |
| SkillMeat API | `POST /api/v1/scaffold-templates` with `kind=project_starter` | Used by scaffold and web UI to fetch starter list |

### Skills Included in Bundle (core tier)

The following skills are deployed as part of the bundle and can be invoked immediately in the target project:

| Skill | Primary Command(s) | Role |
|-------|-------------------|------|
| `dev-execution` | `/dev:execute-phase`, `/dev:quick-feature`, `/dev:implement-story` | Orchestration and phase execution |
| `artifact-tracking` | `update-status.py`, `update-batch.py` | CLI-first progress management |
| `planning` | `/plan:*` | PRD, spike, implementation plan authoring |
| `debugging` | `/fix:debug` | Symbol-first debugging methodology |
| `symbols` | `/analyze:symbols:*` | Codebase navigation |
| `confidence-check` | (invoked by validation agents) | Review readiness calibration |
| `recovering-sessions` | (invoked by agents after compaction) | Context recovery |
| `skill-builder` | (manual invocation) | Custom skill creation |
| `skill-creator` | (manual invocation) | Skill scaffolding with SPEC.md convention |

---

## 5. Variable Contract

Two files in the bundle are parameterized. The build script applies substitution using `{{VAR}}` token syntax.

| Variable | CLI Flag | Template Files | Type | Default |
|----------|----------|----------------|------|---------|
| `PROJECT_NAME` | `--project-name` | `CLAUDE.md`, `intents/intent.md` | string | `{{PROJECT_NAME}}` (token left as-is) |
| `PROJECT_DESCRIPTION` | `--project-description` | `CLAUDE.md`, `intents/intent.md` | string | `{{PROJECT_DESCRIPTION}}` (token left as-is) |
| `AUTHOR` | `--author` | `CLAUDE.md` | string | `{{AUTHOR}}` (token left as-is) |
| `ARCHITECTURE_DESCRIPTION` | `--architecture-description` | `CLAUDE.md` | string | `{{ARCHITECTURE_DESCRIPTION}}` (token left as-is) |
| `DATE` | `--date` | `intents/intent.md` | ISO-8601 string | Today's date (auto-computed) |

**Behavior when variable is omitted**: The `{{VAR}}` token is preserved verbatim in the output. The build script does not fail; it warns if a `.tmpl` file is missing but continues.

**All other files copy verbatim**. No substitution is applied outside the files listed in `parameterized_templates` in the manifest.

---

## 6. Invariants & Constraints

1. **Excluded tier is never packaged.** Files and directories listed under `excluded:` in the manifest must not appear in bundle output regardless of tier argument. The build script reads only `core` and `recommended` tiers.

2. **Security pre-flight is mandatory.** The `security_preflight()` function runs before any files are written. If sensitive patterns are detected (`.env`, `*.token`, `credentials`, `secret`, `settings.local.*`), the build exits non-zero without producing output. This check cannot be bypassed via CLI flags.

3. **chrome-devtools/scripts/ is always excluded.** The recommended-tier `chrome-devtools` skill entry carries a `bundle_note` that suppresses the `scripts/` subdirectory (51 MB of binary data). Only `SKILL.md` and `references/` are bundled.

4. **Parameterized templates use `.tmpl` files, not source files.** When a path is listed in `parameterized_templates`, the build reads from `scripts/templates/<filename>.tmpl` and substitutes variables. The source file at `.claude/` is not read. Template files must exist; a missing template causes a warning but falls back to copying the source file.

5. **Output directory is cleared on each build.** `shutil.rmtree(output_path)` runs before assembly. There is no incremental build.

6. **`bundle-manifest.toml` is always generated last.** It contains the final `file_count` and `total_size_bytes` after all files are written. No external tool should depend on `file_count` being stable across minor manifest changes.

7. **Symbol graph data files are project-specific.** The `symbols/` skill includes pre-generated `ai/symbols-*.json` files from the SkillMeat source repo. Recipients must regenerate these files for their own project after deployment via `/analyze:symbols:symbols-update`.

8. **Recommended-tier hooks require path parameterization.** The four hooks in the recommended tier (`update-symbols-on-code-change.json`, `check-style.sh`, `run-py-tests.sh`, `run-web-tests.sh`) contain hardcoded source paths from the SkillMeat project. Deployers must substitute the target project's paths before activating these hooks.

---

## 7. Enhancement Backlog

- **[BL-1] Starter Bundle Variants**: Support named variant profiles (e.g., `python-backend`, `react-fullstack`, `data-pipeline`) that pre-select tier membership and provide variant-specific template defaults.
  _Status_: candidate
  _Rationale_: Different project types need different artifact subsets. Current approach requires manual manifest editing for each variant.

- **[BL-2] Auto-propagation to Existing Projects**: When a bundle is updated and re-registered, provide a `skillmeat bundle propagate` command that applies the diff to already-scaffolded projects with a dry-run preview.
  _Status_: deferred
  _Rationale_: Requires artifact versioning and conflict resolution UX that is not yet implemented in the core platform.

- **[BL-3] CLI Subcommand for Bundle Operations**: Add a top-level `skillmeat bundle` subcommand that wraps `build-starter-bundle.py` as a first-class CLI command (rather than a standalone Python script).
  _Status_: planned
  _Rationale_: Improves discoverability and removes the need for direct Python invocation. Tracked in the scaffold CLI roadmap.

- **[BL-4] Incremental Build Mode**: Support rebuilding only changed files rather than clearing the output directory on every run.
  _Status_: candidate
  _Rationale_: Build times grow as the bundle expands. Current full-rebuild approach is simple but wasteful for iterative development.

- **[BL-5] Variable Validation at Build Time**: Warn (or fail) when `--project-name` or `--project-description` are left at their default `{{VAR}}` placeholder values, indicating the caller forgot to supply them.
  _Status_: candidate
  _Rationale_: Deployed bundles with unresolved tokens are confusing for end users.

- **[BL-6] Recommended Hook Auto-Parameterization**: Extend the build script to auto-substitute source paths in recommended-tier hooks based on `--source-path` arguments provided at build time.
  _Status_: candidate
  _Rationale_: Currently deployers must manually edit four hook files after deployment; this is error-prone.

---

## 8. Success Signals

- `python scripts/build-starter-bundle.py --dry-run` completes without errors and prints ~435 file entries.
- `python scripts/build-starter-bundle.py --project-name X ...` produces a `dist/starter-bundle/` directory with `CLAUDE.md` containing the substituted project name and no unresolved `{{VAR}}` tokens in the two parameterized files.
- `skillmeat scaffold --full` on a new empty directory produces a `.claude/` tree containing at least the core tier artifacts.
- `bundle-manifest.toml` in the output directory has a `file_count` matching the number of files actually present.
- Security pre-flight rejects a bundle containing a `.env` file and exits non-zero.
- After deployment, `/analyze:symbols:symbols-update` successfully regenerates `ai/symbols-*.json` for the target project (confirming the `symbols/` skill is correctly deployed).
- The `dev-execution` skill is invokable via `Skill("dev-execution")` in the target project without errors.

---

## 9. Changelog

### v1.0.0 — 2026-05-25

- Initial SPEC.md authored at `scripts/bundle/SPEC.md`
- Capability matrix: 11 intents covering build, deploy, parameterize, register, and validate workflows
- Structure overview: three-tier system documented with approximate file and size counts
- Integration points: scaffold CLI, web UI, build script, API paths
- Variable contract: 5 variables documented with defaults and fallback behavior
- 8 invariants documented (excluded-tier enforcement, security pre-flight, chrome-devtools exclusion, parameterized template behavior, output-clearing, manifest generation order, symbol data regeneration, hook path parameterization)
- Enhancement backlog: 6 entries (BL-1 through BL-6)
