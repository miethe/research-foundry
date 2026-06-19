---
schema_version: 1
doc_type: exploration_finding
leg: value
title: "Runs Frontend — Value Leg Findings (Consumers, Counterfactual, Display Priorities)"
feature_slug: runs-frontend
status: complete
created: 2026-06-19
author: ux-researcher
---

# Value Leg — Who consumes RF runs, and what's UNMET by the CLI + MkDocs site

## TL;DR

A run is a **provenance graph** — `report → [claim:clm_NNN] → claim_ledger → source_card_id+evidence_id → quote@locator` — but every existing surface flattens it into linear text. The `rf` CLI gives you a pass/fail gate and counts; the MkDocs site gives a hand-curated prose narrative *about* runs (the AARs). **Neither lets you traverse the graph.** The single most-unmet job is **claim auditing**: confirming that a specific sentence in a report is actually backed by the quote it claims, without grepping across 3+ files and resolving two ID hops by eye. There is at least one concrete viewing JTBD unmet by both surfaces (the Go criterion is satisfied), and a clear top-3 of workflows a viewer must nail.

---

## 1. Consumer segments and frequency of the viewing need

RF is single-operator by design (Nick), so the segmentation is by *posture/mode of the same person*, not by headcount. Frequency is grounded in the run cadence recorded in memory (`rf-run-execution-path-b`: 4-run batch 2026-06-13, 10-run roots wave 2026-06-14, 8-item dependent wave through 2026-06-15, plus the KnitWit pack; 18 dependency-tracked HIGH bundles produced in one week).

| Consumer (posture) | What they need to see | Frequency | Evidence |
|---|---|---|---|
| **Operator-as-trust-gate** (primary) | "Did this run actually pass, and *why* — which checks, which claims?" Re-runs `rf verify` because it does not trust the workflow's self-reported `bundle_ok`. | **Every run** (the AAR records a real false-pass, RIB-018, that authoritative re-verify caught — bundle-audit agent appended an inference claim with empty `from_claims`). | `runs/.../reviews/verification.yaml` (per-check `status`); memory rule "NEVER trust `bundle_ok:true`"; AAR §1 RIB-018 repair |
| **Operator-as-auditor** (primary) | "This sentence asserts X — show me the source card and the exact quote behind it." Spot-checks claim→evidence provenance. | **Per-run, ad hoc**; spikes when a finding looks too strong or is about to be reused downstream. | `report_draft.md` inline `[claim:clm_NNN]` → `claim_ledger.yaml` `sources[].source_card_id/evidence_id` → `src_*.md` `extracted_points[].quote/locator` |
| **Operator-as-synthesizer/reader** (primary) | "What did this run actually conclude?" Reads exec summary + comparison matrices; wants inference/speculation visually distinct from supported fact. | **Per-run**, immediately post-completion. | `report_draft.md` (`**Inference:**` labels inline); claim-status model in `README.md` |
| **Operator-as-portfolio-manager** (secondary) | "Across 18+ runs: which are verified, how many claims, how much did each cost, which still need review?" Cross-run rollup. | **Per-wave / weekly**; today done by hand in AARs. | `evidence_bundle.yaml` `counts`+`governance`; `ccdash_event.yaml` `metrics`; AAR run-by-run tables |
| **Operator-as-governor** (secondary) | "What key profile / sensitivity ran this; is it cleared for writeback; any policy violations?" | **Before any writeback**, esp. for `work_sensitive`/`client_sensitive`. | `evidence_bundle.yaml` `governance`; `ccdash_event.yaml` `governance.violations` |
| **Downstream reader** (tertiary, plausible) | A future MeatyWiki/SkillMeat consumer or a shared link to *one* run's evidence for a colleague. Read-only, no RF context. | **Rare today** (writebacks are file-candidates only, integrations untested live per memory). Latent, not active. | `writebacks/*` candidates; `arc-intenttree-integrations-untested-live` memory |

**Reading of the segmentation:** value concentrates in the two *primary* operator postures — **trust-gate** and **auditor**. These are the jobs done on every single run and the ones where the current surfaces fail hardest. The portfolio/governor postures are real but lower-frequency, and downstream readers are aspirational. A v1 viewer should optimize for the first two and treat the rest as cheap add-ons (they ride on the same parsed data).

---

## 2. Counterfactual — what the operator does today, and the specific friction

### (a) The `rf` CLI

The CLI is a **gate and a generator**, not a browser. From `README.md`: `rf verify --fail-on-unsupported` returns an exit code (0 pass / 4 unsupported / 7 review-required / …) and `rf status`, `rf cost`, `rf bundle --verify` produce summaries.

