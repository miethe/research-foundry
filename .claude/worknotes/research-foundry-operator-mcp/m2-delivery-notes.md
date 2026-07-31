---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
---

# M2 delivery notes — stdio surface exists and provably cannot execute

Running capture for the M2 delivery report + AAR. Continues the M1 pattern
(`m1-remainder-delivery-notes.md`).

## Setup

- Branch `worktree-operator-mcp-v1` @ `053a2c8` (M1 head, pushed, PR #7). ITT node
  `node_01KY5SHNM6JVMCCKYXP44GRSDR` (C5, epic Wave 4) marked `in_progress` at M2 start.
- Provisioning gate: 1 non-fatal gap (skill:delegation-router overlay refused by SkillMeat
  enterprise — skill live at user scope; `enterprise.deploy.overlay_refused`). Non-blocking.
- Fact pack (read-only explorer): 14-tool closed inventory = 12 landed adapters +
  `operation.preflight` (server meta tool, no adapter) + `writeback.preview` (**no adapter, no
  preview seam, no staging root exist yet** — the real M2 build). Knowledge MCP supplies the
  optional-SDK/stdio-only/closed-schema patterns; pyproject already has the shared `mcp` extra.
- Contract: `m2-implementer-contract.md` (decided D1-D10; sibling-input enumeration per M1 AAR
  carry-in #1/#3; scratch-copy rule replaces `git stash` per carry-in #5).

## Routing (delegation-router resolved, logged intent)

| Leg | Work | Route |
|---|---|---|
| A | OPM-5.3 writeback.preview adapter + pure-render split + spies | claude-primary sonnet (preview seam is MUST-stay-adjacent) |
| B | OPM-5.1/5.2/5.4 server scaffold + closed registry + error mapping | claude-primary sonnet |
| C | OPM-5.5 packaging tests | ICA sonnet-5[1m] free lane |
| Pre-gate | two diverse cheap lenses | gpt-5.6-terra (high) + ICA sonnet-5[1m] |
| Gate | security lens (fresh context) | claude Opus — MUST-stay, frontier-class |
| Gate | validator | claude sonnet, fresh context |

Codex is NOT used for the security lens itself (workstream constraint: codex refuses
adversarial-audit framing — pre-gate is framed as code review, which held fine in M1).

## Observations for the AAR

- **O-1 — The orchestrator's environment provisioning caused the first defect.** `uv pip install
  "mcp>=1.0"` (matching the pyproject extra's own pin) resolved `mcp==2.0.0`, which **removed
  `mcp.server.fastmcp`** (renamed to `mcp.server.mcpserver.MCPServer`). Consequences: (a) the
  previously-*skipped* knowledge-MCP tests started *failing* — `import mcp` succeeds so
  `importorskip` passes, then `build_server()` raises the "SDK is not installed" RuntimeError —
  a misleading-hint failure mode worth its own defect class note; (b) Leg B, correctly reading its
  actual environment, adapted the server to the 2.0-only API, which would have forked the two MCP
  servers onto incompatible SDK APIs under one shared extra. Leg B flagged it rather than silently
  shipping — the flag-first posture paid out again (M1 O-10). Resolution: venv + shared extra
  pinned `mcp>=1.0,<2`; Leg B continued (same session, cache-warm) to revert to the fastmcp 1.x
  import; SDK-2.0 migration for BOTH servers filed as a follow-up ITT node. Echo of M1's O-5:
  the party who writes the contract can still hand implementers a defective premise — this time
  via the environment, not the contract text. Pre-flight venv assembly should pin what the code
  actually targets, not what the extra merely allows.

- **O-2 — Whole-tests-tree collection has been broken on main since 2026-07-22, and nobody
  noticed.** `2d40f1f` (swarm-driver PR #6) added `tests/__init__.py` ("packaged so pytest gives
  every module a unique dotted name"), which silently broke the three bare sibling imports in
  `tests/test_verification_pediatric_cds.py` / `tests/test_verification_seam001_gate_composition.py`
  — a whole-tree `pytest` run aborts at collection. Masked because every recent milestone ran
  `pytest tests/unit` and called it "full suite" (M1's 2371-node count vs the plan AC's 4410+
  whole-suite baseline). Surgical 2-line orchestrator fix in-branch (`import x` → `from tests
  import x`), logged as an authorized out-of-scope deviation; the M3 whole-suite AC depends on it.
  Lesson: "full suite" claims must name the collection scope; a green subset run reads identical
  to a green suite in a completion note.
- **O-3 — Leg continuation (continue-don't-redispatch) worked as doctrine predicts.** Both wave-1
  legs took a second instruction in their live session (Leg B: SDK revert + extra pin; Leg A:
  target-coverage extension) at a fraction of a fresh dispatch's cost, with no context loss and
  no re-derivation. The M1-style "fix the sibling" discipline held: Leg A's extension added spy
  coverage for the new paths unprompted-in-detail (the instruction named it once).

## Follow-ups to file as ITT nodes at close

- Unify the duplicated `_stdio_only_fastmcp_class` guard (knowledge_mcp + operator_mcp) into a
  shared module (deliberate duplication per contract D3).
- `itt node list --tree <research-foundry>` returns 0 rows from this repo context while
  `itt node get/update` work fine — list/filter defect or pagination gap in the CLI.
- MCP SDK 2.0 migration (fastmcp → `mcp.server.mcpserver.MCPServer` rename) for ALL THREE stdio
  servers (`rf-mcp`, `rf-knowledge-mcp`, `rf-operator-mcp`); shared extra now pinned `<2`.
- `ccdash` writeback-preview support: needs the same layer-below split applied to
  `telemetry.emit_ccdash_event` (constructs `CCDashClient` internally); out of M2 file scope.
- Skillmeat preview's `ccdash_event_id` is always empty in preview output (Leg A JC-6) — folds
  into the ccdash follow-up above.
- Whole-suite collection scope: add a CI/gate guard that runs `pytest --collect-only -q` on the
  FULL tree so a packaging change can't silently break collection again (O-2).
