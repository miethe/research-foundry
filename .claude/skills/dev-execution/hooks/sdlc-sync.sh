#!/usr/bin/env bash
# =============================================================================
# sdlc-sync.sh — Dev-Execution IntentTree SDLC Status Sync Hook
# =============================================================================
#
# PURPOSE:
#   Non-blocking hook that re-runs `itt sync import <progress-or-plan-file>
#   --apply --tree <tree>` at status hook points (task start, task done,
#   phase done, inter-wave merge) to propagate current status to bound
#   IntentTree nodes.
#
# TRIGGER REGISTRATION:
#   Called from phase-execution.md at §2.3a (task start), §2.5a (task done),
#   §5.2a (phase done) and from plan-execution.md at §3c-sync (inter-wave).
#
#   Suggested snippet (inline):
#     SDLC_SYNC_FILE=".claude/progress/${PRD}/phase-${PHASE_NUM}-progress.md" \
#     INTENTTREE_TREE="<tree-id>" \
#     .claude/skills/dev-execution/hooks/sdlc-sync.sh
#
# ENVIRONMENT:
#   INTENTTREE_SDLC_SYNC  — must be exactly "1" to enable; any other value
#                           (including unset) is a no-op.
#   SDLC_SYNC_FILE        — path to the progress or plan file to sync.
#                           Required when INTENTTREE_SDLC_SYNC=1.
#   INTENTTREE_TREE       — target tree ID (passed to --tree).
#                           Optional: omit to let the CLI infer from the
#                           artifact's `intenttree_tree` frontmatter field.
#
# ERROR HANDLING:
#   All errors are logged to stderr with a [sdlc-sync] prefix.
#   This hook always exits 0 — failures never propagate to the calling workflow.
#
# SPEC REFERENCE:
#   docs/project_plans/implementation_plans/features/awpr-v2-task-node-contract.md
#   (§writeback policy, §idempotency invariants)
#   Plan task: TASK-6.2 (FR-11, dev-execution skill wiring)
#   CLI source: client/src/intenttree_client/cli/commands/sync_cmd.py
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Guard: master switch
# ---------------------------------------------------------------------------
if [ "${INTENTTREE_SDLC_SYNC:-0}" != "1" ]; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Validate required inputs
# ---------------------------------------------------------------------------
SDLC_SYNC_FILE="${SDLC_SYNC_FILE:-}"
INTENTTREE_TREE="${INTENTTREE_TREE:-}"

if [ -z "${SDLC_SYNC_FILE}" ]; then
    echo "[sdlc-sync] SDLC_SYNC_FILE not set — skipping (non-fatal)" >&2
    exit 0
fi

if [ ! -f "${SDLC_SYNC_FILE}" ]; then
    echo "[sdlc-sync] file not found: ${SDLC_SYNC_FILE} — skipping (non-fatal)" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# Build the itt sync command
# ---------------------------------------------------------------------------
ITT_ARGS=("sync" "import" "${SDLC_SYNC_FILE}" "--apply")
if [ -n "${INTENTTREE_TREE}" ]; then
    ITT_ARGS+=("--tree" "${INTENTTREE_TREE}")
fi

# ---------------------------------------------------------------------------
# Run itt sync — capture output; treat all errors as warnings
# ---------------------------------------------------------------------------
(
    if command -v itt >/dev/null 2>&1; then
        itt "${ITT_ARGS[@]}" 2>&1 | head -10
    else
        echo "[sdlc-sync] itt CLI not found — skipping (non-fatal)" >&2
        exit 1
    fi
) || {
    echo "[sdlc-sync] itt sync failed for ${SDLC_SYNC_FILE} — non-fatal, continuing" >&2
}

# Always exit 0 — hook must never block the calling workflow
exit 0
