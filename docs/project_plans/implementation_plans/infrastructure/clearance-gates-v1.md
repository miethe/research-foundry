---
it_schema: 1
feature_slug: clearance-gates
title: "Clearance Gates — separating dev/test enablement from ship enablement"
doc_type: implementation_plan
status: completed
planning_maturity: shipped
tier: 3
priority: P1
points: 52
risk_level: high
context_class: C3
created: 2026-08-05
updated: 2026-08-05
changelog_required: true
prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
plan_ref: null
spike_ref: null
related_documents:
  - docs/project_plans/implementation_plans/infrastructure/attribution-rollup-phase-c-seam-v1.md
  - docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - .claude/worknotes/clearance-gates/context.md
# commit_refs holds ONLY commits reachable from main (.claude/rules/plan-bookkeeping.md
# invariant 1). Verified with `git merge-base --is-ancestor 576778a main`, not `git log -1`
# — the latter resolves an object and succeeds on an orphan, so it is not proof of
# reachability. The branch shas in the Milestones table below are pre-squash and are now
# orphaned by design; do not cite them here.
commit_refs:
  - 576778a
pr_refs: []
merge_commit: 576778a
merge_branch: main
worktree: .claude/worktrees/clearance-gates
branch: feat/clearance-gates
base_commit: ff5a23f
files_affected:
  - config/clearance_gates.yaml
  - schemas/clearance_taint.schema.yaml
  - src/research_foundry/services/clearance.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/services/writeback.py
  - src/research_foundry/integrations/base.py
  - src/research_foundry/integrations/notebooklm.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/config.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/knowledge_access.py
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - frontend/runs-viewer/src/app/AppShell.tsx
routing_constraints:
  - "M3's posture + stamping MUST stay claude-primary — it turns on real network egress and owns the durable half of the guarantee."
  - "M5's egress consolidation MUST stay claude-primary — authorization/governance surface across ~10 call sites."
  - "M1/M2 mechanical test scaffolding is offload-eligible; the guarantees are not."
open_questions:
  - "OQ-1 (CORRECTED 2026-08-05 — the original text was WRONG): when a gate closes, existing records keep their stamp by design (taint is durable), and no *intentional* operator-run re-evaluation path exists to release them. But the original claim that NO release path exists is false. `governs_kind()` returns `kind in applies_to_kinds()`, and when that is False `mediate_egress` returns a clean token unconditionally — so removing `source_attribution` from `applies_to_kinds` in config/clearance_gates.yaml releases EVERY stamped record at EVERY chokepoint, globally, with one line. Guard rule 9's `_CLEARANCE_GOVERNED_FIELDS` originally covered `clearance_gate.state` and omitted `applies_to_kinds`, so an agent-writable path could do it without a guard violation; that omission is closed. It remains an operator-editable release lever by design (config is operator territory), but it must be understood as one. `gate_refs` on each stamp exists so an intentional re-evaluation path CAN be built; building it is deliberately out of scope."
  - "OQ-2 (OPEN, operator decision): `export_run` refuses the WHOLE run when any citation is blocked, so a tainted run becomes locally unusable — which contradicts the feature's stated intended outcome that the site stays usable and data queryable. Writing run.json locally and importing into the local catalog.db do not leave the machine, yet both are gated under `redistribution`, whose own definition here is 'may fetch and use locally; may not leave the machine.' The module already has a per-citation `REDACTION_MARKER` whole-field-swap pattern that would withhold the value while keeping the run viewable. Either justify hard refusal in a `decisions:` entry (as catalog_service.search's identical all-or-nothing choice already does) or switch to the per-citation pattern. Latent today: unreachable until a stamp can be persisted."
