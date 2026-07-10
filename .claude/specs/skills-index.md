---
schema_version: 2
doc_type: spec
title: Skills Index
status: draft
created: 2026-04-14
updated: 2026-07-10
owner: nick
description: "Index of all custom skills in .claude/skills/ with metadata, domain ownership, and SPEC.md presence"
---

# Skills Index

## Overview

This document indexes all custom skills in the `.claude/skills/` directory with metadata about
versions, status, domain ownership, and presence of specification documents. It serves as the
authoritative catalog for skill discovery and inventory management, and as the routing table
planning uses to decide which skill "owns" a given capability area when a doc-update task lands.

**Purpose**: Provide a quick reference for all available skills, their current status, what
capability area each one owns, and documentation coverage.

**How to Read**: Each row represents one skill directory. The table columns show skill name,
version (from `SKILL.md` frontmatter), active status, SPEC.md presence (✓/✗), count of supporting
markdown files, the domain-ownership note (what capability area the skill owns — use this to route
a doc-update task to the right skill), and a one-line purpose extracted from the skill's description.

**Maintenance**: Update this index whenever a skill is added, removed, renamed, or promoted through
SPEC.md finalization. Regenerate against the actual `.claude/skills/` directory listing rather than
patching incrementally — see the correction note below.

## ⚠️ 2026-07-10 correction note

The previous version of this file (`updated: 2026-05-21`) was an **unedited copy carried over from a
sibling project** (SkillMeat). It listed 56 skills, ~15 of which do not exist anywhere in this repo
(`ccdash`, `debug`, `demo-foundry`, `html-capsules`, `meatycapture-capture`, `release`,
`skillmeat-cli`, `ui-ux-pro-max`, `changelog-sync`, `meeting-insights-analyzer`,
`similarity-search-patterns`, `skill_seekers`, `claude-agent-sdk`, and others), and it **entirely
omitted `research-foundry` and `research-foundry-swarm`** — Research Foundry's own crown-jewel
skills. This regeneration is grounded directly in the `.claude/skills/` directory listing taken
2026-07-10 (49 skill directories, verified by presence of `SKILL.md`; see Notes for the one
non-skill directory found alongside them). Follow this self-correcting-note pattern (state what was
verified on-disk vs. inherited) on future regenerations — modeled on
`.claude/specs/workflows/workflow-registry.md`, which has kept an accurate self-correcting note
since its own drift was caught.

## Legend

| Column | Meaning |
|--------|---------|
| **Skill** | Directory name in `.claude/skills/` |
| **Version** | Version from `SKILL.md` frontmatter (or "—" if not declared) |
| **Status** | `active`, `deprecated`, or other status from frontmatter (default: active) |
| **SPEC.md** | ✓ if SPEC.md exists in skill directory; ✗ if not yet created |
| **Docs** | Count of markdown files excluding SKILL.md (rough doc coverage indicator) |
| **Domain Ownership** | What capability area this skill owns — route doc-update/planning tasks here |
| **Purpose** | One-line description from SKILL.md (truncated to ~120 chars) |

## Skills Inventory (49 Total)

### RF Core — Research Foundry's own product surface (highest planning priority)

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| research-foundry | — | active | ✗ | 0 | **RF pipeline CLI reference** — the 21-step run loop + full `rf` command-route table (spot-checked 2026-07-10; see Notes) | Drives the RF control plane — idea → source discovery → claim mapping → synthesis → verification → evidence bundle via the `rf` CLI. |
| research-foundry-swarm | — | active | ✓ | 1 | **RF workspace bootstrap + swarm orchestration** (install/init, Path A/B/C discovery, deterministic tail, governance) | Installs/initializes an RF workspace from scratch, then orchestrates a Claude Code agent swarm into a claim-verified evidence bundle. |
| workflow-authoring | — | active | ✗ | 3 | **Dynamic Workflow script governance** — authoring/validating `.claude/workflows/*.js` for RF (and SkillMeat) | Governs the full procedure for authoring, extending, and validating Dynamic Workflow scripts against the master contract and per-workflow spec. |

