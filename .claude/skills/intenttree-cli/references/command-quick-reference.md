---
name: intenttree-cli-command-quick-reference
description: >-
  Flat command lookup for all 11 intenttree/itt CLI groups, reconciled against
  backend/src/intenttree/cli/commands/ (live source wins over docs/CLI.md).
  Includes global flags, exit codes, config keys, env vars, and node hierarchy.
type: reference
skill_name: intenttree-cli
schema_version: 1
updated: 2026-06-10
---

# Command Quick Reference

Invocation: `uv run intenttree …` (alias `uv run itt …`) in this repo, or bare `intenttree`/`itt` when installed. Version check: `itt --version`. Pass `--json` on every parsed command. Syntax source of truth: `backend/src/intenttree/cli/commands/`.

## Global flags (every command)
`--api-url URL` · `--token TOKEN` · `--workspace ID` · `--json` · `--verbose`/`-v` · `--timeout SECONDS` (default 30) · `--version`

## Exit codes (inspect `$?`; errors → stderr, data → stdout)
`0` SUCCESS · `1` GENERAL_ERROR (5xx) · `2` INVALID_USAGE (bad args) · `3` NOT_FOUND (404) · `4` CONFLICT (400/409/422, wrong state) · `5` PERMISSION_DENIED (401/403) · `6` TIMEOUT (SSE retries exhausted).

## Config & env (precedence: flags > env > `~/.config/intenttree/config.toml`, mode 0600)
| Config key | Env var | Purpose (default) |
|---|---|---|
| `api_url` | `INTENTTREE_API_URL` | API base URL (`http://localhost:8000`) |
| `api_token` | `INTENTTREE_API_TOKEN` | Bearer token (none = auth disabled) |
| `workspace` | `INTENTTREE_WORKSPACE` | Active workspace ID (none) |

Node hierarchy — on-tree: `pillar → work_area → work_package → atomic_task → step`; off-tree: `side_quest`, `quick_win`. `--mode`: `human`/`agent`/`hybrid`. Verify enums via `itt meta enums --json`.

## `capture` (off-tree intake)
| Command | Key options |
|---|---|
| `capture add TITLE` | `--type [side_quest\|quick_win]`, `--workspace`, `--note` |
| `capture list` | `--workspace`, `--type`, `--cursor`, `--limit` |
| `capture promote NODE_ID` | `--parent`, `--tree`, `--dry-run` |

## `node` (tree node ops)
| Command | Key options |
|---|---|
| `node get NODE_ID` | `--include children,ancestors,edges,agent_runs,artifacts` |
| `node list` | `--workspace`, `--tree`, `--type`, `--status`, `--cursor`, `--limit` |
| `node create` | `--title`*, `--type`*, `--tree`, `--parent`, `--status`, `--estimate`, `--mode` |
| `node update NODE_ID` | `--title`, `--status`, `--estimate`, `--mode`, `--description` |
| `node complete NODE_ID` | (cascades progress rollup) |
| `node decompose NODE_ID` | `--strategy [template\|agent]`, `--count`, `--agent-id`, `--dry-run` |
| `node assign NODE_ID` | `--owner`, `--agent`, `--mode`, `--dry-run` |
| `node move NODE_ID` | `--parent`*, `--position` |
| `node defer NODE_ID` | — |
| `node delete NODE_ID` | `--force` (req in TTY), `--hard` (permanent vs archive) |

## `tree` (work-tree ops)
| Command | Key options |
|---|---|
| `tree list` | `--workspace`, `--cursor`, `--limit` |
| `tree get ID` · `tree projection ID` · `tree graph ID` | (ID/slug) |
| `tree create` | `--title`*, `--workspace`, `--slug`, `--description` |

## `today` (daily train)
| Command | Key options |
|---|---|
| `today show` | `--day YYYY-MM-DD`, `--workspace` |
| `today schedule ITEM_ID` | `--start`* (minutes from midnight), `--lane` (default `main`), `--duration` |
| `today unschedule ITEM_ID` | — |

## `run` (agent run lifecycle)
| Command | Key options |
|---|---|
| `run list` | `--workspace`, `--state`, `--node`, `--cursor`, `--limit` |
| `run get RUN_ID` | — |
| `run start NODE_ID` | `--agent` (def `agent_simulated`), `--harness [simulated\|copy_paste]`, `--mode`, `--workspace`, `--name` |
| `run prompt RUN_ID` | emits `prompt_text` (not JSON); exit 4 if not awaiting |
| `run report RUN_ID` | `--summary`*, `--artifact` (repeat), `--artifact-title`, `--artifact-type` (def `file`) |
| `run follow RUN_ID` | `--timeout`; SSE backoff 2s/5s/10s, exit 6 on retries exhausted |
| `run approve RUN_ID` | `--step`, `--note` |
| `run reject RUN_ID` | `--step`, `--reason` |
| `run cancel RUN_ID` · `run awaiting` | awaiting: `--workspace`, `--cursor`, `--limit` |

## `events` (domain log) — `--workspace` required by API
| Command | Key options |
|---|---|
| `events list` | `--workspace`, `--tree`, `--node`, `--type`, `--actor`, `--cursor`, `--limit` |
| `events tail` | `--workspace`, `--tree`, `--node`, `--type`, `--interval` (def 5), `--timeout` |

## `workspace` & `agent`
`workspace list` (`--limit`, `--cursor`) · `workspace get ID` · `workspace use ID` (writes config, no API call). `agent list` (`--workspace-id`, `--limit`, `--cursor`) · `agent get ID`.

## `artifact`
| Command | Key options |
|---|---|
| `artifact list` | `--workspace-id`, `--node-id`, `--run-id`, `--type`, `--limit`, `--cursor` |
| `artifact get ID` | — |
| `artifact upload PATH` | `--title`, `--type`, `--node-id`, `--run-id`, `--workspace-id` |

## `meta` & `config`
`meta enums` (node types, statuses, run states) · `meta version` (API version). `config set KEY VALUE` · `config get KEY` · `config list` · `config whoami` (keys: `api_url`, `api_token`, `workspace`).

\* = required. Live-source notes: `tree create` uses `--title` (not `--name`/`--intent`); `today schedule` uses `--start` (not `--start-min`); `agent list`/`artifact list` use `--workspace-id`.
