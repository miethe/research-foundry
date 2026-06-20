/**
 * kindIcons.tsx — Tiny inline SVG icon components for each LineageNodeKind.
 * No external icon library; each glyph is a minimal 16×16 path.
 */

import type { ReactElement } from "react";
import type { LineageNodeKind } from "./lineageTree";

// ── Per-kind icon components ───────────────────────────────────────────────────

export function KindIconRun({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="1" y="2"   width="14" height="3" rx="1" />
      <rect x="1" y="6.5" width="14" height="3" rx="1" />
      <rect x="1" y="11"  width="14" height="3" rx="1" />
    </svg>
  );
}

export function KindIconSource({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M3 2h7l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z" />
      <path d="M10 2v3h3" />
    </svg>
  );
}

export function KindIconExtraction({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M2 4h4v4H4a2 2 0 0 0 2 2v2a4 4 0 0 1-4-4V4zm8 0h4v4h-2a2 2 0 0 0 2 2v2a4 4 0 0 1-4-4V4z" />
    </svg>
  );
}

export function KindIconClaim({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="2.5" y="0.5" width="1" height="15" rx="0.5" />
      <path d="M3.5 2.5 L13 5 L3.5 7.5 Z" />
    </svg>
  );
}

export function KindIconReport({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M3 2h7l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z" />
      <path d="M10 2v3h3" />
      <line x1="4" y1="9"    x2="12" y2="9"   />
      <line x1="4" y1="11.5" x2="9"  y2="11.5" />
    </svg>
  );
}

export function KindIconWriteback({ size = 14 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M8 10V2M5 5l3-3 3 3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M2 12v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-1" strokeLinecap="round" />
    </svg>
  );
}

// ── renderKindIcon — convenience wrapper used by LineageList / LineageDetailPanel ──

export function KindIcon({ kind, size = 14 }: { kind: LineageNodeKind; size?: number }): ReactElement {
  switch (kind) {
    case "run":        return <KindIconRun size={size} />;
    case "source":     return <KindIconSource size={size} />;
    case "extraction": return <KindIconExtraction size={size} />;
    case "claim":      return <KindIconClaim size={size} />;
    case "report":     return <KindIconReport size={size} />;
    case "writeback":  return <KindIconWriteback size={size} />;
  }
}

/** Chevron icons for expand/collapse toggles */
export function ChevronRight({ size = 12 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 2.5 L7.5 6 L4 9.5" />
    </svg>
  );
}

export function ChevronDown({ size = 12 }: { size?: number }): ReactElement {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 4 L6 7.5 L9.5 4" />
    </svg>
  );
}
