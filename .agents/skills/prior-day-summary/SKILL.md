---
name: prior-day-summary
description: |
  Produce changelog-first, evidence-backed summaries of prior-day work for prompts
  like "what we did yesterday", "what shipped yesterday", "what changed yesterday",
  "what was visibly different", and "how do I try it". Use this skill for daily
  automation reports, release-adjacent status synthesis, empty-day audits, and
  branch-local versus shipped reconciliation. Progressive disclosure: classify the
  day first, then load only the workflow docs needed for visible-surface analysis,
  debt/wins framing, or visual-summary output.
version: 0.1.0
updated: 2026-05-20
spec: ./SPEC.md
status: active
---

# prior-day-summary Skill

High-level router for prior-day delivery summaries. Keep the main path shell-first,
evidence-first, and model-agnostic. For the formal capability contract see `./SPEC.md`.

---

## Route Table

| User Intent | Workflow Doc | Canonical Doc |
|---|---|---|
| Summarize what we did yesterday | `./workflows/core-workflow.md` | `./README.md` |
| Prove what actually shipped yesterday | `./workflows/provenance-rules.md` | `CHANGELOG.md`, `docs/current-state.md` |
| Separate user-visible changes from internal work | `./workflows/visible-surface-pass.md` | `./references/phrasing-rules.md` |
| Explain how to try the changes as a user | `./workflows/visible-surface-pass.md` | `./references/command-reference.md` |
| Choose short/full/audit/visual output modes | `./workflows/output-modes.md` | `./templates/standard-summary.md` |
| Render a deterministic first draft from shell evidence | `./workflows/core-workflow.md` | `./scripts/render_prior_day_summary.py --help` |

---

## Policy

### Core Guardrails

1. Check the exact date window before doing any storytelling.
2. Let git date-window evidence outrank plan docs, memory, and adjacent narrative.
3. Treat dated changelog headings and `origin/main` history as shipping sanity checks, not as standalone proof.
4. Keep empty days empty.
5. Label docs-only or planning-only work explicitly.
6. Never describe branch-local work as shipped unless `origin/main`, a tag, or a dated changelog section proves it.

### Progressive Disclosure

1. Start with `./workflows/core-workflow.md`.
2. Load `./workflows/provenance-rules.md` when shipped versus branch-local status is ambiguous.
3. Load `./workflows/visible-surface-pass.md` only when real visible surfaces exist or the user explicitly asks for try-it steps.
4. Load `./workflows/output-modes.md` only when the answer needs a specific format such as audit-style or visual-companion output.

### Quick Commands

```bash
# Collect deterministic evidence for one date window
python3 .Codex/skills/prior-day-summary/scripts/collect_window_evidence.py --date 2026-05-19

# Render a first-pass markdown summary from collected evidence
python3 .Codex/skills/prior-day-summary/scripts/render_prior_day_summary.py \
  --input /tmp/prior-day-summary.json
```

### Read-Only Default

The summary path is read-only by default. Writing reports, saving rendered output,
or copying visual assets is allowed only when the surrounding task explicitly asks
for durable artifacts.
