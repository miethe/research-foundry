#!/bin/bash

# Artifact utilities for Claude commands
# AI artifact management functions used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/json-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/file-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/git-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/report-utils.sh" 2>/dev/null || true

# Global artifact configuration
readonly AI_DIR="ai"
readonly REPO_MAP_FILE="$AI_DIR/repo.map.json"
readonly SYMBOLS_GRAPH_FILE="$AI_DIR/symbols.graph.json"
readonly CHUNKING_CONFIG_FILE="$AI_DIR/chunking.config.json"
readonly HINTS_FILE="$AI_DIR/hints.md"

# Ensure AI directory exists
ensure_ai_directory() {
    if [[ ! -d "$AI_DIR" ]]; then
        mkdir -p "$AI_DIR"
        echo -e "${GREEN}✓ Created AI directory: $AI_DIR${NC}"
    fi

    # Create README if missing
    if [[ ! -f "$AI_DIR/README.md" ]]; then
        cat > "$AI_DIR/README.md" << 'EOF'
# AI Artifacts Directory

This directory contains AI-optimized artifacts for the SkillMeat project:

- **repo.map.json**: Repository structure and package overview
- **symbols.graph.json**: Code symbols with summaries (≤280 chars)
- **chunking.config.json**: Chunking configuration for AI context
- **hints.md**: AI guidance and architectural patterns

These artifacts are automatically maintained by the artifact command system.
EOF
        echo -e "${GREEN}✓ Created AI directory README${NC}"
    fi
}

# Update repository map
update_repo_map() {
    local include_deps="${1:-true}"
    local format="${2:-json}"
    local dry_run="${3:-false}"

    echo -e "${BLUE}=== Updating Repository Map ===${NC}"

    ensure_ai_directory

    # Analyze repository structure
    local repo_root
    repo_root=$(get_repo_root 2>/dev/null || pwd)

    # Build repository map
    local repo_map
    repo_map=$(cat << 'EOF'
{
  "name": "",
  "description": "",
  "version": "",
  "structure": {
    "apps": [],
    "services": [],
    "packages": [],
    "docs": [],
    "configs": []
  },
  "dependencies": {},
  "metadata": {
    "updated": "",
    "generator": "artifact-utils.sh",
    "total_files": 0,
    "total_size": ""
  }
}
EOF
    )

    # Extract project name and version
    local project_name="unknown"
    local project_version="unknown"
    local project_description=""

    if [[ -f "package.json" ]]; then
        project_name=$(json_extract "package.json" ".name" "file" 2>/dev/null || echo "unknown")
        project_version=$(json_extract "package.json" ".version" "file" 2>/dev/null || echo "unknown")
        project_description=$(json_extract "package.json" ".description" "file" 2>/dev/null || echo "")
    elif [[ -f "pyproject.toml" ]]; then
        project_name=$(grep -E "^name\s*=" pyproject.toml | sed 's/.*=\s*"\([^"]*\)".*/\1/' 2>/dev/null || echo "unknown")
        project_version=$(grep -E "^version\s*=" pyproject.toml | sed 's/.*=\s*"\([^"]*\)".*/\1/' 2>/dev/null || echo "unknown")
    fi

    # Analyze structure
    local apps_structure="[]"
    local services_structure="[]"
    local packages_structure="[]"

    if [[ -d "apps" ]]; then
        apps_structure=$(find apps -maxdepth 1 -type d ! -name apps | jq -R -s 'split("\n")[:-1] | map(split("/")[1]) | map(select(length > 0))')
    fi

    if [[ -d "services" ]]; then
        services_structure=$(find services -maxdepth 1 -type d ! -name services | jq -R -s 'split("\n")[:-1] | map(split("/")[1]) | map(select(length > 0))')
    fi

    if [[ -d "packages" ]]; then
        packages_structure=$(find packages -maxdepth 1 -type d ! -name packages | jq -R -s 'split("\n")[:-1] | map(split("/")[1]) | map(select(length > 0))')
    fi

    # Count files and calculate size
    local total_files=0
    local total_size=""

    if command -v find >/dev/null 2>&1; then
        total_files=$(find . -type f ! -path "./.git/*" ! -path "./node_modules/*" ! -path "./.next/*" | wc -l)
        if command -v du >/dev/null 2>&1; then
            total_size=$(du -sh . 2>/dev/null | cut -f1 || echo "unknown")
        fi
    fi

    # Build final map
    repo_map=$(jq -n \
        --arg name "$project_name" \
        --arg description "$project_description" \
        --arg version "$project_version" \
        --argjson apps "$apps_structure" \
        --argjson services "$services_structure" \
        --argjson packages "$packages_structure" \
        --arg updated "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --arg total_files "$total_files" \
        --arg total_size "$total_size" \
        '{
            name: $name,
            description: $description,
            version: $version,
            structure: {
                apps: $apps,
                services: $services,
                packages: $packages,
                docs: ["docs", "README.md"],
                configs: [".github", ".claude", "package.json", "tsconfig.json"]
            },
            dependencies: {},
            metadata: {
                updated: $updated,
                generator: "artifact-utils.sh",
                total_files: $total_files,
                total_size: $total_size
            }
        }')

    if [[ "$include_deps" == "true" ]] && [[ -f "package.json" ]]; then
        local deps
        deps=$(json_extract "package.json" ".dependencies // {}" "file" 2>/dev/null || echo "{}")
        repo_map=$(echo "$repo_map" | jq --argjson deps "$deps" '.dependencies = $deps')
    fi

    # Output or save
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}Dry run - Repository map:${NC}"
        echo "$repo_map" | jq .
    else
        echo "$repo_map" > "$REPO_MAP_FILE"
        echo -e "${GREEN}✓ Updated repository map: $REPO_MAP_FILE${NC}"
    fi

    return 0
}

