/**
 * reportOutlineUtils.ts — pure utilities for the report heading outline.
 *
 * Split from ReportOutline.tsx to satisfy the react-refresh/only-export-components
 * ESLint rule (components and non-component exports must not share a module).
 *
 * Consumers:
 *   - ReportOutline.tsx    — component uses OutlineHeading type
 *   - ReportRenderer.tsx   — uses slugify for heading id generation
 *   - ReportOverlay.tsx    — uses extractHeadings to populate the outline
 *   - report-outline.test.tsx — tests both functions directly
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export interface OutlineHeading {
  /** Slug used as the element id on the rendered heading (matches ReportRenderer). */
  slug:  string;
  /** Display text (the raw heading text, without markup). */
  text:  string;
  /** Heading depth: 2 = h2, 3 = h3. h1 is the run title — not included. */
  level: 2 | 3;
}

// ── Slug helpers ──────────────────────────────────────────────────────────────

/**
 * Converts a heading string to a URL-safe slug.
 * Must stay in sync with makeSlugCounter (ReportRenderer.tsx) so anchor links work.
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")   // strip non-word chars except hyphens
    .replace(/\s+/g, "-")       // spaces → hyphens
    .replace(/-+/g, "-")        // collapse multiple hyphens
    .replace(/^-+|-+$/g, "");   // trim leading/trailing hyphens
}

/**
 * Extracts h2/h3 headings from a markdown string.
 * Returns deduplicated slugs (appends -2, -3, … for duplicates).
 * Ignores code blocks (``` fences) and front-matter (--- blocks).
 */
export function extractHeadings(markdown: string): OutlineHeading[] {
  const headings: OutlineHeading[] = [];
  const slugCounts: Record<string, number> = {};

  // Strip front-matter
  let body = markdown.trimStart();
  if (body.startsWith("---")) {
    const lines = body.split(/\r?\n/);
    const endIdx = lines.findIndex((l, i) => i > 0 && l.trim() === "---");
    if (endIdx > 0) {
      body = lines.slice(endIdx + 1).join("\n");
    }
  }

  const lines = body.split(/\r?\n/);
  let inCodeFence = false;

  for (const line of lines) {
    // Track fenced code blocks
    if (/^```/.test(line)) {
      inCodeFence = !inCodeFence;
      continue;
    }
    if (inCodeFence) continue;

    // Match ATX headings (## and ###)
    const match = line.match(/^(#{2,3})\s+(.+)$/);
    if (!match) continue;
    const level = match[1]!.length as 2 | 3;
    if (level > 3) continue;

    // Strip inline markup (bold, italic, code, links) for display text
    const rawText = (match[2] ?? "").trim()
      .replace(/\*\*(.+?)\*\*/g, "$1")
      .replace(/\*(.+?)\*/g, "$1")
      .replace(/`(.+?)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");

    const baseSlug = slugify(rawText);
    if (!baseSlug) continue;

    // Deduplicate slugs
    const count = slugCounts[baseSlug] ?? 0;
    slugCounts[baseSlug] = count + 1;
    const slug = count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;

    headings.push({ slug, text: rawText, level });
  }

  return headings;
}
