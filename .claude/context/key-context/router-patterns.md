---
title: FastAPI Router Patterns
description: Comprehensive reference for FastAPI router implementation patterns in SkillMeat
audience: backend-developers
category: api-patterns
tags:
  - fastapi
  - routers
  - api
  - http
  - backend
references:
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/routers/collections.py
  - skillmeat/api/routers/user_collections.py
  - skillmeat/api/routers/deployments.py
  - skillmeat/api/routers/projects.py
  - skillmeat/api/routers/analytics.py
  - skillmeat/api/routers/marketplace.py
  - skillmeat/api/routers/marketplace_sources.py
  - skillmeat/api/routers/mcp.py
  - skillmeat/api/routers/bundles.py
  - skillmeat/api/routers/groups.py
  - skillmeat/api/routers/cache.py
  - skillmeat/api/routers/health.py
  - skillmeat/api/routers/tags.py
  - skillmeat/api/routers/ratings.py
  - skillmeat/api/routers/versions.py
  - skillmeat/api/routers/match.py
  - skillmeat/api/routers/merge.py
  - skillmeat/api/routers/context_entities.py
  - skillmeat/api/routers/context_sync.py
  - skillmeat/api/routers/project_templates.py
last_verified: 2026-01-14
status: active
---

# FastAPI Router Patterns

Comprehensive reference for implementing FastAPI routers in SkillMeat's API layer.

## Table of Contents

