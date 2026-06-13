#!/bin/bash

# Report utilities for Claude commands
# Common reporting functions used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Global report state
declare -g REPORT_START_TIME=""
declare -g REPORT_TITLE=""
declare -g REPORT_SECTIONS=()
declare -g REPORT_WARNINGS=()
declare -g REPORT_ERRORS=()
declare -g REPORT_SUCCESSES=()

# Initialize a new report
init_report() {
    local title="$1"
    local timestamp="${2:-$(date '+%Y-%m-%d %H:%M:%S')}"

    REPORT_START_TIME=$(date +%s)
    REPORT_TITLE="$title"
    REPORT_SECTIONS=()
    REPORT_WARNINGS=()
    REPORT_ERRORS=()
    REPORT_SUCCESSES=()

    echo -e "${CYAN}=====================================${NC}"
    echo -e "${CYAN}  $title${NC}"
    echo -e "${CYAN}  Started: $timestamp${NC}"
    echo -e "${CYAN}=====================================${NC}"
    echo ""
}

# Add a section to the report
add_report_section() {
    local section_title="$1"
    local section_content="$2"
    local section_type="${3:-info}" # info, success, warning, error

    REPORT_SECTIONS+=("$section_type:$section_title:$section_content")

    local color="$BLUE"
    local prefix="ℹ"

    case "$section_type" in
        "success") color="$GREEN"; prefix="✓" ;;
        "warning") color="$YELLOW"; prefix="⚠" ;;
        "error") color="$RED"; prefix="✗" ;;
        *) color="$BLUE"; prefix="ℹ" ;;
    esac

    echo -e "${color}${prefix} $section_title${NC}"
    if [[ -n "$section_content" ]]; then
        echo "$section_content" | sed 's/^/  /'
    fi
    echo ""
}

# Add success message
add_success() {
    local message="$1"
    REPORT_SUCCESSES+=("$message")
    echo -e "${GREEN}✓ $message${NC}"
}

# Add warning message
add_warning() {
    local message="$1"
    REPORT_WARNINGS+=("$message")
    echo -e "${YELLOW}⚠ $message${NC}"
}

# Add error message
add_error() {
    local message="$1"
    REPORT_ERRORS+=("$message")
    echo -e "${RED}✗ $message${NC}"
}

# Generate summary statistics
generate_summary_stats() {
    local total_sections=${#REPORT_SECTIONS[@]}
    local total_successes=${#REPORT_SUCCESSES[@]}
    local total_warnings=${#REPORT_WARNINGS[@]}
    local total_errors=${#REPORT_ERRORS[@]}

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - REPORT_START_TIME))

    echo ""
    echo -e "${CYAN}=====================================${NC}"
    echo -e "${CYAN}  SUMMARY${NC}"
    echo -e "${CYAN}=====================================${NC}"
    echo -e "Duration: ${BLUE}${duration}s${NC}"
    echo -e "Sections: ${BLUE}$total_sections${NC}"
    echo -e "Successes: ${GREEN}$total_successes${NC}"
    echo -e "Warnings: ${YELLOW}$total_warnings${NC}"
    echo -e "Errors: ${RED}$total_errors${NC}"

    # Overall status
    if [[ $total_errors -gt 0 ]]; then
        echo -e "Status: ${RED}FAILED${NC}"
        return 1
    elif [[ $total_warnings -gt 0 ]]; then
        echo -e "Status: ${YELLOW}COMPLETED WITH WARNINGS${NC}"
        return 2
    else
        echo -e "Status: ${GREEN}SUCCESS${NC}"
        return 0
    fi
}

# Generate detailed report in various formats
generate_report() {
    local output_format="${1:-text}" # text, json, markdown, html
    local output_file="${2:-}"

    local report_content

    case "$output_format" in
        "json")
            report_content=$(generate_json_report)
            ;;
        "markdown")
            report_content=$(generate_markdown_report)
            ;;
        "html")
            report_content=$(generate_html_report)
            ;;
        *)
            report_content=$(generate_text_report)
            ;;
    esac

    if [[ -n "$output_file" ]]; then
        echo "$report_content" > "$output_file"
        echo -e "${GREEN}Report saved to: $output_file${NC}"
    else
        echo "$report_content"
    fi
}

