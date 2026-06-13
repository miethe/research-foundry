---
title: Next.js App Router Patterns
description: Comprehensive Next.js 15 App Router patterns for SkillMeat web frontend
audience: developers
tags:
  - nextjs
  - app-router
  - react
  - frontend
  - typescript
created: 2026-01-14
updated: 2026-01-14
category: frontend
status: active
references:
  - skillmeat/web/app/**/*.tsx
  - skillmeat/web/components/**/*.tsx
  - skillmeat/web/app/CLAUDE.md
last_verified: 2026-01-14
---

# Next.js App Router Patterns

Comprehensive patterns for Next.js 15 App Router in SkillMeat web frontend.

---

## Server vs Client Components

**Default**: Server components (no directive needed)

```tsx
// ✅ Server Component (default)
export default async function Page() {
  // Can fetch directly in server components
  const data = await fetchFromAPI();
  return <div>{data}</div>;
}
```

**Use `'use client'`** when component needs:
- React hooks (useState, useEffect, etc.)
- Browser APIs (localStorage, window)
- Event handlers (onClick, onChange)
- TanStack Query hooks (useQuery, useMutation)

```tsx
'use client';

import { useState } from 'react';

export default function Page() {
  const [state, setState] = useState(false);
  return <button onClick={() => setState(!state)}>Toggle</button>;
}
```

**Pattern**: Keep `'use client'` boundary as low as possible. Prefer server components at page level, delegate client interactivity to child components.

---

## Root Layout Structure

**File**: `app/layout.tsx`

```tsx
import { Providers } from '@/components/providers';
import { Header } from '@/components/header';
import { Navigation } from '@/components/navigation';

export default function RootLayout({
  children
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <div className="flex flex-1">
              <Navigation />
              <main className="flex-1 p-6">
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
```

**Key Elements**:
- `Providers` wrap all client-side context (TanStack Query, theme)
- `Header` + `Navigation` are consistent across all pages
- `main` receives page content via `{children}`
- Use `suppressHydrationWarning` for dark mode support

---

## Page Component Patterns

### Simple Page (Server Component)

```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
      <AnalyticsGrid />
    </div>
  );
}
```

### Client Page (Hooks/State)

```tsx
'use client';

import { useState } from 'react';
import { useCollections } from '@/hooks';

export default function CollectionPage() {
  const [viewMode, setViewMode] = useState('grid');
  const { data, isLoading } = useCollections();

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <CollectionToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
      <ArtifactGrid artifacts={data} />
    </div>
  );
}
```

### Container Pattern (Consistent Spacing)

Use `space-y-6` for vertical spacing:

```tsx
<div className="space-y-6">
  <PageHeader />
  <StatsCards />
  <MainContent />
</div>
```

---

## Dynamic Routes

**File Structure**: `app/projects/[id]/page.tsx`

### Next.js 15 Pattern (Async Params)

```tsx
export default async function ProjectPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params; // MUST await params in Next.js 15
  return <ProjectDetails projectId={id} />;
}
```

**Important**: Next.js 15 requires awaiting `params` in dynamic routes.

### Client Component with useParams

If page is `'use client'`, use `useParams()` instead:

```tsx
'use client';

import { useParams } from 'next/navigation';

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;

  return <ProjectDetails projectId={projectId} />;
}
```

---

## Loading and Error States

### Loading Component (Automatic)

**File**: `app/projects/[id]/loading.tsx`

```tsx
import { Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin" />
    </div>
  );
}
```

Auto-wraps page in Suspense boundary.

### Inline Loading (Component-Level)

```tsx
import { Skeleton } from '@/components/ui/skeleton';

export default function Page() {
  const { data, isLoading } = useCollections();

  if (isLoading) {
    return <Skeleton className="h-48 w-full" />;
  }

  return <CollectionList collections={data} />;
}
```

### Error Handling (Client Components)

```tsx
export default function Page() {
  const { data, error } = useCollections();

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">
          Failed to load. Try again.
        </p>
      </div>
    );
  }

  return <CollectionList collections={data} />;
}
```

---

## Data Fetching Patterns

### Server Component (Direct Fetch)

```tsx
export default async function Page() {
  const response = await fetch('http://localhost:8080/api/v1/collections');
  const collections = await response.json();

  return <CollectionList collections={collections} />;
}
```

### Client Component (TanStack Query Hooks)

```tsx
'use client';

import { useCollections } from '@/hooks';

export default function Page() {
  const { data, isLoading, error } = useCollections();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} />;

  return <CollectionList collections={data} />;
}
```

**Rule**: Server components fetch directly; client components use hooks.

---

## URL State Management

### Reading Query Parameters

```tsx
'use client';

import { useSearchParams } from 'next/navigation';

export default function Page() {
  const searchParams = useSearchParams();
  const tab = searchParams.get('tab') || 'deployed';

  return <Tabs value={tab} />;
}
```

### Writing Query Parameters

