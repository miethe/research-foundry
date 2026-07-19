# Agent Memory Index

- [Phase 0 Integration Client Foundation](project_integrations_phase0.md) — ARC+IntentTree clients built, Phase 1-3 stubs in place; stdlib urllib only; config in foundry.yaml + .env.example
- [Degrade/Fail-Soft Pattern](feedback_degrade_pattern.md) — available() never raises, HTTP helpers return None on error; gate all live calls on available()
- [Phase 1 IntentTree Outbound Integration](project_integrations_phase1.md) — intenttree writeback target + status callbacks shipped; 33 new tests; 245 passed (up from 210)
- [Phase 3 ARC Council Review Integration](project_integrations_phase3.md) — schema+client+writeback+CLI+adapter+governance shipped; 27 new tests; 300 passed / 9 pre-existing env failures; mypy 15
- [guard_pretool blocks secret-shaped test literals](feedback_guard_pretool_blocks_test_literals.md) — PreToolUse hook secret-scans Write/Edit content itself; split literals via concatenation in secret-scan test fixtures
