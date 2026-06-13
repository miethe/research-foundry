# Debug and Remediation Stub

Analyze the attached list of bugs. Create a remediation plan with designs, then implement it. You must use subagents to perform all tasks, only delegating tasks. You are Opus, so tokens are expensive; use them wisely to optimize for reasoning, with all token-heavy work being delegated. Commit often.

- **Validation Strategy**:
  - Validate code changes via direct code review (Read/Grep tools).
  - You MAY create test scripts, automation, or similar if absolutely necessary, but only if there isn't a more appropriate, reusable method that wouldn't be significant extra effort or complexity
    - ie unit tests or mock API calls for backend, or chrome-devtools for frontend, etc.
    - However, if one-time scripts are created, or screenshots saved, or otherwise, and they have no further value in the future after immediate verification, then they must be deleted before commit.
  - If new issues appear during implementation, continue to iteratively analyze and remediate them.

- **NO validation reports**:
  - Do not create VALIDATION_SUMMARY.txt, CODE_VERIFICATION_REPORT.md, or any other reports/summaries outside the bug-fixes doc.
  - If an artifact is created by a necessary validation method per above for the agent's immediate review, then it must be deleted before commit.

## Documentation Requirements

**Update the monthly bug-fixes document ONLY** (create if doesn't exist):
- File: `.claude/worknotes/bug-fixes-{YYYY}-{MM}.md`
- Example: `bug-fixes-2025-11.md`

Add one section per bug using this template:

```markdown
### {BUG DESCRIPTIVE TITLE}

**Issue**: {Explanation of the bug}
- **Location**: `filepath:line-number` or component name
- **Root Cause**: {Brief explanation}
- **Fix**: {Brief explanation of changes}
- **Commit(s)**: {Commit hash(es)}
- **Status**: RESOLVED
```

## Strict Rules

- ❌ Do NOT commit validation scripts or test automation if they are one-time use only
- ❌ Do NOT commit screenshots, reports, or summaries outside bug-fixes doc
- ❌ Do NOT add markdown files, PNG files, or JSON reports unless they are part of the actual bug fix, or add significant value to the codebase long-term
- ✅ DO delete all untracked artifacts (screenshots, reports, scripts) before final commit
- ✅ DO update only the monthly bug-fixes document for all validation notes
- ✅ DO commit frequently with clear, focused commit messages