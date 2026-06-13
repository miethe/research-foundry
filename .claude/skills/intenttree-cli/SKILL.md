---
name: intenttree-cli
description: >-
  Drive the IntentTree work-tree through the `intenttree`/`itt` CLI via natural
  language. Use to capture inbox items, create or decompose nodes
  (pillar → work_area → work_package → atomic_task → step), query "what's next",
  complete/update/assign/move/defer nodes, run the M1 copy/paste agent dispatch
  loop, pull prior context, and bootstrap IntentTree into a project. Triggers:
  "log this to IntentTree", "create a task/tree", "what should I work on next",
  "schedule today", "start a run", "decompose this", "mark it done". Requires a
  running API server; the CLI is a thin httpx REST client, never a direct DB
  accessor. Progressive disclosure: load only the one workflow doc the intent matches.
version: 1.0
updated: 2026-06-10
spec: ./SPEC.md
---

## Research Foundry binding (read first)

**RF ships its own offline, file-based intent/tree subset** — no live server required.

| RF command | What it does |
|---|---|
| `rf intent show` | Display the current intent tree from YAML on disk |
| `rf tree add-node` | Append a node to the intent tree YAML under the RF workspace |

These commands read and write YAML files under the RF workspace directory and are the
correct tool for **ordinary RF research runs** (intent capture, node decomposition, loop
step 4 in the research cycle). They work fully offline.

**Live IntentTree integration:** Research Foundry now integrates bidirectionally with the
live IntentTree server when reachable (configured via `integrations.intenttree.base_url` in
`foundry.yaml` or `INTENTTREE_BASE_URL` env var):

- `rf intake intenttree <node_id>` — pull a dispatched IntentTree task (with its linked detail
  including MeatyWiki refs) into capture → triage → optional plan; back-links the RF intent
  to the source node. Offline fallback: accept a locally-exported node YAML via `--from-file PATH`.
- `rf status push --run <run_id> --to intenttree` — push status updates at key milestones
  (discovery_started, sources_ingested, verify_passed, bundle_written) back to the originating
  IntentTree node. Best-effort when reachable; silent degrade when offline.
- `rf writeback <run_id> --targets intenttree` — link the evidence bundle, report, and result
  artifacts back to the originating node. Offline fallback: write a candidate file only.

This `intenttree-cli` skill is a **REST client to a live IntentTree server** for richer
direct work-tree operations (`decompose`, `dispatch`, `whats-next`, M1 agent runs, scheduling).
Use it when you need features the RF CLI does not expose beyond inbound task intake.

**Decision rule**: If you are inside an RF research run and the task is intent capture or
tree manipulation, use `rf intent`/`rf tree` or `rf intake intenttree` first. Reach for this
skill only when you need server-side features beyond task intake (decompose, dispatch, scheduling).

See also: `.claude/skills/research-foundry/SKILL.md` (the RF research run skill — covers
the full swarm lifecycle including loop step 4 where `rf intent`/`rf tree` and the new IntentTree
commands are called).

---

# intenttree-cli — Router

Thin router: match the agent's intent to ONE workflow doc, open it, and stop.
Command syntax lives in `references/command-quick-reference.md` and the workflow
docs — never here. Canonical syntax: `docs/CLI.md`, reconciled to
`backend/src/intenttree/cli/commands/` (live source wins on any conflict).

## When To Use

| The agent needs to… | Route |
|---|---|
| Record, decompose, query, or advance IntentTree work from a terminal session | a workflow in the Route Table below |

## When NOT To Use

| Situation | Correct approach |
|---|---|
| No API server running (agent build in this repo) | Do not invoke; per `docs/AGENT_BRIEF.md`, never start a live server during builds |
| Changing IntentTree backend/frontend code | Use the relevant engineering agent, not this skill |
| Alembic schema migrations | Use the migration workflow; the CLI has no migration commands |
| Auto-generating a task breakdown from prose | Not built; CLI decompose is structural only (see creation-workflow) |

## Route Table

| User Intent | Workflow Doc | Notes |
|---|---|---|
| Capture an inbox item; create nodes under a parent; build a tree; decompose; worked end-to-end | `workflows/creation-workflow.md` | mutation — confirm first |
| Read a node, tree projection/graph, events, artifacts, or a prior-context pack | `workflows/reading-workflow.md` | read-only |
| Update fields/status/mode; complete, assign, move, defer, delete; promote a capture | `workflows/updating-workflow.md` | mutation — confirm first |
| "What should I work on", today's plan, schedule/unschedule, runs awaiting approval | `workflows/whats-next-workflow.md` | reads + scheduling mutations |
| M1 dispatch loop (run start → prompt → report → node complete); approve/reject/cancel; follow | `workflows/dispatch-workflow.md` | mutation — confirm first |
| Bootstrap config, workspace, seed tree, and CLAUDE.md snippet in a host project | `workflows/bootstrap-workflow.md` | mutation — confirm first |
| Quick command/flag lookup across all 11 groups | `references/command-quick-reference.md` | reference |

## Policy

- **Progressive Disclosure** — open only the one workflow doc the intent matches; never preload all files. Pair it with `references/command-quick-reference.md` only when exact flag syntax is needed.
- **Permission Protocol** — mutations (create, update, complete, delete, assign, move, defer, decompose, promote, schedule, dispatch start/report/approve/reject/cancel, config set) require explicit user confirmation before execution. Read-only ops (get, list, projection, graph, today show, run get/list/awaiting, events, meta, config get/list/whoami) do not.
- **Route-First Invariant** — `docs/CLI.md` (reconciled to `cli/commands/`) is the canonical command reference; workflow docs cover agent-specific multi-step patterns and recovery, not raw syntax. On any doc-vs-source conflict, the CLI source wins.

## Setup / Confidence Anchor

Install (this repo): `cd backend && uv sync` registers both `intenttree` and
`itt` entry points. For a global install, confirm `intenttree`/`itt` resolves on
PATH (version check in `references/command-quick-reference.md`).

Config precedence (highest → lowest): CLI flags → environment variables →
`~/.config/intenttree/config.toml` (mode 0600).

| Env var | Purpose | Default |
|---|---|---|
| `INTENTTREE_API_URL` | API base URL | `http://localhost:8000` |
| `INTENTTREE_API_TOKEN` | Bearer token for auth | none (auth disabled) |
| `INTENTTREE_WORKSPACE` | Active workspace ID | none |

**Self-set token (agent session):** no interactive prompt exists — supply the
token non-interactively. Current shell: `export INTENTTREE_API_TOKEN=<token>`.
Persist to config: `itt config set api_token <token>`. Set the workspace once
(`export INTENTTREE_WORKSPACE=<id>` or `itt workspace use <id>`) so commands need
no per-call workspace.
