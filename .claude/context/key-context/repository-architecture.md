# Repository Architecture (Hexagonal Pattern)

**Status**: Active Policy
**Phase**: Complete (enterprise parity v2 done)
**Last Updated**: 2026-03-12

---

## Overview

SkillMeat uses **hexagonal architecture** (ports & adapters) with abstract repository interfaces sitting between API routers and all storage backends. This design:

- **Decouples** the API layer from filesystem/SQLite implementation details
- **Enables** multi-backend support (PostgreSQL, S3, cloud stores) in the future
- **Simplifies** testing via mock repositories
- **Enforces** contracts through abstract base classes (ABCs)

The pattern flows:

```
HTTP Request
    ↓
Router (skillmeat/api/routers/*)
    ↓
Repository Dependency (via Annotated + Depends)
    ↓
Repository Implementation (skillmeat/core/repositories/local_*)
    ↓
Filesystem / SQLAlchemy ORM / External Storage
```

---

## Core Invariants (MUST Follow)

**Schema Note** (enterprise-dvcs-remediation-v2 Phase 1): `ProjectVersionDeployment` now carries four Fork-1 columns (nullable for legacy rows): `version_id` (FK to `artifact_versions.id`), `deployment_target`, `tenant_id` (enterprise only), and `actor_id` (FK to `users.id`). Atomic path recording is the canonical form; no `hasattr` guards on persistence columns are permitted.

### Invariant 1: New Endpoints Use Repository DI

**Rule**: Every new API endpoint MUST use repository dependency injection. No direct `os`, `pathlib`, or `sqlite3` imports in routers.

**Violation Example** (WRONG):
```python
# skillmeat/api/routers/artifacts.py
import os
from pathlib import Path

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    # WRONG: Direct filesystem access in router
    artifact_path = Path.home() / ".skillmeat" / artifact_id
    if artifact_path.exists():
        return {"content": artifact_path.read_text()}
    raise HTTPException(404, "Not found")
```

**Correct Example** (RIGHT):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.api.dependencies import ArtifactRepoDep

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    artifact_repo: ArtifactRepoDep,  # Injected by FastAPI
):
    artifact_dto = artifact_repo.get(artifact_id)
    if not artifact_dto:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")
    return ArtifactResponse.from_dto(artifact_dto)
```

### Invariant 2: Storage Access via Repository Abstraction

**Rule**: All storage access in routers goes through `Annotated[I*Repository, Depends(get_*_repository)]` dependency parameters.

**Syntax**:
```python
from skillmeat.api.dependencies import (
    ArtifactRepoDep,           # Annotated[IArtifactRepository, Depends(...)]
    ProjectRepoDep,            # Annotated[IProjectRepository, Depends(...)]
    CollectionRepoDep,         # Annotated[ICollectionRepository, Depends(...)]
    DeploymentRepoDep,         # Annotated[IDeploymentRepository, Depends(...)]
    TagRepoDep,                # Annotated[ITagRepository, Depends(...)]
    SettingsRepoDep,           # Annotated[ISettingsRepository, Depends(...)]
    GroupRepoDep,              # Annotated[IGroupRepository, Depends(...)]
    ContextEntityRepoDep,      # Annotated[IContextEntityRepository, Depends(...)]
    MarketplaceSourceRepoDep,  # Annotated[IMarketplaceSourceRepository, Depends(...)]
    ProjectTemplateRepoDep,    # Annotated[IProjectTemplateRepository, Depends(...)]
)

@router.get("/artifacts")
async def list_artifacts(artifact_repo: ArtifactRepoDep) -> List[ArtifactResponse]:
    artifacts = artifact_repo.list()
    return [ArtifactResponse.from_dto(a) for a in artifacts]
```

### Invariant 3: DTOs as Data Contract

**Rule**: DTOs from `skillmeat.core.interfaces.dtos` are the API layer's data contract. Never pass ORM models (SQLAlchemy) or filesystem objects to routers.

**Why**: DTOs enforce a stable boundary between the core and infrastructure. If ORM models leak into routers, future storage backend changes require router rewrites.

**Violation Example** (WRONG):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.cache.models import CollectionArtifact  # ORM model

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    orm_model = db.query(CollectionArtifact).filter(...).first()
    return ArtifactResponse.from_orm(orm_model)  # Leaks ORM into router
```

**Correct Example** (RIGHT):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.core.interfaces.dtos import ArtifactDTO

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, artifact_repo: ArtifactRepoDep):
    artifact_dto: ArtifactDTO | None = artifact_repo.get(artifact_id)
    if not artifact_dto:
        raise HTTPException(404)
    return ArtifactResponse.from_dto(artifact_dto)
```

### Invariant 4: Write-Through Pattern

**Rule**: Mutations write filesystem first, then sync to DB via `refresh_single_artifact_cache()`.

**Pattern**:
```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_repo: ArtifactRepoDep,
):
    # 1. Repository writes to filesystem (via artifact_manager)
    artifact_dto = artifact_repo.create(
        name=request.name,
        artifact_type=request.artifact_type,
        ...
    )

    # 2. Sync DB cache (in service layer or router)
    from skillmeat.cache.refresh import refresh_single_artifact_cache
    refresh_single_artifact_cache(artifact_dto.id)

    # 3. Return to client
    return ArtifactResponse.from_dto(artifact_dto), 201
```

See root `CLAUDE.md` → "Data Flow Principles" for full write-through semantics.

### Invariant 5: Mock Updates

**Rule**: When you change an ABC in `skillmeat/core/interfaces/repositories.py`, update the corresponding mock in `tests/mocks/repositories.py`.

**Pattern**:
```python
# If you add a method to IArtifactRepository:
class IArtifactRepository(abc.ABC):
    @abc.abstractmethod
    def search_by_tag(self, tag: str) -> List[ArtifactDTO]:
        raise NotImplementedError

# Then add the mock:
class MockArtifactRepository(IArtifactRepository):
    def search_by_tag(self, tag: str) -> List[ArtifactDTO]:
        return [a for a in self._artifacts.values() if tag in a.tags]
