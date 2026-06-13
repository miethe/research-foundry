# Load  Story

## 1.1 Find Story Specification

Search in this order:

1. Attached file in current message
2. `docs/project_plans/Stories/${story_id}.md`
3. `docs/project_plans/Sprints/*/stories/${story_id}.md`
4. `docs/prd.md` (search for story_id section)
5. Root `CLAUDE.md` references

## 1.2 Extract Requirements

Parse and validate:

- **Epic/Program**: Parent epic ID
- **Acceptance Criteria**: Numbered list of testable outcomes
- **Technical Scope**: Backend/Frontend/Shared/Infra
- **Dependencies**: Other story IDs that must be complete
- **Data Changes**: Schema/migration requirements

### 1.3 Repository Reconnaissance

REQUIRED subagent calls based on scope:

```bash
# For backend stories or mixed scope
@backend-architect analyze ${story_id}

# For frontend stories or mixed scope
@ui-designer review ${story_id}
```

If in PLAN_MODE, then use the `--plan-mode` flag. ie:

```bash
@ui-designer review ${story_id} --plan-mode
```
