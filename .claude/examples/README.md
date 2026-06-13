# Documentation Templates

This directory contains **template files** for creating tracking documentation following the project's documentation policy. These are intentionally brief templates showing structure and format, not full SkillMeat-specific examples.

## Purpose

Provide reusable templates for creating allowed tracking documentation:

- **Progress Tracking** - Track implementation progress across phases
- **Context/Notes** - Document technical decisions and implementation approaches
- **Observation Logs** - Record development insights and learnings (monthly)
- **Bug Fix Tracking** - Brief monthly reference of significant bug fixes
- **Implementation Plans** - Detailed feature breakdown with phases and tasks

**Important**: These are templates (blank forms to fill in), not examples (completed documentation).

## What's Inside

### 1. Phase Progress Template
**File**: `progress/phase-progress-template.md`

Track implementation progress for a specific phase of work.

**Use When**: Working on multi-phase implementations from a PRD

**Key Sections**:
- Status tracking (phase, start date, story description)
- Completed tasks with checkboxes
- Current phase work items
- Acceptance criteria validation
- Decisions log with dates
- Files created/modified
- Next steps and blockers

**Location Pattern**: `.claude/progress/[prd-name]/phase-[N]-progress.md`

**Limit**: ONE per phase (not multiple scattered files)

---

### 2. Phase Context Template
**File**: `worknotes/phase-context-template.md`

Document implementation decisions, technical notes, and architectural considerations for a phase.

**Use When**: Documenting technical decisions and implementation approaches during a phase

**Key Sections**:
- Implementation context
- Technical decisions (with options considered)
- Architecture notes
- Integration patterns
- Implementation gotchas
- Known issues and workarounds
- Next phase considerations

**Location Pattern**: `.claude/worknotes/[prd-name]/phase-[N]-context.md`

**Limit**: ONE per phase (organized by PRD name)

---

### 3. Observation Log Template
**File**: `worknotes/observation-log-template.md`

Track observations, learnings, patterns, and insights discovered during development.

**Use When**: Monthly consolidation of development insights (not daily/weekly)

**Key Sections**:
- Architecture patterns
- Performance insights
- Development workflow learnings
- Integration patterns
- Testing & quality observations
- Code quality notes
- Technical debt tracking

**Format**: Brief bullet points (1-2 lines per observation)

**Location Pattern**: `.claude/worknotes/observations/observation-log-MM-YY.md`

**Limit**: ONE per month

---

### 4. Bug Fix Tracking Template
**File**: `worknotes/bug-fixes-tracking-template.md`

Brief reference of significant bug fixes completed in a month.

**Use When**: Monthly consolidation of significant bug fixes

**Format**:
```markdown
## YYYY-MM-DD: Bug Title
**Issue**: Brief description
**Root Cause**: What caused it
**Fix**: What was fixed
**Location**: Files affected
**Commit**: Commit reference
**Related**: Related context
```

**Content**: Very brief (1-2 lines per fix) with commit references

**Location Pattern**: `.claude/worknotes/fixes/bug-fixes-tracking-MM-YY.md`

**Limit**: ONE per month

---

### 5. Implementation Plan Template
**File**: `plans/implementation-plan-template.md`

Detailed breakdown of feature implementation with phases and tasks.

**Use When**: Planning detailed implementation of a feature or epic from a PRD

**Key Sections**:
- Story summary (epic, scope, complexity)
- File changes (create, modify, delete)
- Component architecture
- Technical specifications
- Integration points
- Test coverage (unit, integration, E2E)
- Observability & monitoring
- Acceptance criteria
- Dependencies and risks

**Location Pattern**: `/docs/project_plans/[prd-name]/implementation-plan.md`

**Required**: When implementing features from a PRD

---

## How to Use These Templates

### Quick Start

```bash
# 1. Copy template to appropriate location
cp examples/progress/phase-progress-template.md \
   .claude/progress/my-feature/phase-1-progress.md

# 2. Edit and replace {{PLACEHOLDERS}} with your values
# 3. Fill in sections with actual content
# 4. Follow naming conventions (see below)
```

### Step-by-Step Workflow

#### Starting a New Phase

