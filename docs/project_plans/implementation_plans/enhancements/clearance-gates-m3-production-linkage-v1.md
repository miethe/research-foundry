---
it_schema: 1
feature_slug: clearance-gates-m3-production-linkage
title: "Clearance-gates M3 production linkage — implementation plan"
doc_type: implementation_plan
status: completed
commit_refs:
  - 83bc76bb2bfbe69a639deb2985bca72225110252
  - 1a1585e61467a3406b58e316a2f337c32d86db62
tier: 2
priority: P1
points: 9
risk_level: medium
context_class: C2
created: 2026-08-05
related_documents:
  - docs/dev/architecture/adr-rights-entity-model.md
acceptance_criteria:
  - "`rf attribution fetch` threads `config` into `fetch()` and handles `ClearedProviderFetchResult`'s shape (no AttributeError on `reason`)."
  - "A writer persists the clearance stamp onto source-card frontmatter as a schema-valid `clearance` block (schemas/clearance_taint.schema.yaml)."
  - "The plan's own end-to-end verification runs for real: posture declared, mocked provider fetched, on-disk card carries blocked_scopes ['redistribution'], posture deleted, mediation still denies."
  - "All 7 committed pediatric bundles still verify (`rf verify`)."
open_questions:
  - "Does the writer live as a new function in services/attribution_fetch/__init__.py (co-located with stamp_taint) or a new services/attribution_write.py module? Decided in M1: co-located, see rationale below."
decisions:
  - decision: "Writer takes a ClearedProviderFetchResult + an existing source_card_id and patches only the `clearance` key onto that card's frontmatter via frontmatter.dump_md, never constructing a full source_attribution record."
    rationale: "The request's AC asks for a schema-valid clearance block on source-card frontmatter, not a new source_attribution entity (that stays out of scope per to_record()'s own docstring: 'a separate, later concern'). Reusing dump_md/load_md keeps the writer inside the existing source-card read/write seam instead of inventing a second one."
    status: accepted
  - decision: "Writer enforces governance rule 9 (no_agent_cleared_clearance_taint) monotonicity in-process before writing: refuses to write if the card already carries a `clearance` block whose blocked_scopes would shrink, and never writes an empty blocked_scopes."
    rationale: "stamp_taint() already refuses malformed scopes; the writer's own extra check is defense-in-depth at the one place clearance state actually lands on disk, matching the ADR's 'guard both write paths' posture (adr-rights-entity-model.md §9.10)."
    status: accepted
routing_constraints:
  - "Clearance-taint write path (writer + governance interaction) MUST stay claude-primary — no offload; this is the exact surface adr-rights-entity-model.md Invariant 1 and governance rule 9 exist to guard."
  - "CLI threading fix (M1) is offload-eligible; mechanical parameter-passing change with existing test coverage as a guardrail."
  - "End-to-end verification test authoring (M2) MUST stay claude-primary — it is the proof artifact for the whole plan; a shortcut here defeats the plan's stated purpose."

