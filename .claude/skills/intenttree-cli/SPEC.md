---
schema_version: 2
doc_type: skill_spec
skill_name: intenttree-cli
skill_version: 0.1.0
status: draft
created: 2026-06-05
updated: 2026-06-05
owner: miethe
source_docs:
  - docs/CLI.md
  - docs/API.md
  - docs/DATA_MODEL.md
affects_commands: []
---

<!-- Convention reference: .claude/specs/artifact-structures/skill-spec-convention.md -->

# intenttree-cli — Skill Specification

> **Reading this file**: This is the versioned capability contract for the `intenttree-cli` skill.
> For invocation-time routing, see `SKILL.md` in this same directory.

---

## 1. Purpose & Scope

**Mission**: Enable agents to orchestrate the full IntentTree work-tree lifecycle — node creation, reading, updating, agent dispatch, daily planning, and project bootstrap — through the `intenttree`/`itt` CLI, using only documented REST-backed surfaces and deferring all command syntax decisions to `docs/CLI.md`.

**In scope**:
- Creating tree nodes of all typed levels: pillar, work_area, work_package, atomic_task, step, side_quest, quick_win.
- Capturing off-tree inbox items (`capture add`) and promoting them into the tree (`capture promote`).
- Reading nodes (`node get --include`), tree projections and graph payloads (`tree projection`, `tree graph`).
- Pulling prior context: event log (`events list`), artifacts (`artifact list`), and agent run history (`run list`, `run get`).
- Updating node fields, status, assignment, and execution mode; lifecycle actions: complete, move, defer, decompose, delete.
- Daily planning: `today show`, `today schedule`, `today unschedule`, backlog view, identifying next work.
- M1 dispatch loop: `run start` (copy_paste harness) → `run prompt` → `run report` → `node complete`.
- Streaming run steps with `run follow` (SSE); tailing domain events with `events tail`.
- Human-in-the-loop approvals: `run approve`, `run reject`, `run cancel`; listing `run awaiting`.
- Managing workspace config (`config set/get/list/whoami`, `workspace use`).
- Discovering valid enum values and API version via `meta enums`/`meta version`.
- Bootstrapping IntentTree into a host project: config, workspace, seed tree, CLAUDE.md sidecar.

**Out of scope**:
- Modifying the IntentTree backend or frontend codebase — use `python-backend-engineer`, `frontend-developer`, or `ui-engineer-enhanced`.
- Alembic schema migrations — the CLI has no migration commands; use `uv run alembic` directly.
- Direct database access — the CLI is an httpx REST client and has no SQLAlchemy imports.
- Generating skills, agent prompts, or AI artifacts — use `skill-creator` or the AI artifacts engineer.
- Running a live server during agent builds in this repo — per `docs/AGENT_BRIEF.md`, this is prohibited.
- Prioritization scoring queries (strategic_value, urgency, leverage, readiness, risk) — no CLI surface exists yet; see Enhancement Backlog.

---

## 2. Capability Coverage