### RF Integration — external subsystems RF writes to, reads from, or hands off to

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| council-review | — | active | ✗ | 3 | ARC review council, **offline path** — backs RF's `rf council` gate (loop step 16, exit code 7) | Runs an Agent Review Council over a product/codebase/artifact; produces evidence-backed findings, scorecard, risks, decision record. |
| council-run | — | active | ✓ | 5 | ARC run scaffolding via the **arc CLI/server** — NOT used by RF pipeline runs (reference-only cross-link from `research-foundry-swarm`) | Scaffolds an ARC run, picks a council, authors/edits council and reviewer-role YAML. |
| intenttree-cli | 1.0 | active | ✓ | 10 | Live IntentTree work-tree CLI — RF ships its own offline file-based subset (`rf intent`/`rf tree`); load this skill only when a live server is required | Drives the IntentTree work-tree via the `intenttree`/`itt` CLI (capture, decompose, claim/complete nodes, schedule). |
| meatywiki | — | active | ✓ | 13 | MeatyWiki CLI knowledge-compilation loop — RF's primary writeback target (`rf writeback --targets meatywiki`) | Drives the MeatyWiki CLI end-to-end (ingest → classify → extract → compile → file-back → lint). |
| meatywiki-author | — | active | ✓ | 5 | MeatyWiki artifact frontmatter authoring conventions | Guides authoring of markdown artifacts destined for MeatyWiki ingestion with valid routing-hint frontmatter. |
| meatywiki-suite | — | active | ✓ | 10 | Full-lifecycle MeatyWiki usage — CLI + Portal REST API + MCP server | Covers running any MeatyWiki CLI command, Portal API calls, vault CRUD, compilation, and agentic deployment. |

### Dev Workflow — building/planning/tracking Research Foundry's own codebase

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| artifact-tracking | — | active | ✗ | 30 | Progress/status tracking — `.claude/progress/` phase files, CLI-first updates | Token-efficient tracking for AI orchestration; CLI-first for status updates, agent fallback for complex ops. |
| changelog-generator | — | active | ✗ | 0 | Changelog generation from git commit history | Automatically creates user-facing changelogs from git commits, categorized and customer-friendly. |
| confidence-check | — | active | ✗ | 0 | Pre-implementation confidence gate (≥90% required) | Pre-implementation confidence assessment with duplicate check, architecture compliance, docs verification. |
| debugging | — | active | ✗ | 12 | Bug triage/remediation + post-incident retrospective (`/fix:debug`, `/fix:bugfix-commit`) | Debug and remediate bugs with severity-gated workflows; retrospective mode classifies post-merge gaps. |
| dev-execution | — | active | ✗ | 16 | `/dev:*` unified execution engine (execute-phase, quick-feature, implement-story, create-feature) | Unified execution engine for all development workflows; progressive disclosure for phase/feature/story work. |
| plan-review | — | active | ✗ | 3 | Post-implementation retrospective — estimate-vs-actual complexity, feeds tuning back into `planning` | Compares estimated story points against measured complexity; identifies which estimation heuristics failed. |
| plan-status | — | active | ✗ | 0 | Cross-feature visibility over implementation plans/PRDs/progress files | Checks what's in progress, audits stale plan statuses, summarizes active work, flags orphaned PRDs. |
| planning | — | active | ✗ | 23 | PRD / Implementation Plan / Progress Tracking authoring | Generates and optimizes PRDs, Implementation Plans, and Progress Tracking documents as AI artifacts. |
| prior-day-summary | 0.1.0 | active | ✓ | 16 | Evidence-backed "what shipped yesterday" summaries | Produces changelog-first, evidence-backed prior-day work summaries with shipped-vs-branch-local reconciliation. |
| project-context-distiller | — | active | ✗ | 10 | Codebase + supplemental-docs → research-ready context artifacts | Distills a software project into feature catalog, design fundamentals, research context pack, opportunity map. |
| project-scaffolder | — | active | ✗ | 2 | PRD/plan/dir → deployed artifact Bundle (SkillMeat-backed) | Transforms context into a deployed Bundle of artifacts via structured Intent extraction and ranked search. |
| receiving-code-review | — | active | ✗ | 1 | Discipline for evaluating (not blindly applying) code review feedback | Requires technical rigor and verification before implementing review suggestions. |
| recovering-sessions | — | active | ✗ | 6 | Crashed/interrupted Claude Code session recovery | Analyzes agent logs, verifies on-disk state, generates resumption plans for interrupted multi-agent work. |
| skill-builder | — | active | ✗ | 3 | Skill authoring/editing, subagent→skill conversion | Creates new Claude Code skills from scratch or edits existing ones; organizes supporting files. |
| skill-creator | — | active | ✗ | 0 | General guide for creating effective Claude Code skills | Guide for creating/updating skills that extend Claude's capabilities with specialized knowledge. |
| symbols | — | active | ✗ | 8 | Token-efficient codebase navigation via symbol graphs (`ai/symbols-*.json`) | Intelligent symbol loading/querying; reduces token usage 60-95% vs. loading full files. |

