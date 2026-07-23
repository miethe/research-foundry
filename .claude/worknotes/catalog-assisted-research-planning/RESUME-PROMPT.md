# C3 Catalog-Assisted Research Planning — Resume Prompt (P3–P6)

Paste the block below into a fresh Claude Code session (Opus) rooted at the Research Foundry repo.
It resumes execution of the C3 plan at **Phase P3**. P1 and P2 are done and gated on `main`.
Read `context.md` in this same directory first — it carries the frozen decisions, the RPC deferral,
and the P2 outputs P3 builds on.

---

## PROMPT TO PASTE

> Resume executing the Tier-3 implementation plan
> `docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md`
> (C3 Catalog-Assisted Research Planning, ITT node `node_01KY5SHD2K1G9KT40E26XMVR43`) at **Phase P3**.
> P1 and P2 are complete and gated; their work is squash-merged to `main`. Squash to main when P3–P6
> are done and gated. Use `/delegation-router` and route all leaf implementation/docs work to **ICA**
> (`ICA_KEY=CC1 ~/ica-claude.sh ... --model 'claude-sonnet-5[1m]'`), not subscription agents; keep
> reviewer gates (task-completion-validator, karen) on claude.
>
> First read, in order:
> 1. `.claude/worknotes/catalog-assisted-research-planning/context.md` — full handoff state.
> 2. `docs/dev/architecture/carp-contract-freeze.md` — the frozen, gated contract. Do NOT re-litigate it.
> 3. The plan's Phase P3/P4/P5/P6 sections + Structured Acceptance Criteria.
>
> Then create/enter a worktree (or reuse `worktree-carp-c3-catalog-planning` if present), re-establish
> the 16-failure test baseline, and run the phases **serially with their gates**:
> P3 (validator + karen) → P4 (validator + karen) → P5 (validator only) → P6 (validator + karen final).
> Each phase = one ICA leaf executing the corresponding brief below, then the gate(s), then a
> fix-cycle if rejected. Re-run authoritative pytest/schema-validation yourself after every leaf —
> never trust the leaf's self-report — and diff the full-suite failures against the 16-failure baseline.
>
> The four phase briefs are embedded verbatim below. Hand each to the ICA leaf as its task file.

---

## Critical carry-forward reminders (also in context.md)

1. **RPC deferral:** C1 (Research Provenance Continuity) has NOT executed; no RPC schemas exist.
   When any AC says "RPC context", it means the CARP-owned `selected_assertion_ref` + `retrieval_receipt`
   carrier (freeze doc §4). Do NOT author or fabricate an RPC surface. CARP-6.6's RPC leg is deferred.
2. **P4 must thread a real `sensitivity_threshold`** from the run/launch context into
   `RetrievalConstraints`, or the `allow` path is unreachable end-to-end (P2 made it caller-supplied +
   never-defaulted; absent ⇒ fail-closed deny).
3. **P3 counter trap:** gate all six candidate-derived summary counters (incl. `questions_residual`)
   on `record_count > 0`; omit otherwise, or every catalog-empty/denied plan is schema-invalid.
4. **Escalation rule:** if fail-closed makes a path dead, escalate as a blocker — do not synthesize a
   value. Verify "no such field exists" before claiming it. Report deviations as deviations.
5. **ICA budget is per-key-block.** CC4/CC2/CC3 exhausted; use `ICA_KEY=CC1` (fallback CC5).

---

# BRIEF — Phase P3 (Evidence Planner, 6 pts)

# CARP Phase P3 — Evidence Planner

You are implementing Phase **P3** of the Tier-3 implementation plan
`docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md`
(feature: Catalog-Assisted Research Planning, "CARP").

**Repo root (worktree — work ONLY here):** the active `worktree-carp-c3-catalog-planning` worktree.

Read the plan's "Phase P3" section, then these authoritative, already-frozen inputs
(do NOT re-litigate them):

- `docs/dev/architecture/carp-contract-freeze.md` — the frozen contract (P1)
- `schemas/research_evidence_plan.schema.yaml` — the plan schema (P1)
- `src/research_foundry/services/catalog_retrieval.py` — the governed adapter (P2)
- `tests/unit/test_catalog_retrieval.py` — the adapter's behavior, by example

## Mode

