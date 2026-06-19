---
title: "Implementation Plan: Research Foundry Docs Site + Flagship Case Study"
schema_version: 2
doc_type: implementation_plan
status: approved
created: 2026-06-19
updated: 2026-06-19
feature_slug: docs-site-case-study
feature_version: "v1"
prd_ref: null
plan_ref: null
scope: "Stand up a MkDocs Material GitHub Pages site for Research Foundry, with the 18/18 HIGH-priority verified-green wave as the centerpiece case study."
effort_estimate: "10–12 pts"
architecture_summary: null
related_documents:
  - docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md
  - README.md
category: infrastructure
priority: medium
risk_level: low
owner: nick
tags: [docs-site, mkdocs, github-pages, case-study, infrastructure]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - website/mkdocs.yml
  - website/docs/
  - .github/workflows/docs.yml
  - pyproject.toml
  - website/README.md
wave_plan:
  serialization_barriers:
    - pyproject.toml
  phases:
    - id: P1
      depends_on: []
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - website/mkdocs.yml
        - website/README.md
        - .github/workflows/docs.yml
        - pyproject.toml
    - id: P2
      depends_on: [P1]
      isolation: shared
      parallelizable: true
      owner_skills: []
      files_affected:
        - website/docs/why.md
        - website/docs/concepts/pipeline.md
        - website/docs/concepts/claim-model.md
        - website/docs/concepts/governance.md
        - website/docs/concepts/artifacts.md
        - website/docs/quickstart.md
        - website/docs/reference/cli.md
        - website/docs/reference/run-artifacts.md
        - website/docs/about.md
    - id: P3
      depends_on: [P1]
      isolation: shared
      parallelizable: true
      owner_skills: []
      files_affected:
        - website/docs/index.md
        - website/docs/case-study/index.md
        - website/docs/case-study/one-run.md
        - website/docs/case-study/the-wave.md
        - website/docs/case-study/what-it-enables.md
        - website/docs/case-study/artifacts-appendix.md
    - id: P4
      depends_on: [P2, P3]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected: []
  waves:
    - [P1]
    - [P2, P3]
    - [P4]
---

# Implementation Plan: Research Foundry Docs Site + Flagship Case Study

**Plan ID**: `IMPL-2026-06-19-DOCS-SITE-CASE-STUDY`
**Date**: 2026-06-19
**Author**: Implementation Planner
**Human Brief**: N/A — not created (docs site; PRD intentionally skipped per YAGNI)
**Related Documents**:
- **Approved plan**: `/Users/miethe/.claude/plans/delightful-whistling-nest.md` (primary source; read before executing any phase)
- **Source AAR**: `docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md`
- **Root README**: `README.md`
- **Source intents**: `intents/intent.md`

**Complexity**: Medium
**Total Estimated Effort**: 10–12 pts
**Target Timeline**: 1–2 weeks (sequential P1, then P2+P3 in parallel, then P4)

---

## Executive Summary

Research Foundry has no public-facing documentation site despite having a production-proven pipeline: 18/18 HIGH-priority backlog items run end-to-end as verified-green evidence bundles (~1,677 material claims, zero unsupported, zero contradicted). This plan stands up a MkDocs Material site under `website/` deployed to GitHub Pages, with an adapted content section covering why/concepts/quickstart/reference and a layered flagship case study showing exactly how RF turns a raw research idea into a governed, claim-verified report — traced through RIB-002 as the single walked run. Content is adapted from committed sources (`README.md`, `intents/intent.md`, `SPEC.md`, `SERVICE_CONTRACT.md`, the AAR); the case study is the only section requiring meaningful net-new synthesis.

---

## Problem / Goals / Success Criteria

### Problem

Research Foundry has a strong `README.md` and a set of planning documents under `docs/projects/research-foundry/`, but no public SSG site and no GitHub Pages workflow. A first-time visitor sees a wall of CLI output and no clear narrative. The 18/18 roots+dependent wave — the best proof that the pipeline works — is locked in an internal AAR. There is no guided entry point for practitioners who want to understand the mechanism, evaluate whether RF fits their workflow, or reproduce the approach.

