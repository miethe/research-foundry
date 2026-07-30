# P3 Delivery Notes — Run Planning and Swarm Adapters

Working notes for the end-of-plan delivery report and the AAR. Appended as execution proceeds;
**not** a completion claim. Started 2026-07-30 on branch `worktree-operator-mcp-v1` @ `4e3e62f`.

## Entry state

| Item | State at P3 start |
|---|---|
| Branch head | `4e3e62f` — "fix(operator-mcp): close K3-BLOCK-1 + K3-NB-1..4 from the round-3 Karen gate" |
| P1 gate `OPM-1.G` | CLOSED by **owner acceptance** 2026-07-29, not by a machine APPROVE. Last machine verdict was `CHANGES_REQUESTED` (R5); the round-6 re-gate was deferred (`OPM-DF-regate`). |
| P2 gate | Finalizing. Owner authorized starting P3 without waiting. |
| Test baseline | All 7 operator suites green: `REALEXIT=0`, 376 dots, 0 F, 0 E (established before first edit). |
| Pre-existing red (do not chase) | `test_verification_pediatric_cds.py`, `test_verification_seam001_gate_composition.py` fail to *collect* under `-k` filtering. Present on base `65d658d`. |

## Scope actually taken

Plan tasks OPM-3.1 … OPM-3.4, **plus** two carried P2 obligations the ledger explicitly assigns to
this phase:

- **NB-D / REGATE-NB-4** — the four receipt writers authorize on a caller-supplied `workspace_id`
  string while the three reads already take an `AuthIdentity`. (`findings:2158`)
- **P2S-NB-9** — AC OPM-3's "bounded attempts" is unimplemented; scheduled at `OPM-3.4`. (`findings:1549`)

Adjacent and explicitly *not* silently absorbed: **K3-NB-5** (nothing binds `action_id` to
`action_index`, so an in-workspace caller writing the next contiguous index out of turn silently
skips the real action). Delegated as "close it if the NB-D change makes it cheap, otherwise leave it
and say why" — a deliberate refusal to half-close.

## Architecture finding that reshaped the phase (decision D1)

The plan's P3 rows all read as "wrap X in an adapter", which implies an adapter layer exists. **It
does not.** Exploration confirmed there is no Operator MCP tool-registration or dispatch module at
all — `grep -rln "operator_mcp" src/research_foundry --include="*.py"` returns only `config.py`,
`auth_identity.py`, and the `services/operator_*` modules. Knowledge MCP has a `registry.py` with
`build_server()`; Operator MCP has no analogue, and building one is P5's job.

So P3 is not four parallel wrapping tasks — it is **one seam plus three consumers**. Consequence for
execution: the progress file's `batch_1: [OPM-3.1, OPM-3.4]` was **not** run as written. Running the
seam-definer and a consumer concurrently would have let each invent its own adapter shape, which is
the precise mechanism behind this plan's recurring defect classes. Restructured to:

| Wave | Legs | Rationale |
|---|---|---|
| 0 | OPM-3.1 (seam + `run.plan`) ∥ NB-D (receipt identity) ∥ OPM-3.2 (swarm extraction) | Disjoint file ownership; the seam and the security-shape change both land before consumers build on them |
| 1 | OPM-3.3, OPM-3.4 (+P2S-NB-9) | Both consume the Wave-0 seam |

The substrate's invariants were **specified by the orchestrator, not left to the leaf** — identity
derived structurally, fixed authorize-before-lookup pipeline order, all errors through `build_error`,
dry-run proven zero-effect by spy, no fail-open on unknown kind/adapter/workspace/sensitivity, no
CLI/Typer/subprocess, imports clean without the `[serve]` extra.

## Routing decisions (via `delegation-router`)

| Leg | Class | Resolved | Why |
|---|---|---|---|
| OPM-3.1 seam, NB-D | `implementation` | claude / `sonnet-5` | Security-shape work on the exact surfaces where every P1/P2 defect landed |
| OPM-3.2 extraction | `implementation` | **ica** / `claude-sonnet-5[1m]` | Genuinely mechanical CLI→service extraction; the free-tier offload the owner asked for |
| Pre-gate sweep | `code_review` | claude / `sonnet-5` | ~30k fail-open/layer-below sweep before any expensive lens (plan §"Cheap pre-gate") |
| AC second opinion | `second_opinion` | codex / `gpt-5.6-terra` | Cross-family lens, framed as **AC validation, not adversarial security audit** |
| Final gate | `verdict` | claude / `opus-5` | MUST-stay-primary; router rejects non-claude |