- [Layer Contract](#layer-contract)
- [Layered Architecture](#layered-architecture)
- [Router Definition](#router-definition)
- [Available Routers](#available-routers)
- [HTTP Methods & Status Codes](#http-methods--status-codes)
- [HTTPException Patterns](#httpexception-patterns)
- [Response Models](#response-models)
- [Dependency Injection](#dependency-injection)
- [Request Parameters](#request-parameters)
- [OpenAPI Documentation](#openapi-documentation)
- [Best Practices](#best-practices)

---

## Layer Contract

### Routers SHOULD

- Define HTTP endpoints and route handlers
- Parse requests (path/query params, request body)
- Serialize responses (Pydantic models)
- Call service/manager layer for business logic
- Handle HTTP-specific concerns (status codes, headers)
- Document endpoints (OpenAPI tags, descriptions)

### Routers MUST NOT

- Access database directly (use service/manager layer)
- Implement business logic (delegate to core/)
- Validate complex domain rules (use service layer)
- Handle file I/O directly (use managers)
- Perform data transformations (use schemas/services)

---

## Layered Architecture

```
routers/ (HTTP layer)
    ↓ calls
managers/services (business logic)
    ↓ calls
repositories (data access)
    ↓ calls
database/filesystem
```

### Example Flow

```python
# Router → Manager → Repository
@router.post("/user-collections")
async def create_collection(
    request: UserCollectionCreateRequest,
    session: DbSessionDep,
) -> UserCollectionResponse:
    # 1. Parse request (router layer)
    collection_data = request.model_dump()

    # 2. Business logic (manager/service layer)
    collection = create_user_collection(session, collection_data)

    # 3. Serialize response (router layer)
    return UserCollectionResponse.model_validate(collection)
```

---

## Router Definition

### Structure

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/resource-name",      # e.g., "/user-collections"
    tags=["resource-name"],        # OpenAPI grouping
)
```

### Registration

**File**: `skillmeat/api/server.py`

```python
from skillmeat.api.routers import artifacts, collections, user_collections

# Health check (no prefix)
app.include_router(health.router)

# API routes (with prefix)
app.include_router(
    collections.router,
    prefix=settings.api_prefix,  # "/api/v1"
    tags=["collections"]
)
app.include_router(
    user_collections.router,
    prefix=settings.api_prefix,
    tags=["user-collections"]
)
```

---

## Available Routers

| Router | Prefix | Purpose | Layer Type |
|--------|--------|---------|------------|
| `health` | `/health` | Health checks | Simple |
| `artifacts` | `/api/v1/artifacts` | Artifact CRUD | Manager-based |
| `collections` | `/api/v1/collections` | Read-only file-based collections | Manager-based |
| `user_collections` | `/api/v1/user-collections` | Database CRUD collections | Database-backed |
| `deployments` | `/api/v1/deployments` | Deployment operations | Manager-based |
| `projects` | `/api/v1/projects` | Project registry | Manager-based |
| `analytics` | `/api/v1/analytics` | Usage analytics & telemetry ingestion | Manager-based |
| `marketplace` | `/api/v1/marketplace` | Claude marketplace | Manager-based |
| `marketplace_sources` | `/api/v1/marketplace-sources` | Marketplace source CRUD | Database-backed |
| `mcp` | `/api/v1/mcp` | MCP server management | Manager-based |
| `bundles` | `/api/v1/bundles` | Artifact bundles | Manager-based |
| `groups` | `/api/v1/groups` | Collection groups | Database-backed |
| `cache` | `/api/v1/cache` | Cache management | Manager-based |
| `tags` | `/api/v1/tags` | Tag management | Database-backed |
| `ratings` | `/api/v1/ratings` | Artifact ratings | Database-backed |
| `versions` | `/api/v1/versions` | Version management | Manager-based |
| `match` | `/api/v1/match` | Artifact matching | Manager-based |
| `merge` | `/api/v1/merge` | Merge operations | Manager-based |
| `context_entities` | `/api/v1/context-entities` | Context entity CRUD | Database-backed |
| `context_sync` | `/api/v1/context-sync` | Context synchronization | Manager-based |
| `project_templates` | `/api/v1/project-templates` | Project templates | Manager-based |

### Analytics Sub-Package Router Pattern

The `analytics/` sub-package uses a nested router pattern:
- **File**: `skillmeat/api/routers/analytics/` (package directory)
- **POST ingestion endpoints** live in `skillmeat/api/routers/analytics/ingestion.py`
- **Aggregation**: `skillmeat/api/routers/analytics/__init__.py` imports and aggregates sub-routers for registration in `server.py`

---

## HTTP Methods & Status Codes

### Standard Mappings

```python
# GET: Retrieve resource(s) → 200 OK
@router.get("/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(artifacts=artifacts)

# POST: Create resource → 201 Created
@router.post("/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(...) -> ArtifactResponse:
    artifact = manager.create_artifact(...)
    return ArtifactResponse.model_validate(artifact)

# PUT: Update resource → 200 OK
@router.put("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(...) -> ArtifactResponse:
    artifact = manager.update_artifact(...)
    return ArtifactResponse.model_validate(artifact)

# DELETE: Remove resource → 204 No Content
@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(...) -> None:
    manager.delete_artifact(artifact_id)
    return None  # or omit return statement
```

### Status Code Reference

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT requests |
| 201 | Created | Successful POST creating new resource |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Client sent malformed/invalid data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation failed (domain-specific) |
| 500 | Internal Server Error | Unexpected server failure |

---

## HTTPException Patterns

### Standard Error Codes

```python
from fastapi import HTTPException, status

# 400 Bad Request: Client sent invalid data
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid cursor format: must be base64-encoded"
)

# 404 Not Found: Resource doesn't exist
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Collection '{collection_id}' not found"
)

# 422 Unprocessable Entity: Validation failed
# (Automatically raised by Pydantic for schema validation)
# Only raise manually for domain-specific validation:
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Cannot add artifact: already exists in collection"
)

# 500 Internal Server Error: Unexpected failure
try:
    result = dangerous_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create collection: {str(e)}"
    )
```

### Error Response Schema

```python
from skillmeat.api.schemas.common import ErrorResponse

# All error responses follow ErrorResponse schema
class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: Optional[str] = None  # ErrorCodes enum
```

### Error Handling Pattern

```python
try:
    result = manager.dangerous_operation()
except ValueError as e:
    logger.warning(f"Validation error: {e}")
    raise HTTPException(400, detail=str(e))
except FileNotFoundError as e:
    logger.warning(f"Resource not found: {e}")
    raise HTTPException(404, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(500, detail="Internal server error")
```

---

## Response Models

### response_model Parameter

```python
# Explicit response model (recommended)
@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(...) -> ArtifactResponse:
    return ArtifactResponse(...)

# List response with pagination
@router.get("/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(
        items=[...],
        page_info=PageInfo(...)
    )

# No response body (204)
@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(...) -> None:
    return None
```

### Model Validation Patterns

```python
# From dict
return ArtifactResponse(**artifact_dict)

# From ORM model (SQLAlchemy)
return ArtifactResponse.model_validate(orm_object)

# From Pydantic model
return ArtifactResponse.model_validate(request_model)

# With configuration (exclude_unset, exclude_none)
return ArtifactResponse.model_validate(
    orm_object,
    from_attributes=True
)
```

---

## Dependency Injection

### Type Aliases with Annotated

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

# Database session
DbSessionDep = Annotated[Session, Depends(get_db_session)]

# Manager dependencies (from dependencies.py)
from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    ConfigManagerDep,
)

# Auth token
from skillmeat.api.middleware.auth import TokenDep
```

### Usage in Routes

```python
@router.get("/artifacts")
async def list_artifacts(
    # Manager dependency
    artifact_mgr: ArtifactManagerDep,
    # Database session
    session: DbSessionDep,
    # Auth token (optional)
    token: TokenDep = Depends(verify_api_key),
    # Query parameters
    artifact_type: Optional[str] = Query(None),
) -> ArtifactListResponse:
    artifacts = artifact_mgr.list_artifacts(artifact_type)
    return ArtifactListResponse(artifacts=artifacts)
```

### Database Session Dependency

```python
def get_db_session():
    """Get database session with proper cleanup.

    Yields:
        SQLAlchemy session instance

    Note:
        Session is automatically closed after request completes
    """
    session = get_session()  # from cache.models
    try:
        yield session
    finally:
        session.close()
```

### Common Dependency Patterns

```python
# Optional authentication
@router.get("/public")
async def public_endpoint(
    token: Optional[TokenDep] = None,  # Optional
) -> Response:
    ...

# Multiple managers
@router.post("/complex-operation")
async def complex_op(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    deploy_mgr: DeploymentManagerDep,
) -> Response:
    ...

# Combination of dependencies
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_mgr: ArtifactManagerDep,
    session: DbSessionDep,
    token: TokenDep,
) -> ArtifactResponse:
    ...
```

---

## Request Parameters

### Path Parameters

```python
from fastapi import Path

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str = Path(..., description="Artifact identifier"),
) -> ArtifactResponse:
    ...

# With validation
@router.get("/collections/{collection_id}")
async def get_collection(
    collection_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        description="Collection ID"
    ),
) -> CollectionResponse:
    ...
```

### Query Parameters

```python
from fastapi import Query

@router.get("/artifacts")
async def list_artifacts(
    # Optional filter
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    # Search
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    # Boolean flags
    include_archived: bool = Query(False, description="Include archived items"),
) -> ArtifactListResponse:
    ...
```

### Request Body

```python
from fastapi import Body

@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,  # Pydantic model
    # OR with Body() for additional validation
    request: ArtifactCreateRequest = Body(..., description="Artifact data"),
) -> ArtifactCreateResponse:
    ...

# Multiple body parameters (rare)
@router.post("/complex")
async def complex_op(
    data: DataModel = Body(...),
    metadata: MetadataModel = Body(...),
) -> Response:
    ...
```

---

## OpenAPI Documentation

### Tags and Descriptions

```python
@router.get(
    "/artifacts",
    summary="List all artifacts",
    description="Retrieve paginated list of artifacts with optional filtering",
    response_description="List of artifacts with pagination info",
    tags=["artifacts"],  # Override router-level tag if needed
)
async def list_artifacts(...):
    ...
```

### Response Examples

```python
@router.get(
    "/artifacts/{artifact_id}",
    responses={
        200: {
            "description": "Artifact found",
            "content": {
                "application/json": {
                    "example": {
                        "id": "abc123",
                        "name": "canvas-design",
                        "type": "skill",
                    }
                }
            }
        },
        404: {
            "description": "Artifact not found",
            "model": ErrorResponse,
        }
    }
)
async def get_artifact(...):
    ...
```

### Deprecation

```python
@router.get(
    "/old-endpoint",
    deprecated=True,
    summary="Legacy endpoint (deprecated)",
    description="Use /new-endpoint instead. Will be removed in v2.0.0"
)
async def old_endpoint(...):
    ...
```

---

## Best Practices

### Async Handlers

All route handlers should be async for consistency:

```python
# ✓ Good
@router.get("/artifacts")
async def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(...)

# ✗ Avoid (use async even if not awaiting)
@router.get("/artifacts")
def list_artifacts(...) -> ArtifactListResponse:
    return ArtifactListResponse(...)
```

### Error Logging

Always log before raising exceptions:

```python
try:
    result = manager.dangerous_operation()
except ValueError as e:
    logger.warning(f"Validation error: {e}")
    raise HTTPException(400, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(500, detail="Internal server error")
```

### Separation of Concerns

```python
# ✓ Good: Router delegates to manager
@router.post("/collections")
async def create_collection(
    request: CollectionCreateRequest,
    manager: CollectionManagerDep,
) -> CollectionResponse:
    collection = manager.create_collection(request.model_dump())
    return CollectionResponse.model_validate(collection)

# ✗ Bad: Router implements business logic
@router.post("/collections")
async def create_collection(request: CollectionCreateRequest) -> CollectionResponse:
    # Don't do validation, file I/O, etc. in router
    path = Path(request.path)
    path.mkdir(parents=True, exist_ok=True)
    manifest = {"name": request.name}
    (path / "manifest.toml").write_text(toml.dumps(manifest))
    ...
```

### Type Hints

Always use explicit type hints for clarity and OpenAPI generation:

```python
# ✓ Good
async def get_artifact(
    artifact_id: str,
    manager: ArtifactManagerDep,
) -> ArtifactResponse:
    ...

# ✗ Bad
async def get_artifact(artifact_id, manager):
    ...
```

### Consistent Return Types

```python
# ✓ Good: Explicit return type
@router.get("/artifacts/{artifact_id}")
async def get_artifact(...) -> ArtifactResponse:
    artifact = manager.get_artifact(artifact_id)
    return ArtifactResponse.model_validate(artifact)

# ✗ Bad: Inconsistent returns
@router.get("/artifacts/{artifact_id}")
async def get_artifact(...):
    artifact = manager.get_artifact(artifact_id)
    if artifact:
        return artifact  # Raw object
    return {"error": "Not found"}  # Dict
```

### Validation Location

```python
# ✓ Good: Schema validation via Pydantic
class ArtifactCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: ArtifactType
    description: Optional[str] = None

@router.post("/artifacts")
async def create_artifact(request: ArtifactCreateRequest) -> ArtifactResponse:
    # Schema validation already done by Pydantic
    return manager.create_artifact(request.model_dump())

# ✗ Bad: Manual validation in router
@router.post("/artifacts")
async def create_artifact(request: dict) -> ArtifactResponse:
    if not request.get("name"):
        raise HTTPException(400, "Name required")
    if len(request["name"]) > 100:
        raise HTTPException(400, "Name too long")
    ...
```

---

## Anti-Patterns to Avoid

### Direct Database Access

```python
# ✗ Bad: Router accesses database directly
@router.get("/collections")
async def list_collections(session: DbSessionDep):
    collections = session.query(Collection).all()
    return collections

# ✓ Good: Router delegates to manager
@router.get("/collections")
async def list_collections(manager: CollectionManagerDep):
    return manager.list_collections()
```

### Business Logic in Router

```python
# ✗ Bad: Complex logic in router
@router.post("/deploy")
async def deploy_artifact(request: DeployRequest):
    # Complex deployment logic here...
    if not Path(request.target).exists():
        Path(request.target).mkdir(parents=True)
    # More logic...

# ✓ Good: Delegate to manager
@router.post("/deploy")
async def deploy_artifact(
    request: DeployRequest,
    manager: DeploymentManagerDep,
):
    return manager.deploy(request.model_dump())
```

### Missing Error Handling

```python
# ✗ Bad: No error handling
@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, manager: ArtifactManagerDep):
    return manager.get_artifact(artifact_id)  # Might raise!

# ✓ Good: Proper error handling
@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, manager: ArtifactManagerDep):
    try:
        artifact = manager.get_artifact(artifact_id)
        return ArtifactResponse.model_validate(artifact)
    except FileNotFoundError:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")
    except Exception as e:
        logger.exception(f"Failed to get artifact: {e}")
        raise HTTPException(500, "Internal server error")
```

---

## Enterprise Dual-Mode Handler Pattern

The dual-mode handler pattern enables endpoints to serve both local (filesystem-based) and enterprise (database-backed) editions from a single codebase branch. Handlers check the edition at entry and branch to separate code paths with appropriately typed dependencies.

### Pattern Overview

**Branch Condition**: Always `if settings.edition == "enterprise":` at the top of the handler.

**Enterprise Path**: Uses `*RepoDep` dependencies (repository layer directly).
- Never accesses `*ManagerDep` or `*ManagerOptDep` in the enterprise branch
- All data access goes through repositories, not managers

**Local Path**: Uses `*ManagerDep` or `*ManagerOptDep` dependencies (unchanged behavior).
- Operates on filesystem-based collections
- No database writes in local mode

**Response Schemas**: Must be identical between enterprise and local paths.

### Copy-Paste-Ready Example

```python
from fastapi import APIRouter, HTTPException
from skillmeat.api.dependencies import (
    SettingsDep,
    ArtifactRepoDep,
    CollectionRepoDep,
    DbSessionDep,
    ArtifactManagerOptDep,
    CollectionManagerOptDep,
)
from skillmeat.api.schemas.artifacts import ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    settings: SettingsDep,
    artifact_repo: ArtifactRepoDep,
    collection_repo: CollectionRepoDep,
    db_session: DbSessionDep,
    artifact_mgr: ArtifactManagerOptDep,
    collection_mgr: CollectionManagerOptDep,
) -> ArtifactResponse:
    """Get a single artifact."""
    if settings.edition == "enterprise":
        # Enterprise path: use repositories
        artifact = artifact_repo.get_by_id(artifact_id, db_session)
        if not artifact:
            raise HTTPException(404, detail=f"Artifact '{artifact_id}' not found")
        return ArtifactResponse.model_validate(artifact)

    # Local path: use managers
    assert artifact_mgr is not None
    assert collection_mgr is not None
    artifact = artifact_mgr.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(404, detail=f"Artifact '{artifact_id}' not found")
    return ArtifactResponse.model_validate(artifact)
```

### Optional Dependency Pattern

Use `*OptDep` type aliases for dependencies that may be `None` in enterprise mode:

- `ArtifactManagerOptDep` → Returns `None` in enterprise, manager instance in local
- `CollectionManagerOptDep` → Returns `None` in enterprise, manager instance in local
- `SyncManagerOptDep` → Returns `None` in enterprise, manager instance in local
- `ContextSyncServiceOptDep` → Returns `None` in enterprise, service instance in local

**Always assert before use in local path**:

```python
assert artifact_mgr is not None  # Type narrowing for type checker
```

### Intentional 501 Pattern (Filesystem-Only Endpoints)

For endpoints that require filesystem access and cannot be implemented in enterprise:

```python
from fastapi import status

@router.post("/artifacts/{artifact_id}/sync-from-source")
async def sync_from_source(
    artifact_id: str,
    settings: SettingsDep,
    sync_mgr: SyncManagerOptDep,
) -> SyncResponse:
    """Synchronize artifact from upstream source (local mode only)."""
    if settings.edition == "enterprise":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Synchronization requires filesystem access and is not available in enterprise edition.",
        )

    assert sync_mgr is not None
    result = sync_mgr.sync_from_source(artifact_id)
    return SyncResponse.model_validate(result)
```

**Note**: Use 501 (Not Implemented) only for features that are intentionally gated by edition. For features that work in both modes, implement both paths in the handler.

### Sub-Module Assembly Pattern

When routers are organized in sub-packages (e.g., `artifacts/`), assemble them in `__init__.py`:

```python
# skillmeat/api/routers/artifacts/__init__.py
from fastapi import APIRouter

from . import artifacts_core, artifacts_sync, artifacts_merge

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

# Track migrated endpoints to filter legacy ones
_MIGRATED = frozenset({
    "get_artifact",
    "list_artifacts",
    "create_artifact",
    "update_artifact",
    "delete_artifact",
    # ... etc
})

# Include dual-mode sub-routers
router.include_router(artifacts_core.router)
router.include_router(artifacts_sync.router)
router.include_router(artifacts_merge.router)
```

Each sub-module defines its own router with `prefix=""` (inherited from parent) and implements dual-mode handlers independently.

### Key Invariants

1. **Enterprise paths never access local managers** — If you use `artifact_mgr` or similar in the enterprise branch, you have a bug.
2. **Edition check is the sole condition** — Do not use other conditions to branch (e.g., `if has_db_support():` is wrong).
3. **Response schemas must match** — Both paths return the same `ArtifactResponse` (or other schema).
4. **Use 501 only for intentional gates** — Never use 500 or other codes to indicate edition incompatibility.
5. **Assert after edition check** — Type narrowing with `assert mgr is not None` tells type checkers the dependency is available in the local path.

---

## Reference

- **Layer Patterns**: `skillmeat/api/routers/CLAUDE.md`
- **Schema Patterns**: `.claude/context/key-context/schema-patterns.md`
- **Dependency Injection**: `skillmeat/api/dependencies.py`
- **Error Handling**: `skillmeat/api/schemas/common.py`
- **FastAPI Docs**: https://fastapi.tiangolo.com/
