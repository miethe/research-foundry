---
schema_version: 2
doc_type: skill_spec
skill_name: prior-day-summary
skill_version: 0.1.0
aligned_app_version: 0.47.0
status: draft
created: 2026-05-20
updated: 2026-05-20
owner: nick
source_docs:
  - CHANGELOG.md
  - docs/current-state.md
  - .claude/skills/prior-day-summary/README.md
related_skills:
  - changelog-sync
  - release
  - demo-foundry
affects_commands: []
---

<!-- Convention reference: .claude/specs/artifact-structures/skill-spec-convention.md -->

# prior-day-summary — Skill Specification

> **Reading this file**: This is the versioned capability contract for the `prior-day-summary` skill.
> For invocation-time routing, see `SKILL.md` in this same directory.

---

## 1. Purpose & Scope

**Mission**: Enable agents to produce honest, changelog-first, git-verified summaries of prior-day work, including shipped versus branch-local status, visible user-facing changes, try-it guidance, and optional visual summary assets, without inventing progress from adjacent work.

**In scope**:
- Prior-day summary synthesis for exact date windows
- Shipping/provenance reconciliation across git history, tags, changelog headings, and branch divergence
- Empty-day, branch-local, docs-only, and shipped-day classification
- Visible-surface pass for web, CLI, docs, demos, and operator-facing changes
- Try-it guidance for real user-visible changes
- Visual-summary template guidance and image-prompt scaffolding
- Deterministic evidence collection and first-draft rendering via bundled scripts

**Out of scope**:
- Writing changelog entries or cutting releases — use `release` and `changelog-sync`
- Deep code implementation review — use normal review/debug workflows
- Inventing PR mappings or release provenance when git cannot prove them
- Repo-wide weekly/monthly reporting; this skill is intentionally prior-day scoped
- Non-evidence-based summaries driven only by memory or plan status

---

## 2. Capability Coverage

| Intent | Workflow / Section | Canonical Doc |
|--------|--------------------|---------------|
| Summarize what we did yesterday | `workflows/core-workflow.md` | `README.md` |
| Tell me what actually shipped yesterday | `workflows/provenance-rules.md` | `CHANGELOG.md`, `docs/current-state.md` |
| Separate visible changes from internal work | `workflows/visible-surface-pass.md` | `references/phrasing-rules.md` |
| Explain how to try the changes as a user | `workflows/visible-surface-pass.md` | `references/command-reference.md` |
| Call out branch-local versus shipped status | `workflows/provenance-rules.md` | `references/evidence-priority.md` |
| Produce an honest empty-day summary | `workflows/core-workflow.md`, `templates/empty-day-summary.md` | `references/phrasing-rules.md` |
| Produce a docs-only prior-day summary | `workflows/provenance-rules.md`, `templates/docs-only-summary.md` | `references/phrasing-rules.md` |
| Produce a branch-local prior-day summary | `workflows/provenance-rules.md`, `templates/branch-local-summary.md` | `references/phrasing-rules.md` |
| Produce a visual summary companion | `workflows/output-modes.md`, `templates/visual-summary-data.schema.yaml` | `templates/visual-image-prompts.md` |
| Collect window evidence deterministically | `workflows/core-workflow.md` | `scripts/collect_window_evidence.py --help` |
| Render a markdown first draft from evidence | `workflows/output-modes.md` | `scripts/render_prior_day_summary.py --help` |

---

## 3. Invariants & Constraints

1. **Exact date-window evidence comes first**: Agents must check the explicit git window for the target date before summarizing. A prior-day summary without an exact `--since/--until` pass is invalid.

2. **Git outranks narrative artifacts**: Commit history, merge history, tags, and branch divergence outrank plan status, memory, or worknotes when they conflict.

3. **Branch-local work is never shipped by implication**: Work that appears only on local or feature branches must not be described as shipped unless `origin/main`, a release tag, or a dated changelog section proves it.

4. **Empty days stay empty**: If the date window has no shipped or completed repo work, the summary must say so directly. Nearest prior work may appear only as clearly labeled context.

5. **Docs-only and planning-only work must be labeled**: Planned commands, routes, or UI surfaces remain future-tense unless runtime evidence shows they are live.

6. **Visible-change and try-it sections are conditional**: These sections appear only when real visible surfaces exist. Do not fabricate user-facing bullets from refactors or repo-internal cleanup.

7. **The skill remains model-agnostic**: Core workflows must not depend on Claude-only or Codex-only primitives. Tool-specific notes belong in integration docs, not in the main workflow path.

---

## 4. Enhancement Backlog

- **[BL-1] Template-driven HTML slide renderer**: Render the visual-summary schema into deterministic HTML/CSS before image generation.
  _Status_: candidate
  _Rationale_: Current visual path is prompt-driven. HTML rendering would improve repeatability and legibility.

- **[BL-2] Cross-repo changelog adapter registry**: Per-repo changelog/source adapters for repos that use `docs/CHANGELOG.md`, multiple changelogs, or nonstandard release notes.
  _Status_: planned
  _Rationale_: The current v0.1.0 scripts handle common patterns but still rely on lightweight heuristics.

- **[BL-3] Structured ledger extraction from plan/progress docs**: Auto-build the `created / started / completed / shipped` ledger from repo-native artifacts rather than manual synthesis.
  _Status_: candidate
  _Rationale_: High value for dense days; needs careful drift handling across plan formats.

- **[BL-4] Saved visual asset export for automation threads**: Emit image metadata plus canonical filenames for compact and expanded modes.
  _Status_: deferred
  _Rationale_: Useful once the visual layer is stable across multiple repos.

- **[BL-5] Confidence score on classification**: Emit confidence and ambiguity notes when evidence is mixed.
  _Status_: deferred
  _Rationale_: Helpful for operator trust, but not required for the initial workflow.

---

## 5. Changelog

### v0.1.0 — 2026-05-20
- Initial SPEC.md drafted
- Capability coverage matrix: 11 intents across 4 workflow docs and 2 bundled scripts
- Status: draft

---

## 6. Integration Points

| Agent / Command | Invocation Pattern | Notes |
|-----------------|--------------------|-------|
| Codex / Claude / equivalent repo-aware agent | Load `prior-day-summary` and route to `workflows/core-workflow.md` | Main model-agnostic entrypoint |
| Daily automation threads | Use the skill's workflow + templates to produce prior-day summaries | Especially useful for recurring `what we did yesterday` jobs |
| `release` skill | Adjacent, not co-required | Release skill proves cut/tag flow; this skill proves prior-day narrative |
| `changelog-sync` skill | Adjacent, not co-required | Helpful when changelog coverage questions arise |
| `demo-foundry` / image generation workflows | Optional co-load | Only when a visual companion image is requested |

**Co-loaded with**: `changelog-sync` when changelog coverage itself is disputed; image-generation tooling only when the user asks for visuals.

---

## 7. Success Signals

- Agents check the exact git window before writing the first narrative sentence.
- Empty days are reported as empty instead of being padded with nearby unreleased work.
- Branch-local completions are explicitly labeled as branch-local and not flattened into shipped language.
- Visible-change sections contain only surfaces a user or operator could actually try.
- Try-it steps map to real routes, commands, or docs rather than speculative future work.
- The bundled scripts produce usable JSON and markdown drafts without external dependencies.
- The skill can be applied the same way from Codex, Claude, or a human shell session.
