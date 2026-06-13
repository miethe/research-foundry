---
title: Debugging Patterns Reference
description: Comprehensive debugging methodology, bug categories, investigation commands, and agent delegation patterns for SkillMeat
audience: ai-agents
tags:
  - debugging
  - symbols
  - investigation
  - error-handling
  - agent-delegation
created: 2026-01-14
updated: 2026-04-04
category: debugging
status: active
references:
  - ai/symbols-backend.json
  - ai/symbols-frontend.json
  - ai/symbols-shared.json
  - .claude/context/symbol-usage-guide.md
related_documents:
  - .claude/context/backend-api-patterns.md
  - .claude/context/frontend-patterns.md
  - .claude/specs/script-usage/bug-automation-scripts.md
last_verified: 2026-01-14
---

# Debugging Patterns Reference

Comprehensive reference for investigating bugs in SkillMeat using symbol-first methodology.

## Prime Directive

**Start with symbols. Fall back to exploration only when needed.**

Symbols provide 96% token savings over reading files. Use them as first-line investigation.

---

## Debugging Workflow

1. **Identify module**: From stack trace or error context
2. **Query symbols** (150 tokens): `grep "[name]" ai/symbols-*.json`
3. **Analyze locally**: Use grep/jq on symbol results
4. **Delegate if needed**: Send to ultrathink-debugger with symbol context
5. **Implement fix**: Use specialist agent

---

## Decision Tree: Symbols vs Codebase Explorer

### Use Symbols When (150 tokens)

- ✓ Looking for function/class definitions
- ✓ Understanding module structure
- ✓ Tracing call paths between components
- ✓ Finding where a name is defined/imported
- ✓ Quick architectural overview
- ✓ Identifying dependencies

**Example**:
```bash
# Find where module is defined
grep -r "\"name\": \"module_name\"" ai/symbols-*.json

# Check if it's exported
grep -A5 "\"exports\"" ai/symbols-backend.json | grep "module_name"
```

### Use Codebase Explorer When (5,000-15,000 tokens)

- ✓ Symbols don't have the name you're searching for
- ✓ Need to see actual implementation logic
- ✓ Investigating string literals or config values
- ✓ Pattern discovery across multiple files
- ✓ Need file content for complex analysis
- ✓ New codebase where symbols don't exist yet

### Hybrid Approach (Most Efficient: 2,000-5,000 tokens)

1. Query symbols first → get file paths
2. Use codebase-explorer with targeted file list
3. Read only specific files needed

**Example**:
```bash
# Step 1: Query symbols for file paths
grep "CollectionManager" ai/symbols-backend.json | jq -r '.file_path'

# Step 2: Delegate to codebase-explorer with specific files
Task("codebase-explorer", "Analyze these files for validation logic:
     - skillmeat/core/collection/manager.py
     - skillmeat/api/app/schemas/collection.py")
```

---

## Bug Categories with Investigation Commands

### 1. Import/Module Errors

**Symptoms**: `ModuleNotFoundError`, `ImportError`, `AttributeError` on import

**Investigation Commands**:

```bash
# Find where module is defined
grep -r "\"name\": \"module_name\"" ai/symbols-*.json

# Check if it's exported
grep -A5 "\"exports\"" ai/symbols-backend.json | grep "module_name"

# Find all imports of this module
grep "\"imports\"" ai/symbols-*.json | grep "module_name"

# Check file structure
grep "\"file_path\".*module_name" ai/symbols-*.json
```

**Common Causes**:
- Module not exported in `__init__.py`
- Circular import dependency
- Incorrect import path
- Module renamed but imports not updated

**Delegation**: If complex → `codebase-explorer` with "Find all imports of X"

**Fix Agent**: `python-backend-engineer` (Sonnet)

---

### 2. Type Errors / Schema Mismatches

**Symptoms**: `ValidationError`, Pydantic errors, TypeScript type errors

**Investigation Commands**:

```bash
# Find schema definition
grep "class.*Schema" ai/symbols-backend.json | grep "SchemaName"

# Get full schema details
grep -B2 -A15 "\"name\": \"SchemaName\"" ai/symbols-backend.json

# Find where schema is used
grep "SchemaName" ai/symbols-backend.json | jq -r '.file_path' | sort -u

# Check field definitions
grep -A20 "\"name\": \"SchemaName\"" ai/symbols-backend.json | grep "\"fields\""
```

**Common Causes**:
- Required field missing from request
- Field type mismatch (str vs int)
- Optional field marked as required
- Field name doesn't match API contract
- Frontend/backend type mismatch

