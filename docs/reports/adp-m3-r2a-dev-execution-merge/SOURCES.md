# Source provenance and classification

All snapshots were copied before the proposal was assembled. They are report evidence only.

| Snapshot | Report location | Original source | File count | Hash |
| --- | --- | --- | ---: | --- |
| Hl ledger base | `sources/ledger-base/` | `git archive ee3d9f6 -- .claude/skills/dev-execution` | 56 | `428b0da6e3358b406ee8d2c08f8aa1c6758bf3dde011810e43a6ed5490a9581a` |
| Hd local | `sources/local/` | `.claude/skills/dev-execution/` | 56 | `58fac0bc80c3bf1151d636c7c8e5d1b0fba6808a47f66adbbbc3f3c9d8ccde0d` |
| Hc catalog | `sources/catalog/` | `~/.skillmeat/collections/default/skills/dev-execution/` | 60 | `323e4e6b728ea83f593ee2c7dba089918e7640f65d6f969bc3e098e55077cb73` |
| Proposed merge | `proposal/` | per-path selection below | 60 | `f1af9fd22e3e0ed5f979399129a5040a3b274e51e460edeba6568c40e366e2e2` |

Hashing used SkillMeat's `skillmeat.utils.filesystem.compute_content_hash`: sorted recursive file paths plus file bytes. The matching Hl computation makes `ee3d9f6` a verifiable base, not an inferred approximation.

## Non-identical paths

| Classification against Hl | Proposal selection | Path |
| --- | --- | --- |
| catalog-only | catalog | `CHANGELOG.md` |
| catalog-only | catalog | `SKILL.md` |
| catalog-only | catalog | `git-worktree-pr-protocol.md` |
| catalog-only | catalog | `hooks/itt-claim.sh` |
| local-only | local | `hooks/sdlc-sync.sh` |
| local-only | local | `hooks/tests/test_sdlc_sync.sh` |
| catalog-only | catalog | `hooks/tests/test_validation_scope.sh` |
| catalog-only | catalog | `hooks/validation-scope.sh` |
| catalog-only | catalog | `hooks/validation_scope.py` |
| catalog-only | catalog | `orchestration/workflow-patterns.md` |
| catalog-only | catalog | `references/worktree-isolation-lane.md` |
| catalog-only | catalog | `validation/completion-criteria.md` |

The remaining 48 paths are byte-identical between Hd and Hc. No path was changed by both sides relative to Hl, so this proposal carries zero unmerged text conflicts.
