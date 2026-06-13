---
name: meatywiki-author-spec
schema_contract_version: v1.6.0
skill_version: 1.0.0
updated: 2026-05-23
---

# MeatyWiki Author Skill — Contract Specification

Schema contract for agent-authored frontmatter hints. Pinned to schema contract v1.6.0 (engine `ArtifactEnvelope` fields added in the agent-frontmatter-contract feature).

Schema reference: `docs/architecture/agent-frontmatter-contract.md`

---

## 1. Schema Version

**Contract version:** v1.6.0
**Engine schema field source:** `src/meatywiki/schema/frontmatter.py` (`ArtifactEnvelope`)
**Skill version:** 1.0.0 — bump `skill_version` in SKILL.md and this file when schema changes.

---

## 2. Field Definitions

### 2.1 Binding Fields

These fields are honored as authoritative. The engine skips LLM inference for the corresponding pipeline stage when these are valid.

#### `routing_workspace`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Binding |
| **Honored by** | Profile stage + Classify stage (workspace override) |
| **Validation** | Must be a valid `Workspace` enum value |

Valid values:

```
"wiki"        — compiled wiki artifacts (concepts, topics, entities)
"research"    — research findings, external research sources
"blog"        — blog posts and drafts
"projects"    — project artifacts, PRDs, specs
"glossary"    — glossary terms
"syntheses"   — synthesis artifacts, summaries
```

When set and valid, the classify stage uses this value directly without calling the LLM for workspace inference. Set only when you are certain of the target workspace.

---

#### `routing_profile_hint`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Binding |
| **Honored by** | Profile stage (skip detector when valid) |
| **Validation** | Must match a registered profile name in the engine profile registry |

Example values: `"ai_chat_export.chatgpt"`, `"ai_chat_export.perplexity"`, `"project_plan"`, `"transcript"`, `"technical_reference"`

When set and valid, the profile stage skips the detector heuristics and uses the specified profile directly. Only set this if you know the exact profile name. Omit if uncertain.

---

### 2.2 Advisory Fields

These fields are injected into the classifier prompt as agent suggestions. The LLM may use or override them based on content.

#### `routing_artifact_type`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Advisory |
| **Honored by** | Classify stage (prompt context) |
| **Validation** | Should be a known `ArtifactType` string; no enum enforcement |

Common values: `"concept"`, `"research_finding"`, `"code_snippet"`, `"conversation"`, `"synthesis"`, `"entity"`, `"topic"`, `"evidence"`, `"glossary_term"`

---

#### `routing_tags`

| Property | Value |
|---|---|
| **Type** | `list[string]` |
| **Default** | `[]` |
| **Category** | Advisory |
| **Honored by** | Classify stage (merged with classifier tags via union) |
| **Validation** | Must be a list of strings |

**Merge semantics:** Agent-supplied tags are merged with classifier-emitted tags via set union (no duplicates). Agent tags are never dropped; classifier tags are never suppressed. Order is undefined; set membership is authoritative.

Recommended standard tags:
- `"agent-authored"` — always include; marks artifact as agent-authored for Portal visibility
- `"llm-research"` — for artifacts derived from LLM-assisted research
- `"needs-review"` — request human review before promotion

---

#### `routing_project`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Advisory |
| **Honored by** | Classify stage (prompt context) |
| **Validation** | Free-form string; no existence check |

Free-form project slug that steers the classifier toward associating the artifact with a named project. The LLM uses this as context but is not constrained by it.

---

### 2.3 Provenance Fields

These fields do not affect routing or classification. They are preserved in the vault artifact and visible in Portal properties.

#### `agent_origin`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Provenance |
| **Honored by** | Metadata tracking, Portal properties |

The identity of the agent that created this artifact. Use a stable, lowercase slug:
- `"claude-code"` — Claude Code instance in a sibling project
- `"mcp-research-agent"` — MCP-driven research workflow
- `"prd-synthesis-workflow"` — automated PRD synthesis pipeline

---

#### `automation_source`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Provenance |
| **Honored by** | Metadata tracking, Portal properties |

The workflow or automation run that produced this artifact. Use a descriptive slug:
- `"weekly-research-sync"` — scheduled research workflow
- `"prd-synthesis-workflow"` — one-shot synthesis run
- `"external-research-workflow"` — external research intake pipeline

---

