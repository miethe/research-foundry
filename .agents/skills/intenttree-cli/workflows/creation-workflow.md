---
skill: intenttree-cli
workflow_id: creation
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# Creation Workflow

### When to use this workflow
The agent must capture an off-tree inbox item, create one or more tree nodes
under a parent, build a new tree, or decompose an existing node into child
stubs. Everything here is a mutation — confirm with the user before executing.

### Prerequisites
- API server reachable at `INTENTTREE_API_URL` (default `http://localhost:8000`).
- `INTENTTREE_WORKSPACE` set (or pass `--workspace`); a target `--tree`/`--parent` for tree nodes.
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Pass `--json`. Precedence: flags > env > `~/.config/intenttree/config.toml`.
- Hierarchy: `pillar → work_area → work_package → atomic_task → step`; off-tree: `side_quest`, `quick_win`. Confirm enums with `itt meta enums --json` before setting `--type`/`--status`.

### Recipe: capture an inbox item
```bash
itt capture add "Investigate Redis eviction bug" --type side_quest \
  --workspace "$WS" --note "Seen in prod logs" --json
itt capture list --workspace "$WS" --json | jq '.items[] | {id, title, type}'
```
`--type` is `side_quest` (default) or `quick_win`; `--workspace` is required for off-tree listing.

### Recipe: create a tree, then nodes under a parent
```bash
itt meta enums --json | jq '{node_type, node_status}'   # confirm valid values first

TREE=$(itt tree create --title "Q3 Engineering" --workspace "$WS" \
  --description "Ship billing overhaul" --json | jq -r '.id')
PILLAR=$(itt node create --title "Auth & Security" --type pillar \
  --tree "$TREE" --json | jq -r '.id')
WP=$(itt node create --title "Implement PKCE" --type work_package \
  --tree "$TREE" --parent "$PILLAR" --estimate 5 --mode agent --json | jq -r '.id')
itt node create --title "Write code-verifier generator" --type atomic_task \
  --tree "$TREE" --parent "$WP" --json | jq -r '.id'
```
`tree create` flags: `--title` (required), `--workspace`, `--slug`, `--description`. `node create`: `--title` + `--type` required; `--parent` required for every non-pillar node; `--estimate` (points) and `--mode` (`human`/`agent`/`hybrid`) optional.

### Recipe: decompose a node into child stubs
```bash
itt node decompose "$WP" --strategy template --count 4 --dry-run   # preview payload
itt node decompose "$WP" --strategy template --count 4 --json      # execute
```
> **Current behavior**: `--strategy template` creates N stub children titled `"<parent title> — part N"` with no description or acceptance criteria (structural scaffold only). `--strategy agent` queues an agent run but, with the default `simulated` harness, creates zero children — a human must paste `task_updates` JSON via the copy/paste dispatch flow. Prose-to-tree distillation does not exist today; see plan `intenttree-prose-distillation-v1` for the roadmap.

### Recipe: worked end-to-end (prose request → tracked node → progress)
User says: *"Log a quick task to update the README install steps and start it."*
```bash
# 1. Capture the prose as an off-tree quick win
CAP=$(itt capture add "Update README install steps" --type quick_win \
  --workspace "$WS" --json | jq -r '.id')
# 2. Promote it under a work package (dry-run to verify parent type, then execute)
itt capture promote "$CAP" --parent "$WP" --tree "$TREE" --dry-run
itt capture promote "$CAP" --parent "$WP" --tree "$TREE" --json
# 3. Mark progress: move to in_progress, then complete when done
itt node update "$CAP" --status in_progress --json
itt node complete "$CAP" --json
```
Status strings (`in_progress`, etc.) are API-defined — verify with `itt meta enums --json`.

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| 2 | Bad args (e.g. missing `--tree` on a non-pillar create) | Add the required flag; check `--type`/`--parent` |
| 3 | Parent, tree, or node not found | Verify IDs with `itt node get` / `itt tree get` |
| 4 | Invalid parent/child pairing, bad enum, or already-promoted capture | Follow the hierarchy; run `itt meta enums --json`; check current state |

### See also
- `docs/CLI.md` § `capture`, § `node`, § `tree`
- `references/command-quick-reference.md`
- `workflows/updating-workflow.md` (status transitions, complete, promote)
