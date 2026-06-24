---
schema_version: 2
doc_type: exploration_charter
title: "Writeback-Boundary Default-Deny Gate (RIB-017) — Exploration Charter"
status: draft
created: 2026-06-23
feature_slug: writeback-default-deny-gate
timebox_days: 3
hypothesis: "We believe a declarative default-deny writeback gate keyed on (sensitivity_tier, target_id, target_topology) with justified-override is worth building on top of the existing governance module, because the current imperative, hardcoded-by-name rule set cannot express boundary policy as data and has no operator-recoverable path past a denied writeback."
deal_killer: "If the existing imperative rule set already covers all real (sensitivity, target) combinations and 'target_topology' adds no expressible policy that the flat target string cannot, abandon the declarative-gate rework and just add the missing justified-override flow on top of guard_check()."
investigation_legs:
  - id: topology
    question: "What does target_topology actually mean, and does it add policy expressiveness over the current flat target strings (e.g. 'meatywiki'/'intenttree')?"
    assigned_to: backend-architect
  - id: gate-model
    question: "How should a declarative default-deny lookup table be structured, and does it replace or wrap guard_check()? How do the ~6 existing imperative rules migrate into the table?"
    assigned_to: spike-writer
  - id: override
    question: "How does a justified-override / HITL flow let an operator approve a denied writeback, where is the justification + approval recorded in the append-only audit log, and how does it interact with the exit-code-7 HUMAN_REVIEW signal?"
    assigned_to: backend-architect
verdict_criteria:
  go:
    - "All investigation legs report confidence >= 0.7"
    - "target_topology adds real policy expressiveness not capturable by the flat target string (topology leg confirms with examples)"
    - "Deal-killer condition not triggered"
  no_go:
    - "Deal-killer condition triggered (existing imperative rules + a thin override addition cover all real cases; topology adds nothing)"
    - "gate-model leg reports the table cannot subsume the existing imperative rules without lossy or unsafe translation, confidence >= 0.8"
  conditional:
    - "Gate model and topology are sound, but the justified-override/HITL flow requires a separate dependency or out-of-band approval surface (named as a specific follow-up investigation)"
verdict: null
verdict_rationale: null
output_artifacts: []
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
---

# Writeback-Boundary Default-Deny Gate (RIB-017) — Exploration Charter

<!-- Copy to docs/project_plans/exploration/[feature-slug]/[feature-slug]-charter.md -->
<!-- Use /plan:explore to scaffold most fields from an idea description. -->

## Hypothesis Context

This exploration derives from completed research run **RIB-017** (IntentTree node
`node_01KVQYMYPN51B5TRGPR65NNPW3`; high evidence). The research recommends a **default-deny
writeback gate** keyed on `(sensitivity_tier, target_id, target_topology)` with a justified-override
path and an append-only audit log. The BUILD is wanted, but two design elements are genuinely
unresolved, so this charter scopes a **design SPIKE**, not a Feature Contract.

Grounding facts (verified against the codebase):

- RF already has a deterministic governance module — `src/research_foundry/services/governance.py`
  exposing `guard_check()`, `preflight()`, `GuardContext` (with `writeback_targets`), and
  `GuardResult`. It implements ~6 **imperative** policy rules evaluated by name (e.g.
  `no_work_keys_for_personal_runs`, `work_writeback_requires_review`,
  `intenttree_writeback_requires_review`, `arc_writeback_requires_review`).
- Sensitivity tiers exist (`_PERSONAL_SENSITIVITIES`, `_WORK_SENSITIVITIES`).
- An append-only audit log already exists via `append_jsonl()` to the run trace.
- Config lives in `config/governance.yaml`, surfaced via `FoundryConfig.policy_rules()`.

What is **MISSING** (and is what this SPIKE must resolve):

1. Rules are **hardcoded-by-name** and evaluated imperatively — there is **no declarative
   default-deny lookup** keyed on a `(sensitivity_tier, target_id, target_topology)` tuple.
2. There is **no justified-override / HITL acceptance flow** — the guard only raises an exit-code-7
   `HUMAN_REVIEW` outcome, with no subsequent approve/reject handler.
3. **`target_topology` is an undefined concept** — current writeback targets are flat strings
   (e.g. `"meatywiki"`, `"intenttree"`).

Counterfactual: if the flat target string plus the existing rule set already covers every real
boundary case, the declarative rework is wasted motion and only the override flow is worth adding.
That counterfactual is the deal-killer below.

---

## Investigation Legs

<!-- One subsection per leg. Each leg runs as a SPIKE via /plan:spike --leg-of=[charter-path]. -->

### Leg: topology — Define target_topology and its expressiveness

**Question**: What does `target_topology` actually mean, and does it add policy expressiveness over
the current flat target strings?
**Assigned to**: `backend-architect`
**Expected output**: `docs/project_plans/exploration/writeback-default-deny-gate/spikes/topology-spike.md`

