/**
 * Tiny className combiner. Accepts strings, falsy values, and
 * `{ className: boolean }` maps; joins the truthy ones with a single space.
 *
 * The design system is ported verbatim from the prototype, so this is only a
 * convenience for conditionally toggling existing class names — it never
 * generates new styles.
 */
export type ClassValue =
  | string
  | number
  | null
  | undefined
  | false
  | Record<string, boolean | null | undefined>
  | ClassValue[];

export function cn(...values: ClassValue[]): string {
  const out: string[] = [];
  for (const value of values) {
    if (!value) continue;
    if (typeof value === "string" || typeof value === "number") {
      out.push(String(value));
    } else if (Array.isArray(value)) {
      const nested = cn(...value);
      if (nested) out.push(nested);
    } else {
      for (const [key, on] of Object.entries(value)) {
        if (on) out.push(key);
      }
    }
  }
  return out.join(" ");
}

export default cn;
