---
skill: intenttree-cli
workflow_id: updating
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# Updating Workflow

### When to use this workflow
The agent must change a node: edit fields, transition status, complete it,
assign an owner/agent, reparent, defer, delete, or promote a capture into the
tree. All operations here are mutations — confirm with the user first.

### Prerequisites
- API server reachable at `INTENTTREE_API_URL` (default `http://localhost:8000`).
- `INTENTTREE_WORKSPACE` set (or pass `--workspace`); the target node/capture ID known.
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Pass `--json`. Precedence: flags > env > `~/.config/intenttree/config.toml`.
- Confirm status/mode enums with `itt meta enums --json` before setting `--status`/`--mode`.

### Recipe: update fields and transition status (partial PATCH)
```bash
itt node update "$NODE" --title "Write PKCE verifier (RFC 7636)" --json
itt node update "$NODE" --estimate 8 --mode hybrid --description "…" --json
itt meta enums --json | jq '.node_status'          # verify target value
itt node update "$NODE" --status in_progress --json
```
Only supplied flags change. `--mode` is `human`/`agent`/`hybrid`.

### Recipe: complete a leaf and verify rollup
```bash
itt node complete "$NODE" --json | jq '{id, status, progress}'
itt node get "$NODE" --include ancestors --json \
  | jq '[.ancestors[] | {id, title, progress}]'   # progress should cascade up
```
Completion is idempotent: a second call on an already-complete node returns exit 4.

### Recipe: assign, move, defer (mutations with dry-run where supported)
```bash
itt node assign "$NODE" --agent agent_simulated --mode agent --dry-run   # preview
itt node assign "$NODE" --agent agent_simulated --mode agent --json      # execute
itt node assign "$NODE" --owner usr_123 --mode human --json
itt node move "$NODE" --parent "$NEW_WP" --position 0 --json   # --parent required
itt node defer "$NODE" --json
```

### Recipe: promote a capture into the tree
```bash
itt capture promote "$CAP" --parent "$WP" --tree "$TREE" --dry-run   # verify first
itt capture promote "$CAP" --parent "$WP" --tree "$TREE" --json
```

### Recipe: delete (archive vs hard-delete)
```bash
itt node delete "$NODE" --force --json          # archive (reversible, default)
itt node delete "$NODE" --force --hard --json   # permanent: node + entire subtree
```
`--force` is required in a TTY (skips the prompt); optional in non-TTY scripts.
`--hard` is irreversible — prefer archive unless permanent removal is explicit.

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| 3 | Node / capture not found (or already hard-deleted) | Verify the ID with `itt node get` |
| 4 | Already in target state, illegal transition, or bad enum/parent type | Check current status; run `itt meta enums --json`; idempotent ops return 4 by design |

Retry pattern: check `$?` — `0` success, `4` is "already there / wrong state"
(diagnose, don't blind-retry), anything else is a real failure.

### See also
- `docs/CLI.md` § `node`, § `capture`
- `references/command-quick-reference.md`
- `workflows/creation-workflow.md` (parent/child hierarchy table)
