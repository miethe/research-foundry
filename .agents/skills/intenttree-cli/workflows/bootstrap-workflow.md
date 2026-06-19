---
skill: intenttree-cli
workflow_id: bootstrap
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# Bootstrap Workflow

### When to use this workflow
The agent must wire IntentTree tracking into a host project: configure the API
connection, select a workspace, find-or-create a tree, inject a CLAUDE.md
snippet, and verify. Idempotent — detect existing state first. Config/tree
writes are mutations — confirm before executing.

### Prerequisites
- API server already running (never start it during a build). If `meta version` fails, instruct the user to start the stack and stop.
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Precedence: flags > env > `~/.config/intenttree/config.toml` (mode 0600).
- `templates/claude-md-snippet.md` available for the CLAUDE.md block.

### Recipe: preflight (read-only state detection)
```bash
itt meta version --json        # API reachable? else stop and tell the user
itt config list                # current merged config
itt config whoami              # identity + active workspace
itt workspace list --json      # available workspaces
itt tree list --workspace "$WS" --json 2>/dev/null || true
```

### Recipe: configure connection and workspace
```bash
itt config set api_url "http://localhost:8000"
itt config set api_token "$INTENTTREE_API_TOKEN"   # only if auth is enabled
itt workspace use "$WS"                            # persists to config file
itt config whoami                                  # verify
```
For CI, prefer env vars: `INTENTTREE_API_URL`, `INTENTTREE_API_TOKEN`,
`INTENTTREE_WORKSPACE`. Workspaces are created in the web UI, not the CLI.

### Recipe: find or create the work tree
```bash
itt tree list --workspace "$WS" --json | jq '.items[] | {id, title}'   # match by title
# Only if no match exists:
TREE=$(itt tree create --title "<Host Project>" --workspace "$WS" \
  --description "Track work for <Host Project>" --json | jq -r '.id')
# Optionally seed confirmed pillars (do not invent):
itt node create --title "<Pillar>" --type pillar --tree "$TREE" --mode human --json
```
`tree create` uses `--title`/`--description` (there is no `--name`/`--intent`).

### Recipe: inject CLAUDE.md snippet and verify
1. Fill `{{WORKSPACE_ID}}`, `{{TREE_ID}}`, `{{API_URL}}` in `templates/claude-md-snippet.md`.
2. `grep -n 'intenttree-cli:begin' "$HOST/CLAUDE.md"` — if absent, append the block (show a preview/diff and confirm); if present and differing, show a unified diff and replace only between markers on confirm.
3. Verify end-to-end:
```bash
itt tree get "$TREE" --json | jq '.id'
SCRATCH=$(itt node create --title "[scratch] delete me" --type atomic_task \
  --tree "$TREE" --json | jq -r '.id')
itt node delete "$SCRATCH" --force
itt today show --workspace "$WS" --json | jq '{scheduled: (.schedule|length)}'
```

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| — | `meta version` unreachable | API down — instruct user to start the stack; stop |
| 3 | Workspace / tree not found | Recheck IDs; `workspace list` / `tree list` |
| 4 | Tree title already exists, or scratch node wrong state | Reuse the existing tree ID; ignore scratch-delete conflicts |

### See also
- `docs/CLI.md` § `config`, § `workspace`, § `tree`, § `meta`
- `templates/claude-md-snippet.md`
- `references/command-quick-reference.md`
