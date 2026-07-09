---
title: "Feature Contract: HTTP Run-Launch Endpoint (POST /api/runs)"
schema_version: 2
doc_type: feature_contract
it_schema: 1
description: "Add POST /api/runs so Hermes/orchestrators can scaffold+register a new RF run over HTTP instead of shelling the rf CLI, returning a run_id/status the caller polls via the existing GET /api/runs/{run_id}."
status: completed
created: 2026-07-09
updated: 2026-07-09
feature_slug: http-run-launch-endpoint
category: features
estimated_points: 6
tier: 1
owner: null
priority: medium
risk_level: medium
changelog_required: true
node_type: work_package
acceptance_criteria: []
definition_of_done: null
execution_mode: unassigned
agent_title: null
agent_summary: null
agent_context: null
open_questions: []
decisions:
  - decision: "Endpoint performs ONLY the deterministic scaffold+register chain (capture -> triage -> plan); it never spawns/drives the Path B discovery swarm."
    rationale: "Path B run execution requires Claude Code agents authoring source cards (rf-run-execution-path-b memory rule); a server-side HTTP handler cannot itself run that swarm. Scaffolding is the architecturally sound HTTP-native slice — the deterministic portion behind rf capture/triage/plan is pure file I/O + governance preflight, with no LLM calls."
    status: accepted
  - decision: "The 'one deep swarm at a time' concurrency limit is NOT enforced inside this endpoint."
    rationale: "There is no reliable in-repo signal for 'a swarm is currently running' — run.yaml status stays 'planned' for every scaffolded-but-unswarmed run (dozens exist today), so gating on status would false-positive immediately. The constraint is already owned operationally by whichever process drives the actual Path B swarm (Hermes / the Claude Code Workflow tool), which must continue to serialize its own swarm launches. The endpoint's response makes the caller's next step (poll GET /api/runs/{run_id}; run the swarm out-of-band) explicit so this ownership boundary is visible to callers."
    status: accepted
  - decision: "Reuse require_role(\"owner\", \"admin\") exactly as agent_jobs.py's mutation routes do; no change to rbac.py or middleware/auth.py."
    rationale: "Launching a run is a mutation with downstream cost/governance implications, same class as agent_jobs.py's POST /agent-jobs. Consistent RBAC posture across the two mutation surfaces; zero auth-logic risk."
    status: accepted
related_documents:
  - src/research_foundry/api/routers/agent_jobs.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/services/planning.py
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs:
  - "870837373190d8322810b286a24d954fc870fe91"
pr_refs: []
files_affected:
  - src/research_foundry/services/run_launch.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/api/openapi.json
  - tests/test_serve_api.py
  - tests/test_run_launch.py
  - tests/unit/test_rbac_route_sweep.py
  - CHANGELOG.md
---

```autopilot-graph
{
  "tier": 1,
  "effort_points": 6,
  "wave_count": 1,
  "phase_count": 1,
  "file_count": 6,
  "mode_d": false,
  "mode_d_reasons": [],
  "needs_spike": false,
  "spike_reasons": [],
  "single_pass_feasible": true,
  "plan_artifact_path": "docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md",
  "execution_target": "execute-contract",
  "slug": "http-run-launch-endpoint",
  "category": "features",
  "review_intensity": "standard",
  "files_affected": [
    "src/research_foundry/services/run_launch.py",
    "src/research_foundry/api/routers/runs.py",
    "src/research_foundry/api/openapi.json",
    "tests/test_serve_api.py",
    "tests/test_planning.py",
    "CHANGELOG.md"
  ],
  "execution_graph": {
    "waves": [
      {
        "id": "wave-1",
        "phases": [
          {
            "id": "phase-1",
            "title": "HTTP run-launch endpoint (scaffold + register only)",
            "mode": "C",
            "review_intensity": "standard",
            "tasks": [
              {
                "id": "TASK-1.1",
                "prompt": "Mode: C — Autonomous Feature Sprint\n\nImplement the full Feature Contract at docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md (read it directly; it is your specification). Summary: add POST /api/runs to the RF HTTP API so callers can scaffold+register a new run over HTTP (capture->triage->plan chain, or plan-only given an existing intent_id) and get back a run_id/status to poll via the existing (unmodified) GET /api/runs/{run_id}. This endpoint does NOT drive the Path B discovery swarm — scaffold+register only.\n\nFiles:\n- NEW src/research_foundry/services/run_launch.py — launch_run(...) wrapping capture_idea/triage_idea (services/capture.py) and plan_run (services/planning.py), unmodified signatures. Validate exactly one of text/intent_id (ValueError on violation).\n- EDIT src/research_foundry/api/routers/runs.py — add LaunchRunRequest pydantic model + POST /runs route, modeled on api/routers/agent_jobs.py's LaunchJobBody/launch_job (RBAC Depends(require_role(\"owner\",\"admin\")), identity capture via request.state.identity with a WKSP-304-forward-compat TODO comment matching agent_jobs.py's exact style, audit_service.record_event with mutation_type=\"run_launched\", exception mapping per the contract's HTTP status table in section 7). Update the stale bottom-of-file comment block that currently claims runs.py has no mutation routes.\n- EDIT src/research_foundry/api/openapi.json — regenerate to include the new route/schemas (determine the correct regeneration command; do not hand-edit).\n- EDIT tests/test_serve_api.py — add integration tests (TEST-00N numbering) per contract Acceptance Criteria section 9.\n- EDIT or NEW test module for src/research_foundry/services/run_launch.py — unit tests for branch logic (text path, intent_id path, both-set, neither-set, unknown intent_id, governance-block) without requiring TestClient. Reuse tests/test_planning.py's existing GovernanceError fixture setup rather than inventing a new one.\n- EDIT CHANGELOG.md — add an [Unreleased] entry.\n\nDo NOT touch src/research_foundry/api/auth/rbac.py, src/research_foundry/api/middleware/auth.py, or the signatures of capture_idea/triage_idea/plan_run. Do NOT implement any swarm-launching or concurrency-lock mechanism (explicitly out of scope per contract Decision #2).\n\nValidation: run ./.venv/bin/python -m pytest tests/test_serve_api.py tests/test_planning.py tests/test_capture_triage.py -q (NOT the pyenv python shim — it fails with \"No module named research_foundry\"); also run ./.venv/bin/python -m pytest --cov=research_foundry.services.run_launch --cov=research_foundry.api.routers.runs -q for coverage; run ruff check (or flake8 if ruff isn't configured for this path) and mypy --ignore-missing-imports on the two edited/new source files; run the full ./.venv/bin/python -m pytest -q suite to confirm no regressions (in particular tests/integration/test_agent_jobs_api.py and tests/unit/test_rbac_*), then git restore --staged 'runs/**' 'ccdash/**' if the full suite touched tracked run/ccdash artifacts.\n\nProduce a Completion Report per contract section 13. Do NOT git add/commit/push/stash.",
                "assigned_to": "python-backend-engineer",
                "effort": 6,
                "files_affected": [
                  "src/research_foundry/services/run_launch.py",
                  "src/research_foundry/api/routers/runs.py",
                  "src/research_foundry/api/openapi.json",
                  "tests/test_serve_api.py",
                  "tests/test_planning.py",
                  "CHANGELOG.md"
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "escalation_recommendation": "If the sprint discovers real cross-cutting scope (e.g. Hermes-side integration work, or a decision to actually enforce swarm concurrency server-side), stop and promote to Tier 2: author a PRD + Implementation Plan via /plan:plan-feature rather than stretching this single-sprint contract."
}
```

