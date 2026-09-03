# dev-execution three-way merge proposal

Status: proposal only. This directory is not a SkillMeat catalog update or deployment.

## Inputs and verification

| Role | Snapshot directory | Verified content hash |
| --- | --- | --- |
| Ledger base (Hl) | `sources/ledger-base/` | `428b0da6e3358b406ee8d2c08f8aa1c6758bf3dde011810e43a6ed5490a9581a` |
| Project-local (Hd) | `sources/local/` | `58fac0bc80c3bf1151d636c7c8e5d1b0fba6808a47f66adbbbc3f3c9d8ccde0d` |
| Catalog (Hc) | `sources/catalog/` | `323e4e6b728ea83f593ee2c7dba089918e7640f65d6f969bc3e098e55077cb73` |

The ledger hash is not merely a pointer: `git archive ee3d9f6 -- .claude/skills/dev-execution`, hashed by SkillMeat's `compute_content_hash`, produced Hl exactly. The base snapshot here is that exact archive. Hc was similarly verified from `~/.skillmeat/collections/default/skills/dev-execution`; Hd was verified from `.claude/skills/dev-execution`.

## Proposed result

`proposal/` is the complete, 60-file proposed skill. The three input snapshots remain separately inspectable under `sources/`; no input has been modified.

The merge has no overlapping text conflicts because every non-identical path changed on exactly one side relative to Hl:

| Decision | Count | Paths |
| --- | ---: | --- |
| Take catalog-only change | 10 | `CHANGELOG.md`, `SKILL.md`, `git-worktree-pr-protocol.md`, `hooks/itt-claim.sh`, `hooks/tests/test_validation_scope.sh`, `hooks/validation-scope.sh`, `hooks/validation_scope.py`, `orchestration/workflow-patterns.md`, `references/worktree-isolation-lane.md`, `validation/completion-criteria.md` |
| Keep local-only change | 2 | `hooks/sdlc-sync.sh`, `hooks/tests/test_sdlc_sync.sh` |
| Unchanged / identical current content | 48 | all remaining proposal paths |
| Text conflicts requiring a human resolution | 0 | none |

This is a merge proposal, not permission to deploy or capture it. A later owner must review the 12 selected paths, choose a catalog versioning action, then run the documented enterprise deployment flow separately. The standing hold on `delegation-router` is unrelated and remains untouched.

## Reproduction / validation evidence

The selection rule is the conventional three-way rule per file: equal current sides stay equal; where one side equals Hl, take the other side; only dual divergence would require a text merge. Counts at generation: base 56 files, local 56, catalog 60, proposal 60; union 60; selected changes 12; conflicts 0.

`SOURCES.md` records source paths, Git revision, hashing mechanism, and the complete path-level classification.
