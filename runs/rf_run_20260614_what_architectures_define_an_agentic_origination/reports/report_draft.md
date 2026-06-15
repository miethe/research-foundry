---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_architectures_define_an_agentic_origination
title: 'Agentic origination layers: intent routing architecture & trade-offs'
intent_id: intent_research_20260614_what_architectures_define_an_agentic_origination
evidence_bundle_id: pending
created_at: '2026-06-14T15:44:23-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Executive summary

Across the surveyed systems the agentic origination layer converges on a three-stage pipeline (intent ingestion and normalization, route/dispatch decision, and a typed execution package handed to the target harness), with Bedrock's per-collaborator 'Collaboration instructions', the OpenAI Agents SDK's input_type schema, and Microsoft Agent Framework's declarative YAML each instantiating one stage of that same loop. **Inference:** [claim:clm_inf01]
Rule-based routing is the most cost-predictable and lowest-latency strategy (deterministic, zero added model tokens, sub-millisecond decisions) but the least maintainable as intent variety grows; it is the correct default for the small, well-bounded route set of research-intent dispatch where intents fall into a handful of stable classes. **Inference:** [claim:clm_inf02]
LLM intent extraction offers the highest accuracy on novel or ambiguous research phrasing and the lowest maintenance burden (new intents need no new rules or training data), but it is the least cost-predictable and highest-latency option because every routing decision incurs a model generation that must itself be budgeted and capped. **Inference:** [claim:clm_inf03]
An embedding/ML classifier (Semantic Router style) occupies the middle of the matrix: near-rule-based latency and cost-predictability (one cheap embedding call, no generation) with better generalization than hand-written rules, at the cost of needing labeled example utterances per route and periodic re-tuning, making it the strongest single-strategy choice once the research-intent route set exceeds what rules can cleanly cover. **Inference:** [claim:clm_inf04]
For Research Foundry's intent->control-plane->route loop the recommended design is a hybrid cascade — a deterministic rule table first, an embedding classifier (Semantic Router) for the unmatched residue, and LLM intent extraction only as a fallback for low-confidence cases — which preserves rule-based cost-predictability for the common case while reserving the expensive LLM decision for the genuinely ambiguous minority. **Inference:** [claim:clm_inf05]
Semantic Router maps most cleanly onto Research Foundry's intent->route decision node, the OpenAI Agents SDK handoff/triage pattern onto RF's route->dispatch hand-off with a typed packet, and LiteLLM's Router onto RF's cost-cap/model-profile selection layer — making these three the highest-fit prior-art systems for RF's loop, with Bedrock supervisor and LangGraph supervisor/swarm as secondary references for the multi-agent execution tier. **Inference:** [claim:clm_inf13]

## Routing-strategy comparison matrix

Each row's score, per axis, with its grounding inference.

| Strategy | Accuracy | Cost-predictability | Latency | Maintainability | Evidence |
|----------|----------|---------------------|---------|-----------------|----------|
| Rule-based routing | Lowest on novel phrasing; exact on bounded classes | Highest; deterministic, zero added model tokens | Lowest; sub-millisecond decisions | Lowest as intent variety grows | **Inference:** [claim:clm_inf02] |
| LLM intent extraction | Highest on novel/ambiguous research phrasing | Lowest; each decision is a billable generation | Highest; a model generation per decision | Highest; new intents need no rules or training data | **Inference:** [claim:clm_inf03] |
| Embedding/ML classifier | Better generalization than rules; mid-tier | Near-rule-based; one cheap embedding call, no generation | Near-rule-based; no generation | Mid; needs labeled utterances per route plus periodic re-tuning | **Inference:** [claim:clm_inf04] |

The routing workflow classifies an input and directs it to a specialized followup task, with classification handled either by an LLM or by a more traditional classification model/algorithm. [claim:clm_024]
All latency and cost advantages claimed for embedding/semantic routing over LLM extraction in this evidence base are vendor-asserted (Aurelio AI's 'milliseconds vs seconds' and Bedrock's 'routing reduces latency') and lack independent benchmarks, so Research Foundry should treat them as design hypotheses to validate with its own telemetry rather than as settled quantitative facts when scoring the routing matrix. **Inference:** [claim:clm_inf16]

### Supporting source-card evidence per axis

The matrix scores rest on the following source-card facts about how the surveyed systems behave.

