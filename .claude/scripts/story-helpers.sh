#!/bin/bash
# Shared utilities for story commands

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Find story file
find_story_file() {
  local story_id="$1"
  local locations=(
    "docs/project_plans/Stories/${story_id}.md"
    "docs/project_plans/Sprints/*/stories/${story_id}.md"
    "docs/project_plans/Sprints/*/${story_id}.md"
    ".claude/stories/${story_id}.md"
  )

  for location in "${locations[@]}"; do
    if [ -f "$location" ]; then
      echo "$location"
      return 0
    fi
  done

  # Try glob search
  local found=$(find docs -name "${story_id}.md" 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    echo "$found"
    return 0
  fi

  return 1
}

# Initialize progress tracker
init_progress() {
  local story_id="$1"
  local progress_file=".claude/progress/${story_id}.json"

  if [ ! -f "$progress_file" ]; then
    mkdir -p .claude/progress
    cat > "$progress_file" << EOF
{
  "story_id": "${story_id}",
  "status": "initialized",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phase": 0,
  "steps_completed": [],
  "files_created": [],
  "files_modified": [],
  "tests_added": [],
  "subagents_used": [],
  "errors": [],
  "decisions": []
}
EOF
    log_info "Progress tracker initialized: $progress_file"
  fi
}

# Update progress tracker
update_progress() {
  local story_id="$1"
  local field="$2"
  local value="$3"
  local progress_file=".claude/progress/${story_id}.json"

  if [ ! -f "$progress_file" ]; then
    init_progress "$story_id"
  fi

  # Update JSON (requires jq)
  if command -v jq &> /dev/null; then
    jq --arg field "$field" --arg value "$value" \
      '.[$field] = $value | .last_update = now' \
      "$progress_file" > "$progress_file.tmp" && mv "$progress_file.tmp" "$progress_file"
  else
    log_warn "jq not found - progress not updated"
  fi
}

# Append to array in progress tracker
append_progress() {
  local story_id="$1"
  local field="$2"
  local value="$3"
  local progress_file=".claude/progress/${story_id}.json"

  if command -v jq &> /dev/null; then
    jq --arg field "$field" --arg value "$value" \
      '.[$field] += [$value] | .last_update = now' \
      "$progress_file" > "$progress_file.tmp" && mv "$progress_file.tmp" "$progress_file"
  fi
}

# Check if on correct branch
ensure_feature_branch() {
  local story_id="$1"
  local current_branch=$(git branch --show-current)

  if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
    local new_branch="feat/${story_id}"
    log_info "Creating feature branch: $new_branch"
    git checkout -b "$new_branch"
    return 0
  fi

  # Check if branch name contains story ID
  if [[ "$current_branch" != *"$story_id"* ]]; then
    log_warn "Current branch ($current_branch) doesn't match story ID ($story_id)"
    read -p "Continue on this branch? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
}

# Run tests for specific scope
run_scoped_tests() {
  local scope="$1"
  local story_id="$2"

  case "$scope" in
    backend)
      log_info "Running backend tests..."
      uv run --project services/api pytest -xvs -k "$story_id" || true
      ;;
    frontend)
      log_info "Running frontend tests..."
      pnpm --filter "./apps/web" test "$story_id" || true
      ;;
    ui)
      log_info "Running UI component tests..."
      pnpm --filter "./packages/ui" test || true
      ;;
    *)
      log_info "Running all tests..."
      uv run --project services/api pytest || true
      pnpm -r test || true
      ;;
  esac
}

# Generate commit message
generate_commit_msg() {
  local story_id="$1"
  local scope="$2"
  local description="$3"

  # Follow conventional commits
  echo "feat(${story_id}): ${description}"
}

# Check dependencies
check_dependencies() {
  local deps_ok=true

  # Check Node/pnpm
  if ! command -v pnpm &> /dev/null; then
    log_error "pnpm not found"
    deps_ok=false
  fi

  # Check Python/uv
  if ! command -v uv &> /dev/null; then
    log_error "uv not found"
    deps_ok=false
  fi

  # Check git/gh
  if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI (gh) not found - PR creation will fail"
  fi

  if [ "$deps_ok" = false ]; then
    exit 1
  fi
}

# Export functions for use in other scripts
export -f log_info log_warn log_error
export -f find_story_file init_progress update_progress append_progress
export -f ensure_feature_branch run_scoped_tests generate_commit_msg
export -f check_dependencies
