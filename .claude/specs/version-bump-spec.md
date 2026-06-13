# Version Bump Spec

Scope: All version string references across the SkillMeat monorepo.

## When to Bump

Bump the version when:
- Merging a feature branch that represents a release milestone
- Preparing a tagged release (pre-push)
- After retroactive tagging if the code doesn't yet reflect the tag

Do NOT bump mid-feature-branch. Bump on main after merge, or as a dedicated version commit.

## Single Source of Truth

```
skillmeat/__init__.py  →  __version__ = "X.Y.Z"
```

All other locations either import from this or must be manually synchronized.

## Auto-Derived (No Manual Update Needed)

These files import `__version__` at runtime and require zero changes:

| File | How It Gets the Version |
|------|------------------------|
| `skillmeat/api/server.py` | `from skillmeat import __version__ as skillmeat_version` |
| `skillmeat/api/openapi.py` | `from skillmeat import __version__ as skillmeat_version` |
| `skillmeat/api/routers/health.py` | `from skillmeat import __version__ as skillmeat_version` (examples field also dynamic) |
| `skillmeat/cache/__init__.py` | `from skillmeat import __version__` |
| `skillmeat/observability/metrics.py` | `from skillmeat import __version__` |
| `tests/test_smoke.py` | Imports and asserts against `skillmeat.__version__` dynamically |
| `tests/unit/test_version_capture.py` | Uses `SKILLMEAT_VERSION` imported from package in f-string fixtures |

## Manual Update Required (7 locations)

These files contain hardcoded version strings that must be updated:

### 1. Python Package Source

```
skillmeat/__init__.py          →  __version__ = "X.Y.Z"
pyproject.toml                 →  version = "X.Y.Z"
```

**Why both**: `pyproject.toml` is read by the build system before the package is importable. `__init__.py` is the runtime source. Keep them identical.

### 2. Frontend Package

```
skillmeat/web/package.json     →  "version": "X.Y.Z"
```

**Why manual**: npm ecosystem, separate build pipeline. `package-lock.json` auto-updates on next `pnpm install`.

### 3. OpenAPI Spec + Generated SDK

```
skillmeat/api/openapi.json     →  "version": "X.Y.Z" (line 6)
                                   "x-package-version": "X.Y.Z" (line 8)
                                   Plus 2 example values in HealthStatus/DetailedHealthStatus schemas
```

**How to update**: Regenerate via `python -c "from skillmeat.api.openapi import export_openapi_spec; export_openapi_spec()"` or update the 4 occurrences manually (all are the same string, use find-replace).

The SDK files auto-regenerate from openapi.json:
```
skillmeat/web/sdk/core/OpenAPI.ts       →  auto-generated
skillmeat/web/sdk/SkillMeatClient.ts    →  auto-generated
```

**Regenerate SDK**: `cd skillmeat/web && pnpm generate-sdk`

### 4. README Build Data

```
.github/readme/data/version.json       →  "current": "X.Y.Z"
.github/readme/data/features.json      →  "version": "X.Y.Z" (line 3)
.github/readme/data/screenshots.json   →  "version": "X.Y.Z" (line 3)
```

### 5. Documentation References

```
README.md                              →  <!-- VERSION: X.Y.Z -->
CLAUDE.md                              →  (vX.Y.Z) in Architecture Overview
```

### 6. Current State Document

```
docs/current-state.md                  →  frontmatter `updated`, header `Version` and `Last Updated`
```

**Why manual**: This document is a curated snapshot of working capabilities, in-progress features, known gaps, and recently shipped work. The version and date fields must be updated, and the content sections should be reviewed against the CHANGELOG entries being released. Delegate to a documentation agent or edit by hand.

### 7. Skill SPEC.md Alignment (advisory)

Skills under `.claude/skills/*/SPEC.md` may contain an `aligned_app_version` field in their
frontmatter that tracks which app version the skill was last verified against. These should be
reviewed and updated when the skill's CLI surface (commands, flags, or documented CLI behaviors)
has changed. This is **not a hard requirement** — a skill may remain aligned to an older version
if no relevant CLI changes occurred in the new release.

## CHANGELOG Roll-Forward

On every version bump, the `[Unreleased]` section of `CHANGELOG.md` MUST be renamed to
`[X.Y.Z] - YYYY-MM-DD` and a fresh empty `[Unreleased]` section MUST be inserted
immediately after the header block, above the newly-renamed version section.

**Preferred invocation**:

```bash
python .claude/skills/release/scripts/rollover-changelog.py \
  --version X.Y.Z \
  --date YYYY-MM-DD
```

The script (`rollover-changelog.py`) is authored in Phase 2 of the changelog-release-automation-v1
plan. Reference it by path when it is available; until then, perform the roll-forward manually.

**Idempotency behaviour**:
- If `[Unreleased]` has already been rolled for the target version, the script emits a warning
  and exits without modifying the file.
- If `[Unreleased]` is missing entirely, the script exits with an error.

**Rationale**: The previous spec omitted this step, causing stale CHANGELOGs where released
versions shipped without their entries being promoted out of `[Unreleased]`.

## Step-by-Step Procedure

