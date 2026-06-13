# README Build System

Modular README assembly using Handlebars templates.

## When to Update

Update README when changing:
- Feature descriptions or CLI commands
- Screenshots (add/remove/update)
- Version numbers
- Documentation links
- Project description or value proposition

## File Locations

| Type | Location | Purpose |
|------|----------|---------|
| Data | `.github/readme/data/*.json` | Features, screenshots, version |
| Partials | `.github/readme/partials/*.md` | Content sections (hero, quickstart, etc.) |
| Templates | `.github/readme/templates/*.hbs` | Structural templates |
| Scripts | `.github/readme/scripts/*.js` | Build and validation |

## Quick Reference

```bash
# Rebuild README
cd .github/readme && node scripts/build-readme.js

# Preview without writing
node scripts/build-readme.js --dry-run

# Validate links
node scripts/validate-links.js

# Check screenshots exist
node scripts/check-screenshots.js
```

## Update Workflows

### Add/Edit Feature
1. Edit `.github/readme/data/features.json`
2. Run build script

### Update Screenshots
1. Capture new screenshot to `docs/screenshots/`
2. Update `.github/readme/data/screenshots.json`
3. Run build script

### Edit Section Content
1. Edit relevant partial in `.github/readme/partials/`
2. Run build script

### Change Structure
1. Edit `.github/readme/templates/README.hbs`
2. Run build script

## Partials (Content Sections)

| Partial | Content |
|---------|---------|
| `hero.md` | Title, badges, tagline |
| `value-prop.md` | Why/Who/Capabilities |
| `screenshots.md` | Screenshot table (uses template) |
| `quickstart.md` | Installation and basic workflow |
| `features.md` | Feature grid (uses template) |
| `cli-reference.md` | CLI commands (uses template) |
| `documentation.md` | Doc links |
| `contributing.md` | Contribution guide |
| `footer.md` | License, credits |

## Data Files

### features.json
Categories with features, CLI commands, stats.

### screenshots.json
Screenshot metadata: id, file path, alt text, status.

### version.json
Current version, release date, changelog.

## Validation

Always run after rebuild:
```bash
node scripts/validate-links.js
```

Fix broken links before committing.