wave_plan:
  waves: [["M1"], ["M2", "M3"]]
  phases:
    - id: M1
      title: "rf attribution fetch reaches authorize_live_fetch and handles both result shapes"
      depends_on: []
      exit_criteria:
        - "CLI passes `config=FoundryConfig.load()` into `fetch_fn(...)`."
        - "CLI branches on `isinstance(result, ClearedProviderFetchResult)` vs `ProviderFetchResult` before reading `.reason`; no AttributeError under either shape."
        - "Existing tests/test_attribution_fetch_cli.py suite passes unchanged; a new test proves the dev/test-posture path reaches authorize_live_fetch (e.g. via a monkeypatched config fixture already present in tests/test_attribution_fetch_dev_test_posture.py's `_posture_config`)."
      gate_lens: [validator]
    - id: M2
      title: "Writer persists a schema-valid clearance stamp onto source-card frontmatter"
      depends_on: ["M1"]
      exit_criteria:
        - "New function (e.g. `stamp_source_card` in services/attribution_fetch/__init__.py) writes `clearance` onto an existing source card's frontmatter, validating the resulting block against schemas/clearance_taint.schema.yaml before write."
        - "Writer never mints a CLEARED_*/counsel_approved/attested value anywhere (grep-verified) and is monotone per governance rule 9 (add-only blocked_scopes, no widening)."
        - "Unit tests cover: fresh card gains clearance block; card that already has one only widens; malformed target scope raises before any write (atomic write, no partial frontmatter)."
      gate_lens: [security, validator]
      gate_lens_reason: authz-boundary
    - id: M3
      title: "Real end-to-end verification + pediatric-bundle regression proof"
      depends_on: ["M1"]
      exit_criteria:
        - "New test (e.g. tests/test_attribution_fetch_e2e_stamp.py) declares the dev/test posture via config, calls `rf attribution fetch` (or the underlying fetch()+writer composition directly) against a mocked provider (monkeypatched `_send_request`/`_fetch_json` seam, per existing test convention — no real socket), reads the resulting on-disk source card off `FoundryPaths`, and asserts `clearance.blocked_scopes == ['redistribution']`."
        - "Same test then removes/deletes the posture declaration and re-runs `clearance.mediate_egress` against the now-on-disk record, asserting `ClearanceDenied` is still raised."
        - "`./.venv/bin/python -m pytest` run from the main checkout confirms all 7 committed pediatric bundles still verify via `rf verify` (run from repo root, not a worktree)."
      gate_lens: [validator]

---

# Implementation Plan — Clearance-gates M3 production linkage

The M3 stamping mechanism (`authorize_live_fetch`, `_send_request`, `stamp_taint`,
`ClearedProviderFetchResult`) is correct and heavily unit-tested, but no production code path
reaches it and no writer ever persists a stamp to disk. When this plan lands, `rf attribution
fetch` threads `config` end-to-end, a writer makes the resulting stamp durable on a source card's
frontmatter, and a real (not merely in-process) end-to-end test proves the fetch->stamp->persist->
mediate chain actually holds together on disk.

