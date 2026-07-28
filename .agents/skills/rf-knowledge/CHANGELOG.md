---
skill: rf-knowledge
---

# rf-knowledge — Changelog

Tracks changes to the skill pack (SKILL.md, SPEC.md, references). Implementation changes live
in git commit messages; this file tracks skill-surface changes only.

---

## v1.0 — 2026-07-28

- Initial authored `SPEC.md` + `CHANGELOG.md`; established `references/` layout.
- Structural spec-compliance pass on the already-shipped SKILL.md against
  `.Codex/skills/_meta/skill-authoring-guide.md`:
  - Frontmatter: added `version: 1.0`, `app_version: "2026-07-28"`, `updated: 2026-07-28`,
    `spec: ./SPEC.md`; converted `description` to a folded scalar and added an explicit
    `Triggers` list; kept the "Do NOT use for" clause. `tools` / `model` / `allowed-tools`
    intentionally not present (the harness does not support them on skills).
  - Sections: added the mandatory `When NOT To Use` (previously frontmatter-only) and the
    mandatory `Deferred / Do Not Say` (six entries covering remote/hosted transport, OpenAI
    compatibility, stdio/CLI assertion deny, the `KMCP-F1` install gap, absent CLI parity for
    frozen core, and the untrusted-content discipline).
  - Restructured to the router shape: H1 + intro → Overview → naming collision → Decision
    Tree → Command Map → Workflow Recipes → Guardrails → When NOT To Use → Deferred / Do Not
    Say → References Pointer Table → Contract Pointer → Key References. Naming-collision
    table stays in SKILL.md as the load-bearing routing content.
  - Progressive disclosure: DTO detail, transport / route parity, curl / CLI examples, paging
    semantics moved to `references/tool-reference.md`. Seven gotchas + the claim-ledger bridge
    moved to `references/gotchas.md`. SKILL.md retains only routing logic + guardrails +
    deferred + pointers.
  - Key References converted from relative to absolute paths so the skill remains loadable
    from arbitrary working directories (this skill is symlinked into the host-agent skills
    tree).
- Content preserved verbatim in intent: the eight tools (frozen core `search` / `fetch` +
  RF-extended `rf_search` / `rf_fetch` + four typed getters), three transports (stdio MCP,
  `rf knowledge` CLI, GET-only HTTP API), the `_StdioOnlyFastMCP` in-code refusal, the
  `content_is_untrusted: true` marker, the `rfk:v1:<kind>:<opaque>` id shape, the
  `no_agent_cleared_rights_value` guard rule, and the claim-ledger bridge.
- Codex-host mirror authored in lockstep with the source skill pack — same file list, with
  the standard host-agent token rewrite applied. Domain nouns (`Anthropic`, `SkillMeat`,
  `MeatyWiki`, `Research Foundry`, the `rf` / `op` CLI names, `rf-knowledge`,
  `rf_knowledge_lookup`, model-id strings) preserved.
