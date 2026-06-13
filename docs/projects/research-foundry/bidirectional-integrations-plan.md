---
doc_type: design_plan
title: Bidirectional Integrations — ARC (council) & IntentTree
status: implemented
created: 2026-06-13
updated: 2026-06-13
owner: Nick Miethe
source_docs:
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
  - src/research_foundry/services/writeback.py
  - src/research_foundry/adapters/base.py
  - src/research_foundry/services/governance.py
  - .claude/skills/council-run/references/surfaces.md
  - .claude/skills/intenttree-cli/workflows/
---

# Bidirectional Integrations — ARC & IntentTree

## 1. Goal

Enable RF to integrate **bidirectionally** with two sibling tools when they are online,
mirroring the existing MeatyWiki writeback seam and degrading safely to file-based
candidates when they are offline:

- **ARC (Agent Review Council)** — RF hands an evidence bundle to ARC for council review,
  and folds the verdict back into RF's gate; optionally uses ARC reviewers to help *run*
  a swarm. (RF ↔ ARC)
- **IntentTree** — RF *receives* research tasks dispatched from IntentTree (with links to
  relevant detail, including MeatyWiki notes), *posts status updates while operating*, and
  *links run results back* to the originating node. (IntentTree ↔ RF)

## 2. Governing principle — "candidate first, push second"

RF is file-first and degrade-to-stub. The existing MeatyWiki target proves the pattern:
`_render_meatywiki()` **always** writes a schema-valid `runs/<run>/writebacks/meatywiki_writeback.md`
candidate; the live "push" (mirror to the vault) only happens when review is not required.

Every new integration follows the same shape:

1. **Always** emit a deterministic, schema-valid candidate file under `runs/<run>/writebacks/`.
2. **Health-gate** the live HTTP call behind an `available()` check (short timeout) **and** the
   run's key profile. If the server is unreachable or the profile forbids the target, leave the
   candidate as `proposed`/`pending` and stop — never fail the pipeline.
3. The candidate is the audit record; the push is best-effort and reversible.

This keeps determinism, offline safety, and governance fail-closed behavior intact.

## 3. Architecture

### 3.1 New integration client layer
`src/research_foundry/integrations/` (new package), thin httpx clients mirroring the
adapter `available()` contract:

| Client | Base URL (default) | Health check | Auth |
|--------|--------------------|--------------|------|
| `ArcClient` | `http://127.0.0.1:8910` | `GET /api/health` → `integrations.authoring.available` | none / local |
| `IntentTreeClient` | `http://localhost:8000` | `GET /api/meta/version` | bearer `INTENTTREE_API_TOKEN` (optional) |

Config keys live in `foundry.yaml` (`integrations.arc.base_url`, `integrations.intenttree.base_url`)
and `.env.<profile>` (tokens). `rf doctor` reports reachability (`arc: reachable`, `intenttree: reachable`)
alongside the existing N/5 adapter line. Both clients degrade to `None`/no-op when unreachable.

### 3.2 RF → IntentTree (outbound) — status + result links
- **Writeback target `intenttree`**: `_render_intenttree_update()` (copy `_render_skillbom()` shape)
  always writes `runs/<run>/writebacks/intenttree_update.yaml` (new schema). When online + the run's
  `intent.intenttree_node_ref` resolves: `PATCH /api/nodes/{node_id}` (status/progress) and
  `POST /api/nodes/{node_id}/artifacts` (links to `evidence_bundle.yaml`, the report, and any
  MeatyWiki note candidate). Fills the node's `reusable_output_candidates` / `expected_artifacts`.
- **Status callbacks while operating**: extend `services/telemetry.py` (which already records stages to
  `run_trace.jsonl`) with a best-effort `push_status(run_id, stage)` that, when IntentTree is online and
  the node is linked, PATCHes node progress at key stages (discovery started → ingested N → verify passed).
  Silent-degrade on any error. Exposed as `rf status push --run <id> --to intenttree` for manual use.

