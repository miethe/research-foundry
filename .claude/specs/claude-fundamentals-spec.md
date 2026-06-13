# Claude Code Fundamentals Spec

**Version**: 1.0
**Purpose**: Generic patterns for Claude Code projects
**Token Target**: ~250 lines
**Format**: Dense, structured, AI-optimized

---

## Task Management

| Pattern | Implementation | Tool |
|---------|---------------|------|
| Track multi-step work | Use TodoWrite for >3 steps | `TodoWrite` |
| Session continuity | Update todos at session end | `TodoWrite` |
| Completion | Mark done + delete completed | `TodoWrite` |
| Abandon work | Clean up stale todos | `TodoWrite` |

**TodoWrite Structure**:
```
- [ ] Task description (clear, actionable)
  - Status: in-progress | blocked | completed
  - Context: [why needed]
```

---

## Agent Delegation

### Decision Tree

```
Task Type           → Agent              → Model   → Use When
──────────────────────────────────────────────────────────────
Exploration         → codebase-explorer  → Haiku   → Find patterns (80%)
Deep analysis       → explore            → Haiku   → Understand how/why (20%)
Most docs          → documentation-writer → Haiku   → 90% of documentation
Complex docs       → documentation-complex → Sonnet → 5+ services, deep trade-offs
Doc planning       → documentation-planner → Opus   → Strategy only (delegates writing)
AI artifacts       → ai-artifacts-engineer → Sonnet → Skills, agents, context files
```

### Exploration Strategy (2-Phase)

**Phase 1: Quick Discovery (0.1s)**
```
Task("codebase-explorer", "Find [pattern] implementations")
→ Get symbol inventory
→ Identify key files (file:line references)
```

**Phase 2: Deep Analysis (2-3 min, only if needed)**
```
Task("explore", "Analyze [specific files from Phase 1]")
→ Full context and patterns
```

**Key Metrics**:
- Symbols: 0.1s, ~$0.001, 96% token reduction
- Explore: 2-3min, ~$0.02, full context

---

## Documentation vs AI Artifacts

| Aspect | Documentation | AI Artifacts |
|--------|--------------|--------------|
| **Audience** | Humans | AI agents |
| **Location** | `/docs/`, READMEs | `.claude/`, `ai/` |
| **Agent** | documentation-* | ai-artifacts-engineer |
| **Examples** | API docs, guides | Skills, agent prompts, symbols |
| **Purpose** | Understand/use | Agent effectiveness |

**Rule**: If primary audience is human → documentation agents. If AI agent → ai-artifacts-engineer.

---

## Tone & Style

| Aspect | Preference | Rationale |
|--------|-----------|-----------|
| Emojis | Never | Professional, clean communication |
| Tone | Direct, objective | Clear signal-to-noise |
| Reports | Concise | Value brevity over verbosity |
| Explanations | Minimal prose | Action-oriented |
| Examples | Only when necessary | Avoid redundancy |

**Professional Objectivity Pattern**:
- State facts, not feelings
- Use "the code", "the implementation", not "I feel"
- Focus on technical merit
- Clear rationale over persuasion

---

## Git Workflow

### Commit Pattern

```bash
# Multi-tool pattern (parallel when safe)
git status && git diff && git log -5

# Review → Stage → Commit
git add [files]
git commit -m "$(cat <<'EOF'
[type](scope): clear message

Brief description of changes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Commit Types

| Type | Use Case | Example |
|------|----------|---------|
| `feat` | New feature | `feat(auth): add OAuth2 flow` |
| `fix` | Bug fix | `fix(api): handle null responses` |
| `refactor` | Code improvement | `refactor(db): extract query helpers` |
| `docs` | Documentation | `docs(api): add endpoint examples` |
| `test` | Tests | `test(auth): add unit tests` |
| `chore` | Maintenance | `chore(deps): update dependencies` |

### Safety Rules

- ✓ Commit often with descriptive messages
- ✗ NEVER `--amend` others' commits
- ✗ NEVER `--force` to main/master
- ✗ NEVER skip hooks without explicit request
- ✗ NEVER commit secrets (.env, credentials.json)

---

## Pull Request Pattern

### PR Creation Workflow

```bash
# 1. Parallel status check
git status & git diff & git log [base]...HEAD

# 2. Analyze ALL commits in PR (not just latest)
git diff [base-branch]...HEAD

# 3. Create PR
gh pr create --title "[title]" --body "$(cat <<'EOF'
## Summary
- [Bullet 1]
- [Bullet 2]

## Test Plan
- [ ] Test case 1
- [ ] Test case 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Critical**: Analyze FULL commit history, not just latest commit.

---

## Tool Usage Best Practices

### Read/Edit/Write Priority

```
Task                 → Tool Order           → Rationale
───────────────────────────────────────────────────────────
File search          → Glob                 → Fast pattern matching
Content search       → Grep                 → Optimized permissions
Read files           → Read                 → NOT cat/head/tail
Edit files           → Edit                 → NOT sed/awk
Write files          → Write                → NOT echo >
Terminal ops         → Bash                 → git, npm, docker
```

**Anti-Patterns**:
- ✗ `find` → Use Glob
- ✗ `grep` → Use Grep
- ✗ `cat/head/tail` → Use Read
- ✗ `sed/awk` → Use Edit
- ✗ `echo >` → Use Write

### Bash Usage

**Parallel Commands** (independent):
```bash
# Multiple Bash calls in one message
git status
git diff
git log -5
```

**Sequential Commands** (dependent):
```bash
# Single Bash call with &&
mkdir foo && cp file foo/ && cd foo
```