### Goals

1. Give RF a real docs site that explains the value, the mechanism, and the evidence in three audience layers: casual visitor (hook), practitioner (concepts + quickstart), and sceptic (case study + artifact excerpts).
2. Showcase the 18/18 HIGH-priority wave (roots wave 10/10, dependent wave 8/8 — documented in `docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md`) as a durable proof artifact.
3. Establish a repeatable docs pipeline (MkDocs Material + GH Actions + `--strict` link-checking) so future contributors can add pages without breakage.

### Success Criteria

- `mkdocs build -f website/mkdocs.yml --strict` exits 0 (no broken links, no missing nav pages).
- Every statistic quoted in the case study traces to a committed source file or the AAR — zero invented numbers.
- A first-time visitor can read Home → Why → one Concept → Quickstart → Case Study index without a dead link.
- GitHub Pages deployment workflow runs on push to `main` (paths: `website/**`) and publishes the site successfully after the one-time Pages source toggle.

---

## Scope

### In Scope

- `website/` directory: `mkdocs.yml`, `docs/` (all pages per the IA below), `README.md`.
- `.github/workflows/docs.yml`: GH Actions build + Pages deployment.
- `pyproject.toml` edit: add `[project.optional-dependencies] docs = [...]` group.
- ~16 Markdown pages across Home, Why, Concepts (×4), Quickstart, Case Study (×5), Reference (×2), About.
- Mermaid diagrams for the pipeline loop and single-run artifact flow (rendered natively via Material).
- Real artifact excerpts in the appendix page, each with a `view full file` GitHub source link.

### Out of Scope

- Live writeback validation — still deferred per project memory (`notebooklm-integration-offline.md`, `arc-intenttree-integrations-untested-live.md`).
- Migrating internal planning docs under `docs/projects/` into the public site — those paths are referenced widely in `CLAUDE.md`, memory, and AARs; leave them in place.
- Custom domain, analytics, or versioned docs — can follow as a later enhancement.
- Any edits to files outside `website/`, `.github/workflows/`, and `pyproject.toml`.

---

## Implementation Strategy

### Approach

Self-contained MkDocs Material site under a new `website/` directory (its own `mkdocs.yml` + `website/docs/`), leaving the existing `docs/` tree untouched. GitHub Actions deploys to Pages on push to `main` (paths: `website/**`). Content is predominantly adapted from `README.md`, `intents/intent.md`, `SPEC.md`, `SERVICE_CONTRACT.md`, and the AAR — subagents receive source file paths, not contents. The case study is the only section requiring synthesis from multiple committed run artifacts.

### Parallel Work Opportunities

Phases 2 and 3 are fully independent after Phase 1 lands the nav skeleton (`mkdocs.yml` with the full `nav:` block). The documentation-writer agent (adapted content) and documentation-complex agent (flagship case study) can run concurrently without file conflicts.

### Critical Path

Phase 1 (tooling) → Phase 4 (verification). Phase 1 must complete before Phase 2 and 3 can start because the `nav:` section in `mkdocs.yml` defines which pages the strict build requires to exist.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Notes |
|-------|-------|----------|--------------------|-------|-------|
| 1 | Site Tooling & Deploy | 2 pts | python-backend-engineer | sonnet | Includes full nav skeleton so P2/P3 know all filenames |
| 2 | Adapted Content Pages | 3–4 pts | documentation-writer | haiku | 9 pages from README/intents/SPEC; runs parallel with P3 |
| 3 | Flagship Case Study | 4 pts | documentation-complex | sonnet | 5 pages synthesized from AAR + run dir; runs parallel with P2 |
| 4 | Verification & Deploy | 1–2 pts | (Opus/sonnet, human) | sonnet | Strict build, stat cross-check, Pages source toggle |
| **Total** | — | **10–12 pts** | — | — | — |

---

## Phase Breakdown

### Phase 1: Site Tooling & Deploy

