# Authoring + Editing Council Definitions

A council definition names the review type, reviewer roster, adjudicator,
required artifacts, gates, and data boundaries. It is YAML validated against
`schemas/council-definition.schema.json`. Existing councils live in `councils/`.

## Schema walkthrough

Top-level: `apiVersion: arc/v1alpha1`, `kind: CouncilDefinition`, `metadata`,
`spec` (`additionalProperties: false` at every level).

`metadata` (all required): `name`, `version`, `owner`.

`spec` required keys:

- `purpose` — one-line statement of what the council reviews.
- `councilType` — category string, e.g. `architecture-review`, `pr-quality`,
  `general-review`.
- `defaultRunMode` — one of: `independent-review-then-adjudicate`,
  `sequential-review-then-adjudicate`, `external-review-then-adjudicate`,
  `human-led-review`, `deterministic-gates-only`.
- `requiredInputs` — non-empty array. Each item is a string OR an object
  `{name, required, description?, acceptableSources?[]}`.
- `reviewers` — non-empty array of reviewer role names (run the independent
  passes).
- `adjudicator` — single role name that merges findings and records dissent.
- `outputSchemas` — non-empty map of output name → `schemas/*.json` path.
- `requiredArtifacts` — non-empty array of filenames a completed run must contain.
- `gates` — non-empty array. Each item is a string OR object
  `{name, required?, description?}`.
- `dataBoundaries` — object with all of: `allowedDataClasses[]`,
  `excludedDataClasses[]`, `externalProviderPolicy`, `networkPolicy`,
  `writePolicy`, `retentionPolicy`.

`spec` optional keys:

- `optionalReviewers` — reviewer roles added only when scope warrants. The run
  wizard / `arc run --optional-reviewer` lets a run convene these per run.
- `externalReviewers` — array of objects, each requiring `name`, `provider`,
  `mode`, `invocation`, `normalizeWith` (non-Claude reviewers).
- `focusChecks` — array of strings: specific things this council should look for.
- `runConfig` — optional per-council run-time configuration the run wizard
  surfaces (`additionalProperties: false`). All sub-fields are optional:
  - `objectiveTemplate` — prefills the wizard's Objective field.
  - `targetHint` — placeholder/help describing what `target` should point at.
  - `defaultConstraints[]` — constraints prefilled for runs of this council.
  - `focusQuestions[]` — specific questions reviewers should answer. Each item is
    `{id, question, description?, default?}`; `default: true` pre-selects it in
    the wizard. Selected questions flow into the run manifest + evidence pack.
  - `parameters[]` — tunable run knobs. Each item is
    `{id, label, type, description?, default?, options?[], min?, max?}` where
    `type` is one of `boolean | number | string | select` (`options` is required
    for `select`). The wizard renders the matching control; resolved values land
    in the manifest.

  ```yaml
  spec:
    # …required keys…
    optionalReviewers: [correctness-reviewer]
    runConfig:
      objectiveTemplate: Evaluate <system> for <decision> before <milestone>.
      targetHint: Path to an ADR, design doc, or service.
      defaultConstraints: [read_only, evidence_required]
      focusQuestions:
        - id: blast-radius
          question: What is the blast radius if the primary datastore fails?
          description: Probe failure isolation across service boundaries.
          default: true
      parameters:
        - id: depth
          label: Review depth
          type: select
          options: [quick, standard, deep]
          default: standard
  ```

## Reviewer roles and rendered agents

Every name in `reviewers` and the `adjudicator`:

1. must exist as a role under `reviewer_roles/<name>.yaml`, and
2. should have a rendered Claude agent at `.claude/agents/<name>.md`.

Schema validation passes without the agent, but it is flagged as a reference
**warning**, not a schema error. You may save a council that references a
not-yet-rendered reviewer; render the agent before running the council so the
`council-review` skill can delegate to it. Every `outputSchemas` path must point
to a real `schemas/*.json` file (also a reference warning if missing).

## View / edit / validate via CLI

```bash
arc councils list                       # catalog (--json for machine output)
arc councils show <name>                # one definition (--json)
arc councils lint <name|path>           # validate a single council def (--json)
arc councils recommend --objective "…"  # ranked suggestions (--target, --json)
```

Edit a council by editing its YAML under `councils/`, then validate:

```bash
arc councils lint <name>     # single-definition check
uv run arc validate .        # whole-repo scan (councils + schemas + runs)
```

## Edit via the Web portal

- `/councils` — registry of rosters/gates.
- `/councils/[name]` — viewer + editor (form or raw YAML); validate before save.
- `/councils/new` — create a new definition.

The editor calls `POST /api/councils/validate` for structured errors, then
`PUT /api/councils/{name}` to commit.

## Edit via the API

`GET /api/councils/{name}` → `{name, file, exists, raw, parsed}`. 404
`{detail:"Council not found: <name>"}` if missing.

`POST /api/councils/validate` (body `{definition?}` or `{definition_text?}` raw
YAML) → `{ok, errors[], warnings[], parsed|null}`.

`POST /api/councils/serialize` (body `{definition: {...}}`) → `{filename, content}`
where `content` is the canonical YAML (byte-identical to the write path) and
`filename` is the suggested `<name>.yaml`. Writes nothing to disk; backs the
portal's **Download YAML** action. Non-dict input → 400.

`PUT /api/councils/{name}` (body `{definition?}` or `{definition_text?}`, plus
`force?`) creates/updates a definition. 200 →
`{ok, file, created, validation, council}`. **Schema-invalid → 400** (blocked,
`{detail:"Council definition is invalid: <first error>"}`). Reference issues
(missing reviewer role/agent, missing schema file) **persist** and come back
under `validation.warnings` — the editor uses `validate` for structured errors,
`PUT` is the commit.

```bash
# Round-trip: read, then update from raw YAML
curl -s http://127.0.0.1:8910/api/councils/architecture-review-council | jq .parsed

curl -s -X PUT http://127.0.0.1:8910/api/councils/my-new-council \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-new-council.yaml)"

# Editor field enums (run modes, reviewer roles, adjudicators, suggestions)
curl -s http://127.0.0.1:8910/api/councils/options | jq .
```

The filename is chosen from `metadata.name` (slugified, plain stem; path
separators/traversal are rejected). Writes take an exclusive lock and use an
atomic temp-then-rename, mirroring the run write path.
