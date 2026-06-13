**You:**

You are the Architect for Nick’s Research Foundry.

Using the Agentic OS architecture, design the MVP folder structure, YAML schemas, CLI commands, agent roles, and execution loop for turning raw ideas into research swarms, evidence bundles, reports, MeatyWiki writebacks, SkillBOM candidates, and CCDash telemetry.

Constraints:
- Markdown/YAML first.
- Use existing tools where possible: Claude Code, Claude Agent SDK, OpenCode, Agent Council, GPT Researcher, PaperQA2, LiteLLM or model-profile routing.
- Use cheap/free models for extraction and expensive models for synthesis.
- Include governance boundaries for work-provided keys.
- Every material claim in research outputs must map to a source card or be labeled inference/speculation.
- Output an implementation-ready spec with schemas and a 7-day MVP plan.

* * *

**ChatGPT:**

I’ll shape this as a buildable Research Foundry MVP within Agentic OS, keeping it Markdown/YAML-first while verifying the named tools against current primary sources.

The core decision is to make Research Foundry a thin, file-backed control plane rather than a monolithic research app, composing agents around an evidence-first pipeline.

---

schema_version: 0.1  
id: spec_research_foundry_mvp_2026_06_12  
type: durable_artifact  
artifact_kind: implementation_ready_spec  
title: "Nick’s Research Foundry MVP"  
project: "Research Foundry"  
domain: "Agentic OS / research execution / evidence operations"  
status: candidate_artifact  
owner: "Nick Miethe"  
created_at: "2026-06-12"  
updated_at: "2026-06-12"  
system_of_record: "MeatyWiki + GitHub"  
current_location: "unassigned"  
related_systems:

* Intent and I-BOM
* IntentTree
* Agent Postures
* SkillMeat/SAM
* Execution Engine
* CCDash
* MeatyWiki
* Agentic Control Plane
* Governance and Evaluation  
    source_context:
* "Agentic OS seed specs"
* "Current tool docs for Claude Code, Claude Agent SDK, OpenCode, GPT Researcher, PaperQA2, LiteLLM, Agent Council-style workflows"  
    intended_use: "Build a Markdown/YAML-first MVP that turns raw ideas into governed research swarms, evidence bundles, reports, memory writebacks, SkillBOM candidates, and CCDash telemetry."  
    next_action: "Create the repo scaffold and implement rf init, rf capture, rf plan, rf verify, and rf writeback first."  
    review_cadence: "daily during MVP week, weekly after MVP"  
    confidentiality: "personal"  
    tags:
* research-foundry
* agentic-os
* evidence-bundles
* research-swarms
* ccdash
* meatywiki
* skillbom

---

# Nick’s Research Foundry MVP Spec

## 0. Objective

Design a **Markdown/YAML-first Research Foundry** that captures raw ideas, converts them into structured research intents, launches research swarms, collects source cards, produces evidence bundles, writes reports, verifies claim-to-source traceability, and feeds results into **MeatyWiki**, **SkillMeat/SAM**, and **CCDash**.

This sits cleanly inside the Agentic OS architecture: the central project already frames the system as intent capture, task decomposition, agent routing, reusable skill/context stacks, telemetry, memory, evaluation, and governance, with the canonical flow: “Intent defines the destination… the control plane routes the next move.” The Research Foundry is a **research-specialized execution engine** that uses that same loop.

---

## 1. System classification

| Dimension | Design decision |
| --- | --- |
| **Layer** | Cross-layer system spanning Intent, I-BOM, IntentTree, Agent Postures, SkillMeat, Execution, CCDash, MeatyWiki, Control Plane, and Governance |
| **Owning project** | New subproject: **Research Foundry** |
| **Central portfolio owner** | Agentic OS Central Project |
| **Primary artifact** | Implementation-ready MVP spec plus repo scaffold |
| **Primary agent posture** | Architect for design, Researcher for source work, Critic for claim verification, Synthesizer for reports, Operator for loop execution |
| **Work class** | Personal + research + implementation; enterprise-ready governance hooks |
| **Systems updated** | MeatyWiki for rationale, SkillMeat for reusable research workflows, CCDash for execution telemetry, IntentTree for active research nodes, Control Plane for routing |

Research Foundry should not collapse the Agentic OS portfolio into one product. It should behave like a **file-backed research control plane** that can call existing agents and tools while preserving traceability.

---

## 2. Design principles

1. **Markdown/YAML is the source of truth.**  
    Every intent, source card, evidence bundle, report, writeback, SkillBOM candidate, and telemetry event is readable without a database.
2. **Research begins with intent, not prompts.**  
    Intent and I-BOM already define objective, motivation, constraints, stakeholders, success criteria, source context, assumptions, tools, and governance boundaries. Research Foundry specializes this into research briefs and swarm plans.
3. **Every material claim is auditable.**  
    A research report may contain only:
    * supported claims mapped to source cards,
    * labeled inference,
    * labeled speculation,
    * or explicitly unresolved claims.
4. **Cheap/free models extract; expensive models synthesize.**  
    Extraction, source-card creation, deduplication, tagging, and formatting should run on local/free/cheap models where feasible. Synthesis, contradiction analysis, executive framing, and final report construction use higher-reasoning models.
5. **The swarm is disposable; the evidence bundle is durable.**  
    Agent runs can be rerun. The durable asset is the bundle: source cards, extracted claims, claim ledger, report, reviews, and telemetry.
6. **Governance is a runtime gate, not a memo.**  
    Work-provided keys, sensitive source material, model routing, and writeback targets must be checked before execution.
7. **CCDash proves which research workflows work.**  
    CCDash is designed to answer “what actually worked?” by tracking completion, rework, drift, cost, latency, quality, reuse candidates, and friction. Research Foundry should emit CCDash-lite events from day one.

---

## 3. External tool fit

