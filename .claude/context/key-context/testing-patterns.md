---
title: Testing Patterns Reference
description: Comprehensive testing patterns for SkillMeat web frontend
references:
  - skillmeat/web/__tests__/**/*.ts
  - skillmeat/web/__tests__/**/*.tsx
  - skillmeat/web/tests/**/*.ts
  - skillmeat/web/tests/**/*.spec.ts
last_verified: 2026-01-14
category: testing
related:
  - skillmeat/web/CLAUDE.md
  - skillmeat/web/hooks/CLAUDE.md
  - skillmeat/web/components/CLAUDE.md
---

# Testing Patterns Reference

Comprehensive testing patterns for SkillMeat web frontend using Jest, React Testing Library, and Playwright.

## Test Types Overview

| Type | Location | Purpose | Runner |
|------|----------|---------|--------|
| Unit/Integration | `__tests__/` | Components, hooks, utils | Jest + RTL |
| E2E | `tests/` | Full user workflows | Playwright |

---

## Unit Test File Structure

```
skillmeat/web/
├── __tests__/
│   ├── components/
│   │   ├── CollectionCard.test.tsx
│   │   ├── GroupList.test.tsx
│   │   ├── ArtifactGrid.test.tsx
│   │   └── ProjectSelector.test.tsx
│   ├── hooks/
│   │   ├── use-collections.test.ts
│   │   ├── use-artifacts.test.ts
│   │   ├── use-deployments.test.ts
│   │   └── use-groups.test.ts
│   └── lib/
│       ├── api.test.ts
│       ├── api-client.test.ts
│       └── utils.test.ts
```

**Naming Convention**: `[module-name].test.ts(x)`

### Test Commands

| Command | Purpose |
|---------|---------|
| `pnpm test` | Run all unit tests |
| `pnpm test:watch` | Watch mode for development |
| `pnpm test:coverage` | Run with coverage report |
| `pnpm test:ci` | CI mode (no watch, coverage) |

---

## Component Test Template

Complete template showing all key patterns:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CollectionCard } from '@/components/collection-card';

