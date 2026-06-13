# Documentation Policy Spec

**Version**: 1.0 (Compressed)
**Purpose**: Documentation rules and patterns
**Token Target**: ~250 lines
**Format**: Dense, structured, AI-optimized

---

## MkDocs Site Structure

SkillMeat documentation is built with MkDocs Material theme and includes auto-generated CLI reference via mkdocs-click.

- **Config**: `mkdocs.yml` (repo root)
- **Content dir**: `docs/user/` (`docs_dir` setting)
- **Full patterns reference**: `.claude/context/key-context/docs-site-patterns.md`

### Navigation (6 tabs)

| Tab | Content | When to add pages here |
|-----|---------|----------------------|
| Home | Landing page (`index.md`) | Rarely changes |
| Getting Started | Quickstart, auth setup, examples | New onboarding flows |
| Guides | Feature docs grouped by domain | New feature guides, usage docs |
| CLI Reference | CLI overview + auto-generated reference | CLI commands auto-update via mkdocs-click |
| Administration | Server setup, config, migration | Platform/infra docs |
| Resources | Release notes, beta, training | New releases, training material |

When adding a new user doc: create the `.md` file under `docs/user/`, then add it to the appropriate tab/section in `mkdocs.yml`.

### Build & Validation

```bash
# Build with strict link validation
mkdocs build --strict

# Local preview
mkdocs serve
```

**Validation command**: Always run `mkdocs build --strict` before committing documentation changes to catch broken links. Cross-repo link warnings are downgraded to info-level and do not fail the build.

### Screenshots

**Source of truth**: `.github/readme/data/screenshots.json` (shared with README build)
**Bridge hook**: `docs/hooks/screenshot_bridge.py` — runs on every `mkdocs build`/`serve`
**Generated dirs** (gitignored): `docs/user/assets/screenshots/`, `docs/user/_includes/`

**Anti-pattern**: Never manually copy PNGs into `docs/user/assets/screenshots/` — the bridge hook manages this directory and will overwrite manual changes.

To add a screenshot to a doc page:
1. Add entry to `.github/readme/data/screenshots.json` with `status: "captured"`
2. Run `mkdocs serve` — hook copies it and regenerates snippets
3. Reference with `--8<-- "_includes/screenshots/{feature}.md"` (all tagged screenshots) or direct image link

### CLI Reference Auto-Generation

The file `docs/user/guides/cli/reference.md` is auto-generated from the SkillMeat CLI source via mkdocs-click directives. It includes:

- All commands, subcommands, options, and arguments
- Auto-generated anchor links (format: `#skillmeat-command-name`)
- Environment variables and version spec reference

**Anti-pattern**: Do NOT manually edit the command sections of `reference.md` — changes will be overwritten on rebuild. For prose documentation with examples, edit `docs/user/guides/cli/commands.md` instead.

### Cross-Linking CLI Documentation

Two complementary CLI docs exist:

| Document | Purpose | Auto-Generated |
|----------|---------|-----------------|
| `cli/commands.md` | Prose guide with examples, patterns, workflows | No |
| `cli/reference.md` | Complete auto-generated reference | Yes (mkdocs-click) |

When adding CLI documentation:
- **Procedural content, examples, workflows** → `commands.md`
- **Complete reference of all options** → `reference.md` (auto-generated)
- **Cross-links from guides** → Point to `cli/reference.md` for comprehensive option reference

---

## Core Principle

**Create documentation ONLY when**:

1. Explicitly tasked (PRD, plan, request)
2. Absolutely necessary (essential info)
3. Fits allowed bucket (see below)

**Rule**: More docs ≠ better. When uncertain → don't create.

---

## Strictly Prohibited

| ✗ Never Create | Why | Alternative |
|----------------|-----|-------------|
| Debugging summaries | Becomes outdated | Git commit message |
| Multiple progress/phase | Creates sprawl | ONE per phase |
| Unorganized context | Hard to find | Structured directories |
| Ad-hoc observations | Fragmentation | Monthly log |
| Session notes as docs | Temporary context | Keep in worknotes |
| Daily/weekly reports | Documentation debt | Git commits + phase progress |

