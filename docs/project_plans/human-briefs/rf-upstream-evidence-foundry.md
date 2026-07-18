---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: ""
root_kind: project_plans

id: "BRIEF-rf-upstream-evidence-foundry"
title: "rf Upstream Evidence Foundry — Human Brief"
status: draft
category: human-briefs

feature_slug: rf-upstream-evidence-foundry
feature_family: rf-upstream-evidence-foundry
feature_version: v1

prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
intent_ref: ""
epic_ref: ""

related_documents:
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/expansion/02-evidence-foundry-on-research-foundry.md
  - .claude/worknotes/rf-upstream-evidence-foundry/decisions-block.md
  - .claude/worknotes/rf-upstream-evidence-foundry/current-state.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: 0.65

created: 2026-07-18
updated: 2026-07-18
target_release: ""

tags: [human-brief, research-foundry, evidence-foundry, upstream, rf-verify, rf-fetch, rf-council]
---

# rf Upstream Evidence Foundry — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

---

## 1. Context Pointers

One-line pointers. Do not restate content.

- **PRD**: `docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md` (not yet authored — pending `implementation-planner` expansion of the decisions block)
- **Decisions Block**: `.claude/worknotes/rf-upstream-evidence-foundry/decisions-block.md` (Opus-authored scaffold; phase boundaries, agent routing, risk hotspots, estimation anchors)
- **Current-State Fact Sheet**: `.claude/worknotes/rf-upstream-evidence-foundry/current-state.md` (line-cited evidence per RFUP-1..7 area)
- **Design Specs**: None yet — RFUP-6 design spec (`docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md`) is a Phase 6 deliverable, not yet on disk
- **SPIKEs**: External spike-equivalent (not first-party) — `pediatric-anemia-site/docs/project_plans/expansion/02-evidence-foundry-on-research-foundry.md` (§6.2 gap register, §8.3 risk table originate this feature)
- **Related Briefs**: None

---

## 2. Estimation Sanity Check

Bottom-up H1–H6 applied independently against the decisions-block §4 scaffold (29 pts across 6 phases). File sizes for every `files_affected` path were checked directly (`wc -l`) rather than assumed.

**H1 — Noun count**: 0 new CRUD-with-RBAC domain nouns. Nothing here creates a new database table or first-class entity with a repo/service/router stack — this feature adds fields (`rf_schema_version`, `extraction_status`, `council_verdict`), a gating flag (`verify.exact_passage`), and an append-only lineage record onto *existing* surfaces (source cards, verify output, run directories). H1's noun-count floor does not apply; the work is breadth-of-surface, not depth-of-entity.

**H2 — Dual-impl multiplier**: N/A. Confirmed — no local/enterprise dual-implementation split exists in `research_foundry`; this is a single-edition Python package + one JS workflow script. Matches decisions block §4 note.

**H3 — Algorithmic service flag**:
- RFUP-2 (PDF extraction adapter, Phase 3) — **flagged**, keyword `transform`/`extraction`. The PRD already enumerates 5 test scenarios (full-text PDF, scanned/locator-only PDF, governance-gate-blocks-secret, missing optional dep, pre-existing-card resilience — AC-RFUP2-1..5), satisfying H3's "enumerate ≥5 scenarios" bar. Budgeted at 8 pts standalone, consistent with H3's 3–5+ pt floor plus the added dependency-packaging surface (optional extra).
- RFUP-3 (exact-passage gating, Phase 2) — **not flagged**. This is a rule/flag addition over an *existing* quote-match mechanism (`verification.py:1032–1033`), not a new algorithmic surface; scope is bounded to eligibility-check + config key + machine-readable violation list.
- RFUP-7 (run seal/lineage, Phase 4b) — **not flagged**, despite touching digest/mutation-detection. It explicitly reuses the assertion-registry's existing atomic-write/digest pattern (`assertion_registry.py:50–81, 156–200`) rather than inventing new algorithmic logic — the hard part is already proven code being repointed at a new scope.

**H4 — Bundle decomposition** (6 capability areas, well over the ≥3 threshold — per-area sum is the floor):

| Capability Area | Independent Estimate | Notes |
|---|---|---|
| RFUP-4 — Machine contract & schema versioning | 6 pts | Breadth-driven, not depth-driven: threading `rf_schema_version` through ~7 enumerated surfaces + contract drift tests + inventory doc. Bumped +1 over the decisions-block anchor (5) for the `cli_commands.py` touch — see H7 note below. |
| RFUP-3 — Exact-passage hard-gating | 4 pts | Flag-gated rule addition; real-corpus regression run is real QA cost but bounded. Matches anchor. |
| RFUP-2 — Governed PDF extraction adapter | 8 pts | H3-flagged; matches anchor exactly. |
| RFUP-5 — Council verdict normalization | 2 pts | Small, contained: string-pattern → 3-value enum + confidence flag, non-destructive, no export-schema touch. |
| RFUP-7 — Run seal, digest & lineage | 4 pts | Reuses assertion-registry pattern (holds down cost) but adds a new CLI seal surface (OQ-2) + mutation-detection + unsealed-run regression tests. +1 over the RFUP-7 share of the decisions-block's combined Phase-4 anchor, for the new `cli_commands.py` surface. |
| RFUP-1 — Path-B workflow parameterization | 4 pts | Mechanical config refactor of a 290-line file; matches anchor exactly. |
| **Σ (6 areas)** | **28 pts** | Floor before finalization/plumbing (H6, below). |

