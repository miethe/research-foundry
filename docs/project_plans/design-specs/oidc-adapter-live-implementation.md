---
schema_version: 2
doc_type: design_spec
title: "Public Multi-User Release Activation: OIDC Adapter Live Implementation (DF-001)"
status: draft
maturity: idea
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
problem_statement: >
  The `oidc` auth provider remains a registered, unimplemented seam (raises "not yet
  implemented" at startup); no live on-prem/BYO-IdP integration exists, so operators
  needing SSO against Azure AD/Okta/Keycloak/an internal IdP cannot deploy Research
  Foundry against their own identity provider.
open_questions:
  - "Does an on-prem-IdP consumer (customer or internal team) exist yet, or have stated demand?"
  - "See docs/project_plans/design-specs/oidc-byo-adapter-implementation.md for the full open-question set (unchanged by this re-anchor)."
explored_alternatives: []
related_documents:
  - docs/project_plans/design-specs/oidc-byo-adapter-implementation.md
  - docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
---

# OIDC Adapter Live Implementation (DF-001)

## Status: Idea (Not Active)

This is the **public-multiuser-release-activation** feature's deferred-item anchor for
DF-001 ("OIDC adapter live implementation") per that plan's Deferred Items Triage Table.
It intentionally does **not** duplicate the existing, fully-detailed design record —
`docs/project_plans/design-specs/oidc-byo-adapter-implementation.md` (FU-2, authored
under the anchor `public-multiuser-p5-auth-rbac-v1`) already covers the `AuthProvider`
port seam, configuration surface, design assumptions, open questions, and a phased
implementation sketch for the concrete OIDC/BYO-IdP adapter. **That document is the
design envelope; this document is the pointer + promotion-trigger record for this
feature's specific deferral decision.**

## Why this feature defers it (decisions-block, accepted)

> "OIDC = deferred (seam/stub only; explicitly out of scope)." — `oidc.py` remains a
> registered, unimplemented seam; no live IdP integration work is in scope for
> public-multiuser-release-activation (PRD §7 Out of Scope). This feature's
> `multi_user` fail-closed gate checks `auth.provider != "none"` — a decision
> deliberately decoupled from Clerk/OIDC procurement status, so `local_static`
> already satisfies the gate for closed-beta/air-gapped `multi_user` deployments
> without waiting on OIDC.

## Trigger for Promotion

Unchanged from the FU-2 spec: an IdP procurement decision is made **and** a concrete
tenant/consumer is available to validate against. See
`oidc-byo-adapter-implementation.md`'s "Known Open Questions (Promotion Triggers)"
and "Acceptance Criteria for Promotion to Shaping" sections for the full checklist —
this anchor promotes to `shaping` the moment that document does.

## Next Steps

1. When a concrete on-prem-IdP consumer emerges, update
   `oidc-byo-adapter-implementation.md` (not this file) with the confirmed provider
   details and promote it to `shaping`.
2. Mirror the promotion by setting this anchor's `maturity: shaping` and linking the
   updated spec, so both this feature's deferred-items registry and the original
   FU-2 spec stay in sync.