### Prohibited Examples

```plaintext
❌ "2025-11-03-bug-fix-context.md"          → git commit
❌ "phase-1-3-progress.md"                  → ONE per phase
❌ "observations-week-1.md"                 → monthly log
❌ "issues-encountered.md"                  → worknotes or commit
❌ "why-we-changed-X.md"                    → ADR or phase context
❌ "random-notes.md"                        → organized structure
```

---

## Allowed Tracking Docs

### Progress Tracking (One Per Phase)

| Field | Value |
|-------|-------|
| **Purpose** | Track progress, tasks, blockers, next steps |
| **Location** | `.claude/progress/[prd-name]/phase-[N]-progress.md` |
| **Limit** | ONE per phase |
| **When** | Multi-phase PRD implementations |
| **Audience** | AI agents (session continuity) |

### Context/Notes (One Per Phase)

| Field | Value |
|-------|-------|
| **Purpose** | Implementation decisions, technical notes, gotchas |
| **Location** | `.claude/worknotes/[prd-name]/phase-[N]-context.md` |
| **Limit** | ONE per phase |
| **Content** | Decisions, patterns, integration notes |
| **Audience** | AI agents + developers |

### Monthly Observations

| Field | Value |
|-------|-------|
| **Purpose** | Patterns, learnings, insights |
| **Location** | `.claude/worknotes/observations/observation-log-MM-YY.md` |
| **Format** | Brief bullets (1-2 lines each) |
| **Limit** | ONE per month |

### Monthly Bug-Fix Tracking

| Field | Value |
|-------|-------|
| **Purpose** | Brief reference of significant fixes |
| **Location** | `.claude/worknotes/fixes/bug-fixes-tracking-MM-YY.md` |
| **Format** | Brief bullets (1-2 lines + commit) |
| **Limit** | ONE per month |

### Other Changelog Types

| Field | Value |
|-------|-------|
| **When** | Explicitly in PRD/plan/request |
| **Examples** | CHANGELOG.md, release notes |
| **Requirement** | Must be planned work |

---

## Directory Structure

```plaintext
.claude/
├── progress/[prd-name]/
│   ├── phase-1-progress.md      # ONE per phase
│   ├── phase-2-progress.md
│   └── phase-3-progress.md
│
├── worknotes/
│   ├── [prd-name]/
│   │   ├── phase-1-context.md   # ONE per phase
│   │   ├── phase-2-context.md
│   │   └── phase-3-context.md
│   │
│   ├── fixes/
│   │   └── bug-fixes-tracking-MM-YY.md  # ONE per month
│   │
│   └── observations/
│       └── observation-log-MM-YY.md     # ONE per month
│
└── agents/[agent-name]/         # Agent configs
```

### Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Progress | `phase-[N]-progress.md` | `phase-2-progress.md` |
| Context | `phase-[N]-context.md` | `phase-2-context.md` |
| Bug fixes | `bug-fixes-tracking-MM-YY.md` | `bug-fixes-tracking-11-25.md` |
| Observations | `observation-log-MM-YY.md` | `observation-log-11-25.md` |

### Organization Rules

1. **By PRD**: Group progress/context by PRD name
2. **By Month**: Group fixes/observations by month (MM-YY)
3. **One Per Phase**: Never multiple for same phase
4. **Consistent Naming**: Exact patterns above
5. **Flat Structure**: No subdirectories in PRD folders

---

## Allowed Documentation Buckets

| Bucket | Purpose | Location | Examples |
|--------|---------|----------|----------|
| **User** | Help users | `/docs/user/`, `/docs/user/guides/` | Setup, tutorials, troubleshooting |
| **Developer** | Help devs | `/docs/dev/`, `/docs/dev/development/` | API docs, integration guides |
| **Architecture** | Design decisions | `/docs/dev/architecture/`, `/docs/dev/designs/` | ADRs, diagrams, specs |
| **README** | Document projects | Root of project/package/module | Project/package READMEs |
| **Configuration** | Setup/deploy | `/docs/configuration/`, `/docs/deployment/` | Env setup, deploy guides |
| **Test** | Testing strategy | `/docs/ops/testing/` | Test plans, strategies |
| **Product** | Requirements | `/docs/project_plans/`, `/docs/product/` | PRDs, impl plans |
| **Tracking** | Progress/context | `.claude/progress/`, `.claude/worknotes/` | Phase tracking (structured) |

