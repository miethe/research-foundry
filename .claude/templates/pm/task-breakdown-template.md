# Task Breakdown Template

<!--
Template Variables (configure in config/template-config.json):
- SkillMeat - Project/organization name
- snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits - Task naming format (e.g., PREFIX-NUMBER)
- Collection (Personal Library) → Projects (Local .claude/ directories) → Deployment Engine → User/Local Scopes - System architecture description
- Full type hints with mypy, >80% test coverage with pytest, Black code formatting, flake8 linting, docstrings on all public APIs, TOML configuration, Git-like CLI patterns, atomic file operations, cross-platform compatibility - Core standards and patterns
- mypy type checking (strict mode), pytest coverage >80%, Black formatting required, flake8 linting (E9,F63,F7,F82 errors), docstrings on all public APIs, error handling for all user inputs, atomic file operations, no hardcoded paths, cross-platform testing - Quality requirements
- false - Whether observability is required
- GitHub Issues - Task tracking system name
-->

Use this template to break down features or projects into GitHub Issues-compatible tasks.

---

# Task Breakdown: [Feature/Project Name]

**Breakdown ID**: `TB-{YYYY-MM-DD}-{SHORT-NAME}`
**Date**: [YYYY-MM-DD]
**Feature Complexity**: [Small/Medium/Large/XL]
**Total Estimated Effort**: [Story points or hours]
**Related Documents**: [Links to PRD, SPIKE, Implementation Plan]

## Task Hierarchy Structure

### Epic Level (Large/XL Features Only)
**Epic**: [High-level feature description spanning multiple sprints]

### Story Level (User-facing functionality)
**Story**: [User value-driven functionality that can be completed in 1-2 sprints]

### Task Level (Technical implementation)
**Task**: [Specific technical work that can be completed by one person in a few days]

### Subtask Level (Granular work items)
**Subtask**: [Very specific work items that can be completed in hours or a day]

## SkillMeat Architecture Breakdown

### Database Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - Database Layer Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Design database schema | Create ERD and table definitions | 3 | None | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Create migration scripts | Database migration for new schema | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Implement security policies | Security enforcement for user data | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Add performance indexes | Optimize queries with indexes | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Test migrations | Validate migrations in test environment | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Backend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001:**
- Research existing schema patterns
- Design table relationships
- Define column types and constraints
- Review schema with architect
- Document schema decisions

### Repository Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - Repository Layer Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Create base repository interface | Define CRUD and pagination interface | 2 | [Previous phase] | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Implement query methods | Specific queries for feature needs | 3 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Add pagination | Implement pagination | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Integrate security enforcement | Ensure all queries respect security | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Add query optimization | Performance tuning for queries | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002:**
- Define repository method signatures
- Implement basic CRUD operations
- Add specialized query methods
- Handle query error cases
- Write repository unit tests

### Service Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - Service Layer Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Define DTO schemas | Request/response DTOs with validation | 2 | [Previous phase] | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Implement business logic | Core feature functionality | 5 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Add error handling | Service-layer error patterns | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Add observability | false - Spans and logging | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Service integration tests | Test service with real repository | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Backend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002:**
- Implement core business rules
- Add data validation logic
- Handle edge cases and errors
- Implement service orchestration
- Create comprehensive unit tests

### API Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - API Layer Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Create API router | Router setup with base endpoints | 2 | [Previous phase] | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Implement request validation | Request validation | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Add response formatting | Consistent response envelopes | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Integrate error handling | Map service errors to HTTP codes | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Add authentication | Authentication validation | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-006 | Create API docs | Comprehensive API documentation | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Backend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005:**
- Integrate authentication middleware
- Add user context to requests
- Handle authentication errors
- Test protected endpoints
- Document authentication flow

### UI Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - UI Layer Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Design UI components | Create/update UI components | 3 | [Previous phase] | UI Engineer |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Create state hooks | Custom hooks for state management | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Implement API integration | API integration with state management | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Add form handling | Forms with validation and submission | 3 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Implement accessibility | Accessibility compliance | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-006 | Add responsive design | Mobile and tablet responsiveness | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-007 | Create component docs | Interactive component documentation | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Frontend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004:**
- Design form component structure
- Implement form validation logic
- Add form submission handling
- Handle form error states
- Test form interactions

### Testing Layer Tasks

#### Epic: `snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-[FEATURE]-001 - Testing Implementation`
| Task ID | Task Name | Description | Story Points | Dependencies | Assignee Type |
|---------|-----------|-------------|--------------|--------------|---------------|
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Create unit tests | Unit tests per mypy type checking (strict mode), pytest coverage >80%, Black formatting required, flake8 linting (E9,F63,F7,F82 errors), docstrings on all public APIs, error handling for all user inputs, atomic file operations, no hardcoded paths, cross-platform testing | 5 | [Previous phase] | All Devs |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Add integration tests | API integration tests with database | 3 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Create component tests | Component tests | 3 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-001 | Frontend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004 | Add E2E tests | End-to-end user journeys | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | QA/Frontend |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-005 | Performance testing | Load testing and performance benchmarks | 2 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-002 | Backend Dev |
| snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-006 | Accessibility testing | Automated accessibility testing | 1 | snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-003 | Frontend Dev |

