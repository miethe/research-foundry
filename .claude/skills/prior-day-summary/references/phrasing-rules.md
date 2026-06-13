# Phrasing Rules

## Empty Day

Preferred phrasing:

- `No shipped or completed repo work landed on YYYY-MM-DD.`
- `Nothing landed yesterday in this checkout.`

Avoid:

- padding the day with adjacent unreleased work
- implying hidden progress without evidence

## Branch-Local Day

Preferred phrasing:

- `Completed branch-local work`
- `Finished in this branch, but not shipped`
- `Still under Unreleased`

Avoid:

- `released`
- `landed for users`
- `shipped`

unless git or changelog evidence proves it.

## Docs-Only Day

Preferred phrasing:

- `docs-only`
- `planning-only`
- `design/report artifacts, not live runtime behavior`

Keep future or planned surfaces in future tense.

## Shipped Day

Preferred phrasing:

- `shipped on main`
- `cut in vX.Y.Z`
- `dated changelog section and git history align`

## Visible Changes

- mention only surfaces users or operators can actually try
- if none exist, say `No real user-visible changes landed that day.`
