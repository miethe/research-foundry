---
description: Create tasks, stories, and epics in Linear with SkillMeat naming conventions and structured formatting
allowed-tools: mcp__linear-server__list_teams, mcp__linear-server__list_users, mcp__linear-server__create_issue, mcp__linear-server__list_issues, mcp__linear-server__list_issue_labels, mcp__linear-server__get_team, mcp__linear-server__get_user
argument-hint: "[task-type] [title] [--epic=epic-name] [--story=story-name] [--assignee=user] [--priority=P0|P1|P2|P3] [--estimate=points] [--labels=label1,label2] [--team=team-name]"
---

# Linear Task Creation Command

Creates tasks, stories, and epics in Linear following SkillMeat naming conventions, architectural patterns, and development workflows using the Linear MCP server.

## Prerequisites

The Linear MCP server is already installed and authenticated. This command uses the MCP functions directly to interact with Linear's API.

## Command Execution

### 1. Parse Arguments and Set Defaults

Parse the command arguments to extract task details:
- `TASK_TYPE`: task, story, epic, bug, enhancement
- `TITLE`: The main task title
- `TEAM_NAME`: Target Linear team (defaults to first available team)
- `EPIC_NAME`: Parent epic name (for stories and tasks)
- `STORY_NAME`: Parent story name (for tasks)
- `ASSIGNEE`: User email or display name
- `PRIORITY`: P0 (Urgent), P1 (High), P2 (Normal), P3 (Low)
- `ESTIMATE`: Story points estimate
- `LABELS`: Comma-separated label names
- `DESCRIPTION`: Custom description content

Validate that required arguments (title) are provided before proceeding.

### 2. Generate SkillMeat Task ID

Generate a unique task ID following MP naming conventions:

**Format**: `MP-{AREA}-{TYPE}-{NUMBER}`

**Area Codes** (based on title keywords):
- `DB`: Database, schema, migration, RLS, PostgreSQL
- `API`: API, endpoint, router, service, FastAPI
- `UI`: UI, component, frontend, React, Storybook
- `TEST`: Test, testing, QA, coverage
- `ARCH`: Architecture, design, ADR, SPIKE
- `DOC`: Documentation, docs, README
- `INFRA`: Deployment, CI/CD, infrastructure
- `SEC`: Security, auth, permissions
- `PERF`: Performance, optimization, monitoring
- `GEN`: General (default)

**Type Codes**:
- `EPIC`: Epic
- `STORY`: Story
- `TASK`: Task
- `BUG`: Bug
- `ENH`: Enhancement

**Example**: `MP-API-TASK-1234` for an API-related task

### 3. Get Team Information

Use `mcp__linear-server__list_teams` to get available teams and select the target team:

1. **List Teams**: Get all available teams in the workspace
2. **Select Team**: Use specified team name or default to first available team
3. **Get Team Details**: Retrieve team ID and key for task creation

### 4. Create Task Description Template

Generate structured descriptions based on task type:

#### Epic Template
```markdown
# Epic: {title}

## Overview
{custom_description or epic description}

## Success Criteria
- [ ] All related stories completed
- [ ] Features tested and validated
- [ ] Documentation updated
- [ ] Deployment successful

## Architecture Compliance
- [ ] Follows MP layered architecture (router → service → repository → DB)
- [ ] Error handling uses ErrorResponse envelope
- [ ] Pagination uses cursor-based approach
- [ ] Observability instrumentation added

## Stories
- (Stories will be linked as they are created)

## Related Documents
- Related PRD: (link when available)
- SPIKE Document: (link when available)
- ADRs: (links when available)
```

#### Story Template
```markdown
# Story: {title}

## Description
{custom_description or user story description}

## Acceptance Criteria
- [ ] (Define specific, testable criteria)
- [ ] (Add more criteria as needed)

## Implementation Notes
- Follows SkillMeat architectural patterns
- Includes comprehensive testing
- Updates documentation as needed

## Definition of Done
- [ ] Code implemented and reviewed
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests added where appropriate
- [ ] Documentation updated
- [ ] Accessibility compliance validated (WCAG 2.1 AA)
- [ ] Performance impact assessed

## Tasks
- (Tasks will be linked as they are created)
```

