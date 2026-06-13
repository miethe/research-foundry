#!/bin/bash

# Git utilities for Claude commands
# Common Git operations used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}Error: Not in a git repository${NC}" >&2
        return 1
    fi
}

# Get current branch name
get_current_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "HEAD"
}

# Get main/master branch name
get_main_branch() {
    # Try common main branch names
    for branch in main master; do
        if git show-ref --verify --quiet refs/heads/$branch || \
           git show-ref --verify --quiet refs/remotes/origin/$branch; then
            echo "$branch"
            return 0
        fi
    done

    # Fallback to first branch
    git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main"
}

# Check if working directory is clean
is_working_directory_clean() {
    [[ -z $(git status --porcelain) ]]
}

# Get list of changed files since a reference (branch/commit)
get_changed_files() {
    local since_ref="${1:-$(get_main_branch)}"
    local filter="${2:-}"

    if [[ -n "$filter" ]]; then
        git diff --name-only "$since_ref"...HEAD | grep -E "$filter" || true
    else
        git diff --name-only "$since_ref"...HEAD || true
    fi
}

# Get list of staged files
get_staged_files() {
    local filter="${1:-}"

    if [[ -n "$filter" ]]; then
        git diff --cached --name-only | grep -E "$filter" || true
    else
        git diff --cached --name-only || true
    fi
}

# Get list of unstaged changes
get_unstaged_files() {
    local filter="${1:-}"

    if [[ -n "$filter" ]]; then
        git diff --name-only | grep -E "$filter" || true
    else
        git diff --name-only || true
    fi
}

# Get list of untracked files
get_untracked_files() {
    local filter="${1:-}"

    if [[ -n "$filter" ]]; then
        git ls-files --others --exclude-standard | grep -E "$filter" || true
    else
        git ls-files --others --exclude-standard || true
    fi
}

# Get comprehensive status report
get_git_status_report() {
    local output_format="${1:-text}" # text, json, or markdown

    check_git_repo || return 1

    local current_branch
    current_branch=$(get_current_branch)
    local main_branch
    main_branch=$(get_main_branch)
    local is_clean
    is_clean=$(is_working_directory_clean && echo "true" || echo "false")

    local staged_files
    staged_files=$(get_staged_files)
    local unstaged_files
    unstaged_files=$(get_unstaged_files)
    local untracked_files
    untracked_files=$(get_untracked_files)
    local changed_files
    changed_files=$(get_changed_files "$main_branch")

    case "$output_format" in
        "json")
            cat <<EOF
{
    "current_branch": "$current_branch",
    "main_branch": "$main_branch",
    "is_clean": $is_clean,
    "staged_files": [$(echo "$staged_files" | sed 's/.*/"&"/' | paste -sd,)],
    "unstaged_files": [$(echo "$unstaged_files" | sed 's/.*/"&"/' | paste -sd,)],
    "untracked_files": [$(echo "$untracked_files" | sed 's/.*/"&"/' | paste -sd,)],
    "changed_files": [$(echo "$changed_files" | sed 's/.*/"&"/' | paste -sd,)]
}
EOF
            ;;
        "markdown")
            echo "## Git Status Report"
            echo ""
            echo "**Branch:** $current_branch"
            echo "**Main Branch:** $main_branch"
            echo "**Working Directory:** $([ "$is_clean" = "true" ] && echo "Clean" || echo "Has Changes")"
            echo ""

            if [[ -n "$staged_files" ]]; then
                echo "### Staged Files"
                echo "$staged_files" | sed 's/^/- /'
                echo ""
            fi

            if [[ -n "$unstaged_files" ]]; then
                echo "### Unstaged Changes"
                echo "$unstaged_files" | sed 's/^/- /'
                echo ""
            fi

            if [[ -n "$untracked_files" ]]; then
                echo "### Untracked Files"
                echo "$untracked_files" | sed 's/^/- /'
                echo ""
            fi

            if [[ -n "$changed_files" ]]; then
                echo "### Changes since $main_branch"
                echo "$changed_files" | sed 's/^/- /'
                echo ""
            fi
            ;;
        *)
            echo -e "${BLUE}Git Status Report${NC}"
            echo "=================="
            echo -e "Branch: ${GREEN}$current_branch${NC}"
            echo -e "Main Branch: ${GREEN}$main_branch${NC}"
            echo -e "Working Directory: $([ "$is_clean" = "true" ] && echo -e "${GREEN}Clean${NC}" || echo -e "${YELLOW}Has Changes${NC}")"
            echo ""

            if [[ -n "$staged_files" ]]; then
                echo -e "${GREEN}Staged Files:${NC}"
                echo "$staged_files" | sed 's/^/  /'
                echo ""
            fi

            if [[ -n "$unstaged_files" ]]; then
                echo -e "${YELLOW}Unstaged Changes:${NC}"
                echo "$unstaged_files" | sed 's/^/  /'
                echo ""
            fi

            if [[ -n "$untracked_files" ]]; then
                echo -e "${RED}Untracked Files:${NC}"
                echo "$untracked_files" | sed 's/^/  /'
                echo ""
            fi

            if [[ -n "$changed_files" ]]; then
                echo -e "${BLUE}Changes since $main_branch:${NC}"
                echo "$changed_files" | sed 's/^/  /'
                echo ""
            fi
            ;;
    esac
}

