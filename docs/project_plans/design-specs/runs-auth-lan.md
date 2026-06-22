---
title: "Design Spec: Runs Viewer — Auth & LAN Exposure (OQ-4)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: promoted
created: 2026-06-19
updated: 2026-06-22
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
feature_slug: runs-frontend
deferred_from: runs-frontend-v1
deferred_item_id: OQ-4
category: scope-cut
owner: nick
related_docs:
  - docs/dev/architecture/adr-runs-read-path.md
  - docs/project_plans/design-specs/runs-loopback-api.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
---

# Design Spec: Runs Viewer — Auth & LAN Exposure (OQ-4)

> **Maturity: promoted** (June 2026) — Loopback auth and gated LAN exposure are now implemented in `runs-loopback-api-v1`. Advanced auth modes (mTLS, SSH-tunnel) deferred to v2.

---

## Implementation Summary (v1.0)

| Field | Value |
|-------|-------|
| **Promoted from** | `runs-frontend-v1` (Phase 5, deferred as OQ-4) |
| **Promoted to** | `runs-loopback-api-v1` (Phase P4, June 2026) |
| **Status** | Core auth implemented (token-over-loopback); gated LAN exposure shipped |
| **Implementation details** | Phase P4 (Auth & LAN Gating) of the implementation plan |

---

## Implementation (v1.0)

### Binding Model

- **Default (loopback)**: `127.0.0.1:7432`, no auth required
- **LAN mode (opt-in)**: `0.0.0.0:7432`, requires `--auth-mode token` and `RF_SERVE_TOKEN` env var
- Fail-closed: server exits non-zero if `bind_host=0.0.0.0` but no token configured

### Authentication (v1.0)

**Shared-secret token (implemented)**:
- Token lives in `RF_SERVE_TOKEN` environment variable (never in config file)
- SPA sends `Authorization: Bearer <token>` header via `VITE_RUNS_LOOPBACK_API_TOKEN` (build-time env var)
- Token comparison uses `hmac.compare_digest` (constant-time, timing-attack resistant)
- GET /health always returns 200 (unauthenticated liveness probe for load balancers)

### IP Allowlist (v1.0)

Optional defense-in-depth layer:
- `foundry.yaml → viewer.allowlist: ["10.0.0.0/8", "192.168.1.0/24", ...]` (CIDR or IP addresses)
- Middleware blocks requests from unlisted IPs with HTTP 403 before auth check
- Empty allowlist (default) allows all IPs

### Config Surface (v1.0)

All via `foundry.yaml → viewer.*`:

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `bind_host` | string | `"127.0.0.1"` | Server bind address |
| `serve_port` | int | `7432` | Server listen port |
| `auth_mode` | enum | `"none"` | `"none"` (loopback) or `"token"` (LAN) |
| `auth_token_env` | string | `"RF_SERVE_TOKEN"` | Name of env var holding the token |
| `allowlist` | list | `[]` | IP allowlist; empty = allow all |
| `cors_origins` | list | `["*"]` | CORS allowed origins |

Plus SPA environment variables (set at build time):
- `VITE_RUNS_FRONTEND_LOOPBACK_API=true` — enable loopback API mode
- `VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:7432/api` — API base URL
- `VITE_RUNS_LOOPBACK_API_TOKEN=<token>` — bearer token (if auth_mode=token)

### Threat Model

See the threat model section in `docs/dev/architecture/adr-runs-read-path.md` (amended June 2026).

### agentic-nuc Scenario (v1.0)

Supported:
- `agentic-nuc` at `10.42.10.76:7432` runs `rf serve --bind-host 0.0.0.0 --auth-mode token`
- Operator's laptop at `http://10.42.10.76:7432/api` with token in request header
- Sensitivity threshold (`public` by default) is the primary data boundary

---

## Deferred (v2)

### DEF-01: mTLS (Mutual TLS)

**Rationale**: Requires certificate provisioning infrastructure (CA, cert distribution). Disproportionate to the threat model (shared LAN, local users). Token auth covers current needs.

**Promotion trigger**: Agentic-nuc deploys a certificate authority (e.g. HashiCorp Vault) **or** operator explicitly requests mTLS for multi-user untrusted networks.

**Implementation sketch**: Starlette middleware to validate client certificate against trusted CA; optional server certificate pinning.

### DEF-02: SSH-Tunnel Auth Mode

**Rationale**: Adds port-forwarding boilerplate. Token-over-loopback covers the threat adequately (shared secret, no cleartext credentials on the wire if HTTPS is added later). SSH-tunnel plumbing out of scope for v1.

**Promotion trigger**: Operator uses `agentic-nuc` from an untrusted network where SSH-tunnel forwarding is preferred over exposed token API.

**Implementation sketch**: Document SSH-tunnel setup in README; no server-side changes needed. Example: `ssh -L 7432:localhost:7432 agentic-nuc`.