describe('CollectionCard', () => {
  // Basic rendering test
  it('renders collection name and description', () => {
    const collection = {
      id: '1',
      name: 'Test Collection',
      description: 'Test description',
      artifact_count: 5,
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<CollectionCard collection={collection} />);

    // Use accessible queries (getByRole preferred)
    expect(screen.getByRole('heading', { name: 'Test Collection' })).toBeInTheDocument();
    expect(screen.getByText('Test description')).toBeInTheDocument();
    expect(screen.getByText('5 artifacts')).toBeInTheDocument();
  });

  // User interaction test
  it('handles click events', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    const collection = { id: '1', name: 'Test' };

    render(<CollectionCard collection={collection} onClick={onClick} />);

    // Click using semantic query
    await user.click(screen.getByRole('button', { name: 'View' }));

    // Assert callback was called with correct args
    expect(onClick).toHaveBeenCalledWith('1');
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  // Async rendering test
  it('shows loading state then content', async () => {
    const collection = { id: '1', name: 'Test' };

    render(<CollectionCard collection={collection} isLoading={true} />);

    // Check loading state
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();

    // Re-render with loaded state
    render(<CollectionCard collection={collection} isLoading={false} />);

    // Use findBy for async appearance
    const heading = await screen.findByRole('heading', { name: 'Test' });
    expect(heading).toBeInTheDocument();
  });

  // Conditional rendering test
  it('shows action buttons only when authorized', () => {
    const collection = { id: '1', name: 'Test' };

    const { rerender } = render(
      <CollectionCard collection={collection} canEdit={false} />
    );

    // Button should not exist
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();

    // Re-render with edit permission
    rerender(<CollectionCard collection={collection} canEdit={true} />);

    // Button should now appear
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
  });

  // Form interaction test
  it('validates and submits form data', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();

    render(<CollectionForm onSubmit={onSubmit} />);

    // Fill form fields
    await user.type(screen.getByLabelText('Name'), 'New Collection');
    await user.type(screen.getByLabelText('Description'), 'Collection description');

    // Submit form
    await user.click(screen.getByRole('button', { name: 'Create' }));

    // Wait for async validation
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'New Collection',
        description: 'Collection description',
      });
    });
  });

  // Error state test
  it('displays error message when provided', () => {
    const error = 'Failed to load collection';

    render(<CollectionCard collection={null} error={error} />);

    expect(screen.getByRole('alert')).toHaveTextContent(error);
  });
});
```

---

## Testing Hooks with TanStack Query

Complete pattern for testing hooks that use TanStack Query:

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCollections } from '@/hooks';

// Mock API client at top level
jest.mock('@/lib/api/collections', () => ({
  fetchCollections: jest.fn(),
  createCollection: jest.fn(),
  updateCollection: jest.fn(),
  deleteCollection: jest.fn(),
}));

import { fetchCollections, createCollection } from '@/lib/api/collections';

describe('useCollections', () => {
  let queryClient: QueryClient;

  // Fresh QueryClient before each test
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },  // Disable retries in tests
        mutations: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  // Wrapper component providing QueryClient
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  // Success case
  it('fetches collections successfully', async () => {
    const mockCollections = [
      { id: '1', name: 'Collection 1', artifact_count: 3 },
      { id: '2', name: 'Collection 2', artifact_count: 5 },
    ];

    (fetchCollections as jest.Mock).mockResolvedValueOnce(mockCollections);

    const { result } = renderHook(() => useCollections(), { wrapper });

    // Initial loading state
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();

    // Wait for query to complete
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Assert final state
    expect(result.current.data).toEqual(mockCollections);
    expect(result.current.isLoading).toBe(false);
    expect(fetchCollections).toHaveBeenCalledTimes(1);
  });

  // Error case
  it('handles errors gracefully', async () => {
    const errorMessage = 'API error';
    (fetchCollections as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useCollections(), { wrapper });

    // Wait for error state
    await waitFor(() => expect(result.current.isError).toBe(true));

    // Assert error state
    expect(result.current.error).toEqual(new Error(errorMessage));
    expect(result.current.data).toBeUndefined();
  });

  // Mutation test
  it('creates collection and invalidates cache', async () => {
    const newCollection = { name: 'New Collection', description: 'Test' };
    const createdCollection = { id: '3', ...newCollection, artifact_count: 0 };

    (createCollection as jest.Mock).mockResolvedValueOnce(createdCollection);

    const { result } = renderHook(() => useCollections(), { wrapper });

    // Execute mutation
    result.current.createMutation.mutate(newCollection);

    // Wait for mutation to complete
    await waitFor(() => expect(result.current.createMutation.isSuccess).toBe(true));

    // Assert mutation result
    expect(result.current.createMutation.data).toEqual(createdCollection);
    expect(createCollection).toHaveBeenCalledWith(newCollection);
  });

  // Refetch test
  it('refetches data when invalidated', async () => {
    const initialData = [{ id: '1', name: 'Collection 1' }];
    const updatedData = [
      { id: '1', name: 'Collection 1' },
      { id: '2', name: 'Collection 2' },
    ];

    (fetchCollections as jest.Mock)
      .mockResolvedValueOnce(initialData)
      .mockResolvedValueOnce(updatedData);

    const { result } = renderHook(() => useCollections(), { wrapper });

    // Wait for initial fetch
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(initialData);

    // Invalidate and refetch
    await result.current.refetch();

    // Wait for refetch
    await waitFor(() => expect(fetchCollections).toHaveBeenCalledTimes(2));
    expect(result.current.data).toEqual(updatedData);
  });
});
```

---

## Mocking Fetch

Pattern for mocking global fetch API:

