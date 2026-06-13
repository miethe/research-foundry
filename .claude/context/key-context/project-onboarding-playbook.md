# Project Onboarding Playbook: SkillMeat Integration

Operational guide for agents bootstrapping and maintaining SkillMeat integration in non-SkillMeat projects.

**Updated**: 2026-05-23

**When to use this**: Agent is working in a project that needs to sync with a SkillMeat collection (either for sourcing artifacts or registering locally-authored artifacts).

---

## Prerequisites

Before any operation, verify:

1. **SkillMeat CLI installed**:
   ```bash
   skillmeat --version
   ```
   If missing: `pip install skillmeat` or `uv tool install skillmeat`

2. **Collection initialized** (required once per machine):
   ```bash
   skillmeat init --collection
   ```
   Creates `~/.skillmeat/collection/` as the user's artifact repository.

3. **API server running** (for web-based operations):
   ```bash
   skillmeat web dev --api-only
   ```
   Listens on `http://localhost:8080`. Needed for deployment, drift detection, memory capture.

4. **Credential handling**:
   - Enterprise: `skillmeat auth login --enterprise <url>`
   - GitHub (for private repos): Set `GITHUB_TOKEN` or `skillmeat config set github-token <token>`

5. **Important file**: `.skillmeat-deployed.toml` tracks deployed artifacts. Located at project root or `.claude/.skillmeat-deployed.toml`. **NEVER edit manually** — use CLI commands only.

---

## First-Time Bootstrap: Local Edition

Steps to register a project's existing artifacts with SkillMeat and sync them to the collection.

### Step 1: Run Scanner

```bash
skillmeat sync-pull <project-path> --auto-link --non-interactive
```

Scans `.claude/` directory structure for artifacts (skills, agents, commands, hooks, specs, contexts, progress files). Matches each against collection by SHA. Queues matches for import approval.

**Output**: List of queued artifacts (approved, rejected, or pending review).

### Step 2: Identify Non-Artifacts

Scanner may queue non-artifact files. Review:

```bash
skillmeat import list
```

Reject files that are not artifacts (e.g., `__pycache__`, `.env`, `_meta/`, temporary notes):

```bash
skillmeat import reject <filename>
```

Examples:
```bash
skillmeat import reject __pycache__
skillmeat import reject local-notes.md
skillmeat import reject config-backup.json
```

### Step 3: Approve Valid Artifacts

Approve discovered artifacts one by one:

```bash
skillmeat import approve <artifact-name>
```

Or batch-approve via script (if API available):

```bash
for artifact in $(skillmeat import list --json | jq -r '.artifacts[].name'); do
  skillmeat import approve "$artifact"
done
```

Each approval registers the artifact in the collection and adds an entry to `.skillmeat-deployed.toml`.

### Step 4: Verify Registration

Confirm all artifacts are deployed:

```bash
grep -c '\[\[deployed\]\]' .claude/.skillmeat-deployed.toml
```

Should match count of approved artifacts. Cross-check with:

```bash
skillmeat list | grep -i deployed
```

---

## First-Time Bootstrap: Enterprise Edition

For projects connected to an enterprise SkillMeat instance.

### Step 1: Authenticate

```bash
skillmeat auth login --enterprise <enterprise-url>
```

Prompts for credentials. Stores auth token in `~/.skillmeat/config.toml`.

### Step 2: Verify Auth

```bash
skillmeat auth status
```

Confirms enterprise connection is active.

### Step 3: Import Collection to Enterprise

Migrate local collection to enterprise instance:

```bash
skillmeat enterprise import --from-collection
```

Uploads all artifacts from `~/.skillmeat/collection/` to the enterprise instance. Idempotent (safe to re-run).

### Step 4: Pull Pending Deployments

If the enterprise instance has pre-staged deployments for this project:

```bash
skillmeat enterprise deploy pull
```

Downloads pending artifact changes from enterprise to local `.claude/` directory.

### Step 5: Check Deployment Status

```bash
skillmeat enterprise deploy status
```

Lists:
- Pending deployments (staged on enterprise, not yet pulled)
- Materialized deployments (pulled to local project)
- Conflicts (upstream vs. local mismatch)

