---
description: Create Architecture Decision Records (ADRs) with MP patterns and traceability
allowed-tools: Read(./**), Write, Edit, Bash(git:*), Grep, Glob
argument-hint: "<decision-title> [--status=proposed|accepted|deprecated|superseded] [--template=standard|lightweight]"
---

# Create Architecture Decision Record

Creates structured Architecture Decision Records (ADRs) following SkillMeat patterns with proper numbering, traceability, and integration with the docs system.

## Context Analysis

Analyze current ADR state and determine next sequence number:

```bash
# Check existing ADR directory structure
echo "=== ADR Directory Analysis ==="
if [ -d "docs/adrs" ] || [ -d "docs/architecture/ADRs" ]; then
  adr_dir=$([ -d "docs/adrs" ] && echo "docs/adrs" || echo "docs/architecture/ADRs")
  echo "ADR directory: $adr_dir"

  # Count existing ADRs and determine next number
  existing_adrs=$(find "$adr_dir" -name "ADR-*.md" | wc -l)
  next_number=$(printf "%04d" $((existing_adrs + 1)))
  echo "Existing ADRs: $existing_adrs"
  echo "Next ADR number: $next_number"

  # Show recent ADRs for context
  echo -e "\nRecent ADRs:"
  find "$adr_dir" -name "ADR-*.md" | sort | tail -5
else
  echo "No ADR directory found - will create docs/adrs"
  adr_dir="docs/adrs"
  next_number="0001"
fi
```

## ADR Template Generation

### 1. Standard Template (Comprehensive)

For significant architectural decisions:

```markdown
# ADR-{number}: {Title}

## Status

{Status} - {Date}

{Optional: Supersedes ADR-XXXX | Superseded by ADR-YYYY}

## Context

{What is the issue that we're seeing that is motivating this decision or change?}

## Decision

{What is the change that we're proposing or have agreed to implement?}

## Rationale

{Why are we making this decision? What factors influenced it?}

### Considered Alternatives

1. **{Alternative 1}**
   - Pros: {benefits}
   - Cons: {drawbacks}
   - Decision: {why rejected/accepted}

2. **{Alternative 2}**
   - Pros: {benefits}
   - Cons: {drawbacks}
   - Decision: {why rejected/accepted}

## Consequences

### Positive
- {Good consequence 1}
- {Good consequence 2}

### Negative
- {Bad consequence 1}
- {Bad consequence 2}

### Neutral
- {Neutral consequence 1}

## Implementation

### Immediate Actions Required
- [ ] {Action item 1}
- [ ] {Action item 2}
- [ ] {Action item 3}

### Timeline
- **Phase 1** ({timeframe}): {milestone}
- **Phase 2** ({timeframe}): {milestone}

### Success Metrics
- {Metric 1}: {target}
- {Metric 2}: {target}

## Compliance & Validation

### Architectural Principles Alignment
- [ ] Follows layered architecture (router → service → repository)
- [ ] Maintains separation of concerns
- [ ] Supports observability requirements
- [ ] Considers security implications

### Code Quality Impact
- Testing strategy: {how this affects testing}
- Documentation updates: {what docs need updating}
- Migration path: {how to transition existing code}

## References

- Related PRD: {link to product requirements}
- Technical Specifications: {links to specs}
- Prior Discussions: {links to discussions, RFCs, issues}
- Implementation PR: {link when available}

## Metadata

- **Author**: {author name}
- **Reviewers**: {list of reviewers}
- **Epic/Story**: {associated work items}
- **Affected Components**: {list of systems/components}
- **Risk Level**: {High|Medium|Low}

---
*ADR Template v1.0 - SkillMeat Architecture Team*
```

### 2. Lightweight Template

For smaller, focused decisions:

```markdown
# ADR-{number}: {Title}

**Status**: {Status} | **Date**: {Date} | **Author**: {Author}

## Problem

{One paragraph describing the problem}

## Decision

{One paragraph describing the decision}

## Rationale

{Key factors that influenced this decision}

## Impact

- {Impact 1}
- {Impact 2}
- {Impact 3}

## Implementation

- [ ] {Action 1}
- [ ] {Action 2}

---
*Tags: {tag1}, {tag2}, {tag3}*
```

## ADR Creation Process

### 1. Generate ADR File

```bash
# Create new ADR with proper naming and numbering
create_adr() {
  local title="$1"
  local status="${2:-proposed}"
  local template="${3:-standard}"
  local author=$(git config user.name || echo "Unknown")
  local date=$(date +"%Y-%m-%d")

  # Ensure ADR directory exists
  mkdir -p "$adr_dir"

  # Create sanitized filename
  sanitized_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
  filename="ADR-${next_number}-${sanitized_title}.md"
  filepath="$adr_dir/$filename"

  echo "Creating ADR: $filepath"

  # Generate content based on template
  if [ "$template" = "lightweight" ]; then
    generate_lightweight_adr "$title" "$status" "$author" "$date" > "$filepath"
  else
    generate_standard_adr "$title" "$status" "$author" "$date" > "$filepath"
  fi

  echo "✅ ADR created: $filepath"
  echo "📝 Next steps:"
  echo "   1. Fill in the template sections"
  echo "   2. Review with team"
  echo "   3. Update status when decision is made"
  echo "   4. Link from relevant documentation"
}
```

### 2. Template Generation Functions

```bash
# Generate standard ADR template
generate_standard_adr() {
  local title="$1"
  local status="$2"
  local author="$3"
  local date="$4"

  cat << EOF
# ADR-${next_number}: ${title}

## Status

**${status}** - ${date}

## Context

<!-- What is the issue that we're seeing that is motivating this decision or change? -->

<!-- Include background information such as: -->
<!-- - Current architecture/implementation -->
<!-- - Pain points or limitations -->
<!-- - Requirements driving the change -->
<!-- - Stakeholder concerns -->

## Decision

<!-- What is the change that we're proposing or have agreed to implement? -->

<!-- Be specific about: -->
<!-- - What will be different after this decision -->
<!-- - Technologies, patterns, or approaches chosen -->
<!-- - Scope and boundaries of the decision -->

## Rationale

<!-- Why are we making this decision? What factors influenced it? -->

### Considered Alternatives

1. **Alternative 1 Name**
   - Pros:
   - Cons:
   - Decision:

2. **Alternative 2 Name**
   - Pros:
   - Cons:
   - Decision:

<!-- Add more alternatives as needed -->

## Consequences

### Positive
-

### Negative
-

### Neutral
-

## Implementation

### Immediate Actions Required
- [ ]
- [ ]
- [ ]

### Timeline
- **Phase 1** (timeframe): milestone
- **Phase 2** (timeframe): milestone

### Success Metrics
- Metric 1: target
- Metric 2: target

## Compliance & Validation

### Architectural Principles Alignment
- [ ] Follows layered architecture (router → service → repository)
- [ ] Maintains separation of concerns
- [ ] Supports observability requirements
- [ ] Considers security implications

### Code Quality Impact
- **Testing strategy**:
- **Documentation updates**:
- **Migration path**:

## References

- Related PRD:
- Technical Specifications:
- Prior Discussions:
- Implementation PR:

## Metadata

- **Author**: ${author}
- **Reviewers**:
- **Epic/Story**:
- **Affected Components**:
- **Risk Level**: Medium

---
*Created: ${date} | ADR Template v1.0 - SkillMeat*
EOF
}

# Generate lightweight ADR template
generate_lightweight_adr() {
  local title="$1"
  local status="$2"
  local author="$3"
  local date="$4"

  cat << EOF
# ADR-${next_number}: ${title}

**Status**: ${status} | **Date**: ${date} | **Author**: ${author}

## Problem

<!-- One paragraph describing the problem this decision addresses -->

## Decision

<!-- One paragraph describing what we decided to do -->

## Rationale

<!-- Key factors that influenced this decision -->
-
-
-

## Impact

<!-- How this decision affects the codebase, team, or product -->
-
-
-

## Implementation

- [ ]
- [ ]
- [ ]

---
*Tags: architecture, {add-relevant-tags}*
EOF
}
```

## ADR Management and Lifecycle

### 1. Status Management

```bash
# Update ADR status
update_adr_status() {
  local adr_file="$1"
  local new_status="$2"
  local date=$(date +"%Y-%m-%d")

  if [ ! -f "$adr_file" ]; then
    echo "❌ ADR file not found: $adr_file"
    return 1
  fi

  # Update status line
  sed -i.bak "s/\*\*[^*]*\*\* - [0-9-]*/\*\*${new_status}\*\* - ${date}/" "$adr_file"

  # Add status change note
  echo -e "\n*Status updated to ${new_status} on ${date}*" >> "$adr_file"

  echo "✅ ADR status updated to: $new_status"
}

