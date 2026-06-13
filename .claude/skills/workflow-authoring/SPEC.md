---
schema_version: 2
doc_type: skill_spec
skill_name: workflow-authoring
skill_version: 1.0.0
status: stable
created: 2026-06-13
updated: 2026-06-13
owner: Nick Miethe
source_docs:
  - .claude/skills/workflow-authoring/SKILL.md
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/workflow-registry.md
  - .claude/skills/workflow-authoring/per-workflow-spec-template.md
  - .claude/skills/workflow-authoring/syntax-check-helper.js
  - .claude/skills/dev-execution/orchestration/workflow-patterns.md
related_skills: [dev-execution, council-review, artifact-tracking, research-foundry-swarm]
affects_commands: []
---

# workflow-authoring — Skill Specification

> **Reading this file**: This is the versioned capability contract for the `workflow-authoring` skill.
> It governs what the skill covers, invariants agents must respect, and the roadmap for future
> enhancements. For invocation-time routing and procedural steps, load `SKILL.md` directly.

---

## 1. Purpose & Scope

The `workflow-authoring` skill governs the end-to-end procedure for creating, modifying, validating,
and registering SkillMeat Dynamic Workflow scripts under `.claude/workflows/`. It operationalizes
the master contract in `.claude/specs/workflows/workflow-authoring-spec.md` into a deterministic
five-step flow: load contracts → choose patterns → generate script → validate constraints →
dry-run and register.

In the Research Foundry context this skill is the authoring authority for any workflow script
that orchestrates RF pipeline stages — including the discovery swarm (`research-foundry-swarm.js`)
and the offline council gate (`research-foundry-council.js`). It ensures that every script
produced for RF respects the four hard constraints, references the correct executor and reviewer
agent types, and carries a registry entry before it is invoked.

**In-scope capabilities**:
- Loading and applying the master workflow contract (`workflow-authoring-spec.md`) and per-workflow specs
- Pattern selection from the pattern library (`workflow-patterns.md`) for standard task shapes
- Script skeleton generation with correct `meta`, `args` parsing, and `dry_run` guard
- Four-constraints checklist validation (no FS/shell, Mode D boundary, edit-less reviewers, no `Date.now`/`Math.random`)
- Durability checklist validation (commit-checkpoints, two-staged heavy agents, fallback on structure miss)
- Syntax-check recipe via `syntax-check-helper.js`
- Per-workflow spec scaffolding from `per-workflow-spec-template.md`
- Registry entry authoring and `workflow-registry.md` maintenance

**Out of scope** (to prevent misuse):
- Executing or invoking workflow scripts at runtime — that is the Workflow tool's responsibility
- Writing or modifying the underlying agent definitions consumed by `agentType` fields
- Authoring per-workflow specs for workflows outside `.claude/workflows/` (e.g., shell scripts, Python tasks)
- Publishing or deploying workflow scripts to remote hosts
- Routing logic — `delegation-router` resolves `RoutingRecord.agent_type_id` at Opus pre-flight; scripts dispatch only

---

## 2. Capability Coverage

| Intent | Workflow / Section | Canonical Doc |
|--------|--------------------|---------------|
| Author a new workflow script from scratch | SKILL.md §Steps 1–5 (full procedure) | `.claude/specs/workflows/workflow-authoring-spec.md` |
| Scaffold a per-workflow spec for a new workflow | SKILL.md §Step 1 — per-workflow spec; use template | `.claude/skills/workflow-authoring/per-workflow-spec-template.md` |
| Choose the right orchestration pattern for a task shape | SKILL.md §Step 2 — pattern selection table | `.claude/skills/dev-execution/orchestration/workflow-patterns.md` |
| Generate the script skeleton with correct `meta` and `args` parsing | SKILL.md §Step 3 — required skeleton | `.claude/specs/workflows/workflow-authoring-spec.md` §2–§3 |
| Validate a script against the four hard constraints | SKILL.md §Step 4 — four-constraints checklist | `.claude/specs/workflows/workflow-authoring-spec.md` §5 |
| Validate a script against the durability checklist | SKILL.md §Step 4 — durability checklist | `.claude/specs/workflows/workflow-authoring-spec.md` §16 |
| Syntax-check a workflow script | SKILL.md §Step 4 — syntax-check recipe | `.claude/skills/workflow-authoring/syntax-check-helper.js` |
| Register a new workflow in the registry | SKILL.md §Step 5 — register | `.claude/specs/workflows/workflow-registry.md` |
| Dry-run a workflow to confirm args parsing and meta correctness | SKILL.md §Step 5 — dry-run | `.claude/specs/workflows/workflow-authoring-spec.md` §3 |
| Extend an existing workflow (new phase or pattern) | SKILL.md §When to Author a New Workflow vs. Extend | `.claude/specs/workflows/workflow-authoring-spec.md` |
| Handle Mode D boundary detection in a script | SKILL.md §Mode D Handling Quick Reference | `.claude/specs/workflows/workflow-authoring-spec.md` §5 |
| Route reviewers via `agentType` in reviewer gates | SKILL.md §Step 3 key rules | `.claude/specs/workflows/workflow-authoring-spec.md` §4, §8 |
| Author an RF-specific workflow (discovery swarm, council gate) | SKILL.md §Steps 1–5 with RF agent types | `.claude/specs/workflows/workflow-registry.md` (RF entries) |

