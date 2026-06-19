---
schema_version: 2
doc_type: report
report_category: feasibility
title: "Research Foundry Runs Frontend — Feasibility Brief"
status: finalized
created: 2026-06-19
updated: '2026-06-19'
feature_slug: runs-frontend
verdict: go
verdict_confidence: 0.84
exploration_charter_ref: 
  docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
proposed_adr_ref:
recommended_next_action: "/plan:plan-feature --tier=2 --charter=docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md"
related_documents:
- docs/project_plans/exploration/runs-frontend/spikes/tech-findings.md
- docs/project_plans/exploration/runs-frontend/spikes/value-findings.md
- docs/project_plans/exploration/runs-frontend/spikes/risk-findings.md
- docs/project_plans/exploration/runs-frontend/spikes/priorart-findings.md
---

# Research Foundry Runs Frontend — Feasibility Brief

---

## 1. Synopsis

A Research Foundry "run" accretes a dense, file-backed provenance graph — raw idea → intent → source cards → extraction cards → claim ledger (`clm_NNN`) → report → verification gate → evidence bundle → governance verdicts → writebacks — but today it is inspectable only via the `rf` CLI (a pass/fail gate plus counts) or by reading raw Markdown/YAML, plus a hand-curated static MkDocs case-study site. This proposes a **read-only web viewer** for the single operator that makes claim→evidence provenance, verification gates, and governance verdicts legible at a glance: turning a pile of files into a navigable run. The bet is that the operator's two highest-frequency jobs — **trusting a run's gate** and **auditing a specific claim to its quote** — are the ones the current surfaces fail hardest, and an interactive viewer that traverses the graph (rather than flattening it to text) is the win.

---

## 2. Investigation Summary

| Leg | Agent | Confidence | Findings | Conclusion |
|-----|-------|:---:|----------|------------|
| tech | spike-writer | 0.82 | [tech-findings.md](spikes/tech-findings.md) | Complete 29-entity model is deterministically derivable from on-disk artifacts + `RunPaths`; faithful read-only viewer needs no always-on service and no LLM on recall; one constraint — author `rf run export --json` first. |
| value | ux-researcher | 0.82 | [value-findings.md](spikes/value-findings.md) | At least one concrete JTBD — claim auditing — is unmet by both the CLI (pass/fail + grep across 3 files / 2 ID hops) and the static MkDocs site (one-way prose, no drill-down); top-3 viewing workflows identified. Go criterion satisfied. |
| risk | backend-architect | 0.82 | [risk-findings.md](spikes/risk-findings.md) | Charter deal-killer **REFUTED**; all 11 risks are engineering risks with defined mitigations, not architectural impossibilities. Top risks: sensitivity leakage (R9), hardcoded paths (R2), missing export command (R3), schema drift (R1). |
| priorart | search-specialist | 0.88 | [priorart-findings.md](spikes/priorart-findings.md) | Strong internal precedent: fork **IntentTree Web** runs viewer (0.92 match) + integrate **MeatyWiki Portal ArtifactLineageGraph** (0.85). Build-vs-adapt → ADAPT. H5 anchor delivers ~60% code reuse. |

---

## 3. Cost Estimate

**Rough estimate**: **~13 story points (lean)** within a reconciled band of **8–21 pts** — **Tier 2** equivalent (high reuse keeps it below the Tier 3 greenfield ceiling).