- **It answers "pass/fail?" but not "show me why."** `verification.yaml` holds rich per-check detail (`all_claim_ids_exist`, `supported_claims_have_source_cards`, `inferences_have_basis`, each with `severity` and `locations`), but the operator either trusts an exit code or opens the YAML by hand. To see *which* claim failed, you read the file.
- **No traversal.** There is no `rf claim show clm_042` that prints the claim, its source card, and the quote in one view. To audit one claim you **manually resolve two ID hops across three files**: find `[claim:clm_042]` in `reports/report_draft.md`, grep `clm_042` in `claims/claim_ledger.yaml` to get `source_card_id` + `evidence_id`, then open `sources/src_*.md` and scan `extracted_points` for the matching `evidence_id` to read the quote and locator. For a 95–102-claim run (typical, per AAR) this is prohibitively slow per-claim, so **auditing degrades to sampling** — the exact gap that let RIB-018 false-pass slip until an authoritative re-verify.
- **Counts without context.** `evidence_bundle.yaml` gives `claims_supported/inference/speculation`, but to see *which* 18 claims are inference and whether each has a populated `inference_basis.from_claims`, you read the ledger top-to-bottom.

### (b) The static MkDocs case-study site (commit 1ae5bff)

The site is a **hand-authored narrative**, sourced from the AARs (`docs/projects/research-foundry/aars/*.md`). It is excellent at what it does and reveals exactly what it does *not* do.

- **It is curated prose, not the live artifact.** The roots-wave AAR's "run-by-run results" table (Sources / Claims sup-inf-spec / Verify / Bundle) and per-run "Findings" bullets are **manually transcribed** from the bundles. It is a snapshot a human wrote, and it summarizes only the runs someone chose to write up (18 of a growing set).
- **One-way, no drill-down.** You can read "RIB-002: 95 claims, 0 unsupported, verified" but you **cannot click into clm_004 and see the RARR quote**. The provenance chain that *is the product's core value* (claim → source card → quote) is invisible on the site. The case study tells you the gate held; it cannot let you re-audit the gate.
- **Goes stale and doesn't scale.** Because it's transcribed prose, it diverges from disk the moment a run is repaired (the RIB-018 fix happened *after* its first verify) and a new run isn't on the site until someone writes a new AAR section. Authoring an AAR table for every wave is exactly the "daily/weekly report" burden the project's own docs policy discourages.

**Net friction in one line:** *To trust a run you read an exit code or a YAML by hand; to audit one claim you grep across three files and resolve two ID hops by eye; to see a run at all on the website you wait for a human to transcribe it into prose.*

---

## 3. Run entities ranked by DISPLAY VALUE

Ranking criterion: how much does an interactive visual rendering beat raw text/CLI for the operator's two primary jobs (trust + audit)? "Display value" = (relational/graph density) × (frequency of inspection) × (current friction).

| Rank | Entity (on disk) | Why it needs a viewer | Verdict |
|---|---|---|---|
| **1** | **Claim ledger** (`claims/claim_ledger.yaml`) | The hub of the provenance graph. Each entry links *out* to source cards (supported) or *to other claims* (inference `from_claims`). A viewer turns each `clm_NNN` into a node you expand to its sources/quotes and filter by `status`/`materiality`/`confidence`. This is where flat YAML hurts most. | **Must visualize** |
| **2** | **Report ↔ ledger cross-links** (`reports/report_*.md` inline `[claim:clm_NNN]`, plus `**Inference:**`/`**Speculation:**` labels) | The report is *meant* to be read, but its value multiplies when each citation is a live link to the claim+evidence and each labeled sentence is color-coded by status. Bidirectional: claim → "where is it cited" (`report_locations`). | **Must visualize** (overlay, not replace prose) |
| **3** | **Source card** (`sources/src_*.md`) | Holds the `quote`, `locator`, `trust.source_rank`, `usage` flags (e.g. `allowed_for_public_output`), and `known_limitations`. The audit terminus — "show me the exact words." Highly valuable as the *target* of a click from rank 1/2; lower value browsed standalone. | **Must visualize** (as drill-down target) |
| **4** | **Verification result** (`reviews/verification.yaml`) | Per-check `id/severity/status/locations`. A red/green checklist with the failing claim's `locations` deep-linked into the ledger is far better than reading YAML or trusting an exit code. Directly serves the trust-gate job and the RIB-018 false-pass lesson. | **High — visualize as a status panel** |
| **5** | **Evidence bundle** (`evidence_bundle.yaml`) | The natural **run summary card** — `counts`, `governance`, `lineage`, artifact pointers. Best rendered as the run's header/overview and the cross-run table row. | **High — the run "card"** |
| **6** | **Telemetry / CCDash event** (`telemetry/*`, `writebacks/ccdash_event.yaml`) | `metrics` (claims, cost, latency, rework, drift, `quality_score`) power a portfolio dashboard. Note current files show `tokens_estimated:0`, `cost_estimated_usd:0.0` (real cost lives in the AARs/workflow telemetry, not the event yet) — so charts are only as good as the data, a caveat for the tech/risk legs. | **Medium — rollup charts** |
| **7** | **Run config / lineage** (`run.yaml`, `routing_decision.yaml`, `swarm_plan.yaml`) | `profile` (depth/audience/max_cost/model_profiles) + the `intent/ibom/brief/swarm/route` ID chain. Useful as metadata/breadcrumbs; modest interactive gain. | **Medium — metadata panel** |
| **8** | **Writeback candidates** (`writebacks/meatywiki_writeback.md`, `skillbom_candidate.md`) | Rendered markdown previews of downstream artifacts. Nice-to-have read-only preview; low traversal value. | **Low — render as markdown** |
| **9** | **Research brief** (`research_brief.md`), **extraction cards** (`extractions/ext_*.yaml`), **reviews** (`reviews/critic_review.yaml`, `council_review.yaml`) | Context/intermediate artifacts. Briefs read fine as prose; extraction cards are an internal hop already summarized in source cards + ledger; council/critic reviews are occasional. | **Low — fine as raw text / collapsed** |