# Link ADRs (superseding relationships)
link_adrs() {
  local superseding_adr="$1"
  local superseded_adr="$2"

  # Add superseded note to old ADR
  echo -e "\n**Superseded by**: [$superseding_adr](./$superseding_adr)" >> "$adr_dir/$superseded_adr"

  # Add supersedes note to new ADR
  sed -i.bak "/^## Status/a\\
**Supersedes**: [$superseded_adr](./$superseded_adr)\\
" "$adr_dir/$superseding_adr"

  echo "✅ Linked ADRs: $superseding_adr supersedes $superseded_adr"
}
```

### 2. ADR Index Generation

```bash
# Generate ADR index/table of contents
generate_adr_index() {
  local adr_dir="$1"
  local index_file="$adr_dir/README.md"

  cat > "$index_file" << 'EOF'
# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for SkillMeat, documenting significant architectural choices and their rationale.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Process

1. **Propose** - Create ADR with status "proposed"
2. **Review** - Team reviews and discusses the decision
3. **Accept/Reject** - Update status to "accepted" or "rejected"
4. **Implement** - Track implementation progress
5. **Review Impact** - Assess outcomes and lessons learned

## Status Definitions

- **Proposed** - Under consideration, not yet decided
- **Accepted** - Decision made and approved for implementation
- **Rejected** - Decision was considered but ultimately rejected
- **Deprecated** - Previously accepted but no longer recommended
- **Superseded** - Replaced by a newer ADR

## ADR Index

| ADR | Title | Status | Date | Author |
|-----|-------|--------|------|--------|
EOF

  # Add table rows for each ADR
  find "$adr_dir" -name "ADR-*.md" ! -name "README.md" | sort | while read adr_file; do
    # Extract metadata from ADR file
    adr_number=$(basename "$adr_file" | sed 's/ADR-\([0-9]*\)-.*/\1/')
    title=$(grep "^# ADR-" "$adr_file" | sed 's/^# ADR-[0-9]*: //')
    status=$(grep -E "\*\*[a-z]+\*\* -" "$adr_file" | sed 's/.*\*\*\([^*]*\)\*\* - .*/\1/' | head -1)
    date=$(grep -E "\*\*[a-z]+\*\* -" "$adr_file" | sed 's/.*- \([0-9-]*\).*/\1/' | head -1)
    author=$(grep "Author.*:" "$adr_file" | sed 's/.*Author[^:]*: \*\*\([^*]*\)\*\*.*/\1/' | head -1)

    # Create relative link
    relative_path=$(basename "$adr_file")
    echo "| ADR-$adr_number | [$title](./$relative_path) | $status | $date | $author |"
  done >> "$index_file"

  cat >> "$index_file" << 'EOF'

## Creating New ADRs

Use the create-adr command to generate properly formatted ADRs:

```bash
# Create standard ADR
/create-adr "Choose Database Technology"

# Create lightweight ADR
/create-adr "API Response Format" --template=lightweight

# Create with specific status
/create-adr "Migration Strategy" --status=accepted
```

## ADR Templates

- **Standard**: Comprehensive template for significant decisions
- **Lightweight**: Streamlined template for smaller decisions

## Related Documentation

- [Architecture Overview](../architecture/)
- [Technical RFCs](../rfcs/)
- [Design Decisions](../design/)
EOF

  echo "✅ ADR index generated: $index_file"
}
```

## Quality Assurance and Validation

### 1. ADR Content Validation

```bash
# Validate ADR content and structure
validate_adr() {
  local adr_file="$1"

  echo "Validating ADR: $adr_file"

  # Check required sections for standard ADR
  required_sections=("Status" "Context" "Decision" "Consequences")
  for section in "${required_sections[@]}"; do
    if grep -q "^## $section" "$adr_file"; then
      echo "✓ Has $section section"
    else
      echo "⚠ Missing $section section"
    fi
  done

  # Check for placeholder content
  if grep -q "<!-- " "$adr_file"; then
    echo "ℹ Contains template comments (consider removing after completion)"
  fi

  # Check status format
  if grep -E "\*\*[a-z]+\*\* - [0-9-]+" "$adr_file" >/dev/null; then
    echo "✓ Valid status format"
  else
    echo "⚠ Invalid status format"
  fi

  # Check ADR numbering
  filename=$(basename "$adr_file")
  if [[ "$filename" =~ ^ADR-[0-9]{4}- ]]; then
    echo "✓ Valid ADR numbering"
  else
    echo "⚠ Invalid ADR numbering format"
  fi
}
```

### 2. Cross-Reference Validation

```bash
# Check ADR references and links
validate_adr_references() {
  local adr_dir="$1"

  echo "Validating ADR cross-references..."

  # Check for broken internal ADR links
  find "$adr_dir" -name "*.md" | while read adr_file; do
    grep -o "ADR-[0-9][0-9][0-9][0-9]" "$adr_file" | while read referenced_adr; do
      if ! find "$adr_dir" -name "${referenced_adr}-*.md" | grep -q .; then
        echo "⚠ Broken ADR reference in $(basename "$adr_file"): $referenced_adr"
      fi
    done
  done

  # Check for orphaned ADRs (not referenced by others)
  echo "Checking for orphaned ADRs..."
  find "$adr_dir" -name "ADR-*.md" ! -name "*README*" | while read adr_file; do
    adr_number=$(basename "$adr_file" | sed 's/ADR-\([0-9]*\)-.*/\1/')
    if ! grep -r "ADR-$adr_number" "$adr_dir" --exclude="$(basename "$adr_file")" >/dev/null 2>&1; then
      echo "ℹ Orphaned ADR (not referenced by others): ADR-$adr_number"
    fi
  done
}
```

## Usage Examples

```bash
# Create standard ADR for major decision
/create-adr "Adopt Microservices Architecture"

