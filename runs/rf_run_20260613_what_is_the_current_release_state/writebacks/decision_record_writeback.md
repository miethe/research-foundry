---
id: mwb_20260622_dr_claude_agent_sdk_readiness_for
evidence_bundle_id: bundle_20260613_intent_research_20260613_what_is_the
target_page: meatywiki/decisions/claude_agent_sdk_readiness_for_research.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260613_what_is_the_current_release_state: clm_025/026 give
  the isolation and final-message contract ideal for stateless map-style decomposition; clm_024 gives
  pro'
key_claims:
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf20
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf17
  include: true
- claim_id: clm_inf18
  include: true
- claim_id: clm_inf19
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_025
  - clm_026
  - clm_024
  - clm_027
  - clm_044
  - clm_055
  - clm_048
  - clm_047
  - clm_063
  - clm_066
  - clm_065
  - clm_inf01
  - clm_inf03
  - clm_inf06
  - clm_inf09
  - clm_inf13
  - clm_002
  - clm_006
  - clm_001
  - clm_056
  - clm_010
  - clm_051
  - clm_057
  - clm_058
  - clm_060
  - clm_052
  - clm_043
  - clm_049
  - clm_028
  - clm_017
  - clm_022
  - clm_023
  - clm_064
  - clm_069
  - clm_021
  - clm_020
  - clm_019
  - clm_040
  - clm_030
  - clm_031
  - clm_067
  - clm_036
  - clm_035
  - clm_034
  - clm_059
  - clm_061
  - clm_062
  - clm_004
  - clm_005
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Claude Agent SDK readiness for Research Foundry: skills API, subagent API, and Python package stability

## Context

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

## Decision

The subagent API is well-suited to RF's bounded single-stage parallel document decomposition: fresh isolated contexts with a prompt-string-only parent channel and final-message-only return give clean fan-out/fan-in, and nested spawning (v2.1.172) is unnecessary for a single stage, so RF can fan out N decomposers and collect N final messages without nesting. [claim:clm_inf04]

## Rationale

- clm_025/026 give the isolation and final-message contract ideal for stateless map-style decomposition; clm_024 gives programmatic invocation; clm_027 shows nesting exists but is not required for a single stage. The shape matches a bounded, single-stage parallel map. [claim:clm_inf04]
- clm_044 (near-daily) and clm_047 (Alpha) make floating ranges hazardous; clm_055/048 show each SDK version bundles a specific CLI version, so pinning the SDK also pins the CLI behavior surface. Exact pinning follows directly. [claim:clm_inf07]
- clm_063 (estimates, not billing, can drift); clm_066 (per-call only, no session total -> accumulate yourself); clm_065 (must dedupe parallel-call usage by ID). Together they prescribe own-accounting plus authoritative reconciliation. [claim:clm_inf11]
- Synthesizes the per-dimension verdicts: subagents/observability/billing favor adoption (clm_inf03/09/13), stability argues for guardrails (clm_inf06), and the absent skills API means no migration there (clm_inf01). The net is conditional go with named conditions. [claim:clm_inf16]
- clm_002 (no SessionStart/SessionEnd Python callbacks), clm_006 (hooks may not fire at max_turns), clm_001 (per-tool hooks available) imply audit must be incremental per-tool-call, not session-terminal. [claim:clm_inf20]
- clm_056 states the SDK has no programmatic registration API for skills; clm_057/058/060 show skills are filesystem SKILL.md artifacts discovered via setting_sources; clm_010/051 show the skills option only filters/selects already-on-disk skills. Together these establish there is nothing to migrate plain-text injection 'to' except a disk-plus-filter mechanism. [claim:clm_inf01]
- clm_056 negates 'native programmatic API'; clm_051 dates the skills option to v0.1.62 (recent); clm_047 (Alpha) and clm_044 (near-daily cadence) negate 'stable'. The conjunction fails the success criterion. [claim:clm_inf02]
- clm_024 (programmatic agents param + Agent tool), clm_025 (documented parent-to-child context boundary), clm_026 (isolated/parallel, final-message-only return), clm_052 (AgentDefinition fields) jointly establish a native, documented subagent API. [claim:clm_inf03]
- clm_025 states the only parent-to-child channel is the Agent tool prompt string (no history/tool results/system prompt); clm_026 confirms intermediates stay inside the child. RF must therefore pack context into the prompt, a direct architectural consequence. [claim:clm_inf05]
- clm_047 (Alpha), clm_043 (0.2.101 pre-1.0), clm_044 (near-daily), clm_049 (breaking rebrand precedent), clm_028 (Task->Agent rename requiring dual-checking) jointly evidence high breaking-change risk. [claim:clm_inf06]
- clm_028 explicitly states the dual-naming inconsistency across surfaces post-rename; failing to check both is a direct correctness bug for any code that inspects tool names. [claim:clm_inf08]
- clm_017/022/023 give OTel metrics/logs/OTLP export including cost+tokens; clm_064 gives per-model/per-step token data; clm_069 ensures even failed runs report usage. Plain-text injection has no comparable native accounting. [claim:clm_inf09]
- clm_021/020 establish inbound TRACEPARENT propagation into SDK sessions and subprocesses; clm_019 flags the whole distributed-tracing feature as beta behind an extra env flag. The capability exists but is beta-gated, hence best-effort. [claim:clm_inf10]
- clm_065 states parallel calls share id/usage and require dedup-by-id; clm_026 confirms RF's decomposition runs subagents in parallel. The over-count consequence follows directly. [claim:clm_inf12]
- clm_040/030 establish the separate-credit decoupling from interactive limits; clm_031 gives the credit amounts; clm_067 shows automatic prompt caching with reduced-rate cache reads. Together they make SDK usage cheaper/decoupled for subscription auth. [claim:clm_inf13]
- clm_036 (requests stop, no rollover when usage credits off); clm_035 (overflow only if usage credits enabled); clm_034 (API-key/pay-as-you-go path is uncapped but gets no credit). The availability hazard and its two mitigations follow directly. [claim:clm_inf14]
- The billing source (basis for clm_030/040) explicitly states no latency/throughput/rate-limit guarantees (recorded in the contradiction log for src_20260613_rib008_06), and no source card supplies latency data; therefore the latency claim cannot be evidenced and is an open item. [claim:clm_inf15]
- clm_058/059 give the discovery toggle via setting_sources; clm_051/061/010 give the skills option and auto-added Skill tool. Disabling (skills=[] or setting_sources=[]) is the symmetric rollback, making the change additive and reversible. [claim:clm_inf17]
- clm_062 states allowed-tools frontmatter is CLI-only and ignored via the SDK; clm_057 confirms the skills filter is not a sandbox. Per-skill restrictions therefore must move to allowedTools or access widens, a direct migration hazard. [claim:clm_inf18]
- clm_004 (deny-priority permission decisions), clm_005 (block/audit/transform), clm_001 (PreToolUse available in Python) give RF a runtime governance gate; prompt injection has no equivalent enforcement point. [claim:clm_inf19]

