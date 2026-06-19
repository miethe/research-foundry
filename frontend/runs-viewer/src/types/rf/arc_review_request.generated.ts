/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

export interface ArcReviewRequest {
  id: string;
  run_id: string;
  arc_run_id?: string | null;
  evidence_bundle_id: string;
  /**
   * ARC target (e.g. 'runs/<run>/evidence_bundle.yaml')
   */
  target: string;
  /**
   * Human-readable review objective passed to ARC
   */
  objective: string;
  /**
   * ARC council name (e.g. 'research-review-council')
   */
  council: string;
  roles: string[];
  claims_for_review: {
    [k: string]: any;
  }[];
  verdict?: "approve" | "concern" | "block" | null;
  /**
   * 0=approve, 7=concern|block; null until verdict arrives
   */
  rf_exit_code: number;
  status: "proposed" | "submitted" | "approved" | "concern" | "block";
  governance_context: {
    sensitivity?: string;
    requires_review?: boolean;
    profile?: string;
    [k: string]: any;
  };
  [k: string]: any;
}