```

---

## Module Map

### 1. Interfaces Layer
**Location**: `skillmeat/core/interfaces/`

| File | Purpose |
|------|---------|
| `repositories.py` | 10 ABC interfaces: `IArtifactRepository`, `IProjectRepository`, `ICollectionRepository`, `IDeploymentRepository`, `ITagRepository`, `ISettingsRepository`, `IGroupRepository`, `IContextEntityRepository`, `IMarketplaceSourceRepository`, `IProjectTemplateRepository` |
| `dtos.py` | 16 frozen dataclasses: `ArtifactDTO`, `ProjectDTO`, `CollectionDTO`, `DeploymentDTO`, `TagDTO`, `SettingsDTO`, `CollectionMembershipDTO`, `EntityTypeConfigDTO`, `CategoryDTO`, `GroupDTO`, `GroupArtifactDTO`, `ContextEntityDTO`, `MarketplaceSourceDTO`, `CatalogItemDTO`, `ProjectTemplateDTO`, `TemplateEntityDTO` |
| `context.py` | RequestContext (per-request metadata: auth, tracing, etc.) |
| `__init__.py` | Public exports |

**Key Constraint**: No imports from other skillmeat modules except `skillmeat.core.enums` and `skillmeat.core.exceptions`.

### 2. Repository Implementations

**Location**: `skillmeat/core/repositories/`

#### Local Repositories (Filesystem-Backed)

| File | Implements | Backing Store |
|------|-----------|----------------|
| `local_artifact.py` | IArtifactRepository | Filesystem + SQLAlchemy cache |
| `local_project.py` | IProjectRepository | Filesystem + SQLAlchemy cache |
| `local_collection.py` | ICollectionRepository | Filesystem (CollectionManager) |
| `local_deployment.py` | IDeploymentRepository | Filesystem + SQLAlchemy cache |
| `local_tag.py` | ITagRepository | SQLAlchemy cache only |
| `local_settings_repo.py` | ISettingsRepository | TOML files + SQLAlchemy cache |
| `local_group.py` | IGroupRepository | SQLAlchemy cache only |
| `local_context_entity.py` | IContextEntityRepository | SQLAlchemy cache only |
| `local_marketplace_source.py` | IMarketplaceSourceRepository | SQLAlchemy cache only |
| `local_project_template.py` | IProjectTemplateRepository | SQLAlchemy cache only |

Each local implementation:
- Receives **managers** (ArtifactManager, CollectionManager, etc.) via constructor DI
- Receives **PathResolver** for filesystem navigation
- Returns DTOs, never ORM models
- Delegates to managers for complex logic (filesystem I/O, artifact parsing, etc.)

#### Enterprise Repositories (PostgreSQL-Backed)

| File | Implements | Pattern |
|------|-----------|---------|
| `enterprise_artifact.py` | IArtifactRepository | Tenant-filtered SELECT + DI-injected session |
| `enterprise_branch.py` | IBranchRepository | Full CRUD with tenant-scoped joins on versions (Wave 3B) |
| `enterprise_collection.py` | ICollectionRepository | Tenant-filtered SELECT + multi-table scans |
| `enterprise_deployment.py` | IDeploymentRepository | Stub (returns empty list, no-op mutations) |
| `enterprise_tag.py` | ITagRepository | Tenant-filtered SELECT + DI-injected session |
| `enterprise_group.py` | IGroupRepository | Tenant-filtered SELECT + child collection validation |
| `enterprise_context_entity.py` | IContextEntityRepository | Stub (no-op) |
| `enterprise_marketplace_source.py` | IMarketplaceSourceRepository | Full CRUD (`create`, `delete`, `list_all`, `get_by_repo_url`) |
| `enterprise_project_template.py` | IProjectTemplateRepository | Full CRUD (`create`, `delete`, `list_all`, `get_by_repo_url`) |
| `enterprise_project.py` | IProjectRepository | Stub (returns empty) |
| `enterprise_settings.py` | ISettingsRepository | Stub (returns empty dict, no-op writes) |
| `enterprise_workflow.py` | IWorkflowRepository | Full CRUD (Phase 3) |
| `enterprise_memory_item.py` | IMemoryItemRepository | Full CRUD (Phase 3) |
| `enterprise_bundle.py` | IBundleRepository | Full CRUD (Phase 3) |
| `enterprise_bom.py` | IBomRepository | Full CRUD (Phase 3) |
| `enterprise_context_category.py` | IContextCategoryRepository | Stub (Phase 5) |
| `enterprise_audit_history.py` | IAuditHistoryRepository | Stub (Phase 5) |

**Enterprise Pattern**: All enterprise repos:
- Receive **SQLAlchemy Session** via DI (vs managers for local)
- Use SQLAlchemy 2.x `select()` style (not 1.x `session.query()`)
- Inherit from `EnterpriseRepositoryBase` for tenant filtering
- UUID primary keys and `EnterpriseBase` declarative base
- Use `flush()` never `commit()` — caller manages transactions
- Implement stub (empty) methods for repos without enterprise storage (deployment, projects, settings, etc.)

### 3. EnterpriseRepositoryBase — Tenant Isolation Pattern

**Location**: `skillmeat/core/repositories/enterprise_base.py`

All enterprise repositories inherit from `EnterpriseRepositoryBase`, which enforces tenant isolation across all SELECT queries.

#### Core Methods

```python
class EnterpriseRepositoryBase:
    def _get_tenant_id(self) -> UUID:
        """Resolve tenant_id from TenantContext ContextVar."""
        return get_tenant_id()  # Raises if not in enterprise context

    def _tenant_select(self, model: Type[T]) -> Select[tuple[T]]:
        """Return a select() pre-filtered by tenant_id."""
        return select(model).where(model.tenant_id == self._get_tenant_id())

    def _apply_tenant_filter(self, stmt: Select) -> Select:
        """Apply tenant_id filter to an existing select statement."""
        return stmt.where(stmt.model.tenant_id == self._get_tenant_id())

    def _validate_collection_tenant(self, collection_id: UUID) -> UUID:
        """Verify that a collection belongs to the current tenant.

        Used for join tables without tenant_id column (e.g., EnterpriseCollectionArtifact).
        Queries the parent EnterpriseCollection and asserts it belongs to the tenant.
        Raises NotFoundError if collection not found or belongs to different tenant.
        """
        # Implementation queries EnterpriseCollection by (id, tenant_id)
