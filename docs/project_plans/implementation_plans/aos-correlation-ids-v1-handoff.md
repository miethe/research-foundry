---
schema_version: 1
status: completed
updated: 2026-07-06
source_plan: /Users/miethe/dev/homelab/development/agentic_meta_dev/.claude/plans/aos-universal-correlation-ids-v1.md
contract: /Users/miethe/dev/homelab/development/agentic_meta_dev/docs/agentic-operator/contracts/aos-correlation.md
---

# AOS Correlation IDs v1 - Research Foundry Handoff

## Goal

Carry AOS run/session/artifact metadata through Research Foundry run artifacts and runs-viewer
exports when RF is launched by the Operator.

## Required Work

- Add optional envelope fields to run metadata: `aos_run_uuid`, `aos_session_uuid`,
  `aos_feature_uuid`, `aos_artifact_uuid`, and `aos_trace_uuid`.
- Preserve native RF run IDs as aliases.
- Update runs-viewer/export surfaces to display or expose resolver links where appropriate.
- Avoid storing prompt/response bodies in correlation sidecars.

## Acceptance

- Existing RF runs with no AOS fields load unchanged.
- Operator-launched RF outputs carry enough metadata to resolve back to the parent AOS run/session.
- Runs-viewer handles unknown or missing UUIDs as unresolved, not as load failures.

## Validation

Add a run.json fixture with AOS metadata and run the normal RF viewer/backend validation for that
fixture.

## Completion Evidence

Implemented in Research Foundry schema/export version 1.4.

- `rf run export` now emits nullable `aos_run_uuid`, `aos_session_uuid`,
  `aos_feature_uuid`, `aos_artifact_uuid`, `aos_trace_uuid`, and
  `native_aliases.rf_run_id`.
- Native RF `run_id` remains canonical; `native_aliases.rf_run_id` preserves the RF alias for
  resolver surfaces.
- AOS UUID inputs are accepted only as valid UUID strings and are exported in canonical
  hyphenated form. Missing, unknown, unresolved, invalid, or nested values export as `null`.
- The runs-viewer metadata panel renders AOS UUIDs and native aliases when present and treats
  missing or unknown UUIDs as not available.
- Added `frontend/runs-viewer/src/test/fixtures/aos-run.json` as a schema 1.4 AOS fixture.
- Added regression coverage for non-AOS runs, correlation-block fallback, malformed/nested values,
  UUID canonicalization, and viewer unknown-value handling.

Validation:

- `./.venv/bin/python -m pytest tests/unit/test_export_service.py tests/integration/test_export_round_trip.py`
- `./.venv/bin/python -m ruff check src/research_foundry/services/export_service.py tests/unit/test_export_service.py tests/integration/test_export_round_trip.py`
- `PATH="/Users/miethe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" ./node_modules/.bin/vitest run src/test/p8-smoke.test.tsx`
- `PATH="/Users/miethe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" ./node_modules/.bin/tsc -p tsconfig.app.json --noEmit`
- `git diff --check`
- Delegated reviewer pass: PASS.
