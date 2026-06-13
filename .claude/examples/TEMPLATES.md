# Documentation Templates

This directory contains template files that demonstrate the structure and format for creating tracking documentation following the SkillMeat documentation policy.

## Available Templates

### 1. Progress Tracking Template
**File**: `progress/phase-progress-template.md`
**Purpose**: Track implementation progress for a specific phase of work
**Location Pattern**: `.claude/progress/[prd-name]/phase-[N]-progress.md`
**Limit**: ONE per phase

**Sections**:
- Status (phase, start date, story description)
- Summary (brief overview)
- Completed tasks
- Current phase tasks
- Acceptance criteria validation
- Decisions log
- Files created/modified
- Dependencies
- Risks identified
- Next steps
- Blockers

**When to Use**: When working on multi-phase implementations from a PRD

---

### 2. Phase Context Template
**File**: `worknotes/phase-context-template.md`
**Purpose**: Document implementation decisions, technical notes, and architectural considerations for a phase
**Location Pattern**: `.claude/worknotes/[prd-name]/phase-[N]-context.md`
**Limit**: ONE per phase

**Sections**:
- Phase overview
- Implementation context
- Technical decisions (with options considered)
- Architecture notes
- Integration patterns
- Implementation notes
- Gotchas & learnings
- Known issues
- Next phase considerations

**When to Use**: When documenting technical decisions and implementation approaches during a phase

---

### 3. Observation Log Template
**File**: `worknotes/observation-log-template.md`
**Purpose**: Track observations, learnings, patterns, and insights discovered during development
**Location Pattern**: `.claude/worknotes/observations/observation-log-MM-YY.md`
**Limit**: ONE per month

**Sections**:
- Architecture patterns
- Performance insights
- Development workflow
- Integration patterns
- Testing & quality
- Code quality
- Technical debt

**Format**: Brief bullet points (1-2 lines per observation)

**When to Use**: For monthly consolidation of development insights and learnings

---

### 4. Bug Fix Tracking Template
**File**: `worknotes/bug-fixes-tracking-template.md`
**Purpose**: Brief reference of significant bug fixes completed in a month
**Location Pattern**: `.claude/worknotes/fixes/bug-fixes-tracking-MM-YY.md`
**Limit**: ONE per month

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

**Format**: Very brief bullet points (1-2 lines per fix) with commit references

**When to Use**: For monthly consolidation of significant bug fixes

---

### 5. Implementation Plan Template
**File**: `plans/implementation-plan-template.md`
**Purpose**: Detailed breakdown of feature implementation with phases and tasks
**Location Pattern**: `/docs/project_plans/[prd-name]/implementation-plan.md`
**Required**: When implementing features from a PRD

**Sections**:
- Story summary (epic, scope, complexity)
- Overview
- File changes (create, modify, delete)
- Component architecture
- Technical specifications
- Integration points
- Test coverage (unit, integration, E2E)
- Observability & monitoring
- Documentation updates
- Acceptance criteria
- Dependencies
- Risks & mitigation
- Rollout strategy

**When to Use**: When planning detailed implementation of a feature or epic

---

## How to Use These Templates

### 1. Copy the Template

```bash
# Copy progress template
cp examples/progress/phase-progress-template.md .claude/progress/my-feature/phase-1-progress.md

# Copy context template
cp examples/worknotes/phase-context-template.md .claude/worknotes/my-feature/phase-1-context.md

# Copy observation log template
cp examples/worknotes/observation-log-template.md .claude/worknotes/observations/observation-log-11-25.md

# Copy bug fix tracking template
cp examples/worknotes/bug-fixes-tracking-template.md .claude/worknotes/fixes/bug-fixes-tracking-11-25.md

# Copy implementation plan template
cp examples/plans/implementation-plan-template.md docs/project_plans/my-feature/implementation-plan.md
```

### 2. Replace Placeholders

