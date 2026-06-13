#!/bin/bash

# File utilities for Claude commands
# Common file operations used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Find files with pattern and optional filters
find_files() {
    local search_dir="${1:-.}"
    local pattern="${2:-*}"
    local file_type="${3:-f}" # f for files, d for directories, l for links
    local max_depth="${4:-}"
    local exclude_patterns="${5:-}"

    local find_cmd="find \"$search_dir\" -type $file_type"

    # Add max depth if specified
    if [[ -n "$max_depth" ]]; then
        find_cmd="$find_cmd -maxdepth $max_depth"
    fi

    # Add name pattern
    find_cmd="$find_cmd -name \"$pattern\""

    # Add exclusions if specified (comma-separated)
    if [[ -n "$exclude_patterns" ]]; then
        IFS=',' read -ra EXCLUDES <<< "$exclude_patterns"
        for exclude in "${EXCLUDES[@]}"; do
            exclude=$(echo "$exclude" | xargs) # trim whitespace
            find_cmd="$find_cmd ! -path \"*/$exclude/*\" ! -name \"$exclude\""
        done
    fi

    eval "$find_cmd" 2>/dev/null | sort
}

# Find files by extension
find_by_extension() {
    local search_dir="${1:-.}"
    local extension="$2"
    local exclude_patterns="${3:-node_modules,.git,dist,build,.next}"

    # Add leading dot if not present
    [[ "$extension" != .* ]] && extension=".$extension"

    find_files "$search_dir" "*$extension" "f" "" "$exclude_patterns"
}

# Find files modified within time period
find_recent_files() {
    local search_dir="${1:-.}"
    local time_spec="${2:-1}" # hours, days, etc.
    local time_unit="${3:-days}" # minutes, hours, days
    local pattern="${4:-*}"

    local find_time
    case "$time_unit" in
        "minutes"|"min") find_time="-${time_spec}" ;;
        "hours"|"hr") find_time="-$((time_spec * 60))" ;;
        "days") find_time="-${time_spec}" ;;
        *) echo -e "${RED}Invalid time unit: $time_unit${NC}" >&2; return 1 ;;
    esac

    if [[ "$time_unit" == "minutes" || "$time_unit" == "min" || "$time_unit" == "hours" || "$time_unit" == "hr" ]]; then
        find "$search_dir" -type f -name "$pattern" -mmin "$find_time" 2>/dev/null | sort
    else
        find "$search_dir" -type f -name "$pattern" -mtime "$find_time" 2>/dev/null | sort
    fi
}

# Get file information (size, permissions, modified date)
get_file_info() {
    local file_path="$1"
    local output_format="${2:-text}" # text, json, csv

    if [[ ! -e "$file_path" ]]; then
        echo -e "${RED}File not found: $file_path${NC}" >&2
        return 1
    fi

    local file_size permissions modified_date file_type owner group

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        file_size=$(stat -f%z "$file_path")
        permissions=$(stat -f%Mp%Lp "$file_path")
        modified_date=$(stat -f%Sm "$file_path")
        file_type=$(stat -f%HT "$file_path")
        owner=$(stat -f%Su "$file_path")
        group=$(stat -f%Sg "$file_path")
    else
        # Linux
        file_size=$(stat -c%s "$file_path")
        permissions=$(stat -c%A "$file_path")
        modified_date=$(stat -c%y "$file_path")
        file_type=$(stat -c%F "$file_path")
        owner=$(stat -c%U "$file_path")
        group=$(stat -c%G "$file_path")
    fi

    case "$output_format" in
        "json")
            cat <<EOF
{
    "path": "$file_path",
    "size": $file_size,
    "size_human": "$(format_bytes "$file_size")",
    "permissions": "$permissions",
    "modified_date": "$modified_date",
    "type": "$file_type",
    "owner": "$owner",
    "group": "$group"
}
EOF
            ;;
        "csv")
            echo "path,size,permissions,modified_date,type,owner,group"
            echo "$file_path,$file_size,$permissions,$modified_date,$file_type,$owner,$group"
            ;;
        *)
            echo -e "${BLUE}File Information${NC}"
            echo "=================="
            echo -e "Path: ${GREEN}$file_path${NC}"
            echo -e "Size: ${GREEN}$(format_bytes "$file_size")${NC} ($file_size bytes)"
            echo -e "Permissions: ${GREEN}$permissions${NC}"
            echo -e "Modified: ${GREEN}$modified_date${NC}"
            echo -e "Type: ${GREEN}$file_type${NC}"
            echo -e "Owner: ${GREEN}$owner:$group${NC}"
            ;;
    esac
}