```bash
# 1. Set the new version
NEW_VERSION="X.Y.Z"

# 2. Update Python source of truth
sed -i '' "s/__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" skillmeat/__init__.py

# 3. Update pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml

# 4. Update web package.json (first "version" line only)
cd skillmeat/web
npm version ${NEW_VERSION} --no-git-tag-version
cd ../..

# 5. Regenerate OpenAPI spec (picks up __version__ automatically)
python -c "from skillmeat.api.openapi import export_openapi_spec; export_openapi_spec()"
# If the export function isn't available, manually replace in openapi.json:
sed -i '' "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"${NEW_VERSION}\"/" skillmeat/api/openapi.json
sed -i '' "s/\"x-package-version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"x-package-version\": \"${NEW_VERSION}\"/" skillmeat/api/openapi.json

# 6. Regenerate SDK from updated openapi.json
cd skillmeat/web && pnpm generate-sdk && cd ../..

# 7. Update README build data
python -c "
import json
for f in ['.github/readme/data/version.json', '.github/readme/data/features.json', '.github/readme/data/screenshots.json']:
    with open(f) as fh: data = json.load(fh)
    if 'current' in data: data['current'] = '${NEW_VERSION}'
    if 'version' in data: data['version'] = '${NEW_VERSION}'
    with open(f, 'w') as fh: json.dump(data, fh, indent=2); fh.write('\n')
"

# 8. Update doc references
sed -i '' "s/<!-- VERSION: .* -->/<!-- VERSION: ${NEW_VERSION} -->/" README.md
sed -i '' "s/(v[0-9]*\.[0-9]*\.[0-9]*[-a-z]*)/(v${NEW_VERSION})/" CLAUDE.md

# 9. Roll forward CHANGELOG (rename [Unreleased] to [X.Y.Z] and insert fresh [Unreleased])
BUMP_DATE=$(date +%Y-%m-%d)
python .claude/skills/release/scripts/rollover-changelog.py \
  --version ${NEW_VERSION} \
  --date ${BUMP_DATE}

# 10. Refresh docs/current-state.md
# Update frontmatter (updated date), header block (version, date, branch),
# and review Working Capabilities / In Progress / Known Gaps / Recently Changed
# sections against the CHANGELOG entries being released.
# This is a manual review step — use a documentation agent or edit by hand.

# 12. Check skill alignment (advisory — does not block release)
echo "Skills with stale aligned_app_version:"
grep -rl "aligned_app_version:" .claude/skills/*/SPEC.md 2>/dev/null | while read f; do
  ver=$(grep "aligned_app_version:" "$f" | sed 's/.*: *//' | tr -d '"')
  if [ "$ver" != "${NEW_VERSION}" ]; then
    echo "  $f → aligned at $ver (current: ${NEW_VERSION})"
  fi
done
# Advisory: stale skills do NOT block the release. Update skills in a follow-up commit
# only when their CLI surface (commands, flags, or documented behaviors) has actually changed.
# A version bump alone does not require a skill update.

# 13. Verify no stale references (should return only historical docs, changelogs, security reviews)
grep -rn "0\.\(OLD\)\.0" --include="*.py" --include="*.json" --include="*.ts" --include="*.tsx" --include="*.toml" .
```

## Files That Should NOT Be Updated

These contain historical version references that are correct as-is:

| Location | Reason |
|----------|--------|
| `CHANGELOG.md` | Historical version entries only; the `[Unreleased]` section IS rolled forward to the new version per §CHANGELOG Roll-Forward |
| `docs/user/release-notes/` | Historical release notes |
| `docs/user/beta/` | Historical beta program docs |
| `docs/ops/security/` | Security reviews scoped to specific versions |
| `skillmeat/api/openapi-pre-refactor.json` | Historical snapshot |
| `tests/test_sync_rollback.py` | Fixture data representing old lockfile snapshots |
| `tests/test_sync_diff_service.py` | Fixture data representing artifact versions (not app version) |
| `tests/test_context_booster.py` | Generic package version in fixture (not SkillMeat) |
| `package-lock.json` / `web/package-lock.json` | Auto-generated |
| `plugins/` | Separate packages with own versioning |
| `.claude/plans/` | Historical planning documents |

## Validation Checklist

After bumping, verify:

- [ ] `python -c "import skillmeat; print(skillmeat.__version__)"` prints new version
- [ ] `grep '"version"' pyproject.toml` matches
- [ ] `grep '"version"' skillmeat/web/package.json` matches
- [ ] `jq '.info.version' skillmeat/api/openapi.json` matches
- [ ] `grep 'VERSION:' README.md` matches
- [ ] `pytest tests/test_smoke.py -v` passes
- [ ] `pytest tests/unit/test_version_capture.py -v` passes
- [ ] CHANGELOG.md: `[Unreleased]` section rolled forward to `[X.Y.Z] - YYYY-MM-DD`; new empty `[Unreleased]` inserted above it
- [ ] `docs/current-state.md` frontmatter `updated` and header `Version` reflect the new version

## Git Tagging (Post-Bump)

```bash
git tag -a v${NEW_VERSION} -m "v${NEW_VERSION}: <brief description>"
git push origin v${NEW_VERSION}
gh release create v${NEW_VERSION} --title "v${NEW_VERSION}: <title>" --notes "<notes>"
```