```

#### Tenant Isolation Invariant

**CRITICAL**: Every SELECT must filter by tenant. Failure to apply `_tenant_select()` or `_apply_tenant_filter()` will leak data across tenants.

**Correct Example**:
```python
def get(self, id: UUID) -> ArtifactDTO | None:
    stmt = self._tenant_select(EnterpriseArtifact).where(
        EnterpriseArtifact.id == id
    )
    result = self.session.execute(stmt).scalar_one_or_none()
    return self._to_dto(result) if result else None
```

**Wrong Example** (SECURITY BUG):
```python
def get(self, id: UUID) -> ArtifactDTO | None:
    # WRONG: No tenant filter — returns artifacts from ANY tenant!
    result = self.session.get(EnterpriseArtifact, id)
    return self._to_dto(result) if result else None
```

#### Membership-Aware Query Filters

Enterprise repositories often filter results by team membership. Use helpers from `skillmeat/core/repositories/filters.py` to enforce visibility based on team access:

```python
from skillmeat.core.repositories.filters import apply_membership_visibility_filter_stmt

# In enterprise repository list() method
stmt = apply_membership_visibility_filter_stmt(
    stmt,
    user_id=auth_context.user_id,
    membership_repo=self.membership_repo,  # IMembershipRepository
)
```

**Membership Repository** (`skillmeat/core/interfaces/repositories.py`):
- `is_team_member(team_id, user_id)` — check team membership
- `get_user_team_ids(user_id)` — get all teams user belongs to

Implementations: `LocalMembershipRepository` (SQLite), `EnterpriseMembershipRepository` (PostgreSQL, tenant-filtered).

### Enterprise CAS Blob Repository

The `ArtifactBlobsRepository` in `skillmeat/cache/enterprise_repositories.py` is the canonical example of enterprise-only repository patterns:

- **UUID PKs**: Enterprise repos use `uuid.UUID` primary keys (not `int`)
- **SQLAlchemy 2.x style**: `select()`, `mapped_column()` — no 1.x `session.query()` or `Column()`
- **Idempotent upsert**: `upsert_blob()` uses `INSERT ... ON CONFLICT DO UPDATE` via SQLAlchemy
- **Ref-counting**: `increment_ref_count()` / `decrement_ref_count()` for GC eligibility tracking
- **Service coupling**: `EnterpriseFileContentService` in `skillmeat/core/services/enterprise_file_content.py` owns the business logic; repository is pure data access

#### Join Tables Without tenant_id

When a join table lacks a `tenant_id` column (e.g., `EnterpriseCollectionArtifact` bridges `EnterpriseCollection` + `EnterpriseArtifact`), use `_validate_collection_tenant()` to verify ownership through the parent:

```python
def add_artifact_to_collection(self, collection_id: UUID, artifact_id: UUID):
    # Verify collection belongs to current tenant
    self._validate_collection_tenant(collection_id)

    # Now safe to add artifact (artifact already validated elsewhere)
    link = EnterpriseCollectionArtifact(
        collection_id=collection_id,
        artifact_id=artifact_id
    )
    self.session.add(link)
    self.session.flush()
```

#### Session Management

- **Always use `flush()`** for intermediate commits — caller manages transaction
- **Never use `commit()`** — transactions are managed at router level
- Return **DTOs**, never ORM models (same as local repos)

**Transaction boundary**:
```python
# In router
async def create_artifact(request, artifact_repo: ArtifactRepoDep, db: SessionDep):
    try:
        dto = artifact_repo.create(...)  # Uses session.flush()
        db.commit()                       # Router commits
        return dto
    except Exception:
        db.rollback()
        raise
```

### 4. Dependency Injection Factory
**Location**: `skillmeat/api/dependencies.py`

| Function | Returns | DI Alias |
|----------|---------|----------|
| `get_artifact_repository()` | IArtifactRepository | `ArtifactRepoDep` |
| `get_project_repository()` | IProjectRepository | `ProjectRepoDep` |
| `get_collection_repository()` | ICollectionRepository | `CollectionRepoDep` |
| `get_deployment_repository()` | IDeploymentRepository | `DeploymentRepoDep` |
| `get_tag_repository()` | ITagRepository | `TagRepoDep` |
| `get_settings_repository()` | ISettingsRepository | `SettingsRepoDep` |
| `get_group_repository()` | IGroupRepository | `GroupRepoDep` |
| `get_context_entity_repository()` | IContextEntityRepository | `ContextEntityRepoDep` |
| `get_marketplace_source_repository()` | IMarketplaceSourceRepository | `MarketplaceSourceRepoDep` |
| `get_project_template_repository()` | IProjectTemplateRepository | `ProjectTemplateRepoDep` |

**Edition-Based Routing** (Active):

All factory functions follow the same pattern:

```python
def get_artifact_repository(
    state: AppState,
    session: SessionDep,  # For enterprise
) -> IArtifactRepository:
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return LocalArtifactRepository(
            artifact_manager=state.artifact_manager,
            path_resolver=state.path_resolver,
        )
    elif edition == "enterprise":
        return EnterpriseArtifactRepository(session=session)
    else:
        raise HTTPException(503, f"Unsupported edition: {edition}")
```

**Available Editions**:
- `"local"` (default): Single-tenant, filesystem-backed (Local* repos)
- `"enterprise"`: Multi-tenant, PostgreSQL-backed (Enterprise* repos, DI-injected session)

Set via `SKILLMEAT_EDITION=enterprise` env var or `settings.edition` config field.

### Edition-Based DI Routing (Phase 2)

Three repositories updated to route by `APISettings.edition` (not by `tenant_id` presence):
- `IMembershipRepository` — `LocalMembershipRepository` (SQLite) vs `EnterpriseMembershipRepository` (PostgreSQL, tenant-filtered)
- `IFavoritesRepository` — routes similarly
- `ISelectionRepository` — routes similarly

**Pattern** (in `dependencies.py`):
```python
def get_membership_repository(state: AppState, session: SessionDep) -> IMembershipRepository:
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return LocalMembershipRepository(session=state.db_session)
    elif edition == "enterprise":
        return EnterpriseMembershipRepository(session=session)
    else:
        raise HTTPException(503, f"Unsupported edition: {edition}")
