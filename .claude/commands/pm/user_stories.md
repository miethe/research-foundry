---
description: Create implementation plan with Epic headers and Story ID tables, then auto-extract individual story files
allowed-tools: Read(./**), Write(./docs/**), Edit, Bash
argument-hint: "[STORY_IDS] [ATTACHMENT] [ADDITIONAL_DETAILS]"
---

# Implementation Plan & User Story Creation

Role: Utilize the lead-pm subagent to create a properly formatted implementation plan, then automatically extract individual story files.

INPUTS I WILL PROVIDE:

- STORY_IDS: {STORY_IDS}   # list of 1+, comma-separated (e.g., MP-AUTH-API-002, MP-UI-UI-015)
- ATTACHMENT: {ATTACHMENT_NAME}  # a single attached file containing the details/requirements per ID
- ADDITIONAL_DETAILS: (optional) {ADDITIONAL_DETAILS}  # file(s) with any other relevant information or context

PROCESS OVERVIEW:

1. Use the existing implementation plan (skip creation if one already exists)
2. Automatically run the @story-population.py script to extract individual story files
3. Output the locations of all created files
4. Create/Update Linear task for each Story ID created using the @linear-create-task command.

IMPLEMENTATION PLAN FORMAT REQUIREMENTS:

1. **Epic Headers**: Format as "## Epic: {EPIC_ID} - {Title}" (e.g., "## Epic: MP-MODEL-DB-001 - Database Schema & Infrastructure Foundation")
2. **Story Tables**: Must have "Story ID" as the first column header
3. **Table Structure**: Include columns: Story ID, Task Name, Description, Acceptance Criteria, Estimate, Dependencies
4. **File Location**: Save to `/docs/project_plans/implementation_plans/{plan_name}.md`

EPIC AND STORY ID ORGANIZATION:

- Group related stories under logical epics
- Epic IDs should follow pattern: MP-{AREA}-{EPIC_TYPE}-{NUMBER}
- Story IDs should follow pattern: MP-{AREA}-{NUMBER}
- Areas: MODEL, API, UI, DB, TEST, DEPLOY, etc.
- Epic Types: DB (database), API (backend), UI (frontend), TEST (testing), etc.

WHAT TO READ & HOW:

1) Parse the attachments. Locate the sections for each STORY_ID. If an ID appears multiple times, merge the most recent/most specific details.
2) Group stories into logical epics based on technical layers and dependencies
3) If any field is missing, infer sensible defaults from the attachment's surrounding context
4) Use codebase knowledge to fill in gaps or clarify requirements

IMPLEMENTATION PLAN STRUCTURE:

```markdown
# Implementation Plan: {Feature Name}

**Plan ID**: `IMPL-{YYYY-MM-DD}-{PLAN_NAME}`
**Date**: {Current Date}
**Author**: Lead PM Agent
**Related Documents**: Links to PRDs, SPIKEs, ADRs

## Epic: {EPIC_ID} - {Epic Title}

| Story ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|----------|-----------|-------------|-------------------|----------|--------------|
| {STORY_ID} | {Task Name} | {Description} | {Criteria} | {Points} | {Dependencies} |

## Epic: {NEXT_EPIC_ID} - {Next Epic Title}

...
```

STORY EXTRACTION PROCESS:

After creating the implementation plan:

1. **Script Execution**: If empty files for each story do not yet exist, run `python /scripts/story-population.py {impl_plan_filename}` on the full implementation plan with all Epics and Stories.
2. **File Naming**: Use format `{feature-name}-implementation-plan.md`
3. **Directory Structure**: Stories created in `/docs/project_plans/Stories/{plan_name}/{epic_id}/{story_id}.md`
4. **Validation**: Verify all story files were created correctly

OUTPUT REQUIREMENTS:

1. Use existing implementation plan (skip creation if already exists)
2. Execute the story-population script automatically
3. Report the locations of all created files
4. Confirm successful extraction of individual stories

ERROR HANDLING:

- If story-population script fails, report the error and provide manual extraction instructions
- Verify implementation plan format meets script requirements before extraction
- Ensure all Epic headers follow the required pattern: "## Epic: {EPIC_ID} - {Title}"

FINAL DELIVERABLES:

- Individual story files in `/docs/project_plans/Stories/{plan_name}/{epic_id}/`
- Summary of created files and their locations

BEGIN STORY EXTRACTION FROM EXISTING IMPLEMENTATION PLAN NOW.
