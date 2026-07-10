---
doc_type: report
report_category: investigation
title: "Docs, Skills, and INTENT Surface Inventory — Staleness Assessment for Web-App/Platform Evolution"
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
---

# Docs, Skills, and INTENT Surface Inventory

Scope: inventory Research Foundry's documentation surface, project-level skills/commands, and the
INTENT/mission doc, then flag staleness relative to the app's evolution from a "7-day MVP CLI" into
a CLI + agentic + web-app + public multi-user service. This feeds a docs/artifact/INTENT update plan.

## 1. INTENT summary + staleness assessment

`intents/intent.md:1-128` (full file read) is **still the unfilled scaffold template**. Only the
Mission line and frontmatter were ever completed:

- `intents/intent.md:15` — Mission: *"Research Foundry is a Markdown/YAML-first, evidence-first
  research control plane: it turns raw ideas into governed research swarms, evidence bundles, and
  claim-verified reports, with writebacks to MeatyWiki, SkillMeat, and CCDash."* This is accurate as
  far as it goes but describes only the **research-pipeline core**, not the platform RF has become.
- Every other section is placeholder bracket-text, verbatim from the template:
  - `intents/intent.md:41-43` Primary Users — `1. **[Primary User Type]**: [Description...]` (never
    filled in).
  - `intents/intent.md:52-56` Core JTBD — `1. **[Descriptive label]**: Users want to [do X]...`
    (template placeholders, ×5).
  - `intents/intent.md:65-67` Non-Goals — `- Not becoming a [X]...` (never filled in).
  - `intents/intent.md:80-84` Product Principles — `1. **[Principle Name]**: [What this means...]`
    (never filled in).
  - `intents/intent.md:92-94` Experience Goals — placeholder.
  - `intents/intent.md:103-105` Long-Term Direction — placeholder.
  - `intents/intent.md:119-127` Current Priority — `Stabilize [current core capability] while
    clarifying [strategic direction].` (literal placeholder text, never replaced).

**What current reality this doc entirely fails to describe** (because it was never written past the
mission line):

1. **Public/multi-user service.** P0–P5 of the "public multi-user release" shipped auth providers
   (local-static, Clerk, OIDC — `src/research_foundry/api/auth/adapters/`), RBAC enforcement
   (`docs/dev/architecture/auth-rbac-operator-guide.md`), and workspace row-level isolation
   (WKSP-304, `docs/dev/architecture/workspace-migration-runbook.md`). None of the "Primary Users"
   or "Non-Goals" sections say anything about multi-tenant operators, admins, or shared deployments
   — because those sections were never written.
2. **Web-app surface.** `frontend/runs-viewer/` is a full SPA (portfolio, run detail, claim
   audit/report-builder workbench) served either as a static export or live via `rf serve`
   (`src/research_foundry/api/app.py`). The intent doc has no user type for "someone who opens the
   web viewer" vs. "someone who drives the `rf` CLI."
3. **Agentic integrations.** Live bidirectional integrations exist with ARC/council-review and
   IntentTree (`docs/projects/research-foundry/bidirectional-integrations-plan.md`, status:
   `implemented`), plus agent-job launch/streaming from the web app
   (`src/research_foundry/api/routers/agent_jobs.py` — SSE events, guard-gated launch, sole
   accept-to-catalog write path). None of this is reflected in Long-Term Direction or Product
   Principles.
4. **MCP/API surface.** `src/research_foundry/api/openapi.json` plus routers for `catalog`,
   `reports` (Builder/drafts), `audit`, `auth_identity`, `admin` constitute a real API product
   surface, not just a CLI. The intent doc's mission line only mentions "writebacks" — it does not
   acknowledge RF now *serves* data to other consumers over HTTP.
5. **Hybrid persistence.** WKSP-304 enforcement notes (see `catalog_service`, `builder_service`,
   `agent_job_service` query-layer scoping) imply a DB-backed layer sits alongside the
   Markdown/YAML file store for multi-tenant surfaces (catalog, drafts, agent jobs). The "Markdown/
   YAML-first" framing in the mission line is no longer the whole story for these subsystems.

