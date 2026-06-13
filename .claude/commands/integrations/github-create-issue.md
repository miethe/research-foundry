---
description: Create GitHub Issues for bug tracking and small enhancements with SkillMeat templates and workflow integration
allowed-tools: Bash, Read(./**), Write, Edit, Bash(gh:*)
argument-hint: "[issue-type] [title] [--priority=P0|P1|P2|P3] [--labels=label1,label2] [--assignee=user] [--milestone=milestone] [--project=project]"
---

# GitHub Issue Creation Command

Creates structured GitHub Issues for bug reports, small enhancements, and technical tasks following SkillMeat development patterns and quality standards.

## Prerequisites

1. **GitHub CLI Setup**
   ```bash
   # Check if GitHub CLI is installed and authenticated
   if ! command -v gh &> /dev/null; then
     echo "❌ GitHub CLI not found. Install with: brew install gh"
     exit 1
   fi

   # Check authentication status
   gh auth status
   if [ $? -ne 0 ]; then
     echo "❌ GitHub CLI not authenticated. Run 'gh auth login' to authenticate."
     exit 1
   fi

   # Verify we're in a git repository
   if ! git rev-parse --git-dir > /dev/null 2>&1; then
     echo "❌ Not in a git repository"
     exit 1
   fi
   ```

2. **Repository Setup**
   ```bash
   # Get repository information
   REPO_NAME=$(gh repo view --json name --jq '.name')
   REPO_OWNER=$(gh repo view --json owner --jq '.owner.login')

   echo "Repository: $REPO_OWNER/$REPO_NAME"
   ```

## Command Execution

### 1. Parse Arguments and Set Defaults

```bash
# Parse command arguments
ISSUE_TYPE="${1:-bug}"  # bug, enhancement, task, documentation, security
TITLE="$2"
PRIORITY="P2"
LABELS=""
ASSIGNEE=""
MILESTONE=""
PROJECT=""
DESCRIPTION=""
REPRODUCTION_STEPS=""
EXPECTED_BEHAVIOR=""
ACTUAL_BEHAVIOR=""
ENVIRONMENT=""
BROWSER=""
OS=""

# Parse optional flags
for arg in "${@:3}"; do
  case $arg in
    --priority=*)
      PRIORITY="${arg#*=}"
      ;;
    --labels=*)
      LABELS="${arg#*=}"
      ;;
    --assignee=*)
      ASSIGNEE="${arg#*=}"
      ;;
    --milestone=*)
      MILESTONE="${arg#*=}"
      ;;
    --project=*)
      PROJECT="${arg#*=}"
      ;;
    --description=*)
      DESCRIPTION="${arg#*=}"
      ;;
    --reproduction=*)
      REPRODUCTION_STEPS="${arg#*=}"
      ;;
    --expected=*)
      EXPECTED_BEHAVIOR="${arg#*=}"
      ;;
    --actual=*)
      ACTUAL_BEHAVIOR="${arg#*=}"
      ;;
    --environment=*)
      ENVIRONMENT="${arg#*=}"
      ;;
    --browser=*)
      BROWSER="${arg#*=}"
      ;;
    --os=*)
      OS="${arg#*=}"
      ;;
  esac
done

# Validate required arguments
if [ -z "$TITLE" ]; then
  echo "❌ Error: Issue title is required"
  echo "Usage: /github-create-issue [issue-type] [title] [options]"
  echo "Types: bug, enhancement, task, documentation, security"
  exit 1
fi
```

### 2. Generate Issue Templates

```bash
# Generate structured issue body based on type
generate_issue_body() {
  local issue_type="$1"
  local title="$2"
  local description="$3"

  case "$issue_type" in
    "bug")
      cat << EOF
# Bug Report: $title

## Description
${description:-"Brief description of the bug"}

## Steps to Reproduce
${REPRODUCTION_STEPS:-"1. Go to...\n2. Click on...\n3. See error"}

## Expected Behavior
${EXPECTED_BEHAVIOR:-"What should happen"}

## Actual Behavior
${ACTUAL_BEHAVIOR:-"What actually happens"}

## Environment
- **OS**: ${OS:-"Not specified"}
- **Browser**: ${BROWSER:-"Not specified"}
- **Version**: ${ENVIRONMENT:-"Not specified"}
- **Device**: (Desktop/Mobile/Tablet)

## Screenshots/Videos
<!-- Please attach screenshots or videos if applicable -->

## Additional Context
<!-- Add any other context about the problem here -->

## Impact Assessment
- **Severity**: $PRIORITY
- **User Impact**: (High/Medium/Low)
- **Frequency**: (Always/Often/Sometimes/Rarely)
- **Workaround Available**: (Yes/No)

## Acceptance Criteria
- [ ] Bug is reliably reproduced
- [ ] Root cause is identified
- [ ] Fix is implemented and tested
- [ ] Fix doesn't break existing functionality
- [ ] Edge cases are considered and tested

## SkillMeat Architecture Compliance
- [ ] Fix follows layered architecture (router → service → repository → DB)
- [ ] Error handling uses ErrorResponse envelope
- [ ] Proper observability instrumentation added
- [ ] Security implications considered

---
**Bug Report Template v1.0 - SkillMeat**
EOF
      ;;
    "enhancement")
      cat << EOF
# Enhancement: $title

## Description
${description:-"Brief description of the enhancement"}

## Business Value
- **User Benefit**: (How does this help users?)
- **Business Impact**: (Revenue/engagement/efficiency impact)
- **Strategic Alignment**: (How does this align with product goals?)

## Current Behavior
${ACTUAL_BEHAVIOR:-"How things work currently"}

## Desired Behavior
${EXPECTED_BEHAVIOR:-"How things should work after enhancement"}

## Proposed Solution
<!-- High-level approach to implementing this enhancement -->

## Alternative Solutions Considered
<!-- Other approaches that were considered -->

## Implementation Considerations
- **Complexity**: Small/Medium/Large
- **Dependencies**: (List any dependencies)
- **Migration**: (Data/user migration needed?)
- **Performance**: (Performance implications)

## Acceptance Criteria
- [ ] Enhancement meets user requirements
- [ ] Implementation follows MP architecture patterns
- [ ] Comprehensive testing completed
- [ ] Documentation updated
- [ ] Performance impact assessed

## Success Metrics
- **Measurement**: (How will success be measured?)
- **Target**: (Specific targets or thresholds)
- **Timeline**: (When to measure success)

## SkillMeat Architecture Compliance
- [ ] Follows layered architecture patterns
- [ ] Uses @miethe/ui components for UI changes
- [ ] Implements proper error handling
- [ ] Includes observability instrumentation
- [ ] Maintains security standards

---
**Enhancement Template v1.0 - SkillMeat**
EOF
      ;;
    "task")
      cat << EOF
# Task: $title

## Description
${description:-"Detailed description of the task"}

## Purpose
<!-- Why is this task necessary? -->

## Implementation Details
- **Component**: (Which part of the system)
- **Layer**: (Database/Repository/Service/API/UI/Testing/Documentation)
- **Dependencies**: (Prerequisites for this task)
- **Complexity**: Small/Medium/Large

## Technical Requirements
- **Specifications**: (Technical specifications to implement)
- **Constraints**: (Any constraints or limitations)
- **Integration**: (How this integrates with existing systems)

## Acceptance Criteria
- [ ] Implementation is complete and functional
- [ ] Code follows MP patterns and standards
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests added where appropriate
- [ ] Documentation updated
- [ ] Code reviewed and approved

## Testing Strategy
- [ ] Unit tests for core functionality
- [ ] Integration tests for external dependencies
- [ ] Manual testing of user-facing features
- [ ] Performance testing if applicable
- [ ] Security testing if applicable

## Definition of Done
- [ ] Code implemented and committed
- [ ] All tests passing in CI/CD
- [ ] Code reviewed by senior developer
- [ ] Documentation updated
- [ ] Deployed to staging environment
- [ ] Stakeholder acceptance obtained

## SkillMeat Architecture Compliance
- [ ] Follows layered architecture (router → service → repository → DB)
- [ ] Uses proper error handling patterns
- [ ] Implements cursor pagination where applicable
- [ ] Includes OpenTelemetry instrumentation
- [ ] Maintains security best practices

---
**Task Template v1.0 - SkillMeat**
EOF
      ;;
    "documentation")
      cat << EOF
# Documentation: $title

## Description
${description:-"Documentation that needs to be created or updated"}

## Purpose
<!-- Why is this documentation needed? -->

## Target Audience
- **Primary**: (Developers/Users/Stakeholders)
- **Secondary**: (Other audiences)
- **Expertise Level**: (Beginner/Intermediate/Advanced)

## Documentation Type
- [ ] API Documentation (OpenAPI)
- [ ] Component Documentation (Storybook)
- [ ] User Guide
- [ ] Developer Guide
- [ ] Architecture Documentation (ADR)
- [ ] Process Documentation
- [ ] Tutorial/How-to Guide

## Content Requirements
- **Scope**: (What should be covered?)
- **Format**: (Markdown/Interactive/Video)
- **Location**: (Where will this live?)
- **Maintenance**: (How will this be kept up to date?)

## Acceptance Criteria
- [ ] Documentation is clear and comprehensive
- [ ] Examples and code snippets are accurate
- [ ] Screenshots/diagrams are up to date
- [ ] Content is accessible and well-organized
- [ ] Links and references are working
- [ ] Grammar and spelling are correct

## Review Requirements
- [ ] Technical accuracy reviewed by subject matter expert
- [ ] Clarity and usability reviewed by target audience
- [ ] Editorial review for grammar and style
- [ ] Accessibility compliance validated

## Success Metrics
- **Usability**: (How will effectiveness be measured?)
- **Maintenance**: (Update frequency and process)
- **Feedback**: (How will user feedback be collected?)

---
**Documentation Template v1.0 - SkillMeat**
EOF
      ;;
    "security")
      cat << EOF
# Security Issue: $title

## ⚠️ Security Information
<!-- Please be mindful of sensitive information in public issues -->

## Description
${description:-"Brief description of the security concern"}

## Security Classification
- **Severity**: Critical/High/Medium/Low
- **Type**: (Vulnerability/Compliance/Best Practice)
- **OWASP Category**: (If applicable)

## Affected Components
- **Frontend**: (Components/pages affected)
- **Backend**: (Services/APIs affected)
- **Database**: (Tables/data affected)
- **Infrastructure**: (Systems/services affected)

## Risk Assessment
- **Confidentiality Impact**: High/Medium/Low/None
- **Integrity Impact**: High/Medium/Low/None
- **Availability Impact**: High/Medium/Low/None
- **Exploitability**: Easy/Medium/Hard
- **User Data at Risk**: Yes/No

## Steps to Reproduce (if applicable)
<!-- Be careful not to include actual exploits -->
${REPRODUCTION_STEPS:-"General steps to identify the issue"}

## Mitigation Recommendations
<!-- High-level recommendations for addressing the issue -->

## Acceptance Criteria
- [ ] Security issue is properly assessed
- [ ] Fix is implemented following security best practices
- [ ] Security testing completed
- [ ] No regression in security posture
- [ ] Incident response procedures followed if needed

## Compliance Considerations
- [ ] OWASP compliance maintained
- [ ] Data protection regulations considered
- [ ] Access control patterns verified
- [ ] Audit logging maintained

## SkillMeat Security Standards
- [ ] Authentication via Clerk maintained
- [ ] RLS policies properly enforced
- [ ] PII handling follows guidelines
- [ ] Logging excludes sensitive data
- [ ] HTTPS/secure communication enforced

---
**Security Issue Template v1.0 - SkillMeat**
EOF
      ;;
    *)
      echo "${description:-"Issue description for $title"}"
      ;;
  esac
}

ISSUE_BODY=$(generate_issue_body "$ISSUE_TYPE" "$TITLE" "$DESCRIPTION")
```

### 3. Determine Labels and Priority

```bash
# Build labels based on issue type and priority
build_labels() {
  local issue_type="$1"
  local priority="$2"
  local custom_labels="$3"

  local labels="$issue_type"

  # Add priority label
  case "$priority" in
    "P0") labels+=",critical,priority-critical" ;;
    "P1") labels+=",high-priority,priority-high" ;;
    "P2") labels+=",priority-medium" ;;
    "P3") labels+=",low-priority,priority-low" ;;
  esac

  # Add type-specific labels
  case "$issue_type" in
    "bug")
      labels+=",needs-triage"
      ;;
    "enhancement")
      labels+=",feature-request,needs-discussion"
      ;;
    "task")
      labels+=",technical-debt"
      ;;
    "documentation")
      labels+=",documentation,good-first-issue"
      ;;
    "security")
      labels+=",security,needs-immediate-attention"
      ;;
  esac

  # Add area-specific labels based on title
  case "$TITLE" in
    *"frontend"*|*"UI"*|*"component"*|*"React"*|*"Storybook"*)
      labels+=",frontend"
      ;;
    *"backend"*|*"API"*|*"service"*|*"database"*|*"FastAPI"*)
      labels+=",backend"
      ;;
    *"mobile"*|*"iOS"*|*"Android"*|*"React Native"*)
      labels+=",mobile"
      ;;
    *"CI/CD"*|*"deployment"*|*"infra"*)
      labels+=",infrastructure"
      ;;
    *"test"*|*"testing"*|*"QA"*)
      labels+=",testing"
      ;;
    *"performance"*|*"optimization"*)
      labels+=",performance"
      ;;
    *"accessibility"*|*"a11y"*)
      labels+=",accessibility"
      ;;
  esac

  # Add custom labels
  if [ -n "$custom_labels" ]; then
    labels+=,"$custom_labels"
  fi

  echo "$labels"
}

FINAL_LABELS=$(build_labels "$ISSUE_TYPE" "$PRIORITY" "$LABELS")
```

### 4. Create the GitHub Issue

```bash
# Build GitHub CLI command
gh_command="gh issue create"
gh_command+=" --title \"$TITLE\""
gh_command+=" --body \"$ISSUE_BODY\""
gh_command+=" --label \"$FINAL_LABELS\""

# Add optional parameters
if [ -n "$ASSIGNEE" ]; then
  gh_command+=" --assignee \"$ASSIGNEE\""
fi

if [ -n "$MILESTONE" ]; then
  gh_command+=" --milestone \"$MILESTONE\""
fi

if [ -n "$PROJECT" ]; then
  gh_command+=" --project \"$PROJECT\""
fi

# Create the issue
echo "Creating GitHub issue..."
echo "Title: $TITLE"
echo "Type: $ISSUE_TYPE"
echo "Priority: $PRIORITY"
echo "Labels: $FINAL_LABELS"

# Execute the command
issue_result=$(eval "$gh_command" 2>&1)

if [ $? -eq 0 ]; then
  # Extract issue URL from result
  issue_url=$(echo "$issue_result" | tail -n 1)
  issue_number=$(echo "$issue_url" | grep -o '[0-9]*$')

  echo "✅ Issue created successfully!"
  echo "🔗 Issue URL: $issue_url"
  echo "📋 Issue #$issue_number: $TITLE"
  echo "🎯 Priority: $PRIORITY"
  echo "🏷️  Labels: $FINAL_LABELS"

  # Store issue information for tracking
  echo "$issue_number,$TITLE,$ISSUE_TYPE,$PRIORITY,$issue_url,$(date +%Y-%m-%d)" >> .github_issues.csv

else
  echo "❌ Failed to create issue:"
  echo "$issue_result"
  exit 1
fi
```

### 5. Post-Creation Actions

```bash
# Generate unique issue ID for internal tracking
ISSUE_ID="GH-$issue_number"

echo ""
echo "📋 Issue Creation Summary:"
echo "========================="
echo "Issue ID: $ISSUE_ID"
echo "GitHub #: $issue_number"
echo "Title: $TITLE"
echo "Type: $ISSUE_TYPE"
echo "Priority: $PRIORITY"
echo "URL: $issue_url"

# Provide type-specific follow-up actions
case "$ISSUE_TYPE" in
  "bug")
    echo ""
    echo "🐛 Bug Report Next Steps:"
    echo "- Reproduce the issue in a clean environment"
    echo "- Add screenshots or screen recordings"
    echo "- Determine root cause through debugging"
    echo "- Estimate fix complexity and timeline"
    echo "- Assign to appropriate developer"
    ;;
  "enhancement")
    echo ""
    echo "✨ Enhancement Next Steps:"
    echo "- Review and discuss with product team"
    echo "- Validate business case and user need"
    echo "- Create technical design if approved"
    echo "- Estimate development effort"
    echo "- Plan implementation timeline"
    ;;
  "task")
    echo ""
    echo "⚙️ Technical Task Next Steps:"
    echo "- Break down into smaller subtasks if needed"
    echo "- Assign to developer with relevant expertise"
    echo "- Set up development environment/branch"
    echo "- Plan testing and validation approach"
    echo "- Schedule code review"
    ;;
  "documentation")
    echo ""
    echo "📚 Documentation Next Steps:"
    echo "- Assign to technical writer or developer"
    echo "- Gather source material and references"
    echo "- Create outline and structure"
    echo "- Schedule review with subject matter experts"
    echo "- Plan integration with existing docs"
    ;;
  "security")
    echo ""
    echo "🔒 Security Issue Next Steps:"
    echo "- IMMEDIATE: Assess impact and severity"
    echo "- Review with security team/expert"
    echo "- Plan mitigation strategy"
    echo "- Implement fix with security testing"
    echo "- Update security documentation"
    ;;
esac

# Integration recommendations
echo ""
echo "🔗 Integration Recommendations:"

# Suggest Linear integration for complex issues
if [ "$ISSUE_TYPE" == "enhancement" ] || [ "$PRIORITY" == "P0" ] || [ "$PRIORITY" == "P1" ]; then
  echo "- Consider creating Linear epic for complex features:"
  echo "  /linear-create-task epic \"$TITLE\" --priority=$PRIORITY"
fi

# Suggest Trello for ideation-stage enhancements
if [ "$ISSUE_TYPE" == "enhancement" ] && [ "$PRIORITY" != "P0" ]; then
  echo "- Consider moving to Trello for further ideation:"
  echo "  /trello-add-card \"$TITLE\" --priority=$PRIORITY --category=Enhancement"
fi

# Update local tracking
if [ ! -f ".github_issues.csv" ]; then
  echo "issue_number,title,type,priority,url,created_date" > .github_issues.csv
fi

# Track in workflow
echo "$ISSUE_ID,github-$ISSUE_TYPE,$(date +%Y-%m-%d),$TITLE" >> .mp_workflow_tracking.csv

echo ""
echo "✨ GitHub issue created and workflow integration complete!"
```

## Usage Examples

### Create a Bug Report
```bash
/github-create-issue bug "Search results are incorrect on mobile Safari" --priority=P1 --labels="mobile,frontend" --assignee="frontend-dev"
```

### Create an Enhancement Request
```bash
/github-create-issue enhancement "Add dark mode toggle to settings" --priority=P2 --labels="ui,accessibility" --milestone="Q1-2024"
```

### Create a Technical Task
```bash
/github-create-issue task "Implement cursor pagination for prompts API" --priority=P2 --labels="backend,api" --assignee="backend-dev"
```

### Create Documentation Task
```bash
/github-create-issue documentation "Update Storybook stories for PromptCard component" --priority=P3 --labels="storybook,components"
```

### Create Security Issue
```bash
/github-create-issue security "Review authentication flow for potential vulnerabilities" --priority=P1 --labels="auth,review" --assignee="security-team"
```

## SkillMeat Integration Features

### 1. Template Standardization
- Structured templates for each issue type
- Consistent acceptance criteria and quality gates
- MP architecture compliance checkboxes
- Integration with development workflow

### 2. Automatic Labeling
- Priority-based labels (P0-P3)
- Area-based labels (frontend, backend, mobile)
- Type-based labels (bug, enhancement, task)
- Custom workflow labels

### 3. Workflow Integration
- Links to Linear for complex development
- Trello integration for ideation stage
- Local tracking and reporting
- Cross-tool workflow coordination

### 4. Quality Assurance
- Architecture compliance requirements
- Testing strategy inclusion
- Documentation requirements
- Security considerations

### 5. Progress Tracking
- `.github_issues.csv`: Issue tracking
- `.mp_workflow_tracking.csv`: Workflow state
- Integration with MP development processes
- Progress reporting and analytics

This command ensures GitHub Issues are created with proper structure, comprehensive context, and integration with SkillMeat' development workflow and quality standards.