```

### Startup Guard (Phase 2)

Application startup performs edition/auth-provider alignment check in `skillmeat/api/startup_checks.py`:

**Guard logic**:
```python
if settings.edition == "enterprise" and not settings.auth_enabled:
    raise RuntimeError(
        "Enterprise edition requires auth_enabled=True. "
        "Set SKILLMEAT_AUTH_ENABLED=true or SKILLMEAT_ENTERPRISE_DEV_ALLOW_LOCAL_AUTH=true (dev-only override)."
    )
```

**Raises `RuntimeError` if**:
- Edition is `enterprise` AND
- `auth_enabled=False` AND
- Developer override env var `SKILLMEAT_ENTERPRISE_DEV_ALLOW_LOCAL_AUTH` is not set to `true`

**Rationale**: Enterprise deployments cannot launch without authentication enabled; the guard prevents misconfiguration.

**Code location**: `skillmeat/api/startup_checks.py`, wired into lifespan event handler in `skillmeat/api/server.py`

#### DI Recipe: IProjectGitConnectionRepository

**Task**: Inject project-to-git-connection repository with edition-aware routing.

**Location**: `skillmeat/api/dependencies.py`

```python
from skillmeat.core.interfaces.repositories import IProjectGitConnectionRepository
from skillmeat.cache.repositories import LocalProjectGitConnectionRepository
from skillmeat.cache.enterprise_repositories import EnterpriseProjectGitConnectionRepository
from skillmeat.api.config import APISettings
from typing import Annotated

def get_project_git_connection_repository(
    state: AppState,
    session: SessionDep,  # For enterprise
) -> IProjectGitConnectionRepository:
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return LocalProjectGitConnectionRepository(
            path_resolver=state.path_resolver,
            session=state.db_session,
        )
    elif edition == "enterprise":
        return EnterpriseProjectGitConnectionRepository(session=session)
    else:
        raise HTTPException(503, f"Unsupported edition: {edition}")

# Create DI alias
ProjectGitConnectionRepoDep = Annotated[
    IProjectGitConnectionRepository,
    Depends(get_project_git_connection_repository)
]
```

**Usage in Router**:
```python
# skillmeat/api/routers/projects.py
from skillmeat.api.dependencies import ProjectGitConnectionRepoDep

@router.get("/{project_id}/git-connections")
async def list_project_git_connections(
    project_id: str,
    proj_git_conn_repo: ProjectGitConnectionRepoDep,
) -> List[GitConnectionResponse]:
    connections = proj_git_conn_repo.list_by_project(project_id)
    return [GitConnectionResponse.from_dto(c) for c in connections]
```

#### DI Recipe: IGitCredentialRepository

**Task**: Inject git credentials repository with token management support.

**Location**: `skillmeat/api/dependencies.py`

```python
from skillmeat.core.interfaces.repositories import IGitCredentialRepository
from skillmeat.cache.repositories import LocalGitCredentialRepository
from skillmeat.cache.enterprise_repositories import EnterpriseGitCredentialRepository

def get_git_credential_repository(
    state: AppState,
    session: SessionDep,  # For enterprise
) -> IGitCredentialRepository:
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return LocalGitCredentialRepository(
            path_resolver=state.path_resolver,
            session=state.db_session,
        )
    elif edition == "enterprise":
        return EnterpriseGitCredentialRepository(session=session)
    else:
        raise HTTPException(503, f"Unsupported edition: {edition}")

# Create DI alias
GitCredentialRepoDep = Annotated[
    IGitCredentialRepository,
    Depends(get_git_credential_repository)
]
```

**Usage in Router**:
```python
# skillmeat/api/routers/git_credentials.py
from skillmeat.api.dependencies import GitCredentialRepoDep
from skillmeat.api.schemas.git import GitCredentialCreateRequest, GitCredentialResponse

@router.post("/git-credentials")
async def create_git_credential(
    request: GitCredentialCreateRequest,
    cred_repo: GitCredentialRepoDep,
) -> GitCredentialResponse:
    cred_dto = cred_repo.create(
        scope=request.scope,
        token=request.token,
        developer_id=request.developer_id,
    )
    return GitCredentialResponse.from_dto(cred_dto)

@router.get("/git-credentials/{cred_id}")
async def get_git_credential(
    cred_id: str,
    cred_repo: GitCredentialRepoDep,
) -> GitCredentialResponse:
    cred_dto = cred_repo.get(cred_id)
    if not cred_dto:
        raise HTTPException(404, f"Credential '{cred_id}' not found")
    return GitCredentialResponse.from_dto(cred_dto)

@router.delete("/git-credentials/{cred_id}")
async def delete_git_credential(
    cred_id: str,
    cred_repo: GitCredentialRepoDep,
) -> dict:
    success = cred_repo.delete(cred_id)
    if not success:
        raise HTTPException(404, f"Credential '{cred_id}' not found")
    return {"deleted": True}
```

**Note**: Both repositories follow the **edition-based routing pattern**. Local implementations receive `path_resolver` and `session`; enterprise implementations receive only `session` (tenant isolation handled by `EnterpriseRepositoryBase`).

### 5. Mock Repositories (Testing)
**Location**: `tests/mocks/repositories.py`

| Class | Implements |
|-------|-----------|
| `MockArtifactRepository` | IArtifactRepository |
| `MockProjectRepository` | IProjectRepository |
| `MockCollectionRepository` | ICollectionRepository |
| `MockDeploymentRepository` | IDeploymentRepository |
| `MockTagRepository` | ITagRepository |
| `MockSettingsRepository` | ISettingsRepository |

All mocks are in-memory (no filesystem or DB I/O). `IGroupRepository`, `IContextEntityRepository`, `IMarketplaceSourceRepository`, and `IProjectTemplateRepository` do not yet have dedicated mocks — tests for those interfaces use the DI override pattern with `MagicMock` or `patch.object` directly.

**Use in Tests**:
```python
# Fixture
@pytest.fixture
def artifact_repo():
    repo = MockArtifactRepository()
    yield repo
    repo.reset()

