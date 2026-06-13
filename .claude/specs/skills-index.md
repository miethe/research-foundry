---
schema_version: 2
doc_type: spec
title: Skills Index
status: draft
created: 2026-04-14
updated: 2026-05-21
owner: nick
description: "Index of all custom skills in .claude/skills/ with metadata and SPEC.md presence"
---

# Skills Index

## Overview

This document indexes all custom skills in the `.claude/skills/` directory with metadata about versions, status, and presence of specification documents. It serves as the authoritative catalog for skill discovery and inventory management.

**Purpose**: Provide a quick reference for all available skills, their current status, and documentation coverage.

**How to Read**: Each row represents one skill directory. The table columns show skill name, version (from `SKILL.md` frontmatter), active status, SPEC.md presence (✓/✗), count of supporting markdown files, and a one-line purpose extracted from the skill's description.

**Maintenance**: Update this index whenever a skill is added, removed, renamed, or promoted through SPEC.md finalization. Phase 4 will backfill SPEC.md for high-value skills; check the SPEC.md column to track progress.

## Legend

| Column | Meaning |
|--------|---------|
| **Skill** | Directory name in `.claude/skills/` |
| **Version** | Version from `SKILL.md` frontmatter (or "—" if not declared) |
| **Status** | `active`, `deprecated`, or other status from frontmatter (default: active) |
| **SPEC.md** | ✓ if SPEC.md exists in skill directory; ✗ if not yet created |
| **Docs** | Count of markdown files excluding SKILL.md (rough doc coverage indicator) |
| **Purpose** | One-line description from SKILL.md (truncated to ~120 chars) |

## Skills Inventory (56 Total)

