---
title: HTTP API (rf serve)
doc_type: user_guide
schema_version: 2
status: active
created: 2026-08-06
updated: 2026-08-06
feature_slug: loopback-api
---

# HTTP API (`rf serve`)

`rf serve` starts a FastAPI application — `Research Foundry API` (version `0.1.0`) —
that exposes a JSON HTTP surface over your local Research Foundry workspace. It is
described in-code as the "Loopback read API for the Research Foundry runs viewer":
it powers the runs viewer and adds a bounded set of authoring, catalog, and audit
mutations on top of the read surface.

The server requires the `serve` extra:

```bash
pip install 'research-foundry[serve]'
```

Start it with:

```bash
rf serve --port 7432 --bind-host 127.0.0.1
```

> `rf serve` fails closed if `fastapi`/`uvicorn` are not installed — it prints an
> install hint and exits non-zero rather than starting.

## The `rf serve` command

| Flag | Default | Purpose |
|------|---------|---------|
| `--port` | `7432` | TCP port to bind (chosen to avoid the MeatyWiki API at 8765). |
| `--bind-host` | `127.0.0.1` | Host address to bind. See [Bind policy](#bind-policy-loopback-by-default). |
| `--auth-mode` | from `foundry.yaml` `viewer.auth_mode` (default `none`) | `none` or `token`. |
| `--sensitivity-threshold` | from `foundry.yaml` `viewer.sensitivity_threshold` (default `public`) | Redaction threshold applied by the read/export surface. |
| `--mode` | from `foundry.yaml` `deployment_mode` (else `single_user`) | `single_user` or `multi_user`. |

CLI flags override the corresponding `foundry.yaml` values, and the overrides are
applied **before** the pre-bind safety gate runs. After validation, the app is
constructed with `create_app(config)` and served via `uvicorn` on
`bind_host:port`.

## Base URL and shape

With the defaults above, the base URL is:

```
http://127.0.0.1:7432
```

- Application routes are mounted under the **`/api`** prefix (for example
  `GET /api/runs`).
- Operational endpoints (`/health`, `/data/governance.json`) sit at the **root**,
  outside `/api`.
- Interactive docs and the machine-readable schema are served at the FastAPI
  defaults: **`/docs`** (Swagger UI) and **`/openapi.json`**.

### Response envelope

Object-shaped (JSON object) responses are stamped with a top-level
`rf_schema_version` field so clients can detect schema drift:

```json
{
  "rf_schema_version": "1.4",
  "run_id": "run-abc123",
  "status": "planned"
}
```

Endpoints that intentionally return a **bare array** (for example `GET /api/runs`
and `GET /api/runs/{run_id}/claims`) are not stamped.

## `GET /health`

Liveness probe. Always returns `200` with:

```json
{"status": "ok"}
```

`/health` is never authenticated (see [Authentication](#authentication)), so it is
safe to use as a readiness/liveness check even when auth is enabled.

## Authentication

Authentication is **off by default**. When the config leaves `auth.provider=none`
and `viewer.auth_mode` is not `token`, no auth middleware is installed and every
request is served unauthenticated — appropriate for the single-operator loopback
default.

When auth **is** enabled (`auth.provider` set to `local_static`/`clerk`, or
`viewer.auth_mode=token`), requests must present a bearer token:

```
Authorization: Bearer <token>
```

Behaviour of the auth middleware:

- The `Authorization` header is required and must use the `Bearer ` scheme.
  A missing or non-Bearer header, or an empty token after the prefix, is rejected
  with `401`.
- The supplied token is compared against configured tokens using a
  **constant-time** comparison (`hmac.compare_digest`) to avoid timing oracles.
- On any authentication failure the response is a generic `401` — no provider
  name or token detail is leaked.
- **Exempt paths** (served without a token even when auth is enabled):
  - `GET /health`
  - `GET /api/reports/shares/{share_token}` — here the share token *is* the
    credential.

### Configuring tokens (`local_static`)

The `local_static` provider maps bearer tokens to identities. Token **values are
read from environment variables at request time** (only the variable *names* live
in `foundry.yaml`), so secrets never sit in the config file:

```yaml
auth:
  provider: local_static
  local_static:
    tokens:
      - token_env: RF_SERVE_TOKEN_ALICE
        user_id: alice
        workspace_id: default
        roles: [owner]
      - token_env: RF_SERVE_TOKEN_BOB
        user_id: bob
        workspace_id: default
        roles: [researcher]
```

A matched token resolves to an identity carrying `user_id`, `workspace_id`, and
`roles`. The legacy single-token path uses `viewer.auth_mode=token` with the token
in the env var named by `viewer.auth_token_env` (default `RF_SERVE_TOKEN`).

### Roles and authorization

Read endpoints are open to any authenticated caller (subject to sensitivity
gating). Mutations require a role:

- **`owner` / `admin`** — launch runs, delete reports, create share links, and all
  audit reads.
- **`owner` / `admin` / `researcher`** — report authoring (drafts, revisions,
  blocks, links, verify) and catalog re-import.

In **single-operator mode** (no identity present because auth is disabled), all
role gates pass unconditionally.

## Bind policy (loopback by default)

The server binds to **`127.0.0.1` by default**. Loopback addresses recognised by
the safety gate are `127.0.0.1`, `localhost`, and `::1`.

Binding to a **non-loopback** address (for example `--bind-host 0.0.0.0` for LAN
exposure) is only allowed when authentication is configured. The check fails
**closed** before any port is opened, and it is enforced in two places:

1. **`create_app()`** calls `assert_bind_is_safe(config)` as its first statement.
   If `viewer.bind_host` is non-loopback and no auth is configured
   (`auth.provider=none` and `viewer.auth_mode != token`), it raises `ValueError`
   and refuses to construct the app. This protects code that mounts the ASGI app
   directly, bypassing the CLI.
2. **`rf serve`** additionally requires, before binding a non-loopback host, that
   at least one usable token actually exists — a configured `token_env` env var
   (or the legacy `viewer.auth_token_env`) must be non-empty. Auth being
   *configured* is not enough; the token must be *resolvable*.

So a LAN bind looks like:

```bash
rf serve --bind-host 0.0.0.0 --auth-mode token   # RF_SERVE_TOKEN must be set
```

## Endpoint surface under `/api`

The endpoints below are the core surface (runs, reports, catalog, audit). The app
also mounts additional routers under `/api` — identity (`/api/auth/*`), admin,
writeback, knowledge, assertions, and (when `agents.enabled`) agent jobs — which
are outside the scope of this guide.

Sensitivity gating applies across read endpoints: records above the active
sensitivity threshold return `404` in a way that is **indistinguishable** from a
genuinely missing record (no-existence-leak). Many endpoints accept an optional
`sensitivity_threshold` query parameter to override the default per request.

### Runs

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/runs` | any | List runs (bare array, sensitivity-gated). |
| `POST` | `/api/runs` | `owner`/`admin` | Scaffold and register a new run (`201`). Body is a launch request (raw idea text or `intent_id`, plus sensitivity, planning, and reuse fields). |
| `GET` | `/api/runs/{run_id}` | any | Run detail. |
| `GET` | `/api/runs/{run_id}/claims` | any | Run claim ledger (bare array). |
| `GET` | `/api/runs/{run_id}/context` | any | Lazy-loaded context block (`null` if none). |
| `GET` | `/api/runs/{run_id}/sources/{source_card_id}` | any | Resolved source card. |
| `GET` | `/api/reports/{run_id}/anchors` | any | Report anchors for a run. |

### Reports

Report drafts are composed of blocks, versions, and claim/source links, with a
verification and publish-preview gate.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/reports` | any | List report drafts. |
| `POST` | `/api/reports` | `owner`/`admin`/`researcher` | Create a draft (`201`). |
| `GET` | `/api/reports/{report_id}` | any | Get a draft. |
| `DELETE` | `/api/reports/{report_id}` | `owner`/`admin` | Delete a draft (idempotent `204`). |
| `GET` | `/api/reports/{report_id}/versions` | any | List revisions. |
| `POST` | `/api/reports/{report_id}/versions` | `owner`/`admin`/`researcher` | Snapshot a revision (`201`). |
| `GET` | `/api/reports/{report_id}/versions/{version_id}` | any | Get a revision. |
| `POST` | `/api/reports/{report_id}/versions/{version_id}/restore` | `owner`/`admin`/`researcher` | Restore a prior revision. |
| `POST` | `/api/reports/{report_id}/blocks` | `owner`/`admin`/`researcher` | Add a block (`201`). |
| `PATCH` | `/api/reports/{report_id}/blocks/reorder` | `owner`/`admin`/`researcher` | Reorder blocks. |
| `PATCH` | `/api/reports/{report_id}/blocks/{block_id}` | `owner`/`admin`/`researcher` | Update a block. |
| `DELETE` | `/api/reports/{report_id}/blocks/{block_id}` | `owner`/`admin`/`researcher` | Delete a block (returns the updated draft). |
| `POST` | `/api/reports/{report_id}/claim-links` | `owner`/`admin`/`researcher` | Add a claim link (`201`). |
| `DELETE` | `/api/reports/{report_id}/claim-links/{claim_link_id}` | `owner`/`admin`/`researcher` | Remove a claim link. |
| `POST` | `/api/reports/{report_id}/source-links` | `owner`/`admin`/`researcher` | Add a source link (`201`). |
| `DELETE` | `/api/reports/{report_id}/source-links/{source_link_id}` | `owner`/`admin`/`researcher` | Remove a source link. |
| `POST` | `/api/reports/{report_id}/verify` | `owner`/`admin`/`researcher` | Run report checks; returns pass/fail detail (always `200`). |
| `POST` | `/api/reports/{report_id}/publish-preview` | any | Publish-preview gate; `422` when blocking checks fail, `503` if the audit store is degraded. |
| `GET` | `/api/reports/{report_id}/export` | any | Export the draft as Markdown. |
| `POST` | `/api/reports/{report_id}/share-links` | `owner`/`admin` | Create a read-only share link (`201`). |
| `GET` | `/api/reports/shares/{share_token}` | token | Resolve a share link (the share token is the credential; auth-exempt). |

### Catalog

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/catalog/stats` | any | Aggregate catalog counts and attribution coverage (never `404`). |
| `GET` | `/api/catalog/search` | any | Search the catalog. Query params include `q`, `item_type`, `project`, `status`, `sensitivity`, `run_id`, repeated `term`/`role`, `sort`, `page`, `page_size`. Empty corpus yields an empty result set. |
| `GET` | `/api/catalog/items/{catalog_item_id}` | any | Item detail with payload (`404` if unknown or over-threshold). |
| `POST` | `/api/catalog/import/run/{run_id}` | `owner`/`admin`/`researcher` | Re-import a single run (`404` if the run is unknown). |
| `POST` | `/api/catalog/import` | `owner`/`admin`/`researcher` | Re-import all discovered runs (best-effort; returns per-run errors). |

### Audit

All audit endpoints require the `owner` or `admin` role (in single-operator mode
they pass unconditionally).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/audit` | `owner`/`admin` | List audit events, most-recent-first, cursor-paginated. Query params include `mutation_type`, `actor`, `workspace`, `since`, `until`, `limit` (default `50`), and `cursor`. Response carries `items` and `next_cursor`. |
| `GET` | `/api/audit/health` | `owner`/`admin` | Audit-store health state (`healthy`/`degraded`, last probe/success timestamps, error detail). |
| `GET` | `/api/audit/{audit_event_id}` | `owner`/`admin` | Get a single audit event (`404` if unknown or cross-workspace). |

## Related surfaces

- `GET /data/governance.json` — root-level dump of the active key profiles and
  policy rules.
- `/docs` and `/openapi.json` — interactive and machine-readable API references,
  useful for exploring request/response bodies not fully expanded here.
