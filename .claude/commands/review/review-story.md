---
description: Comprehensive review of implemented story
argument-hint: "<story_id>"
allowed-tools: Read, Grep, Bash(git:*), Bash(pnpm:*), Bash(pytest:*), Bash(uv:*)
---

# /review-story

You are Claude Code performing final QA review for story `$ARGUMENTS`.

## Review Checklist

### 1. Code Quality Review

Use code-reviewer subagent for comprehensive review:

```bash
@code-reviewer comprehensive-review ${story_id} \
  --check-standards \
  --check-security \
  --check-performance \
  --check-accessibility
```

### 2. Acceptance Criteria Verification

For each AC in the original story:

```markdown
## AC Verification Report

| AC # | Criterion | Status | Evidence |
|------|-----------|--------|----------|
| 1 | User can create resource | ✅ PASS | Test: test_create_resource.py:15 |
| 2 | Resource validates input | ✅ PASS | Test: test_resource_validation.py:22 |
| 3 | Error shows friendly message | ✅ PASS | E2E: resource.spec.ts:45 |
```

### 3. Test Coverage Analysis

```bash
# Backend coverage
uv run --project services/api pytest --cov=app --cov-report=term-missing

# Frontend coverage
pnpm --filter "./apps/web" test:coverage

# Generate report
echo "## Test Coverage Report" > .claude/reports/${story_id}-coverage.md
echo "Backend: ${backend_coverage}%" >> .claude/reports/${story_id}-coverage.md
echo "Frontend: ${frontend_coverage}%" >> .claude/reports/${story_id}-coverage.md
```

### 4. Performance Check

```bash
# Check bundle size impact
pnpm --filter "./apps/web" build
pnpm --filter "./apps/web" analyze

# Check API response times
uv run --project services/api python -m pytest app/tests/performance/ -v
```

### 5. Security Audit

```bash
# Check for security issues
pnpm audit
uv run --project services/api pip-audit

# Check for secrets
git diff origin/main..HEAD | grep -E "(password|secret|key|token)" || echo "No secrets detected"
```

### 6. Documentation Verification

Ensure all docs updated:

- [ ] API docs reflect new endpoints
- [ ] README includes feature description
- [ ] CHANGELOG has entry
- [ ] Storybook stories for new components
- [ ] ADRs for significant decisions

### 7. Generate QA Report

```markdown
# QA Report: ${story_id}

## Summary
- Story: ${story_id}
- Review Date: ${date}
- Reviewer: Claude Code + subagents
- Status: [PASS|FAIL|NEEDS_WORK]

## Code Quality
- Standards Compliance: [score]/10
- Security: [PASS|FAIL]
- Performance: [PASS|FAIL]
- Accessibility: [WCAG AA compliance]

## Test Results
- Unit Tests: [X passed, Y failed]
- Integration Tests: [X passed, Y failed]
- E2E Tests: [X passed, Y failed]
- Coverage: [XX%]

## Issues Found
1. [Issue description] - Severity: [High|Medium|Low]
2. [Issue description] - Severity: [High|Medium|Low]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]

## Sign-off
- [ ] Ready for PR review
- [ ] Needs additional work
```

Save to: `.claude/reports/${story_id}-qa.md`

<!-- MeatyCapture Integration - Project: skillmeat -->
### 8. Capture Review Findings

Use `mc-quick.sh` for token-efficient capture (~50 tokens per item):

```bash
# Single issue capture
mc-quick.sh bug [DOMAIN] [COMPONENT] "Issue title" "What's wrong" "Expected behavior"

# Examples:
mc-quick.sh bug web components "Missing error boundary" "Component crashes on bad data" "Add error handling"
MC_PRIORITY=high mc-quick.sh bug api security "Auth bypass vulnerability" "Token not validated" "Add token verification"
```

- **3+ issues**: Use `/meatycapture-capture` skill for batch capture with JSON
- **Script location**: `.claude/skills/meatycapture-capture/scripts/mc-quick.sh`
- Update resolved items: `meatycapture log item update DOC ITEM --status done`
<!-- End MeatyCapture Integration -->
