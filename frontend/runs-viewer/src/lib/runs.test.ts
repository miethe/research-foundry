import { describe, expect, it } from "vitest";
import { shouldRedactSource } from "./runs";
import type { RFResolvedSource } from "@/types/rf";

function source(overrides: Partial<RFResolvedSource>): RFResolvedSource {
  return {
    source_card_id: "src_test",
    evidence_id: "ev_test",
    relation: "supports",
    resolved: true,
    dangling: false,
    sensitivity: "public",
    quote: "visible quote",
    summary: "visible summary",
    ...overrides,
  };
}

describe("run redaction helpers", () => {
  it("defaults a missing run threshold to public", () => {
    expect(shouldRedactSource(source({ sensitivity: "personal" }), null)).toBe(true);
    expect(shouldRedactSource(source({ sensitivity: "public" }), undefined)).toBe(false);
  });

  it("hides source text that is already redacted in the export", () => {
    expect(
      shouldRedactSource(
        source({
          sensitivity: "public",
          quote: "[redacted:sensitivity]",
          summary: "placeholder",
        }),
        "client_sensitive",
      ),
    ).toBe(true);
  });
});