```bash
# Step 1: Copy progress template
cp examples/progress/phase-progress-template.md \
   .claude/progress/user-authentication/phase-1-progress.md

# Step 2: Copy context template
cp examples/worknotes/phase-context-template.md \
   .claude/worknotes/user-authentication/phase-1-context.md

# Step 3: Replace placeholders
# Edit both files and replace:
# - {{EPIC_ID}} with your epic ID
# - {{PHASE_NUMBER}} with 1
# - {{FEATURE_NAME}} with "User Authentication"
# - {{YYYY-MM-DD}} with current date

# Step 4: Fill in actual content as you work
```

#### Monthly Observation Log

```bash
# Copy observation log template
cp examples/worknotes/observation-log-template.md \
   .claude/worknotes/observations/observation-log-11-25.md

# Replace {{Month Year}} with current month
# Add observations as brief bullet points throughout the month
```

#### Monthly Bug Fix Tracking

```bash
# Copy bug fix tracking template
cp examples/worknotes/bug-fixes-tracking-template.md \
   .claude/worknotes/fixes/bug-fixes-tracking-11-25.md

# Replace {{Month Year}} with current month
# Add brief fix summaries with commit references as bugs are fixed
```

### Placeholder Variables

All templates use `{{PLACEHOLDER}}` format for variables:

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{EPIC_ID}}` | Epic identifier | `AUTH-EPIC-1`, `NAV-E001` |
| `{{STORY_ID}}` | Story identifier | `UI-005`, `STORY-123` |
| `{{PHASE_NUMBER}}` | Phase number | `1`, `2`, `3` |
| `{{PHASE_NAME}}` | Phase name | `Analysis & Planning`, `In Progress` |
| `{{FEATURE_NAME}}` | Feature name | `User Authentication`, `Dashboard` |
| `{{YYYY-MM-DD}}` | Date | `2025-11-05` |
| `{{MM-YY}}` | Month-year | `11-25` (November 2025) |
| `{{Month Year}}` | Month and year | `November 2025` |
| `{{PROJECT_NAME}}` | Your project name | `MyApp`, `MyService` |

**Search and Replace**:
```bash
# Replace all placeholders in a file
sed -i 's/{{EPIC_ID}}/AUTH-EPIC-1/g' phase-1-progress.md
sed -i 's/{{PHASE_NUMBER}}/1/g' phase-1-progress.md
sed -i 's/{{FEATURE_NAME}}/User Authentication/g' phase-1-progress.md
```

### Naming Conventions

**Follow these exact patterns** for consistency:

#### Progress Tracking
```
✅ phase-1-progress.md
✅ phase-2-progress.md
✅ phase-3-progress.md

❌ phase-1-progress-updated.md
❌ phase-1-2-progress.md
❌ progress-phase-1.md
```

#### Phase Context
```
✅ phase-1-context.md
✅ phase-2-context.md
✅ phase-3-context.md

❌ phase-1-context-notes.md
❌ phase-1-worknotes.md
❌ context-phase-1.md
```

#### Observation Logs
```
✅ observation-log-11-25.md (November 2025)
✅ observation-log-12-25.md (December 2025)
✅ observation-log-01-26.md (January 2026)

❌ observation-log-nov-3.md
❌ observations-week-1.md
❌ observation-log-2025-11.md
```

#### Bug Fix Tracking
```
✅ bug-fixes-tracking-11-25.md
✅ bug-fixes-tracking-12-25.md
✅ bug-fixes-tracking-01-26.md

