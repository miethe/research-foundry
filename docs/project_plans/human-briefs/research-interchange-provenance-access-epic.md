---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: epic_brief
root_kind: project_plans
id: BRIEF-research-interchange-provenance-access-epic
title: "Research Interchange, Provenance, and Agent Access — Epic Human Brief"
status: draft
category: human-briefs
feature_slug: research-interchange-provenance-access-epic
feature_family: research-interchange-provenance-access
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
plan_ref: .codex/plans/research-interchange-provenance-access-initiative-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/design-specs/notebooklm-research-foundry-refresh.md
  - docs/project_plans/design-specs/browser-research-capture-extension.md
  - docs/project_plans/human-briefs/reusable-assertion-ledger.md
  - docs/project_plans/human-briefs/rf-upstream-evidence-foundry.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.72
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags:
  - human-brief
  - epic
  - research-interchange
  - provenance
  - assertion-ledger
  - mcp
  - agent-access
---

# Research Interchange, Provenance, and Agent Access — Epic Human Brief

> Living document for human orchestrators. Agents must not load this brief unless
> their task explicitly names it. Status: draft | Updated: 2026-07-18.

## 1. Context Pointers

- **Epic PRD**: `docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md`
- **Sequencing authority**: `.codex/plans/research-interchange-provenance-access-initiative-v1.md`
- **Child 1**: `research-provenance-continuity` — provenance contracts and report-use continuity
- **Child 2**: `external-research-report-interchange` — governed external handoff import
- **Child 3**: `catalog-assisted-research-planning` — pre-discovery governed reuse
- **Child 4**: `research-foundry-knowledge-mcp` — read-only local MCP
- **Child 5**: `research-foundry-operator-mcp` — separately governed mutation MCP
- **Shaping specs**: `notebooklm-research-foundry-refresh` and `browser-research-capture-extension`
- **Reuse anchors**: Reusable Assertion Ledger, assertion-ledger activation, and RFUP; no child may replace their evidence authorities.

This brief explains initiative estimates, wave rationale, and human review concerns.
The epic owns shared product gates; child plans own implementation and validation.

## 2. Estimation Sanity Check

### Child rollup

| Child package | Locked estimate | Tier | Main cost driver |
|---|---:|---:|---|
| `research-provenance-continuity` | 40 pts | 3 | Canonical origin/run/activity, search-only receipts, materialization and lifecycle |
| `external-research-report-interchange` | 38 pts | 3 | SSRF-safe hostile-input import, exact source/passage resolution, quarantine/resume |
| `catalog-assisted-research-planning` | 28 pts | 3 | Deterministic selection/denial, freshness, revalidation, gap routing |
| `research-foundry-knowledge-mcp` | 34 pts | 3 | Exact core/RF wire contracts, non-writing projections, separate process/credential boundary |
| `research-foundry-operator-mcp` | 29 pts | 3 | Idempotency, confirmation, guard, jobs, and mutation audit |
| **Initiative floor** | **169 pts** | epic | Sum of independently estimated children; no package discount |

The six linked shaping design specs have no execution points. Their promoted work must be
estimated separately or explicitly absorbed by an approved child amendment.

### H1 — Noun-counting

The epic itself introduces no table or CRUD-with-RBAC noun. Candidate durable records
include origin envelopes, acquisition/import receipts, report-use edges, selection or
denial receipts, and MCP resource descriptors. These are primarily file-canonical or
append-only records, but each child must count its own first-class write/read surface.
No child may hide a new authoritative entity behind the phrase “metadata.”

### H2 — Dual-implementation multiplier

Not applied. Research Foundry remains one file-first implementation; a possible remote
MCP is deferred and is not estimated as a parallel implementation. If local stdio and
remote service contracts diverge during planning, affected MCP estimates must be
re-derived with H2 rather than stretched.

### H3 — Algorithmic-service flag

Flagged in four areas:

- inference/canonical-claim materialization and report-use dependency traversal,
- citation/source resolution plus resumable/idempotent import,
- catalog ranking, freshness/revalidation, and gap routing,
- operator-job scheduling, replay safety, and mutation-state reconciliation.

