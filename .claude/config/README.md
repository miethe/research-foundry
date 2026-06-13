# Template Configuration Guide

This directory contains the central configuration for customizing the claude-export system for any project.

## Files

### `template-config.json` (Primary Configuration)

The master configuration file containing 45+ variables organized into 13 categories. This file serves as the single source of truth for all project-specific values used throughout the claude-export system.

**Structure:**
- **metadata** (8 fields) - Configuration versioning and project information
- **identity** (3 variables) - Project name, description, and domain
- **architecture** (3 variables) - System architecture patterns and diagrams
- **standards** (4 variables) - Code quality, validation, naming, and patterns
- **workflow** (4 variables) - PM tools, sprint duration, approval workflows
- **documentation** (4 variables) - Documentation policy, buckets, paths, frontmatter
- **observability** (4 variables) - Logging, tracing, metrics configuration
- **permissions** (4 variables) - Tool permissions, hooks, auth, secrets
- **paths** (3 variables) - Project structure and excluded paths
- **technology** (8 variables) - Framework stack, languages, databases
- **examples** (4 variables) - Code patterns and architecture examples
- **agents** (1 variable) - Feature complexity assessment scale
- **subagents** (1 variable) - Agent routing and invocation rules
- **version** (2 variables) - Configuration schema versioning

## Quick Start

### For New Projects

1. **Copy the template:**
   ```bash
   cp template-config.json your-project-config.json
   ```

2. **Fill in required fields:**
   - `metadata.projectName` - Your project name
   - `identity.PROJECT_NAME` - Project name (SCREAMING_SNAKE_CASE)
   - `identity.PROJECT_DESCRIPTION` - What your project does
   - `identity.PROJECT_DOMAIN` - Business domain
   - `architecture.PROJECT_ARCHITECTURE` - Your system architecture
   - `standards.PROJECT_STANDARDS` - Your coding standards
   - `workflow.PM_WORKFLOW` - Your PM tool (Linear, Jira, etc.)
   - `technology.*` - Your tech stack

3. **Customize optional fields:**
   - `architecture.LAYER_ARCHITECTURE` - Detailed layer breakdown
   - `observability.*` - If you use observability tools
   - `permissions.*` - If you need custom permissions
   - `paths.*` - Your specific directory structure

4. **Validate the configuration:**
   ```bash
   python3 -m json.tool your-project-config.json
   ```

### For Existing Projects

If you're customizing for SkillMeat or an existing project:

1. **Review defaults** - The template has sensible SkillMeat defaults
2. **Compare with your project** - Update values that don't match
3. **Test with an agent** - Verify configuration works:
   ```bash
   Task("codebase-explorer", "Find all components")
   ```

## Variable Categories

### Identity (3 variables)

Identifies the project:

```json
{
  "PROJECT_NAME": "Your Project Name",
  "PROJECT_DESCRIPTION": "What your project does",
  "PROJECT_DOMAIN": "Business domain (e.g., Healthcare, FinTech)"
}
```

### Architecture (3 variables)

Describes system design:

```json
{
  "PROJECT_ARCHITECTURE": "Router → Service → Repository → DB",
  "LAYER_ARCHITECTURE": "Detailed 8-layer breakdown...",
  "ARCHITECTURE_DIAGRAM": "URL or ASCII art"
}
```

### Standards (4 variables)

Code and pattern standards:

```json
{
  "PROJECT_STANDARDS": "Layered architecture, DTOs separate, etc.",
  "VALIDATION_RULES": "Error envelopes, pagination, etc.",
  "NAMING_CONVENTION": "PREFIX-NUMBER format, kebab-case, semver",
  "CODE_QUALITY_STANDARDS": "No SQL in services, 80%+ coverage, etc."
}
```

### Workflow (4 variables)

Development process:

```json
{
  "PM_WORKFLOW": "Linear",
  "TASK_TRACKER": "Linear",
  "SPRINT_DURATION": "14",
  "APPROVAL_WORKFLOW": "GitHub PR with 2 approvals"
}
```

### Documentation (4 variables)

Documentation approach:

```json
{
  "DOC_POLICY": "Document only when explicitly needed...",
  "DOC_BUCKETS": "User Docs, Developer Docs, Architecture, etc.",
  "ADR_PATH": "/docs/architecture/ADRs",
  "DOC_FRONTMATTER": "title, description, audience, etc."
}
```

### Observability (4 variables)

Monitoring and logging:

```json
{
  "OBSERVABILITY_REQUIRED": true,
  "LOGGING_FORMAT": "Structured JSON",
  "TRACING_ENABLED": "OpenTelemetry",
  "METRICS_SYSTEM": "OpenTelemetry"
}
```