| Source-card fact (abridged) | Strategy axis | Evidence |
|-----------------------------|---------------------------|----------|
| Anthropic routes easy/common questions to cheaper models (Claude Haiku) and hard/unusual questions to more capable models (Claude Sonnet) to optimize cost and performance | LLM-extraction accuracy/cost tiering | [claim:clm_025] |
| Aurelio AI: Semantic Router decides in milliseconds rather than seconds and avoids expensive LLM inference | Embedding-classifier latency/cost | [claim:clm_002] |
| Routing decisions made in semantic vector space using embeddings rather than slow LLM generations | Embedding-classifier latency | [claim:clm_066] |
| Routes defined declaratively as named objects with example utterances; query matched by semantic similarity | Embedding-classifier maintenance cost | [claim:clm_067] |
| Orchestrating flow via code rather than the LLM is more deterministic and predictable in speed, cost, performance | Rule-based cost-predictability | [claim:clm_035] |
| Deployments prioritized via an order parameter; higher-priority levels exhausted before fallbacks | Rule-based determinism | [claim:clm_033] |
| The augmented LLM generates its own queries, selects tools, and decides what to retain | LLM-extraction generalization | [claim:clm_023] |

## Reference origination-layer architecture

Anthropic defines workflows as systems where LLMs and tools are orchestrated through predefined code paths, and agents as systems where LLMs dynamically direct their own processes and tool usage. [claim:clm_022]

### Stage 1 — intent ingestion and the routing decision

Semantic Router is positioned as a decision-making layer for LLMs/agents that routes requests by meaning in semantic vector space instead of waiting on LLM generation for tool-use decisions. [claim:clm_001]
A supervisor agent can be configured either to coordinate responses from collaborator agents or to route information to the appropriate collaborator to send the final response. [claim:clm_071]
Each collaborator's 'Collaboration instructions' tell the supervisor when that collaborator should be used. [claim:clm_075]
Beyond static classification, the package supports 'Dynamic Routes' that generate parameters and trigger function calls. [claim:clm_068]

### Stage 2 — cost-cap decision point

The most direct mechanism to enforce a hard per-intent cost cap is to bind a model-profile selection rule (e.g. Haiku-class for common intents, Sonnet-class for hard ones) at the routing boundary, exactly mirroring LiteLLM's lowest-cost routing which only considers deployments already under their rpm/tpm limits — turning the budget ceiling into a precondition of dispatch rather than a post-hoc check. **Inference:** [claim:clm_inf06]

| LiteLLM mechanism (abridged) | Role at the cost-cap decision point | Evidence |
|------------------------------|--------------------------------------|----------|
| Cost-based routing picks, among healthy deployments under rpm/tpm limits, the lowest-cost model via the cost map (unknown defaults to $1) | Budget ceiling as admission filter | [claim:clm_030] |
| usage-based-routing-v2 routes to the deployment with lowest TPM this minute, tracking TPM/RPM in Redis | Per-minute usage accounting | [claim:clm_028] |
| Default weighted simple-shuffle pick selects by configured rpm/tpm weighting | Default weighted dispatch | [claim:clm_027] |
| Latency-based routing picks lowest response time; least-busy picks fewest ongoing calls | Latency/load-aware selection | [claim:clm_029] |

Token-cost predictability at the routing boundary requires bounding the input the routing decision itself sees, and the surveyed SDKs already supply the primitives: the OpenAI Agents SDK input_filter (and prebuilt handoff_filters that strip tool calls) and Bedrock Payload Referencing both cut the tokens that travel with a dispatch, so estimable cost depends on filtering history before, not after, the route is chosen. **Inference:** [claim:clm_inf07]
An input_filter controls which conversation history the receiving agent sees, with common patterns (such as removing all tool calls) prebuilt in agents.extensions.handoff_filters. [claim:clm_045]
Payload Referencing lets supervisor agents reference linked data instead of embedding it in every request, reducing data transfer and lowering operational costs. [claim:clm_049]

### Stage 3 — execution package and dispatch-mechanism decision point

The minimum metadata an intent must carry for downstream agents to act without re-deriving context is the bundle the surveyed systems already standardize: a route/specialization label, a typed task-description argument, a curated (filtered) slice of conversation/source history, and an agent-name/provenance tag — mirroring Bedrock's task description, the SDK input_type, input_filter history, and with_agent_name tagging respectively. **Inference:** [claim:clm_inf11]
input_type describes the handoff tool-call arguments; the SDK exposes that schema to the model as the tool's parameters, validates the returned JSON locally, and passes the parsed value to on_handoff. [claim:clm_043]
with_agent_name() attaches formatted agent-name tags to messages passed to and from the model so a multi-agent history stays coherent and the supervisor can track which agent a message belongs to. [claim:clm_064]
Handoff tools can be customized by changing the tool name and/or description and by adding tool-call arguments for the LLM to populate, such as a task description for the next agent. [claim:clm_056]