### 2.4 Derivation Fields

These fields record parent-child relationships for graph inference and attribution. Dangling pointers are allowed (doctor warns, does not reject).

#### `parent_artifact_id`

| Property | Value |
|---|---|
| **Type** | `string (UUID) \| null` |
| **Default** | `null` |
| **Category** | Derivation |
| **Honored by** | Doctor lint (warn if missing), graph layer (future edge inference) |
| **Validation** | Must be UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

UUID of the parent artifact in the vault. Set when this artifact is derived from or synthesized from a specific source artifact. Doctor lint emits a warning if the referenced UUID does not exist in the vault (dangling pointer), but does not reject the file.

---

#### `parent_run_id`

| Property | Value |
|---|---|
| **Type** | `string \| null` |
| **Default** | `null` |
| **Category** | Derivation |
| **Honored by** | Doctor lint, Portal activity timeline |
| **Validation** | Free-form string; no existence check |

The workflow run ID that produced this artifact. Used for Portal activity timeline display and workflow attribution. Format is workflow-specific (e.g., `"workflow-run-abc123"`, `"run-2026-05-23-001"`).

---

## 3. Validation Logic

Before writing a file with frontmatter hints, verify:

1. **`routing_workspace`**: If set, value must be one of: `"wiki"`, `"research"`, `"blog"`, `"projects"`, `"glossary"`, `"syntheses"`. Invalid values will be rejected by `meatywiki doctor`.

2. **`routing_profile_hint`**: If set, value must be a registered profile name. Check the engine profile registry at `src/meatywiki/workflows/profiles/`. If unsure, omit.

3. **`routing_tags`**: Must be a YAML list (`- "tag"` format), not a comma-separated string. A single string will fail Pydantic validation.

4. **`parent_artifact_id`**: If set, must match UUID format. `meatywiki doctor` warns (does not reject) if the referenced artifact is not found in the vault.

5. **All other fields**: Preserved as-is; advisory fields have no hard validation at ingest time.

---

## 4. Merge Semantics

### Tag Union

```
agent_tags = ["agent-authored", "transformer"]
classifier_tags = ["machine-learning", "transformer"]  # note duplicate

merged_tags = union(agent_tags, classifier_tags)
# result: ["agent-authored", "transformer", "machine-learning"]
# order undefined; duplicates removed
```

### Workspace Binding Override

```
routing_workspace = "research"   # set by agent

classify_stage:
  workspace_inference = SKIPPED   # LLM not called for workspace
  final_workspace = "research"    # agent value used directly

structured_log: { "event": "hint_applied", "field": "routing_workspace", "value": "research", "override": true }
```

### Dangling Pointer Policy

```
parent_artifact_id = "550e8400-e29b-41d4-a716-446655440000"

doctor_lint:
  if vault.get(parent_artifact_id) is None:
    emit WARNING: "parent_artifact_id references unknown artifact: 550e8400-..."
    # does NOT reject; file is valid
```

---

## 5. Skill Versioning Policy

| Event | Action |
|---|---|
| New hint field added to `ArtifactEnvelope` | Bump `schema_contract_version` (e.g., v1.6.0 → v1.7.0); update §2; bump `skill_version` minor |
| Field semantics change (binding → advisory) | Bump `schema_contract_version` + `skill_version` minor; add migration note |
| Field removed or renamed | Bump `schema_contract_version` major + `skill_version` major; add migration note |
| Examples updated, wording clarified | Bump `skill_version` patch only |

External projects that copy-install this skill should pin the `skill_version` in their repo and monitor for updates.

---

## 6. Coverage Matrix

| Field | Skill Quick Ref | SPEC Types | Validation | Example |
|---|:---:|:---:|:---:|:---:|
| `routing_workspace` | Y | Y | Y | Y |
| `routing_profile_hint` | Y | Y | Y | Y |
| `routing_artifact_type` | Y | Y | — | Y |
| `routing_tags` | Y | Y | Y | Y |
| `routing_project` | Y | Y | — | Y |
| `agent_origin` | Y | Y | — | Y |
| `automation_source` | Y | Y | — | Y |
| `parent_artifact_id` | Y | Y | Y | Y |
| `parent_run_id` | Y | Y | — | Y |

All 9 fields covered in SKILL.md quick reference, SPEC.md type definitions, and at least one example file.