**Avoid**:
- Newlines to separate commands (except in quoted strings)
- `cd` unless explicit (use absolute paths)
- Interactive flags (`-i`) - not supported

---

## Code Review Expectations

### Review Checklist

| Area | Check |
|------|-------|
| **Architecture** | Follows project patterns? |
| **Tests** | Unit + integration coverage? |
| **Documentation** | In allowed buckets? Required frontmatter? |
| **Error Handling** | Comprehensive, logged? |
| **Observability** | Spans, structured logs? |
| **Security** | No secrets, proper auth? |
| **Performance** | Efficient queries, pagination? |

### Review Standards

- Prefer refactoring over new code
- Justify new patterns in ADRs
- Validate with appropriate agents:
  - `task-completion-validator` for implementation
  - `documentation-writer` for doc quality
- Link PRDs, ADRs in PR description

---

## Development Approach

### Before Implementing

```
1. Explore → Find existing patterns (codebase-explorer)
2. Understand → Read similar implementations
3. Plan → Identify affected layers/files
4. Implement → Follow existing conventions
5. Test → Unit + integration + E2E
6. Document → Update relevant docs
7. Validate → Use task-completion-validator
```

### Reuse > Refactor > New Code

**Priority Order**:
1. **Reuse**: Existing code handles use case?
2. **Refactor**: Adapt existing pattern?
3. **New Code**: Justify in ADR, establish pattern

**Anti-Pattern**: One-off implementations, dead code paths

---

## Project Lifecycle Context

### Active Development Phase

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| Migrations | Direct, no rollback | No prod users |
| Compatibility | Current version only | No legacy support needed |
| Features | Complete or remove | No partial implementations |
| Tech Debt | Fix on sight | Clean codebase priority |

**Rule**: No prod users = aggressive refactoring OK

---

## Multi-Agent Orchestration

### Delegation Pattern

```
Main Agent (Sonnet)
  ├─ Task("codebase-explorer", "query") → Symbol lookup
  ├─ Task("explore", "analyze") → Deep analysis
  ├─ Task("documentation-writer", "create docs") → Most docs
  ├─ Task("ai-artifacts-engineer", "create skill") → AI artifacts
  └─ Task("task-completion-validator", "verify") → Validation
```

### When to Delegate

| Task | Delegate? | Why |
|------|-----------|-----|
| Find pattern | ✓ codebase-explorer | Fast symbol query |
| Understand implementation | ✓ explore | Full context needed |
| Write docs | ✓ documentation-writer | Optimized for docs |
| Create skill | ✓ ai-artifacts-engineer | Context engineering |
| Validate work | ✓ task-completion-validator | Objective verification |
| Simple edit | ✗ Do directly | Overhead not worth it |

---

## Symbol System Awareness

### Symbol Query Pattern

```
Query: "Find Button implementations"
↓
Returns: file:line references with metadata
↓
Read specific files: Targeted, token-efficient
```

### Domain-Specific Symbols

| File | Domain | Symbols | Use Case |
|------|--------|---------|----------|
| `symbols-api.json` | Backend | 3041 | API layer queries |
| `symbols-ui.json` | Frontend | 755 | UI component queries |
| `symbols-web.json` | Next.js | 1088 | App router queries |
| `symbols-*-tests.json` | Tests | 4004 | Test helper queries |

**Layer Tags**: `router`, `service`, `repository`, `component`, `hook`, `page`, `test`

---

## Professional Objectivity

### Language Patterns

| ✗ Avoid | ✓ Prefer |
|---------|----------|
| "I think we should..." | "The implementation should..." |
| "I feel this is better" | "This approach provides..." |
| "In my opinion..." | "Based on [criteria]..." |
| "I discovered..." | "Analysis shows..." |
| "I'm excited to..." | "The next step is..." |

### Rationale-First Communication

```
❌ "Let's refactor this!"
✓ "Refactoring consolidates duplicate logic (40% reduction) and improves maintainability."

❌ "This is a better approach."
✓ "This approach reduces latency by 30% (benchmark: X vs Y)."
```

---

## Error Handling Philosophy

| Level | Strategy | Example |
|-------|----------|---------|
| **System** | Fail fast, log structured | OpenTelemetry spans + JSON logs |
| **User** | Graceful degradation | Fallback UI, error boundaries |
| **Developer** | Clear error messages | Include context, file:line |
| **AI Agent** | Actionable feedback | Specific fix suggestions |

---

## Testing Strategy

### Test Pyramid

```
E2E (10%)          → User workflows
Integration (30%)  → Service boundaries
Unit (60%)         → Functions, components
```

### Test Coverage Targets

| Layer | Target | Priority |
|-------|--------|----------|
| Business logic | 90%+ | Critical |
| API endpoints | 80%+ | High |
| UI components | 70%+ | Medium |
| Utilities | 90%+ | High |

---

## Observability Requirements

### Structured Logging

```javascript
log.info({
  message: "Operation completed",
  trace_id: "...",
  span_id: "...",
  user_id: "...",
  request_id: "...",
  duration_ms: 123
})
```

### Span Naming

Pattern: `{route}.{operation}`

Examples:
- `listings.create`
- `auth.login`
- `valuation.calculate`

---

## Summary

This spec provides generic Claude Code patterns applicable across projects. Compose with project-specific specs for complete CLAUDE.md.

**Key Principles**:
- Task management with TodoWrite
- 2-phase exploration (symbols → deep analysis)
- Documentation vs AI artifacts distinction
- Professional objectivity in communication
- Tool usage best practices
- Git workflow and PR patterns
- Multi-agent delegation strategy