Mode C — bounded implementation. You own **`src/research_foundry/services/research_evidence_planning.py`**
(new) and its tests. **Consume the P2 adapter's DTOs only** — this module must NOT import
`assertion_catalog`, `assertion_reuse`, or touch the ledger. It talks to the adapter, nothing else.
Do not modify `planning.py`, `run_launch.py`, or the search router in this phase.

## CARP-3.1 — Coverage rule implementation

Implement the frozen conservative coverage rule. Exactly one **terminal** state per question:
`covered` | `residual`.

`covered` requires **all six** conditions (verbatim from the freeze doc):

1. ≥1 authorized candidate whose case-folded required terms all appear in the candidate's
   `search_text` (conservative lexical only — **no** semantic/vector/embedding matching, and no
   model call of any kind).
2. Candidate `lifecycle_state == "eligible"` re-read immediately before selection.
3. The adapter's reuse decision is **allow** (`refresh` and `deny` are both residual).
4. All the question's `required_source_types` and `required_qualifiers` are satisfied. A
   constraint the candidate cannot be *shown* to meet ⇒ residual (missing data is never a pass).
5. No contradicting authorized candidate exists for the same question.
6. `assertion_version` pinned exactly at selection time.

Any failure, uncertainty, error, or unrepresentable state ⇒ `residual` carrying exactly one
typed `residual_reason` from the frozen closed enum. `covered` carries `residual_reason: null`.

This function must be **pure and total**: every input maps to a terminal state; it never raises
past the boundary; an internal error becomes `residual` / `evaluation_error`.

## CARP-3.2 — Evidence-plan builder

- Iterate stable `question_id`s in ascending order.
- For each, evaluate a **bounded** candidate set via the P2 adapter, honoring the frozen limits
  (`max_questions` 200, `max_candidates_per_question` 50, `max_pages_per_question` 5). Hitting a
  bound is itself a residual reason (`candidate_limit` / `pagination_limit`) — never a silent
  truncation that reads as "covered".
- Select deterministically: candidates ascending by `assertion_id`; on equivalent hits the lowest
  `assertion_id` wins. Record the tie-break in the receipt so it is auditable.
- Record retrieval receipts and exact decision refs (`assertion_id` + `assertion_version`).
- Write the plan **atomically** (temp file → atomic move) and **schema-valid** against
  `schemas/research_evidence_plan.schema.yaml`.

### Counter-emission trap — read this before you write `summary`

The frozen schema constrains **all six** candidate-derived summary counters to `0`/absent whenever
`catalog_receipt.record_count == 0` — which covers **both** the denied and the catalog-empty
terminal states. Critically, that set includes `questions_residual`.

So a `catalog_empty` plan carrying N residual questions **must omit `summary.questions_residual`**,
not report N. This was verified against the live schema: 3 catalog-empty residual questions with
`summary: {questions_total: 3}` validates; the same plan reporting `questions_residual: 3` is
**rejected**.

This is the intended conservative behavior — a privacy invariant should over-suppress rather than
risk over-exposing — but it is a predictable trap. A builder that naively computes
`questions_residual = len([q for q in questions if q.coverage_state == "residual"])` will emit an
**invalid plan on every catalog-empty and every denied run**.

**Gate all six candidate-derived counters on `record_count > 0` and omit them otherwise.**
`questions_total` stays free — it comes from the request, not the corpus. Add a test covering a
catalog-empty plan that has residual questions, asserting the counters are omitted and the plan
validates.

**Replay invariant (this is the hard one):** the same inputs against the same catalog generation
MUST produce a **byte-equivalent** plan. That means: stable key ordering on serialization, no
wall-clock timestamps or uuids generated inside the builder (any timestamp/plan-id must be an
*injected input*, not ambient), no set-iteration order leaking into output, no `Path.glob` order
dependence. Write a test that builds the plan twice and asserts the bytes are identical.

## CARP-3.3 — H3 fixture matrix

Test every scenario, asserting the exact terminal state **and** the exact residual reason:

exact match · no hit · refresh required · reuse denied · stale projection · conflicting packet ·
missing qualifier · source-type mismatch · multiple equivalent hits · pagination boundary ·
duplicate candidate · catalog generation changed mid-plan.

Plus the byte-equivalent replay test and a schema-validity test for the emitted plan.