**H5 — Anchor reference**: Decisions-block §4 anchors sanity-checked individually above; all hold except RFUP-4 and RFUP-7, nudged up +1 pt each for a file-size finding (H7, below) the original anchors didn't account for. No anchor is off by >30% in either direction — deltas are single-point nudges, not re-derivations.

**H6 — Hidden plumbing budget**: Decisions block folds all finalization work (full regression suite, CHANGELOG, machine-surface inventory doc, RFUP-6 design-spec authoring, IntentTree node writebacks, karen review) into Phase 6 at 3 pts. Against the Σ=28 area floor, H6's 15–20% guidance implies **4.2–5.6 pts**, not 3 — Phase 6 is doing more than pure plumbing (it also owns the RFUP-6 design-spec authoring task and the real-corpus regression gate). Bottom-up: **4 pts** for Phase 6 (lower end of the H6 band, since some plumbing — the contract doc — is already counted inside Phase 1's 6 pts).

**H7 (supplementary, not requested but load-bearing)**: `wc -l` on every `files_affected` path found `cli_commands.py` at **2,640 lines** — over the 2K H7 threshold. It is touched by Phase 1 (stamping `rf_schema_version` across "all `--json` CLI outputs" necessarily means auditing most commands in this file) and plausibly by Phase 4b (if OQ-2 resolves to a new `rf seal <run>` CLI command rather than a flag on an existing path). This is the primary driver of the +1/+1 nudges above. `verification.py` (1,256 lines) and `assertion_registry.py` (767 lines) are sizable but under the 2K trigger. **Recommend the implementation plan add a "High-Friction Surfaces" note flagging `cli_commands.py`** so Phase 1 and Phase 4b tasks touching it get the anti-blow guardrail treatment (grep -n + sed navigation, no whole-file reads).

**Bottom-up total**: 28 (area Σ) + 4 (Phase 6 plumbing) = **32 pts**
**Top-down scaffold (decisions block §4)**: **29 pts**
**Delta**: +3 pts, **~10.3%** — at the edge of, not clearly over, the plan's own 10% explain-if-exceeded bar.

**Reconciliation**: The two estimates substantively agree — the same 6 capability areas, same phase boundaries, same anchors for 4 of 6 phases. The full delta is explained by one concrete finding the original decisions block didn't check: `cli_commands.py` is a 2,640-line file touched by both the highest-breadth phase (Phase 1) and the phase most likely to add a new CLI command (Phase 4b), which the estimation-heuristics doc's H7 rule (huge-file touch) says costs ≥2× on any task that touches it. This does not warrant re-scoping or promoting the feature — it warrants the implementation plan flagging `cli_commands.py` as a High-Friction Surface and treating 29 pts as a floor rather than a ceiling (32 pts is a more realistic execution estimate; watch Phase 1 and Phase 4 for creep first).

---

## 3. Wave & Orchestration Notes

_Critical path narrative and parallelization hints. Plan owns the phase summary table._

**Critical path**: [Which phases/tasks gate everything else]
**Parallel opportunities**: [What can run concurrently and why]
**Merge order**: [Ordering constraints on PR merges or branch integration]
**Cross-feature coupling**: [Dependencies on other in-flight features]

---

## 4. Open Questions Ledger

_Pointer inventory across PRD, plan, design specs, and SPIKE findings. Update status as resolved._

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | Decisions block §7; PRD §13 | Exact config key + profile shape for strict passage gating: `verify.exact_passage` (flat config key) vs a sensitivity-profile-driven shape. Default direction: keep both a run-level flag and a config default. | open | — |
| OQ-2 | Decisions block §7; PRD §13 | Seal trigger surface: new `rf seal <run>` command vs an additive flag on an existing finalize/export path. Default direction: planner picks the smaller surface; must be additive. | open | — |
| OQ-3 | Decisions block §7; PRD §13 | Which PDF extraction library — pypdf vs pdfminer.six. Default direction: planner picks based on existing dependency footprint; ships as an optional extra either way. | open | — |
| OQ-4 | Decisions block §7; PRD §13 | Does the normalized council enum (`approve\|concern\|block`) land in the runs-viewer export schema now (bump 1.5→1.6), or stay CLI/YAML-only until the viewer needs it. Default direction: stays out of the viewer export for this feature (PRD FR-5.4). | open | — |

---

## 5. Deferred Items Rationale

_Why items were deferred and what would trigger promotion. Plan owns the triage table._