# Test
def test_list_artifacts(artifact_repo):
    repo.create(name="test-skill", artifact_type="skill", ...)
    artifacts = repo.list()
    assert len(artifacts) == 1
```

### 6. Stub Repositories Pattern (Enterprise Edition)

**Location**: `skillmeat/core/repositories/enterprise_*.py` (partial implementations)

Repositories without enterprise storage (projects, deployments, settings, context_entity, marketplace_source, project_template) implement the interface with stub methods that:

1. **Return empty responses** without queries:
   - `list()` returns `[]`
   - `get()` returns `None`
   - `search()` returns `[]`

2. **Log debug messages** for audit:
   ```python
   logger.debug(f"Stub operation on enterprise {repo_name}: {method}")
   ```

3. **No-op on writes**:
   - `create()` returns synthetic DTO with sensible defaults
   - `update()` returns input unchanged
   - `delete()` returns `True` (success) without side effects

4. **Raise `HTTPException(503)` on unsupported mutations** (if applicable):
   ```python
   async def deploy(self, ...) -> DeploymentDTO:
       raise HTTPException(503, "Deployments not yet supported in enterprise edition")
   ```

**Why stubs?**: Enterprise repos follow the 16-repository parity model. All 10 abstract interfaces are implemented by all 2 editions (local + enterprise), even if enterprise doesn't yet store that entity. Stubs allow routers to be edition-agnostic — DI selects the right repo, and unsupported operations fail gracefully.

**Gap Closure Status** (as of 2026-04-02): Phase 3 added 4 critical-domain repositories (`EnterpriseWorkflowRepository`, `EnterpriseMemoryItemRepository`, `EnterpriseBundleRepository`, `EnterpriseBomRepository`). Phase 5 added context category and audit history stub repositories. `EnterpriseArtifactRepository` implements full `IArtifactRepository` interface surface. `EnterpriseProjectTemplateRepository` has real CRUD implementation.

**Example stub** (EnterpriseProjectRepository):
```python
class EnterpriseProjectRepository(IProjectRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, project_id: str) -> ProjectDTO | None:
        logger.debug(f"Stub: get project {project_id} in enterprise edition")
        return None

    def create(self, ...) -> ProjectDTO:
        logger.debug(f"Stub: create project in enterprise edition")
        return ProjectDTO(id="stub", ...)  # Synthetic

    def deploy(self, ...) -> DeploymentDTO:
        raise HTTPException(503, "Project deployment not yet supported")
