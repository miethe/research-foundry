---
name: meatywiki-bootstrap-troubleshooting
description: Recovery procedures for partial bootstrap state, sidecar drift across skill versions, CLAUDE.md conflicts, and re-bootstrap scenarios.
type: progressive-disclosure
skill_name: meatywiki
schema_version: 1
cli_version_range: "compilation-engine-v1 – v1.2 (pre-release)"
---

# Bootstrap Troubleshooting

Load this only when bootstrap hits a non-trivial state. Routine idempotent re-runs do not need this file.

## Init Failures

### Symptom: `meatywiki init <path>` exits non-zero

| Cause | Detection | Fix |
|---|---|---|
| Path exists and is a non-empty directory that's not a MeatyWiki vault | `ls <path>` shows unrelated files | Choose a different path, or empty the directory first (with user consent) |
| Path is a MeatyWiki vault with corrupted `_meta/` | `meatywiki --vault <path> doctor` reports drift | Run `meatywiki --vault <path> index --reset`; rerun `doctor` |
| Permission denied | Filesystem error in init output | Reroot the vault under a writable path |
| `meatywiki` CLI not on `$PATH` | `which meatywiki` empty | `uv sync` in the meatywiki repo, or install globally per repo README |

### Symptom: Init succeeds but `doctor` fails immediately

Almost always a config error in `_meta/config.yaml`. Inspect the file; common issues:

- Missing required `llm.providers` block
- Provider declared but `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` env var unset
- `vault_root` path mismatch between config and actual location

Fix the config, rerun `doctor`. Do not proceed to B3 until doctor is green.

---

## Sidecar Drift

### Symptom: Existing `.claude/context/meatywiki.md` does not match current template hash

This happens when:

- The `meatywiki` skill was upgraded since last bootstrap (new fields, reordered sections, new guardrails)
- The user hand-edited the sidecar **above** the "Edit by hand only" line
- Another tool wrote a sidecar with the same name

**Resolution flow:**

1. Compute diff between current file and freshly-substituted template.
2. Categorize diff hunks:
   - **Above the HR line** (managed content) — candidate for overwrite
   - **Below the HR line** (user content) — preserve verbatim
3. Show the user the managed-content diff only. Ask: accept upgrade / keep existing / abort.
4. On accept: write new template body, then re-append preserved user content below the HR.
5. On keep: do nothing, log the version mismatch in the bootstrap summary.

If user content has accidentally been written above the HR line, point this out and offer to move it below.

---

## CLAUDE.md Conflicts

### Symptom: Existing `<!-- meatywiki:start -->` block content differs from canonical

Same flow as sidecar drift: diff, categorize, ask. The canonical block is small (≤6 lines), so accepting an upgrade is low-risk.

### Symptom: Another tool owns a managed block in root CLAUDE.md

Example: a `notebooklm-cli` or `demo-forge` skill bootstrap has added its own block.

**Do not merge.** Each skill owns its own fenced block. Append MeatyWiki's block at the end of `CLAUDE.md`, after any existing managed blocks. Order does not matter.

### Symptom: User declined CLAUDE.md update in B4

Bootstrap is **partial**. The sidecar exists but is not auto-loaded by future agents. Two acceptable resolutions:

- Accept the partial state; agents must be told to load `.claude/context/meatywiki.md` manually each session.
- Recommend the user invoke bootstrap again later and accept B4 then.

Record the partial state in the bootstrap summary so future you / future agent knows.

---

## `wiki-spec.md` Conflicts

### Symptom: `wiki-spec.md` exists and has substantive content

Never overwrite. Offer the user three paths:

1. **Diff merge** — show the user template sections missing from their existing spec; they hand-fold.
2. **Rename + write fresh** — back up existing as `wiki-spec.old.md`, write fresh template. **Only with explicit consent.**
3. **Skip** — do nothing; B5 is no-op.

Default: option 1 (diff merge).

### Symptom: `wiki-spec.md` exists but is empty / placeholder-only

Treat as "not really there" — overwrite is safe. Confirm with the user once, then proceed.

---

## Re-Bootstrap (Skill Version Upgrade)

When the `meatywiki` skill version bumps and a project was bootstrapped on an earlier version:

1. The sidecar's `meatywiki_skill_version` field in frontmatter is the version pin.
2. Compare to the current skill's `skill_version` in `SKILL.md` frontmatter.
3. If equal → no re-bootstrap needed.
4. If different → run bootstrap again. Steps B1, B2, B5 will be no-ops (state detection skips). B3 enters sidecar drift flow. B4 may or may not need updating depending on whether the canonical block changed.

The skill's `SPEC.md` §13 records breaking changes to the sidecar/CLAUDE.md contract. Check that section for forced-update rules.

---

## Partial-State Recovery

You can land in partial state if:

- The user Ctrl-C'd midway
- A step failed and bootstrap aborted before all five completed
- B3 succeeded but B4 was declined

**Recovery is just re-running bootstrap.** Every step's idempotency check will detect what's done and skip it. The summary report at the end will list what's now present vs. still missing.

If state is so corrupted that step detection itself is unreliable, the nuclear option is:

```bash
# DESTRUCTIVE — requires explicit user consent
rm <project_root>/.claude/context/meatywiki.md
# manually remove the <!-- meatywiki:start --> ... <!-- meatywiki:end --> block from CLAUDE.md
rm <vault>/wiki-spec.md  # only if user agrees their intent doc is salvageable from elsewhere
# leave _meta/ alone — never delete a real vault
```

Then re-run bootstrap from scratch. **Never delete `_meta/` to "reset" the vault** — that destroys the index but not the files, and the next compile will rebuild the index anyway. If the user genuinely wants a fresh vault, that's a separate destructive operation requiring explicit consent and is **out of scope for bootstrap**.

---

## Cross-Skill Interactions

If the project will also bootstrap `notebooklm-cli` or `demo-forge` (assuming they adopt this same pattern):

- Each skill's sidecar lives at its own path: `.claude/context/<skill-name>.md`
- Each skill's CLAUDE.md block uses its own marker: `<!-- <skill-name>:start --> ... <!-- <skill-name>:end -->`
- Order in CLAUDE.md does not matter
- Sidecars do not depend on each other; agents load whichever are referenced

No cross-skill coordination is needed during bootstrap. If multiple skills want to coexist in `<vault>/wiki-spec.md` (which is MeatyWiki-specific), the answer is: they don't. `wiki-spec.md` is MeatyWiki's; other skills get their own project-spec files at paths they define.