Put tests at `tests/unit/test_research_evidence_planning.py`.

## Constraints

- Python 3.9+ idioms; `from __future__ import annotations`; full type hints.
- No network. No model calls. No provider imports. No ambient time/randomness.
- Atomic writes only.
- Match the surrounding code's docstring density and naming idiom.

## Validation (all must pass before you report done)

```bash
export PY=/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/unit/test_research_evidence_planning.py tests/unit/test_catalog_retrieval.py -q -p no:randomly
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/test_schema_validation.py -q -p no:randomly
$PY -m ruff check src/research_foundry tests
$PY -m mypy src/research_foundry/services/research_evidence_planning.py --ignore-missing-imports
git diff --check
```

**Pre-existing baseline failures — do NOT try to fix these:** 16 tests fail on the clean tree.
Your bar is **no NEW failures**.

## Durability

You are on the isolated worktree branch, which you own. Commit as you go with `feat(carp): P3 ...`.
Do NOT push, merge, switch branches, or stash.

## Report

Print a short report: files created/changed, validation output tail, how you guaranteed the
byte-equivalent replay invariant, any deviation from this brief and why, and anything a reviewer
must check.

## Escalation rule

If a fail-closed / no-synthesis constraint would make the feature dead or a path unreachable, that
is an **ESCALATION** — stop and report it as a blocker, do not invent/alias/default a value. Verify
"no such field/signal exists" before claiming it. Report deviations as deviations. Never silently
widen or weaken a governed surface to make your phase pass.

---

# BRIEF — Phase P4 (Retrieval-Then-Discovery Integration, 5 pts)

# CARP Phase P4 — Retrieval-Then-Discovery Integration

You are implementing Phase **P4** of the plan (feature "CARP"). Work ONLY in the active worktree.

Read the plan's "Phase P4" section, then these authoritative, already-frozen inputs
(do NOT re-litigate them):

- `docs/dev/architecture/carp-contract-freeze.md` — the frozen contract (P1)
- `schemas/research_evidence_plan.schema.yaml`, `schemas/search_request.schema.yaml`,
  `schemas/search_run.schema.yaml` (P1)
- `src/research_foundry/services/catalog_retrieval.py` (P2)
- `src/research_foundry/services/research_evidence_planning.py` (P3)

## Mode

Mode C — bounded implementation. You are the **integration owner** for this phase and own edits to:
`src/research_foundry/services/planning.py`, `src/research_foundry/services/run_launch.py`,
`src/research_foundry/services/search_router/modes.py`,
`src/research_foundry/services/search_router/policy.py`,
`src/research_foundry/services/search_router/router.py`.

Do NOT touch the API routers, MCP server, export service, or OpenAPI in this phase — that is P5.

## CARP-4.1 — Operational cache-first

Today `cache_first` (`search_router/modes.py`) has an empty `provider_chain` and a
`max_external_queries: 0` budget, so `run_search` (`search_router/router.py:174`) effectively
does nothing for it. Make it catalog-backed:

- Add a catalog branch to `run_search` that, for `cache_first`, retrieves and evaluates governed
  packets through the **P2 adapter + P3 planner** — never the ledger, never a provider.
- **Zero-provider-call invariant**: for `cache_first`, provider `search`/`extract` call counts
  must be exactly `0`. Prove it with injected provider spies whose `search`/`extract` methods
  **fail the test if invoked at all** (raise/assert, not just count). This is the phase's
  headline invariant.
- Persist governed selected refs + retrieval receipts and the observed metrics block into the
  `search_run` record, per the P1 schema. Metrics must be derived from **actual executed**
  adapter/provider control flow, never precomputed or assumed.
- An empty or denied catalog result is **terminal** for `cache_first` — it must NOT fall through
  to any provider.

## CARP-4.2 — Evidence-aware run planning

- Thread `AuthIdentity` + retrieval policy through `planning.py` and `run_launch.py`.
- **Thread a real `sensitivity_threshold`** from the run/launch context into the adapter's
  `RetrievalConstraints`. P2 made this caller-supplied and never-defaulted: if you don't pass one,
  every candidate fails closed (`sensitivity_denied`) and the whole `allow` path is dead. This is
  the single biggest correctness risk in P4 — get the threshold from the run's own sensitivity
  posture, do not hardcode or default it.
