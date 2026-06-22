---
title: "ADR: Runs Frontend Read Path"
doc_type: adr
status: amended
schema_version: 1
created: 2026-06-19
updated: 2026-06-22
feature_slug: runs-frontend
resolves: ["OQ-1", "OQ-6", "R7", "R9"]
related_docs:
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
  - docs/project_plans/design-specs/runs-loopback-api.md
  - docs/project_plans/design-specs/runs-auth-lan.md
owner: nick
---

# ADR: Runs Frontend Read Path

## Status

**Amended** (2026-06-22) — Original decision (**Accepted** at P5) recorded static export as the primary, sole v1 read path. This amendment records that the loopback API (`rf serve`) has been implemented as a secondary, opt-in read path (Phase P7 of `runs-loopback-api-v1` feature). Both paths coexist; the choice is controlled via the `VITE_RUNS_FRONTEND_LOOPBACK_API` environment flag at SPA build time. The sensitivity gate, read-only invariant, and path-safety requirement remain binding on both paths.

---

## Context

The Research Foundry runs viewer (`frontend/runs-viewer/`) needs a data source
for displaying run provenance, claim audit trails, and verification status. Three
candidate read paths were evaluated during pre-commitment exploration
(`docs/project_plans/exploration/runs-frontend/`):

| Candidate | Description | Verdict |
|-----------|-------------|---------|
| **Static JSON export** | `rf run export --json` writes a denormalized `run.json` per run at pre-build or on-demand; the SPA loads from the filesystem via a static-file server | **Selected (PRIMARY)** |
| **Loopback REST API** | A local HTTP server (`rf serve`) exposes live artifact reads at `localhost:PORT` | Deferred behind `RUNS_FRONTEND_LOOPBACK_API` flag — see Deferred section |
| **Direct YAML read** | Browser JS reads raw `run.yaml`, `claim_ledger.yaml`, etc. | Rejected — browser cannot access arbitrary filesystem paths; multi-file join at render time is slow and error-prone |

The **static JSON export** path was selected because:
- The foundry is file-first: the SPA should be a *view* over on-disk artifacts,
  not an always-on daemon that must remain running.
- Static export aligns with the "CLIs are the contract" invariant — the SPA is a
  read-only consumer of a well-defined, frozen JSON shape.
- No network daemon means no auth surface, no port-conflict risk, and trivially
  predictable behavior on the operator's laptop and on `agentic-nuc`.
- Denormalizing the claim graph at export time (join once, in Python) keeps the
  SPA free of graph-join logic, which would be slow and would place logic on the
  recall path.

---

## Decision

**Dual-mode read path**:

1. **Static JSON export (PRIMARY, default)**: `rf run export --json` writes a denormalized `run.json` per run. The SPA loads from a static-file server. No always-on backend required.
2. **Live loopback API (SECONDARY, opt-in)**: `rf serve` runs a read-only FastAPI server on loopback (`127.0.0.1:7432`). The SPA switches to this API via the `VITE_RUNS_FRONTEND_LOOPBACK_API=true` environment flag. LAN exposure to `0.0.0.0` is gated behind `--auth-mode token` with a fail-closed bind check.

Both paths apply the same sensitivity gate (P9 Invariant 1 below), enforce the read-only contract (Invariant 2), and route through established path-safety logic (Invariant 3 for loopback; Invariant 3 already applies to export). The SPA's fetch client (`frontend/runs-viewer/src/api/client.ts`) is structured behind a dual-mode seam that allows switching between them without component changes.

### Load-Bearing Invariants

These invariants are enforced architecturally and tested at each phase gate. They
may not be relaxed without a superseding ADR.

#### Invariant 1 — R9 Sensitivity Gate

> **Sensitivity redaction is applied at the export layer. Governed content never
> enters `run.json`. No frontend component may act as the sensitivity gate.**

- The export service (`export_service.py`) applies the sensitivity threshold
  (default: `public`; configurable via `foundry.yaml -> viewer.sensitivity_threshold`
  or `--sensitivity-threshold`) **before serialization**.
- `quote` and `summary` fields for evidence points above the threshold are
  replaced with `"[redacted:sensitivity]"` in the emitted JSON.
- The claim, its source linkage, and the `sensitivity` label remain — only the
  governed text is dropped.
- Unrecognized sensitivity labels are treated as stricter than any known threshold
  (fail-closed; never leaks).
- A **synthetic sensitivity fixture test** (P1-SENS-001, P4-SENS-001) enforces
  this gate. If the fixture test fails, the export is not shipped.