---

## 3. Invariants & Constraints

1. **Load the master contract before any authoring action.** `workflow-authoring-spec.md` is the canonical authority. Per-workflow specs extend it; they never contradict it. Any instruction in SKILL.md or SPEC.md that conflicts with the master contract is incorrect and must not be followed. (Source: `workflow-authoring-spec.md` preamble)

2. **No workflow script is saved without a corresponding per-workflow spec.** The spec at `.claude/specs/workflows/<name>-workflow-spec.md` is the contract; the script implements it. A script without a spec is an invariant violation. (Source: `workflow-authoring-spec.md` §5.4)

3. **No workflow script is saved without passing all four hard constraints.** The four-constraints checklist is a gate, not a recommendation. Failing any check blocks saving. (Source: `workflow-authoring-spec.md` §5)

4. **No workflow script is saved without a registry entry.** Every `.claude/workflows/<name>.js` must have a corresponding row in `workflow-registry.md` before the script is used. (Source: `workflow-registry.md` preamble)

5. **Scripts never call `Date.now()`, `Math.random()`, or argless `new Date()`.** Timestamps arrive via `args.timestamp` (set by Opus pre-flight). Violating this breaks session resumption. (Source: constraint 4 of the four-constraints checklist)

6. **Scripts never perform FS or shell access.** No `import fs`, `require`, `exec`, `readFile`, `child_process`, or equivalent. All file reads and CLI commands are performed by agents, not the script. (Source: constraint 1)

7. **Mode D phases are workflow boundaries, never internal phases.** On detection (`phase.mode === 'D'`), the script returns `{status: 'blocked', reason: 'mode_d', blocked_phase: phase.id, report}` immediately before any agents spawn. Opus runs the phase interactively. (Source: constraint 2)

8. **All reviewer gate calls use an edit-less `agentType`.** Valid edit-less set: `task-completion-validator`, `karen`, `council-review`, `code-reviewer`, `senior-code-reviewer`. Inline prompts for reviewers are forbidden — they cannot enforce read-only. (Source: constraint 3)

9. **`meta` is a pure literal object.** No computed values, function calls, or expressions inside `meta`. Mismatches between `meta.phases` and `phase()` calls produce ghost phase groups in the `/workflows` TUI. (Source: `workflow-authoring-spec.md` §2)

10. **`args` is always parsed at the top of the script body.** Use `typeof args === 'string' ? JSON.parse(args) : args` before any destructuring. And `args.dry_run === true` must return the parsed graph immediately without spawning agents. (Source: `workflow-authoring-spec.md` §3)

11. **One level of `workflow()` nesting only.** A nested workflow may not call `workflow()` itself. (Source: `workflow-authoring-spec.md` §1)

12. **The `delegation-router` is never called at runtime inside a script.** Provider routing is resolved by Opus pre-flight; the resolved `agent_type_id` becomes the `agentType` value. Scripts dispatch; they do not resolve. (Source: `.claude/specs/provider-routing-spec.md`)

---

## 4. Enhancement Backlog

- **[BL-1] Automated registry linter**: A pre-authoring check that validates `workflow-registry.md` for missing columns, stale script paths, and `candidate` entries with no matching spec file.
  _Status_: candidate
  _Rationale_: Registry drift is a recurring maintenance risk. A lightweight linter would catch stale entries without requiring manual audits.