- Persist the evidence plan and reference it from the run.
- Mark brief / swarm / routing questions `covered` or `residual` — every question terminal.
- Selected refs must be **exact** (`assertion_id` + `assertion_version`).
- **Legacy behavior is sacred**: with policy absent or `disabled`, the brief/swarm/routing/provider
  chain must be byte-identical to today. Write a snapshot test proving it.
- **RPC context:** C1 has NOT executed and no RPC schemas exist. Carry the **CARP-owned**
  selection-provenance carrier from the P1 freeze doc. Do **not** author, stub, or invent RPC-owned
  structures. Keep the fields where the freeze doc's "RPC rebase contract" section says they live.

## CARP-4.3 — Residual discovery seam

- In `catalog_then_discovery`, build provider requests for **residual question IDs only**.
- Assert equality, not containment: the set of question IDs sent to providers must **equal**
  the evidence plan's residual set — no extras, no drops.
- Preserve existing budgets and constraints.
- Merge discovery outputs **without** mutating any already-`covered` decision.
- `disabled` preserves the prior question/provider flow exactly. An empty catalog becomes
  residual **only** under explicit `catalog_then_discovery` policy — never implicitly.

## Constraints

- Python 3.9+ idioms; full type hints; `from __future__ import annotations`.
- Additive and backward compatible: no removed/renamed public parameters; new params keyword-only
  with safe defaults that reproduce legacy behavior.
- `planning.py` and `router.py` are declared serialization barriers — you are their sole owner this
  phase. Keep edits surgical and localized.
- Deterministic; atomic writes; no ambient randomness in ordering.

## Tests

Extend/author: `tests/test_search_router_router.py`, `tests/integration/test_run_launch_reuse.py`.
Must cover: provider-spy zero-call proof for `cache_first`; residual-set equality for
`catalog_then_discovery`; `disabled` legacy snapshot; empty-catalog terminal behavior;
covered-decision immutability across a discovery merge; a real sensitivity_threshold producing an
`allow`.

## Validation (all must pass before you report done)

```bash
export PY=/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/test_search_router_foundation.py tests/test_search_router_router.py tests/integration/test_run_launch_reuse.py -q -p no:randomly
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/unit/test_catalog_retrieval.py tests/unit/test_research_evidence_planning.py -q -p no:randomly
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/ -q -p no:randomly 2>&1 | tail -25
$PY -m ruff check src/research_foundry tests
git diff --check
```

Baseline: 16 pre-existing failures. Bar: **no NEW failures**.

## Durability

Commit as you go with `feat(carp): P4 ...`. Do NOT push, merge, switch branches, or stash.

## Report

Files changed; validation tail; exactly how you proved the zero-provider-call invariant, the
residual-set equality, and that a real threshold flows through to an `allow`; deviations; anything
a reviewer must check.

## Escalation rule

If a fail-closed / no-synthesis constraint would make the feature dead or a path unreachable, that
is an **ESCALATION** — stop and report it, do not invent/alias/default. Verify before claiming a
field is absent. Report deviations as deviations. Never silently widen a governed surface.

---

# BRIEF — Phase P5 (API, MCP, Export, Metrics, 4 pts)

# CARP Phase P5 — API, MCP, Export, Metrics

You are implementing Phase **P5** of the plan (feature "CARP"). Work ONLY in the active worktree.

Read the plan's "Phase P5" section, then these authoritative, already-frozen inputs
(do NOT re-litigate them):

- `docs/dev/architecture/carp-contract-freeze.md` (P1)
- `schemas/search_request.schema.yaml`, `schemas/search_run.schema.yaml`,
  `schemas/research_evidence_plan.schema.yaml` (P1)
- `src/research_foundry/services/catalog_retrieval.py` (P2)
- `src/research_foundry/services/research_evidence_planning.py` (P3)
- `src/research_foundry/services/planning.py`, `run_launch.py`, `search_router/router.py` (P4)

## Mode

Mode C — bounded implementation. You own:
`src/research_foundry/api/routers/runs.py`,
`src/research_foundry/services/search_router/mcp_server.py`,
`src/research_foundry/services/export_service.py`,
`src/research_foundry/api/openapi.json` (regenerated, never hand-edited).

