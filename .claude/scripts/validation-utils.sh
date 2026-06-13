#!/bin/bash

# Validation utilities for Claude commands
# Common validation functions used across artifact commands

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

# Validate package.json structure
validate_package_json() {
    local file_path="${1:-package.json}"
    local strict="${2:-false}"

    if [[ ! -f "$file_path" ]]; then
        echo -e "${RED}✗ package.json not found: $file_path${NC}" >&2
        return 1
    fi

    # Basic JSON validation
    if ! validate_json_file "$file_path" true; then
        echo -e "${RED}✗ Invalid JSON in: $file_path${NC}" >&2
        return 1
    fi

    # Required fields validation
    local required_fields=("name" "version")
    local missing_fields=()

    for field in "${required_fields[@]}"; do
        local value
        value=$(json_extract "$file_path" ".$field" "file")
        if [[ "$value" == "null" || -z "$value" ]]; then
            missing_fields+=("$field")
        fi
    done

    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required fields in $file_path:${NC}"
        printf "  - %s\n" "${missing_fields[@]}"
        return 1
    fi

    # Strict validation
    if [[ "$strict" == "true" ]]; then
        local recommended_fields=("description" "scripts" "dependencies")
        local missing_recommended=()

        for field in "${recommended_fields[@]}"; do
            local value
            value=$(json_extract "$file_path" ".$field" "file")
            if [[ "$value" == "null" ]]; then
                missing_recommended+=("$field")
            fi
        done

        if [[ ${#missing_recommended[@]} -gt 0 ]]; then
            echo -e "${YELLOW}⚠ Missing recommended fields in $file_path:${NC}"
            printf "  - %s\n" "${missing_recommended[@]}"
        fi
    fi

    echo -e "${GREEN}✓ Valid package.json: $file_path${NC}"
    return 0
}

# Validate pyproject.toml structure
validate_pyproject_toml() {
    local file_path="${1:-pyproject.toml}"
    local strict="${2:-false}"

    if [[ ! -f "$file_path" ]]; then
        echo -e "${RED}✗ pyproject.toml not found: $file_path${NC}" >&2
        return 1
    fi

    # Check for required sections using basic parsing
    local required_sections=("project" "build-system")
    local missing_sections=()

    for section in "${required_sections[@]}"; do
        if ! grep -q "^\[$section\]" "$file_path"; then
            missing_sections+=("$section")
        fi
    done

    if [[ ${#missing_sections[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required sections in $file_path:${NC}"
        printf "  - %s\n" "${missing_sections[@]}"
        return 1
    fi

    # Check for required project fields
    local required_fields=("name" "version")
    local missing_fields=()

    for field in "${required_fields[@]}"; do
        if ! grep -q "^$field\s*=" "$file_path"; then
            missing_fields+=("$field")
        fi
    done

    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required project fields in $file_path:${NC}"
        printf "  - %s\n" "${missing_fields[@]}"
        return 1
    fi

    echo -e "${GREEN}✓ Valid pyproject.toml: $file_path${NC}"
    return 0
}

# Validate TypeScript configuration
validate_tsconfig() {
    local file_path="${1:-tsconfig.json}"

    if [[ ! -f "$file_path" ]]; then
        echo -e "${RED}✗ TypeScript config not found: $file_path${NC}" >&2
        return 1
    fi

    # Basic JSON validation
    if ! validate_json_file "$file_path" true; then
        echo -e "${RED}✗ Invalid JSON in: $file_path${NC}" >&2
        return 1
    fi

    # Check for compilerOptions
    local compiler_options
    compiler_options=$(json_extract "$file_path" ".compilerOptions" "file")
    if [[ "$compiler_options" == "null" ]]; then
        echo -e "${YELLOW}⚠ No compilerOptions found in: $file_path${NC}"
    fi

    # Check for common TypeScript settings
    local target
    target=$(json_extract "$file_path" ".compilerOptions.target" "file")
    if [[ "$target" == "null" ]]; then
        echo -e "${YELLOW}⚠ No target specified in compilerOptions${NC}"
    fi

    echo -e "${GREEN}✓ Valid TypeScript config: $file_path${NC}"
    return 0
}

# Validate environment variables
validate_env_vars() {
    local required_vars=("$@")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required environment variables:${NC}"
        printf "  - %s\n" "${missing_vars[@]}"
        return 1
    fi

    echo -e "${GREEN}✓ All required environment variables are set${NC}"
    return 0
}

# Validate file permissions
validate_file_permissions() {
    local file_path="$1"
    local expected_perms="$2" # e.g., "rwx", "rw", "r"

    if ! check_permissions "$file_path" "$expected_perms" > /dev/null 2>&1; then
        echo -e "${RED}✗ Incorrect permissions for: $file_path${NC}" >&2
        echo -e "  Expected: $expected_perms" >&2
        return 1
    fi

    echo -e "${GREEN}✓ Correct permissions for: $file_path${NC}"
    return 0
}

# Validate directory structure
validate_directory_structure() {
    local base_dir="$1"
    shift
    local required_dirs=("$@")
    local missing_dirs=()

    if [[ ! -d "$base_dir" ]]; then
        echo -e "${RED}✗ Base directory not found: $base_dir${NC}" >&2
        return 1
    fi

    for dir in "${required_dirs[@]}"; do
        local full_path="$base_dir/$dir"
        if [[ ! -d "$full_path" ]]; then
            missing_dirs+=("$dir")
        fi
    done

    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required directories in $base_dir:${NC}"
        printf "  - %s\n" "${missing_dirs[@]}"
        return 1
    fi

    echo -e "${GREEN}✓ Valid directory structure in: $base_dir${NC}"
    return 0
}

# Validate required files exist
validate_required_files() {
    local base_dir="${1:-.}"
    shift
    local required_files=("$@")
    local missing_files=()

    for file in "${required_files[@]}"; do
        local full_path="$base_dir/$file"
        if [[ ! -f "$full_path" ]]; then
            missing_files+=("$file")
        fi
    done

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required files in $base_dir:${NC}"
        printf "  - %s\n" "${missing_files[@]}"
        return 1
    fi

    echo -e "${GREEN}✓ All required files found in: $base_dir${NC}"
    return 0
}

# Validate URL format
validate_url() {
    local url="$1"
    local url_regex='^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'

    if [[ $url =~ $url_regex ]]; then
        echo -e "${GREEN}✓ Valid URL format: $url${NC}"
        return 0
    else
        echo -e "${RED}✗ Invalid URL format: $url${NC}" >&2
        return 1
    fi
}

# Validate email format
validate_email() {
    local email="$1"
    local email_regex='^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if [[ $email =~ $email_regex ]]; then
        echo -e "${GREEN}✓ Valid email format: $email${NC}"
        return 0
    else
        echo -e "${RED}✗ Invalid email format: $email${NC}" >&2
        return 1
    fi
}

# Validate semantic version format
validate_semver() {
    local version="$1"
    local semver_regex='^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'

    if [[ $version =~ $semver_regex ]]; then
        echo -e "${GREEN}✓ Valid semantic version: $version${NC}"
        return 0
    else
        echo -e "${RED}✗ Invalid semantic version: $version${NC}" >&2
        return 1
    fi
}

# Validate port number
validate_port() {
    local port="$1"

    if [[ $port =~ ^[0-9]+$ ]] && [[ $port -ge 1 ]] && [[ $port -le 65535 ]]; then
        echo -e "${GREEN}✓ Valid port number: $port${NC}"
        return 0
    else
        echo -e "${RED}✗ Invalid port number: $port (must be 1-65535)${NC}" >&2
        return 1
    fi
}

# Validate Git repository
validate_git_repository() {
    local repo_path="${1:-.}"

    if [[ ! -d "$repo_path/.git" ]]; then
        echo -e "${RED}✗ Not a Git repository: $repo_path${NC}" >&2
        return 1
    fi

    # Check if repository has commits
    if ! git -C "$repo_path" rev-parse HEAD > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Git repository has no commits: $repo_path${NC}"
    fi

    # Check for uncommitted changes
    if ! git -C "$repo_path" diff-index --quiet HEAD -- 2>/dev/null; then
        echo -e "${YELLOW}⚠ Git repository has uncommitted changes: $repo_path${NC}"
    fi

    echo -e "${GREEN}✓ Valid Git repository: $repo_path${NC}"
    return 0
}

# Validate command exists
validate_command_exists() {
    local command="$1"

    if command -v "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Command available: $command${NC}"
        return 0
    else
        echo -e "${RED}✗ Command not found: $command${NC}" >&2
        return 1
    fi
}

# Validate multiple commands exist
validate_commands_exist() {
    local commands=("$@")
    local missing_commands=()

    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" > /dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done

    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required commands:${NC}"
        printf "  - %s\n" "${missing_commands[@]}"
        return 1
    fi

    echo -e "${GREEN}✓ All required commands are available${NC}"
    return 0
}

# Validate Node.js version
validate_node_version() {
    local min_version="${1:-16.0.0}"

    if ! validate_command_exists "node"; then
        return 1
    fi

    local current_version
    current_version=$(node --version | sed 's/v//')

    # Simple version comparison (works for basic semver)
    if [[ "$current_version" == "$(echo -e "$current_version\n$min_version" | sort -V | tail -n1)" ]]; then
        echo -e "${GREEN}✓ Node.js version $current_version >= $min_version${NC}"
        return 0
    else
        echo -e "${RED}✗ Node.js version $current_version < $min_version${NC}" >&2
        return 1
    fi
}

# Validate Python version
validate_python_version() {
    local min_version="${1:-3.8.0}"
    local python_cmd="${2:-python3}"

    if ! validate_command_exists "$python_cmd"; then
        return 1
    fi

    local current_version
    current_version=$("$python_cmd" --version 2>&1 | awk '{print $2}')

    # Simple version comparison (works for basic semver)
    if [[ "$current_version" == "$(echo -e "$current_version\n$min_version" | sort -V | tail -n1)" ]]; then
        echo -e "${GREEN}✓ Python version $current_version >= $min_version${NC}"
        return 0
    else
        echo -e "${RED}✗ Python version $current_version < $min_version${NC}" >&2
        return 1
    fi
}

# Validate YAML file (basic validation)
validate_yaml_file() {
    local file_path="$1"

    if [[ ! -f "$file_path" ]]; then
        echo -e "${RED}✗ YAML file not found: $file_path${NC}" >&2
        return 1
    fi

    # Basic YAML validation using Python (if available)
    if command -v python3 > /dev/null 2>&1; then
        if python3 -c "
import yaml
import sys
try:
    with open('$file_path', 'r') as f:
        yaml.safe_load(f)
    print('✓ Valid YAML: $file_path')
except Exception as e:
    print(f'✗ Invalid YAML: $file_path - {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            echo -e "${GREEN}✓ Valid YAML: $file_path${NC}"
            return 0
        else
            echo -e "${RED}✗ Invalid YAML: $file_path${NC}" >&2
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ Cannot validate YAML (Python not available): $file_path${NC}"
        return 0
    fi
}

# Comprehensive project validation
validate_project() {
    local project_dir="${1:-.}"
    local project_type="${2:-auto}" # auto, node, python, mixed

    echo -e "${BLUE}Validating project: $project_dir${NC}"
    echo ""

    local validation_errors=0

    # Detect project type if auto
    if [[ "$project_type" == "auto" ]]; then
        if [[ -f "$project_dir/package.json" ]]; then
            project_type="node"
        elif [[ -f "$project_dir/pyproject.toml" ]] || [[ -f "$project_dir/setup.py" ]]; then
            project_type="python"
        elif [[ -f "$project_dir/package.json" ]] && [[ -f "$project_dir/pyproject.toml" ]]; then
            project_type="mixed"
        fi
    fi

    # Git repository validation
    if ! validate_git_repository "$project_dir"; then
        ((validation_errors++))
    fi

    # Project-type specific validation
    case "$project_type" in
        "node"|"mixed")
            if ! validate_package_json "$project_dir/package.json"; then
                ((validation_errors++))
            fi
            if [[ -f "$project_dir/tsconfig.json" ]]; then
                if ! validate_tsconfig "$project_dir/tsconfig.json"; then
                    ((validation_errors++))
                fi
            fi
            ;;
        "python"|"mixed")
            if [[ -f "$project_dir/pyproject.toml" ]]; then
                if ! validate_pyproject_toml "$project_dir/pyproject.toml"; then
                    ((validation_errors++))
                fi
            fi
            ;;
    esac

    echo ""
    if [[ $validation_errors -eq 0 ]]; then
        echo -e "${GREEN}✓ Project validation completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Project validation failed with $validation_errors error(s)${NC}"
        return 1
    fi
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "Validation utilities loaded. Available functions:"
    echo "  validate_package_json, validate_pyproject_toml, validate_tsconfig"
    echo "  validate_env_vars, validate_file_permissions, validate_directory_structure"
    echo "  validate_required_files, validate_url, validate_email, validate_semver"
    echo "  validate_port, validate_git_repository, validate_command_exists"
    echo "  validate_commands_exist, validate_node_version, validate_python_version"
    echo "  validate_yaml_file, validate_project"
fi
