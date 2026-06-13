# SkillMeat Instance Starter Bundle

The Instance Starter Bundle packages SkillMeat's AI-assisted development methodology — rules, skills, agents, commands, configuration, and specs — into a single deployable artifact for new Claude Code projects. Deploy it once to any project directory and your agents arrive pre-configured with orchestration patterns, delegation modes, progress tracking, debugging workflows, and more.

The bundle is assembled by `scripts/build-starter-bundle.py` using `scripts/starter-bundle-manifest.yaml` as its inclusion list. Two template files (`CLAUDE.md` and `intents/intent.md`) are parameterized with project-specific values at build time; all other files are copied verbatim.

## What's Included

The manifest organizes artifacts into three tiers. The build script defaults to including all tiers.

### Core Tier (always deployed)

Portable methodology essentials that work for any project type:

- **5 methodology rules** — context budget invariants, debugging invariants, delegation modes, LSP diagnostic handling, progress CLI-only policy
- **9 core skill frameworks** — `dev-execution`, `artifact-tracking`, `planning`, `debugging`, `symbols`, `confidence-check`, `recovering-sessions`, `skill-builder`, `skill-creator`
- **~47 agent definitions** — architects, reviewers, AI/orchestration agents, PM agents, fix-team, tech writers, scaffolding agents
- **Workflow commands** — `/dev:*`, `/plan:*`, `/fix:*`, `/review:*`, `/analyze:*`, `/test:*`, `/artifacts:*`, `/pm:*`, `/release:pr`
- **Multi-model config** — `multi-model.toml`, `subagents.json`, config index and README
- **PM templates** — feature-request, implementation-plan, spike-document, task-breakdown
- **Methodology specs** — changelog spec, doc policy, version-bump procedure, project-tracking spec, multi-model usage spec, Claude fundamentals spec, artifact-structure conventions, skills index
- **Key-context playbooks** — context loading, debugging patterns, agent-teams patterns, layered-context governance, testing patterns
- **Utility scripts** — file, git, validation, contract, architecture, artifact, story, CI, JSON, and report utils
- **Hooks** — Python/JS auto-formatters, test runner, git-add, pre-compact state capture, staleness check
- **Example templates** — implementation plan, phase progress, bug-fix tracking, observation log, phase context
- **Parameterized files** — `CLAUDE.md` and `intents/intent.md` (project-specific values substituted at build time)

**Estimated size**: ~342 files, ~3.5 MB

### Recommended Tier (deployed by default)

Domain-specific supplements for UI/design, advanced tooling, and integrations:

- **~29 additional skill directories** — aesthetic, frontend-design, cognitive-design, design-system-patterns, interface-design, README management, session continuity, context distillation, plan review, Claude Code patterns, changelog generation, DevOps, PostgreSQL, Docker Compose, auth patterns (Better Auth, Clerk), Chrome DevTools references, Gemini CLI, Codex, Bob Shell, Nano Banana, Sora, NotebookLM, project-scaffolder
- **11 additional agent files** — UI engineer (enhanced), mobile app builder, vector database engineer, full UI/UX team, web optimization team, API designer, content curator
- **6 supplementary commands** — integration commands (GitHub, Linear, Trello), AI meta-commands, story loader, animation command
- **6 additional key-context playbooks** — React/shadcn patterns, Next.js patterns, FastAPI router patterns, repository architecture, project onboarding, spec-backed skills convention
- **2 supplementary specs** — README build system spec, bug automation scripts reference
- **4 parameterizable hooks** — symbol graph auto-update, style check, Python test runner, web test runner (all require path substitution for the target project)
- **1 supplementary doc** — claudectl quickstart guide

**Estimated size**: ~93 files, ~1.8 MB

### Excluded Tier (never packaged)

SkillMeat product-specific content (collection management, marketplace, demo workflows, internal API/web patterns), ephemeral artifacts (progress files, worknotes, worktrees, capsules), and historical plans/analyses. See `scripts/starter-bundle-manifest.yaml` for the full list with reasons.

