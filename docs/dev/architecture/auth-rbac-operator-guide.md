---
title: "Auth/RBAC Operator & Admin Guide"
description: "Configuring authentication providers, role-based access control (RBAC), and admin settings for Research Foundry deployments"
audience: ["operators", "admins", "DevOps"]
tags: ["auth", "rbac", "deployment", "configuration", "security"]
created: 2026-07-08
updated: 2026-07-08
category: "operations"
status: "published"
related_documents:
  - "docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md"
  - "docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md"
---

# Auth/RBAC Operator & Admin Guide

Research Foundry's authentication and role-based access control (RBAC) system allows you to safely expose the research control plane to multiple users on shared infrastructure. This guide covers how to configure authentication providers, understand the role model, enable Clerk, and adjust audit/rate-limit settings.

## Table of Contents

1. [Authentication Providers Overview](#authentication-providers-overview)
2. [Role Model & Capability Matrix](#role-model--capability-matrix)
3. [Enabling local_static (Air-Gapped Multi-User)](#enabling-local_static-air-gapped-multi-user)
4. [Enabling Clerk (Cloud-Hosted)](#enabling-clerk-cloud-hosted)
5. [Admin Configuration](#admin-configuration)
6. [Security Model](#security-model)

---

## Authentication Providers Overview

Research Foundry supports four authentication providers, selectable via `foundry.yaml`:

### none (Default)

- **Use case**: Single trusted operator on a private network (loopback-only).
- **Security model**: Trust boundary = network perimeter.
- **Requirements**: None (zero-dependency).
- **When to use**: Local development, personal LAN instances, test environments.
- **When NOT to use**: Never use on public or non-loopback binds — RF will refuse to start.

### local_static (Recommended for Air-Gapped Multi-User)

- **Use case**: Multi-user deployments on private infrastructure without internet access.
- **Security model**: Trust boundary = RBAC roles + static token validation.
- **Requirements**: Environment variables with bearer tokens (e.g., `RF_TOKEN_ALICE=<secret>`).
- **When to use**: Self-hosted, air-gapped, small-team LAN deployments; highly controlled multi-user scenarios.
- **Features**:
  - Zero external dependencies (no outbound internet required).
  - Supports N concurrent users with different roles within a single workspace.
  - Tokens pulled from env vars at startup; never stored plain-text on disk.
  - RBAC roles enforced server-side (see [Role Model](#role-model--capability-matrix)).

### clerk (Cloud-Hosted, Production-Grade)

- **Use case**: Cloud deployments needing enterprise identity + MFA.
- **Security model**: Trust boundary = Clerk's OIDC identity + RF's RBAC.
- **Prerequisites** (all three required):
  1. **Outbound internet access** — RF must reach Clerk's API (`https://api.clerk.dev`).
  2. **Public domain** — Registered, DNS-resolvable domain (e.g., `rf.example.com`).
  3. **Paid Clerk plan** — Free plan does not support custom RBAC roles; RF will error at startup if roles are unavailable.
- **When to use**: Production SaaS deployments, enterprises needing audit/compliance, multi-team scenarios.
- **Fail-closed behavior**: If Clerk is unreachable, all auth checks fail (no fallback to `none`).

### oidc (Deferred, FU-2)

- **Status**: Seam-only in P5.1; concrete adapter (FU-2) deferred.
- **Use case**: Support any OIDC provider (Azure AD, Okta, on-prem IdP).
- **When available**: FU-2 design-spec tracked in `docs/project_plans/design-specs/oidc-byo-adapter-implementation.md`.
- **Do not use**: Currently raises "not yet implemented" error at startup.

---

## Role Model & Capability Matrix

Research Foundry enforces a 5-role model at both the API and CLI layers. Roles are assigned per-user and enforced server-side, independent of the authentication provider.

### 5-Role Model

| Role | Description | Typical User |
|------|-------------|--------------|
| **owner** | Full control: create/edit/delete workspaces, invite users, approve writebacks, audit logs, admin settings. | Workspace lead, research director. |
| **admin** | Manage users, workspaces, rate-limit config, audit settings (no financial/data-deletion approval). | DevOps, workspace administrator. |
| **contributor** | Create/edit runs, add source cards, edit reports. Cannot approve writebacks, invite users, or change config. | Researcher, analyst. |
| **analyst** | Read-only: view runs, reports, source cards; export for offline analysis. No mutations. | Stakeholder, review board member. |
| **viewer** | Read-only public-exposure layer: view only public (non-sensitive) runs and reports. No catalog/builder access. | External stakeholder, public-facing viewer. |

### Capability Matrix

| Capability | owner | admin | contributor | analyst | viewer |
|-----------|-------|-------|-------------|---------|--------|
| **Create workspace** | ✓ | — | — | — | — |
| **Invite users** | ✓ | ✓ | — | — | — |
| **Manage roles** | ✓ | — | — | — | — |
| **Create/edit runs** | ✓ | — | ✓ | — | — |
| **Add source cards** | ✓ | — | ✓ | — | — |
| **Edit reports** | ✓ | — | ✓ | — | — |
| **Approve writebacks** | ✓ | — | — | — | — |
| **Export runs (full)** | ✓ | — | ✓ | ✓ | — |
| **Export runs (public only)** | ✓ | — | ✓ | ✓ | ✓ |
| **View audit logs** | ✓ | ✓ | — | — | — |
| **Configure rate limits** | ✓ | ✓ | — | — | — |
| **Configure auth provider** | ✓ | — | — | — | — |

---

## Enabling local_static (Air-Gapped Multi-User)

### Prerequisites

- Environment variables set with bearer tokens and their mapped user/role identities.
- No internet access required.

### Configuration Steps

1. **Set environment variables for each user:**

   ```bash
   export RF_TOKEN_ALICE="alice-secret-token-xyz"
   export RF_TOKEN_BOB="bob-secret-token-abc"
   ```

   Note: Use strong, randomly-generated tokens. Store securely (e.g., secrets vault, not version control).

2. **Edit `foundry.yaml` to enable local_static:**

   ```yaml
   auth:
     provider: local_static
     local_static:
       tokens:
         - token_env: RF_TOKEN_ALICE
           user_id: alice
           workspace_id: default
           roles: [owner]          # Alice is an owner
         - token_env: RF_TOKEN_BOB
           user_id: bob
           workspace_id: default
           roles: [contributor]    # Bob is a contributor
   ```

3. **Start RF:**

   ```bash
   rf serve
   ```

   RF reads `RF_TOKEN_ALICE` and `RF_TOKEN_BOB` from the environment, maps them to user/role identities, and validates bearer tokens on every request.

### Making Requests

Clients include bearer tokens in the Authorization header:

```bash
curl -H "Authorization: Bearer $(echo -n 'alice-secret-token-xyz')" \
  http://localhost:8000/api/runs
```

### Rotating Tokens

1. Update the environment variable with a new token.
2. Update `foundry.yaml` if the `token_env` name changes.
3. Restart RF (`rf serve` picks up new env vars).
4. Old tokens become invalid immediately upon restart.

---

## Enabling Clerk (Cloud-Hosted)

### Prerequisites (All Required)

1. **Outbound internet** — RF must reach `https://api.clerk.dev`.
2. **Public domain** — DNS-resolvable domain (e.g., `rf.example.com`).
3. **Paid Clerk plan** — Free tier does not support custom RBAC roles.

### Configuration Steps

1. **Create a Clerk application:**

   - Visit [clerk.com](https://clerk.com) and sign up.
   - Create a new application (Web, native, or hybrid depending on your frontend).
   - In **Clerk Dashboard → Settings → API Keys**, copy your **Frontend API key** (format: `https://your-app.clerk.accounts.dev`).

2. **Enable custom roles (Paid Plan Required):**

   - In **Clerk Dashboard → Permissions → Roles**, create the 5 roles: `owner`, `admin`, `contributor`, `analyst`, `viewer`.
   - Optionally add permissions under each role (Clerk's permission system is optional; RF enforces roles).

3. **Edit `foundry.yaml`:**

   ```yaml
   auth:
     provider: clerk
     clerk:
       frontend_api: "https://your-app.clerk.accounts.dev"
       outbound_internet_enabled: true    # Must be explicit
   ```

   Note: `outbound_internet_enabled: true` is required and must be set explicitly (fail-closed policy).

4. **Restart RF:**

   ```bash
   rf serve
   ```

   RF validates JWTs from Clerk and enforces roles on every request.

### User Sign-In Flow

1. User navigates to your RF frontend (e.g., `https://rf.example.com`).
2. Frontend redirects to Clerk's sign-in page.
3. User authenticates (email/password, SSO, MFA, etc.).
4. Clerk issues a JWT.
5. Frontend includes JWT in Authorization header.
6. RF validates JWT and checks role claims.
7. User gains access based on assigned role.

### Assigning Roles in Clerk

In **Clerk Dashboard → Users**:

1. Select a user.
2. Under **Roles**, click **Add Role**.
3. Select one of the 5 roles (`owner`, `admin`, `contributor`, `analyst`, `viewer`).
4. Save.

The role is immediately available in the JWT's custom claims.

### Fail-Closed Behavior

If Clerk is unreachable:
- All JWT validations fail.
- All requests return HTTP 401 Unauthorized.
- **No fallback to public access** — the system fails closed, not open.

---

## Admin Configuration

### Rate Limiting

Rate limits are configured in `foundry.yaml` under `auth.rate_limit`:

```yaml
auth:
  rate_limit:
    enabled: true                # Enable rate limiting
    requests_per_window: 60      # 60 requests per window
    window_seconds: 60           # 60-second sliding window
```

**Behavior:**
- Per-identity, per-route sliding-window limiter.
- One user's burst never throttles another.
- On exceed: HTTP 429 with `Retry-After` header.
- **Note**: Automatically disabled when `auth.provider = none` (no identity available to key on).

**Headers returned:**
- `X-RateLimit-Limit` — Total requests per window.
- `X-RateLimit-Remaining` — Requests left in current window.
- `X-RateLimit-Reset` — UNIX timestamp of window reset.
- `Retry-After` — Seconds until reset (429 only).

### RBAC Enforcement Toggle

RBAC enforcement is controlled by `auth.rbac_enforcement`:

```yaml
auth:
  rbac_enforcement: auto    # auto (default), disabled (loopback only), or enabled
```

**Values:**
- `auto` (default) — RBAC enforced when `auth.provider != none`; not enforced when `provider=none`.
- `disabled` — Force RBAC OFF. **Only allowed on loopback binds (127.0.0.1)**. Setting `disabled` on a public bind causes startup to refuse with an error.
- `enabled` — Force RBAC ON even when `auth.provider=none`.

---

## Security Model

### Trust Boundaries by Provider

| Provider | Trust Boundary | Threat Model |
|----------|---|---|
| `none` | Network perimeter | Single trusted operator behind firewall. |
| `local_static` | RBAC + static token validation | Multiple authenticated users on private network. |
| `clerk` | Clerk's OIDC identity + RF's RBAC | Multiple authenticated users via cloud provider. |
| `oidc` | OIDC provider's identity + RF's RBAC | Multiple authenticated users via on-prem/cloud IdP. |

### Fail-Closed Guarantees

1. **Default is safest** — `none` (loopback-only) is the canonical default in `foundry.yaml`. Multi-user deployments require explicit opt-in.
2. **Public binds refuse unsafe configs** — RF will not start with `provider=none` on a non-loopback bind (0.0.0.0 or public IP).
3. **RBAC is always-on when auth is enabled** — When `auth.provider != none`, RBAC is enforced by default (`rbac_enforcement: auto`).
4. **Clerk is fail-closed** — If Clerk is unreachable, requests fail (no fallback to public).
5. **Rate limits are per-identity** — One user's burst never throttles another.
6. **Audit logs capture all mutations** — Every authenticated mutation (run create, report edit, writeback approval, etc.) is logged with user identity and timestamp.

### Sensitivity & Export Gates

- **Sensitivity threshold** — Configured separately in `viewer.sensitivity_threshold` (default: `public`). Controls which source-card fields are redacted in exports.
- **Catalog visibility** — Enforced by workspace isolation (all catalog items filtered to authenticated user's workspace).
- **Share links** — Read-only, sensitivity-scoped; shared runs/reports respect the sensitivity threshold at export time.

---

## Related Documentation

- **Full PRD**: [docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md](../../../project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md) — Design rationale, acceptance criteria, security model.
- **SPIKE & ADRs**: [docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md](../../../project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md) — ADR-001 (auth-provider abstraction) and ADR-002 (agent-job credential isolation).
- **Deferred Design-Spec**: [docs/project_plans/design-specs/oidc-byo-adapter-implementation.md](../../../project_plans/design-specs/oidc-byo-adapter-implementation.md) — FU-2 OIDC adapter (deferred).
- **foundry.yaml**: [foundry.yaml](../../../foundry.yaml) — Full configuration reference with commented examples.

---

**Last Updated**: 2026-07-08  
**Phase**: Public Multi-User P5 (Auth/RBAC/Isolation/Audit Hardening)
