---
schema_version: 2
doc_type: design_spec
maturity: idea
title: "OIDC/BYO Adapter Implementation"
description: "Design specification for concrete OIDC/Bring-Your-Own-IdP adapter implementation — deferred pending on-prem-IdP consumer demand validation"
audience: [developers, operators, maintainers]
tags: [auth, oidc, adapter, design-spec, deferred, multi-user]
created: 2026-07-08
updated: 2026-07-08
category: "authentication"
status: idea
feature_slug: oidc-byo-adapter-implementation
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
  - "ADR-001 (auth-provider port, SPIKE public-multiuser-p4p5-foundations)"
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
open_questions:
  - "Does an on-prem-IdP consumer (customer or internal team) exist yet, or have stated demand for OIDC/BYO authentication?"
  - "What OIDC provider characteristics are required: authorization-code flow, refresh-token support, custom claims mapping?"
  - "Should the adapter support direct SAML → OIDC bridging, or only native OIDC providers (e.g., Keycloak, FusionAuth)?"
  - "What is the required OIDC discovery endpoint timeout and fallback behavior for on-prem deployments with intermittent network?"
priority: low
effort_estimate: "TBD (unknown scope)"
---

# OIDC/BYO Adapter Implementation

## Status: Idea (Not Active)

This design specification documents a **deferred engineering task** (FU-2 from the P5 SPIKE):
concrete implementation of a **Bring-Your-Own-IdP (BYO) adapter** for Research Foundry's
`AuthProvider` port. The **seam** (abstract protocol boundary) is already defined in P5.1/P5.4
([ADR-001](docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md)); this
specification covers what it would take to implement the adapter itself once concrete customer
or operational demand materializes.

**Maturity: `idea`** — not `shaping`, not `ready`. This document captures the design questions
and known constraints; promotion to `shaping` requires evidence of a real on-prem-IdP consumer
(internal or external) with stated authentication needs.

---

## Context & Motivation

### Current State (P5 Baseline)

P5.1/P5.4 introduced an `AuthProvider` port with two concrete adapters:

- **`local_static`** (default): static per-token → role mapping, zero external dependency, air-gapped.
- **`clerk`** (opt-in): pure-Python JWT verification against Clerk's hosted JWKS, with Clerk Organizations → RF roles mapping.

The `oidc` adapter seam is defined as a **Protocol**-level abstraction (see ADR-001); the concrete
implementation does not exist yet. The adapter will enable operators to bring their own on-prem OIDC
provider (e.g., **Keycloak**, **FusionAuth**, **Dex**, or an internal corporate IdP) without
depending on Clerk's managed infrastructure.

### Why Defer?

1. **No known consumer yet**: Research Foundry's P5 GA target (public LAN/edge deployment) has not
   yet identified an on-prem-IdP customer or internal deployment requiring SSO/OIDC.
2. **Scope uncertainty**: Concrete requirements (authorization-code flow, token refresh, claim mapping,
   discovery-endpoint fallback for degraded networks) are unmeasured; committing to an implementation
   before demand clarifies risks over-engineering.
3. **Seam-first delivery**: The abstract `AuthProvider` port is complete and testable (mock OIDC
   adapter possible); shipping the seam unblocks customer feedback without an OIDC implementation.

---

## Design Envelope (Known Constraints)

### AuthProvider Port Seam (ADR-001)

From the SPIKE verdict, the OIDC adapter must satisfy the `AuthProvider` protocol:

```python
class AuthProvider(Protocol):
    async def authenticate(request: Request) -> AuthIdentity | None:
        """Extract and validate identity from request; return None if auth fails."""
        ...

    async def register() -> None:
        """One-time setup (e.g., JWKS cache warming, discovery-endpoint fetch)."""
        ...
```

The adapter returns an `AuthIdentity`:

```python
@dataclass
class AuthIdentity:
    user_id: str
    workspace_id: str
    roles: list[str]  # mapped from OIDC claims
```

### Configuration Surface

The adapter is wired via `foundry.yaml`:

```yaml
auth:
  provider: oidc
  oidc:
    discovery_url: "https://idp.internal/oauth/.well-known/openid-configuration"
    client_id: "research-foundry"
    client_secret: "${OIDC_CLIENT_SECRET}"  # from environment or secrets store
    # Additional options TBD:
    # scope: ["openid", "profile", "email", "groups"]
    # role_claim_path: "groups"  # or custom claim mapping logic
    # token_endpoint_timeout_ms: 5000
    # discovery_cache_ttl_seconds: 3600
```

### Design Assumptions (Unvalidated)

1. **Authorization-Code Flow**: browser-initiated OAuth/OIDC login, not client-credentials or SAML.
2. **JWT token format**: standard RS256 or ES256 signed JWTs (not opaque reference tokens).
3. **Claims mapping**: at least `sub` (user_id), and a configurable claim for roles/groups.
4. **Discovery-endpoint available**: the `/.well-known/openid-configuration` endpoint is reachable
   and stable (discovery-endpoint availability is a prerequisite; degraded-network fallback TBD).
5. **No implicit grant flow or legacy OAuth 2.0**: assuming modern OIDC-compliant providers.

---

## Known Open Questions (Promotion Triggers)

