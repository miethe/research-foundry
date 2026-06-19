/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * An execution event emitted to CCDash capturing metrics, governance, reuse, and review state.
 */
export interface CCDashEvent {
  event_id: string;
  timestamp: string;
  project: string;
  intent_id?: string;
  task_node_id?: string;
  run_id?: string;
  agent_postures?: string[];
  skillbom_ids?: string[];
  tools?: string[];
  input_artifacts?: string[];
  output_artifacts?: string[];
  metrics?: {
    source_cards_created?: number;
    claims_total?: number;
    claims_supported?: number;
    claims_inference?: number;
    claims_speculation?: number;
    unsupported_claims?: number;
    verification_passed?: boolean;
    tokens_estimated?: number;
    cost_estimated_usd?: number;
    latency_minutes?: number;
    rework_count?: number;
    drift_score?: number;
    quality_score?: string | number;
    [k: string]: any;
  };
  governance?: {
    sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
    key_profile_used?: "personal" | "work_approved" | "client_approved" | "offline_only";
    policy_passed?: boolean;
    violations?: string[];
    [k: string]: any;
  };
  reuse?: {
    meatywiki_writeback_candidate?: boolean;
    skillbom_candidate?: boolean;
    reusable_source_pack_candidate?: boolean;
    [k: string]: any;
  };
  human_review?: {
    required?: boolean;
    status?: "pending" | "approved" | "rejected" | "not_required";
    reviewer?: string | null;
    [k: string]: any;
  };
  [k: string]: any;
}