| Dispatch mechanism | Strengths | Weaknesses | Best fit | Evidence |
|--------------------|-----------|-----------|----------|----------|
| In-process Agent SDK call | Lowest latency, shared memory | Less isolation and observability than out-of-process | Low-latency intra-platform hot path | **Inference:** [claim:clm_inf08] |
| Serialized execution-packet (out-of-process request) | More deterministic, isolated, observable | Adds serialization and process-spawn latency | Separate or sandboxed target harness | **Inference:** [claim:clm_inf08] |
| CLI subprocess exec | Maximizes isolation and harness-agnosticism; strongest observability via stdout/stderr and exit codes | Slowest and least type-safe of the three | Cross-tool dispatch to harnesses with no native SDK | **Inference:** [claim:clm_inf09] |

A hybrid execution-packet-over-SDK model — author a typed packet, then bind it to whichever transport (in-process SDK, subprocess CLI, or remote API request) the target harness supports — is the best fit for Research Foundry because it decouples the routing/packaging decision from the dispatch transport, and Microsoft Agent Framework's declarative YAML-loaded-with-one-API-call is a concrete existence proof of that decoupling. **Inference:** [claim:clm_inf10]
Agents and workflows can be defined declaratively in version-controlled YAML files (instructions, tools, memory, orchestration topology) and loaded/run with a single API call. [claim:clm_021]
Deployment is done by setting up the supervisor agent to make an InvokeAgent request. [claim:clm_077]

## Prior-art systems mapped to RF design choices

| Prior-art system | RF design choice it maps to | Evidence |
|------------------|-----------------------------|----------|
| Semantic Router (Aurelio AI) | RF's intent->route decision node | **Inference:** [claim:clm_inf13] |
| OpenAI Agents SDK handoff/triage | RF's route->dispatch hand-off with a typed packet | **Inference:** [claim:clm_inf13] |
| LiteLLM Router | RF's cost-cap / model-profile selection layer | **Inference:** [claim:clm_inf13] |
| Amazon Bedrock multi-agent supervisor | Secondary reference for the multi-agent execution tier | **Inference:** [claim:clm_inf13] |
| LangGraph supervisor / swarm | Secondary reference for the multi-agent execution tier | **Inference:** [claim:clm_inf13] |

### Semantic Router as the decision node

Semantic Router positions itself as a fast decision-making/routing layer that sits in front of LLMs and agents. [claim:clm_065]
Semantic Router supports three execution modes: cloud-based (API embeddings), hybrid (local embeddings with API-based LLMs), and fully local with models like Llama and Mistral. [claim:clm_003]
Semantic Router can run fully locally using a local encoder (HuggingFaceEncoder) and a local LLM (LlamaCppLLM), avoiding hosted-API dependencies. [claim:clm_069]
The library ships pluggable encoder integrations (Cohere, OpenAI, Hugging Face, FastEmbed, and multi-modal encoders) and integrates with vector databases such as Pinecone and Qdrant. [claim:clm_070]
The docs note Semantic Router v0.1 is available and point migrating users from earlier versions to a migration guide. [claim:clm_006]

### OpenAI Agents SDK as the dispatch hand-off

An Agents SDK agent is an LLM equipped with instructions, tools, and handoffs, letting it autonomously plan, take actions, and delegate to sub-agents for open-ended tasks. [claim:clm_034]
In the handoffs pattern, a triage agent routes the conversation to a specialist, and that specialist becomes the active agent for the rest of the turn. [claim:clm_038]
Handoffs are exposed to the LLM as tools, with a handoff to an agent named 'Refund Agent' surfacing as a tool named transfer_to_refund_agent. [claim:clm_041]
An agent's handoffs param accepts either an Agent directly or a Handoff object, and the handoff() function exposes parameters including agent, tool_name_override, tool_description_override, on_handoff, input_type, input_filter, and is_enabled. [claim:clm_042]
Orchestrating agent flow via code rather than the LLM makes tasks more deterministic and predictable in speed, cost, and performance. [claim:clm_035]
In the agents-as-tools (manager) pattern, a manager agent keeps control of the conversation and calls specialist agents through Agent.as_tool(). [claim:clm_037]