1. **On-prem-IdP consumer existence** (CRITICAL)
   - Is there a real customer, internal team, or operational scenario that requires an on-prem OIDC provider?
   - Does the consumer have a specific OIDC provider in mind (Keycloak, FusionAuth, corporate SAML → OIDC bridge)?

2. **Token refresh and session management**
   - Should the adapter support refresh tokens (rotate short-lived access tokens)?
   - If yes: where is the refresh token stored (secure HTTP-only cookie vs. in-memory)?
   - Session timeout and revocation requirements?

3. **Claims mapping and role federation**
   - How are roles/groups extracted from OIDC claims (standard `groups` claim, custom claim, SCIM groups)?
   - Does the adapter support OIDC-defined role hierarchies, or map flat groups → RF roles?
   - What is the fallback if a user lacks a role claim (deny all, assign default role)?

4. **Discovery-endpoint availability and fallback**
   - Should the adapter cache the discovery endpoint indefinitely, or validate on each request?
   - On-prem deployments often have intermittent network; what is the fallback if discovery fails?
   - Should JWKS keys be cached, and for how long?

5. **SAML interop** (lower priority, clarify scope)
   - Does any consumer need SAML → OIDC bridging (e.g., corporate Okta/Azure AD already deployed)?
   - If yes, is a dedicated SAML adapter preferable, or a OIDC bridge to a SAML provider?

6. **Multi-tenancy and claim isolation**
   - Should a single OIDC provider instance serve multiple RF workspaces?
   - Does the adapter need to map workspace_id from an OIDC claim, or assume single workspace per RF instance?

---

## Implementation Sketch (Placeholder)

Once demand clarifies, the implementation would follow this rough outline:

### Phase A: Discovery & Validation (Shaping)

- [ ] Confirm on-prem-IdP consumer and their OIDC provider (e.g., Keycloak 23.x).
- [ ] Validate OIDC discovery endpoint and JWKS endpoint availability.
- [ ] Validate required claims (sub, role/group claim path, workspace_id if multi-tenant).
- [ ] Create a contract test stub (mock OIDC provider response; no live provider needed yet).

### Phase B: Core Adapter (Ready)

- [ ] Implement `OIDCAuthProvider` (AsyncAuthProvider mixin):
  - Fetch and cache discovery endpoint.
  - Fetch and cache JWKS.
  - Verify authorization-code (browser redirect) or introspect bearer token (API).
  - Map claims → `AuthIdentity`.
- [ ] Configuration loading & validation in `create_app`.
- [ ] Unit tests: mock OIDC provider, claim extraction, role mapping.
- [ ] Integration test: contract test against known provider (Keycloak or FusionAuth sandbox).

### Phase C: Hardening (if needed post-GA)

- [ ] Refresh-token support (if session persistence required).
- [ ] Discovery-endpoint resilience (cache + fallback, not hot-reload on every request).
- [ ] Rate limiting on JWKS fetch (prevent abuse if discovery endpoint is slow).
- [ ] Frontend context awareness (OIDC adapter → dynamic login flow in AuthContext.tsx).

---

## Acceptance Criteria for Promotion to Shaping

This spec becomes `shaping` once:

- [ ] **Confirmed consumer**: A customer, internal team, or operational scenario with stated OIDC/on-prem-IdP requirement.
- [ ] **Provider validated**: The consumer's OIDC provider details are documented (Keycloak, FusionAuth, corporate SAML bridge, etc.).
- [ ] **Claims clarified**: Required OIDC claims (sub, roles/groups, workspace_id) are enumerated and validated against the provider.
- [ ] **Scope locked**: The implementation envelope (refresh tokens, SAML interop, multi-tenancy) is decided based on consumer input.
- [ ] **Risk assessment**: On-prem network resilience (discovery-endpoint fallback, token caching) requirements are defined.

---

## Deferred to Future Phase

This specification does **not** include:

- **Full OIDC implementation** (refresh tokens, authorization-code server flow, SAML interop, multi-tenancy) — scope TBD post-demand clarification.
- **Frontend auth-context changes** — if OIDC requires dynamic login UI, that is a separate P5.8-adjacent task.
- **Performance benchmarks** — OIDC discovery/JWKS fetch latency budgets are TBD.
- **Regulatory/compliance** — HIPAA, SOC 2, GDPR alignment is organizational, not engineering.

---

## Related Documents

- **ADR-001** (SPIKE verdict): Auth-provider port design, seam definition, Clerk + local_static baseline.
- **P5 Parent Plan**: `public-multiuser-p5-auth-rbac-v1.md` — deferred items triage table.
- **P5.1 Phase (Auth Port)**: implementation of `AuthProvider` seam, `local_static`, and Clerk adapter.
- **P5.4 Phase (Clerk Integration)**: Clerk adapter refinement and frontend auth-context wiring.

---

## Next Steps

1. **Marketing/PM**: Gather customer feedback on OIDC/on-prem-IdP demand.
2. **If demand exists**:
   - Create a follow-up design-spec with confirmed consumer details and claim mapping.
   - Promote to `shaping` once scope is locked.
3. **If no demand emerges** (post-GA):
   - Keep this spec as a reference for future consumers ("here's how to add OIDC").
   - Close the issue as a deferred capability.

---

**Maturity**: idea
**Last Updated**: 2026-07-08
**Status**: Awaiting on-prem-IdP consumer feedback for promotion trigger.
