# Output Modes

Use this workflow when the user asks for a specific answer shape or a visual companion.

## Short Answer

Use when the user wants a concise status update.

Structure:

1. what shipped or did not ship
2. one sentence on visible changes
3. one sentence on caveats or branch-local context

## Full Answer

Use when the user wants the full daily pass.

Structure:

1. shipped / completed work
2. visible changes and try-it steps
3. wins, debt, deferred items, caveats

## Audit Style

Use when precision matters more than readability.

Structure:

1. date window and evidence sources
2. classification and provenance notes
3. explicit contradictions or metadata drift

## Visual Companion

Use only when the day has enough substance to justify a visual artifact.

### Compact Mode

Use one image when:

- one dominant story defines the day
- ledger rows are limited
- visible surfaces are 1-2 related areas

### Expanded Mode

Use multiple images when:

- there are multiple visible stories
- the ledger becomes unreadable in one frame
- shipped and branch-local work both deserve distinct treatment

For the data contract and prompts, use:

- `../templates/visual-summary-data.schema.yaml`
- `../templates/visual-image-prompts.md`