### 3.3 IntentTree → RF (inbound) — receive dispatched tasks
- **New command `rf intake intenttree <node_id>`** (service `services/intake.py`): pull the node via
  `GET /api/nodes/{node_id}?include=artifacts,edges`, map it onto `capture_idea()` with `attachments[]`
  populated from the node's linked detail (URLs, MeatyWiki note refs, prior artifacts), then `triage_idea()`
  (writing the RF intent's `intenttree_node_ref` = the **source** node so the loop closes), then optionally
  `plan_run()`. Offline fallback: accept a pasted/locally-exported node YAML. This is the entry point for
  "research tasks with links to relevant details."

### 3.4 RF ↔ ARC — review (and optionally help run)
- **Writeback target `arc`**: `_render_arc_council()` (copy `_render_meatywiki()` shape) always writes
  `runs/<run>/writebacks/arc_review_request.yaml` (new schema; the evidence-bundle review packet).
  When ARC online + profile permits: `POST /api/runs` to scaffold a review of the bundle, persist the
  returned `arc_run_id`, then read the verdict via `GET /api/runs/{arc_run_id}`. Map the verdict to RF's
  council gate: **approve → exit 0; concern/block → exit 7** (human review required) — the same semantics
  as the offline `research-foundry-council.js` workflow and `rf council`.
- **ARC adapter `arc_council`** (optional, in `adapters/_CONCRETE`): lets `rf swarm run` use ARC reviewers
  to critique discovery/synthesis mid-run. Degrades to the deterministic stub like every other adapter.
- **Offline fallback** for both: the vendored `research-foundry-council.js` Workflow + `rf council` (no arc server).

### 3.5 Governance
- Register `arc` and `intenttree` as governable writeback targets in `config/governance.yaml` with
  permitted tiers, and validate them in `governance.py:guard_check()` exactly like `meatywiki`.
- Health-gated push **respects the profile**: never push data above a target's permitted tier; fail closed
  when ambiguous. Client-confidential never pushes to a personal-tier IntentTree/ARC.
- Proposed defaults (see Open Decisions): `arc` permitted for personal + work_approved + client_approved
  (it is a review/governance gate); `intenttree` permitted for personal + work_approved.

## 4. Phasing (each phase independently shippable & offline-safe)

Phases 0–4 shipped live, bidirectional, with offline fallback.

| Phase | Scope | Key files |
|-------|-------|-----------|
| **0 — Client foundation** | `integrations/` (ArcClient, IntentTreeClient, health-gated, env/yaml config); `rf doctor` reachability; mocked-HTTP tests. No behavior change. | `integrations/`, `config/`, `cli_commands.py` (doctor), `tests/` |
| **1 — RF→IntentTree** | `intenttree` writeback target (candidate + live PATCH/artifact); status callbacks; governance registration. Delivers "status + result links back to tasks." | `writeback.py`, `telemetry.py`, `paths.py`, `schemas/intenttree_update.schema.yaml`, `config/governance.yaml` |
| **2 — IntentTree→RF** | `rf intake intenttree <node>` → capture(attachments incl. MeatyWiki links) → triage(link to source node) → optional plan. Round-trips with Phase 1. | `services/intake.py`, `cli_commands.py`, tests |
| **3 — RF↔ARC** | `arc` writeback target (review-request candidate + live scaffold/verdict); `arc_council` adapter; verdict→exit-7 gate; governance. | `writeback.py`, `adapters/arc_council.py`, `adapters/__init__.py`, `schemas/arc_review_request.schema.yaml`, `config/governance.yaml` |
| **4 — Skills/workflow wiring** | Flip the binding notes from "offline only" to "online-aware"; teach `research-foundry-swarm.js` / `research-foundry-council.js` to use live paths when reachable. | `.claude/skills/{council-run,intenttree-cli}/SKILL.md`, `.claude/workflows/*.js` |

## 5. Open decisions (need sign-off)
1. **Permitted tiers** for `arc` and `intenttree` writeback (defaults in §3.5).
2. **Surface naming**: `rf intake intenttree <node>` vs `rf capture --from intenttree --node <id>`;
   writeback target names `arc` / `intenttree` (proposed).
3. **Status-callback cadence**: every stage vs milestone stages (discovery/ingest/verify/bundle) — proposed milestones.
4. **Start scope**: Phase 0 + 1 first (outbound IntentTree, highest value, lowest risk), or all four.

## 6. Non-goals (v1)
- No new long-running RF server; RF remains CLI/file-first and *calls* the sibling servers.
- No bundling of the ARC/IntentTree apps; RF assumes they run separately (like MeatyWiki).
- No live push of data above a profile's permitted tier — ever.
