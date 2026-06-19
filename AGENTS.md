# AGENTS.md

Research Foundry: a Markdown/YAML-first, evidence-first research control plane: it turns raw ideas into governed research swarms, evidence bundles, and claim-verified reports, with writebacks to MeatyWiki, SkillMeat, and CCDash

> Created: 2026-05-27 | Author: Nick Miethe

## Prime Directives

| Directive | Implementation |
|-----------|---------------|
| **Delegate everything** | Opus reasons & orchestrates; subagents implement |
| Token efficient | Symbol system, codebase-explorer |
| Rapid iteration | PRD → code → deploy fast |
| No over-architecture | YAGNI until proven |

### Opus Delegation Principle

**You are Opus. Tokens are expensive. You orchestrate; subagents execute.**

- Do **not** write code directly (Read/Edit/Write for implementation)
- Do **not** do token-heavy exploration yourself
- Do **not** read full implementation files before delegating
- **Always** delegate implementation to specialized subagents
- **Always** use codebase-explorer for pattern discovery
- **Focus** on reasoning, analysis, planning, and orchestration

**Delegation Pattern**:

```text
1. Analyze task → identify what needs to change
2. Delegate exploration → codebase-explorer finds files/patterns
3. Read progress YAML → get assigned_to and batch strategy
4. Delegate implementation → use Task() from Orchestration Quick Reference
5. Update progress → artifact-tracker marks tasks complete
6. Commit → only direct action Opus takes
```

**When you catch yourself about to edit a file**: STOP. Delegate instead.

**File context for subagents**: Provide file paths, not file contents. Subagents read files themselves. Only read files directly when planning decisions require understanding current state.

## Documentation Policy

**Allowed**:

- `/docs/` → User/dev/architecture docs (with frontmatter)
- `docs/project_plans/human-briefs/` → human-orchestrator planning lens
- `.Codex/progress/[prd]/` → ONE per phase (YAML+Markdown hybrid)
- `.Codex/worknotes/[prd]/` → ONE context.md per PRD (agent worknotes)
- `.Codex/worknotes/fixes/` → ONE per month
- `.Codex/worknotes/observations/` → ONE per month

**Prohibited**:

- Debugging summaries → git commit
- Multiple progress files per phase
- Daily/weekly reports
- Session notes as docs

---

## Command-Skill Bindings

**Commands do not automatically load skills.** When executing `/dev:*` or other workflow commands, you MUST explicitly invoke required skills using the `Skill` tool before proceeding.

### Required Skill Invocations

