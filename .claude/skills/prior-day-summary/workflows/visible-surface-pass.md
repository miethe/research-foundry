# Visible Surface Pass

Load this workflow only when the day includes real visible changes or the user explicitly asks how to try them.

## Goal

Separate:

- user-facing changes
- fixes
- refactors
- infra / ops

Then describe only the visible surfaces a user or operator could actually exercise.

## Procedure

1. Start from shipped or clearly completed evidence.
2. Trace each item to a visible surface:
   - web route or page
   - CLI command
   - docs page or demo
   - operator surface
3. Exclude:
   - internal refactors
   - backend-only hardening with no visible effect
   - future or planned surfaces

## How To Try It

For each retained visible item:

1. name the route, command, or doc
2. give the minimum steps to exercise it
3. avoid speculative instructions

Examples:

- Web: `skillmeat web dev`, then visit the artifact detail page and open the Recipe tab.
- CLI: `skillmeat auth login --enterprise <url>`, then `skillmeat enterprise deploy pull`.
- Docs: open the shipped guide and follow the listed commands.

## Output Discipline

- Keep user-facing bullets separate from fixes, refactors, and infra.
- If there are no visible surfaces, say so directly.
- Try-it steps should be practical and short.