- **RFUP-6 — Native discovery adapter install/eval**: Deferred by design, not by capacity. The originating IntentTree node states install/evaluation should happen "only after a measured value/security gap," and today 0 of the 6 non-`arc_council`/non-`litellm_router` adapters (`gpt_researcher`, `paperqa2`, `notebooklm`, `openai_agents`, `opencode`, `claude_agent_sdk`) are installed or live (external spec §6.2 gap register). Both the decisions block (§0 Framing) and the external spec (§6.2, §8.1) converge on stabilizing the proven Path-B Claude workflow (RFUP-1, in scope here) first, since installing a native adapter before that lane is proven adds dependency weight and per-adapter security-review burden without a demonstrated gap. Promote when either: (1) a **measured value gap** — the post-RFUP-1 Path-B workflow is shown insufficient for a specific discovery need via a comparison run, or (2) a **security/governance gap** — a concrete downstream requirement emerges that the existing adapter set can't satisfy and the DI-1 audit register has cleared it. Until then, no adapter installation, evaluation harness, or `adapters/__init__.py::load_all()` change happens under this feature. What *does* happen: Phase 6 authors a `design_spec` at `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` (maturity: `idea`) capturing the trigger condition and adapter shortlist — a documentation task inside Phase 6, not its own phase.

---

## 6. Risk Narrative

_Orchestrator-facing risk rationale. Plan owns the per-phase risk mitigation table._

- **[Risk name]**: [Why this is risky at the orchestration level; what to watch for in execution]

_None identified._

---

## 7. What to Watch For

_Gotchas, trap-doors, and retrospective hooks for real-time review during execution._

- [Specific gotcha or pattern to monitor]

_None identified._

---

## 8. Expected Success Behaviors

_Observable, human-verifiable post-ship outcomes. Not agent acceptance criteria._

- [ ] Running any `rf` command with `--json` (or reading a run export / catalog API response) shows a top-level `rf_schema_version` string — pick any three commands at random and confirm by eye, not just in tests.
- [ ] A machine-surface inventory doc exists and lists every command/endpoint that emits `rf_schema_version`, with its current stamped value — spot-check it against the actual CLI surface.
- [ ] Diffing a fixture run's JSON/YAML output from before vs after this feature shows only the addition of `rf_schema_version` — no renamed or removed keys anywhere.
- [ ] Setting `verify.exact_passage: strict` on a run with a claim lacking a passage anchor makes `rf verify` exit nonzero and show the violation in a distinct `exact_passage_violations` list; the same run in default (unset) mode still passes as before.
- [ ] Running `rf verify` in default mode over a real-corpus sample (drawn from the 2,835 backfilled assertions / prior KnitWit runs) produces zero new failures versus the pre-feature baseline — this is the regression gate that must hold before Phase 2 is considered done.
- [ ] Fetching a PDF with an extractable text layer produces a source card with `extraction_status: full_text` and real content; fetching a scanned/non-extractable PDF produces `extraction_status: locator_only`, matching today's degrade behavior — try both by hand against real PDF URLs.
- [ ] Fetching a PDF containing a synthetic secret pattern gets blocked/redacted by the existing governance gate, same as any other extracted text today.
- [ ] With the optional `pdf` extra NOT installed, fetching a PDF URL still completes (falls back to jina/firecrawl or locator-only) without a stack trace.
- [ ] `rf council` output (or the CLI summary) shows both the raw ARC verdict text and a normalized `council_verdict: approve|concern|block`; an unparseable verdict shows `concern` with `normalization_confidence: low`, never a silent `approve`.
- [ ] Sealing a completed run (via whatever surface OQ-2 resolves to) produces a lineage record with a digest; editing `claim_ledger.yaml` on a sealed run and re-checking the digest shows a mismatch. An *unsealed* run can still be freely edited (`rf tail`, report iteration) with no change in behavior versus today.
- [ ] The Path-B workflow (`rf-run-execute.js`) runs successfully on this machine using explicit `--rf-bin`/`--repo`/`--tmp-dir` args in a dry run, and a `grep` for `/Users/miethe/` in the script source comes back empty.
- [ ] `./.venv/bin/python -m pytest` is green across the full suite after all six phases land, and `flake8 <src> --select=E9,F63,F7,F82` is clean.
- [ ] CHANGELOG `[Unreleased]` has entries for the new user-facing surfaces: `verify.exact_passage`, the run-seal command/flag, `extraction_status`, and the council enum.

---

## 9. Running Log

_Optional. Append-only. Short notes during execution — surprises, pivots, validated assumptions._
_Agents may append here only if explicitly instructed in a task prompt._

- [2026-07-18] Brief created from decisions block + PRD. Bottom-up H1–H6 estimation run independently: 32 pts vs decisions-block scaffold of 29 pts (~10.3% delta), driven by an H7 finding (`cli_commands.py` at 2,640 lines, touched by Phase 1 and plausibly Phase 4b) not present in the original anchors. Recommend flagging `cli_commands.py` as a High-Friction Surface when the implementation plan is authored.
