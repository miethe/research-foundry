---
name: council-run-spec
description: Skill contract for the council-run skill — capability coverage, surface matrix, boundary rules, and project-specific council workflow reference.
type: spec
skill_name: council-run
schema_version: 1
created: 2026-06-01
updated: 2026-06-01
status: current
---

# Council Run — Skill Contract

## 1. Purpose

Document the authoritative capability boundary of the `council-run` skill: what
it covers, what it delegates to `council-review`, and the full surface matrix
for CLI / Web / API. Includes the project-specific council workflow (Council
Resolution Layer, SAM modes, policy-floor enforcement) added in phase 9 of
`arc-project-councils-skillmeat-v1`.

---

## 2. Scope

### In Scope

- Scaffolding run skeletons (`arc run`, `POST /api/runs`, portal wizard)
- Council recommendation and auto-selection
- Council definition authoring and editing (YAML, portal form, API)
- Reviewer role authoring and editing (YAML, portal form, API)
- Rendering `.claude/agents/<name>.md` companion stubs
- Agentic draft composition (`POST /api/authoring/compose`) — drafts only, no writes
- Project binding initialization (`arc project init`, `.arc/project.yaml`)
- Council resolution without running (`arc councils resolve`, `POST /api/councils/resolve`)
- Project-aware run scaffolding (`--project` / `--council-type` flags on `arc run`)
- SAM artifact pull and certification publish (`arc sam pull`, `arc sam publish`)
- Policy-floor enforcement rules and error interpretation

### Out of Scope

- **Populating a run** (running reviewers, building evidence packs, adjudicating) — use `council-review`
- SAM server-side contract negotiation (see OQ-01 in `arc-project-councils-skillmeat-v1` PRD)
- P2 enterprise integrations: RHDH/Backstage, GitHub/ADO PR checks, CCDash export, MeatyWiki filing

---

## 3. Capability Coverage Matrix

| Capability | CLI | Web | API | Skill |
|---|---|---|---|---|
| Start a run (named council) | `arc run --council …` | New review wizard (`/runs/new`) | `POST /api/runs` | — (scaffold first) |
| Start a run from a RunSpec | `arc run --spec run_spec.yaml` | Paste / upload spec (`/runs/new`) | `POST /api/runs` (`spec_text`) | — |
| Preview a run (no write) | `arc run … --dry-run` | Wizard plan preview | `POST /api/runs/preview` | — |
| Recommend a council | `arc councils recommend` / `--council auto` | Wizard recommendations | `POST /api/councils/recommend` | Agent reads catalog when skill runs |
| Populate a run | — | — | — | `council-review` skill |
| List councils | `arc councils list` | Registry (`/councils`) | `GET /api/councils` | reads `councils/` |
| Show a council | `arc councils show <name>` | Viewer (`/councils/[name]`) | `GET /api/councils/{name}` | reads `councils/<name>.yaml` |
| Edit / create a council | edit YAML + `arc validate` | Editor / creator (`/councils/[name]`, `/councils/new`) | `PUT /api/councils/{name}` | edit YAML + `arc validate` |
| Validate a council def | `arc councils lint <name>` | Editor validate-before-save | `POST /api/councils/validate` | `arc councils lint` |
| Council field enums | — | wizard/editor options | `GET /api/councils/options` | — |
| List reviewer roles | `arc roles list` | Roles registry (`/roles`) | `GET /api/roles` | reads `reviewer_roles/` |
| Show a reviewer role | `arc roles show <name>` | Detail (`/roles/[name]`) | `GET /api/roles/{name}` | reads `reviewer_roles/<name>.yaml` |
| Edit / create a reviewer role | edit YAML + `arc roles lint` | Editor / creator (`/roles/[name]`, `/roles/new`) | `PUT /api/roles/{name}` | edit YAML + `arc roles lint` |
| Validate a reviewer role def | `arc roles lint <name\|path>` | Editor validate-before-save | `POST /api/roles/validate` | `arc roles lint` |
| Reviewer-role field enums | — | RoleForm options | `GET /api/roles/options` | — |
| Render agent companion stub | `arc roles render <name> [--force]` | "Render agent" on `/roles/[name]` | `POST /api/roles/{name}/render-agent` | `arc roles render <name>` |
| Browse library (rubrics/schemas/adapters) | — | `/library` | `GET /api/library` | — |
| Check agentic-compose availability | — | "Compose with AI" panel state | `GET /api/authoring/status` | — |
| Agentic NL compose (draft only) | — | "Compose with AI" panel on `/councils/new`, `/roles/new` | `POST /api/authoring/compose` | call API then present draft |
| Validate / close a run | `arc validate runs/<dir>` | Run detail schema-valid badge | `GET /api/runs/{id}/validate` | `arc validate runs/<dir>` |
| **Initialize project binding** | **`arc project init`** | **`/projects/new`** | **`POST /api/projects`** | **write `.arc/project.yaml`, then `arc project show`** |
| **Show project profile** | **`arc project show`** | **`/projects/[id]`** | **`GET /api/projects/{id}`** | **reads `.arc/project.yaml`** |
| **Sync SAM artifacts for project** | **`arc sam pull`** | **`/projects/[id]` → Sync** | **`POST /api/projects/{id}/sync`** | **`arc sam pull --project <id>`** |
| **Resolve council (no run)** | **`arc councils resolve`** | **Resolved council viewer** | **`POST /api/councils/resolve`** | **`arc councils resolve --dry-run` to inspect** |
| **Start a run with project context** | **`arc run --project / --council-type`** | **Wizard with project selector** | **`POST /api/runs` with `project_id` + `council_type`** | **provide `--project` + `--council-type` flags** |
| **Fetch resolved lock for a run** | **`arc validate` (verifies lock)** | **Resolved council detail page** | **`GET /api/runs/{id}/resolved-council`** | **reads `runs/<id>/resolved_council.lock.yaml`** |
| **Publish certification to SAM** | **`arc sam publish certification`** | **`/projects/[id]` → Publish** | **`POST /api/sam/publish`** | **`arc sam publish certification --run <dir>`** |