# Format bytes in human-readable format
format_bytes() {
    local bytes=$1
    local sizes=("B" "KB" "MB" "GB" "TB")
    local i=0

    while [[ $bytes -ge 1024 && $i -lt $((${#sizes[@]} - 1)) ]]; do
        bytes=$((bytes / 1024))
        ((i++))
    done

    printf "%.1f%s" "$bytes" "${sizes[$i]}"
}

# Calculate directory size
get_directory_size() {
    local dir_path="${1:-.}"
    local output_format="${2:-text}" # text, json
    local include_hidden="${3:-false}"

    if [[ ! -d "$dir_path" ]]; then
        echo -e "${RED}Directory not found: $dir_path${NC}" >&2
        return 1
    fi

    local du_cmd="du -s"
    [[ "$include_hidden" == "true" ]] && du_cmd="$du_cmd -a"

    local size_kb
    size_kb=$(eval "$du_cmd \"$dir_path\"" | cut -f1)
    local size_bytes=$((size_kb * 1024))

    case "$output_format" in
        "json")
            cat <<EOF
{
    "path": "$dir_path",
    "size_bytes": $size_bytes,
    "size_kb": $size_kb,
    "size_human": "$(format_bytes "$size_bytes")"
}
EOF
            ;;
        *)
            echo -e "${BLUE}Directory Size${NC}"
            echo "=============="
            echo -e "Path: ${GREEN}$dir_path${NC}"
            echo -e "Size: ${GREEN}$(format_bytes "$size_bytes")${NC}"
            ;;
    esac
}

# List files with size information
list_files_with_size() {
    local search_dir="${1:-.}"
    local pattern="${2:-*}"
    local sort_by="${3:-name}" # name, size, date
    local reverse="${4:-false}"
    local max_results="${5:-50}"

    local sort_opt
    case "$sort_by" in
        "size") sort_opt="-S" ;;
        "date"|"time") sort_opt="-t" ;;
        *) sort_opt="" ;;
    esac

    local reverse_opt
    [[ "$reverse" == "true" ]] && reverse_opt="-r" || reverse_opt=""

    find "$search_dir" -name "$pattern" -type f 2>/dev/null | \
    head -n "$max_results" | \
    xargs ls -lah $sort_opt $reverse_opt 2>/dev/null | \
    grep -v "^total"
}

# Check file permissions
check_permissions() {
    local file_path="$1"
    local required_perms="${2:-r}" # r, w, x, rw, rx, wx, rwx

    if [[ ! -e "$file_path" ]]; then
        echo -e "${RED}File not found: $file_path${NC}" >&2
        return 1
    fi

    local has_read has_write has_execute
    [[ -r "$file_path" ]] && has_read=true || has_read=false
    [[ -w "$file_path" ]] && has_write=true || has_write=false
    [[ -x "$file_path" ]] && has_execute=true || has_execute=false

    local check_read=false check_write=false check_execute=false
    [[ "$required_perms" =~ r ]] && check_read=true
    [[ "$required_perms" =~ w ]] && check_write=true
    [[ "$required_perms" =~ x ]] && check_execute=true

    local permissions_ok=true

    if [[ "$check_read" == "true" && "$has_read" == "false" ]]; then
        permissions_ok=false
    fi

    if [[ "$check_write" == "true" && "$has_write" == "false" ]]; then
        permissions_ok=false
    fi

    if [[ "$check_execute" == "true" && "$has_execute" == "false" ]]; then
        permissions_ok=false
    fi

    if [[ "$permissions_ok" == "true" ]]; then
        echo -e "${GREEN}✓ File has required permissions ($required_perms): $file_path${NC}"
        return 0
    else
        echo -e "${RED}✗ File missing required permissions ($required_perms): $file_path${NC}"
        return 1
    fi
}

# Create directory structure
create_directory_tree() {
    local base_dir="$1"
    shift
    local directories=("$@")

    echo -e "${BLUE}Creating directory structure in: $base_dir${NC}"

    for dir in "${directories[@]}"; do
        local full_path="$base_dir/$dir"
        if mkdir -p "$full_path"; then
            echo -e "${GREEN}✓${NC} Created: $full_path"
        else
            echo -e "${RED}✗${NC} Failed to create: $full_path"
            return 1
        fi
    done
}

