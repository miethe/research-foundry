# ADP-M3 / R1 — Canonical/deployed split (research-foundry)

> Campaign: artifact-deployment-program (spine in `agentic_meta_dev`)
> Child plan: `campaigns/artifact-deployment-program/children/research-foundry-v1.md`, phase R1
> IntentTree key: `m3-research-foundry-split` — `node_01M0DY03YQ3BBGRQNJRTKARXJ0`
> Branch: `worktree-adp-m3-r1-canonical-split` · Status: **partial — artifact-scoped acceptance met, two campaign-level blockers open**

## Entry gate

`m2-drift-gate` (`node_01M0DXZYQR9BPFDKCTQJFHXF5J`), asserted verbatim:

```
itt --json node get "$M2_NODE_ID" --include completion_evidence \
  | jq -e '.status == "completed" and (.completion_evidence | length > 0)'
```

Result: `true`, exit `0`.

## What landed

| Change | Path |
|---|---|
| Canonical source root | `artifacts/` |
| Root declared to SkillMeat | `.skillmeat/config.toml` → `[artifacts].canonical_roots = ["artifacts"]` |
| R1 canary moved | `.claude/skills/research-foundry/` → `artifacts/skills/research-foundry/` |
| Edit-point contract | `artifacts/README.md` |
| Config tracked, identity not | `.gitignore` — un-ignore `.skillmeat/config.toml` only |

Two decisions worth recording, because both were live disagreements:

**Plural container names** (`artifacts/skills/`, not `artifacts/skill/`). HR-1's wording
`<repo>/artifacts/<type>/<name>` uses `<type>` as a placeholder, so it does not settle the
spelling. `skillmeat/core/artifact_detection.py` does: `CONTAINER_ALIASES` accepts both
spellings for skill, command, agent, hook and workflow, but `RULE_FILE = {"rules"}` accepts
only the plural. Plural is therefore the only spelling uniformly discoverable across every
artifact type. (Cross-checked with the `skillmeat` session, which owns that code and issued
the correction.)

**The type subdirectory is implied, not declared.** A canonical root is a peer of `.claude/`,
and the scanner applies its own container vocabulary underneath, so only `artifacts` is named
in config. `canonical_roots` is live in the installed build — `skillmeat --version` reports
`0.81.0 (editable 6e0e9f11 on development)`, and the feature landed on `development` in
`ed21d4d40`; it is absent from `main`/v0.81.0, so a main-based install would make this config
inert. Verified before writing it, not assumed.

## Acceptance

**Artifact-scoped predicates — all pass.**

| Predicate | Result |
|---|---|
| `git ls-files --error-unmatch artifacts/skills/research-foundry/SKILL.md` | PASS |
| `test -e .claude/skills/research-foundry` | PASS |
| `test ! -L .claude/skills/research-foundry` | PASS |
| `diff -qr artifacts/skills/research-foundry .claude/skills/research-foundry` | PASS (no output) |

Reconcile's own view of the canary corroborates it: absent from both `drift[]` and `gaps[]`,
with `h_c == h_d == 7d6895d8c738765da48cc3a0f55264254bdcb66cc921d4ef9cf2ce508b248e30`.

`.claude/skills/research-foundry/` is deliberately left in place and tracked. Under the target
doctrine it is now the *deployed runtime copy*, not the canonical source; gitignoring deployed
copies is R2's job.

**Repo-wide predicate and deploy receipt — blocked.** See below.

## Blockers

Both are campaign-level and both look cross-repo. Filed as
`req_01M16X6GDE5DW62VSTMXYPH7BA` (blocker, requires approval).

### 1. The deploy fixture cannot run under the isolation the phase mandates

R1 is declared `isolation: worktree`, and its fixture is
`skillmeat deploy … --project <repo>`. Against the worktree that returns
`HTTP 404: Project not found for path: …/.claude/worktrees/adp-m3-r1-canonical-split.
Register it first` — a git worktree is not a registered SkillMeat project.

Every exit is unattractive: registering the ephemeral worktree pollutes the shared enterprise
registry with a path that vanishes at merge; deploying against the real repo root writes the
receipt's only tracked side effect (`.claude/.skillmeat-deployed.toml`, confirmed git-tracked)
into the *main* checkout rather than the PR branch, which is precisely the isolation being
mandated. Recommendation on the request: deploy post-merge against the registered project — a
receipt for a project state that exists only on an unmerged branch is not a real receipt.

### 2. The repo-wide reconcile predicate is unsatisfiable on pre-existing state

R1 asserts `.gaps == [] and .drift == []` across the whole repo. Measured here:

| | baseline (pre-move) | post-move |
|---|---|---|
| expected | 350 | 350 |
| present | 202 | 202 |
| gaps | 148 | 148 |
| drift | 83 | 83 |
| `exit_reason` | `unsatisfiable` | `unsatisfiable` |
| verdicts | 200 `refuse_queue`, 1 `capture`, 1 `queue` | identical |

Identical before and after, so the canonical move neither causes nor can cure it. The
per-artifact verdict names the cause: `provenance unknown -- no ledger row and no
project-original marker; inventory gap, fail closed`. Those artifacts have never been deployed
through SkillMeat, so none has a ledger row — and earning ~200 ledger rows *is* the M3
migration. It cannot also be the precondition of M3's first phase.

Related finding: `node_01M16WRV2NPZVVAYNE02TDWWVK`.

Worth tightening separately: the predicate's other half, `all(. != "refuse")`, passes only
because the emitted verdict string is `refuse_queue` rather than `refuse`. It is passing on a
substring technicality, not on merit.

## Not done — handed off

"Register the upstream edit point" means editing `docs/ARTIFACT-UPSTREAM-REGISTRY.md` in
`agentic_meta_dev`. This session is cwd-pinned to `research-foundry` and cannot write that
repo. The existing RF row reads:

```
| `research-foundry`, `research-foundry-swarm` | `research-foundry/.claude/skills/...` | symlink → research-foundry repo |
```

It needs its second column repointed at `research-foundry/artifacts/skills/research-foundry`
and its third changed from the symlink mechanism to a copied deployment. Handed to the
`agentic_meta_dev` session.

## Receipts

`.adp-m3-r1-evidence/` on this branch (untracked scratch):
`baseline-reconcile.json` · `r1-reconcile-receipt.json` · `r1-deploy-receipt.json` (the 404) ·
`canary-assertion.sh`.
