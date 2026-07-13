/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable, normalized excerpt from one immutable source edition. The raw rendition and normalized text are both retained so normalization changes cannot conceal material source changes.
 */
export interface Passage {
  schema_version: "1.0";
  type: "passage";
  passage_id: string;
  source_edition_id: string;
  normalized_text: string;
  normalized_text_sha256: string;
  raw_text_sha256: string;
  /**
   * @minItems 1
   */
  selectors: [
    {
      kind: string;
      value: string;
      confidence?: number | null;
      [k: string]: any;
    },
    ...{
      kind: string;
      value: string;
      confidence?: number | null;
      [k: string]: any;
    }[]
  ];
  predecessor_passage_id?: string | null;
  normalization: {
    algorithm: string;
    version: string;
    options?: {
      [k: string]: any;
    };
  };
  context?: {
    [k: string]: any;
  };
}
