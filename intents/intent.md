---
schema_version: 2
doc_type: context
status: active
created: 2026-05-27
updated: 2026-07-26
title: Research Foundry Project Intent
description: Durable orientation document for AI agents and developers. Captures why Research Foundry exists, who it serves, and what it should become. Refresh quarterly or when strategic direction changes.
---

# Research Foundry Project Intent

## Mission

Research Foundry is a Markdown/YAML-first, evidence-first research control plane: it turns raw ideas into governed research swarms, evidence bundles, and claim-verified reports, with writebacks to MeatyWiki, SkillMeat, and CCDash.

Tactically, Research Foundry is a file-backed pipeline — capture → triage → plan → ingest → extract → claim-map → synthesize → verify → bundle → writeback — where every material claim in a report either traces to a source card in a claim ledger or is explicitly labeled inference/speculation, and a deterministic verifier (not a model) decides whether a report is publishable. Strategically, it is growing into a four-surface platform around that same core: the `rf` CLI/engine, an agentic and external-system integration layer, an HTTP+MCP API, and a web app (runs-viewer) — all sharing one evidence-first center of gravity rather than fragmenting into separate tools.

Research Foundry exists because "research done with an LLM" usually means an unstructured chat transcript with unverifiable claims, no durable evidence trail, and no way to tell a supported fact from a confident guess. It closes four specific gaps: (1) LLM-generated research has no citation discipline — RF makes the claim ledger, not narrative fluency, the pass/fail bar; (2) research findings die in one tool's chat history — RF writes evidence back into the knowledge systems that already exist (MeatyWiki, SkillMeat, CCDash) instead of creating a fifth silo; (3) research pipelines are usually all-or-nothing on live network/API access — RF's core is deliberately offline-capable, degrading gracefully rather than failing when an external provider is unavailable; and (4) "governance" is usually a manual review step that gets skipped under deadline pressure — RF enforces policy, secrets, and sensitivity checks as a runtime gate in the CLI/service path itself.

## Primary Users

1. **Operator/Researcher (primary)**: The single-operator power user who runs the `rf` CLI end-to-end — launches research runs, reviews claim ledgers, reads verifier output, and pushes verified evidence into MeatyWiki/SkillMeat/CCDash. This is today's best-validated, highest-maturity user role.
2. **Small Research Team Collaborators**: A handful of trusted teammates sharing RF as a LAN or self-hosted service (`rf serve` at `10.42.10.76:7432`, token/Clerk auth, RBAC, and workspace-scoped access). They need read/authoring access scoped to their workspace without full filesystem or CLI access to the host. This remains a trusted-cohort posture, not adversarial tenant certification.
3. **Downstream Reviewers/Readers**: People who consume finished runs and reports without authoring them — via the runs-viewer's Portfolio/Run Detail/Catalog screens or a report share token — and need a trustworthy, always-available read surface that works even with no backend running (the static-export SPA).
4. **Agentic & System Integrators**: Other subsystems and agent runtimes (Claude Agent SDK swarms, MeatyWiki, SkillMeat, CCDash, and — once validated live — ARC and IntentTree) that call RF as a writeback target, evidence source, or search/fetch utility via CLI, HTTP API, or `rf-mcp`.
5. **Platform Operator/Admin**: The person configuring auth providers, RBAC roles, rate limits, and workspace isolation for a shared deployment — often the same person as (1) locally, but a distinct responsibility once RF runs as a small-team service rather than a single-user tool.

## Core Jobs To Be Done

1. **Evidence-first research**: Users want to turn a raw idea into a claim-verified report instead of an unstructured LLM chat transcript with no citation discipline.
2. **Deterministic trust**: Users want a pass/fail verdict from a deterministic verifier against a claim ledger instead of trusting an LLM's self-reported confidence in its own synthesis.
3. **Write once, land everywhere**: Users want one `rf writeback` to push verified evidence into MeatyWiki, SkillMeat, and CCDash instead of manually re-entering the same findings into three separate systems.
4. **Offline-capable research**: Users want the core pipeline (extract → claim-map → verify → bundle) to work with zero network dependency instead of a system that goes dark the moment an API key or provider is unavailable.
5. **Browse without babysitting a server**: Users want to review past runs and reports from a always-on read surface (static-export runs-viewer) instead of digging through raw YAML/markdown files or keeping a backend process alive.
6. **Governance without gatekeeping friction**: Users want policy, secrets, and sensitivity checks enforced automatically at `rf guard check` instead of a manual pre-publish review someone has to remember to run.
7. **Share without over-granting access**: Users want to hand a teammate or stakeholder a scoped report link or workspace-bound account instead of giving them full filesystem or root API access.
8. **Extend without vendor lock-in**: Users want to add a new search provider or agent runtime as a self-registering, gracefully-degrading adapter instead of hardcoding one vendor's SDK into the core pipeline.
9. **Run it as a small team, not just solo**: Users want to stand up RF as a shared LAN/self-hosted service for a handful of collaborators instead of waiting on a hosted SaaS offering that doesn't exist yet.

