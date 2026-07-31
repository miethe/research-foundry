---
schema_version: 2
doc_type: phase_plan
title: "Operator MCP — P1-P2 executed record (legacy phase structure)"
status: completed
created: 2026-07-18
updated: 2026-07-30
phase: "1-2"
phase_title: "Contract/Identity/Confirmation; Durable Operation Coordinator"
feature_slug: research-foundry-operator-mcp
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
entry_criteria: ["RPC-1.G and KMCP-1.G satisfied upstream"]
exit_criteria: ["OPM-1.G closed (owner acceptance, e5a2e6e)", "OPM-2.G re-gate pending on tree be6ba96"]
---

# P1-P2 Executed Record (legacy phase structure)

> **Historical record, not guidance.** P1 and P2 were authored and executed under the pre-Claude-5
> phase/task/pin structure and finish under those rules — including the per-task agent, model, and
> effort pins below, which are **deprecated-not-deleted** (`plan-doctrine.md` rule 3) and must not be
> stripped or extended.
>
> The remaining work (M1-M3) is defined in the parent plan:
> [`research-foundry-operator-mcp-v1.md`](../research-foundry-operator-mcp-v1.md) — do not use this
> file as a template for it.
>
> **Current status**: P1 CLOSED by owner acceptance (`e5a2e6e`; last machine verdict
> `CHANGES_REQUESTED`, round-6 re-gate deferred as `OPM-DF-regate`). P2 implementation COMPLETE, gate
> NOT OBTAINED on tree `be6ba96` — next action is a re-gate, not a re-fix.

