---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-research-foundry-operator-mcp
title: "Research Foundry Operator MCP — Human Brief"
status: draft
category: human-briefs
feature_slug: research-foundry-operator-mcp
feature_family: research-foundry-operator-mcp
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - .codex/worknotes/research-foundry-operator-mcp/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.72
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags: [human-brief, mcp, operator, governance, jobs, receipts]
---

# Research Foundry Operator MCP — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`
- **Decisions block**: `.codex/worknotes/research-foundry-operator-mcp/decisions-block.md`
- **Parent epic**: `docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md`
- **Initiative sequence**: `.codex/plans/research-interchange-provenance-access-initiative-v1.md`
- **Hard dependencies**: Research Provenance Continuity P1; External Interchange P5; Catalog Planning P4; Knowledge MCP tool/resource contract
- **Existing MCP pattern**: `src/research_foundry/services/search_router/mcp_server.py` and `docs/project_plans/design-specs/research_foundry_search_router_spec.md`
- **SPIKEs**: None. Known runtime seams and explicit security gaps make contract-first implementation appropriate; promote a targeted SPIKE only if AgentJob reuse cannot satisfy the operation lifecycle matrix.

## 2. Estimation Sanity Check

**Bottom-up total**: 29 points
**Top-down anchors**: Public Multi-User P4 Embedded Agent Research (planned 24 pts), Assertion-Ledger Activation (current planned 30 pts), External Research Report Interchange (planned 34 pts), and the existing thin Search Router MCP adapter
**Confidence**: medium. The repository contains plans, current code, and landed surface evidence but no authoritative actual-point ledger. These are scope anchors, not observed velocity.

### H1 — Noun counting

No new CRUD-with-RBAC database table is proposed. The package introduces three file/schema-level concepts—operator operation manifest, confirmation binding, and immutable operator receipt—but reuses existing AgentJob attempts/events/artifacts and existing RBAC/audit stores. H1's ≥2-point-per-new-CRUD-noun floor does not apply.

The lack of a table does not make identity cheap: P1 still budgets 4 points for schemas, authorization ordering, workspace/sensitivity binding, confirmation, and bounded errors.

### H2 — Dual-implementation multiplier

Not applicable. V1 has exactly one transport and deployment shape: local stdio. Remote HTTP/SSE/WebSocket and hosted/public deployment are deferred, so there is no local-plus-remote dual implementation to multiply. If remote transport enters this package, re-estimate rather than adding it to P5.

### H3 — Algorithmic service flag

Flagged for the durable operation coordinator because it performs scheduling, cancellation, resume, replay, and conflict resolution. The minimum scenario matrix is:

1. exact retry before execution returns the same operation;
2. exact retry after completion returns the same terminal receipt;
3. same idempotency key with changed payload/target/policy denies;
4. expired, replayed, wrong-actor, or wrong-workspace token causes zero effects;
5. cancel before first action produces a canceled receipt with zero effects;
6. cancel during a multi-action operation stops at the next safe point;
7. process loss after an effect receipt but before checkpoint resumes without replay;
8. truncated, extra, duplicate, reordered, or mismatched effect receipts deny resume;
9. policy/sensitivity change before resume requires fresh preflight and confirmation;
10. non-cancelable atomic publication completes or fails without a partial artifact.

The plan enumerates these tests; a SPIKE is unnecessary unless implementation cannot map them to AgentJob attempts plus an operation manifest.

### H4 — Bundle versus sum

| Capability area | Points | Rationale |
|---|---:|---|
| Contract, identity, confirmation, errors | 4 | Security and schema breadth |
| Durable coordinator and lifecycle | 5 | H3 state machine over existing AgentJob primitives |
| Plan/swarm/lifecycle adapters | 5 | Existing `plan_run`; swarm extraction and job integration remain |
| Import/research-stage adapters | 5 | Seven closed service adapters plus ERI seam |
| Stdio server and writeback preview | 6 | Tool registry, namespace split, limits, optional dependency, pure preview proof |
| Hardening/docs/plumbing | 4 | Adversarial matrix, compatibility, docs, CHANGELOG, deferred specs |
| **Sum** | **29** | Bottom-up total |

Five capability areas exceed H4's decomposition threshold. The 29-point total is the sum, not a discounted bundle estimate.

### H5 — Anchor reference

- Public Multi-User P4 already built AgentJob schemas/service/API/CLI with launch/status/events/cancel/accept and was planned at 24 points. Operator MCP reuses those primitives but must close workspace-scoping TODOs, add confirmation/idempotency/resume, and avoid accept.
- Assertion-Ledger Activation demonstrates why reachability plus workspace confinement and receipts can grow after real mapping; its current plan is 30 points. Operator MCP's 29 points is similar in security/integration breadth but has no historical corpus migration.
- External Research Interchange is 34 points because it owns hostile packet schemas, producer profiles, source resolution, and a resumable importer. Operator MCP consumes its service seam and does not copy that work.
- Search Router MCP proves the FastMCP lazy-import/stdio adapter pattern is small. It does not provide privileged-operation policy or durable lifecycle.

No anchor delta is presented as actual productivity. The estimate must be revisited if ERI or Knowledge MCP contracts move materially.

### H6 — Hidden plumbing budget

P1–P5 total 25 points. P6 budgets 4 points (16%) for adversarial integration, legacy AgentJob compatibility, schema/tool introspection, optional-dependency checks, docs, CHANGELOG, deferred specs, and reviewer evidence. This falls within the 15–20% guideline.

**Reconciliation**: 29 points is credible only with the hard boundaries: local stdio, closed tools, no Knowledge MCP duplication, no agent-job accept, no live writeback, no remote transport, and no arbitrary execution.

## 3. Wave & Orchestration Notes

