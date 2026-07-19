---
title: "Design Spec: RFUP-6 — Native Discovery Adapter Install/Eval (Deferred)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-18
updated: 2026-07-18
feature_slug: rf-upstream-evidence-foundry
prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
owner: nick
tags: [deferred, adapters, discovery, rfup-6, governance]
category: scope-cut
deferred_from: rf-upstream-evidence-foundry-v1
deferred_item_id: RFUP-6
problem_statement: "Research Foundry declares eight concrete tool adapters in adapters/__init__.py, but only arc_council (council review) is installed and live in production discovery runs; the remaining native discovery/orchestration adapters (gpt_researcher, notebooklm, openai_agents, paperqa2, opencode, litellm_router) exist as degraded-mode stubs with no installed dependency, no live credential path, and no evaluation of whether they add discovery value beyond the already-proven Path-B (Claude Code agent swarm) workflow."
open_questions:
  - "Has Path-B (the RFUP-1-parameterized Claude Code discovery swarm) been shown insufficient for a specific, evidenced discovery need — e.g., a research angle that gpt_researcher or paperqa2 would measurably handle better, demonstrated by a documented comparison run? (measured value gap)"
  - "Has a concrete downstream requirement emerged that the existing adapter set cannot satisfy, and has that requirement cleared the governance/DI-1 audit register as an approved capability gap? (security/governance gap)"
explored_alternatives: []
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
related_prds: []
---

# Design Spec: RFUP-6 — Native Discovery Adapter Install/Eval (Deferred)

> **Maturity: idea.** This is a deferral placeholder, not an implementation-ready design. It exists
> so the RFUP-6 backlog item has a durable, referenceable artifact with an explicit promotion trigger,
> per the `rf-upstream-evidence-foundry-v1` PRD §14 and the parent implementation plan's Deferred
> Items Triage Table (TASK-6.4).

## 1. Defer-until trigger

RFUP-6 (installing and evaluating any native, non-`arc_council` discovery adapter) is deferred until
**one of two conditions** becomes true. Both conditions require *evidence*, not intuition — a hunch
that "gpt_researcher would probably help" does not clear the bar.

### Condition 1 — Measured value gap

The Path-B workflow (the Claude Code agent discovery swarm, parameterized and hardened under RFUP-1
in this same plan) is shown to be **insufficient for a specific discovery need**, with evidence. This
means:

- A concrete research angle or source class exists where Path-B underperforms in a way that matters
  (missed sources, poor coverage, excessive manual curation cost, etc.).
- The gap is demonstrated via a **documented comparison run** — not a general belief that a
  purpose-built tool "should" be better. For example: running the same research brief through Path-B
  and through a native adapter (in a sandboxed evaluation, outside production) and showing the native
  adapter surfaces materially better source candidates or coverage for that specific need.
- The comparison and its evidence are captured in a report (`doc_type: report`, `report_category:
  investigation` or `finding`) that this design spec's `related_documents` should reference once it
  exists.

### Condition 2 — Security/governance gap

A **concrete downstream requirement** emerges that the existing adapter set (Path-B plus
`arc_council`) cannot satisfy, AND that requirement has been reviewed and cleared by the project's
governance process:

- A real, named downstream consumer or workflow needs a specific adapter's capability (e.g., a
  scientific-literature RAG workflow needing `paperqa2`'s local-corpus grounding, or a governed
  orchestration need matching `openai_agents`).
- The requirement has gone through the governance/DI-1 audit register (the same gate used for
  workspace-scoping and privileged-writeback review in this project) and has been cleared as an
  approved capability gap — not merely requested.
- Installing the adapter does not reintroduce a privileged-writeback or workspace-isolation surface
  that DI-1 has flagged elsewhere.

**Either condition alone is sufficient to trigger a promotion review.** Absent both, RFUP-6 stays in
`idea` maturity and no adapter installation, evaluation harness, or `adapters/__init__.py` `load_all()`
change should be made under this or any other in-flight plan.

## 2. Adapter shortlist

Six adapters are declared in `adapters/__init__.py` (`_CONCRETE` tuple) alongside the already-live
`arc_council` council-review adapter, but are not installed or live in production discovery runs
today. `load_all()` imports each lazily and silently swallows import errors, so a missing optional
dependency never breaks `research_foundry` startup — these adapters currently run in degraded/stub
mode only, producing deterministic labeled placeholders instead of live network or subprocess calls.