| Skill | Version | Status | SPEC.md | Docs | Purpose |
|-------|---------|--------|---------|------|---------|
| aesthetic | — | active | ✗ | 6 | Create aesthetically beautiful interfaces following proven design principles. |
| artifact-tracking | — | active | ✗ | 30 | Token-efficient tracking for AI orchestration. CLI-first for status updates. |
| better-auth | 2.0.0 | active | ✗ | 4 | TypeScript authentication framework (framework-agnostic) with OAuth & 2FA. |
| bob-shell-delegate | — | active | ✗ | 4 | Delegate bounded subtasks to IBM Bob Shell CLI for drafting/scaffolding. |
| ccdash | — | active | ✗ | 5 | Drive CCDash CLI to answer questions about project status & agent sessions. |
| changelog-generator | — | active | ✗ | 0 | Automatically create user-facing changelogs from git commits. |
| changelog-sync | 1.0.0 | active | ✓ | 0 | Audit CHANGELOG coverage against a git range and surface gaps for remediation. |
| chrome-devtools | — | active | ✗ | 135 | Browser automation, debugging & performance analysis using Puppeteer. |
| claude-code | — | active | ✗ | 13 | Anthropic's agentic coding tool for autonomous planning & execution. |
| clerk-install-auth | 1.0.0 | active | ✗ | 0 | Install & configure Clerk SDK/CLI authentication. |
| codex | — | active | ✗ | 1 | Run Codex CLI (GPT-5.3-Codex) for code analysis & automated editing. |
| confidence-check | — | active | ✗ | 0 | Pre-implementation confidence assessment (≥90% required). |
| crafting-effective-readmes | — | active | ✗ | 13 | Use when writing or improving README files with audience-matched templates. |
| debug | — | active | ✗ | 11 | Debug & remediate bugs with severity-gated workflows & planning integration. |
| demo-foundry | 0.1.0 | active | ✓ | 7+ | Build & maintain demos as versioned executable artifacts (Playwright + Remotion + FFmpeg). |
| Design Principles | — | active | ✗ | 1 | Minimal design system inspired by Linear, Notion, Stripe. |
| dev-execution | — | active | ✗ | 18 | Unified execution engine for all development workflows & phase execution. |
| devops | 2.0.0 | active | ✗ | 21 | Deploy to Cloudflare, Docker, GCP, Kubernetes with CI/CD & GitOps. |
| frontend-design | — | active | ✗ | 1 | Create production-grade frontend interfaces with high design quality. |
| gemini-cli | — | active | ✗ | 6 | Google Gemini CLI orchestration for AI-assisted development & validation. |
| generating-docker-compose-files | 1.0.0 | active | ✗ | 4 | Generate Docker Compose configurations. |
| html-capsules | 0.1.0 | active | ✓ | 2 | Render Markdown/YAML/JSON artifacts as self-contained HTML capsules with safe-HTML enforcement. |
| managing-readmes | — | active | ✗ | 6 | Manage & maintain README files across projects. |
| meatycapture-capture | — | active | ✗ | 9 | Capture bugs/enhancements/ideas to request-logs with /mc command. |
| meeting-insights-analyzer | — | active | ✗ | 0 | Analyze meeting transcripts for communication insights & behavioral patterns. |
| nano-banana | — | active | ✗ | 0 | Generate AI images using nano-banana CLI (Gemini 3.1 Flash). |
| nano-banana-pro | — | active | ✗ | 0 | Generate/edit images with Nano Banana Pro (Gemini 3 Pro). |
| notebooklm | — | active | ✗ | 0 | Complete API for Google NotebookLM with programmatic access. |
| notebooklm-skill | — | active | ✗ | 6 | Query Google NotebookLM notebooks directly for source-grounded answers. |
| notebooklm-sync | — | active | ✗ | 1 | Synchronize with NotebookLM. |
| plan-status | — | active | ✗ | 0 | Cross-feature visibility layer for implementation plans & progress files. |
| planning | — | active | ✗ | 13 | Strategic planning & PRD creation for implementation features. |
| postgresql-psql | 1.0.0 | active | ✗ | 2 | Comprehensive guide for PostgreSQL psql terminal client. |
| prior-day-summary | 0.1.0 | active | ✓ | 16 | Produce evidence-backed prior-day summaries with shipped-vs-branch-local and visual-summary support. |
| project-context-distiller | — | active | ✗ | 10 | Distill software projects into research-ready context artifacts. |
| project-scaffolder | — | active | ✗ | 2 | Scaffold new projects/features from context using artifact bundles. |
| receiving-code-review | — | active | ✗ | 1 | Receive & evaluate code review feedback with technical rigor. |
| recovering-sessions | — | active | ✗ | 6 | Recover from crashed or interrupted Claude Code sessions. |
| release | 1.0.0 | active | ✓ | 0 | End-to-end release orchestration (version bump, regen openapi/SDK, audit coverage, rollover changelog, commit/tag). |
| similarity-search-patterns | — | active | ✗ | 1 | Implement efficient similarity search with vector databases. |
| skill_seekers | — | active | ✗ | 0 | Automatically detect source types and build AI skills. |
| skill-builder | — | active | ✗ | 3 | Create new Claude Code skills from scratch or edit existing ones. |
| skill-creator | — | active | ✗ | 0 | Guide for creating effective skills that extend Claude's capabilities. |
| skillmeat-cli | 1.2.1 | active | ✓ | 20 | SkillMeat CLI orchestration & artifact management (v0.49+: per-user API keys). |
| sora | — | active | ✗ | 8 | Generate, remix, poll, download Sora videos via OpenAI API. |
| symbols | — | active | ✗ | 8 | Token-efficient codebase navigation through intelligent symbol loading. |
| ui-ux-pro-max | — | active | ✗ | 0 | UI/UX design intelligence with 50+ styles, palettes, fonts & charts. |

## Notes

- **No Deprecations**: All 56 skills are currently in `active` status.
- **Missing SPEC.md**: 8 skills (`release`, `changelog-sync`, `demo-foundry`, `html-capsules`, `skillmeat-cli`, `claude-agent-sdk`, `prior-day-summary`) now have SPEC.md documents (skillmeat-cli added in v0.49); 48 remaining without specs. Phase 4 will backfill high-value specs.
- **Missing Versions**: 33 skills lack declared versions in SKILL.md frontmatter. Consider adding `version: x.y.z` to SKILL.md for better versioning practices.
- **Doc Coverage**: Skills range from 0–135 supporting markdown files. High-count skills (e.g., `artifact-tracking` with 30, `chrome-devtools` with 135) indicate mature implementations with extensive reference documentation.

## Phase 4: SPEC.md Finalization

During Phase 4 of `.claude/plans/skill-spec-convention-and-skillmeat-cli-refresh.md`, high-value skills will receive SPEC.md documents outlining:

- Official skill interface (inputs, outputs, responsibilities)
- Integration points with other skills
- Quality criteria & acceptance standards
- Deprecation/sunset policies

Check back to this index for ✓ marks as SPEC.md coverage increases.