| Tool | MVP use | Notes |
| --- | --- | --- |
| **Claude Code** | Main repo operator, schema generator, file editor, hook runner, local orchestrator | Claude Code supports terminal/IDE/browser usage and can read codebases, edit files, run commands, and automate development tasks. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude API Docs](https://docs.anthropic.com/en/docs/claude-code/overview?utm_source=chatgpt.com) |
| **Claude Agent SDK** | Programmatic swarm orchestration, structured agent runs, permissions, subagents, sessions | The SDK exposes built-in tools, hooks, subagents, MCP, permissions, and sessions; it can read files, run commands, grep/glob, and use web tools. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude API Docs](https://docs.anthropic.com/en/docs/claude-code/sdk) |
| **Claude Code Skills/Subagents** | Define Research Foundry skills and roles as Markdown files with YAML front matter | Claude Code skills use `SKILL.md`; subagents are Markdown files with YAML front matter and can be created manually or with `/agents`. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude API Docs+1](https://docs.anthropic.com/en/docs/claude-code/skills) |
| **OpenCode** | Optional open-source coding agent for repo operations, parallel sessions, and local/editor workflows | OpenCode describes itself as an open-source AI coding agent for terminal, IDE, or desktop, with LSP support, multi-session operation, many providers, and privacy-first positioning. [![](https://www.google.com/s2/favicons?domain=https://opencode.ai&sz=128)OpenCode](https://opencode.ai/) |
| **Agent Council / council pattern** | Optional multi-agent review stage with structured votes: Approve / Concern / Block | The `agent-council` project organizes specialized agent personas into councils and uses structured voting to surface risks and tradeoffs. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/andrewvaughan/agent-council) |
| **GPT Researcher** | Web/local/hybrid source discovery and initial research pass | GPT Researcher supports web and local document research, multi-source reports, citations, local docs, many LLMs, and multi-agent support. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub+1](https://github.com/assafelovic/gpt-researcher) |
| **PaperQA2** | Scientific-paper RAG, citation-grounded answers, PDF/text corpus search | PaperQA2 is designed for agentic RAG over scientific papers, grounded responses with in-text citations, re-ranking/contextual summarization, local PDF/text search, and LiteLLM model support. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/future-house/paper-qa) |
| **LiteLLM / model-profile routing** | Cost-aware model routing, provider budgets, model budgets, fallbacks | LiteLLM supports routing strategies including weighted, rate-limit aware, least-busy, latency-based, cost-based, and lowest-cost routing; it also supports provider, model, and tag budgets. [![](https://www.google.com/s2/favicons?domain=https://docs.litellm.ai&sz=128)LiteLLM+1](https://docs.litellm.ai/docs/routing) |

---

## 4. MVP architecture

Mermaid![](data:image/svg+xml;utf8,%3Csvg%20id%3D%22mermaid-_r_8ne_%22%20width%3D%223305.09375%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20class%3D%22flowchart%22%20height%3D%22293.00311279296875%22%20viewBox%3D%220%200%203305.09375%20293.00311279296875%22%20role%3D%22graphics-document%20document%22%20aria-roledescription%3D%22flowchart-v2%22%3E%3Cstyle%3E%23mermaid-_r_8ne_%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A16px%3Bfill%3A%23ccc%3B%7D%40keyframes%20edge-animation-frame%7Bfrom%7Bstroke-dashoffset%3A0%3B%7D%7D%40keyframes%20dash%7Bto%7Bstroke-dashoffset%3A0%3B%7D%7D%23mermaid-_r_8ne_%20.edge-animation-slow%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2050s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_8ne_%20.edge-animation-fast%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2020s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_8ne_%20.error-icon%7Bfill%3A%23a44141%3B%7D%23mermaid-_r_8ne_%20.error-text%7Bfill%3A%23ddd%3Bstroke%3A%23ddd%3B%7D%23mermaid-_r_8ne_%20.edge-thickness-normal%7Bstroke-width%3A1px%3B%7D%23mermaid-_r_8ne_%20.edge-thickness-thick%7Bstroke-width%3A3.5px%3B%7D%23mermaid-_r_8ne_%20.edge-pattern-solid%7Bstroke-dasharray%3A0%3B%7D%23mermaid-_r_8ne_%20.edge-thickness-invisible%7Bstroke-width%3A0%3Bfill%3Anone%3B%7D%23mermaid-_r_8ne_%20.edge-pattern-dashed%7Bstroke-dasharray%3A3%3B%7D%23mermaid-_r_8ne_%20.edge-pattern-dotted%7Bstroke-dasharray%3A2%3B%7D%23mermaid-_r_8ne_%20.marker%7Bfill%3Alightgrey%3Bstroke%3Alightgrey%3B%7D%23mermaid-_r_8ne_%20.marker.cross%7Bstroke%3Alightgrey%3B%7D%23mermaid-_r_8ne_%20svg%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A16px%3B%7D%23mermaid-_r_8ne_%20p%7Bmargin%3A0%3B%7D%23mermaid-_r_8ne_%20.label%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bcolor%3A%23ccc%3B%7D%23mermaid-_r_8ne_%20.cluster-label%20text%7Bfill%3A%23F9FFFE%3B%7D%23mermaid-_r_8ne_%20.cluster-label%20span%7Bcolor%3A%23F9FFFE%3B%7D%23mermaid-_r_8ne_%20.cluster-label%20span%20p%7Bbackground-color%3Atransparent%3B%7D%23mermaid-_r_8ne_%20.label%20text%2C%23mermaid-_r_8ne_%20span%7Bfill%3A%23ccc%3Bcolor%3A%23ccc%3B%7D%23mermaid-_r_8ne_%20.node%20rect%2C%23mermaid-_r_8ne_%20.node%20circle%2C%23mermaid-_r_8ne_%20.node%20ellipse%2C%23mermaid-_r_8ne_%20.node%20polygon%2C%23mermaid-_r_8ne_%20.node%20path%7Bfill%3A%231f2020%3Bstroke%3A%23ccc%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_8ne_%20.rough-node%20.label%20text%2C%23mermaid-_r_8ne_%20.node%20.label%20text%2C%23mermaid-_r_8ne_%20.image-shape%20.label%2C%23mermaid-_r_8ne_%20.icon-shape%20.label%7Btext-anchor%3Amiddle%3B%7D%23mermaid-_r_8ne_%20.node%20.katex%20path%7Bfill%3A%23000%3Bstroke%3A%23000%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_8ne_%20.rough-node%20.label%2C%23mermaid-_r_8ne_%20.node%20.label%2C%23mermaid-_r_8ne_%20.image-shape%20.label%2C%23mermaid-_r_8ne_%20.icon-shape%20.label%7Btext-align%3Acenter%3B%7D%23mermaid-_r_8ne_%20.node.clickable%7Bcursor%3Apointer%3B%7D%23mermaid-_r_8ne_%20.root%20.anchor%20path%7Bfill%3Alightgrey!important%3Bstroke-width%3A0%3Bstroke%3Alightgrey%3B%7D%23mermaid-_r_8ne_%20.arrowheadPath%7Bfill%3Alightgrey%3B%7D%23mermaid-_r_8ne_%20.edgePath%20.path%7Bstroke%3Alightgrey%3Bstroke-width%3A2.0px%3B%7D%23mermaid-_r_8ne_%20.flowchart-link%7Bstroke%3Alightgrey%3Bfill%3Anone%3B%7D%23mermaid-_r_8ne_%20.edgeLabel%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_8ne_%20.edgeLabel%20p%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_8ne_%20.edgeLabel%20rect%7Bopacity%3A0.5%3Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bfill%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_8ne_%20.labelBkg%7Bbackground-color%3Argba(87.75%2C%2087.75%2C%2087.75%2C%200.5)%3B%7D%23mermaid-_r_8ne_%20.cluster%20rect%7Bfill%3Ahsl(180%2C%201.5873015873%25%2C%2028.3529411765%25)%3Bstroke%3Argba(255%2C%20255%2C%20255%2C%200.25)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_8ne_%20.cluster%20text%7Bfill%3A%23F9FFFE%3B%7D%23mermaid-_r_8ne_%20.cluster%20span%7Bcolor%3A%23F9FFFE%3B%7D%23mermaid-_r_8ne_%20div.mermaidTooltip%7Bposition%3Aabsolute%3Btext-align%3Acenter%3Bmax-width%3A200px%3Bpadding%3A2px%3Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A12px%3Bbackground%3Ahsl(20%2C%201.5873015873%25%2C%2012.3529411765%25)%3Bborder%3A1px%20solid%20rgba(255%2C%20255%2C%20255%2C%200.25)%3Bborder-radius%3A2px%3Bpointer-events%3Anone%3Bz-index%3A100%3B%7D%23mermaid-_r_8ne_%20.flowchartTitleText%7Btext-anchor%3Amiddle%3Bfont-size%3A18px%3Bfill%3A%23ccc%3B%7D%23mermaid-_r_8ne_%20rect.text%7Bfill%3Anone%3Bstroke-width%3A0%3B%7D%23mermaid-_r_8ne_%20.icon-shape%2C%23mermaid-_r_8ne_%20.image-shape%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_8ne_%20.icon-shape%20p%2C%23mermaid-_r_8ne_%20.image-shape%20p%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bpadding%3A2px%3B%7D%23mermaid-_r_8ne_%20.icon-shape%20rect%2C%23mermaid-_r_8ne_%20.image-shape%20rect%7Bopacity%3A0.5%3Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bfill%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_8ne_%20.label-icon%7Bdisplay%3Ainline-block%3Bheight%3A1em%3Boverflow%3Avisible%3Bvertical-align%3A-0.125em%3B%7D%23mermaid-_r_8ne_%20.node%20.label-icon%20path%7Bfill%3AcurrentColor%3Bstroke%3Arevert%3Bstroke-width%3Arevert%3B%7D%23mermaid-_r_8ne_%20%3Aroot%7B--mermaid-font-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3B%7D%3C%2Fstyle%3E%3Cg%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-pointEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%225%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%228%22%20markerHeight%3D%228%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%200%20L%2010%205%20L%200%2010%20z%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-pointStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%224.5%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%228%22%20markerHeight%3D%228%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%205%20L%2010%2010%20L%2010%200%20z%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-circleEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%2211%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-circleStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%22-1%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-crossEnd%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%2212%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_8ne__flowchart-v2-crossStart%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%22-1%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cg%20class%3D%22root%22%3E%3Cg%20class%3D%22clusters%22%3E%3C%2Fg%3E%3Cg%20class%3D%22edgePaths%22%3E%3Cpath%20d%3D%22M132.953%2C105.802L137.12%2C105.802C141.286%2C105.802%2C149.62%2C105.802%2C157.286%2C105.802C164.953%2C105.802%2C171.953%2C105.802%2C175.453%2C105.802L178.953%2C105.802%22%20id%3D%22L_A_B_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_A_B_0%22%20data-points%3D%22W3sieCI6MTMyLjk1MzEyNSwieSI6MTA1LjgwMTU2MTM1NTU5MDgyfSx7IngiOjE1Ny45NTMxMjUsInkiOjEwNS44MDE1NjEzNTU1OTA4Mn0seyJ4IjoxODIuOTUzMTI1LCJ5IjoxMDUuODAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M414.578%2C105.802L418.745%2C105.802C422.911%2C105.802%2C431.245%2C105.802%2C438.911%2C105.802C446.578%2C105.802%2C453.578%2C105.802%2C457.078%2C105.802L460.578%2C105.802%22%20id%3D%22L_B_C_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_B_C_0%22%20data-points%3D%22W3sieCI6NDE0LjU3ODEyNSwieSI6MTA1LjgwMTU2MTM1NTU5MDgyfSx7IngiOjQzOS41NzgxMjUsInkiOjEwNS44MDE1NjEzNTU1OTA4Mn0seyJ4Ijo0NjQuNTc4MTI1LCJ5IjoxMDUuODAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M709.109%2C105.802L713.276%2C105.802C717.443%2C105.802%2C725.776%2C105.802%2C733.443%2C105.802C741.109%2C105.802%2C748.109%2C105.802%2C751.609%2C105.802L755.109%2C105.802%22%20id%3D%22L_C_D_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_C_D_0%22%20data-points%3D%22W3sieCI6NzA5LjEwOTM3NSwieSI6MTA1LjgwMTU2MTM1NTU5MDgyfSx7IngiOjczNC4xMDkzNzUsInkiOjEwNS44MDE1NjEzNTU1OTA4Mn0seyJ4Ijo3NTkuMTA5Mzc1LCJ5IjoxMDUuODAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M974.719%2C105.802L978.885%2C105.802C983.052%2C105.802%2C991.385%2C105.802%2C999.052%2C105.802C1006.719%2C105.802%2C1013.719%2C105.802%2C1017.219%2C105.802L1020.719%2C105.802%22%20id%3D%22L_D_E_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_D_E_0%22%20data-points%3D%22W3sieCI6OTc0LjcxODc1LCJ5IjoxMDUuODAxNTYxMzU1NTkwODJ9LHsieCI6OTk5LjcxODc1LCJ5IjoxMDUuODAxNTYxMzU1NTkwODJ9LHsieCI6MTAyNC43MTg3NSwieSI6MTA1LjgwMTU2MTM1NTU5MDgyfV0%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1153.173%2C130.302L1171.235%2C149.935C1189.297%2C169.568%2C1225.422%2C208.834%2C1246.985%2C228.467C1268.547%2C248.1%2C1275.547%2C248.1%2C1279.047%2C248.1L1282.547%2C248.1%22%20id%3D%22L_E_F1_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_E_F1_0%22%20data-points%3D%22W3sieCI6MTE1My4xNzI3MjY0NzM3NDQ3LCJ5IjoxMzAuMzAxNTYxMzU1NTkwODJ9LHsieCI6MTI2MS41NDY4NzUsInkiOjI0OC4wOTk5OTg0NzQxMjExfSx7IngiOjEyODYuNTQ2ODc1LCJ5IjoyNDguMDk5OTk4NDc0MTIxMX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1204.709%2C130.302L1214.182%2C133.435C1223.655%2C136.568%2C1242.601%2C142.834%2C1259.185%2C145.967C1275.768%2C149.1%2C1289.99%2C149.1%2C1297.1%2C149.1L1304.211%2C149.1%22%20id%3D%22L_E_F2_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_E_F2_0%22%20data-points%3D%22W3sieCI6MTIwNC43MDkyNjI5Mzc5MTU0LCJ5IjoxMzAuMzAxNTYxMzU1NTkwODJ9LHsieCI6MTI2MS41NDY4NzUsInkiOjE0OS4wOTk5OTg0NzQxMjExfSx7IngiOjEzMDguMjEwOTM3NSwieSI6MTQ5LjA5OTk5ODQ3NDEyMTF9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1180.359%2C81.302L1193.89%2C74.635C1207.421%2C67.968%2C1234.484%2C54.634%2C1255.088%2C47.967C1275.693%2C41.3%2C1289.839%2C41.3%2C1296.911%2C41.3L1303.984%2C41.3%22%20id%3D%22L_E_F3_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_E_F3_0%22%20data-points%3D%22W3sieCI6MTE4MC4zNTg2NTUxOTEzMTMxLCJ5Ijo4MS4zMDE1NjEzNTU1OTA4Mn0seyJ4IjoxMjYxLjU0Njg3NSwieSI6NDEuMjk5OTk5MjM3MDYwNTV9LHsieCI6MTMwNy45ODQzNzUsInkiOjQxLjI5OTk5OTIzNzA2MDU1fV0%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1519.859%2C248.1L1524.026%2C248.1C1528.193%2C248.1%2C1536.526%2C248.1%2C1552.609%2C237.168C1568.692%2C226.235%2C1592.524%2C204.37%2C1604.44%2C193.438L1616.356%2C182.506%22%20id%3D%22L_F1_G_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_F1_G_0%22%20data-points%3D%22W3sieCI6MTUxOS44NTkzNzUsInkiOjI0OC4wOTk5OTg0NzQxMjExfSx7IngiOjE1NDQuODU5Mzc1LCJ5IjoyNDguMDk5OTk4NDc0MTIxMX0seyJ4IjoxNjE5LjMwMzMwMzI4OTUxOTQsInkiOjE3OS44MDE1NjEzNTU1OTA4Mn1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1498.195%2C149.1L1505.973%2C149.1C1513.75%2C149.1%2C1529.305%2C149.1%2C1540.583%2C149.315C1551.862%2C149.529%2C1558.864%2C149.959%2C1562.366%2C150.173L1565.867%2C150.388%22%20id%3D%22L_F2_G_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_F2_G_0%22%20data-points%3D%22W3sieCI6MTQ5OC4xOTUzMTI1LCJ5IjoxNDkuMDk5OTk4NDc0MTIxMX0seyJ4IjoxNTQ0Ljg1OTM3NSwieSI6MTQ5LjA5OTk5ODQ3NDEyMTF9LHsieCI6MTU2OS44NTkzNzUsInkiOjE1MC42MzI3ODYwODY3NDk3NX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1498.422%2C41.3L1506.161%2C41.3C1513.901%2C41.3%2C1529.38%2C41.3%2C1549.912%2C55.718C1570.445%2C70.136%2C1596.03%2C98.973%2C1608.823%2C113.391L1621.615%2C127.809%22%20id%3D%22L_F3_G_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_F3_G_0%22%20data-points%3D%22W3sieCI6MTQ5OC40MjE4NzUsInkiOjQxLjI5OTk5OTIzNzA2MDU1fSx7IngiOjE1NDQuODU5Mzc1LCJ5Ijo0MS4yOTk5OTkyMzcwNjA1NX0seyJ4IjoxNjI0LjI3MDA2ODk3NTI4MDMsInkiOjEzMC44MDE1NjEzNTU1OTA4Mn1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1722.156%2C155.302L1726.323%2C155.302C1730.49%2C155.302%2C1738.823%2C155.302%2C1746.49%2C155.302C1754.156%2C155.302%2C1761.156%2C155.302%2C1764.656%2C155.302L1768.156%2C155.302%22%20id%3D%22L_G_H_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_G_H_0%22%20data-points%3D%22W3sieCI6MTcyMi4xNTYyNSwieSI6MTU1LjMwMTU2MTM1NTU5MDgyfSx7IngiOjE3NDcuMTU2MjUsInkiOjE1NS4zMDE1NjEzNTU1OTA4Mn0seyJ4IjoxNzcyLjE1NjI1LCJ5IjoxNTUuMzAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M1950.281%2C155.302L1954.448%2C155.302C1958.615%2C155.302%2C1966.948%2C155.302%2C1974.615%2C155.302C1982.281%2C155.302%2C1989.281%2C155.302%2C1992.781%2C155.302L1996.281%2C155.302%22%20id%3D%22L_H_I_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_H_I_0%22%20data-points%3D%22W3sieCI6MTk1MC4yODEyNSwieSI6MTU1LjMwMTU2MTM1NTU5MDgyfSx7IngiOjE5NzUuMjgxMjUsInkiOjE1NS4zMDE1NjEzNTU1OTA4Mn0seyJ4IjoyMDAwLjI4MTI1LCJ5IjoxNTUuMzAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2154.375%2C159.984L2158.542%2C160.237C2162.708%2C160.49%2C2171.042%2C160.997%2C2178.708%2C161.25C2186.375%2C161.503%2C2193.375%2C161.503%2C2196.875%2C161.503L2200.375%2C161.503%22%20id%3D%22L_I_J_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_I_J_0%22%20data-points%3D%22W3sieCI6MjE1NC4zNzUsInkiOjE1OS45ODM4MzE1MzkxMDQ0MX0seyJ4IjoyMTc5LjM3NSwieSI6MTYxLjUwMzEyNDIzNzA2MDU1fSx7IngiOjIyMDQuMzc1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2382.313%2C161.503L2386.479%2C161.503C2390.646%2C161.503%2C2398.979%2C161.503%2C2406.646%2C161.503C2414.313%2C161.503%2C2421.313%2C161.503%2C2424.813%2C161.503L2428.313%2C161.503%22%20id%3D%22L_J_K_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_J_K_0%22%20data-points%3D%22W3sieCI6MjM4Mi4zMTI1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9LHsieCI6MjQwNy4zMTI1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9LHsieCI6MjQzMi4zMTI1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2590.984%2C161.503L2595.151%2C161.503C2599.318%2C161.503%2C2607.651%2C161.503%2C2615.318%2C161.503C2622.984%2C161.503%2C2629.984%2C161.503%2C2633.484%2C161.503L2636.984%2C161.503%22%20id%3D%22L_K_L_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_K_L_0%22%20data-points%3D%22W3sieCI6MjU5MC45ODQzNzUsInkiOjE2MS41MDMxMjQyMzcwNjA1NX0seyJ4IjoyNjE1Ljk4NDM3NSwieSI6MTYxLjUwMzEyNDIzNzA2MDU1fSx7IngiOjI2NDAuOTg0Mzc1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2705.616%2C141.729L2715.3%2C133.191C2724.984%2C124.654%2C2744.351%2C107.578%2C2759.767%2C98.011C2775.182%2C88.443%2C2786.646%2C86.382%2C2792.378%2C85.352L2798.11%2C84.322%22%20id%3D%22L_L_M_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_L_M_0%22%20data-points%3D%22W3sieCI6MjcwNS42MTYzNDE2NDI2MDY2LCJ5IjoxNDEuNzI4ODQwODc5NjY3Mjd9LHsieCI6Mjc2My43MTg3NSwieSI6OTAuNTAzMTI0MjM3MDYwNTV9LHsieCI6MjgwMi4wNDY4NzUsInkiOjgzLjYxNDA1NzAzNTQ1NTczfV0%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2802.047%2C42.635L2795.659%2C41.554C2789.271%2C40.474%2C2776.495%2C38.313%2C2756.685%2C37.232C2736.875%2C36.152%2C2710.031%2C36.152%2C2685.409%2C36.152C2660.786%2C36.152%2C2638.385%2C36.152%2C2609.796%2C36.152C2581.206%2C36.152%2C2546.427%2C36.152%2C2511.648%2C36.152C2476.87%2C36.152%2C2442.091%2C36.152%2C2405.707%2C36.152C2369.323%2C36.152%2C2331.333%2C36.152%2C2293.344%2C36.152C2255.354%2C36.152%2C2217.365%2C36.152%2C2185.293%2C51.42C2153.221%2C66.689%2C2127.067%2C97.226%2C2113.99%2C112.495L2100.913%2C127.764%22%20id%3D%22L_M_I_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_M_I_0%22%20data-points%3D%22W3sieCI6MjgwMi4wNDY4NzUsInkiOjQyLjYzNTA1MDQ4NDU1MzAyfSx7IngiOjI3NjMuNzE4NzUsInkiOjM2LjE1MTU2MTczNzA2MDU1fSx7IngiOjI2ODMuMTg3NSwieSI6MzYuMTUxNTYxNzM3MDYwNTV9LHsieCI6MjYxNS45ODQzNzUsInkiOjM2LjE1MTU2MTczNzA2MDU1fSx7IngiOjI1MTEuNjQ4NDM3NSwieSI6MzYuMTUxNTYxNzM3MDYwNTV9LHsieCI6MjQwNy4zMTI1LCJ5IjozNi4xNTE1NjE3MzcwNjA1NX0seyJ4IjoyMjkzLjM0Mzc1LCJ5IjozNi4xNTE1NjE3MzcwNjA1NX0seyJ4IjoyMTc5LjM3NSwieSI6MzYuMTUxNTYxNzM3MDYwNTV9LHsieCI6MjA5OC4zMTEzMjYzODkwNDI3LCJ5IjoxMzAuODAxNTYxMzU1NTkwODJ9XQ%3D%3D%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2725.391%2C161.503L2731.779%2C161.503C2738.167%2C161.503%2C2750.943%2C161.503%2C2767.818%2C161.503C2784.693%2C161.503%2C2805.667%2C161.503%2C2816.154%2C161.503L2826.641%2C161.503%22%20id%3D%22L_L_N_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_L_N_0%22%20data-points%3D%22W3sieCI6MjcyNS4zOTA2MjUsInkiOjE2MS41MDMxMjQyMzcwNjA1NX0seyJ4IjoyNzYzLjcxODc1LCJ5IjoxNjEuNTAzMTI0MjM3MDYwNTV9LHsieCI6MjgzMC42NDA2MjUsInkiOjE2MS41MDMxMjQyMzcwNjA1NX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2954.754%2C137.003L2972.62%2C124.586C2990.487%2C112.17%2C3026.22%2C87.336%2C3047.587%2C74.92C3068.953%2C62.503%2C3075.953%2C62.503%2C3079.453%2C62.503L3082.953%2C62.503%22%20id%3D%22L_N_O_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_N_O_0%22%20data-points%3D%22W3sieCI6Mjk1NC43NTM1NTExMzYzNjM1LCJ5IjoxMzcuMDAzMTI0MjM3MDYwNTV9LHsieCI6MzA2MS45NTMxMjUsInkiOjYyLjUwMzEyNDIzNzA2MDU1fSx7IngiOjMwODYuOTUzMTI1LCJ5Ijo2Mi41MDMxMjQyMzcwNjA1NX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M3008.359%2C161.503L3017.292%2C161.503C3026.224%2C161.503%2C3044.089%2C161.503%2C3057.503%2C161.503C3070.917%2C161.503%2C3079.88%2C161.503%2C3084.362%2C161.503L3088.844%2C161.503%22%20id%3D%22L_N_P_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_N_P_0%22%20data-points%3D%22W3sieCI6MzAwOC4zNTkzNzUsInkiOjE2MS41MDMxMjQyMzcwNjA1NX0seyJ4IjozMDYxLjk1MzEyNSwieSI6MTYxLjUwMzEyNDIzNzA2MDU1fSx7IngiOjMwOTIuODQzNzUsInkiOjE2MS41MDMxMjQyMzcwNjA1NX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M2954.754%2C186.003L2972.62%2C198.42C2990.487%2C210.836%2C3026.22%2C235.67%2C3051.963%2C248.086C3077.706%2C260.503%2C3093.458%2C260.503%2C3101.335%2C260.503L3109.211%2C260.503%22%20id%3D%22L_N_Q_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_N_Q_0%22%20data-points%3D%22W3sieCI6Mjk1NC43NTM1NTExMzYzNjM1LCJ5IjoxODYuMDAzMTI0MjM3MDYwNTV9LHsieCI6MzA2MS45NTMxMjUsInkiOjI2MC41MDMxMjQyMzcwNjA1NX0seyJ4IjozMTEzLjIxMDkzNzUsInkiOjI2MC41MDMxMjQyMzcwNjA1NX1d%22%20marker-end%3D%22url(%23mermaid-_r_8ne__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabels%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_A_B_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_B_C_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_C_D_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_D_E_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_E_F1_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_E_F2_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_E_F3_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_F1_G_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_F2_G_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_F3_G_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_G_H_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_H_I_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_I_J_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_J_K_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_K_L_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%20transform%3D%22translate(2749.27289%2C%20103.23925)%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_L_M_0%22%20transform%3D%22translate(-11.3984375%2C%20-11.5)%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22%22%20x%3D%22-2%22%20y%3D%22-1%22%20width%3D%2222.796875%22%20height%3D%2223%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ENo%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_M_I_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%20transform%3D%22translate(2763.71875%2C%20161.50312423706055)%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_L_N_0%22%20transform%3D%22translate(-13.328125%2C%20-11.5)%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22%22%20x%3D%22-2%22%20y%3D%22-1%22%20width%3D%2226.65625%22%20height%3D%2223%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EYes%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_N_O_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_N_P_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_N_Q_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22nodes%22%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-A-0%22%20transform%3D%22translate(70.4765625%2C%20105.80156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-62.4765625%22%20y%3D%22-24.5%22%20width%3D%22124.953125%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ERaw%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Idea%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-B-1%22%20transform%3D%22translate(298.765625%2C%20105.80156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-115.8125%22%20y%3D%22-24.5%22%20width%3D%22231.625%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EResearch%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Intent%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20%2B%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20I-BOM%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-C-3%22%20transform%3D%22translate(586.84375%2C%20105.80156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-122.265625%22%20y%3D%22-24.5%22%20width%3D%22244.53125%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EIntentTree%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Research%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Node%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-D-5%22%20transform%3D%22translate(866.9140625%2C%20105.80156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-107.8046875%22%20y%3D%22-33.29999923706055%22%20width%3D%22215.609375%22%20height%3D%2266.5999984741211%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-18.299999237060547)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EControl%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Plane%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Routing%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EDecision%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-E-7%22%20transform%3D%22translate(1130.6328125%2C%20105.80156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-105.9140625%22%20y%3D%22-24.5%22%20width%3D%22211.828125%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EResearch%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Swarm%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Plan%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-F1-9%22%20transform%3D%22translate(1403.203125%2C%20248.0999984741211)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-116.65625%22%20y%3D%22-24.5%22%20width%3D%22233.3125%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EGPT%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Researcher%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Adapter%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-F2-11%22%20transform%3D%22translate(1403.203125%2C%20149.0999984741211)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-94.9921875%22%20y%3D%22-24.5%22%20width%3D%22189.984375%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPaperQA2%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Adapter%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-F3-13%22%20transform%3D%22translate(1403.203125%2C%2041.29999923706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-95.21875%22%20y%3D%22-33.29999923706055%22%20width%3D%22190.4375%22%20height%3D%2266.5999984741211%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-18.299999237060547)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EClaude%2FOpenCode%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EExtractors%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-G-15%22%20transform%3D%22translate(1646.0078125%2C%20155.30156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-76.1484375%22%20y%3D%22-24.5%22%20width%3D%22152.296875%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ESource%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Cards%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-H-21%22%20transform%3D%22translate(1861.21875%2C%20155.30156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-89.0625%22%20y%3D%22-24.5%22%20width%3D%22178.125%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EExtraction%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Cards%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-I-23%22%20transform%3D%22translate(2077.328125%2C%20155.30156135559082)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-77.046875%22%20y%3D%22-24.5%22%20width%3D%22154.09375%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EClaim%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Ledger%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-J-25%22%20transform%3D%22translate(2293.34375%2C%20161.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-88.96875%22%20y%3D%22-24.5%22%20width%3D%22177.9375%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ESynthesis%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Report%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-K-27%22%20transform%3D%22translate(2511.6484375%2C%20161.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-79.3359375%22%20y%3D%22-24.5%22%20width%3D%22158.671875%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EClaim%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Verifier%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-L-29%22%20transform%3D%22translate(2683.1875%2C%20161.50312423706055)%22%3E%3Cpolygon%20points%3D%2242.203125%2C0%2084.40625%2C-42.203125%2042.203125%2C-84.40625%200%2C-42.203125%22%20class%3D%22label-container%22%20transform%3D%22translate(-41.703125%2C%2042.203125)%22%3E%3C%2Fpolygon%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPass%3F%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-M-31%22%20transform%3D%22translate(2919.5%2C%2062.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-117.453125%22%20y%3D%22-24.5%22%20width%3D%22234.90625%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ERevise%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20%2F%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Label%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Inference%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-N-35%22%20transform%3D%22translate(2919.5%2C%20161.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-88.859375%22%20y%3D%22-24.5%22%20width%3D%22177.71875%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EEvidence%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Bundle%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-O-37%22%20transform%3D%22translate(3192.0234375%2C%2062.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-105.0703125%22%20y%3D%22-24.5%22%20width%3D%22210.140625%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EMeatyWiki%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Writeback%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-P-39%22%20transform%3D%22translate(3192.0234375%2C%20161.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-99.1796875%22%20y%3D%22-24.5%22%20width%3D%22198.359375%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ESkillBOM%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Candidate%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-Q-41%22%20transform%3D%22translate(3192.0234375%2C%20260.50312423706055)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-78.8125%22%20y%3D%22-24.5%22%20width%3D%22157.625%22%20height%3D%2249%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-9.5)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ECCDash%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Event%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E)

### Core object flow

| Stage | Input | Output | Primary owner |
| --- | --- | --- | --- |
| Capture | Raw note, voice transcript, clipped link, question | `raw_idea.md` | Intake Curator |
| Intenting | Raw idea | `intent.yaml`, `ibom.yaml` | Intent Curator |
| Planning | Intent + I-BOM | `intenttree_node.yaml`, `research_brief.md`, `swarm_plan.yaml` | Control Plane Router |
| Discovery | Research brief | `source_candidates.yaml` | Source Scout |
| Ingestion | URLs, PDFs, docs, notes | `source_card.md` | Source Carder |
| Extraction | Source cards | `extraction_card.yaml` | Extractor |
| Claim mapping | Extractions | `claim_ledger.yaml` | Claim Mapper |
| Synthesis | Claim ledger + source cards | `report.md` | Synthesizer |
| Review | Report + claim ledger | `review_packet.yaml` | Critic / Council |
| Verification | Report + claim ledger | `verification.yaml` | Claim Auditor |
| Writeback | Evidence bundle | MeatyWiki page, SkillBOM candidate, CCDash event | Librarian / Skill Curator / Telemetry Logger |

---

## 5. MVP folder structure

```
research-foundry/
  README.md
  foundry.yaml
  .gitignore
  .env.example

  config/
    governance.yaml
    model_profiles.yaml
    routing_rules.yaml
    tools.yaml
    claim_policy.yaml

  schemas/
    raw_idea.schema.yaml
    research_intent.schema.yaml
    ibom.schema.yaml
    intenttree_node.schema.yaml
    research_brief.schema.yaml
    swarm_plan.schema.yaml
    source_card.schema.yaml
    extraction_card.schema.yaml
    claim_ledger.schema.yaml
    evidence_bundle.schema.yaml
    report_frontmatter.schema.yaml
    review_packet.schema.yaml
    meatywiki_writeback.schema.yaml
    skillbom_candidate.schema.yaml
    ccdash_event.schema.yaml
    routing_decision.schema.yaml

  templates/
    raw_idea.md
    research_brief.md
    source_card.md
    report.md
    meatywiki_source_note.md
    meatywiki_decision_record.md
    skillbom_candidate.md
    ccdash_event.yaml

  inbox/
    raw_ideas/
    clips/
    imports/
    voice_transcripts/

  intents/
    active/
    paused/
    completed/
    archived/

  iboms/
    active/
    snapshots/

  intenttree/
    research_foundry_tree.yaml
    nodes/

  runs/
    rf_run_YYYYMMDD_slug/
      run.yaml
      routing_decision.yaml
      research_brief.md
      swarm_plan.yaml
      source_candidates.yaml
      sources/
        src_*.md
      extractions/
        ext_*.yaml
      claims/
        claim_ledger.yaml
        contradiction_log.yaml
        inference_log.yaml
      reports/
        report_draft.md
        report_final.md
      reviews/
        critic_review.yaml
        council_review.yaml
        governance_review.yaml
      evidence_bundle.yaml
      writebacks/
        meatywiki_writeback.md
        skillbom_candidate.md
        ccdash_event.yaml
      telemetry/
        token_costs.yaml
        tool_calls.yaml
        run_trace.jsonl

  registries/
    agents.yaml
    tools.yaml
    source_index.yaml
    claim_index.yaml
    skillbom_index.yaml
    report_index.yaml
    run_index.yaml

  meatywiki/
    concepts/
    projects/research-foundry.md
    sources/
    decisions/
    patterns/

  skillmeat/
    skillboms/
    prompts/
    context_packs/
    evals/
    tool_profiles/

  ccdash/
    events/
    daily/
    summaries/

  .claude/
    settings.json
    agents/
      rf_intake_curator.md
      rf_source_scout.md
      rf_source_carder.md
      rf_claim_auditor.md
      rf_synthesizer.md
      rf_governance_officer.md
    skills/
      research-foundry/
        SKILL.md
        scripts/
        templates/

  opencode/
    agents/
    sessions/

  src/
    research_foundry/
      cli.py
      config.py
      schemas.py
      validators/
      adapters/
        claude_agent_sdk.py
        gpt_researcher.py
        paperqa2.py
        opencode.py
        litellm_router.py
      services/
        capture.py
        planning.py
        source_cards.py
        extraction.py
        claim_mapping.py
        synthesis.py
        verification.py
        writeback.py
        telemetry.py
        governance.py

  tests/
    fixtures/
    test_schema_validation.py
    test_claim_verifier.py
    test_governance_profiles.py
    test_writebacks.py
```

### Folder rules

| Rule | Rationale |
| --- | --- |
| `runs/` is append-first and mostly immutable | Preserves traceability and reproducibility |
| `registries/` indexes artifacts but does not replace them | Keeps Markdown/YAML source of truth |
| `meatywiki/`, `skillmeat/`, and `ccdash/` are local mirrors | Allows later sync to dedicated repos/tools |
| `.env*` files are always gitignored | Prevents credential leakage |
| Work-sensitive runs must not write to personal MeatyWiki by default | Prevents cross-boundary contamination |

---

## 6. Core YAML schemas

### 6.1 `foundry.yaml`

```YAML
schema_version: 0.1
foundry:
  id: rf_nick_research_foundry
  name: "Nick's Research Foundry"
  owner: "Nick Miethe"
  default_profile: personal
  storage_mode: markdown_yaml_first
  timezone: America/New_York

  systems:
    meatywiki_path: meatywiki/
    skillmeat_path: skillmeat/
    ccdash_path: ccdash/
    intenttree_path: intenttree/research_foundry_tree.yaml

  defaults:
    claim_policy: config/claim_policy.yaml
    governance_policy: config/governance.yaml
    model_profiles: config/model_profiles.yaml
    routing_rules: config/routing_rules.yaml

  adapters:
    claude_agent_sdk: enabled
    claude_code: enabled
    opencode: optional
    gpt_researcher: optional
    paperqa2: optional
    litellm: optional
```

---

### 6.2 Raw idea schema

```YAML
raw_idea:
  id: raw_YYYYMMDD_HHMM_slug
  created_at: datetime
  captured_from: chat|voice|note|clip|email|meeting|manual
  title: string
  body: string
  tags: [string]
  sensitivity: public|personal|work_sensitive|client_sensitive
  urgency: low|medium|high
  research_potential: unknown|low|medium|high
  suggested_project: Research Foundry|Agentic OS|unassigned
  initial_questions:
    - string
  attachments:
    - path_or_uri: string
      type: url|pdf|markdown|image|audio|other
  triage:
    status: untriaged|converted_to_intent|archived|duplicate
    intent_id: string|null
```

---

### 6.3 Research intent schema

This extends the Agentic OS intent model. Intent already captures desired outcome, constraints, stakeholders, success criteria, risks, and I-BOM fields.

```YAML
research_intent:
  id: intent_research_YYYYMMDD_slug
  title: string
  owner: string
  created_at: date
  status: proposed|active|paused|completed|archived
  type: research

  objective: string
  motivation: string
  desired_output:
    artifact_type: evidence_bundle|report|brief|source_note|market_scan|technical_memo|literature_review
    audience: self|public|executive|technical|client|work_internal
    depth: skim|standard|deep|exhaustive

  scope:
    in:
      - string
    out:
      - string

  research_questions:
    primary:
      - string
    secondary:
      - string

  constraints:
    hard:
      - "Every material claim must map to source_card_id or be labeled inference/speculation."
    soft:
      - string

  success_criteria:
    - criterion: string
      measure: string

  governance:
    sensitivity: public|personal|work_sensitive|client_sensitive
    key_profile_allowed: personal|work_approved|client_approved|offline_only
    requires_human_review: boolean
    allowed_writebacks:
      - meatywiki_personal
      - meatywiki_work
      - skillmeat_personal
      - ccdash_local

  ibom_ref: ibom_research_YYYYMMDD_slug
  intenttree_node_ref: tree_rf_YYYYMMDD_slug
```

---

### 6.4 I-BOM schema for research

```YAML
ibom:
  id: ibom_research_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  created_at: datetime
  snapshot_status: draft|locked|superseded

  context_snapshot: string

  sources_seeded:
    - id: seed_001
      kind: url|pdf|note|book|paper|repo|conversation|unknown
      locator: string
      sensitivity: public|personal|work_sensitive|client_sensitive
      notes: string

  assumptions:
    - id: asm_001
      text: string
      risk: low|medium|high
      should_verify: boolean

  known_constraints:
    - string

  tools_available:
    - claude_code
    - claude_agent_sdk
    - opencode
    - gpt_researcher
    - paperqa2
    - litellm

  model_policy:
    extraction_profile: rf_extract_cheap
    synthesis_profile: rf_synthesize_deep
    verification_profile: rf_verify_balanced

  relevant_memory:
    - meatywiki_ref: string
      reason: string

  open_questions:
    - string

  security_boundaries:
    - "Do not mix personal and work-provided API keys in one run."
    - "Do not send work-sensitive source content to non-approved providers."
```

---

### 6.5 IntentTree research node

IntentTree preserves multiple levels of abstraction so agents can execute leaf nodes while retaining the larger story.

```YAML
intenttree_node:
  node_id: tree_rf_YYYYMMDD_slug
  level: L4
  title: string
  parent: tree_research_foundry
  intent_id: intent_research_YYYYMMDD_slug
  status: ready|active|blocked|completed|archived
  priority: low|medium|high
  dependencies:
    - node_id: string
  blockers:
    - string
  required_agent_postures:
    - researcher
    - critic
    - synthesizer
  required_skill_stack:
    - skill_research_swarm_v0
  required_context:
    - ibom_research_YYYYMMDD_slug
  expected_artifacts:
    - evidence_bundle
    - report
    - meatywiki_writeback
    - ccdash_event
  success_criteria:
    - "Claim verifier passes."
    - "Evidence bundle generated."
    - "At least one writeback candidate generated."
  reusable_output_candidates:
    - source_card_template
    - research_prompt
    - claim_verifier_rule
```

---

### 6.6 Research brief

```YAML
research_brief:
  id: brief_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  title: string
  audience: self|technical|executive|public|client
  research_depth: skim|standard|deep|exhaustive

  questions:
    primary:
      - id: rq_001
        question: string
    secondary:
      - id: rq_002
        question: string

  source_strategy:
    include_source_types:
      - official_docs
      - peer_reviewed_papers
      - standards
      - reputable_news
      - vendor_docs
      - repo_readmes
      - personal_notes
    exclude_source_types:
      - unsourced_social_posts
      - SEO_content_farms
    freshness:
      required: true
      max_age_days: 180
      exceptions:
        - foundational_theory
        - historical_background

  output_requirements:
    format: markdown
    include_claim_ledger: true
    include_source_cards: true
    include_inference_log: true
    include_open_questions: true
```

---

### 6.7 Swarm plan

```YAML
swarm_plan:
  id: swarm_YYYYMMDD_slug
  brief_id: brief_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  created_at: datetime
  status: planned|running|completed|failed|cancelled

  budget:
    max_cost_usd: 5.00
    max_runtime_minutes: 60
    extraction_model_profile: rf_extract_cheap
    synthesis_model_profile: rf_synthesize_deep
    verification_model_profile: rf_verify_balanced

  agents:
    - role: source_scout
      posture: researcher
      tool: gpt_researcher
      model_profile: rf_extract_cheap
      task: "Find candidate sources and produce source_candidates.yaml."
    - role: paper_analyst
      posture: researcher
      tool: paperqa2
      model_profile: rf_extract_cheap
      task: "Answer research questions over local scientific PDFs."
    - role: source_carder
      posture: operator
      tool: claude_agent_sdk
      model_profile: rf_extract_cheap
      task: "Convert sources into source cards."
    - role: claim_mapper
      posture: critic
      tool: claude_agent_sdk
      model_profile: rf_verify_balanced
      task: "Map extracted findings to claims."
    - role: synthesis_lead
      posture: synthesizer
      tool: claude_agent_sdk
      model_profile: rf_synthesize_deep
      task: "Write report only from supported claims and labeled inferences."
    - role: governance_officer
      posture: red_team
      tool: deterministic_validator
      model_profile: none
      task: "Block invalid key/data/writeback combinations."

  required_outputs:
    - source_candidates.yaml
    - source_cards
    - extraction_cards
    - claim_ledger.yaml
    - report_draft.md
    - verification.yaml
    - evidence_bundle.yaml
    - ccdash_event.yaml
```

---

### 6.8 Source card

```Markdown
---
schema_version: 0.1
type: source_card
source_card_id: src_YYYYMMDD_slug_hash
created_at: datetime
created_by_agent: rf_source_carder
sensitivity: public|personal|work_sensitive|client_sensitive

source:
  title: string
  source_type: official_doc|paper|standard|repo|news|blog|book|personal_note|internal_doc|other
  locator:
    url: string|null
    file_path: string|null
    doi: string|null
    repo: string|null
  authors:
    - string
  publisher: string|null
  published_at: date|null
  accessed_at: datetime
  version: string|null

trust:
  source_rank: primary|secondary|tertiary|unknown
  reliability_notes: string
  known_limitations:
    - string
  conflicts_with:
    - source_card_id: string
      reason: string

usage:
  allowed_for_public_output: boolean
  allowed_for_work_output: boolean
  allowed_for_personal_meatywiki: boolean
  citation_required: true
  quote_limit_notes: string

extracted_points:
  - evidence_id: ev_001
    locator: "section/page/paragraph/timestamp"
    summary: string
    quote: string|null
    supports_potential_claims:
      - clm_pending
---
# Source Card: {{title}}

## Summary

## Key evidence

## Limitations

## Related source cards
```

---

### 6.9 Extraction card

```YAML
extraction_card:
  id: ext_YYYYMMDD_sourcehash_001
  source_card_id: src_YYYYMMDD_slug_hash
  created_at: datetime
  extractor_agent: rf_extractor
  model_profile: rf_extract_cheap

  extracted_facts:
    - evidence_id: ev_001
      text: string
      locator: string
      confidence: low|medium|high
      quote_available: boolean
      notes: string

  extracted_definitions:
    - term: string
      definition: string
      locator: string

  extracted_metrics:
    - metric_name: string
      value: string|number
      unit: string|null
      date_context: string|null
      locator: string

  contradictions_or_cautions:
    - text: string
      locator: string
```

---

### 6.10 Claim ledger

```YAML
claim_ledger:
  id: claims_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  report_ref: reports/report_draft.md
  verification_status: pending|passed|failed

  claims:
    - claim_id: clm_001
      text: string
      materiality: material|background|style
      claim_type: factual|causal|comparative|quantitative|attribution|recommendation|prediction
      status: supported|mixed|contradicted|inference|speculation|unsupported
      confidence: low|medium|high
      sources:
        - source_card_id: src_YYYYMMDD_slug_hash
          evidence_id: ev_001
          relation: supports|contradicts|context
          locator: string
      inference_basis:
        from_claims:
          - clm_001
          - clm_002
        reasoning_summary: string|null
      report_locations:
        - file: reports/report_draft.md
          heading: string
          paragraph_id: string
      reviewer_notes: string

  unresolved_questions:
    - question: string
      why_unresolved: string
      recommended_next_source: string|null
```

---

### 6.11 Evidence bundle

```YAML
evidence_bundle:
  id: bundle_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  run_id: rf_run_YYYYMMDD_slug
  created_at: datetime
  status: draft|verified|published|archived

  artifacts:
    research_brief: research_brief.md
    swarm_plan: swarm_plan.yaml
    source_cards_dir: sources/
    extraction_cards_dir: extractions/
    claim_ledger: claims/claim_ledger.yaml
    report: reports/report_final.md
    verification: reviews/verification.yaml
    ccdash_event: writebacks/ccdash_event.yaml

  counts:
    source_cards: integer
    extraction_cards: integer
    claims_total: integer
    claims_supported: integer
    claims_inference: integer
    claims_speculation: integer
    claims_unsupported: integer

  governance:
    sensitivity: public|personal|work_sensitive|client_sensitive
    approved_for_writeback: boolean
    approved_by: string|null
    approval_timestamp: datetime|null

  lineage:
    raw_idea_ids: [string]
    intent_id: string
    ibom_id: string
    intenttree_node_id: string
    skillbom_ids_used: [string]
```

---

### 6.12 Report front matter

```YAML
---
schema_version: 0.1
type: research_report
report_id: report_YYYYMMDD_slug
title: string
intent_id: intent_research_YYYYMMDD_slug
evidence_bundle_id: bundle_YYYYMMDD_slug
created_at: datetime
status: draft|verified|published|archived
audience: self|technical|executive|public|client
sensitivity: public|personal|work_sensitive|client_sensitive
claim_policy: "Every material claim maps to claim_ledger.yaml or is labeled inference/speculation."
verification_status: pending|passed|failed
---
```

Report body convention:

```Markdown
## Finding

Supported material claim. [claim:clm_001]

Analytic inference based on supported claims. **Inference:** ... [claim:clm_007]

Forward-looking idea without enough evidence. **Speculation:** ... [claim:clm_012]
```

---

### 6.13 MeatyWiki writeback

MeatyWiki stores rationale, decisions, source notes, insights, patterns, and concept lineage; it should cross-link with SkillMeat rather than duplicate operational artifacts.

```YAML
meatywiki_writeback:
  id: mwb_YYYYMMDD_slug
  evidence_bundle_id: bundle_YYYYMMDD_slug
  target_page: meatywiki/sources/source-note-slug.md
  writeback_type: source_note|concept_update|decision_record|pattern|project_update|insight
  status: proposed|approved|written|rejected

  summary: string
  key_claims:
    - claim_id: clm_001
      include: true
  links:
    source_cards:
      - src_YYYYMMDD_slug_hash
    related_pages:
      - "[[Research Foundry]]"
      - "[[Agentic Control Plane]]"

  approval:
    required: boolean
    reason: string
    approved_by: string|null
```

---

### 6.14 SkillBOM candidate

SkillMeat/SAM stores, versions, governs, and evaluates reusable stacks of agent capability; a SkillBOM includes prompts, posture, context, tools, schemas, validation, evals, failure modes, runtime metadata, and performance history.

```YAML
skillbom_candidate:
  id: skillcand_research_swarm_YYYYMMDD_slug
  name: string
  proposed_skillbom_id: skill_research_swarm_v0
  evidence_bundle_id: bundle_YYYYMMDD_slug
  status: candidate|needs_review|promoted|rejected

  purpose: string
  agent_postures:
    - researcher
    - critic
    - synthesizer
  tools_used:
    - gpt_researcher
    - paperqa2
    - claude_agent_sdk
    - litellm
  prompts:
    system: skillmeat/prompts/research_swarm_system.md
    task: skillmeat/prompts/research_swarm_task.md
  context_packs:
    - research_foundry_core
  output_schemas:
    - source_card.schema.yaml
    - claim_ledger.schema.yaml
    - evidence_bundle.schema.yaml
  validation:
    - claim_verifier_passed
    - governance_guard_passed
    - report_reviewed
  known_failure_modes:
    - source_overcollection
    - unsupported_synthesis
    - citation_mismatch
    - stale_sources
    - work_personal_boundary_leak
  performance_evidence:
    ccdash_event_id: exec_YYYYMMDD_slug
    quality_score: pending
    rework_count: integer
    estimated_cost_usd: number
```

---

### 6.15 CCDash event

```YAML
execution_event:
  event_id: exec_YYYYMMDD_slug
  timestamp: datetime
  project: Research Foundry
  intent_id: intent_research_YYYYMMDD_slug
  task_node_id: tree_rf_YYYYMMDD_slug
  run_id: rf_run_YYYYMMDD_slug

  agent_postures:
    - researcher
    - critic
    - synthesizer
    - operator
  skillbom_ids:
    - skill_research_swarm_v0

  tools:
    - claude_code
    - claude_agent_sdk
    - gpt_researcher
    - paperqa2
    - litellm

  input_artifacts:
    - inbox/raw_ideas/raw_*.md
    - intents/active/intent_*.yaml
  output_artifacts:
    - runs/rf_run_*/evidence_bundle.yaml
    - runs/rf_run_*/reports/report_final.md
    - runs/rf_run_*/writebacks/meatywiki_writeback.md
    - runs/rf_run_*/writebacks/skillbom_candidate.md

  metrics:
    source_cards_created: integer
    claims_total: integer
    claims_supported: integer
    claims_inference: integer
    claims_speculation: integer
    unsupported_claims: integer
    verification_passed: boolean
    tokens_estimated: integer
    cost_estimated_usd: number
    latency_minutes: number
    rework_count: integer
    drift_score: number
    quality_score: pending|number

  governance:
    sensitivity: public|personal|work_sensitive|client_sensitive
    key_profile_used: personal|work_approved|client_approved|offline_only
    policy_passed: boolean
    violations:
      - string

  reuse:
    meatywiki_writeback_candidate: boolean
    skillbom_candidate: boolean
    reusable_source_pack_candidate: boolean

  human_review:
    required: boolean
    status: pending|approved|rejected|not_required
    reviewer: string|null
```

---

## 7. Governance boundaries

The Governance and Evaluation layer already covers intent approval, context access, tool permissions, data handling, agent boundaries, human review, output validation, execution logs, reuse approval, memory writeback, and skill promotion/deprecation. Research Foundry operationalizes that with hard gates.

### 7.1 Key profiles

```YAML
key_profiles:
  personal:
    allowed_use:
      - personal_research
      - public_research
      - personal_meatywiki
    forbidden_use:
      - employer_confidential_data
      - client_confidential_data
    env_file: .env.personal
    gitignored: true

  work_approved:
    allowed_use:
      - work_internal_research
      - approved_work_tools
    forbidden_use:
      - personal_cost_avoidance
      - personal_publication_without_review
      - non_approved_model_endpoints
      - personal_meatywiki_writeback_without_sanitization
    env_file: .env.work
    gitignored: true
    requires_profile_flag: true

  client_approved:
    allowed_use:
      - explicit_client_authorized_research
    forbidden_use:
      - cross_client_reuse
      - public_writeback
      - personal_writeback
    env_file: .env.client
    gitignored: true
    requires_human_review: true

  offline_only:
    allowed_use:
      - local_documents
      - local_models
      - no_network
    forbidden_use:
      - external_llm_calls
      - external_search
```

### 7.2 Non-negotiable policy rules

```YAML
policy_rules:
  - id: no_work_keys_for_personal_runs
    severity: block
    condition: "intent.governance.key_profile_allowed == personal AND runtime.key_profile == work_approved"
    message: "Work-provided keys cannot be used for personal research."

  - id: no_work_sensitive_to_unapproved_provider
    severity: block
    condition: "run.sensitivity in [work_sensitive, client_sensitive] AND model.provider not in approved_work_providers"
    message: "Sensitive work/client data cannot be sent to non-approved providers."

  - id: no_mixed_personal_work_bundle
    severity: block
    condition: "evidence_bundle contains both personal and work_sensitive sources"
    message: "Personal and work-sensitive source cards cannot be mixed in one evidence bundle."

  - id: no_secret_in_markdown
    severity: block
    condition: "file_content matches secret_pattern"
    message: "Potential secret detected in Markdown/YAML artifact."

  - id: work_writeback_requires_review
    severity: require_approval
    condition: "writeback.target contains personal_meatywiki AND source.sensitivity == work_sensitive"
    message: "Work-sensitive content requires sanitization and approval before personal MeatyWiki writeback."

  - id: material_claims_must_be_mapped
    severity: block
    condition: "report contains material claim without claim_id OR claim.status == unsupported"
    message: "Every material claim must map to a source card or be labeled inference/speculation."
```

### 7.3 Claude Code hooks caution

Use hooks for deterministic checks, not blind trust. Claude’s own docs warn that command hooks run with the user’s full system permissions and can modify, delete, or access files; they recommend validating inputs, quoting variables, blocking path traversal, using absolute paths, and skipping sensitive files like `.env` and `.git`. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude API Docs](https://docs.anthropic.com/en/docs/claude-code/hooks)

Recommended hooks:

```JSON
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python -m research_foundry.validators.guard_pretool"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python -m research_foundry.validators.scan_artifact"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m research_foundry.telemetry.emit_ccdash_event"
          }
        ]
      }
    ]
  }
}
```

---

## 8. Model routing

### 8.1 Routing policy

| Work type | Model tier | Reason |
| --- | --- | --- |
| Source discovery | cheap/free or search-native | High volume, low synthesis burden |
| Source card creation | cheap/free | Mostly extraction and normalization |
| Deduplication | cheap/free | Deterministic-ish text comparison |
| Claim mapping | cheap/balanced | Needs accuracy but not maximal creativity |
| Contradiction detection | balanced/deep | Requires judgment across sources |
| Final synthesis | expensive/deep | High-leverage reasoning and structure |
| Executive translation | expensive/deep or strong standard | Nuance + compression |
| YAML validation | deterministic/no LLM | Should not spend tokens |
| Governance guard | deterministic/no LLM by default | Must be enforceable |

### 8.2 `model_profiles.yaml`

```YAML
model_profiles:
  rf_extract_free:
    purpose: "Local/free extraction and formatting"
    tier: cheap_free
    allowed_for:
      - source_carding
      - simple_extraction
      - tagging
      - dedupe
    preferred:
      - provider: ollama
        model: local-small-instruct
      - provider: openrouter
        model: free-or-low-cost-extraction-model
    max_tokens: 4096
    temperature: 0.1

  rf_extract_cheap:
    purpose: "Cheap API extraction when local quality is insufficient"
    tier: cheap
    allowed_for:
      - source_carding
      - extraction_cards
      - initial_claim_mapping
    preferred:
      - provider: anthropic
        model: haiku_or_equivalent
      - provider: openai
        model: mini_or_equivalent
      - provider: google
        model: flash_or_equivalent
    temperature: 0.1

  rf_verify_balanced:
    purpose: "Claim verification, contradiction detection, governance review"
    tier: balanced
    allowed_for:
      - claim_audit
      - contradiction_review
      - council_review
    preferred:
      - provider: anthropic
        model: sonnet_or_equivalent
      - provider: openai
        model: standard_reasoning_or_equivalent
    temperature: 0.0

  rf_synthesize_deep:
    purpose: "Final synthesis, high-stakes report writing, strategic framing"
    tier: expensive
    allowed_for:
      - final_report
      - executive_synthesis
      - deep_literature_synthesis
    preferred:
      - provider: anthropic
        model: opus_or_equivalent
      - provider: openai
        model: high_reasoning_or_equivalent
      - provider: google
        model: pro_or_equivalent
    temperature: 0.2
```

### 8.3 LiteLLM proxy example

```YAML
model_list:
  - model_name: rf-extract
    litellm_params:
      model: os.environ/RF_EXTRACT_MODEL
      api_key: os.environ/RF_EXTRACT_API_KEY
      max_budget: 2
      budget_duration: 1d

  - model_name: rf-verify
    litellm_params:
      model: os.environ/RF_VERIFY_MODEL
      api_key: os.environ/RF_VERIFY_API_KEY
      max_budget: 5
      budget_duration: 1d

  - model_name: rf-synthesize
    litellm_params:
      model: os.environ/RF_SYNTH_MODEL
      api_key: os.environ/RF_SYNTH_API_KEY
      max_budget: 10
      budget_duration: 1d

router_settings:
  routing_strategy: simple-shuffle
  redis_host: os.environ/REDIS_HOST
  provider_budget_config:
    anthropic:
      budget_limit: 20
      time_period: 1d
    openai:
      budget_limit: 20
      time_period: 1d
    openrouter:
      budget_limit: 5
      time_period: 1d

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

---

## 9. Agent roles

Agent postures define cognitive style and should be reusable, evaluated, and composable; the existing posture catalog includes Architect, Implementer, Critic, Researcher, Strategist, Editor, Operator, Synthesizer, Red Team, and Executive Translator.

| Agent role | Posture | Model tier | Main outputs | Tools |
| --- | --- | --- | --- | --- |
| **Intake Curator** | Operator + Synthesizer | cheap | `raw_idea.md`, suggested intent | Claude Code / Agent SDK |
| **Intent Curator** | Architect | cheap/balanced | `research_intent.yaml`, `ibom.yaml` | Claude Agent SDK |
| **Control Plane Router** | Architect + Operator | balanced | `routing_decision.yaml`, `swarm_plan.yaml` | Claude Agent SDK |
| **Source Scout** | Researcher | cheap | `source_candidates.yaml` | GPT Researcher, web/search adapters |
| **Paper Analyst** | Researcher | cheap/balanced | paper-grounded answers, source cards | PaperQA2 |
| **Source Carder** | Operator | cheap/free | `source_card.md` files | Claude Agent SDK, local models |
| **Extractor** | Researcher | cheap/free | `extraction_card.yaml` | local model, LiteLLM |
| **Claim Mapper** | Critic | balanced | `claim_ledger.yaml` | Claude Agent SDK |
| **Contradiction Hunter** | Red Team | balanced/deep | `contradiction_log.yaml` | PaperQA2, GPT Researcher, Claude |
| **Synthesis Lead** | Synthesizer | expensive | `report_draft.md` | Claude Agent SDK |
| **Executive Translator** | Executive Translator | expensive | executive brief/report variant | Claude Agent SDK |
| **Claim Auditor** | Critic | deterministic + balanced | `verification.yaml` | schema validator, Claude |
| **Governance Officer** | Red Team + Operator | deterministic first | policy pass/fail | local validators, hooks |
| **MeatyWiki Librarian** | Editor + Operator | cheap | writeback candidate | Claude Code |
| **SkillBOM Curator** | Architect + Operator | balanced | SkillBOM candidate | Claude Code |
| **CCDash Logger** | Operator | deterministic | telemetry event | local CLI |

### Minimal Claude subagent front matter

```Markdown
---
name: rf_claim_auditor
description: Verifies that every material claim in a research report maps to a claim ledger entry backed by source cards, or is labeled inference/speculation.
tools:
  - Read
  - Grep
  - Glob
  - Bash
permission_mode: dontAsk
model: rf-verify
---

You are the Claim Auditor for Nick's Research Foundry.

Rules:
1. Do not add new claims.
2. Do not repair unsupported claims silently.
3. Produce verification.yaml.
4. Mark report verification failed if any material claim is unsupported.
5. Treat unlabeled causal, comparative, attribution, or quantitative statements as material claims.
```

---

## 10. CLI command design

Use command group `rf`.

### 10.1 Initialize

```Bash
rf init ./research-foundry \
  --profile personal \
  --with-claude \
  --with-litellm \
  --with-gpt-researcher \
  --with-paperqa2
```

Creates folder structure, templates, schemas, `.env.example`, `.gitignore`, governance policy, and default model profiles.

---

### 10.2 Capture raw idea

```Bash
rf capture "Research how agentic research workflows should handle evidence bundles" \
  --from manual \
  --sensitivity personal \
  --tag agentic-os \
  --tag research-foundry
```

Outputs:

```
inbox/raw_ideas/raw_20260612_agentic_research_workflows.md
```

---

### 10.3 Triage into intent and I-BOM

```Bash
rf triage inbox/raw_ideas/raw_20260612_agentic_research_workflows.md \
  --create-intent \
  --create-ibom \
  --create-tree-node
```

Outputs:

```
intents/active/intent_research_20260612_agentic_research_workflows.yaml
iboms/active/ibom_research_20260612_agentic_research_workflows.yaml
intenttree/nodes/tree_rf_20260612_agentic_research_workflows.yaml
```

---

### 10.4 Plan swarm

```Bash
rf plan intent_research_20260612_agentic_research_workflows \
  --depth deep \
  --audience technical \
  --max-cost 5 \
  --freshness 180d
```

Outputs:

```
runs/rf_run_20260612_agentic_research_workflows/research_brief.md
runs/rf_run_20260612_agentic_research_workflows/swarm_plan.yaml
runs/rf_run_20260612_agentic_research_workflows/routing_decision.yaml
```

---

### 10.5 Ingest source manually

```Bash
rf ingest ./papers/example.pdf \
  --source-type paper \
  --sensitivity personal \
  --run rf_run_20260612_agentic_research_workflows
```

or:

```Bash
rf ingest "https://example.com/source" \
  --source-type official_doc \
  --sensitivity public \
  --run rf_run_20260612_agentic_research_workflows
```

Outputs a source card in the run’s `sources/` folder.

---

### 10.6 Run swarm

```Bash
rf swarm run rf_run_20260612_agentic_research_workflows \
  --profile personal \
  --extract-model rf_extract_cheap \
  --synthesis-model rf_synthesize_deep
```

Runs enabled adapters according to `swarm_plan.yaml`.

---

### 10.7 Extract

```Bash
rf extract rf_run_20260612_agentic_research_workflows \
  --source-cards runs/rf_run_*/sources \
  --model-profile rf_extract_cheap
```

Creates extraction cards.

---

### 10.8 Build claim ledger

```Bash
rf claim-map rf_run_20260612_agentic_research_workflows \
  --from extractions \
  --out claims/claim_ledger.yaml
```

---

### 10.9 Synthesize report

```Bash
rf synthesize rf_run_20260612_agentic_research_workflows \
  --report reports/report_draft.md \
  --model-profile rf_synthesize_deep
```

Hard rule: synthesis agent can only cite claim IDs already present in `claim_ledger.yaml`, or label a sentence as inference/speculation.

---

### 10.10 Verify report

```Bash
rf verify rf_run_20260612_agentic_research_workflows \
  --report reports/report_draft.md \
  --claim-ledger claims/claim_ledger.yaml \
  --fail-on-unsupported
```

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Pass |
| 2 | Schema validation failed |
| 3 | Governance policy blocked |
| 4 | Unsupported material claim |
| 5 | Budget exceeded |
| 6 | Adapter/tool failure |
| 7 | Human review required |

---

### 10.11 Council review

```Bash
rf council rf_run_20260612_agentic_research_workflows \
  --roles critic,domain_reviewer,governance_officer,executive_translator \
  --vote approve-concern-block
```

Outputs:

```
reviews/council_review.yaml
```

---

### 10.12 Publish evidence bundle

```Bash
rf bundle rf_run_20260612_agentic_research_workflows \
  --verify \
  --out evidence_bundle.yaml
```

---

### 10.13 Writebacks

```Bash
rf writeback rf_run_20260612_agentic_research_workflows \
  --targets meatywiki,skillmeat,ccdash \
  --require-review
```

Outputs:

```
writebacks/meatywiki_writeback.md
writebacks/skillbom_candidate.md
writebacks/ccdash_event.yaml
```

---

### 10.14 Promotion

```Bash
rf skillbom propose rf_run_20260612_agentic_research_workflows
rf skillbom promote skillcand_research_swarm_20260612_agentic_research_workflows \
  --reviewer Nick
```

---

### 10.15 Utility commands

```Bash
rf status
rf doctor
rf guard check --profile work_approved
rf redact runs/rf_run_*/ --target public
rf cost runs/rf_run_*/
rf index rebuild
rf ccdash summarize --period daily
```

---

## 11. Execution loop

The Execution Engine’s canonical loop is: capture raw input, convert to intent, generate/update I-BOM, place into IntentTree, select next node, choose posture and SkillBOM, execute, validate, record CCDash evidence, update MeatyWiki and SkillMeat, and route the next move. Research Foundry specializes that into this loop:

```
1. Capture raw idea.
2. Convert idea into research intent.
3. Build or update research I-BOM.
4. Create IntentTree research node.
5. Generate routing decision.
6. Generate research brief.
7. Plan swarm.
8. Run governance preflight.
9. Discover sources.
10. Create source cards.
11. Extract evidence.
12. Build claim ledger.
13. Detect contradictions and gaps.
14. Synthesize report.
15. Verify every material claim.
16. Run council/human review if needed.
17. Publish evidence bundle.
18. Write back to MeatyWiki.
19. Generate SkillBOM candidate.
20. Emit CCDash telemetry.
21. Route next research move.
```

### Pseudocode

```Python
def run_research_foundry_loop(raw_idea_path: str, profile: str):
    raw = capture_or_load(raw_idea_path)
    intent = triage_to_intent(raw)
    ibom = build_ibom(intent, raw)
    node = place_in_intenttree(intent, ibom)

    routing = control_plane_route(intent, ibom, node)
    guard_preflight(intent, ibom, routing, profile)

    run = create_run(intent, routing)
    brief = create_research_brief(intent, ibom)
    swarm = create_swarm_plan(brief, routing)

    candidates = discover_sources(swarm)
    source_cards = create_source_cards(candidates)
    extractions = extract_evidence(source_cards)
    claim_ledger = build_claim_ledger(extractions)

    contradictions = find_contradictions(claim_ledger, source_cards)
    draft = synthesize_report(claim_ledger, contradictions)

    verification = verify_report_claims(draft, claim_ledger)
    if not verification.passed:
        draft = revise_or_label_inferences(draft, verification)
        verification = verify_report_claims(draft, claim_ledger)

    bundle = publish_evidence_bundle(run, source_cards, extractions, claim_ledger, draft, verification)

    writeback_meatywiki(bundle)
    propose_skillbom(bundle)
    emit_ccdash_event(bundle)

    return route_next_move(bundle)
```

---

## 12. Claim verification policy

### 12.1 Material claim definition

A **material claim** is any statement that a reader could reasonably rely on as true, especially:

| Claim type | Example |
| --- | --- |
| Factual | “Tool X supports local documents.” |
| Quantitative | “The benchmark used 1,000 queries.” |
| Comparative | “A is more accurate than B.” |
| Causal | “This policy reduces leakage.” |
| Attribution | “The vendor says this feature exists.” |
| Recommendation | “Use PaperQA2 for scientific PDFs.” |
| Prediction | “This pattern will likely become reusable.” |

### 12.2 Allowed claim statuses

```YAML
allowed_claim_statuses:
  supported:
    meaning: "Directly supported by one or more source cards."
    report_label_required: false

  mixed:
    meaning: "Sources disagree or support only part of the claim."
    report_label_required: true
    label: "Mixed evidence"

  contradicted:
    meaning: "Evidence contradicts the claim."
    report_label_required: true
    label: "Contradicted / do not use as finding"

  inference:
    meaning: "Reasonable synthesis from supported claims, but not directly stated by sources."
    report_label_required: true
    label: "Inference"

  speculation:
    meaning: "Forward-looking or insufficiently evidenced idea."
    report_label_required: true
    label: "Speculation"

  unsupported:
    meaning: "Material claim lacks source or proper label."
    report_label_required: true
    build_status: fail
```

### 12.3 Report verifier checks

```YAML
verifier_checks:
  - id: report_has_frontmatter
    severity: error

  - id: all_claim_ids_exist
    severity: error

  - id: material_claims_have_claim_ids
    severity: error

  - id: supported_claims_have_source_cards
    severity: error

  - id: source_cards_have_locators
    severity: warning

  - id: inferences_have_basis
    severity: error

  - id: speculation_is_labeled
    severity: error

  - id: unsupported_claims_block_publish
    severity: error

  - id: work_sensitive_claims_block_public_report
    severity: error
```

---

## 13. Adapter contracts

### 13.1 GPT Researcher adapter

Use for:

* broad web scans,
* market scans,
* tool landscape summaries,
* source discovery,
* first-pass reports that are then decomposed into source cards.

Do **not** treat GPT Researcher’s final report as the final Research Foundry report. Treat it as source discovery + draft input. GPT Researcher can produce cited deep research reports and supports web/local/hybrid research, but Research Foundry’s claim ledger remains the authority. [![](https://www.google.com/s2/favicons?domain=https://gptr.dev&sz=128)GPT Researcher](https://gptr.dev/)

```YAML
adapter:
  id: gpt_researcher
  type: research_discovery
  inputs:
    - research_brief.md
  outputs:
    - source_candidates.yaml
    - gpt_researcher_raw_report.md
  allowed_profiles:
    - personal
    - work_approved_if_provider_approved
  postprocessing_required:
    - source_card_generation
    - claim_ledger_mapping
```

### 13.2 PaperQA2 adapter

Use for:

* scientific literature,
* local PDF/text corpora,
* citation-grounded answers,
* contradiction search across papers.

```YAML
adapter:
  id: paperqa2
  type: scientific_rag
  inputs:
    - research_questions
    - local_pdf_dir
  outputs:
    - paper_answers.yaml
    - source_cards
    - extraction_cards
  allowed_profiles:
    - personal
    - offline_only
    - work_approved_if_docs_are_approved
  postprocessing_required:
    - claim_ledger_mapping
    - locator_validation
```

### 13.3 Claude Agent SDK adapter

Use for:

* generating structured YAML,
* running subagents,
* reading/writing repo artifacts,
* controlled claim mapping,
* synthesis,
* writeback generation.

```YAML
adapter:
  id: claude_agent_sdk
  type: orchestration
  inputs:
    - prompt
    - allowed_tools
    - model_profile
    - output_schema
  outputs:
    - structured_artifact
    - session_trace
  required_controls:
    - permission_mode
    - disallowed_tools_for_sensitive_runs
    - setting_sources
    - governance_preflight
```

### 13.4 OpenCode adapter

Use for:

* local codebase edits,
* alternative/open-source agent runs,
* parallel implementation sessions,
* privacy-sensitive local development where appropriate.

```YAML
adapter:
  id: opencode
  type: code_agent
  inputs:
    - task_prompt
    - model_profile
    - repo_path
  outputs:
    - session_summary
    - changed_files
    - run_trace
  required_controls:
    - no_secret_write
    - git_diff_review
    - ccdash_event
```

### 13.5 Council adapter

Use for:

* high-impact report review,
* architecture decisions,
* weak-claim detection,
* governance review,
* executive framing review.

```YAML
council_review:
  id: council_YYYYMMDD_slug
  evidence_bundle_id: bundle_YYYYMMDD_slug
  voting:
    allowed_votes:
      - approve
      - concern
      - block
  members:
    - role: domain_reviewer
      posture: researcher
    - role: claim_critic
      posture: critic
    - role: governance_officer
      posture: red_team
    - role: executive_translator
      posture: executive_translator
  output:
    decision: approve|revise|required_block
    concerns:
      - concern_id: string
        severity: low|medium|high|blocker
        text: string
        required_fix: string
```

---

## 14. Control plane routing

The Agentic Control Plane chooses the next task node, abstraction level, posture, SkillBOM, context packs, tools, approval path, and writebacks. Research Foundry’s routing decision should look like this:

```YAML
routing_decision:
  id: route_YYYYMMDD_slug
  intent_id: intent_research_YYYYMMDD_slug
  active_node_id: tree_rf_YYYYMMDD_slug
  selected_abstraction_level: L4
  selected_posture_chain:
    - researcher
    - critic
    - synthesizer
    - governance_officer
  selected_skillbom: skill_research_swarm_v0
  selected_context_packs:
    - research_foundry_core
    - agentic_os_core
  selected_tools:
    - gpt_researcher
    - paperqa2
    - claude_agent_sdk
    - litellm
  human_required: true
  rationale: >
    Topic requires source-backed synthesis and may generate reusable research
    workflow patterns. Use cheap extraction, deep synthesis, and claim audit.
  expected_output: evidence_bundle
  validation:
    - schema_validation
    - governance_guard
    - claim_verifier
    - council_review_optional
  writebacks:
    - target: meatywiki
      type: source_note
    - target: skillmeat
      type: skillbom_candidate
    - target: ccdash
      type: execution_event
```

---

## 15. MVP success criteria

| Criterion | Measure |
| --- | --- |
| Raw idea becomes structured research intent | `rf capture` + `rf triage` produce valid YAML |
| Research swarm can be planned | `rf plan` creates research brief, routing decision, and swarm plan |
| Source cards are created | At least 5 source cards from mixed source types |
| Claims are traceable | 100% of material claims are mapped or labeled inference/speculation |
| Report verifies | `rf verify` exits 0 before final publication |
| Evidence bundle is durable | `evidence_bundle.yaml` references all run artifacts |
| MeatyWiki writeback exists | At least one source note or concept update candidate |
| SkillBOM candidate exists | At least one reusable workflow candidate produced |
| CCDash telemetry exists | One execution event emitted per run |
| Governance boundaries hold | Work/personal key mixing is blocked by `rf guard` |

---

## 16. Seven-day MVP plan

### Day 1 — Repo scaffold and schemas

**Goal:** Create the Markdown/YAML substrate.

Deliverables:

* Folder structure.
* `foundry.yaml`.
* Core schemas for raw idea, research intent, I-BOM, source card, claim ledger, evidence bundle, CCDash event.
* `.gitignore`, `.env.example`, `README.md`.

Commands to prove:

```Bash
rf init ./research-foundry --profile personal
rf doctor
rf schema validate foundry.yaml
```

Acceptance:

* Repo initializes cleanly.
* All templates validate.
* Secrets are ignored.

---

### Day 2 — Capture, triage, and IntentTree

**Goal:** Turn a raw idea into an intent/I-BOM/tree node.

Deliverables:

* `rf capture`.
* `rf triage`.
* `rf intent show`.
* `rf tree add-node`.
* Templates for research intent and I-BOM.

Commands to prove:

```Bash
rf capture "Research evidence bundle patterns for agentic workflows" --sensitivity personal
rf triage inbox/raw_ideas/raw_*.md --create-intent --create-ibom --create-tree-node
```

Acceptance:

* One raw idea becomes three linked artifacts.
* IntentTree node references intent and expected outputs.

---

### Day 3 — Source cards and extraction

**Goal:** Ingest sources and create normalized source cards.

Deliverables:

* `rf ingest`.
* `rf source-card create`.
* `rf extract`.
* Source index.
* Extraction card schema.

Commands to prove:

```Bash
rf ingest ./examples/source.pdf --source-type paper --sensitivity personal --run rf_run_demo
rf ingest "https://example.com" --source-type official_doc --sensitivity public --run rf_run_demo
rf extract rf_run_demo --model-profile rf_extract_cheap
```

Acceptance:

* Source cards include locator, sensitivity, trust notes, and extracted evidence IDs.
* Extraction cards map back to source cards.

---

### Day 4 — Tool adapters

**Goal:** Connect existing research tools without making them the source of truth.

Deliverables:

* GPT Researcher adapter.
* PaperQA2 adapter.
* Claude Agent SDK adapter stub.
* Optional OpenCode adapter stub.
* Adapter output normalization.

Commands to prove:

```Bash
rf swarm run rf_run_demo --adapters gpt_researcher,paperqa2 --dry-run
rf swarm run rf_run_demo --adapters claude_agent_sdk --profile personal
```

Acceptance:

* Adapter outputs become source candidates, source cards, or extraction cards.
* Raw adapter output is stored under `run_trace` but not treated as verified.

---

### Day 5 — Claim ledger and report verifier

**Goal:** Enforce claim traceability.

Deliverables:

* `rf claim-map`.
* `rf synthesize`.
* `rf verify`.
* Claim policy.
* Failure report for unsupported claims.

Commands to prove:

```Bash
rf claim-map rf_run_demo
rf synthesize rf_run_demo --model-profile rf_synthesize_deep
rf verify rf_run_demo --fail-on-unsupported
```

Acceptance:

* Unsupported material claims fail verification.
* Inference/speculation labels pass only if properly recorded in claim ledger.

---

### Day 6 — Writebacks and telemetry

**Goal:** Complete the Agentic OS feedback loop.

Deliverables:

* MeatyWiki writeback generator.
* SkillBOM candidate generator.
* CCDash event emitter.
* `rf bundle`.
* `rf writeback`.

Commands to prove:

```Bash
rf bundle rf_run_demo --verify
rf writeback rf_run_demo --targets meatywiki,skillmeat,ccdash
rf ccdash summarize --period daily
```

Acceptance:

* `meatywiki_writeback.md`, `skillbom_candidate.md`, and `ccdash_event.yaml` are generated.
* CCDash event includes cost, claims, unsupported claims, tools, postures, and reuse candidates.

---

### Day 7 — Governance hardening and demo run

**Goal:** Run a full end-to-end research workflow safely.

Deliverables:

* `rf guard check`.
* Work/personal profile separation.
* Secret scanner.
* Council review.
* Demo evidence bundle.
* MVP README walkthrough.

Commands to prove:

```Bash
rf guard check --profile personal
rf council rf_run_demo --roles critic,governance_officer,executive_translator
rf verify rf_run_demo
rf bundle rf_run_demo --verify
```

Acceptance:

* End-to-end run completes.
* Work-provided key misuse is blocked.
* Demo report has zero unsupported material claims.
* One reusable SkillBOM candidate is ready for human review.

---

## 17. Risks and open questions

| Risk | Mitigation |
| --- | --- |
| Tool APIs and CLIs change quickly | Keep adapters thin; normalize outputs into stable YAML |
| Agents generate plausible but unsupported synthesis | Claim ledger is the authority; verifier blocks unsupported material claims |
| Source cards become too heavy | Store metadata + evidence excerpts first; avoid full-text duplication unless permitted |
| Work/personal boundary leakage | Enforce key profiles, sensitivity tags, writeback policy, and secret scanning |
| Too many agents create overhead | MVP uses role names, not necessarily separate processes for each role |
| Expensive model overuse | Route extraction to cheap/free profiles; use deep models only for synthesis/review |
| Research reports overfit to first-pass web results | Add contradiction hunter and source-rank policy |
| MeatyWiki writebacks pollute memory | Require writeback candidates before promotion |
| SkillBOM promotion happens too early | Follow governance promotion path: candidate → evaluated → human-reviewed → promoted |

---

## 18. MVP build order

Build in this order:

1. **Schemas and folders**
2. **CLI skeleton**
3. **Governance guard**
4. **Capture/triage**
5. **Source cards**
6. **Claim ledger**
7. **Verifier**
8. **Report generator**
9. **Writebacks**
10. **Adapters**
11. **Council review**
12. **Telemetry summaries**

The key is to implement the **claim verifier before fancy swarm orchestration**. The Foundry’s differentiated value is not that it can ask many agents to research something. It is that it can prove which claims came from where, what was inferred, what remains speculative, and what should be reused.

---

## 19. Suggested first demo topic

Use a self-referential but bounded demo:

> “What is the minimum viable architecture for an evidence-backed research swarm inside Agentic OS?”

Why this works:

* It exercises Research Foundry itself.
* It produces MeatyWiki pages for the concept.
* It generates the first SkillBOM candidate.
* It creates a CCDash event.
* It avoids work-sensitive data.
* It validates the claim-ledger discipline.

---

## 20. Suggested file/project update

| Item | Recommendation |
| --- | --- |
| **Suggested owner project** | Research Foundry, under Agentic OS Central Project |
| **Suggested artifact to update** | Create `12_Research_Foundry_MVP_Spec.md` |
| **Suggested next action** | Scaffold the repo and implement `rf init`, `rf capture`, `rf triage`, `rf verify`, and `rf writeback` before adding advanced swarm adapters |