| Adapter | Apparent purpose/niche |
| --- | --- |
| `gpt_researcher` | Broad web-scan research discovery. Runs a wide search and returns cited findings when the `gpt_researcher` package and a key are available; intended as a source-discovery/draft-input feeder into the claim ledger, not a report writer in its own right. |
| `notebooklm` | Grounded research/Q&A sourcing via Google's NotebookLM, driven through an external CLI binary (`notebooklm-py`). Produces normalized source candidates from a research brief; its synthesized answers are stored as non-authoritative telemetry only. |
| `openai_agents` | Orchestration via the OpenAI Agents SDK. Promoted to a real-mode-capable implementation in a prior phase, but real-mode execution is currently blocked by an explicit Mode-D gate (no live API keys / live provider calls approved) — only test-double/mock-client paths are reachable today. |
| `paperqa2` | Scientific RAG over a local PDF corpus. In real mode, runs citation-grounded question-answering against a local PDF/text directory; degraded mode just lists local PDFs as labeled candidates. Niche fit: literature-heavy research briefs with a curated local corpus. |
| `opencode` | Local/open-source code agent, invoked as a CLI binary (`opencode`) rather than a Python dependency. Intended for local codebase edits/discovery; degrades to a deterministic no-op note when the binary is absent. |
| `litellm_router` | Not a discovery adapter — a model-profile routing layer. Maps a named model profile (e.g. `rf_extract_cheap`) to a concrete provider/model decision by reading `config/model_profiles.yaml`. Currently deterministic/degraded (no `litellm` package, no provider keys), so it always returns the first preferred profile entry rather than picking a live-reachable provider. |

None of these six should be installed, credentialed, or exercised in real mode until the defer-until
trigger in §1 is met.

## 3. Why deferred

Path-B — the Claude Code agent discovery swarm, now in scope and parameterized/hardened under RFUP-1
in the `rf-upstream-evidence-foundry-v1` implementation plan — is the **proven live-discovery lane**.
It already runs production research campaigns end-to-end (source discovery → claim extraction →
verification), and RFUP-1 removes its remaining machine-specific hard-coding so it is portable across
environments.

Installing any native adapter *before* Path-B is proven and stabilized would add:

- **Dependency weight** — each adapter pulls in a distinct third-party package or CLI binary
  (`gpt_researcher`, `paperqa`, `notebooklm-py`, `litellm`, the OpenAI Agents SDK, the `opencode`
  binary), each with its own maintenance and compatibility surface.
- **Security-review surface** — every adapter that reaches real mode needs credential handling review,
  a Mode-D gate check (per this project's delegation-modes rule), and — for anything touching
  workspace-scoped data — a DI-1 governance pass.

None of that investment is justified without a **demonstrated gap** that the existing Path-B lane
cannot fill. The IntentTree node for RFUP-6 states this explicitly: install/evaluate native adapters
"only after a measured value/security gap." This design spec exists so that gap, if and when it
appears, has a clear place to land instead of triggering ad hoc adapter installation.

## 4. Trigger conditions for promotion

Promotion out of this deferred state follows the same two-condition gate restated in §1, now framed
as the **concrete promotion gate**:

1. **Measured value gap** — a documented comparison run shows Path-B is measurably insufficient for a
   specific discovery need that a named native adapter would fill better.
2. **Security/governance gap** — a concrete downstream requirement for a named adapter's capability has
   been reviewed and cleared through the governance/DI-1 audit register.

When either condition is met:

1. Update this document's `maturity` field: `idea` → `shaping` (begin structuring the specific
   adapter(s) and evidence), then → `ready` once the promotion case is fully argued.
2. At `maturity: ready`, promote to a real PRD at `docs/project_plans/PRDs/[category]/` scoping the
   specific adapter(s) to install, their credential/governance handling, and an evaluation harness —
   set this spec's `maturity: promoted` and `prd_ref` to that new PRD.
3. From there, a standard implementation plan follows the normal Tier classification (adapter
   installation plus governance review is unlikely to be Tier 0/1 given the DI-1 audit dependency).

Until then, this spec remains at `maturity: idea` and the six adapters in §2 stay in degraded/stub
mode, exactly as they run today.