decisions:
  - decision: "The registry carries DATA only — no `condition:`/`severity:` keys, and the loader actively refuses them."
    rationale: "config/governance.yaml's policy_rules has exactly those keys and they are NEVER parsed — documentation masquerading as enforcement, with real conditions hardcoded in guard_check's numbered if-blocks. Repeating that shape yields a registry that looks enforcing and is not."
  - decision: "Agent writes to clearance are MONOTONE (add a blocked scope, never assert the empty set) rather than diffed against prior on-disk state."
    rationale: "guard_check is deterministic and stateless and cannot ask 'did this write remove a scope?'. Constraining the direction of travel gives a stronger guarantee than diffing, and it holds even for a caller that never read the prior value."
  - decision: "Enforcement is RUNTIME-checked, not type-checked, and the transport accepts either a bare dict or a MediatedPayload."
    rationale: "The approved plan called for a type-level guarantee, but mypy does not run in CI in this repo (only .github/workflows/docs.yml; no pre-commit config), so a mypy-only wrapper would be unenforced and its AC vacuous. A mandatory-parameter migration across every client method was also rejected: it breaks every existing signature and test for no added guarantee, since the real per-record check happens upstream on raw records."
  - decision: "NotebookLM is gated at its call site (_render_notebooklm_update takes a required token), not at the transport."
    rationale: "It overrides _get/_post/_patch as dead `return None` stubs and works through subprocess, so the transport backstop is structurally unreachable — while being the richest content egress in the codebase (full report + every source card to Google's cloud)."
  - decision: "The three `# type: ignore[override]` comments on NotebookLM's stubs were NARROWED rather than left in place."
    rationale: "As blanket ignores they suppressed the whole override check, so the base class's payload-type widening would have been silently swallowed — worse than being merely uncovered."
  - decision: "The clinical marker derives from the EXISTING claim_clinical_eligibility() heuristic, never from clearance.blocked_scopes presence."
    rationale: "The 7 committed pediatric bundles predate clearance and can never carry a stamp; wiring the marker to require one would newly and wrongly fail all 7."
  - decision: "applies_to_kinds lists only source_attribution; pre-existing kinds are excluded."
    rationale: "Backward compatibility, not a loophole. Every record kind predating clearance is structurally incapable of carrying a stamp, so demanding one converts a safety control into a correctness regression."
wave_plan:
  waves: [["m1"], ["m2"], ["m3"], ["m4"], ["m5"]]
  phases:
    - id: m1
      title: "Clearance-gate registry, taint schema, vocabulary guard"
      depends_on: []
      context_class: C2
      review_intensity: standard
      gate_lens: [validator]
    - id: m2
      title: "Mediation primitive + chokepoint retrofit (fixtures only)"
      depends_on: [m1]
      context_class: C3
      review_intensity: tier3
      gate_lens: [validator, codex]
    - id: m3
      title: "Dev/test posture + real taint stamping at fetch"
      depends_on: [m2]
      context_class: C3
      review_intensity: tier3
      gate_lens: [validator, karen, codex]
    - id: m4
      title: "Clinical surfacing + non-dismissible marker"
      depends_on: [m3]
      context_class: C3
      review_intensity: standard
      gate_lens: [validator]
    - id: m5
      title: "Egress governance consolidation (closes pre-existing gaps)"
      depends_on: [m4]
      context_class: C3
      review_intensity: tier3
      gate_lens: [validator, karen, codex]
---

# Clearance Gates — implementation plan

> **Execution state, handoff, and the full trap list live in
> `.claude/worknotes/clearance-gates/context.md`.** Read that first when resuming.

## Context

RF conflates three distinct meanings into single boolean flags. The clearest
instance is `AttributionFetchControls.attribution_fetch_enabled`
(`src/research_foundry/config.py:119`), whose docstring spends 15 lines explaining
what the flag does *not* mean — because the flag's existence reads as a license
posture even though it governs only config visibility.

The three meanings: **capability** (is the mechanism reachable?), **use scope**
(view locally / build rules against / redistribute / rely on clinically), and
**clearance** (has a human with standing signed off?).

