---
title: "ADR: Runs Frontend Read Path"
doc_type: adr
status: accepted
schema_version: 1
created: 2026-06-19
updated: 2026-06-19
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

**Accepted** — recorded at P5 (Phase 5 of `runs-frontend-v1`). This decision is
binding for v1 and any patch work until explicitly superseded.

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

**`rf run export --json` is the PRIMARY and sole v1 read path** for the runs
frontend SPA. The SPA is a static single-page application served from
`frontend/runs-viewer/`; it loads pre-built `run.json` files from a static-file
server (or directly from disk in development). No always-on backend is required.

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

## Deferred: Loopback API (`RUNS_FRONTEND_LOOPBACK_API`)

A live loopback REST API (`rf serve --port ...`) is recognized as a natural
follow-on once the static-export cycle proves too slow for the "browse as runs
land" workflow (OQ-6). It is deferred to post-v1 for two reasons:

1. The "browse as runs land" JTBD has not been validated with the operator.
   Static export with a `--all` pre-build step covers the current cadence.
2. A loopback API introduces an auth surface (OQ-4) that is out of scope for a
   loopback-only v1 deployment.

The SPA's fetch client is structured behind a `RUNS_FRONTEND_LOOPBACK_API`
environment flag so that switching to a live API requires only a client-layer
change, not a component rewrite. See
`docs/project_plans/design-specs/runs-loopback-api.md` and
`docs/project_plans/design-specs/runs-auth-lan.md` for the design stubs.

---

## Consequences

**Positive:**
- Zero always-on process required; SPA works with `npx serve` or any static host.
- Sensitivity invariant is structurally enforced (component cannot leak what was
  never serialized).
- Path-safety and determinism are unit-testable without a running server.
- The JSON shape is a stable, versioned contract (`schema_version: "1.0"`); the
  SPA can be developed and tested entirely from fixture files.

**Negative / Trade-offs:**
- Claim data is stale after a run update until `rf run export --json` is re-run.
  The static build step (`rf run export --all` pre-build) is the operator's
  responsibility.
- The pre-build step scales linearly with run count. For large corpora (100+
  runs), this may take tens of seconds. Addressed in the loopback API deferred
  spec.

**Neutral:**
- The loopback API path is not closed — it is actively designed for via the
  `RUNS_FRONTEND_LOOPBACK_API` flag. This ADR records the v1 baseline, not a
  permanent rejection.