All templates use `{{PLACEHOLDER}}` format for variables:

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{EPIC_ID}}` | Epic identifier | `MP-NAV-E001` or `AUTH-EPIC-1` |
| `{{STORY_ID}}` | Story identifier | `UI-005` or `STORY-123` |
| `{{PHASE_NAME}}` | Phase name | `Analysis & Planning`, `In Progress`, `Testing` |
| `{{PHASE_NUMBER}}` | Phase number | `1`, `2`, `3` |
| `{{FEATURE_NAME}}` | Feature name | `User Authentication`, `Top Navigation` |
| `{{YYYY-MM-DD}}` | Date | `2025-11-05` |
| `{{MM-YY}}` | Month-year | `11-25` (November 2025) |
| `{{Month Year}}` | Month and year | `November 2025` |
| `{{PROJECT_NAME}}` | Your project name | `MyProject` |

**Search and Replace**:
```bash
# Replace variables in a file
sed -i 's/{{EPIC_ID}}/MY-EPIC-001/g' phase-1-progress.md
sed -i 's/{{PHASE_NUMBER}}/1/g' phase-1-progress.md
```

### 3. Fill In Content

Replace placeholder sections with actual content:

- Remove sections that aren't applicable
- Add additional sections as needed
- Keep format consistent (checkboxes, bullet points, etc.)
- Follow the 1-2 line brevity guideline for observations and bug fixes

### 4. Follow Naming Conventions

**Progress Tracking**: `phase-[N]-progress.md`
- ✅ `phase-1-progress.md`
- ✅ `phase-2-progress.md`
- ❌ `phase-1-progress-updated.md`

**Phase Context**: `phase-[N]-context.md`
- ✅ `phase-1-context.md`
- ✅ `phase-2-context.md`
- ❌ `phase-2-context-notes.md`

**Observations**: `observation-log-MM-YY.md`
- ✅ `observation-log-11-25.md`
- ✅ `observation-log-12-25.md`
- ❌ `observation-log-nov-3.md`

**Bug Fixes**: `bug-fixes-tracking-MM-YY.md`
- ✅ `bug-fixes-tracking-11-25.md`
- ✅ `bug-fixes-tracking-12-25.md`
- ❌ `bugs-11-25.md`

---

## Documentation Policy Compliance

These templates follow the SkillMeat documentation policy:

### ✅ Allowed Tracking Documentation

1. **Progress Tracking** - ONE per phase
2. **Context/Notes** - ONE per phase
3. **Observation Logs** - ONE per month
4. **Bug Fix Tracking** - ONE per month
5. **Implementation Plans** - ONE per feature/epic

### ❌ Prohibited Documentation

- ❌ Multiple scattered progress docs per phase
- ❌ Ad-hoc debugging summaries (use git commits)
- ❌ Unstructured context files
- ❌ Daily/weekly observation logs (use monthly)
- ❌ Session notes as permanent docs

### Key Principles

1. **One Per Phase**: Don't create multiple progress or context docs for the same phase
2. **Organized Structure**: Use consistent directory structure
3. **Explicit Need**: Only create when working on multi-phase implementations
4. **Concise Content**: Keep notes brief and actionable
5. **Temporary Nature**: These are working documents, not permanent documentation

---

## Examples vs Templates

| Type | Purpose | Content | SkillMeat-Specific |
|------|---------|---------|----------------------|
| **Templates** (this directory) | Blank forms to fill in | `{{PLACEHOLDERS}}` | ❌ No - Generic |
| **Examples** (other directories) | Real-world reference | Actual SkillMeat data | ✅ Yes - Specific |

**Templates**: Use these to create new tracking docs for your project
**Examples**: Reference these to see how SkillMeat used the templates

---

## Customization for Your Project

### Variable Naming Conventions

Adapt placeholder names to your project:

```markdown
# SkillMeat pattern
{{EPIC_ID}}-{{STORY_ID}}

# Your project pattern
{{FEATURE_ID}}-{{TASK_ID}}
{{JIRA_KEY}}
{{LINEAR_ISSUE_ID}}
```

### Section Customization

Add or remove sections based on your needs:

**Add**:
- Security considerations
- Performance benchmarks
- A11y requirements
- Design system compliance

**Remove**:
- Sections not relevant to your workflow
- Tracking you don't need

**Adapt**:
- Change section names to match your process
- Adjust format to your team's preferences

### Integration with Your Tools

Replace tool references with your stack:

- `Clerk` → `Auth0`, `Supabase Auth`, `Custom Auth`
- `FastAPI` → `Express`, `Django`, `Rails`
- `Next.js` → `React`, `Vue`, `SvelteKit`
- `Linear` → `Jira`, `GitHub Issues`, `Trello`

---

## See Also

- **[CLAUDE.md](../CLAUDE.md)** - Documentation policy and tracking rules
- **[examples/README.md](./README.md)** - SkillMeat-specific examples
- **[TEMPLATIZATION_GUIDE.md](../TEMPLATIZATION_GUIDE.md)** - Comprehensive customization guide

---

**Created**: 2025-11-05
**Purpose**: Provide generic templates for creating tracking documentation
**Compliance**: Follows SkillMeat documentation policy exactly
