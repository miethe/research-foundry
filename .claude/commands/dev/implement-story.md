---
description: Execute an existing story implementation plan
argument-hint: "<story_id>"
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*)
---

# /implement-story

You are Claude Code executing an approved implementation plan for story `$ARGUMENTS`.

<!-- MeatyCapture Integration - Project: skillmeat -->
## Context Gathering

Before implementation, search for related request-log items:
- `/mc search "story-keyword" skillmeat` - Find related bugs/enhancements

## Prerequisites

- Plan must exist at `.claude/plans/${story_id}-plan.md`
- Progress tracker initialized at `.claude/progress/${story_id}.json`

## Process

### 1. Load Plan and Progress

```bash
story_id="${1}"
plan_file=".claude/plans/${story_id}-plan.md"
progress_file=".claude/progress/${story_id}.json"

if [ ! -f "$plan_file" ]; then
  echo "ERROR: No plan found. Run /plan-story ${story_id} first"
  exit 1
fi

# Check current progress
if [ -f "$progress_file" ]; then
  current_phase=$(jq -r '.phase' "$progress_file")
  echo "Resuming from phase: $current_phase"
else
  echo "Starting fresh implementation"
fi
```

### 2. Execute Plan Systematically

For each file in the plan:

#### 2.1 Backend Files

```bash
for file in $(grep -A 100 "### Backend Files" "$plan_file" | grep "^- \[ \]" | cut -d' ' -f3); do
  echo "Implementing: $file"

  # Use appropriate subagent
  if [[ $file == *"schemas"* ]]; then
    @backend-developer implement-schema $file --story ${story_id}
  elif [[ $file == *"repositories"* ]]; then
    @backend-developer implement-repository $file --story ${story_id}
  elif [[ $file == *"services"* ]]; then
    @backend-developer implement-service $file --story ${story_id}
  elif [[ $file == *"endpoints"* ]]; then
    @backend-developer implement-endpoint $file --story ${story_id}
  fi

  # Verify and commit
  if uv run --project services/api mypy "$file"; then
    git add "$file"
    git commit -m "feat(${story_id}): implement $(basename $file .py)"
  else
    echo "Type check failed for $file - fixing..."
    # Fix and retry
  fi
done
```

#### 2.2 Frontend Files

```bash
for file in $(grep -A 100 "### Frontend Files" "$plan_file" | grep "^- \[ \]" | cut -d' ' -f3); do
  echo "Implementing: $file"

  # Use appropriate subagent
  if [[ $file == *"components"* ]]; then
    @ui-designer create-component $(basename $file .tsx) --story ${story_id}
  elif [[ $file == *"hooks"* ]]; then
    @frontend-developer implement-hook $file --story ${story_id}
  elif [[ $file == *"pages"* ]] || [[ $file == *"app/"* ]]; then
    @frontend-developer implement-page $file --story ${story_id}
  fi

  # Verify and commit
  if pnpm typecheck "$file"; then
    git add "$file"
    git commit -m "feat(${story_id}): implement $(basename $file .tsx)"
  fi
done
```

### 3. Run Tests Continuously

After each component implementation:

```bash
# Run relevant tests
if [[ $last_file == *"service"* ]]; then
  uv run --project services/api pytest -xvs app/tests/test_$(basename $last_file .py).py
elif [[ $last_file == *"component"* ]]; then
  pnpm --filter "./packages/ui" test $(basename $last_file .tsx)
fi
```

### 4. Update Progress After Each File

```bash
update_progress() {
  local file="$1"
  local status="$2"

  jq --arg file "$file" --arg status "$status" \
    '.files_modified += [$file] | .last_update = now | .status = $status' \
    "$progress_file" > "$progress_file.tmp" && mv "$progress_file.tmp" "$progress_file"
}
```

### 5. Final Validation

```bash
# Run full test suite
echo "Running full validation..."

# Backend
uv run --project services/api pytest
uv run --project services/api mypy app
uv run --project services/api ruff check

# Frontend
pnpm -r typecheck
pnpm -r lint
pnpm -r test

# A11y check for UI components
pnpm --filter "./packages/ui" test:a11y

# If all passes
update_progress "complete" "validated"
echo "✅ Implementation complete and validated"
```

<!-- MeatyCapture Integration - Project: skillmeat -->
### 6. Post-Implementation

Update status of any request-log items addressed by this story:
- Edit markdown files: change `**Status:** triage` → `**Status:** done`
- If issues arose during implementation: `/mc capture {"title": "...", "type": "bug"}`

## Rollback Protocol

If implementation fails at any point:

```bash
rollback_implementation() {
  local story_id="$1"
  local checkpoint="$2"

  echo "⚠️ Rolling back to checkpoint: $checkpoint"

  # Git rollback
  git reset --hard "$checkpoint"

  # Update progress
  jq --arg status "rolled_back" \
    '.status = $status | .rolled_back_at = now' \
    "$progress_file" > "$progress_file.tmp" && mv "$progress_file.tmp" "$progress_file"

  echo "Rollback complete. Review errors in progress file."
}
```