**Deliberate deviation from a blanket "ICA for all leaf nodes".** ICA was used for the one leg that
is genuinely mechanical and withheld from the three that carry authorization/identity/bounded-effect
semantics. Rationale: P3's gate is validator-only, and the P1 record shows the validator *approved a
critical authorization-bypass bug twice*. Pairing the weakest lens with a weaker implementer on the
security-shaped legs is the one combination this plan's own retro argues against. Stated here rather
than silently applied.

**Codex is used for AC validation only.** Per the P1 traps, `codex exec` **refused** the adversarial
security-audit framing on this codebase under its own safety classifier after burning a long
reasoning trace — a policy refusal on their side, not a config problem. Framing matters.

## Process controls carried into every leg

Written once into `.claude/worknotes/research-foundry-operator-mcp/p3-implementer-contract.md` and
referenced by path from each dispatch, rather than restated per prompt.

1. The plan's four-item **defect-class checklist**, verbatim (fail-open / layer-below / never-pin-
   unsafe-behavior / never-fabricate-a-transcript).
2. **Mutation verification inside the implementer's own step** — the highest-leverage item from the
   P2 retro. Rounds 4 and 5 of the P1 gate exist almost entirely because closure was *asserted*
   rather than demonstrated: a correct fix shipped with four purpose-built tests, all four of which
   **passed on revert**. Contract requires revert → named test must fail → restore → record.
3. The **`__pycache__` false-green trap**, with the purge + `PYTHONDONTWRITEBYTECODE=1` recipe on
   *every* iteration, plus the non-redundancy cross-check (two guards must each fail only their own test).
4. The **pytest pythonpath trap** — `pyproject.toml` sets `pythonpath = ["src"]`, which pytest inserts
   ahead of the `PYTHONPATH` env var, so a `PYTHONPATH=$PWD/src` prefix is decorative and is not
   evidence of an isolated run.
5. Exit-code discipline: this repo suppresses the "N passed" line, and `FAILED` rows carry ANSI, so
   `grep "^FAILED"` returns zero hits on a red suite.
6. **Single committer** — implementers never touch git.

## Open items / follow-ups captured

| ID | Item | Where |
|---|---|---|
| `node_01KYTBQ3D44CYEYFXZYP8KWJT2` | delegation-router: ICA `sonnet` alias still resolves to `claude-sonnet-4-5[1m]` though `claude-sonnet-5[1m]` exists in the same registry — silently downgrades ICA offloads | ITT `agentic_meta_dev` |
| `node_01KYTBRTK0BT9ETQS0W8TE2BAV` | delegation-router SKILL.md "Key References" all point at a `skillmeat/.claude/skills/delegation-router/` directory that does not exist | ITT `agentic_meta_dev` |

## P3 findings raised during execution

### P3-F1 — `swarm_service.run_swarm` dry-run short-circuits *before* the allowlist/registry checks (OPM-3.2)

`src/research_foundry/services/swarm_service.py:131-140` returns immediately on `dry_run=True`,
ahead of the `unknown_adapter` / `adapter_not_allowlisted` branches at `:144-163`. So
`run_swarm(run_id, ["anything-at-all"], dry_run=True)` returns `outcomes=()` — **no denial** — for
an adapter id that a real run would refuse.

