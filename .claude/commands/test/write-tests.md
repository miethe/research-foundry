---
description: Add unit + integration tests for a changed area; include negative paths.
allowed-tools: Read(./**), Write(./**), Edit, MultiEdit, Bash(pnpm:*), Bash(uv:*), Bash(git add:*), Bash(git commit:*)
argument-hint: "[path-or-glob]"
---

Identify code touched under "$ARGUMENTS". For each file:
- Add unit tests (DTO validation, services, repos).
- Add FastAPI TestClient tests for API shapes and errors.
- Add RTL/Playwright happy + failure paths for web.
Propose a commit message and run the test suites.
