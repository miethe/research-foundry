/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Immutable, ordered event that changes authoritative eligibility before any asynchronous reconciliation of dependent projections.
 */
export type AssertionLifecycleEvent = (
  | {
      transition?: {
        from?: "eligible";
        to?: "stale";
      };
    }
  | {
      transition?: {
        from?: "eligible";
        to?: "invalidated";
      };
    }
  | {
      transition?: {
        from?: "eligible";
        to?: "tombstoned";
      };
    }
  | {
      transition?: {
        from?: "stale";
        to?: "invalidated";
      };
    }
  | {
      transition?: {
        from?: "stale";
        to?: "tombstoned";
      };
    }
  | {
      transition?: {
        from?: "invalidated";
        to?: "tombstoned";
      };
    }
) & {
  [k: string]: any;
} & {
  schema_version: "1.0";
  type: "assertion_lifecycle_event";
  event_id: string;
  sequence: number;
  idempotency_key: string;
  occurred_at: string;
  cause: "corrected_edition" | "invalid_extraction" | "formal_retraction" | "manual_tombstone" | "merge_reversal";
  target: {
    kind: "source_edition" | "passage" | "source_assertion" | "canonical_claim" | "inference_record";
    id: string;
    version: number;
  };
  transition: {
    from: "eligible" | "stale" | "invalidated" | "tombstoned";
    to: "stale" | "invalidated" | "tombstoned";
  };
  authoritative_action?: "block_reuse";
  dependent_actions?: {
    object_kind:
      | "canonical_claim_edge"
      | "inference"
      | "report_revision"
      | "run"
      | "export"
      | "cache_index"
      | "writeback_receipt";
    action:
      | "block_reuse"
      | "mark_stale"
      | "retract"
      | "regenerate"
      | "purge_derived_cache"
      | "queue_default_denied_reconciliation";
  }[];
};
