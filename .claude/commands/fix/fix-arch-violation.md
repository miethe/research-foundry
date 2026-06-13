---
description: Fix common architecture violations (mixed DTO/ORM, direct Radix imports, etc.)
allowed-tools: Read(./**), Edit, MultiEdit, Grep
argument-hint: "[violation-type]"
---

Common violations to fix:
- "mixed-dto-orm": Separate Pydantic and SQLAlchemy models
- "direct-radix": Move Radix imports to @miethe/ui wrapper
- "raw-errors": Wrap in ErrorResponse envelope
- "offset-pagination": Convert to cursor pagination

Identify violations in codebase and fix systematically.

<!-- MeatyCapture Integration - Project: skillmeat -->
## Post-Fix

If violation pattern warrants tracking (recurring/significant):
- `/mc capture {"title": "Fixed [violation-type]", "type": "task", "status": "done"}`
