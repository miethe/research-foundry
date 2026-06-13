#!/usr/bin/env bash
# pre-compact-state.sh
#
# PreCompact hook — captures orchestrator state before context compaction.
#
# Contract (OQ-5 resolution):
#   - Reads structured JSON from stdin (session_id, transcript_path, cwd,
#     matcher ["auto"|"manual"], hook_event_name)
#   - CLAUDE_PROJECT_DIR env var (or pwd fallback) locates the project root
#   - Exit 0 always — hooks must never block compaction
#
# Output: ${CLAUDE_PROJECT_DIR}/.claude/telemetry/compaction-state.json
#   Single JSON snapshot (overwritten each invocation — "last known state").
#
# Captured state (all best-effort, individual failures are tolerated):
#   - session_id, matcher, timestamp
#   - background_agents: from `claude agents --json` or
#                        ~/.claude/daemon/roster.json fallback; null on failure
#   - pending_phases:    progress YAML files with status: in_progress|pending
#   - outstanding_gates: progress YAML files with pending tasks assigned to
#                        reviewer agents (task-completion-validator, karen,
#                        code-reviewer, senior-code-reviewer, api-librarian)
#
# IMPORTANT: Do NOT parse the transcript file inline (<100ms latency budget).
#
# Usage (smoke-test):
#   echo '{"session_id":"test","transcript_path":"/tmp/x","cwd":"/tmp",
#          "matcher":"manual","hook_event_name":"PreCompact"}' \
#     | CLAUDE_PROJECT_DIR=/path/to/project \
#       ./.claude/hooks/pre-compact-state.sh

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TELEMETRY_DIR="${PROJECT_DIR}/.claude/telemetry"
OUTPUT_FILE="${TELEMETRY_DIR}/compaction-state.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Reviewer agent names that constitute "validator gates"
REVIEWER_PATTERN="task-completion-validator\|karen\|code-reviewer\|senior-code-reviewer\|api-librarian"

# Cap on progress files scanned (latency guard)
MAX_PROGRESS_FILES=10

# ── Read stdin ───────────────────────────────────────────────────────────────

STDIN_JSON=$(cat)

parse_field() {
  local value
  value=$(echo "$STDIN_JSON" | jq -r "$1 // empty" 2>/dev/null) || true
  echo "${value:-$2}"
}

SESSION_ID=$(parse_field '.session_id' "")
MATCHER=$(parse_field '.matcher' "unknown")

# ── Ensure output directory exists ───────────────────────────────────────────

mkdir -p "$TELEMETRY_DIR"

# ── Capture background agents (best-effort) ──────────────────────────────────

capture_agents() {
  # Try claude agents --json first
  local agent_json
  agent_json=$(claude agents --json 2>/dev/null) && {
    echo "$agent_json"
    return 0
  }

  # Fall back to daemon roster file
  local roster="${HOME}/.claude/daemon/roster.json"
  if [[ -f "$roster" ]]; then
    cat "$roster" 2>/dev/null && return 0
  fi

  # Both failed — return null
  echo "null"
}

AGENTS_JSON=$(capture_agents)

# ── Scan progress files for pending phases (best-effort, capped) ─────────────

# Find progress YAML/MD files for all plans under .claude/progress/
# Pattern: .claude/progress/*/phase-*-progress.md
capture_pending_phases() {
  local pending_list=()
  local count=0

  # Use a glob-safe find, bail after MAX_PROGRESS_FILES
  while IFS= read -r -d '' progress_file; do
    [[ $count -ge $MAX_PROGRESS_FILES ]] && break
    (( count++ )) || true

    # Extract status line from YAML frontmatter (between first two --- markers)
    # Accept status: in_progress or status: pending
    local status_line
    status_line=$(awk '/^---/{if(++n==2)exit} n==1 && /^status:/{print}' \
                  "$progress_file" 2>/dev/null) || continue

    if echo "$status_line" | grep -qE 'status:[[:space:]]*(in_progress|pending)'; then
      pending_list+=("$progress_file")
    fi
  done < <(find "${PROJECT_DIR}/.claude/progress" \
               -name "phase-*-progress.md" \
               -print0 2>/dev/null | sort -z)

  # Output as JSON array
  if [[ ${#pending_list[@]} -eq 0 ]]; then
    echo "[]"
  else
    printf '%s\n' "${pending_list[@]}" | jq -R . | jq -s .
  fi
}

PENDING_PHASES=$(capture_pending_phases 2>/dev/null) || PENDING_PHASES="[]"

# ── Scan for outstanding validator gates (best-effort, capped) ───────────────

capture_outstanding_gates() {
  local gate_list=()
  local count=0

  while IFS= read -r -d '' progress_file; do
    [[ $count -ge $MAX_PROGRESS_FILES ]] && break
    (( count++ )) || true

    # Check if the file has any task with status: pending AND assigned to a reviewer
    # Approximate via grep — both conditions must appear somewhere in the file.
    if grep -q "status:.*pending" "$progress_file" 2>/dev/null && \
       grep -qE "assigned_to:.*($REVIEWER_PATTERN)" "$progress_file" 2>/dev/null; then
      gate_list+=("$progress_file")
    fi
  done < <(find "${PROJECT_DIR}/.claude/progress" \
               -name "phase-*-progress.md" \
               -print0 2>/dev/null | sort -z)

  if [[ ${#gate_list[@]} -eq 0 ]]; then
    echo "[]"
  else
    printf '%s\n' "${gate_list[@]}" | jq -R . | jq -s .
  fi
}

OUTSTANDING_GATES=$(capture_outstanding_gates 2>/dev/null) || OUTSTANDING_GATES="[]"

# ── Write snapshot ───────────────────────────────────────────────────────────

# Determine if agents_json is valid JSON or the literal "null"
AGENTS_VALUE="null"
if [[ "$AGENTS_JSON" != "null" ]] && echo "$AGENTS_JSON" | jq -e . > /dev/null 2>&1; then
  AGENTS_VALUE="$AGENTS_JSON"
fi

jq -n \
  --arg     timestamp        "$TIMESTAMP" \
  --arg     session_id       "$SESSION_ID" \
  --arg     matcher          "$MATCHER" \
  --argjson background_agents "$AGENTS_VALUE" \
  --argjson pending_phases   "$PENDING_PHASES" \
  --argjson outstanding_gates "$OUTSTANDING_GATES" \
  '{
    timestamp:          $timestamp,
    session_id:         $session_id,
    matcher:            $matcher,
    background_agents:  $background_agents,
    pending_phases:     $pending_phases,
    outstanding_gates:  $outstanding_gates
  }' > "$OUTPUT_FILE"

exit 0
