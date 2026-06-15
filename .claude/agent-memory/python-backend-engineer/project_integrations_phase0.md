---
name: project-integrations-phase0
description: Phase 0 integration client foundation for ARC + IntentTree bidirectional integrations — what was built, the design decisions, and what comes next.
metadata:
  type: project
---

Phase 0 of the bidirectional integrations plan is complete. A new `src/research_foundry/integrations/` package provides stdlib-only (urllib) HTTP clients for ARC and IntentTree, following the adapter `available()` degrade pattern exactly.

**Why:** Per `docs/projects/research-foundry/bidirectional-integrations-plan.md` §4, Phase 0 is the client/config/doctor foundation; no writeback/intake/adapter behavior yet.

**How to apply:** When implementing Phase 1 (RF→IntentTree writeback), use `IntentTreeClient.patch_node()` and `IntentTreeClient.add_node_artifact()` stubs in `src/research_foundry/integrations/intenttree.py` — fill these in and call them from `services/writeback.py`. Same pattern for Phase 3 ARC.

Key design decisions:
- NO httpx added as required dep — stdlib urllib only (matches "no new hard dep" requirement)
- Config loader uses lazy import of `FoundryConfig` inside a helper function to avoid circular import (not top-level import)
- `available()` always returns bool, never raises — same degrade contract as adapters
- `rf doctor` row is informational only: offline is "unreachable" not an error, exit code always 0
- `foundry.yaml` now has `integrations.arc.base_url` and `integrations.intenttree.base_url` keys
- `.env.example` now has `ARC_BASE_URL`, `INTENTTREE_BASE_URL`, `INTENTTREE_API_TOKEN`