---

## Frontmatter Requirements

**ALL docs in `/docs/` MUST include frontmatter** (tracking docs excepted):

```yaml
---
title: "Clear, Descriptive Title"
description: "1-2 sentence summary"
audience: [ai-agents, developers, users, design, pm, qa]
tags: [relevant, searchable, keywords]
created: 2025-11-03
updated: 2025-11-03
category: "bucket-name"
status: draft|review|published|deprecated
related:
  - /docs/path/to/related.md
---
```

### Frontmatter Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `title` | Searchable title | "Authentication API" |
| `description` | Brief summary | "Guide to auth endpoints" |
| `audience` | Who reads | `[developers, ai-agents]` |
| `tags` | Keywords | `[api, auth, security]` |
| `created` | Creation date | `2025-11-03` |
| `updated` | Last modified | `2025-11-03` |
| `category` | Bucket name | `developer-documentation` |
| `status` | State | `draft`, `review`, `published` |
| `related` | Links | Array of doc paths |

### Category Options

`user-documentation`, `developer-documentation`, `architecture-design`, `api-documentation`, `configuration-deployment`, `test-documentation`, `product-planning`, `worknotes`

### Audience Options

`users`, `developers`, `ai-agents`, `design`, `pm`, `qa`, `devops`

---

## Documentation vs. Worknotes

| Use `.claude/worknotes/` For | Use `/docs/` For |
|------------------------------|------------------|
| Exploration/investigation logs | Permanent published docs |
| Debugging sessions/findings | User/developer guides |
| Temporary implementation context | Stable, supported info |
| Notes to remember | Official references |
| Status updates/progress | Architecture decisions |
| Day-to-day session notes | API documentation |

**Rule**: Never mix. Worknotes ≠ permanent documentation.

---

## Decision Checklist

Before creating ANY documentation:

1. **In allowed bucket?** → If no, don't create
2. **Explicitly tasked?** → If no, is it absolutely necessary?
3. **Will it become outdated?** → If yes, it's not permanent doc
4. **Already exists?** → Update existing, don't create new
5. **Is this a worknote?** → Keep in `.claude/worknotes/`

**Rule of Thumb**: If uncertain → don't create unless explicitly tasked.

---

## Common Anti-Patterns

### ❌ Anti-Pattern 1: Multiple Progress Docs

```plaintext
.claude/progress/proj/
├── phase-2-progress.md
├── phase-2-progress-updated.md    ❌ WRONG
└── phase-2-notes.md               ❌ WRONG
```

**Fix**: ONE file, update it.

### ❌ Anti-Pattern 2: Date-Prefixed Context

```plaintext
.claude/worknotes/
├── 2025-11-02-bug-fix.md          ❌ WRONG
└── 2025-11-03-feature.md          ❌ WRONG
```

**Fix**: Use monthly bug-fix tracking or git commit.

### ❌ Anti-Pattern 3: Daily/Weekly Observations

```plaintext
.claude/worknotes/observations/
├── observation-log-nov-1.md       ❌ WRONG
└── observation-log-week-1.md      ❌ WRONG
```

**Fix**: ONE monthly file: `observation-log-11-25.md`.

### ❌ Anti-Pattern 4: Worknotes in /docs/

```plaintext
docs/
├── worknotes/impl-notes.md        ❌ WRONG LOCATION
└── sessions/summary.md            ❌ WRONG LOCATION
```

**Fix**: Move to `.claude/worknotes/` with structure.

### ❌ Anti-Pattern 5: Debugging as Docs

```plaintext
docs/dev/development/
└── event-loop-issues-nov-2.md     ❌ WRONG
```