#### Task Template
```markdown
# Task: {title}

## Description
{custom_description or technical implementation description}

## Implementation Details
- Layer: (Database/Repository/Service/API/UI/Testing/Documentation)
- Dependencies: (List prerequisite tasks)
- Acceptance Criteria: (Specific, testable outcomes)

## MP Architecture Compliance
- [ ] Follows layered architecture patterns
- [ ] Implements proper error handling
- [ ] Includes appropriate observability
- [ ] Maintains security standards

## Testing Requirements
- [ ] Unit tests implemented
- [ ] Integration tests where applicable
- [ ] Manual testing completed
- [ ] Edge cases covered

## Definition of Done
- [ ] Implementation complete and functional
- [ ] Code reviewed and approved
- [ ] Tests passing in CI/CD
- [ ] Documentation updated
```

### 5. Set Priority and Labels

#### Priority Mapping
Convert SkillMeat priority format to Linear priority values:
- `P0/Critical` → `1` (Urgent)
- `P1/High` → `2` (High)
- `P2/Medium` → `3` (Normal) - Default
- `P3/Low` → `4` (Low)

#### Label Processing
1. **Parse Custom Labels**: Split comma-separated labels from `--labels` argument
2. **Use `mcp__linear-server__list_issue_labels`**: Get available labels for the team
3. **Match Label Names**: Map label names to Linear label objects
4. **Add MP Default Labels**: Based on title keywords:
   - Database/schema → `backend`, `database`
   - API/endpoint → `backend`, `api`
   - UI/component → `frontend`, `ui`
   - Test → `testing`, `qa`
   - Documentation → `documentation`

### 6. Handle Parent Relationships

#### Epic/Story Hierarchy
1. **For Stories**: Can be linked to epics using `--epic=epic-name`
2. **For Tasks**: Can be linked to stories using `--story=story-name`

#### Parent Lookup Process
1. **Use `mcp__linear-server__list_issues`**: Search for parent issues by query
2. **Filter by Title**: Match issues containing the specified epic/story name
3. **Validate Parent**: Ensure parent exists before creating child task
4. **Set Parent ID**: Use the `parentId` parameter in issue creation

Example parent searches:
- Epic search: Query issues for epic name, filter by title match
- Story search: Query issues for story name within the epic context

### 7. Find Assignee

#### User Lookup Process
1. **Use `mcp__linear-server__list_users`**: Get all users in the workspace
2. **Match by Email or Name**: Search by email address or display name
3. **Validate Assignee**: Ensure user exists and is active
4. **Set Assignee**: Use the user ID in issue creation

#### Fallback Behavior
- If assignee not found, create task unassigned
- Display warning message for invalid assignees
- Support both email addresses and display names

### 8. Create the Task in Linear

#### Task Creation Process
1. **Use `mcp__linear-server__create_issue`**: Create the issue with all gathered information
2. **Build Issue Parameters**:
   - `title`: `{TASK_ID}: {TITLE}` format
   - `description`: Generated template with MP standards
   - `team`: Target team ID
   - `priority`: Converted priority value (1-4)
   - `assignee`: User ID or name (optional)
   - `parentId`: Parent issue ID for hierarchy (optional)
   - `estimate`: Story points (optional)
   - `labels`: Array of label names (optional)

#### Success Response
The MCP function returns:
- Issue ID and URL
- Created issue details
- Status confirmation

#### Error Handling
- Validate all required parameters before creation
- Handle missing teams, assignees, or parents gracefully
- Provide clear error messages for failures
- Fallback to unassigned/unlabeled if lookups fail

### 9. Post-Creation Actions

#### Task Creation Summary
Display comprehensive creation results:
- **Task Details**: ID, title, type, priority
- **Linear URL**: Direct link to created issue
- **Relationships**: Parent epic/story if applicable
- **Assignment**: Assignee information
- **Estimation**: Story points if provided

#### Local Tracking
Maintain a local CSV file (`.linear_tasks.csv`) with:
- Task ID
- Linear URL
- Title
- Priority
- Created date
- Parent relationships