# Feature Contract: HTTP Run-Launch Endpoint (POST /api/runs)

## 1. Goal

Add `POST /api/runs` to the RF HTTP API so Hermes and other orchestrators can scaffold and register
a new run over HTTP — returning a `run_id` and initial `status` the caller polls via the existing
`GET /api/runs/{run_id}` — instead of shelling the `rf` CLI's `capture` -> `triage` -> `plan` chain.

## 2. User / Actor

- **Primary user**: Hermes (the always-on gateway service on the agentic node) and other
  orchestrators that need to trigger RF runs programmatically over the LAN API rather than by
  shelling `rf` subprocess commands.
- **Secondary users**: Any future automation (CI, scheduled research jobs) that already
  authenticates against `research-foundry-api.service` with `RF_TOKEN_AGENT`.

## 3. Job To Be Done

When an orchestrator has a research question (or an already-triaged `intent_id`) and needs a new
RF run to exist, the orchestrator wants to **POST it to the API and get back a `run_id`**, so it can
poll run status and hand the swarm-execution step (Path B: Claude Code agents author source cards,
then deterministic `rf` tail) to whichever process actually drives that swarm — without needing
local filesystem/CLI access to the RF workspace.

## 4. Scope

### In Scope

- `POST /api/runs` — launch endpoint. Accepts **either**:
  - `text` (+ optional `title`, `sensitivity`, `urgency`, `tags`, `backlog_idea_ref`) — runs the
    full `capture_idea` -> `triage_idea` -> `plan_run` chain (mirrors `rf capture` -> `rf triage` ->
    `rf plan`), **or**
  - `intent_id` (an already-triaged intent) — runs `plan_run(intent_id, ...)` directly (mirrors
    `rf plan <intent_id>` alone).
  - Common planning params passthrough: `depth`, `audience`, `max_cost_usd`, `freshness_days`,
    `profile`, `project`.
  - Exactly one of `text` / `intent_id` is required; both-or-neither is a 400.
- New service-layer orchestration module `run_launch.py` wrapping the existing
  `capture_idea` / `triage_idea` / `plan_run` functions (no changes to their signatures).
- RBAC gate (`require_role("owner", "admin")`) on the new route, matching `agent_jobs.py`'s
  mutation-route pattern exactly.
- Audit event (`audit_service.record_event`, `mutation_type="run_launched"`) on success, matching
  the `agent_job_launched` pattern in `agent_jobs.py`.
- Error mapping from `RFError` subtypes (`NotFoundError`, `GovernanceError`, `SchemaError`, base
  `RFError`) to HTTP status codes (see §7).
- Response includes an explicit `next_step` field telling the caller how to proceed (poll
  `GET /api/runs/{run_id}`; the actual discovery swarm is driven out-of-band via Path B — this
  endpoint does not run it).
