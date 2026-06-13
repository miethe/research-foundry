# Surfaces: CLI / Web / API / Skill

The same capability is available from the CLI, the Web portal, the HTTP API, and
the `council-review` skill — for a human or an agent, from any project that has
ARC installed. Scaffolding surfaces (CLI/Web/API) set up and validate; they never
run reviewers. The `council-review` skill is the only surface that populates a run.

## Matrix

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
| Council field enums (incl. categorySuggestions/tagSuggestions) | — | wizard/editor options | `GET /api/councils/options` | — |
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

## Curl examples

Backend default base: `http://127.0.0.1:8910`. All bodies are JSON; non-2xx
errors carry `{detail}`.

### Runs and councils

```bash
# Preview a run (resolve + validate, write nothing)
curl -s -X POST http://127.0.0.1:8910/api/runs/preview \
  -H 'Content-Type: application/json' \
  -d '{"council":"auto","target":"src/api/","objective":"Check endpoints before merge."}'

# Create a run skeleton (201; returns validation + next_steps with skill_prompt)
curl -s -X POST http://127.0.0.1:8910/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"council":"architecture-review-council","target":"docs/design.md","objective":"Evaluate portability."}'

# Create from a pasted/uploaded RunSpec
curl -s -X POST http://127.0.0.1:8910/api/runs \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{spec_text: .}' < run_spec.yaml)"

# Recommend a council (heuristic; default-review-council always included)
curl -s -X POST http://127.0.0.1:8910/api/councils/recommend \
  -H 'Content-Type: application/json' \
  -d '{"objective":"Evaluate the control-plane architecture","target":"docs/design.md"}'

# Council editor field enums (run modes, reviewer roles, adjudicators,
# categorySuggestions, tagSuggestions, schema files)
curl -s http://127.0.0.1:8910/api/councils/options

# Read a council (raw + parsed); 404 {detail} if missing
curl -s http://127.0.0.1:8910/api/councils/architecture-review-council

# Validate a council def without saving
curl -s -X POST http://127.0.0.1:8910/api/councils/validate \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-council.yaml)"

# Create / update a council (200; schema-invalid → 400, reference issues → warnings)
curl -s -X PUT http://127.0.0.1:8910/api/councils/my-new-council \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-new-council.yaml)"
```

### Reviewer roles

```bash
# List all reviewer roles (summary shape)
curl -s http://127.0.0.1:8910/api/roles

# Role editor field enums (roleTypes, toolModes, modelClasses, toolSuggestions, …)
curl -s http://127.0.0.1:8910/api/roles/options

# Read one role (raw + parsed); 404 {detail} if missing
curl -s http://127.0.0.1:8910/api/roles/architecture-reviewer

# Validate a role def without saving
curl -s -X POST http://127.0.0.1:8910/api/roles/validate \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-role.yaml)"

# Create / update a role (200; schema-invalid → 400, reference issues → warnings)
curl -s -X PUT http://127.0.0.1:8910/api/roles/my-new-role \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{definition_text: .}' < my-new-role.yaml)"

# Render the .claude/agents/<name>.md companion stub (add {"force":true} to overwrite)
curl -s -X POST http://127.0.0.1:8910/api/roles/architecture-reviewer/render-agent \
  -H 'Content-Type: application/json' \
  -d '{}'
```

### Library

```bash
# Browse rubrics, schemas, and adapters (read-only reference)
curl -s http://127.0.0.1:8910/api/library
```

### Agentic composition

```bash
# Check availability before calling compose
curl -s http://127.0.0.1:8910/api/authoring/status
# {"available": true, "auth_mode": "oauth", "model": "claude-sonnet-4-6"}

# Compose a council draft from natural language (writes nothing)
curl -s -X POST http://127.0.0.1:8910/api/authoring/compose \
  -H 'Content-Type: application/json' \
  -d '{"kind":"council","prompt":"a council to review database migrations for a Postgres shop"}'
# → {ok, kind, draft, rationale, validation, warnings}

# Compose a reviewer-role draft
curl -s -X POST http://127.0.0.1:8910/api/authoring/compose \
  -H 'Content-Type: application/json' \
  -d '{"kind":"role","prompt":"a read-only specialist that checks SQL migration correctness"}'
```

## Response shapes (essentials)

**Runs and councils**

- `POST /api/runs/preview` → `{ok, errors[], warnings[], resolved|null, plan|null, auto_selected|null}`.
  Too-incomplete input → `ok:false` + errors with `resolved:null, plan:null`
  (still HTTP 200).
- `POST /api/runs` → 201 `{run_id, dir, path, council, reviewers[], auto_selected,
  validation, summary, next_steps}`. `next_steps` = `{message, skill_prompt,
  cli_validate, run_dir}`. 400 `{detail}` on missing target/objective or unknown
  council.
- `POST /api/councils/recommend` → `{objective, target, recommendations[]}`; each
  recommendation `{name, score, recommended, councilType, purpose, reviewers[],
  matched_terms[], rationale}`, sorted desc, top one `recommended:true`.
- `GET /api/councils/options` → `{runModes[], reviewerRoles[], adjudicators[],
  gateSuggestions[], dataClassSuggestions[], outputSchemaFiles[],
  councilTypeSuggestions[], categorySuggestions[], tagSuggestions[]}`.
- `GET /api/councils` summaries include `category` and `tags` fields.
- `POST /api/councils/validate` → `{ok, errors[], warnings[], parsed|null}`.
- `GET /api/councils/{name}` → `{name, file, exists, raw, parsed}`.
- `PUT /api/councils/{name}` → 200 `{ok, file, created, validation, council}`;
  400 `{detail}` when schema-invalid.

**Reviewer roles**

- `GET /api/roles` → array of role summaries:
  `{name, file, roleType, mission, version, owner, hasAgent, allowedTools,
  deniedTools, defaultModelClass, defaultMode, primarySchema}`.
- `GET /api/roles/options` → `{roleTypes[], toolModes[], modelClasses[],
  providerSuggestions[], capabilitySuggestions[], toolSuggestions[],
  schemaFiles[], rubricFiles[], dataClassSuggestions[]}`.
- `POST /api/roles/validate` → `{ok, errors[], warnings[], parsed|null}`.
- `GET /api/roles/{name}` → `{name, file, exists, raw, parsed}`; 404 `{detail}` if missing.
- `PUT /api/roles/{name}` → 200 `{ok, file, created, validation, role, agent?}`;
  400 `{detail}` when schema-invalid.
- `POST /api/roles/{name}/render-agent` → `{ok, created, file, agent}`;
  409 (or `ok:false`) when file exists and `force` is false.

**Library**

- `GET /api/library` → `{rubrics: [{name, path, summary}], schemas: [{name, path, summary}], adapters: [{name, path, summary}]}`.

**Agentic composition**

- `GET /api/authoring/status` → `{available, reason?, auth_mode?, model?}`.
  `reason` values when unavailable: `"package_not_installed"`, `"no_credential"`.
- `POST /api/authoring/compose` → `{ok, kind, draft, rationale, validation,
  warnings[], degraded?}`. 503 `{detail}` when `available:false`.
  `draft` is a schema-valid object (not a committed file).

**Health**

- `GET /api/health` `integrations.authoring` → `{available, auth_mode}`.

## Honesty rule

The recommend/`auto` path is a transparent heuristic, not an LLM. Always present
its pick as a labeled suggestion with a rationale. The real agent-driven council
choice happens when the `council-review` skill runs.
