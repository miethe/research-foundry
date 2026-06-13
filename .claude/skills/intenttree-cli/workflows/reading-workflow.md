---
skill: intenttree-cli
workflow_id: reading
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# Reading Workflow

### When to use this workflow
The agent needs to inspect a node, walk a tree, paginate lists, read the event
log or artifacts, or assemble a prior-context pack before starting work. All
operations here are read-only and need no confirmation.

### Prerequisites
- API server reachable at `INTENTTREE_API_URL` (default `http://localhost:8000`).
- `INTENTTREE_WORKSPACE` set (or pass `--workspace`).
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Pass `--json`. Precedence: flags > env > `~/.config/intenttree/config.toml`.

### Recipe: read a node with related data
```bash
itt node get "$NODE" --json
# Expand related data (comma-separated, no spaces):
itt node get "$NODE" --include ancestors,children,edges,agent_runs,artifacts --json
```
`--include` values: `children`, `ancestors`, `edges`, `agent_runs`, `artifacts`.

### Recipe: list and paginate nodes
```bash
itt node list --tree "$TREE" --type atomic_task --status in_progress --json \
  | jq '.items[] | {id, title, status, progress}'

# Walk all pages via next_cursor
CURSOR=""; ALL="[]"
while :; do
  PAGE=$(itt node list --workspace "$WS" --limit 20 \
    ${CURSOR:+--cursor "$CURSOR"} --json)
  ALL=$(jq -s 'add' <(echo "$ALL") <(echo "$PAGE" | jq '.items'))
  CURSOR=$(echo "$PAGE" | jq -r '.next_cursor // empty'); [ -z "$CURSOR" ] && break
done
echo "$ALL" | jq 'length'
```
Envelope: `{ items, next_cursor, total }`. Filters: `--workspace`, `--tree`, `--type`, `--status` (verify via `itt meta enums --json`).

### Recipe: tree views
```bash
itt tree projection "$TREE" --json   # deeply nested pillar→…→step hierarchy
itt tree graph "$TREE" --json        # flat { nodes, edges } for dependency traversal
```
Use `projection` for structural summaries; `graph` for edge/dependency analysis.

### Recipe: pull prior context for a node
```bash
NODE_JSON=$(itt node get "$NODE" --include ancestors,agent_runs,artifacts --json)
echo "$NODE_JSON" | jq '[.ancestors[] | {id, title, type}]'        # intent chain
echo "$NODE_JSON" | jq '[.agent_runs[] | {id, state, created_at}]' # prior runs
# Artifacts from a completed run, plus node-scoped artifacts:
itt artifact list --run-id "$RUN" --json | jq '.items[] | {id, title, type}'
itt artifact get "$ARTIFACT" --json | jq '.content'
itt artifact list --node-id "$NODE" --json | jq '.items[] | {id, title, type}'
```

### Recipe: query the event log
```bash
itt events list --workspace "$WS" --node "$NODE" --type node.completed \
  --limit 20 --json | jq '[.items[] | {event_type, created_at}]'
itt events tail --workspace "$WS" --interval 5 --timeout 300 --json
```
`--workspace` is required by the API for event queries; `events tail` polls and exits 6 on timeout. Optional filters: `--tree`, `--node`, `--type`, `--actor`.

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| 3 | Node / tree / artifact not found | Recheck the ID; list the parent collection |
| 4 | Bad filter or enum value | Run `itt meta enums --json`; fix `--type`/`--status` |
| 6 | `events tail` timed out | Re-run; raise `--timeout` if expected to be quiet |

### See also
- `docs/CLI.md` § `node`, § `tree`, § `events`, § `artifact`, § `meta`
- `references/command-quick-reference.md`
- `workflows/whats-next-workflow.md` (turning reads into the next action)
