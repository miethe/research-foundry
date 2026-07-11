---
title: "AAR — KnitWit Extension Runs & the nuc Execution Boundary"
type: after_action_report
created: 2026-07-11
author: Nick Miethe (orchestrated by Claude Opus, Path-B research swarm)
status: final
scope: >
  Two KnitWit/LoopNest extension research runs scaffolded on the agentic node via
  POST /api/runs, executed locally via Path B, and landed back on the node viewer.
runs:
  - rf_run_20260710_stitch_level_3d_crochet_rendering_fidelity_caec
  - rf_run_20260710_server_offload_architecture_for_a_premium_a669
related:
  - docs/projects/research-foundry/aars/roots-wave-high-priority-runs-aar-2026-06-14.md
  - .claude/workflows/rf-run-execute.js
  - "PKM: KnitWit/Research/research-workflow-pack/knitwit-run-execute.js"
  - runs/rf_run_20260710_stitch_level_3d_crochet_rendering_fidelity_caec/
  - runs/rf_run_20260710_server_offload_architecture_for_a_premium_a669/
lessons:
  - nuc-api-runs-are-scaffold-only
  - viewer-deploy-hard-reset-endangers-untracked-runs
  - rf-shim-node-mode-splits-swarm-filesystem
---

# AAR — KnitWit Extension Runs & the nuc Execution Boundary

**Date:** runs executed 2026-07-10; landed on node 2026-07-11
**Orchestration:** Opus + Dynamic Workflow (one deep swarm at a time, strictly sequential)
**Mode:** Path B (Claude-orchestrated discovery, RF governance spine + deterministic tail)
**Trigger:** Operator: *"there are 2 pending rf runs on the nuc host … run them now"* → *"I want these and all existing runs present on the nuc instance and viewable in the viewer there."*

---

## 1. Results

| Ref | Run ID (`rf_run_20260710_…`) | Topic | Sources | Claims (sup / inf / spec) | Unsup | Verify | Bundle |
|---|---|---|---|---|---|---|---|
| stitch3d | `stitch_level_3d_crochet_rendering_fidelity_caec` | Stitch-level 3D crochet rendering fidelity | 12 | **97** (77 / 18 / 2) | 0 | ✅ exit 0 | verified |
| offload | `server_offload_architecture_for_a_premium_a669` | Premium-tier hybrid on-device/server split | 12 | **94** (75 / 16 / 3) | 0 | ✅ exit 0 | verified |
| **TOTAL** | 2 runs | KnitWit extensions | 24 | **191** (152 / 34 / 5) | **0** | 2/2 | 2/2 |

Both runs verify-clean (0 unsupported), committed as `9ffe13a` → `origin/main`, surgically landed on the node (`git checkout origin/main -- runs/<dir>`), viewer re-exported to **41 runs**, node API (`:7432`) reports both `published` / `verified=True`. ~2.4–2.7M subagent tokens per deep run (in-band with the ~1.2–1.4M/std baseline, ~2× for these larger deep runs).

---

## 2. The central question: why not the nuc?

The runs were *created* on the nuc but *could not be executed* there. This is architectural, not an oversight:

1. **The discovery/synthesis swarm is Claude Code Workflow-tool orchestration in the primary interactive session.** The deep swarm fans out ~9–12 Claude subagents that do real web discovery and author curated source cards. That harness runs only inside my live Claude Code session on the Mac. It is **not a headless job** that can be shipped to the node and run under systemd. The node has no mechanism to drive it.

2. **The node API scaffolds, it does not execute.** `POST /api/runs` runs capture → triage → plan: it creates the run dir, `research_brief`, `swarm_plan`, `routing_decision`, and registers the run as `planned`. It explicitly **does not drive the swarm** (per the service contract and global CLAUDE.md). So an API-launched run sits `planned` indefinitely until a primary session picks it up.

3. **Evidence injection is filesystem-local.** Path B's whole premise is that Claude agents write source cards to `runs/<id>/sources/`, and the deterministic tail (`extract → claim-map → synthesize → verify → bundle`) reads *those same files*. Agents and the tail must share one filesystem.

4. **The `rf` shim would have split that filesystem.** `~/.aos/shims/rf` sources `aos-env.sh`, which under `AOS_TARGET=node` **SSH-execs the CLI on the node**. Had I used the bare shim for the tail while agents wrote source cards locally, extract would have run on the node against an empty `sources/` — a silent split-brain. I pinned the swarm's `rf_bin` to the local `.venv/bin/rf` to keep discovery and the tail coherent on one host.

