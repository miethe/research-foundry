# Execution Doctrine (Claude-5 generation)

> The execution half of the Claude-5-generation doctrine. Authoring half:
> `.claude/skills/planning/references/plan-doctrine.md`. Long form + evidence:
> `docs/project_plans/design-specs/claude5-plan-doctrine-v1.md`.
>
> Applies to runs of **new** doctrine plans. In-flight plans finish under their own rules.

## Why this exists

Gate loops replayed the full plan-plus-diff context up to five times on a single phase before a
human made a re-scope call the plan structure had prevented the executor from making. Retries,
not implementation, were the dominant cost: measured ~1000:1 in:out ratios concentrated in fix
loops, and 186-489% context utilization in single sessions. The levers are **how often gates
fire, how much context each one carries, and whether a fix re-ingests everything**.

## The four execution rules

**1. Gate budget: 2 re-passes, then re-scope.** Any adversarial or validator gate on the **same
scope** gets at most two re-passes. The third failure does not escalate to "a human looks at it";
it **auto-escalates to re-scope/redesign**. Three failures against the same lens is evidence the
scope is wrong, not that the fix was sloppy — the five-pass path was measured as strictly worse
on every axis. Count re-passes per *scope x lens*, not per dispatch: re-spawning an executor does
not reset the budget.

> **Enforcement is uneven — know which path you are on.** The scripted workflow path enforces this
> mechanically (`fixLoop` hard-caps at 2 cycles and returns `needs_rescope` /
> `gate_budget_exhausted`). The manual orchestrated path has **no counter**: there the budget is a
> rule the orchestrator follows, not a mechanism that stops it. Count the re-passes yourself.

**2. Delta context, not the full stack.** A gate dispatch carries the **delta**: the failure
summary, the touched files, and the AC actually in question. It does not carry the full plan, the
cumulative diff, or the progress file. A reviewer that needs the whole plan to judge one AC is a
signal the AC is under-specified — fix the AC, do not widen the packet.

**3. Continue; don't re-dispatch. Reserve fresh context for verification.** Fix loops should reuse
the existing agent session: it is cache-warm and already holds the context the fix depends on. A
fresh re-dispatch re-ingests everything to relearn what the previous session already knew.
Fresh context belongs on the **verifier** — a fresh-context verifier outperforms self-critique,
and inherited-context validators rubber-stamp. Today's default is exactly inverted: implementers
get re-spawned and validators inherit stale context. Invert it.

> **Where this is real today, and where it isn't.** The Tier 1 sprint path genuinely continues one
> session (`feature-sprint-executor` holds context across its fix cycles), and the manual
> phase-owner loop preserves the session and its branch rather than deleting and re-spawning.
> The **scripted workflow path cannot yet**: the documented primitive set (`agent`, `parallel`,
> `pipeline`, …) has no session-continuation call, so `fixLoop` issues a fresh `agent()` dispatch.
> That is a known gap, not a described capability — see `orchestration/workflow-patterns.md`.
> Prefer the paths that can continue; do not claim the scripted one does.

**4. Context tripwire at 150%.** Above 150% context utilization in one session, split or
summarize-forward **before continuing** — it is not a post-hoc AAR observation, it is a live
execution signal. Carrying on past the tripwire is how a fix loop becomes a retry storm.

## Implementation notes over halt-and-gate

Executors **log and keep going**. A deviation — a conservative choice, an assumption, a
discovered constraint — goes into the run's implementation-notes file with its rationale, and is
reviewed at the **milestone boundary**.

The distinction is **deviation vs blocker**, not "how bad does it feel". A deviation is a choice
you made and could defend — log it and continue. A blocker is work that cannot correctly proceed.
Blockers still stop, and always did: a failing test on the current work, an unsatisfiable declared
artifact, an exhausted recovery path. Those are not exceptions to this rule; they are simply not
deviations.

Beyond blockers, mid-milestone halts are reserved for three cases:

1. a **destructive** action (deletion, force-push, migration, secret rotation),
2. a **real scope change** (the work is not what the plan describes), or
3. **input only the operator has**.

Everything else is a note, not a stop. Mode-D boundaries are unchanged and non-negotiable: auth,
payments, billing, schema migrations, data deletion, secret rotation, infrastructure.

## Frequency, not existence

Reviewer gates **stay**. What shrinks is how often they fire and how much they carry. Nothing in
this doctrine authorizes dropping a phase's only security lens — that is a scope cut disguised as
gate optimization, and it remains prohibited (`references/gate-risk-classes.md`). Validator and
review re-runs are scoped to reviewers whose governed surface actually changed; there is no
unconditional exact-tree re-review at every boundary.

## Bookkeeping demotions

Per-hop bookkeeping was measured as pure overhead at task granularity and real value at milestone
granularity:

| Bookkeeping | Was | Now |
|---|---|---|
| IntentTree lookup/claim/sync 3-step | every task start | **once per milestone** |
| Delivery-dossier regeneration | every phase boundary + every wave | **end of plan** |
| Plan-level completion report | written at plan close | **retired** — the reviewer verdict + `commit_refs` is the record |
| Phase Summary prose table | mandatory in every plan | **deleted** (duplicated the wave plan) |
| `orchestrator_model` frontmatter | plan + per-phase | **deleted** (advisory, never read; the loop cannot switch its own model mid-run) |

Everything else in the DoD stays: worktree -> PR -> squash, AOS writeback gates, SkillMeat
registration, ephemeral teardown, changelog discipline.

## Terminology

**Plan milestone** = a reviewable state of the system, the coarse unit *above* phases, as
authored by the plan doctrine. Older text in this skill uses "milestone" for a batch boundary
inside a phase; where both senses could be read, write **plan milestone** for the new one.