❌ bugs-11-25.md
❌ bug-fixes-nov-2025.md
❌ fixes-tracking-11-25.md
```

## Directory Structure Pattern

When creating tracking docs from templates, follow this **exact structure**:

```
.claude/
├── progress/                                    # Phase progress tracking
│   └── [prd-name]/                             # Organized by PRD
│       ├── phase-1-progress.md                 # ONE per phase
│       ├── phase-2-progress.md
│       └── phase-3-progress.md
│
├── worknotes/                                   # Implementation context & notes
│   ├── [prd-name]/                             # Organized by PRD
│   │   ├── phase-1-context.md                  # ONE per phase
│   │   ├── phase-2-context.md
│   │   └── phase-3-context.md
│   │
│   ├── fixes/                                   # Bug fix tracking
│   │   ├── bug-fixes-tracking-11-25.md         # ONE per month
│   │   ├── bug-fixes-tracking-12-25.md
│   │   └── bug-fixes-tracking-01-26.md
│   │
│   └── observations/                            # Development observations
│       ├── observation-log-11-25.md            # ONE per month
│       ├── observation-log-12-25.md
│       └── observation-log-01-26.md
│
└── [Other .claude directories...]
```

### Example Directory for a Feature

```
.claude/
├── progress/
│   └── user-authentication/
│       ├── phase-1-progress.md
│       ├── phase-2-progress.md
│       └── phase-3-progress.md
│
└── worknotes/
    ├── user-authentication/
    │   ├── phase-1-context.md
    │   ├── phase-2-context.md
    │   └── phase-3-context.md
    │
    ├── fixes/
    │   └── bug-fixes-tracking-11-25.md
    │
    └── observations/
        └── observation-log-11-25.md
```

## Documentation Policy Compliance

These templates follow the project's documentation policy exactly:

### ✅ Allowed Tracking Documentation

1. **Progress Tracking** - ONE per phase, not multiple scattered files
2. **Context/Notes** - ONE per phase, organized by PRD name
3. **Observation Logs** - ONE per month, brief bullet points
4. **Bug Fix Tracking** - ONE per month, brief with commit references
5. **Implementation Plans** - ONE per feature/epic

### ❌ Prohibited Documentation

**DO NOT Create:**

- ❌ Multiple progress docs for the same phase (`phase-1-progress-v2.md`)
- ❌ Ad-hoc debugging summaries (use git commits instead)
- ❌ Unstructured context files with date prefixes (`2025-11-03-context.md`)
- ❌ Daily/weekly observation logs (use monthly consolidation)
- ❌ Session notes as permanent docs (keep in temporary worknotes)

**Examples of What NOT to Create:**
```
❌ .claude/worknotes/2025-11-03-celery-event-loop-fix-context.md
   → Should be: git commit message or entry in bug-fixes-tracking-11-25.md

❌ .claude/progress/my-feature/phase-1-progress-updated.md
   → Should be: Update existing phase-1-progress.md, not create new file

❌ .claude/worknotes/observations/nov-3-observations.md
   → Should be: Entry in observation-log-11-25.md (monthly, not daily)

❌ .claude/worknotes/my-feature/phase-2-context-notes.md
   → Should be: phase-2-context.md (follow naming convention)
```

### Key Principles

1. **One Per Phase**: Don't create multiple progress or context docs for the same phase — update the existing one
2. **Organized Structure**: Use consistent directory structure (see above)
3. **Explicit Need**: Only create when working on multi-phase implementations from a PRD
4. **Concise Content**: Keep notes brief and actionable (1-2 lines for observations/fixes)
5. **Temporary Nature**: These are working documents, not permanent documentation

## Templates vs. Full Examples

| Type | Purpose | Content | Project-Specific |
|------|---------|---------|------------------|
| **Templates** (this directory) | Blank forms to fill in | `{{PLACEHOLDERS}}` | ❌ No - Generic |
| **Full Examples** | Real-world reference | Actual completed docs | ✅ Yes - Project-specific |

**Templates**: Use these to create new tracking docs for your project

**Full Examples**: If you need to see completed examples, refer to actual project documentation in `.claude/progress/`, `.claude/worknotes/`, etc.

### Why Templates Instead of Examples?

This directory contains **templates only** (not 60+ full SkillMeat-specific examples) because:

1. **Reduces Bloat**: Templates are ~50 lines each vs. full examples at 200-500 lines
2. **Prevents Confusion**: Users fill in their project data, not edit out SkillMeat-specific content
3. **Encourages Adaptation**: Forces users to think about their project's needs
4. **Easier Maintenance**: Updating 5 templates vs. 60+ examples
5. **Clearer Intent**: Shows structure and format, not implementation details

**If you need full examples**: Look at your project's actual tracking docs in `.claude/progress/` and `.claude/worknotes/` once you've started using the templates.

## Customization for Your Project

### Variable Naming Conventions

Adapt placeholder names to match your project:

```markdown
# Generic pattern (templates use this)
{{EPIC_ID}}-{{STORY_ID}}

