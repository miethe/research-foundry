# ARC Output Contract

## Required Files

Every completed run directory must contain:

- `evidence_pack.md`
- `findings.yaml`
- `scorecard.json`
- `risk_register.yaml`
- `decision_record.md`
- `validation_plan.md`

Use `templates/` for Markdown structure and `schemas/` as the authority for structured outputs.

## Finding Requirements

Each finding must include:

- Stable `id`.
- Clear `title` and `claim`.
- `finding_type`, `severity`, and `confidence`.
- At least one evidence item with source and locator.
- Recommendation.
- Validation method and concrete check.
- Reviewer identity.

Synthetic or persona-based observations are hypotheses until validated.

## Disposition Buckets

The decision record should separate:

- `accepted` - evidence is sufficient and action is warranted.
- `rejected` - unsupported, out of scope, duplicate, or intentionally not acted on.
- `disputed` - plausible but unresolved conflict remains.
- `watchlist` - worth tracking but not actionable now.

Rejected and disputed findings still keep their evidence.

## Validation Gate

Use:

```bash
uv run arc validate runs/<date>-<slug>
```

Validation must pass before presenting a run as complete.
