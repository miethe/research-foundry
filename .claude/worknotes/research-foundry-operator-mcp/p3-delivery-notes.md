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
| `node_01KYTDY3WA8TK23PDNCAGP8S89` | Background-job worktree guard spuriously blocks *subagent* Edit/Write when cwd already IS the worktree; `EnterWorktree` cannot satisfy it; agents route around it with a Bash patcher | ITT `agentic_meta_dev` |
| `node_01KYTDXMJ21ZZBWKAR6RMNFGWC` | 8 remaining module-level `..api.auth.*` imports in `services/` break the serve-extra boundary (latent P5 blockers) | ITT `research-foundry` |
| `node_01KYTDXMYQXGTJJP9KG0325RV2` | P3-F3 — no public reader to recover canonical effect refs on exact replay | ITT `research-foundry` |
| `node_01KYTDXN8R957GFF3CQGRVPRKJ` | K3-NB-5 — nothing binds `action_id` to `action_index` at receipt-write time | ITT `research-foundry` |

## Wave 0 result — landed `70c8a6f`

| Task | Outcome |
|---|---|
| OPM-3.1 | Adapter substrate + `run.plan` adapter. 16 tests, 5-guard mutation matrix. |
| OPM-3.2 | `swarm_service.py` extracted from the Typer body; allowlist, dry-run, typed adapter errors, byte-for-byte CLI parity. 8 tests, 4-guard matrix. |
| NB-D | Four receipt writers now require a real `AuthIdentity`; `workspace_id: str` removed entirely and `identity=None` made *unrepresentable* (no default + isinstance guard) rather than documented. 9-guard matrix. |

Orchestrator-run validation (not agent-reported): 10 operator suites `exit 0`, 393 tests, 0 F / 0 E.
Full suite with the two known-uncollectable files ignored → **16 distinct FAILED nodes, zero
operator/adapter/swarm nodes** — exactly P2's documented pre-P2 baseline, so Wave 0 introduced no
regressions.

**A judgment call worth recording:** the NB-D leg made `identity=None` unrepresentable for writes
while *keeping* it a permitted default on the module's three read methods. That asymmetry is
deliberate and correct — a write has no safe "no scoping" default — and it was stated rather than
slipped in. It is also the shape the ledger asked for.

**K3-NB-5 was left explicitly open rather than half-closed**, with a stated reason: a real check needs
an authoritative persisted per-index action manifest that does not exist in this module family, so
any check writable today would validate against non-authoritative data. That is the right call and the
opposite of the "assert closure" failure mode that produced P1 gate rounds 4 and 5.

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

## Mid-phase events that changed P3's scope

### P2 closed *during* P3, and its commits landed on this branch on top of Wave 0