Do NOT re-open the P1 contracts or the P2/P3/P4 service internals. This phase propagates the
already-settled shapes through the transport layer.

## CARP-5.1 — Run-launch identity/policy API

- Thread the request's authenticated identity through to the service layer.
- Add **optional** retrieval policy + limits to the run-launch request.
- Return the evidence-plan reference and a **safe** retrieval summary.
- **Legacy request keys must behave exactly as before.** A request with no retrieval fields is
  `disabled` and byte-identical to today. Prove it with a test.
- RBAC/workspace tests must pass. A denied caller gets the frozen denial shape with **zero**
  candidate-derived fields — assert this positively.

## CARP-5.2 — MCP / search contracts

- Add policy/context options to the search tools in `search_router/mcp_server.py`.
- **MCP wrappers stay thin**: no business logic duplication. The wrapper marshals arguments and
  delegates; coverage/selection logic lives in P3/P4 only.
- Preserve the existing offline-safe import behavior — the module must still import without
  network or optional deps present.
- Expose typed run results.

## CARP-5.3 — Export / metrics propagation

- Propagate observed **authorized** retrieval counts and exact evidence-plan refs through the
  search run and `export_service.py`.
- **Denial metrics must contain no candidate signals** — no counts, no facets, no ids. `questions_total`
  (from the request) is the only safe echo.
- Legacy artifacts that omit the additive block must remain readable, with **no placeholder IDs**
  invented to fill gaps. Absence stays absence.

## CARP-5.4 — OpenAPI / type seam

- Regenerate OpenAPI and any generated types **once**, via the repo's existing generation path.
  Find it first (check `package.json` scripts, `scripts/`, and how `api/openapi.json` is produced)
  and use it — do **not** hand-edit `openapi.json`.
- Verify clients tolerate missing optional fields.
- Exercise the service → router → schema seam end to end.
- If the repo has a frontend codegen check (`frontend/runs-viewer`), run it. A bare
  `npx tsc --noEmit` there is a **no-op** — the real gate is `npx tsc -p tsconfig.app.json --noEmit`.

## Constraints

- Python 3.9+ idioms; full type hints. Additive and backward compatible everywhere.
- No hand-edited generated artifacts.

## Validation (all must pass before you report done)

```bash
export PY=/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/api tests/unit -q -p no:randomly 2>&1 | tail -20
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/ -q -p no:randomly 2>&1 | tail -25
$PY -m ruff check src/research_foundry tests
git diff --check
```

Baseline: 16 pre-existing failures (the 5 `test_serve_api` 404s are the known sensitivity-gate
default — do not chase). Bar: **no NEW failures**. (Gate: validator only for P5.)

## Durability

Commit as you go with `feat(carp): P5 ...`. Do NOT push, merge, switch branches, or stash.

## Report

Files changed; which generation command you used for OpenAPI/types; validation tail; deviations;
anything a reviewer must check.

## Escalation rule

If a fail-closed / no-synthesis constraint would make a path unreachable, ESCALATE as a blocker —
do not invent/alias/default. Verify before claiming a field is absent. Report deviations as
deviations. Never silently widen a governed surface.

---

# BRIEF — Phase P6 (Hardening and Documentation, 4 pts)

# CARP Phase P6 — Hardening and Documentation

You are implementing Phase **P6**, the final phase, of the plan (feature "CARP"). Work ONLY in the
active worktree.

Read the plan's "Phase P6" section AND its "Structured Acceptance Criteria" section
(AC CARP-1 … AC CARP-6) — this phase exists to verify those ACs. Also read
`docs/dev/architecture/carp-contract-freeze.md` (the frozen P1 contract).

## Mode

Mode C — bounded implementation, verification-weighted. You are hardening and documenting work
that P1–P5 already landed. Prefer **adding tests** over changing service code. If a gate reveals
a genuine defect, fix it minimally and call it out prominently in your report.

## Verification gates — each maps to a plan AC

Author or extend tests so each of these is positively demonstrated:

- **CARP-6.2 → AC CARP-1 (policy/privacy).** Missing identity · two-workspace isolation ·
  rights denial · disabled capability · denial-metric emptiness. Assert denied responses expose
  **zero** candidate-derived fields.
