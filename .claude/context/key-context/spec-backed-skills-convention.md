# Spec-Backed Skills Convention

**Load this when**: Reading or updating a skill's SPEC.md, maintaining a skill that has published a specification, or understanding the capability contract for a skill.

---

## What is a SPEC.md?

A `SPEC.md` file is a **versioned capability contract** that lives alongside a skill's `SKILL.md`:

| File | Audience | Purpose |
|------|----------|---------|
| `SKILL.md` | Agents at invocation time | Quick-reference routing and permissions |
| `SPEC.md` | Skill maintainers, orchestrators, planners | Formal capability coverage, invariants, roadmap |

`SPEC.md` answers the question: **What does this skill intend to cover, and what gaps exist for future development?**

---

## When to Create or Update SPEC.md

### Create SPEC.md When

1. **New skill** — Part of the skill-creator workflow (required before marking skill as `stable`).
2. **CLI surface changes** — New commands, renamed flags, or removed subcommands in `docs/user/guides/cli/commands.md`.
3. **Status transitions** — Moving a skill from `draft` → `stable` or to `deprecated`.

### Update SPEC.md When

- **Capability Coverage table diverges from actual CLI surface** — Invariant violation; fix in the same commit as the CLI change.
- **New workflow file added or renamed** — Update the Capability Coverage table mapping.
- **Enhancement Backlog item implemented** — Move it to the Changelog section; keep BL-N ID for traceability.
- **Quarterly review** — Verify stable skills' capability tables against the live CLI surface once per quarter.

---

## How to Read a SPEC.md

### Quick Orientation

Start with the frontmatter:

```yaml
---
schema_version: 2
doc_type: skill_spec
skill_name: my-skill
skill_version: 1.0.0
status: stable | draft | deprecated
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: owner-name
source_docs:
  - docs/path/to/canonical/doc.md
---
```

**Key signals**:
- **`status`**: Draft = incomplete, Stable = published & maintained, Deprecated = superseded.
- **`source_docs`**: Canonical user/dev docs agents should reference for command syntax.
- **`skill_version`**: Follows semver; bump MINOR for new intent rows, MAJOR for breaking changes.

### The 7 Required Sections

| Section | Contains | Used By |
|---------|----------|---------|
| **1. Purpose & Scope** | Mission, in-scope capabilities, out-of-scope items | Agents deciding if the skill solves their problem |
| **2. Capability Coverage** | Table mapping user intents → workflows → canonical docs | Agents finding the exact workflow file for a task |
| **3. Invariants & Constraints** | Non-negotiable rules agents must follow | Agents understanding the skill's contract |
| **4. Enhancement Backlog** | Future capabilities with stable BL-N IDs | Planners tracking skill roadmap; agents understanding what's deferred |
| **5. Changelog** | SPEC.md version history (not implementation changes) | Reviewers understanding what changed in the spec contract |
| **6. Integration Points** | Which agents/commands load this skill | Orchestrators and skill maintainers |
| **7. Success Signals** | Observable heuristics for correct usage | Reviewers validating skill effectiveness |

---

## Quick-Reference: Key SPEC.md Patterns

### Capability Coverage Table

This is the **versioned contract surface**:

```markdown
| Intent | Workflow / Section | Canonical Doc |
|--------|-------------------|---------------|
| "Find or search an artifact" | `workflows/discovery-workflow.md` | `docs/user/guides/cli/commands.md § "Core Commands"` |
| "Deploy an artifact" | `workflows/deployment-workflow.md` | `docs/user/guides/cli/commands.md § "Deployment"` |
| "[deprecated] Old feature" | Deprecated in v2.0.0 | — |
| "New feature (pending)" | new — phase 3C: `workflows/new-workflow.md` | — |
```

**Rules**:
- One row per addressable user intent.
- Canonical Doc is the authoritative source for command syntax (agents consult this, not the workflow file).
- Mark deprecated intents as `[deprecated]` with a forward reference to the replacement.
- New workflows not yet implemented use "new — pending [phase]: filename" pattern.
- When a canonical doc doesn't exist, write `—` and add a backlog entry (§4).

### Invariants Section

Non-negotiable rules. Each is a single, testable statement:

```markdown
1. **Rule name**: Single testable statement. _Source_: `.claude/path/to/policy.md`

2. **Another rule**: What agents must or must not do.
   _Source_: CLAUDE.md § "Section Name"
```

**This is NOT preferences**—it's a contract. Breaking an invariant requires a MAJOR version bump.

### Enhancement Backlog (BL-N Format)

Track gaps and improvements with stable IDs:

```markdown
- **[BL-1] Feature name**: One-sentence description.
  _Status_: candidate | planned | deferred | will-not-fix
  _Rationale_: Why deferred, or why it won't be fixed.

- **[BL-5] Another feature**: Description.
  _Status_: will-not-fix
  _Rationale_: This task requires X, which is out of scope for this skill.
```

**When you implement a BL-N item**: Move it to the Changelog, keep the ID, mark it as "implemented in vX.Y.Z".

### Changelog Entry (on Update)

Track SPEC.md spec changes only (not implementation):

```markdown
### v1.1.0 — 2026-04-15
- Added new intent row for "Create bundle"
- Implemented [BL-2] (supply chain security workflows)
- Updated Canonical Doc links (bundle command moved to § "Bundle")
```

---

## Reading a Specific Workflow File

When the Capability Coverage table points you to a workflow file, follow this pattern:

1. **First paragraph**: Intent statement ("How do I X?")
2. **Workflow steps**: Sequential or parallel task blocks.
3. **Error handling section**: Common failure modes and recovery patterns.
4. **Code examples**: Copy-pasteable command sequences.
5. **Canonical doc reference**: Link back to user docs for syntax authority.

**Do not use the workflow file as command syntax reference**—use the canonical doc instead (listed in Capability Coverage table).

---

## Version-Management Quick Rules

| Change | Bump |
|--------|------|
| Add intent row to Capability Coverage | MINOR |
| Remove or deprecate an intent | MINOR |
| Add a new invariant | MINOR |
| Break or remove an invariant | MAJOR |
| Fix a doc link or typo | PATCH |
| First publication (draft → stable) | Promote to 1.0.0 |

---

## Linking Back from Source Docs

When you modify `docs/user/guides/cli/commands.md` or other source docs:

1. Update the Capability Coverage table in the skill's SPEC.md with new/renamed intents.
2. Commit both files together (single commit message).
3. If a workflow file references the old path, update that too.
4. Example commit message: `fix(skillmeat-cli): Rename bundle command, update SPEC.md § 2.2`

---

## Common Maintenance Tasks

### A skill's CLI surface changed

1. Open the skill's `SPEC.md`.
2. Find the Capability Coverage table (§2).
3. Add a new row for the new intent, or update the row for the changed intent.
4. If adding a new row, bump `skill_version` to MINOR (e.g., `1.1.0`).
5. Commit with both the source doc change and SPEC.md update.

### A workflow file was renamed or consolidated

1. Update the Capability Coverage table rows that point to it.
2. If the old path was public (agents might have cached it), add a comment: `<!-- formerly workflows/old-name.md -->`
3. Bump `skill_version` to MINOR.
4. Update the `updated` date.

### Moving a skill from draft to stable

1. Verify all 7 required sections are complete.
2. Remove any `TODO` or `{{PLACEHOLDER}}` markers.
3. Set `status: stable` in frontmatter.
4. Set `skill_version: 1.0.0`.
5. Add a Changelog entry: "Initial stable release".
6. Update `updated` date.

### Deprecating a skill

1. Set `status: deprecated` in frontmatter.
2. Add `deprecated_by: path/to/replacement-skill/SPEC.md` (or omit if no replacement).
3. Add `deprecation_date: YYYY-MM-DD`.
4. Add a final Changelog entry explaining why.
5. Do NOT delete the SPEC.md—archive it with the skill.

---

## When to Read Each Section

**Planning a feature that uses this skill** → Read §1 (Purpose & Scope) and §2 (Capability Coverage).

**Implementing an agent that loads this skill** → Read §3 (Invariants & Constraints) and §6 (Integration Points).

**Adding a new workflow to the skill** → Read §2 (Capability Coverage) and §4 (Enhancement Backlog) to avoid duplicating work.

**Reviewing a skill PR** → Verify all required sections are present, check Capability Coverage against SKILL.md, verify no TODOs in stable status.

**Updating skill roadmap** → Read §4 (Enhancement Backlog) and understand BL-N statuses.

---

## Key Files

| File | Purpose |
|------|---------|
| `.claude/specs/artifact-structures/skill-spec-convention.md` | Formal convention specification (version rules, frontmatter schema, all 7 sections) |
| `.claude/specs/artifact-structures/skill-spec-template.md` | Fillable template for new SPEC.md files |
| `.claude/skills/skillmeat-cli/SPEC.md` | Stable example with full Capability Coverage and Invariants |
| `.claude/specs/skills-index.md` | Inventory of all skills with SPEC.md presence indicator (✓/✗) |

---

## Links

- **Convention spec**: `.claude/specs/artifact-structures/skill-spec-convention.md`
- **Template**: `.claude/specs/artifact-structures/skill-spec-template.md`
- **Example (stable)**: `.claude/skills/skillmeat-cli/SPEC.md`
- **Skills index**: `.claude/specs/skills-index.md`