## Quick Start

### Deploy via SkillMeat Scaffold (recommended)

```bash
# Full scaffolding: interactive init + starter deployment
skillmeat scaffold --full

# Deploy starters only (project already initialized)
skillmeat scaffold --standard
```

All enabled org starters deploy automatically. The bundle is registered as a template via:

```bash
skillmeat template list --kind project-starter
```

### Build Manually

Use the build script when you need to generate a customized bundle:

```bash
python scripts/build-starter-bundle.py \
  --project-name "MyProject" \
  --project-description "AI-assisted Python backend with React frontend" \
  --author "Your Team" \
  --architecture-description "FastAPI + PostgreSQL + Next.js 15" \
  --output dist/starter-bundle/
```

**Preview without writing files:**

```bash
python scripts/build-starter-bundle.py \
  --project-name "MyProject" \
  --project-description "..." \
  --author "..." \
  --architecture-description "..." \
  --dry-run
```

**Include recommended tier only:**

```bash
python scripts/build-starter-bundle.py \
  --tier recommended \
  ...
```

After building, register the bundle with SkillMeat:

```bash
skillmeat add dist/starter-bundle/
skillmeat template create \
  --kind project-starter \
  --name "instance-starter-bundle" \
  --source dist/starter-bundle/ \
  --enable
```

## Variable Substitution

Two files are parameterized at build time using `{{VAR}}` tokens. All other files copy verbatim.

| Variable | File(s) | Description |
|----------|---------|-------------|
| `PROJECT_NAME` | `CLAUDE.md`, `intents/intent.md` | Short project identifier (e.g., `MyApp`) |
| `PROJECT_DESCRIPTION` | `CLAUDE.md`, `intents/intent.md` | One-line description of the project's purpose |
| `AUTHOR` | `CLAUDE.md` | Primary author name or org (e.g., `Platform Team`) |
| `ARCHITECTURE_DESCRIPTION` | `CLAUDE.md` | Short paragraph describing the tech stack |
| `DATE` | `intents/intent.md` | ISO-8601 creation date (auto-set to today if omitted) |

Unresolved tokens (`{{VAR}}`) remain as-is if a variable is not provided. The build script warns for any missing templates but does not fail.

## Customization

To add, remove, or recategorize artifacts in the bundle:

1. **Edit the manifest** — `scripts/starter-bundle-manifest.yaml` controls the full inclusion list. Each entry specifies `path`, `type` (`file` or `directory`), and an optional `comment`.

2. **Add a template file** — Place a `.tmpl` file in `scripts/templates/` (e.g., `myconfig.toml.tmpl`). Add the target path to `parameterized_templates` in the manifest.

3. **Rebuild** — Re-run the build script with your project variables.

4. **Re-register** — Run `skillmeat add` and `skillmeat template configure` to update the registered bundle.

For the complete manifest format, field reference, and validation rules, see the [Starter Bundle Manifest Guide](../../docs/user/dev/features/starter-bundle-manifest-guide.md).

## Security

The build script runs a pre-flight check before writing any files. It rejects bundles containing:

- `.env` files and variant patterns
- `*.token`, `*.key`, credential, or secret files
- `settings.local.*` overrides

Build fails with a clear error if any matched files are detected. The allowlist (`*.example`, `*.sample`, `*.template`, `no-secrets.md`) covers common placeholder files that are safe to include.

## Version and Compatibility

| Field | Value |
|-------|-------|
| Bundle version | `1.0.0` (set in `bundle_metadata.version` in the manifest) |
| Bundle kind | `project_starter` |
| Source project | `skillmeat` |
| Minimum SkillMeat | `v0.50.1` |
| Python (build script) | 3.9+ |
| YAML dependency | PyYAML (optional; falls back to built-in minimal parser) |

The bundle version in `bundle-manifest.toml` is separate from the SkillMeat application version. Increment `bundle_metadata.version` in the manifest when the bundle contents change significantly.