Unknowns / sources this leg must address:
- Candidate meanings of `target_topology`: (a) a URI-like path/namespace within a target
  (e.g. `meatywiki/work/...` vs `meatywiki/personal/...`); (b) the sensitivity-of-the-target
  (where the data lands, independent of the run's own sensitivity); (c) a node-level vs system-level
  scope distinction (single node vs whole subsystem).
- For each candidate meaning, produce concrete policy examples that the **flat target string cannot
  express** today — or conclude that none exist (which feeds the deal-killer).
- Cite the current target representation in `GuardContext.writeback_targets` and how targets are
  consumed by the existing rules in `src/research_foundry/services/governance.py`.
- State whether topology is data the run already knows, or new metadata that targets/adapters would
  have to start emitting.

### Leg: gate-model — Declarative default-deny lookup table design

**Question**: How should the declarative default-deny lookup table be structured, and does it
**replace** or **wrap** `guard_check()`? How do the existing imperative rules migrate into the table?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/writeback-default-deny-gate/spikes/gate-model-spike.md`

Unknowns / sources this leg must address:
- Schema for a default-deny table keyed on `(sensitivity_tier, target_id, target_topology)` →
  `{allow | deny | review}`; where it lives relative to `config/governance.yaml` and
  `FoundryConfig.policy_rules()`.
- Replace vs wrap: does the table become the inner evaluator that `guard_check()` calls, or a
  parallel pass `preflight()` composes? Preserve the existing `GuardResult` shape and exit-code-7
  contract either way.
- Migration: map each of the ~6 named imperative rules (e.g. `no_work_keys_for_personal_runs`,
  `work_writeback_requires_review`, `intenttree_writeback_requires_review`,
  `arc_writeback_requires_review`) onto table rows. Flag any rule whose logic is **not** a pure
  tuple lookup (e.g. depends on key profile, not just target) and therefore must stay imperative.
- Default-deny semantics: confirm an unmatched tuple denies (not allows), and how that interacts with
  existing runs that currently pass because no rule names them.

### Leg: override — Justified-override + HITL flow design

**Question**: How does an operator approve a denied writeback, where is the justification + approval
recorded in the append-only audit log, and how does it interact with the exit-code-7 signal?
**Assigned to**: `backend-architect`
**Expected output**: `docs/project_plans/exploration/writeback-default-deny-gate/spikes/override-spike.md`

Unknowns / sources this leg must address:
- The approve/reject handler that today does not exist downstream of the exit-code-7 `HUMAN_REVIEW`
  outcome: where it lives, what its CLI/API surface is, and whether it resumes the same run or a new
  privileged action.
- Audit record shape: what `append_jsonl()` entry captures the justification text, approver identity,
  the original denied `(sensitivity_tier, target_id, target_topology)` tuple, and the resulting
  decision — written to the run trace, append-only, never mutated.
- Interaction with the gate: does an override write a one-shot allow record consumed on re-run, or a
  durable table exception? Confirm overrides cannot silently widen policy for future runs.
- Whether the override surface needs a dependency or out-of-band approval channel (feeds the
  `conditional` verdict gate).

---

## Verdict Criteria Narrative

**Go** if: all three legs land at confidence ≥ 0.7, the `topology` leg demonstrates at least one real
policy that `target_topology` expresses and the flat target string cannot, the `gate-model` leg shows
the existing imperative rules migrate into the table (or are explicitly carved out as imperative
residue) without lossy/unsafe translation, and the deal-killer is not triggered.

**No-go** if: the deal-killer holds — the existing imperative rules plus a thin override addition
already cover every real `(sensitivity, target)` case and `target_topology` adds no expressible
policy — OR the `gate-model` leg concludes (confidence ≥ 0.8) that a declarative table cannot subsume
the current rules without unsafe translation.

**Conditional** if: the gate model and topology are sound, but the justified-override / HITL flow
needs a separate dependency or out-of-band approval surface. In that case, name that follow-up as a
specific subsequent investigation and proceed to contract only the table + topology portion.

---

## Out of Scope

- Building the gate, table, or override handler — this is a design SPIKE only; no production-code
  edits. (Verdict stays `null` until the legs conclude.)
- Re-deriving RIB-017's research findings; treat the research recommendation as the input premise.
- Redesigning the broader governance module beyond the writeback-boundary surface (key profiles,
  secret scanning, and unrelated policy rules stay as-is).
- The downstream writeback adapters themselves (MeatyWiki/IntentTree/ARC client behavior); this
  charter governs the **gate**, not the transport.

---

## Citations / Prior Art

- Source run: RIB-017 — IntentTree node `node_01KVQYMYPN51B5TRGPR65NNPW3` (high evidence).
- Completed-runs harvest: `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md`.
- Existing governance module: `src/research_foundry/services/governance.py`
  (`guard_check()`, `preflight()`, `GuardContext.writeback_targets`, `GuardResult`,
  `_PERSONAL_SENSITIVITIES`, `_WORK_SENSITIVITIES`, `append_jsonl()` audit log).
- Governance config: `config/governance.yaml` via `FoundryConfig.policy_rules()`.

---

## Notes

- 2026-06-23: Charter authored (Mode B — Contract Drafting). Verdict left `null`; this charter scopes
  the investigation and does not conclude it. Cited file paths verified on disk before authoring.