#### Follow-up Recommendations
- Review task in Linear for completeness
- Add detailed acceptance criteria if needed
- Link related documents (PRD, SPIKE, ADR)
- Set up task dependencies in Linear
- Add to appropriate project/milestone
- Update team about new task creation

## Usage Examples

### Create an Epic
```bash
/linear-create-task epic "User Avatar Support" --team="Engineering" --priority=P1 --estimate=21 --labels="feature,ui,backend" --description="Comprehensive avatar support system for user profiles"
```

**Result**: Creates `MP-UI-EPIC-1234: User Avatar Support` with epic template

### Create a Story under an Epic
```bash
/linear-create-task story "User can upload avatar image" --epic="User Avatar Support" --team="Engineering" --assignee="dev@skillmeat.com" --estimate=8 --labels="frontend,ui"
```

**Result**: Creates `MP-UI-STORY-1235: User can upload avatar image` linked to epic

### Create a Task under a Story
```bash
/linear-create-task task "Implement avatar upload API endpoint" --story="User can upload avatar image" --team="Engineering" --priority=P2 --estimate=3 --labels="backend,api" --assignee="backend-dev@skillmeat.com"
```

**Result**: Creates `MP-API-TASK-1236: Implement avatar upload API endpoint` linked to story

### Create a Bug Report
```bash
/linear-create-task bug "Avatar images not displaying correctly on mobile" --team="Engineering" --priority=P1 --assignee="frontend-dev@skillmeat.com" --labels="bug,mobile,ui" --description="Images appear distorted on iOS Safari"
```

**Result**: Creates `MP-UI-BUG-1237: Avatar images not displaying correctly on mobile`

### Create a Documentation Task
```bash
/linear-create-task task "Update avatar API documentation" --team="Engineering" --priority=P3 --estimate=2 --labels="documentation,api" --description="Document new avatar endpoints in OpenAPI spec"
```

**Result**: Creates `MP-DOC-TASK-1238: Update avatar API documentation`

## SkillMeat Integration Features

### 1. Architecture Compliance

- **Layered Architecture**: Templates enforce router → service → repository → DB patterns
- **Error Handling**: Includes ErrorResponse envelope requirements
- **Pagination**: Specifies cursor-based pagination standards
- **Observability**: Requires telemetry spans and structured JSON logs

### 2. Quality Gates

- **Definition of Done**: Comprehensive criteria for task completion
- **Testing Requirements**: Unit tests (>80% coverage), integration tests, E2E tests
- **Accessibility**: WCAG 2.1 AA compliance validation
- **Documentation**: Required updates for all changes

### 3. Naming Conventions

- **MP Task IDs**: `MP-{AREA}-{TYPE}-{NUMBER}` format
- **Area Classification**: Auto-categorizes by content (DB, API, UI, TEST, etc.)
- **Type Indicators**: TASK, STORY, EPIC, BUG, ENH classifications

### 4. Template Integration

- **Structured Descriptions**: Different templates for epics, stories, tasks
- **Related Documents**: Links to PRDs, SPIKEs, ADRs
- **Acceptance Criteria**: Specific, testable requirements
- **Implementation Guidance**: MP-specific patterns and standards

### 5. MCP Integration Benefits

- **Direct API Access**: No CLI dependency, uses Linear's official API
- **Real-time Validation**: Immediate feedback on teams, users, labels
- **Rich Metadata**: Access to full Linear object details
- **Reliable Authentication**: Uses MCP server's authentication
- **Error Handling**: Structured error responses from API

### 6. Workflow Integration

- **Local Tracking**: Maintains `.linear_tasks.csv` for project records
- **Hierarchy Management**: Automatic parent-child relationships
- **Label Automation**: Smart label assignment based on content
- **Priority Mapping**: MP priority conventions to Linear values
- **Follow-up Actions**: Clear next steps and recommendations

This MCP-powered command ensures Linear tasks are created with comprehensive context, proper relationships, and full SkillMeat-specific requirements while leveraging the reliability and features of Linear's official API integration.