**Duration**: ~0.5 day
**Dependencies**: None
**Assigned Subagent(s)**: `python-backend-engineer`
**Source reference**: Approved plan §1 (`/Users/miethe/.claude/plans/delightful-whistling-nest.md`)

Create the MkDocs Material configuration, GitHub Actions Pages workflow, pyproject.toml docs extra, and a website README. The `mkdocs.yml` must include the complete `nav:` block for all pages (even stubs) so the strict build in Phase 4 can validate the full IA without errors from missing nav entries.

| Task ID | Task | Description | Assigned Subagent(s) | Model | Effort | Acceptance Criteria |
|---------|------|-------------|----------------------|-------|--------|---------------------|
| SITE-001 | `website/mkdocs.yml` | MkDocs Material config: theme, full nav (all pages), Mermaid via `pymdownx.superfences`, search, repo link, palette toggle, admonitions/tabs/snippets. Nav must enumerate every page in the IA (including stubs) so strict build passes. | python-backend-engineer | sonnet | adaptive | `mkdocs build -f website/mkdocs.yml --strict` exits 0 against stub pages; all nav sections present. |
| SITE-002 | `.github/workflows/docs.yml` | GH Actions workflow: on push to `main` (paths: `website/**`), pip-install docs group, `mkdocs build -f website/mkdocs.yml --strict`, upload artifact, `actions/deploy-pages`. Permissions: `pages: write`, `id-token: write`. | python-backend-engineer | sonnet | adaptive | Workflow YAML valid; build step uses `--strict`; deploy step uses official `actions/deploy-pages`. |
| SITE-003 | `pyproject.toml` docs extra | Add `[project.optional-dependencies] docs = ["mkdocs-material", "pymdown-extensions"]` to existing `pyproject.toml`. | python-backend-engineer | sonnet | adaptive | `pip install -e ".[docs]"` installs `mkdocs-material` and `pymdown-extensions` without error. |
| SITE-004 | `website/README.md` | One-liner local dev instructions: `pip install -e ".[docs]"` + `mkdocs serve -f website/mkdocs.yml`. | python-backend-engineer | sonnet | adaptive | README present; commands match what `pyproject.toml` and `mkdocs.yml` require. |

**Phase 1 Quality Gates:**
- [ ] `mkdocs build -f website/mkdocs.yml --strict` exits 0 against stub pages
- [ ] All nav entries in `mkdocs.yml` have a corresponding (possibly stub) `.md` file
- [ ] `pyproject.toml` docs extra installs without conflict
- [ ] `docs.yml` workflow uses official `actions/deploy-pages` with correct permissions block

---

### Phase 2: Adapted Content Pages

**Duration**: ~0.5–1 day (parallel with Phase 3)
**Dependencies**: Phase 1 complete (nav skeleton in `mkdocs.yml`)
**Assigned Subagent(s)**: `documentation-writer` (haiku)

Adapt content from committed source files into the public site pages. Subagent receives source file paths; it reads them itself and adapts (does not copy verbatim). No net-new claims — content must be traceable to its source.

**Source files for this phase** (pass as paths, not contents):
- `README.md` — primary source for pipeline overview, concepts, CLI reference, quickstart
- `intents/intent.md` — problem framing, mission, users, JTBD (for `why.md`)
- `SPEC.md` — governance model, policy gate, sensitivity tiers (for `concepts/governance.md`)
- `SERVICE_CONTRACT.md` — artifact types, integrations (for `concepts/artifacts.md`, `about.md`)