### LiteLLM Router as the cost-cap layer

LiteLLM cooldowns let you cap how many times a deployment may fail within a minute before it is taken out of rotation (cooled down) for a minute. [claim:clm_031]
On retries, LiteLLM applies exponential backoff specifically for RateLimitError, while retrying immediately for generic errors. [claim:clm_032]

### Bedrock and LangGraph as the execution-tier references

Multi-agent collaboration for Amazon Bedrock reached general availability on March 10, 2025, letting developers build networks of specialized agents coordinated by a supervisor agent. [claim:clm_046]
A supervisor agent can associate a maximum of 10 collaborator agents. [claim:clm_073]
The GA release adds agent monitoring and observability features to track and optimize agent interactions. [claim:clm_051]
create_supervisor() is the package's primary entry point for building a multi-agent supervisor that manages a list of worker agents under a single supervising language model. [claim:clm_059]
In a swarm architecture agents dynamically hand off control to one another based on their specializations, with no central coordinator. [claim:clm_053]

## Analysis and derivation

### Why a supervisor topology, not a swarm

A central-supervisor topology (Bedrock supervisor-with-routing, LangGraph create_supervisor) is the better fit than a decentralized swarm for Research Foundry's origination layer because RF needs a single auditable point that enforces the cost cap, emits routing telemetry, and validates the dispatched packet — control that a coordinator-free swarm, which hands off peer-to-peer, structurally cannot centralize. **Inference:** [claim:clm_inf17]
In the console the two modes are explicit options: 'Supervisor' coordinates collaborator responses, while 'Supervisor with routing' routes information to the appropriate collaborator to send the final response. [claim:clm_074]
Assigning the supervisor the routing task reduces latency. [claim:clm_072]
create_forward_message_tool() lets the supervisor forward a worker message by name rather than rewriting it, so the central supervisor mediates communication while avoiding information loss and token cost. [claim:clm_063]

### Scale ceiling and the case for two levels

Bedrock's documented hard limit of 10 collaborator agents per supervisor is an architectural signal that flat supervisor routing does not scale to large route sets, implying Research Foundry should plan a two-level origination layer (a coarse rule/embedding router selecting a route family, then a finer dispatcher within it) once its distinct research-intent routes approach the low tens. **Inference:** [claim:clm_inf18]
In the orchestrator-workers workflow a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes results, with subtasks determined at runtime by the orchestrator rather than pre-defined (the key difference from parallelization). [claim:clm_026]
The two patterns are composable: a triage agent can hand off to a specialist that itself still calls other agents as tools for narrow subtasks. [claim:clm_039]

### Failure modes and mitigations

The dominant failure mode of LLM intent extraction is runaway cost from unbounded routing generations plus prompt-injection at the routing boundary (a crafted intent steering the route), and the recommended mitigation stack is exactly the surveyed reliability primitives: a hard per-intent token/cost cap, LiteLLM-style cooldowns and exponential backoff, and local schema validation of the dispatched packet before any harness is invoked. **Inference:** [claim:clm_inf14]
Rule-based and embedding-classifier routing share a distinct failure mode — silent misclassification of out-of-distribution intents (a rule gap or a query unlike any example utterance) — whose recommended mitigation is a confidence threshold that escalates low-score decisions to an LLM extraction fallback, which is precisely why a hybrid cascade dominates any single strategy for an open-ended research-intent space. **Inference:** [claim:clm_inf15]

### Telemetry as a first-class layer

Routing decisions cannot be tuned after the fact without telemetry capturing the chosen route, the decision confidence/score, the model profile and token cost incurred, and the eventual task outcome; Bedrock's added agent monitoring/observability and LiteLLM's per-minute TPM/RPM tracking show this telemetry is treated as a first-class layer, not an afterthought, in production routing systems. **Inference:** [claim:clm_inf12]

### State and structure of the dispatch package

Structured state management uses predefined Pydantic BaseModel schemas to enforce consistency, type safety, validation, and auto-completion across the workflow. [claim:clm_014]
In unstructured state management, all state lives in the Flow's state attribute, allowing attributes to be added or modified on the fly without a strict schema. [claim:clm_013]
The on_handoff callback receives the agent context and can optionally receive LLM-generated input, with the input data controlled by the input_type parameter. [claim:clm_044]
Multi-turn state requires always compiling the swarm with a checkpointer (e.g. workflow.compile(checkpointer=checkpointer)). [claim:clm_058]
Checkpointing and hydration let long-running agentic processes survive interruptions. [claim:clm_019]