# Generate JSON report
generate_json_report() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - REPORT_START_TIME))

    local sections_json="[]"
    for section in "${REPORT_SECTIONS[@]}"; do
        IFS=':' read -r type title content <<< "$section"
        local section_obj
        section_obj=$(jq -n \
            --arg type "$type" \
            --arg title "$title" \
            --arg content "$content" \
            '{type: $type, title: $title, content: $content}')
        sections_json=$(echo "$sections_json" | jq ". += [$section_obj]")
    done

    local successes_json
    successes_json=$(printf '%s\n' "${REPORT_SUCCESSES[@]}" | jq -R . | jq -s .)

    local warnings_json
    warnings_json=$(printf '%s\n' "${REPORT_WARNINGS[@]}" | jq -R . | jq -s .)

    local errors_json
    errors_json=$(printf '%s\n' "${REPORT_ERRORS[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg title "$REPORT_TITLE" \
        --arg start_time "$REPORT_START_TIME" \
        --arg end_time "$end_time" \
        --arg duration "${duration}s" \
        --argjson sections "$sections_json" \
        --argjson successes "$successes_json" \
        --argjson warnings "$warnings_json" \
        --argjson errors "$errors_json" \
        '{
            title: $title,
            start_time: $start_time,
            end_time: $end_time,
            duration: $duration,
            sections: $sections,
            summary: {
                total_sections: ($sections | length),
                total_successes: ($successes | length),
                total_warnings: ($warnings | length),
                total_errors: ($errors | length),
                status: (if ($errors | length) > 0 then "FAILED" elif ($warnings | length) > 0 then "COMPLETED WITH WARNINGS" else "SUCCESS" end)
            },
            details: {
                successes: $successes,
                warnings: $warnings,
                errors: $errors
            }
        }'
}

# Generate Markdown report
generate_markdown_report() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - REPORT_START_TIME))

    cat <<EOF
# $REPORT_TITLE

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Duration:** ${duration}s

## Summary

