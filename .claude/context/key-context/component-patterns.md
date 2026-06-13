---
title: React Component Patterns - Quick Reference
description: Index and quick-reference guide for SkillMeat component conventions, styling, and accessibility patterns
audience: developers
tags: [react, typescript, components, accessibility, shadcn, radix-ui]
created: 2025-01-14
updated: 2026-03-11
category: frontend
status: active
references:
  - skillmeat/web/components/**/*.tsx
  - skillmeat/web/lib/utils.ts
---

# React Component Patterns - Quick Reference

Quick-reference decision matrix and index for SkillMeat component conventions. Detailed guides are in the `component-patterns/` subdirectory.

## Component Directory Decision

| Directory | Purpose | When to Use | Examples |
|-----------|---------|-------------|----------|
| `ui/` | shadcn/ui primitives | Never create/modify — use CLI | button, dialog, dropdown-menu |
| `shared/` | Cross-cutting UI | Used by 2+ features | ColorSelector, IconPicker, EntityPickerDialog (unified picker for members/entities) |
| `[feature]/` | Feature-specific only | Only used within one feature | collection-card, deployment-set-card |

## Key Invariants

- **Named exports only** — no default exports
- **`cn()` for all class composition** — never inline styles
- **Server components by default** — add `'use client'` only when needed
- **Never modify `components/ui/`** — compose instead using shadcn primitives

## Component Template (Minimal)

```typescript
import { cn } from '@/lib/utils';

interface MyComponentProps {
  required: string;
  optional?: boolean;
  className?: string;
}

export function MyComponent({ required, optional = false, className }: MyComponentProps) {
  return (
    <div className={cn('base-classes', optional && 'conditional-class', className)}>
      {required}
    </div>
  );
}
```

## Load Detailed Guides When Working On

| Topic | File | Use When |
|-------|------|----------|
| Shared components (ColorSelector, IconPicker) | `./component-patterns/shared-components.md` | Building or modifying cross-feature components |
| Deployment sets (card, modal, member picker) | `./component-patterns/deployment-sets.md` | Working on deployment set UI |
| Accessibility (ARIA, keyboard nav) | `./component-patterns/accessibility.md` | Building interactive components or forms |
| Styling (cn(), Tailwind, spacing, antipatterns) | `./component-patterns/styling.md` | Need spacing reference or styling conventions |
| Artifact picker patterns (useInfiniteArtifacts) | `./component-patterns/artifact-picker.md` | Building browse/select dialogs for artifacts |
| Entity picker dialog system (unified member/entity picker) | `.claude/context/key-context/entity-picker-patterns.md` | Integrating EntityPickerDialog for members, bundles, or context entities |
| Component extraction to @miethe/ui | `.claude/specs/ui-package-extraction-spec.md` | Planning new design system components or shared library extraction |

## Quick Answers

### Should I modify a shadcn component?

**No.** Compose a new component instead:

```typescript
// WRONG: Editing components/ui/button.tsx
// CORRECT: Create components/shared/submit-button.tsx
import { Button } from '@/components/ui/button';

export function SubmitButton({ loading, children }: Props) {
  return (
    <Button disabled={loading}>
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
    </Button>
  );
}
```

### How do I export components?

**Always use named exports:**

```typescript
// ✅ Correct
export function MyComponent() { ... }

// ❌ Wrong
export default function MyComponent() { ... }
```

### How do I style components?

**Always use `cn()` with Tailwind classes:**

```typescript
// ✅ Correct
<div className={cn('base-class', variant === 'primary' && 'bg-primary', className)} />

// ❌ Wrong
<div style={{ backgroundColor: variant === 'primary' ? 'blue' : 'gray' }} />
```

## Reference Links

- **shadcn/ui**: https://ui.shadcn.com/
- **Radix UI**: https://www.radix-ui.com/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **WAI-ARIA Practices**: https://www.w3.org/WAI/ARIA/apg/