Each child must enumerate at least five correctness fixtures before execution. A child
that cannot enumerate them requires a SPIKE or remains blocked at its decision gate.

### H4 — Bundle-versus-sum

The epic bundles five capability areas, so the 169-point child sum is the locked
floor. Shared schemas may reduce duplicated plumbing, but they do not compress source
resolution, catalog decisioning, MCP tool contracts, or their test matrices.

### H5 — Anchor comparison

- Reusable Assertion Ledger: 72 pts for durable evidence identity, lifecycle, search,
  provenance, UI, hardening, and rollout.
- Assertion-ledger activation: current 30-pt scope for reachability and population.
- RFUP: plan says 29 pts; its human brief derives a more realistic 32-pt floor across
  six upstream enhancements.
- Embedded agent research: 24 pts for job/provider/credential/acceptance surfaces.
- Runs loopback API and runs provenance frontend: 13 pts each.

The five-child total is larger than any single anchor because the initiative combines
interchange, lineage, reuse planning, and two access threat models. Child estimates
remain close to their narrow anchors; any final delta beyond 30 percent needs written
reconciliation in the child brief.

### H6 — Hidden plumbing

Current child allocations reserve 24 pts for final plumbing/hardening phases:
schemas, DTOs, process/tool inventories, OpenAPI, audit fields, adversarial
fixtures, docs, CHANGELOG, and skill updates. Against a 145-pt core subtotal,
that is 16.6 percent and within the 15–20 percent guideline. Child briefs own
the final allocation and must prevent double-counting.

**Bottom-up total:** 169 pts.

**Top-down intuition:** 160–175 pts for five Tier-3 packages sharing mature evidence
substrate but adding canonical provenance breadth, hostile acquisition/injection
defenses, two independently auditable MCP processes, and substantial integration testing.

**Locked planning floor:** 169 pts. Re-lock only after a child H1-H6 amendment;
never back-solve child phases to preserve this number.

## 3. Wave and Orchestration Notes

**Critical path:** existing RAL/activation/RFUP -> provenance continuity -> external
interchange and catalog planning -> knowledge MCP -> operator MCP -> initiative
integration qualification.

**Wave 0 — Packet and contract freeze:** Validate the epic/meta-plan and each child
packet. Assign one owner for origin, receipt, completeness-tier, report-use, and MCP
resource-ID schemas. No progress trackers or implementation branches yet.

**Wave 1 — Provenance continuity:** Land origin, discovery/search receipt, canonical
run/activity, inference/canonical-claim, report-use, and AOS context-reference contracts.

**Wave 2 — Parallel interchange and catalog work:** The importer and catalog-planning
children may run concurrently after Wave 1. Serialize writes to source-card, assertion,
run-launch, CLI, schema, and documentation barriers.

**Wave 3 — Knowledge MCP:** Start an independent read-only process after read contracts
stabilize. Its registry, entry point, settings/credentials, dependency boundary, and
inventory remain separate from Search Router and Operator MCP; only governed read
services are shared. Local stdio is schema-aligned, not hosted-compatible.

**Wave 4 — Operator MCP:** Last implementation wave. Local stdio only; no remote
mutation surface. Preserve confirmation, idempotency, guard, audit, and human review.

**Wave 5 — Integration qualification:** Run an external handoff through exact source
resolution, verification, catalog reuse, report-use lineage, read-only retrieval, and
governed operator action. Keep external live status separate from synthetic evidence.