#### Invariant 2 — Read-Only SPA

> **The SPA is GET-only. It contains no POST, PUT, or DELETE operations, no form
> elements that submit data, and no mutation methods in the API client.**

- The SPA is a viewer, not an editor. The file-first invariant ("the file is the
  source of truth") is enforced architecturally — the SPA has no mechanism to
  write back to the foundry.
- The API client layer (`frontend/runs-viewer/src/api/`) exposes only `GET`
  operations. No `axios.post`, `fetch("...", { method: "POST" })`, or equivalent.
- This prevents the "just add an edit button" scope-creep path (Risk R7) by
  making mutation structurally impossible at the transport layer.

#### Invariant 3 — Path Safety (No Stored Absolute Paths)

> **All run artifact reads in the export service go through `FoundryPaths.discover()`
> (or `RunPaths`). Stored absolute paths from `run_index.yaml` or
> `verification.yaml` are never used for I/O.**

- `run_index.yaml` and `verification.yaml` may embed absolute paths (e.g.
  `run_dir`, `report_path`, `claim_ledger_path`) that reflect the machine and
  user home directory at write time. These break on any workspace move or
  different host (e.g. `agentic-nuc`).
- The export service derives every file path from `workspace_root` + `run_id` via
  `FoundryPaths.discover()`. Stored path fields are used for metadata only.
- A unit test (`P1-PATHS-001`) asserts that no stored field from these files is
  used in an `open()` or `Path.read_*()` call.

#### Invariant 4 — No LLM on the Recall Path

> **The export service (`export_service.py`) is pure file-walk + dict assembly.
> Zero model calls are made during export or during SPA page loads.**

- `rf run export --json` is deterministic: same on-disk inputs -> byte-identical
  JSON output (insertion-ordered, atomic temp-to-move write).
- This is not a performance optimisation — it is a correctness invariant. An LLM
  on the recall path would make claim provenance non-reproducible.
- The SPA makes no LLM calls. It renders the pre-joined, pre-redacted JSON.

---

## Implementation: Loopback API (`VITE_RUNS_FRONTEND_LOOPBACK_API`)

The live loopback REST API (`rf serve`) was implemented in the `runs-loopback-api-v1` feature (Phase P7, June 2026). Design specifications and implementation details:

- **Loopback API specification**: `docs/project_plans/design-specs/runs-loopback-api.md` (promoted to `maturity: promoted`)
- **Auth & LAN specification**: `docs/project_plans/design-specs/runs-auth-lan.md` (promoted to `maturity: promoted`)
- **Implementation plan**: `docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md`
- **Threat model**: See §Threat Model below

The API binds to loopback (`127.0.0.1:7432`) by default with no auth. LAN exposure to `0.0.0.0` is a gated opt-in requiring `--auth-mode token` and a configured shared-secret token (fail-closed bind check). The SPA's fetch client (`frontend/runs-viewer/src/api/client.ts`) is already structured behind the `VITE_RUNS_FRONTEND_LOOPBACK_API` environment flag (set at build time); switching requires only the flag and env-var configuration, not component rewrites.

---

## Threat Model

Applies to the live loopback API path (`rf serve`) introduced in
`runs-loopback-api-v1`.  The static export path has no network surface.

| # | Threat | Attack scenario | Countermeasure | Where enforced |
|---|--------|-----------------|----------------|----------------|
| T1 | **Unauthenticated LAN exposure** | Operator binds `rf serve` to `0.0.0.0` without configuring a token, exposing run data to all hosts on the LAN segment. | Pre-bind validation in `rf serve` exits non-zero *before* any port is opened when `bind_host != loopback` and `auth_mode != "token"`. No socket is created. | `cli_commands.py::serve` — security invariants 1 & 2 |
| T2 | **Token timing attack** | Attacker makes many requests with slightly-varied tokens, measuring response time to guess the correct token byte-by-byte. | Token comparison uses `hmac.compare_digest` exclusively, which runs in constant time regardless of where the strings differ. The `==` operator is never used. | `api/middleware/auth.py::TokenAuthMiddleware.dispatch` |
| T3 | **IP bypass via X-Forwarded-For** | Attacker spoofs the `X-Forwarded-For` header to appear as an allowlisted IP, bypassing the allowlist middleware. | The allowlist reads `request.client.host` (the TCP peer address), which is set by the kernel and cannot be spoofed by the HTTP client. `X-Forwarded-For` is ignored. | `api/middleware/allowlist.py::IPAllowlistMiddleware.dispatch` |
| T4 | **Token leaked through config file** | Token stored in `foundry.yaml` is committed to version control or read by a process with config access, exposing the shared secret. | The token value is stored exclusively in an environment variable named by `viewer.auth_token_env` (default `RF_SERVE_TOKEN`). The `foundry.yaml` key only names the env var — the value is never accepted inline in config. `config.viewer_auth_token_env()` returns the variable *name*, not its value. | `config.py::FoundryConfig.viewer_auth_token_env` — design-level enforcement |
| T5 | **auth_mode=none on 0.0.0.0** | Operator or automation misconfigures `auth_mode: none` in `foundry.yaml` but also sets `bind_host: 0.0.0.0`, creating an open server on the LAN. | Same pre-bind check as T1: `auth_mode != "token"` on a non-loopback host is a hard exit before any port is opened. Config-level `auth_mode: none` + non-loopback `bind_host` is caught the same way as a CLI flag combination. | `cli_commands.py::serve` |

### Security non-goals (out of scope for v1)

- **mTLS** — requires certificate provisioning infrastructure; deferred (DEF-01).
- **SSH-tunnel mode** — token-over-loopback covers the operator threat adequately; deferred (DEF-02).
- **Rate limiting / DDoS protection** — the server is loopback-first and LAN-exposed only by explicit operator opt-in; DOS from the LAN is outside the v1 threat model.

---

## Threat Model

This section documents security considerations for both read paths, especially the loopback API introduced in the June 2026 amendment.

**Loopback-mode threats (127.0.0.1:7432, default):**
- **Threat 1: Unauthenticated LAN access by multiple users on the same machine.** *Countermeasure*: Loopback-only binding prevents non-localhost traffic. The `VITE_RUNS_FRONTEND_LOOPBACK_API` flag is off by default, so the SPA uses static files by default.
- **Threat 2: Token timing attack on Bearer token comparison.** *Countermeasure*: `hmac.compare_digest` is used for all token comparisons (constant-time).
- **Threat 3: Token accidentally committed to config file or source control.** *Countermeasure*: Token lives in an environment variable (`RF_SERVE_TOKEN`) only; `foundry.yaml` never contains the token value.

**LAN-mode threats (0.0.0.0, opt-in with `--bind-host 0.0.0.0`):**
- **Threat 4: Exposure of sensitive run data to untrusted networks.** *Countermeasure*: Bind to `0.0.0.0` requires `--auth-mode token` and a configured token; the server exits non-zero (fail-closed) if the token is missing or the condition is violated.
- **Threat 5: IP address spoofing on a shared network.** *Countermeasure*: Optional IP allowlist (`viewer.allowlist` config key) blocks unlisted IPs with HTTP 403 before auth middleware runs.
- **Threat 6: Unauthorized port scanning discovery.** *Countermeasure*: Port `7432` is documented and non-standard, reducing accidental discovery. The operator chooses whether to expose the API; the default is loopback only.

**Static export path (unchanged from original):**
- No network exposure. File-based read paths validated at export time via `FoundryPaths.discover()`. Sensitivity gate applied at serialization, not at read time.

---

## Consequences

### Static Export Path

**Positive:**
- Zero always-on process; SPA works with `npx serve` or any static HTTP host.
- Sensitivity gate structurally enforced (component cannot leak what export never serialized).
- Determinism and correctness testable without a running server.
- Stable, versioned JSON contract (`schema_version: "1.0"`); fixtures support full SPA testing.

**Negative / Trade-offs:**
- Run data is stale after `rf run` finishes until `rf run export --json` is re-run.
- Export scales linearly with run count. For large corpora (500+ runs), pre-build may take tens of seconds.

### Loopback API Path (v1.1+)

**Positive:**
- Enables "browse as runs land" workflow without manual export steps.
- Live data reflects run updates within per-request latency (no stale export window).
- Loopback-only binding (default) is safe for multi-user machines; no auth required.
- LAN exposure is opt-in and fail-closed; cannot accidentally expose without `--auth-mode token` and a configured token.
- Single-origin `RUNS_FRONTEND_LOOPBACK_API` flag allows toggling between paths without code changes.

**Negative / Trade-offs:**
- Introduces an always-on process and an auth surface (LAN mode).
- Per-request disk reads scale linearly; high run counts (1000+ runs) may show latency. Filesystem-watch hot-reload caching deferred to v2.

### Overall

The dual-mode approach preserves the zero-daemon safety of static export while offering live API access for workflows that benefit from it. The choice is operator-controlled and build-time configurable; neither path is forced on users who prefer file-first simplicity.