| Task ID | Task | Description | Assigned Subagent(s) | Model | Effort | Acceptance Criteria |
|---------|------|-------------|----------------------|-------|--------|---------------------|
| CONT-001 | `website/docs/why.md` | Why Research Foundry: problem (LLM fabrication, ungoverned research), thesis (evidence-first, claim ledger as authority). Source: `intents/intent.md` + `README.md`. | documentation-writer | haiku | adaptive | Explains the problem and RF's thesis; no invented claims; links to concepts pages. |
| CONT-002 | `website/docs/concepts/pipeline.md` | The 11-step loop (capture → … → writeback) + Mermaid flow diagram. Source: `README.md` demo loop section. | documentation-writer | haiku | adaptive | Loop steps accurate; Mermaid diagram renders; cross-links to `claim-model.md`. |
| CONT-003 | `website/docs/concepts/claim-model.md` | Four claim states (supported/inference/speculation/unresolved) + the verify gate mechanic. Source: `README.md`. | documentation-writer | haiku | adaptive | States defined accurately; `rf verify` exit codes explained; no invented behavior. |
| CONT-004 | `website/docs/concepts/governance.md` | Key profiles, policy gate, sensitivity tiers, secret scanning. Source: `README.md` + `SPEC.md`. | documentation-writer | haiku | adaptive | Sensitivity tiers match `SPEC.md`; policy gate behavior described accurately. |
| CONT-005 | `website/docs/concepts/artifacts.md` | Run-directory anatomy: every file type and its role. Source: `SERVICE_CONTRACT.md` + a real `runs/` directory listing. | documentation-writer | haiku | adaptive | All run-directory files enumerated accurately; matches actual committed run structure. |
| CONT-006 | `website/docs/quickstart.md` | Install + demo loop (copy-paste). Source: `README.md` "Install & quickstart" section. | documentation-writer | haiku | adaptive | Commands copy-paste correctly; matches `pyproject.toml` install method; no placeholder steps. |
| CONT-007 | `website/docs/reference/cli.md` | `rf` command reference: capture/triage/plan/ingest/extract/ledger/synthesize/verify/bundle/writeback. Source: `README.md` + `src/` CLI. | documentation-writer | haiku | adaptive | All top-level `rf` subcommands present; flags accurate; no undocumented invention. |
| CONT-008 | `website/docs/reference/run-artifacts.md` | File-by-file reference for a run directory. Source: `SERVICE_CONTRACT.md` + schemas. | documentation-writer | haiku | adaptive | Each artifact file documented with schema reference; consistent with CONT-005. |
| CONT-009 | `website/docs/about.md` | Status (MVP), links to AARs, repo, integrations (MeatyWiki/SkillMeat/CCDash/NLM). Source: `README.md`, `SERVICE_CONTRACT.md`. Note live writeback still unvalidated. | documentation-writer | haiku | adaptive | Integration status is accurate; caveats for unvalidated live targets are present. |

**Phase 2 Quality Gates:**
- [ ] All 9 pages exist and are non-stub
- [ ] No invented statistics, commands, or behaviors — every claim traces to a source file
- [ ] `mkdocs build -f website/mkdocs.yml --strict` still exits 0 after Phase 2 pages are added
- [ ] Internal cross-links between pages use relative paths (not absolute URLs)

---

### Phase 3: Flagship Case Study

**Duration**: ~1 day (parallel with Phase 2)
**Dependencies**: Phase 1 complete (nav skeleton in `mkdocs.yml`)
**Assigned Subagent(s)**: `documentation-complex` (sonnet)

Synthesize the flagship case study from committed run artifacts and the AAR. RIB-002 (`runs/rf_run_20260614_what_does_the_empirical_literature_say/`) is the single traced run — deliberately meta: RF using its own evidence discipline to research hallucination mitigation, the exact problem RF exists to solve.

**Source files for this phase** (pass as paths, not contents):
- `docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md` — aggregate stats, per-run results table, all findings sections
- `runs/rf_run_20260614_what_does_the_empirical_literature_say/` — RIB-002 run directory (all artifacts)
- `README.md` — framing context

**Accuracy constraint**: Every statistic in the case study (claim counts, verification status, token costs, source counts) must be pulled verbatim from the committed AAR or from a file in the RIB-002 run directory. No rounding or estimation unless the source itself estimates.