### Model Delegation — routing work to external CLIs/models

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| bob-shell-delegate | — | active | ✗ | 5 | IBM Bob Shell CLI delegation for bounded subtasks | Delegates bounded subtasks (drafting/scaffolding/exploration) to IBM Bob Shell CLI. |
| codex | — | active | ✗ | 1 | OpenAI Codex CLI delegation (`codex exec`/`codex resume`) | Runs Codex CLI for code analysis, refactoring, or automated editing (GPT-5.3-Codex default). |
| gemini-cli | — | active | ✗ | 6 | Google Gemini CLI orchestration — second opinion, web search, codegen, image gen | Second opinion/cross-validation, real-time web search, architecture analysis, parallel code generation. |
| notebooklm | — | active | ✗ | 0 | Full programmatic NotebookLM API (notebooks, sources, artifact generation) | Complete API for Google NotebookLM including features not in the web UI. |
| notebooklm-skill | — | active | ✗ | 6 | Query NotebookLM notebooks for source-grounded, citation-backed answers | Queries Google NotebookLM notebooks directly for hallucination-reduced, document-grounded answers. |
| notebooklm-sync | — | active | ✗ | 1 | Auto-sync markdown docs to a NotebookLM notebook on Write/Edit | Deploys/manages a hook-driven NotebookLM documentation sync system for any project. |

### Media Generation

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| nano-banana | — | active | ✗ | 0 | AI image generation (Gemini 3.1 Flash default, Pro available) | Generates AI images via the nano-banana CLI; multi-resolution, style transfer, green-screen workflow. |
| nano-banana-pro | — | active | ✗ | 0 | AI image generation/editing (Gemini 3 Pro Image) | Generates/edits images with Nano Banana Pro; text-to-image + image-to-image, 1K/2K/4K. |
| sora | — | active | ✗ | 8 | AI video generation via OpenAI's Sora API | Generates, remixes, polls, lists, downloads, or deletes Sora videos via the bundled CLI. |

### UI/Design — used when building the `frontend/runs-viewer/` SPA

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| aesthetic | — | active | ✗ | 6 | Aesthetic QA — BEAUTIFUL/RIGHT/SATISFYING/PEAK design stages | Creates aesthetically beautiful interfaces following proven design principles. |
| cognitive-design | — | active | ✗ | 9 | Cognitive-load-aware visual/dashboard/form design | Aligns interfaces, data viz, and educational content with how humans perceive and remember information. |
| design-system-patterns | — | active | ✗ | 3 | Design tokens, theming infra, component-library architecture | Builds scalable design systems with design tokens, theming, and component architecture patterns. |
| Design Principles | — | active | ✗ | 1 | Minimal design-system enforcement (Linear/Notion/Stripe-inspired) | Enforces a precise, minimal design system for dashboards/admin UIs requiring pixel-level precision. |
| frontend-design | — | active | ✗ | 1 | Production-grade frontend interface generation | Creates distinctive, production-grade frontend interfaces avoiding generic AI aesthetics. |
| interface-design | — | active | ✗ | 3 | Dashboard/app/tool interface design (not marketing design) | Interface design for dashboards, admin panels, apps, and interactive products. |

### Docs/README

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| crafting-effective-readmes | — | active | ✗ | 13 | README authoring templates matched to audience/project type | Writes/improves README files using templates and guidance matched to audience and project type. |
| managing-readmes | — | active | ✗ | 6 | README build system (Handlebars scaffold, screenshots, CI freshness) | Creates, rebuilds, or maintains a project README via a modular Handlebars build system. |

### Claude Code Meta / Generic Infra