`9df464b` ("close K4-BLOCK-1 + record P2 rounds 4-5 (both gates APPROVED)") and `5a13848` ("P2 phase
closed") were committed to `worktree-operator-mcp-v1` **after** P3's Wave-0 commit `70c8a6f`. This is
the first honest gate close in this workstream — P1 was closed by owner acceptance over a
`CHANGES_REQUESTED` verdict; P2 has two genuinely APPROVED gates.

Handled, not merely noticed:
- Verified the commits were **targeted** (5 files), not a `git add -A` sweep, so no in-flight P3 work
  was captured into someone else's commit.
- They modified `operator_cancel_resume_service.py` and `operator_operation_service.py` — both
  underneath live P3 legs. Re-ran OPM-3.3's full surface against the merged tree (green) and messaged
  the in-flight leg to re-read both files rather than build on its launch-time snapshot.

**Standing hazard**: two agents committing to one worktree concurrently. It was benign this time
because both committers scoped their `git add`. It would not be benign with `git add -A`.

### K4-NB-1 became a new P3 obligation (High)

P2's close explicitly assigns it here, with the instruction that it "must not be re-deferred as
'adjacent' a third time". `operator_receipt_service.py` has **zero** `OperationalError` handlers
across all **seven** `_ensure_schema` sites; three methods (`load_terminal_receipt`,
`load_checkpoint`, `resolve_resume_point`) leak a raw `sqlite3.OperationalError: database is locked`
to callers, reachable from the same two governed APIs K4-BLOCK-1 was about.

The ledger's own durable lesson is the actual instruction: K3-BLOCK-1, K4-BLOCK-1 and K4-NB-1 are
**one defect** — an unguarded `_ensure_schema` on a shared SQLite file — and each round closed the
instance in front of it while the sweep found the next, at a cost of one full adversarial round per
instance. Dispatched with: enumerate every occurrence of the *pattern* and fix as a set; inventory
(don't fix) the sibling modules; don't fold "store unavailable" into a `KeyError`/not-found contract
(a transient lock reported as "does not exist" is worse than the raw leak); don't over-broaden the
`except` (`K3-NB-6`); and exercise the **cold-start** path, because a warm schema makes a contention
test pass for free.

### Orchestrator error, corrected: P3-F2's closure was deeper than reported

I traced the serve-extra leak as `planning.py:47 → assertion_catalog.py:45 → api/__init__.py:21` and
scoped the fix to that one file, telling the leg the other eight `..api.auth.*` imports were out of
scope. That was wrong: the chain is one file deep only **at the first failure point**. Fixing
`assertion_catalog` reveals `catalog_retrieval.py:24` behind it, and `planning` still won't import
clean. This is the same "fix the layer below" class the plan's own checklist names as item 2 — the
tracer stops at the first raise, and the first raise is not the boundary.

Scope corrected in flight: fix **every** module in `planning`'s import closure, iterating until it
imports clean under a blocked-fastapi harness. Noted here rather than quietly amended because the
mis-scoping, not the fix, is the transferable lesson.

## Cross-model lane

`gpt-5.6-terra` probed and confirmed working in this repo (`codex exec --sandbox read-only`, prompt
via **stdin** — the argument form hangs waiting on stdin). Reserved for (a) AC cross-validation and
(b) fix runs if a Claude leg stalls or a gate returns red.

The P1-era trap "do not use Codex here" is **narrower than it reads**: what Codex refused was the
*adversarial security-audit* framing, under its own safety classifier, after burning a long reasoning
trace. Concrete "validate these acceptance criteria" and "fix this named defect" framings are a
different ask and work fine. Recorded so the next phase doesn't over-generalize the trap into "Codex
is unusable on this codebase".

## Cross-model result: two codex runs, same repo, same model, opposite outcomes

Both were `codex exec --model gpt-5.6-terra --sandbox workspace-write`, prompt via stdin, same
worktree, minutes apart.

| Run | Shape | Outcome |
|---|---|---|
| Registry test-isolation fix | ~60 lines, 2 files, **one concrete defect** | **Excellent.** 38.9k tokens, exit 0, fixed the *root cause* — an autouse whole-registry snapshot/restore fixture — rather than the two red assertions, and explicitly declined the tempting shortcut of swapping in another concrete operation kind, which would have re-armed the trap for P4/P5. Verified by me in both orderings. |
| sqlite guard completion sweep | ~110 lines, 4 files, **enumerate-a-pattern + a propagation sub-task** | **Derailed.** Pulled in the repo's own artifact-tracking / CLAUDE.md skill documentation, then looped trying to spawn full-history forked subagents (`ERROR codex_core::tools::router: Full-history forked agents inherit the parent agent type`), ended in a `collab: Wait` loop, and **exited 0 having made zero edits** — clean tree, unchanged guard counts. |

Two transferable lessons:

1. **`codex exec` exit 0 is not a completion signal.** It exited 0 with an empty diff. Verify on disk,
   always. (Same family as the "agent self-reported transcript is not evidence" rule this ledger
   already carries — a *third* variant of it.)
2. **The failure correlated with prompt shape, not with the model or the codebase.** Single-concern,
   short prompt → excellent root-cause work. Multi-concern sweep prompt → skill-doc loading and
   subagent forking instead of the task. The right response is to split codex fix runs into
   single-concern prompts, **not** to conclude "codex doesn't work here" — which is exactly the
   over-generalization the P1 trap note already invites.

Captured as ITT `node_01KYTGKRK7RW3NNDM1DFSW7DWW`. Fallback was a Claude implementer, chosen because
it had already completed an identical task shape (the K4-NB-1 seven-site sweep) successfully.

## Gate findings — what the two cheap lenses caught after every leg reported done

Every one of these landed on a tree where the implementing agent had reported success **with its own
mutation matrix**, and where my independent re-run of the suites was green. That is the headline
number for the AAR: **five defects survived implementation + self-verification + orchestrator
re-validation**, and were caught by two review passes costing a fraction of a full gate.

| # | Lens | Defect | Class |
|---|---|---|---|
| G1 | gpt-5.6 | `run.plan` exact replay loses canonical refs → AC-1 only PARTIAL | known (P3-F3), confirmed |
| G2 | gpt-5.6 | **CLI dry-run conceals service-level denials** | fail-open signal, layer-above |
| G3 | gpt-5.6 | Adapter exception text returned **unbounded and unredacted** | NEW-21 class, AC OPM-7 |
| G4 | gpt-5.6 | `job.status` does an **unbounded internal attempt-list read** behind a bounded response | AC OPM-3.4 |
| G5 | ICA | **Attempt cap is a read-then-write** — concurrent `create_attempt` can exceed it | DUR-1 class |
| G6 | ICA | `job_lifecycle`'s blanket `except Exception` collapses transient store-unavailable into permanent `not_found` | layer-below |

### G2 is the orchestrator's own defect, and worth naming as such

I found P3-F1 (the service returning no denial on dry-run), specified the fix, verified the fix, and
**never checked the caller**. `cli_commands.py` returns on `result.dry_run` before the loop that
prints denials, so the CLI still shows "would run: <disallowed-adapter>". The service is hardened and
its caller still presents the unsafe answer — checklist item 2 applied to my own remediation. I had
flagged that exact pattern twice in others' work the same session before reproducing it.

### G6 undoes, one layer up, the contract the whole sqlite sweep exists to establish

Four bounded `*StoreUnavailableError` types were added across three commits, each justified in its own
docstring by "a transient lock must never be reported as permanent absence". `job_lifecycle`'s
`except Exception: return None` then swallowed `OperationStoreUnavailableError` identically to a
genuine miss. Fails closed, so not a privilege bug — a **retry-contract** bug that made the sweep
partially decorative at the adapter boundary.

### The fix for G6 introduced its own residual — caught on review, not by its tests

Narrowing `except Exception` → `except KeyError` closed the retry-contract bug and opened a raw-leak
bug: the wrapper caught only `OperationStoreUnavailableError`, and it runs *before* every `invoke_*`'s
own `try`, so a third exception type escaped raw out of a public adapter surface. Reachable, not
theoretical: `OperationRecord.from_manifest` does bare `manifest["operation_id"]` subscripting, so a
manifest deserializing to a non-Mapping raises **`TypeError`**, not `KeyError` — the K4-NB-3 corrupt-
manifest path. Closed with a bounded catch-all at `retryable=False`, deliberately distinct from the
store-unavailable `retryable=True`; collapsing them would have undone the distinction the fix existed
to create. Three envelopes are now pairwise distinct and tested as such.

### The transferable pattern

**Three separate times this phase, a fix needed its own layer-below check** — the serve-extra closure
(one file named, three actually in the closure), P3-F1 (service fixed, CLI missed), and G6 (retry
contract fixed, raw leak opened). On this codebase the checklist's item 2 is not a formality; it is
where most of the remaining defects live, and it applies to *remediations* at least as much as to
original code. The cheap pre-gate is worth its cost precisely because it re-attacks fixes, not just
features.

## Timeline

- **2026-07-30** — P3 opened. Baseline captured, surface mapped, implementer contract written,
  Wave 0 dispatched (3 legs). OPM-3.2 (ICA) returned and was independently verified; one real
  finding (P3-F1) raised against it.
