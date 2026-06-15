---
id: mwb_20260614_agentic_origination_layers_intent_routing_archit
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_architectures_defi
target_page: meatywiki/sources/agentic_origination_layers_intent_routing_archit.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_architectures_define_an_agentic_origination:
  77 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
links:
  source_cards:
  - src_20260614_rib026_00
  - src_20260614_rib026_01
  - src_20260614_rib026_02
  - src_20260614_rib026_03
  - src_20260614_rib026_04
  - src_20260614_rib026_05
  - src_20260614_rib026_06
  - src_20260614_rib026_07
  - src_20260614_rib026_08
  - src_20260614_rib026_09
  - src_20260614_rib026_10
  - src_20260614_rib026_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Agentic origination layers: intent routing architecture & trade-offs

## Summary

Source note distilled from research run rf_run_20260614_what_architectures_define_an_agentic_origination: 77 supported claim(s) across 12 source card(s).

## Key claims

- Semantic Router is positioned as a decision-making layer for LLMs/agents that routes requests by meaning in semantic vector space instead of waiting on LLM generation for tool-use decisions. [claim:clm_001]
- Aurelio AI claims Semantic Router makes routing decisions in milliseconds rather than seconds and avoids expensive LLM inference for simple routing tasks. [claim:clm_002]
- Semantic Router supports three execution modes: cloud-based (API embeddings), hybrid (local embeddings with API-based LLMs), and fully local with models like Llama and Mistral. [claim:clm_003]
- Semantic Router integrates with the Pinecone and Qdrant vector stores for persistence of route sets. [claim:clm_004]
- Semantic Router supports multiple embedding integrations including Cohere, OpenAI, Hugging Face, and FastEmbed. [claim:clm_005]
- The docs note Semantic Router v0.1 is available and point migrating users from earlier versions to a migration guide. [claim:clm_006]
- Semantic Router can route based on image content (multi-modal) and can run entirely on a local machine with no API dependencies. [claim:clm_007]
- CrewAI Flows is an event-driven feature for building structured, multi-step AI workflows that orchestrate CrewAI capabilities. [claim:clm_008]
- The @start() decorator marks entry points, and all satisfied @start() methods execute (often in parallel) when the Flow begins or resumes. [claim:clm_009]
- A start can be unconditional, gated on a prior method or router label, or controlled by a callable condition. [claim:clm_010]
- The @listen() decorator marks a method as a listener that runs automatically when the specified upstream task emits an output. [claim:clm_011]
- The @router() decorator defines conditional routing logic based on a method's output, dynamically controlling which downstream routes execute. [claim:clm_012]
- In unstructured state management, all state lives in the Flow's state attribute, allowing attributes to be added or modified on the fly without a strict schema. [claim:clm_013]
- Structured state management uses predefined Pydantic BaseModel schemas to enforce consistency, type safety, validation, and auto-completion across the workflow. [claim:clm_014]
- Microsoft Agent Framework reached version 1.0 GA for both .NET and Python on April 3, 2026 as a production-ready release with stable APIs and long-term support. [claim:clm_015]
- Agent Framework was built to unify Semantic Kernel's enterprise foundations with AutoGen's orchestrations into a single open-source SDK. [claim:clm_016]
- The framework supports five multi-agent orchestration patterns: sequential, concurrent, handoff, group chat, and Magentic-One. [claim:clm_017]
- A graph-based workflow engine composes agents and functions into deterministic, repeatable processes and is now marked stable. [claim:clm_018]
- Checkpointing and hydration let long-running agentic processes survive interruptions. [claim:clm_019]
- Agent Framework ships first-party service connectors for multiple model providers including Microsoft Foundry, Azure OpenAI, OpenAI, Anthropic Claude, Amazon Bedrock, Google Gemini, and Ollama. [claim:clm_020]
- Agents and workflows can be defined declaratively in version-controlled YAML files (instructions, tools, memory, orchestration topology) and loaded/run with a single API call. [claim:clm_021]
- Anthropic defines workflows as systems where LLMs and tools are orchestrated through predefined code paths, and agents as systems where LLMs dynamically direct their own processes and tool usage. [claim:clm_022]
- The foundational building block of agentic systems is an 'augmented LLM' enhanced with retrieval, tools, and memory, which the model can actively use by generating its own queries, selecting tools, and deciding what to retain. [claim:clm_023]
- The routing workflow classifies an input and directs it to a specialized followup task, with classification handled either by an LLM or by a more traditional classification model/algorithm. [claim:clm_024]
- Anthropic gives a routing example of sending easy/common questions to smaller cost-efficient models like Claude Haiku and hard/unusual questions to more capable models like Claude Sonnet to optimize for cost and performance. [claim:clm_025]
- In the orchestrator-workers workflow a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes results, with subtasks determined at runtime by the orchestrator rather than pre-defined (the key difference from parallelization). [claim:clm_026]
- LiteLLM's default and production-recommended routing strategy is the weighted simple-shuffle pick, which selects a deployment based on its configured requests-per-minute (rpm) or tokens-per-minute (tpm) weighting. [claim:clm_027]
- The usage-based-routing-v2 strategy routes to the deployment with the lowest TPM usage for the current minute, using Redis in production to track TPM/RPM usage across multiple deployments. [claim:clm_028]
- Latency-based routing picks the deployment with the lowest response time, while least-busy routing picks the deployment handling the fewest ongoing calls. [claim:clm_029]
- Cost-based routing selects, among healthy deployments under their rpm/tpm limits, the one with the lowest cost by checking each deployment's model against LiteLLM's cost map (defaulting unknown deployments to a $1 cost). [claim:clm_030]
- LiteLLM cooldowns let you cap how many times a deployment may fail within a minute before it is taken out of rotation (cooled down) for a minute. [claim:clm_031]
- On retries, LiteLLM applies exponential backoff specifically for RateLimitError, while retrying immediately for generic errors. [claim:clm_032]
- Deployments can be prioritized via an order parameter (lower = higher priority); the router exhausts higher-priority order levels in sequence before falling through to any configured cross-group fallbacks. [claim:clm_033]
- An Agents SDK agent is an LLM equipped with instructions, tools, and handoffs, letting it autonomously plan, take actions, and delegate to sub-agents for open-ended tasks. [claim:clm_034]
- Orchestrating agent flow via code rather than the LLM makes tasks more deterministic and predictable in speed, cost, and performance. [claim:clm_035]
- Code-based orchestration patterns include using structured outputs, chaining one agent's output into the next agent's input, running an agent in a while loop, and running multiple agents in parallel via primitives like asyncio.gather. [claim:clm_036]
- In the agents-as-tools (manager) pattern, a manager agent keeps control of the conversation and calls specialist agents through Agent.as_tool(). [claim:clm_037]
- In the handoffs pattern, a triage agent routes the conversation to a specialist, and that specialist becomes the active agent for the rest of the turn. [claim:clm_038]
- The two patterns are composable: a triage agent can hand off to a specialist that itself still calls other agents as tools for narrow subtasks. [claim:clm_039]
- A handoff lets one agent delegate a task to another agent, useful when different agents specialize in distinct areas. [claim:clm_040]
- Handoffs are exposed to the LLM as tools, with a handoff to an agent named 'Refund Agent' surfacing as a tool named transfer_to_refund_agent. [claim:clm_041]
- An agent's handoffs param accepts either an Agent directly or a Handoff object, and the handoff() function exposes parameters including agent, tool_name_override, tool_description_override, on_handoff, input_type, input_filter, and is_enabled. [claim:clm_042]
- input_type describes the handoff tool-call arguments; the SDK exposes that schema to the model as the tool's parameters, validates the returned JSON locally, and passes the parsed value to on_handoff. [claim:clm_043]
- The on_handoff callback receives the agent context and can optionally receive LLM-generated input, with the input data controlled by the input_type parameter. [claim:clm_044]
- An input_filter controls which conversation history the receiving agent sees, with common patterns (such as removing all tool calls) prebuilt in agents.extensions.handoff_filters. [claim:clm_045]
- Multi-agent collaboration for Amazon Bedrock reached general availability on March 10, 2025, letting developers build networks of specialized agents coordinated by a supervisor agent. [claim:clm_046]
- The capability targets more complex, multi-step workflows and is positioned to scale AI-driven applications. [claim:clm_047]
- Inline Agents let teams dynamically adjust agent roles and behaviors at runtime to make workflows more adaptable. [claim:clm_048]
- Payload Referencing lets supervisor agents reference linked data instead of embedding it in every request, reducing data transfer and lowering operational costs. [claim:clm_049]
- Multi-agent collaboration adds CloudFormation and CDK support so teams of agents can be authored as reusable templates shared across accounts in an organization. [claim:clm_050]
- The GA release adds agent monitoring and observability features to track and optimize agent interactions. [claim:clm_051]
- Multi-agent collaboration is available in all AWS Regions where Amazon Bedrock is supported. [claim:clm_052]
- In a swarm architecture agents dynamically hand off control to one another based on their specializations, with no central coordinator. [claim:clm_053]
- The swarm remembers which agent was last active so that subsequent interactions resume the multi-turn conversation with that same agent. [claim:clm_054]
- By default, swarm agents use handoff tools built with the prebuilt create_handoff_tool helper. [claim:clm_055]
- Handoff tools can be customized by changing the tool name and/or description and by adding tool-call arguments for the LLM to populate, such as a task description for the next agent. [claim:clm_056]
- create_swarm() builds the workflow from a list of agents and accepts a default_active_agent argument (e.g. create_swarm([alice, bob], default_active_agent="Alice")). [claim:clm_057]
- Multi-turn state requires always compiling the swarm with a checkpointer (e.g. workflow.compile(checkpointer=checkpointer)). [claim:clm_058]
- create_supervisor() is the package's primary entry point for building a multi-agent supervisor that manages a list of worker agents under a single supervising language model. [claim:clm_059]
- The supervisor manages a list of agents, where each agent can be a LangGraph CompiledStateGraph, a functional-API workflow, or any other Pregel object. [claim:clm_060]
- create_handoff_tool() creates a tool that hands off control to a named worker agent (the tool is named transfer_to_<agent_name> by default). [claim:clm_061]
- create_handoff_back_messages() builds an (AIMessage, ToolMessage) pair added to the message history when control returns from a worker to the supervisor, implementing the return-communication leg of delegation. [claim:clm_062]
- create_forward_message_tool() lets the supervisor forward a worker message by name rather than rewriting it, so the central supervisor mediates communication while avoiding information loss and token cost. [claim:clm_063]
- with_agent_name() attaches formatted agent-name tags to messages passed to and from the model so a multi-agent history stays coherent and the supervisor can track which agent a message belongs to. [claim:clm_064]
- Semantic Router positions itself as a fast decision-making/routing layer that sits in front of LLMs and agents. [claim:clm_065]
- Routing decisions are made in semantic vector space using embeddings rather than by waiting for slow LLM generations, reducing latency for routing/tool-use decisions. [claim:clm_066]
- Routes are defined declaratively as objects with a name and a list of example 'utterances' that exemplify that route; an incoming query is matched against these by semantic similarity. [claim:clm_067]
- Beyond static classification, the package supports 'Dynamic Routes' that generate parameters and trigger function calls. [claim:clm_068]
- Semantic Router can run fully locally using a local encoder (HuggingFaceEncoder) and a local LLM (LlamaCppLLM), avoiding hosted-API dependencies. [claim:clm_069]
- The library ships pluggable encoder integrations (Cohere, OpenAI, Hugging Face, FastEmbed, and multi-modal encoders) and integrates with vector databases such as Pinecone and Qdrant. [claim:clm_070]
- A supervisor agent can be configured either to coordinate responses from collaborator agents or to route information to the appropriate collaborator to send the final response. [claim:clm_071]
- Assigning the supervisor the routing task reduces latency. [claim:clm_072]
- A supervisor agent can associate a maximum of 10 collaborator agents. [claim:clm_073]
- In the console the two modes are explicit options: 'Supervisor' coordinates collaborator responses, while 'Supervisor with routing' routes information to the appropriate collaborator to send the final response. [claim:clm_074]
- Each collaborator's 'Collaboration instructions' tell the supervisor when that collaborator should be used. [claim:clm_075]
- The optional 'Enable conversation history' setting shares full current-session context (user input and supervisor response from each turn) with the collaborator agent. [claim:clm_076]
- Deployment is done by setting up the supervisor agent to make an InvokeAgent request. [claim:clm_077]

## Sources

- src_20260614_rib026_00 — Building Effective AI Agents
- src_20260614_rib026_01 — Handoffs — OpenAI Agents SDK
- src_20260614_rib026_02 — Agent orchestration — OpenAI Agents SDK
- src_20260614_rib026_03 — LangGraph Multi-Agent Supervisor (langgraph-supervisor reference)
- src_20260614_rib026_04 — langgraph-swarm-py (LangGraph Multi-Agent Swarm)
- src_20260614_rib026_05 — Create multi-agent collaboration - Amazon Bedrock User Guide
- src_20260614_rib026_06 — Amazon Bedrock now supports multi-agent collaboration
- src_20260614_rib026_07 — Microsoft Agent Framework Version 1.0
- src_20260614_rib026_08 — Flows — CrewAI Documentation
- src_20260614_rib026_09 — Router - Load Balancing | liteLLM
- src_20260614_rib026_10 — aurelio-labs/semantic-router — README (official repo)
- src_20260614_rib026_11 — Semantic Router — Introduction (Aurelio AI official docs)

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
