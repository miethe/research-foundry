---
name: council-run
description: >
  Scaffold an ARC run, choose or recommend a council, and author or edit council
  definitions and reviewer roles. Triggers on starting/scaffolding a run, picking
  the right council for an objective, creating/editing council YAML or reviewer-role
  YAML, rendering agent stubs, using the optional agentic compose surface, and
  setting up project-specific councils with arc project init, arc councils resolve,
  --project/--council-type flags, or SAM modes — via the arc CLI, the Web portal,
  or the HTTP API. Use council-review (not this skill) to actually run the review.
allowed-tools: Read, Grep, Glob, Bash
updated: 2026-06-01
---

# Council Run Skill

## Research Foundry binding (read first)

**`council-run` drives the `arc` CLI and HTTP API server, which Research Foundry does NOT ship.**

- **For offline RF use:** drive the council through the `rf council` command and the
  `.Codex/workflows/research-foundry-council.js` Workflow instead of any `arc` commands.
- **Live ARC integration:** Research Foundry now integrates bidirectionally with ARC when reachable:
  - `rf council --via arc` runs a live ARC review when the ARC server is online (configured via
    `integrations.arc.base_url` in `foundry.yaml` or `ARC_BASE_URL` env var), with automatic
    offline fallback to the local `research-foundry-council.js` workflow.
  - `rf writeback <run_id> --targets arc` writes a review request to ARC and folds the verdict back
    into RF's gate (approve → exit 0; concern/block → exit 7).
  - `rf swarm run --adapters arc_council` lets ARC reviewers critique discovery/synthesis mid-run,
    degrading to the deterministic stub when ARC is offline.
  - All paths degrade safely: if ARC is unreachable, RF falls back to the offline council.
- **`arc` commands below apply only** when an `agentic-research` arc server is actually running
  (`GET /api/authoring/status` returns `available: true`). If you are not certain a server is
  running, assume it is not and use the RF-native path.
- Treat the **run-skeleton layout**, **role-authoring conventions**, and
  **approve / concern / block vote model** documented here as the reference model that the
  RF council Workflow implements natively. The patterns are identical; only the execution
  surface differs (`rf council` vs `arc run`).

**Related skills:** [`research-foundry`](./../research-foundry/SKILL.md) · [`council-review`](./../council-review/SKILL.md)

---

Use this skill to **set up** ARC work: scaffold a run skeleton, choose or
recommend a council, and author/edit council definitions and reviewer roles. This
skill drives the portal/CLI/API. It does **not** run reviewers — that is the
`council-review` skill.

## When to use this skill vs `council-review`

- **`council-run` (this skill):** scaffold a run (`arc run`), choose/recommend a
  council, author or edit council definitions, author or edit reviewer roles,
  render agent stubs, initialize project bindings, resolve project-specific
  councils, and drive the portal/CLI/API for any of that.
- **`council-review`:** actually run the review — build the evidence pack, run
  independent reviewer passes, adjudicate, and write the structured artifacts
  into a scaffolded run.

The boundary: creating a run produces an **empty 11-artifact skeleton** under
`runs/<date>-<slug>/`. There is **no orchestration** in scaffolding. The
`council-review` skill populates the skeleton; `uv run arc validate` is the
close gate.

## Workflow

1. Confirm the intent: start a run, pick a council, author/edit a council,
   author/edit a reviewer role, or set up a project-specific council.
2. To start a run, gather council + target + objective. If the council is
   unknown, recommend one (`arc councils recommend --objective "<text>"`) or
   scaffold with `arc run --council auto`. Read `references/run-spec.md` for the
   RunSpec contract and every way to create a run.
3. Scaffold the run (`arc run …`, optionally `--dry-run` first), then hand off
   the printed `council-review` prompt and `arc validate` next steps.
4. To author/edit a **council**, read `references/council-authoring.md` and walk
   the `schemas/council-definition.schema.json` fields; validate before saving
   (`arc councils lint <name>` / `uv run arc validate .`).
5. To author/edit a **reviewer role**, read `references/role-authoring.md` and
   walk the `schemas/reviewer-role.schema.json` fields; validate before saving
   (`arc roles lint <name|path>`). To generate the `.Codex/agents/<name>.md`
   companion, run `arc roles render <name>` (or use "Render agent" in the portal).
6. To use **agentic composition**, confirm `GET /api/authoring/status` is
   `available: true`, then call `POST /api/authoring/compose` with a
   natural-language prompt. The endpoint returns a DRAFT — never a committed
   write. Present the draft to the human for review; they save through the normal
   form/CLI path.
7. To set up **project-specific councils**, see the section below. Use
   `arc project init`, `arc councils resolve`, and the `--project`/`--council-type`
   flags on `arc run`.
8. For the CLI / Web / API / skill surfaces and curl examples, read
   `references/surfaces.md`.

## Ground Rules

- Scaffolding never runs reviewers. Do not fabricate findings or claim a run is
  reviewed when it is only scaffolded.
- The "auto"/recommend path is a **transparent heuristic**, not an LLM. Always
  present it as a labeled suggestion with a rationale, and note that the real
  agent-driven choice happens when `council-review` runs.
- Validate before persisting any council or role write. Schema-invalid definitions
  are blocked; reference issues (a reviewer whose `.Codex/agents/<name>.md` is
  not rendered yet, a missing output schema file) are warnings.
- Reviewer roles in `reviewers`/`adjudicator` must exist under `reviewer_roles/`
  and should have a rendered `.Codex/agents/<name>.md` before the council runs.
- **Agentic composition never writes.** `POST /api/authoring/compose` returns a
  draft + rationale + validation report. The human must review the draft and save
  through the normal validated registry path. Never treat a compose response as a
  committed artifact.