```tsx
'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';

export default function Page() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', value);
    router.push(`${pathname}?${params.toString()}`);
  };

  return <Tabs onValueChange={handleTabChange} />;
}
```

---

## Suspense Boundaries

For client components with async data:

```tsx
'use client';

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

function PageContent() {
  const { data } = useCollections(); // Async data
  return <CollectionList collections={data} />;
}

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }
    >
      <PageContent />
    </Suspense>
  );
}
```

---

## Metadata (Server Components Only)

### Static Metadata

```tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard | SkillMeat',
  description: 'Manage your artifact collection',
};

export default function Page() {
  return <div>Dashboard</div>;
}
```

### Dynamic Metadata

```tsx
import type { Metadata } from 'next';

export async function generateMetadata({
  params
}: {
  params: Promise<{ id: string }>
}): Promise<Metadata> {
  const { id } = await params;
  const collection = await fetchCollection(id);

  return {
    title: `${collection.name} | SkillMeat`,
    description: collection.description,
  };
}

export default async function Page({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;
  return <CollectionDetails collectionId={id} />;
}
```

**Note**: `generateMetadata` must be async and is only available in server components.

---

## Import Conventions

| Import | Usage |
|--------|-------|
| `@/components/*` | Shared UI components |
| `@/hooks` | Custom hooks (barrel import) |
| `@/lib/api` | API client functions |
| `@/types/*` | TypeScript types |
| `next/navigation` | `useRouter`, `useParams`, `useSearchParams`, `usePathname` |
| `next/image` | Optimized images |

**Always use `@/` alias** - never relative imports for cross-directory files.

### Component Imports

```tsx
// ✅ GOOD: Absolute imports with @/ alias
import { Button } from '@/components/ui/button';
import { CollectionCard } from '@/components/shared/collection-card';
import { useCollections } from '@/hooks';
import { Collection } from '@/types/collection';

// ❌ BAD: Relative imports
import { Button } from '../../../components/ui/button';
import { useCollections } from '../../hooks/use-collections';
```

### Navigation Imports

```tsx
'use client';

import {
  useRouter,      // For programmatic navigation
  useParams,      // For dynamic route params
  useSearchParams, // For query parameters
  usePathname     // For current path
} from 'next/navigation';

export default function Page() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Navigate programmatically
  router.push('/collections');

  // Get dynamic route param
  const collectionId = params.id as string;

  // Get query parameter
  const tab = searchParams.get('tab');

  // Get current path
  console.log(pathname); // e.g., /collections/abc123

  return <div>Navigation Example</div>;
}
```

---

## Common Antipatterns

### ❌ Using hooks in server components

```tsx
// BAD: Server component with hook
export default function Page() {
  const [state, setState] = useState(false); // Error!
  return <div>{state}</div>;
}
```

### ✅ Add 'use client' or delegate to child

```tsx
'use client'; // Add directive

export default function Page() {
  const [state, setState] = useState(false);
  return <div>{state}</div>;
}
```

### ❌ Not awaiting params in Next.js 15

```tsx
// BAD: Not awaiting params
export default async function Page({
  params
}: {
  params: { id: string }
}) {
  return <div>{params.id}</div>; // Error in Next.js 15!
}
```

### ✅ Await params

```tsx
export default async function Page({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;
  return <div>{id}</div>;
}
```

### ❌ Fetching in client components without hooks

```tsx
// BAD: Inline fetch in client component
'use client';
export default function Page() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch('/api/collections').then(r => setData(r));
  }, []);
  // ...
}
```

### ✅ Use TanStack Query hooks

```tsx
'use client';
import { useCollections } from '@/hooks';

export default function Page() {
  const { data } = useCollections();
  // ...
}
```

---

## Best Practices Summary

1. **Server components by default** - Only use `'use client'` when needed
2. **Await params in Next.js 15** - Dynamic routes require `await params`
3. **Use TanStack Query for client data** - Never inline fetch in useEffect
4. **Suspense for async boundaries** - Wrap async client components
5. **Absolute imports with @/ alias** - Consistent import paths
6. **Metadata in server components** - SEO and social sharing
7. **URL state with searchParams** - Shareable, bookmarkable state
8. **Loading/error states** - Both automatic (loading.tsx) and inline
9. **Consistent spacing** - Use `space-y-6` for vertical rhythm
10. **Type safety** - Explicit types for params, searchParams, metadata

---

## Reference

- **Next.js 15 Docs**: https://nextjs.org/docs/app
- **App Router Migration**: https://nextjs.org/docs/app/building-your-application/upgrading/app-router-migration
- **Data Fetching**: https://nextjs.org/docs/app/building-your-application/data-fetching
- **Routing**: https://nextjs.org/docs/app/building-your-application/routing
- **Hooks**: `skillmeat/web/hooks/CLAUDE.md`
- **API Client**: `skillmeat/web/lib/api/CLAUDE.md`
- **Components**: `skillmeat/web/components/CLAUDE.md`