# Adapt to your project's pattern
{{FEATURE_ID}}-{{TASK_ID}}
{{JIRA_KEY}}
{{LINEAR_ISSUE_ID}}
{{GITHUB_ISSUE_NUMBER}}
```

### Section Customization

**Add sections** based on your needs:
- Security considerations
- Performance benchmarks
- Accessibility requirements
- Design system compliance
- Compliance/regulatory notes

**Remove sections** not relevant:
- Sections you don't track
- Metrics you don't measure
- Processes you don't follow

**Adapt sections** to your workflow:
- Change section names to match your process
- Adjust format to your team's preferences
- Add custom fields your team needs

### Integration with Your Tools

Replace tool/framework references with your stack:

| Template Reference | Your Project |
|-------------------|--------------|
| `Clerk` | `Auth0`, `Supabase Auth`, `Custom Auth` |
| `FastAPI` | `Express`, `Django`, `Rails`, `Spring` |
| `Next.js` | `React`, `Vue`, `SvelteKit`, `Angular` |
| `Linear` | `Jira`, `GitHub Issues`, `Trello`, `Asana` |
| `SQLAlchemy` | `Prisma`, `TypeORM`, `Sequelize` |

## Anti-Patterns to Avoid

### ❌ Multiple Files Per Phase

```
❌ .claude/progress/my-feature/phase-1-progress.md
❌ .claude/progress/my-feature/phase-1-progress-updated.md
❌ .claude/progress/my-feature/phase-1-progress-v2.md

✅ .claude/progress/my-feature/phase-1-progress.md (just update this one)
```

### ❌ Ad-Hoc Debugging Summaries

```
❌ .claude/worknotes/2025-11-03-celery-event-loop-fix-context.md
❌ .claude/worknotes/debugging-session-nov-3.md

✅ Git commit message with detailed explanation
✅ Entry in bug-fixes-tracking-11-25.md if significant
```

### ❌ Daily/Weekly Observation Logs

```
❌ .claude/worknotes/observations/nov-3-observations.md
❌ .claude/worknotes/observations/week-1-observations.md
❌ .claude/worknotes/observations/observations-2025-11-03.md

✅ .claude/worknotes/observations/observation-log-11-25.md (monthly consolidation)
```

### ❌ Inconsistent Naming

```
❌ phase-2-context-notes.md
❌ progress-phase-1.md
❌ bugs-11-25.md

✅ phase-2-context.md
✅ phase-1-progress.md
✅ bug-fixes-tracking-11-25.md
```

## When to Use Each Template

### Use Progress Template When:
- Starting a new phase of a multi-phase feature
- Need to track tasks across multiple sessions
- Working from a PRD with defined acceptance criteria
- Coordinating work with other team members

### Use Context Template When:
- Making architectural or technical decisions
- Documenting implementation approaches
- Recording gotchas and learnings
- Need to explain "why" to future developers

### Use Observation Log When:
- End of month consolidation of learnings
- Discovered patterns that inform future work
- Performance insights worth tracking
- Architectural learnings from implementation

### Use Bug Fix Tracking When:
- End of month consolidation of significant fixes
- Bug required non-trivial debugging
- Fix has implications for other features
- Root cause is worth documenting

### Use Implementation Plan When:
- Starting work on a new feature or epic
- PRD exists but needs detailed technical breakdown
- Need to define phases, tasks, and acceptance criteria
- Coordinating multi-phase implementation

## See Also

- **[TEMPLATES.md](./TEMPLATES.md)** - Detailed template usage guide
- **[CLAUDE.md](../CLAUDE.md)** - Documentation policy and tracking rules (if working in SkillMeat project)
- **[TEMPLATIZATION_GUIDE.md](../TEMPLATIZATION_GUIDE.md)** - Comprehensive customization guide for entire config

---

**Created**: 2025-11-05
**Updated**: 2025-11-05
**Purpose**: Provide reusable templates for creating tracking documentation
**Audience**: Developers, AI agents
**Compliance**: Follows structured tracking documentation policy exactly