**The shape this implies:** the viewer's spine is the **claim graph** (entities 1–3) with the **verification panel** and **bundle summary** (4–5) framing it; everything else is supporting metadata or markdown preview.

---

## 4. Top 3 viewing workflows the frontend must nail

### Workflow 1 — Audit a claim to its evidence (THE flagship; highest unmet value)
- **Task:** From a sentence/citation in the report, reach the exact supporting quote and judge whether it holds — in one or two clicks, not three file-greps and two ID hops.
- **Entities:** report `[claim:clm_NNN]` → claim_ledger entry (`status`, `confidence`, `materiality`) → `sources[]` (`source_card_id`, `evidence_id`, `relation`, `locator`) → source card `extracted_points[]` (`quote`, `locator`, `trust.source_rank`, `usage`).
- **"Good" looks like:** click a citation → side panel shows the claim text + status badge → expand to the source card title, the verbatim **quote**, the `locator` (e.g. "Section 3.1"), and trust/usage flags (e.g. "not allowed for public output"). For an **inference** claim, the panel instead shows `inference_basis.from_claims` as links to the underlying supported claims (so the reasoning chain is walkable). Zero grep, two ID hops resolved automatically. This is the job the CLI and the static site both fail; nailing it is the whole bet.

### Workflow 2 — Trust the run (verification + governance gate)
- **Task:** Decide whether to trust/writeback a run by seeing *which* checks passed and *which* claims (if any) are weak — replacing "stare at an exit code / trust `bundle_ok`."
- **Entities:** `verification.yaml` (`passed`, `exit_code`, `checks[].id/severity/status/locations`) + `evidence_bundle.yaml` `counts` + `governance` + `ccdash_event.yaml` `governance.violations`.
- **"Good" looks like:** a green/amber/red checklist of the named checks (`supported_claims_have_source_cards`, `inferences_have_basis`, `material_claims_have_claim_ids`, …); any failing/`warning` check deep-links to the offending claim's `locations` in the ledger; a governance badge (sensitivity, `key_profile_used`, `approved_for_writeback`, `human_review_required`). This is precisely the surface that would have made the RIB-018 false-pass (inference claim with empty `from_claims`, no label) visible at a glance instead of slipping to a manual re-verify. Note: the viewer should *render* `verification.yaml`, not recompute it — `rf verify` remains the authority (file-first, no-LLM-on-recall).

### Workflow 3 — Read the report with provenance overlaid + status faceting
- **Task:** Read the actual conclusions while keeping supported / inference / speculation visually distinct, and pivot to "show me only the inference claims" or "only material claims" to gauge how much of the report is fact vs. synthesis.
- **Entities:** `report_draft.md` body (prose + matrices + inline `[claim:clm_NNN]` + `**Inference:**`/`**Speculation:**` labels), facet/filter over `claim_ledger.yaml` (`status`, `materiality`, `claim_type`, `confidence`).
- **"Good" looks like:** report rendered as readable markdown with citations as hover/click affordances (feeding Workflow 1) and each labeled sentence color-coded by status; a sidebar facet showing the run's composition (e.g. roots-wave norm ~80% supported / ~17% inference / ~2.5% speculation per AAR §1) and letting the reader isolate every `inference` claim to confirm each has a populated basis. Turns "a wall of claim-tagged text" into a navigable, trustworthy document.

*(Adjacent, lower-priority: a cross-run portfolio table — one row per `evidence_bundle.yaml` with counts/verify/governance — directly automates the manually-transcribed AAR tables and would obsolete the staleness problem in §2(b). Strong secondary win; rank it just below the top 3.)*

---

## 5. Verdict input

- **Go criterion (value):** **Satisfied.** At least one concrete viewing JTBD — claim auditing (Workflow 1) — is unmet by both the `rf` CLI (pass/fail + grep) and the static MkDocs site (one-way prose, no drill-down). Workflows 2 and 3 are also materially under-served. All three read entirely from on-disk artifacts whose shapes are confirmed above, consistent with the file-first / no-LLM-on-recall constraints (the viewer renders existing files; it does not recompute verification or call a model).
- **What would lower value:** the consumer is a single operator, so this is a quality-of-life / trust-quality win, not a throughput unlock; telemetry fields are currently zeroed in the event files (cost/latency live in AARs), so the portfolio-charts angle is weaker until that data lands. These cap the ceiling but do not threaten the core bet.

**Value confidence: 0.82**