### Permissions (4 variables)

Claude Code security:

```json
{
  "PERMISSIONS": { "deny": [...], "ask": [...], "allow": [...] },
  "HOOKS": { "PreToolUse": [...] },
  "AUTH_METHOD": "Clerk",
  "ENV_GATE_SECRET": "32+ char secret"
}
```

### Paths (3 variables)

Project structure:

```json
{
  "PROJECT_PATHS": {
    "api": "services/api",
    "web": "apps/web",
    "ui": "packages/ui"
  },
  "EXCLUDED_PATHS": "node_modules, .git, __pycache__",
  "SYMBOL_FILES": { "api": "ai/symbols-api.json" }
}
```

### Technology (8 variables)

Tech stack:

```json
{
  "FRONTEND_FRAMEWORK": "React with Next.js",
  "BACKEND_LANGUAGE": "Python 3.12",
  "BACKEND_FRAMEWORK": "FastAPI",
  "DATABASE": "PostgreSQL with SQLAlchemy ORM",
  "UI_LIBRARY": "Radix UI components",
  "PACKAGE_MANAGER": "pnpm",
  "BUILD_TOOL": "Turbo",
  "TESTING_FRAMEWORK": "Pytest, Jest"
}
```

### Examples (4 variables)

Real patterns from your project:

```json
{
  "PROJECT_EXAMPLES": "Real code examples...",
  "EXAMPLE_FEATURE": "User authentication",
  "EXAMPLE_ARCHITECTURE": "Full architecture description",
  "EXAMPLE_ERROR_HANDLING": "Error envelope pattern"
}
```

## Understanding Variable Types

Each variable has metadata:

```json
{
  "VARIABLE_NAME": {
    "description": "What this variable is for",
    "default": "Sensible default value",
    "required": true,           // Must customize for new projects
    "type": "string",           // string, boolean, object, array
    "examples": [               // Examples of valid values
      "Example 1",
      "Example 2"
    ],
    "enum": ["option1", "option2"]  // Only if restricted values
  }
}
```

### Type Reference

- **string** - Text values (project name, descriptions)
- **boolean** - true/false (observability required?)
- **object** - Structured data (paths, permissions, hooks)
- **array** - Lists of values (examples)

### Required vs Optional

- **required: true** - Must customize for new projects
- **required: false** - Optional, can use default

## Using This Configuration

### In Agents

Variables are used in agent prompts to customize behavior:

```markdown
You are the GitHub Issues orchestrator for SkillMeat...
```

### In Templates

Variables customize templates for your project:

```markdown
## Implementation Strategy

Following SkillMeat architecture patterns:

1. Source Layer (GitHub, local sources)
```

### In Configuration Files

Variables populate configuration files:

```json
{
  "projectName": "SkillMeat",
  "paths": {,
  "permissions": {
}
```

## Customization Workflow

### Step 1: Copy Template

```bash
cp config/template-config.json .claude-config.json
```

### Step 2: Update Identity

```json
{
  "identity": {
    "PROJECT_NAME": "MyProject",
    "PROJECT_DESCRIPTION": "My awesome project",
    "PROJECT_DOMAIN": "Cloud Computing"
  }
}
```

### Step 3: Update Architecture

```json
{
  "architecture": {
    "PROJECT_ARCHITECTURE": "Microservices with event-driven...",
    "LAYER_ARCHITECTURE": "Your layer breakdown...",
    "ARCHITECTURE_DIAGRAM": "URL to diagram"
  }
}
```

### Step 4: Update Tech Stack

```json
{
  "technology": {
    "FRONTEND_FRAMEWORK": "Vue 3 with Nuxt",
    "BACKEND_LANGUAGE": "Go 1.21",
    "BACKEND_FRAMEWORK": "Gin",
    "DATABASE": "MongoDB",
    "UI_LIBRARY": "Ant Design"
  }
}
```

### Step 5: Update Workflow

```json
{
  "workflow": {
    "PM_WORKFLOW": "Jira",
    "TASK_TRACKER": "Jira",
    "SPRINT_DURATION": "21",
    "APPROVAL_WORKFLOW": "Single maintainer approval"
  }
}
```

### Step 6: Customize Standards

```json
{
  "standards": {
    "PROJECT_STANDARDS": "Your standards here",
    "VALIDATION_RULES": "Your validation rules",
    "NAMING_CONVENTION": "Your naming convention",
    "CODE_QUALITY_STANDARDS": "Your quality standards"
  }
}
```

### Step 7: Test Configuration

```bash
# Test with an agent
Task("codebase-explorer", "Find all major components")

# Check if variables are properly recognized
```

## Variable Priority Levels

### Critical (Customize First)

These variables are essential:

- `PROJECT_NAME` - Appears everywhere
- `PROJECT_ARCHITECTURE` - Core to agents
- `LAYER_ARCHITECTURE` - Used in implementation planning
- `PROJECT_STANDARDS` - Enforcement rules
- `TASK_TRACKER` - PM integration
- `TECHNOLOGY` stack - Implementation guidance

### High (Should Customize Early)

- `WORKFLOW` variables
- `DOCUMENTATION` policy
- `PERMISSIONS`
- `PATHS` - Project structure

### Medium (Nice to Customize)

- `OBSERVABILITY` settings
- `EXAMPLES` - Teaching patterns
- `NAMING_CONVENTION`
- `CODE_QUALITY_STANDARDS`

### Low (Optional)

- `ARCHITECTURE_DIAGRAM`
- Detailed observability config
- Example features

## Common Customization Scenarios

### For a Node.js/React Project

```json
{
  "identity": {
    "PROJECT_NAME": "WebApp",
    "PROJECT_DESCRIPTION": "Modern web application"
  },
  "technology": {
    "FRONTEND_FRAMEWORK": "React with Next.js",
    "BACKEND_LANGUAGE": "Node.js 18+",
    "BACKEND_FRAMEWORK": "Express",
    "DATABASE": "MongoDB with Mongoose",
    "UI_LIBRARY": "Shadcn/ui"
  }
}
```

### For a Python/Flask Project

```json
{
  "identity": {
    "PROJECT_NAME": "DataService",
    "PROJECT_DESCRIPTION": "Data processing service"
  },
  "technology": {
    "FRONTEND_FRAMEWORK": "Vue 3",
    "BACKEND_LANGUAGE": "Python 3.11",
    "BACKEND_FRAMEWORK": "Flask",
    "DATABASE": "PostgreSQL",
    "UI_LIBRARY": "Bootstrap"
  }
}
```

### For a Mobile-First Project

```json
{
  "identity": {
    "PROJECT_NAME": "MobileApp",
    "PROJECT_DESCRIPTION": "Mobile-first application"
  },
  "technology": {
    "FRONTEND_FRAMEWORK": "React Native with Expo",
    "BACKEND_LANGUAGE": "Python 3.12",
    "BACKEND_FRAMEWORK": "FastAPI",
    "DATABASE": "PostgreSQL",
    "UI_LIBRARY": "Native Elements"
  }
}
```

## Validation

### Validate JSON Syntax

```bash
python3 -m json.tool your-config.json > /dev/null && echo "Valid!"
```

### Check Required Fields

All variables marked `"required": true` must be customized:

- `metadata.projectName`
- `identity.PROJECT_NAME`
- `identity.PROJECT_DESCRIPTION`
- `identity.PROJECT_DOMAIN`
- `architecture.PROJECT_ARCHITECTURE`
- `standards.PROJECT_STANDARDS`
- `workflow.PM_WORKFLOW`
- `workflow.TASK_TRACKER`
- `technology.*` (most tech variables)
- `paths.PROJECT_PATHS`

### Test with Claude Code

```bash
# Create a simple test task
Task("codebase-explorer", "Find all test files")

# If variables work, agent should use your project config
```

## Integration with Templatization

This file works with the `TEMPLATIZATION_GUIDE.md`:

1. **TEMPLATIZATION_GUIDE.md** - Documents all variables and how they're used
2. **template-config.json** - Provides the values for those variables
3. **Agent/template files** - Use `{{VARIABLE_NAME}}` placeholders
4. **Substitution script** - Replaces placeholders with config values

## Next Steps

1. **Copy** `template-config.json` to your project
2. **Customize** required fields for your project
3. **Validate** JSON syntax
4. **Test** with an agent using `Task()`
5. **Reference** TEMPLATIZATION_GUIDE.md for detailed documentation

## Troubleshooting

### "Variable not recognized"

Check:
1. Variable name matches exactly (case-sensitive)
2. Variable is defined in your config file
3. JSON syntax is valid (`python3 -m json.tool`)

### "Default value doesn't match my project"

Update the default value in your customized config file. Defaults are SkillMeat-specific.

### "Which variables do I need to customize?"

Check the `required` field:
- `"required": true` - Must customize
- `"required": false` - Optional, can use default

## References

- **TEMPLATIZATION_GUIDE.md** - Complete variable documentation
- **CLAUDE.md** - Operating manual for the configuration system
- **../CLAUDE.md** - SkillMeat project-specific guide
- **../README.md** - Repository overview

## Version History

- **1.0.0 (2025-11-05)** - Initial template-config.json with 45+ variables
  - 13 categories of configuration
  - Comprehensive descriptions and examples
  - SkillMeat defaults included
  - Production-ready format