**Subtasks for snake_case for Python functions/variables, kebab-case for CLI commands, semantic versioning (MAJOR.MINOR.PATCH), conventional commits (feat:, fix:, docs:, test:, refactor:), GitHub issue references in commits-004:**
- Design critical user journey tests
- Set up Playwright test environment
- Implement E2E test scenarios
- Add test data management
- Configure CI/CD integration

## Task Estimation Guidelines

### Story Point Scale
- **1 Point**: Very simple task, few hours of work
- **2 Points**: Simple task, half day of work
- **3 Points**: Moderate task, 1 day of work
- **5 Points**: Complex task, 2-3 days of work
- **8 Points**: Very complex task, should be broken down
- **13+ Points**: Epic-level work, must be broken down

### Estimation Factors
Consider these factors when estimating:
- **Complexity**: Technical difficulty and unknowns
- **Dependencies**: Waiting on other work or external factors
- **Risk**: Potential for unexpected issues
- **Experience**: Team familiarity with the technology/domain
- **Testing**: Time needed for comprehensive testing
- **Documentation**: Time for proper documentation

## Task Assignment Guidelines

### Skill-Based Assignment
| Role | Primary Responsibilities | Secondary Responsibilities |
|------|-------------------------|----------------------------|
| **Backend Developer** | DB, Repository, Service, API layers | Integration testing, performance |
| **Frontend Developer** | UI layer, component tests | E2E tests, accessibility |
| **Full-Stack Developer** | Any layer as needed | Integration across layers |
| **UI/UX Designer** | Component design, UX validation | Accessibility consultation |
| **QA Engineer** | E2E tests, test strategy | Manual testing, bug validation |
| **DevOps Engineer** | Deployment, monitoring | Infrastructure, CI/CD |

### Workload Balancing
- **Parallel Work**: Identify tasks that can be done simultaneously
- **Critical Path**: Ensure critical path tasks get priority
- **Knowledge Sharing**: Pair experienced with less experienced developers
- **Review Distribution**: Spread code review load across team

## GitHub Issues Integration Format

### Epic Creation
```json
{
  "title": "[Feature Name] Implementation",
  "description": "Epic description with acceptance criteria",
  "labels": ["feature", "backend", "frontend"],
  "priority": "High",
  "estimate": 45
}
```

### Story Creation
```json
{
  "title": "User can [specific functionality]",
  "description": "Story description with user value",
  "labels": ["story", "user-facing"],
  "priority": "High",
  "estimate": 13,
  "parent": "epic-id"
}
```

### Task Creation
```json
{
  "title": "Implement [specific technical work]",
  "description": "Technical task with acceptance criteria",
  "labels": ["task", "backend"],
  "priority": "Medium",
  "estimate": 3,
  "parent": "story-id"
}
```

## Quality Gates

### Phase Completion Criteria
Each phase must meet these criteria before proceeding:

#### Database Phase
- [ ] All migrations run successfully
- [ ] RLS policies enforce correct boundaries
- [ ] Performance benchmarks met
- [ ] Database tests pass

#### Repository Phase
- [ ] All CRUD operations working
- [ ] Pagination implemented
- [ ] Security integration validated
- [ ] Repository tests meet coverage requirements

#### Service Phase
- [ ] Business logic unit tests pass
- [ ] DTOs validate correctly
- [ ] Error handling follows Full type hints with mypy, >80% test coverage with pytest, Black code formatting, flake8 linting, docstrings on all public APIs, TOML configuration, Git-like CLI patterns, atomic file operations, cross-platform compatibility
- [ ] false - Observability implemented

#### API Phase
- [ ] All endpoints return correct responses
- [ ] API documentation complete
- [ ] Error envelopes consistent
- [ ] Authentication working

#### UI Phase
- [ ] Components render correctly
- [ ] User interactions work
- [ ] Accessibility compliance met
- [ ] Mobile responsiveness validated

#### Testing Phase
- [ ] Code coverage meets mypy type checking (strict mode), pytest coverage >80%, Black formatting required, flake8 linting (E9,F63,F7,F82 errors), docstrings on all public APIs, error handling for all user inputs, atomic file operations, no hardcoded paths, cross-platform testing
- [ ] All tests passing in CI/CD
- [ ] E2E tests cover critical paths
- [ ] Performance benchmarks met

## Risk Considerations

### Common Task Risks
- **Underestimation**: Tasks more complex than expected
- **Dependencies**: Blocking dependencies delay work
- **Scope Creep**: Requirements change during implementation
- **Technical Debt**: Existing code issues slow progress
- **Integration Issues**: Components don't work together

### Risk Mitigation Strategies
- **Buffer Time**: Add 20% buffer to estimates
- **Parallel Work**: Reduce dependency chains
- **Incremental Delivery**: Deliver value early and often
- **Regular Reviews**: Catch issues early
- **Documentation**: Maintain clear requirements

---

**Task Breakdown Template Version**: 1.0
**Last Updated**: [Date]
**Usage**: Use with GitHub Issues or other project management tools