| Intent | Workflow / Section | Canonical Doc |
|--------|--------------------|---------------|
| Create a pillar node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create a work_area node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create a work_package node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create an atomic_task node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create a step node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create a side_quest node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Create a quick_win node | `workflows/creation-workflow.md` | `docs/CLI.md § node create` |
| Capture an off-tree inbox item | `workflows/creation-workflow.md` | `docs/CLI.md § capture add` |
| Decompose a node into child plan nodes | `workflows/creation-workflow.md` | `docs/CLI.md § node decompose` |
| Get a node with related data (children, ancestors, edges, agent_runs, artifacts) | `workflows/reading-workflow.md` | `docs/CLI.md § node get` |
| Get tree nested projection | `workflows/reading-workflow.md` | `docs/CLI.md § tree projection` |
| Get tree graph payload (nodes + edges) | `workflows/reading-workflow.md` | `docs/CLI.md § tree graph` |
| List or tail domain events | `workflows/reading-workflow.md` | `docs/CLI.md § events` |
| List or get artifacts for a node or run | `workflows/reading-workflow.md` | `docs/CLI.md § artifact` |
| Pull prior context (runs, events, artifacts) for a node | `workflows/reading-workflow.md` | `docs/CLI.md § run list, events list, artifact list` |
| Update node title, status, estimate, mode, or description | `workflows/updating-workflow.md` | `docs/CLI.md § node update` |
| Mark a node complete (cascades rollup) | `workflows/updating-workflow.md` | `docs/CLI.md § node complete` |
| Assign a node to a user, agent, or execution mode | `workflows/updating-workflow.md` | `docs/CLI.md § node assign` |
| Move (reparent) a node | `workflows/updating-workflow.md` | `docs/CLI.md § node move` |
| Defer a node | `workflows/updating-workflow.md` | `docs/CLI.md § node defer` |
| Delete (archive or hard-delete) a node | `workflows/updating-workflow.md` | `docs/CLI.md § node delete` |
| Promote a capture into the work tree | `workflows/updating-workflow.md` | `docs/CLI.md § capture promote` |
| Show today's plan (schedule + backlog) | `workflows/whats-next-workflow.md` | `docs/CLI.md § today show` |
| Schedule or unschedule a backlog item | `workflows/whats-next-workflow.md` | `docs/CLI.md § today schedule / unschedule` |
| Identify the next work to pick up | `workflows/whats-next-workflow.md` | `docs/CLI.md § today show, run awaiting` |
| List runs awaiting human approval | `workflows/whats-next-workflow.md` | `docs/CLI.md § run awaiting` |
| Start an agent run (copy_paste or simulated harness) | `workflows/dispatch-workflow.md` | `docs/CLI.md § run start` |
| Fetch prompt text for a copy_paste run | `workflows/dispatch-workflow.md` | `docs/CLI.md § run prompt` |
| Submit a completion report with optional artifacts | `workflows/dispatch-workflow.md` | `docs/CLI.md § run report` |
| Stream live step and state updates (SSE) | `workflows/dispatch-workflow.md` | `docs/CLI.md § run follow` |
| Approve a gated run step and resume | `workflows/dispatch-workflow.md` | `docs/CLI.md § run approve` |
| Reject a gated run step | `workflows/dispatch-workflow.md` | `docs/CLI.md § run reject` |
| Cancel a queued, running, or awaiting run | `workflows/dispatch-workflow.md` | `docs/CLI.md § run cancel` |
| Bootstrap IntentTree config, workspace, and seed tree in a host project | `workflows/bootstrap-workflow.md` | `docs/CLI.md § config, workspace, tree create` |
| Add CLAUDE.md sidecar snippet to a host project | `workflows/bootstrap-workflow.md` | `templates/claude-md-snippet.md` |
| Workspace config: set, get, list, whoami | `workflows/bootstrap-workflow.md` | `docs/CLI.md § config` |
| Discover valid enum values (node types, statuses, run states) | `SKILL.md § Confidence Anchor` | `docs/CLI.md § meta enums` |
| CLI command syntax quick lookup | `references/command-quick-reference.md` | `docs/CLI.md` |

> When no canonical doc exists for an intent, `—` appears in the Canonical Doc column and a backlog entry in §4 tracks the gap.

---

## 3. Invariants & Constraints

1. **CLI is REST-only, never direct DB**: The CLI is a thin httpx client (`backend/src/intenttree/cli/client.py`). Agents must not claim or assume the CLI bypasses the API or accesses the database directly. Every command requires a running API server.

2. **`docs/CLI.md` is the authoritative source for command syntax**: Workflow files provide agent-specific patterns (sequencing, error recovery, scripting idioms). They do not duplicate flag definitions or argument formats from `docs/CLI.md`. When in conflict, `docs/CLI.md` wins.

3. **Agents use `--json` for all machine-consumed output**: Agents must pass `--json` when parsing command output. Human-readable table output is not a stable parsing surface.

4. **Exit codes 0–6 are a contract**: Agents must inspect `$?` after every command. The mapping is deterministic and defined in `backend/src/intenttree/cli/exit_codes.py`. Agents must not parse stderr to infer success or failure.

5. **`bootstrap-workflow.md` never overwrites an existing CLAUDE.md section without showing a diff**: Before appending or modifying any CLAUDE.md in a host project, the workflow must read the existing file and show the proposed diff to the agent or user.

6. **Never run a live server during agent builds in this repo**: Per `docs/AGENT_BRIEF.md`, agent builds under this repo use `uv run pytest` only. Dispatch workflows (`dispatch-workflow.md`) assume a separately running server — they do not start one.
   _Source_: `docs/AGENT_BRIEF.md`

7. **`uv run` wraps all CLI invocations in this repo**: Agents operating inside the backend uv project must prefix every CLI invocation with `uv run` (`uv run intenttree …`). Bare `intenttree` is only valid when the package is globally installed.

8. **Workflow files stay under 400 lines**: Any workflow exceeding 400 lines must split overflow into a named supporting reference file. This preserves single-load token efficiency.

9. **No speculative CLI coverage**: Workflow files document only surfaces present in `backend/src/intenttree/cli/commands/`. Planned or aspirational commands belong in the Enhancement Backlog (§4), not in active workflow docs.

---

## 4. Enhancement Backlog

- **[BL-1] MCP server transport**: Expose IntentTree CLI operations as MCP tools so agents can invoke them via the MCP protocol rather than subprocess shell commands.
  _Status_: candidate
  _Rationale_: MCP transport would eliminate shell quoting complexity and enable structured input/output without `--json` parsing. Requires a dedicated MCP server layer on top of the existing httpx client.