**Delegation**:
- Python schemas → `python-backend-engineer` (Sonnet)
- TypeScript types → `ui-engineer` (Sonnet)

---

### 3. API Endpoint Errors

**Symptoms**: 404, 422, 500 errors from FastAPI

**Investigation Commands**:

```bash
# Find router definition
grep "\"@app\\..*router\"" ai/symbols-backend.json | grep "/api/path"

# Find endpoint handler
grep -B5 -A15 "\"router\": \"/api/v1/endpoint\"" ai/symbols-backend.json

# Find schema used by endpoint
grep -A10 "\"router\": \"/api/v1/endpoint\"" ai/symbols-backend.json | grep "Schema"

# Check request/response models
grep "response_model" ai/symbols-backend.json | grep "endpoint"

# Find middleware or dependencies
grep "Depends" ai/symbols-backend.json | grep -A5 "endpoint"
```

**Common Causes**:

**404 Not Found**:
- Route not registered in server.py
- Incorrect URL prefix
- Path parameter mismatch

**422 Unprocessable Entity**:
- Request body validation failed
- Required field missing
- Field type mismatch
- Schema constraint violation

**500 Internal Server Error**:
- Unhandled exception in handler
- Database connection issue
- Missing dependency injection
- Manager/service layer error

**Delegation**: `python-backend-engineer` (Sonnet) for backend, check both router and schema

---

### 4. Database/ORM Errors

**Symptoms**: `IntegrityError`, `NoResultFound`, SQLAlchemy errors

**Investigation Commands**:

```bash
# Find model definition
grep "class.*Base" ai/symbols-backend.json | grep "ModelName"

# Check model fields and relationships
grep -A25 "\"name\": \"ModelName\"" ai/symbols-backend.json

# Find relationships
grep -A15 "\"name\": \"ModelName\"" ai/symbols-backend.json | grep "relationship"

# Find foreign keys
grep -A15 "\"name\": \"ModelName\"" ai/symbols-backend.json | grep "ForeignKey"

# Find repository methods
grep "Repository" ai/symbols-backend.json | grep "ModelName"
```

**Common Causes**:

**IntegrityError**:
- Foreign key constraint violation
- Unique constraint violation
- NOT NULL constraint violation
- Check constraint violation

**NoResultFound**:
- Query returned no results when one() used
- Record deleted but still referenced
- Incorrect filter condition

**Other SQLAlchemy Errors**:
- Detached instance (accessing relationship after session closed)
- Lazy loading outside session
- Concurrent modification conflict

**Delegation**: `python-backend-engineer` (Sonnet) for models and migrations

---

### 5. Frontend Component Errors

**Symptoms**: React errors, hooks errors, rendering issues, TypeScript errors

**Investigation Commands**:

```bash
# Find component definition
grep "\"name\": \"ComponentName\"" ai/symbols-frontend.json

# Get full component details
grep -B5 -A25 "\"name\": \"ComponentName\"" ai/symbols-frontend.json

# Check props interface
grep -A10 "ComponentNameProps" ai/symbols-frontend.json

# Find where component is used
grep "import.*ComponentName" ai/symbols-frontend.json

# Check hooks usage
grep -A20 "\"name\": \"ComponentName\"" ai/symbols-frontend.json | grep "use"

# Find event handlers
grep -A20 "\"name\": \"ComponentName\"" ai/symbols-frontend.json | grep "handle"
```

**Common Causes**:
- Incorrect prop types
- Missing required props
- Hook called conditionally
- Hook called outside component
- State update during render
- Missing dependency in useEffect
- Stale closure in callback

**Delegation**:
- Components → `ui-engineer-enhanced` (Sonnet)
- Hooks → `ui-engineer` (Sonnet)

---

### 6. ID vs Display Name Mismatch

**Symptoms**: 404/not found errors where traced value looks human-readable (spaces, capitals: "Default Collection" instead of "default")

**Investigation Commands**:

```bash
# Find where value was extracted from source
grep -r "\.name" ai/symbols-backend.json | grep -B5 "id"

# Check transformer/mapper functions
grep -A10 "def.*mapper\\|def.*transform" ai/symbols-backend.json
```

**Common Causes**:
- Mapper extracted `.name` instead of `.id`
- Display name passed to API expecting identifier
- Query parameter confusion (human-readable vs system ID)

**Quick Diagnostic**: If failing parameter has spaces or mixed case → probable display name used as identifier

**Fix Pattern**: Trace backwards from error to where value was first extracted. Replace `.name` with `.id` in mapper or caller.

**Delegation**: `python-backend-engineer` (Sonnet) or `ui-engineer` (Sonnet) depending on layer

---

### 7. State Management Issues

