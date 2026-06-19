# `meatywiki` Skill

This is the agent-facing skill for driving the [MeatyWiki](https://github.com/miethe/meatywiki) CLI. It has two postures:

1. **Driver** — invoke `meatywiki` CLI commands against a project that already has a vault. This is 99% of use.
2. **Bootstrap** — one-shot setup of MeatyWiki in a fresh project (vault init, CLAUDE.md sidecar, project intent stub). Run once per project.

Agents read `SKILL.md` (entry point) and progressively disclose `references/` and `bootstrap/` files as needed. Humans should read this file.

## Skill Layout

```
.claude/skills/meatywiki/
├── README.md                          ← this file (humans)
├── SKILL.md                           ← agent entry (≤ 500 lines)
├── SPEC.md                            ← skill contract, coverage matrix
├── references/                        ← driver-posture progressive disclosure
│   ├── command-reference.md           ← full CLI flag tables
│   ├── workflow-patterns.md           ← multi-step recipes
│   ├── vault-layout.md
│   ├── artifact-taxonomy.md
│   ├── hook-policy.md                 ← SAM/CCDash deferral
│   └── troubleshooting.md             ← compile failures, index drift
├── bootstrap/                         ← bootstrap-posture progressive disclosure
│   ├── README.md                      ← bootstrap entry
│   ├── plan.md                        ← B1–B5 orchestration steps
│   ├── sidecar-template.md            ← .claude/context/meatywiki.md content
│   ├── wiki-spec-template.md          ← <vault>/wiki-spec.md content
│   └── troubleshooting.md             ← partial state, drift, re-bootstrap
└── scripts/                           ← (empty by design; OQ-1 deferred)
```

## Bootstrap Quickstart

When you start using MeatyWiki on a new project, say one of:

- "bootstrap meatywiki here"
- "set up meatywiki for this project"
- "wire meatywiki into this repo"

The agent will:

1. Detect existing state (is there a vault? a sidecar? a CLAUDE.md reference? a `wiki-spec.md`?)
2. Run `meatywiki init <path>` if no vault exists
3. Write `.claude/context/meatywiki.md` (a sidecar that tells future agents how/when to use MeatyWiki for this project)
4. Propose a small managed block in your root `CLAUDE.md` — you confirm the diff before it's applied
5. Generate `<vault>/wiki-spec.md` capturing the project's knowledge intent

All steps are idempotent. Run bootstrap again any time without fear of duplicate state.

**What bootstrap does NOT do:**

- Does not install the skill globally (it assumes the skill is already discoverable)
- Does not touch parent directories, sibling repos, or global Claude config
- Does not invent ingest sources or success criteria — you fill those into `wiki-spec.md` over time
- Does not overwrite a non-empty `wiki-spec.md` or existing managed-block content without your explicit consent

See `bootstrap/README.md` for the full when/why/how, and `SPEC.md` §13 for the durable contract.

## Day-to-Day Usage

After bootstrap, drive MeatyWiki via natural-language prompts to your agent. The skill's `SKILL.md` decision tree maps tasks to commands; common patterns:

```bash
# Add a source
meatywiki --vault <path> ingest https://example.com/article

# Process the inbox (raw/ → wiki/)
meatywiki --vault <path> compile --pending

# Ask a question with citations
meatywiki --vault <path> query "what are the lens priorities for this vault?"

# Health check
meatywiki --vault <path> doctor
```

The agent translates your intent into these commands. You only need to know the command surface for direct CLI use.

## Pattern Reusability

The bootstrap pattern in this skill — minimal SKILL.md mention + `bootstrap/` progressive disclosure + sidecar at `.claude/context/<skill>.md` + diff-confirmed managed CLAUDE.md block + project-spec stub — is generic enough to reuse for other CLI-driver skills:

- `notebooklm-cli` — could bootstrap a project's notebook directory, sidecar pointing to the notebook ID + audio source policy
- `demo-forge` — could bootstrap a demo manifest + storyboard directory + sidecar with the demo-forge command map

Each skill owns its own marker namespace (e.g., `<!-- notebooklm:start -->`) and its own sidecar path. The bootstraps coexist without conflict. See `SPEC.md` §13.6.

## Updating

- New CLI commands or flags → see `SPEC.md` §6 Update / Enhancement Protocol
- New bootstrap step or template change → see `SPEC.md` §13.5 Update Protocol for Bootstrap Surface
- Skill version bumps → `SKILL.md` frontmatter `skill_version` (semver: bootstrap-contract breaking = major, additive = minor, patch = patch)

## Contact / Issues

The skill source lives in `.claude/skills/meatywiki/` of the [meatywiki repo](https://github.com/miethe/meatywiki). File issues or PRs against that path.