## Recommendations and decision rules

For Research Foundry's intent->control-plane->route loop the recommended design is a hybrid cascade — a deterministic rule table first, an embedding classifier (Semantic Router) for the unmatched residue, and LLM intent extraction only as a fallback for low-confidence cases — which preserves rule-based cost-predictability for the common case while reserving the expensive LLM decision for the genuinely ambiguous minority. **Inference:** [claim:clm_inf05]
The most direct mechanism to enforce a hard per-intent cost cap is to bind a model-profile selection rule (e.g. Haiku-class for common intents, Sonnet-class for hard ones) at the routing boundary, exactly mirroring LiteLLM's lowest-cost routing which only considers deployments already under their rpm/tpm limits — turning the budget ceiling into a precondition of dispatch rather than a post-hoc check. **Inference:** [claim:clm_inf06]
A hybrid execution-packet-over-SDK model — author a typed packet, then bind it to whichever transport (in-process SDK, subprocess CLI, or remote API request) the target harness supports — is the best fit for Research Foundry because it decouples the routing/packaging decision from the dispatch transport, and Microsoft Agent Framework's declarative YAML-loaded-with-one-API-call is a concrete existence proof of that decoupling. **Inference:** [claim:clm_inf10]
A central-supervisor topology (Bedrock supervisor-with-routing, LangGraph create_supervisor) is the better fit than a decentralized swarm for Research Foundry's origination layer because RF needs a single auditable point that enforces the cost cap, emits routing telemetry, and validates the dispatched packet — control that a coordinator-free swarm, which hands off peer-to-peer, structurally cannot centralize. **Inference:** [claim:clm_inf17]
Bedrock's documented hard limit of 10 collaborator agents per supervisor is an architectural signal that flat supervisor routing does not scale to large route sets, implying Research Foundry should plan a two-level origination layer (a coarse rule/embedding router selecting a route family, then a finer dispatcher within it) once its distinct research-intent routes approach the low tens. **Inference:** [claim:clm_inf18]
All latency and cost advantages claimed for embedding/semantic routing over LLM extraction in this evidence base are vendor-asserted (Aurelio AI's 'milliseconds vs seconds' and Bedrock's 'routing reduces latency') and lack independent benchmarks, so Research Foundry should treat them as design hypotheses to validate with its own telemetry rather than as settled quantitative facts when scoring the routing matrix. **Inference:** [claim:clm_inf16]

### Forward-looking design bets

Within the next 1-2 years the prevailing pattern for agentic origination layers will be a declarative, version-controlled routing policy (intent classes, model-profile/budget bindings, and dispatch transport per route in YAML) loaded as data rather than coded, extending Microsoft Agent Framework's YAML-topology approach from agent definitions to the routing decision itself. **Speculation:** [claim:clm_spec01]
As routing-LLM and embedding-model prices continue to fall, the cost gap that today justifies a rules-first cascade will narrow to the point where an embedding-classifier-first design (rules reserved only for a few hard policy/compliance routes) becomes the pragmatic default for research-intent origination, because the classifier's generalization advantage will outweigh its shrinking per-decision cost penalty. **Speculation:** [claim:clm_spec02]

## Supplementary findings