**Critical path**: RPC P1 + Knowledge MCP contract -> OPM P1 -> P2 lifecycle -> CARP-gated P3 -> ERI-gated P4 -> P5 stdio/preview -> P6 exact-tree gate.

**Parallel opportunities**: Within P1, schema fixtures and read-only threat review can proceed separately. Within P2/P4, tests may be authored beside implementation when ownership does not overlap. Avoid concurrent writers in `agent_job_service.py`, `governance.py`, `audit_service.py`, `writeback.py`, and the operation registry.

**Merge order**: Freeze schemas/policy first. Land operation lifecycle before tools. Land run/swarm before external import/stages. Register MCP only after adapter contracts settle. Reconcile docs and introspection fixtures against one final tool list.

**Cross-feature coupling**: OPM must consume RPC receipt/context refs, ERI's import service, CARP's plan/run contract, and Knowledge MCP's namespace. A material change to any consumed contract invalidates the dependent seam approval.

## 4. Open Questions Ledger

| ID | Question | Status | Default if unresolved | Resolved by |
|---|---|---|---|---|
| OPM-OQ-1 | What establishes trusted local actor/workspace identity? | open | Explicit configured identity; no request-body/default workspace | — |
| OPM-OQ-2 | Confirmation TTL and exact replay semantics? | open | 5 minutes; consume with manifest; exact replay returns receipt | — |
| OPM-OQ-3 | One confirmation per stage or confirmed action chain? | open | One operation; chain requires one complete bounded manifest | — |
| OPM-OQ-4 | Cancellation safe points? | open | Between actions; atomic publication non-cancelable | — |
| OPM-OQ-5 | AgentJob reuse boundary? | open | Attempts/events/artifacts/status only; operation manifest owns effects | — |
| OPM-OQ-6 | Must audit-health degradation block confirmation? | open | Yes; mandatory operator receipt remains primary | — |
| OPM-OQ-7 | Writeback preview staging root? | open | Operation staging root, never target mirrors | — |
| OPM-OQ-8 | Verification failure terminal state? | open | Completed governed result with downstream block | — |

## 5. Deferred Items Rationale

- **Remote transport**: Deferred because local stdio does not solve remote authentication, authorization, TLS/origin, canonical URL, revocation, rate-limit, approval UI, or multi-instance routing. Promote after a separate threat model and approved design spec.
- **Live writeback**: Deferred because preview safety does not establish authorization for external effects. Promote only after target-specific approval, idempotency, rollback/compensation, and owner-held canary design.
- **Arbitrary automation**: Shell, filesystem, URL, provider, adapter, plugin, scheduler, and unattended chains are excluded. Promote individual named operations only when a measured use case and canonical service exist.
- **Public/hosted qualification**: Repository fixtures cannot authorize exposure. Promotion requires owner identity, private data, deployment, and operational evidence.

## 6. Risk Narrative

- **Identity is the central risk**: Existing AgentJob mutation paths still advertise workspace TODOs. Do not treat local stdio or process ownership as a substitute for explicit identity/workspace binding.
- **Receipts and audit are different**: The audit service is intentionally fail-open. Each operator effect needs a primary immutable operation/effect receipt; audit delivery is a linked secondary disposition.
- **Cancellation is not process kill**: The durable manifest and effect receipts decide what may resume. Killing a subprocess without reconciliation is not a valid cancel implementation.
- **Preview is a negative proof**: The important evidence is that no integration client, downstream mirror, or live writeback path is reachable from the registered tool.
- **Thin adapters stay thin**: If a handler starts parsing external packets, building claims, or choosing providers, scope has leaked from the owning service package.

## 7. What to Watch For

- CLI ingest currently resolves a hard-coded `default` workspace. Operator MCP must not copy that behavior.
- Agent-job `accept` is documented as the sole staged-artifact promotion path; it is out of scope and must not appear in the tool inventory.
- Search Router MCP's `extract_url` has effects despite living in a search server. Knowledge/Operator MCP boundaries must classify tools by effect, not by current module name.
- `audit_service.record_event()` never raises; do not infer successful audit persistence from a successful mutation.
- `services.writeback.writeback()` can push or mirror. A preview implementation must have a separate call path.
- The current swarm command contains orchestration inline. Extract a canonical service used by both CLI and MCP instead of calling Typer.
- MCP schema or generated tool changes invalidate prior exact-tree review.

## 8. Expected Success Behaviors

- [ ] Tool introspection shows only the closed Operator MCP inventory and no Knowledge MCP search/source/assertion/report/run read tools.
- [ ] A plan request returns a preview and confirmation binding before any run directory exists; executing the exact confirmed request creates one operation and one run.
- [ ] A wrong-workspace job id returns the same safe shape as a missing id and leaks no event/count/path detail.
- [ ] Repeating a completed operation with the same idempotency key returns the same receipt and creates no new source, extraction, claim, report, bundle, or preview artifact.
- [ ] Canceling a staged multi-action fixture and resuming it converges with uninterrupted execution byte-for-byte for canonical effects.
- [ ] ERI import is unavailable until the child importer service is present and approved; MCP never substitutes its own parser.
- [ ] A failed verify operation is an explicit governed result and blocks a chained bundle action.
- [ ] Writeback preview produces a local staged preview while network, integration-client, and mirror spies remain untouched.
- [ ] Missing MCP SDK produces one clear installation hint while base-package import and existing CLI tests remain green.
- [ ] Final closeout distinguishes repository readiness from owner-held canary, deployment, release, remote transport, and live writeback authorization.

## 9. Running Log

- [2026-07-18] Draft package created. Bottom-up H1-H6 estimate locked at 29 points. H3 lifecycle scenarios are explicit; H5 uses planned/shipped surface comparisons only because no authoritative actual-point ledger was found. Remote transport and live writeback remain deferred.
