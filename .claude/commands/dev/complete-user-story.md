---
description: Complete a user story end-to-end with automatic subagent orchestration
argument-hint: "[<story_id>] | [<attached_user_story.md>]"
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*), Bash(pytest:*),
---

# /complete-user-story

You are Claude Code implementing user story `$ARGUMENTS` following SkillMeat standards.

<!-- MeatyCapture Integration - Project: skillmeat -->
## Context Gathering

Before implementation, search request-logs for related items:
- `/mc search "story-keyword" skillmeat` - Find bugs/enhancements that may be resolved by this story

## Story Execution

Execute story ${ARGUMENTS} by:

1. Create branch from main (eg feat/{story_id})
2. Load story specification
3. Plan the implementation and create a progress tracker in @.claude/progress/${story_id}.md
4. For each component:
   - Identify required expertise
   - Request appropriate specialist subagent
   - Track completion
   - Push commits incrementally
5. Run validation with task-completion-validator agent (fallback to manual review)
6. Run final code review with senior-code-reviewer agent
7. Create PR

When I need specialized work, I'll describe what's needed and the appropriate agent should handle it based on their expertise.

## CRITICAL: Subagent Usage Protocol

You MUST use these specialized agents for their domains:

| Task Type | Required Subagent |
|-----------|------------------|
| Project Architecture | lead-architect |
| Backend analysis | backend-architect |
| Backend implementation | python-backend-engineer |
| NextJS-specific analysis/design | nextjs-architecture-expert |
| Frontend analysis | frontend-architect |
| Frontend implementation | ui-engineer-enhanced |
| Component creation | ui-designer |
| UX Flows | ux-researcher |
| Code review | senior-code-reviewer |
| Test creation | test-engineer |

For example, if the task is to implement a new API endpoint, then the backend-architect agent would need to analyze the story requirements and design the API schema before handing it off to the backend-developer agent for implementation.

If subagent invocation fails, document in progress tracker and proceed directly.

## Phase 0: Initialize Context

Retrieve the story ID `${story_id}` from `$ARGUMENTS` either directly, or as the name of the user story (minus .md filetype).

Setup tracking for the user story. Create a progress tracker, worknotes, and plan file for the story as `${story_id}.md` in its corresponding directory within `.claude/`, ie `.claude/progress/123.md`. If the file already exists and is not empty, then the conversation must have already started and you should start from wherever it left off.

```bash
# Collect environment state
story_id="${1:-$ARGUMENTS}"
story_id="${story_id%.md}"  # Strip .md if present

# Set up tracking
mkdir -p .claude/{progress,worknotes,plans}
progress_file=".claude/progress/${story_id}.md"
worknotes_file=".claude/worknotes/${story_id}.md"
plan_file=".claude/plans/${story_id}-plan.md"

# Check for existing work
if [ -f "$progress_file" ]; then
  echo "Found existing progress for ${story_id}"
  cat "$progress_file"
fi
```

## Phase 1: Load & Analyze Story

### 1.1 Find Story Specification

- Follow guidance to load and analyze story from @load-analyze-story.

### 1.2 Generate Implementation Plan

Create `${plan_file}` with:

```markdown
# Implementation Plan: ${story_id}

## Story Summary
- Epic: [epic_id]
- Scope: [Backend|Frontend|Full-Stack]
- Complexity: [S|M|L|XL]

## File Changes
### Create
- [ ] path/to/new/file1.py - [description]
- [ ] path/to/new/file2.tsx - [description]

### Modify
- [ ] path/to/existing/file1.py - [what to change]
- [ ] path/to/existing/file2.tsx - [what to change]

### Delete
- [ ] path/to/obsolete/file.py - [why removing]

## API Changes
- [ ] POST /api/v1/resource - [Create resource]
- [ ] GET /api/v1/resource/{id} - [Get resource]

## Schema Changes
- [ ] Table: resources - [Add columns: x, y, z]
- [ ] Migration: add_resources_table

## Test Coverage
- [ ] Unit: test_resource_service.py
- [ ] Integration: test_resource_api.py
- [ ] E2E: resource.spec.ts

## Documentation Updates
- [ ] API docs: /api/v1/resource endpoints
- [ ] README: New resource feature
- [ ] CHANGELOG: Feature entry
```

### 1.3 Initialize Progress Tracker

```markdown
## Progress Tracker: ${story_id}

### Status

- Phase: Implementation
- Started: [timestamp]

### Completed

- [x] Planning
- [ ] Backend implementation
- [ ] Frontend implementation

### Decisions Log

- [timestamp]: Chose approach X because Y

### Subagents Used

- @backend-architect
- @python-backend-engineer
- @ui-designer
- @frontend-developer
- @code-reviewer
- @test-engineer

### Files Updated/Added

- /api/v2/resource (A)
- /api/v1/resource (U)

### Tests

- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests

### Encounters of an Unrelated Kind (Unrelated Bugs, Errors, and Other Debt)

- Implementation of x should be refactored as a separate function
- Implementation of y is causing performance issues
```

## Phase 2: Implementation

### 2.1 Backend Implementation (if applicable)

For backend implementation of ${file_path}:

