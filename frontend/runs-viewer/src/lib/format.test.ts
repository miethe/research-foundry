import { describe, expect, it } from "vitest";
import {
  formatClock,
  formatCost,
  formatDuration,
  formatPercent,
  formatRelativeTime,
  initialsOf,
  snapMinutes,
} from "./format";

describe("format helpers", () => {
  it("formats 0..1 as integer percent", () => {
    expect(formatPercent(0.62)).toBe("62%");
    expect(formatPercent(0)).toBe("0%");
    expect(formatPercent(1)).toBe("100%");
    expect(formatPercent(null)).toBe("0%");
  });

  it("formats minutes-from-midnight as a clock label", () => {
    expect(formatClock(0)).toBe("12:00 AM");
    expect(formatClock(9 * 60 + 5)).toBe("9:05 AM");
    expect(formatClock(13 * 60)).toBe("1:00 PM");
  });

  it("formats durations compactly", () => {
    expect(formatDuration(45)).toBe("45m");
    expect(formatDuration(60)).toBe("1h");
    expect(formatDuration(90)).toBe("1h 30m");
    expect(formatDuration(0)).toBe("0m");
  });

  it("formats relative timestamps", () => {
    const now = new Date("2026-06-03T12:00:00Z");
    expect(formatRelativeTime("2026-06-03T11:59:40Z", now)).toBe("Just now");
    expect(formatRelativeTime("2026-06-03T11:28:00Z", now)).toBe("32m ago");
    expect(formatRelativeTime("2026-06-03T11:00:00Z", now)).toBe("1 hr ago");
    expect(formatRelativeTime("2026-06-03T07:00:00Z", now)).toBe("5 hrs ago");
    expect(formatRelativeTime("2026-06-02T10:00:00Z", now)).toBe("Yesterday");
    expect(formatRelativeTime("2026-05-31T10:00:00Z", now)).toBe("3 days ago");
    expect(formatRelativeTime("not-a-date", now)).toBe("not-a-date");
  });

  it("snaps minutes to a step", () => {
    expect(snapMinutes(7, 5)).toBe(5);
    expect(snapMinutes(8, 5)).toBe(10);
    expect(snapMinutes(7, 0)).toBe(7);
  });

  it("derives initials and formats cost", () => {
    expect(initialsOf("Alicia Chen")).toBe("AC");
    expect(formatCost(0.91)).toBe("$0.91");
  });
});