**Symptoms**: Stale data, incorrect updates, race conditions, cache issues

**Investigation Commands**:

```bash
# Find state hooks
grep "useState\\|useQuery\\|useMutation" ai/symbols-frontend.json

# Find React Query hooks
grep "useQuery" ai/symbols-frontend.json | grep -A10 "queryKey"

# Find mutation hooks
grep "useMutation" ai/symbols-frontend.json | grep -A10 "mutationFn"

# Find context providers
grep "createContext\\|Provider" ai/symbols-frontend.json

# Find cache invalidation
grep "invalidateQueries\\|setQueryData" ai/symbols-frontend.json
```

**Common Causes**:
- Query key not invalidated after mutation
- Optimistic update not rolled back on error
- Stale time too long
- Race condition between queries
- Context not properly provided
- Missing dependency causing stale closure

**Delegation**: `ui-engineer-enhanced` (Sonnet) for React Query, state patterns

---

## Agent Delegation by Bug Type

| Bug Category | Primary Agent | Model | Escalate To |
|-------------|---------------|-------|-------------|
| Import/Module | codebase-explorer | Haiku | ultrathink-debugger (Opus) |
| Python Type/Schema | python-backend-engineer | Sonnet | ultrathink-debugger (Opus) |
| TypeScript Type | ui-engineer | Sonnet | backend-typescript-architect (Opus) |
| API Endpoint | python-backend-engineer | Sonnet | ultrathink-debugger (Opus) |
| Database/ORM | python-backend-engineer | Sonnet | ultrathink-debugger (Opus) |
| ID vs Display Name | python-backend-engineer / ui-engineer | Sonnet | ultrathink-debugger (Opus) |
| React Component | ui-engineer-enhanced | Sonnet | ui-engineer (Opus) |
| State Management | ui-engineer-enhanced | Sonnet | ultrathink-debugger (Opus) |
| Complex/Multi-system | ultrathink-debugger | Opus | Opus orchestration |

---

## Delegation Patterns

### Simple Bugs (Single File, Clear Fix)

**Pattern**: Direct delegation with specific instructions

```text
Task("python-backend-engineer", "Fix SchemaName - make field_name optional.
     File: skillmeat/api/app/schemas/collection.py
     Change: field_name from required to optional (Type | None = None)
     Reason: field comes from URL path, not request body")
```

**When to Use**:
- Single file change
- Clear root cause from error message
- Straightforward fix (add None, change type, add import)
- No architectural impact

**Model**: Sonnet (cost-effective for well-scoped fixes)

---

### Complex Bugs (Multi-File, Unclear Root Cause)

**Pattern**: Delegate to debugger with symbol context

```text
Task("ultrathink-debugger", "Investigate 422 error on POST /api/v1/collections.

     Symptoms:
     - Error: 'list_id required but not provided'
     - Endpoint: POST /api/v1/collections/{collection_id}/items

     Stack trace:
     [paste relevant stack trace]

     Symbol context:
     - Router: skillmeat/api/app/routers/collections.py
     - Schema: skillmeat/api/app/schemas/list_item.py (ListItemCreate)
     - Found via: grep 'ListItemCreate' ai/symbols-backend.json

     Suspected files:
     - skillmeat/api/app/routers/collections.py (endpoint definition)
     - skillmeat/api/app/schemas/list_item.py (schema validation)

     Investigation needed:
     - Why is list_id required in schema when it comes from URL path?
     - Check if router passes list_id correctly
     - Verify schema matches API contract")
```

**When to Use**:
- Multi-file investigation needed
- Root cause unclear from error message
- Requires understanding data flow
- Potential architectural issue

**Model**: Opus (requires deep reasoning)

---

### Multi-System Bugs (Frontend + Backend)

**Pattern**: Opus orchestrates sequential investigation and fixes

```text
# Opus orchestrates:

1. Task("codebase-explorer", "Find API contract between frontend and backend.
        - Frontend: Find where POST /api/v1/collections is called
        - Backend: Find router definition and schema
        - Compare request/response types")

2. [Wait for results]

3. Task("python-backend-engineer", "Fix backend schema:
        File: skillmeat/api/app/schemas/collection.py
        Change: Make collection_id optional in CollectionUpdate
        Reason: Frontend sends only changed fields, not full object")

4. Task("ui-engineer", "Update frontend types:
        File: skillmeat/web/types/collection.ts
        Change: Update CollectionUpdateRequest to match backend schema
        Ensure all fields are optional except id")

5. [Commit changes]
```

**When to Use**:
- Bug spans multiple layers (frontend, backend, database)
- Type mismatch between systems
- API contract violation
- Requires coordinated changes