```typescript
// Mock global fetch
global.fetch = jest.fn();

beforeEach(() => {
  jest.resetAllMocks();
});

describe('API Client', () => {
  it('calls API correctly', async () => {
    const mockData = { id: '1', name: 'Test Collection' };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
      headers: new Headers(),
    });

    const result = await fetchCollection('1');

    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/collections/1',
      expect.objectContaining({
        method: 'GET',
        headers: expect.any(Object),
      })
    );
  });

  it('handles fetch errors', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    await expect(fetchCollection('1')).rejects.toThrow('Network error');
  });

  it('handles HTTP error responses', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Not found' }),
    });

    await expect(fetchCollection('1')).rejects.toThrow();
  });
});
```

---

## E2E Test Structure

```
skillmeat/web/tests/
├── collections.spec.ts
├── groups.spec.ts
├── deployments.spec.ts
├── artifacts.spec.ts
└── navigation.spec.ts
```

**Naming Convention**: `[feature].spec.ts`

### E2E Test Commands

| Command | Purpose |
|---------|---------|
| `pnpm test:e2e` | Run E2E tests headless |
| `pnpm test:e2e:ui` | Run with Playwright UI |
| `pnpm test:e2e:debug` | Run in debug mode |
| `pnpm test:e2e:codegen` | Generate test code |

---

## E2E Test Template (Playwright)

Complete E2E test examples:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Collections', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app before each test
    await page.goto('http://localhost:3000');
  });

  test('creates new collection', async ({ page }) => {
    // Navigate to create dialog
    await page.getByRole('button', { name: 'New Collection' }).click();

    // Fill form fields
    await page.getByLabel('Name').fill('My Collection');
    await page.getByLabel('Description').fill('Test description');

    // Submit form
    await page.getByRole('button', { name: 'Create' }).click();

    // Assert success
    await expect(page.getByText('My Collection')).toBeVisible();
    await expect(page.getByText('Collection created successfully')).toBeVisible();
  });

  test('navigates to collection details', async ({ page }) => {
    // Click collection card
    await page.getByRole('link', { name: 'My Collection' }).click();

    // Assert navigation
    await expect(page).toHaveURL(/\/collections\/[a-f0-9-]+/);
    await expect(page.getByRole('heading', { name: 'My Collection' })).toBeVisible();
  });

  test('edits collection details', async ({ page }) => {
    // Navigate to collection
    await page.getByRole('link', { name: 'My Collection' }).click();

    // Open edit dialog
    await page.getByRole('button', { name: 'Edit' }).click();

    // Update fields
    await page.getByLabel('Name').fill('Updated Collection');

    // Save changes
    await page.getByRole('button', { name: 'Save' }).click();

    // Assert update
    await expect(page.getByRole('heading', { name: 'Updated Collection' })).toBeVisible();
  });

  test('deletes collection', async ({ page }) => {
    // Navigate to collection
    await page.getByRole('link', { name: 'My Collection' }).click();

    // Open delete dialog
    await page.getByRole('button', { name: 'Delete' }).click();

    // Confirm deletion
    await page.getByRole('button', { name: 'Confirm' }).click();

    // Assert redirect and removal
    await expect(page).toHaveURL('/');
    await expect(page.getByText('My Collection')).not.toBeVisible();
  });

  test('searches collections', async ({ page }) => {
    // Enter search query
    await page.getByPlaceholderText('Search collections').fill('Test');

    // Wait for results
    await expect(page.getByText('Test Collection')).toBeVisible();
    await expect(page.getByText('Other Collection')).not.toBeVisible();
  });

  test('filters collections by type', async ({ page }) => {
    // Open filter dropdown
    await page.getByRole('button', { name: 'Filter' }).click();

    // Select artifact type
    await page.getByRole('menuitem', { name: 'Skills' }).click();

    // Assert filtered results
    await expect(page.getByText('Skill Collection')).toBeVisible();
    await expect(page.getByText('Command Collection')).not.toBeVisible();
  });
});
```

---

## Query Priority (React Testing Library)

Use queries in this order for best accessibility:

### 1. getByRole (Preferred)

Most accessible - use for buttons, links, headings, form controls:

```typescript
// Buttons
screen.getByRole('button', { name: 'Submit' })
screen.getByRole('button', { name: /submit/i }) // Case-insensitive regex

