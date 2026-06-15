---
id: mwb_20260613_claude_agent_sdk_readiness_for_research
evidence_bundle_id: bundle_20260613_intent_research_20260613_what_is_the
target_page: meatywiki/sources/claude_agent_sdk_readiness_for_research.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260613_what_is_the_current_release_state: 69
  supported claim(s) across 10 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
links:
  source_cards:
  - src_20260613_rib008_00
  - src_20260613_rib008_01
  - src_20260613_rib008_02
  - src_20260613_rib008_03
  - src_20260613_rib008_04
  - src_20260613_rib008_05
  - src_20260613_rib008_06
  - src_20260613_rib008_07
  - src_20260613_rib008_08
  - src_20260613_rib008_09
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Claude Agent SDK readiness for Research Foundry: skills API, subagent API, and Python package stability

## Summary

Source note distilled from research run rf_run_20260613_what_is_the_current_release_state: 69 supported claim(s) across 10 source card(s).

## Key claims

- The Python SDK supports PreToolUse, PostToolUse, PostToolUseFailure, UserPromptSubmit, Stop, SubagentStart, SubagentStop, PreCompact, PermissionRequest, and Notification, while PostToolBatch, MessageDisplay, SessionStart, SessionEnd, Setup, and several others are TypeScript-only. [claim:clm_001]
- SessionStart and SessionEnd cannot be registered as Python SDK callback hooks (HookEvent omits them) and in Python work only as shell-command hooks defined in settings files loaded via setting_sources. [claim:clm_002]
- The tool-use ID correlates PreToolUse and PostToolUse events for the same tool call, and agent_id/agent_type are populated inside subagents (in Python only on PreToolUse, PostToolUse, and PostToolUseFailure). [claim:clm_003]
- PreToolUse callbacks set permissionDecision of allow, deny, ask, or defer, and the precedence is deny over defer over ask over allow, with any deny blocking the operation regardless of other hooks. [claim:clm_004]
- Hooks can block dangerous operations, audit-log every tool call, transform inputs via updatedInput and tool outputs via updatedToolOutput, and forward Notifications (permission_prompt, idle_prompt, auth_success) to external services like Slack or PagerDuty. [claim:clm_005]
- Hooks may not fire when the agent hits the max_turns limit because the session ends before hooks can execute. [claim:clm_006]
- Async hook outputs (async_=True in Python) let side-effect logging run without blocking the agent, which proceeds immediately, but such outputs cannot block, modify, or inject context into the operation. [claim:clm_007]
- query() creates a new session for each interaction by default and returns an async iterator of messages, with no memory of prior interactions unless continue_conversation or resume is passed in ClaudeAgentOptions. [claim:clm_008]
- ClaudeSDKClient maintains a conversation session across multiple exchanges, positioned as the stateful, multi-turn counterpart to query(). [claim:clm_009]
- Setting the skills option (a list of names or 'all') causes the SDK to add the Skill tool to allowed_tools automatically; if you also pass tools, you must include 'Skill' in that list. [claim:clm_010]
- When setting_sources is omitted or None, query() loads the same filesystem settings as the Claude Code CLI (user, project, and local); managed policy settings load in all cases. [claim:clm_011]
- AgentDefinition field names use camelCase (e.g. disallowedTools, permissionMode, maxTurns) to match the TypeScript wire format, and passing a snake_case keyword raises a TypeError at construction time. [claim:clm_012]
- An AgentDefinition's model field accepts an alias such as 'sonnet', 'opus', 'haiku', or 'inherit', or a full model ID, and falls back to the main model if omitted. [claim:clm_013]
- max_thinking_tokens is deprecated in favor of the thinking config, which takes precedence over it. [claim:clm_014]
- The context-1m-2025-08-07 beta is retired as of April 30, 2026; passing the header with Sonnet 4.5 or Sonnet 4 has no effect and over-200k requests error, with newer 4.6/4.7/4.8 models offering 1M context at standard pricing without a beta header. [claim:clm_015]
- Transport is documented as a low-level internal API whose interface may change in future releases, requiring custom implementations to be updated. [claim:clm_016]
- Telemetry is enabled with CLAUDE_CODE_ENABLE_TELEMETRY=1, with optional exporters OTEL_METRICS_EXPORTER (otlp/prometheus/console/none) and OTEL_LOGS_EXPORTER (otlp/console/none). [claim:clm_017]
- Default export intervals are 60 seconds for metrics and 5 seconds for logs, with shorter intervals recommended only for debugging. [claim:clm_018]
- Distributed tracing is a beta feature requiring CLAUDE_CODE_ENABLE_TELEMETRY=1 plus CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 and OTEL_TRACES_EXPORTER, with spans linking each prompt to API requests and tool executions. [claim:clm_019]
- When tracing is active, Bash and PowerShell subprocesses automatically inherit a TRACEPARENT env var carrying the W3C trace context of the active tool execution span, enabling end-to-end distributed tracing through scripts. [claim:clm_020]
- In Agent SDK and non-interactive (-p) sessions, Claude Code reads TRACEPARENT and TRACESTATE from its environment so its spans become children of the caller's distributed trace; interactive sessions ignore inbound TRACEPARENT. [claim:clm_021]
- OTLP endpoint is configured via OTEL_EXPORTER_OTLP_PROTOCOL (e.g. grpc), OTEL_EXPORTER_OTLP_ENDPOINT, and OTEL_EXPORTER_OTLP_HEADERS for authentication. [claim:clm_022]
- Claude Code exports metrics as time series via the standard metrics protocol, events via the logs/events protocol, and optionally distributed traces via the traces protocol; exported metrics include cost and token usage. [claim:clm_023]
- Subagents are defined programmatically via the agents parameter and invoked through the Agent tool; including Agent in allowedTools auto-approves invocations without a permission prompt. [claim:clm_024]
- A subagent starts a fresh context whose only parent-to-child channel is the Agent tool prompt string; it does not receive the parent's conversation history, tool results, or system prompt, but does inherit tool definitions and project CLAUDE.md (via settingSources). [claim:clm_025]
- Subagents run in isolated context and can run concurrently; intermediate tool calls and results stay inside the subagent and only its final message returns to the parent (verbatim as the Agent tool result). [claim:clm_026]
- As of Claude Code v2.1.172, subagents can spawn their own subagents; a background subagent five levels below the main agent cannot spawn further, while foreground subagents can spawn at any depth. [claim:clm_027]
- The Agent tool was renamed from Task to Agent in Claude Code v2.1.63; current SDK releases emit Agent in tool_use blocks but still use Task in the system:init tools list and in result.permission_denials, so code must check both. [claim:clm_028]
- Subagents are resumable by capturing the session_id and parsing agentId from the Agent tool result, then passing resume=sessionId; for runs coordinating dozens to hundreds of agents, the docs point to the Workflow tool (available in the TypeScript Agent SDK v0.3.149 and later). [claim:clm_029]
- Effective June 15, 2026, Claude Agent SDK and claude -p usage no longer counts toward a Claude plan's usage limits. [claim:clm_030]
- Monthly Agent SDK credit is $20 for Pro, $100 for Max 5x, and $200 for Max 20x. [claim:clm_031]
- Team Standard seats get a $20/month credit and Team Premium seats get a $100/month credit; Enterprise ranges from $20 (usage-based) to $200 (seat-based Premium seats). [claim:clm_032]
- The credit covers Agent SDK usage in the user's own Python/TypeScript projects, the claude -p non-interactive command, the Claude Code GitHub Actions integration, and third-party apps that authenticate via a Claude subscription. [claim:clm_033]
- Claude Platform accounts using an API key receive no credit; pay-as-you-go billing continues unchanged. [claim:clm_034]
- Once the monthly credit runs out, additional Agent SDK usage flows to usage credits at standard API rates, but only if usage credits are enabled. [claim:clm_035]
- If usage credits aren't enabled, Agent SDK requests stop until the credit refreshes; unused credits do not roll over to the next billing cycle. [claim:clm_036]
- The Claude Agent SDK is positioned as a library that gives developers the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript. [claim:clm_037]
- The SDK authenticates via ANTHROPIC_API_KEY and also supports third-party providers Amazon Bedrock (CLAUDE_CODE_USE_BEDROCK=1), Claude Platform on AWS (CLAUDE_CODE_USE_ANTHROPIC_AWS=1), Google Vertex AI (CLAUDE_CODE_USE_VERTEX=1), and Microsoft Azure (CLAUDE_CODE_USE_FOUNDRY=1). [claim:clm_038]
- Anthropic does not allow third-party developers to offer claude.ai login or rate limits for products built on the Agent SDK unless previously approved, and directs them to API key authentication instead. [claim:clm_039]
- Starting June 15, 2026, Agent SDK and `claude -p` usage on subscription plans draws from a new monthly Agent SDK credit that is separate from interactive usage limits. [claim:clm_040]
- With the Client SDK the developer implements the tool execution loop; the Agent SDK runs the loop autonomously with built-in tool execution. [claim:clm_041]
- The Agent SDK runs the agent loop inside your own process with session state as JSONL on your filesystem, while Managed Agents is a hosted REST API where Anthropic runs the agent and a managed sandbox per session; a common path is to prototype on the SDK then move to Managed Agents for production. [claim:clm_042]
- The latest released version of claude-agent-sdk is 0.2.101, published June 13, 2026 (the same day as this run's as-of date). [claim:clm_043]
- The package's release cadence is near-daily, with multiple versions shipped on consecutive days (0.2.101 on Jun 13, 0.2.100 and 0.2.99 on Jun 12 2026). [claim:clm_044]
- The first published release of the package, version 0.1.0, dates to September 28, 2025, establishing the project's roughly nine-month public history. [claim:clm_045]
- The package requires Python 3.10 or newer. [claim:clm_046]
- PyPI classifies the package as Development Status 3 - Alpha, signaling pre-stable status with possible breaking changes. [claim:clm_047]
- The Claude Code CLI is bundled with the package automatically, so no separate CLI installation is required. [claim:clm_048]
- v0.1.0 was a breaking rebrand of the Claude Code SDK to the Claude Agent SDK, renaming ClaudeCodeOptions to ClaudeAgentOptions. [claim:clm_049]
- As of v0.1.0 the Claude Code system prompt is no longer included by default and filesystem settings/slash commands/subagents are not auto-loaded unless setting_sources is set explicitly. [claim:clm_050]
- v0.1.62 added a top-level skills option to ClaudeAgentOptions accepting 'all', a named list, or [] to suppress all skills. [claim:clm_051]
- Programmatic subagents are defined inline via the agents option (introduced in the v0.1.0 reorganization); v0.1.51 added AgentDefinition fields disallowedTools, maxTurns, and initialPrompt. [claim:clm_052]
- v0.1.60 added subagent transcript helpers list_subagents()/get_subagent_messages() and W3C OpenTelemetry distributed tracing via the claude-agent-sdk[otel] extra. [claim:clm_053]
- v0.2.96 pinned the mcp dependency below 2.0.0 to avoid upstream breaking changes and updated the bundled Claude CLI to 2.1.172. [claim:clm_054]
- The most recent changelog entry is v0.2.101, which bundles Claude CLI version 2.1.177, indicating active sub-1.0 releases with the CLI tracking the ~2.1.17x line. [claim:clm_055]
- The Agent SDK has no programmatic API for registering Skills; they must be created as filesystem SKILL.md artifacts, unlike subagents which can be defined programmatically. [claim:clm_056]
- The `skills` option is a context filter that accepts 'all', a list of skill names, or [] to disable all; it is not a sandbox, since unlisted skills' files remain on disk and reachable via Read and Bash. [claim:clm_057]
- Skills are discovered only through the filesystem setting sources; if settingSources is set explicitly, it must include 'user' or 'project' to keep skill discovery. [claim:clm_058]
- Setting setting_sources=[] disables skill discovery entirely, because it excludes the user and project sources that skills are loaded from. [claim:clm_059]
- Skill metadata is discovered at startup from user and project directories, with full SKILL.md content loaded only when the skill is triggered (progressive disclosure). [claim:clm_060]
- Setting the `skills` option automatically adds the Skill tool to allowedTools; if an explicit tools list is also passed, it must include 'Skill' so Claude can invoke skills. [claim:clm_061]
- The allowed-tools frontmatter field in SKILL.md is only honored by the Claude Code CLI and does not apply via the SDK, where tool access must be controlled through the main allowedTools option. [claim:clm_062]
- total_cost_usd and costUSD are client-side estimates computed locally from a price table bundled at build time, not authoritative billing, and can drift on pricing changes or unrecognized models; authoritative billing is the Usage and Cost API or Claude Console Usage page. [claim:clm_063]
- The Python ResultMessage exposes per-model cost via model_usage and the accumulated total via total_cost_usd plus a cumulative usage dict, while per-step token breakdowns live on each assistant message via message.usage and message.message_id. [claim:clm_064]
- Parallel tool calls in one turn produce multiple assistant messages whose nested BetaMessage shares the same id and identical usage, so you must deduplicate by ID to avoid double-counting tokens. [claim:clm_065]
- Each query() call returns its own total_cost_usd covering only that call; the SDK provides no session-level total, so multi-call sessions must accumulate cost yourself. [claim:clm_066]
- The usage object includes cache_creation_input_tokens (charged at a higher rate) and cache_read_input_tokens (charged at a reduced rate); the Agent SDK uses prompt caching automatically without configuration. [claim:clm_067]
- Setting the ENABLE_PROMPT_CACHING_1H environment variable requests a 1-hour TTL on cache writes, extending the default 5-minute TTL used with API-key auth or Bedrock/Vertex/Foundry. [claim:clm_068]
- Both success and error result messages include usage and total_cost_usd, so failed conversations still report the tokens consumed up to the point of failure. [claim:clm_069]

## Sources

- src_20260613_rib008_00 — claude-agent-sdk - PyPI (Python SDK for Claude Code)
- src_20260613_rib008_01 — claude-agent-sdk-python CHANGELOG.md
- src_20260613_rib008_02 — Agent SDK reference — Python
- src_20260613_rib008_03 — Subagents in the SDK (Claude Docs)
- src_20260613_rib008_04 — Agent Skills in the SDK
- src_20260613_rib008_05 — Agent SDK overview
- src_20260613_rib008_06 — Use the Claude Agent SDK with your Claude plan
- src_20260613_rib008_07 — Track cost and usage
- src_20260613_rib008_08 — Intercept and control agent behavior with hooks
- src_20260613_rib008_09 — Monitoring (OpenTelemetry for Claude Code)

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
