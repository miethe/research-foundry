/**
 * P4-SENS-001 fixture: sensitivity gate test sources.
 *
 * Provides a work_sensitive source (must render redaction placeholder, NOT quote)
 * and a public source (must render real quote when expanded).
 */

import type { RFResolvedSource } from "@/types/rf";

export const WORK_SENSITIVE_SOURCE: RFResolvedSource = {
  source_card_id:  "src_sensitive_001",
  evidence_id:     "ev_sensitive_001",
  relation:        "supports",
  locator:         "§3.2 Internal evaluation notes",
  resolved:        true,
  dangling:        false,
  title:           "Internal Evaluation — Work Sensitive",
  source_type:     "internal_doc",
  url:             null,
  trust: {
    source_rank:        "primary",
    reliability_notes:  "Internal document; do not share.",
    known_limitations:  [],
  },
  usage: {
    allowed_for_public_output:      false,
    allowed_for_work_output:        true,
    allowed_for_personal_meatywiki: false,
    citation_required:              true,
  },
  sensitivity:      "work_sensitive",
  evidence_locator: "§3.2 Internal evaluation notes",
  summary:          "This is a confidential summary that must not appear in the UI.",
  quote:            "Verbatim confidential content — must be redacted in the UI.",
};

export const PUBLIC_SOURCE: RFResolvedSource = {
  source_card_id:  "src_public_001",
  evidence_id:     "ev_public_001",
  relation:        "supports",
  locator:         "Introduction",
  resolved:        true,
  dangling:        false,
  title:           "Public Documentation",
  source_type:     "official_doc",
  url:             "https://example.com/docs",
  trust: {
    source_rank:        "primary",
    reliability_notes:  "First-party documentation.",
    known_limitations:  [],
  },
  usage: {
    allowed_for_public_output:      true,
    allowed_for_work_output:        true,
    allowed_for_personal_meatywiki: true,
    citation_required:              false,
  },
  sensitivity:      "public",
  evidence_locator: "Introduction",
  summary:          "Public summary visible to everyone.",
  quote:            "The actual public verbatim quote that should be shown when expanded.",
};