```

---

## Repository Audit Checklist

When auditing an abstract repository interface (ABC) for completeness, DI integration, or multi-backend support, **check all 3 implementation layers**:

### Layer 1: Local Filesystem Implementations

**Location**: `skillmeat/core/repositories/`

Every ABC must have a local implementation prefixed `Local*Repository` (e.g., `LocalArtifactRepository`, `LocalProjectRepository`).

**Enumeration recipe**:
```bash
grep 'class Local.*Repository' skillmeat/core/repositories/*.py
```

**Verification checklist**:
- [ ] Class inherits from the ABC (e.g., `class LocalArtifactRepository(IArtifactRepository)`)
- [ ] Constructor receives managers (ArtifactManager, etc.) and/or PathResolver via DI
- [ ] All abstract methods are implemented (no `raise NotImplementedError`)
- [ ] Returns DTOs, never ORM models or filesystem objects
- [ ] Handles edge cases (missing files, empty collections, invalid paths)
- [ ] Has corresponding mock in `tests/mocks/repositories.py`

### Layer 2: Local DB Cache Implementations

**Location**: `skillmeat/cache/repositories.py`

Some repositories may have SQLite-backed implementations in the cache layer, especially for entities that are only stored in DB (tags, groups, context entities, etc.).

**Enumeration recipe**:
```bash
grep 'class.*Repository' skillmeat/cache/repositories.py | grep -v Enterprise
```

**Verification checklist**:
- [ ] Class name matches pattern (e.g., `LocalTagRepository`)
- [ ] Receives SQLAlchemy `Session` via DI
- [ ] Uses SQLAlchemy 1.x `session.query()` style (intentional divergence from enterprise)
- [ ] Implements all abstract methods from the ABC
- [ ] Returns DTOs via `from_dict()` constructors or dataclass factories
- [ ] Includes unit tests in `skillmeat/cache/tests/`

### Layer 3: Enterprise DB Implementations

**Location**: `skillmeat/cache/enterprise_repositories.py`

Every ABC must have an enterprise implementation (either full CRUD or stub). This is critical for multi-tenant support.

**Enumeration recipe**:
```bash
grep 'class Enterprise.*Repository' skillmeat/cache/enterprise_repositories.py
```

**Verification checklist**:
- [ ] Class name matches pattern (e.g., `EnterpriseArtifactRepository`)
- [ ] Inherits from `EnterpriseRepositoryBase` (if data-backed) or `IRepository` (if stub)
- [ ] Receives SQLAlchemy `Session` via DI
- [ ] Uses SQLAlchemy 2.x `select()` style (never 1.x `session.query()`)
- [ ] All SELECT queries apply tenant filter via `_tenant_select()` or `_apply_tenant_filter()`
- [ ] Uses `session.flush()` (never `commit()`) — caller manages transactions
- [ ] Returns DTOs, never ORM models
- [ ] **New `create()` methods call `ensure_created_by(entity)` before `session.add(entity)`** — belt-and-suspenders behind the Phase 2 `before_insert` listener. Import from `skillmeat.cache.created_by_helpers`. Skip only if the entity model has no `created_by` column (the helper self-guards with `hasattr`) or if `created_by` is always set explicitly from a UUID-typed column (e.g. `EnterpriseGitCredential`).
- [ ] Stub methods (if enterprise doesn't yet support this entity):
  - [ ] `list()` returns `[]`
  - [ ] `get()` returns `None`
  - [ ] `create()` returns synthetic DTO or raises `HTTPException(503)`
  - [ ] Includes debug logging: `logger.debug(f"Stub: {method_name}")`

### Cross-Cutting Validation

After verifying all 3 layers, check DI routing and consistency:

**In `skillmeat/api/dependencies.py`**:
```bash
grep 'def get_.*_repository' skillmeat/api/dependencies.py
```

For each factory function `get_artifact_repository()`, `get_project_repository()`, etc.:

- [ ] Factory checks `state.settings.edition` to route to correct implementation
- [ ] Local edition returns `Local*Repository` instance
- [ ] Enterprise edition returns `Enterprise*Repository` instance
- [ ] Factory creates DI alias: `ArtifactRepoDep = Annotated[IArtifactRepository, Depends(...)]`
- [ ] Return type is the ABC interface, not the concrete implementation

**SQLAlchemy 1.x vs 2.x Divergence** (Intentional):

This is a **design decision**, not a bug:
- **Local repositories** (cache/repositories.py): SQLAlchemy 1.x `session.query()` style
- **Enterprise repositories** (cache/enterprise_repositories.py): SQLAlchemy 2.x `select()` style

This divergence reflects different maturity levels. Verify it's consistent within each layer:
```bash
# Should show ONLY 1.x queries
grep -n 'session.query' skillmeat/cache/repositories.py

# Should show ONLY 2.x queries
grep -n 'select(' skillmeat/cache/enterprise_repositories.py
```

**Enterprise-Only Features**:

Some ABCs have **implementations ONLY in enterprise_repositories.py** (no corresponding local repos). This is by design for features that are enterprise-exclusive:

- `IWorkflowRepository` — enterprise-only (Phase 3)
- `IMemoryItemRepository` — enterprise-only (Phase 3)
- `IBomRepository` — enterprise-only (Phase 3)
- `IProjectGitConnectionRepository` — enterprise-only (Phase 2)
- `IGitCredentialRepository` — enterprise-only (Phase 2)

When auditing these, verify:
- [ ] No `Local*Repository` class exists in `skillmeat/core/repositories/`
- [ ] Factory in `dependencies.py` raises `HTTPException(503)` for local edition
- [ ] Tests use enterprise-edition fixtures (PostgreSQL integration tests)
- [ ] Stub behavior is documented if needed for future local support

### Quick Audit Workflow

1. **Start with the ABC**:
   ```bash
   grep -A 20 'class I.*Repository' skillmeat/core/interfaces/repositories.py
   ```

2. **Check local implementation**:
   ```bash
   grep -n 'class Local.*Repository' skillmeat/core/repositories/*.py
   grep -n 'def method_name' <local_file>  # Verify all methods present
   ```

3. **Check DB cache** (if applicable):
   ```bash
   grep -n 'class.*Repository' skillmeat/cache/repositories.py | grep -i <entity>
   ```

4. **Check enterprise implementation**:
   ```bash
   grep -n 'class Enterprise.*Repository' skillmeat/cache/enterprise_repositories.py
   grep -n 'def method_name' skillmeat/cache/enterprise_repositories.py
   ```

5. **Check DI routing**:
   ```bash
   grep -A 15 'def get_.*_repository' skillmeat/api/dependencies.py
   ```

6. **Verify return types**:
   - All methods should return DTOs (frozen dataclasses from `skillmeat/core/interfaces/dtos.py`)
   - Use type hints: `-> ArtifactDTO | None` or `-> List[ArtifactDTO]`
   - Never return `Any` or raw ORM models

---

## Quick Recipes

### Recipe 1: Enterprise Tenant Isolation Check

**Task**: Verify that an enterprise repository properly filters by tenant.

**Steps**:

1. **Identify the method** that queries data (e.g., `get()`, `list()`, `search()`).
2. **Check the select statement**:
   ```python
   # CORRECT:
   stmt = self._tenant_select(EnterpriseArtifact).where(
       EnterpriseArtifact.id == id
   )

   # Or:
   stmt = select(EnterpriseArtifact).where(
       EnterpriseArtifact.tenant_id == self._get_tenant_id(),
       EnterpriseArtifact.id == id
   )
   ```

3. **For join tables without tenant_id**: Verify `_validate_collection_tenant()` is called before any mutations:
   ```python
   def add_artifact_to_collection(self, collection_id: UUID, artifact_id: UUID):
       self._validate_collection_tenant(collection_id)  # MUST be present
       # ... rest of method
   ```

4. **Anti-pattern** to catch:
   ```python
   # WRONG: No tenant filter
   self.session.get(EnterpriseArtifact, id)

   # WRONG: Using .query() (SQLAlchemy 1.x style in enterprise repo)
   self.session.query(EnterpriseArtifact).filter(...).first()
   ```

### Recipe 2: Adding a New Endpoint

**Task**: Create `GET /api/v1/artifacts/{id}/metadata` that returns artifact metadata.

**Steps**:

1. **Define the route** with repository dependency:
   ```python
   # skillmeat/api/routers/artifacts.py
   from skillmeat.api.dependencies import ArtifactRepoDep
   from skillmeat.api.schemas.artifacts import ArtifactMetadataResponse

   @router.get("/{artifact_id}/metadata", response_model=ArtifactMetadataResponse)
   async def get_artifact_metadata(
       artifact_id: str,
       artifact_repo: ArtifactRepoDep,
   ) -> ArtifactMetadataResponse:
       # Call repository
       artifact_dto = artifact_repo.get(artifact_id)
       if not artifact_dto:
           raise HTTPException(404, f"Artifact '{artifact_id}' not found")

       # Convert DTO to response schema
       return ArtifactMetadataResponse(
           id=artifact_dto.id,
           name=artifact_dto.name,
           artifact_type=artifact_dto.artifact_type,
           created_at=artifact_dto.created_at,
           updated_at=artifact_dto.updated_at,
       )
   ```

2. **Define the response schema** (already exists, reuse):
   ```python
   # skillmeat/api/schemas/artifacts.py
   class ArtifactMetadataResponse(BaseModel):
       id: str
       name: str
       artifact_type: str
       created_at: datetime
       updated_at: datetime
   ```

3. **Test it** using the mock:
   ```python
   # skillmeat/api/tests/test_artifacts.py
   from tests.mocks.repositories import MockArtifactRepository

   def test_get_artifact_metadata():
       repo = MockArtifactRepository()
       repo.create(name="test", artifact_type="skill", ...)

       artifact = repo.get("skill:test")
       assert artifact is not None
       assert artifact.name == "test"
   ```

4. **Never**:
   - Import `pathlib.Path` or `os` in the router
   - Query the database directly (no SQLAlchemy ORM models)
   - Access filesystem via `artifact_manager` directly in the router

---

### Recipe 3: Adding a New Storage Backend (e.g., Future Editions)

**Task**: Create a new edition adapter (e.g., future S3-backed or multi-cloud support).

**Steps**:

1. **Implement all 10 ABCs** (IArtifactRepository, IProjectRepository, ICollectionRepository, IDeploymentRepository, ITagRepository, ISettingsRepository, IGroupRepository, IContextEntityRepository, IMarketplaceSourceRepository, IProjectTemplateRepository):
   ```python
   # skillmeat/core/repositories/cloud_artifact.py
   from skillmeat.core.interfaces.repositories import IArtifactRepository
   from skillmeat.core.interfaces.dtos import ArtifactDTO

   class CloudArtifactRepository(IArtifactRepository):
       def __init__(self, s3_client):
           self.s3 = s3_client

       def get(self, id: str, ctx=None) -> ArtifactDTO | None:
           # Query cloud storage
           obj = self.s3.get_object(Bucket="artifacts", Key=id)
           if obj:
               return ArtifactDTO(...)  # Convert to DTO
           return None

       def list(self, filters=None, ctx=None) -> List[ArtifactDTO]:
           # ... implement other methods
           pass
   ```

2. **Register in factory** (`dependencies.py`):
   ```python
   def get_artifact_repository(state: AppState, session: SessionDep) -> IArtifactRepository:
       edition = state.settings.edition if state.settings else "local"
       if edition == "local":
           return LocalArtifactRepository(...)
       elif edition == "enterprise":
           return EnterpriseArtifactRepository(session=session)
       elif edition == "cloud":  # Future
           return CloudArtifactRepository(s3_client=state.s3_client)
       else:
           raise HTTPException(503, f"Unsupported edition: {edition}")
   ```

3. **Update config** (`skillmeat/api/config.py`):
   ```python
   class APISettings(BaseSettings):
       edition: str = "local"  # "local" | "enterprise" | "cloud" (future)
       s3_bucket: Optional[str] = None  # For cloud edition
   ```

4. **No router changes needed** — the dependency injection handles the swap automatically.

---

### Recipe 5: Updating Mock Repositories After ABC Changes

**Task**: You add a method `search_by_tags()` to IArtifactRepository.

**Steps**:

1. **Add abstract method** to ABC:
   ```python
   # skillmeat/core/interfaces/repositories.py
   class IArtifactRepository(abc.ABC):
       @abc.abstractmethod
       def search_by_tags(
           self,
           tags: List[str],
           ctx: RequestContext | None = None,
       ) -> List[ArtifactDTO]:
           """Return artifacts matching any of the given tags."""
           raise NotImplementedError
   ```

2. **Implement in mock**:
   ```python
   # tests/mocks/repositories.py
   class MockArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           if not tags:
               return []
           result = []
           for artifact in self._artifacts.values():
               if any(tag in artifact.tags for tag in tags):
                   result.append(artifact)
           return result
   ```

3. **Implement in local repository**:
   ```python
   # skillmeat/core/repositories/local_artifact.py
   class LocalArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           # Query the artifact manager or database
           results = []
           for artifact in self._artifacts:
               if any(tag in artifact.tags for tag in tags):
                   results.append(artifact)
           return results
   ```

4. **Implement in enterprise repository**:
   ```python
   # skillmeat/core/repositories/enterprise_artifact.py
   class EnterpriseArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           # Query PostgreSQL with tenant filter + JOIN to tags table
           tenant_id = self._get_tenant_id()
           stmt = (
               select(EnterpriseArtifact)
               .join(EnterpriseArtifactTag)
               .where(
                   EnterpriseArtifact.tenant_id == tenant_id,
                   EnterpriseArtifactTag.tag.in_(tags)
               )
               .distinct()
           )
           results = self.session.execute(stmt).scalars().all()
           return [self._to_dto(r) for r in results]
   ```

---

## DTO Migration Status

### Repository DTO Migration v2 — COMPLETE (Phases 1-5)

**Completion Date**: 2026-04-04
**Scope**: Core domain ABCs, marketplace callers, and low-priority partial-compliance DTOs

#### Phase 1: Git Scanning Stack (GIT-004)
- ✓ 3 ABCs fully DTO-typed: `IGitRepoConnectionRepository`, `IGitRepoScanRepository`, `IGitScanArtifactRepository`
- ✓ 3 new DTOs: `GitRepoConnectionDTO`, `GitRepoScanDTO`, `GitScanArtifactDTO`
- ✓ All 18 methods across git scanning stack converted to DTO signatures
- ✓ Local and enterprise implementations updated

#### Phase 2: Activity Tracking (ACT-002)
- ✓ `IArtifactActivityRepository` ABC rewritten to remove ORM imports
- ✓ `ActivityEventDTO` covers all activity tracking fields
- ✓ All 4 methods in activity repository use DTO signatures
- ✓ Implementations converted to use `from_dict()` constructors

#### Phase 3: Bundle Domain (BND-001..003)
- ✓ `BundleDTO` and `BundleMembershipDTO` introduced
- ✓ `IBundleRepository` fully DTO-typed (11 methods)
- ✓ `CatalogEntryDTO` added for marketplace integration
- ✓ `BundleListDTO` wrapper for paginated responses

#### Phase 4: Marketplace Caller Refactor (MKT-001)
- ✓ 4 `Any`-typed marketplace escape-hatches removed
- ✓ Callers routed to `IArtifactRepository.get()` where appropriate
- ✓ `getattr()` calls eliminated from marketplace_sources.py
- ✓ `IMarketplaceSourceRepository` now fully typed

#### Phase 5: Low-Priority Partial-Compliance DTOs (LOW-001..003)
- ✓ `CollectionStatsDTO` — typed `ICollectionRepository.get_stats()`
- ✓ `TemplateDeployResultDTO` — typed `IProjectTemplateRepository.deploy()` return
- ✓ 3 batch helper DTOs: `BulkAddResultDTO`, `BulkRemoveResultDTO`, `MoveArtifactResultDTO`
- ✓ All implementations and local repositories updated

**Total Deliverables (v2 Phases 1-5)**:
- ✓ 8 ABCs fully DTO-migrated (git scanning, activity, bundle, marketplace, collection, template, artifact bulk ops)
- ✓ 13 new DTOs added across core domains
- ✓ Zero `Any` return types in migrated ABCs
- ✓ All `getattr()` escape-hatches eliminated from routers

**Exception Type Imports**

**Status**: Whitelisted
**Note**: Imports of `ConstraintError`, `NotFoundError`, and `RepositoryError` from `skillmeat.cache.repositories` are permitted in routers and services. These exception types are not ORM models and carry no data-access coupling.

## Known Remaining Cleanup

### Phase 6+ Scope: Enterprise-Only DTO Migrations

**Status**: Pending (Phase 6-8 of v2)
**Note**: Four enterprise-only ABCs remain outside the Phase 1-5 scope per design:

| ABC | DTO Status | Reason | Planned Phase |
|-----|-----------|--------|---------------|
| `IWorkflowRepository` | Not started | Enterprise-specific domain | Phase 7 |
| `IMemoryItemRepository` | Not started | Enterprise-specific domain | Phase 7 |
| `IBomRepository` | Not started | Enterprise-specific domain | Phase 7 |
| `IProjectGitConnectionRepository` | Not started | Missed in original audit | Phase 7 |
| `IGitCredentialRepository` | Not started | Missed in original audit | Phase 8 |

**Planned Deliverables (Phase 6+)**: 5+ new DTOs (WorkflowDTO, MemoryItemDTO, BomSnapshotDTO, AttestationRecordDTO, etc.) + 6 enterprise-only repository converters.

### Router DI Migration: Session Query Cleanup

**Status**: Tracked under `db-user-collection-repository-v1` plan
**Note**: Two distinct work streams remain:
1. `user_collections.py` (50 direct `session.query()` calls) — largest remaining footprint
2. Residual queries in 5 routers (artifacts.py: 15, artifact_history.py: 2, deployment_profiles.py: 2, projects.py: 1, tags.py: 1)

These are separate from DTO migration and tracked under the db-user-collection-repository implementation plan.

### Architecture Review Findings (v2 Phases 1-5)

Captured in `.claude/findings/dto-migration-v2-review-findings.md`. Key findings:

**RESOLVED**:
- ✓ `IProjectTemplateRepository.deploy()` signature mismatch fixed (Phase 5)
- ✓ `CollectionStatsDTO.from_dict` timestamp consistency fixed (Phase 5)

**Open / Backlog**:
- `last_scan_id` missing from `GitRepoConnectionResponse` schema (Phase 1 follow-up)
- Dead-code artifact enrichment in git_connections router (Phase 1 follow-up)
- Mutable list fields in frozen DTOs (Backlog — change to tuples in future cleanup)
- Sensitive fields exposed in `GitRepoConnectionDTO` (Backlog — redact at DTO boundary)
- N+1-style pre-query in group memberships batch operation (Backlog — single-join optimization)

---

## Design Principles

### Why Hexagonal Architecture?

1. **Testability**: Mock repositories enable fast unit tests without filesystem I/O
2. **Flexibility**: Swap storage backends without touching routers
3. **Clarity**: Explicit data contracts (DTOs) prevent leaky abstractions
4. **Maintainability**: Clear separation of concerns

### DTO Immutability

All DTOs are **frozen dataclasses**:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ArtifactDTO:
    id: str
    name: str
    # ... other fields
```

This enforces immutability at the boundary — mutations return new DTOs via `dataclasses.replace()`.

### RequestContext (Per-Request Metadata)

Context flows through method calls without threading globals:
```python
# In a router
ctx = RequestContext(
    user_id="john@example.com",
    request_id="req-12345",
    trace_id="trace-abcdef",
)

# Pass to repository
artifacts = artifact_repo.list(ctx=ctx)
```

---

## Related Documentation

- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
- **Type Sync**: `.claude/context/key-context/fe-be-type-sync-playbook.md`
- **API Contracts**: `.claude/context/key-context/api-contract-source-of-truth.md`
- **Root Architecture**: `CLAUDE.md` → "Architecture Overview"

---

## Tenant-Filter Omission Risk (F-014)

All enterprise repository methods **must** call `_apply_tenant_filter()` before query execution. This is the sole enforcement mechanism for tenant isolation — omission is a **critical security bug**.

**Required pattern**:
```python
stmt = select(self.model).where(...)
stmt = self._apply_tenant_filter(stmt)  # Never skip this
return self.session.execute(stmt).scalars().all()
```

**Code review gate**: All enterprise repository PRs require a visible `_apply_tenant_filter()` call on the diff for every query path.

**Reference**: F-014 in `.claude/findings/enterprise-stub-promotion-findings.md`

---

## Checklist: Adding Repository DI to a Router

Use this checklist when migrating an existing router to repository DI:

- [ ] Read interface ABC in `skillmeat/core/interfaces/repositories.py`
- [ ] Add dependency parameter to route(s): `artifact_repo: ArtifactRepoDep`
- [ ] Replace direct filesystem/DB access with repository method calls
- [ ] Convert returned DTOs to Pydantic response schemas
- [ ] Remove direct imports of `pathlib`, `os`, SQLAlchemy ORM models
- [ ] Update or create mock implementation in `tests/mocks/repositories.py`
- [ ] Write tests using the mock (no filesystem I/O required)
- [ ] Verify endpoint still works end-to-end
- [ ] Commit with message: `refactor(api): migrate <router> to repository DI`

---

**Last Reviewed**: 2026-04-04
**Next Review**: After Phase 6+ (enterprise DTO migrations) and `db-user-collection-repository-v1` plan completion