- **[BL-2] Per-workflow spec validator**: A Node.js script (parallel to `syntax-check-helper.js`) that checks per-workflow spec files for required sections and non-null canonical doc entries.
  _Status_: candidate
  _Rationale_: Spec quality is currently enforced only at review time. A validator would catch structural gaps at authoring time.

- **[BL-3] RF-specific pattern additions**: Document RF pipeline patterns (`rf_ingest_loop`, `council_gate_pattern`) in `workflow-patterns.md` as named, copy-paste-ready blocks.
  _Status_: planned
  _Rationale_: The research-foundry-swarm and research-foundry-council workflows use RF-specific orchestration shapes. Naming and documenting them enables safe reuse by future RF workflow authors.

- **[BL-4] Workflow TUI dry-run integration**: Extend `args.dry_run` handling to emit a schema-valid `ExecutionGraph` preview consumable by `/workflows inspect`.
  _Status_: deferred
  _Rationale_: Dependent on the `/workflows` TUI exposing a dry-run display mode. Deferred until TUI supports it.

- **[BL-5] `workflow-authoring` command binding**: Add an explicit `/workflow:author` command that loads this skill and pre-selects the five-step procedure.
  _Status_: candidate
  _Rationale_: Currently there is no slash command that automatically loads this skill. The command binding from `CLAUDE.md` is convention-based, not enforced. A dedicated command would reduce cognitive load.

---

## 5. Changelog

### v1.0.0 — 2026-06-13
- Initial SPEC.md authored for the `workflow-authoring` vendored skill.
- Capability coverage matrix: 14 intent rows across 5 workflow procedure steps plus RF-specific authoring.
- Invariants: 12 invariants drawn from the master contract's four-constraints checklist, durability checklist, meta conventions, and registry policy.
- Enhancement backlog: 5 candidates (BL-1 through BL-5).
- Scoped to RF context: includes RF-specific workflow authoring (discovery swarm, council gate) as an in-scope capability.

---

## 6. Integration Points

| Agent / Command | Invocation | Notes |
|-----------------|------------|-------|
| Opus orchestrator (any) | `Skill("workflow-authoring")` before writing `.claude/workflows/*.js` | Mandatory per CLAUDE.md §Command-Skill Bindings |
| `lead-architect` | `Skill("workflow-authoring")` | Uses when authoring new phase types or reviewer routing changes |
| `platform-engineer` | `Skill("workflow-authoring")` | Uses when building new RF workflow scripts |
| `ai-artifacts-engineer` | Direct — reads `SKILL.md` procedural steps | Follows five-step procedure directly for registry authoring |
| `/dev:execute-phase` | Indirect — `dev-execution` delegates here for workflow step generation | Loaded by `dev-execution` as a sub-dependency |
| `workflow-authoring` skill itself | Loaded via `Skill("workflow-authoring")` | No recursive invocation |
| `council-review` skill | Co-loaded alongside `workflow-authoring` when authoring council-gated workflows | `councilEscalation` pattern requires `council-review` agent types |
| `research-foundry-swarm` skill | Co-loaded when authoring RF discovery swarm workflows | Provides RF pipeline context (rf ingest, guard, governance profiles) |

**Dependencies this skill loads or expects**:
- `workflow-authoring-spec.md` — master contract (must be read in Step 1 before any authoring)
- `workflow-patterns.md` — pattern library (consulted in Step 2)
- `per-workflow-spec-template.md` — scaffold for new per-workflow specs (used in Step 1 when spec is missing)
- `syntax-check-helper.js` — syntax validator (run in Step 4)
- `workflow-registry.md` — registry (updated in Step 5)

---

## 7. Success Signals

- An agent loads this skill and produces a passing four-constraints checklist within the same session — no constraint violations survive to the saved script.
- The per-workflow spec for every new script is authored before the script body, not after.
- `workflow-registry.md` has a row for the new script before the first `workflow()` invocation.
- Dry-run (`args.dry_run === true`) returns the parsed graph without spawning any agents.
- `syntax-check-helper.js` exits 0 on the authored script.
- RF-specific workflows (`research-foundry-swarm.js`, `research-foundry-council.js`) use only RF-native agent types (`rf_discovery_lead`, `rf_deep_reader`, `rf_domain_researcher`, `council-review`) and never call `delegation-router` at runtime.
- `meta.phases` titles match `phase()` calls character-for-character — the `/workflows` TUI shows no ghost or duplicate phase groups.