### Step 6: Complete Local Bootstrap

Run **Step 2-4 from the Local Edition section** above (scanner, approve, verify).

---

## Adding New Artifacts to a Project

When creating new skills, agents, commands, hooks, specs, contexts, or progress files in a project.

### Step 1: Create in Standard Location

Place artifact under `.claude/` directory structure:

```
.claude/
  ├── skills/my-skill/          # Skills
  ├── agents/ai/my-agent.md     # Agents (can nest)
  ├── commands/dev/cmd.md       # Commands (can nest)
  ├── hooks/pre-commit/hook.md  # Hooks
  ├── specs/api-spec.md         # Specs
  └── context/...               # Context files
```

### Step 2: Add to Collection

```bash
skillmeat add <artifact-type> <path>
```

Examples:

```bash
skillmeat add skill .claude/skills/my-skill/
skillmeat add agent .claude/agents/ai/expert.md
skillmeat add command .claude/commands/dev/analyze.md
skillmeat add spec .claude/specs/api-design.md
```

This registers the artifact in `~/.skillmeat/collection/`.

### Step 3: Register in Project (if tracking enabled)

If the project already has SkillMeat tracking enabled (`.skillmeat-deployed.toml` exists):

```bash
skillmeat sync-pull . --auto-link
```

Auto-detects the newly-added artifact by SHA and adds to `.skillmeat-deployed.toml`.

---

## Deploying Collection Artifacts to Projects

When pulling artifacts from the collection into a project's `.claude/` directory.

### Step 1: Deploy Single Artifact

```bash
skillmeat deploy <artifact-name>
```

Copies artifact from collection to project's `.claude/` directory. Creates or overwrites local copy.

### Step 2: Deploy to Specific Project

```bash
skillmeat deploy <artifact-name> -p <project-path>
```

If not in the target project directory.

### Step 3: Deploy Multiple Artifacts

Use web UI (more intuitive) or loop via CLI:

```bash
for artifact in skill-1 skill-2 command-analyze; do
  skillmeat deploy "$artifact"
done
```

### Step 4: Verify Deployment

Check `.claude/.skillmeat-deployed.toml`:

```bash
grep "name = \"<artifact-name>\"" .claude/.skillmeat-deployed.toml
```

Should show the artifact's entry.

---

## Ongoing Sync Workflow

Keeping a project synchronized with collection changes (bi-directional).

### Scenario A: Detect Upstream Changes

Check if collection has newer versions than the project:

```bash
skillmeat sync-pull . --dry-run
```

Shows what would change (without applying). Lists added, updated, deleted artifacts.

### Scenario B: Pull Updates from Collection

Apply upstream changes:

```bash
skillmeat sync-pull .
```

Overwrites local copies with collection versions. Pre-flight: `--dry-run` recommended.

### Scenario C: Push Local Changes to Collection

If a locally-modified artifact should update the collection:

```bash
skillmeat add <type> <path>
```

Re-adds the artifact to the collection, updating its SHA and version info. Does NOT overwrite other projects' local copies (they must pull explicitly).

### Scenario D: Check Web UI Drift Badges

The web interface shows sync status visually:

- **Blue badge**: Upstream has a newer version (pull recommended)
- **Amber badge**: Local project differs from collection (review mismatch)
- **Red badge**: Conflict (manual resolution needed)

---

## Using the skillmeat-cli Skill

For structured, multi-step workflows, load the SkillMeat CLI skill:

```
Skill("skillmeat-cli")
```

Skill routes to workflow docs based on intent:

- **Discovery**: Finding artifacts in collection
- **Deployment**: Pushing artifacts to projects
- **Management**: Adding, updating, removing artifacts
- **Bundles**: Creating and publishing artifact bundles
- **Scaffolding**: Project generation from templates
- **Memory**: Capturing and consuming context
- **Supply Chain**: Version tracking and audit
- **Versioning**: Tag, release, promote workflows
- **Auth**: Token setup and enterprise login
- **Enterprise**: Multi-instance federation

Reference: `.claude/skills/skillmeat-cli/SPEC.md` (capability matrix and routing table).

---

## Agent Invariants

Agents working with SkillMeat must follow:

1. **Never manually edit `.skillmeat-deployed.toml`**
   - Use `skillmeat import approve`, `skillmeat deploy`, `skillmeat sync-pull` only
   - File is auto-managed by CLI; manual edits cause state corruption

2. **Always confirm before deploy/undeploy**
   - Use `--dry-run` before applying changes
   - Don't use `--force` without explicit user approval

3. **Use `--non-interactive` for batch operations**
   - Prevents hangs in automated workflows
   - Required when running in agent/CI contexts

4. **Understand source of truth by edition**
   - **Local**: `~/.skillmeat/collection/` is authoritative (filesystem-backed)
   - **Enterprise**: PostgreSQL instance is authoritative
   - Cache DB at `~/.skillmeat/cache/cache.db` is derived, NOT source of truth

5. **Refresh cache when needed**
   ```bash
   curl -X POST http://localhost:8080/api/v1/cache/refresh
   ```
   Use after manual file edits or when sync seems stale.

6. **Abort on permission prompts if not approved**
   - Some deploy operations request user confirmation
   - If agent receives confirmation prompt and no approval was given, stop and escalate

---

## Troubleshooting

### Problem: "0 matches found" on auto-link

**Cause**: Artifacts are locally authored (SHAs don't match collection). Normal behavior.

**Solution**: Use the 3-step import approval flow (import list → reject non-artifacts → approve valid ones).

### Problem: API 405 Method Not Allowed

**Cause**: Endpoint doesn't exist yet (e.g., DELETE on collection artifacts).

**Solution**: Use web UI instead, or request API route addition in issue.

### Problem: Scanner misses nested artifacts

**Cause**: Known depth-1 limitation. Scanner only finds artifacts directly under profile roots (`.claude/skills/`, `.claude/agents/`, etc.). Nested artifacts (e.g., `.claude/agents/ai/expert.md` or `.claude/commands/analyze/tool.md`) are not discovered.

**Workaround**:
- Deploy individually: `skillmeat deploy <artifact-name>`
- Use web UI (scans recursively)
- Manual `.skillmeat-deployed.toml` entry for known nested paths (then run `sync-pull`)

**Tracking**: Fix is in backlog; feedback: `docs/user/guides/scan-import-existing.md` § "Known Limitations".

### Problem: 422 Validation Error on memory create

**Cause**: CLI `skillmeat memory item create` occasionally fails with 422 (payload validation).

**Workaround**: Use API fallback:
```bash
curl -s "http://localhost:8080/api/v1/memory-items?project_id=<PROJECT_ID>" \
  -X POST -H "Content-Type: application/json" \
  -d '{
    "type": "decision",
    "content": "...",
    "confidence": 0.85,
    "status": "candidate",
    "anchors": ["path/to/file:code"]
  }'
```

### Problem: Cache stale after manual file changes

**Cause**: Web UI or API operations read cache, not filesystem (by design).

**Solution**: Refresh cache:
```bash
curl -X POST http://localhost:8080/api/v1/cache/refresh
```

Or restart API: `skillmeat web dev --api-only` (rebuilds cache on startup).

### Problem: Permission denied on `.skillmeat-deployed.toml`

**Cause**: File was created by different user or in elevated mode.

**Solution**:
```bash
chmod 644 .claude/.skillmeat-deployed.toml
chown $(whoami) .claude/.skillmeat-deployed.toml
```

---

## Diagnostics

For general environment issues, use the built-in doctor:

```bash
skillmeat web doctor
```

Checks:
- Python version and dependencies
- Collection initialization
- Database connectivity
- API server status
- GitHub token configuration
- Enterprise auth status

Output indicates what's missing or misconfigured.

---

## Related Guides

- `docs/user/guides/scan-import-existing.md` — Detailed scanner workflow
- `docs/user/guides/deploying-artifacts.md` — Deployment patterns
- `docs/user/guides/syncing-changes.md` — Bi-directional sync
- `docs/user/guides/skillmeat-cli-skill.md` — CLI skill reference
- `docs/user/guides/enterprise-features.md` — Enterprise-specific workflows
- `.claude/context/key-context/marketplace-import-flows.md` — Marketplace artifact ingestion