## Consequences

- RF should pin an exact claude-agent-sdk version (and the bundled Claude CLI it carries, e.g. 0.2.101 -> CLI 2.1.177) rather than a range, because near-daily releases on a pre-1.0 line mean an unpinned dependency can pull a breaking change between any two CI runs. [claim:clm_inf07]
- RF must build its own session-level cost accounting and must not trust SDK cost fields for billing: total_cost_usd is a per-call client-side estimate from a build-time price table (no session total, can drift on pricing/unknown models), so RF should accumulate per-call estimates for telemetry but reconcile spend against the Usage and Cost API. [claim:clm_inf11]
- Recommended verdict is a CONDITIONAL GO (build behind a feature flag): adopt the SDK for its native subagent decomposition, observability, and billing decoupling, but keep RF's plain-text skills injection in place because there is no skills API to migrate to, and gate the adapter behind exact version pinning, dual Agent/Task detection, own cost accounting, and a documented rollback to plain-text mode. [claim:clm_inf16]
- RF should not rely on session-lifecycle or max-turns-terminal hooks for governance-critical audit in Python: SessionStart/SessionEnd are not Python callback hooks and hooks may not fire when an agent hits max_turns, so RF must persist audit state on each PreToolUse/PostToolUse rather than at session close. [claim:clm_inf20]
- No native programmatic skills/resources API exists in the Claude Agent SDK, so RF cannot migrate plain-text skills injection to a registration API; the only SDK-native path is to materialize SKILL.md files on disk and select them through the filesystem-discovered skills context filter. [claim:clm_inf01]
- The skills success criterion ('exposes a stable native skills/resources API') is NOT met: skills are filesystem-only with no registration API, and even the surrounding skills option is recent (v0.1.62) and sits in a pre-1.0 Alpha line, so the answer is no on both 'native API' and 'stable'. [claim:clm_inf02]
- By contrast the parent-child subagent API IS native and documented: subagents are defined programmatically via the agents parameter, invoked through the Agent tool, run in isolated parallel contexts, and return only their final message verbatim to the parent, satisfying the 'documented parent-child subagent API' half of the research question. [claim:clm_inf03]
- The prompt-string-only parent-to-child channel is the main design constraint for RF: because subagents do not receive parent conversation, tool results, or system prompt, RF must serialize each document's full decomposition context into the Agent tool prompt and cannot rely on shared in-conversation state. [claim:clm_inf05]
- Stability is the dominant risk and the strongest argument against building RF's real-mode adapter now: the package is PyPI 'Development Status 3 - Alpha', pre-1.0 (latest 0.2.101), ships near-daily, and has already shipped a breaking rename rebrand (v0.1.0: ClaudeCodeOptions to ClaudeAgentOptions) plus a tool rename (Task to Agent, v2.1.63), so breaking-change risk is high. [claim:clm_inf06]
- Detection code in RF's adapter must check for both 'Agent' and 'Task' tool names because current SDK releases emit 'Agent' in tool_use blocks but still report 'Task' in system:init and result.permission_denials; treating these as a single name will silently break subagent accounting. [claim:clm_inf08]
- Observability is a clear point in favor of migration: the SDK/CLI exports cost and token-usage metrics, logs/events, OTLP-configurable endpoints, and per-model/per-step token breakdowns on result and assistant messages, giving RF governed-run accounting that plain-text prompt injection cannot provide. [claim:clm_inf09]
- RF's distributed tracing requirement is only partly met today: end-to-end trace propagation works because Agent SDK sessions read inbound TRACEPARENT/TRACESTATE and nest under the caller's trace, but the feature is beta and gated behind CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1, so RF should treat cross-process tracing as best-effort, not a guarantee. [claim:clm_inf10]
- For RF's parallel decomposition the per-step token counts must be deduplicated by message ID, because parallel tool calls in one turn emit multiple assistant messages whose nested BetaMessage share one id and identical usage; without dedup RF would over-count decomposition token cost by the parallelism factor. [claim:clm_inf12]
- Billing economics favor migration for subscription-authenticated RF: from June 15 2026 Agent SDK usage draws on a separate monthly credit ($20 Pro / $100 Max 5x / $200 Max 20x) instead of interactive limits, and automatic prompt caching (cache_read charged at a reduced rate) further lowers effective cost versus uncached plain-text prompt injection. [claim:clm_inf13]
- The credit model introduces a hard-stop availability risk RF must design around: if usage credits are not enabled, Agent SDK requests stop once the monthly credit is exhausted and unused credit does not roll over, so a high-volume RF swarm on a subscription plan can be cut off mid-run unless it enables usage-credit overflow or runs on a pay-as-you-go API key. [claim:clm_inf14]
- Latency is the single unmet evidence dimension in the go/no-go: the billing and SDK sources state no latency, throughput, or rate-limit guarantees, so the latency leg of the success criterion cannot be satisfied from the gathered evidence and remains an open validation item before committing the real-mode adapter. [claim:clm_inf15]
- Migration cost from plain-text skills injection to the SDK is low because it is mostly additive, not a rewrite: RF keeps authoring SKILL.md files and simply sets setting_sources to include 'user'/'project' and the skills option ('all' or a named list), which auto-adds the Skill tool; the rollback path is symmetric (set setting_sources=[] or skills=[] to disable discovery and fall back to plain-text). [claim:clm_inf17]
- A correctness pitfall in the skills migration is that the SDK ignores the SKILL.md allowed-tools frontmatter (CLI-only), so any per-skill tool restrictions RF relies on today must be re-expressed through the SDK's main allowedTools option or they silently grant broader tool access than intended. [claim:clm_inf18]
- RF can enforce governance gates natively through the Python hook surface: PreToolUse hooks return deny/defer/ask/allow with deny taking absolute precedence, enabling RF's policy engine and secret-scanning to block dangerous tool calls and audit-log every call, which is a capability plain-text prompt injection cannot enforce at runtime. [claim:clm_inf19]