**Merge order:** Contract/schema work first; child service work second; access adapters
after their underlying services; cross-child fixtures and docs last. A material fix
invalidates the previous exact-tree review.

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved by |
|---|---|---|---|---|
| OQ-E1 | Epic | Is acquisition activity a run subtype or sibling artifact? | open | Provenance child decision |
| OQ-E2 | Epic | Which report anchor survives Markdown edits for report-use edges? | open | Provenance child decision |
| OQ-E3 | Epic | Which packet fields participate in the idempotency hash? | open | Interchange child decision |
| OQ-E4 | Epic | What completeness tier is sufficient for planning reuse? | open | Catalog child decision |
| OQ-E5 | Epic | Which knowledge resources require cursor pagination? | open | Knowledge MCP decision |
| OQ-E6 | Epic | Which operator tools need typed confirmation versus human review? | open | Operator MCP decision |
| OQ-E7 | Epic | What canonical HTTPS namespace could support future remote MCP resources? | deferred | Future remote-access design |
| OQ-E8 | Design spec | Can NotebookLM qualify through manual export without a local CLI? | open | NotebookLM shaping review |
| OQ-E9 | Design spec | Which browser content forms are safe to capture and retain? | open | Browser shaping review |

## 5. Deferred Items Rationale

- **NotebookLM live/API automation:** Deferred until current CLI availability and
  `notebooklm source add` syntax are verified. Manual deterministic export comes first;
  unofficial API use requires pinned dependencies and canary rollback.
- **Browser promotion into RF evidence:** Deferred beyond capture-envelope staging.
  MV3 `activeTab` and native messaging must pass permission, sensitivity, and native
  host review before source-card promotion is considered.
- **Remote MCP:** Deferred until auth, workspace isolation, canonical HTTPS resources,
  audit, rate limits, and explicit approval policy are proven.

## 6. Risk Narrative

- **Authority duplication:** The most dangerous failure is a child inventing a second
  source, assertion, verifier, or run-launch authority. Review cross-links before code.
- **Provenance laundering:** Vendor synthesis with plausible citations may look more
  trustworthy than it is. Require immutable edition and exact-passage verification.
- **Reuse overreach:** Catalog hits can conceal stale, retracted, rights-denied, or
  partial coverage. Demand deterministic denial and gap receipts.
- **Access-boundary collapse:** Combining process, registry, credentials, dependencies,
  or inventory across knowledge, Search Router, and operator tools would make
  least-privilege review unverifiable. Share governed read services only.
- **Estimate compression:** Shared substrate is real leverage, but it does not erase
  algorithmic fixtures or integration cost. The child sum remains the floor.

## 7. What to Watch For

- Search-only actions still absent from run/activity provenance.
- Tags or vendor fields being treated as origin authority.
- Import replay creating duplicate receipts or candidate records.
- Candidate claims escaping quarantine after partial source resolution.
- Catalog planning treating “no eligible hit” as “no evidence exists.”
- Knowledge tools acquiring side effects for convenience.
- Local schema alignment being reported as OpenAI/ChatGPT compatibility without a
  reachable canonical HTTPS remote profile and promoted transport/URL/cache specs.
- Operator tools returning success before guard or human-review completion.
- Synthetic tests being reported as NotebookLM, browser, or remote qualification.

## 8. Expected Success Behaviors

- [ ] A reviewer can trace an external assertion candidate to its immutable handoff
  receipt, original source edition, exact passage, RF assertion, claim/inference, and
  report-use edge.
- [ ] Replaying the same handoff produces the same receipt and no duplicate authority.
- [ ] Catalog-assisted planning records why evidence was selected, denied, revalidated,
  or routed to new discovery.
- [ ] Search-only research appears in the canonical run/activity history.
- [ ] Knowledge MCP can retrieve governed sources, assertions, reports, and runs with
  exact core/dual-encoded and RF-extended contracts, no mutation/provider tools, and
  an independent process/registry/settings/credential/inventory boundary.
- [ ] Operator MCP retries are idempotent and cannot bypass confirmation, guard, audit,
  or human review.
- [ ] NotebookLM and browser work remain visibly shaping until their promotion gates
  have literal evidence.
- [ ] Final status distinguishes planning approval, repository readiness, and live
  integration qualification.

## 9. Running Log

- 2026-07-18: Reviewer fixes re-derived child totals to 40 + 38 + 28 + 34 + 29 =
  169 points, added hostile acquisition/injection gates, and made the Knowledge MCP
  process/credential/compatibility boundary explicit. No child execution or design-spec
  promotion is authorized.
