# Configuration Directory Index

Complete guide to all configuration files for template-config customization.

## Files in This Directory

### 1. template-config.json (Primary Configuration)

**Purpose:** Master configuration file containing all 45+ variables organized by category.

**Size:** 20KB | **Lines:** 586

**Contains:**
- Metadata (8 fields) - Project info and versioning
- 13 categories of configuration variables
- 45 total variables with descriptions, defaults, types, and examples
- Production-ready JSON format

**When to use:**
- As the base for all project configurations
- Reference for available variables
- Source for substitution in agents/templates

**Key sections:**
- Identity (PROJECT_NAME, PROJECT_DESCRIPTION, PROJECT_DOMAIN)
- Architecture (PROJECT_ARCHITECTURE, LAYER_ARCHITECTURE)
- Standards (VALIDATION_RULES, CODE_QUALITY_STANDARDS)
- Workflow (PM_WORKFLOW, TASK_TRACKER)
- Technology (FRONTEND_FRAMEWORK, BACKEND_LANGUAGE, etc.)

### 2. template-config-schema.json (JSON Schema)

**Purpose:** JSON Schema for validating template-config.json files.

**Size:** 17KB

**Validates:**
- Required fields
- Field types (string, boolean, object, array)
- Required sub-properties
- Pattern matching (dates, versions)
- URI formatting for URLs

**When to use:**
- Validate your custom configuration files
- IDE/editor schema support (VS Code JSON)
- CI/CD validation pipelines
- Configuration linting tools

**Features:**
- Draft-07 JSON Schema format
- Type constraints
- Required field validation
- Enum constraints for limited options

### 3. README.md (Detailed Documentation)

**Purpose:** Comprehensive guide to understanding and customizing the configuration.

**Size:** 12KB

**Contains:**
- Quick start for new projects
- Detailed variable descriptions by category
- Customization workflow (7 steps)
- Variable priority levels (Critical, High, Medium, Low)
- Common customization scenarios
- Validation and troubleshooting
- Integration with templatization system

**When to use:**
- Learning how to customize the configuration
- Understanding variable categories
- Following step-by-step customization
- Troubleshooting configuration issues
- Checking variable types and examples

**Key sections:**
- Quick Start (copy, fill, customize, validate)
- Variable Categories (detailed breakdown)
- Customization Workflow
- Priority Implementation Order
- Common Scenarios (Web App, Mobile, Python Backend)

### 4. QUICK_REFERENCE.md (Quick Lookup Card)

**Purpose:** Fast reference guide for all variables and common tasks.

**Size:** 11KB

**Contains:**
- All 45+ variables organized in lookup tables
- Variable type reference
- Customization checklist
- Quick examples by project type
- Priority implementation order
- Common customization snippets
- File usage patterns

**When to use:**
- Quick lookup of variable names and purposes
- Checking if you need to customize a variable
- Finding examples for your project type
- Verifying required vs optional fields
- Quick customization reference

**Key sections:**
- Variable Lookup by Category (tables with all info)
- Customization Checklist
- Quick Examples by Project Type
- Variable Types at a Glance
- Priority Implementation Order

## Quick Start Decision Tree

### "I need to customize this for my project"
Start with **README.md** → Follow "Customization Workflow" section

### "I need to look up a specific variable"
Check **QUICK_REFERENCE.md** → Variable Lookup by Category table

### "I need to validate my configuration file"
Use **template-config-schema.json** → Validate with `python3 -m json.tool`

### "I need to understand all available variables"
Read **template-config.json** → Each variable has description, type, examples

### "I need examples for my tech stack"
See **QUICK_REFERENCE.md** → "Quick Examples by Project Type" section

### "I need detailed docs on a variable"
Check **TEMPLATIZATION_GUIDE.md** (parent directory) → Complete variable documentation

## File Organization

```
config/
├── template-config.json              (Master config with all variables)
├── template-config-schema.json       (JSON Schema for validation)
├── README.md                         (Comprehensive guide)
├── QUICK_REFERENCE.md               (Quick lookup card)
├── INDEX.md                         (This file)
└── [your-project-config.json]       (Your customized copy)
```

## Common Workflows

### Creating a New Project Configuration

1. Copy `template-config.json` to `your-project-config.json`
2. Open `README.md` → Follow "Customization Workflow"
3. Update required variables (marked `required: true`)
4. Validate with: `python3 -m json.tool your-project-config.json`
5. Test with Claude Code: `Task("codebase-explorer", "Find components")`

### Validating Your Configuration

```bash
# Method 1: Python JSON validator
python3 -m json.tool your-project-config.json > /dev/null && echo "Valid JSON!"

# Method 2: Using JSON schema (requires ajv or similar)
ajv validate -s template-config-schema.json -d your-project-config.json
```

### Finding Variables for Your Stack

