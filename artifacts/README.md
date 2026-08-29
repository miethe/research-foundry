# `artifacts/` — canonical artifact sources

This directory is the **canonical source root** for artifacts this repository owns.
It is declared to SkillMeat in `.skillmeat/config.toml`:

```toml
[artifacts]
canonical_roots = ["artifacts"]
```

Layout: `artifacts/<types>/<name>` — plural container names.

| | `artifacts/**` | `.claude/**` |
|---|---|---|
| Role | **canonical source** — the file a human edits | **deployed runtime copy** |
| Produced by | hand-authored, code-reviewed | `skillmeat deploy` only |
| Git | tracked | tracked today; gitignored from ADP-M3 R2 |
| Symlinks | n/a | forbidden — a symlink is an *unrecorded* deployment |

## Editing an artifact

Edit the file under `artifacts/`. **Never** edit the copy under `.claude/` — it is
overwritten by the next deploy, and the change is invisible to the deployment ledger.

Propagation is three steps, and step 3 is not optional:

```bash
# 1. RE-REGISTER — publish the edited canonical into the enterprise catalog
skillmeat enterprise add artifacts/skills/<name> --type skill

# 2. DEPLOY — skillmeat deploy reads the ENTERPRISE store, not your working tree
skillmeat deploy <name> --type skill --project "$PWD"

# 3. VERIFY AT THE DESTINATION — by content, never by exit code
diff -r artifacts/skills/<name> .claude/skills/<name>
```

Skipping step 1 deploys the *previous* enterprise content over your edit. Skipping
step 3 means you have a green exit code and no evidence.

## Why plural container names

`skillmeat/core/artifact_detection.py` accepts both spellings for skill, command,
agent, hook, and workflow — but `RULE_FILE` accepts only `rules`. Plural is the only
spelling uniformly discoverable across every artifact type, so the whole tree uses it.

The type subdirectory is **implied, not declared**: a canonical root is a peer of
`.claude/`, and the scanner applies its own container vocabulary underneath. Only the
root is named in config.

## Provenance

Established by the artifact-deployment-program campaign, milestone M3, phase R1
(`research-foundry-v1.md`). Layout authorized by HR-1: "Standard root
`<repo>/artifacts/<type>/<name>` everywhere; staged moves authorized."

Migration is **staged** — this root currently holds the R1 canary. Remaining
repo-owned artifacts move in later passes; until then their canonical source is
still their `.claude/` path.
