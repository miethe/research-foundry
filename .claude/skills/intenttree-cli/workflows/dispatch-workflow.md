---
skill: intenttree-cli
workflow_id: dispatch
canonical_docs:
  - docs/CLI.md
version: 1.1
updated: 2026-06-10
---

# Dispatch Workflow (M1 copy/paste loop)

### When to use this workflow
The agent must execute a delegated node through the M1 dispatch loop: start a
run, retrieve the prompt, do the work, submit a report, and complete the node —
plus approve/reject/cancel gated runs. All steps are mutations — confirm first.
Never start the API server during a build; it must already be running.

### Prerequisites
- API server reachable at `INTENTTREE_API_URL` (default `http://localhost:8000`).
- `INTENTTREE_WORKSPACE` set (or pass `--workspace`); the target `$NODE` known.
- Run `uv run intenttree …` (alias `uv run itt …`) in this repo; bare `intenttree`/`itt` if installed. Pass `--json` where parsed. Precedence: flags > env > `~/.config/intenttree/config.toml`.

### Recipe: full M1 loop (start → follow → prompt → report → complete)
```bash
# 1. Start a copy/paste run (emits run id to stdout; capture with --json + jq)
RUN=$(itt run start "$NODE" --harness copy_paste --agent agent_simulated --json \
  | jq -r '.id')
# 2. Stream to a terminal state, then fetch the prompt (run prompt emits raw text)
itt run follow "$RUN" --timeout 120
PROMPT=$(itt run prompt "$RUN")
echo "$PROMPT"   # paste into the external agent CLI; collect output artifacts
# 3. Submit the report (--artifact repeatable)
itt run report "$RUN" --summary "Completed; see artifact." \
  --artifact ./out/survey.md --artifact-title "Survey" --artifact-type document
# 4. Complete the node (cascades progress rollup)
itt node complete "$NODE" --json
```
`--harness` is `simulated` (default) or `copy_paste`; `--agent` defaults to
`agent_simulated`. `run prompt` and `run follow` emit text/SSE, not JSON.

### Recipe: monitor and gate runs
```bash
itt run list --workspace "$WS" --state awaiting_human --node "$NODE" --json
itt run awaiting --workspace "$WS" --json | jq '.items[] | {id, node_id, state}'
itt run approve "$RUN" --step "$STEP" --note "LGTM"        # resume a gated run
itt run reject  "$RUN" --step "$STEP" --reason "Scope creep"  # terminates run
itt run cancel  "$RUN"                                      # any non-terminal run
```

### Recipe: attach artifacts independently
```bash
itt artifact upload ./out/report.md --title "Report" --type document \
  --node-id "$NODE" --run-id "$RUN" --workspace-id "$WS"
```
Run states: `queued → running → awaiting_human → completed | failed | cancelled`.

### Error handling
| Exit code | Meaning | Recovery |
|-----------|---------|----------|
| 3 | Run or node not found | Verify with `itt run get` / `itt node get`; check workspace |
| 4 | `run prompt`/`run report` against wrong state; node already complete | `itt run get` to inspect state; wait for `awaiting_human`; completion is idempotent |
| 6 | `run follow` timed out / SSE retries exhausted (backoff 2s,5s,10s) | Re-run `run follow`, or poll `run get`; then continue |

### See also
- `docs/CLI.md` § "M1 Dispatch-Loop Quickstart", § `run`, § `artifact`
- `references/command-quick-reference.md`
- `workflows/reading-workflow.md` (context pack before dispatch)
- `workflows/whats-next-workflow.md` (choosing the node to dispatch)