// Links
screen.getByRole('link', { name: 'View Details' })

// Headings
screen.getByRole('heading', { name: 'Collection Name' })
screen.getByRole('heading', { level: 1 }) // Specific heading level

// Form controls
screen.getByRole('textbox', { name: 'Email' })
screen.getByRole('checkbox', { name: 'Remember me' })
screen.getByRole('combobox', { name: 'Select country' })
```

### 2. getByLabelText

For form inputs with associated labels:

```typescript
screen.getByLabelText('Email')
screen.getByLabelText('Password')
screen.getByLabelText(/username/i)
```

### 3. getByPlaceholderText

Fallback for inputs without labels:

```typescript
screen.getByPlaceholderText('Enter name')
screen.getByPlaceholderText('Search...')
```

### 4. getByText

For non-interactive text content:

```typescript
screen.getByText('Success message')
screen.getByText(/error/i)
screen.getByText((content, element) => {
  return element?.tagName.toLowerCase() === 'p' && content.includes('text');
})
```

### 5. getByTestId (Last Resort)

Only when no semantic query works:

```typescript
screen.getByTestId('custom-widget')
screen.getByTestId('complex-component')
```

**Note**: Always prefer semantic queries over test IDs for better accessibility.

---

## Async Testing Patterns

### waitFor (Condition-Based Waiting)

```typescript
// Wait for element to appear
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});

// Wait for multiple conditions
await waitFor(() => {
  expect(screen.getByText('Data')).toBeInTheDocument();
  expect(screen.queryByText('Loading')).not.toBeInTheDocument();
});

// Custom timeout
await waitFor(
  () => {
    expect(screen.getByText('Slow data')).toBeInTheDocument();
  },
  { timeout: 3000 }
);
```

### findBy Queries (Built-in waitFor)

```typescript
// Automatically waits for element
const element = await screen.findByText('Loaded');
expect(element).toBeInTheDocument();

// With role
const button = await screen.findByRole('button', { name: 'Submit' });

// findAll for multiple elements
const items = await screen.findAllByRole('listitem');
expect(items).toHaveLength(5);
```

### waitForElementToBeRemoved

```typescript
// Wait for loading spinner to disappear
await waitForElementToBeRemoved(() => screen.getByText('Loading...'));

// Then assert loaded state
expect(screen.getByText('Data loaded')).toBeInTheDocument();
```

---

## User Interactions

### userEvent Setup and Usage

```typescript
import userEvent from '@testing-library/user-event';