CrewAI Flows is an event-driven feature for building structured, multi-step AI workflows that orchestrate CrewAI capabilities. [claim:clm_008]
The @start() decorator marks entry points, and all satisfied @start() methods execute (often in parallel) when the Flow begins or resumes. [claim:clm_009]
A start can be unconditional, gated on a prior method or router label, or controlled by a callable condition. [claim:clm_010]
The @listen() decorator marks a method as a listener that runs automatically when the specified upstream task emits an output. [claim:clm_011]
The @router() decorator defines conditional routing logic based on a method's output, dynamically controlling which downstream routes execute. [claim:clm_012]
Microsoft Agent Framework reached version 1.0 GA for both .NET and Python on April 3, 2026 as a production-ready release with stable APIs and long-term support. [claim:clm_015]
Agent Framework was built to unify Semantic Kernel's enterprise foundations with AutoGen's orchestrations into a single open-source SDK. [claim:clm_016]
The framework supports five multi-agent orchestration patterns: sequential, concurrent, handoff, group chat, and Magentic-One. [claim:clm_017]
A graph-based workflow engine composes agents and functions into deterministic, repeatable processes and is now marked stable. [claim:clm_018]
Agent Framework ships first-party service connectors for multiple model providers including Microsoft Foundry, Azure OpenAI, OpenAI, Anthropic Claude, Amazon Bedrock, Google Gemini, and Ollama. [claim:clm_020]
Code-based orchestration patterns include using structured outputs, chaining one agent's output into the next agent's input, running an agent in a while loop, and running multiple agents in parallel via primitives like asyncio.gather. [claim:clm_036]
A handoff lets one agent delegate a task to another agent, useful when different agents specialize in distinct areas. [claim:clm_040]
The capability targets more complex, multi-step workflows and is positioned to scale AI-driven applications. [claim:clm_047]
Inline Agents let teams dynamically adjust agent roles and behaviors at runtime to make workflows more adaptable. [claim:clm_048]
Multi-agent collaboration adds CloudFormation and CDK support so teams of agents can be authored as reusable templates shared across accounts in an organization. [claim:clm_050]
Multi-agent collaboration is available in all AWS Regions where Amazon Bedrock is supported. [claim:clm_052]
The optional 'Enable conversation history' setting shares full current-session context (user input and supervisor response from each turn) with the collaborator agent. [claim:clm_076]
The swarm remembers which agent was last active so that subsequent interactions resume the multi-turn conversation with that same agent. [claim:clm_054]
By default, swarm agents use handoff tools built with the prebuilt create_handoff_tool helper. [claim:clm_055]
create_swarm() builds the workflow from a list of agents and accepts a default_active_agent argument (e.g. create_swarm([alice, bob], default_active_agent="Alice")). [claim:clm_057]
The supervisor manages a list of agents, where each agent can be a LangGraph CompiledStateGraph, a functional-API workflow, or any other Pregel object. [claim:clm_060]
create_handoff_tool() creates a tool that hands off control to a named worker agent (the tool is named transfer_to_<agent_name> by default). [claim:clm_061]
create_handoff_back_messages() builds an (AIMessage, ToolMessage) pair added to the message history when control returns from a worker to the supervisor, implementing the return-communication leg of delegation. [claim:clm_062]
Semantic Router integrates with the Pinecone and Qdrant vector stores for persistence of route sets. [claim:clm_004]
Semantic Router supports multiple embedding integrations including Cohere, OpenAI, Hugging Face, and FastEmbed. [claim:clm_005]
Semantic Router can route based on image content (multi-modal) and can run entirely on a local machine with no API dependencies. [claim:clm_007]

## Open questions

- What is RF's measured per-decision latency and cost for an embedding classifier versus LLM extraction, given that the vendor latency/cost claims lack independent benchmarks? [claim:clm_inf16]
- At what count of distinct research-intent routes does flat supervisor routing hit its fan-out ceiling and require the two-level hierarchy? [claim:clm_inf18]
- Will the declining cost of routing-LLM and embedding models flip the optimal cascade ordering from rules-first to classifier-first within the 1-2 year horizon? [claim:clm_spec02]
- Will routing policy itself become declarative version-controlled data rather than code, as the YAML-topology pattern extends from agent definitions to the routing decision? [claim:clm_spec01]

## Sources

- src_20260614_rib026_11: Semantic Router — Introduction (Aurelio AI official docs)
- src_20260614_rib026_08: Flows — CrewAI Documentation
- src_20260614_rib026_07: Microsoft Agent Framework Version 1.0
- src_20260614_rib026_00: Building Effective AI Agents
- src_20260614_rib026_09: Router - Load Balancing | liteLLM
- src_20260614_rib026_02: Agent orchestration — OpenAI Agents SDK
- src_20260614_rib026_01: Handoffs — OpenAI Agents SDK
- src_20260614_rib026_06: Amazon Bedrock now supports multi-agent collaboration
- src_20260614_rib026_04: langgraph-swarm-py (LangGraph Multi-Agent Swarm)
- src_20260614_rib026_03: LangGraph Multi-Agent Supervisor (langgraph-supervisor reference)
- src_20260614_rib026_10: aurelio-labs/semantic-router — README (official repo)
- src_20260614_rib026_05: Create multi-agent collaboration - Amazon Bedrock User Guide