| Command                    | Required Skills                  | Invoke First                                               |
| -------------------------- | -------------------------------- | ---------------------------------------------------------- |
| `/dev:execute-phase`       | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:quick-feature`       | dev-execution                    | `Skill("dev-execution")`                                   |
| `/dev:implement-story`     | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:complete-user-story` | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:create-feature`      | dev-execution                    | `Skill("dev-execution")`                                   |
| `/plan:*`                  | planning                         | `Skill("planning")`                                        |
| `/analyze:symbols:*`       | symbols                          | CLI scripts (automatic via commands)                       |
| `/fix:debug`               | debug                            | `Skill("debug")`                                           |

### Symbol-First Exploration

**Pattern discovery uses symbols automatically** via `codebase-explorer` agent delegation.

When exploring code patterns before implementation:
1. Delegate to `Task("codebase-explorer", "Find [pattern]")` — uses symbols internally
2. Direct queries: `jq '.symbols[] | select(.layer == "service")' ai/symbols-api.json`
3. Token savings: ~150 tokens (symbols) vs 5–15K tokens (file reads)

### Enforcement Protocol

1. **First action** after receiving a listed command: Call `Skill()` for each required skill
2. **Do not proceed** with any other actions until skills are loaded
3. **Skill content** provides execution guidance that the command references

---

## Agent Delegation

**Mandatory**: All implementation work MUST be delegated. Opus orchestrates only.

### Model Selection

| Model | Budget | Use When |
|-------|--------|----------|
| **Opus 4.x** | High | Orchestration, deep reasoning, architectural decisions |
| **Sonnet 4.x** | Medium | Implementation, review, moderate reasoning (DEFAULT for subagents) |
| **Haiku 4.x** | Low | Mechanical search, extraction, simple queries |

**Default: Sonnet** — Sonnet is near-Opus for coding. Use Opus only for deep reasoning.

### Multi-Model Integration

External models are available as **opt-in** supplements. Codex Opus remains the sole orchestrator.

| Capability | Model | Trigger |
|-----------|-------|---------|
| Plan review (second opinion) | Codex / GPT | Opt-in checkpoint |
| PR cross-validation | Gemini Pro / Flash | Opt-in checkpoint |
| Debug escalation | Codex | After 2+ failed Codex cycles |
| Web research | Gemini Pro | Current web info needed |
| Image generation | Nano Banana Pro | Task requires image output |

### Implementation Agents

| Agent | Model | Skills | Permission |
|-------|-------|--------|------------|
| python-backend-engineer | sonnet | artifact-tracking | acceptEdits |
| ui-engineer-enhanced | sonnet | frontend-design, aesthetic, artifact-tracking | acceptEdits |
| ui-engineer | sonnet | frontend-design, aesthetic | acceptEdits |
| frontend-developer | sonnet | frontend-design | acceptEdits |
| frontend-architect | sonnet | - | acceptEdits |
| backend-architect | sonnet | - | acceptEdits |
| data-layer-expert | sonnet | - | acceptEdits |
| refactoring-expert | sonnet | - | acceptEdits |

### Exploration & Analysis

| Agent | Model | Skills | Permission |
|-------|-------|--------|------------|
| codebase-explorer | haiku | symbols | plan |
| search-specialist | haiku | - | plan |
| symbols-engineer | haiku | - | plan |
| task-decomposition-expert | haiku | - | plan |
| implementation-planner | sonnet | planning | plan |

### Review & Validation

| Agent | Model | Permission | disallowedTools |
|-------|-------|------------|-----------------|
| senior-code-reviewer | sonnet | plan | Write, Edit, Bash |
| task-completion-validator | sonnet | plan | Write, Edit |
| karen | opus | plan | Write, Edit |

### Orchestration (Opus Only)

| Agent | Model | Skills | Permission |
|-------|-------|--------|------------|
| lead-architect | opus | planning | default |
| lead-pm | opus | planning, artifact-tracking | default |
| spike-writer | opus | planning | default |
| ultrathink-debugger | opus | - | acceptEdits |
| platform-engineer | opus | - | acceptEdits |

### Documentation

| Agent | Model | Permission |
|-------|-------|------------|
| documentation-writer | haiku | acceptEdits |
| documentation-expert | haiku | acceptEdits |
| changelog-generator | haiku | acceptEdits |

### PM & Planning

| Agent | Model | Skills |
|-------|-------|--------|
| prd-writer | sonnet | planning |
| feature-planner | sonnet | planning, artifact-tracking |

### Context Budget Discipline

**Budget**: ~52K baseline leaves ~148K for work. Budget ~25–30K per phase.

**Key rules**:
- No `TaskOutput()` for file-writing agents (verify on disk instead)
- Task prompts < 500 words (paths, not contents)
- Don't explore for work you'll delegate
- Always scope Glob with `path`

---

## Orchestration-Driven Development

### File Locations

| Type | Location | Limit |
|------|----------|-------|
| Progress | `.Codex/progress/[prd]/phase-N-progress.md` | ONE per phase |
| Context | `.Codex/worknotes/[prd]/context.md` | ONE per PRD |

### CLI-First Updates

**Use CLI scripts for status updates** (0 agent tokens):

```bash
# Single task
python .Codex/skills/artifact-tracking/scripts/update-status.py \
  -f .Codex/progress/prd/phase-1-progress.md -t TASK-1.1 -s completed

# Batch update
python .Codex/skills/artifact-tracking/scripts/update-batch.py \
  -f FILE --updates "TASK-1.1:completed,TASK-1.2:completed"
