# research-foundry `.claude/` survey — gitignore-deployed-artifacts milestone

- **Date:** 2026-09-03
- **Method:** read-only Codex leg (`gpt-5.6`, report `research-foundry/.claude/reports/legs/20260903T164753Z-72906-codex.report.jsonl`), survey of `research-foundry/.claude/` against the SkillMeat deployment ledger and `.gitignore`.
- **"Unregistered" means:** a leaf file under `.claude/{skills,agents,commands,rules,workflows,hooks}` that carries no corresponding entry in the SkillMeat deployment ledger — i.e. it is not one of the artifacts SkillMeat currently tracks as deployed, per `.claude/rules/artifact-registration.md` in `agentic_meta_dev` (every artifact deployment should happen via SkillMeat, recorded and hash-verified, never a bare copy).

---

Report path was not writable; read-only verified report follows.

**Ledger: 12 deployed; all hashes present**

| artifact/type/path | tracked | symlink | HEAD | hash |
|---|---:|---|---|---|
| planning/skill/skills/planning | Y | — | clean | N/A-dir |
| dev-execution/skill/skills/dev-execution | Y | — | clean | N/A-dir |
| a11y-sheriff/agent/agents/a11y-sheriff.md | N | — | untracked | match |
| backend-architect | N | — | untracked | match |
| changelog-generator | N | — | untracked | match |
| data-layer-expert | N | — | untracked | match |
| documentation-expert | N | — | untracked | match |
| documentation-writer | N | — | untracked | match |
| feature-sprint-executor | N | — | untracked | match |
| frontend-developer | N | — | untracked | match |
| search-specialist | N | — | untracked | match |
| task-completion-validator | N | — | untracked | match |

The final ten rows are `agent` paths under `agents/`; SHA-256 matches each ledger hash. Directory entries have no single-file SHA comparison. Symlinks found: **0**.

Unregistered leaf files: **664** = **647 tracked, 17 untracked, 0 symlink**.

| area | total / tracked / untracked |
|---|---:|
| skills | 480 / 473 / 7 |
| agents | 91 / 81 / 10 |
| commands | 64 / 64 / 0 |
| rules | 7 / 7 / 0 |
| workflows | 12 / 12 / 0 |
| hooks | 10 / 10 / 0 |

Current `.gitignore` `.claude` lines: `.claude/agent-memory/`, `.claude/skills/symbols/ai/`, `.claude/worktrees/`.

Project-authored, tracked: `.claude/settings.json`, `.claude/aos-artifacts.yaml`, `.claude/rules/`.

```gitignore
# SkillMeat-managed deployments
/.claude/skills/
/.claude/agents/
/.claude/commands/
/.claude/workflows/
/.claude/hooks/
```

Order: register unregistered → deploy SkillMeat → verify hashes → `git rm --cached` only → add block → replace any future symlinks with deployments.

Flags: 12 unregistered `.skillmeat-lock` files need ownership classification; ledger has an existing uncommitted 140-line addition (10 agents). Preserve it.