- Prefer read-only tools. The filesystem under `runs/`, `councils/`, and
  `reviewer_roles/` is the system of record; the CLI and API share one
  implementation (`arc_cli/core.py`).
- After scaffolding a run, point the user at the `council-review` skill to
  populate it.
- **Policy floors cannot be weakened.** Project and run overlays may tighten
  data boundaries, write policy, and denied tools. They may never loosen them.
  The resolver enforces this as a hard error (non-zero exit / HTTP 422).

## Project-Specific Councils

When a project needs councils tuned to its architecture vocabulary, context
sources, reviewer calibration, and policy posture, use the project-specific
council workflow. This produces a deterministic `resolved_council.lock.yaml`
that captures the full artifact chain and is validated by `arc validate`.

### Resolution Layers

The resolver merges seven precedence layers to produce a single effective council:

| Layer | Name | Example |
|-------|------|---------|
| 0 | Schema defaults | default run mode, output schemas |
| 1 | Global council template | `architecture-review-council` |
| 2 | Domain / offer pack | `openshift-modernization` |
| 3 | Project council profile | `project: arc` (from `.arc/project.yaml`) |
| 4 | Reviewer overlays | `arc.security-governance-reviewer.overlay` |
| 5 | Environment override | `regulated-client`, `internal-lab` |
| 6 | Run override | target-specific focus questions, optional reviewers |
| 7 | Policy floor | enterprise/project minimum control policy (cannot be weakened) |

### Initialize a Project Binding

```bash
arc project init \
  --project-id arc \
  --sam-url https://skillmeat.local \
  --fallback local
```

This writes `.arc/project.yaml` (the `ProjectCouncilProfile`) for the current
repo and configures the SAM URL and fallback mode. When SAM is unavailable or
intentionally omitted, omit `--sam-url` and the project runs in `local_only` mode.

```bash
arc project show --project-id arc   # inspect the resolved project profile
```

### Resolve a Council Without Running It

`arc councils resolve` materializes the lock file from the project profile and
all applicable overlays, without creating a run or executing any reviewers:

```bash
arc councils resolve \
  --project arc \
  --type architecture-review \
  --target web/src \
  --objective "Review ARC web console architecture." \
  --output runs/2026-06-01-arc-web-arch/resolved_council.lock.yaml

# Dry-run: resolve and print the plan as JSON without writing anything
arc councils resolve \
  --project arc \
  --type architecture-review \
  --target web/src \
  --dry-run
```

The resolved lock is hashable and replay-grade. `arc validate` verifies the lock
hash, source chain, and effective schema validity:

```bash
uv run arc validate runs/2026-06-01-arc-web-arch
```

### Start a Run with Project Context

Pass `--project` and `--council-type` to `arc run` to invoke the resolution
layer and materialize the lock file into the run directory:

```bash
arc run \
  --project arc \
  --council-type pr-quality \
  --target pull-request:123 \
  --objective "Review agent-generated changes before merge."
```

These flags are additive to the standard `arc run` flags (`--council`,
`--optional-reviewer`, `--focus-question`, `--param`, `--dry-run`). When
`--project` is given, the resolver runs first and the effective council definition
is written to `runs/<date>-<slug>/resolved_council.lock.yaml` before the run
skeleton is created.

### SAM Modes

Every run with project context records `skillmeat_mode` in
`provenance.skillbom.yaml`. Three modes are possible:

| Mode | When | Behavior |
|------|------|----------|
| `sam_native` | SAM reachable and trusted | Pull + verify artifacts from SkillMeat; publish certification on run completion |
| `cache_verified` | SAM unavailable; local cache from a prior verified pull exists | Resolve from the last verified cache; publish-back queued or skipped |
| `local_only` | No SAM URL configured, or SAM unreachable with no valid cache | Resolve from local filesystem only; no remote operations |

SAM is always optional. `local_only` and `cache_verified` modes require no SAM
code paths and run fully offline.

```bash
# Pull approved project artifacts from SAM before running
arc sam pull --project arc --include councils,roles,context-packs,overlays

# Publish a run certification back to SAM after arc validate passes
arc sam publish certification --run runs/2026-06-01-arc-web-arch
```

### API Equivalents

| Operation | Endpoint |
|-----------|----------|
| List projects | `GET /api/projects` |
| Show project profile | `GET /api/projects/{id}` |
| Sync SAM artifacts for a project | `POST /api/projects/{id}/sync` |
| Resolve a council (no run created) | `POST /api/councils/resolve` |
| Fetch the lock for an existing run | `GET /api/runs/{id}/resolved-council` |

```bash
# Resolve via API (dry-run equivalent)
curl -s -X POST http://127.0.0.1:8910/api/councils/resolve \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"arc","council_type":"architecture-review","target":"web/src","dry_run":true}'
```

### Key Artifacts in the Run Directory

When `--project` is used, two extra files appear in the run directory:

- `resolved_council.lock.yaml` — deterministic, hashable, replay-grade effective
  council definition with full source chain, overlays applied, reviewer effective
  hashes, and policy constraints.
- `provenance.skillbom.yaml` — extended with a `council_resolution` block
  containing the resolved hash, template chain, overlays, context packs, reviewer
  effective hashes, evidence hash, and the `skillmeat_mode` field.

`arc validate` checks the lock hash and source chain integrity. A tampered or
missing lock causes exit 2 with a `lock_hash_mismatch` error.

### Policy Floor Enforcement

The resolver enforces that overlays at layers 3–6 cannot weaken:
- `data_boundaries` (allowed/excluded data classes, network policy)
- `write_policy`
- `denied_tools`

Any attempt to loosen these fields raises a hard error before the lock file is
written. Tightening (adding restrictions) is always permitted.