```json autopilot-graph
{
  "tier": 2,
  "effort_points": 9,
  "wave_count": 2,
  "phase_count": 3,
  "file_count": 5,
  "mode_d": false,
  "mode_d_reasons": [],
  "needs_spike": false,
  "spike_reasons": [],
  "single_pass_feasible": false,
  "plan_artifact_path": "docs/project_plans/implementation_plans/enhancements/clearance-gates-m3-production-linkage-v1.md",
  "execution_target": "execute-plan",
  "slug": "clearance-gates-m3-production-linkage",
  "category": "enhancements",
  "review_intensity": "tier3",
  "files_affected": [
    "src/research_foundry/cli_commands.py",
    "src/research_foundry/services/attribution_fetch/__init__.py",
    "src/research_foundry/services/governance.py",
    "tests/test_attribution_fetch_cli.py",
    "tests/test_attribution_fetch_e2e_stamp.py"
  ],
  "execution_graph": {
    "waves": [
      {
        "id": "wave-1",
        "phases": [
          {
            "id": "phase-1",
            "title": "M1 - rf attribution fetch reaches production authorization",
            "mode": "C",
            "review_intensity": "standard",
            "tasks": [
              {
                "id": "TASK-1.1",
                "prompt": "Mode: C — Autonomous Feature Sprint\nFile: src/research_foundry/cli_commands.py (~line 3350-3430, the `rf attribution fetch` command).\nThread `config` from `FoundryConfig.load()` (already loaded earlier in the function) into `fetch_fn(request_cls(identifier), config=config)`. After the call, branch on `isinstance(result, ClearedProviderFetchResult)`: for that shape, build the JSON/table output from `result.provider`, `result.status`, and a derived reason string (e.g. `f\"fetched (dev/test posture): {result.status}\"`) since `ClearedProviderFetchResult` has no `.reason` field — see `services/attribution_fetch/__init__.py` for its exact shape. For the plain `ProviderFetchResult` shape, keep the existing `.reason`-based rendering unchanged. Import `ClearedProviderFetchResult` from `.services.attribution_fetch` at the top of the branch. Do not change the disabled-path (umbrella flag off) branch above this code. Add a focused test to tests/test_attribution_fetch_cli.py proving the posture-on path renders without AttributeError, using the `_posture_config`-style fixture pattern already in tests/test_attribution_fetch_dev_test_posture.py (mock at the `_send_request`/`_fetch_json` seam — no real socket). Run `./.venv/bin/python -m pytest tests/test_attribution_fetch_cli.py -v` from the main checkout root and confirm all pass. Do NOT git add/commit/push/stash.",
                "assigned_to": "python-backend-engineer",
                "effort": 3,
                "files_affected": [
                  "src/research_foundry/cli_commands.py",
                  "tests/test_attribution_fetch_cli.py"
                ]
              }
            ]
          }
        ]
      },
      {
        "id": "wave-2",
        "phases": [
          {
            "id": "phase-2",
            "title": "M2 - Writer persists a schema-valid clearance stamp",
            "mode": "C",
            "review_intensity": "tier3",
            "tasks": [
              {
                "id": "TASK-2.1",
                "prompt": "Mode: C — Autonomous Feature Sprint\nFile: src/research_foundry/services/attribution_fetch/__init__.py (add a new function, e.g. `stamp_source_card(card_path: Path, result: ClearedProviderFetchResult) -> None`, colocated with `stamp_taint`).\nThe writer must: (1) load the existing source card via `frontmatter.load_md`, (2) take the `clearance` block already produced by `result.clearance` (built by `stamp_taint` at fetch time — do not re-derive or hand-assemble a new taint dict), (3) if the card already carries a `clearance` key, merge `blocked_scopes` as a set union (monotone widen-only — never remove an existing scope, never write an empty set), (4) validate the resulting `clearance` block's shape against schemas/clearance_taint.schema.yaml (use the existing schema-validation helper pattern in src/research_foundry/services/source_cards.py's `_validate`), (5) write back atomically via `frontmatter.dump_md` (temp file + atomic move, per this project's Security Patterns in CLAUDE.md). Read docs/dev/architecture/adr-rights-entity-model.md Invariant 1 and src/research_foundry/services/governance.py lines 787-828 (rule 9, `no_agent_cleared_clearance_taint`) before writing — the writer must never construct a CLEARED_*/counsel_approved/attested value anywhere, and must never widen scope beyond what `result.clearance` already carries. Add unit tests: fresh card gains the clearance block; a card with a pre-existing narrower stamp only widens; a malformed target raises before any write (atomic — no partial frontmatter on disk after a failure). Run `./.venv/bin/python -m pytest tests/test_attribution_fetch_dev_test_posture.py -v` and the new writer tests; all must pass. Do NOT git add/commit/push/stash.",
                "assigned_to": "python-backend-engineer",
                "effort": 4,
                "files_affected": [
                  "src/research_foundry/services/attribution_fetch/__init__.py"
                ]
              }
            ]
          },
          {
            "id": "phase-3",
            "title": "M3 - Real end-to-end verification + pediatric-bundle regression",
            "mode": "C",
            "review_intensity": "standard",
            "tasks": [
              {
                "id": "TASK-3.1",
                "prompt": "Mode: C — Autonomous Feature Sprint\nFile: new tests/test_attribution_fetch_e2e_stamp.py.\nWrite one end-to-end test (mocked provider only — no real network, mock at the `_fetch_json`/`_send_request` seam per the convention in tests/test_attribution_fetch_dev_test_posture.py's `_posture_config` fixture) that: (1) declares the dev/test posture on a `FoundryConfig`, (2) calls the openalex adapter's `fetch()` (or the CLI command from M1, if already landed) against a mocked identifier, (3) passes the resulting `ClearedProviderFetchResult` into M2's writer against a real source card on a `tmp_path`-scoped `FoundryPaths` workspace, (4) reads the card back off disk via `frontmatter.load_md` and asserts `clearance['blocked_scopes'] == ['redistribution']`, (5) deletes/unsets the posture declaration on the config, and (6) re-runs `clearance.mediate_egress` against the now-on-disk record and asserts `ClearanceDenied` is raised. Model this on the in-process precedent `test_stamped_record_stays_denied_after_posture_removed_and_gates_closed` in tests/test_attribution_fetch_dev_test_posture.py, but this version must touch a real file on disk, not just an in-memory dict. Run `./.venv/bin/python -m pytest tests/test_attribution_fetch_e2e_stamp.py -v` and confirm it passes. Then, from the MAIN checkout root (never a worktree — FoundryPaths.discover() silently builds an empty ledger in a worktree), run `rf verify` and confirm all 7 committed pediatric bundles still report verified with no regression. Do NOT git add/commit/push/stash.",
                "assigned_to": "python-backend-engineer",
                "effort": 2,
                "files_affected": [
                  "tests/test_attribution_fetch_e2e_stamp.py"
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "escalation_recommendation": "If M2's writer surfaces additional governance-rule interactions beyond rule 9 (e.g. a second guard needed for a not-yet-anticipated write path), stop and route through /plan:plan-feature for a fresh Tier 2 pass rather than expanding this plan's scope in-flight."
}
```

## Scope boundary

**In:** `src/research_foundry/cli_commands.py` `rf attribution fetch` command; a new
clearance-stamp writer colocated in `services/attribution_fetch/__init__.py`; a new end-to-end
test exercising the full chain against a mocked provider.

**Out (stated, not silently dropped):** DEF-1/DEF-6 (per-provider license/ToS verification) stay
open — this plan does not close them and asserts no license posture for any provider, exactly as
today. Authoring a full `source_attribution` entity (schema `source_attribution.schema.yaml`) from
a fetched value is explicitly out of scope — `ClearedProviderFetchResult.to_record()`'s own
docstring calls that "a separate, later concern," and this plan's writer only persists the
`clearance` taint block onto the source card that already exists, not a new attribution record.
Closing a clearance gate, or minting any `CLEARED_*`/`counsel_approved`/`attested` value, is out of
scope by hard constraint (ADR Invariant 1) and stays a human-only, agent-unreachable act.

## Rubric — what "good" looks like

The chain is judged end-to-end, on disk, not by unit tests of its halves. A reviewer should be
able to run the M3 test, watch a source card gain a `clearance` block with
`blocked_scopes: ["redistribution"]`, delete the posture, and watch `mediate_egress` still refuse
that exact card. Anything that makes that chain "work" only in-memory (e.g. asserting on a
`ClearedProviderFetchResult` object without ever touching a real file on `FoundryPaths`) does not
satisfy this plan's stated purpose, which is specifically about closing the dormancy gap between
two halves that "are joined only in tests."

## Named risks

- **A CLI-level e2e test drifts from the intended provider-adapter seam.** Existing tests mock at
  `_fetch_json`/`_send_request`; the new e2e test must mock at the same seam (never opening a real
  socket) rather than inventing a third mocking convention that could silently diverge from what
  `authorize_live_fetch` actually gates.
- **The writer becomes a second, looser write path into clearance state.** `stamp_taint()` is the
  only function that builds a taint block today; the writer must call it (or validate against its
  exact schema) rather than hand-assembling a `clearance` dict, or it becomes a second surface for
  governance rule 9 to have to separately guard.
- **Threading `config` into `fetch_fn` changes default (disabled-path) behaviour.** Every adapter's
  `fetch()` already treats `config=None` as unconditionally byte-identical to pre-M3 — the CLI fix
  must call `FoundryConfig.load()` and pass it through unconditionally (not only when some flag is
  set), trusting the adapters' own gating rather than re-implementing it at the CLI layer.

## References

- `src/research_foundry/cli_commands.py:3350-3430` (`rf attribution fetch` command)
- `src/research_foundry/services/attribution_fetch/__init__.py` (`ProviderFetchResult`,
  `ClearedProviderFetchResult`, `stamp_taint`, `authorize_live_fetch`, `disabled_result`)
- `src/research_foundry/services/attribution_fetch/openalex.py` (adapter shape to mirror for the
  mocked-provider e2e test)
- `src/research_foundry/services/clearance.py` (`mediate_egress`, `ClearanceDenied`,
  `TAINT_KEY`, `BLOCKING_SCOPES`, `POSTURE_VALUES`)
- `src/research_foundry/services/source_cards.py:245-420` (`ingest_source` — frontmatter shape and
  `dump_md` usage pattern the writer should mirror)
- `src/research_foundry/frontmatter.py` (`load_md`, `dump_md`)
- `src/research_foundry/services/governance.py:787-828` (rule 9,
  `no_agent_cleared_clearance_taint`)
- `schemas/clearance_taint.schema.yaml`, `schemas/source_attribution.schema.yaml`
- `tests/test_attribution_fetch_dev_test_posture.py` (`_posture_config` fixture,
  `test_stamped_record_stays_denied_after_posture_removed_and_gates_closed` — the in-process
  precedent for M3's on-disk equivalent)
- `docs/dev/architecture/adr-rights-entity-model.md` §9.10, Invariant 1

## Milestones

### M1 — `rf attribution fetch` reaches production authorization

The CLI command loads `FoundryConfig` and passes it into every adapter's `fetch()` call, and
branches correctly on which of the two result types it gets back — never touching `.reason` on a
`ClearedProviderFetchResult`.

**AC:** No AttributeError under an active dev/test posture; disabled-path output (JSON and table)
is unchanged for `config=None`/posture-off (regression-proof via existing
`tests/test_attribution_fetch_cli.py`).

### M2 — A writer makes a stamp durable on disk, schema-valid, monotonically

Given a `ClearedProviderFetchResult` and a target source card, a new writer patches that card's
frontmatter with a `clearance` block that validates against `clearance_taint.schema.yaml`, without
ever weakening an existing stamp or minting a rights-clearance value.

**AC:** Round-trip (`load_md` -> write -> `load_md`) shows `clearance.blocked_scopes ==
["redistribution"]`; governance rule 9 continues to pass on the resulting field writes (add
`clearance` writes to the governance-guard test parametrization if one exists, or add a targeted
new test asserting `_is_disallowed_clearance_value` rejects an empty-set write attempt).

### M3 — The chain is proven end-to-end, for real

A single test declares the dev/test posture, fetches from a mocked provider through the real CLI
composition (or the fetch()->writer composition it delegates to), reads the resulting file off
`FoundryPaths`, and confirms both the positive (stamp present, blocked) and negative-after-removal
(posture deleted, still denied) halves — plus a regression pass confirming the 7 committed
pediatric bundles still verify.

**AC:** Test passes with zero real network access; `rf verify` (run from the main checkout root)
reports all 7 pediatric bundles verified, unchanged from before this plan.

## AC -> command -> evidence

| AC | Command | Evidence of pass |
|---|---|---|
| CLI threads config, handles both result shapes | `./.venv/bin/python -m pytest tests/test_attribution_fetch_cli.py -v` | All pass; no AttributeError in a new posture-on test case |
| Writer persists schema-valid clearance stamp | `./.venv/bin/python -m pytest tests/test_attribution_fetch_dev_test_posture.py -k writer -v` (or new test module) | New writer tests pass; frontmatter round-trip shows valid `clearance` block |
| Real e2e chain holds (fetch->stamp->persist->deny-after-removal) | `./.venv/bin/python -m pytest tests/test_attribution_fetch_e2e_stamp.py -v` | On-disk card shows `blocked_scopes: ["redistribution"]`; `ClearanceDenied` raised after posture deletion |
| 7 pediatric bundles still verify | `rf verify` (from repo root, not a worktree) | Verification report lists all 7 bundles as verified, no regression |

## Execution ledger

Deviations and conservative choices are logged with rationale to
`.claude/worknotes/clearance-gates-m3-production-linkage/implementation-notes.md` and reviewed at
each milestone boundary — rather than halting on them.

**Blockers still stop** (work that cannot correctly proceed: a failing test on current work, an
unsatisfiable declared artifact, exhausted recovery). Beyond those, mid-milestone halts are only
for: destructive action, real scope change, or input only the operator has.

**Mode-D boundaries are unchanged and non-negotiable** — these always halt for explicit human
approval, whatever this plan says: **auth · payments/billing · schema migrations · data deletion ·
secret rotation · infrastructure**. This plan does not touch any of those, but M2's write path sits
adjacent to the rights-governance boundary (ADR Invariant 1) — it is proven `security`-gated (M2's
`gate_lens`) precisely because it is an authz-adjacent boundary, not because it crosses into
Mode-D territory.

## Residual gap at landing (2026-08-05) — READ BEFORE CLOSING THE PARENT FINDING

All four acceptance criteria above are met as worded, and the full suite shows zero regressions
(9 pre-existing failures, byte-identical to `main` at `4c136d5`; 5538 passed; 7/7 pediatric
bundles verify). **One link of the chain is still not reachable from production**, and this plan's
own wording is how it survived.

`stamp_source_card` has **zero production callers**. Every occurrence under `src/` is its own
definition, docstring, or error string; the only invocations anywhere are
`tests/test_attribution_fetch_clearance_stamp_writer.py` and
`tests/test_attribution_fetch_e2e_stamp.py`. So the chain moved from

    fetch -> stamp -> [no link] -> persist          (before)
    fetch OK -> stamp OK -> [still no link] -> persist(writer exists, unreachable)   (after)

M3's exit criterion permits calling *"`rf attribution fetch` **or the underlying fetch()+writer
composition directly**"*. The e2e test took the second option, which is legitimate against this
plan but leaves the composition asserted only by a test that performs it itself. This is the parent
finding's own warning realised one altitude down: *"the implementer said the CLI doesn't thread
config" and "the milestone has no reachable entry point" are the same fact stated at different
altitudes.*

**Why it was not closed here rather than being an oversight.** `rf attribution fetch <provider>
<identifier>` has no source card in scope to stamp, so wiring the last hop is a design decision,
not a parameter pass — either a `--card`/`--source-card-id` option on that command, or a call from
the source-card ingest/export path (`export_service.py` ~:741, whose comment admits no writer puts
`clearance:` on frontmatter). Either choice makes an agent-invocable surface write governance state
to disk, which is exactly the rights-clearance boundary this plan's own `routing_constraints`
declare must stay claude-primary. It needs explicit operator sign-off, not an autopilot default.

Consequence for tracking: the parent IntentTree finding
(`node_01KZ9WKCPA8RBG3722QN3KH3S6`) stays **open**. Do not mark it resolved on the strength of this
plan's `completed` status.

### Operator decision, 2026-08-06 — deferral accepted and made safe (`1a1585e`)

The gap above was put to the operator as three options: (A) add `--card`/`--source-card-id` to
`rf attribution fetch` so it calls the writer, (B) build the attribution-value -> source-card merge
path and stamp inseparably as part of that write, or (C) accept "mechanism ready, no caller yet" and
make the deferral safe by documentation plus a guard.

**Chosen: C now, B later.** The reasoning that decided it: the `clearance` block is a *taint*
meaning "this record carries provider-derived data whose redistribution rights (DEF-1/DEF-6) are not
cleared." Nothing puts provider data on a card yet — `ClearedProviderFetchResult.value` has no
consumer anywhere in `src/` and `to_record()` has zero callers, exactly as its docstring defers.
Option A would therefore stamp a taint onto a card carrying no provider data: over-blocking (the safe
direction) but asserting something untrue, and the card's export would then deny for a reason not
visible on the card. On a rights-clearance surface a false assertion is worse than an absent one.
Note also that A made semantically honest simply *becomes* B.

Landed for C in `1a1585e`:

- **ADR Invariant 4** (`docs/dev/architecture/adr-rights-entity-model.md`, "Single Clearance-Taint
  Write Path") — `stamp_source_card` is the single sanctioned mechanism for persisting a taint onto a
  card; records its type gate, fail-closed schema validation, monotone widen-only merge, the
  intentional no-caller state, and that `export_service.py`'s `_stamped_clearance_candidates`
  mediation is already armed for the moment a writer runs.
- **`tests/test_clearance_stamp_single_write_path.py`** — an AST guard (no `rg`/`grep` subprocess)
  asserting only an explicit, reasoned allowlist of modules writes the taint key: the sanctioned
  writer, plus `export_service.py`'s non-persisting outward projection. Detection is purely key-based
  and indifferent to the subscripted base expression's name or shape, and two non-vacuity pins
  ensure the guard cannot rot into a no-op (the sanctioned write must still be *detected*, and
  export_service's site must still be detected-then-allowlisted rather than merely unseen).

B is filed as IntentTree `node_01KZCB1SQ5DKW965J202PW7JSC`, with a `depends_on` edge from this
finding. Its constraint: route the merge's write **through** `stamp_source_card` — do not add a
second taint write path, or Invariant 4's guard will fail by design.