- Update the stale comment block at the bottom of `runs.py` (currently states "no mutation
  routes... RBAC-005 audit") — it must move to `agent_jobs.py`-style route documentation instead
  of describing `runs.py` as read-only, since this router now owns one mutation route.
- Regenerate `src/research_foundry/api/openapi.json` to include the new route/schemas.
- Unit tests for the `run_launch` service function (both `text` and `intent_id` paths, both
  error paths) and integration tests for the new endpoint in `tests/test_serve_api.py` (following
  the `TEST-00N` numbering convention already used there).
- `CHANGELOG.md` `[Unreleased]` entry (user-facing capability: new API surface).

### Out of Scope

- Spawning, driving, or polling the actual Path B discovery swarm from this endpoint or from any
  new server-side process. The swarm remains a Claude-Code-agent-driven, out-of-band activity.
- Any concurrency-limiting/locking mechanism for "one deep swarm at a time" — see Decision #2.
  This is explicitly deferred; if real enforcement is wanted later, it needs its own spike (the
  codebase has no existing "swarm in progress" signal to gate on — `run.yaml.status` stays
  `"planned"` regardless of whether a swarm ever ran).
- NotebookLM correlation (`--notebook-mode` / `--notebook-id` CLI options) — not threaded into the
  new endpoint's request body. Existing `rf plan --notebook-mode` CLI path is unaffected.
- Any change to `auth/rbac.py`, `middleware/auth.py`, or the RBAC capability matrix — role reuse
  only, per Decision #3.
- WKSP-304 workspace-isolation *enforcement* — identity is captured from
  `request.state.identity` for forward-compat (mirroring the exact `# TODO(WKSP-304 P4): ... does
  not accept identity` pattern already used four times in `agent_jobs.py`) but is **not** threaded
  into `capture_idea`/`triage_idea`/`plan_run` — those functions accept no `identity` parameter
  today, and WKSP-304 enforcement is inert project-wide as of this writing. Do not add an
  `identity` parameter to those service functions in this contract.
- Any change to the `agent_jobs.py` router or `AgentJobService` (that is a separate, existing
  agent-job-provider launch surface, unrelated to this run-scaffold surface, despite superficial
  naming similarity).

## 5. UX / Behavior Requirements

- `POST /api/runs` with `{"text": "..."}` behaves like `rf capture "..." | rf triage <id> | rf plan
  <intent_id>` chained deterministically in one request; returns `201` with
  `{run_id, status, intent_id, raw_idea_id, brief_path, swarm_path, routing_path, next_step}` on
  success. `status` is always `"planned"` on success (the initial `run.yaml.status` value — the
  caller should use `GET /api/runs/{run_id}`'s `status_derived` field for actual progress once a
  swarm has run against it).
- `POST /api/runs` with `{"intent_id": "..."}` skips capture/triage and calls `plan_run` directly;
  same response shape, `raw_idea_id: null`.
- Supplying both `text` and `intent_id`, or neither, returns `400` with a clear `detail` message.
- A `GovernanceError` raised by `plan_run` (blocking governance rule, e.g. `work_approved` profile
  against a personal-only intent) returns `422` with
  `{"error": "governance_rejected", "violations": [...]}"` — same shape convention as
  `agent_jobs.py`'s `guard_check` rejection body, for a consistent client-side error contract
  across both mutation surfaces.
- A `NotFoundError` (unknown `intent_id`) returns `404` with an opaque `{"detail": "..."}` body —
  does not need indistinguishable-404 discipline here (intent existence isn't sensitivity-gated
  data the way run/report existence is elsewhere in this codebase), a plain 404 is sufficient.
- A `SchemaError` (malformed brief/swarm-plan/routing-decision — should not normally happen for
  well-formed requests) returns `400`.
- Any other unexpected exception returns `500` with a generic detail (never leaks internals),
  matching the `except Exception` pattern already used in `agent_jobs.py`'s `launch_job`.
- Missing/insufficient role returns `403` (`require_role` behavior, unchanged).

## 6. Data Requirements

- **Entities affected**: none new. Reuses `raw_idea`, `intent`, `ibom`, `run` file-backed
  artifacts exactly as `rf capture`/`rf triage`/`rf plan` already produce them on disk, and the
  existing `registries/run_index.yaml` registration `plan_run` already performs.
- **New fields**: none in any on-disk schema. The only new "field" is the HTTP response envelope
  itself (`run_id`, `status`, `intent_id`, `raw_idea_id`, `brief_path`, `swarm_path`,
  `routing_path`, `next_step`), which is a pure API-layer construct, not a persisted schema.
- **State changes**: identical state transitions to the existing CLI chain — a new
  `inbox/raw_ideas/<id>.md` (if `text` path), `intents/<id>.md` + `ibom` (if `text` path), and a
  new `runs/<run_id>/` scaffold + `run.yaml` + `research_brief.md` + `swarm_plan.yaml` +
  `routing_decision.yaml`, registered in `registries/run_index.yaml`.
- **Storage implications**: none — no new tables/files/indexes beyond what `plan_run` already
  writes.

## 7. API / Integration Requirements

**New endpoint:**
- `POST /api/runs` — launch a new run (scaffold + register only; does not drive the swarm).

**Internal service dependencies:**
- `research_foundry.services.capture.capture_idea` (existing, unmodified)
- `research_foundry.services.capture.triage_idea` (existing, unmodified)
- `research_foundry.services.planning.plan_run` (existing, unmodified)
- New: `research_foundry.services.run_launch.launch_run(...)` — thin orchestration wrapper around
  the three functions above; owns the "exactly one of text/intent_id" validation and the
  text-path-vs-intent-path branching. Router calls this single function; router stays thin.
- `research_foundry.api.auth.rbac.require_role` (existing, unmodified) — reused as
  `Depends(require_role("owner", "admin"))`.
- `research_foundry.services.audit_service.record_event` (existing, unmodified) — reused for the
  success-path audit event.

**HTTP status mapping (in `run_launch` -> router boundary):**

| Condition | HTTP status | Body shape |
|---|---|---|
| Success | 201 | `{run_id, status, intent_id, raw_idea_id, brief_path, swarm_path, routing_path, next_step}` |
| Both/neither of text/intent_id | 400 | `{"detail": "..."}` |
| `GovernanceError` | 422 | `{"error": "governance_rejected", "violations": [...]}` |
| `NotFoundError` (unknown intent_id) | 404 | `{"detail": "..."}` |
| `SchemaError` / other `RFError` | 400 | `{"detail": "..."}` |
| Insufficient role | 403 | (unchanged `require_role` behavior) |
| Unexpected exception | 500 | `{"detail": "..."}` (generic, no internals) |

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `src/research_foundry/api/routers/agent_jobs.py` — mutation-route RBAC dependency pattern
  (`_RBAC_...` module-level `Depends(require_role(...))`), audit-event-on-success pattern,
  `except Exception` -> 500 pattern, identity-capture-for-forward-compat pattern
  (`identity = getattr(request.state, "identity", None)` + `# TODO(WKSP-304 P4): ... does not
  accept identity` comment style).
- `src/research_foundry/cli_commands.py`'s `capture`/`triage`/`plan` command bodies — the exact
  chain and parameter set the new endpoint mirrors over HTTP; do not diverge from the CLI's
  parameter names/semantics without a documented reason.
- `src/research_foundry/services/planning.py`'s `plan_run` docstring — the governance preflight
  behavior it already performs must not be re-implemented or duplicated in the router; let
  `GovernanceError` propagate and map it at the router boundary.

**Must not change** (protected areas):
- `src/research_foundry/api/auth/rbac.py`, `src/research_foundry/api/middleware/auth.py` — no
  edits. Reuse only.
- `capture_idea`, `triage_idea`, `plan_run` function signatures in `services/capture.py` /
  `services/planning.py` — call them as-is; do not add an `identity` or `workspace_id` parameter
  to them in this contract (out of scope; see §4).
- The existing five `GET` routes in `runs.py` — read-only behavior and response shapes must be
  byte-identical after this change (additive only).

**New dependencies:**
- Allowed? **No.** No new third-party dependencies expected — `run_launch.py` only imports
  existing project modules (`capture`, `planning`, `errors`).

## 9. Acceptance Criteria

- [ ] `POST /api/runs` with `{"text": "..."}` returns `201` and a `run_id` that subsequently
      resolves via `GET /api/runs/{run_id}` (existing endpoint, unmodified) with `status_derived ==
      "planned"`.
- [ ] `POST /api/runs` with `{"intent_id": "<existing-intent>"}` returns `201`, skips
      capture/triage, and `raw_idea_id` is `null` in the response.
- [ ] `POST /api/runs` with both `text` and `intent_id` set returns `400`.
- [ ] `POST /api/runs` with neither `text` nor `intent_id` set returns `400`.
- [ ] `POST /api/runs` with an unknown `intent_id` returns `404`.
- [ ] `POST /api/runs` against an intent whose profile trips the existing governance preflight
      (mirroring `test_planning.py`'s existing `GovernanceError` coverage, e.g. `profile="work_approved"`
      against a personal-only intent) returns `422` with `{"error": "governance_rejected", ...}`.
- [ ] When `auth_mode == "token"` and RBAC enforcement is active, a caller without `owner`/`admin`
      role receives `403`; a caller with the role and a valid bearer token succeeds (mirrors
      `agent_jobs.py`'s existing RBAC test coverage pattern in `test_rbac_*`).
- [ ] All five pre-existing `GET /api/runs*` / `GET /api/reports/{run_id}/anchors` endpoints in
      `runs.py` are unchanged in behavior and response shape (regression-checked by existing tests
      in `tests/test_serve_api.py` continuing to pass unmodified).
- [ ] A successful launch writes exactly one `audit_service` event with
      `mutation_type="run_launched"`.
- [ ] `src/research_foundry/api/openapi.json` is regenerated and includes `POST /api/runs`'s
      request/response schemas.
- [ ] `CHANGELOG.md` `[Unreleased]` has an entry describing the new endpoint.
- [ ] The stale "runs.py has no mutation routes as of P5.2" comment block at the bottom of
      `runs.py` is updated to reflect the new mutation route (no longer describing the router as
      fully read-only), following the RBAC-FORWARD-COMPAT documentation convention already
      established in `auth/rbac.py`.

## 10. Validation Requirements

- [ ] `./.venv/bin/python -m pytest tests/test_serve_api.py tests/test_planning.py
      tests/test_capture_triage.py -q` passes (NOT the pyenv `python` shim — it fails with "No
      module named research_foundry").
- [ ] `./.venv/bin/python -m pytest --cov=research_foundry.services.run_launch
      --cov=research_foundry.api.routers.runs -q` shows meaningful coverage of the new code paths
      (success x2, both-set, neither-set, not-found, governance-block).
- [ ] `ruff check src/research_foundry/services/run_launch.py
      src/research_foundry/api/routers/runs.py` (or `flake8` if `ruff` is not configured for this
      path — check `pyproject.toml`) passes clean.
- [ ] `mypy src/research_foundry/services/run_launch.py src/research_foundry/api/routers/runs.py
      --ignore-missing-imports` passes clean.
- [ ] Full `./.venv/bin/python -m pytest -q` run does not regress any existing test (in particular
      `tests/integration/test_agent_jobs_api.py`, `tests/unit/test_rbac_*`, and
      `tests/test_serve_api.py`).
- [ ] No unrelated changes introduced — do not touch `runs/**` or `ccdash/**` tracked artifacts as
      a side effect of running the test suite (per the project's known pytest-pollution gotcha);
      `git restore --staged 'runs/**' 'ccdash/**'` before any commit if the full suite was run.

## 11. Risk Areas

- **Caller confusion about "launch" semantics**: because this endpoint does not run the Path B
  swarm, a naive caller might expect `POST /api/runs` to fully execute research. Mitigated by the
  `next_step` response field and explicit docstring language ("scaffold + register only").
- **Governance error-shape drift**: reusing the `{"error": "governance_rejected", "violations":
  [...]}"` shape from `agent_jobs.py` requires translating `GovernanceError.violations` (a
  `list[str]`) into the same per-violation dict shape `agent_jobs.py` uses for its own
  `GuardResult.violations` (which are richer objects with `rule_id`/`severity`/`message`/`detail`).
  These are two different violation representations from two different governance code paths
  (`plan_run`'s internal preflight vs. `agent_jobs.py`'s `guard_check`) — the implementer must not
  assume they're interchangeable; adapt `GovernanceError.violations` (list of message strings) into
  a compatible-but-simpler per-item shape (e.g. `{"rule_id": null, "severity": "block", "message":
  "<str>", "detail": null}`) rather than forcing a false 1:1 match.
- **RBAC-901 route-sweep test**: adding a mutation route without the `require_role` dependency
  marker (`_is_require_role = True`) would likely fail an existing route-sweep test (referenced in
  `rbac.py`'s docstring as "RBAC-901"). Confirm this test's location and that the new route passes
  it before considering the contract complete.
- **openapi.json regeneration mechanism unknown**: no committed script was found that regenerates
  `src/research_foundry/api/openapi.json`; the implementer must determine the correct regeneration
  command (likely `create_app().openapi()` dumped to that path) and confirm it matches how the file
  was previously produced, to avoid an unrelated diff noise in the committed JSON.

## 12. Implementation Notes

**Suggested approach:**
1. Write `src/research_foundry/services/run_launch.py` with a single function
   `launch_run(*, text=None, intent_id=None, title=None, sensitivity="personal", urgency="medium",
   tags=None, backlog_idea_ref=None, depth="standard", audience="technical", max_cost_usd=5.0,
   freshness_days=180, profile=None, project=None, paths=None) -> LaunchRunResult` (a small
   dataclass: `run_id, status, intent_id, raw_idea_id, brief_path, swarm_path, routing_path`).
   Validate exactly one of `text`/`intent_id` up front (`ValueError` on violation — the router maps
   `ValueError` to 400).
2. Add `LaunchRunRequest` (pydantic `BaseModel`) and the `POST /runs` route to
   `api/routers/runs.py`, modeled closely on `agent_jobs.py`'s `LaunchJobBody`/`launch_job`
   structure (RBAC dependency, identity capture, audit event, exception mapping).
3. Update the bottom-of-file comment block in `runs.py` to reflect the new mutation route.
4. Regenerate `openapi.json`.
5. Add tests to `tests/test_serve_api.py` (integration, following `TEST-00N` numbering) and a small
   unit test module for `run_launch.py` covering the branch logic without needing `TestClient`.
6. Add the `CHANGELOG.md` entry.

**Similar existing code**:
- `src/research_foundry/api/routers/agent_jobs.py::launch_job` — closest existing analog for
  RBAC + audit + error-mapping conventions on a mutation route.
- `src/research_foundry/cli_commands.py` `capture`/`triage`/`plan` command bodies (~lines 195–313)
  — the exact chain and parameter semantics to mirror.

**Known gotchas**:
- The run_id slug is derived from `title` (or the derived default title), **not** from the raw
  `text` — do not assume a text-derived slug when writing tests; assert against whatever `run_id`
  the response actually returns.
- `plan_run`'s governance preflight uses the *effective* profile (arg `profile`, else the intent's
  `governance.key_profile_allowed`, else `"personal"`) — a governance-rejection test must set up
  an intent (or pass `profile="work_approved"`) that actually trips a `block`-severity rule; check
  `tests/test_planning.py`'s existing `GovernanceError` test for the exact minimal setup already
  used there, and reuse it rather than inventing a new fixture.
- `pytest` must run under `./.venv/bin/python -m pytest` (or `uv run pytest`) — the pyenv `python`
  shim fails with `No module named research_foundry`.

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason.
- **Tests run**: What tests were added/updated and results.
- **Validation results**: Table of all validation commands (pytest, ruff/flake8, mypy) and their
  results (pass/fail/not applicable).
- **Deviations from contract**: Any material changes to the contract during implementation and why
  (e.g. if the openapi.json regeneration mechanism required a different approach than assumed).
- **Risks / Limitations**: Any remaining risks (e.g. confirmation or non-confirmation of the
  RBAC-901 route-sweep test passing).
- **Follow-up recommendations**: Suggested next steps (e.g. whether a real concurrency-limit
  mechanism should be spiked later; whether Hermes integration needs a follow-up doc).

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report
template.

---

## Metadata & References

**Tier**: 1 (3–8 points), estimated 6

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase
orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents**:
- `src/research_foundry/api/routers/agent_jobs.py` — RBAC/audit/error-mapping pattern source
- `src/research_foundry/api/routers/runs.py` — router being extended
- `src/research_foundry/services/planning.py` — `plan_run` (wrapped, unmodified)
- `src/research_foundry/services/capture.py` — `capture_idea`/`triage_idea` (wrapped, unmodified)
- `~/.claude/projects/.../memory/rf-run-execution-path-b.md` — Path B swarm execution rule and the
  operational "one deep swarm at a time" concurrency constraint this contract deliberately does
  not attempt to enforce in-process (see Decision #2)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass
validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in
  the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with
  justification.

Stay within scope. Do NOT implement a swarm-launching mechanism, a concurrency lock, or any
change to `auth/rbac.py` / `middleware/auth.py` — these are explicitly out of scope per §4 and the
Decisions above. Avoid cleanup, refactors, or feature expansion beyond this contract. The reviewer
will check for scope drift.

---

## Completion Report

### Summary

Added `POST /api/runs` to `src/research_foundry/api/routers/runs.py`, gated by
`Depends(require_role("owner", "admin"))` and backed by a new
`research_foundry.services.run_launch.launch_run(...)` orchestration module that wraps the
existing, unmodified `capture_idea` / `triage_idea` / `plan_run` functions. The endpoint performs
the deterministic scaffold+register chain only (text -> capture/triage/plan, or intent_id ->
plan-only) and never drives the Path B swarm. `openapi.json` was surgically updated (additive-only
merge, not a full regeneration) to add the new path + `LaunchRunRequest` schema. All five
pre-existing `GET` routes in `runs.py` are untouched.

### Files Changed

- `src/research_foundry/services/run_launch.py` (NEW) — `launch_run()` + `LaunchRunResult`
  dataclass; owns the "exactly one of text/intent_id" validation; wraps
  `capture_idea`/`triage_idea`/`plan_run` unmodified.
- `src/research_foundry/api/routers/runs.py` (EDIT) — added `LaunchRunRequest` pydantic model,
  `_RBAC_RUN_LAUNCH` module-level dependency, `POST /runs` route (`launch_run_endpoint`), and
  replaced the stale "no mutation routes" comment block with an updated RBAC-005/RBAC-901 audit
  note reflecting the new mutation route. Imports added: `logging`, `Request`, `BaseModel`,
  `GovernanceError`/`NotFoundError`/`RFError`/`SchemaError`, `audit_service`/`AuditEvent`/`run_launch`,
  `require_role`.
- `src/research_foundry/api/openapi.json` (EDIT) — additive merge of the new `POST /api/runs` path
  item + `LaunchRunRequest` component schema into the existing committed file (see Deviations —
  full regeneration was rejected in favor of a surgical merge to avoid unrelated diff noise from
  drift already present in the committed file before this contract).
- `tests/test_serve_api.py` (EDIT) — TEST-011a..j: 10 new integration tests for the launch endpoint
  (text path, intent_id path, both/neither-set 400, unknown-intent 404, governance-block 422, audit
  event, RBAC 403/201, and a regression check that the five pre-existing GET routes are unaffected).
- `tests/test_run_launch.py` (NEW) — unit tests for `launch_run()`'s branch logic without
  `TestClient` (text path, intent_id path, both-set, neither-set, unknown intent, governance-block).
- `tests/unit/test_rbac_route_sweep.py` (EDIT, deviation — not in original `files_affected`) —
  updated `TestRunsRouterSweep` (previously asserted `runs_router` has **zero** mutation routes,
  which the new `POST /runs` route would have violated) to the same
  gated-count-inventory pattern already used for `agent_jobs_router`/`catalog_router`/
  `reports_router`; updated the module docstring's route inventory (19 -> 20 routes).
- `CHANGELOG.md` (EDIT) — `[Unreleased]` entry describing the new endpoint.

### Acceptance Criteria Status

- [x] `POST /api/runs` with `{"text": "..."}` returns `201` and `run_id` resolves via
      `GET /api/runs/{run_id}` with `status_derived == "planned"` (TEST-011a; see Deviations note
      on the default `sensitivity_threshold` param used in the GET follow-up).
- [x] `POST /api/runs` with `{"intent_id": "..."}` returns `201`, skips capture/triage, `raw_idea_id`
      is `null` (TEST-011b).
- [x] Both `text` and `intent_id` set -> `400` (TEST-011c).
- [x] Neither set -> `400` (TEST-011d).
- [x] Unknown `intent_id` -> `404` (TEST-011e).
- [x] Governance-blocked plan -> `422` with `{"error": "governance_rejected", "violations": [...]}`
      (TEST-011f; unit-level equivalent in `test_run_launch.py`).
- [x] RBAC: no owner/admin role -> `403`; owner role + valid bearer -> `201` (TEST-011h, TEST-011i).
- [x] All five pre-existing `GET /api/runs*` / `GET /api/reports/{run_id}/anchors` endpoints
      unchanged (TEST-011j regression check; plus the untouched original TEST-001..003 test bodies
      continuing to exercise the same routes).
- [x] Exactly one `run_launched` audit event written per successful launch (TEST-011g, queries
      `audit_event` directly).
- [x] `src/research_foundry/api/openapi.json` regenerated (surgical additive merge — see Deviations)
      to include `POST /api/runs`'s request/response schemas.
- [x] `CHANGELOG.md` `[Unreleased]` entry added.
- [x] Stale "runs.py has no mutation routes" comment block updated to the RBAC-005/RBAC-901
      documentation convention (mirrors `agent_jobs.py`'s style).

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pytest tests/test_serve_api.py tests/test_planning.py tests/test_capture_triage.py tests/test_run_launch.py tests/unit/test_rbac_route_sweep.py -q` | **Pass\*** | 62 passed, 5 failed. The 5 failures (`test_get_run_detail_known_run_returns_200`, `test_get_claims_non_empty`, `test_get_claims_empty_ledger_returns_empty_list`, `test_get_source_found`, `test_sensitivity_gate_parity_work_sensitive_claim`) are **pre-existing and unrelated** — confirmed reproducible with the pristine (git `HEAD`) `runs.py` + `test_serve_api.py` *before any of this contract's edits* (a default-threshold `"public"` vs. default-plant-sensitivity `"personal"` mismatch trips the no-existence-leak gate in `_enforce_existence_gate`). All new TEST-011 tests and all of `test_run_launch.py` pass. |
| `pytest --cov=research_foundry.services.run_launch --cov=research_foundry.api.routers.runs -q` | Pass | `run_launch.py` 97% (31/32 stmts; only an unreachable defensive `ValueError` branch uncovered), `runs.py` 88% (79/90 stmts; uncovered lines are the pre-existing `get_paths()` body — always dependency-overridden in tests — one pre-existing GET error branch, and my new route's `SchemaError`/`RFError`/generic-`Exception` 500 branches, which have no dedicated AC and are not directly exercised). Overall 90%. |
| `ruff check src/research_foundry/services/run_launch.py src/research_foundry/api/routers/runs.py` | **Partial pass** | `run_launch.py`: clean (0 errors). `runs.py`: 6 `B008` findings (`Depends(...)` in argument defaults) — 5 are **pre-existing** (confirmed against pristine `HEAD` `runs.py`); my new route adds exactly 1 more of the identical pattern, matching this file's own established (if not ruff-B008-clean) `Depends(get_paths)` convention used by all five GET routes. Not a regression; ruff was already failing on this file before this contract. |
| `mypy src/research_foundry/services/run_launch.py src/research_foundry/api/routers/runs.py --ignore-missing-imports` | **Partial pass** | Zero errors reported *directly* in either target file. 8 errors surface transitively from imported modules: 7 are pre-existing (`governance.py` x5, `verification.py`, `app.py` — confirmed present even against pristine `HEAD` `runs.py`); 1 additional (`planning.py:87`, a pre-existing `_AGENT_SPECS` dict-typing issue in code I did not touch) is newly *reached* by mypy's import graph because `runs.py` now transitively imports `planning.py` via `run_launch.py` — it was not previously reachable from `runs.py`'s import graph, but the bug itself predates this contract and lives entirely inside `planning.py`, which is out of scope here. |
| Full `pytest -q` suite | **Pass\*** | Same 5 pre-existing failures as above; zero new failures. `tests/integration/test_agent_jobs_api.py` and all `tests/unit/test_rbac_*` modules pass in full (including the updated `test_rbac_route_sweep.py`). The suite touched 3 already-dirty tracked files (`ccdash/events/exec_20260613_...yaml`, two files under `runs/rf_run_20260613_what_is_the_current_release_state/`) that were **already modified at session start** (pre-existing dirty state, not caused by this run), and created untracked pollution (`ccdash/events/exec_20260709_runs.yaml`, `runs/runs/telemetry/`, `runs/runs/writebacks/`) from an **unrelated** pre-existing full-suite side effect (a non-isolated test resolves `FoundryPaths.discover()` against the real repo root and writes a spurious `run_id: "runs"` artifact tree — matches the documented "full pytest pollutes tracked run/ccdash files" gotcha, not anything introduced by `run_launch.py`/`runs.py`). Left as-is per instructions for the orchestrator to `git restore --staged`. |

### Deviations From Contract

1. **`tests/test_planning.py` not edited; `tests/test_run_launch.py` created instead.** The contract
   asked for unit tests to "reuse `tests/test_planning.py`'s existing `GovernanceError` fixture
   setup." That fixture does not actually exist in `test_planning.py` — the real (and only)
   `GovernanceError`-over-`plan_run` fixture in this codebase is `_write_intent` /
   `test_plan_run_blocks_work_profile_on_personal_intent` in `tests/test_cli_governance.py`. I
   reused that exact fixture shape (mirrored verbatim as a local helper) in a new, dedicated
   `tests/test_run_launch.py` module rather than shoehorning unrelated service tests into
   `test_planning.py` (which tests `plan_run` only, not the new `run_launch` wrapper). Updated
   `files_affected` accordingly.
2. **`tests/unit/test_rbac_route_sweep.py` edited (not in the original `files_affected` list).**
   This was foreseen by the contract's own §11 Risk Area ("RBAC-901 route-sweep test — confirm the
   new mutation route passes it"): the existing `TestRunsRouterSweep.test_runs_has_no_mutation_routes`
   hard-asserted `runs_router` has **zero** mutation routes. Adding `POST /runs` without updating
   this test would have been an immediate, unavoidable regression. Updated it to the same
   gated/count/inventory three-test pattern already used for `agent_jobs_router` — confirms
   `POST /runs` **is** gated (RBAC-901 passes) rather than removing the safety net.
3. **`openapi.json` was surgically merged, not fully regenerated.** No committed regeneration
   script exists (confirmed by repo-wide grep). A full `create_app().openapi()` dump was attempted
   first and diffed against the committed file: the committed file is already stale relative to
   current `runs.py`/`reports.py` GET-route behavior in ways unrelated to this contract (four of
   the five pre-existing GET path items differ from a fresh dump — pre-existing drift, not
   something I introduced), and a full regen would also silently omit `admin_router`/`audit_router`
   /`auth_identity_router` paths' *absence* consistency in a way that looks like unrelated
   diff noise for this contract. To honor "additive only" and avoid diff noise (contract §11 Risk
   Area, explicitly named), I extracted only the new `POST /api/runs` path item and the new
   `LaunchRunRequest` schema from a freshly generated spec and merged them into the existing file
   in place, leaving every other byte untouched. Confirmed via `git diff --stat`: a clean
   159-line-insertion, 0-deletion diff.
4. **GET-parity test (TEST-011a) and the regression test (TEST-011j) pass `sensitivity_threshold`
   explicitly.** `launch_run` defaults to `sensitivity="personal"` (contract default), while
   `GET /api/runs/{run_id}`'s own default threshold is `"public"` — a caller reading back a
   personal-sensitivity run at the default threshold 404s via the pre-existing no-existence-leak
   gate, independent of anything in this contract. Passing the threshold explicitly isolates the
   new endpoint's behavior from that pre-existing, unrelated GET-side default mismatch (documented
   pre-existing failures above).
5. **`audit_service.MUTATION_TYPES` was NOT extended to include `"run_launched"`**, even though the
   contract specifies exactly that `mutation_type` string. `audit_event.mutation_type` has no DB
   `CHECK` constraint (confirmed in `rbac_store.py`'s DDL — plain `TEXT NOT NULL`), so the write
   succeeds regardless. `tests/unit/test_audit_service.py::TestTaxonomyCompleteness` hard-locks
   `MUTATION_TYPES` to exactly 6 specific reserved values (none is `"run_launched"`); extending the
   frozenset would break that existing, unrelated completeness test. `audit_service.py` is not in
   this contract's declared scope. Flagged as a follow-up recommendation below rather than expanded
   in-scope.

### Risks and Limitations

- **RBAC-901 route-sweep test: CONFIRMED PASSING.** `tests/unit/test_rbac_route_sweep.py::TestRunsRouterSweep::test_all_runs_mutations_are_gated`
  passes — `POST /runs` carries the `require_role`-derived dependency marker.
- **`openapi.json` regeneration mechanism: CONFIRMED** as `create_app().openapi()` (in-memory,
  no live server needed), consistent with the `phase-4-completion.md` note ("generated from live
  app") for the prior agent-jobs addition — but applied as a surgical merge rather than a full
  dump, per Deviation #3 above.
- `run_launch.py`'s `except SchemaError` / `except RFError` / generic `except Exception` -> 500
  branches in the router have no dedicated Acceptance Criterion and are not directly test-covered
  (defensive branches mirroring `agent_jobs.py`'s identical pattern).
- The pre-existing `ruff`/`mypy` debt on `runs.py` (B008 `Depends()`-in-defaults; transitive mypy
  errors in `governance.py`/`verification.py`/`app.py`/`planning.py`) means this contract cannot
  achieve a fully "clean" lint/type gate on `runs.py` — that debt predates this contract and is out
  of scope to fix here.
- The 5 pre-existing `test_serve_api.py` failures and the full-suite `runs/**`/`ccdash/**` pollution
  are both pre-existing, environment-level issues unrelated to this contract; flagged for separate
  triage, not fixed here (out of scope; fixing them would itself be scope drift).

### Follow-Up Recommendations

1. Investigate and fix the pre-existing `test_serve_api.py` sensitivity-threshold-default mismatch
   (5 failing tests) — likely a real regression from a recent `runs.py` commit
   (`504bc38 feat(api): existence-gate parity across all 4 run-detail endpoints`) or a stale
   default in `_make_config`'s test helper; separate PRD/bugfix, not part of this contract.
2. Investigate the full-suite `runs/**`/`ccdash/**` pollution source (a non-isolated test writing a
   `run_id: "runs"` artifact tree against the real repo root) — matches the known
   "full pytest pollutes tracked run/ccdash files" gotcha; consider a `conftest.py`-level guard
   (e.g., `monkeypatch.chdir` or a `FoundryPaths.discover()` autouse fixture override) to make this
   impossible suite-wide.
3. Extend `audit_service.MUTATION_TYPES` to include `"run_launched"` (and update
   `TestTaxonomyCompleteness`) in a small, dedicated follow-up — currently the taxonomy frozenset is
   out of sync with this contract's own audit call.
4. If Hermes integration surfaces a real need to enforce "one deep swarm at a time" server-side,
   that requires its own SPIKE (per Decision #2 and the contract's `escalation_recommendation`) —
   no in-repo signal currently exists to gate on.
5. `planning.py:87`'s `_AGENT_SPECS` dict-typing mypy error and the 5 pre-existing `runs.py` B008
   ruff findings are small, low-risk cleanup opportunities for a future lint-debt pass — not blocking
   for this contract.

### Memory Candidates Captured

- **Gotcha**: `tests/test_cli_governance.py::_write_intent` (not `tests/test_planning.py`) is the
  actual minimal `GovernanceError`-over-`plan_run` fixture in this codebase — a `work_approved`
  profile against a `key_profile_allowed: personal` intent trips `no_work_keys_for_personal_runs`.
  Any future contract/PRD referencing "test_planning.py's GovernanceError fixture" should be
  corrected to point at `test_cli_governance.py`.
- **Gotcha**: `GET /api/runs/{run_id}`'s default `sensitivity_threshold` (`"public"`) vs.
  `capture_idea`/`launch_run`'s default `sensitivity` (`"personal"`) means a bare
  `POST /api/runs` -> bare `GET /api/runs/{run_id}` round-trip 404s unless the caller passes
  `?sensitivity_threshold=personal` (or higher) on the GET. This is pre-existing
  `_enforce_existence_gate` behavior (`SENSITIVITY_ORDER`), not new to this contract, but worth
  flagging for any future HTTP-client/Hermes-integration doc.
- **Gotcha**: `src/research_foundry/api/openapi.json` has no committed regeneration script;
  the correct mechanism is `create_app(cfg).openapi()` (in-process, no server needed) — but the
  committed file already has pre-existing drift from current router behavior, so a full dump
  introduces unrelated diff noise. Prefer a surgical merge (extract only the new/changed path
  items + component schemas) until a canonical regeneration script is authored.