- **[BL-2] Prioritization-score query commands**: CLI commands to query or filter nodes by `strategic_value`, `urgency`, `leverage`, `readiness`, and `risk` scoring fields.
  _Status_: candidate
  _Rationale_: Score fields exist in the data model (`docs/DATA_MODEL.md`) but there are no CLI flags to filter or sort by them. High value for "what's next" automation once the API exposes score-based ordering.

- **[BL-3] Watch-mode what's-next**: A `today watch` or `run watch` command that continuously polls and re-renders the daily schedule as nodes complete or new runs are approved.
  _Status_: deferred
  _Rationale_: `events tail` partially covers this. A dedicated watch-mode command with structured output requires the SSE or WebSocket upgrade of the events endpoint.

- **[BL-4] Agent-harness beyond copy_paste and simulated**: Additional harness implementations — e.g., a native `claude_code` harness that invokes Claude Code SDK directly without copy/paste friction.
  _Status_: candidate
  _Rationale_: The dispatch harness is extensible (Protocol-based in `backend/src/intenttree/agents/`). A `claude_code` harness would close the loop without manual prompt transfer.

- **[BL-5] Decompose with agent strategy end-to-end**: The `node decompose --strategy agent` path is documented but depends on LLMExecutor, which is currently a stub. Full agentic decomposition requires a wired LLM executor.
  _Status_: deferred
  _Rationale_: `LLMExecutor` in `backend/src/intenttree/agents/llm.py` is a stub as of 2026-06-05. Restore to candidate when the executor is implemented.

- **[BL-6] Artifact download command**: A `artifact download <id>` command to retrieve artifact content to disk, complementing the existing `artifact upload`.
  _Status_: candidate
  _Rationale_: Upload exists; download is the natural complement for agent workflows that need to retrieve prior output files.

---

## 5. Changelog

### v0.1.0 — 2026-06-05
- Initial SPEC.md drafted.
- Capability coverage matrix: 35 intents across 7 workflows (creation, reading, updating, whats-next, dispatch, bootstrap, quick-reference).
- Invariants: 9 entries covering REST-only constraint, syntax source of truth, `--json`, exit codes, bootstrap safety, server policy, uv wrapping, line limit, and no-speculative-coverage.
- Enhancement Backlog: 6 entries (MCP transport, prioritization scoring, watch-mode, extended harnesses, agent-decompose, artifact download).
- Status: draft.

---

## 6. Integration Points

| Agent / Command | Invocation Pattern | Notes |
|-----------------|--------------------|-------|
| `lead-architect` | `Skill("intenttree-cli")` | Uses creation, reading, and dispatch workflows when planning or orchestrating work-tree changes |
| `python-backend-engineer` | `Skill("intenttree-cli")` | References reading and dispatch workflows when implementing or testing CLI-adjacent backend features |
| `pm/implementation-planner` | `Skill("intenttree-cli")` | Uses bootstrap and what's-next workflows to initialize project trees and inspect planning state |
| `pm/feature-planner` | `Skill("intenttree-cli")` | References creation and updating workflows when decomposing features into typed tree nodes |
| `dev-team/frontend-developer` | `Skill("intenttree-cli")` | Uses reading workflows to pull node and tree data shapes for UI implementation reference |
| `reviewers/task-completion-validator` | `Skill("intenttree-cli")` | References dispatch and reading workflows to verify agent-run completion reports |

**Co-loaded with**: `artifact-tracking` when tracking progress alongside CLI operations. `dev-execution` when CLI operations are part of a broader feature sprint.

**No `/dev:*` command bindings**: This skill has no automatic binding to dev workflow commands. Agents invoke it explicitly via `Skill("intenttree-cli")`.

---

## 7. Success Signals

- Agents route to the correct single workflow file on first attempt without re-reading `SKILL.md` mid-task.
- All agent-constructed `intenttree` invocations use flags and subcommands present in `docs/CLI.md`; no invented flags or nonexistent subcommands appear in agent output.
- Agents pass `--json` on every command when parsing output; no agent parses human-readable table columns.
- After a `run follow` completes with exit code `0`, agents proceed to `run report` and `node complete` without additional polling.
- When any command exits with code `4` (CONFLICT), agents diagnose state mismatch (wrong run state, node already complete) before retrying — they do not blindly retry.
- Bootstrap workflow produces a working config, workspace, and tree in a net-new host project without overwriting existing CLAUDE.md content.
- Token usage per typical intent stays under 10,000 tokens: `SKILL.md` routing read plus one workflow file (≤400 lines) without cascading reads of all 7 workflow files.
