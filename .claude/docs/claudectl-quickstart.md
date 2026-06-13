---
title: claudectl Quick Start Guide
description: Installation and first steps with claudectl, the simplified SkillMeat CLI
audience: users
tags: [cli, getting-started, tutorial, claudectl]
created: 2025-12-24
updated: 2025-12-24
category: guide
status: published
related_documents:
  - PRD-003-claudectl-alias.md
  - PRD-003-implementation-plan.md
---

# claudectl Quick Start Guide

claudectl is a streamlined interface for SkillMeat, providing sensible defaults for common operations. It reduces typing and cognitive load while maintaining access to the full power of SkillMeat.

## Installation

### Step 1: Install the Wrapper

```bash
# Install claudectl wrapper and shell completion
skillmeat alias install

# For specific shells (bash, zsh, fish)
skillmeat alias install --shells bash zsh
```

The installation creates:
- `~/.local/bin/claudectl` - The command wrapper
- Shell completion files for selected shells
- Configuration entries in your shell rc file

### Step 2: Add to PATH (if needed)

If `~/.local/bin` is not already in your PATH, add it:

```bash
# Add to your shell's rc file (~/.bashrc, ~/.zshrc, etc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc for zsh
```

Check if it works:

```bash
claudectl --help
```

### Step 3: Verify Installation

Test that everything is working:

```bash
# Should show available commands
claudectl --help

# Should list your collection contents
claudectl list
```

## First 5 Commands

### 1. Search for Artifacts

Find artifacts by name or description:

```bash
# Search for PDF-related skills
claudectl search pdf

# Search with type filter
claudectl search auth --type skill

# JSON output (for scripting)
claudectl search pdf --format json
```

Example output:

```
Name              Type     Source                  Rating
pdf-tools         skill    anthropics/skills       4.8
pdf-expert        command  community/data-tools    4.2
spreadsheet-pdf   skill    user/specialized       5.0
```

### 2. Add an Artifact to Your Collection

Add artifacts from GitHub or local path:

```bash
# Add from GitHub (type auto-detected from name)
claudectl add anthropics/skills/canvas-design

# Add with explicit type
claudectl add user/repo/my-cli --type command

# Add from local path
claudectl add ./my-local-skill

# Add with short name (fuzzy match)
claudectl add canvas  # Automatically finds canvas-design
```

The `add` command:
- Auto-detects artifact type from name (pdf → skill, react-cli → command)
- Uses active collection by default
- Returns artifact ID and version

Example output:

```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "name": "pdf",
  "type": "skill",
  "collection": "default",
  "version": "1.2.0"
}
```

### 3. List Your Artifacts

View what's in your collection:

```bash
# List all artifacts
claudectl list

# Filter by type
claudectl list --type skill

# Show as JSON (easier to parse)
claudectl list --format json
```

Example output:

```
Name      Type     Version  Collection  Deployed  Projects
pdf       skill    1.2.0    default     Yes       2 (.claude, ../src)
canvas    skill    2.0.1    default     No        -
react-cli command  0.5.0    default     Yes       1 (.claude)
```

### 4. Deploy to Project

Deploy artifacts to your project's `.claude` directory:

```bash
# Deploy to current directory
claudectl deploy canvas-design

# Deploy multiple artifacts
claudectl deploy pdf canvas react-cli

# Deploy to specific project
claudectl deploy my-skill --project /path/to/project

# Redeploy even if already deployed
claudectl deploy pdf --force
```

The `deploy` command:
- Creates `.claude/` directory structure if needed
- Skips if already deployed (unless `--force`)
- Returns deployment location and file count

Example output:

```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "project": "/Users/user/.claude/",
  "location": "/Users/user/.claude/skills/pdf-tools",
  "file_count": 12
}
```

### 5. Check Deployment Status

View what's deployed in your project:

```bash
# Show status for current directory
claudectl status

# Show status for specific project
claudectl status --project /path/to/project

# Show detailed info (file counts, last modified)
claudectl status --detail

# Get as JSON
claudectl status --format json
```

Example output:

```
Artifact         Type     Version  Location              Files
pdf              skill    1.2.0    .claude/skills/pdf    12
canvas           skill    2.0.1    .claude/skills/canvas 8
react-testing    command  0.5.0    .claude/commands      3
```

## Common Workflows

### Find and Deploy in One Flow

The typical workflow is: search → add → deploy

```bash
# 1. Search for what you need
claudectl search pdf

# 2. Add the top result to your collection
claudectl add pdf-tools

# 3. Deploy to your project
claudectl deploy pdf-tools

# 4. Verify it's deployed
claudectl status
```

### Deploy Multiple Artifacts

Deploy a complete setup for a project:

```bash
# Add multiple artifacts
claudectl add pdf canvas react-cli

# Deploy all three
claudectl deploy pdf canvas react-cli

# Check they're all there
claudectl status
```