## Non-Goals

- Not becoming a general-purpose chatbot or open-ended conversational assistant. RF is a research pipeline with a file-canonical evidence trail; use a chat interface for open-ended conversation, not RF.
- Not a public multi-tenant SaaS in the near term. DF-004 workspace ownership, public visibility, and enforcement engineering are merged, but full adversarial shared-store multi-tenancy (self-service signup, billing, cross-tenant admin) remains a **long-term**, gated direction pending a formal DI-1 delta audit and human Mode-D signoff.
- LLM synthesis is not the source of truth. The deterministic claim ledger and verifier are authoritative; `rf synthesize --llm` never overrides the ledger-faithful report body — the flag only appends an explanatory note. Do not build features that treat raw LLM narrative output as citation-worthy.
- Not replacing MeatyWiki, SkillMeat, or CCDash. They remain the systems of record for compiled knowledge, artifacts, and dashboards respectively; RF writes evidence into them — it does not supersede or duplicate their role.
- Not treating unvalidated live integrations as production-load-bearing. ARC, IntentTree, and NotebookLM bidirectional sync are implemented against inferred external contracts but have never fired against a live remote from this repo — don't build downstream features that assume they already work end-to-end.
- Not becoming a general-purpose agent-orchestration runtime. The Agent Jobs subprocess model exists to launch bounded research swarms tied to a run, not to compete with IntentTree/aos-operator as a task-orchestration platform.
- Not over-building full web-app run-control before the auth/RBAC/workspace-isolation foundation is validated live. Phased, gated authoring (intake, plan review, monitoring first; live run-control later) is the near-term posture — not a hosted, always-available authoring commitment.

## Product Principles

1. **Files are canonical**: Markdown/YAML on disk (source cards, claim ledger, evidence bundle, telemetry trace) is the durable truth. Databases (catalog SQLite+FTS5, draft/agent-job/audit tables) are derived read models that can be rebuilt from files — never the reverse.
2. **Evidence-first, claim-ledger authority**: Every material claim in a report maps to a claim ledger entry backed by a source card, or is explicitly labeled inference/speculation. The deterministic verifier (`rf verify`) — not model output — decides whether a report passes.
3. **Cheap-extract, expensive-synthesize**: Regex/heuristic classifiers do claim extraction and classification for free; any expensive LLM call is reserved for narrative framing around an already-verified ledger, never for populating the ledger itself.
4. **Governance as a runtime gate, not a review checklist**: Policy rules, secret scanning, and sensitivity checks run deterministically inside the CLI/service path (`rf guard check`) and fail closed — enforced code, not a human step someone can skip under deadline pressure.
5. **Loopback-first**: New capability (Builder writes, agent-job launch, admin panels) ships gated behind a loopback/local-auth boundary first, and only widens to network-reachable/multi-user access once RBAC and workspace isolation are proven live — not before.
6. **Degrade, never crash, on external dependency**: Adapters (search providers, agent runtimes, ARC/IntentTree/NotebookLM) return a degraded result rather than raising when a live dependency is unavailable. Offline capability is a floor, not an edge case.
7. **Shared-schema drift is a defect, not a pattern**: Where frontend and backend currently duplicate a schema by hand (run-export fields, catalog mapping), treat the drift risk as debt to close with codegen or a shared schema source — don't add a fourth hand-synced copy.
8. **Compatibility does not establish tenant certification**: Single-user paths preserve their compatibility behavior, while the `multi_user` workspace ownership and enforcement engineering is merged. Neither code presence nor trusted-cohort acceptance establishes adversarial shared-store safety; that claim requires the formal DI-1 delta audit and human Mode-D signoff.
9. **Small-team self-host over speculative scale**: Design for "a handful of trusted collaborators on a LAN or self-hosted box" as the real near-term ceiling. Don't pre-build for hypothetical SaaS scale at the cost of the CLI core's simplicity.