```

### Orchestration Workflow

1. **Read YAML frontmatter** → get `parallelization.batch_N` and `tasks[].assigned_to`
2. **Execute batch in parallel** → single message with multiple Task() calls
3. **Update via CLI** → `update-batch.py` after tasks complete
4. **Validate** → `artifact-validator` before marking phase complete

### Commands

| Command | Purpose |
|---------|---------|
| `/dev:execute-phase N` | Execute phase N with orchestration |
| `Skill("artifact-tracking")` | Load skill for complex operations |

---

## Architecture Overview

**Research Foundry** — a Markdown/YAML-first, evidence-first research control plane: it turns raw ideas into governed research swarms, evidence bundles, and claim-verified reports, with writebacks to MeatyWiki, SkillMeat, and CCDash

Research Foundry is a thin, file-backed control plane — a Python `rf` CLI and `research_foundry` package. Markdown/YAML is the source of truth and the claim ledger is the authority: every material claim in a report maps to a source card or is labeled inference/speculation. Cheap models extract, expensive models synthesize, and governance (key profiles, policy rules, secret scanning) is enforced as a runtime gate. See `docs/projects/research-foundry/` for the MVP spec, implementation plan, and service contract.

### Artifact Types Supported

This project defines its own artifact types. See `docs/dev/architecture/artifact-type-reference.md` for the complete reference with detection signals and usage patterns.

### Project Structure

```
Research Foundry/
├── AGENTS.md               # This file — project methodology and agent config
├── intents/
│   └── intent.md           # Project mission, users, JTBD, principles
├── docs/                   # User/dev/architecture documentation
├── .Codex/                # Agent configuration, skills, rules, commands
│   ├── rules/              # Invariants and constraints
│   ├── skills/             # Workflow skill definitions
│   ├── agents/             # Agent persona definitions
│   ├── commands/           # Slash-command definitions
│   ├── config/             # Multi-model routing, subagent config
│   ├── specs/              # Methodology specifications
│   └── context/            # Key-context playbooks
└── ai/                     # Symbol graphs and AI artifacts
    └── symbols-*.json      # Pre-generated symbol graphs (project-specific)
```

---

## Development Commands

### Setup

| Command | Purpose |
|---------|---------|
| `pip install -e ".[dev]"` | Install Python project in dev mode |
| `uv tool install --editable .` | Install with uv (recommended) |
| `npm install` / `pnpm install` | Install frontend dependencies |

### Development

| Command | Purpose |
|---------|---------|
| `<start-command>` | Start dev server(s) |
| `<build-command>` | Build for production |
| `<test-command>` | Run test suite |

### Code Quality

| Command | Purpose |
|---------|---------|
| `black <src>` | Format Python code |
| `flake8 <src> --select=E9,F63,F7,F82` | Lint Python (errors only) |
| `mypy <src> --ignore-missing-imports` | Type check Python |
| `npx tsc --noEmit` | Type check TypeScript |

> **Note**: Replace `<start-command>`, `<build-command>`, and `<test-command>` with your project's actual commands after deployment.

---

## Key Cross-Cutting Patterns

### Version Compatibility (Python)

```python
# Required: Python 3.9+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
```

### Error Handling

```python
# CLI: Exit with sys.exit(1) on failure
# API: Raise HTTPException with status code
# Core: Raise domain-specific exceptions
```

### Type Hints

All Python code should include type hints throughout for IDE support and runtime safety. Use `from __future__ import annotations` for forward references.

### Security Patterns

- **Atomic Operations**: Use temp directories → atomic move for file writes
- **Validation**: All external inputs validated before use
- **Permissions**: Warn before destructive operations

---

## Progressive Disclosure Context

**Context loading ladder**:
1. Runtime truth (symbol graphs, OpenAPI spec if present)
2. Entry `AGENTS.md` for scope + invariants
3. Key-context playbooks for task routing
4. Deep context docs only when unresolved
5. Historical plans/reports only for rationale (verify behavior from runtime truth)

**Global rules** (minimal):
- `.Codex/rules/debugging.md` — Universal symbol-first debugging pointer
- `.Codex/rules/delegation-modes.md` — Five delegation modes (A–E) calibrating agent autonomy
- `.Codex/rules/context-budget.md` — Token budget invariants
- `.Codex/rules/lsp-diagnostics.md` — LSP diagnostic handling

**Key Context** (read when working in domain):
- `.Codex/context/key-context/context-loading-playbook.md` — Trigger matrix for what to read first
- `.Codex/context/key-context/debugging-patterns.md` — Bug categories, delegation patterns
- `.Codex/context/key-context/agent-teams-patterns.md` — Agent Teams vs subagents decision framework
- `.Codex/context/key-context/layered-context-governance.md` — Layer policy and token budgets
- `.Codex/context/key-context/testing-patterns.md` — Test structure and patterns

**Methodology skills** (load via `Skill()` tool):
- `dev-execution` — Unified execution engine
- `artifact-tracking` — CLI-first progress tracking
- `planning` — PRD/implementation plan/spike workflows
- `symbols` — Token-efficient codebase navigation

---

## Important Notes

- **Symbol graphs** (`ai/symbols-*.json`) are project-specific. Regenerate after deployment via `/analyze:symbols:symbols-update`.
- **Rich Output**: Use Rich library for CLI output (ASCII-compatible, no Unicode box-drawing in tests).
- **CI/CD**: Configure tests to run on your supported Python/Node.js version matrix.
- **Scopes**: `user` scope (`~/.Codex/`) is global; `local` scope (`./.Codex/`) is per-project.
