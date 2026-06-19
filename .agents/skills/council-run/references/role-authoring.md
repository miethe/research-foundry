# Authoring + Editing Reviewer Roles

A reviewer role defines the mission, model policy, tool policy, and output
contract for one specialist in a council. It is YAML validated against
`schemas/reviewer-role.schema.json`. Existing roles live in `reviewer_roles/`.

## Schema walkthrough

Top-level: `apiVersion: arc/v1alpha1`, `kind: ReviewerRole` (or `AgentRole`),
`metadata`, `spec` (`additionalProperties: false` at every level).

`metadata` (all required): `name`, `version`, `owner`.

`spec` required keys:

- `mission` — one-line purpose of the reviewer (non-empty string).
- `roleType` — one of: `coordinator`, `evidence`, `specialist`, `adjudicator`.
- `modelPolicy` — object (all sub-fields required):
  - `defaultModelClass` — tier string, e.g. `strong_reasoning`, `fast`, `balanced`.
  - `preferredCapabilities` — array of capability strings (e.g. `architecture_review`,
    `systems_thinking`).
  - `allowedProviders` — array of provider strings (e.g. `claude-code`, `codex`,
    `human-reviewer`).
- `toolPolicy` — object (all sub-fields required):
  - `defaultMode` — one of: `read_only`, `read_only_with_validation_shell`,
    `approval_required`.
  - `allowedTools` — array of tool name strings (e.g. `read_file`, `grep`, `glob`).
  - `deniedTools` — array of tool name strings (e.g. `write_file`, `shell_exec`,
    `external_network`).
- `output` — object (all sub-fields required except `secondarySchemas`):
  - `primarySchema` — path to a `schemas/*.json` file for this role's main output.
  - `secondarySchemas` — optional array of additional schema paths.
  - `hypothesisLabeling` — policy string, e.g. `required_when_evidence_below_E2`.
- `dataPolicy` — object (all sub-fields required):
  - `allowedDataClasses` — array of data class strings.
  - `excludedDataClasses` — array of data class strings.

`spec` optional keys:

- `source` — object:
  - `claudeAgent` — path to the rendered `.claude/agents/<name>.md` companion
    (e.g. `.claude/agents/architecture-reviewer.md`). Can be omitted and filled
    in after rendering.
- `calibration` — object:
  - `severityRubric` — path to a `rubrics/*.yaml` file for severity scoring.
  - `confidenceRubric` — path to a `rubrics/*.yaml` file for confidence scoring.

A minimal role skeleton:

```yaml
apiVersion: arc/v1alpha1
kind: ReviewerRole
metadata:
  name: my-reviewer
  version: 0.1.0
  owner: platform-team
spec:
  mission: Review X for Y to support Z decisions.
  roleType: specialist
  modelPolicy:
    defaultModelClass: strong_reasoning
    preferredCapabilities: []
    allowedProviders:
      - claude-code
  toolPolicy:
    defaultMode: read_only
    allowedTools:
      - read_file
      - grep
    deniedTools:
      - write_file
      - shell_exec
      - external_network
  output:
    primarySchema: schemas/finding.schema.json
    hypothesisLabeling: required_when_evidence_below_E2
  dataPolicy:
    allowedDataClasses:
      - public
      - internal
    excludedDataClasses:
      - production_secrets
      - regulated_personal_data
```

## Rendered agent companion

A reviewer role can have a `.claude/agents/<name>.md` companion that the
`council-review` skill delegates to. The companion is generated from the role —
do not hand-author it unless you need custom behavior.

Generate it with:

```bash
arc roles render <name>           # writes .claude/agents/<name>.md
arc roles render <name> --force   # overwrite an existing file
```

Or via the API:

```bash
curl -s -X POST http://127.0.0.1:8910/api/roles/<name>/render-agent \
  -H 'Content-Type: application/json' \
  -d '{}'
# Add {"force": true} to overwrite a hand-authored file.
```

The render maps `toolPolicy.allowedTools` to Claude tool names, sets `model`
from `defaultModelClass`, and writes the mission + output-contract boilerplate
as the body. The write is atomic; it never clobbers a hand-authored file unless
`force` is true.

When `source.claudeAgent` is absent in the YAML, the validator flags it as a
reference **warning** (not a schema error). You may save a role without the agent
and render it later; render before running any council that references this role.

## Referencing a role from a council

In a council definition, add the role's `metadata.name` value to `spec.reviewers`
or `spec.adjudicator`. The council validator checks:

1. The role file `reviewer_roles/<name>.yaml` exists — schema **warning** if
   missing.
2. The rendered agent `.claude/agents/<name>.md` exists — reference **warning**
   if missing.

Schema errors in the role itself are independent of the council; fix them with
`arc roles lint <name>` before the council lint runs cleanly.

## Validate and lint via CLI

```bash
arc roles list                  # catalog (--json for machine output)
arc roles show <name>           # one definition (--json)
arc roles lint <name|path>      # validate a single role def (--json)
arc roles render <name>         # render .claude/agents/<name>.md
arc roles render <name> --force # overwrite existing agent file
```

After editing a role under `reviewer_roles/`, validate the whole repo to catch
cross-references:

```bash
uv run arc validate .
```

## Edit via the Web portal

- `/roles` — categorized registry grouped by roleType, searchable.
- `/roles/[name]` — viewer + editor (form or raw YAML); "Render agent" button;
  "Used by N councils" backlink. Validate before save.
- `/roles/new` — create a new role definition.

The editor calls `POST /api/roles/validate` for structured errors, then
`PUT /api/roles/{name}` to commit.

## Edit via the API

`GET /api/roles/{name}` → `{name, file, exists, raw, parsed}`. 404
`{detail:"Role not found: <name>"}` if missing.

`POST /api/roles/validate` (body `{definition_text: "<raw yaml>"}`) →
`{ok, errors[], warnings[], parsed|null}`.

`POST /api/roles/serialize` (body `{definition: {...}}`) → `{filename, content}`
where `content` is the canonical YAML (byte-identical to the write path) and
`filename` is the suggested `<name>.yaml`. Writes nothing to disk; backs the
portal's **Download YAML** action. Non-dict input → 400.

`PUT /api/roles/{name}` (body `{definition_text: "<raw yaml>"}`, optional
`render_agent: true`, `force: false`) creates/updates the role. 200 →
`{ok, file, created, validation, role, agent?}`. **Schema-invalid → 400**.
Reference issues (missing agent file, missing schema or rubric file) persist and
return under `validation.warnings`.

```bash
# Round-trip: read, inspect, update
curl -s http://127.0.0.1:8910/api/roles/architecture-reviewer | jq .parsed

curl -s -X PUT http://127.0.0.1:8910/api/roles/my-new-role \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-new-role.yaml)"

# Role editor field enums
curl -s http://127.0.0.1:8910/api/roles/options | jq .
```

The filename is chosen from `metadata.name` (slugified). Writes take an exclusive
lock and use atomic temp-then-rename, mirroring the council write path.
