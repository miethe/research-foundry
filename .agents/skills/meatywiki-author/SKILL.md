---
name: meatywiki-author
description: Use this skill when authoring markdown artifacts destined for MeatyWiki ingestion. Guides agents in writing valid YAML frontmatter with routing hints that the engine honors during ingest → classify → compile. Triggers: "write a MeatyWiki artifact", "author an artifact for the wiki", "create a concept/research-finding/code-snippet for MeatyWiki", "add frontmatter hints", "meatywiki frontmatter", "routing hints", "meatywiki-author". Do NOT use for: authoring general markdown, running meatywiki CLI commands (use meatywiki skill), Portal UI actions.
schema_version: 1
skill_version: 1.0.0
schema_contract_version: v1.6.0
spec_ref: SPEC.md
---

# MeatyWiki Author Skill

Guide for agents writing markdown artifacts that MeatyWiki will ingest. Place frontmatter hints at the top of every artifact file so the engine routes them correctly without LLM guesswork.

Schema reference: `docs/architecture/agent-frontmatter-contract.md`

---

## 1. Workflow

1. **Decide workspace** — identify the target `Workspace` enum value (see §3 quick reference). If confident, set `routing_workspace` (binding). If uncertain, omit it and let the classifier infer.
2. **Include YAML frontmatter** — add the frontmatter block as the first thing in the file (before any content).
3. **Set hint fields** — binding hints are authoritative; advisory hints steer the classifier.
4. **Write the body** — standard markdown after the closing `---`.
5. **Submit** — via `meatywiki ingest <file>` or Portal intake API.

---

## 2. Hint Field Categories

| Category | Fields | Engine Behavior |
|---|---|---|
| **Binding** | `routing_workspace`, `routing_profile_hint` | Engine skips LLM inference; uses hint value directly. Must be valid enum/name. |
| **Advisory** | `routing_artifact_type`, `routing_tags`, `routing_project` | Injected into classifier prompt; LLM may refine. No validation enforcement. |
| **Provenance** | `agent_origin`, `automation_source` | Metadata tracking; visible in Portal properties. No routing effect. |
| **Derivation** | `parent_artifact_id`, `parent_run_id` | Records parent-child relationships; dangling pointers allowed (doctor warns). |

---

## 3. Quick Reference — All 9 Fields

| Field | Type | Category | Example |
|---|---|---|---|
| `routing_workspace` | `Workspace` enum or `null` | Binding | `"research"` |
| `routing_profile_hint` | `string` or `null` | Binding | `"ai_chat_export.chatgpt"` |
| `routing_artifact_type` | `ArtifactType` string or `null` | Advisory | `"research_finding"` |
| `routing_tags` | list of strings | Advisory | `["agent-authored", "llm-research"]` |
| `routing_project` | `string` or `null` | Advisory | `"project-nexus"` |
| `agent_origin` | `string` or `null` | Provenance | `"Codex"` |
| `automation_source` | `string` or `null` | Provenance | `"weekly-research-sync"` |
| `parent_artifact_id` | UUID string or `null` | Derivation | `"550e8400-e29b-41d4-a716-446655440000"` |
| `parent_run_id` | `string` or `null` | Derivation | `"workflow-run-abc123"` |

**Valid `routing_workspace` values:** `"wiki"`, `"research"`, `"blog"`, `"projects"`, `"glossary"`, `"syntheses"`

---

## 4. Full Example Frontmatter Block

```yaml
---
routing_workspace: "research"
routing_artifact_type: "research_finding"
routing_tags:
  - "agent-authored"
  - "llm-research"
  - "transformer-architecture"
routing_project: "ml-foundations"
agent_origin: "Codex"
automation_source: "external-research-workflow"
parent_artifact_id: null
parent_run_id: "workflow-run-abc123"
---

# Article Title or Concept Name

Body content here...
```

---

## 5. Binding Hints — Rules

- `routing_workspace` must be one of the valid enum values above. If you set an invalid value, `meatywiki doctor` will reject it. When in doubt, omit it.
- `routing_profile_hint` must match a registered profile name in the engine profile registry (e.g., `"ai_chat_export.chatgpt"`, `"project_plan"`, `"transcript"`). Only set this if you know the profile name exactly; otherwise omit.
- **Binding means binding.** When set correctly, the engine skips LLM inference for that field. Get it right or leave it null.

---

## 6. Advisory Hints — Rules

- `routing_artifact_type` should be a known `ArtifactType` string (e.g., `"research_finding"`, `"concept"`, `"code_snippet"`, `"conversation"`, `"synthesis"`). The classifier will use it as context but may override based on content.
- `routing_tags` merges with classifier-emitted tags via union — your tags are additive, never dropped. Include `"agent-authored"` as a standard provenance tag.
- `routing_project` is a free-form string matching a project slug. Advisory only.

---

## 7. Validation Checklist

Before writing the file:

- [ ] `routing_workspace` is a valid `Workspace` enum value, or omitted
- [ ] `routing_profile_hint` matches a registered profile name, or omitted
- [ ] `routing_tags` is a list of strings, not a single string
- [ ] `parent_artifact_id` is a valid UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), or null
- [ ] No extra required fields are added that belong to the full engine schema (those are engine-managed)

---

## 8. Examples

See `examples/` for complete, realistic artifact examples:

| File | Type | Demonstrates |
|---|---|---|
| `examples/concept.md` | Concept | Binding workspace, advisory type + tags |
| `examples/research-finding.md` | Research Finding | Advisory hints, provenance, parent derivation |
| `examples/code-snippet.md` | Code Snippet | Minimal hints, project routing |

---

## 9. Minimal Valid Frontmatter

If you are unsure about routing, include only provenance fields. The engine will classify from content:

```yaml
---
routing_tags:
  - "agent-authored"
agent_origin: "Codex"
---
```

This is always safe. The `agent-authored` tag is preserved via union merge and visible in Portal.

---

## 10. Contract Pointer

See `SPEC.md` for the full schema contract, field types, validation logic, merge semantics, and versioning policy.
