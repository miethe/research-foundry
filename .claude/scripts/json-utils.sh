#!/bin/bash

# JSON utilities for Claude commands
# Common JSON operations used across artifact commands

# Only set these options if running as script, not when sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    set -euo pipefail
fi

# Colors for output (only set if not already defined)
if [[ -z "${RED:-}" ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m' # No Color
fi

# Check if jq is available
check_jq_available() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required but not installed${NC}" >&2
        echo "Please install jq: brew install jq (macOS) or apt-get install jq (Ubuntu)" >&2
        return 1
    fi
}

# Validate JSON string
validate_json() {
    local json_string="$1"
    local quiet="${2:-false}"

    check_jq_available || return 1

    if echo "$json_string" | jq . > /dev/null 2>&1; then
        [[ "$quiet" != "true" ]] && echo -e "${GREEN}JSON is valid${NC}"
        return 0
    else
        [[ "$quiet" != "true" ]] && echo -e "${RED}JSON is invalid${NC}" >&2
        return 1
    fi
}

# Validate JSON file
validate_json_file() {
    local file_path="$1"
    local quiet="${2:-false}"

    check_jq_available || return 1

    if [[ ! -f "$file_path" ]]; then
        [[ "$quiet" != "true" ]] && echo -e "${RED}File not found: $file_path${NC}" >&2
        return 1
    fi

    if jq . "$file_path" > /dev/null 2>&1; then
        [[ "$quiet" != "true" ]] && echo -e "${GREEN}JSON file is valid: $file_path${NC}"
        return 0
    else
        [[ "$quiet" != "true" ]] && echo -e "${RED}JSON file is invalid: $file_path${NC}" >&2
        return 1
    fi
}

# Pretty print JSON string
pretty_print_json() {
    local json_string="$1"

    check_jq_available || return 1
    validate_json "$json_string" true || return 1

    echo "$json_string" | jq .
}

# Pretty print JSON file
pretty_print_json_file() {
    local file_path="$1"

    check_jq_available || return 1
    validate_json_file "$file_path" true || return 1

    jq . "$file_path"
}

# Minify JSON string
minify_json() {
    local json_string="$1"

    check_jq_available || return 1
    validate_json "$json_string" true || return 1

    echo "$json_string" | jq -c .
}

# Minify JSON file
minify_json_file() {
    local file_path="$1"
    local output_file="${2:-}"

    check_jq_available || return 1
    validate_json_file "$file_path" true || return 1

    if [[ -n "$output_file" ]]; then
        jq -c . "$file_path" > "$output_file"
        echo -e "${GREEN}Minified JSON written to: $output_file${NC}"
    else
        jq -c . "$file_path"
    fi
}

# Extract value from JSON using jq query
json_extract() {
    local json_input="$1"
    local jq_query="$2"
    local input_type="${3:-string}" # string or file

    check_jq_available || return 1

    if [[ "$input_type" == "file" ]]; then
        validate_json_file "$json_input" true || return 1
        jq -r "$jq_query" "$json_input" 2>/dev/null || echo "null"
    else
        validate_json "$json_input" true || return 1
        echo "$json_input" | jq -r "$jq_query" 2>/dev/null || echo "null"
    fi
}

# Merge two JSON objects
json_merge() {
    local json1="$1"
    local json2="$2"
    local input_type="${3:-string}" # string or file

    check_jq_available || return 1

    if [[ "$input_type" == "file" ]]; then
        validate_json_file "$json1" true || return 1
        validate_json_file "$json2" true || return 1
        jq -s '.[0] * .[1]' "$json1" "$json2"
    else
        validate_json "$json1" true || return 1
        validate_json "$json2" true || return 1
        jq -s '.[0] * .[1]' <(echo "$json1") <(echo "$json2")
    fi
}

# Create JSON array from lines
lines_to_json_array() {
    local input="${1:-}"
    local quote_strings="${2:-true}"

    check_jq_available || return 1

    if [[ -n "$input" ]]; then
        # Input provided as argument
        if [[ "$quote_strings" == "true" ]]; then
            echo "$input" | jq -R . | jq -s .
        else
            echo "$input" | jq -s .
        fi
    else
        # Read from stdin
        if [[ "$quote_strings" == "true" ]]; then
            jq -R . | jq -s .
        else
            jq -s .
        fi
    fi
}

# Convert JSON array to lines
json_array_to_lines() {
    local json_input="$1"
    local input_type="${2:-string}" # string or file

    check_jq_available || return 1

    if [[ "$input_type" == "file" ]]; then
        validate_json_file "$json_input" true || return 1
        jq -r '.[]' "$json_input" 2>/dev/null || return 1
    else
        validate_json "$json_input" true || return 1
        echo "$json_input" | jq -r '.[]' 2>/dev/null || return 1
    fi
}

# Filter JSON array with jq expression
filter_json_array() {
    local json_input="$1"
    local filter_expr="$2"
    local input_type="${3:-string}" # string or file

    check_jq_available || return 1

    if [[ "$input_type" == "file" ]]; then
        validate_json_file "$json_input" true || return 1
        jq ".[] | select($filter_expr)" "$json_input"
    else
        validate_json "$json_input" true || return 1
        echo "$json_input" | jq ".[] | select($filter_expr)"
    fi
}

# Create JSON object from key-value pairs
create_json_object() {
    local -A pairs
    local json_obj="{}"

    check_jq_available || return 1

    # Parse key=value arguments
    for arg in "$@"; do
        if [[ "$arg" =~ ^([^=]+)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"

            # Determine if value should be quoted or treated as JSON
            if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [[ "$value" =~ ^(true|false|null)$ ]] || [[ "$value" =~ ^\[.*\]$ ]] || [[ "$value" =~ ^\{.*\}$ ]]; then
                # Numeric, boolean, null, or JSON object/array
                json_obj=$(echo "$json_obj" | jq --argjson val "$value" ". + {\"$key\": \$val}")
            else
                # String value
                json_obj=$(echo "$json_obj" | jq --arg val "$value" ". + {\"$key\": \$val}")
            fi
        fi
    done

    echo "$json_obj"
}

# Update JSON file with new key-value pair
update_json_file() {
    local file_path="$1"
    local key_path="$2"
    local new_value="$3"
    local backup="${4:-true}"

    check_jq_available || return 1
    validate_json_file "$file_path" true || return 1

    # Create backup if requested
    if [[ "$backup" == "true" ]]; then
        cp "$file_path" "${file_path}.backup.$(date +%Y%m%d%H%M%S)"
        echo -e "${BLUE}Created backup: ${file_path}.backup.$(date +%Y%m%d%H%M%S)${NC}"
    fi

    # Determine if value should be quoted or treated as JSON
    if [[ "$new_value" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [[ "$new_value" =~ ^(true|false|null)$ ]] || [[ "$new_value" =~ ^\[.*\]$ ]] || [[ "$new_value" =~ ^\{.*\}$ ]]; then
        # Numeric, boolean, null, or JSON object/array
        jq --argjson val "$new_value" ".$key_path = \$val" "$file_path" > "${file_path}.tmp"
    else
        # String value
        jq --arg val "$new_value" ".$key_path = \$val" "$file_path" > "${file_path}.tmp"
    fi

    mv "${file_path}.tmp" "$file_path"
    echo -e "${GREEN}Updated $file_path: .$key_path = $new_value${NC}"
}

# Compare two JSON files and show differences
json_diff() {
    local file1="$1"
    local file2="$2"
    local output_format="${3:-text}" # text, json

    check_jq_available || return 1
    validate_json_file "$file1" true || return 1
    validate_json_file "$file2" true || return 1

    local json1 json2
    json1=$(jq -S . "$file1")
    json2=$(jq -S . "$file2")

    if [[ "$json1" == "$json2" ]]; then
        echo -e "${GREEN}JSON files are identical${NC}"
        return 0
    fi

    case "$output_format" in
        "json")
            # Return structured diff
            echo "{"
            echo "  \"files_identical\": false,"
            echo "  \"file1\": \"$file1\","
            echo "  \"file2\": \"$file2\","
            echo "  \"diff_available\": \"Use text format for detailed diff\""
            echo "}"
            ;;
        *)
            echo -e "${YELLOW}JSON files differ:${NC}"
            echo -e "${BLUE}File 1: $file1${NC}"
            echo -e "${BLUE}File 2: $file2${NC}"
            echo ""
            diff <(echo "$json1") <(echo "$json2") || true
            ;;
    esac
}

# Schema validation (requires a JSON schema)
validate_json_schema() {
    local json_data="$1"
    local schema_file="$2"
    local input_type="${3:-string}" # string or file

    check_jq_available || return 1

    # Note: This is a basic schema validation using jq
    # For full JSON Schema validation, consider using ajv-cli or similar tools

    if [[ "$input_type" == "file" ]]; then
        validate_json_file "$json_data" true || return 1
        validate_json_file "$schema_file" true || return 1
        echo -e "${YELLOW}Basic validation only - consider using ajv-cli for full JSON Schema support${NC}"
        return 0
    else
        validate_json "$json_data" true || return 1
        validate_json_file "$schema_file" true || return 1
        echo -e "${YELLOW}Basic validation only - consider using ajv-cli for full JSON Schema support${NC}"
        return 0
    fi
}

# Find JSON files in directory tree
find_json_files() {
    local search_dir="${1:-.}"
    local pattern="${2:-*.json}"
    local validate_files="${3:-false}"

    local json_files
    json_files=$(find "$search_dir" -name "$pattern" -type f 2>/dev/null)

    if [[ -z "$json_files" ]]; then
        echo -e "${YELLOW}No JSON files found matching pattern: $pattern${NC}"
        return 1
    fi

    if [[ "$validate_files" == "true" ]]; then
        echo -e "${BLUE}Validating found JSON files...${NC}"
        local valid_count=0
        local invalid_count=0

        while IFS= read -r file; do
            if validate_json_file "$file" true; then
                echo -e "${GREEN}✓${NC} $file"
                ((valid_count++))
            else
                echo -e "${RED}✗${NC} $file"
                ((invalid_count++))
            fi
        done <<< "$json_files"

        echo ""
        echo -e "${BLUE}Summary:${NC} $valid_count valid, $invalid_count invalid"

        [[ "$invalid_count" -eq 0 ]]
    else
        echo "$json_files"
    fi
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "JSON utilities loaded. Available functions:"
    echo "  validate_json, validate_json_file, pretty_print_json, pretty_print_json_file"
    echo "  minify_json, minify_json_file, json_extract, json_merge"
    echo "  lines_to_json_array, json_array_to_lines, filter_json_array"
    echo "  create_json_object, update_json_file, json_diff, validate_json_schema, find_json_files"
fi