## Experience Goals

- **The CLI research pipeline feels like a lab notebook with a built-in fact-checker**: capture → plan → ingest → extract → verify → bundle, ending in an unambiguous pass/fail before anything is called a "report."
- **The runs-viewer feels like a calm, read-first dashboard**: Portfolio and Run Detail are thorough and trustworthy even with zero backend running (static export), and browsing past runs never feels fragile or backend-dependent.
- **Governance failures feel like a compiler error, not a surprise**: `rf guard check` reports specific, actionable violations before a draft can publish — never a silent pass or a vague warning.
- **Writebacks feel automatic and low-friction**: once a run verifies, pushing evidence into MeatyWiki/SkillMeat/CCDash is a single command, not a manual re-authoring exercise.
- **Operating RF as a small-team service feels incremental, not risky**: turning on auth, RBAC, or workspace isolation is a deliberate, reversible flag flip with a clear default-safe fallback — never a leap of faith.
- **Extending RF with a new adapter feels purely additive**: it self-registers, degrades safely when unavailable, and never destabilizes the deterministic core pipeline underneath it.

## Long-Term Direction

The shaping product-direction authority for a public knowledge catalog,
controlled contribution, provider policy, domain-cell topology, hosted scale,
and eventual federation is
[`docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md`](../docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md).
It does not supersede the current small-team/self-hosted maturity boundary
below or authorize public deployment by itself.

- **Four-surface platform maturing in place**: the CLI/core engine, agentic integrations, HTTP+MCP API, and web app continue to harden as one coherent platform around a shared evidence-first center of gravity, rather than fragmenting into separate projects.
- **Small-team self-host is the durable service model; full multi-tenant SaaS is a long-term, gated aspiration**: RF is designed to run as a shared LAN/self-hosted service for a trusted small team — auth-on and workspace-scoped — as the near/mid-term target. DF-004 workspace engineering is merged, but a true adversarial shared-store SaaS (self-service signup, cross-tenant admin, billing) remains gated behind a formal DI-1 delta audit and human Mode-D signoff; it is not a near-term commitment.
- **Web app as both operator console and research reader**: the runs-viewer grows into a dual-purpose surface — an always-trustworthy read experience (Portfolio/Catalog/Run Detail) for anyone consuming research, and an increasingly capable operator console (Builder authoring, governance/admin panels, agent-job monitoring) for the people running RF — without collapsing the two into one undifferentiated UI.
- **Run authoring in the web app widens in phases**: intake/idea capture, plan review, and run monitoring come first as lower-risk, high-value surfaces; gated live run-control (agent-job launch) widens behind flags/roles only as auth, RBAC, and workspace isolation prove themselves against real traffic.
- **Integration breadth converts to integration depth**: ARC, IntentTree, NotebookLM, and the non-Claude research adapters move from offline-implemented to live-validated one at a time, with real first-contact testing before adding further integrations to the validated set.
- **The claim ledger and deterministic verifier remain the moat**: as every other surface grows, the evidence-first core stays the thing RF is trusted for — no future feature should dilute the guarantee that every claim in a published report is traceable to a source or explicitly labeled as inference.

## Current Priority

Convert the merged trusted-cohort substrate into an evidence-backed public program without
overstating deployment, tenant certification, owner-data qualification, or market validation.

Near-term work should prioritize:

1. **Keep current and target truth aligned**: maintain the README, intent, service contract, public-platform direction, and point-in-time status report without turning merged engineering into deployment or certification claims.
2. **Re-certify adversarial isolation**: run the formal DI-1 delta audit against current HEAD, close the remaining catalog import/stat workspace seams, and obtain human Mode-D signoff before any adversarial shared-store claim.
3. **Validate integrations at first live contact, one at a time**: ARC and IntentTree writebacks have never fired against a live remote from this repo. Pick one, exercise it for real, and fix whatever the inferred contract got wrong before adding NotebookLM or further adapters to the validated set.
4. **Keep authoring surfaces gated and discoverable-by-design**: retain the current trusted-cohort flags around `/agents` and Builder writes, make gated capabilities findable, and widen them only through the staged public plan after the applicable tenant, provider, job, and human gates clear.

The guiding priority is: **prove what is already built is trustworthy — documentation, DI-1
delta review, human signoff, and live integration contact — before widening public execution or
contribution.**
