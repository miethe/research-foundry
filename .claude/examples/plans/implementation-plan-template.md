# Implementation Plan: {{EPIC_ID}}-{{STORY_ID}}

## Story Summary
- Epic: {{EPIC_ID}} - {{Epic Description}}
- Scope: {{Frontend | Backend | Full-stack | Infrastructure}}
- Complexity: {{S | M | L | XL}}

## Overview
{{Brief 2-3 sentence description of what this implementation does and why it's needed}}

## File Changes

### Create
- [ ] {{path/to/new/file1.ext}} - {{Description of what this file does}}
- [ ] {{path/to/new/file2.ext}} - {{Description}}
- [ ] {{path/to/new/file3.ext}} - {{Description}}

### Modify
- [ ] {{path/to/existing/file1.ext}} - {{Description of changes}}
- [ ] {{path/to/existing/file2.ext}} - {{Description of changes}}
- [ ] {{path/to/existing/file3.ext}} - {{Description of changes}}

### Delete
- [ ] {{path/to/old/file1.ext}} - {{Reason for deletion}}
- [ ] {{path/to/old/file2.ext}} - {{Reason for deletion}}

## Component Architecture

### Component 1: {{Component Name}}
- [ ] {{Responsibility 1}}
- [ ] {{Responsibility 2}}
- [ ] {{Responsibility 3}}

### Component 2: {{Component Name}}
- [ ] {{Responsibility 1}}
- [ ] {{Responsibility 2}}
- [ ] {{Responsibility 3}}

### Component 3: {{Component Name}}
- [ ] {{Responsibility 1}}
- [ ] {{Responsibility 2}}
- [ ] {{Responsibility 3}}

## Technical Specifications

### Data Models
```typescript
interface {{ModelName}} {
  {{field1}}: {{type}};  // {{Description}}
  {{field2}}: {{type}};  // {{Description}}
  {{field3}}: {{type}};  // {{Description}}
}
```

### API Endpoints (if applicable)
- `{{METHOD}} /api/v1/{{resource}}` - {{Description}}
- `{{METHOD}} /api/v1/{{resource}}/{{id}}` - {{Description}}

### State Management
- {{State 1}}: {{Description of state and how it's managed}}
- {{State 2}}: {{Description of state and how it's managed}}

## Integration Points
- [ ] {{Integration 1}} - {{Description of how systems integrate}}
- [ ] {{Integration 2}} - {{Description of integration approach}}
- [ ] {{Integration 3}} - {{Description of dependencies}}

## Test Coverage

### Unit Tests
- [ ] {{Component 1}} - {{Test scenarios}}
- [ ] {{Component 2}} - {{Test scenarios}}
- [ ] {{Utility/Helper}} - {{Test scenarios}}

### Integration Tests
- [ ] {{Integration 1}} - {{Test scenarios}}
- [ ] {{Integration 2}} - {{Test scenarios}}
- [ ] {{API endpoint}} - {{Test scenarios}}

### E2E Tests
- [ ] {{User flow 1}} - {{Test scenarios}}
- [ ] {{User flow 2}} - {{Test scenarios}}
- [ ] {{Critical path}} - {{Test scenarios}}

## Observability & Monitoring
- [ ] {{Event 1}}: `{{event.name.pattern}}` - {{When it fires}}
- [ ] {{Event 2}}: `{{event.name.pattern}}` - {{When it fires}}
- [ ] {{Metric 1}}: {{Description of what's tracked}}
- [ ] {{Metric 2}}: {{Description of what's tracked}}

## Documentation Updates
- [ ] {{Doc 1}}: {{What needs to be documented}}
- [ ] {{Doc 2}}: {{What needs to be documented}}
- [ ] {{API Documentation}}: {{Endpoint specs to add}}

## Acceptance Criteria
1. [ ] {{Criterion 1 - measurable condition}}
2. [ ] {{Criterion 2 - measurable condition}}
3. [ ] {{Criterion 3 - measurable condition}}
4. [ ] {{Criterion 4 - measurable condition}}

## Dependencies
- {{Dependency 1}}: {{Description of what's required}}
- {{Dependency 2}}: {{Description of what's required}}
- {{Dependency 3}}: {{Description of what's required}}

## Risks & Mitigation
- **{{Risk 1}}**: {{Description}} → {{Mitigation strategy}}
- **{{Risk 2}}**: {{Description}} → {{Mitigation strategy}}
- **{{Risk 3}}**: {{Description}} → {{Mitigation strategy}}

## Rollout Strategy (if applicable)
1. {{Phase 1}}: {{Description}}
2. {{Phase 2}}: {{Description}}
3. {{Phase 3}}: {{Description}}
