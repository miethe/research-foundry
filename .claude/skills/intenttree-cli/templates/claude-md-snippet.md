---
name: intenttree-cli-claude-md-snippet
description: >-
  Template for the CLAUDE.md (or AGENTS.md) block injected by the bootstrap
  workflow. Fill all {{PLACEHOLDER}} values before writing. The HTML-comment
  markers allow idempotent re-injection on future bootstrap runs.
type: template
skill_name: intenttree-cli
schema_version: 1
---

# CLAUDE.md Snippet Template

The block below is the **exact content** to append (or replace between markers)
in the host project's `CLAUDE.md`. Substitute every `{{PLACEHOLDER}}` before
writing. The outer HTML-comment markers must appear verbatim in the target file.

---

## Template Body (copy verbatim, substitute placeholders)

```markdown
<!-- intenttree-cli:begin -->
## IntentTree Work Tracking

This project's work is tracked in IntentTree.
Workspace: {{WORKSPACE_ID}} | Tree: {{TREE_ID}} | API: {{API_URL}}

**Session start procedure:**
1. Run `uv run intenttree today show --workspace {{WORKSPACE_ID}} --json` to see today's plan.
2. Run `uv run intenttree node list --tree {{TREE_ID}} --status in_progress --json` to resume in-progress nodes.
3. For the highest-priority item, load `Skill("intenttree-cli")` and follow the dispatch workflow.

**As work progresses — keep the tree current:**
- Create nodes: `uv run intenttree node create --title "..." --type atomic_task --tree {{TREE_ID}}`
- Update status: `uv run intenttree node update <node_id> --status in_progress`
- Complete nodes: `uv run intenttree node complete <node_id>`
- Defer items: `uv run intenttree node defer <node_id>`

**Agent work (M1 dispatch loop):**
Load `Skill("intenttree-cli")` and follow `workflows/dispatch-workflow.md`.
The four steps are: `run start` → `run prompt` → do work → `run report` → `node complete`.

**Config:** flags > `INTENTTREE_API_URL` / `INTENTTREE_API_TOKEN` / `INTENTTREE_WORKSPACE` env > `~/.config/intenttree/config.toml`
<!-- intenttree-cli:end -->
```

---

## Notes for the Bootstrap Agent

- Write only the content between and including the HTML-comment marker lines.
  Do not include this commentary file's frontmatter or surrounding fences.
- Substitute all four placeholders before writing:

| Placeholder | Source |
|-------------|--------|
| `{{WORKSPACE_ID}}` | Active workspace ID (from `config whoami` or `workspace list`) |
| `{{TREE_ID}}` | Tree ID found or created in bootstrap step B3 |
| `{{API_URL}}` | Value of `api_url` from `config list` |

- Idempotency rules (from `bootstrap-workflow.md` step B4):
  - No markers present: append block; confirm with user.
  - Markers present, identical content: skip.
  - Markers present, different content: show unified diff; replace between markers only on explicit user confirm.
- After writing, verify markers are present:
  `grep -c 'intenttree-cli:begin' "$HOST_PROJECT_ROOT/CLAUDE.md"` must return `1`.
- Expected line count of the injected block (between markers, inclusive): ~20 lines.
  If significantly different, the template may have been corrupted — abort and report.
