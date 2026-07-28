---
schema_version: 2
doc_type: design-spec
title: "External Research Public/Cross-Workspace Interchange (ERI-DF-4)"
status: draft
maturity: shaping
created: 2026-07-27
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
related_documents:
  - docs/dev/architecture/external-research-handoff-contract.md
  - docs/dev/architecture/adr-rights-entity-model.md
deferred_from: "ERI Phase 1 (Contract Freeze) / Phase 6 (Hardening) — deferred item ERI-DF-4 in the ERI implementation plan's Deferred Items table"
---

# External Research Public/Cross-Workspace Interchange (ERI-DF-4)

## What is deferred

ERI v1 is strictly **single-workspace-scoped**: `workspace_id` is always required and explicit
(contract §1.3), every per-item authorization check denies on a workspace mismatch
(`cross_workspace_denied`, one of the closed 19-code vocabulary), and `AssertionRegistry` itself is
workspace-isolated at the storage-root level (`external_research_interchange.py`'s
`self.root = .../workspaces/<workspace_key>/...`). There is no mechanism to import a packet as
shared, cross-workspace, or public-facing evidence — nor to export a packet, receipt, or resolved
evidence *out of* one workspace for consumption by another.

This spec names, but does not scope, a future **public/cross-workspace exchange** mode: something
that would let one workspace's ERI-imported (and resolved/verified) evidence be intentionally shared
with, or re-imported into, a different workspace or a public-facing surface.

## Why it was deferred (from the implementation plan)

> Public/cross-workspace exchange needs independent rights/sensitivity promotion.

This is squarely a **rights and governance** boundary, not an engineering convenience. RF's rights
model (`docs/dev/architecture/adr-rights-entity-model.md`) already treats rights clearance as a
human/counsel-only surface — no agent-writable code path can mint a `CLEARED_*`/`counsel_approved`/
`attested` value (governance guard `no_agent_cleared_rights_value`). A source acquired and resolved
under one workspace's own rights/sensitivity posture was authorized for THAT workspace's use — sharing
it with another workspace, or a public audience, is a **new** rights decision, not a mechanical data
move, and ERI-6.0's own caller-reauthorization work (this same phase; see the contract's §1.6a) is a
deliberately narrow, workspace-scoped mechanism that does not attempt to solve cross-workspace sharing
— it exists specifically to keep a revoked caller from replaying within their OWN workspace, nothing
more.

Additionally, the workspace-isolation storage model (`AssertionRegistry`, `ExternalResearchInterchange`)
was built and tested (WKSP-304 enforcement) around the invariant that one workspace's evidence never
crosses into another's storage root implicitly. Any cross-workspace mechanism has to be an explicit,
audited, opt-in operation layered on top — never a default behavior, and never something ERI's own
per-item authorization gate should be weakened to permit as a side effect.

## Trigger for promotion

Per the plan's Deferred Items table: "Rights review and tenant-safe resource identities."
Concretely, before this is promotable:

1. A **rights review** (human/counsel, per the existing rights-entity model's own review discipline)
   explicitly signs off on what categories of ERI-resolved evidence may ever be shared cross-workspace
   or made public, and under what `rights_summary`/`rights_record` state.
2. **Tenant-safe resource identities**: today's content-addressed identities (`sed_<sha256>` editions,
   content-addressed passages, `receipt_digest`) are workspace-scoped by construction (the storage
   root, not the digest itself, provides isolation) — a cross-workspace scheme needs an identity model
   that remains safe to expose across that boundary without leaking one workspace's private resource
   existence/counts to another (the same "safe denial, zero leaked facts" discipline the contract's
   §4.3 already applies within a single workspace would need to extend across workspaces too).
3. An explicit, opt-in sharing/export operation is designed — never an implicit widening of an
   existing read path's authorization scope.

## What this spec does NOT do

It does not design a sharing API, does not propose a public-visibility flag on any ERI artifact, and
does not touch the existing per-workspace storage isolation model, which stays exactly as strict as
it is today until this is formally promoted and reviewed.