Clearance and use scope were invisible to code. DEF-1 (per-provider license terms
for bundle redistribution) and DEF-6 (live ToS re-verification for Semantic
Scholar / NCBI) existed only as prose in PRD §7's deferrals table and in
`services/attribution_fetch/__init__.py`'s docstring. There was no
machine-readable registry of open gates anywhere in the repo. Consequence: because
clearance was invisible, the only safe posture was total inertness — that package
imports no networking library at all — so no development or evaluation work could
proceed against real provider data until a *legal* determination landed.

That coupling is wrong in both directions. **Acquiring a value for local
evaluation is not redistribution, and viewing a clinical claim is not clinical
reliance.** The gates should govern the outward and clinical-reliance boundaries,
not local development.

**Intended outcome:** the site stays fully usable, the data queryable, and rules
authorable before any license, ToS, or clinical attestation clears — while
redistribution and clinical reliance become *structurally* impossible rather than
merely disabled.

## Gate taxonomy — three blocking scopes

| Scope | Meaning | Gates |
|---|---|---|
| `acquisition` | May not fetch or cache even locally | **DEF-2** (Scopus/WoS/JCR/SCImago — contractual prohibition; procurement precondition) |
| `redistribution` | May fetch and use locally; may not leave the machine | **DEF-1**, **DEF-3**, **DEF-6** |
| `clinical_reliance` | May be viewed and reasoned over; may not be relied on clinically | **CLIN-ATTEST** |

The dev/test posture opens `redistribution` and `clinical_reliance` for local use
only. It must **never** open `acquisition`; no DEF-2 adapter exists, so that is
structural rather than a runtime check.

## Milestones

| ID | Title | Pts | Risk | State | Branch commit |
|---|---|---|---|---|---|
| M1 | Registry, taint schema, guard rule 9 | 5 | Low | **done** | `dd5310f` |
| M2 | Mediation primitive + chokepoint retrofit | 13 | Med-High | **done** | `0fcd368` |
| M3 | Dev/test posture + real taint stamping | 13 | High | **done** | `82431c7`, `bf8691c`, `a69d337` |
| M4 | Clinical surfacing + non-dismissible marker | 8 | Med | **done** | `2028ea1` |
| M5 | Egress governance consolidation | 13 | High | **done** | `13222e5`, `425b66f`, `db8b823` |

`e6a057f` merged upstream `main` (`e30ad44`) into the branch mid-stream. It was
required, not incidental: `d0cb1a8` on `main` fixed the validator hook-output
schema *and* modified `tests/test_governance_adversarial.py`, so without the merge
the hybrid gate paired main's fixed tests against this branch's pre-fix validators
and produced failures that read as defects but only meant the branch was behind.
The handoff's "6 governance_adversarial failures, do not chase" accounting was
stale as a result — a baseline captured on `main` at `e30ad44` has exactly 8
failures and `test_governance_adversarial` is not among them.

Branch shas above are **not** main-reachable and will go orphan on squash; per
`.claude/rules/plan-bookkeeping.md` invariant 1 they stay out of `commit_refs`
and must be replaced by the squash sha on merge.

### Sequencing — the two hazards this order avoids

**Hazard A — taint exists, unenforced.** Shipping live fetch before the chokepoint
means the first `writeback()` run pushes a should-never-leave value straight to
NotebookLM/ARC/MeatyWiki, silently, with no code defect required beyond bad
ordering.

**Hazard B — enforcement exists, taint unstamped.** Wiring a fail-closed check
before anything stamps, with scope too broad, retroactively blocks every
pre-existing record — including the 7 committed pediatric bundles, which can never
comply. `applies_to_kinds` (decided in M1) is what lets the rule be strict without
causing this.

Hence: M1 foundation → M2 chokepoint proven on fixtures → M3 real taint → M4
clinical → M5 turn it loose on pre-existing content. **Do not reorder.**

## Design invariants (must hold at every milestone)

1. **The registry holds data, never pseudo-logic.** No `condition:`/`severity:`.
2. **Taint is stamped from posture-at-fetch-time and never re-derived** from the
   registry's live gate state. This is what makes a posture flip or gate closure
   unable to retroactively release a record.
