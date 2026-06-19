# Visual Prompt Templates

## Compact Mode

```text
Create a polished editorial daily engineering summary slide for {project} on {date}.

Use a fixed 3-section layout:
1. Day context + visual summary
2. Change classification
3. Plans / features ledger

Show shipped versus branch-local context clearly.
Keep the text concise and legible.
Use a light background with blue-green accents.
Avoid purple and dense paragraphs.
```

## Expanded Mode — Overview

```text
Create page 1 of a multi-image daily engineering summary for {project} on {date}.

This page is the overview page.
Use 2 sections:
1. Day context + visual summary
2. Change classification grouped into User-facing changes, Fixes, Refactors, Infra / ops

Keep the ledger off this page.
```

## Expanded Mode — Ledger

```text
Create page 2 of a multi-image daily engineering summary for {project} on {date}.

This page is the ledger and overflow page.
Use a full-width status ledger with columns:
Item, Type, Created, Started, Completed, Shipped, Surface, Refs

Make planning-only and branch-local rows visually obvious.
```