**Fix**: Git commit OR observation log OR phase context (as appropriate).

### ❌ Anti-Pattern 6: Missing Frontmatter

```markdown
# API Documentation
Some docs...
```

**Fix**: Add complete YAML frontmatter.

### ❌ Anti-Pattern 7: Consolidated Multi-Phase

```plaintext
.claude/progress/
└── phase-1-3-progress.md          ❌ WRONG
```

**Fix**: Separate files, one per phase.

---

## Validation Checks

### Check 1: Directory Structure

```bash
# Verify required directories exist
ls .claude/progress/
ls .claude/worknotes/fixes/
ls .claude/worknotes/observations/
ls docs/dev/api/
```

### Check 2: Naming Compliance

```bash
# Find non-conforming names
find .claude/progress -name "*progress*.md" | grep -v "phase-"
find .claude/worknotes -name "*.md" | grep -E "^[0-9]{4}-[0-9]{2}-"
find .claude/worknotes/observations | grep -v "observation-log-"
```

### Check 3: Frontmatter Presence

```bash
# Check for frontmatter in /docs/
for f in docs/**/*.md; do
  if ! head -1 "$f" | grep -q "^---"; then
    echo "Missing: $f"
  fi
done
```

### Check 4: Multiple Docs Per Phase

```bash
# Find PRDs with too many progress docs
for prd in .claude/progress/*/; do
  count=$(ls -1 "$prd"phase-*-progress.md 2>/dev/null | wc -l)
  if [ "$count" -gt 5 ]; then
    echo "Check: $prd"
  fi
done
```

---

## Quick Reference Matrix

| Task Type | Doc Type | Location | Naming |
|-----------|----------|----------|--------|
| Setup guide | Guide | `/docs/user/guides/` | Explicit |
| API endpoints | API ref | `/docs/dev/api/` | Explicit |
| Architecture | ADR | `/docs/dev/architecture/` | `adr-NNN.md` |
| Impl notes | Context | `.claude/worknotes/[prd]/` | `phase-N-context.md` |
| Phase progress | Progress | `.claude/progress/[prd]/` | `phase-N-progress.md` |
| Bug fixes (monthly) | Bug tracking | `.claude/worknotes/fixes/` | `bug-fixes-tracking-MM-YY.md` |
| Observations (monthly) | Obs log | `.claude/worknotes/obs/` | `observation-log-MM-YY.md` |
| Debugging | Commit msg | (git history) | Detailed message |
| Session notes | Temp worknotes | `.claude/worknotes/temp/` | Temporary |

---

## Enforcement Points

### Code Review Checklist

- [ ] Documentation explicitly tasked or necessary?
- [ ] Fits allowed bucket?
- [ ] If tracking: Correct structure? (dir, naming, one-per)
- [ ] If permanent: Complete frontmatter?
- [ ] No ad-hoc files? (date prefixes, unorganized, etc.)
- [ ] No multiple scattered docs for same phase?
- [ ] No debugging summaries as permanent docs?
- [ ] Directory structure matches spec?

**If any fail**: Request changes, point to policy.

---

## Lifecycle

### Progress Tracking Docs

- **During phase**: Active updates
- **After phase**: Archive or keep for 1 quarter
- **Decision point**: Convert to permanent or delete

### Context Docs

- **During phase**: Active notes
- **After phase**: Keep for 1 quarter
- **Decision point**: Becomes permanent doc or deleted

### Monthly Logs

- **During month**: Active updates
- **After month**: Keep indefinitely for reference
- **Review**: Annually, consolidate insights into guides

---

## Summary

**Documentation Policy in 3 Rules**:

1. **Create only when**: Explicitly tasked OR absolutely necessary OR fits allowed bucket
2. **Structure strictly**: ONE per phase, monthly logs, exact naming, organized directories
3. **Enforce consistently**: AI agents (CLAUDE.md) + humans (code review)

**Key Insight**: Quality over quantity. One well-organized doc > five scattered ones.

**Token Efficiency**: 250 lines (compressed from 1323) = 81% reduction while preserving all rules.
