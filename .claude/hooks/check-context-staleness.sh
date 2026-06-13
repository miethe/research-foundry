#!/bin/bash
# Staleness Detection Hook for Progressive Disclosure Context Files
#
# Purpose: Warn when context files may be stale due to referenced file changes
# Trigger: Pre-commit or on-demand via /analyze:check-context-freshness
#
# Usage:
#   .claude/hooks/check-context-staleness.sh           # Check against staged files
#   .claude/hooks/check-context-staleness.sh --all     # Check all referenced files
#
# Exit codes:
#   0 - No staleness detected
#   1 - Staleness warnings issued (non-blocking by default)

set -e

CONTEXT_DIR=".claude/context"
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get staged files or check all
if [[ "$1" == "--all" ]]; then
    CHECK_MODE="all"
    echo -e "${GREEN}Checking all referenced files for staleness...${NC}"
else
    CHECK_MODE="staged"
    STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
    if [[ -z "$STAGED_FILES" ]]; then
        echo -e "${GREEN}No staged files to check.${NC}"
        exit 0
    fi
fi

WARNINGS=0

# Check if context directory exists
if [[ ! -d "$CONTEXT_DIR" ]]; then
    echo -e "${YELLOW}No context directory found at $CONTEXT_DIR${NC}"
    exit 0
fi

# Process each context file
for context_file in "$CONTEXT_DIR"/*.md; do
    [[ -f "$context_file" ]] || continue

    # Extract references from YAML frontmatter
    # Look for lines starting with "  - " after "references:" until next top-level key
    refs=$(sed -n '/^references:/,/^[a-z_-]*:/p' "$context_file" 2>/dev/null | \
           grep "^  - " | \
           sed 's/^  - //' | \
           sed 's/[[:space:]]*$//')

    [[ -z "$refs" ]] && continue

    # Check each reference
    while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue

        # Handle glob patterns (e.g., ai/symbols-*.json)
        if [[ "$ref" == *"*"* ]]; then
            # For glob patterns, check if any matching file is staged
            for matched_file in $ref; do
                if [[ "$CHECK_MODE" == "staged" ]]; then
                    if echo "$STAGED_FILES" | grep -q "$matched_file"; then
                        echo -e "${YELLOW}⚠️  Warning: $(basename "$context_file") references modified file: $matched_file${NC}"
                        echo "   Please verify context is still accurate."
                        ((WARNINGS++))
                    fi
                else
                    # In --all mode, just report if file exists
                    if [[ -f "$matched_file" ]]; then
                        file_mtime=$(stat -f "%m" "$matched_file" 2>/dev/null || stat -c "%Y" "$matched_file" 2>/dev/null)
                        context_mtime=$(stat -f "%m" "$context_file" 2>/dev/null || stat -c "%Y" "$context_file" 2>/dev/null)
                        if [[ "$file_mtime" -gt "$context_mtime" ]]; then
                            echo -e "${YELLOW}⚠️  Warning: $(basename "$context_file") may be stale (referenced file newer): $matched_file${NC}"
                            ((WARNINGS++))
                        fi
                    fi
                fi
            done
        else
            # Direct file reference
            if [[ "$CHECK_MODE" == "staged" ]]; then
                if echo "$STAGED_FILES" | grep -q "$ref"; then
                    echo -e "${YELLOW}⚠️  Warning: $(basename "$context_file") references modified file: $ref${NC}"
                    echo "   Please verify context is still accurate."
                    ((WARNINGS++))
                fi
            else
                # In --all mode, check if referenced file is newer
                if [[ -f "$ref" ]]; then
                    file_mtime=$(stat -f "%m" "$ref" 2>/dev/null || stat -c "%Y" "$ref" 2>/dev/null)
                    context_mtime=$(stat -f "%m" "$context_file" 2>/dev/null || stat -c "%Y" "$context_file" 2>/dev/null)
                    if [[ "$file_mtime" -gt "$context_mtime" ]]; then
                        echo -e "${YELLOW}⚠️  Warning: $(basename "$context_file") may be stale (referenced file newer): $ref${NC}"
                        ((WARNINGS++))
                    fi
                fi
            fi
        fi
    done <<< "$refs"
done

if [[ $WARNINGS -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Found $WARNINGS staleness warning(s).${NC}"
    echo "Run 'grep -l \"pattern\" .claude/context/*.md' to find affected files."
    # Non-blocking exit - change to exit 1 to block commits
    exit 0
else
    echo -e "${GREEN}✓ No context staleness detected.${NC}"
    exit 0
fi
