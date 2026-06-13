# meatywiki-author — Claude Code Skill

This skill guides AI agents in authoring markdown artifacts with valid MeatyWiki frontmatter hints. When an external project's agent produces artifacts destined for MeatyWiki ingestion, this skill ensures routing hints are correctly typed, semantically valid, and interpreted correctly by the engine.

---

## What This Skill Does

The MeatyWiki engine infers artifact workspace, type, and tags via LLM classification. Agents that already know where an artifact belongs can supply **frontmatter hints** to skip or steer that inference. This skill teaches agents:

- Which 9 hint fields exist and what each one means
- Which hints are **binding** (engine skips LLM inference) vs. **advisory** (LLM context only)
- Validation rules to avoid doctor lint failures
- How provenance and derivation fields track agent attribution

---

## Installation

Copy the skill directory into the target project's `.claude/skills/` folder:

```bash
cp -r .claude/skills/meatywiki-author/ /path/to/your-project/.claude/skills/meatywiki-author/
```

Or reference it from the MeatyWiki monorepo via a relative path in your project's CLAUDE.md.

---

## Usage

Reference SKILL.md in agent prompts or CLAUDE.md:

```
When authoring artifacts for MeatyWiki ingestion, load and follow
.claude/skills/meatywiki-author/SKILL.md for frontmatter hint guidance.
```

Claude Code will load the skill on demand. For recurring authoring workflows, add a CLAUDE.md note pointing to the skill so it is loaded automatically when the agent creates artifacts.

---

## Schema Reference

The authoritative field definitions live in the MeatyWiki monorepo:

```
docs/architecture/agent-frontmatter-contract.md
```

SPEC.md in this skill is a portable copy of the contract pinned to schema contract version v1.6.0. When the engine schema is updated, re-copy SPEC.md from the MeatyWiki source.

---

## Skill Version

This skill is pinned to **schema contract v1.6.0** (`skill_version: 1.0.0`). Check SPEC.md §5 for the versioning policy and upgrade instructions.
