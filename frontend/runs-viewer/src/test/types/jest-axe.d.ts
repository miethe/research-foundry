/**
 * Vitest type augmentation for jest-axe's `toHaveNoViolations()` matcher.
 *
 * `@types/jest-axe` only augments Jest's `jest.Matchers` / `@jest/expect`
 * interfaces (see node_modules/@types/jest-axe/index.d.ts) — it has no
 * awareness of vitest's `Assertion` interface. Mirrors the pattern
 * `@testing-library/jest-dom/vitest.d.ts` uses for its own matchers.
 *
 * Note: `src/test/**` is excluded from `tsconfig.app.json` (see its
 * `exclude` list), so this file is a developer-experience aid for the
 * editor/vitest typecheck mode only — it is not part of the
 * `tsc -p tsconfig.app.json --noEmit` production gate.
 */
import "vitest";

declare module "vitest" {
  interface Assertion<T = unknown> {
    toHaveNoViolations(): T;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}
