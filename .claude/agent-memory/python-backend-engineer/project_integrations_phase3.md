---
name: project-integrations-phase3
description: Phase 3 RF-ARC council review integration shipped — schema, writeback target, CLI option, adapter, governance rule; 300 passed / 9 pre-existing failures
metadata:
  type: project
---

Phase 3 ARC review integration complete. Key deliverables:

1. `schemas/arc_review_request.schema.yaml` — review packet schema (status enum: proposed/submitted/approved/concern/block; verdict enum: approve/concern/block/null)
2. `integrations/arc.py` — `scaffold_review(payload)` → POST /api/runs; `get_run(arc_run_id)` → GET /api/runs/{id}; both fail-soft returning None
3. `services/writeback.py` — `_render_arc_council()` always writes candidate; online path maps approve→0, concern/block→7; `arc` wired into `writeback()` dispatch; `WritebackResult.arc_review_path` added
4. `paths.py` — `RunPaths.arc_review_request` property
5. `cli_commands.py` — `rf council --via arc/--local` option; `_arc_council_via()` / `_local_council_fallback()` helpers; `--targets` help updated to include arc
6. `adapters/arc_council.py` — ARCCouncilAdapter: available() gates on ArcClient.available(); real mode submits and reads verdict; degraded returns stub; registered in _CONCRETE
7. `config/governance.yaml` — `arc_writeback_requires_review` rule + arc target permissions
8. `services/governance.py` — rule 5c fires arc_writeback_requires_review for work_sensitive/client_sensitive + arc target
9. `tests/test_arc_integration.py` — 27 new tests; `tests/test_integrations.py` updated to Phase 3 signatures

**Why:** ARC is the council-review sibling; RF needed to hand it evidence bundles and get verdicts back. offline-first design: candidate always written, live push conditional on available()+requires_review.

**How to apply:** Follow the `_render_intenttree_update` gating pattern exactly: check `not requires_review and profile not in _offline_profiles` before any live call; swallow all exceptions with bare `except Exception`.

Test counts: 300 passed, 9 pre-existing env failures (adapters env + governance adversarial CLI script tests). mypy: 15 errors (baseline, no increase).
