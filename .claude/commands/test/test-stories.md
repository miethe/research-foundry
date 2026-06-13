---
description: Run Storybook tests on UI components with accessibility validation
allowed-tools: Bash, Read(./**), Glob
argument-hint: "[component-pattern]"
---

Execute MP Storybook testing for "$ARGUMENTS":

1. Run component tests: `pnpm --filter "./packages/ui" test -- --testPathPattern="$ARGUMENTS"`
2. Build Storybook: `pnpm --filter "./packages/ui" build-storybook`
3. Run accessibility tests: `pnpm --filter "./packages/ui" test -- --testNamePattern="a11y"`
4. Generate coverage report and validate >80% threshold

Use MP testing patterns and report structured results with accessibility compliance.