**Verdict**: the INTENT doc is not merely stale — it was **never completed**. This is the highest-
priority item in the update backlog: it currently provides zero JTBD/non-goals/principles guidance
to any agent or human orienting to the project.

## 2. Docs inventory table

| Doc / dir | Purpose | Currency | Notes |
|---|---|---|---|
| `intents/intent.md` | Mission/JTBD/principles orientation doc | **stale (never completed)** | See §1. Mission line only; rest is template placeholder text. |
| `README.md` | Top-level project overview + quickstart | **partially stale** | `README.md:35` `## Status: MVP` and `README.md:37` *"This is the 7-day MVP described in the spec"* — stale label; body (lines 129-256) actually documents `rf serve`, loopback API, run metadata, auth-adjacent flags fairly currently (dated content through the multi-user work), but the top-level status banner contradicts it. |
| `docs/projects/research-foundry/research-foundry-mvp-spec.md` (2207 lines) | Original architect-authored MVP spec (schemas, CLI, loop, agents) | **stale but historically valid** | Frontmatter `created_at/updated_at: 2026-06-12`, `status: candidate_artifact`. Describes only the 21-step research pipeline; no mention of auth, RBAC, workspaces, web app, agent-jobs, catalog, or Builder/drafts (all shipped after 2026-06-12). Fine as historical rationale; misleading if read as "the spec" without a superseding doc. |
| `docs/projects/research-foundry/_spec-agent-readable.md` (2208 lines) | Unclear — appears to duplicate the MVP spec | **stale / redundant duplicate** | First 20 lines are byte-identical to `research-foundry-mvp-spec.md` (same ChatGPT transcript preamble). No distinguishing frontmatter found in the sampled head. Candidate for deletion or must be re-justified as a distinct agent-consumption format. |
| `docs/projects/research-foundry/IMPLEMENTATION_PLAN.md` | MVP build-wave plan (W0-W5) | **stale, correctly marked `completed`** | `status: completed`, scoped to the 7-day MVP only. No successor "platform implementation plan" exists at this path level — the actual platform build history lives scattered across `docs/project_plans/implementation_plans/features/public-multiuser-p*` instead. |
| `docs/projects/research-foundry/SERVICE_CONTRACT.md` (466 lines) | "Single coordination contract" for services/CLI signatures | **stale relative to current surface** | `created_at: 2026-06-13`. Documents only the 12 original service modules (`capture, planning, source_cards, extraction, claim_mapping, synthesis, verification, governance, writeback, telemetry, adapters, cli_commands`). Missing entirely: Search Router (`rf search`/`rf fetch`), `rf serve` (loopback API), `agent_job_service`, `builder_service` (report Builder/drafts), `catalog_service`, workspace migration service, audit service, auth/RBAC providers — i.e. everything under `src/research_foundry/api/` and `src/research_foundry/services/` added post-MVP. Still says "single coordination contract" in its own header, which is no longer accurate. |
| `docs/projects/research-foundry/bidirectional-integrations-plan.md` | ARC + IntentTree integration design | current | `status: implemented`, dated 2026-06-13. Cross-referenced correctly by the `research-foundry-swarm` skill. Per memory, integrations are implemented but untested against a live server — doc itself doesn't flag that caveat. |
| `docs/projects/research-foundry/notebooklm-integration-plan.md` | NotebookLM sourcing/report/extended-run integration | current, self-flagged | `status: implemented (offline; live-unvalidated)` — correctly honest about its own gap. |
| `docs/projects/research-foundry/aars/*.md` | After-action reports for early runs | historical, fine as-is | Dated 2026-06-13/14; no currency concern (AARs are point-in-time by design). |
| `docs/dev/architecture/adr-runs-read-path.md` | ADR: static export vs. loopback API read path | **current** | `status: amended`, updated 2026-06-22. Reflects the actual dual-mode architecture. |
| `docs/dev/architecture/auth-rbac-operator-guide.md` | Auth provider + RBAC operator/admin guide | **current** | Created/updated 2026-07-08, `status: published`. Best single doc describing the multi-user reality; INTENT and README should point here. |
| `docs/dev/architecture/rf-run-export-schema.md` | run.json export contract (schema v1.4) | **current** | Updated 2026-07-06, `reviewed_by/review_verdict: approved`. Well maintained. |
| `docs/dev/architecture/workspace-migration-runbook.md` + `runbooks/workspace-migration-rollback.md` | Operator runbooks for WKSP-304 isolation rollout | **current** | Both dated 2026-07-07/08, `status: active`. |
| `docs/dev/architecture/search-router/*.md` | Search Router architecture, provider profiles, deployment, security | **current** | Created 2026-06-21, `last_verified: 2026-06-21`. Not yet referenced from `intent.md` or `SERVICE_CONTRACT.md`. |
| `docs/dev/architecture/artifact-type-reference.md` | Artifact type reference (per top-level `CLAUDE.md` pointer) | **MISSING — does not exist** | `CLAUDE.md` says *"See `docs/dev/architecture/artifact-type-reference.md` for the complete reference"* for artifact types, but the file is absent from the repo (confirmed via full-tree search). This is a broken/aspirational pointer, not merely stale — there is no artifact-type reference at all for RF's now-large artifact surface (raw_idea, research_intent, ibom, intenttree_node, research_brief, swarm_plan, routing_decision, source_card, extraction_card, claim_ledger, review_packet, evidence_bundle, skillbom_candidate, meatywiki_writeback, notebooklm_update, ccdash_event, search_request/search_run, plus the newer DB-backed draft/agent_job/catalog_item/audit_log types that have no YAML schema at all). |
| `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` | Handoff doc for the public multi-user release | current | Best candidate source for what the INTENT rewrite should absorb. |
| `docs/project_plans/**` (PRDs, implementation_plans, feature_contracts, human-briefs, SPIKEs, AARs) | Standard planning-artifact tree | current, well-populated | Large and current (through 2026-07-09); not a staleness concern — this is where the real "current state" narrative already lives, just not synthesized back into `intent.md` or `SERVICE_CONTRACT.md`. |
| `.claude/specs/skills-index.md` | "Authoritative catalog" of all skills in `.claude/skills/` | **stale / wrong content** | `updated: 2026-05-21`. Lists 56 skills that **do not match** the actual `.claude/skills/` directory: it includes skills absent from this repo (`ccdash`, `debug`, `demo-foundry`, `html-capsules`, `meatycapture-capture`, `release`, `skillmeat-cli`, `ui-ux-pro-max`, etc.) and **omits the RF-specific crown-jewel skills that actually exist** — `research-foundry`, `research-foundry-swarm`, `workflow-authoring`, `intenttree-cli`, `council-review`, `council-run`, `meatywiki`, `meatywiki-author`, `meatywiki-suite`, `symbols`, `cognitive-design`, `design-system-patterns`, `interface-design`. This index appears to be an unedited copy from a sibling project (likely SkillMeat) and is actively misleading if consulted for RF skill discovery. |
| `.claude/specs/workflows/workflow-registry.md` | Authoritative index of Dynamic Workflow scripts | **current** | Updated 2026-06-22 with an accurate self-correcting note; rows verified truthful against on-disk scripts. Good model for how `skills-index.md` should be maintained. |
| `.claude/specs/*` (other) | doc-policy, changelog-spec, provider-routing-spec, subagent-nesting-spec, project-tracking-spec, artifact-structures/* | not deeply audited this pass | Generic/global specs shared across projects; no RF-specific staleness signal found in filenames/scope. |

## 3. Skills & commands table

| Name | Domain | Reflects current capabilities? | Notes |
|---|---|---|---|
| `research-foundry` (`.claude/skills/research-foundry/SKILL.md`) | Per-command RF pipeline reference, 21-step loop | **yes, current** | Covers `rf search`/`rf fetch` (Search Router), `rf serve` with fail-closed LAN bind semantics, run metadata/backlog reconcile, full exit-code table. Does **not** mention the newer web-platform surfaces: `rf report`/draft Builder (add-block/verify/publish-preview/export), `rf audit`, `agent-jobs`, `catalog import/search`, `rf workspace migrate`. These are documented only in code/CHANGELOG, not in this skill's route table. |
| `research-foundry-swarm` (`.claude/skills/research-foundry-swarm/SKILL.md`) | Workspace bootstrap + swarm orchestration (Path A/B/C) | **yes, current** | Explicitly documents live ARC/IntentTree integration, three discovery paths, and `rf serve` governance section. Same gap as above: no mention of agent-jobs (the *web-driven* agent execution path, distinct from the CLI-orchestrated swarm paths this skill documents) or the Builder/report/catalog subsystem. |
| `workflow-authoring` (`.claude/skills/workflow-authoring/SKILL.md` + `SPEC.md`) | Governs authoring of `.claude/workflows/*.js` Dynamic Workflow scripts | current | Cross-referenced correctly from `research-foundry-swarm`; registry (`workflow-registry.md`) is itself current. |
| `intenttree-cli` | Drives IntentTree work-tree via CLI | current (per description) | Correctly flagged in `research-foundry-swarm` SKILL.md as "live server interface"; not RF-owned so lower audit priority here. |
| `council-review` / `council-run` | Offline vs. arc-server council execution | current | `research-foundry-swarm` SKILL.md explicitly disambiguates the two (`council-run` is arc-server-dependent, not used by RF pipeline runs) — good, current cross-reference. |
| `meatywiki` / `meatywiki-author` / `meatywiki-suite` | Drive MeatyWiki CLI / author writeback artifacts | current (per description) | Correctly scoped as external-app skills RF hands off to, not RF-internal. |
| `.claude/specs/skills-index.md` (as a skill catalog, not a skill itself) | Skill discovery index | **stale, see §2** | Does not list `research-foundry`/`research-foundry-swarm`/`workflow-authoring` at all — the single most important gap in the whole docs surface, since an agent trusting this index would never discover RF's own primary skills. |
| Project-level commands (`.claude/commands/**`) | `analyze/*`, `dev/*`, `plan/*`, `pm/*`, `review/*`, `test/*`, `fix/*`, `artifacts/*`, `integrations/*`, `ai/*`, `release/pr`, `mc`, `add-animation`, `quick-feature`, `stubs/load-story` | **generic, not RF-specific** | No `rf`-prefixed or research-foundry-specific slash command exists in `.claude/commands/`. All commands are the shared dev-workflow family (ported from SkillMeat conventions per `CLAUDE.md`'s Command-Skill Bindings table) applied *to* RF's own codebase (e.g., `/dev:execute-plan` for changing `research_foundry`/`runs-viewer` source). This is consistent with how RF is actually driven — the `rf` CLI itself is the product interface, and `research-foundry`/`research-foundry-swarm` skills are the pipeline-driving surface, while `.claude/commands/` govern *developing* RF, not *using* it. No staleness found here, just a naming/discoverability note: nothing in `.claude/commands/` signals "this repo is Research Foundry" — a newcomer skimming commands would not learn what RF does. |

## 4. Artifact-type reference

`docs/dev/architecture/artifact-type-reference.md` **does not exist**. `CLAUDE.md` (project root)
references it directly: *"This project defines its own artifact types. See
`docs/dev/architecture/artifact-type-reference.md` for the complete reference with detection
signals and usage patterns."* A full-tree search (`find ... -iname "*artifact-type*"`) returned
nothing. This is a dangling pointer, not a stale doc — there is currently **zero** written
reference enumerating RF's ~17 file-backed YAML/Markdown artifact types (schemas in `schemas/*.
schema.yaml`) *or* the newer DB-backed types introduced by the multi-user platform (draft/report-
builder records, agent_job, catalog_item, audit_log, workspace, auth identity) that have no YAML
schema counterpart at all.

## 5. Specs (`.claude/specs/`)

- `.claude/specs/README.md`, `doc-policy-spec.md`, `changelog-spec.md`, `project-tracking-spec.md`,
  `provider-routing-spec.md`, `subagent-nesting-spec.md`, `version-bump-spec.md`,
  `claude-fundamentals-spec.md`, `multi-model-usage-spec.md` — generic cross-project specs, not
  audited for RF-specific drift this pass (out of scope: they don't describe RF's product surface).
- `.claude/specs/artifact-structures/*` — generic artifact-structure conventions (human-brief-spec,
  ccdash-doc-structure, skill-spec-convention/template) — not RF product-surface docs.
- `.claude/specs/workflows/*` — see §2 table; `workflow-registry.md` is the one genuinely
  well-maintained, self-correcting index in the whole `.claude/specs/` tree and should be the model
  for fixing `skills-index.md`.
- `.claude/specs/skills-index.md` — see §2/§3; needs a full regeneration against the actual
  `.claude/skills/` directory listing, not incremental patching.

## 6. Update backlog (prioritized)

1. **P0 — Write `intents/intent.md` for real.** Currently a template with only the mission line
   filled in (§1). This is the cheapest, highest-leverage fix: every section is a placeholder that
   needs real content covering (a) the research-pipeline user (CLI/agent-driven), (b) the web-app
   viewer user, (c) the multi-tenant operator/admin, (d) the API/MCP consumer. Non-Goals should
   state explicitly what "public service" does and does not mean (e.g., not a hosted SaaS yet, not
   replacing MeatyWiki/SkillMeat as system of record). Current Priority section should name the
   actual current focus (WKSP-304 full-surface audit per memory) rather than bracket text.
2. **P0 — Fix `.claude/specs/skills-index.md`.** Regenerate from the real `.claude/skills/`
   directory listing (~50 dirs). It currently omits `research-foundry` and `research-foundry-swarm`
   entirely and lists ~15 skills that don't exist in this repo. Follow the `workflow-registry.md`
   self-correcting-note pattern (state explicitly what was verified on-disk vs. copied).
3. **P1 — Create `docs/dev/architecture/artifact-type-reference.md`.** Currently a dangling
   `CLAUDE.md` pointer to a nonexistent file. Should enumerate the ~17 YAML-schema-backed artifact
   types (from `schemas/*.schema.yaml`) plus the DB-backed platform types (draft/report-builder
   record, agent_job, catalog_item, audit_log entry, workspace, auth identity) that have no YAML
   schema, with detection signals (frontmatter `type:`/`doc_type:` field, file location convention)
   and usage patterns for each.
4. **P1 — Update `SERVICE_CONTRACT.md` or explicitly retire it.** Either extend it to cover Search
   Router, `rf serve`/loopback API, agent-jobs, Builder/drafts, catalog, workspace migration, and
   auth/RBAC services (bringing it in line with its own "single coordination contract" framing), or
   retag its header as historical/Wave-2-only and point to the newer per-feature implementation
   plans (`docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1*`,
   `-p5-auth-rbac-v1*`) as the current contract sources.
5. **P1 — Fix the README "Status" banner.** `README.md:35-40` still says "Status: MVP / This is the
   7-day MVP described in the spec." Replace with a status that reflects the shipped public
   multi-user release (P0-P5 complete per memory), while still linking the MVP spec as historical
   foundation. Consider adding a "What RF is today" paragraph enumerating CLI + web viewer + HTTP
   API + agent-jobs + auth/RBAC, since the rest of the README body already documents most of these
   pieces individually without a synthesizing overview.
6. **P2 — Resolve `_spec-agent-readable.md` duplication.** Confirm whether this file is meant to
   diverge from `research-foundry-mvp-spec.md` for a different consumption format; if it's a stale
   fork (first 20 lines are byte-identical), either delete it or document why two copies are
   intentionally maintained.
7. **P2 — Refresh `research-foundry` and `research-foundry-swarm` SKILL.md route tables.** Add rows
   for the web-platform surfaces now shipped: report Builder/drafts (`rf report`/draft subcommands),
   `rf audit`, agent-jobs (web-driven agent launch distinct from the CLI swarm paths already
   documented), and catalog import/search. These skills are otherwise the best-maintained docs in
   the repo — the gap is additive, not corrective.
8. **P3 — Cross-link Search Router docs from `intent.md`/`SERVICE_CONTRACT.md`.**
   `docs/dev/architecture/search-router/*` is current and well-written but isolated; nothing in the
   top-level intent/contract docs points to it.
9. **P3 — Add an RF-identifying signal to `.claude/commands/`** (or accept the gap as intentional,
   since `.claude/commands/` governs developing RF, not using it, and the `research-foundry*` skills
   already own the "using RF" surface).
