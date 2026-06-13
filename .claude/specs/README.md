# CLAUDE.md Specification System

**Purpose**: Token-optimized specs for generating CLAUDE.md files

## File Structure

| File | Purpose | Size | Usage |
|------|---------|------|-------|
| `claude-fundamentals-spec.md` | Generic patterns across all projects | ~250 lines | Base layer |
| `meatyprompts-spec.md` | MeatyPrompts-specific patterns | ~200 lines | Project layer |
| `doc-policy-spec.md` | Documentation policy (compressed) | ~250 lines | Policy layer |

## Subdirectory: artifact-structures/

Document schema and structure specs (as opposed to process/policy specs) live in `artifact-structures/`. See [`artifact-structures/README.md`](artifact-structures/README.md) for the full index.

| File | Purpose |
|------|---------|
| `artifact-structures/ccdash-doc-structure.md` | CCDash base envelope (schema_version 2) |
| `artifact-structures/human-brief-spec.md` | `human_brief` doc type spec |
| `artifact-structures/skill-spec-convention.md` | SPEC.md convention for custom skills |
| `artifact-structures/skill-spec-template.md` | Copy-paste template for new SPEC.md files |

## Composition Pattern

```
CLAUDE.md = fundamentals + project-specific + doc-policy
```

**Example Usage:**

```markdown
# Generate CLAUDE.md for MeatyPrompts
1. Load claude-fundamentals-spec.md (generic patterns)
2. Load meatyprompts-spec.md (project architecture)
3. Load doc-policy-spec.md (documentation rules)
4. Compose → output CLAUDE.md
```

## When to Use Which Spec

**claude-fundamentals-spec.md** → Generic patterns:
- Task management (TodoWrite)
- Agent delegation
- Documentation vs AI artifacts
- Tone/style preferences
- Git workflow
- Professional objectivity

**meatyprompts-spec.md** → Project-specific:
- Layered architecture patterns
- Package structure
- Error/pagination patterns
- UI constraints
- Symbols system
- Observability requirements

**doc-policy-spec.md** → Documentation rules:
- Allowed/prohibited docs
- Directory structure
- Naming conventions
- Frontmatter requirements
- Tracking patterns

## Token Efficiency

- **Before**: 1323 lines (verbose explanations)
- **After**: ~700 lines total (3 files, structured)
- **Reduction**: ~47% while preserving all rules
- **Format**: Tables, decision trees, shorthand notation
