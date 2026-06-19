---
title: "Design Spec: Runs Viewer — Auth & LAN Exposure (OQ-4)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-06-19
updated: 2026-06-19
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

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-frontend-v1` (Phase 5, DOC-006) |
| **Reason** | Loopback-only serving is sufficient for the v1 operator workflow. No confirmed use case for multi-device LAN access (e.g. browsing from a phone while `agentic-nuc` serves the SPA). Introducing auth before the loopback API itself ships (OQ-6) would be premature. |
| **Promotion trigger** | An active operator need for LAN exposure is confirmed — specifically: operator wants to browse runs from a device other than the one running `rf`; or the loopback API (OQ-6) ships and a networked access scenario emerges. |
| **Target spec path** | `docs/project_plans/design-specs/runs-auth-lan.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover:

- **Binding model** — whether the viewer/API binds to `127.0.0.1` (loopback,
  current) or `0.0.0.0` (LAN-reachable, gated behind a flag or config key).
- **Authentication** — what credential model is appropriate for a local-LAN
  tool: shared secret, mTLS, SSH tunnel, or no-auth with IP allowlist.
- **Threat model** — who can reach the port; what the worst-case data exposure
  is given `foundry.yaml → viewer.sensitivity_threshold`.
- **`agentic-nuc` scenario** — the node at `10.42.10.76` runs RF as a service;
  the operator's laptop accesses the viewer at `http://10.42.10.76:<port>`.
  This is the primary motivating use case.
- **Config surface** — `foundry.yaml → viewer.bind_host`, `viewer.auth_mode`,
  and the relationship to the `RUNS_FRONTEND_LOOPBACK_API` flag from OQ-6.

### v1 Constraint (enforced in `adr-runs-read-path.md`)

In v1, the SPA is served from a **loopback-only** static-file server. No LAN
binding, no authentication surface. This is not configurable in v1.

---

## Notes for Promotion

- Coordinate with OQ-6 (loopback API spec) — auth only matters if there is a
  live server to protect. Design these together.
- The sensitivity threshold (`public` default) is the primary data-exposure
  boundary; auth is a defense-in-depth layer on top of it.
- Review `agentic-nuc` node config (`~/dev/homelab/development/agentic_meta_dev/
  infra/agentic-node/README.md`) for the existing port/binding model of other
  services before designing a divergent approach.