Both acceptance criteria are *literally* satisfied ("dry-run has zero effects" holds; "unknown/
disallowed adapters deny" holds on the wet path), which is exactly why it survived the leg's own
mutation matrix — the dry-run guard and the denial guards were each verified against their own test
and neither test covers the *intersection*.

It is not an effect leak: zero effects occur either way. It is a **fail-open signal**, defect class 1's
shape. It matters because dry-run is the natural preflight for an operator MCP tool surface, and a
preflight that reports "no objection" for a disallowed adapter will mislead a caller into believing
the adapter is permitted. Under a strict reading it also fails the AC on the dry-run path.

**Fix**: validate first, populate `outcomes` with the denials, *then* short-circuit before any
`adapter.run()` or `dump_yaml`. Dry-run must still perform zero effects **and** must still deny.
**Requires a new test for the intersection** (`dry_run=True` + disallowed id → denial recorded, spy
proves zero dispatch and zero write). Assigned to the consolidated fix wave.

### P3-F2 — `assertion_catalog.py` breaks the serve-extra import boundary for the whole `planning` closure

Raised by the OPM-3.1 leg as "out of my ownership, worked around, not fixed" — correctly, and it is
a real defect, independently reproduced.

Exact chain, traced with a `sys.meta_path` blocker carrying a control assertion:

```
research_foundry/services/planning.py:47
  -> research_foundry/services/assertion_catalog.py:45   from ..api.auth.provider import AuthIdentity
     -> research_foundry/api/__init__.py:21              raises "fastapi and uvicorn are required"
```

`operator_mcp_adapters` and `operator_mcp_adapters.run_plan` both import **clean**; `planning` and
`assertion_catalog` both **leak**. So the `run.plan` adapter — OPM-3.1's actual deliverable — cannot
execute in a base install, which is precisely the local-stdio topology P5 declares. This is the same
defect class as P1 blocking finding **NEW-23** ("serve-extra import boundary claim is false") and as
**KMCP-F1**; the `deff14f` fix closed the `rf` CLI path but left the service-level imports standing.

**Fix is one line and is a true fix, not a guard:** import `AuthIdentity` from `..auth_identity` —
the canonical, deliberately import-clean module that `api/auth/provider.py` re-exports *the same
class object* from. No `TYPE_CHECKING` dance needed, and it keeps working at runtime.

**Wider sweep (reported, not fixed here — out of P3 scope):** nine module-level `..api.auth.*`
imports remain across `services/`, in `research_evidence_planning.py:122`, `verification.py:32`,
`catalog_service.py:65-66`, `catalog_retrieval.py:24`, `assertion_impact.py:25`,
`knowledge_access.py:138-139`, `builder_service.py:49-50`, and `assertion_catalog.py:45`. Only the
last is on P3's import path. The rest belong to their owning phases/plans and are captured as a
follow-up rather than silently swept into this phase.

### P3-F3 — no public reader to recover canonical effect refs on exact replay (reported by OPM-3.1, not fixed)

On a genuine exact-replay of an already-terminal `run.plan` operation, the adapter cannot reconstruct
the four canonical ids from durable operator-layer state: `OperatorReceiptService` exposes no public
reader for a persisted `effect_ref` keyed by `operation_id`/`action_id` — `load_terminal_receipt`
returns content digests, and `load_checkpoint` does not carry it. The adapter returns an honest,
bounded partial payload (`canonical_refs_available: False`) rather than fabricating refs, which is
the right call. Needs a public effect-receipt reader; bears on AC OPM-3's exact-replay clause.

## Verification the orchestrator performed independently (not accepted from agent self-report)

| Claim | How checked | Result |
|---|---|---|
| OPM-3.2 suite green | Re-ran `tests/unit/test_swarm_service.py` myself, caches purged | `REALEXIT=0`, 8 dots, 0 FAILED |
| No CLI/Typer/subprocess in the service | `grep` over the import block | clean |
| Imports without the `[serve]` extra | `sys.meta_path` blocker **with a control assertion** | PASS |
| flake8 `E9,F63,F7,F82` | ran directly | `FLAKE8EXIT=0` |

**Process note (soft finding).** The ICA leg's transcript quoted `.venv/bin/python -m pytest` — a
relative path, and **there is no `.venv` in this worktree**. Either it ran from the main checkout
(which would be the pythonpath-trap failure mode: testing main's source, not the worktree's) or it
tidied the command when writing up. The result reproduces under the correct interpreter from the
worktree, so the substance stands — but the transcript as written could not have produced it. This is
the third variant of "an agent's self-reported test output is not evidence" this plan has recorded.
Re-running each leg's suite myself is what surfaced it, and stays mandatory.

## Timeline

- **2026-07-30** — P3 opened. Baseline captured, surface mapped, implementer contract written,
  Wave 0 dispatched (3 legs). OPM-3.2 (ICA) returned and was independently verified; one real
  finding (P3-F1) raised against it.
