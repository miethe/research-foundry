---
skill: intenttree-cli
workflow_id: whats-next
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# What's-Next Workflow

### When to use this workflow
The agent (or user) asks "what should I work on?", wants today's plan, needs to
schedule/unschedule an item, or must clear runs awaiting approval. Reads need no
confirmation; `today schedule`/`unschedule` are mutations — confirm first.

### Prerequisites
- API server reachable at `INTENTTREE_API_URL` (default `http://localhost:8000`).
- `INTENTTREE_WORKSPACE` set (or pass `--workspace`).
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Pass `--json`. Precedence: flags > env > `~/.config/intenttree/config.toml`.

### Recipe: today's plan (schedule + backlog)
```bash
itt today show --workspace "$WS" --json \
  | jq '{schedule: [.schedule[] | {id, title, start_min, lane}],
         backlog:  [.backlog[]  | {id, title, type, status}]}'
itt today show --workspace "$WS" --day 2026-06-10 --json   # a specific day
```

### Recipe: schedule / unschedule a backlog item
```bash
itt today schedule "$ITEM" --start 540 --lane focus --duration 60 --json
itt today unschedule "$ITEM" --json
```
`--start` is required (minutes from midnight, e.g. 540 = 09:00). `--lane`
defaults to `main`; `--duration` (minutes) is optional.

### Recipe: pick the next item (decision procedure)
Take the first non-empty result, in order:
```bash
# 1. Runs awaiting human approval — always clear these first
itt run awaiting --workspace "$WS" --json | jq '.items[] | {id, node_id, state}'
# 2. Earliest scheduled item not yet complete
itt today show --workspace "$WS" --json \
  | jq '[.schedule[]] | sort_by(.start_min) | .[0] | {id, title, start_min}'
# 3. Top backlog item (API-ordered by priority)
itt today show --workspace "$WS" --json | jq '.backlog[0] | {id, title, type, status}'
# 4. Fallback: nodes by status (verify status strings first)
itt meta enums --json | jq '.node_status'
itt node list --workspace "$WS" --status in_progress --limit 5 --json \
  | jq '.items[] | {id, title, type, progress}'
```
If `run awaiting` returns rows, review with `itt run get <id>` / `itt run prompt
<id>` and approve or reject (see `dispatch-workflow.md`) before moving on.

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| 2 | `today schedule` missing `--start` | Add `--start <minutes>` |
| 3 | Item / node not found | Recheck the ID from `today show` output |
| 4 | Item already scheduled, or bad `--status`/`--lane` | Unschedule first; run `itt meta enums --json` |

### See also
- `docs/CLI.md` § `today`, § `run`, § `node`, § `meta`
- `references/command-quick-reference.md`
- `workflows/dispatch-workflow.md` (act on the chosen item)
- `workflows/reading-workflow.md` (assemble a context pack before dispatch)
