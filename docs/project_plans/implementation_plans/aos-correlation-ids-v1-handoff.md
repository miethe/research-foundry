---
schema_version: 1
status: handoff-ready
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
