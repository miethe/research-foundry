# Changelog Spec

Scope: Rules for maintaining `CHANGELOG.md` at the repository root. This spec governs how commits are categorized into changelog sections, which commits can be skipped, how entries are formatted, and how automation scripts (`rollover-changelog.py`, `audit-coverage.py`) interact with these rules.

## Keep a Changelog Reference

Format: [Keep a Changelog v1.1.0](https://keepachangelog.com/en/1.1.0/)

SkillMeat uses v1.1.0 with the following ordered sections under each release heading:

| Section | Purpose |
|---------|---------|
| `Added` | New features or capabilities |
| `Changed` | Changes to existing functionality |
| `Deprecated` | Soon-to-be-removed features |
| `Removed` | Features removed in this release |
| `Fixed` | Bug fixes |
| `Security` | Security patches and vulnerability fixes |

Sections are omitted entirely when empty. The `[Unreleased]` heading sits at the top and accumulates changes until a version is cut.

## Categorization Rules

Map Conventional Commit prefixes to changelog sections:

| Prefix | Section | Notes |
|--------|---------|-------|
| `feat` | Added | Use Changed instead when the commit replaces or alters existing behavior without adding net-new capability |
| `feat!` | Added + Removed/Deprecated | Breaking change — add to Added and call out what was removed or deprecated in the appropriate section |
| `fix` | Fixed | |
| `perf` | Changed | Performance improvements are user-visible behavior changes |
| `security` | Security | Also applies to dependency bumps that address a CVE or advisory |
| `revert` | Changed | Note what was reverted and the original commit or PR reference |
| `deprecate` | Deprecated | |
| `remove` | Removed | |
| `refactor` | skip | Internal restructuring, no user-visible impact |
| `test` | skip | Test additions and modifications |
| `docs` | skip | Documentation changes (unless a user-facing guide is added for the first time — treat as Added) |
| `chore` | skip | |
| `ci` | skip | |
| `build` | skip | Unless a build change affects the published artifact (e.g., broken npm exports) — treat as Fixed |
| `style` | skip | Code formatting, whitespace |
| `plan` | skip | Planning/spec artifacts under `.claude/plans/` or `docs/project_plans/` — internal to development workflow |

**Breaking changes** (`!` suffix on any prefix): always warrant an entry regardless of prefix. Surface in the most relevant section with a note indicating breaking behavior.

## Skip Patterns

The following commit characteristics mean no changelog entry is required. `audit-coverage.py` uses this list when evaluating coverage gaps.

- Prefixes: `refactor`, `test`, `docs`, `chore`, `ci`, `build`, `style`, `plan`
- Merge commits: lines matching `^Merge (pull request|branch)`
- Version bump commits: lines matching `^chore\(release\):` or `^bump version`
- Dependency bumps without a security advisory (e.g., Dependabot routine updates)
- Internal tooling changes that do not affect CLI behavior, API contracts, or the web UI
- Progress/worknotes file updates (`.claude/progress/`, `.claude/worknotes/`)
- README-only changes where no feature was added or changed

**Exception**: A `docs` commit that introduces a new user-facing guide for a previously undocumented feature should be treated as `Added`.

## Entry Conventions

- Entries are bullet points (`-`) under the appropriate section heading.
- Begin with a **bold short title** (noun phrase, title case) followed by an em-dash (`—`) and one sentence in past or present-perfect tense describing the change from the user's perspective.
- Reference the PR number at the end of the line where applicable: `(#123)`.
- Group tightly related sub-points under the parent entry using indented sub-bullets.
- Do not include implementation details (file names, function names) unless they are part of the public surface (CLI flags, API endpoints, config keys).
- Tense: match the existing CHANGELOG.md style — past tense for fixes (`Fixed X that caused Y`), present-perfect for features (`Added X that enables Y`), nominal phrases for removals (`Removed deprecated X`).

## Examples

### Added

```markdown
- **Composite artifact import** — Marketplace import now handles composite (plugin) artifact types, automatically importing child artifacts and registering them in the DB cache (#201).
- **`--from-repo` scaffold flag** — `skillmeat scaffold` accepts a GitHub repo URL, clones it to a temp directory for analysis, and scaffolds artifacts based on the remote project context (#188).
- **LLM project analyzer** — New `--use-llm-analyzer` flag for `skillmeat scaffold` enables AI-powered project analysis as an opt-in alternative to the default heuristic analyzer.
```

### Changed

```markdown
- **Artifact browser consolidated to `/artifacts`** — Primary artifact browsing now at `/artifacts` supporting all-artifacts, by-tier, by-type, collection-scoped, and group-scoped views; legacy `/manage` and `/collection` routes issue 301 redirects with parameter mapping (#190).
- **`TokenDep` replaced by `AuthContextDep`** — All enterprise router files now use `AuthContextDep` dependency injection; `TokenDep` bearer token extractor removed (#186).
- **Reverted: eager aggregate loading** — Reverts commit `abc1234`; aggregate queries were triggering N+1 on large collections under high concurrency (PR #195).
```

### Fixed

```markdown
- **Enterprise deploy path resolution** — `POST /deploy` now resolves `project_path` to the enterprise project UUID instead of emitting a base64-encoded path, unblocking enterprise-edition deploys (#191).
- **Synthetic Tier-0 artifact id guards** — Files and topology routes now reject synthetic Tier-0 artifact ids with a clean 4xx instead of surfacing ORM errors (#191).
```

### Security

```markdown
- **Enterprise RLS enforcement** — Row-Level Security policies enforced on all 57 tenant-scoped enterprise tables; `app.current_tenant_id` GUC wired application-wide via `TenantContextDep` (#186).
- **BundleSigner key storage** — Key pairs are now stored via `EncryptedFileKeyStorage`; plain-text key files from previous releases are rejected on load (#197).
```

## Pre-commit Hook (optional)

A lightweight `commit-msg` hook warns (never blocks) when a user-facing commit is made without a corresponding `[Unreleased]` CHANGELOG entry.

### Files

| File | Purpose |
|------|---------|
| `.claude/hooks/check-changelog-entry.sh` | Shell wrapper — the file you symlink as `.git/hooks/commit-msg` |
| `.claude/hooks/check-changelog-entry.py` | Python helper with all detection logic (testable in isolation) |

### Installation (manual, per-checkout)

```bash
ln -s ../../.claude/hooks/check-changelog-entry.sh .git/hooks/commit-msg
```

Run from the repository root. The symlink uses a relative path so it survives directory renames. The hook resolves the repo root via `git rev-parse --show-toplevel` at runtime, so it works correctly when `git commit` is invoked from any subdirectory.

### Behaviour

1. Reads the commit subject from the commit message file (`$1` per git hook contract).
2. If the subject matches a **skip pattern** (see §Skip Patterns above) → exits 0 silently.
3. Otherwise checks `git diff --cached -- CHANGELOG.md` for an added line containing `[Unreleased]`.
4. If found → exits 0 silently (entry present).
5. If not found → prints a warning to stderr with instructions, then exits 0 (never blocks).

### Opt-out

```bash
SKILLMEAT_SKIP_CHANGELOG_CHECK=1 git commit ...
```

### Skip-pattern authority

The hook's skip-prefix list is maintained in `.claude/hooks/check-changelog-entry.py` (`SKIP_PREFIXES` set) and must stay in sync with the §Skip Patterns table above and with `SKIP_PREFIXES` in `audit-coverage.py`. The spec table is the source of truth — update the script sets when the spec changes.

---

## Audit and Rollover Integration

### rollover-changelog.py

Located at `.claude/skills/release/scripts/rollover-changelog.py`. Invoked as part of the version bump procedure described in `version-bump-spec.md`. This script:

1. Renames the `[Unreleased]` section heading to the new version with today's date.
2. Inserts a fresh empty `[Unreleased]` heading at the top.
3. Writes a comparison link footer entry for the new version.

The script does not add or remove entries — categorization is the responsibility of the author or the changelog-sync automation.

### audit-coverage.py

Located at `.claude/skills/changelog-sync/scripts/audit-coverage.py`. This script consumes the **Skip Patterns** section above (encoded as configuration) to identify commits since the last tagged release that have no corresponding changelog entry. It outputs a list of uncovered commits grouped by suggested section so an agent or author can draft the missing entries.

Run it before cutting a release to catch gaps:

```bash
python .claude/skills/changelog-sync/scripts/audit-coverage.py \
  --since v0.31.0 --changelog CHANGELOG.md
```