# Update symbols graph
update_symbols_graph() {
    local max_summary="${1:-280}"
    local include_private="${2:-false}"
    local language="${3:-all}"
    local dry_run="${4:-false}"

    echo -e "${BLUE}=== Updating Symbols Graph ===${NC}"

    ensure_ai_directory

    # Initialize symbols structure
    local symbols_graph
    symbols_graph=$(cat << 'EOF'
{
  "symbols": {
    "functions": [],
    "classes": [],
    "interfaces": [],
    "types": [],
    "constants": []
  },
  "relationships": [],
  "metadata": {
    "updated": "",
    "generator": "artifact-utils.sh",
    "max_summary_length": 280,
    "total_symbols": 0
  }
}
EOF
    )

    # Find relevant source files
    local file_patterns=()
    case "$language" in
        "ts"|"typescript")
            file_patterns=("*.ts" "*.tsx")
            ;;
        "py"|"python")
            file_patterns=("*.py")
            ;;
        "js"|"javascript")
            file_patterns=("*.js" "*.jsx")
            ;;
        "all"|*)
            file_patterns=("*.ts" "*.tsx" "*.js" "*.jsx" "*.py")
            ;;
    esac

    local functions=()
    local classes=()
    local total_symbols=0

    # Extract TypeScript/JavaScript symbols
    for pattern in "${file_patterns[@]}"; do
        while IFS= read -r -d '' file; do
            [[ "$file" =~ node_modules|\.next|dist|build ]] && continue

            # Extract functions
            while IFS= read -r line; do
                if [[ -n "$line" ]]; then
                    local func_name
                    func_name=$(echo "$line" | sed -E 's/^[[:space:]]*export[[:space:]]+)?[[:space:]]*(async[[:space:]]+)?function[[:space:]]+([a-zA-Z_][a-zA-Z0-9_]*).*/\3/' 2>/dev/null || echo "")

                    if [[ -n "$func_name" ]] && [[ "$func_name" != "$line" ]]; then
                        local summary="${line:0:$max_summary}"
                        [[ ${#line} -gt $max_summary ]] && summary="${summary}..."

                        local symbol_entry
                        symbol_entry=$(jq -n \
                            --arg name "$func_name" \
                            --arg type "function" \
                            --arg file "$file" \
                            --arg summary "$summary" \
                            '{
                                name: $name,
                                type: $type,
                                file: $file,
                                summary: $summary
                            }')
                        functions+=("$symbol_entry")
                        ((total_symbols++))
                    fi
                fi
            done < <(grep -E "^[[:space:]]*(export[[:space:]]+)?(async[[:space:]]+)?function[[:space:]]+[a-zA-Z_]" "$file" 2>/dev/null || true)

            # Extract classes
            while IFS= read -r line; do
                if [[ -n "$line" ]]; then
                    local class_name
                    class_name=$(echo "$line" | sed -E 's/^[[:space:]]*export[[:space:]]+)?[[:space:]]*class[[:space:]]+([a-zA-Z_][a-zA-Z0-9_]*).*/\2/' 2>/dev/null || echo "")

                    if [[ -n "$class_name" ]] && [[ "$class_name" != "$line" ]]; then
                        local summary="${line:0:$max_summary}"
                        [[ ${#line} -gt $max_summary ]] && summary="${summary}..."

                        local symbol_entry
                        symbol_entry=$(jq -n \
                            --arg name "$class_name" \
                            --arg type "class" \
                            --arg file "$file" \
                            --arg summary "$summary" \
                            '{
                                name: $name,
                                type: $type,
                                file: $file,
                                summary: $summary
                            }')
                        classes+=("$symbol_entry")
                        ((total_symbols++))
                    fi
                fi
            done < <(grep -E "^[[:space:]]*(export[[:space:]]+)?class[[:space:]]+[a-zA-Z_]" "$file" 2>/dev/null || true)

        done < <(find . -name "$pattern" -type f -print0 2>/dev/null)
    done

    # Build symbols array
    local all_functions="[]"
    local all_classes="[]"

    if [[ ${#functions[@]} -gt 0 ]]; then
        all_functions=$(printf '%s\n' "${functions[@]}" | jq -s .)
    fi

    if [[ ${#classes[@]} -gt 0 ]]; then
        all_classes=$(printf '%s\n' "${classes[@]}" | jq -s .)
    fi

    # Update symbols graph
    symbols_graph=$(echo "$symbols_graph" | jq \
        --argjson functions "$all_functions" \
        --argjson classes "$all_classes" \
        --arg updated "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --arg max_summary "$max_summary" \
        --arg total_symbols "$total_symbols" \
        '{
            symbols: {
                functions: $functions,
                classes: $classes,
                interfaces: .symbols.interfaces,
                types: .symbols.types,
                constants: .symbols.constants
            },
            relationships: .relationships,
            metadata: {
                updated: $updated,
                generator: "artifact-utils.sh",
                max_summary_length: ($max_summary | tonumber),
                total_symbols: ($total_symbols | tonumber)
            }
        }')

    # Output or save
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}Dry run - Symbols graph:${NC}"
        echo "$symbols_graph" | jq .
    else
        echo "$symbols_graph" > "$SYMBOLS_GRAPH_FILE"
        echo -e "${GREEN}✓ Updated symbols graph: $SYMBOLS_GRAPH_FILE (${total_symbols} symbols)${NC}"
    fi

    return 0
}

# Validate chunking configuration
validate_chunking_config() {
    local chunk_size="${1:-8192}"
    local overlap="${2:-200}"
    local validate_embeddings="${3:-false}"
    local dry_run="${4:-false}"

    echo -e "${BLUE}=== Validating Chunking Configuration ===${NC}"

    ensure_ai_directory

    # Default chunking configuration
    local chunking_config
    chunking_config=$(cat << 'EOF'
{
  "chunk_size": 8192,
  "chunk_overlap": 200,
  "separators": ["\n\n", "\n", " ", ""],
  "keep_separator": true,
  "length_function": "token_count",
  "metadata": {
    "updated": "",
    "generator": "artifact-utils.sh",
    "validation_passed": false,
    "estimated_chunks": 0
  }
}
EOF
    )

    # Update configuration values
    chunking_config=$(echo "$chunking_config" | jq \
        --arg chunk_size "$chunk_size" \
        --arg overlap "$overlap" \
        --arg updated "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        '.chunk_size = ($chunk_size | tonumber) |
         .chunk_overlap = ($overlap | tonumber) |
         .metadata.updated = $updated')

    # Validate configuration
    local validation_errors=()

    if [[ $chunk_size -lt 512 ]]; then
        validation_errors+=("Chunk size too small (${chunk_size} < 512)")
    fi

    if [[ $chunk_size -gt 32768 ]]; then
        validation_errors+=("Chunk size too large (${chunk_size} > 32768)")
    fi

    if [[ $overlap -ge $((chunk_size / 2)) ]]; then
        validation_errors+=("Overlap too large (${overlap} >= ${chunk_size}/2)")
    fi

    # Estimate total chunks for project
    local estimated_chunks=0
    if command -v find >/dev/null 2>&1 && command -v wc >/dev/null 2>&1; then
        local total_chars
        total_chars=$(find . -name "*.md" -o -name "*.ts" -o -name "*.js" -o -name "*.py" | \
            grep -v node_modules | \
            xargs wc -c 2>/dev/null | \
            tail -1 | \
            awk '{print $1}' || echo "0")

        if [[ $total_chars -gt 0 ]]; then
            estimated_chunks=$(( (total_chars + chunk_size - 1) / chunk_size ))
        fi
    fi

    # Update validation results
    local validation_passed="true"
    if [[ ${#validation_errors[@]} -gt 0 ]]; then
        validation_passed="false"
        echo -e "${RED}❌ Validation errors:${NC}"
        printf "  - %s\n" "${validation_errors[@]}"
    else
        echo -e "${GREEN}✓ Chunking configuration is valid${NC}"
    fi

    chunking_config=$(echo "$chunking_config" | jq \
        --arg validation_passed "$validation_passed" \
        --arg estimated_chunks "$estimated_chunks" \
        '.metadata.validation_passed = ($validation_passed == "true") |
         .metadata.estimated_chunks = ($estimated_chunks | tonumber)')

    # Output or save
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}Dry run - Chunking configuration:${NC}"
        echo "$chunking_config" | jq .
    else
        echo "$chunking_config" > "$CHUNKING_CONFIG_FILE"
        echo -e "${GREEN}✓ Updated chunking config: $CHUNKING_CONFIG_FILE${NC}"
        echo -e "  Chunk size: ${chunk_size}, Overlap: ${overlap}, Estimated chunks: ${estimated_chunks}"
    fi

    return 0
}

# Update AI hints
update_ai_hints() {
    local patterns_only="${1:-false}"
    local include_examples="${2:-true}"
    local format="${3:-markdown}"
    local dry_run="${4:-false}"

    echo -e "${BLUE}=== Updating AI Hints ===${NC}"

    ensure_ai_directory

    # Build hints content
    local hints_content
    hints_content=$(cat << 'EOF'
# AI Hints and Patterns

This file contains architectural patterns, conventions, and guidance for AI agents working with the SkillMeat codebase.

## Architecture Patterns

### Layered Architecture
The codebase follows strict layered architecture:
- **Routers** → handle HTTP requests and responses
- **Services** → contain business logic and coordinate operations
- **Repositories** → handle data access and RLS (Row Level Security)
- **Models** → define data structures and validation

### Component Patterns
- Use `@meaty/ui` for all UI components
- Implement proper error boundaries
- Follow atomic design principles
- Ensure accessibility compliance

### State Management
- Use React Query for server state
- Implement proper loading and error states
- Use Zustand for client state when needed
- Follow unidirectional data flow

## Coding Conventions

### Naming
- Use camelCase for variables and functions
- Use PascalCase for components and types
- Use SCREAMING_SNAKE_CASE for constants
- Use kebab-case for file names

### Error Handling
- Always use ErrorResponse envelope for API errors
- Implement proper error boundaries in React
- Log errors with structured data (trace_id, user_id)
- Provide user-friendly error messages

### Testing
- Write tests for critical paths
- Use meaningful test descriptions
- Mock external dependencies
- Include accessibility tests

## Performance Guidelines

### Backend
- Use cursor pagination for lists
- Implement proper database indexes
- Use connection pooling
- Cache frequently accessed data

### Frontend
- Implement code splitting
- Use React.memo for expensive components
- Optimize bundle size
- Use proper image optimization

## Security Considerations

- Validate all inputs
- Use proper authentication/authorization
- Implement CSRF protection
- Follow principle of least privilege
- Never log sensitive information

---

Generated by artifact-utils.sh
EOF
    )

    # Add examples if requested
    if [[ "$include_examples" == "true" ]]; then
        hints_content=$(cat << 'EOF'

## Code Examples

### Service Layer Example
```typescript
// Good service implementation
export class UserService {
  constructor(private userRepo: UserRepository) {}

  async createUser(data: CreateUserDto): Promise<UserDto> {
    // Validate input
    const validated = validateCreateUser(data);

    // Business logic
    const user = await this.userRepo.create(validated);

    // Transform to DTO
    return mapToUserDto(user);
  }
}
```

### Error Handling Example
```typescript
// Good error handling
try {
  const result = await service.operation();
  return { success: true, data: result };
} catch (error) {
  logger.error('Operation failed', { error, trace_id });
  return ErrorResponse.internal('Operation failed');
}
```

### Component Example
```typescript
// Good component structure
export const UserCard: React.FC<UserCardProps> = ({ user }) => {
  const { data, isLoading, error } = useUser(user.id);

  if (isLoading) return <UserCardSkeleton />;
  if (error) return <ErrorBoundary error={error} />;

  return (
    <Card>
      <UserAvatar user={data} />
      <UserInfo user={data} />
    </Card>
  );
};
```

EOF
        )
    fi

    # Add updated timestamp
    hints_content="${hints_content}
Last updated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
"

    # Output or save
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}Dry run - AI hints content:${NC}"
        echo "$hints_content"
    else
        echo "$hints_content" > "$HINTS_FILE"
        echo -e "${GREEN}✓ Updated AI hints: $HINTS_FILE${NC}"
    fi

    return 0
}

# Refresh all AI artifacts
refresh_all_ai_artifacts() {
    local force_all="${1:-false}"
    local skip_validation="${2:-false}"
    local parallel="${3:-false}"
    local dry_run="${4:-false}"

    echo -e "${BLUE}=== Refreshing All AI Artifacts ===${NC}"

    ensure_ai_directory

    local errors=0

    # Run artifact updates
    if [[ "$parallel" == "true" ]]; then
        echo "Running artifact updates in parallel..."
        (
            update_repo_map "true" "json" "$dry_run" || ((errors++)) &
            update_symbols_graph "280" "false" "all" "$dry_run" || ((errors++)) &
            validate_chunking_config "8192" "200" "false" "$dry_run" || ((errors++)) &
            update_ai_hints "false" "true" "markdown" "$dry_run" || ((errors++)) &
            wait
        )
    else
        echo "Running artifact updates sequentially..."
        update_repo_map "true" "json" "$dry_run" || ((errors++))
        update_symbols_graph "280" "false" "all" "$dry_run" || ((errors++))
        validate_chunking_config "8192" "200" "false" "$dry_run" || ((errors++))
        update_ai_hints "false" "true" "markdown" "$dry_run" || ((errors++))
    fi

    # Summary
    if [[ $errors -eq 0 ]]; then
        echo -e "${GREEN}✓ All AI artifacts refreshed successfully${NC}"
    else
        echo -e "${RED}❌ ${errors} errors occurred during artifact refresh${NC}"
        return 1
    fi

    return 0
}

# Check if jq is available (required for JSON operations)
check_jq_available() {
    if ! command -v jq >/dev/null 2>&1; then
        echo -e "${RED}Error: jq is required but not installed${NC}" >&2
        echo "Please install jq: https://stedolan.github.io/jq/download/" >&2
        return 1
    fi
    return 0
}

# Main function for testing
main() {
    local command="${1:-help}"

    case "$command" in
        "repo-map")
            check_jq_available || exit 1
            update_repo_map "${2:-true}" "${3:-json}" "${4:-false}"
            ;;
        "symbols")
            check_jq_available || exit 1
            update_symbols_graph "${2:-280}" "${3:-false}" "${4:-all}" "${5:-false}"
            ;;
        "chunking")
            check_jq_available || exit 1
            validate_chunking_config "${2:-8192}" "${3:-200}" "${4:-false}" "${5:-false}"
            ;;
        "hints")
            update_ai_hints "${2:-false}" "${3:-true}" "${4:-markdown}" "${5:-false}"
            ;;
        "refresh-all")
            check_jq_available || exit 1
            refresh_all_ai_artifacts "${2:-false}" "${3:-false}" "${4:-false}" "${5:-false}"
            ;;
        "help"|*)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  repo-map [include_deps] [format] [dry_run]"
            echo "  symbols [max_summary] [include_private] [language] [dry_run]"
            echo "  chunking [chunk_size] [overlap] [validate_embeddings] [dry_run]"
            echo "  hints [patterns_only] [include_examples] [format] [dry_run]"
            echo "  refresh-all [force_all] [skip_validation] [parallel] [dry_run]"
            echo ""
            echo "Examples:"
            echo "  $0 repo-map true json false"
            echo "  $0 symbols 280 false all true"
            echo "  $0 refresh-all false false true false"
            ;;
    esac
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
