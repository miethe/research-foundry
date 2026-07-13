/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Derived reasoning record. It is intentionally distinct from a source assertion and records the immutable assertion versions from which it was made.
 */
export interface InferenceRecord {
  schema_version: "1.0";
  type: "inference_record";
  inference_id: string;
  inference_version: number;
  conclusion: string;
  /**
   * @minItems 1
   */
  source_assertion_refs: [
    {
      assertion_id: string;
      assertion_version: number;
    },
    ...{
      assertion_id: string;
      assertion_version: number;
    }[]
  ];
  reasoning: {
    summary: string;
    method: string;
    producer?: string | null;
  };
  status: "active" | "stale" | "invalidated";
}
