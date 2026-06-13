---
description: Scaffold a feature following MP architecture (schema → DTO → repo → service → API → UI)
allowed-tools: Read(./**), Write(./**), Edit, MultiEdit
argument-hint: "[feature-name]"
---

<!-- MeatyCapture Integration - Project: skillmeat -->
## Context Gathering

Before implementation, search request-logs: `/mc search "feature-keyword" skillmeat`

## Implementation

Using MP architecture rules:

1. Plan "$ARGUMENTS" (scope 1-2 files per layer)
2. Implement sequence: schema → DTO → repo → service → API → web hook + UI → tests
3. Wire telemetry spans & JSON logs
4. Update OpenAPI docs
5. Create commit with clear message

## Post-Implementation

- Update related request-log items: change `**Status:**` to `done`
- Capture issues discovered: `/mc capture {"title": "...", "type": "bug"}`

Follow @CLAUDE.md implementation sequence exactly.