| Metric | Count |
|--------|-------|
| Sections | ${#REPORT_SECTIONS[@]} |
| Successes | ${#REPORT_SUCCESSES[@]} |
| Warnings | ${#REPORT_WARNINGS[@]} |
| Errors | ${#REPORT_ERRORS[@]} |

EOF

    # Overall status
    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo "**Status:** ❌ FAILED"
    elif [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo "**Status:** ⚠️ COMPLETED WITH WARNINGS"
    else
        echo "**Status:** ✅ SUCCESS"
    fi

    echo ""
    echo "## Sections"
    echo ""

    for section in "${REPORT_SECTIONS[@]}"; do
        IFS=':' read -r type title content <<< "$section"
        local emoji
        case "$type" in
            "success") emoji="✅" ;;
            "warning") emoji="⚠️" ;;
            "error") emoji="❌" ;;
            *) emoji="ℹ️" ;;
        esac

        echo "### $emoji $title"
        echo ""
        if [[ -n "$content" ]]; then
            echo "$content"
            echo ""
        fi
    done

    # Add details if there are successes, warnings, or errors
    if [[ ${#REPORT_SUCCESSES[@]} -gt 0 ]]; then
        echo "## ✅ Successes"
        echo ""
        for success in "${REPORT_SUCCESSES[@]}"; do
            echo "- $success"
        done
        echo ""
    fi

    if [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo "## ⚠️ Warnings"
        echo ""
        for warning in "${REPORT_WARNINGS[@]}"; do
            echo "- $warning"
        done
        echo ""
    fi

    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo "## ❌ Errors"
        echo ""
        for error in "${REPORT_ERRORS[@]}"; do
            echo "- $error"
        done
        echo ""
    fi
}

# Generate HTML report
generate_html_report() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - REPORT_START_TIME))

    cat <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$REPORT_TITLE</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .meta { background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .summary table { width: 100%; border-collapse: collapse; }
        .summary th, .summary td { padding: 10px; text-align: left; border-bottom: 1px solid #bdc3c7; }
        .summary th { background: #3498db; color: white; }
        .status-success { color: #27ae60; font-weight: bold; }
        .status-warning { color: #f39c12; font-weight: bold; }
        .status-error { color: #e74c3c; font-weight: bold; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }
        .section.success { border-left-color: #27ae60; }
        .section.warning { border-left-color: #f39c12; }
        .section.error { border-left-color: #e74c3c; }
        .section h3 { margin-top: 0; }
        .list-item { padding: 5px 0; border-bottom: 1px solid #ecf0f1; }
        .list-item:last-child { border-bottom: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>$REPORT_TITLE</h1>

        <div class="meta">
            <strong>Generated:</strong> $(date '+%Y-%m-%d %H:%M:%S')<br>
            <strong>Duration:</strong> ${duration}s
        </div>

        <h2>Summary</h2>
        <div class="summary">
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Sections</td><td>${#REPORT_SECTIONS[@]}</td></tr>
                <tr><td>Successes</td><td>${#REPORT_SUCCESSES[@]}</td></tr>
                <tr><td>Warnings</td><td>${#REPORT_WARNINGS[@]}</td></tr>
                <tr><td>Errors</td><td>${#REPORT_ERRORS[@]}</td></tr>
                <tr><td>Status</td><td>
EOF

    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo '<span class="status-error">❌ FAILED</span>'
    elif [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo '<span class="status-warning">⚠️ COMPLETED WITH WARNINGS</span>'
    else
        echo '<span class="status-success">✅ SUCCESS</span>'
    fi

    echo "</td></tr>"
    echo "</table>"
    echo "</div>"

    echo "<h2>Sections</h2>"

    for section in "${REPORT_SECTIONS[@]}"; do
        IFS=':' read -r type title content <<< "$section"
        local emoji class
        case "$type" in
            "success") emoji="✅"; class="success" ;;
            "warning") emoji="⚠️"; class="warning" ;;
            "error") emoji="❌"; class="error" ;;
            *) emoji="ℹ️"; class="info" ;;
        esac

        echo "<div class=\"section $class\">"
        echo "<h3>$emoji $title</h3>"
        if [[ -n "$content" ]]; then
            echo "<pre>$content</pre>"
        fi
        echo "</div>"
    done

    # Add details sections
    if [[ ${#REPORT_SUCCESSES[@]} -gt 0 ]]; then
        echo "<h2>✅ Successes</h2>"
        echo "<div>"
        for success in "${REPORT_SUCCESSES[@]}"; do
            echo "<div class=\"list-item\">$success</div>"
        done
        echo "</div>"
    fi

    if [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo "<h2>⚠️ Warnings</h2>"
        echo "<div>"
        for warning in "${REPORT_WARNINGS[@]}"; do
            echo "<div class=\"list-item\">$warning</div>"
        done
        echo "</div>"
    fi

    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo "<h2>❌ Errors</h2>"
        echo "<div>"
        for error in "${REPORT_ERRORS[@]}"; do
            echo "<div class=\"list-item\">$error</div>"
        done
        echo "</div>"
    fi

    echo "</div>"
    echo "</body>"
    echo "</html>"
}

# Generate text report
generate_text_report() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - REPORT_START_TIME))

    echo "======================================"
    echo "  $REPORT_TITLE"
    echo "======================================"
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Duration: ${duration}s"
    echo ""

    echo "SUMMARY"
    echo "======="
    echo "Sections: ${#REPORT_SECTIONS[@]}"
    echo "Successes: ${#REPORT_SUCCESSES[@]}"
    echo "Warnings: ${#REPORT_WARNINGS[@]}"
    echo "Errors: ${#REPORT_ERRORS[@]}"

    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo "Status: FAILED"
    elif [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo "Status: COMPLETED WITH WARNINGS"
    else
        echo "Status: SUCCESS"
    fi

    echo ""
    echo "SECTIONS"
    echo "========"

    for section in "${REPORT_SECTIONS[@]}"; do
        IFS=':' read -r type title content <<< "$section"
        local prefix
        case "$type" in
            "success") prefix="[SUCCESS]" ;;
            "warning") prefix="[WARNING]" ;;
            "error") prefix="[ERROR]" ;;
            *) prefix="[INFO]" ;;
        esac

        echo ""
        echo "$prefix $title"
        echo "$(printf '%*s' ${#prefix} '' | tr ' ' '-')$(printf '%*s' ${#title} '' | tr ' ' '-')"
        if [[ -n "$content" ]]; then
            echo "$content"
        fi
    done

    # Add details sections
    if [[ ${#REPORT_SUCCESSES[@]} -gt 0 ]]; then
        echo ""
        echo "SUCCESSES"
        echo "========="
        for success in "${REPORT_SUCCESSES[@]}"; do
            echo "✓ $success"
        done
    fi

    if [[ ${#REPORT_WARNINGS[@]} -gt 0 ]]; then
        echo ""
        echo "WARNINGS"
        echo "========"
        for warning in "${REPORT_WARNINGS[@]}"; do
            echo "⚠ $warning"
        done
    fi

    if [[ ${#REPORT_ERRORS[@]} -gt 0 ]]; then
        echo ""
        echo "ERRORS"
        echo "======"
        for error in "${REPORT_ERRORS[@]}"; do
            echo "✗ $error"
        done
    fi
}

# Progress bar utility
show_progress() {
    local current="$1"
    local total="$2"
    local task_name="${3:-Processing}"
    local width=50

    local percentage=$((current * 100 / total))
    local completed=$((current * width / total))
    local remaining=$((width - completed))

    printf "\r${BLUE}$task_name:${NC} ["
    printf "%${completed}s" | tr ' ' '█'
    printf "%${remaining}s" | tr ' ' '░'
    printf "] %d%% (%d/%d)" "$percentage" "$current" "$total"

    if [[ $current -eq $total ]]; then
        printf "\n"
    fi
}

# Create a simple table
create_table() {
    local headers=("$@")
    local rows=()

    # This is a placeholder - would need more complex implementation
    # for reading data rows. For now, just print headers
    echo "| $(IFS=' | '; echo "${headers[*]}") |"
    printf "|"
    for header in "${headers[@]}"; do
        printf " %*s |" ${#header} "$(printf '%*s' ${#header} '' | tr ' ' '-')"
    done
    printf "\n"
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "Report utilities loaded. Available functions:"
    echo "  init_report, add_report_section, add_success, add_warning, add_error"
    echo "  generate_summary_stats, generate_report, show_progress, create_table"
fi