describe('UserInteractions', () => {
  it('handles click events', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();

    render(<Button onClick={onClick}>Click me</Button>);

    await user.click(screen.getByRole('button', { name: 'Click me' }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('handles text input', async () => {
    const user = userEvent.setup();

    render(<input type="text" placeholder="Name" />);

    const input = screen.getByPlaceholderText('Name');
    await user.type(input, 'John Doe');

    expect(input).toHaveValue('John Doe');
  });

  it('handles keyboard navigation', async () => {
    const user = userEvent.setup();

    render(
      <div>
        <button>First</button>
        <button>Second</button>
      </div>
    );

    // Tab to first button
    await user.tab();
    expect(screen.getByRole('button', { name: 'First' })).toHaveFocus();

    // Tab to second button
    await user.tab();
    expect(screen.getByRole('button', { name: 'Second' })).toHaveFocus();
  });

  it('handles selection', async () => {
    const user = userEvent.setup();

    render(
      <select>
        <option value="1">Option 1</option>
        <option value="2">Option 2</option>
      </select>
    );

    const select = screen.getByRole('combobox');
    await user.selectOptions(select, '2');

    expect(select).toHaveValue('2');
  });

  it('handles file upload', async () => {
    const user = userEvent.setup();
    const file = new File(['content'], 'file.txt', { type: 'text/plain' });

    render(<input type="file" />);

    const input = screen.getByRole('textbox', { hidden: true });
    await user.upload(input, file);

    expect(input.files?.[0]).toEqual(file);
  });
});
```

---

## Common Antipatterns

### Testing Implementation Details

```typescript
// ❌ BAD: Testing internal state
expect(component.state.count).toBe(1);
expect(component.instance().handleClick).toBeDefined();

// ✅ GOOD: Test user-visible behavior
expect(screen.getByText('Count: 1')).toBeInTheDocument();
await user.click(screen.getByRole('button'));
expect(screen.getByText('Count: 2')).toBeInTheDocument();
```

### Skipping Accessibility Queries

```typescript
// ❌ BAD: Using testId first
screen.getByTestId('submit-button')

// ❌ BAD: Using class names
container.querySelector('.submit-button')

// ✅ GOOD: Use accessible role
screen.getByRole('button', { name: 'Submit' })
```

### No Cleanup Between Tests

```typescript
// ❌ BAD: Shared mutable state
let queryClient = new QueryClient();

beforeEach(() => {
  // No reset - state leaks between tests
});

// ✅ GOOD: Fresh instance per test
beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  jest.clearAllMocks();
});
```

### Hardcoded Waits

```typescript
// ❌ BAD: Arbitrary timeout
await new Promise(resolve => setTimeout(resolve, 1000));
expect(screen.getByText('Loaded')).toBeInTheDocument();

// ✅ GOOD: Condition-based waiting
await waitFor(() => expect(screen.getByText('Loaded')).toBeInTheDocument());

// ✅ BETTER: Use findBy
const element = await screen.findByText('Loaded');
expect(element).toBeInTheDocument();
```

### Using fireEvent Instead of userEvent

```typescript
// ❌ BAD: Less realistic interactions
fireEvent.click(button);
fireEvent.change(input, { target: { value: 'text' } });

// ✅ GOOD: Realistic user interactions
const user = userEvent.setup();
await user.click(button);
await user.type(input, 'text');
```

---

## Coverage Requirements

| Metric | Target | Description |
|--------|--------|-------------|
| Statements | >80% | Lines of code executed |
| Branches | >75% | Conditional paths taken |
| Functions | >80% | Functions called |
| Lines | >80% | Total lines covered |

### Checking Coverage

```bash
# Run tests with coverage
pnpm test:coverage

# Open HTML report
open coverage/lcov-report/index.html

# View in terminal
pnpm test:coverage --coverage
```

### Coverage Configuration

In `jest.config.js`:

```javascript
module.exports = {
  collectCoverageFrom: [
    'app/**/*.{ts,tsx}',
    'components/**/*.{ts,tsx}',
    'hooks/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThresholds: {
    global: {
      statements: 80,
      branches: 75,
      functions: 80,
      lines: 80,
    },
  },
};
```

---

## Quick Reference

### Essential Imports

```typescript
// Unit tests
import { render, screen, waitFor, renderHook } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// E2E tests
import { test, expect } from '@playwright/test';
```

### Common Test Patterns

```typescript
// Component test
render(<Component {...props} />);
expect(screen.getByRole('button')).toBeInTheDocument();

// Hook test
const { result } = renderHook(() => useHook(), { wrapper });
await waitFor(() => expect(result.current.isSuccess).toBe(true));

// User interaction
const user = userEvent.setup();
await user.click(screen.getByRole('button'));

// Async assertion
await waitFor(() => expect(screen.getByText('Loaded')).toBeInTheDocument());
const element = await screen.findByText('Loaded');
```

### Debugging Tests

```typescript
// Print component tree
screen.debug();

// Print specific element
screen.debug(screen.getByRole('button'));

// Log available queries
screen.logTestingPlaygroundURL();
```