---

## 4. Boundary Rules

### council-run vs council-review

| Task | Skill |
|------|-------|
| Scaffold an empty run skeleton | `council-run` |
| Choose or recommend a council | `council-run` |
| Author / edit council YAML | `council-run` |
| Author / edit reviewer role YAML | `council-run` |
| Render `.claude/agents/<name>.md` | `council-run` |
| Compose NL drafts via API (no write) | `council-run` |
| Initialize project binding | `council-run` |
| Resolve project council to lock file | `council-run` |
| Pull SAM artifacts / publish certification | `council-run` |
| Build evidence pack | `council-review` |
| Run independent reviewer passes | `council-review` |
| Adjudicate findings | `council-review` |
| Write structured run artifacts | `council-review` |

### Validation Gates

- **Schema errors** are blocked: schema-invalid council/role YAML cannot be saved.
- **Reference warnings** persist: a missing rendered agent or output schema file
  is a warning, not a block. Save is allowed; run before rendering the agent
  is permitted but flagged.
- **Lock hash mismatch**: `arc validate` exits 2 and prints `lock_hash_mismatch`
  when the lock file has been tampered with or its source chain is invalid.
- **Policy floor violations**: the resolver raises a hard error (non-zero exit /
  HTTP 422) before writing any lock file when an overlay attempts to weaken
  `data_boundaries`, `write_policy`, or `denied_tools`.

---

## 5. Project-Specific Councils

### Resolution Layer Precedence

| Layer | Name | May override |
|-------|------|-------------|
| 0 | Schema defaults | nothing |
| 1 | Global council template | base purpose, reviewers, gates |
| 2 | Domain / offer pack | adds domain context |
| 3 | Project council profile (`.arc/project.yaml`) | project vocabulary, default context, routing |
| 4 | Reviewer overlays | mission, focus checks, tool policy (stricter only) |
| 5 | Environment override | data boundaries, required reviewers, approval gates |
| 6 | Run override | optional reviewers, focus questions, temporary constraints |
| 7 | Policy floor | constrains final result; **cannot be weakened by any layer** |

### SAM Modes

Recorded in `provenance.skillbom.yaml` as `skillmeat_mode`:

| Value | Trigger | Remote ops |
|-------|---------|-----------|
| `sam_native` | SAM reachable; `--sam-url` configured | Pull + verify; publish-back enabled |
| `cache_verified` | SAM unreachable; local verified cache present | Resolve from cache; no remote pull |
| `local_only` | No SAM URL; or SAM unreachable with no cache | Filesystem only; no remote ops |

### Key Run Artifacts

When `--project` is used:

- `runs/<id>/resolved_council.lock.yaml` — hashable, replay-grade effective
  council (source chain, overlays applied, reviewer effective hashes, policy
  constraints).
- `runs/<id>/provenance.skillbom.yaml` — extended with `council_resolution`
  block: resolved hash, template chain, overlays, context packs, reviewer
  effective hashes, evidence hash, `skillmeat_mode`.

### Policy Floor Fields (Hard Enforcement)

These fields can only be tightened by overlays; loosening them is a hard error:

- `spec.dataBoundaries.allowedDataClasses` / `excludedDataClasses`
- `spec.dataBoundaries.networkPolicy`
- `spec.dataBoundaries.writePolicy`
- `spec.dataBoundaries.deniedTools` (via reviewer role overlays)

---

## 6. Reference Files

| File | Purpose |
|------|---------|
| `references/run-spec.md` | RunSpec contract, all ways to create a run, `arc run` flags |
| `references/council-authoring.md` | Council YAML schema walkthrough, CLI/Web/API edit surface |
| `references/role-authoring.md` | Reviewer role YAML schema walkthrough |
| `references/surfaces.md` | Full CLI / Web / API surface matrix with curl examples |
| `schemas/council-definition.schema.json` | Council definition JSON Schema |
| `schemas/reviewer-role.schema.json` | Reviewer role JSON Schema |
| `schemas/council-run-spec.schema.json` | RunSpec JSON Schema |
| `schemas/project-council-profile.schema.json` | `ProjectCouncilProfile` JSON Schema |
| `schemas/resolved-council-lock.schema.json` | `ResolvedCouncilLock` JSON Schema |
| `schemas/skillbom-provenance.schema.json` | SkillBOM provenance schema (incl. `council_resolution` block) |