# Backup file or directory
backup_path() {
    local source_path="$1"
    local backup_dir="${2:-./backups}"
    local timestamp="${3:-$(date +%Y%m%d-%H%M%S)}"

    if [[ ! -e "$source_path" ]]; then
        echo -e "${RED}Source path not found: $source_path${NC}" >&2
        return 1
    fi

    # Create backup directory if it doesn't exist
    mkdir -p "$backup_dir"

    local basename
    basename=$(basename "$source_path")
    local backup_path="$backup_dir/${basename}-${timestamp}"

    if cp -r "$source_path" "$backup_path" 2>/dev/null; then
        echo -e "${GREEN}✓ Backup created: $backup_path${NC}"
        echo "$backup_path"
        return 0
    else
        echo -e "${RED}✗ Failed to create backup of: $source_path${NC}" >&2
        return 1
    fi
}

# Restore from backup
restore_backup() {
    local backup_path="$1"
    local restore_location="$2"
    local confirm="${3:-true}"

    if [[ ! -e "$backup_path" ]]; then
        echo -e "${RED}Backup not found: $backup_path${NC}" >&2
        return 1
    fi

    if [[ "$confirm" == "true" ]]; then
        echo -e "${YELLOW}This will overwrite: $restore_location${NC}"
        echo -e "Continue? (y/N): ${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Restore cancelled${NC}"
            return 1
        fi
    fi

    if cp -r "$backup_path" "$restore_location" 2>/dev/null; then
        echo -e "${GREEN}✓ Restored from backup: $backup_path -> $restore_location${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to restore from backup: $backup_path${NC}" >&2
        return 1
    fi
}

# Clean up old backups
cleanup_backups() {
    local backup_dir="${1:-./backups}"
    local keep_days="${2:-7}"
    local pattern="${3:-*}"
    local dry_run="${4:-false}"

    if [[ ! -d "$backup_dir" ]]; then
        echo -e "${YELLOW}Backup directory not found: $backup_dir${NC}"
        return 0
    fi

    echo -e "${BLUE}Cleaning up backups older than $keep_days days in: $backup_dir${NC}"

    local old_backups
    old_backups=$(find "$backup_dir" -name "$pattern" -type f -mtime "+$keep_days" 2>/dev/null)

    if [[ -z "$old_backups" ]]; then
        echo -e "${GREEN}No old backups found to clean up${NC}"
        return 0
    fi

    local count=0
    while IFS= read -r backup_file; do
        if [[ "$dry_run" == "true" ]]; then
            echo -e "${YELLOW}[DRY RUN] Would delete: $backup_file${NC}"
        else
            if rm "$backup_file" 2>/dev/null; then
                echo -e "${GREEN}✓ Deleted: $backup_file${NC}"
            else
                echo -e "${RED}✗ Failed to delete: $backup_file${NC}"
            fi
        fi
        ((count++))
    done <<< "$old_backups"

    echo -e "${BLUE}Found $count old backup(s)${NC}"
}

# Get file count and statistics for a directory
get_directory_stats() {
    local dir_path="${1:-.}"
    local output_format="${2:-text}" # text, json
    local include_hidden="${3:-false}"

    if [[ ! -d "$dir_path" ]]; then
        echo -e "${RED}Directory not found: $dir_path${NC}" >&2
        return 1
    fi

    local find_opts=""
    [[ "$include_hidden" == "false" ]] && find_opts="! -path '*/.*'"

    local total_files total_dirs total_size
    total_files=$(eval "find \"$dir_path\" -type f $find_opts" 2>/dev/null | wc -l | xargs)
    total_dirs=$(eval "find \"$dir_path\" -type d $find_opts" 2>/dev/null | wc -l | xargs)

    # Calculate total size
    local size_kb
    size_kb=$(eval "find \"$dir_path\" -type f $find_opts -exec du -k {} +" 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
    total_size=$((size_kb * 1024))

    case "$output_format" in
        "json")
            cat <<EOF
{
    "path": "$dir_path",
    "total_files": $total_files,
    "total_directories": $total_dirs,
    "total_size_bytes": $total_size,
    "total_size_human": "$(format_bytes "$total_size")",
    "include_hidden": $include_hidden
}
EOF
            ;;
        *)
            echo -e "${BLUE}Directory Statistics${NC}"
            echo "===================="
            echo -e "Path: ${GREEN}$dir_path${NC}"
            echo -e "Files: ${GREEN}$total_files${NC}"
            echo -e "Directories: ${GREEN}$total_dirs${NC}"
            echo -e "Total Size: ${GREEN}$(format_bytes "$total_size")${NC}"
            echo -e "Include Hidden: ${GREEN}$include_hidden${NC}"
            ;;
    esac
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "File utilities loaded. Available functions:"
    echo "  find_files, find_by_extension, find_recent_files, get_file_info"
    echo "  format_bytes, get_directory_size, list_files_with_size, check_permissions"
    echo "  create_directory_tree, backup_path, restore_backup, cleanup_backups, get_directory_stats"
fi
