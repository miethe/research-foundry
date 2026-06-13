#!/bin/bash

# Contract utilities for Claude commands
# API contract management functions used across artifact commands

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
source "$SCRIPT_DIR/validation-utils.sh" 2>/dev/null || true

# Contract configuration
readonly CONTRACTS_DIR="contracts"
readonly VERSIONS_DIR="$CONTRACTS_DIR/versions"
readonly SCHEMAS_DIR="$CONTRACTS_DIR/schemas"

# Ensure contracts directory structure
ensure_contracts_directory() {
    for dir in "$CONTRACTS_DIR" "$VERSIONS_DIR" "$SCHEMAS_DIR"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo -e "${GREEN}✓ Created directory: $dir${NC}"
        fi
    done

    # Create main README if missing
    if [[ ! -f "$CONTRACTS_DIR/README.md" ]]; then
        cat > "$CONTRACTS_DIR/README.md" << 'EOF'
# API Contracts Directory

This directory contains versioned API contracts and schemas:

- **versions/**: Timestamped contract versions following semver
- **schemas/**: Reusable JSON schemas for validation
- **openapi.json**: Current OpenAPI specification
- **asyncapi.json**: Current AsyncAPI specification (if applicable)

Contract versions are automatically managed by the artifact command system.
EOF
        echo -e "${GREEN}✓ Created contracts directory README${NC}"
    fi
}

# Validate OpenAPI specification
validate_openapi_spec() {
    local spec_file="${1:-openapi.json}"
    local strict_mode="${2:-false}"
    local fix_errors="${3:-false}"

    echo -e "${BLUE}=== Validating OpenAPI Specification ===${NC}"

    if [[ ! -f "$spec_file" ]]; then
        echo -e "${RED}❌ OpenAPI spec not found: $spec_file${NC}"
        return 1
    fi

    # Check basic JSON validity
    if ! validate_json_file "$spec_file" true; then
        echo -e "${RED}❌ Invalid JSON in OpenAPI spec${NC}"
        return 1
    fi

    local violations=0
    local spec_content
    spec_content=$(cat "$spec_file")

    # Check required OpenAPI fields
    local required_fields=("openapi" "info" "paths")
    for field in "${required_fields[@]}"; do
        local field_value
        field_value=$(echo "$spec_content" | jq -r ".$field // empty" 2>/dev/null)

        if [[ -z "$field_value" || "$field_value" == "null" ]]; then
            echo -e "${RED}❌ Missing required field: $field${NC}"
            violations=$((violations + 1))
        else
            echo -e "${GREEN}✓ Required field present: $field${NC}"
        fi
    done

    # Validate OpenAPI version
    local openapi_version
    openapi_version=$(echo "$spec_content" | jq -r '.openapi // empty')

    if [[ -n "$openapi_version" ]]; then
        if [[ "$openapi_version" =~ ^3\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "${GREEN}✓ Valid OpenAPI version: $openapi_version${NC}"
        else
            echo -e "${YELLOW}⚠ Non-standard OpenAPI version: $openapi_version${NC}"
            violations=$((violations + 1))
        fi
    fi

    # Validate info section
    local info_fields=("title" "version")
    for field in "${info_fields[@]}"; do
        local field_value
        field_value=$(echo "$spec_content" | jq -r ".info.$field // empty")

        if [[ -z "$field_value" || "$field_value" == "null" ]]; then
            echo -e "${RED}❌ Missing info.$field${NC}"
            violations=$((violations + 1))
        else
            echo -e "${GREEN}✓ Info field present: $field${NC}"
        fi
    done

    # Validate paths
    local paths_count
    paths_count=$(echo "$spec_content" | jq '.paths | length' 2>/dev/null || echo "0")

    if [[ $paths_count -eq 0 ]]; then
        echo -e "${YELLOW}⚠ No paths defined in specification${NC}"
        violations=$((violations + 1))
    else
        echo -e "${GREEN}✓ Paths defined: $paths_count${NC}"

        # Check for proper HTTP methods
        local methods_found=()
        mapfile -t methods_found < <(echo "$spec_content" | jq -r '.paths | to_entries[] | .value | keys[]' 2>/dev/null | sort -u)

        if [[ ${#methods_found[@]} -gt 0 ]]; then
            echo -e "${GREEN}✓ HTTP methods found: ${methods_found[*]}${NC}"
        fi
    fi

    # Check for components/schemas (strict mode)
    if [[ "$strict_mode" == "true" ]]; then
        local components_count
        components_count=$(echo "$spec_content" | jq '.components.schemas | length' 2>/dev/null || echo "0")

        if [[ $components_count -eq 0 ]]; then
            echo -e "${YELLOW}⚠ No components/schemas defined${NC}"
            violations=$((violations + 1))
        else
            echo -e "${GREEN}✓ Components/schemas defined: $components_count${NC}"
        fi

        # Check for security definitions
        local security_schemes
        security_schemes=$(echo "$spec_content" | jq '.components.securitySchemes | length' 2>/dev/null || echo "0")

        if [[ $security_schemes -eq 0 ]]; then
            echo -e "${YELLOW}⚠ No security schemes defined${NC}"
            violations=$((violations + 1))
        else
            echo -e "${GREEN}✓ Security schemes defined: $security_schemes${NC}"
        fi
    fi

    # Summary
    if [[ $violations -eq 0 ]]; then
        echo -e "${GREEN}✓ OpenAPI specification is valid${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $violations validation issues${NC}"
        return 1
    fi
}

# Validate AsyncAPI specification
validate_asyncapi_spec() {
    local spec_file="${1:-asyncapi.json}"
    local strict_mode="${2:-false}"

    echo -e "${BLUE}=== Validating AsyncAPI Specification ===${NC}"

    if [[ ! -f "$spec_file" ]]; then
        echo -e "${YELLOW}⚠ AsyncAPI spec not found: $spec_file (optional)${NC}"
        return 0
    fi

    # Check basic JSON validity
    if ! validate_json_file "$spec_file" true; then
        echo -e "${RED}❌ Invalid JSON in AsyncAPI spec${NC}"
        return 1
    fi

    local violations=0
    local spec_content
    spec_content=$(cat "$spec_file")

    # Check required AsyncAPI fields
    local required_fields=("asyncapi" "info" "channels")
    for field in "${required_fields[@]}"; do
        local field_value
        field_value=$(echo "$spec_content" | jq -r ".$field // empty" 2>/dev/null)

        if [[ -z "$field_value" || "$field_value" == "null" ]]; then
            echo -e "${RED}❌ Missing required field: $field${NC}"
            violations=$((violations + 1))
        else
            echo -e "${GREEN}✓ Required field present: $field${NC}"
        fi
    done

    # Validate AsyncAPI version
    local asyncapi_version
    asyncapi_version=$(echo "$spec_content" | jq -r '.asyncapi // empty')

    if [[ -n "$asyncapi_version" ]]; then
        if [[ "$asyncapi_version" =~ ^[2-9]\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "${GREEN}✓ Valid AsyncAPI version: $asyncapi_version${NC}"
        else
            echo -e "${YELLOW}⚠ Non-standard AsyncAPI version: $asyncapi_version${NC}"
            violations=$((violations + 1))
        fi
    fi

    # Validate channels
    local channels_count
    channels_count=$(echo "$spec_content" | jq '.channels | length' 2>/dev/null || echo "0")

    if [[ $channels_count -eq 0 ]]; then
        echo -e "${YELLOW}⚠ No channels defined in specification${NC}"
        violations=$((violations + 1))
    else
        echo -e "${GREEN}✓ Channels defined: $channels_count${NC}"
    fi

    if [[ $violations -eq 0 ]]; then
        echo -e "${GREEN}✓ AsyncAPI specification is valid${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $violations validation issues${NC}"
        return 1
    fi
}

# Detect breaking changes between API versions
detect_breaking_changes() {
    local current_spec="${1:-openapi.json}"
    local previous_spec="${2}"
    local spec_type="${3:-openapi}"

    echo -e "${BLUE}=== Detecting Breaking Changes ===${NC}"

    if [[ ! -f "$current_spec" ]]; then
        echo -e "${RED}❌ Current spec not found: $current_spec${NC}"
        return 1
    fi

    if [[ ! -f "$previous_spec" ]]; then
        echo -e "${YELLOW}⚠ Previous spec not found: $previous_spec${NC}"
        echo "Cannot detect breaking changes without previous version"
        return 0
    fi

    local breaking_changes=0
    local current_content previous_content
    current_content=$(cat "$current_spec")
    previous_content=$(cat "$previous_spec")

    case "$spec_type" in
        "openapi")
            breaking_changes=$(detect_openapi_breaking_changes "$current_content" "$previous_content")
            ;;
        "asyncapi")
            breaking_changes=$(detect_asyncapi_breaking_changes "$current_content" "$previous_content")
            ;;
        *)
            echo -e "${RED}❌ Unsupported spec type: $spec_type${NC}"
            return 1
            ;;
    esac

    if [[ $breaking_changes -eq 0 ]]; then
        echo -e "${GREEN}✓ No breaking changes detected${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $breaking_changes potential breaking changes${NC}"
        return 1
    fi
}

# Detect OpenAPI breaking changes
detect_openapi_breaking_changes() {
    local current_content="$1"
    local previous_content="$2"

    local breaking_changes=0

    # Get paths from both specs
    local current_paths previous_paths
    current_paths=$(echo "$current_content" | jq -r '.paths | keys[]' 2>/dev/null | sort)
    previous_paths=$(echo "$previous_content" | jq -r '.paths | keys[]' 2>/dev/null | sort)

    # Check for removed paths
    while IFS= read -r path; do
        if [[ -n "$path" ]] && ! echo "$current_paths" | grep -Fxq "$path"; then
            echo -e "${RED}❌ Removed path: $path${NC}"
            breaking_changes=$((breaking_changes + 1))
        fi
    done <<< "$previous_paths"

    # Check for removed HTTP methods
    while IFS= read -r path; do
        if [[ -n "$path" ]]; then
            local current_methods previous_methods
            current_methods=$(echo "$current_content" | jq -r ".paths[\"$path\"] | keys[]" 2>/dev/null | sort)
            previous_methods=$(echo "$previous_content" | jq -r ".paths[\"$path\"] | keys[]" 2>/dev/null | sort)

            while IFS= read -r method; do
                if [[ -n "$method" ]] && ! echo "$current_methods" | grep -Fxq "$method"; then
                    echo -e "${RED}❌ Removed method: $method $path${NC}"
                    breaking_changes=$((breaking_changes + 1))
                fi
            done <<< "$previous_methods"
        fi
    done <<< "$previous_paths"

    # Check for required parameter changes
    while IFS= read -r path; do
        if [[ -n "$path" ]] && echo "$current_paths" | grep -Fxq "$path"; then
            local methods
            methods=$(echo "$current_content" | jq -r ".paths[\"$path\"] | keys[]" 2>/dev/null)

            while IFS= read -r method; do
                if [[ -n "$method" ]]; then
                    # Check for new required parameters
                    local current_required previous_required
                    current_required=$(echo "$current_content" | jq -r ".paths[\"$path\"][\"$method\"].parameters[]? | select(.required == true) | .name" 2>/dev/null | sort)
                    previous_required=$(echo "$previous_content" | jq -r ".paths[\"$path\"][\"$method\"].parameters[]? | select(.required == true) | .name" 2>/dev/null | sort)

                    while IFS= read -r param; do
                        if [[ -n "$param" ]] && ! echo "$previous_required" | grep -Fxq "$param"; then
                            echo -e "${RED}❌ New required parameter: $param in $method $path${NC}"
                            breaking_changes=$((breaking_changes + 1))
                        fi
                    done <<< "$current_required"
                fi
            done <<< "$methods"
        fi
    done <<< "$current_paths"

    echo "$breaking_changes"
}

# Detect AsyncAPI breaking changes
detect_asyncapi_breaking_changes() {
    local current_content="$1"
    local previous_content="$2"

    local breaking_changes=0

    # Get channels from both specs
    local current_channels previous_channels
    current_channels=$(echo "$current_content" | jq -r '.channels | keys[]' 2>/dev/null | sort)
    previous_channels=$(echo "$previous_content" | jq -r '.channels | keys[]' 2>/dev/null | sort)

    # Check for removed channels
    while IFS= read -r channel; do
        if [[ -n "$channel" ]] && ! echo "$current_channels" | grep -Fxq "$channel"; then
            echo -e "${RED}❌ Removed channel: $channel${NC}"
            breaking_changes=$((breaking_changes + 1))
        fi
    done <<< "$previous_channels"

    echo "$breaking_changes"
}

# Freeze API contract version
freeze_api_version() {
    local version="${1}"
    local spec_file="${2:-openapi.json}"
    local generate_examples="${3:-true}"
    local dry_run="${4:-false}"

    echo -e "${BLUE}=== Freezing API Contract Version ===${NC}"

    if [[ -z "$version" ]]; then
        echo -e "${RED}❌ Version is required${NC}"
        return 1
    fi

    if [[ ! -f "$spec_file" ]]; then
        echo -e "${RED}❌ Spec file not found: $spec_file${NC}"
        return 1
    fi

    # Validate semantic version format
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${RED}❌ Invalid semantic version format: $version${NC}"
        return 1
    fi

    ensure_contracts_directory

    # Create versioned filename
    local timestamp
    timestamp=$(date +%Y%m%d-%H%M%S)
    local versioned_file="$VERSIONS_DIR/v${version}-${timestamp}.json"

    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}Dry run - Would create: $versioned_file${NC}"
        return 0
    fi

    # Update version in spec and freeze
    local updated_spec
    updated_spec=$(jq --arg version "$version" '.info.version = $version' "$spec_file")

    # Add freeze metadata
    updated_spec=$(echo "$updated_spec" | jq \
        --arg timestamp "$timestamp" \
        --arg frozen_by "contract-utils.sh" \
        '.info["x-frozen"] = {
            timestamp: $timestamp,
            frozen_by: $frozen_by,
            original_file: "'$spec_file'"
        }')

    # Save frozen version
    echo "$updated_spec" > "$versioned_file"
    echo -e "${GREEN}✓ Frozen API contract: $versioned_file${NC}"

    # Generate examples if requested
    if [[ "$generate_examples" == "true" ]]; then
        generate_contract_examples "$versioned_file" "$version"
    fi

    # Create version manifest
    create_version_manifest "$version" "$versioned_file" "$spec_file"

    return 0
}

# Generate contract examples
generate_contract_examples() {
    local spec_file="$1"
    local version="$2"

    echo -e "${BLUE}Generating contract examples for version $version${NC}"

    local examples_dir="$VERSIONS_DIR/v${version}-examples"
    mkdir -p "$examples_dir"

    local spec_content
    spec_content=$(cat "$spec_file")

    # Generate example requests/responses for each path
    local paths
    paths=$(echo "$spec_content" | jq -r '.paths | keys[]' 2>/dev/null)

    while IFS= read -r path; do
        if [[ -n "$path" ]]; then
            local methods
            methods=$(echo "$spec_content" | jq -r ".paths[\"$path\"] | keys[]" 2>/dev/null)

            while IFS= read -r method; do
                if [[ -n "$method" ]]; then
                    local example_file="$examples_dir/${method}_${path//\//_}.json"

                    # Create basic example structure
                    local example_content
                    example_content=$(jq -n \
                        --arg path "$path" \
                        --arg method "$method" \
                        --arg version "$version" \
                        '{
                            path: $path,
                            method: ($method | ascii_upcase),
                            version: $version,
                            example_request: {},
                            example_response: {},
                            generated_at: now | strftime("%Y-%m-%dT%H:%M:%SZ")
                        }')

                    echo "$example_content" > "$example_file"
                done
            done <<< "$methods"
        fi
    done <<< "$paths"

    echo -e "${GREEN}✓ Generated examples in: $examples_dir${NC}"
}

# Create version manifest
create_version_manifest() {
    local version="$1"
    local versioned_file="$2"
    local original_file="$3"

    local manifest_file="$VERSIONS_DIR/manifest.json"

    # Create or update manifest
    local manifest="{\"versions\": []}"

    if [[ -f "$manifest_file" ]]; then
        manifest=$(cat "$manifest_file")
    fi

    # Add new version entry
    manifest=$(echo "$manifest" | jq \
        --arg version "$version" \
        --arg file "$(basename "$versioned_file")" \
        --arg original "$original_file" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '.versions += [{
            version: $version,
            file: $file,
            original_file: $original,
            frozen_at: $timestamp
        }] | .versions |= sort_by(.version)')

    echo "$manifest" > "$manifest_file"
    echo -e "${GREEN}✓ Updated version manifest: $manifest_file${NC}"
}

# List contract versions
list_contract_versions() {
    local format="${1:-text}"

    echo -e "${BLUE}=== Contract Versions ===${NC}"

    local manifest_file="$VERSIONS_DIR/manifest.json"

    if [[ ! -f "$manifest_file" ]]; then
        echo -e "${YELLOW}⚠ No version manifest found${NC}"
        return 0
    fi

    case "$format" in
        "json")
            cat "$manifest_file"
            ;;
        "text"|*)
            local versions
            versions=$(jq -r '.versions[] | "\(.version) - \(.file) (frozen: \(.frozen_at))"' "$manifest_file" 2>/dev/null)

            if [[ -n "$versions" ]]; then
                echo "$versions"
            else
                echo "No versions found"
            fi
            ;;
    esac
}

# Compare contract versions
compare_contract_versions() {
    local version1="$1"
    local version2="$2"
    local output_format="${3:-text}"

    echo -e "${BLUE}=== Comparing Contract Versions ===${NC}"

    if [[ -z "$version1" || -z "$version2" ]]; then
        echo -e "${RED}❌ Both versions are required${NC}"
        return 1
    fi

    # Find version files
    local file1 file2
    file1=$(find "$VERSIONS_DIR" -name "v${version1}-*.json" | head -1)
    file2=$(find "$VERSIONS_DIR" -name "v${version2}-*.json" | head -1)

    if [[ ! -f "$file1" ]]; then
        echo -e "${RED}❌ Version not found: $version1${NC}"
        return 1
    fi

    if [[ ! -f "$file2" ]]; then
        echo -e "${RED}❌ Version not found: $version2${NC}"
        return 1
    fi

    echo "Comparing $version1 vs $version2"

    # Detect breaking changes
    detect_breaking_changes "$file2" "$file1" "openapi"
}

# Main function for testing
main() {
    local command="${1:-help}"

    case "$command" in
        "validate-openapi")
            validate_openapi_spec "${2:-openapi.json}" "${3:-false}" "${4:-false}"
            ;;
        "validate-asyncapi")
            validate_asyncapi_spec "${2:-asyncapi.json}" "${3:-false}"
            ;;
        "detect-breaking")
            detect_breaking_changes "${2:-openapi.json}" "$3" "${4:-openapi}"
            ;;
        "freeze")
            freeze_api_version "$2" "${3:-openapi.json}" "${4:-true}" "${5:-false}"
            ;;
        "list-versions")
            list_contract_versions "${2:-text}"
            ;;
        "compare")
            compare_contract_versions "$2" "$3" "${4:-text}"
            ;;
        "help"|*)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  validate-openapi [spec_file] [strict_mode] [fix_errors]"
            echo "  validate-asyncapi [spec_file] [strict_mode]"
            echo "  detect-breaking [current_spec] [previous_spec] [spec_type]"
            echo "  freeze [version] [spec_file] [generate_examples] [dry_run]"
            echo "  list-versions [format]"
            echo "  compare [version1] [version2] [format]"
            echo ""
            echo "Examples:"
            echo "  $0 validate-openapi openapi.json true"
            echo "  $0 freeze 1.2.0 openapi.json true false"
            echo "  $0 compare 1.1.0 1.2.0"
            ;;
    esac
}

# Check if jq is available (required for JSON operations)
if ! command -v jq >/dev/null 2>&1; then
    echo -e "${RED}Error: jq is required but not installed${NC}" >&2
    echo "Please install jq: https://stedolan.github.io/jq/download/" >&2
    exit 1
fi

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