### Quick Add and Deploy

Combine add and deploy in one workflow:

```bash
# Search for artifact
claudectl search database-migration

# Add it (note: you can use partial names)
claudectl add database-migration

# Deploy it
claudectl deploy database-migration
```

### Update and Sync

Keep artifacts up to date:

```bash
# Check if updates are available
claudectl sync --check-only

# Apply updates to all artifacts with newer versions
claudectl sync

# Update a specific artifact
claudectl update pdf
```

### Scripting with JSON Output

Use JSON output for automation and CI/CD:

```bash
# Get artifact list as JSON
claudectl list --format json | jq '.artifacts[].name'

# Check if specific artifact is deployed
claudectl status --format json | jq '.deployed | map(.name) | contains(["pdf"])'

# Deploy all artifacts from a bundle
claudectl import my-setup.tar.gz --format json | jq '.artifacts_added'
```

## Key Differences from skillmeat

| Feature | skillmeat | claudectl |
|---------|-----------|-----------|
| **Output** | Always table | Auto: table (TTY), JSON (pipe) |
| **Type** | Required | Auto-detected from name |
| **Project** | Required | Defaults to current dir (`.`) |
| **Collection** | Required | Uses active collection |
| **Confirmation** | Always prompt | Auto for scripts via `--force` |
| **Characters** | `skillmeat add skill pdf --project .` (60 chars) | `claudectl add pdf` (17 chars) |

## Environment Variables

Control claudectl behavior with environment variables:

```bash
# Force JSON output (even in terminal)
export CLAUDECTL_JSON=1
claudectl list

# Switch active collection for a single command
export CLAUDECTL_COLLECTION=work
claudectl list

# Reset defaults
unset CLAUDECTL_JSON
```

## Useful Flags

Most commands support these flags:

```bash
# Output format
--format table    # Human-readable (default in TTY)
--format json     # Machine-readable (default in pipes)

# Force operation (skip confirmations)
--force           # Skip confirmation prompts

# Specify location
--project /path   # Target project directory
--collection name # Target collection (default: active)

# Type and limits
--type skill      # Filter by artifact type
--limit 10        # Limit results in search/list
```

## Troubleshooting

### "claudectl: command not found"

The wrapper isn't in your PATH:

```bash
# Check if ~/.local/bin is in PATH
echo $PATH | grep local/bin

# If not, add it to your shell rc file
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or use full path
~/.local/bin/claudectl list
```

### Tab completion not working

Shell completion may need configuration:

```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
source ~/.config/fish/conf.d/claudectl.fish
```

### Artifact not found

Fuzzy matching didn't find your artifact:

```bash
# Try searching first
claudectl search artifact-name

# Use full artifact path
claudectl add anthropics/skills/exact-name

# Check collection
claudectl list
```

### Permission denied when deploying

You don't have write access to the target project:

```bash
# Check directory permissions
ls -la .claude/

# Create directory if it doesn't exist
mkdir -p .claude

# Try deployment again
claudectl deploy artifact-name
```

## Next Steps

### Learn More

- See all commands: `claudectl --help`
- See command details: `claudectl <command> --help`
- Full guide: See `docs/claudectl-guide.md` for all 14 commands
- Examples: See `docs/claudectl-examples.sh` for scripting patterns

### Configure Defaults

```bash
# View current configuration
claudectl config

# Set your default collection
claudectl config default-collection work

# Set score weights (for confidence scoring)
claudectl config score-weights trust=0.3 match=0.7
```

### Create Bundles

Package your setup for sharing:

```bash
# Create a bundle from current project deployments
claudectl bundle my-setup

# Import bundle elsewhere
claudectl import my-setup.tar.gz
```

## Uninstalling

Remove claudectl when no longer needed:

```bash
# Remove wrapper and completion files
skillmeat alias uninstall

# Or manually
rm ~/.local/bin/claudectl
rm ~/.bashrc_claudectl_completion  # (or zsh/fish equivalents)
```

## Getting Help

- **Built-in help**: `claudectl --help`
- **Command-specific help**: `claudectl <command> --help`
- **Full documentation**: See project docs directory
- **Issues**: Report via project issue tracker

---

**Quick Reference Card:**

```bash
claudectl search <query>      # Find artifacts
claudectl add <name>          # Add to collection
claudectl deploy <name>       # Deploy to project
claudectl list                # Show collection
claudectl status              # Show deployments
claudectl sync                # Update artifacts
claudectl config              # View/set configuration
claudectl --help              # Show all commands
```

**Installation Check:**

```bash
# 1. Is claudectl installed?
which claudectl

# 2. Can it run?
claudectl --help

# 3. Is collection accessible?
claudectl list
```

Start with the first 5 commands above, and you'll be productive in minutes!
