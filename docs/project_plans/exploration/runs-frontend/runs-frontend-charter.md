---
schema_version: 2
doc_type: exploration_charter
title: "Research Foundry Runs Frontend — Exploration Charter"
status: concluded
created: 2026-06-19
feature_slug: runs-frontend
timebox_days: 3
hypothesis: "We believe a frontend web app for viewing Research Foundry runs is worth
  building because a run's artifacts (raw idea, source candidates/cards, claim ledger,
  evidence bundles, governance verdicts, reports, writebacks) are rich and file-backed
  but today only inspectable via the rf CLI or raw markdown/YAML, and an interactive
  viewer would make claim→evidence provenance and verification status legible at a
  glance."
deal_killer: "If the complete run entity model cannot be derived deterministically
  from existing on-disk artifacts plus rf CLI output — i.e., a faithful read-only
  viewer would require a new always-on backend service or an LLM on the recall path,
  violating the AOS file-first / no-LLM-on-recall / loopback-only constraints — abandon
  in favor of enriching the existing MkDocs/CLI surfaces."
investigation_legs:
- id: tech
  question: Enumerate the COMPLETE run entity model from RF's on-disk artifacts 
    + rf CLI + symbol graph (every entity a run can contain, its fields, 
    relationships, and lifecycle states). Is a faithful read-only viewer 
    feasible inside the file-first architecture, and what is the read path? 
    Identify integration points and a story-point ROM.
  assigned_to: spike-writer
- id: value
  question: Who consumes RF runs today, and what jobs-to-be-done are unmet by 
    the rf CLI and the static MkDocs case-study site? Which run entities most 
    need visual display (e.g., claim-ledger verification, evidence provenance, 
    governance verdicts), and what are the top 3 viewing workflows a frontend 
    must nail?
  assigned_to: ux-researcher
- id: risk
  question: What are the top risks of building a runs frontend against RF's 
    file-first / loopback-only / no-LLM-on-recall constraints? Assess data-shape
    volatility (markdown/YAML schemas drifting), read-path coupling, blast 
    radius on the rf CLI contract, and operational/maintenance cost. Confirm or 
    refute the charter deal_killer.
  assigned_to: backend-architect
- id: priorart
  question: 'Find reusable internal precedent for the read path and UI: sibling AOS
    web apps (CCDash, IntentTree web, SkillMeat web, MeatyWiki Portal) and the new
    RF MkDocs site — their stack, data-loading patterns, and component reuse. Find
    external run/pipeline-viewer patterns. Recommend the single best H5 estimation
    anchor and a build-vs-adapt call.'
  assigned_to: search-specialist
verdict_criteria:
  go:
  - Technical leg enumerates a complete, stable run entity model from on-disk 
    artifacts + rf CLI with confidence >= 0.7
  - A read path exists that respects file-first / no-LLM-on-recall (static 
    export or loopback read API) — deal-killer NOT triggered
  - Value leg confirms >= 1 concrete viewing JTBD unmet by the CLI and MkDocs 
    site
  no_go:
  - 'Deal-killer triggered: entity model not derivable without an always-on service
    or LLM on the recall path'
  - Technical leg reports infeasibility with confidence >= 0.8
  conditional:
  - Entity model is derivable but a specific machine-readable contract (e.g., 
    `rf run export --json` schema) must be authored first — named as the 
    concrete next step
verdict: go
verdict_rationale: 'All three go criteria met: tech leg enumerated a complete 29-entity
  run model derivable from files (0.82); deal-killer REFUTED by risk leg (no always-on
  service, no LLM on recall); value leg confirmed unmet claim-audit JTBD (0.82). Strong
  reuse (priorart 0.88, fork IntentTree Web). Export contract (rf run export/list
  --json) is a Phase-1 build precondition, not a verdict blocker. Tier 2, ~13 pts.'
output_artifacts: []
updated: '2026-06-19'
---

# Research Foundry Runs Frontend — Exploration Charter

## Hypothesis Context

