---
name: codex
description: Use when the user asks to run Codex CLI (codex exec, codex resume) or references OpenAI Codex for code analysis, refactoring, or automated editing. Uses GPT-5.3-Codex by default for state-of-the-art software engineering.
---

# Codex Skill Guide

## Running a Task
1. Default to `gpt-5.3-codex` model. Ask the user (via `AskUserQuestion`) which reasoning effort to use (`xhigh`, `high`, `medium`, `low`, or `none`). User can override model if needed (see Model Options below).
2. Select the sandbox mode required for the task; default to `--sandbox read-only` unless edits or network access are necessary.
3. Assemble the command with the appropriate options:
   - `-m, --model <MODEL>`
   - `--config model_reasoning_effort="<xhigh|high|medium|low|none>"`
   - `--sandbox <read-only|workspace-write|danger-full-access>`
   - `--full-auto`
   - `-C, --cd <DIR>`
   - `--skip-git-repo-check`
3. Always use --skip-git-repo-check.
4. When continuing a previous session, use `codex exec --skip-git-repo-check resume --last` via stdin. When resuming don't use any configuration flags unless explicitly requested by the user e.g. if he species the model or the reasoning effort when requesting to resume a session. Resume syntax: `echo "your prompt here" | codex exec --skip-git-repo-check resume --last 2>/dev/null`. All flags have to be inserted between exec and resume.
5. **IMPORTANT**: By default, append `2>/dev/null` to all `codex exec` commands to suppress thinking tokens (stderr). Only show stderr if the user explicitly requests to see thinking tokens or if debugging is needed.
6. Run the command, capture stdout/stderr (filtered as appropriate), and summarize the outcome for the user.
7. **After Codex completes**, inform the user: "You can resume this Codex session at any time by saying 'codex resume' or asking me to continue with additional analysis or changes."

### Quick Reference
| Use case | Sandbox mode | Key flags |
| --- | --- | --- |
| Read-only review or analysis | `read-only` | `--sandbox read-only 2>/dev/null` |
| Apply local edits | `workspace-write` | `--sandbox workspace-write --full-auto 2>/dev/null` |
| Permit network or broad access | `danger-full-access` | `--sandbox danger-full-access --full-auto 2>/dev/null` |
| Resume recent session | Inherited from original | `echo "prompt" \| codex exec --skip-git-repo-check resume --last 2>/dev/null` (no flags allowed) |
| Run from another directory | Match task needs | `-C <DIR>` plus other flags `2>/dev/null` |

## Model Options

### Codex Line (coding and execution tasks)

| Model | Best for | Context window | Key features |
| --- | --- | --- | --- |
| `gpt-5.3-codex` ⭐ | **Default**: Software engineering, agentic coding workflows, repo-scale edits | 400K input / 128K output | Optimized for coding, adaptive reasoning |
| `gpt-5.3-codex-spark` | Ultra-fast simple tasks (formatting, search, trivial fixes) | 400K input / 128K output | Highest speed, lowest latency |

### General Line (review, analysis, and planning tasks)

| Model | Best for | Context window | Key features |
| --- | --- | --- | --- |
| `gpt-5.2-max` | **Max model**: Ultra-complex reasoning, deep problem analysis | 400K input / 128K output | 76.3% SWE-bench, adaptive reasoning, $1.25/$10.00 |
| `gpt-5.2` | **Flagship general model**: Architecture review, planning, analysis | 400K input / 128K output | 76.3% SWE-bench, adaptive reasoning, $1.25/$10.00 |
| `gpt-5.2-mini` | Cost-efficient review/analysis (4x more usage allowance) | 400K input / 128K output | Near SOTA performance, $0.25/$2.00 |
| `gpt-5.1-thinking` | Ultra-complex reasoning, deep problem analysis | 400K input / 128K output | Adaptive thinking depth, runs 2x slower on hardest tasks |

**Reliability Hazard**: Codex models can overfit to their own generated plan — re-check outputs against repo reality (existing types, APIs, test state) before committing.

**Reasoning Effort Levels**:
- `xhigh` - Ultra-complex tasks (deep problem analysis, complex reasoning, deep understanding of the problem)
- `high` - Complex tasks (refactoring, architecture, security analysis, performance optimization)
- `medium` - Standard tasks (refactoring, code organization, feature additions, bug fixes)
- `low` - Simple tasks (quick fixes, simple changes, code formatting, documentation)
- `none` - Mechanical tasks (pure formatting, trivial text changes, no reasoning required)

**Effort Policy** (default selection by task type):

| Task type | Reasoning effort |
| --- | --- |
| Architecture design | `xhigh` |
| Complex debug | `xhigh` |
| Plan generation | `high` |
| Plan review | `medium` |
| Implementation | `medium` |
| Code review | `medium` |
| Simple search | `low` |
| Documentation | `low` |
| Formatting | `none` |

**Escalation rule**: Only escalate to `xhigh` when blocked with concrete artifacts (failing tests, stack traces). Attempt with `medium` first.

**Cached Input Discount**: 90% off ($0.125/M tokens) for repeated context, cache lasts up to 24 hours.

## Following Up
- After every `codex` command, immediately use `AskUserQuestion` to confirm next steps, collect clarifications, or decide whether to resume with `codex exec resume --last`.
- When resuming, pipe the new prompt via stdin: `echo "new prompt" | codex exec resume --last 2>/dev/null`. The resumed session automatically uses the same model, reasoning effort, and sandbox mode from the original session.
- Restate the chosen model, reasoning effort, and sandbox mode when proposing follow-up actions.

## Error Handling
- Stop and report failures whenever `codex --version` or a `codex exec` command exits non-zero; request direction before retrying.
- Before you use high-impact flags (`--full-auto`, `--sandbox danger-full-access`, `--skip-git-repo-check`) ask the user for permission using AskUserQuestion unless it was already given.
- When output includes warnings or partial results, summarize them and ask how to adjust using `AskUserQuestion`.

## CLI Version

Requires Codex CLI v0.57.0 or later for GPT-5.2 model support and v0.60.0 or later for GPT-5.3-Codex model support. The CLI defaults to `gpt-5.3-codex` on macOS/Linux and Windows. Check version: `codex --version`

Use `/model` slash command within a Codex session to switch models, or configure default in `~/.codex/config.toml`.