| Skill | Version | Status | SPEC.md | Docs | Domain Ownership | Purpose |
|-------|---------|--------|---------|------|-------------------|---------|
| claude-code | 1.0 | active | ✗ | 13 | Claude Code itself — features/setup/hooks/MCP/enterprise reference | Expert reference for Claude Code — installation, slash commands, agent skills, MCP, hooks, enterprise use. |
| chrome-devtools | — | active | ✗ | 3 | Browser automation/debugging via Puppeteer CLI | Browser automation, screenshots, performance analysis, network monitoring, JS debugging. |
| better-auth | 2.0.0 | active | ✗ | 4 | TypeScript auth framework guidance (generic, not RF-specific) | OAuth/2FA/passkey/RBAC implementation guidance for the Better Auth framework. |
| clerk-install-auth | 1.0.0 | active | ✗ | 0 | Clerk SDK/CLI install (generic, not RF-specific) | Installs and configures Clerk SDK/CLI authentication and API keys. |
| devops | 2.0.0 | active | ✗ | 21 | Cloud/container deploy guidance (generic, not RF-specific) | Deploys to Cloudflare, Docker, GCP, Kubernetes with CI/CD, GitOps, security audit. |
| generating-docker-compose-files | 1.0.0 | active | ✗ | 4 | Docker Compose file generation (generic, not RF-specific) | Generates Docker Compose configurations for multi-container apps. |
| postgresql-psql | 1.0.0 | active | ✗ | 2 | psql terminal client reference (generic, not RF-specific) | Comprehensive guide for connecting, querying, and administering via the PostgreSQL psql client. |

## Notes

- **49 skill directories on disk**, all `active`, verified by `SKILL.md` presence 2026-07-10. One
  additional directory, `_meta/`, sits alongside the skills but is **not itself a skill** — it holds
  a shared `skill-authoring-guide.md` reference and has no `SKILL.md`; it is intentionally excluded
  from the inventory count and table above.
- **Directory-name / frontmatter-name mismatch**: the `Design Principles` directory (capitalized,
  with a space) declares `name: design-principles` in its own frontmatter. Listed here under its
  on-disk directory name per this index's stated convention ("Skill = directory name").
- **RF-crown-jewel gap closed**: `research-foundry`, `research-foundry-swarm`, and
  `workflow-authoring` are now listed and grouped first (RF Core) — the single most important fix
  from the prior version of this index, which omitted all three.
- **rf/research-foundry skill spot-check (2026-07-10)**: `research-foundry/SKILL.md`'s
  intent→command route table was missing the newer web-platform CLI surfaces
  (`rf catalog`, `rf workspace migrate`, `rf report`/draft Builder, `rf agent-job`, `rf audit`) —
  confirmed against `src/research_foundry/cli_commands.py` and
  `src/research_foundry/cli/commands/agent_job.py`. Added six new route-table rows plus one command
  note; the 21-step loop and existing rows were left untouched (additive fix, not a restructure).
  `research-foundry-swarm/SKILL.md` was also spot-checked: its scope (workspace bootstrap +
  Path A/B/C swarm driving) does not cover those platform surfaces, its own command inventory
  (`rf init`/`rf doctor`, `rf search`/`rf fetch`, the deterministic tail, `rf serve` governance) is
  current, and its Cross-References section already correctly links out to `research-foundry`,
  `council-review`/`council-run`, `intenttree-cli`, and the `meatywiki*` skills — **no change made**.
- **Missing SPEC.md**: 8 of 49 skills have a SPEC.md (`council-run`, `intenttree-cli`,
  `meatywiki-author`, `meatywiki-suite`, `meatywiki`, `prior-day-summary`, `research-foundry-swarm`,
  `workflow-authoring`). 41 remain without one; `research-foundry` itself — RF's primary skill — has
  no SPEC.md, which is a candidate for a future backfill pass but out of scope for this correction.
- **Generic/template skills**: the Claude Code Meta / Generic Infra, Media Generation, and several
  UI/Design and Model Delegation rows are shared dev-tooling skills carried over from the sibling
  SkillMeat project's skill set (same provenance issue as the stale index itself, per
  `docs/project_plans/exploration/web-app-platform-evolution/discovery/05-docs-intent.md`). They are
  present and functional on disk, so they remain listed, but they are not Research-Foundry-specific
  and should not be assumed to reflect RF product decisions.
