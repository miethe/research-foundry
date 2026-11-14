---
schema_version: 2
doc_type: design_spec
title: "Public Knowledge Platform: Owner Decision Pack"
status: draft
created: 2026-11-13
updated: 2026-11-13
feature_slug: public-knowledge-platform
owner: project owner
related_documents:
  - docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md
  - docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
  - docs/project_plans/PRDs/features/public-knowledge-platform-v1.md
  - docs/project_plans/design-specs/public-knowledge-platform-regrounding-checklist-2026-11-13.md
---

# Public Knowledge Platform: Owner Decision Pack

> **Owner intent, 2026-11-13:** The [owner intent](research-foundry-public-knowledge-platform.md#owner-intent-2026-11-13-governs-first-release-scope) supersedes the review-gated human showcase for first-release scope. D2 source rights, D5 separate deployment, and D8 no hosted runs survive; D7 BYOK becomes bring your own model through the toolkit. D3 reviewer quorum and D4 promotion move to the later stage when net-new findings start. The initial domain mix is agent tools and software engineering plus research methods; the earlier picks below remain a historical record, not first-release decisions.

The recommendations below record the earlier proposal; first-release decisions are recorded in the PRD and decision record node_01KZ755YBS3A99PVJBC53R4DTY.

## 0. Basis and caveats

- Authority: the design spec "Research Foundry Public Knowledge Platform" (the *spec*), baseline 2026-07-26, truth status `partially_verified`. §20 lists 12 decisions; §23 says the spec stays `shaping` until they are made.
- Shipped baseline: commits `99ef69d` and `08559a0` and the activation PRD document deployment presets, non-human principals, workspace isolation and public visibility. The [re-grounding checklist](public-knowledge-platform-regrounding-checklist-2026-11-13.md) checks the current branch; the superseded hand-off is not evidence of shipped state.
- Trust boundary: the multi-user mode is accepted for a **trusted cohort only** (spec §8, §14.15). DI-1 delta re-audit and human Mode-D signoff are still open.
- No metric, price or date below is measured. Placeholders are marked `OWNER`.

Spec §20 numbering is used (D1-D12). The six headline questions in the spec front matter map to D1, D2, D3+D4, D6, D7, D12.

The earlier proposal deferred six headline questions to the owner: domain (D1), because reviewer capacity and rights-cleared sources must be chosen; display unit (D2), because source rights require an owner policy; roles and quorum (D3-D4), because accountable people and removal terms must be selected; pilot thresholds (D6), because no baseline is measured; providers and BYOK (D7), because provider and spend choices are outstanding; and federation trigger (D12), because demand has not been measured. These recommendations record the earlier proposal; subsequent first-release decisions supersede conflicting recommendations.

---

## D1. First public domain (spec §20.1, §5, §16.3)

**Question.** Which single domain seeds the first public instance, under what inclusion, evidence, freshness, reviewer, rights and no-PHI policy?

**Options.**
- A. A narrow domain where the owner is a competent reviewer and sources are open-licensed (for example, software or tooling research).
- B. A domain with an existing external reviewer pool, at the cost of coordination.
- C. A health domain.
- D. A small mixed showcase across two or three topics.

**Recommendation, pending owner decision: A.** Spec §16.3 says a narrow, high-value domain seeds reusable assertion capital faster than a broad catalog. Spec §14.8-9 forbid PHI in the public alpha and the public execution zone; a health domain is possible only with a compliant, no-PHI corpus. Spec §18 stage 2 requires a "small rights-cleared corpus", and reviewer capacity is the stated limiting cost (§16.1); the owner as reviewer is the only capacity known to exist. D dilutes the narrow-domain hypothesis and multiplies policy writing.

**Unblocks.** D2, showcase content, the pilot baseline (D6), PRD content scope.

**Reversible?** Yes before promotion. After promotion, earlier records remain and need the D4 removal path.

---

## D2. Public display unit (spec §20.2, §10, §12)

**Question.** Which source components may the public instance show: metadata, assertion text, bounded passage snippets, or source links only?

**Options.**
- A. Metadata and source links only.
- B. A plus assertion text, with passage locators but no passage text.
- C. B plus bounded passage snippets, per source, only where rights are cleared.
- D. Full passage text for permissively licensed sources.

**Recommendation, pending owner decision: B first, with C as a per-source opt-in later.** Spec §10 says a public record contains only approved public fields. Spec §12 and §14.6 say public rights are never inferred from metadata or open-access labels and missing or unknown rights fail closed. B shows the project's own reviewed assertion text and keeps source text out until a human rights decision exists for the exact version, while still giving the reader a traceable link. C needs the positive rights-owner workflow, which §13 says is still a child-spec task.

**Unblocks.** Rights scope for D3/D4, the public API field list, page design, legal review scope.

**Reversible?** Narrowing and widening are easy. Retracting displayed text needs the D4 path, and copies in caches and exports persist, so start narrow.

---

## D3. Roles, separation of duties and quorum (spec §20.3, §13)

**Question.** Who holds the curator, domain-reviewer, rights-owner, security and incident roles, and what quorum applies to promote, correct and retract?

**Options.**
- A. Owner holds every role; a second reviewer only for rights decisions.
- B. Owner plus one named independent reviewer; two-person rule for promotion and retraction.
- C. Formal panel (curator, reviewer, counsel), two of three.
- D. Owner alone with a cooling-off delay.

**Recommendation, pending owner decision: B.** Spec §13 says a curator may not self-approve required independent gates and rights clearance cannot be delegated to a model. D conflicts with the first rule. C is realistic only after the pilot shows reviewer volume (§16.2 reviewer backlog). A is tolerable only if the showcase carries no source text (D2 = B), since rights exposure is then limited. Counsel involvement for any text display is a cost for the owner to decide.

**Unblocks.** D4, promotion workflow requirements, audit-event design.

**Reversible?** Yes. Roles can change; past decisions stay attributed.

---

## D4. Promotion, correction, retraction, deletion and tombstone contract (spec §20.4, §12)

**Question.** What is the approved contract for exact-version promotion, correction, revocation and removal, including the removal deadline?

**Options.**
- A. Manual: a human writes a promotion receipt; removal follows a documented runbook with a stated deadline.
- B. Workflow-enforced: promotion and removal are service operations with receipts, synchronous read-blocking and asynchronous cache/index reconciliation.
- C. B plus public correction requests from readers.

**Recommendation, pending owner decision: B, scoped to owner-curated content, with the removal deadline set by the owner (`OWNER`: removal SLA).** Spec §12 requires exact-version binding, successor records for corrections, synchronous blocking of tombstoned material and a bounded removal path. Inspection did not establish an end-to-end public promotion/removal workflow; the checklist marks that claim unmeasured. A is cheaper but misses the synchronous-block rule. C belongs to stage 5 (§18), which first needs a synthetic promotion/revocation prototype.

**Unblocks.** Any public record; D2 text display; the stage 2 exit gate.

**Reversible?** The contract is amendable. Published records cannot be recalled from third parties, so first promotion is effectively irreversible.

---

## D5. DI-1 and the catalog import/stat seams (spec §20.5, §8, §14.15)

**Question.** Close, or explicitly scope, the DI-1 isolation audit and the catalog import/stat workspace seams?

**Options.**
- A. Scope: the first public instance is a **separate, read-only deployment holding only promoted data and no user workspaces**; DI-1 stays open for the beta.
- B. Close: run the DI-1 delta re-audit and Mode-D signoff before any public exposure.
- C. Close only the catalog import/stat seams now; defer the audit.

**Recommendation, pending owner decision: A for the read-only instance; B as a separate gated step before any shared-store or adversarial exposure.** Spec §8 says tenant certification is trusted-cohort only, and §14.15 requires formal DI-1 re-audit and human Mode-D approval before adversarial tenancy claims. A read-only instance serving only promoted records has no cross-tenant surface, which is why scoping is defensible. That depends on deployment configuration and is not established by code inspection. Catalog imports do not pass an identity, and most statistics counts remain unscoped (`src/research_foundry/api/routers/catalog.py:101`, `:216`, `:245`).

**Unblocks.** The minimum viable public instance; stage 3 later.

**Reversible?** Scoping can be revoked, but a public claim is hard to unmake.

---

## D6. Pilot SLOs, metrics, thresholds, budget and stop conditions (spec §20.6, §16.2)

**Question.** What measurable success, failure and stop conditions define the pilot?

**Options.**
- A. Adopt the §16.2 metric list now; set numbers after a baseline period.
- B. A plus numeric thresholds now (`OWNER`-supplied).
- C. Defer metrics until after launch.

**Recommendation, pending owner decision: A.** Spec §16.2 gives a metric list but no numbers, and §16.1 says the `$0.13-$2.16` per-article figure is illustrative, model-only and unmeasured, so numbers invented now would be unfounded. Stop conditions that need no data can be set now: any PHI in a public record, any rights complaint unresolved within the D4 deadline, any exposure of a private identifier.

**Unblocks.** Spec §23 "measurable" criterion; D7/D8 budgets; D10 triggers.

**Reversible?** Yes.

---

## D7. Provider allowlist and BYOK (spec §20.7, §15)

**Question.** Which providers/models are allowlisted, and does an invited beta include BYOK?

**Options.**
- A. Platform-controlled pinned models only; no BYOK before stage 4.
- B. A for the showcase; BYOK in the invited beta via encrypted, server-resolved key references.
- C. BYOK from the start.

**Recommendation, pending owner decision: A for showcase and beta; revisit at stage 4.** Spec §15.1 says the credential seam does not establish hosted BYOK support: the production runner is absent, while a job budget field is recorded without establishing enforcement (`src/research_foundry/services/agent_job_service.py:366`, `:801`). Spec §15.2 says the showcase uses pinned allowlisted models and readers execute nothing. The read-only instance needs no model on the read path. The provider list and any paid-provider spend are `OWNER` choices.

**Unblocks.** Stage 4 design; cost forecast.

**Reversible?** Yes.

---

## D8. Hosted job, secret, quota, cost and abuse boundary (spec §20.8, §8, §17)

**Question.** What boundary governs hosted jobs, secrets, quotas, cost attribution and abuse?

**Options.** A. No hosted execution in the public instance. B. Single-worker private execution behind the trusted cohort. C. Full durable queue, key vault and quotas.

**Recommendation, pending owner decision: A for the first instance.** Spec §8 says the production SDK runner is absent; job orchestration and a recorded budget field do exist (`src/research_foundry/services/agent_job_service.py:329`, `:366`, `:801`). Inspection did not establish a tenant key vault or billing; durable queue, enforced quotas and shared multi-worker state remain open readiness questions. Spec §17 requires a durable queue before more than one worker, retries or production provider execution. Spec §11.1 excludes anonymous or self-service execution. Rate limiting already exists, but its suitability for an anonymous read-only profile requires verification; §17 says process-local limits must be replaced before horizontal scale.

**Unblocks.** Nothing in the minimum instance; gates stage 4.

**Reversible?** Yes.

---

## D9. Canonical URL and remote read/API/MCP scope (spec §20.9, §11.1, §8)

**Question.** What is the canonical public URL scheme, and which of web, HTTP API and MCP are exposed?

**Options.** A. Web plus a read-only HTTP API under one domain with stable record URLs; no MCP. B. A plus hosted read-only Knowledge MCP. C. Web only.

**Recommendation, pending owner decision: A.** Spec §11.1 requires stable identifiers and canonical URLs, and says read-only agent access follows only after the remote access profile is qualified. Spec §8 says hosted MCP is local/schema only. Spec §19 makes stable URLs a federation prerequisite, so the scheme is the hard-to-reverse part. **The domain name and registration are a cost and an owner decision.**

**Unblocks.** Public page and API build; link stability for citations.

**Reversible?** The URL scheme is not cheaply reversible once cited. Scope (adding MCP later) is.

---

## D10. Storage and incremental-index migration triggers (spec §20.10, §17)

**Question.** What measured thresholds trigger relational/object storage and incremental indexing?

**Options.** A. Adopt the §17 trigger list; numbers after the D6 baseline. B. Migrate to Postgres up front. C. Never migrate.

**Recommendation, pending owner decision: A.** Spec §17 says the current file-canonical, SQLite/FTS design supports a bounded single-host pilot and that infrastructure migration is not evidence of demand. A small curated corpus fits. B is premature.

**Unblocks.** Avoids early infrastructure spend.

**Reversible?** Yes; Markdown/YAML evidence stays portable (§17).

---

## D11. Canonical claim groupings (spec §20.11, §7.3)

**Question.** Are canonical claim groupings global, domain-namespaced, or only presentation views?

**Options.** A. Global. B. Domain-namespaced. C. Presentation views only (assertion-only mode).

**Recommendation, pending owner decision: C for the first instance.** Spec §7.3 says the platform must stay useful in assertion-only mode and groupings must not make private material public by association; §9.2 allows namespaced groupings later. C avoids building grouping lifecycle (proposal, split, rollback) for the minimum instance.

**Unblocks.** Smaller PRD scope.

**Reversible?** Yes; C creates no persistent groupings.

---

## D12. Federation threshold (spec §20.12, §19)

**Question.** What measured need and business reason would justify federation?

**Options.** A. Defer; set no threshold until stage 5 completes. B. Write a threshold now. C. Never federate.

**Recommendation, pending owner decision: A.** Spec §6 lists federation before identity, lifecycle, promotion and removal work as a non-goal, and §19 requires measured need that one canonical service plus governed cells cannot meet. Nothing exists to measure yet. Record only that infrastructure migration is not federation evidence.

**Unblocks.** Nothing now.

**Reversible?** Yes.

---

## Already settled by the spec or shipped code (not owner decisions)

- Release order: OSS release, read-only showcase, trusted-cohort beta, private ingestion/execution, reviewed contribution, federation (spec §18). No stage implies the next.
- The first public instance is curated and read-only, with no anonymous execution, direct imports, arbitrary BYOM, self-service billing or federation (§11.1).
- Models and agents propose; they do not promote, write `CLEARED_*` or attest (§12, §13, §14.5).
- No PHI in the public alpha or public execution zone (§14.8-9).
- Rights fail closed; public eligibility is never inferred (§12, §14.6).
- Hidden equals missing; public readability grants no mutation (§14.10-11).
- One canonical spine with governed domain cells, not independent public instances (§9).
- Arbitrary BYOM is self-hosted or quarantined only (§15.2).
- No adversarial multi-tenancy claim before DI-1 and Mode-D closure (§14.15).
- Verified shipped substrate (see checklist): deployment presets, local/Clerk auth, RBAC, PATs and service accounts, workspace fields, public-read visibility.

---

## Minimum viable public instance

**Goal.** A read-only instance a stranger can browse, showing a small set of owner-promoted records, with no login, no execution and no write path.

**What exists** (see the re-grounding checklist): the multi-user mode with deployment presets, local/Clerk auth, RBAC, PATs and service accounts, workspace fields and public-read visibility; a runs API and viewer; assertion, rights and catalog contracts and registry (flags default-off); a CLI that produces evidence bundles. The accepted trust level is trusted cohort.

**What remains to establish** (spec §8, §11): a public hosting receipt; an end-to-end promotion/removal workflow; a positive rights-owner role; an anonymous-safe, rate-limited read profile with canonical URLs; public-read UX for status, caveats, corrections and retractions; no-PHI and rights review of content; accessibility review (§18 stage 2); a backup and restore drill. Inspection did not establish the hosting receipt or promotion/removal workflow; this does not prove their absence. Hosted MCP is not needed.

**Ordered steps.**

| # | Step | Size | Decisions needed |
|---|------|------|------------------|
| 1 | Re-ground §8 and §15.1 against code (completed in checklist) | s | none |
| 2 | Owner decisions D1-D6 and D9 | s | those |
| 3 | Write the first-domain policy; curate a small corpus; run rights triage by hand | m | D1, D2, D3 |
| 4 | Define the public field projection: approved fields only, no private paths, workspace ids or hidden counts (§10) | m | D2 |
| 5 | Exact-version promotion and removal receipts, with synchronous read-blocking of tombstoned records | l | D3, D4 |
| 6 | Anonymous read-only profile: public-visibility records only, no mutation routes, rate limiting, hidden-equals-missing, canonical record URLs | m | D5, D9 |
| 7 | Public reader UI: search/browse, status, freshness, caveat, correction and retraction display | m | D2 |
| 8 | Reviews: no-PHI scan, rights, accessibility, security of the read profile; backup/restore drill | m | D3, D5 |
| 9 | Deploy a standalone instance holding only promoted data; record a hosting receipt | m | D9, hosting choice |
| 10 | Baseline the §16.2 read-side metrics and set thresholds | s | D6 |

**Costs the owner must decide** (none assumed): hosting; domain registration; any paid provider if records are model-produced before review (D7); counsel time for any text display (D2/D3); TLS, monitoring and backup services if not self-provided.

**Boundary.** The instance must be a separate deployment from any workspace-bearing deployment (D5-A). Any adversarial multi-tenant exposure (shared store, untrusted users, public execution) needs a formal DI-1 re-audit plus human Mode-D approval. That is a separate gated step, and this plan does not design around it.
