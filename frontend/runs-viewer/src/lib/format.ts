/**
 * Display formatting helpers shared across screens. Pure functions, no deps.
 */

/** 0..1 → integer percent string, e.g. 0.62 → "62%". */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0%";
  return `${Math.round(value * 100)}%`;
}

/** Minutes from midnight → "9:05 AM" style clock label. */
export function formatClock(minutes: number): string {
  const total = ((minutes % 1440) + 1440) % 1440;
  const h24 = Math.floor(total / 60);
  const min = total % 60;
  const period = h24 < 12 ? "AM" : "PM";
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${String(min).padStart(2, "0")} ${period}`;
}

/** Minutes → compact duration, e.g. 90 → "1h 30m", 45 → "45m". */
export function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null || minutes <= 0) return "0m";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Snap a minute value to the nearest `step` (e.g. 5/15/30). */
export function snapMinutes(minutes: number, step: number): number {
  if (!step || step <= 0) return Math.round(minutes);
  return Math.round(minutes / step) * step;
}

/** Initials fallback from a display name when no avatar string is present. */
export function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** ISO timestamp → relative label, e.g. "32m ago", "1 hr ago", "Yesterday". */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const diffMs = now.getTime() - then.getTime();
  if (Number.isNaN(diffMs)) return iso;
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return "Just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return hr === 1 ? "1 hr ago" : `${hr} hrs ago`;
  const day = Math.floor(hr / 24);
  if (day === 1) return "Yesterday";
  if (day < 7) return `${day} days ago`;
  return then.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Compact number, e.g. 36610 → "36.6k". */
export function formatCompact(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0";
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

/** USD cost, e.g. 0.91 → "$0.91". */
export function formatCost(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}