- **CARP-6.3 → AC CARP-2 (cache-first).** Eligible · empty · denied · stale projection ·
  provider-spy zero-call · zero-budget. The provider spy must **fail the test if invoked at all**.
- **CARP-6.4 → AC CARP-3 (evidence plan).** The full H3 scenario matrix + byte-equivalent replay
  + schema validity.
- **CARP-6.5 → AC CARP-4 (residual discovery).** Residual question-ID set **equals** the provider
  call set (equality, not containment); plus `disabled` and explicit-fallback modes.
- **CARP-6.6 → AC CARP-5 (provenance round-trip).** Round-trip the selected refs and receipts
  through the CARP selection-provenance carrier → search run → plan → launch → export →
  OpenAPI/types. **Note:** the plan's original text says "RPC context", but C1 has NOT executed and
  no RPC schemas exist. Verify the **CARP-owned** carrier defined in the freeze doc instead, and
  confirm the freeze doc's "RPC rebase contract" still accurately names every field that migrates to C1.
- **CARP-6.7 → AC CARP-6 (metrics/legacy).** Authorized observed counts are real (derived from
  executed control flow); denied runs show zeros/absence; pre-feature snapshots are unchanged.

## CARP-6.8 — Documentation and deferred specs

1. **User/dev guide** at `docs/dev/guides/catalog-assisted-research-planning.md`. Cover: what the
   feature does, the three policy states and how to opt in, the coverage rule in plain language,
   residual reasons and what each means operationally, the limits, and the privacy/denial
   guarantees. Match the frontmatter convention of neighboring files in `docs/dev/guides/`.
2. **CHANGELOG.md** entry following `.claude/specs/changelog-spec.md`.
3. **Four `maturity: idea` design specs**, one per deferred item in the plan's Deferred Items
   Triage table — write each at the exact path the table names:
   - `docs/project_plans/design-specs/catalog-planning-semantic-reranking.md` (CARP-DF-1)
   - `docs/project_plans/design-specs/catalog-planning-adaptive-query-decomposition.md` (CARP-DF-2)
   - `docs/project_plans/design-specs/catalog-planning-canonical-claim-coverage.md` (CARP-DF-3)
   - `docs/project_plans/design-specs/catalog-planning-shared-evidence.md` (CARP-DF-4)
   Each records the reason deferred and the promotion trigger from the plan's table.
4. **Populate the plan's frontmatter**: append those four paths to `deferred_items_spec_refs`, and
   add crosslinks. Also ensure the two limitations recorded in freeze-doc §8 (extraction-contract
   advisory; sensitivity axis) are reflected in the guide.

### Documentation honesty constraint (the plan is explicit about this)

Do **NOT** claim reuse rate, quality uplift, cost savings, or "avoided provider calls" as a
realized benefit. No real-corpus measurement exists. Describe **mechanism and guarantees only**.
"Avoided provider calls" may appear as an observed *counter definition*, never as a savings claim.
Also do not claim deployment, release, default-on eligibility, or real-corpus usefulness.

## Validation (all must pass before you report done)

```bash
export PY=/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python
PYTHONPATH=$PWD/src:$PWD/tests $PY -m pytest tests/ -q -p no:randomly 2>&1 | tail -30
$PY -m ruff check src/research_foundry tests
$PY .claude/skills/artifact-tracking/scripts/validate_artifact.py \
  -f docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md --strict
$PY .claude/skills/artifact-tracking/scripts/ac-coverage-report.py \
  --plan docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md --dry
git diff --check
```

(If those scripts are not at that path, locate them — they may live under
`.agents/skills/artifact-tracking/scripts/`. Run whichever exists.)

Baseline: 16 pre-existing failures. Bar: **no NEW failures**.

## Durability

Commit as you go with `feat(carp): P6 ...`. Do NOT push, merge, switch branches, or stash.

## Report

Files created/changed; validation tail; the AC → test mapping (which test file/name verifies each
of AC CARP-1..6); any genuine defect you found and how you fixed it; deviations; anything a reviewer
must re-check.

## Escalation rule

If a fail-closed / no-synthesis constraint would make a path unreachable, ESCALATE as a blocker —
do not invent/alias/default. Verify before claiming a field is absent. Report deviations as
deviations. Never silently widen a governed surface.
