---
title: "Public Multi-User Release — P2+P3 Execution Handoff (Opus 4.8)"
doc_type: implementation_plan
status: ready-for-execution
created: 2026-07-04
feature_slug: public-multiuser-release
feature_version: v1
phases_covered: [2, 3]
source_spec: docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
prior_plan: docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md
branch: feat/public-multiuser-p2 (then feat/public-multiuser-p3)
owner: nick
orchestrator: opus-4-8
prepared_by: fable-5
---

# P2+P3 Execution Handoff — Opus 4.8

## 0. Mission & authority

Execute **Phase 2 (Granular Report Audit Links)** and **Phase 3 (Report Builder)** of the
public multi-user release spec (§7, §8, §12) in `research-foundry`. The operator has
**pre-authorized squash-merge to `main` on completion** ("Proceed with P2-3. Squash merge to
main when done") — that is the in-prompt merge override; no re-ask needed once validation
passes. Phases 4–5 (agents, auth/RBAC hardening) are explicitly OUT of scope here.

**Model routing (per MODEL-ROUTING.md):** Opus 4.8 orchestrates + adjudicates gates in-session.
Sonnet 5 (`claude-sonnet-5`, `xhigh` on the hard waves) does subscription-side implementation.
ICA Sonnet 4.6 (`~/ica-claude.sh`, `claude-sonnet-4-6[1m]`) takes bounded, contract-clear waves
behind a reviewer gate. Codex `gpt-5.5` (`codex exec`, read-only) runs the adversarial review
pass. Never offload MUST-stay work (anchor contract design, sensitivity paths) to ICA/Codex.

## 1. State as of handoff (2026-07-04)

- **P0+P1 are MERGED to main**: PR #1, merge commit `1f19379`. Local checkout is synced.
- Working tree clean, branch `main`. This handoff file is intentionally **untracked** —
  commit it with the first P2 wave.
- P0+P1 as-built recon (verified against `1f19379`) is embedded in §3/§7 below — trust it
  over the spec's §3 "code-truth baseline", which predates implementation.

## 2. Required reading (before the plan gate)

1. Spec §7 (Report Audit), §8 (Builder), §10 (API), §13 (Validation):
   `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md`
2. Prior plan format + frozen decisions D1–D6: `docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md`
3. **Mockups — Read the PNGs** (they are the UI target, per operator directive):
   - `docs/project_plans/design-specs/assets/public-multiuser-release/mockup-report-builder.png` (P3 target)
   - `docs/project_plans/design-specs/assets/public-multiuser-release/mockup-evidence-catalog.png` (visual language)
   - `current-audit.png`, `current-report.png` (P2 baseline)
4. Key code (skim, don't dump): `src/research_foundry/services/catalog_service.py`,
   `services/export_service.py`, `services/verification.py`, `api/routers/catalog.py`,
   `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx`,
   `components/ClaimLedger/ClaimAuditWorkbench.tsx`, `src/lib/catalog.ts`, `src/lib/auditStateMachine.ts`.

## 3. As-built map you will build on (recon, verified)

**Catalog backend (P1):** `catalog_service.py` (~1.4k lines) — sqlite3+FTS5 derived store at
`<workspace>/.rf_cache/catalog.db`, `PRAGMA user_version=1`, **drop+rebuild on version
mismatch** (it is a cache, never durable state). Import calls `export_run(...)` live,
delete-then-insert per run (idempotent). IDs: `ci_ + sha1("{item_type}:{run_id}:{local_ref}")[:12]`.
Read-time sensitivity gating fail-closed (`WHERE sensitivity_rank <= threshold`; 404 hides
existence). Router `api/routers/catalog.py`: `GET /api/catalog/{stats,search,items/{id}}`,
`POST /api/catalog/import[/run/{run_id}]`. CLI `rf catalog import|search|show|stats|rebuild`,
all reads take `--sensitivity-threshold`.

**Catalog frontend:** `CatalogScreen.tsx` + `useCatalog.ts` (react-query) + `api/client.ts`
**dual-mode**: loopback hits `/api/catalog/*`; static mode builds a client-side index in
`src/lib/catalog.ts` with the **same mapping table as the backend** (parity rule D4 — any
read-model change lands in BOTH places or modes diverge). Types in `src/types/rf/catalog.ts`
(links = `{outgoing, incoming}` of `{catalog_item_id, relation}`).

**Report audit today (what P2 replaces):** `ReportRenderer.tsx` renders `report_draft` via
react-markdown v10 + remark-gfm; claim chips parsed by **regex** `\[claim:(clm_\w+)\]` over
rendered children; highlighting is **block-level only** (`activeClaimIds` intersection);
heading slugs are the only stable anchors. `ClaimAuditWorkbench.tsx` (ledger left / report
center / inspector right) + `auditStateMachine.ts` (`HighlightMode = none|composition|selected-claim`).
`report_locations` today = `{file, heading, paragraph_id}` in `schemas/claim_ledger.schema.yaml:83`,
usually empty, passed through verbatim at `export_service.py:326`.

**Deps gap:** backend has **no** markdown/AST lib (typer/rich/pyyaml/jsonschema only);
frontend has react-markdown+remark-gfm only, no first-class mdast/unified. Stack: Vite 5,
react-router 6, react-query 5, hand-written CSS (`tokens.css`, `rv-*`/`it-*` classes — no
Tailwind), vitest 2 (jsdom), Playwright 1.48 in `e2e/`.

**Nav placeholders:** `AppShell.tsx` `NAV_ITEMS` — Builder is `state:"disabled"` with
`disabledReason:"Planned — report composition workspace (Phase 3)"`. P3 flips it to enabled.

## 4. Frozen design decisions (D7–D14)

Confirm at your plan gate, then treat as locked. D7–D10 are load-bearing; reversing them
mid-flight invalidates wave contracts.

| # | Decision | Rationale |
|---|---|---|
| D7 | **Backend owns anchor derivation.** Add `markdown-it-py` to backend deps; derive block/paragraph anchors + claim spans server-side at export time (new deterministic pass in `export_service.py`). Frontend **consumes** anchors, never re-derives them. | Spec mandates AST-not-regex for persisted anchors. `token.map` gives source line ranges for stable block IDs. Single derivation site keeps static/loopback parity trivial (D4). |
| D8 | **Anchors ship as an additive `run.json` field** (`report_anchors`: blocks with `block_id`, `section_id`, `paragraph_ordinal`, `text_hash`, `claim_links[]` incl. `span_start/end`, `relation`, `link_status`). `block_id` = sha1(section slug + normalized text + ordinal)[:12]. Bump export schema minor version; old exports lack the field → UI falls back to today's regex path with `link_status:"legacy"`. | run.json stays the deterministic read contract (additive = non-breaking). Hash-based IDs give drift detection for free (`quote_text_hash` semantics from spec §7). |
| D9 | **Frontend anchor consumption**: `ReportRenderer` keeps react-markdown for rendering but keys highlighting/chips off exported anchors (block_id → DOM `id`), enabling paragraph+span selection. Regex path retained ONLY as legacy fallback. Extend `auditStateMachine.ts` rather than replacing it. | Minimal blast radius on a working audit surface; e2e specs w1/w3 keep passing during migration. |
| D10 | **Builder drafts are file-canonical, NOT rows in catalog.db.** Durable state = YAML+MD under `<workspace>/reports/drafts/<report_draft_id>/` (draft.yaml: metadata, blocks[], claim_links[]; blocks carry markdown). catalog.db gets only a derived, rebuildable index of drafts. New `builder_service.py` parallel to `catalog_service.py`. | catalog.db is drop+rebuild-on-mismatch — user drafts there would be destroyed. Files-canonical is the RF/AOS constraint and keeps `rf` CLI + git-diffability. |
| D11 | Builder draft IDs use a new `rpt_` namespace; the P1 catalog's synthetic one-per-run `report` item stays as-is (`origin=run_export`); link drafts to source runs/claims via `catalog_links` relations (`derived_from`, `cites`). | Avoids colliding the P1 synthetic report row with multi-draft builder state (recon landmine #5). |
| D12 | **No auth/RBAC/workspace enforcement in P2/P3** (that is P5). New schemas include nullable `workspace_id`/`created_by` fields for forward-compat, unenforced. | Keeps P2/P3 out of Mode-D territory; cheap forward-compat per spec §6 field list. |
| D13 | New verification checks (spec §7: paragraph-has-support, `[claim:]` resolves, anchor-hash match, report-body sensitivity fail-closed) land in `services/verification.py` as deterministic checks and gate `rf report verify` + the builder publish-preview endpoint. | Verifier is the crown jewel; publish gates must be encodable, not remembered. |
| D14 | **Two sequential PRs**: `feat/public-multiuser-p2` → squash-merge → `feat/public-multiuser-p3` → squash-merge. Worktree per branch under `.claude/worktrees/`, commit per wave. | P3 builds on merged P2 anchors; two tractable reviews beat one 4k-line diff. Matches git-worktree-pr-protocol. |

## 5. Wave plan

Assemble the delegation context bundle once per PR at the plan gate:
`op context pack --budget 6000 --plan-ref <this file> --project-root ~/dev/homelab/development/research-foundry --project research-foundry`
Thread the printed path into every delegated leg (`--append-system-prompt-file` for ICA).

### PR 1 — Phase 2: Granular Report Audit (branch `feat/public-multiuser-p2`)

| Wave | Scope | Executor | Notes |
|---|---|---|---|
| A | Anchor model + AST extraction: add `markdown-it-py`; anchor derivation pass in `export_service.py` emitting `report_anchors` (D8); schema bump; unit tests over fixture runs incl. drift (edit paragraph → hash mismatch → `link_status:"stale"`). | **Sonnet 5 xhigh** (MUST-stay) | Hardest contract work. Do NOT touch sensitivity defaults (`DEFAULT_THRESHOLD="public"`, `export_service.py:48`). |
| B | API + CLI + catalog surfacing: expose anchors via runs/catalog APIs (`GET /api/reports/{run_id}/anchors` or embedded in run detail — keep read-only, spec §10 report POST endpoints are P3); extend `catalog_service._build_links` (~line 849) to use real anchors for report→claim links; `rf report anchors <run>` + `--sensitivity-threshold` parity. | **ICA Sonnet 4.6** behind review gate | Bounded, contract from Wave A. Pipe long prompts via **stdin** (ICA gotcha); turn cap ~100. |
| C | Frontend audit upgrade: consume `report_anchors` in `ReportRenderer`/`ReportOverlay`/`ClaimAuditWorkbench` — paragraph+span highlighting, per-section coverage strip, filters (unsupported/contradicted/inference/speculation/stale), paragraph inspector shows exact sources+locators; legacy regex fallback (D9); update `lib/catalog.ts` for static parity (D4). | **Sonnet 5** | Read `current-audit.png` + `mockup-report-builder.png` right panel first. Keep `rv-*` CSS conventions; extend `auditStateMachine.ts`. |
| R1 | Review gate: Codex `gpt-5.5` read-only adversarial pass over the PR diff (anchors determinism, parity, sensitivity regressions) + Opus adjudication; fix-loop; then full validation (§6), push, PR, **squash-merge to main** (pre-authorized). | Codex + Opus | |

### PR 2 — Phase 3: Report Builder (branch `feat/public-multiuser-p3`, after PR 1 merges)

| Wave | Scope | Executor | Notes |
|---|---|---|---|
| D | Draft model + service: file-canonical draft store (D10) — `builder_service.py` (create from template/run/collection/blank; block CRUD; claim/source links; revisions); draft verification via D13 checks; export-to-Markdown with frontmatter + stable `[claim:]` links; derived index in catalog.db (version bump, rebuild-safe). | **Sonnet 5 xhigh** (MUST-stay) | Durable-state discipline: never store draft truth in the rebuildable cache. |
| E | Builder API + CLI: spec §10 report endpoints (`POST /api/reports`, versions, block PATCH, claim-links, verify, publish-preview); publish-preview runs D13 checks fail-closed; `rf report draft *` CLI with threshold parity. | **ICA Sonnet 4.6** behind review gate | Contract-clear from Wave D; stdin prompts; incremental writes. |
| F | Builder UI: `/builder` route (flip AppShell Builder nav to enabled); layout per `mockup-report-builder.png` — left catalog search (reuse `useCatalog` + `CatalogResultsTable`), center outline+block editor with inline chips, right audit inspector (reuse Wave C components), bottom Claim Basket; coverage/risk live while editing; publish gate UI. **Not a blank markdown editor.** | **Sonnet 5**; Claim Basket + search pane subcomponents may go ICA | Visual grounding: paste mockup into delegate context. Dual-mode: builder is **loopback-only** in v1 — static mode shows read-only published drafts or a disabled state (document choice). |
| R2 | Review gate: Codex adversarial pass (draft durability, publish-gate fail-closed, anchor preservation across revisions) + Opus adjudication; validation; PR; **squash-merge to main**; flip this doc's `status` to completed; run `op story capture` on lessons. | Codex + Opus | |

## 6. Validation (per PR, before merge)

```sh
# backend (repo root)
pytest
rf run export --json --all        # regenerate exports; anchors present
rf catalog rebuild && rf catalog stats

# frontend (frontend/runs-viewer — npm-style scripts; there is NO pnpm e2e script)
npm run lint
npm run test                       # vitest
npm run build                      # tsc -b && vite build (static parity compiles)
npx playwright test                # e2e: w1-claim-audit, w3-report-chip-navigation must pass
```

New tests required: anchor determinism + drift (backend), static/loopback parity (both modes
return identical anchor/coverage data for fixture runs), publish-preview fail-closed on
sensitivity (report body with client_sensitive quote must refuse public export), draft
revision round-trip preserving anchors.

## 7. Landmines (verified in recon — do not rediscover these the hard way)

1. **Sensitivity fail-closed is a shipped guarantee** (`0d9d278`): default threshold
   `public`; precedence override > foundry.yaml > public; bogus labels raise. Static mode
   applies NO read-time gate (pre-gated at export) — any new static bundle for P2/P3 data
   MUST be exported at audience threshold or it leaks. Loopback gates every read.
2. **Dual-mode parity (D4 from P0/P1 plan):** every read-model behavior exists twice —
   `catalog_service.py` (SQL) and `lib/catalog.ts` (pure TS). Anchors and coverage must land
   in both or static mode silently diverges. There are parity tests to extend.
3. **catalog.db is disposable** — `user_version` mismatch drops everything. Nothing durable
   goes there (hence D10). When you add index tables, bump `user_version` to 2.
4. **`get_item` 404s hide over-threshold items** — new report/anchor endpoints must keep the
   no-existence-leak behavior.
5. **CLI threshold parity** (`344a318`): every new read command takes `--sensitivity-threshold`.
6. **e2e specs w1/w3 exercise today's chip/highlight behavior** — keep them green through the
   D9 migration; extend rather than rewrite.
7. **ICA delegate gotchas:** long prompts → pipe via stdin; pin `[1m]` aliases; turn caps
   100–120; require incremental file writes; give FE delegates the mockup image.
8. **`report_locations` (v1) stays** in the ledger schema for back-compat; V2 anchors are the
   new system of record for report↔claim location links.

## 8. Definition of done

- [ ] Both PRs squash-merged to `main`; worktrees + branches cleaned up.
- [ ] Spec §12 Phase 2 + Phase 3 acceptance bullets all demonstrably true.
- [ ] Validation suite (§6) green on `main` after each merge.
- [ ] No sensitivity regression: fail-closed tests added and passing.
- [ ] AppShell: Builder nav enabled; Agents still disabled ("Phase 4").
- [ ] This doc committed (PR 1) and `status: completed` (PR 2); AAR captured via `op story capture`.
