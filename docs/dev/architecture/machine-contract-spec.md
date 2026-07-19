---
title: "Research Foundry — Machine Contract Spec"
description: "States explicitly what part of rf's output automation may depend on: the ExitCode enum + JSON/YAML output IS the stable, versioned machine contract; Rich console text is presentation-only and MUST NOT be parsed."
audience: [ai-agents, developers]
created: 2026-07-18
status: draft
category: architecture
doc_type: architecture
prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
related_documents:
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/dev/architecture/machine-surface-inventory.md
  - docs/dev/architecture/rf-run-export-schema.md
---

# Research Foundry — Machine Contract Spec

## Purpose

This doc is the FR-4.2 deliverable (`docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md:268`,
AC-RFUP4-2): it states, explicitly and normatively, **what part of `rf`'s output is a contract
automation may rely on, and what part is not**. It answers a question that was previously implicit
in code comments and CLI help text scattered across `cli_commands.py`: *"if I write a script that
shells out to `rf`, what can I safely parse?"*

This doc does not duplicate the full per-surface stamping inventory — see
`docs/dev/architecture/machine-surface-inventory.md` for the enumerated list of 7 target surfaces,
their current stamped state, and which implementation-plan task stamps each one.

## The contract, stated explicitly

**The stable, versioned machine contract is:**

1. The process **exit code**, drawn from the `ExitCode` enum (`src/research_foundry/errors.py`).
2. The **JSON or YAML output** emitted when a command is invoked in its machine-readable mode
   (`--json` on CLI commands, the YAML/JSON produced by `rf verify`, the runs-viewer run-export
   document, and the LAN API JSON payloads under `/api/runs`, `/api/reports`, `/api/catalog`).

**Everything else — in particular Rich console text (tables, panels, colored status lines, human
progress output) — is presentation-only.** It is not part of the contract, is not versioned, and
carries no compatibility guarantee.

## 1. Exit codes are the process-exit-code contract

`ExitCode` (`src/research_foundry/errors.py`) is an `IntEnum` with eight stable values:

| Value | Name | Meaning |
|---|---|---|
| 0 | `OK` | Success. |
| 1 | `USAGE` | Usage error (bad arguments, missing/unknown artifact — see `NotFoundError`). |
| 2 | `SCHEMA` | Schema validation failed (`SchemaError`). |
| 3 | `GOVERNANCE` | A governance policy rule with severity `block` fired (`GovernanceError`). |
| 4 | `UNSUPPORTED` | A material claim could not be supported by evidence (`UnsupportedClaimError`). |
| 5 | `BUDGET` | A budget guard was exceeded (`BudgetError`). |
| 6 | `ADAPTER` | An adapter or external tool call failed (`AdapterError`). |
| 7 | `HUMAN_REVIEW` | The operation requires human review before proceeding (`HumanReviewRequired`). |

Every `RFError` subclass carries an `exit_code: ExitCode` class attribute, and the CLI entry point
translates any raised `RFError` into the corresponding process exit status. **Automation (CI,
`rf-run-execute.js`-style workflows, the execution loop) should branch on the numeric exit code**,
not on stderr/stdout text, to determine which failure class occurred. This mapping is itself part
of the stable contract: the meaning of exit code `3` will always be "governance blocked," never
repurposed for a different failure class in a later release. New failure classes get new enum
values appended; existing values are never renumbered or reassigned.

## 2. JSON/YAML output is the stable, versioned payload contract

Where a command supports a machine-readable output mode — `--json` on CLI subcommands, `rf verify`'s
YAML/JSON report, the runs-viewer run-export document, and the LAN API's JSON responses — **that
output's field names and structure are the contract**, not the Rich-rendered human view of the same
data. From RFUP-4 (Phase 1) forward, every one of these surfaces stamps a top-level
`rf_schema_version` field (see §3) so consumers can detect drift instead of guessing at shape from
field presence.

Concretely, this means:

- A script that runs `rf run status <run_id> --json` and reads `result["status"]` is depending on
  the contract and is supported.
- A script that runs `rf run status <run_id>` (Rich table output, no `--json`) and greps the
  colored table text for a status string is **not** depending on the contract, is unsupported, and
  may break on any release — including patch releases — without notice.
- The runs-viewer's static export consumer reads the JSON run-export document
  (`docs/dev/architecture/rf-run-export-schema.md`), never scrapes any CLI console output.

## 3. `rf_schema_version` versions the contract going forward

`RF_SCHEMA_VERSION` (`src/research_foundry/__init__.py`, currently `"1.0.0"`) is the canonical
semver string stamped as a top-level `rf_schema_version` field on every machine-readable `rf`
surface enumerated in `docs/dev/architecture/machine-surface-inventory.md`. It is the versioning
mechanism for the JSON/YAML half of this contract:

- **Additive changes** (new optional field, new enum value appended) do not require a version bump.
  Consumers should use `.get()` or optional field syntax to handle absent fields gracefully.
  Example additive fields (Phases 2–4) that arrived at schema v1.0.0 without a bump: `exact_passage_violations` (verify output), `extraction_status` (source cards), `--seal` lineage records (run export).
- **Breaking changes** (a field renamed or removed, a field's type or meaning changed, an exit code
  repurposed) require a `rf_schema_version` major bump and a corresponding entry in the contract
  drift test suite (AC-RFUP4-3, TASK-1.4).
- Consumers that read a payload with an absent `rf_schema_version` (pre-feature `rf`, or a surface
  not yet migrated) should treat it as an implicit "unversioned/legacy" contract rather than raising
  an unhandled exception (AC-RFUP4-5).

`RF_SCHEMA_VERSION` is distinct from two other, narrower version constants that must not be
conflated with it: the unused legacy `SCHEMA_VERSION` package constant, and
`EXPORT_SCHEMA_VERSION` in `services/export_service.py` (currently `"1.5"`), which versions only the
runs-viewer run-export document schema independently of the broader machine contract.

## Non-goal: Rich console formatting is not covered by this contract

Explicitly out of scope, and never a breaking change under this contract:

- Rewording, recoloring, reformatting, or restructuring any Rich console table, panel, or progress
  display.
- Adding, removing, or reordering columns in a human-facing table.
- Changing log/status message text printed to stdout/stderr outside of `--json`/YAML/API payloads.

None of the above require a `rf_schema_version` bump, a changelog entry under "breaking changes," or
advance notice to consumers, because none of it is part of the machine contract. Automation and
scripts **MUST NOT** parse Rich console text output — doing so is unsupported and any resulting
breakage is not a regression against this contract.

## Summary

| Surface | Contract status |
|---|---|
| Process exit code (`ExitCode` enum) | Stable, versioned via enum semantics (values never reassigned) |
| CLI `--json`, `rf verify` YAML/JSON, run-export JSON, LAN API JSON | Stable, versioned via `rf_schema_version` |
| Rich console text (tables, panels, colored output, human progress) | Presentation-only, unversioned, not a contract — MUST NOT be parsed |

See `docs/dev/architecture/machine-surface-inventory.md` for the full per-surface stamping
inventory and which implementation-plan task stamps each one.