> Preserved verbatim as the record of work executed under the pre-Claude-5 rules, including its
> per-task agent/model/effort pins. **Not a template for M1-M3** — the remaining work is defined in
> [Milestones (M1-M3)](#milestones-m1-m3) below.

### Phase Summary (P1-P2 only — legacy structure, retained as the executed record)

| Phase | Title | Estimate | Target subagent(s) | Model | Effort | Gate |
|---|---|---:|---|---|---|---|
| P1 | Contract, Identity, and Confirmation | 4 pts | backend-architect, api-designer | sonnet | extended | CLOSED by owner acceptance (`e5a2e6e`); last machine verdict CHANGES_REQUESTED |
| P2 | Durable Operation Coordinator | 5 pts | python-backend-engineer | sonnet | extended | Security (AC-mandated), then Karen — **OPEN, re-gate pending** |
| **Subtotal** | — | **9 pts** | — | — | — | — |

> The agent/model/effort columns above are the **executed record of P1-P2**, not guidance for the
> remaining work. Per `plan-doctrine.md` rule 3 they are deprecated-not-deleted: they still parse for
> in-flight phases, and must not be stripped mid-execution. **Do not extend this table to M1-M3** —
> the remaining 20 pts carry `routing_constraints` instead, and a Phase Summary table for them is
> retired by doctrine (it duplicated `wave_plan`).

### Phase P1: Contract, Identity, and Confirmation

**Dependencies**: Research Provenance Continuity `RPC-1.G` and Knowledge MCP `KMCP-1.G` approved exact-tree contracts.
**Integration owner**: backend-architect.
**Exit state**: effect writers have stable schemas, trusted identity inputs, policy order, confirmation semantics, limits, and safe errors.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| OPM-1.1 | Operation and tool contract | Define closed operation kinds/tool names, input/result schemas, canonicalization, limits, target refs, stage prerequisites, and Knowledge MCP non-overlap inventory. | Positive/negative fixtures validate; unknown/wildcard operations reject | 1 pt | api-designer | sonnet | extended | RPC-1.G, KMCP-1.G |
| OPM-1.2 | Identity and sensitivity contract | Resolve trusted local `AuthIdentity`, require workspace, compute strictest sensitivity, and freeze no-existence-leak behavior before lookup. | Missing/wrong identity and two-workspace fixtures return one safe denial | 1 pt | backend-architect | sonnet | extended | OPM-1.1 |
| OPM-1.3 | Guard/preflight and confirmation | Order capability/RBAC/audit-health/guard/preflight checks; define opaque token binding, TTL, one-time atomic consumption, policy-drift and exact-replay rules. | Expired/replayed/mismatched token matrix produces zero manifest/effects | 1 pt | backend-architect, python-backend-engineer | sonnet | extended | OPM-1.2 |
| OPM-1.4 | Receipt and bounded-error schemas | Freeze operation/action/effect/checkpoint/terminal receipt fields, audit disposition, reason codes, retryability, redaction, and size limits. | Golden/negative schemas reject unbounded/raw exception and unauthorized fields | 1 pt | api-designer | sonnet | extended | OPM-1.1 |
| OPM-1.G | Tier-3 contract gate | Review identity source, authorization-before-lookup, confirmation binding, receipts, tool inventory, provenance reuse, task/AC traceability, and exact P1 tree. | task-completion-validator then Karen APPROVE the same exact tree; material changes invalidate both verdicts | gate | task-completion-validator, Karen | sonnet/opus | extended | OPM-1.2, OPM-1.3, OPM-1.4 |

**Quality gate**:

- OPM-OQ-1..4 resolved or defaults explicitly approved.
- Security reviewer verifies authorization-before-lookup and token binding.
- `task-completion-validator` then Karen approve the same exact schemas/examples/threat-matrix tree.
- No effect adapter or MCP server exists yet.
- **Status (2026-07-29): `OPM-1.G` is NOT APPROVED — 6 blocking findings open in `FIND-P1-R3`.**
  `schemas/operator_mcp_receipt.schema.yaml` was never adversarially attacked until round 3 (rounds
  1 and 2 both targeted `operator_mcp_policy.py` and the error schema); two of the six blocking
  findings came from its first real review. Treat it as still under-reviewed.

### Phase P2: Durable Operation Coordinator

**Dependencies**: `OPM-1.G` approved on the exact current tree.
**Integration owner**: python-backend-engineer.
**Exit state**: stable operation manifests coordinate AgentJob attempts and converge through retry/cancel/resume.

**Inherited P1 obligations (frozen — DUR-1)**: consumption is a compare-and-swap on `status` from
exactly `issued` to `consumed`, in the SAME durable transaction as the operation-manifest write,
under an exclusive single-writer lock (SQLite `BEGIN IMMEDIATE`, or `O_EXCL` create-then-atomic-
rename). A CAS observing any other status MUST route to exact-replay/idempotency-conflict and MUST
NOT execute. P1's `consume_confirmation` is a pure function — real atomicity is P2's job, and **a
read-then-write implementation passes every P1 test and is still wrong**. This requirement is
folded into `OPM-2.1`'s acceptance criteria below.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-2.1 | Immutable operation store | Atomically persist canonical operation/action manifests, input/policy digests, token-consumption proof, workspace, sensitivity, and target refs under confined local state. | Exact manifest replay resolves same operation; changed manifest conflicts; **consumption CAS on `status` (`issued`→`consumed`) occurs in the same durable transaction as the manifest write, under an exclusive single-writer lock; any other observed status routes to exact-replay/idempotency-conflict and does not execute** | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-1.G |
| OPM-2.2 | AgentJob attempt adapter | Reuse create/load/events/artifacts/status/poll/terminate/cleanup with identity scoping; link attempts to operation id; do not expose `accept_job`. | Legacy AgentJob reads pass; wrong-workspace attempts are indistinguishable from missing | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-2.1 |
| OPM-2.3 | Effect/checkpoint/terminal receipts | Persist immutable action/effect receipts and separate atomic checkpoints; reconcile counts/digests into one terminal receipt; link supplemental audit event/disposition. | Truncated/extra/duplicate/reordered/mismatched receipt fixtures deny | 1 pt | python-backend-engineer, data-layer-expert | sonnet | extended | OPM-2.2 |
| OPM-2.4 | Cancel and resume state machine | Persist cancellation request, honor safe points, mark non-cancelable atomic sections, resume first incomplete action under fresh policy/confirmation and new attempt. | H3 ten-scenario matrix converges with uninterrupted effects | 1 pt | python-backend-engineer | sonnet | extended | OPM-2.3 |

**Quality gate**:

- Process-loss, exact-retry, conflict, cancel, resume, policy-change, and reconciliation fixtures pass.
- Operation receipt is primary; audit-service failure is explicit and cannot erase effect truth.
- **Revised gate (post-P1 retro):** a security reviewer carrying an explicit AC-mapping mandate
  reviews the exact lifecycle candidate, then Karen approves. Durability/atomicity is a security
  property, and a validator alone will approve a read-then-write compare-and-swap.