## Links

- [[claim:clm_025]]
- [[claim:clm_026]]
- [[claim:clm_024]]
- [[claim:clm_027]]
- [[claim:clm_044]]
- [[claim:clm_055]]
- [[claim:clm_048]]
- [[claim:clm_047]]
- [[claim:clm_063]]
- [[claim:clm_066]]
- [[claim:clm_065]]
- [[claim:clm_inf01]]
- [[claim:clm_inf03]]
- [[claim:clm_inf06]]
- [[claim:clm_inf09]]
- [[claim:clm_inf13]]
- [[claim:clm_002]]
- [[claim:clm_006]]
- [[claim:clm_001]]
- [[claim:clm_056]]
- [[claim:clm_010]]
- [[claim:clm_051]]
- [[claim:clm_057]]
- [[claim:clm_058]]
- [[claim:clm_060]]
- [[claim:clm_052]]
- [[claim:clm_043]]
- [[claim:clm_049]]
- [[claim:clm_028]]
- [[claim:clm_017]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_064]]
- [[claim:clm_069]]
- [[claim:clm_021]]
- [[claim:clm_020]]
- [[claim:clm_019]]
- [[claim:clm_040]]
- [[claim:clm_030]]
- [[claim:clm_031]]
- [[claim:clm_067]]
- [[claim:clm_036]]
- [[claim:clm_035]]
- [[claim:clm_034]]
- [[claim:clm_059]]
- [[claim:clm_061]]
- [[claim:clm_062]]
- [[claim:clm_004]]
- [[claim:clm_005]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
