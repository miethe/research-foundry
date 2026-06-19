# Core Workflow

Use this workflow for the default prior-day summary path.

## 1. Normalize the Window

1. Resolve the exact target date.
2. Convert it into a closed-open git window:
   - `since = YYYY-MM-DD 00:00:00`
   - `until = next day 00:00:00`
3. Use absolute dates in the output when there is any chance of confusion.

## 2. Run the Fast Truth Pass

Run the minimum evidence set before any narrative work:

```bash
python3 .claude/skills/prior-day-summary/scripts/collect_window_evidence.py --date YYYY-MM-DD
```

At minimum, the evidence pass must gather:

- `git log --all` over the window
- merge log for the same window
- current branch
- `git rev-list --left-right --count origin/main...HEAD` when available
- latest tags
- dated changelog headings from `CHANGELOG.md` and `docs/CHANGELOG.md` when present

## 3. Classify the Day

Choose one primary class:

- `empty_day`
- `branch_local`
- `docs_only`
- `shipped`

Use [`provenance-rules.md`](./provenance-rules.md) when the classification is ambiguous.

Do this before writing any prose.

## 4. Render the First Draft

Render the matching markdown template from the evidence JSON:

```bash
python3 .claude/skills/prior-day-summary/scripts/render_prior_day_summary.py \
  --input /tmp/prior-day-summary.json
```

Treat the rendered output as a first draft. It is allowed to be concise and caveated.

## 5. Add Secondary Passes Only When Needed

Load additional workflows only when needed:

- visible surfaces and try-it guidance → [`visible-surface-pass.md`](./visible-surface-pass.md)
- alternate answer shapes or visual companions → [`output-modes.md`](./output-modes.md)

## 6. Final Output Rules

- Lead with what is proven.
- Separate shipped from branch-local.
- Keep empty days empty.
- Label docs-only work clearly.
- Avoid PR or release attribution unless git proves it.
