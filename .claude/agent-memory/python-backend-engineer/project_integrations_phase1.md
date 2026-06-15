---
name: project-integrations-phase1
description: Phase 1 IntentTree outbound integration shipped — writeback target, status callbacks, governance, schema
metadata:
  type: project
---

Phase 1 RF→IntentTree outbound integration shipped 2026-06-13.

**Why:** Design §3.2/§3.5 in docs/projects/research-foundry/bidirectional-integrations-plan.md; highest-value, lowest-risk integration.

**What was built:**
- `schemas/intenttree_update.schema.yaml` — candidate schema (node_id, evidence_bundle_id, status, claims_total, claims_supported, verification_passed, reusable_output_candidates, artifact_links, blocked_by, push_status)
- `paths.py` — `RunPaths.intenttree_update` property → `writebacks/intenttree_update.yaml`
- `integrations/intenttree.py` — real `patch_node` (PATCH `/api/nodes/{node_id}`) and `add_node_artifact` (POST `/api/nodes/{node_id}/artifacts`); get_node still Phase 2 stub
- `services/writeback.py` — `_render_intenttree_update()` (always-write + conditional live push), `WritebackResult.intenttree_update_path`, dispatch in `writeback()` when "intenttree" in targets
- `services/telemetry.py` — `push_status(run_id, stage, *, paths)` — fires only at 4 milestone stages; best-effort, never raises
- `services/governance.py` — `intenttree_writeback_requires_review` rule (work/client-sensitive → require_approval)
- `config/governance.yaml` — new rule + `writeback_targets.intenttree` block (permitted: personal, work_approved, client_approved; NOT offline_only)
- `cli_commands.py` — `rf writeback --targets` updated to include intenttree; `rf status push --run X --to intenttree --stage Y` subcommand
- `tests/test_intenttree_writeback.py` — 33 new tests (schema validity, dispatch, online path, offline path, requires_review gate, governance tiers, push_status, CLI)
- `tests/test_schema_validation.py` — added intenttree_update to EXPECTED_SCHEMA_NAMES (now 18 schemas)

**How to apply:** When implementing Phase 2 (IntentTree→RF inbound), the `IntentTreeClient.get_node()` stub needs implementation. The `_render_intenttree_update` pattern in writeback.py is the template for all future integration targets.

Test baseline: 210 passed → 245 passed, 9 pre-existing failures unchanged.

Links: [[project-integrations-phase0]] [[feedback-degrade-pattern]]