| Task ID | Task | Description | Assigned Subagent(s) | Model | Effort | Acceptance Criteria |
|---------|------|-------------|----------------------|-------|--------|---------------------|
| CS-001 | `website/docs/index.md` | Home / value landing: hook + the 18/18 headline result, "Why it's different," call-to-action links to case study and quickstart. Stats from AAR §1. | documentation-complex | sonnet | adaptive | 18/18 result prominently stated; stats sourced from AAR §1; CTA links to case-study/index and quickstart. |
| CS-002 | `website/docs/case-study/index.md` | Case study overview: what was attempted (all 18 items), the headline results table (18/18 verified green, 0/0 unsupported/contradicted, total claims, total cost estimate), and why it matters. From AAR §1. | documentation-complex | sonnet | adaptive | Results table numbers match AAR §1 exactly; aggregate claim counts match; 18/18 result stated with 0 unsupported. |
| CS-003 | `website/docs/case-study/one-run.md` | Single-run walkthrough: trace RIB-002 through every artifact in order with a Mermaid artifact-flow diagram + short real excerpts at each stage. Stages: `research_brief.md` → `routing_decision.yaml`/`swarm_plan.yaml` → source cards → extractions → claim ledger → report draft → `reviews/verification.yaml` → `evidence_bundle.yaml` → writeback candidates. | documentation-complex | sonnet | extended | Each artifact stage present with a real (not invented) excerpt from the committed RIB-002 run dir; Mermaid flow matches the artifact sequence; 95 claims and 12 sources match AAR §1 RIB-002 row. |
| CS-004 | `website/docs/case-study/the-wave.md` | The full 18-run wave: roots (10/10) + dependent (8/8) per-run results tables, grouped findings (quality/verification, orchestration/storage, governance/calibration), cross-run convergence summary, stable cost profile (~1.22M tokens/bundle), RIB-018 false-pass caught and fixed. From AAR §1–4, §6. | documentation-complex | sonnet | extended | Per-run results tables match AAR §1 and §6.2 exactly; cost figures match AAR §2 / §6.4; RIB-018 false-pass described accurately. |
| CS-005 | `website/docs/case-study/what-it-enables.md` | Actionable RF outputs: quality_score formula (RIB-042), SkillBOM lifecycle fields (RIB-051), key-isolation tightenings (RIB-018), context-persistence gap (RIB-025). Plus honest caveats: live writeback unvalidated; spend exposure per monthly cap. From AAR §5. | documentation-complex | sonnet | adaptive | All four actionable items present with correct references; caveats on live writeback and spend included. |
| CS-006 | `website/docs/case-study/artifacts-appendix.md` | Real committed artifact excerpts: one source card, one claim-ledger entry showing `[claim:clm_NNN]` provenance, the `reviews/verification.yaml` checks block, one writeback candidate file. Each with a "view full file" GitHub source link pointing to the committed path. Excerpts only — do not dump full files. | documentation-complex | sonnet | extended | All four excerpts are from real committed files in the RIB-002 run dir; GitHub source links are well-formed; no invented content. |

**Phase 3 Quality Gates:**
- [ ] All 6 pages (including `index.md`) exist and are non-stub
- [ ] Every statistic cross-checked against AAR §1, §2, §6.2, §6.4 — zero invented numbers
- [ ] RIB-002 artifact excerpts in CONT-006 trace to actual committed files in `runs/rf_run_20260614_what_does_the_empirical_literature_say/`
- [ ] GitHub source links in `artifacts-appendix.md` use correct repo-relative paths
- [ ] `mkdocs build -f website/mkdocs.yml --strict` still exits 0 after Phase 3 pages are added

---

### Phase 4: Verification & Deploy

**Duration**: ~0.5 day
**Dependencies**: Phases 2 and 3 complete
**Assigned Subagent(s)**: sonnet (or Opus for the stat cross-check pass); human for the one-time Pages source toggle

This phase is primarily verification, not authoring. The goal is a clean strict build, a manual accuracy review of case-study stats, and triggering the first live deployment.