RF is a Markdown/YAML-first, evidence-first research control plane. A "run" accretes a dense set of governed artifacts — but the only ways to inspect a run today are the `rf` CLI and reading raw files, plus a static MkDocs case-study site (committed 2026-06-19). The operator runs swarms regularly (per memory: Path-B swarms, KnitWit packs, roots waves) and re-runs `rf verify` to trust bundles. The value bet is that an interactive viewer makes claim→evidence provenance, verification gates, and governance verdicts legible at a glance — turning a pile of files into a navigable run. The core unknown the user named explicitly: **what are all the entities a run can contain, and how should each be displayed?**

---

## Investigation Legs

### Leg: tech — Run Entity Model + Read-Path Feasibility (CORE)

**Question**: (see frontmatter) Enumerate the complete run entity model and assess read-only viewer feasibility.
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/runs-frontend/spikes/tech-findings.md`

- Enumerate EVERY entity: raw_idea, research intent/brief, source_candidates, source_cards, deep-reading notes, claim ledger entries (`clm_NNN`), evidence bundles, governance/key-profile verdicts, secret-scan results, reports/drafts, writeback targets (MeatyWiki/SkillMeat/CCDash), swarm/subagent run records, cost/telemetry, AAR.
- For each: fields, on-disk location/format, relationships, lifecycle states, and display affordances.
- Read path: static export vs loopback read API vs direct file read; honor file-first + no-LLM-on-recall.
- ROM story points + H5 anchor if one exists; OQ-* for unresolved architecture decisions.

### Leg: value — Viewing JTBD & Display Priorities

**Question**: (see frontmatter)
**Assigned to**: `ux-researcher`
**Expected output**: `docs/project_plans/exploration/runs-frontend/spikes/value-findings.md`

- Consumers (operator-first; possible downstream readers). Counterfactual: what the CLI + MkDocs site already cover.
- Rank entities by display value; define the top 3 viewing workflows (e.g., audit a claim, trace evidence, review a verdict).

### Leg: risk — Constraints, Blast Radius, Deal-Killer Test

**Question**: (see frontmatter)
**Assigned to**: `backend-architect`
**Expected output**: `docs/project_plans/exploration/runs-frontend/spikes/risk-findings.md`

- AOS constraints (file-first canonical, loopback-only, no-LLM-on-recall, CLIs are the contract).
- Schema-drift / read-path coupling risk; maintenance cost. Confirm/refute deal_killer.

### Leg: priorart — Reusable Precedent + Estimation Anchor

**Question**: (see frontmatter)
**Assigned to**: `search-specialist`
**Expected output**: `docs/project_plans/exploration/runs-frontend/spikes/priorart-findings.md`

- Sibling AOS web apps + RF MkDocs site: stack, data-loading, reusable components. External run-viewer patterns. Best H5 anchor + build-vs-adapt.

---

## Verdict Criteria Narrative

**Go** if: the run entity model is fully enumerated and stable, a read path honoring file-first/no-LLM-on-recall exists, and at least one viewing JTBD is unmet by today's CLI + MkDocs surfaces.
**No-go** if: the deal-killer fires — a faithful viewer demands an always-on service or LLM on the recall path — or the technical leg reports infeasibility (≥0.8).
**Conditional** if: the model is derivable but needs a machine-readable export contract authored first; the brief names that contract and the next command.

---

## Out of Scope

- Writeback/editing of runs from the UI (read-only viewer for v1).
- Authoring/launching new runs from the UI (CLI/swarm remains the run trigger).
- Multi-user auth, hosting beyond loopback/LAN.

---

## Citations / Prior Art

- RF MkDocs site + 18-run case study (commit 1ae5bff, 2026-06-19).
- AOS eight constraints (universal persona memory): files canonical, loopback only, no LLM on recall path, CLIs are the contract.
- RF run execution = Path-B swarm (project memory) — run lifecycle, `rf verify` gate.
- Sibling AOS web apps: CCDash UI, IntentTree web, SkillMeat web, MeatyWiki Portal (global CLAUDE.md).

---

## Notes

- 2026-06-19: Charter scaffolded via `/plan:explore`; all four legs selected (greenfield, high-uncertainty, Tier 3 candidate).
