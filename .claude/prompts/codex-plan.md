{
"REASONING": "High",
"MODEL": "GPT-5.1-Codex-Max"
}

Enhancing your reasoning effort for this planning phase; expect reasoning level to change every turn, depending on the task at hand - plan accordingly.

Create your implementation plan for the entire attached PRD @docs/project_plans/artifact-version-tracking/artifact-version-tracking-sync-prd-v2.md . Create a file for the plan within project_plans/artifact-version-tracking/. Remember that you (AI Agents) will solely be using this plan, so optimize for AI, NOT humans. Do NOT be overly verbose or use pseudocode except when absolutely necessary. Consider using JSON or a highly structured markdown doc to simplify your ability to grep and update the file as you proceed, as an AI Agent.

Also, update and maintain a tracking list at the end of the implementation plan. This should contain every task to be completed, linked to the more detailed explanation from the plan above via some unique key per task.

Every task should be broken out by phase, and labeled with the relevant Functional Requirement (FR). Do NOT include estimated time to complete, but you may use the concept of storypoints to guage LoE per task.

You should update each task with an [X] as complete as you progress. Add key success criteria for each task to simplify validation. Every task should also be noted with the code domain it will touch, ie: API, Web, CLI, Docs, Test, Infra, etc. If a task would be better suited for completion by another model or provider, or would benefit from a specific dedicated subagent SME, or MCP access, or otherwise, then note as such. We have access to all GPT Codex models, Gemini 3 Pro, and the full Claude Code suite(Opus 4.5, Sonnet 4.5, Haiku 4.5, with significant agents and skills in .claude/), + all GH Copilot capabilities.

Additionally, every task should be marked with a recommended reasoning effort. For example, if you know a task will require (or would benefit from) substantial reasoning effort, mark it as such so that we can explicitly work on that task in a separate turn with a higher level of reasoning. Use one of [Low, Medium, High, Extra High].