# Create a backup branch
create_backup_branch() {
    local backup_name="${1:-backup-$(date +%Y%m%d-%H%M%S)}"

    check_git_repo || return 1

    echo -e "${BLUE}Creating backup branch: $backup_name${NC}"

    if git checkout -b "$backup_name" 2>/dev/null; then
        echo -e "${GREEN}Backup branch created successfully${NC}"
        # Switch back to original branch
        git checkout - > /dev/null 2>&1
        echo "$backup_name"
        return 0
    else
        echo -e "${RED}Failed to create backup branch${NC}" >&2
        return 1
    fi
}

# Stash changes with a message
stash_changes() {
    local message="${1:-Automated stash by Claude command}"

    check_git_repo || return 1

    if ! is_working_directory_clean; then
        echo -e "${BLUE}Stashing changes: $message${NC}"
        git stash push -m "$message"
        return 0
    else
        echo -e "${GREEN}Working directory is clean, nothing to stash${NC}"
        return 0
    fi
}

# Pop the most recent stash
pop_stash() {
    check_git_repo || return 1

    if git stash list | head -1 | grep -q .; then
        echo -e "${BLUE}Restoring stashed changes${NC}"
        git stash pop
        return 0
    else
        echo -e "${YELLOW}No stash entries found${NC}"
        return 1
    fi
}

# Check if a branch exists (local or remote)
branch_exists() {
    local branch_name="$1"

    git show-ref --verify --quiet "refs/heads/$branch_name" || \
    git show-ref --verify --quiet "refs/remotes/origin/$branch_name"
}

# Get the number of commits ahead/behind main
get_branch_status() {
    local current_branch
    current_branch=$(get_current_branch)
    local main_branch
    main_branch=$(get_main_branch)

    if [[ "$current_branch" == "$main_branch" ]]; then
        echo "on-main"
        return 0
    fi

    local ahead behind
    {
        read -r ahead
        read -r behind
    } <<< "$(git rev-list --left-right --count "$main_branch"..."$current_branch" | tr '\t' '\n')"

    if [[ "$ahead" -gt 0 && "$behind" -gt 0 ]]; then
        echo "diverged:$ahead:$behind"
    elif [[ "$ahead" -gt 0 ]]; then
        echo "ahead:$ahead"
    elif [[ "$behind" -gt 0 ]]; then
        echo "behind:$behind"
    else
        echo "up-to-date"
    fi
}

# Validate that all changes are committed or stashed
ensure_clean_state() {
    local allow_stash="${1:-true}"

    check_git_repo || return 1

    if is_working_directory_clean; then
        echo -e "${GREEN}Working directory is clean${NC}"
        return 0
    fi

    if [[ "$allow_stash" == "true" ]]; then
        echo -e "${YELLOW}Working directory has uncommitted changes${NC}"
        echo "Options:"
        echo "1. Commit changes"
        echo "2. Stash changes"
        echo "3. Abort operation"
        return 1
    else
        echo -e "${RED}Working directory must be clean to proceed${NC}" >&2
        return 1
    fi
}

# Get recent commit information
get_recent_commits() {
    local count="${1:-10}"
    local format="${2:-oneline}" # oneline, short, medium, full

    check_git_repo || return 1

    case "$format" in
        "json")
            git log -"$count" --pretty=format:'{"hash":"%H","short_hash":"%h","author":"%an","date":"%ai","message":"%s"}' | \
            sed '$!s/$/,/' | sed '1i[' | sed '$a]'
            ;;
        *)
            git log -"$count" --pretty="$format"
            ;;
    esac
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "Git utilities loaded. Available functions:"
    echo "  check_git_repo, get_current_branch, get_main_branch"
    echo "  is_working_directory_clean, get_changed_files, get_staged_files"
    echo "  get_unstaged_files, get_untracked_files, get_git_status_report"
    echo "  create_backup_branch, stash_changes, pop_stash"
    echo "  branch_exists, get_branch_status, ensure_clean_state, get_recent_commits"
fi