**Model**: Opus for orchestration, Sonnet for implementation tasks

---

## Context File Maintenance

### When Modified Files Are Referenced

After modifying a file, check if it's referenced by context files:

```bash
# Find context files referencing this file
grep -l "skillmeat/api/app/routers/collections.py" .claude/context/*.md
```

### Update Process

1. **Read context file**: Check if patterns/examples are still accurate
2. **Verify references**: Ensure file paths are still correct
3. **Update examples**: Fix function names, signatures if changed
4. **Update frontmatter**: Set `last_verified` to current date

**Example Frontmatter**:

```yaml
---
title: Backend API Patterns
references:
  - skillmeat/api/app/routers/collections.py
  - skillmeat/api/app/schemas/collection.py
last_verified: 2026-01-14
---
```

### When to Update Context

| Change Type | Action Required |
|------------|-----------------|
| File renamed/moved | Update `references:` paths |
| Function signatures changed | Update example code in context |
| Patterns changed | Edit context or regenerate |
| Major refactor | Mark for review, regenerate if needed |
| Minor bug fix | Usually no update needed |

---

## Best Practices

### 1. Always Start with Error Message

**Capture Full Error Output**:
- Error type and message
- Stack trace (if available)
- Request/response data (if API error)
- Line numbers and file paths
- Environment context (dev/prod, browser/server)

**Example Error Capture**:
```text
Error: ValidationError
Message: field required
Field: list_id
Location: body -> list_id
Type: value_error.missing
Request: POST /api/v1/collections/abc123/items
Body: {"name": "Item 1", "description": "Test"}
Stack:
  File "skillmeat/api/app/routers/collections.py", line 45, in create_item
  File "pydantic/main.py", line 342, in parse_obj
```

---

### 2. Use Symbols for Reconnaissance

**Before delegating, gather context**:

```bash
# What module is this in?
grep "ModuleName" ai/symbols-*.json

# What depends on this?
grep "import.*ModuleName" ai/symbols-*.json

# What does this export?
grep -A10 "\"exports\"" ai/symbols-*.json | grep -i "name"

# Get file paths for targeted exploration
grep "SchemaName" ai/symbols-backend.json | jq -r '.file_path' | sort -u
```

**Benefits**:
- Understand scope before deep dive
- Identify related files
- Provide targeted context to agents
- Save 96% tokens vs reading files

---

### 3. Provide Targeted Context to Agents

**Don't just say "fix the bug"**. Provide:

✅ **Good Delegation**:
```text
Task("python-backend-engineer", "Fix ListItemCreate schema validation error.

     File: skillmeat/api/app/schemas/list_item.py

     Problem: list_id is marked required but comes from URL path

     Change: Make list_id optional (int | None = None)

     Reason: Router extracts list_id from URL and injects it,
             not from request body

     Symbol context:
     - Schema: ListItemCreate in schemas/list_item.py
     - Router: POST /collections/{collection_id}/items in routers/collections.py
     - Found via: grep 'ListItemCreate' ai/symbols-backend.json")
```

❌ **Bad Delegation**:
```text
Task("python-backend-engineer", "Fix the validation error in the API")
```

---

### 4. Verify Fixes Don't Break Context

**After fix is implemented**:

1. Check if modified files are in context references
2. Update context if patterns changed
3. Update `last_verified` date
4. Ensure examples still match actual code

```bash
# Check context references
grep -l "skillmeat/api/app/schemas/collection.py" .claude/context/**/*.md

# If found, verify and update
# - Read context file
# - Check examples match new code
# - Update last_verified date
```

---

## Common Audit Blind Spots

### Enterprise-Only Repository Implementations

**Pattern**: Enterprise-specific features (workflows, memory items, BOM, git credentials) have implementations **only** in `skillmeat/cache/enterprise_repositories.py`. Searching only `skillmeat/core/repositories/` and `skillmeat/cache/repositories.py` will miss them entirely.

**Why it matters**: The v2 DTO migration discovered 5 ABCs missed by the original audit because `enterprise_repositories.py` was not searched. Any repository audit, refactoring, or DTO migration must check all three implementation layers:
1. `skillmeat/core/repositories/` - Local filesystem implementations
2. `skillmeat/cache/repositories.py` - SQLite-based cache implementations (local edition)
3. `skillmeat/cache/enterprise_repositories.py` - PostgreSQL-based implementations (enterprise edition)

**Search Recipe**:

```bash
# Find all enterprise-only repository classes
grep 'class Enterprise.*Repository' skillmeat/cache/enterprise_repositories.py

# Cross-reference against ABCs to find which are enterprise-only
grep 'class I.*Repository' skillmeat/core/interfaces/repositories.py

# Check for enterprise-only methods not in local implementations
diff <(grep 'def ' skillmeat/cache/repositories.py) \
     <(grep 'def ' skillmeat/cache/enterprise_repositories.py)

# Verify a specific ABC has implementations in all 3 layers
grep 'class IMemoryItemRepository' skillmeat/core/interfaces/repositories.py
grep 'class.*MemoryItemRepository' skillmeat/core/repositories/*.py
grep 'class.*MemoryItemRepository' skillmeat/cache/repositories.py
grep 'class.*MemoryItemRepository' skillmeat/cache/enterprise_repositories.py
```

**Impact Examples**:
- **DTO Migrations**: Must update serialization in both local and enterprise implementations
- **Repository Refactoring**: Changes to ABCs need updates in all 3 implementation files
- **Feature Additions**: New repository methods must be added to all implementations or marked edition-specific
- **Test Coverage**: Missing tests for enterprise-only repos can hide bugs that only surface in production

**Delegation**: When auditing repository changes, explicitly ask agents to check all three layers or risk incomplete implementations.

---

## Anti-Patterns

### ❌ Reading Multiple Files Without Checking Symbols First

```text
# BAD: Immediately reading 5 files
Read(skillmeat/api/app/routers/collections.py)
Read(skillmeat/api/app/schemas/collection.py)
Read(skillmeat/core/collection/manager.py)
# ... 15,000 tokens wasted
```

✅ **Use symbols first**:
```bash
# GOOD: Query symbols (150 tokens)
grep "CollectionManager" ai/symbols-backend.json
# Then read only needed files based on results
```

---

### ❌ Delegating with Vague Instructions

```text
# BAD
Task("python-backend-engineer", "investigate the error")
```

✅ **Provide specifics**:
```text
# GOOD
Task("python-backend-engineer", "Fix ListItemCreate schema.
     File: skillmeat/api/app/schemas/list_item.py
     Change: Make list_id optional
     Reason: Comes from URL path, not body")
```

---

### ❌ Fixing Bugs Without Updating Context Files

```text
# BAD: Edit file, commit, done
Edit(skillmeat/api/app/routers/collections.py, ...)
# Context file now has stale examples!
```

✅ **Check and update context**:
```bash
# GOOD
# 1. Make fix
# 2. Check context references
grep -l "routers/collections.py" .claude/context/*.md
# 3. Update context if needed
# 4. Update last_verified date
```

---

### ❌ Using Codebase Explorer for Simple Name Lookups

```text
# BAD: 5,000 tokens for simple lookup
Task("codebase-explorer", "Find where CollectionManager is defined")
```

✅ **Use grep on symbols**:
```bash
# GOOD: 150 tokens
grep "CollectionManager" ai/symbols-backend.json
```

---

### ❌ Opus Implementing Fixes Directly

```text
# BAD: Opus reading and editing files
Read(skillmeat/api/app/schemas/list_item.py)
Edit(skillmeat/api/app/schemas/list_item.py, ...)
# Expensive! Opus should delegate!
```

✅ **Opus delegates to specialist**:
```text
# GOOD: Opus orchestrates, specialist implements
Task("python-backend-engineer", "Fix schema...")
```

---

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `.claude/context/symbol-usage-guide.md` | Symbol query patterns and examples |
| `.claude/context/backend-api-patterns.md` | Backend architecture and patterns |
| `.claude/context/frontend-patterns.md` | Frontend architecture and patterns |
| `.claude/context/key-context/symbols-query-playbook.md` | Symbols-first query recipes |
| `CLAUDE.md` → Agent Delegation | Model selection and delegation patterns |
| `.claude/specs/script-usage/bug-automation-scripts.md` | Automated bug tracking workflows |

---

## Quick Reference Commands

```bash
# Find module definition
grep -r "\"name\": \"ModuleName\"" ai/symbols-*.json

# Find where module is imported
grep "import.*ModuleName" ai/symbols-*.json

# Find schema definition
grep "class.*Schema" ai/symbols-backend.json | grep "SchemaName"

# Find API endpoint
grep "\"@app\\..*router\"" ai/symbols-backend.json | grep "/api/path"

# Find component definition
grep "\"name\": \"ComponentName\"" ai/symbols-frontend.json

# Find hooks usage
grep "useState\\|useQuery\\|useMutation" ai/symbols-frontend.json

# Get file paths for targeted exploration
grep "TargetName" ai/symbols-*.json | jq -r '.file_path' | sort -u

# Check context file references
grep -l "path/to/file.py" .claude/context/**/*.md
```
