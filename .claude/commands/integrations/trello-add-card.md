---
description: Add ideation and research cards to Trello boards with structured formatting and SkillMeat workflow integration
allowed-tools: Bash, Read(./**), Write, Edit, WebFetch
argument-hint: "[card-title] [--board=board-name] [--list=list-name] [--description=text] [--labels=label1,label2] [--assignee=user] [--due-date=YYYY-MM-DD]"
---

# Trello Card Creation Command

Creates ideation and research cards in Trello following SkillMeat workflow patterns for idea capture, research coordination, and feature development preparation.

## Prerequisites

1. **Trello CLI Setup**

   ```bash
   # Install Trello CLI if not present (using unofficial CLI tool)
   if ! command -v trello &> /dev/null; then
     echo "Installing Trello CLI..."
     npm install -g trello-cli
   fi

   # Check authentication status
   trello set-auth
   if [ $? -ne 0 ]; then
     echo "❌ Trello CLI not authenticated. Run 'trello set-auth' to authenticate."
     exit 1
   fi
   ```

2. **Board and List Setup**

   ```bash
   # Get board information for SkillMeat ideation
   BOARD_NAME="SkillMeat Ideation"
   BOARD_ID=$(trello show-boards | grep "$BOARD_NAME" | cut -d' ' -f1)

   if [ -z "$BOARD_ID" ]; then
     echo "📋 Creating SkillMeat Ideation board..."
     BOARD_ID=$(trello add-board "$BOARD_NAME" | cut -d' ' -f1)

     # Create standard lists
     trello add-list "Ideas" "$BOARD_ID"
     trello add-list "Research" "$BOARD_ID"
     trello add-list "Ready for SPIKE" "$BOARD_ID"
     trello add-list "In Development" "$BOARD_ID"
     trello add-list "Completed" "$BOARD_ID"
     trello add-list "Archived" "$BOARD_ID"
   fi

   echo "Board: $BOARD_NAME ($BOARD_ID)"
   ```

## Command Execution

### 1. Parse Arguments and Set Defaults

```bash
# Parse command arguments
CARD_TITLE="$1"
BOARD_NAME="SkillMeat Ideation"
LIST_NAME="Ideas"
DESCRIPTION=""
LABELS=""
ASSIGNEE=""
DUE_DATE=""
PRIORITY="Medium"
CATEGORY="General"

# Parse optional flags
for arg in "${@:2}"; do
  case $arg in
    --board=*)
      BOARD_NAME="${arg#*=}"
      ;;
    --list=*)
      LIST_NAME="${arg#*=}"
      ;;
    --description=*)
      DESCRIPTION="${arg#*=}"
      ;;
    --labels=*)
      LABELS="${arg#*=}"
      ;;
    --assignee=*)
      ASSIGNEE="${arg#*=}"
      ;;
    --due-date=*)
      DUE_DATE="${arg#*=}"
      ;;
    --priority=*)
      PRIORITY="${arg#*=}"
      ;;
    --category=*)
      CATEGORY="${arg#*=}"
      ;;
  esac
done

# Validate required arguments
if [ -z "$CARD_TITLE" ]; then
  echo "❌ Error: Card title is required"
  echo "Usage: /trello-add-card [card-title] [options]"
  exit 1
fi
```

### 2. Generate Structured Card Description

```bash
# Generate card description template based on category
generate_card_description() {
  local title="$1"
  local custom_description="$2"
  local category="$3"
  local priority="$4"

  cat << EOF
# 💡 Idea: $title

## Overview
${custom_description:-"Idea description for $title"}

## Business Context
- **Priority**: $priority
- **Category**: $category
- **Submitted**: $(date +"%Y-%m-%d")
- **Status**: Ideation

## Key Questions
- What problem does this solve?
- Who would benefit from this feature?
- How does this align with MP goals?
- What's the expected business impact?

## Initial Assessment
### Business Value
- [ ] High user impact potential
- [ ] Aligns with product strategy
- [ ] Market differentiation opportunity
- [ ] Revenue/engagement impact

### Technical Feasibility
- [ ] Fits within current architecture
- [ ] Reasonable implementation complexity
- [ ] Available technical expertise
- [ ] No major infrastructure changes needed

### Resource Requirements
- [ ] Design resources needed
- [ ] Development resources estimated
- [ ] Timeline considerations
- [ ] Dependencies identified

## Research Needed
- [ ] User research and validation
- [ ] Competitive analysis
- [ ] Technical feasibility study
- [ ] Business case development
- [ ] Success metrics definition

## Success Criteria (Preliminary)
- [ ] (Define when research is complete)
- [ ] (Add measurable outcomes)
- [ ] (Include user satisfaction metrics)

## Next Steps
1. Conduct initial research
2. Validate with stakeholders
3. Create feature brief if promising
4. Move to SPIKE analysis if approved

## Related Links
- User feedback: (add links)
- Competitive references: (add links)
- Technical references: (add links)

---
**Workflow Status**: Ideas → Research → Ready for SPIKE → In Development → Completed

**Tags**: #ideation #$category #$(echo $priority | tr '[:upper:]' '[:lower:]')
EOF
}

CARD_DESCRIPTION=$(generate_card_description "$CARD_TITLE" "$DESCRIPTION" "$CATEGORY" "$PRIORITY")
```

### 3. Determine Card Category and Labels

```bash
# Auto-categorize based on title keywords
auto_categorize() {
  local title="$1"

  case "$title" in
    *"UI"*|*"interface"*|*"design"*|*"component"*|*"visual"*)
      echo "UI/UX"
      ;;
    *"API"*|*"backend"*|*"database"*|*"service"*|*"integration"*)
      echo "Backend"
      ;;
    *"user"*|*"customer"*|*"experience"*|*"workflow"*)
      echo "User Experience"
      ;;
    *"performance"*|*"speed"*|*"optimization"*|*"scalability"*)
      echo "Performance"
      ;;
    *"security"*|*"auth"*|*"permission"*|*"privacy"*)
      echo "Security"
      ;;
    *"analytics"*|*"tracking"*|*"metrics"*|*"reporting"*)
      echo "Analytics"
      ;;
    *"mobile"*|*"iOS"*|*"Android"*|*"app"*)
      echo "Mobile"
      ;;
    *"AI"*|*"ML"*|*"intelligence"*|*"automation"*)
      echo "AI/ML"
      ;;
    *)
      echo "General"
      ;;
  esac
}

# Set category if not provided
if [ "$CATEGORY" == "General" ]; then
  CATEGORY=$(auto_categorize "$CARD_TITLE")
fi

# Build labels list
label_list="$CATEGORY"

# Add priority label
case "$PRIORITY" in
  "Critical"|"High") label_list+=",High Priority" ;;
  "Low") label_list+=",Low Priority" ;;
  *) label_list+=",Medium Priority" ;;
esac

# Add custom labels
if [ -n "$LABELS" ]; then
  label_list+=,"$LABELS"
fi
```

### 4. Find or Create Target List

```bash
# Get board ID
BOARD_ID=$(trello show-boards | grep "$BOARD_NAME" | head -1 | cut -d' ' -f1)

if [ -z "$BOARD_ID" ]; then
  echo "❌ Error: Board '$BOARD_NAME' not found"
  exit 1
fi

# Get list ID
LIST_ID=$(trello show-lists "$BOARD_ID" | grep "$LIST_NAME" | head -1 | cut -d' ' -f1)

if [ -z "$LIST_ID" ]; then
  echo "📝 Creating list '$LIST_NAME' in board '$BOARD_NAME'..."
  LIST_ID=$(trello add-list "$LIST_NAME" "$BOARD_ID" | cut -d' ' -f1)
fi

echo "Target List: $LIST_NAME ($LIST_ID)"
```

### 5. Handle Assignee and Due Date

```bash
# Find assignee by username (Trello uses usernames)
assignee_arg=""
if [ -n "$ASSIGNEE" ]; then
  # In real implementation, would validate username exists
  assignee_arg="--assign $ASSIGNEE"
fi

# Format due date
due_date_arg=""
if [ -n "$DUE_DATE" ]; then
  # Validate date format (YYYY-MM-DD)
  if [[ "$DUE_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    due_date_arg="--due $DUE_DATE"
  else
    echo "⚠️  Warning: Invalid due date format. Use YYYY-MM-DD."
  fi
fi
```

### 6. Create the Card in Trello

```bash
# Generate unique card ID for tracking
CARD_ID="IDEA-$(date +%Y%m%d-%H%M%S)"

# Build card title with ID
FULL_TITLE="$CARD_ID: $CARD_TITLE"

# Create the card
echo "Creating Trello card..."
echo "Title: $FULL_TITLE"
echo "Board: $BOARD_NAME"
echo "List: $LIST_NAME"
echo "Category: $CATEGORY"
echo "Priority: $PRIORITY"

# Execute Trello command
trello_command="trello add-card \"$FULL_TITLE\" \"$LIST_ID\""

if [ -n "$CARD_DESCRIPTION" ]; then
  # Save description to temp file (Trello CLI may not handle long descriptions well via command line)
  temp_desc_file="/tmp/trello_desc_${CARD_ID}.txt"
  echo "$CARD_DESCRIPTION" > "$temp_desc_file"
  trello_command+=" --desc-file \"$temp_desc_file\""
fi

# Add labels if supported by CLI
if [ -n "$label_list" ]; then
  trello_command+=" --labels \"$label_list\""
fi

# Add assignee and due date
trello_command+=" $assignee_arg $due_date_arg"

# Execute the command
echo "Command: $trello_command"
card_result=$(eval "$trello_command" 2>&1)

if [ $? -eq 0 ]; then
  # Extract card URL from result (if provided by CLI)
  card_url=$(echo "$card_result" | grep -o 'https://trello.com/c/[^[:space:]]*' || echo "")

  echo "✅ Card created successfully!"
  echo "📋 Card ID: $CARD_ID"
  echo "📝 Title: $CARD_TITLE"
  echo "📂 Category: $CATEGORY"
  echo "🎯 Priority: $PRIORITY"

  if [ -n "$card_url" ]; then
    echo "🔗 Trello URL: $card_url"
  fi

  # Clean up temp file
  if [ -f "$temp_desc_file" ]; then
    rm "$temp_desc_file"
  fi

  # Store card information for tracking
  echo "$CARD_ID,$BOARD_NAME,$LIST_NAME,$CARD_TITLE,$CATEGORY,$PRIORITY,$(date +%Y-%m-%d)" >> .trello_cards.csv

else
  echo "❌ Failed to create card:"
  echo "$card_result"

  # Clean up temp file on error
  if [ -f "$temp_desc_file" ]; then
    rm "$temp_desc_file"
  fi

  exit 1
fi
```

### 7. Post-Creation Actions and Workflow Integration

```bash
# Add workflow-specific actions based on list
case "$LIST_NAME" in
  "Ideas")
    echo ""
    echo "💡 Idea Capture Workflow:"
    echo "========================="
    echo "1. ✅ Idea captured in Trello"
    echo "2. 📋 Next: Gather initial feedback and validation"
    echo "3. 🔍 Then: Move to 'Research' when ready for analysis"
    echo "4. 📝 Eventually: Create Feature Brief if promising"
    ;;
  "Research")
    echo ""
    echo "🔍 Research Workflow:"
    echo "===================="
    echo "1. ✅ Research task created"
    echo "2. 📊 Next: Conduct user research and competitive analysis"
    echo "3. 📋 Then: Document findings and business case"
    echo "4. 🎯 Eventually: Move to 'Ready for SPIKE' if validated"
    ;;
  "Ready for SPIKE")
    echo ""
    echo "🎯 SPIKE Preparation:"
    echo "===================="
    echo "1. ✅ Feature ready for technical analysis"
    echo "2. 📝 Next: Create Feature Brief document"
    echo "3. 🔧 Then: Conduct SPIKE analysis with technical team"
    echo "4. 📋 Eventually: Create PRD if technically feasible"
    ;;
esac

# Provide follow-up recommendations
echo ""
echo "📋 Recommended Next Steps:"
echo "- Add relevant stakeholders to the card"
echo "- Attach supporting documents or links"
echo "- Set up regular review schedule"
echo "- Define specific research questions (if applicable)"
echo "- Link to related cards or external resources"

# Update local tracking
if [ ! -f ".trello_cards.csv" ]; then
  echo "card_id,board,list,title,category,priority,created_date" > .trello_cards.csv
fi
```

### 8. Integration with SkillMeat Workflow

```bash
# Create workflow tracking entry
echo ""
echo "🔄 Workflow Integration:"
echo "======================="

# Suggest Linear integration if idea progresses
if [ "$LIST_NAME" == "Ready for SPIKE" ] || [ "$LIST_NAME" == "In Development" ]; then
  echo "💡 Consider creating Linear epic when moving to development:"
  echo "   /linear-create-task epic \"$CARD_TITLE\" --priority=$PRIORITY --labels=\"$CATEGORY\""
fi

# Suggest documentation if research stage
if [ "$LIST_NAME" == "Research" ]; then
  echo "📚 Consider creating research document:"
  echo "   Create: docs/research/$(echo $CARD_TITLE | tr '[:upper:]' '[:lower:]' | tr ' ' '-')-research.md"
fi

# Track in workflow state
workflow_state="trello-$LIST_NAME"
echo "$CARD_ID,$workflow_state,$(date +%Y-%m-%d),$CARD_TITLE" >> .mp_workflow_tracking.csv

echo ""
echo "✨ Card created and workflow integration complete!"
```

## Usage Examples

### Create an Idea Card

```bash
/trello-add-card "AI-powered prompt suggestions" --category="AI/ML" --priority="High" --description="Suggest relevant prompts based on user writing style and context"
```

### Create a Research Task

```bash
/trello-add-card "Research user collaboration patterns" --list="Research" --assignee="research-team" --due-date="2024-01-15" --labels="user-research,collaboration"
```

### Create a Ready-for-SPIKE Card

```bash
/trello-add-card "Real-time collaboration implementation" --list="Ready for SPIKE" --priority="High" --category="Backend" --description="Enable multiple users to edit prompts simultaneously"
```

### Create a Board-Specific Card

```bash
/trello-add-card "Mobile app performance optimization" --board="SkillMeat Mobile" --list="Ideas" --category="Performance" --labels="mobile,optimization"
```

## SkillMeat Workflow Integration

### 1. Ideation Workflow
- **Ideas**: Initial concept capture with business context
- **Research**: User validation and competitive analysis
- **Ready for SPIKE**: Technical feasibility assessment preparation
- **In Development**: Active development tracking
- **Completed**: Delivered features
- **Archived**: Ideas that didn't progress

### 2. Template Standardization
- Consistent card structure across all ideas
- Mandatory business context and success criteria
- Research checklist for validation
- Clear next steps and workflow progression

### 3. Cross-Tool Integration
- Links to Linear for development tracking
- References to documentation and research
- Workflow state tracking across tools
- Progress monitoring and reporting

### 4. Quality Gates
- Business value assessment required
- Technical feasibility consideration
- Resource requirement estimation
- Success criteria definition

### 5. Local Tracking
- `.trello_cards.csv`: Card creation tracking
- `.mp_workflow_tracking.csv`: Cross-tool workflow state
- Integration with MP project management processes

This command ensures Trello cards are created with proper context, structured templates, and integration with the broader SkillMeat development workflow.