# Create lightweight ADR for minor decision
/create-adr "API Error Response Format" --template=lightweight

# Create ADR with accepted status
/create-adr "Database Migration Strategy" --status=accepted

# Create ADR for specific topic
/create-adr "Authentication Method Selection" --status=proposed
```

## Integration with Development Workflow

### 1. Git Integration

```bash
# Automatically open ADR in editor after creation
open_adr_in_editor() {
  local adr_file="$1"

  # Try common editors
  if command -v code >/dev/null 2>&1; then
    code "$adr_file"
  elif command -v vim >/dev/null 2>&1; then
    vim "$adr_file"
  elif [ -n "$EDITOR" ]; then
    $EDITOR "$adr_file"
  else
    echo "ADR created at: $adr_file"
    echo "Open it in your preferred editor to complete"
  fi
}

# Create commit message for ADR
create_adr_commit() {
  local adr_file="$1"
  local adr_number=$(basename "$adr_file" | sed 's/ADR-\([0-9]*\)-.*/\1/')
  local title=$(grep "^# ADR-" "$adr_file" | sed 's/^# ADR-[0-9]*: //')

  git add "$adr_file"
  git commit -m "docs(adr): add ADR-$adr_number - $title

Created new Architecture Decision Record for: $title

Status: proposed
File: $adr_file"

  echo "✅ ADR committed to git"
}
```

### 2. Documentation Integration

```bash
# Link ADR from main architecture docs
link_adr_to_architecture() {
  local adr_file="$1"
  local arch_doc="docs/ARCHITECTURE.md"

  if [ -f "$arch_doc" ]; then
    adr_number=$(basename "$adr_file" | sed 's/ADR-\([0-9]*\)-.*/\1/')
    title=$(grep "^# ADR-" "$adr_file" | sed 's/^# ADR-[0-9]*: //')

    # Add to architecture doc if not already present
    if ! grep -q "ADR-$adr_number" "$arch_doc"; then
      echo "- [ADR-$adr_number: $title](./adrs/$(basename "$adr_file"))" >> "$arch_doc"
      echo "✅ Added ADR reference to architecture documentation"
    fi
  fi
}
```

The create-adr command ensures:

- **Consistent numbering**: Sequential ADR numbering with zero-padding
- **Proper structure**: Required sections for effective decision documentation
- **Traceability**: Links between related ADRs and superseding relationships
- **Integration**: Seamless integration with git workflow and docs system
- **Quality**: Validation and cross-reference checking
- **Templates**: Multiple templates for different types of decisions