1. Open `QUICK_REFERENCE.md`
2. Go to "Quick Examples by Project Type"
3. Find your type (Web App, Mobile, Backend Service, etc.)
4. Copy the JSON snippet
5. Customize with your specific values

### Implementing a Complete Configuration

1. Start with `template-config.json` defaults
2. Check `QUICK_REFERENCE.md` Customization Checklist
3. Update "Must Customize" variables (13 variables)
4. Update "Tech Stack" variables (5 variables)
5. Update "Project Structure" variables (1 variable)
6. Validate JSON syntax
7. Test with an agent

## Variable Statistics

| Category | Count | Required | Optional |
|----------|-------|----------|----------|
| Identity | 3 | 3 | 0 |
| Architecture | 3 | 2 | 1 |
| Standards | 4 | 4 | 0 |
| Workflow | 4 | 2 | 2 |
| Documentation | 4 | 3 | 1 |
| Observability | 4 | 0 | 4 |
| Permissions | 4 | 0 | 4 |
| Paths | 3 | 1 | 2 |
| Technology | 8 | 5 | 3 |
| Examples | 4 | 0 | 4 |
| Agents | 1 | 0 | 1 |
| Subagents | 1 | 0 | 1 |
| Version | 2 | 2 | 0 |
| **TOTAL** | **45** | **22** | **23** |

## Integration Points

### With Agents
Variables are used in agent prompts:
```markdown
You are the GitHub Issues orchestrator for SkillMeat
```

### With Templates
Variables customize templates:
```markdown
## SkillMeat Implementation

Following Collection (Personal Library) → Projects (Local .claude/ directories) → Deployment Engine → User/Local Scopes patterns:
1. Source Layer (GitHub, local sources)
```

### With Scripts
Variables configure behavior:
```json
{
  "projectName": "SkillMeat",
  "paths": {
}
```

## Troubleshooting

### "JSON validation fails"
- Check for missing commas between properties
- Verify string quotes are matched
- Use online JSON validator: https://jsonlint.com/
- Run: `python3 -m json.tool your-config.json`

### "Variable not recognized"
- Check spelling (case-sensitive, SCREAMING_SNAKE_CASE)
- Verify variable is in template-config.json
- Confirm variable is used in agent/template file
- Search: `grep "VARIABLE_NAME" template-config.json`

### "Don't know which variables are required"
- Check `required` field in template-config.json
- See QUICK_REFERENCE.md "Customization Checklist"
- Look for `required: true` in variable definitions

### "Need examples for my project type"
- See README.md "Common Customization Scenarios"
- Check QUICK_REFERENCE.md "Quick Examples by Project Type"
- Copy and customize for your tech stack

## Files Used Together

### Configuration Trilogy
1. **template-config.json** - The values
2. **template-config-schema.json** - Validation rules
3. **README.md** - How to customize

### Quick Reference Stack
1. **QUICK_REFERENCE.md** - Fast lookup
2. **template-config.json** - Detailed info
3. **TEMPLATIZATION_GUIDE.md** (parent) - Complete documentation

### Implementation Path
1. **README.md** - Read "Quick Start"
2. **QUICK_REFERENCE.md** - Check "Customization Checklist"
3. **template-config.json** - Copy and customize
4. **template-config-schema.json** - Validate

## Next Steps

### If you're new to this system:
1. Read **README.md** intro
2. Copy **template-config.json**
3. Follow README.md "Customization Workflow"
4. Validate with schema
5. Test with an agent

### If you're customizing for a specific project:
1. Check **QUICK_REFERENCE.md** for your project type
2. Copy relevant values to your config
3. Update remaining variables from README.md
4. Validate and test

### If you need detailed variable documentation:
1. Check **template-config.json** for description, type, examples
2. See **README.md** for detailed explanations
3. Refer to **TEMPLATIZATION_GUIDE.md** (parent) for complete docs
4. Check **QUICK_REFERENCE.md** for quick lookup

## Version Information

- **Configuration Version:** 1.0.0
- **Schema Version:** 1.0.0
- **Last Updated:** 2025-11-05
- **Status:** Production Ready

## Related Documentation

- **TEMPLATIZATION_GUIDE.md** (parent dir) - Complete variable documentation
- **CLAUDE.md** (parent dir) - Operating manual
- **../CLAUDE.md** - SkillMeat project guide
- **../README.md** - Repository overview
- **examples/** - Real-world examples

## Summary

This directory provides everything needed to customize the claude-export system:

- **template-config.json** - 45+ variables, production-ready defaults
- **README.md** - Complete customization guide
- **QUICK_REFERENCE.md** - Fast variable lookup and examples
- **template-config-schema.json** - JSON Schema validation
- **INDEX.md** - This file, directory guide

Start with **README.md** for customization, use **QUICK_REFERENCE.md** for quick lookups, and reference **template-config.json** for detailed variable information.