3. **Absence of a stamp means refused, not clean** — for governed kinds only.
   DEF-5 records that outward projections use hand-listed allowlists that drop
   unknown fields; if a dropped stamp read as clean, the allowlist would *be* the
   leak.
4. **Always mediate raw loaded records, never a projected payload.** Checking
   post-projection trivially passes whatever the projection stripped.
5. **Clearance vocabulary never reuses `CLEARED_*` / `counsel_approved` /
   `attested`** (ADR Invariant 1 reserves those for humans).
6. **Gate-closing is an operator file edit only.** No `rf` verb may close a gate.
7. **Schema shape is the primary control; name-tuples are defence-in-depth.**
   `governance.py`'s own rule-8 comment records why.

## Verification

- Python: `./.venv/bin/python -m pytest` (a bare `pytest` fails with "No module
  named research_foundry"). Compare failure **sets** against a baseline at the
  same base commit, never counts.
- Frontend: `npm run lint && npx tsc -p tsconfig.app.json --noEmit && npx vitest run`
  (root `tsc --noEmit` is a documented no-op — the root tsconfig is a solution file).
- End-to-end (M3 + M5 together, the real proof): declare the posture, fetch against
  a mocked provider, confirm the on-disk card carries
  `blocked_scopes: ["redistribution"]`, view it in the viewer with its marker,
  author a rule against it, then confirm `rf bundle` and all 6 writeback targets
  refuse. Finally delete the posture block and re-run mediation on that same record
  — it must **still** be denied.
  - **UNMET as of 2026-08-05 — recorded, not quietly passed.** Two halves of this
    criterion could not be executed, and the reasons are structural rather than
    oversights in testing:
    - **No on-disk card can carry a stamp.** `rf attribution fetch` threads no
      `config`, so the live-fetch path is unreachable from any shipped surface, and
      nothing persists `clearance:` onto source-card frontmatter. The final
      posture-deletion half WAS proven, but against an in-memory record, not a
      round-tripped on-disk one. Filed: `node_01KZ9WKCPA8RBG3722QN3KH3S6`.
    - **`rf bundle` is STRUCK, with a stated reason — not unmet.** `build_bundle` has
      no clearance call and deliberately needs none. Verified empirically, not by
      reading: a marker string injected into a source card's title, author, DOI,
      abstract and quote body, and into its claim statements, was present in the
      source cards (positive control) and **absent** from the emitted
      `evidence_bundle.yaml`. Every value the bundle writes is a generated id, a
      timestamp, a status literal, an integer count, the controlled-vocabulary
      sensitivity label, a boolean/null, or a hardcoded relative path. Separately,
      `build_bundle` is not an egress at all — it writes inside the run directory on
      the local machine — and DEF-1 is scoped to "bundle **redistribution**", which is
      what the six mediated writeback targets and `export_service` do. A comment at
      `build_bundle` records this along with what would invalidate it: any
      source-derived field added to the `bundle` dict makes it a mediation site.
  - Everything else in this criterion is met: the viewer marker, the per-record
    denial at all 6 writeback targets, and the durability of the stamp against a
    posture flip plus a gate closure.
- Regression floor: all 7 committed pediatric bundles still verify, with a
  field-by-field export diff.

## Non-goals

- A real counsel/attestation workflow (ADR OQ-RF-6; deferred to
  `docs/project_plans/design-specs/rights-counsel-workflow.md`).
- **Closing DEF-1/DEF-6.** This plan asserts *no* license posture for any provider.
- Filesystem-level tamper resistance (same bounded limitation
  `assertion_report_use.py:1424-1432` already accepts).
- Changing `ingest_source`'s fail-open convention (`source_cards.py:283`).
- Expanding `redact_payload()`'s secret-pattern scope.
- AST-level enforcement for CLI/subprocess sites — a grep-based CI lint is the
  proportionate interim control.
- DEF-2 provider adapters; adding one requires a reviewable new module.
