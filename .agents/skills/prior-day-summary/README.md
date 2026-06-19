# prior-day-summary Skill

## Purpose

`prior-day-summary` is a model-agnostic workflow pack for answering prompts like
"what we did yesterday", "what shipped yesterday", "what changed yesterday",
"what was visibly different", and "how do I try it". It is designed for recurring
automation threads, release-adjacent daily summaries, and honest empty-day audits.

The workflow is shell-first and evidence-first: classify the day from git and
changelog evidence before doing any storytelling.

## When To Use This Skill

Use this skill when the task is to:

- summarize completed work from the prior day
- separate shipped work from branch-local or docs-only work
- explain which changes were actually visible to users
- provide concise try-it steps for real visible surfaces
- produce a reusable daily visual-summary companion

Do not use this skill for:

- release execution
- changelog authoring
- deep code review
- generic weekly or monthly narrative reporting

## Evidence Sources In Priority Order

1. Exact git date-window history
2. Merge history for the same date window
3. `origin/main` versus `HEAD` divergence
4. Tags and dated changelog headings
5. Plan/progress/worknote artifacts
6. Memory or prior summaries

See [`references/evidence-priority.md`](./references/evidence-priority.md) for the full ranking.

## File Layout

```text
.claude/skills/prior-day-summary/
├── SKILL.md
├── SPEC.md
├── README.md
├── workflows/
│   ├── core-workflow.md
│   ├── provenance-rules.md
│   ├── visible-surface-pass.md
│   └── output-modes.md
├── references/
│   ├── evidence-priority.md
│   ├── phrasing-rules.md
│   └── command-reference.md
├── scripts/
│   ├── collect_window_evidence.py
│   └── render_prior_day_summary.py
├── templates/
│   ├── standard-summary.md
│   ├── empty-day-summary.md
│   ├── branch-local-summary.md
│   ├── docs-only-summary.md
│   ├── visual-summary-data.schema.yaml
│   └── visual-image-prompts.md
├── examples/
│   ├── release-day.yaml
│   ├── empty-day.yaml
│   └── branch-local-day.yaml
└── integrations/
    ├── codex.md
    └── claude-code.md
```

## Fast Path Commands

```bash
# Collect evidence for a single prior day
python3 .claude/skills/prior-day-summary/scripts/collect_window_evidence.py --date 2026-05-19

# Save JSON to a file
python3 .claude/skills/prior-day-summary/scripts/collect_window_evidence.py \
  --date 2026-05-19 \
  --out /tmp/prior-day-summary.json

# Render a markdown first draft
python3 .claude/skills/prior-day-summary/scripts/render_prior_day_summary.py \
  --input /tmp/prior-day-summary.json \
  --mode full
```

## Output Modes

- **Short answer**: one or two paragraphs, minimal evidence
- **Full answer**: shipped status, visible changes, try-it steps, wins/debt
- **Audit style**: explicit evidence framing, caveats, provenance notes
- **Visual companion**: compact one-image or expanded multi-image summary

See [`workflows/output-modes.md`](./workflows/output-modes.md).

## Classification Rules

The workflow classifies the day before writing the summary:

- `empty_day`
- `branch_local`
- `docs_only`
- `shipped`

Mixed days can still be `shipped` if shipped proof exists, but branch-local work
must remain labeled as not shipped.

See [`workflows/provenance-rules.md`](./workflows/provenance-rules.md).

## Common Failure Modes

- **Quiet-day inflation**: adjacent unreleased work gets narrated as yesterday's progress
- **Branch-local shipping drift**: completed plan status gets mistaken for shipped work
- **Docs-only overclaim**: design docs or plans are written as live product behavior
- **Visible-surface fabrication**: internal fixes are described as user-facing changes
- **Tag/changelog overtrust**: a dated changelog line is used without checking the real commit window

## Script Contracts

### `collect_window_evidence.py`

- Input: `--date YYYY-MM-DD` or explicit `--since` and `--until`
- Output: JSON evidence payload to stdout or `--out`
- Purpose: deterministic fast truth pass over git/changelog state

### `render_prior_day_summary.py`

- Input: evidence JSON from the collector
- Output: markdown summary draft
- Purpose: choose the correct template and render a first-pass narrative with caveats

These scripts are intentionally lightweight and dependency-free.

## Agent-Specific Invocation Notes

The core workflow is the same across tools. Only the loading style differs:

- Codex: open `SKILL.md`, then the one matching workflow doc
- Claude Code: `Skill("prior-day-summary")`, then load matching workflow docs
- Human shell session: run the bundled scripts directly and edit the rendered draft

See [`integrations/codex.md`](./integrations/codex.md) and [`integrations/claude-code.md`](./integrations/claude-code.md).

## Maintenance Checklist

- Keep `SPEC.md` in sync when workflows or templates change
- Update examples when the classification rules evolve
- Re-verify script behavior against a real shipped day, a branch-local day, and an empty day
- Update `skills-index.md` when the skill is added, renamed, or promoted
- Keep visual template prompts aligned with the automation's current rendering expectations