| Task ID | Task | Description | Assigned Subagent(s) | Model | Effort | Acceptance Criteria |
|---------|------|-------------|----------------------|-------|--------|---------------------|
| VER-001 | Strict build validation | Run `pip install -e ".[docs]"` then `mkdocs build -f website/mkdocs.yml --strict`. Fix any broken internal links or missing nav page references until exit 0. | (executor) | sonnet | adaptive | `mkdocs build --strict` exits 0 with zero warnings about missing files or broken links. |
| VER-002 | Local serve spot-check | Run `mkdocs serve -f website/mkdocs.yml`. Manually verify: Home page renders, case-study walkthrough readable, at least two Mermaid diagrams render, no 404s on nav links. | (human/executor) | sonnet | adaptive | All pages reachable via nav; Mermaid diagrams visible; no console errors about missing assets. |
| VER-003 | Case-study accuracy cross-check | Cross-check every statistic and artifact excerpt in `website/docs/case-study/` against the committed AAR (`aars/roots-wave-high-priority-runs-aar-2026-06-14.md`) and the RIB-002 run directory. Flag any invented or approximated numbers. | (executor) | sonnet | extended | All claim counts, verification statuses, token figures, and source counts in the case study match their committed sources exactly. |
| VER-004 | GitHub Pages source toggle | One-time manual step: set repo Settings → Pages → Source = GitHub Actions. Then push to `main` and confirm the deployed `*.github.io` URL renders the site. | (human) | — | — | Site accessible at the GitHub Pages URL; deployed content matches local build. |

**Phase 4 Quality Gates:**
- [ ] `mkdocs build -f website/mkdocs.yml --strict` exits 0
- [ ] All Mermaid diagrams render in local serve
- [ ] Zero invented statistics in case study (cross-check complete)
- [ ] GitHub Pages deployment live and accessible

---

## Verification

Full verification steps (reference: approved plan §Verification):

1. `pip install -e ".[docs]"` — installs `mkdocs-material` + `pymdown-extensions` from the `docs` optional group.
2. `mkdocs build -f website/mkdocs.yml --strict` — must exit 0; this is the link-integrity gate and CI enforcer.
3. `mkdocs serve -f website/mkdocs.yml` — spot-check Home, case-study walkthrough, Mermaid diagrams render, no dead nav links.
4. **Stat cross-check**: verify every claim count, verification status, token figure, and source count in `website/docs/case-study/` against `docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md` and the committed run artifacts under `runs/rf_run_20260614_what_does_the_empirical_literature_say/`. No number may be invented or approximated without an explicit `(estimated)` qualifier sourced from the AAR.
5. Validate the `.github/workflows/docs.yml` workflow by inspection (or with `act`); after merging to `main`, set Pages source = GitHub Actions and confirm the published URL renders.

---

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Strict-build broken links | Blocks deployment | Medium | Phase 1 requires full nav skeleton; VER-001 is a dedicated fix pass before deploy |
| Invented stats in case study | Undermines credibility; violates RF's own evidence discipline | Medium | VER-003 cross-check every figure against committed AAR and run-dir files; documentation-complex agent instructed to quote verbatim from sources |
| `repo_url` guesswork in `mkdocs.yml` | Wrong GitHub source links in appendix | Low | Executor reads the actual remote from `git remote -v` before writing `mkdocs.yml`; appendix links use repo-relative paths, not assumed URL |
| RIB-002 run directory incomplete | Missing artifact stages break the walkthrough | Low | Run directory is already committed; executor lists `runs/rf_run_20260614_what_does_the_empirical_literature_say/` before authoring CS-003 |
| `pyproject.toml` edit conflict | Breaks existing install | Low | Edit is additive only (new optional-deps group); does not touch existing groups |

---

## Deferred Items

| Item | Reason Deferred | Trigger for Promotion |
|------|-----------------|-----------------------|
| Live writeback validation | Deferred by operator decision; live HTTP targets (arc/intenttree) unreachable | First confirmed live writeback session |
| Custom domain / analytics / versioning | YAGNI for v1 | Explicit operator request |
| Migration of `docs/projects/` into public site | Would break widely-referenced paths in CLAUDE.md, memory, AARs | Deliberate decision not to attempt |

---

*This plan is already in progress in worktree `.claude/worktrees/docs-site-case-study`. Status: approved / in-progress.*