I need to delegate this to our backend specialist. The backend-architect should analyze the requirements and python-backend-engineer should implement:

Story: ${story_id}
File: ${file_path}
Acceptance Criteria: [...]

After each file, update progress and commit atomically.

Backend checklist per file:

- [ ] Schema/DTO in `app/schemas/`
- [ ] Repository in `app/repositories/`
- [ ] Service in `app/services/`
- [ ] Router in `app/api/v1/endpoints/`
- [ ] Migration if schema changed
- [ ] Tests in `app/tests/`

### 2.2 Frontend Implementation (if applicable)

For frontend implementation of ${file_path}:

I need to delegate this to our frontend specialist. The ui-designer should analyze the requirements and ui-engineer-enhanced should implement:

Story: ${story_id}
File: ${file_path}
Acceptance Criteria: [...]

Frontend checklist per component:

- [ ] Component in `packages/ui/` if reusable
- [ ] Hook in `apps/web/src/hooks/` if needed
- [ ] Page/Route in `apps/web/src/app/`
- [ ] API client in `packages/api/`
- [ ] Tests in `__tests__/` directories
- [ ] Storybook story if in `packages/ui/`

### 2.3 Test Implementation

REQUIRED for all stories:

Use write-tests subagent to create tests.

```bash
# Run tests based on scope
if [[ $scope == *"Backend"* ]]; then
  uv run --project services/api pytest app/tests -k ${story_id}
fi

if [[ $scope == *"Frontend"* ]]; then
  pnpm --filter "./apps/web" test ${story_id}
fi
```

### 2.4 Documentation Updates

Update based on changes:

- [ ] API: Update OpenAPI docs if endpoints added
- [ ] Components: Add Storybook stories for new UI components
- [ ] Guides: Update relevant guides in `/docs`
- [ ] CHANGELOG: Add entry under current version

## Phase 4: Validation & Review

### 4.1 Run Quality Checks

```bash
# Type checking
pnpm -r typecheck
uv run --project services/api mypy app

# Linting
pnpm -r lint
uv run --project services/api ruff check

# Tests
pnpm -r test
uv run --project services/api pytest

# A11y for new components
if [ -n "$(ls packages/ui/src/components/*/new 2>/dev/null)" ]; then
  pnpm --filter "./packages/ui" test:a11y
fi
```

### 4.2 Code Review

REQUIRED final review:

```bash
@senior-code-reviewer final-review ${story_id} --comprehensive
```

### 4.3 Update Progress

Update the Progress Tracker with all relevant information.

## Phase 5: Create Pull Request

```bash
#!/bin/bash
set -euo pipefail

# Simple PR creation with all context
story_id="${1}"
current_branch=$(git branch --show-current)

# Ensure we're not on main
if [ "$current_branch" = "main" ]; then
  new_branch="feat/${story_id}"
  git checkout -b "$new_branch"
  current_branch="$new_branch"
fi

# Push all commits
git push -u origin "$current_branch"

# Create comprehensive PR body
cat > .claude/pr-body.md << EOF
## ${story_id}: ${feature_description}

### Summary
Implementation of user story ${story_id} as specified in project documentation.

### Changes
$(cat ${plan_file} | grep -A 100 "## File Changes")

### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests passing
- [ ] E2E tests cover happy path
- [ ] Manual testing completed

### Review Checklist
- [ ] Follows CLAUDE.md standards
- [ ] No hardcoded values
- [ ] Error handling complete
- [ ] Documentation updated
- [ ] Accessibility verified (WCAG AA)

### Progress Tracker
\`\`\`json
$(cat ${progress_file})
\`\`\`

### Related
- Epic: [epic_id]
- Depends on: [dependency_ids]
EOF

# Create PR
gh pr create \
  --base main \
  --head "$current_branch" \
  --title "feat(${story_id}): ${feature_description}" \
  --body-file .claude/pr-body.md \
  --draft

echo "✅ PR created for ${story_id}"
```

## Error Recovery Protocol

If ANY step fails:

1. **Log Error**:

```json
{
  "error": {
    "phase": "current_phase",
    "step": "current_step",
    "message": "error_message",
    "timestamp": "ISO_timestamp",
    "recovery_attempted": true
  }
}
```

2. **Attempt Recovery**:

- Git conflicts → stash, pull, reapply
- Test failures → fix or mark as known issue
- Subagent failure → retry once, then proceed directly
- Build failure → check dependencies, clean and rebuild

3. **If Unrecoverable**:

- Create PR with `[BLOCKED]` prefix
- Document specific blockers in PR body
- Tag with `needs-help` label

## Completion Checklist

- [ ] All acceptance criteria met
- [ ] Tests passing (unit, integration, e2e)
- [ ] Documentation updated
- [ ] Code reviewed by subagent
- [ ] PR created and linked to story
- [ ] Progress tracker shows "complete"

<!-- MeatyCapture Integration - Project: skillmeat -->
## Post-Completion

After successful PR creation:
- Update any request-log items addressed: change `**Status:**` to `done`
- If issues arose during implementation: `/mc capture {"title": "...", "type": "bug"}`
- Document recurring patterns for future reference