**Conclusion:** "Use the nuc" was viable only for *scaffolding* (which is exactly what created the two `planned` runs) and for *serving* (API + viewer). Execution is intrinsically a primary-session activity today. Running locally was correct, not a shortcut.

---

## 3. Gaps needing remediation

The episode surfaced three real seams (severity in brackets):

- **[High] The API creates work it cannot finish.** `POST /api/runs` mints `planned` runs with no executor and no signal that they are stranded. Both runs sat `planned` on the node until a human noticed. Remediation options: (a) mark API-created runs with an explicit `awaiting_local_execution` sub-state so they are not mistaken for in-flight; (b) emit a notification/queue entry the primary session (or Hermes) can watch; (c) longer-term, a headless executor (Agent SDK / `claude -p` harness) on the node that *can* drive discovery — but that is a substantial build, not a config change.

- **[High] The canonical viewer deploy path is destructive to node-local runs.** The documented refresh (`git fetch && git reset --hard origin/main`) would **delete any run the API scaffolded on the node but that was never committed** (they live untracked). This session dodged it by using surgical `git checkout origin/main -- <dir>` + export-only rebuild, but the *documented* path is a live foot-gun. Remediation: change the deploy to not hard-reset (fetch + ff-only, or checkout scoped paths), and/or have the viewer export read the superset of tracked + untracked runs so untracked API runs still render. Best fix: the API commits the runs it scaffolds.

- **[Low] Scaffold leaves junk.** The API left two empty, un-suffixed stub dirs on the node (slug-derivation artifacts) that would have become blank viewer entries; I removed them by hand. Remediation: API should not persist a run dir until the slug is finalized, or should garbage-collect empty scaffolds.

None of these blocked the task; all three are seams where the file-canonical / loopback model and the "node is a service host, not an agent host" reality are not yet reconciled.

---

## 4. What went well

- **Path B held.** 191 claims, 0 unsupported, both bundles verified — consistent with the roots-wave baseline. The `[claim:clm_NNN]` gate and inference-labeling discipline continue to produce clean bundles.
- **Authoritative re-verify caught nothing, but was still run.** Held to the rule: never trust workflow-reported `bundle_ok`; re-ran `rf verify` as the checkpoint. Both passed independently.
- **Sequential discipline paid off.** One deep swarm at a time — no rate-limit events across two large deep runs.
- **Surgical landing preserved node state.** Scoped `git add runs/<dir>` (not `-A`), push, `git checkout` (not reset) — no collateral damage to the node's untracked runs or the working tree's `.firecrawl/`/registry/ccdash pollution.

## 5. What was friction

- **Landing is a manual, multi-step, trap-laden ritual** (rsync down → pin `rf_bin` → tmp outside `runs/` → scoped commit → push → surgical checkout → viewer rebuild → service restart → curl verify). It works but is entirely tribal knowledge; every step has a documented failure mode. This is the tax of local-execution + remote-serving with no bridge between them.
- **`rf status <run_id>` is not a command** — `status` is a group; runs are addressed positionally by `rf verify <run>` / `rf extract <run>`. Minor, but cost a cycle.
- **Deviation from the KnitWit Operating Spec v2:** discovery/synthesis used Claude Path B, not the spec-prescribed GPT-5.5-Pro/Perplexity stack. Documented here as a standing deviation (offline, no non-Claude keys wired).

## 6. Recommendations

1. **Close the scaffold-execution seam first (the High items).** At minimum, give API-created runs a visible `awaiting_local_execution` state and a notification — so "2 pending runs on the nuc" becomes a surfaced queue item, not something a human stumbles on.
2. **De-fang the viewer deploy.** Replace `git reset --hard origin/main` in the runbook with a non-destructive refresh, and/or have the export read untracked runs. This is a one-line safety fix guarding against silent run loss.
3. **Codify the landing ritual** (already captured to memory `rf-run-execution-path-b`; promote to the runbook doc so it is not memory-only).
4. **Do not attempt a headless node executor yet** — it is the "right" long-term answer but a real project (shipping the agent harness off the primary session); scope it deliberately, don't back into it.

---

*Landing mechanics and the shim trap are captured durably in memory: `rf-run-execution-path-b`, `runs-viewer-deploy`, `knitwit-research-pack`.*