**Reconciling the two legs**: the tech leg sized this bottom-up as a **greenfield** build at **13–21 pts**; the prior-art leg sized it as an **adapt** (fork IntentTree Web + lift MeatyWiki's lineage graph) at **8–13 pts**. The delta is **entirely reuse-driven**: prior-art establishes ~60% code reuse from a sibling AOS app that is *already a runs viewer* on the same React + Vite + React Query + Tailwind stack, plus a shipping SVG-DAG lineage component. The greenfield range assumes re-implementing the API client, filter/sort/paginate UX, component library, and lineage layout — work the adapt path inherits. **Reconciled call: lean to ~13 pts (Tier 2)**, treating 8 pts as the optimistic floor only if the IntentTree fork is as clean as estimated and 21 pts as the pessimistic ceiling if the entity-model adaptation and export contract prove thornier than the schemas suggest.

**Comparable past feature (H5 anchor)**: The **IntentTree Web runs viewer** (sibling AOS app, `web/src/screens/WorkspaceRuns.tsx` + `RunCard.tsx` + typed `api/client.ts`) — an existing, operational runs viewer whose WorkspaceRuns pattern is ~90% adoptable. **Secondary anchor**: the **RF MkDocs site + 18-run case study** (commit `1ae5bff`, 2026-06-19) — same data corpus, proves the static-from-files read path is viable, and supplies a deploy template.

**Major cost drivers**:
- The deterministic `rf run export --json` + `rf run list --json` contract (Phase 1 precondition; 3–5 pts) — the highest-leverage, highest-risk-retiring slice.
- The claim-ledger view with claim→source_card→evidence drill-down (the marquee feature; 3–5 pts) — the whole value bet.
- Entity-model adaptation from IntentTree's `AgentRun` to RF's `RFRun` + nested claim/evidence/source types, and lifting MeatyWiki's lineage graph (~200 LOC copy+adapt).
- Hidden plumbing (H6): TS types generated/validated from the 20 JSON Schemas, graceful empty-states for all 9 optional entities, build/deploy glue (~2 pts).

---

## 4. Value Statement

**Primary beneficiaries**: The single operator (Nick), in two high-frequency postures — **operator-as-trust-gate** ("did this run pass, and *why* — which checks, which claims?") and **operator-as-auditor** ("this sentence asserts X — show me the source card and the exact quote behind it"). Secondary postures (portfolio-manager, governor) ride on the same parsed data as cheap add-ons; a downstream-reader use case is latent, not active.

**Evidence of demand**:
- **Run cadence is real and sustained**: 4-run batch (2026-06-13), 10-run roots wave (2026-06-14), 8-item dependent wave through 2026-06-15, plus the KnitWit pack — 18 dependency-tracked HIGH bundles in one week (project memory: `rf-run-execution-path-b`). The viewing need recurs every run.
- **A documented trust failure the current surface let slip**: AAR §1 records RIB-018, a real false-pass (a bundle-audit agent appended an inference claim with an empty `from_claims`) that only an authoritative `rf verify` re-run caught — codified as the memory rule "NEVER trust `bundle_ok:true`." A verification panel that surfaces failing checks at a glance is exactly the surface that would have made this visible.
- **Audit currently degrades to sampling**: confirming one claim requires resolving two ID hops across three files by eye; for a typical 95–102-claim run this is prohibitively slow per-claim, so auditing is sampled rather than exhaustive — the precise gap the viewer closes.

**Counterfactual**: If not built, claim auditing stays a manual three-file grep that degrades to sampling, trust stays "stare at an exit code or trust `bundle_ok`," and run visibility on the website stays gated behind a human transcribing each wave into prose — exactly the daily/weekly-report burden the project's own docs policy discourages, and a surface that goes stale the moment a run is repaired.

---

## 5. Risks & Blast Radius

| Risk | Category | Severity | Mitigation |
|------|----------|:---:|------------|
| **R9. Sensitivity / governance data leakage** — source cards carry `sensitivity` (`public`/`personal`/`work_sensitive`/`client_sensitive`); a viewer reading `extracted_points` could surface governed content to anyone reaching the loopback port. `rf redact` exists but is not auto-called. | technical / organizational | **H** | The serving layer **must filter source-card bodies by sensitivity before render** — never bypass the governance gate. Either the export step applies redaction before writing JSON, or the loopback API enforces a sensitivity threshold on GET. This is a hard architectural constraint, not a courtesy. |
| **R2. Hardcoded absolute paths** — `run_index.yaml` `run_dir`, and `verification.yaml` `report_path`/`claim_ledger_path` are absolute (local-dev mount); wrong on agentic-nuc or any clone/move. | technical | **H** | **Re-derive paths via `FoundryPaths.discover()`** (walk up to `foundry.yaml`) from workspace root + `run_id`. Trust `run_index.yaml` for *listing metadata only*; **never** trust its stored absolute paths for file reads. |
| **R3 / OQ-1. No machine-readable run enumeration/export** — no `rf run list`/`rf run export`; only a Rich table and an internal registry YAML. | technical | **H (confirmed gap)** | **Phase 1 precondition**: author `rf run export --json` + `rf run list --json` as the stable contract. De-risks R2/R5 by centralizing the file-walk + claim-graph join in Python beside the schemas. (See §6 — ADR-worthy.) |
| **R1 / R5. Schema & layout drift** — all 20 schemas use `additionalProperties: true`; most lack top-level `schema_version` enforcement. Stable to *additive* changes; fragile to *renames/removals* of required fields (`claim_id`, `run_id`) and to `RunPaths` property renames. | technical | **M** | Bind the viewer to `required:` fields only; treat extras as optional display metadata. **Pin/version-check `schema_version` per artifact in the export** and warn on mismatch. Fail loudly per-artifact ("artifact not found") rather than rendering absence as corruption. |
| **R4 / R6 / R11. Status staleness & partial runs** — `run.yaml.status` stays `planned` even for verified runs; the registry mirrors it; some runs have scaffold-without-contents. | technical | **M** | Derive effective lifecycle from `evidence_bundle.yaml.status` + `reviews/verification.yaml.passed` + artifact presence; treat `run.yaml.status` as advisory. Use `run_trace.jsonl` (JSONL) for optional telemetry only, never as a hard lifecycle dependency. |
| **R7. Scope creep toward write/edit** — `reviewer_notes`, `required_fix`, `approved_for_writeback` are natural edit targets; inline editing would bypass `rf verify`/`rf council` gates. | operational | **M** | Enforce read-only **architecturally**: GET-only serving surface, no mutation routes, no form elements; label values view-only. Record the read-only invariant in the planning-time ADR. |
| **R10. Nested `runs/runs/` anomaly** — 4 runs live one level deeper and are absent from the registry. | technical | **L** | Discovery must `runs/**/run.yaml` recursive-glob, not flat-glob or registry-only. |
| **R8. Maintenance cost for a one-operator project** — a second JS/TS codebase to maintain as RF evolves. | organizational | **M** | Adapt (don't build) per prior-art; prefer static export over an always-on server; the only RF-side coupling point to audit on upgrade is the `RunPaths`/export layer. |

**Blast radius**: No write-path or sibling-service impact — the viewer is read-only and file-backed; `writebacks/` are already produced by `rf writeback` and only read here. CLI additions (`rf run list/export`) fit the existing thin-command + service-call + Rich-render pattern (low risk). Performance is negligible (~1.9 MB of YAML across 38 runs; manageable at 1000). The one genuine integrity exposure is R9 (governance leakage), which the serving layer must close.

---

## 6. Architectural Implications

The idea fits **cleanly** into the existing file-first architecture — it requires **no structural change** to RF's data model or governance gates, and adds **no always-on service and no LLM on the recall path** (charter deal-killer refuted by the risk leg). It does, however, surface two decisions significant enough to be **ADR-worthy at planning time** (no ADR is drafted now, per the exploration-stage convention; `proposed_adr_ref` is null):

1. **The export contract (the build-sequencing precondition).** Phase 1 of any build **MUST** author a deterministic `rf run export --json` plus `rf run list --json` *before* any frontend work. Non-negotiable properties: (a) **no LLM** — pure file-walk and key-lookup; (b) discover runs via `FoundryPaths.discover()` and **re-derive every path** from workspace root + `run_id` rather than trusting `run_index.yaml`'s absolute paths (closes R2); (c) **centralize the claim→source_card→evidence join in Python** beside the schemas so the data-shape contract does not leak into the browser (closes R5 / OQ-1, the anti-pattern the tech leg explicitly rejects); (d) **pin a `schema_version` in the export** and warn on per-artifact mismatch (closes R1 drift); (e) **apply sensitivity filtering at export/serve time** (closes R9). Authoring this first is what retires R2, R3, R5, and R9 in a single deterministic slice.

2. **Static export vs. loopback read API.** The recommended primary read path is a **build-time static export → static SPA** (honors file-first / no-runtime-service, matches the just-shipped MkDocs deploy model). A **thin loopback read-only API** (`rf serve --read-only`, loopback-bound like MeatyWiki's `:8765`) is the optional second mode, warranted only if "browse runs as they land" proves a real JTBD (OQ-6); it remains within AOS constraints (read-only, loopback, no LLM). The **rejected** anti-pattern is in-browser raw-file parsing of arbitrary `runs/` paths.

Both decisions should be captured as a single ADR (`status: proposed`) at the start of feature planning, not deferred to implementation.

---

## 7. Verdict

**Verdict**: `go`
**Confidence**: 0.84

**Rationale**: All three charter `go` criteria are MET. (1) The **tech leg** (0.82) enumerated a complete, schema-backed, deterministically derivable **29-entity run model** with a defined read path — exceeding the ">= 0.7 confidence, stable model" bar. (2) The charter's **deal-killer is REFUTED** by the risk leg: a faithful viewer requires neither an always-on backend nor an LLM on the recall path; the read path honors file-first / no-LLM-on-recall. (3) The **value leg** (0.82) confirmed at least one concrete viewing JTBD — claim auditing — unmet by *both* the `rf` CLI and the MkDocs site, with two further under-served workflows. The one outstanding item — the absent `rf run export --json` / `rf run list --json` contract — is a **build-sequencing precondition** (Phase 1 of the plan), **not** a verdict blocker: it is small, deterministic, no-LLM glue, and authoring it first is what de-risks R2/R3/R5/R9. Strong internal reuse (prior-art 0.88) keeps this firmly in Tier 2. Confidence is held at 0.84 (not higher) by two real ceilings the value leg flagged: this is a single-operator quality-of-life/trust win rather than a throughput unlock, and telemetry cost fields are currently zeroed (weakening the portfolio-charts angle until that data lands).

**Recommended next action**: `/plan:plan-feature --tier=2 --charter=docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md` — and add this feasibility brief to the resulting PRD's `related_documents`. The implementation plan's **Phase 1 must be the export contract** (`rf run export --json` + `rf run list --json`), with the static-export-vs-loopback decision captured as a proposed ADR.

---

## 8. Citations

- Exploration charter: `docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md`
- Tech leg SPIKE (entity model + read-path feasibility, 0.82): `docs/project_plans/exploration/runs-frontend/spikes/tech-findings.md`
- Value leg SPIKE (consumers, counterfactual, display priorities, 0.82): `docs/project_plans/exploration/runs-frontend/spikes/value-findings.md`
- Risk leg SPIKE (risk register, deal-killer refutation, blast radius, 0.82): `docs/project_plans/exploration/runs-frontend/spikes/risk-findings.md`
- Prior-art leg SPIKE (internal/external precedent, H5 anchor, build-vs-adapt, 0.88): `docs/project_plans/exploration/runs-frontend/spikes/priorart-findings.md`
- RF MkDocs site + 18-run case study — commit `1ae5bff` (2026-06-19).
- Project memory: `rf-run-execution-path-b` (run cadence, `rf verify` gate, RIB-018 false-pass lesson).
- Code anchors: `src/research_foundry/paths.py` (`RunPaths`, `FoundryPaths.discover`), `schemas/*.schema.yaml` (20 schemas), `src/research_foundry/cli_commands.py`.

---

## 9. Run Entity → Display Matrix

The user's explicit core deliverable: consolidate the tech leg's 29 entities into a viewer information architecture — what to show, how to show it, and which job it serves. Presence legend: ●=always-present, ◐=optional/conditional, ○=upstream (linked by id). Workflow legend: **W1**=Audit a claim to its evidence (flagship), **W2**=Trust the run (verification + governance gate), **W3**=Read report with provenance overlay + status faceting, **P**=Portfolio/cross-run (adjacent secondary).

### 9.1 Entity groups → display affordances

**Group A — Run identity & inputs (header / metadata; modest interactive gain)**

| Entity | Presence | Display affordance | Serves |
|--------|:---:|--------------------|:---:|
| run (`run.yaml`) | ● | Run header bar: status badge (derived, not raw), sensitivity badge, profile chips (depth/audience/budget) | W2, P |
| routing_decision | ● | "How this run was routed" card: posture-chain stepper, tool chips, rationale quote | W2 (context) |
| research_brief | ● | Questions list (`rq_NNN` anchors); source-strategy include/exclude filter chips | W3 (context) |
| swarm_plan | ● | Agent roster table (role × posture × tool × model); required-outputs checklist with present/absent ticks | W2 (context) |
| research_intent | ○ | Header panel: objective hero text + hard-constraint pills ("every claim → source") | W2/W3 (context) |
| ibom | ○ | Side panel "run inputs": tools list, model-policy table, security-boundary callouts | context (collapsed) |
| intenttree_node | ○ | Breadcrumb / "open in IntentTree" deep-link badge | navigation |
| swarm/subagent records | ◐ (derived) | "Who did what" lane: map `swarm_plan.agents[]` ↔ telemetry stages ↔ `created_by_agent` | context (collapsed) |

**Group B — Provenance spine (the marquee; highest display value)**

| Entity | Presence | Display affordance | Serves |
|--------|:---:|--------------------|:---:|
| **claim_ledger entry (`clm_NNN`)** | ● (1..N) | **Claim-ledger table** — status/confidence/materiality badges; each row a node that expands to its sources/quotes; facet by `status`/`materiality`/`claim_type`/`confidence` | **W1, W3** |
| source_card | ● (1..N) | Literal card: trust badge, source-type icon, usage-permission pills, expandable **quote** + `locator`; **the audit terminus** and drill-down target | **W1** |
| extraction_card | ● (1..N) | Nested under its source card; per-fact confidence badge; "metrics extracted" sub-table | W1 (drill) |
| report (draft) | ● | Rendered Markdown with **inline `[claim:clm_NNN]` chips** (hover/click → claim + provenance); `**Inference:**`/`**Speculation:**` sentences color-coded by status | **W3, W1** |
| report (final) | ◐ | Tab toggle draft↔final; diff view when both exist | W3 |
| source_candidates | ◐ | Ranked candidate table with accept/reject; graceful empty-state when absent | context |
| contradiction_log | ● | Conflict callout panel; empty-state "no contradictions"; side-by-side diff when populated | W1/W2 |
| inference_log | ● | "Analytic inferences" panel linking to inference-status claims | W3 |

**Group C — Trust & governance (the gate; high value, low traversal)**

| Entity | Presence | Display affordance | Serves |
|--------|:---:|--------------------|:---:|
| **verification** | ● | **Red/amber/green checklist** of named checks; failing check deep-links to the offending claim's `locations`; big gate badge in header. *Render `verification.yaml`; never recompute — `rf verify` is the authority.* | **W2** |
| governance / key-profile verdict | ● (as data) | Governance badge (sensitivity, `key_profile_used`, `approved_for_writeback`, `human_review_required`); violations list — synthesized in the export from `evidence_bundle.governance` + `ccdash_event.governance` | **W2** |
| secret-scan result | ● (process) | Inline warning badge on flagged artifacts; aggregate "scan clean" badge derived from governance violations | W2 |
| critic_review / council_review / governance_review | ◐ | Review-packet card / per-reviewer verdict grid; collapsed by default; empty-state when absent | W2 (occasional) |

**Group D — Roll-up, telemetry & writebacks (summary + portfolio)**

| Entity | Presence | Display affordance | Serves |
|--------|:---:|--------------------|:---:|
| **evidence_bundle** | ● | **Run summary dashboard / the run "card"**: counts as stat tiles, claim-status donut, governance badge, artifact map as nav; **best single entrypoint** | **W2, P** |
| telemetry / run_trace | ● | Run timeline / stepper (plan → ingest → extract → claim_map → synthesize → verify → bundle → writeback) with per-stage status dots | W2 (context) |
| ccdash_event | ● | Cost/telemetry tiles (cost, latency, drift, quality) + reuse flags. *Caveat: cost/token fields currently zeroed; charts gated on real data.* | P |
| meatywiki_writeback | ● | Writeback-target card: destination badge, `approved_for_writeback` gate, payload preview/diff | governance preview |
| skillbom_candidate | ● | Writeback-target card: destination badge, candidate/promoted state | governance preview |
| AAR | ◐ (wave-level) | Out of v1 run scope; optional "related AAR" link at index level | — |

### 9.2 Proposed viewer information architecture

Four views, ordered by the value leg's ranking — the spine is the claim graph (Group B), framed by the trust gate (Group C) and bundle summary (Group D):

**(a) Run list view** — fork of IntentTree's `WorkspaceRuns`. One row/card per run, sourced from `rf run list --json` and one `evidence_bundle.yaml` per run: derived status badge, sensitivity badge, claim counts (supported/inference/speculation), verification pass/fail, governance verdict, cost (when populated). Filter tabs by derived state (verified / needs-review / failed / planned). Discovery walks `runs/**/run.yaml` (R10). This view *also* satisfies the adjacent **P** workflow — it automates the manually-transcribed AAR cross-run tables and obsoletes their staleness.

**(b) Run overview / "trust panel"** (serves **W2**) — landing view for a single run, built on `evidence_bundle.yaml` as the entrypoint. Header: derived status + sensitivity + governance badges. Body: the **verification checklist** (rendered, not recomputed) with failing checks deep-linking into the ledger; claim-status donut from `counts`; the stage timeline from `run_trace.jsonl`; governance/approval block. This is the surface that would have caught RIB-018 at a glance.

**(c) Claim-ledger audit view** (serves **W1** — the flagship) — the claim-ledger table with status/confidence/materiality facets. Selecting a `clm_NNN` opens a side panel resolving the two ID hops automatically: claim text + status → `sources[]` (`source_card_id` + `evidence_id`) → source card title + verbatim **quote** + `locator` + trust/usage flags. For an **inference** claim, the panel instead walks `inference_basis.from_claims` as links to the underlying supported claims. A MeatyWiki-style SVG lineage graph (source_card → extraction → claim → evidence_bundle → report) is the optional visual companion. Zero grep; two hops resolved in one or two clicks.

**(d) Report-with-provenance-overlay view** (serves **W3**) — `report_draft.md` rendered as readable Markdown; inline `[claim:clm_NNN]` citations become live affordances feeding view (c); each `**Inference:**`/`**Speculation:**` sentence color-coded by claim status; a sidebar facet shows the run's composition (e.g., ~80% supported / ~17% inference / ~2.5% speculation) and lets the reader isolate, say, every inference claim to confirm each has a populated basis. Toggle to `report_final.md` (diff) when present.

**Cross-cutting invariants for all four views**: render-only (no mutation surface, no form elements — R7); every source-card body filtered by sensitivity *before* render (R9); paths re-derived via `FoundryPaths.discover()`, never trusted from the registry (R2); all 9 optional entities show graceful empty-states, never errors (R6, OQ-3); status always derived from `evidence_bundle` + `verification`, never from raw `run.yaml.status` (R4).
