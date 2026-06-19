# RunSpec + Ways to Create a Run

A run is an **empty 11-artifact skeleton** under `runs/<date>-<slug>/`. Creating
it never runs reviewers. The `council-review` skill populates it; `uv run arc
validate` is the close gate.

## The RunSpec contract

A RunSpec is a request to scaffold a run. Template:
`templates/run_spec.yaml`. Schema: `schemas/council-run-spec.schema.json`
(`$id` `https://agentic-research.local/schemas/council-run-spec.schema.json`,
draft 2020-12, title `ARCCouncilRunSpec`, `additionalProperties: false`).

```yaml
apiVersion: arc/v1alpha1
kind: CouncilRunSpec
council: default-review-council    # council name, or "auto" to recommend
target: path/to/artifact-or-description
objective: Evaluate X for Y before Z.
constraints:
  - read_only
  - evidence_required
# slug: short-slug
# run_id: arc-run-2026-05-28-foo
# date: 2026-05-28
# provider_adapters: []
# optional_reviewers: [correctness-reviewer]   # convene council-declared optionals
# focus_questions: [blast-radius, "How do cold starts behave?"]  # ids or free text
# parameters: {depth: deep, include_threat_model: true}  # per council runConfig.parameters
# notes: free-form human context (ignored by scaffolder)
```

- **Required:** `council`, `target`, `objective`.
- **Optional:** `apiVersion`, `kind`, `constraints[]`, `slug`, `run_id`, `date`,
  `provider_adapters[]`, `optional_reviewers[]`, `focus_questions[]`,
  `parameters{}`, `notes` (`notes` is ignored by the scaffolder).
- `council: auto` asks the heuristic recommender to choose a council.
- **Per-council run customization** (resolved against the council's
  `spec.runConfig`, all backward-compatible):
  - `optional_reviewers[]` — role names from the council's `optionalReviewers`
    to convene for this run; merged into the reviewer roster (undeclared names
    are ignored with a warning).
  - `focus_questions[]` — each entry is either a declared question **id** (from
    `runConfig.focusQuestions`, resolved to its text) or **free text** (kept
    verbatim). When omitted, the council's `default: true` questions are used.
  - `parameters{}` — `id: value` per `runConfig.parameters`; values are coerced
    to the declared type and unspecified declared params fall back to `default`.
  - When `constraints` is omitted, `runConfig.defaultConstraints` is used (else
    the standard `read_only` + `evidence_required`).
  - Resolved `focus_questions` land in the run manifest + the evidence pack's
    "Focus questions" section; `parameters` and `optional_reviewers` are recorded
    in the manifest. This is how `council-review` picks them up.

## (a) CLI — `arc run`

```bash
uv run arc run \
  --council architecture-review-council \
  --target docs/design.md \
  --objective "Evaluate portability before adoption." \
  --constraint read_only \
  --constraint evidence_required
```

Flags: `--council`, `--target`, `--objective`, `--output`, `--run-id`, `--slug`,
`--date`, `--constraint` (repeatable), `--force`, plus:

- `--optional-reviewer NAME` (repeatable) — convene a council-declared optional reviewer.
- `--focus-question ID|TEXT` (repeatable) — a declared question id or free text.
- `--param KEY=VALUE` (repeatable) — set a council-declared run parameter.
- `--spec PATH` — load a RunSpec; explicit flags override spec fields.
- `--council auto` — scaffold with the top heuristic recommendation; the chosen
  council and rationale are reported.
- `--dry-run` — resolve + validate the plan, print it as JSON, write nothing.

```bash
uv run arc run --spec run_spec.yaml                 # from a file
uv run arc run --spec run_spec.yaml --slug override  # flag wins over spec
uv run arc run --council auto --target src/api/ \
  --objective "Check endpoints before merge." --dry-run
```

On success the CLI prints the run directory and the next steps (the
`council-review` skill prompt + the `arc validate` command).

## (b) HTTP API

All bodies are JSON. The frontend extracts `body.detail` on non-2xx errors.

`POST /api/runs/preview` — resolve + validate, write nothing. Body (all
optional; `spec_text` is raw YAML/JSON parsed server-side, then structured
fields overlay it):

```bash
curl -s -X POST http://127.0.0.1:8910/api/runs/preview \
  -H 'Content-Type: application/json' \
  -d '{"council":"auto","target":"src/api/","objective":"Check endpoints before merge."}'
```

Returns `{ok, errors[], warnings[], resolved|null, plan|null, auto_selected|null}`.
When inputs are too incomplete to resolve, it returns `ok:false` + errors with
`resolved:null, plan:null` (still HTTP 200).

`POST /api/runs` — create the skeleton (same body shape as preview). 201 returns
`{run_id, dir, path, council, reviewers[], optional_reviewers[], focus_questions[],
parameters{}, constraints[], auto_selected, validation, summary, next_steps}`.
`next_steps` contains `message`, `skill_prompt` (paste into the
`council-review` skill), `cli_validate`, and `run_dir`. 400 `{detail}` on bad
input (missing target/objective, unknown council).

```bash
curl -s -X POST http://127.0.0.1:8910/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"council":"architecture-review-council","target":"docs/design.md","objective":"Evaluate portability."}'
```

Pasted/uploaded RunSpec YAML goes in `spec_text`:

```bash
curl -s -X POST http://127.0.0.1:8910/api/runs \
  -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{spec_text: .}' < run_spec.yaml)"
```

## (c) Web portal

A **"New review" modal** (launched from the top bar, the Runs page, and the
dashboard) is the entry point: drop / browse / paste a RunSpec file (sent as
`spec_text` to `POST /api/runs/preview` then `POST /api/runs`), or click **Build
with guided wizard** to open `/runs/new`.

`/runs/new` — a **multi-step guided wizard**: (1) Council (radio cards +
recommend + auto), (2) Scope (target, objective, constraints — prefilled from the
council's `runConfig.objectiveTemplate` / `targetHint` / `defaultConstraints`),
(3) Tune (council-declared focus-question toggles, typed parameter controls, and
optional-reviewer toggles — this step is skipped when the council has no
`runConfig`), (4) Review + create. A live plan preview (`POST /api/runs/preview`)
shows the resolved reviewers, focus questions, and parameters throughout.
Creating a run calls `POST /api/runs` — the same path as the CLI.

## (d) Let ARC choose the council

`POST /api/councils/recommend` (CLI: `arc councils recommend`). Body
`{objective, target?}`:

```bash
curl -s -X POST http://127.0.0.1:8910/api/councils/recommend \
  -H 'Content-Type: application/json' \
  -d '{"objective":"Evaluate the control-plane architecture","target":"docs/design.md"}'
```

Returns recommendations sorted by score, the top one with `recommended:true`,
each with a `rationale` and `matched_terms`. `default-review-council` is always
included as a baseline fallback.

> The recommender is a **transparent heuristic** (keyword scoring over council
> name/type/purpose/focusChecks/requiredInputs). It is not an LLM and is never
> authoritative. The real agent-driven choice happens when `council-review`
> runs and Claude reads the catalog. Always present it as a labeled suggestion.

## After scaffolding

Hand off to the `council-review` skill with the printed prompt, then:

```bash
uv run arc validate runs/<date>-<slug>
```
